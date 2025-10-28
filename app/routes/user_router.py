# app/routes/user_router.py
"""
用户路由模块 (User Router Module) 
本模块负责处理所有与用户相关的API路由，包括微信登录和用户信息管理。
[v2.0 SQLAlchemy 迁移版]
"""
from fastapi import APIRouter, HTTPException, File, UploadFile, Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.services.user_service import UserService
from app.core.config import settings
from app.core.auth import AuthMiddleware, require_permission_level
from app.models.user import User
from app.core.database import get_db
from app.core.storage import minio_client
import aiohttp
import json

router = APIRouter()
user_service = UserService()

class WxLoginRequest(BaseModel):
    code: str

@router.post("/wx-login")
async def wx_login(request: WxLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    微信小程序登录接口。
    接收前端的临时code，换取openid，然后创建或更新用户并返回JWT。
    """
    try:
        url = f"{settings.WECHAT_LOGIN_URL}?appid={settings.WECHAT_APPID}&secret={settings.WECHAT_SECRET}&js_code={request.code}&grant_type=authorization_code"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                wx_response_text = await response.text()
                wx_response = json.loads(wx_response_text)

        if 'errcode' in wx_response and wx_response['errcode'] != 0:
            error_msg = wx_response.get('errmsg', 'Unknown WeChat API error')
            logger.error(f"微信API返回错误: {error_msg}")
            raise HTTPException(status_code=502, detail=f"微信登录失败: {error_msg}")

        openid = wx_response.get("openid")
        if not openid:
            logger.error("微信登录失败: 未能从微信API获取openid")
            raise HTTPException(status_code=502, detail="微信登录失败: openid获取失败")

        return await user_service.create_or_update_wx_user(db, openid)
    except aiohttp.ClientError as e:
        logger.error(f"请求微信API时网络错误: {e}")
        raise HTTPException(status_code=504, detail="微信服务响应超时")
    except Exception as e:
        logger.error(f"微信登录流程异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.get("/profile")
async def get_user_profile(current_user: User = Depends(AuthMiddleware.get_current_user)):
    """
    获取当前登录用户的个人资料。
    """
    try:
        user_data = user_service._user_to_dict(current_user)
        
        # 处理头像URL的逻辑保持不变
        if user_data.get("profile_photo"):
            photo_url_result = minio_client.get_file(user_data["profile_photo"], bucket_type="AVATARS")
            if "url" in photo_url_result:
                user_data["profile_photo"] = photo_url_result["url"]
            else:
                logger.warning(f"获取头像URL失败 for {user_data['profile_photo']}")
                user_data["profile_photo"] = ""
        
        # 只返回前端需要的字段，保持API兼容性
        profile_data = {
            "real_name": user_data.get("real_name", ""),
            "role": user_data.get("role", 0),
            "phone_num": user_data.get("phone_num", ""),
            "state": user_data.get("state", 1),
            "profile_photo": user_data.get("profile_photo", ""),
            "motto": user_data.get("motto", ""),
            "score": user_data.get("score", 0)
        }
        return {"code": 200, "message": "获取用户资料成功", "data": profile_data}
    except Exception as e:
        logger.error(f"获取用户资料失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取用户资料失败")

class UserProfileUpdatePayload(BaseModel):
    real_name: Optional[str] = None
    phone_num: Optional[str] = None
    motto: Optional[str] = None

class UserProfileUpdateRequest(BaseModel):
    data: UserProfileUpdatePayload

@router.patch("/profile")
async def update_user_profile(
    request: UserProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthMiddleware.get_current_user)
):
    """
    更新当前登录用户的个人资料（姓名、手机、签名）。
    """
    try:
        update_data = request.data.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="没有提供任何要更新的字段")

        await user_service.update_user_profile(db, current_user, update_data)
        
        return {"code": 200, "message": "用户资料更新成功", "data": {"updated_fields": list(update_data.keys())}}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"更新用户资料失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.post("/profile-photo")
async def upload_profile_photo(
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    current_user: User = Depends(AuthMiddleware.get_current_user)
):
    """
    上传或更新当前登录用户的头像。
    """
    try:
        contents = await file.read()
        if not contents:
             raise HTTPException(status_code=400, detail="上传的文件为空")

        result = await user_service.update_user_profile_photo(db, current_user.userid, contents)

        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "头像上传失败"))
            
        return {
            "code": 200,
            "message": "头像上传成功",
            "data": {"profile_photo": result.get("url", "")}
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"上传头像失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="上传头像失败")

@router.get("/get-makers")
async def get_all_makers(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission_level(2)) # 验证权限
):
    """
    获取全部协会成员列表，按部门分组。仅限部长及以上权限访问。
    """
    try:
        return await user_service.get_all_makers(db)
    except Exception as e:
        logger.error(f"获取协会成员列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取协会成员列表失败")