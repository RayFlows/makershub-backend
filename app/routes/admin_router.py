# app/routes/admin_router.py
"""
管理员路由模块
独立于微信小程序的管理后台API接口。
[v2.0 SQLAlchemy 迁移版]
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from loguru import logger
import os

from app.core.config import settings
from app.core.admin_auth import create_admin_token, get_admin_auth # 导入 get_admin_auth
from app.services.admin_service import AdminService
from app.core.database import get_db # 导入 get_db

router = APIRouter()
admin_service = AdminService()

class AdminLoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
async def admin_login(request: AdminLoginRequest):
    """
    管理员登录接口。
    此接口逻辑不变，因为它不直接与业务数据库交互。
    """
    try:
        ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
        ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "MakerHub@2024") # 修正了你注释中的密码
        
        if request.username != ADMIN_USERNAME or request.password != ADMIN_PASSWORD:
            logger.warning(f"管理员登录失败: 用户名={request.username}")
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        token = create_admin_token(request.username)
        logger.info(f"管理员登录成功: {request.username}")
        
        return {
            "code": 200, "message": "登录成功",
            "data": {"token": token, "username": request.username}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"管理员登录异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="登录失败")

@router.get("/verify")
async def verify_token(admin: str = Depends(get_admin_auth)):
    """
    验证管理员token是否有效。
    现在依赖于 get_admin_auth, 成功时 admin 会被注入用户名。
    """
    return {
        "code": 200, "message": "token有效",
        "data": {"valid": True, "username": admin}
    }

@router.post("/logout")
async def admin_logout(admin: str = Depends(get_admin_auth)):
    """
    管理员登出（前端清理token即可，这里仅作为接口预留）。
    """
    return {"code": 200, "message": "登出成功"}

@router.get("/stats/overview")
async def get_overview_stats(
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_admin_auth)
):
    """
    获取系统概览统计数据。
    [迁移中]：部分数据为实时，部分为模拟。
    """
    try:
        stats = await admin_service.get_overview_stats(db) # 传入 db 会话
        return {
            "code": 200,
            "message": "获取统计数据成功（部分数据为模拟）",
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取统计数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取统计数据失败")