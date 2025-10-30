# app/services/site_borrow_service.py
"""
场地借用服务类：处理场地借用相关的业务逻辑。
[v2.0 SQLAlchemy 迁移版 - 采用“审批时占用”新业务流程]
"""
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger
from fastapi import HTTPException
from datetime import datetime
import random

from app.models.site_borrow import SiteBorrow
from app.models.site import Site

class SiteBorrowService:
    """场地借用服务类：处理场地借用相关的业务逻辑"""

    @staticmethod
    def _generate_apply_id() -> str:
        """
        生成唯一的场地借用申请ID。
        格式: SB_SITE_ + 当前时间戳(精确到毫秒) + 3位随机数，以区别于物资借用ID。
        
        Returns:
            str: 生成的唯一ID字符串。
        """
        now = datetime.utcnow()
        timestamp = now.strftime("%Y%m%d%H%M%S%f")[:-3]
        random_suffix = f"{random.randint(0,999):03d}"
        return f"SB_SITE_{timestamp}_{random_suffix}"

    @staticmethod
    def _borrow_to_dict(application: SiteBorrow) -> dict:
        """
        辅助函数：将SiteBorrow ORM对象安全地转换为用于API响应的字典。
        确保所有字段都被正确序列化，特别是时间字段。

        Args:
            application: SQLAlchemy的SiteBorrow模型实例。

        Returns:
            dict: 一个包含场地借用申请完整信息的字典，如果输入为None则返回None。
        """
        if not application:
            return None
        return {
            "apply_id": application.apply_id,
            "userid": application.userid,
            "name": application.name,
            "student_id": application.student_id,
            "phone_num": application.phone_num,
            "email": application.email,
            "purpose": application.purpose,
            "project_id": application.project_id,
            "mentor_name": application.mentor_name,
            "mentor_phone_num": application.mentor_phone_num,
            "site_id": application.site_id,
            "site": application.site,
            "number": application.number,
            "start_time": application.start_time.isoformat() if application.start_time else None,
            "end_time": application.end_time.isoformat() if application.end_time else None,
            "state": application.state,
            "review": application.review,
            "created_at": application.created_at.isoformat() + "Z" if application.created_at else None,
            "updated_at": application.updated_at.isoformat() + "Z" if application.updated_at else None,
        }
    
    async def create_borrow_application(self, db: AsyncSession, application_data: dict, userid: str) -> str:
        """
        【新流程】创建场地借用申请。
        此方法仅创建申请记录，状态为“未审核”，不涉及场地占用操作。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            application_data: 包含申请信息的字典。
            userid: 申请人的用户ID。
        
        Returns:
            str: 成功创建的申请ID。
        
        Raises:
            ValueError: 当业务逻辑验证失败时（如日期错误、场地不存在）。
            Exception: 当发生其他数据库或未知错误时。
        """
        logger.info(f"用户 {userid} 开始创建场地借用申请...")
        logger.debug(f"收到的申请数据: {application_data}")
        try:
            # 1. 预处理和验证时间字段
            start_time_str = application_data.get("start_time")
            end_time_str = application_data.get("end_time")
            if not start_time_str or not end_time_str:
                raise ValueError("必须提供开始和结束时间")
            
            start_time = datetime.fromisoformat(start_time_str)
            end_time = datetime.fromisoformat(end_time_str)

            if start_time >= end_time:
                logger.warning(f"时间逻辑错误: 结束时间 {end_time} 必须晚于开始时间 {start_time}")
                raise ValueError("结束时间必须晚于开始时间")

            # 2. 检查申请的场地工位是否存在
            site_id = application_data.get("site_id")
            number = application_data.get("number")
            logger.debug(f"检查场地是否存在: site_id={site_id}, number={number}")
            site_check_stmt = select(Site.id).where(Site.site_id == site_id, Site.number == number)
            site_exists = (await db.execute(site_check_stmt)).scalar_one_or_none()
            if not site_exists:
                logger.warning(f"场地或工位不存在: site_id={site_id}, number={number}")
                raise ValueError("申请的场地或工位不存在")
            
            # 3. 创建申请记录
            apply_id = self._generate_apply_id()
            logger.info(f"生成新的申请ID: {apply_id}")
            new_borrow = SiteBorrow(
                apply_id=apply_id,
                userid=userid,
                name=application_data["name"],
                student_id=application_data["student_id"],
                phone_num=application_data["phone_num"],
                email=application_data["email"],
                purpose=application_data["purpose"],
                project_id=application_data.get("project_id", ""),
                mentor_name=application_data["mentor_name"],
                mentor_phone_num=application_data["mentor_phone_num"],
                site_id=site_id,
                site=application_data["site"],
                number=number,
                start_time=start_time,
                end_time=end_time,
                state=0 # 初始状态为未审核
            )
            
            # 4. 提交到数据库
            db.add(new_borrow)
            await db.commit()
            
            logger.success(f"场地借用申请创建成功 | 申请ID: {apply_id}")
            return apply_id

        except ValueError as e:
            await db.rollback()
            logger.warning(f"创建场地申请失败 - 业务错误: {e}")
            raise e
        except Exception as e:
            await db.rollback()
            logger.error(f"创建场地借用申请时发生未知错误: {e}", exc_info=True)
            raise Exception("创建场地借用申请失败")
    
    async def get_application_detail(self, db: AsyncSession, apply_id: str) -> dict:
        """
        获取场地借用申请详情。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            apply_id: 申请ID。
            
        Returns:
            dict: 包含申请详情的字典。
        
        Raises:
            ValueError: 当申请不存在时。
            Exception: 当发生其他数据库或未知错误时。
        """
        try:
            logger.info(f"开始查询场地借用详情 | 申请ID: {apply_id}")
            stmt = select(SiteBorrow).where(SiteBorrow.apply_id == apply_id)
            result = await db.execute(stmt)
            application = result.scalar_one_or_none()
            if not application:
                raise ValueError("申请不存在")
            
            logger.success(f"成功获取申请详情: {apply_id}")
            return self._borrow_to_dict(application)
        except ValueError as e:
            logger.warning(f"获取申请详情失败，申请不存在: {apply_id}")
            raise e
        except Exception as e:
            logger.error(f"获取申请详情时发生未知错误: {e}", exc_info=True)
            raise Exception("获取申请详情失败")
    
    async def get_all_applications(self, db: AsyncSession) -> dict:
        """
        获取所有场地借用申请（简化列表，供管理员概览）。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            
        Returns:
            dict: 包含申请总数和简化版申请信息列表的字典。
        
        Raises:
            Exception: 当发生数据库或未知错误时。
        """
        try:
            logger.info("开始查询所有场地借用申请...")
            
            # 查询所有申请记录，并按创建时间降序排列
            stmt = select(SiteBorrow.apply_id, SiteBorrow.state, SiteBorrow.created_at, SiteBorrow.site, SiteBorrow.number)\
                .order_by(SiteBorrow.created_at.desc())
            
            result = await db.execute(stmt)
            applications = result.all() # .all() 获取元组列表
            
            # 构建响应数据
            application_list = [
                {
                    "apply_id": app.apply_id,  
                    "state": app.state,
                    "created_time": app.created_at.isoformat() + "Z",
                    "site": app.site,
                    "number": app.number
                }
                for app in applications
            ]
            
            logger.success(f"成功获取 {len(application_list)} 条场地借用申请")
            
            return {
                "total": len(application_list),
                "list": application_list
            }
        except Exception as e:
            logger.error(f"获取全部场地申请失败: {e}", exc_info=True)
            raise Exception("获取全部场地申请失败")

    async def get_user_applications(self, db: AsyncSession, userid: str) -> dict:
        """
        获取指定用户的所有场地借用申请。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            userid: 用户的ID。
            
        Returns:
            dict: 包含申请总数和简化版申请信息列表的字典。
        """
        try:
            logger.info(f"开始查询用户 {userid} 的场地借用申请...")
            
            # 查询该用户的所有申请记录，按创建时间降序排列
            stmt = select(SiteBorrow.apply_id, SiteBorrow.state, SiteBorrow.created_at, SiteBorrow.site, SiteBorrow.number)\
                .where(SiteBorrow.userid == userid)\
                .order_by(SiteBorrow.created_at.desc())

            result = await db.execute(stmt)
            applications = result.all()
            
            # 构建响应数据
            application_list = [
                {
                    "apply_id": app.apply_id,
                    "state": app.state,
                    "created_time": app.created_at.isoformat() + "Z",
                    "site": app.site,
                    "number": app.number
                }
                for app in applications
            ]
            
            logger.success(f"为用户 {userid} 找到 {len(application_list)} 条场地借用申请")
            
            return {
                "total": len(application_list),
                "list": application_list
            }
        except Exception as e:
            logger.error(f"获取用户场地申请列表失败: {e}", exc_info=True)
            raise Exception("获取用户场地申请列表失败")

    async def cancel_application(self, db: AsyncSession, apply_id: str, userid: str) -> str:
        """
        【事务】用户取消自己的场地借用申请。
        此操作是事务性的，因为它可能需要释放场地。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            apply_id: 申请ID。
            userid: 当前用户ID（用于验证权限）。
        
        Returns:
            str: 被取消的申请ID。
        
        Raises:
            ValueError: 当业务逻辑验证失败时。
            Exception: 当发生其他数据库或未知错误时。
        """
        async with db.begin_nested() as transaction:
            try:
                logger.info(f"用户 {userid} 尝试取消场地申请: {apply_id}")
                
                # 1. 获取并锁定申请记录
                stmt = select(SiteBorrow).where(SiteBorrow.apply_id == apply_id).with_for_update()
                result = await db.execute(stmt)
                application = result.scalar_one_or_none()

                if not application:
                    logger.warning(f"取消失败：申请不存在 | 申请ID: {apply_id}")
                    raise ValueError("申请不存在")
                
                # 2. 检查权限和状态
                if application.userid != userid:
                    logger.warning(f"权限不足：用户 {userid} 尝试取消属于 {application.userid} 的申请")
                    raise ValueError("无权限取消该申请")
                
                # 状态 (0:未审核, 1:打回, 2:通过未归还, 3:已归还, 4:取消)
                original_state = application.state
                if original_state not in [0, 1, 2]:
                    logger.warning(f"申请状态不允许取消 | 当前状态: {original_state}")
                    raise ValueError("只有未审核、已打回或已通过的申请才能取消")
                
                # 3. 更新申请状态为4（已取消）
                application.state = 4
                db.add(application)
                logger.info(f"申请 {apply_id} 状态已在会话中更新为 '已取消'")
                
                # 4. 如果申请是“已通过”状态，需要释放场地
                if original_state == 2:
                    logger.info(f"申请原状态为'已通过'，准备释放场地: {application.site} - {application.number}")
                    update_stmt = update(Site).where(
                        Site.site_id == application.site_id, 
                        Site.number == application.number
                    ).values(is_occupied=False)
                    
                    # 执行更新，并检查是否真的有行被更新
                    update_result = await db.execute(update_stmt)
                    if update_result.rowcount == 0:
                        # 这是一个警告，说明场地可能已被删除，但不应中断取消流程
                        logger.warning(f"尝试释放场地时，未找到匹配的场地记录: {application.site_id} - {application.number}")
                    else:
                        logger.success(f"场地已成功释放: {application.site} - {application.number}")

                # 5. 事务将在 async with 块结束时自动提交
                logger.info(f"取消申请 {apply_id} 操作完成，事务即将提交。")
                return apply_id
            
            except ValueError as e:
                await transaction.rollback()
                logger.warning(f"取消场地申请失败 - 业务错误: {e}")
                raise e
            except Exception as e:
                await transaction.rollback()
                logger.error(f"取消场地申请失败: {e}", exc_info=True)
                raise Exception("取消场地申请失败")
            
    async def review_application(self, db: AsyncSession, apply_id: str, state: int, review: str = "") -> tuple:
        """
        【核心事务】审核场地借用申请。
        - 如果批准，将原子性地检查并占用场地，然后更新申请状态。
        - 如果打回，仅更新申请状态。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            apply_id: 申请ID。
            state: 新状态 (1:打回, 2:通过)。
            review: 审核反馈。
        
        Returns:
            tuple: (apply_id, state, review)。
        """
        async with db.begin_nested() as transaction:
            try:
                logger.info(f"开始审核场地申请 | 申请ID: {apply_id} | 目标状态: {state}")
                
                # 1. 获取并锁定申请记录
                stmt = select(SiteBorrow).where(SiteBorrow.apply_id == apply_id).with_for_update()
                result = await db.execute(stmt)
                application = result.scalar_one_or_none()

                if not application: raise ValueError("申请不存在")
                if application.state not in (0, 1): raise ValueError(f"只有'未审核'和'已打回'的申请才能被审核，当前状态: {application.state}")
                if state not in [1, 2]: raise ValueError(f"无效的新状态值: {state} (只允许 1 或 2)")
                if state == 1 and not review: raise ValueError("打回申请时必须提供审核反馈")

                # --- 核心逻辑分支 ---
                if state == 2: # 批准申请
                    logger.info(f"批准申请 {apply_id}，准备锁定并占用场地: {application.site} - {application.number}")
                    
                    # 2. 锁定目标场地工位
                    site_stmt = select(Site).where(
                        Site.site_id == application.site_id, 
                        Site.number == application.number
                    ).with_for_update()
                    site_result = await db.execute(site_stmt)
                    site = site_result.scalar_one_or_none()

                    if not site:
                        raise ValueError("申请关联的场地工位已不存在，无法批准")
                    
                    # 3. 在锁定的安全环境中检查场地是否已被占用
                    if site.is_occupied:
                        logger.warning(f"批准失败：场地 {site.site}-{site.number} 已被占用")
                        # 自动将申请打回
                        application.state = 1
                        application.review = f"【系统自动打回】场地已被占用"
                        db.add(application)
                        raise ValueError("场地已被占用，申请已自动打回")

                    # 4. 占用场地
                    site.is_occupied = True
                    db.add(site)
                    logger.success(f"场地 {site.site}-{site.number} 已成功在会话中标记为占用")
                
                # 更新申请状态和审核意见 (批准或打回都会执行)
                application.state = state
                application.review = review
                db.add(application)
                
                logger.info(f"申请 {apply_id} 状态已更新为 {state}，事务即将提交。")
                return (apply_id, state, review)

            except ValueError as e:
                await transaction.rollback()
                logger.warning(f"审核场地申请失败 - 业务错误: {e}")
                raise e
            except Exception as e:
                await transaction.rollback()
                logger.error(f"审核场地申请失败: {e}", exc_info=True)
                raise Exception("审核场地申请失败")

    async def return_borrow_application(self, db: AsyncSession, apply_id: str, userid: str) -> tuple:
        """
        【事务】归还已借用的场地，并释放场地。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            apply_id: 申请ID。
            userid: 当前用户ID（用于记录操作员）。
        
        Returns:
            tuple: (apply_id, new_state)。
        """
        async with db.begin_nested() as transaction:
            try:
                logger.info(f"处理场地归还 | 申请ID: {apply_id} | 操作员: {userid}")
                
                stmt = select(SiteBorrow).where(SiteBorrow.apply_id == apply_id).with_for_update()
                result = await db.execute(stmt)
                application = result.scalar_one_or_none()

                if not application: raise ValueError("申请不存在")
                if application.state != 2: raise ValueError("只有'通过未归还'的申请才能被归还")
                
                application.state = 3 # 已归还
                db.add(application)
                
                # 释放场地
                update_stmt = update(Site).where(
                    Site.site_id == application.site_id, 
                    Site.number == application.number
                ).values(is_occupied=False)
                update_result = await db.execute(update_stmt)

                if update_result.rowcount == 0:
                    logger.error(f"严重警告：尝试释放一个不存在的场地工位！场地ID: {application.site_id}, 工位号: {application.number}")
                else:
                    logger.success(f"场地已释放 | 场地ID: {application.site_id} | 工位号: {application.number}")
                
                logger.info(f"场地已成功归还 | 申请ID: {apply_id}")
                return (apply_id, 3)
            
            except ValueError as e:
                await transaction.rollback()
                raise e
            except Exception as e:
                await transaction.rollback()
                logger.error(f"归还场地失败: {e}", exc_info=True)
                raise Exception("归还场地失败")

    async def update_application(self, db: AsyncSession, apply_id: str, userid: str, update_data: dict) -> tuple:
        """
        【修正】更新场地借用申请信息（允许更换场地）。
        在新业务流程下，此操作不涉及场地占用，是安全的。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            apply_id: 申请ID。
            userid: 当前用户ID。
            update_data: 包含更新字段的字典。
        
        Returns:
            tuple: (apply_id, 实际更新的字段字典)。
        """
        try:
            logger.info(f"用户 {userid} 开始更新场地申请 | 申请ID: {apply_id}")
            
            stmt = select(SiteBorrow).where(SiteBorrow.apply_id == apply_id)
            result = await db.execute(stmt)
            application = result.scalar_one_or_none()

            if not application: raise ValueError("申请不存在")
            if application.userid != userid: raise ValueError("无权限更新该申请")
            if application.state not in [0, 1]: raise ValueError("只有'未审核'或'已打回'的申请才能更新")
            
            allowed_fields = [
                "email", "end_time", "mentor_name", "mentor_phone_num", "name", 
                "phone_num", "project_id", "purpose", "start_time", "student_id",
                "site_id", "site", "number" # 允许更新场地相关字段
            ]
            changed_fields = {}
            
            for field, value in update_data.items():
                if field in allowed_fields:
                    if field in ["start_time", "end_time"] and isinstance(value, str):
                        value = datetime.fromisoformat(value)
                    
                    if getattr(application, field) != value:
                        setattr(application, field, value)
                        changed_fields[field] = value
            
            if changed_fields:
                if application.state == 1:
                    application.state = 0
                    application.review = ""
                db.add(application)
                await db.commit()
                logger.info(f"申请已更新 | 申请ID: {apply_id} | 更新字段: {list(changed_fields.keys())}")
            else:
                logger.info(f"申请 {apply_id} 无任何变更。")

            return (apply_id, changed_fields)
        
        except ValueError as e:
            await db.rollback()
            raise e
        except Exception as e:
            await db.rollback()
            logger.error(f"更新场地申请失败: {e}", exc_info=True)
            raise Exception("更新场地申请失败")