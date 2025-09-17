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

# 物资管理接口
@router.get("/stuff")
async def get_all_stuff(admin: bool = Depends(get_admin_auth)):
    """
    获取所有物资（管理员视角）
    """
    try:
        result = await admin_service.get_all_stuff()
        return {
            "code": 200,
            "message": "获取物资列表成功",
            "data": result
        }
    except Exception as e:
        logger.error(f"获取物资列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取物资列表失败")

@router.post("/stuff")
async def add_stuff(stuff_data: dict, admin: bool = Depends(get_admin_auth)):
    """
    添加物资
    """
    try:
        result = await admin_service.add_stuff(stuff_data)
        return {
            "code": 200,
            "message": "添加物资成功",
            "data": result
        }
    except Exception as e:
        logger.error(f"添加物资失败: {str(e)}")
        raise HTTPException(status_code=500, detail="添加物资失败")

@router.put("/stuff/{stuff_id}")
async def update_stuff(
    stuff_id: str, 
    stuff_data: dict, 
    admin: bool = Depends(get_admin_auth)
):
    """
    更新物资信息
    """
    try:
        result = await admin_service.update_stuff(stuff_id, stuff_data)
        return {
            "code": 200,
            "message": "更新物资成功",
            "data": result
        }
    except Exception as e:
        logger.error(f"更新物资失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新物资失败")

@router.delete("/stuff/{stuff_id}")
async def delete_stuff(stuff_id: str, admin: bool = Depends(get_admin_auth)):
    """
    删除物资
    """
    try:
        result = await admin_service.delete_stuff(stuff_id)
        return {
            "code": 200,
            "message": "删除物资成功"
        }
    except Exception as e:
        logger.error(f"删除物资失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除物资失败")

# 场地管理接口
@router.get("/sites")
async def get_all_sites(admin: bool = Depends(get_admin_auth)):
    """
    获取所有场地（管理员视角）
    """
    try:
        result = await admin_service.get_all_sites()
        return {
            "code": 200,
            "message": "获取场地列表成功",
            "data": result
        }
    except Exception as e:
        logger.error(f"获取场地列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取场地列表失败")

@router.post("/sites")
async def add_site(site_data: dict, admin: bool = Depends(get_admin_auth)):
    """
    添加场地
    """
    try:
        result = await admin_service.add_site(site_data)
        return {
            "code": 200,
            "message": "添加场地成功",
            "data": result
        }
    except Exception as e:
        logger.error(f"添加场地失败: {str(e)}")
        raise HTTPException(status_code=500, detail="添加场地失败")

@router.put("/sites/{site_id}")
async def update_site(
    site_id: str, 
    site_data: dict, 
    admin: bool = Depends(get_admin_auth)
):
    """
    更新场地信息
    """
    try:
        result = await admin_service.update_site(site_id, site_data)
        return {
            "code": 200,
            "message": "更新场地成功",
            "data": result
        }
    except Exception as e:
        logger.error(f"更新场地失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新场地失败")

@router.delete("/sites/{site_id}")
async def delete_site(site_id: str, admin: bool = Depends(get_admin_auth)):
    """
    删除场地
    """
    try:
        result = await admin_service.delete_site(site_id)
        return {
            "code": 200,
            "message": "删除场地成功"
        }
    except Exception as e:
        logger.error(f"删除场地失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除场地失败")

# 用户管理接口
@router.get("/users")
async def get_all_users(admin: bool = Depends(get_admin_auth)):
    """
    获取所有用户（管理员视角）
    """
    try:
        result = await admin_service.get_all_users()
        return {
            "code": 200,
            "message": "获取用户列表成功",
            "data": result
        }
    except Exception as e:
        logger.error(f"获取用户列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户列表失败")

@router.put("/users/{user_id}/ban")
async def ban_user(user_id: str, admin: bool = Depends(get_admin_auth)):
    """
    封禁用户
    """
    try:
        result = await admin_service.ban_user(user_id)
        return {
            "code": 200,
            "message": "封禁用户成功"
        }
    except Exception as e:
        logger.error(f"封禁用户失败: {str(e)}")
        raise HTTPException(status_code=500, detail="封禁用户失败")

@router.put("/users/{user_id}/unban")
async def unban_user(user_id: str, admin: bool = Depends(get_admin_auth)):
    """
    解封用户
    """
    try:
        result = await admin_service.unban_user(user_id)
        return {
            "code": 200,
            "message": "解封用户成功"
        }
    except Exception as e:
        logger.error(f"解封用户失败: {str(e)}")
        raise HTTPException(status_code=500, detail="解封用户失败")

@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str, 
    role_data: dict, 
    admin: bool = Depends(get_admin_auth)
):
    """
    更新用户角色
    """
    try:
        new_role = role_data.get("role")
        if new_role not in [0, 1, 2]:
            raise HTTPException(status_code=400, detail="无效的角色值")
        
        result = await admin_service.update_user_role(user_id, new_role)
        return {
            "code": 200,
            "message": "更新用户角色成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户角色失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新用户角色失败")