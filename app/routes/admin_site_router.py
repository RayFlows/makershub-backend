# app/routes/admin_site_router.py
"""
管理员场地路由模块
提供管理员端的场地管理API接口。
[v2.0 SQLAlchemy 迁移版 - 恢复并重构所有功能]
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.core.admin_auth import get_admin_auth
from app.services.admin_site_service import AdminSiteService
from app.services.site_borrow_service import SiteBorrowService # 导入以复用审核、归还逻辑
from app.core.database import get_db
from app.models.user import User

router = APIRouter()
admin_site_service = AdminSiteService()
site_borrow_service = SiteBorrowService() # 实例化

# --- 请求模型定义 (与原始文件完全兼容) ---

class SiteCreateRequest(BaseModel):
    """场地创建请求模型"""
    site: str = Field(..., description="场地名称")
    workstations: List[int] = Field(..., description="工位号列表")

class SiteUpdateRequest(BaseModel):
    """场地更新请求模型"""
    new_name: Optional[str] = Field(None, description="新场地名称")
    add_workstations: Optional[List[int]] = Field(None, description="新增工位列表")
    remove_workstations: Optional[List[int]] = Field(None, description="删除工位列表")

class ReviewRequest(BaseModel):
    """审核场地申请的请求模型"""
    state: int = Field(..., description="新状态：1=打回, 2=通过")
    review: str = Field("", description="审核意见")

# --- API路由 ---

@router.get("/list", summary="获取场地列表（管理员）")
async def get_site_list(
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_admin_auth),
    site: Optional[str] = Query(None, description="场地位置"),
    is_occupied: Optional[bool] = Query(None, description="占用状态")
):
    """
    获取场地列表（管理员），支持按场地位置和占用状态筛选。
    """
    try:
        logger.info(f"[AdminSiteRouter] 管理员 {admin} 请求场地列表")
        filters = {}
        if site: filters['site'] = site
        if is_occupied is not None: filters['is_occupied'] = is_occupied
        return await admin_site_service.get_all_sites_admin(db, filters)
    except Exception as e:
        logger.error(f"[AdminSiteRouter] 获取场地列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create", summary="创建新场地")
async def create_site(
    request: SiteCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_admin_auth)
):
    """
    创建新场地及多个工位（管理员）。
    """
    try:
        logger.info(f"[AdminSiteRouter] 管理员 {admin} 创建场地: {request.site}")
        result = await admin_site_service.create_site_admin(db, request.dict())
        logger.info(f"管理员操作日志 | 操作人: {admin} | 操作: 创建场地 | 场地: {request.site} | 工位数: {len(request.workstations)}")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete/{site_name}", summary="删除场地")
async def delete_site(
    site_name: str,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_admin_auth)
):
    """
    删除整个场地及其所有工位（管理员）。
    只有当场地所有工位都未被占用且无未完成借用申请时才能删除。
    """
    try:
        logger.info(f"[AdminSiteRouter] 管理员 {admin} 删除场地: {site_name}")
        result = await admin_site_service.delete_site_admin(db, site_name)
        logger.info(f"管理员操作日志 | 操作人: {admin} | 操作: 删除场地 | 场地: {site_name}")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 【TODO 已完成】恢复并重构与场地借用相关的管理接口 ---

@router.put("/update/{site_name}", summary="更新场地信息（管理员）")
async def update_site(
    site_name: str,
    request: SiteUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_admin_auth)
):
    """
    更新场地信息（管理员），支持修改名称、增删工位。
    """
    try:
        logger.info(f"[AdminSiteRouter] 管理员 {admin} 更新场地: {site_name}")
        update_data = request.dict(exclude_unset=True)
        if not update_data:
            raise ValueError("没有提供要更新的数据")
        
        result = await admin_site_service.update_site_admin(db, site_name, update_data)
        logger.info(f"管理员操作日志 | 操作人: {admin} | 操作: 更新场地 | 场地: {site_name} | 更新内容: {list(update_data.keys())}")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/borrow-history/{site_name}", summary="获取场地借用历史（管理员）")
async def get_site_borrow_history(
    site_name: str,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_admin_auth)
):
    """
    查看指定场地的所有借用记录。
    """
    try:
        logger.info(f"[AdminSiteRouter] 管理员 {admin} 查看场地借用历史: {site_name}")
        result = await admin_site_service.get_site_borrow_history(db, site_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", summary="获取场地统计信息（管理员）")
async def get_site_stats(
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_admin_auth)
):
    """
    获取场地的总体统计数据。
    """
    try:
        logger.info(f"[AdminSiteRouter] 管理员 {admin} 请求场地统计")
        result = await admin_site_service.get_all_sites_admin(db) # 复用列表接口的统计能力
        
        if result['code'] == 200:
            # ... (此统计逻辑可以根据前端需求细化，暂时返回基础统计)
            return {"code": 200, "message": "获取统计信息成功", "data": {"stats": result['data']['stats']}}
        else:
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/review-borrow/{apply_id}", summary="审核场地借用申请（管理员）")
async def review_site_borrow(
    apply_id: str,
    review_data: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_admin_auth)
):
    """
    审核场地借用申请（管理员）。批准操作将原子性地占用场地。
    """
    try:
        logger.info(f"[AdminSiteRouter] 管理员 {admin} 审核场地申请: {apply_id}")
        
        # 复用小程序端的 service 逻辑
        result_tuple = await site_borrow_service.review_application(db, apply_id, review_data.state, review_data.review)
        
        logger.info(f"管理员操作日志 | 操作人: {admin} | 操作: 审核场地申请 | 申请ID: {apply_id} | 结果: {'通过' if review_data.state == 2 else '打回'}")
        
        return {
            "code": 200, "message": "审核成功",
            "data": {"apply_id": result_tuple[0], "state": result_tuple[1], "review": result_tuple[2]}
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/return-borrow/{apply_id}", summary="确认场地归还（管理员）")
async def return_site_borrow(
    apply_id: str,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_admin_auth)
):
    """
    管理员确认场地已归还，将原子性地更新申请状态并释放场地。
    """
    try:
        logger.info(f"[AdminSiteRouter] 管理员 {admin} 确认场地归还: {apply_id}")
        
        # 复用小程序端的 service 逻辑
        result_tuple = await site_borrow_service.return_borrow_application(db, apply_id, admin)
        
        logger.info(f"管理员操作日志 | 操作人: {admin} | 操作: 确认场地归还 | 申请ID: {apply_id}")
        
        return {
            "code": 200, "message": "场地归还成功",
            "data": {"apply_id": result_tuple[0], "state": result_tuple[1]}
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))