#user_service.py
from typing import Optional
from app.models.user import User
from app.core.auth import create_access_token
from loguru import logger
import uuid
from io import BytesIO
from app.core.config import settings
from app.core.db import minio_client

class UserService:
    """
    用户服务类：处理与用户相关的所有业务逻辑
    
    提供微信用户的创建、查询和信息更新等功能
    """

    async def create_or_update_wx_user(self, openid: str) -> dict:
        """
        创建或更新微信用户信息并生成访问令牌
        
        Args:
            openid: 微信用户的唯一标识符
            
        Returns:
            dict: 包含状态码、用户令牌和用户信息的字典
            
        Raises:
            Exception: 数据库操作失败时抛出异常
        """
        try:
            logger.info("开始处理微信用户") 

            try:
                # 查询用户是否已存在
                user = User.objects(userid=openid).first()
            except Exception as e:
                logger.error(f"数据库要不没连上，要不就是连上了创建用户失败：{e}")
                raise  # 重新抛出异常，让调用方处理
                
            logger.info("数据库查询完成")  
            if not user:
                # 用户不存在，创建新用户
                logger.info(f"创建新用户: {openid}")

                default_avatar = "default-profile-photo.jpg"  # 默认头像文件名
                
                user = User(
                    userid=openid,
                    real_name="",  # 初始化为空字符串
                    state=1,       # 1表示正常状态
                    score=0,       # 初始积分为0
                    role=1,        # 初始用户级别为1
                    profile_photo=default_avatar,  # 初始化头像链接为空
                    phone_num="",  # 初始化手机号为空
                    motto="",       # 初始化个性签名为空
                    total_dutytime=0  # 初始总值班时长为0
                )
                user.save()
            else:
                logger.info(f"用户已存在: {openid}")

            # 生成用户认证令牌
            token = create_access_token(openid)
            return {
                "code": 200,  # 成功状态码
                "data": {
                    "token": token,
                    "user_info": await self.get_user(openid),  # 获取完整用户信息
                }
            }
        except Exception as e:
            logger.error(f"微信用户处理失败: {e}")
            raise e  # 向上层抛出异常

    async def get_user(self, openid: str) -> Optional[dict]:
        """
        根据openid获取用户信息
        
        Args:
            openid: 用户的微信openid
            
        Returns:
            Optional[dict]: 用户信息字典，未找到用户则返回None
        """
        user = User.objects(userid=openid).first()
        return user.to_dict() if user else None

    async def update_user_score(self, user_id: str, score_change: int) -> bool:
        """
        更新用户积分
        
        Args:
            user_id: 用户ID
            score_change: 积分变化值，可正可负
            
        Returns:
            bool: 更新成功返回True，失败返回False
        """
        try:
            user = User.objects(userid=user_id).first()
            if user:
                user.score += score_change  # 增加或减少用户积分
                user.save()
                return True
            return False  # 用户不存在
        except Exception:
            return False  # 数据库操作失败

    async def update_user_state(self, user_id: str, state: int) -> bool:
        """
        更新用户状态
        
        Args:
            user_id: 用户ID
            state: 用户状态值(0:禁用, 1:正常)
            
        Returns:
            bool: 更新成功返回True，失败返回False
        """
        try:
            user = User.objects(userid=user_id).first()
            if user:
                user.state = state
                user.save()
                return True
            return False  # 用户不存在
        except Exception:
            return False  # 数据库操作失败
        
    async def update_user_realname(self, user_id: str, real_name: str) -> bool:
        """
        更新用户真实姓名
        
        Args:
            user_id: 用户ID
            real_name: 用户真实姓名
            
        Returns:
            bool: 更新成功返回True，失败返回False
        """
        try:
            user = User.objects(userid=user_id).first()
            if user:
                user.real_name = real_name
                user.save()
                return True
            return False  # 用户不存在
        except Exception:
            return False  # 数据库操作失败

    # user_service.py中修复的方法
    async def update_user_profile_photo(self, user_id: str, photo_data: bytes) -> dict:
        """
        更新用户头像
        
        将头像上传到MinIO并更新用户记录中的头像URL
        
        Args:
            user_id: 用户ID
            photo_data: 头像二进制数据
            
        Returns:
            dict: 包含成功状态和头像URL的字典
        """
        try:
            # 检查用户是否存在
            user = User.objects(userid=user_id).first()
            if not user:
                return {"success": False, "error": "User not found"}
                
            # 生成唯一文件名
            file_name = f"{user_id}.jpg"
            
            # 上传到MinIO
            minio_client.client.put_object(
                settings.MINIO_BUCKETS["AVATARS"],  # 使用正确的存储桶
                file_name,
                BytesIO(photo_data),
                length=len(photo_data),
                content_type="image/jpeg"
            )
            
            # 获取签名URL (关键修复)
            url_result = minio_client.get_file(
                file_name, 
                expire_seconds=3600,  # 使用数字3600而不是timedelta对象
                bucket_type="AVATARS"
            )
            
            if "error" in url_result:
                return {"success": False, "error": url_result["error"]}
            # 更新用户资料
            user.profile_photo = file_name
            user.save()
            
            return {
                "success": True, 
                "url": url_result["url"]
                # "url": result.get("url")
            }
        except Exception as e:
            logger.error(f"更新用户头像失败: {e}")
            return {"success": False, "error": str(e)}
            
    async def update_user_motto(self, user_id: str, motto: str) -> bool:
        """
        更新用户个性签名
        
        Args:
            user_id: 用户ID
            motto: 用户个性签名
            
        Returns:
            bool: 更新成功返回True，失败返回False
        """
        try:
            user = User.objects(userid=user_id).first()
            if user:
                user.motto = motto
                user.save()
                return True
            return False  # 用户不存在
        except Exception:
            return False  # 数据库操作失败