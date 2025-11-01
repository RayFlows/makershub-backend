# app/services/task_service.py
"""
任务服务类：处理与任务相关的所有业务逻辑
[v2.0 SQLAlchemy 迁移版 - 最终整合版]
"""
from typing import Optional, List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from datetime import datetime
import random
from dateutil import parser

from app.models.task import Task
from app.models.user import User
from app.services.arrange_service import ArrangeService

class TaskService:
    """
    任务服务类，封装了所有创建、查询、更新和状态变更的任务相关业务逻辑。
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
        辅助函数：将SQLAlchemy Task ORM对象安全地转换为字典。
        用于API响应序列化，以保持与旧接口的数据结构兼容，特别是处理时间格式。
        
        Args:
            task: SQLAlchemy的Task模型实例。
        
        Returns:
            一个包含任务信息的字典，如果输入为None则返回None。
        """
        if not task:
            return None
        
        return {
            "task_id": task.task_id,
            "department": task.department,
            "task_type": task.task_type,
            "maker_id": task.maker_id,
            "name": task.name,
            "content": task.content,
            "state": task.state,
            "deadline": task.deadline.isoformat().replace('+00:00', 'Z') if task.deadline else None,
            "created_at": task.created_at.isoformat().replace('+00:00', 'Z') if task.created_at else None,
            "updated_at": task.updated_at.isoformat().replace('+00:00', 'Z') if task.updated_at else None
        }

    async def get_task_by_id(self, db: AsyncSession, task_id: str) -> Optional[Task]:
        """
        通过业务ID (task_id) 获取任务的 ORM 实例。
        这是一个内部使用的辅助方法，方便其他服务方法复用。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            task_id: 任务的业务唯一标识符。
            
        Returns:
            Task ORM实例，如果未找到则返回None。
        """
        logger.debug(f"正在通过 task_id 查询任务 ORM: {task_id}")
        stmt = select(Task).where(Task.task_id == task_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_task(self, db: AsyncSession, task_data: Dict[str, Any]) -> Task:
        """
        创建新任务。如果任务类型匹配，会自动从排班系统分配负责人并切换排班。
        整个创建过程（包括排班切换）都在同一个数据库事务中，保证操作的原子性。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            task_data: 包含任务所有信息的字典。
            
        Returns:
            新创建的Task ORM实例。
        
        Raises:
            ValueError: 如果负责人不存在或姓名与ID不匹配。
            Exception: 其他数据库或未知错误。
        """
        logger.info(f"开始创建新任务，原始负责人ID: {task_data.get('maker_id')}")
        maker_id = task_data["maker_id"]
        name = task_data["name"]
        
        # 验证原始负责人是否存在且姓名匹配
        logger.debug(f"验证负责人信息: maker_id={maker_id}, name={name}")
        user_stmt = select(User).where(User.maker_id == maker_id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"负责人不存在 (maker_id: {maker_id})")
            raise ValueError(f"负责人不存在 (maker_id: {maker_id})")
        if user.real_name != name:
            logger.warning(f"负责人姓名与协会ID不匹配 (请求姓名: {name}, 实际姓名: {user.real_name})")
            raise ValueError(f"负责人姓名与协会ID不匹配 (请求姓名: {name}, 实际姓名: {user.real_name})")

        deadline = parser.isoparse(task_data["deadline"])

        # [关键整合] 激活自动排班逻辑
        task_type = task_data.get("task_type")
        if task_type in [1, 2, 3]:
            logger.info(f"任务类型 {task_type} 匹配自动排班规则，开始处理排班逻辑...")
            arrange_service = ArrangeService()
            current_arranger = await arrange_service.get_current_arranger(db, task_type)
            if current_arranger and current_arranger.get("maker_id"):
                maker_id = current_arranger["maker_id"]
                name = current_arranger["name"]
                logger.success(f"✅ 自动分配任务给值班人员 | 类型: {task_type} | 姓名: {name} | ID: {maker_id}")
                
                # 在同一事务中切换排班到下一个人
                await arrange_service.switch_to_next_arranger(db, task_type)
            else:
                logger.warning(f"⚠️ 未找到任务类型 {task_type} 的当前值班人员，将使用原始手动分配的负责人。")
        else:
            logger.info(f"任务类型 {task_type} 不属于自动排班范围，使用手动指定的负责人。")

        new_task = Task(
            task_id=self._generate_task_id(),
            department=task_data["department"],
            task_type=task_data["task_type"],
            maker_id=maker_id,
            name=name,
            content=task_data["content"],
            deadline=deadline,
            state=0  # 初始状态为未完成
        )
        
        db.add(new_task)
        await db.flush()
        await db.refresh(new_task)
        logger.success(f"✅ 任务已成功存入数据库: {new_task.task_id}")
        return new_task

    async def update_task_state(self, db: AsyncSession, task_id: str, new_state: int) -> Task:
        """
        更新任务的状态 (完成或取消)。这是一个核心的状态机转换方法。
        
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
        if new_state == 1: # 尝试完成任务
            if task.state == 2:
                logger.warning(f"非法操作：尝试完成一个已取消的任务 | TaskID: {task_id}")
                raise ValueError("已取消的任务不能被完成")
            logger.info(f"任务标记为已完成: {task_id}")
        elif new_state == 2: # 尝试取消任务
            if task.state == 1:
                logger.warning(f"非法操作：尝试取消一个已完成的任务 | TaskID: {task_id}")
                raise ValueError("已完成的任务不能被取消")
            logger.info(f"任务标记为已取消: {task_id}")
        else:
            logger.error(f"非法的目标状态码: {new_state}")
            raise ValueError(f"无效的目标状态: {new_state}")

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
        更新任务的详细信息（如内容、负责人等）。
        
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
            raise ValueError(f"已完成的任务不能被更新 (当前状态: {task.state})")
        
        original_state = task.state
        
        # 如果更新负责人信息，需要进行验证
        if "maker_id" in update_data or "name" in update_data:
            maker_id = update_data.get("maker_id", task.maker_id)
            name = update_data.get("name", task.name)
            logger.debug(f"更新负责人，验证新负责人信息: maker_id={maker_id}, name={name}")
            user_stmt = select(User).where(User.maker_id == maker_id)
            user_result = await db.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            if not user or user.real_name != name:
                logger.warning(f"新负责人信息验证失败 | MakerID: {maker_id}, Name: {name}")
                raise ValueError("负责人姓名与协会ID不匹配或负责人不存在")
            
            task.maker_id = maker_id
            task.name = name
        
        # 更新其他字段
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
        """获取所有任务，按创建时间降序。"""
        logger.info("正在查询所有任务...")
        stmt = select(Task).order_by(Task.created_at.desc())
        result = await db.execute(stmt)
        tasks = result.scalars().all()
        logger.info(f"查询到 {len(tasks)} 个任务。")
        return [self._task_to_dict(task) for task in tasks]

    async def get_user_tasks(self, db: AsyncSession, maker_id: str) -> List[Dict[str, Any]]:
        """获取指定用户的所有任务。"""
        logger.info(f"正在查询用户 {maker_id} 的任务...")
        stmt = select(Task).where(Task.maker_id == maker_id).order_by(Task.created_at.desc())
        result = await db.execute(stmt)
        tasks = result.scalars().all()
        logger.info(f"为用户 {maker_id} 查询到 {len(tasks)} 个任务。")
        return [self._task_to_dict(task) for task in tasks]