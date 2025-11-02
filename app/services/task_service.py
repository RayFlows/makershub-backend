# app/services/task_service.py
"""
任务服务类：处理与任务相关的所有业务逻辑
[v0.2 SQLAlchemy 重构版]
"""
from typing import Optional, List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger
from datetime import datetime
import random
from dateutil import parser

from app.models.task import Task
from app.models.user import User
# 依赖已迁移的 ArrangeService
from app.services.arrange_service import ArrangeService

class TaskService:
    """
    任务服务类，封装了所有创建、查询、更新和状态变更的任务相关业务逻辑。
    在v0.2重构中，所有逻辑都已基于外键和ORM关系进行重写，以确保数据一致性和性能。
    """

    @staticmethod
    def _generate_task_id() -> str:
        """
        生成全局唯一的任务ID。
        格式: TS + 当前时间戳(YYYYMMDDHHMMSSms) + 3位随机数。
        
        Returns:
            str: 生成的唯一任务ID。
        """
        now = datetime.utcnow()
        timestamp = now.strftime("%Y%m%d%H%M%S%f")[:-3]
        random_suffix = f"{random.randint(0, 999):03d}"
        logger.debug(f"生成新的任务ID: TS{timestamp}_{random_suffix}")
        return f"TS{timestamp}_{random_suffix}"

    def _task_to_dict(self, task: Task) -> Optional[Dict[str, Any]]:
        """
        [v0.2 兼容性保障] 辅助函数：将 Task ORM 对象转换为兼容旧版API的字典。
        
        这个函数是保证后端重构对前端透明的核心。即使数据库结构已经改变（例如，
        不再有 name 和 maker_id 字段），它也会通过 SQLAlchemy 的 relationship 
        访问关联的 User 对象，重新构建出与旧 API 完全一致的 JSON 结构。

        Args:
            task: SQLAlchemy的Task模型实例，必须已预加载了 user 关系。
        
        Returns:
            一个包含任务信息的字典，如果输入为空或关系未加载则返回None。
        """
        if not task or not task.user:
            logger.warning(f"序列化任务失败：任务对象为空或其 user 关系未加载。Task ID: {task.task_id if task else 'N/A'}")
            return None
        
        return {
            "task_id": task.task_id,
            "department": task.department,
            "task_type": task.task_type,
            # [核心兼容] 通过 relationship 访问 user 对象的属性，伪造出旧的字段
            "maker_id": task.user.maker_id,
            "name": task.user.real_name,
            "content": task.content,
            "state": task.state,
            "deadline": task.deadline.isoformat().replace('+00:00', 'Z') if task.deadline else None,
            "created_at": task.created_at.isoformat().replace('+00:00', 'Z') if task.created_at else None,
            "updated_at": task.updated_at.isoformat().replace('+00:00', 'Z') if task.updated_at else None
        }

    async def get_task_by_id(self, db: AsyncSession, task_id: str) -> Optional[Task]:
        """
        [v0.2] 通过业务ID (task_id) 获取任务的 ORM 实例，并预加载负责人信息。
        使用 `selectinload(Task.user)` 性能优化，避免N+1查询。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            task_id: 任务的业务唯一标识符。
            
        Returns:
            Task ORM实例，如果未找到则返回None。
        """
        logger.debug(f"正在通过 task_id 查询任务 ORM: {task_id}")
        stmt = select(Task).where(Task.task_id == task_id).options(selectinload(Task.user))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_task(self, db: AsyncSession, maker_id: str, task_data: Dict[str, Any]) -> Task:
        """
        [v0.2] 创建新任务。
        如果任务类型匹配，会自动从排班系统分配负责人并切换排班。
        整个创建过程（包括排班切换）都在同一个数据库事务中，保证操作的原子性。

        Args:
            db: SQLAlchemy的异步数据库会话。
            maker_id: 请求中手动指定的负责人 maker_id。
            task_data: 包含任务其他信息的字典。
            
        Returns:
            新创建的Task ORM实例。
        
        Raises:
            ValueError: 如果负责人不存在。
        """
        logger.info(f"开始创建新任务，请求的负责人 maker_id: {maker_id}")
        
        target_maker_id = maker_id # 默认为手动指定的负责人
        
        # [核心交互] 与 ArrangeService 交互，以确定最终负责人
        task_type = task_data.get("task_type")
        if task_type in [1, 2, 3]:
            logger.info(f"任务类型 {task_type} 匹配自动排班规则，开始处理排班逻辑...")
            arrange_service = ArrangeService()
            current_arranger = await arrange_service.get_current_arranger(db, task_type)
            if current_arranger and current_arranger.get("maker_id"):
                target_maker_id = current_arranger["maker_id"]
                logger.success(f"✅ 自动分配任务给值班人员: {target_maker_id}")
                # 在同一事务中切换排班
                await arrange_service.switch_to_next_arranger(db, task_type)
            else:
                logger.warning(f"⚠️ 未找到任务类型 {task_type} 的当前值班人员，将使用手动指定的负责人: {target_maker_id}")
        else:
            logger.info(f"任务类型 {task_type} 不属于自动排班范围，使用手动指定的负责人。")
        
        # [核心改造] 通过最终的 maker_id 找到 User 对象，以获取用于外键关联的 user.id
        logger.debug(f"正在查询最终负责人 User 对象: maker_id={target_maker_id}")
        user_stmt = select(User).where(User.maker_id == target_maker_id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if not user:
            logger.error(f"创建任务失败：最终确定的负责人 (maker_id: {target_maker_id}) 不存在。")
            raise ValueError(f"负责人 (maker_id: {target_maker_id}) 不存在")

        deadline = parser.isoparse(task_data["deadline"])

        new_task = Task(
            task_id=self._generate_task_id(),
            department=task_data["department"],
            task_type=task_data["task_type"],
            user_id=user.id, # [核心改造] 使用外键 user.id
            content=task_data["content"],
            deadline=deadline,
            state=0
        )
        
        db.add(new_task)
        await db.flush()
        await db.refresh(new_task)
        logger.success(f"✅ 任务已成功存入数据库: {new_task.task_id}, 负责人: {user.real_name}")
        return new_task

    async def update_task_state(self, db: AsyncSession, task_id: str, new_state: int) -> Task:
        """
        [v0.2] 更新任务的状态 (完成或取消)。这是一个核心的状态机转换方法。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            task_id: 任务的业务ID。
            new_state: 新的状态码 (1=完成, 2=取消)。
            
        Returns:
            更新后的Task ORM实例。
            
        Raises:
            ValueError: 如果任务不存在或状态转换不被允许。
        """
        logger.info(f"请求更新任务状态: TaskID={task_id}, NewState={new_state}")
        task = await self.get_task_by_id(db, task_id)
        if not task:
            logger.warning(f"尝试更新一个不存在的任务状态: {task_id}")
            raise ValueError("任务不存在")

        # 检查状态转换的业务规则
        if new_state == 1 and task.state == 2: # 尝试完成一个已取消的任务
            logger.warning(f"非法操作：尝试完成一个已取消的任务 | TaskID: {task_id}")
            raise ValueError("已取消的任务不能被完成")
        if new_state == 2 and task.state == 1: # 尝试取消一个已完成的任务
            logger.warning(f"非法操作：尝试取消一个已完成的任务 | TaskID: {task_id}")
            raise ValueError("已完成的任务不能被取消")
        
        if task.state == new_state:
            logger.warning(f"任务状态已经是 {new_state}，无需重复操作: {task_id}")
            return task

        task.state = new_state
        db.add(task)
        await db.flush()
        await db.refresh(task)
        logger.success(f"✅ 任务状态更新成功: TaskID={task_id}, State={task.state}")
        return task
        
    async def update_task_details(self, db: AsyncSession, task_id: str, update_data: Dict[str, Any]) -> Task:
        """
        [v0.2] 更新任务的详细信息（如内容、负责人等）。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            task_id: 任务的业务ID。
            update_data: 包含要更新字段的字典。
        
        Returns:
            更新后的Task ORM实例。
        
        Raises:
            ValueError: 如果任务不存在或状态不允许更新，或者负责人信息无效。
        """
        logger.info(f"请求更新任务详情: {task_id}")
        task = await self.get_task_by_id(db, task_id)
        if not task:
            logger.warning(f"尝试更新一个不存在的任务详情: {task_id}")
            raise ValueError("任务不存在")

        if task.state == 1: # 已完成的任务不能被更新
            logger.warning(f"非法操作：尝试更新一个已完成的任务 | TaskID: {task_id}, State: {task.state}")
            raise ValueError("已完成的任务不能被更新")
        
        original_state = task.state
        
        # 如果更新负责人信息，需要验证并更新 user_id
        if "maker_id" in update_data:
            new_maker_id = update_data["maker_id"]
            logger.debug(f"更新负责人，验证新负责人信息: maker_id={new_maker_id}")
            user_stmt = select(User).where(User.maker_id == new_maker_id)
            user_result = await db.execute(user_stmt)
            new_user = user_result.scalar_one_or_none()
            if not new_user:
                logger.warning(f"新负责人信息验证失败 | MakerID: {new_maker_id}")
                raise ValueError(f"新负责人 (maker_id: {new_maker_id}) 不存在")
            task.user_id = new_user.id # [核心改造] 更新外键
        
        # 更新其他可编辑字段
        for field in ["department", "task_type", "content"]:
            if field in update_data:
                setattr(task, field, update_data[field])
        if "deadline" in update_data:
            task.deadline = parser.isoparse(update_data["deadline"])
        
        # 业务规则：重新编辑后，状态重置为未完成
        task.state = 0
        if original_state == 2:
            logger.info(f"一个已取消的任务被重新编辑并激活: {task_id}")

        db.add(task)
        await db.flush()
        await db.refresh(task)
        logger.success(f"✅ 任务详情更新成功: {task_id}")
        return task
    
    async def get_all_tasks(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """[v0.2] 获取所有任务，并预加载负责人信息以优化性能。"""
        logger.info("正在查询所有任务...")
        stmt = select(Task).order_by(Task.created_at.desc()).options(selectinload(Task.user))
        result = await db.execute(stmt)
        tasks = result.scalars().all()
        logger.info(f"查询到 {len(tasks)} 个任务。")
        return [self._task_to_dict(task) for task in tasks]

    async def get_user_tasks(self, db: AsyncSession, maker_id: str) -> List[Dict[str, Any]]:
        """[v0.2] 获取指定用户的所有任务。"""
        logger.info(f"正在查询用户 (maker_id: {maker_id}) 的任务...")
        
        # [核心改造] 先通过 maker_id 找到 User，再通过 relationship 获取 tasks
        user_stmt = (
            select(User)
            .where(User.maker_id == maker_id)
            .options(
                selectinload(User.tasks).selectinload(Task.user) # 预加载 User 的 tasks，以及每个 task 关联的 user
            )
        )
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"查询用户任务失败：未找到 maker_id 为 {maker_id} 的用户。")
            return []
        
        # 在内存中对已加载的任务进行排序
        tasks = sorted(user.tasks, key=lambda t: t.created_at, reverse=True)
        
        logger.info(f"为用户 {user.real_name} 查询到 {len(tasks)} 个任务。")
        return [self._task_to_dict(task) for task in tasks]