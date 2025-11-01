# app/services/arrange_service.py
"""
排班服务类：处理排班相关的业务逻辑
[v2.0 SQLAlchemy 迁移版]
"""
from typing import Optional, List, Dict, Any
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from datetime import datetime
import random
from collections import defaultdict

from app.models.arrange import Arrange
from app.models.user import User

class ArrangeService:
    """
    排班服务类，封装了所有与学年工作排班相关的业务逻辑。
    特别注意：本服务中的 `switch_to_next_arranger` 和 `batch_create_arrangements` 
    方法包含了关键的事务和锁控制，以确保数据在并发环境下的强一致性。
    """

    @staticmethod
    def _generate_arrange_id() -> str:
        """生成全局唯一的排班ID。"""
        now = datetime.utcnow()
        timestamp = now.strftime("%Y%m%d%H%M%S%f")[:-3]
        random_suffix = f"{random.randint(0, 999):03d}"
        return f"AR{timestamp}_{random_suffix}"

    def _arrange_to_dict(self, arrange: Arrange) -> Optional[Dict[str, Any]]:
        """辅助函数：将 Arrange ORM 对象转换为字典。"""
        if not arrange:
            return None
        return {
            "arrange_id": arrange.arrange_id,
            "name": arrange.name,
            "maker_id": arrange.maker_id,
            "task_type": arrange.task_type,
            "order": arrange.order,
            "current": arrange.current
        }

    async def switch_to_next_arranger(self, db: AsyncSession, task_type: int) -> bool:
        """
        [原子操作] 切换到指定任务类型的下一个值班人员。
        此操作是原子性的，并使用行级锁来防止并发冲突。
        """
        try:
            # 1. 使用 SELECT ... FOR UPDATE 锁定该任务类型的所有排班行
            #    这确保了在当前事务完成之前，没有其他并发事务可以修改这些行。
            stmt = select(Arrange).where(Arrange.task_type == task_type).order_by(Arrange.order).with_for_update()
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
            
            # 如果没有当前值班人员，则将第一个设为当前并返回
            if current_index == -1:
                logger.warning(f"未找到当前值班人员，将自动设置第一个为当前 | 任务类型: {task_type}")
                arrangements[0].current = True
                db.add(arrangements[0])
                # 注意：这里的 commit 由调用方（如TaskService）或 get_db 依赖项统一处理
                return True

            # 3. 更新当前和下一个值班人员的状态
            current_arranger = arrangements[current_index]
            next_index = (current_index + 1) % len(arrangements)
            next_arranger = arrangements[next_index]

            current_arranger.current = False
            next_arranger.current = True
            
            db.add_all([current_arranger, next_arranger])
            
            logger.info(f"排班切换成功 | 类型: {task_type} | 当前: {current_arranger.name} -> 下一个: {next_arranger.name}")
            return True

        except Exception as e:
            logger.error(f"排班切换时发生数据库错误: {e}", exc_info=True)
            # 向上抛出异常，以便事务可以回滚
            raise

    async def get_all_arrangements(self, db: AsyncSession) -> Dict[str, List[Dict[str, Any]]]:
        """获取所有排班安排，按任务类型分组。"""
        stmt = select(Arrange).order_by(Arrange.task_type, Arrange.order)
        result = await db.execute(stmt)
        arrangements = result.scalars().all()
        
        grouped = defaultdict(list)
        for arrange in arrangements:
            grouped[str(arrange.task_type)].append({
                "name": arrange.name,
                "maker_id": arrange.maker_id,
                "order": arrange.order,
                "current": arrange.current
            })
        
        return {
            "1": grouped.get("1", []),
            "2": grouped.get("2", []),
            "3": grouped.get("3", [])
        }
    
    async def batch_create_arrangements(self, db: AsyncSession, arrangements_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        [原子操作] 批量创建排班安排，会先清空所有旧的排班数据。
        整个过程是事务性的，要么全部成功，要么全部失败回滚。
        """
        try:
            # 1. 在事务中先删除所有现有排班记录
            delete_stmt = delete(Arrange)
            await db.execute(delete_stmt)
            logger.info("已清空所有旧的排班记录。")
            
            # 2. 准备新的排班记录
            new_arrangements = []
            for task_type_str, arrangement_list in arrangements_data.items():
                task_type = int(task_type_str)
                for arrange_data in arrangement_list:
                    new_arrangements.append(
                        Arrange(
                            arrange_id=self._generate_arrange_id(),
                            name=arrange_data["name"],
                            maker_id=arrange_data["maker_id"],
                            task_type=task_type,
                            order=arrange_data["order"],
                            current=arrange_data["current"]
                        )
                    )
            
            # 3. 批量插入新记录
            db.add_all(new_arrangements)
            logger.info(f"准备批量插入 {len(new_arrangements)} 条新排班记录。")
            
            result_summary = {
                "total_created": len(new_arrangements),
                "types": list(arrangements_data.keys())
            }
            return result_summary
        except Exception as e:
            logger.error(f"批量创建排班失败，事务将回滚: {e}", exc_info=True)
            raise

    async def get_current_arranger(self, db: AsyncSession, task_type: int) -> Optional[Dict[str, str]]:
        """获取指定任务类型的当前值班人员。"""
        stmt = select(Arrange).where(Arrange.task_type == task_type, Arrange.current == True)
        result = await db.execute(stmt)
        arrangement = result.scalar_one_or_none()

        if not arrangement:
            logger.warning(f"未找到任务类型 {task_type} 的当前值班人员")
            return None
            
        return {"name": arrangement.name, "maker_id": arrangement.maker_id}

    async def get_current_makers(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """获取所有任务类型的当前值班人员。"""
        stmt = select(Arrange).where(Arrange.current == True)
        result = await db.execute(stmt)
        current_arrangers = result.scalars().all()
        
        # 使用字典以便快速查找
        arranger_map = {arr.task_type: arr for arr in current_arrangers}
        
        result_list = []
        for task_type in [1, 2, 3]:
            arranger = arranger_map.get(task_type)
            if arranger:
                result_list.append({
                    "task_type": task_type,
                    "name": arranger.name,
                    "maker_id": arranger.maker_id
                })
            else:
                result_list.append({"task_type": task_type, "name": "", "maker_id": ""})
        
        return result_list