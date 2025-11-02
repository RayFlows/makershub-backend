# app/services/arrange_service.py
"""
排班服务类：处理排班相关的业务逻辑
[v0.2 SQLAlchemy 重构版]
"""
from typing import Optional, List, Dict, Any
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger
from datetime import datetime
import random
from collections import defaultdict

from app.models.arrange import Arrange
from app.models.user import User

class ArrangeService:
    """
    排班服务类，封装了所有与学年工作排班相关的业务逻辑。
    在v0.2重构中，所有逻辑都已基于外键和ORM关系进行重写，以确保数据一致性和性能。
    """

    @staticmethod
    def _generate_arrange_id() -> str:
        """生成全局唯一的排班ID。"""
        now = datetime.utcnow()
        timestamp = now.strftime("%Y%m%d%H%M%S%f")[:-3]
        random_suffix = f"{random.randint(0, 999):03d}"
        logger.debug(f"生成新的排班ID: AR{timestamp}_{random_suffix}")
        return f"AR{timestamp}_{random_suffix}"

    def _arrange_to_dict(self, arrange: Arrange, user: User) -> Dict[str, Any]:
        """
        [v0.2 兼容性保障] 辅助函数：将 Arrange ORM 对象转换为兼容旧版API的字典。
        
        Args:
            arrange: SQLAlchemy的Arrange模型实例。
            user: 与该排班关联的User模型实例。
        
        Returns:
            一个包含排班信息的字典，其中 name 和 maker_id 是为了API兼容而添加的。
        """

        return {
            "name": user.real_name,
            "maker_id": user.maker_id,
            "order": arrange.order,
            "current": arrange.current,
            # arrange_id 等其他内部字段通常不在列表视图中需要
        }

    async def switch_to_next_arranger(self, db: AsyncSession, task_type: int) -> bool:
        """
        [v0.2 原子操作] 切换到指定任务类型的下一个值班人员。
        此操作是原子性的，并使用行级锁来防止并发冲突。
        """
        logger.info(f"开始为任务类型 {task_type} 切换排班...")
        try:
            # 1. 使用 SELECT ... FOR UPDATE 锁定该任务类型的所有排班行以防止并发问题
            stmt = (
                select(Arrange)
                .where(Arrange.task_type == task_type)
                .order_by(Arrange.order)
                .with_for_update()
                .options(selectinload(Arrange.user)) # 预加载 User 对象，避免 N+1 查询
            )
            result = await db.execute(stmt)
            arrangements = result.scalars().all()

            if not arrangements:
                logger.warning(f"切换排班失败：任务类型 {task_type} 没有任何排班记录。")
                return False

            # 2. 查找当前值班人员
            current_index = -1
            for idx, arrange in enumerate(arrangements):
                if arrange.current:
                    current_index = idx
                    break
            
            # 3. 如果没有当前值班人员，则将第一个设为当前
            if current_index == -1:
                logger.warning(f"未找到当前值班人员，将自动设置第一个为当前 | 任务类型: {task_type}")
                arrangements[0].current = True
                db.add(arrangements[0])
                return True

            # 4. 更新当前和下一个值班人员的状态
            current_arranger_obj = arrangements[current_index]
            next_index = (current_index + 1) % len(arrangements)
            next_arranger_obj = arrangements[next_index]

            current_arranger_obj.current = False
            next_arranger_obj.current = True
            
            db.add_all([current_arranger_obj, next_arranger_obj])
            
            # 通过 relationship 访问 user.real_name，不再需要冗余的 name 字段
            logger.success(f"✅ 排班切换成功 | 类型: {task_type} | 当前: {current_arranger_obj.user.real_name} -> 下一个: {next_arranger_obj.user.real_name}")
            return True

        except Exception as e:
            logger.error(f"排班切换时发生数据库错误，事务将回滚: {e}", exc_info=True)
            raise

    async def get_all_arrangements(self, db: AsyncSession) -> Dict[str, List[Dict[str, Any]]]:
        """[v0.2] 获取所有排班安排，按任务类型分组。"""
        logger.info("正在获取所有排班安排...")
        stmt = (
            select(Arrange)
            .order_by(Arrange.task_type, Arrange.order)
            .options(selectinload(Arrange.user)) # 关键性能优化: 一次性加载所有关联的 User
        )
        result = await db.execute(stmt)
        arrangements = result.scalars().all()
        
        grouped = defaultdict(list)
        for arrange in arrangements:
            # 通过 relationship 调用序列化方法
            grouped[str(arrange.task_type)].append(self._arrange_to_dict(arrange, arrange.user))
        
        logger.info(f"成功获取并分组了 {len(arrangements)} 条排班记录。")
        return {
            "1": grouped.get("1", []),
            "2": grouped.get("2", []),
            "3": grouped.get("3", [])
        }
    
    async def batch_create_arrangements(self, db: AsyncSession, arrangements_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        [v0.2 原子操作] 批量创建排班安排，会先清空所有旧的排班数据。
        整个过程是事务性的，要么全部成功，要么全部失败回滚。
        """
        logger.info("开始批量创建/重置排班安排...")
        try:
            # 1. 在事务中先删除所有现有排班记录
            delete_stmt = delete(Arrange)
            await db.execute(delete_stmt)
            logger.info("已清空所有旧的排班记录。")
            
            # 2. 准备新的排班记录，这里需要通过 maker_id 找到 user.id
            new_arrangements = []
            all_maker_ids = [
                person["maker_id"]
                for person_list in arrangements_data.values()
                for person in person_list
            ]
            
            # 一次性查询所有需要的 User 对象，避免在循环中查询数据库
            users_stmt = select(User).where(User.maker_id.in_(all_maker_ids))
            users_result = await db.execute(users_stmt)
            # 创建一个 maker_id -> User 对象的映射，便于快速查找
            user_map = {user.maker_id: user for user in users_result.scalars()}

            for task_type_str, arrangement_list in arrangements_data.items():
                task_type = int(task_type_str)
                for arrange_data in arrangement_list:
                    maker_id = arrange_data["maker_id"]
                    user = user_map.get(maker_id)
                    if not user:
                        logger.error(f"批量创建失败：未找到 maker_id 为 {maker_id} 的用户。")
                        raise ValueError(f"用户 (maker_id: {maker_id}) 不存在，无法创建排班。")
                    
                    new_arrangements.append(
                        Arrange(
                            arrange_id=self._generate_arrange_id(),
                            user_id=user.id, # [核心改造] 使用 user.id 而不是 maker_id
                            task_type=task_type,
                            order=arrange_data["order"],
                            current=arrange_data["current"]
                        )
                    )
            
            # 3. 批量插入新记录
            db.add_all(new_arrangements)
            logger.success(f"✅ 批量创建排班成功，准备插入 {len(new_arrangements)} 条新记录。")
            
            return {
                "total_created": len(new_arrangements),
                "types": list(arrangements_data.keys())
            }
        except Exception as e:
            logger.error(f"批量创建排班失败，事务将回滚: {e}", exc_info=True)
            raise

    async def get_current_arranger(self, db: AsyncSession, task_type: int) -> Optional[Dict[str, str]]:
        """[v0.2] 获取指定任务类型的当前值班人员。"""
        logger.debug(f"正在查询任务类型 {task_type} 的当前值班人员...")
        stmt = (
            select(Arrange)
            .where(Arrange.task_type == task_type, Arrange.current == True)
            .options(selectinload(Arrange.user)) # 预加载 User
        )
        result = await db.execute(stmt)
        arrangement = result.scalar_one_or_none()

        if not arrangement:
            logger.warning(f"未找到任务类型 {task_type} 的当前值班人员")
            return None
            
        logger.debug(f"找到当前值班人员: {arrangement.user.real_name}")
        # 通过 relationship 返回 API 兼容的数据
        return {"name": arrangement.user.real_name, "maker_id": arrangement.user.maker_id}

    async def get_current_makers(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """[v0.2] 获取所有任务类型的当前值班人员。"""
        logger.info("正在查询所有任务类型的当前值班人员...")
        stmt = (
            select(Arrange)
            .where(Arrange.current == True)
            .options(selectinload(Arrange.user)) # 一次性加载所有关联的 User
        )
        result = await db.execute(stmt)
        current_arrangers = result.scalars().all()
        
        arranger_map = {arr.task_type: arr.user for arr in current_arrangers}
        
        result_list = []
        for task_type in [1, 2, 3]:
            user = arranger_map.get(task_type)
            if user:
                result_list.append({
                    "task_type": task_type,
                    "name": user.real_name,
                    "maker_id": user.maker_id
                })
            else:
                result_list.append({"task_type": task_type, "name": "", "maker_id": ""})
        
        logger.info(f"成功获取到 {len(current_arrangers)} 个当前值班人员的信息。")
        return result_list