# app/routes/admin_router.py
"""
管理员路由模块
独立于微信小程序的管理后台API接口
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
from loguru import logger
from app.core.config import settings
from app.core.admin_auth import create_admin_token, verify_admin_token
from app.services.admin_service import AdminService
import os

router = APIRouter()
admin_service = AdminService()

# 管理员登录请求模型
class AdminLoginRequest(BaseModel):
    username: str
    password: str

# 管理员认证依赖
async def get_admin_auth(authorization: Optional[str] = Header(None)):
    """
    验证管理员token
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="未提供认证token")
    
    # 移除 "Bearer " 前缀
    token = authorization.replace("Bearer ", "")
    
    if not verify_admin_token(token):
        raise HTTPException(status_code=401, detail="无效的认证token")
    
    return True

@router.post("/login")
async def admin_login(request: AdminLoginRequest):
    """
    管理员登录接口
    
    使用硬编码的管理员账号密码进行验证
    """
    try:
        # 从环境变量获取管理员凭据（如果没有则使用默认值）
        ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
        ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "MakerHub@2024#Secret")
        
        # 验证账号密码
        if request.username != ADMIN_USERNAME or request.password != ADMIN_PASSWORD:
            logger.warning(f"管理员登录失败: 用户名={request.username}")
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        # 生成token
        token = create_admin_token(request.username)
        
        logger.info(f"管理员登录成功: {request.username}")
        
        return {
            "code": 200,
            "message": "登录成功",
            "data": {
                "token": token,
                "username": request.username
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"管理员登录异常: {str(e)}")
        raise HTTPException(status_code=500, detail="登录失败")

@router.get("/verify")
async def verify_token(admin: bool = Depends(get_admin_auth)):
    """
    验证管理员token是否有效
    """
    return {
        "code": 200,
        "message": "token有效",
        "data": {
            "valid": True
        }
    }

@router.post("/logout")
async def admin_logout(admin: bool = Depends(get_admin_auth)):
    """
    管理员登出（前端清理token即可，这里仅作为接口预留）
    """
    return {
        "code": 200,
        "message": "登出成功"
    }

# 统计数据接口
@router.get("/stats/overview")
async def get_overview_stats(admin: bool = Depends(get_admin_auth)):
    """
    获取系统概览统计数据
    """
    try:
        stats = await admin_service.get_overview_stats()
        return {
            "code": 200,
            "message": "获取统计数据成功",
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取统计数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取统计数据失败")

