# app/routes/admin_user_router.py
"""
管理员用户路由模块
提供管理员端的用户管理API接口
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Header
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.core.logging import logger
from app.core.admin_auth import verify_admin_token
from app.services.admin_user_service import AdminUserService

router = APIRouter()

# ========== 请求模型定义 ==========

class UserRoleUpdateRequest(BaseModel):
    """用户角色更新请求模型"""
    role: int = Field(..., ge=0, le=2, description="用户角色: 0=普通用户, 1=干事, 2=部长及以上")

class UserStateUpdateRequest(BaseModel):
    """用户状态更新请求模型"""
    state: int = Field(..., ge=0, le=1, description="用户状态: 0=封禁, 1=正常")

class UserInfoUpdateRequest(BaseModel):
    """用户信息更新请求模型"""
    role: Optional[int] = Field(None, ge=0, le=2, description="用户角色")
    state: Optional[int] = Field(None, ge=0, le=1, description="用户状态")
    department: Optional[int] = Field(None, description="部门")
    score: Optional[int] = Field(None, ge=0, description="积分")
    total_dutytime: Optional[int] = Field(None, ge=0, description="值班时长")

# ========== 认证依赖 ==========

async def get_admin_auth(authorization: Optional[str] = Header(None)):
    """
    验证管理员token
    从Header中获取Authorization并验证
    """
    if not authorization:
        logger.warning("[AdminUserRouter] 未提供认证token")
        raise HTTPException(status_code=401, detail="未提供认证token")
    
    # 移除 "Bearer " 前缀
    token = authorization.replace("Bearer ", "")
    
    # 使用管理员认证验证token
    username = verify_admin_token(token)
    
    if not username:
        logger.warning("[AdminUserRouter] 无效的认证token")
        raise HTTPException(status_code=401, detail="无效的认证token")
    
    logger.debug(f"[AdminUserRouter] 管理员认证成功: {username}")
    return username

# ========== API路由 ==========

@router.get("/list")
async def get_user_list(
    admin: str = Depends(get_admin_auth),
    role: Optional[int] = Query(None, description="用户角色"),
    state: Optional[int] = Query(None, description="用户状态"),
    department: Optional[int] = Query(None, description="部门"),
    search: Optional[str] = Query(None, description="搜索关键字")
):
    """
    获取用户列表（管理员）
    
    支持按角色、状态、部门筛选，支持搜索姓名和手机号
    """
    try:
        logger.info(f"[AdminUserRouter] 管理员 {admin} 请求用户列表")
        
        # 构建筛选条件
        filters = {}
        if role is not None:
            filters['role'] = role
        if state is not None:
            filters['state'] = state
        if department is not None:
            filters['department'] = department
        if search:
            filters['search'] = search
        
        result = AdminUserService.get_all_users_admin(filters)
        return result
        
    except Exception as e:
        logger.error(f"[AdminUserRouter] 获取用户列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/role/{userid}")
async def update_user_role(
    userid: str,
    request: UserRoleUpdateRequest,
    admin: str = Depends(get_admin_auth)
):
    """
    更新用户角色（管理员）
    
    修改用户的权限级别
    """
    try:
        logger.info(f"[AdminUserRouter] 管理员 {admin} 更新用户角色: {userid} -> {request.role}")
        
        result = AdminUserService.update_user_role(userid, request.role)
        
        # 记录操作日志
        logger.info(f"管理员操作日志 | 操作人: {admin} | 操作: 更新用户角色 | "
                   f"用户ID: {userid} | 新角色: {request.role}")
        
        return result
        
    except ValueError as e:
        logger.warning(f"[AdminUserRouter] 更新用户角色参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[AdminUserRouter] 更新用户角色失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/state/{userid}")
async def update_user_state(
    userid: str,
    request: UserStateUpdateRequest,
    admin: str = Depends(get_admin_auth)
):
    """
    更新用户状态（管理员）
    
    封禁或解封用户
    """
    try:
        action = "封禁" if request.state == 0 else "解封"
        logger.info(f"[AdminUserRouter] 管理员 {admin} {action}用户: {userid}")
        
        result = AdminUserService.update_user_state(userid, request.state)
        
        # 记录操作日志
        logger.info(f"管理员操作日志 | 操作人: {admin} | 操作: {action}用户 | 用户ID: {userid}")
        
        return result
        
    except ValueError as e:
        logger.warning(f"[AdminUserRouter] 更新用户状态参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[AdminUserRouter] 更新用户状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/update/{userid}")
async def update_user_info(
    userid: str,
    request: UserInfoUpdateRequest,
    admin: str = Depends(get_admin_auth)
):
    """
    更新用户信息（管理员）
    
    批量更新用户的多个字段
    """
    try:
        logger.info(f"[AdminUserRouter] 管理员 {admin} 更新用户信息: {userid}")
        
        # 过滤掉None值，只更新提供的字段
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        
        if not update_data:
            raise ValueError("没有提供要更新的数据")
        
        result = AdminUserService.update_user_info(userid, update_data)
        
        # 记录操作日志
        logger.info(f"管理员操作日志 | 操作人: {admin} | 操作: 更新用户信息 | "
                   f"用户ID: {userid} | 更新字段: {list(update_data.keys())}")
        
        return result
        
    except ValueError as e:
        logger.warning(f"[AdminUserRouter] 更新用户信息参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[AdminUserRouter] 更新用户信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/detail/{userid}")
async def get_user_detail(
    userid: str,
    admin: str = Depends(get_admin_auth)
):
    """
    获取用户详细信息（管理员）
    
    返回单个用户的完整信息
    """
    try:
        logger.info(f"[AdminUserRouter] 管理员 {admin} 查看用户详情: {userid}")
        
        result = AdminUserService.get_user_detail(userid)
        return result
        
    except ValueError as e:
        logger.warning(f"[AdminUserRouter] 获取用户详情失败: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[AdminUserRouter] 获取用户详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_user_stats(
    admin: str = Depends(get_admin_auth)
):
    """
    获取用户统计信息（管理员）
    
    返回用户的总体统计数据
    """
    try:
        logger.info(f"[AdminUserRouter] 管理员 {admin} 请求用户统计")
        
        # 获取所有用户以计算统计
        result = AdminUserService.get_all_users_admin()
        
        # 提取统计信息
        if result['code'] == 200:
            stats_data = {
                "code": 200,
                "message": "获取统计信息成功",
                "data": {
                    "stats": result['data']['stats'],
                    "department_stats": result['data']['department_stats']
                }
            }
            return stats_data
        else:
            return result
        
    except Exception as e:
        logger.error(f"[AdminUserRouter] 获取统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))