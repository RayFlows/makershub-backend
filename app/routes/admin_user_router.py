# app/routes/admin_user_router.py
"""
管理员用户路由模块，提供管理员端的用户管理API接口。
[v2.0 SQLAlchemy 迁移版]
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional

from app.core.logging import logger
from app.core.admin_auth import get_admin_auth # 直接导入依赖
from app.services.admin_user_service import AdminUserService
from app.core.database import get_db

router = APIRouter()

# --- 请求模型 (保持不变) ---
class UserRoleUpdateRequest(BaseModel):
    role: int = Field(..., ge=0, le=2)

class UserStateUpdateRequest(BaseModel):
    state: int = Field(..., ge=0, le=1)

class UserInfoUpdateRequest(BaseModel):
    role: Optional[int] = Field(None, ge=0, le=2)
    state: Optional[int] = Field(None, ge=0, le=1)
    department: Optional[int] = None
    score: Optional[int] = Field(None, ge=0)
    total_dutytime: Optional[int] = Field(None, ge=0)

# --- API 路由 ---

@router.get("/list", summary="获取用户列表")
async def get_user_list(
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_admin_auth),
    role: Optional[int] = Query(None),
    state: Optional[int] = Query(None),
    department: Optional[int] = Query(None),
    search: Optional[str] = Query(None)
):
    """获取用户列表，支持多种条件筛选和关键词搜索。"""
    try:
        filters = {k: v for k, v in locals().items() if v is not None and k in ['role', 'state', 'department', 'search']}
        return await AdminUserService.get_all_users_admin(db, filters)
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/role/{userid}", summary="更新用户角色")
async def update_user_role(
    userid: str,
    request: UserRoleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_admin_auth)
):
    """更新指定用户的角色（权限等级）。"""
    try:
        update_data = {"role": request.role}
        result = await AdminUserService.update_user_info_by_admin(db, userid, update_data)
        logger.info(f"管理员 {admin} 更新用户 {userid} 角色为 {request.role}")
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"更新用户角色失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/state/{userid}", summary="更新用户状态")
async def update_user_state(
    userid: str,
    request: UserStateUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_admin_auth)
):
    """更新指定用户的状态（封禁/解封）。"""
    try:
        update_data = {"state": request.state}
        result = await AdminUserService.update_user_info_by_admin(db, userid, update_data)
        action = "封禁" if request.state == 0 else "解封"
        logger.info(f"管理员 {admin} {action} 用户 {userid}")
        # 为了前端兼容性，可以自定义message
        result["message"] = f"用户已{action}"
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"更新用户状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/update/{userid}", summary="更新用户综合信息")
async def update_user_info(
    userid: str,
    request: UserInfoUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_admin_auth)
):
    """由管理员更新用户的多个字段信息。"""
    try:
        update_data = request.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="没有提供要更新的数据")
        
        result = await AdminUserService.update_user_info_by_admin(db, userid, update_data)
        logger.info(f"管理员 {admin} 更新用户 {userid} 信息: {list(update_data.keys())}")
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"更新用户信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/detail/{userid}", summary="获取用户详情")
async def get_user_detail(
    userid: str,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_admin_auth)
):
    """获取单个用户的完整详细信息。"""
    try:
        return await AdminUserService.get_user_detail_by_admin(db, userid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取用户详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", summary="获取用户统计信息")
async def get_user_stats(
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_admin_auth)
):
    """获取所有用户的总体统计数据，如总数、各角色人数、部门分布等。"""
    try:
        result = await AdminUserService.get_all_users_admin(db) # 获取全部数据以计算统计
        stats_data = {
            "code": 200, "message": "获取统计信息成功",
            "data": {
                "stats": result['data']['stats'],
                "department_stats": result['data']['department_stats']
            }
        }
        return stats_data
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))