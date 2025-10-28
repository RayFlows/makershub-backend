# app/routes/admin_stuff_router.py
"""
管理员物资路由模块
提供管理员端的物资管理API接口，包含完整的CRUD操作和批量操作。
[v2.0 SQLAlchemy 迁移版]
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.core.admin_auth import get_admin_auth
from app.services.admin_stuff_service import AdminStuffService
from app.core.database import get_db

router = APIRouter()

# --- 请求模型定义 (与旧版本完全兼容) ---

class StuffCreateRequest(BaseModel):
    """物资创建请求模型"""
    type: str = Field(..., description="物资类型")
    stuff_name: str = Field(..., description="物资名称")
    number_total: int = Field(..., ge=0, description="总数量")
    number_remain: int = Field(..., ge=0, description="剩余数量")
    description: str = Field("", description="描述信息")
    location: str = Field("", description="所在场地")
    cabinet: str = Field("", description="展柜位置")
    layer: int = Field(1, ge=1, le=10, description="所在层数")
    
class StuffUpdateRequest(BaseModel):
    """物资更新请求模型"""
    type: Optional[str] = Field(None, description="物资类型")
    stuff_name: Optional[str] = Field(None, description="物资名称")
    number_total: Optional[int] = Field(None, ge=0, description="总数量")
    number_remain: Optional[int] = Field(None, ge=0, description="剩余数量")
    description: Optional[str] = Field(None, description="描述信息")
    location: Optional[str] = Field(None, description="所在场地")
    cabinet: Optional[str] = Field(None, description="展柜位置")
    layer: Optional[int] = Field(None, ge=1, le=10, description="所在层数")

class BatchUpdateItem(BaseModel):
    """批量更新项"""
    stuff_id: str = Field(..., description="物资ID")
    update_data: StuffUpdateRequest = Field(..., description="更新数据")

class BatchUpdateRequest(BaseModel):
    """批量更新请求模型"""
    items: List[BatchUpdateItem] = Field(..., description="更新项列表")

# --- API路由 ---

@router.get("/list", summary="获取物资列表（管理员）")
async def get_stuff_list(
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_admin_auth),
    type: Optional[str] = Query(None, description="物资类型"),
    location: Optional[str] = Query(None, description="所在场地"),
    cabinet: Optional[str] = Query(None, description="展柜位置"),
    layer: Optional[int] = Query(None, description="层数"),
    search: Optional[str] = Query(None, description="搜索关键词")
):
    """
    获取物资列表（管理员）。
    支持多条件筛选，返回包含扩展字段的完整物资信息。
    """
    try:
        logger.info(f"[AdminStuffRouter] 管理员 {admin} 请求物资列表")
        
        filters = {k: v for k, v in locals().items() if v is not None and k in ['type', 'location', 'cabinet', 'layer', 'search']}
        
        return await AdminStuffService.get_all_stuff_admin(db, filters)
        
    except Exception as e:
        logger.error(f"[AdminStuffRouter] 获取物资列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create", summary="创建新物资")
async def create_stuff(
    request: StuffCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_admin_auth)
):
    """
    创建新物资（管理员）。
    创建包含位置信息的完整物资记录。
    """
    try:
        logger.info(f"[AdminStuffRouter] 管理员 {admin} 创建物资: {request.stuff_name}")
        
        result = await AdminStuffService.create_stuff_admin(db, request.dict())
        
        logger.info(f"管理员操作日志 | 操作人: {admin} | 操作: 创建物资 | 物资: {request.stuff_name} | 位置: {request.location}-{request.cabinet}-{request.layer}")
        
        return result
        
    except Exception as e:
        logger.error(f"[AdminStuffRouter] 创建物资失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/update/{stuff_id}", summary="更新物资信息")
async def update_stuff(
    stuff_id: str,
    request: StuffUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_admin_auth)
):
    """
    更新物资信息（管理员）。
    支持部分更新，只更新提供的字段。
    """
    try:
        logger.info(f"[AdminStuffRouter] 管理员 {admin} 更新物资: {stuff_id}")
        
        update_data = request.dict(exclude_unset=True)
        if not update_data:
            raise ValueError("没有提供要更新的数据")
        
        result = await AdminStuffService.update_stuff_admin(db, stuff_id, update_data)
        
        logger.info(f"管理员操作日志 | 操作人: {admin} | 操作: 更新物资 | 物资ID: {stuff_id} | 更新字段: {list(update_data.keys())}")
        
        return result
        
    except ValueError as e:
        logger.warning(f"[AdminStuffRouter] 更新物资参数错误: {str(e)}")
        # Service层抛出的ValueError可能是404（未找到）或400（验证错误）
        raise HTTPException(status_code=404 if "不存在" in str(e) else 400, detail=str(e))
    except Exception as e:
        logger.error(f"[AdminStuffRouter] 更新物资失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete/{stuff_id}", summary="删除物资")
async def delete_stuff(
    stuff_id: str,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_admin_auth)
):
    """
    删除物资（管理员）。
    只有当物资全部归还时才能删除。
    """
    try:
        logger.info(f"[AdminStuffRouter] 管理员 {admin} 删除物资: {stuff_id}")
        
        result = await AdminStuffService.delete_stuff_admin(db, stuff_id)
        
        logger.info(f"管理员操作日志 | 操作人: {admin} | 操作: 删除物资 | 物资ID: {stuff_id}")
        
        return result
        
    except ValueError as e:
        logger.warning(f"[AdminStuffRouter] 删除物资失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) # "有未归还记录" 或 "不存在"
    except Exception as e:
        logger.error(f"[AdminStuffRouter] 删除物资失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch-update", summary="批量更新物资")
async def batch_update_stuff(
    request: BatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_admin_auth)
):
    """
    批量更新物资（管理员）。
    支持一次性更新多个物资的信息。
    """
    try:
        logger.info(f"[AdminStuffRouter] 管理员 {admin} 批量更新物资，数量: {len(request.items)}")
        
        update_list = [item.dict() for item in request.items if item.update_data.dict(exclude_unset=True)]
        if not update_list:
            raise ValueError("没有有效的更新数据")
        
        result = await AdminStuffService.batch_update_stuff_admin(db, update_list)
        
        logger.info(f"管理员操作日志 | 操作人: {admin} | 操作: 批量更新 | 数量: {len(update_list)}")
        
        return result
        
    except ValueError as e:
        logger.warning(f"[AdminStuffRouter] 批量更新参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[AdminStuffRouter] 批量更新失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", summary="获取物资统计信息")
async def get_stuff_stats(
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_admin_auth)
):
    """
    获取物资统计信息（管理员）。
    返回物资的总体统计数据。
    """
    try:
        logger.info(f"[AdminStuffRouter] 管理员 {admin} 请求物资统计")
        
        # AdminStuffService.get_all_stuff_admin 内部包含了统计计算
        result = await AdminStuffService.get_all_stuff_admin(db)
        
        if result['code'] == 200:
            stats_data = {
                "code": 200,
                "message": "获取统计信息成功",
                "data": {
                    "stats": result['data']['stats'],
                    "type_stats": result['data']['type_stats']
                }
            }
            return stats_data
        else:
            return result
        
    except Exception as e:
        logger.error(f"[AdminStuffRouter] 获取统计信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# TODO: 此路由依赖于StuffBorrow模型的服务层逻辑，将在迁移StuffBorrow模块后恢复。
# 我们将暂时注释掉它，以确保当前模块可以独立运行和测试。
# @router.get("/detail/{stuff_id}")
# async def get_stuff_detail(
#     stuff_id: str,
#     admin: str = Depends(get_admin_auth)
# ):
#     """
#     获取物资详情（管理员）
    
#     返回单个物资的完整信息，包括借用历史
#     """
#     try:
#         logger.info(f"[AdminStuffRouter] 管理员 {admin} 查看物资详情: {stuff_id}")
        
#         from app.models.stuff import Stuff
#         from app.models.stuff_borrow import StuffBorrow
        
#         # 查找物资
#         stuff = Stuff.objects(stuff_id=stuff_id).first()
#         if not stuff:
#             raise ValueError(f"物资不存在: {stuff_id}")
        
#         # 获取相关的借用记录
#         borrow_records = []
#         all_borrows = StuffBorrow.objects()
        
#         for borrow in all_borrows:
#             # 检查借用列表中是否包含此物资
#             for item in borrow.stuff_list:
#                 if stuff.stuff_name in item.get('stuff', ''):
#                     borrow_records.append({
#                         'sb_id': borrow.sb_id,
#                         'borrower': borrow.name,
#                         'start_time': borrow.start_time.isoformat() if borrow.start_time else None,
#                         'deadline': borrow.deadline.isoformat() if borrow.deadline else None,
#                         'state': borrow.state,
#                         'state_text': ['未审核', '被打回', '通过未归还', '已归还'][borrow.state]
#                     })
#                     break
        
#         # 构建响应
#         detail = stuff.to_dict(include_admin_fields=True)
#         detail['borrow_history'] = borrow_records
#         detail['borrow_count'] = len(borrow_records)
        
#         return {
#             "code": 200,
#             "message": "获取物资详情成功",
#             "data": detail
#         }
        
#     except ValueError as e:
#         logger.warning(f"[AdminStuffRouter] 获取物资详情失败: {str(e)}")
#         raise HTTPException(status_code=404, detail=str(e))
#     except Exception as e:
#         logger.error(f"[AdminStuffRouter] 获取物资详情失败: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))