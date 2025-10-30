# app/services/stuff_borrow_service.py
"""
物资借用服务类：处理物资借用相关的业务逻辑。
[v2.0 SQLAlchemy 迁移版 - 最终审查完整版]
"""
from typing import List, Dict, Any, Optional
from sqlalchemy import select, func
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime
from loguru import logger
import time
import random
import re
import traceback

from app.models.stuff_borrow import StuffBorrow
from app.models.borrow_item import BorrowItem
from app.models.stuff import Stuff
from app.models.user import User

class StuffBorrowService:
    """物资借用服务类：处理物资借用相关的业务逻辑"""

    # --- 辅助方法 ---
    @staticmethod
    def _generate_sb_id() -> str:
        """
        生成唯一的借用申请ID: SB + 当前时间戳(精确到毫秒) + 3位随机数
        
        Returns:
            str: 生成的唯一ID字符串。
        """
        timestamp = int(time.time() * 1000)
        random_num = random.randint(100, 999)
        return f"SB{timestamp}{random_num}"
        
    @staticmethod
    def _stuff_borrow_to_dict(record: StuffBorrow, stuff_list_reconstructed: List[Dict] = None) -> Optional[dict]:
        """
        辅助函数：将StuffBorrow ORM对象安全地转换为字典，以便API返回。
        
        Args:
            record: SQLAlchemy的StuffBorrow模型实例。
            stuff_list_reconstructed (optional): 已预先构建好的物资列表，用于避免重复查询。
        
        Returns:
            一个包含申请详情的字典，如果输入为None则返回None。
        """
        if not record:
            return None
            
        detail_data = {
            "sb_id": record.sb_id,
            "user_id": record.user_id,
            "type": record.type,
            "name": record.name,
            "student_id": record.student_id,
            "phone_num": record.phone_num,
            "email": record.email,
            "grade": record.grade,
            "major": record.major,
            "review": record.review,
            "start_time": record.start_time.isoformat() if record.start_time else None,
            "deadline": record.deadline.isoformat() if record.deadline else None,
            "reason": record.reason,
            "state": record.state,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            "stuff_list": stuff_list_reconstructed if stuff_list_reconstructed is not None else []
        }

        if record.type == 1:
            detail_data.update({
                "project_number": record.project_number,
                "supervisor_name": record.supervisor_name,
                "supervisor_phone": record.supervisor_phone
            })
            
        return detail_data

    # --- 核心 CRUD 方法 ---

    @staticmethod
    async def create_stuff_borrow_application(db: AsyncSession, application_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建物资借用申请
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            application_data: 包含申请信息的字典。
        
        Returns:
            包含申请结果的字典。
        """
        logger.info("开始处理物资借用申请")
        try:
            logger.debug(f"收到申请数据: {application_data}")
            
            sb_id = StuffBorrowService._generate_sb_id()
            logger.info(f"生成申请ID: {sb_id}")
            
            deadline_str = application_data.get('deadline')
            if not deadline_str:
                raise ValueError("必须提供归还时间 (deadline)")
            deadline = datetime.strptime(deadline_str, '%Y-%m-%d %H:%M:%S')
            
            # 1. 创建主申请对象
            new_application = StuffBorrow(
                sb_id=sb_id,
                user_id=str(application_data['user_id']),
                type=int(application_data.get('type', 0)),
                name=str(application_data['name']),
                student_id=str(application_data['student_id']),
                phone_num=str(application_data['phone']),
                email=str(application_data['email']),
                grade=str(application_data['grade']),
                major=str(application_data['major']),
                start_time=datetime.utcnow(),
                deadline=deadline,
                reason=str(application_data.get('reason', '')),
                state=0 # 初始状态为未审核
            )

            # 2. 处理团队借物字段
            if new_application.type == 1:
                logger.info("处理团队借物额外字段")
                new_application.project_number = str(application_data.get('project_number'))
                new_application.supervisor_name = str(application_data.get('supervisor_name'))
                new_application.supervisor_phone = str(application_data.get('supervisor_phone'))

            # 3. 解析并创建关联的 BorrowItem 对象
            materials = application_data.get('materials', [])
            borrow_items_to_create = []
            for material_str in materials:
                match = re.match(r'^\s*(.+?)\s*-\s*(.+?)\s*-\s*(\d+)\s*$', material_str)
                if not match:
                    logger.warning(f"物资格式不匹配，已跳过: {material_str}")
                    continue
                
                category, name, quantity = match.group(1).strip(), match.group(2).strip(), int(match.group(3))
                
                stmt = select(Stuff.stuff_id).where(Stuff.type == category, Stuff.stuff_name == name).limit(1)
                result = await db.execute(stmt)
                stuff_id = result.scalar_one_or_none()
                
                if not stuff_id:
                    logger.error(f"无法在数据库中找到物资: {category} - {name}")
                    raise ValueError(f"物资 '{name}' 不存在")
                
                borrow_items_to_create.append(BorrowItem(stuff_id=stuff_id, quantity=quantity))
            
            if not borrow_items_to_create:
                raise ValueError("申请中必须包含至少一个有效的物资")

            new_application.borrow_items = borrow_items_to_create
            
            db.add(new_application)
            await db.commit()
            
            logger.info(f"物资借用申请保存成功: {sb_id}")
            return {
                "code": 200, "message": "申请提交成功",
                "data": {"sb_id": sb_id, "type": new_application.type}
            }
        except ValueError as e:
            await db.rollback()
            logger.error(f"创建物资借用申请失败 - 数据验证错误: {e}")
            raise e
        except Exception as e:
            await db.rollback()
            logger.error(f"创建物资借用申请失败 - 服务器错误: {e}", exc_info=True)
            raise Exception(f"提交申请失败: {str(e)}")

    @staticmethod
    async def get_user_stuff_borrow_list(db: AsyncSession, user_id: str) -> Dict[str, Any]:
        """
        获取特定用户的所有物资借用记录。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            user_id: 用户的openid。
        
        Returns:
            包含用户借用记录列表的字典。
        """
        try:
            logger.info(f"开始获取用户 {user_id} 的物资借用记录...")
            stmt = select(StuffBorrow).where(StuffBorrow.user_id == user_id).order_by(StuffBorrow.created_at.desc())
            result = await db.execute(stmt)
            borrow_records = result.scalars().all()
            logger.info(f"为用户 {user_id} 找到 {len(borrow_records)} 条记录。")
            
            records_list = [
                {
                    "sb_id": record.sb_id, "name": record.name, "grade": record.grade, "major": record.major,
                    "start_time": record.start_time.isoformat() + "Z" if record.start_time else None,
                    "deadline": record.deadline.isoformat() + "Z" if record.deadline else None,
                    "state": record.state
                }
                for record in borrow_records
            ]
            
            return {
                "code": 200, "message": "successfully get user stuff-borrow list",
                "data": {"total": len(records_list), "records": records_list}
            }
        except Exception as e:
            logger.error(f"获取用户借物记录失败: {e}", exc_info=True)
            raise Exception(f"获取用户借物记录失败: {str(e)}")

    @staticmethod
    async def get_stuff_borrow_detail(db: AsyncSession, sb_id: str) -> Dict[str, Any]:
        """
        获取物资借用申请详情。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            sb_id: 借用申请的业务ID。
        
        Returns:
            包含申请详情的字典。
        """
        try:
            logger.info(f"开始获取借用申请详情: {sb_id}")
            stmt = select(StuffBorrow).where(StuffBorrow.sb_id == sb_id)\
                .options(selectinload(StuffBorrow.borrow_items))
            result = await db.execute(stmt)
            borrow_record = result.scalar_one_or_none()
            if not borrow_record:
                raise ValueError("借物申请不存在")
            
            logger.debug("成功获取申请主记录，开始处理物资列表...")
            reconstructed_stuff_list = []
            if borrow_record.borrow_items:
                stuff_ids = [item.stuff_id for item in borrow_record.borrow_items]
                stuff_map_stmt = select(Stuff).where(Stuff.stuff_id.in_(stuff_ids))
                stuff_res = await db.execute(stuff_map_stmt)
                stuff_map = {s.stuff_id: s for s in stuff_res.scalars().all()}
                
                for i, item in enumerate(borrow_record.borrow_items):
                    stuff_details = stuff_map.get(item.stuff_id)
                    category = stuff_details.type if stuff_details else "未知分类"
                    name = stuff_details.stuff_name if stuff_details else f"未知物资({item.stuff_id})"
                    reconstructed_stuff_list.append({"category": i, "stuff": f"{category} - {name} - {item.quantity}"})
            
            detail_data = StuffBorrowService._stuff_borrow_to_dict(borrow_record, reconstructed_stuff_list)
            
            logger.info(f"获取申请详情 {sb_id} 成功。")
            return {
                "code": 200, "message": "successfully get stuff-borrow detail",
                "data": detail_data
            }
        except ValueError as e:
            raise e
        except Exception as e:
            logger.error(f"获取借物详情失败: {e}", exc_info=True)
            raise Exception(f"获取借物详情失败: {str(e)}")

    @staticmethod
    async def get_all_stuff_borrow_list(db: AsyncSession) -> Dict[str, Any]:
        """
        获取所有物资借用申请记录（供管理员使用）。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            
        Returns:
            Dict[str, Any]: 包含所有借用记录列表的字典。
        """
        try:
            logger.info("开始获取所有物资借用申请记录...")
            stmt = select(StuffBorrow).order_by(StuffBorrow.created_at.desc())
            result = await db.execute(stmt)
            all_records = result.scalars().all()
            logger.info(f"成功获取 {len(all_records)} 条借用记录。")

            records_list = [
                {
                    "sb_id": record.sb_id,
                    "type": record.type,
                    "name": record.name,
                    "major": record.major,
                    "grade": record.grade,
                    "start_time": record.start_time.isoformat() + "Z" if record.start_time else None,
                    "state": record.state
                }
                for record in all_records
            ]
            
            return {
                "code": 200,
                "message": "successfully get all stuff-borrow list",
                "data": {
                    "total": len(records_list),
                    "records": records_list
                }
            }
        except Exception as e:
            logger.error(f"获取所有借物记录失败: {e}", exc_info=True)
            raise Exception(f"获取所有借物记录失败: {str(e)}")
        
    # --- 审核与库存变更核心事务方法 ---
    @staticmethod
    async def handle_review_process(db: AsyncSession, sb_id: str, action: str, reason: str, reviewer_id: str) -> Dict[str, Any]:
        """
        【最终核心事务 - 修复所有错误版】处理管理员的审核决定。
        这是一个原子性操作，确保审核、库存检查、库存扣减、状态变更要么全部成功，要么全部回滚。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            sb_id: 借用申请ID。
            action: 操作类型 ('approve' 或 'reject')。
            reason: 审核意见。
            reviewer_id: 审核员ID。
        
        Returns:
            操作结果的字典。
        """
        logger.info(f"管理员 {reviewer_id} 开始处理申请 {sb_id}，操作: {action}")
        
        # --- 在函数作用域顶部初始化返回值变量 ---
        return_code = 500
        return_message = "内部服务器错误"
        return_data = {}

        if action == "approve":
            logger.debug(f"[{sb_id}] 进入 'approve' 分支。")
            try:
                logger.debug(f"[{sb_id}] 准备进入 'approve' 事务块。")
                async with db.begin_nested() as transaction:
                    logger.success(f"[{sb_id}] 成功进入 'approve' 事务块。")
                    
                    # 1. 获取并锁定申请记录
                    stmt = select(StuffBorrow).where(StuffBorrow.sb_id == sb_id)\
                        .options(selectinload(StuffBorrow.borrow_items)).with_for_update()
                    logger.debug(f"[{sb_id}] [SQL-PREP] 准备执行申请记录的锁定查询。")
                    result = await db.execute(stmt)
                    application = result.scalar_one_or_none()

                    if not application: raise ValueError(f"借物申请不存在: {sb_id}")
                    if application.state != 0: raise ValueError(f"只有'未审核'的申请才能被批准。当前状态: {application.state}")
                    logger.info(f"[{sb_id}] 成功锁定申请记录，当前状态: {application.state}。")

                    borrow_items = application.borrow_items
                    if not borrow_items: raise ValueError("申请中没有有效的物资项")
                    
                    # 2. 锁定相关物资行
                    stuff_ids_to_lock = [item.stuff_id for item in borrow_items]
                    lock_stmt = select(Stuff).where(Stuff.stuff_id.in_(stuff_ids_to_lock)).with_for_update()
                    logger.debug(f"[{sb_id}] [SQL-PREP] 准备执行物资库存的锁定查询，IDs: {stuff_ids_to_lock}。")
                    locked_stuff_result = await db.execute(lock_stmt)
                    locked_stuff_map = {s.stuff_id: s for s in locked_stuff_result.scalars().all()}
                    logger.info(f"[{sb_id}] 成功锁定 {len(locked_stuff_map)} 个物资记录。")

                    # 3. 在安全上下文中检查库存
                    insufficient_items = []
                    for item in borrow_items:
                        stuff = locked_stuff_map.get(item.stuff_id)
                        if not stuff or stuff.number_remain < item.quantity:
                            msg = f"物资 '{stuff.stuff_name if stuff else item.stuff_id}' 余量不足"
                            insufficient_items.append(msg)
                    
                    # 4. 【关键修复】正确的 if/else 缩进结构
                    if insufficient_items:
                        # 分支A：库存不足
                        logger.warning(f"[{sb_id}] 库存不足，准备执行打回逻辑: {insufficient_items}")
                        
                        # 因为我们要返回错误，所以当前事务的目标是失败。我们手动回滚它。
                        await transaction.rollback()
                        logger.critical(f"[{sb_id}] [TRANSACTION] 库存不足分支：手动执行 rollback 完成。")
                        
                        # 在一个新的事务/会话状态中更新申请状态为“已打回”
                        application.state = 1
                        application.review = f"【系统自动打回】库存不足: {', '.join(insufficient_items)}"
                        db.add(application)
                        logger.debug(f"[{sb_id}] 准备提交'自动打回'的状态变更。")
                        await db.commit()
                        logger.success(f"[{sb_id}] [TRANSACTION] '自动打回'的状态变更已提交。")
                        
                        # 准备错误返回值
                        return_code = 400
                        return_message = "部分物资余量不足，申请已自动打回"
                        return_data = {"errors": insufficient_items}
                    else:
                        # 分支B：库存充足
                        updated_stuff_log = []
                        for item in borrow_items:
                            stuff = locked_stuff_map[item.stuff_id]
                            old_remain = stuff.number_remain # 记录旧库存用于日志
                            stuff.number_remain -= item.quantity
                            db.add(stuff)
                            updated_stuff_log.append({"stuff_name": stuff.stuff_name, "borrowed": item.quantity, "old_remain": old_remain, "new_remain": stuff.number_remain})
                            logger.info(f"[{sb_id}] 物资 '{stuff.stuff_name}' 库存在会话中更新: {old_remain} -> {stuff.number_remain}")

                        application.state = 2
                        application.review = reason or "审核通过"
                        db.add(application)
                        
                        logger.info(f"[{sb_id}] 所有变更已暂存，事务即将提交。")
                        
                        # 准备成功返回值
                        return_code = 200
                        return_message = "审核通过，库存已成功扣减"
                        return_data = {"updated_stuff": updated_stuff_log}

                # `async with` 块在这里退出。如果执行的是分支B，事务会自动提交。
                logger.success(f"[{sb_id}] [TRANSACTION] 'approve' 事务块已成功退出。")
            
            except Exception as e:
                logger.error(f"[{sb_id}] 'approve' 分支的 try 块中捕获到异常: {e}", exc_info=True)
                # 向上抛出异常，让路由层统一处理并返回500错误
                raise e

        elif action == "reject":
            logger.debug(f"[{sb_id}] 进入 'reject' 分支。")
            try:
                # 打回操作是一个独立的简单事务
                async with db.begin_nested() as transaction:
                    logger.success(f"[{sb_id}] 成功进入 'reject' 事务块。")
                    stmt = select(StuffBorrow).where(StuffBorrow.sb_id == sb_id)
                    result = await db.execute(stmt)
                    application = result.scalar_one_or_none()
                    if not application: raise ValueError(f"借物申请不存在: {sb_id}")
                    if application.state != 0: raise ValueError(f"只有'未审核'的申请才能被打回。当前状态: {application.state}")
                    
                    application.state = 1
                    application.review = reason
                    db.add(application)
                    logger.info(f"[{sb_id}] 申请已设置为'打回'，准备退出 'async with' 块并自动提交。")
                
                logger.success(f"[{sb_id}] [TRANSACTION] 'reject' 的 'async with' 块已无异常地执行完毕，事务应该已自动提交。")
                
                # 准备成功返回值
                return_code = 200
                return_message = "申请已成功打回"
                return_data = {"borrow_id": sb_id, "new_state": 1}

            except Exception as e:
                logger.error(f"[{sb_id}] 'reject' 分支的 try 块中捕获到异常: {e}", exc_info=True)
                raise e
        else:
            raise ValueError(f"无效的操作类型: {action}")

        # --- 所有逻辑分支最终汇合到这里返回 ---
        logger.info(f"[{sb_id}] 函数执行完毕，准备返回最终结果。Code: {return_code}, Message: {return_message}")
        return {"code": return_code, "message": return_message, "data": return_data}
        
    @staticmethod
    async def confirm_stuff_return(db: AsyncSession, return_data: dict) -> Dict[str, Any]:
        """
        确认物资归还（仅更新状态）。
        库存恢复由另一个独立的API调用触发。
        """
        borrow_id = return_data["borrow_id"]
        operator_id = return_data["operator_id"]
        logger.info(f"管理员 {operator_id} 开始确认归还申请 {borrow_id}")
        try:
            stmt = select(StuffBorrow).where(StuffBorrow.sb_id == borrow_id)
            result = await db.execute(stmt)
            application = result.scalar_one_or_none()
            if not application: raise ValueError(f"借物申请不存在: {borrow_id}")
            if application.state != 2: raise ValueError(f"当前状态不是“通过未归还”，无法执行归还操作。")

            application.state = 3  # 3 = 已归还
            db.add(application)
            await db.commit()
            
            logger.info(f"申请 {borrow_id} 归还状态确认成功。")
            return {"code": 200, "message": "物资归还确认成功", "data": {"borrow_id": borrow_id, "new_state": 3}}
        except (ValueError, NoResultFound) as e:
            await db.rollback()
            logger.warning(f"确认归还失败: {e}")
            raise ValueError(str(e))
        except Exception as e:
            await db.rollback()
            logger.error(f"确认归还失败: {e}", exc_info=True)
            raise e
    
    @staticmethod
    async def restore_stuff_quantity_from_return(db: AsyncSession, sb_id: str, operator_id: str) -> Dict[str, Any]:
        """
        【事务】归还时恢复物资数量。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            sb_id: 借用申请ID。
            operator_id: 操作员ID。
        
        Returns:
            Dict: 恢复结果。
        """
        logger.info(f"事务开始：准备为申请 {sb_id} 恢复库存...")
        async with db.begin_nested() as transaction:
            try:
                stmt = select(StuffBorrow).where(StuffBorrow.sb_id == sb_id)\
                    .options(selectinload(StuffBorrow.borrow_items))
                result = await db.execute(stmt)
                application = result.scalar_one_or_none()
                if not application: raise ValueError(f"借物申请不存在: {sb_id}")

                borrow_items = application.borrow_items
                if not borrow_items: 
                    logger.info(f"申请 {sb_id} 中无物资项，无需恢复库存。")
                    return {"code": 200, "message": "申请中无物资项，无需恢复库存"}
                
                stuff_ids_to_lock = [item.stuff_id for item in borrow_items]
                lock_stmt = select(Stuff).where(Stuff.stuff_id.in_(stuff_ids_to_lock)).with_for_update()
                locked_stuff_result = await db.execute(lock_stmt)
                locked_stuff_map = {s.stuff_id: s for s in locked_stuff_result.scalars().all()}

                restored_stuff_log = []
                for item in borrow_items:
                    stuff = locked_stuff_map.get(item.stuff_id)
                    if stuff:
                        old_remain = stuff.number_remain
                        stuff.number_remain += item.quantity
                        db.add(stuff)
                        log_entry = {"stuff_name": stuff.stuff_name, "old_remain": old_remain, "new_remain": stuff.number_remain}
                        restored_stuff_log.append(log_entry)
                        logger.info(f"物资 '{stuff.stuff_name}' 库存已在内存中恢复: {old_remain} -> {stuff.number_remain}")
                
                logger.info(f"库存恢复事务即将提交。")
                return {"code": 200, "message": "物资数量恢复完成", "data": {"restored_stuff": restored_stuff_log}}
            except Exception as e:
                logger.error(f"库存恢复事务失败: {e}", exc_info=True)
                raise e

    @staticmethod
    async def cancel_stuff_borrow_application(db: AsyncSession, sb_id: str, user_id: str) -> Dict[str, Any]:
        """
        用户取消自己的借物申请。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            sb_id: 借用申请ID。
            user_id: 当前操作的用户ID。
        
        Returns:
            Dict: 取消结果。
        """
        logger.info(f"用户 {user_id} 开始取消借物申请: {sb_id}")
        try:
            stmt = select(StuffBorrow).where(StuffBorrow.sb_id == sb_id)
            result = await db.execute(stmt)
            application = result.scalar_one_or_none()
            if not application: raise ValueError("借物申请不存在")
            if application.user_id != user_id: raise ValueError("无权限取消此申请")
            if application.state not in [0, 1]: raise ValueError("只有未审核和已打回的申请才能取消")

            await db.delete(application) # cascade="all, delete-orphan" 会自动删除关联的 borrow_items
            await db.commit()
            
            logger.info(f"申请 {sb_id} 已成功删除。")
            return {"code": 200, "message": "借物申请已成功取消"}
        except (ValueError, Exception) as e:
            await db.rollback()
            logger.error(f"取消申请失败: {e}", exc_info=True)
            raise e

    @staticmethod
    async def update_stuff_borrow_application(db: AsyncSession, sb_id: str, update_data: dict, user_id: str) -> Dict[str, Any]:
        """
        【事务】用户更新自己的借物申请。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            sb_id: 借用申请ID。
            update_data: 更新数据字典。
            user_id: 当前操作的用户ID。
        
        Returns:
            更新结果的字典。
        """
        logger.info(f"用户 {user_id} 开始更新借物申请 {sb_id}")
        
        # 将整个更新操作包裹在一个事务中
        async with db.begin_nested() as transaction:
            try:
                # 1. 获取并锁定申请记录
                stmt = select(StuffBorrow).where(StuffBorrow.sb_id == sb_id)\
                    .options(selectinload(StuffBorrow.borrow_items)).with_for_update()
                result = await db.execute(stmt)
                application = result.scalar_one_or_none()

                if not application: raise ValueError(f"借物申请不存在: {sb_id}")
                if application.state not in [0, 1]: raise ValueError("只有未审核和已打回的申请才能修改")
                if application.user_id != user_id: raise ValueError("无权限修改此申请")

                # 2. 更新非物资字段
                for field, value in update_data.items():
                    if field == 'materials': continue
                    
                    # --- 【关键修复 1】处理时间字符串 ---
                    if field in ['start_time', 'deadline'] and isinstance(value, str):
                        parsed_time = None
                        # 尝试多种常见格式
                        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                            try:
                                parsed_time = datetime.strptime(value, fmt)
                                # 如果只匹配到日期，时间部分默认为 00:00:00
                                break # 成功解析后退出循环
                            except ValueError:
                                continue # 尝试下一个格式
                        
                        if parsed_time is None:
                            # 如果所有格式都尝试失败
                            raise ValueError(f"时间格式无法识别: {field}='{value}'. 请使用 'YYYY-MM-DD HH:MM:SS' 或 'YYYY-MM-DD'")
                        
                        value = parsed_time # 使用解析后的 datetime 对象
                    
                    if hasattr(application, field):
                        db_field = 'phone_num' if field == 'phone' else field
                        setattr(application, db_field, value)
                        logger.debug(f"在会话中更新字段 {db_field}: {value}")
                
                # 3. 如果物资列表有变更... (这部分逻辑不变)
                if 'materials' in update_data:
                    logger.info(f"检测到物资列表变更，开始事务性更新...")
                    
                    # 使用 SQLAlchemy 的 relationship 特性，直接清空旧列表
                    application.borrow_items.clear()
                    await db.flush() # 同步清除操作到会话

                    new_materials = update_data['materials']
                    new_borrow_items = []
                    
                    for material_str in new_materials:
                        match = re.match(r'^\s*(.+?)\s*-\s*(.+?)\s*-\s*(\d+)\s*$', material_str)
                        if not match: continue
                        category, name, quantity = match.group(1).strip(), match.group(2).strip(), int(match.group(3))
                        
                        stuff_stmt = select(Stuff.stuff_id).where(Stuff.type == category, Stuff.stuff_name == name)
                        stuff_res = await db.execute(stuff_stmt)
                        stuff_id = stuff_res.scalar_one_or_none()

                        if not stuff_id: raise ValueError(f"新物资 '{name}' 不存在")
                        new_borrow_items.append(BorrowItem(stuff_id=stuff_id, quantity=quantity))
                    
                    application.borrow_items = new_borrow_items
                    logger.info("新的物资列表已在会话中关联。")

                # 4. 状态重置为“未审核”
                application.state = 0
                db.add(application)
                
                logger.info("所有变更已暂存，事务即将提交。")
                
            except (ValueError, Exception) as e:
                # 事务将自动回滚
                logger.error(f"更新借物申请事务失败，将回滚: {e}", exc_info=True)
                raise e

        # --- 【关键修复 2】在事务成功提交后，重新查询详情 ---
        # 此时数据库中的数据已经是最新且类型正确的
        logger.info("更新事务成功，正在获取最新的申请详情...")
        updated_detail_response = await StuffBorrowService.get_stuff_borrow_detail(db, sb_id)
        
        return {
            "code": 200,
            "message": "借物申请更新成功",
            "data": updated_detail_response['data']
        }
