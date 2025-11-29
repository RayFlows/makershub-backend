# app/services/user_service.py
"""
用户服务类：处理与用户相关的所有业务逻辑
[v2.0 SQLAlchemy 迁移版]
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from datetime import datetime
import random
from io import BytesIO

from app.models.user import User
from app.core.auth import create_access_token
from app.core.config import settings
from app.core.storage import minio_client

class UserService:
    """
    用户服务类，封装了所有面向小程序用户的业务逻辑。
    所有方法都接收一个AsyncSession对象来执行数据库操作。
    """

    def _user_to_dict(self, user: User) -> Optional[dict]:
        """
        辅助函数：将SQLAlchemy User ORM对象安全地转换为字典。
        用于API响应序列化，以保持与旧接口的数据结构兼容。
        
        Args:
            user: SQLAlchemy的User模型实例。
        
        Returns:
            一个包含用户信息的字典，如果输入为None则返回None。
        """
        if not user:
            return None
        return {
            "userid": user.userid,
            "maker_id": user.maker_id,
            "student_id": user.student_id, # [v0.3 新增]
            "qq": user.qq,                 # [v0.3 新增]
            "grade": user.grade,           # [v0.2 新增]
            "role": user.role,
            "department": user.department,
            "real_name": user.real_name,
            "phone_num": user.phone_num,
            "college": user.college,       # 确保包含 college
            "motto": user.motto,
            "state": user.state,
            "profile_photo": user.profile_photo,
            "score": user.score,
            "total_dutytime": user.total_dutytime,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None
        }
    
    async def get_user_orm_by_id(self, db: AsyncSession, openid: str) -> Optional[User]:
        """
        根据openid获取用户的ORM实例。
        这是一个内部使用的辅助方法，方便其他服务方法直接获取可操作的ORM对象。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            openid: 用户的微信openid。
            
        Returns:
            User ORM实例，如果未找到则返回None。
        """
        stmt = select(User).where(User.userid == openid)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_or_update_wx_user(self, db: AsyncSession, openid: str) -> dict:
        """
        创建或更新微信用户信息并生成访问令牌。
        这是用户通过微信登录时的核心业务逻辑。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            openid: 微信用户的唯一标识符。
            
        Returns:
            包含状态码、用户令牌和完整用户信息的字典。
        """
        try:
            logger.info(f"开始处理微信用户: {openid}")
            user = await self.get_user_orm_by_id(db, openid)
                
            if not user:
                logger.info(f"用户不存在，开始创建新用户: {openid}")
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
                random_suffix = str(random.randint(100, 999))
                maker_id = f"MK{timestamp}_{random_suffix}"
                
                new_user = User(
                    userid=openid,
                    maker_id=maker_id,
                    real_name="",
                    profile_photo="default-profile-photo.jpg"
                    # 其他字段将使用模型中定义的默认值
                )
                db.add(new_user)
                await db.commit()
                await db.refresh(new_user)
                user = new_user
                logger.info(f"新用户创建成功: {openid}")
            else:
                logger.info(f"用户已存在: {openid}")

            token = create_access_token(openid)
            user_info = self._user_to_dict(user)
            
            if not user_info:
                 logger.error(f"在登录/创建后未能获取用户信息: {openid}")
                 return {"code": 500, "message": "获取用户信息失败"}

            return {
                "code": 200,
                "data": {"token": token, "user_info": user_info}
            }
        except Exception as e:
            await db.rollback()
            logger.error(f"处理微信用户失败: {e}", exc_info=True)
            raise e

    async def get_user(self, db: AsyncSession, openid: str) -> Optional[dict]:
        """
        根据openid获取并序列化用户信息。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            openid: 用户的微信openid。
            
        Returns:
            用户信息字典，如果用户不存在则返回None。
        """
        user = await self.get_user_orm_by_id(db, openid)
        return self._user_to_dict(user)

    async def update_user_profile(self, db: AsyncSession, user: User, update_data: dict) -> User:
        """
        通用更新用户资料的方法。
        包含对特定字段的业务逻辑校验。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            user: 要更新的User ORM实例。
            update_data: 包含要更新字段和值的字典。
            
        Returns:
            更新并刷新后的User ORM实例。
        """
        try:
            # 校验学号
            if "student_id" in update_data:
                student_id = update_data["student_id"]
                # 如果传了空字符串，视为清除或不更新（视具体业务而定，这里假设允许更新为空）
                if student_id:
                    if not student_id.isdigit():
                         raise ValueError("学号必须由纯数字组成")
                    # 可以在这里添加长度校验，例如 if len(student_id) < 8: ...

            # 校验QQ
            if "qq" in update_data:
                qq = update_data["qq"]
                if qq and not qq.isdigit():
                    raise ValueError("QQ号必须由纯数字组成")

            # 校验年级 (如果有) - [v0.3 新增]
            if "grade" in update_data:
                grade = update_data["grade"]
                if grade and not grade.isdigit():
                    raise ValueError("年级必须由纯数字组成 (例如 '2023')")

            for field, value in update_data.items():
                if hasattr(user, field):
                    setattr(user, field, value)
            
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info(f"用户资料更新成功: {user.userid}")
            return user
        except ValueError as ve:
            # 捕获校验错误，这里不回滚因为还没开始写库，但为了统一逻辑可以不处理直接抛出
            logger.warning(f"用户更新数据校验失败: {ve}")
            raise ve
        except Exception as e:
            await db.rollback()
            logger.error(f"更新用户资料失败: {e}", exc_info=True)
            raise e

    async def update_user_profile_photo(self, db: AsyncSession, user_id: str, photo_data: bytes) -> dict:
        """
        更新用户头像，包括上传文件到MinIO和更新数据库记录。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            user_id: 用户的openid。
            photo_data: 头像文件的二进制数据。
            
        Returns:
            包含操作结果和新头像URL的字典。
        """
        try:
            user = await self.get_user_orm_by_id(db, user_id)
            if not user:
                return {"success": False, "error": "User not found"}
                
            file_name = f"{user_id}.jpg"
            
            minio_client.upload_file(
                photo_data,
                file_name,
                content_type="image/jpeg",
                bucket_type="AVATARS"
            )
            
            url_result = minio_client.get_file(file_name, bucket_type="AVATARS")
            if "error" in url_result:
                return {"success": False, "error": url_result["error"]}

            user.profile_photo = file_name
            db.add(user)
            await db.commit()
            
            return {"success": True, "url": url_result["url"]}
        except Exception as e:
            await db.rollback()
            logger.error(f"更新用户头像失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def get_all_makers(self, db: AsyncSession) -> dict:
        """
        获取全部协会成员及编号，用于小程序端展示。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
        
        Returns:
            按部门分组的成员列表。
        """
        try:
            stmt = select(User.real_name, User.maker_id, User.department)\
                .where(User.state == 1, User.role.in_([1, 2]))\
                .order_by(User.department)

            result = await db.execute(stmt)
            makers = result.all()
            
            department_groups = {}
            for maker in makers:
                dept = maker.department
                maker_info = {"name": maker.real_name, "maker_id": maker.maker_id}
                if dept not in department_groups:
                    department_groups[dept] = []
                department_groups[dept].append(maker_info)
            
            result_list = []
            ordered_departments = [0, 1, 2, 3, 4, 5, 999]
            for dept in ordered_departments:
                if dept in department_groups:
                    result_list.append({
                        "department": dept,
                        "makers": department_groups[dept]
                    })
            
            return {
                "code": 200,
                "message": "successfully get all makers",
                "list": result_list
            }
        except Exception as e:
            logger.error(f"获取协会成员列表失败: {e}", exc_info=True)
            raise e

    async def search_users_by_phone(self, db: AsyncSession, phone_keyword: str) -> list:
        """
        根据手机号模糊搜索用户 (用于前端实时联想)
        只返回前10条匹配记录。
        """
        try:
            # 如果搜索词为空，直接返回空列表
            if not phone_keyword or not phone_keyword.strip():
                return []
            
            # 使用 like 进行模糊匹配: %keyword%
            # limit(10) 限制返回数量，防止搜索 "1" 时把全库都查出来
            stmt = select(User).where(
                User.phone_num.like(f"%{phone_keyword}%")
            ).limit(10)
            
            result = await db.execute(stmt)
            users = result.scalars().all()
            
            # 构造精简的返回数据
            return [
                {
                    "real_name": u.real_name,
                    "college": u.college,
                    "phone_num": u.phone_num,
                    "maker_id": u.maker_id  # 这是前端真正需要的“里子”
                }
                for u in users
            ]
        except Exception as e:
            logger.error(f"搜索用户失败: {e}", exc_info=True)
            raise e