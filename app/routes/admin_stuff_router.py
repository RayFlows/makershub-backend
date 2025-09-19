# app/routes/admin_stuff_router.py
"""
管理员物资路由模块
提供管理员端的物资管理API接口，包含完整的CRUD操作和批量操作
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.core.logging import logger
from app.core.admin_auth import verify_admin_token
from app.services.admin_stuff_service import AdminStuffService

router = APIRouter()

# ========== 请求模型定义 ==========

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
    
    class Config:
        schema_extra = {
            "example": {
                "type": "开发板",
                "stuff_name": "Arduino UNO R3",
                "number_total": 10,
                "number_remain": 10,
                "description": "Arduino开发板，适合初学者使用",
                "location": "i创街",
                "cabinet": "A",
                "layer": 2
            }
        }

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

# ========== 认证依赖 ==========

from fastapi import Header

async def get_admin_auth(authorization: Optional[str] = Header(None)):
    """
    验证管理员token
    从Header中获取Authorization并验证
    """
    if not authorization:
        logger.warning("[AdminStuffRouter] 未提供认证token")
        raise HTTPException(status_code=401, detail="未提供认证token")
    
    # 移除 "Bearer " 前缀
    token = authorization.replace("Bearer ", "")
    
    # 使用管理员认证验证token
    username = verify_admin_token(token)
    
    if not username:
        logger.warning("[AdminStuffRouter] 无效的认证token")
        raise HTTPException(status_code=401, detail="无效的认证token")
    
    logger.debug(f"[AdminStuffRouter] 管理员认证成功: {username}")
    return username

# ========== API路由 ==========

@router.get("/list")
async def get_stuff_list(
    admin: str = Depends(get_admin_auth),
    type: Optional[str] = Query(None, description="物资类型"),
    location: Optional[str] = Query(None, description="所在场地"),
    cabinet: Optional[str] = Query(None, description="展柜位置"),
    layer: Optional[int] = Query(None, description="层数"),
    search: Optional[str] = Query(None, description="搜索关键词")
):
    """
    获取物资列表（管理员）
    
    支持多条件筛选，返回包含扩展字段的完整物资信息
    """
    try:
        logger.info(f"[AdminStuffRouter] 管理员 {admin} 请求物资列表")
        
        # 构建筛选条件
        filters = {}
        if type:
            filters['type'] = type
        if location:
            filters['location'] = location
        if cabinet:
            filters['cabinet'] = cabinet
        if layer is not None:
            filters['layer'] = layer
        if search:
            filters['search'] = search
        
        result = AdminStuffService.get_all_stuff_admin(filters)
        return result
        
    except Exception as e:
        logger.error(f"[AdminStuffRouter] 获取物资列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create")
async def create_stuff(
    request: StuffCreateRequest,
    admin: str = Depends(get_admin_auth)
):
    """
    创建新物资（管理员）
    
    创建包含位置信息的完整物资记录
    """
    try:
        logger.info(f"[AdminStuffRouter] 管理员 {admin} 创建物资: {request.stuff_name}")
        
        result = AdminStuffService.create_stuff_admin(request.dict())
        
        # 记录操作日志
        logger.info(f"管理员操作日志 | 操作人: {admin} | 操作: 创建物资 | "
                   f"物资: {request.stuff_name} | 位置: {request.location}-{request.cabinet}-{request.layer}")
        
        return result
        
    except ValueError as e:
        logger.warning(f"[AdminStuffRouter] 创建物资参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[AdminStuffRouter] 创建物资失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/update/{stuff_id}")
async def update_stuff(
    stuff_id: str,
    request: StuffUpdateRequest,
    admin: str = Depends(get_admin_auth)
):
    """
    更新物资信息（管理员）
    
    支持部分更新，只更新提供的字段
    """
    try:
        logger.info(f"[AdminStuffRouter] 管理员 {admin} 更新物资: {stuff_id}")
        
        # 过滤掉None值，只更新提供的字段
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        
        if not update_data:
            raise ValueError("没有提供要更新的数据")
        
        result = AdminStuffService.update_stuff_admin(stuff_id, update_data)
        
        # 记录操作日志
        logger.info(f"管理员操作日志 | 操作人: {admin} | 操作: 更新物资 | "
                   f"物资ID: {stuff_id} | 更新字段: {list(update_data.keys())}")
        
        return result
        
    except ValueError as e:
        logger.warning(f"[AdminStuffRouter] 更新物资参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[AdminStuffRouter] 更新物资失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete/{stuff_id}")
async def delete_stuff(
    stuff_id: str,
    admin: str = Depends(get_admin_auth)
):
    """
    删除物资（管理员）
    
    只有当物资全部归还时才能删除
    """
    try:
        logger.info(f"[AdminStuffRouter] 管理员 {admin} 删除物资: {stuff_id}")
        
        result = AdminStuffService.delete_stuff_admin(stuff_id)
        
        # 记录操作日志
        logger.info(f"管理员操作日志 | 操作人: {admin} | 操作: 删除物资 | 物资ID: {stuff_id}")
        
        return result
        
    except ValueError as e:
        logger.warning(f"[AdminStuffRouter] 删除物资失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[AdminStuffRouter] 删除物资失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch-update")
async def batch_update_stuff(
    request: BatchUpdateRequest,
    admin: str = Depends(get_admin_auth)
):
    """
    批量更新物资（管理员）
    
    支持一次性更新多个物资的信息
    """
    try:
        logger.info(f"[AdminStuffRouter] 管理员 {admin} 批量更新物资，数量: {len(request.items)}")
        
        # 转换请求数据格式
        update_list = []
        for item in request.items:
            update_data = {k: v for k, v in item.update_data.dict().items() if v is not None}
            if update_data:  # 只添加有更新内容的项
                update_list.append({
                    'stuff_id': item.stuff_id,
                    'update_data': update_data
                })
        
        if not update_list:
            raise ValueError("没有有效的更新数据")
        
        result = AdminStuffService.batch_update_stuff_admin(update_list)
        
        # 记录操作日志
        logger.info(f"管理员操作日志 | 操作人: {admin} | 操作: 批量更新 | 数量: {len(update_list)}")
        
        return result
        
    except ValueError as e:
        logger.warning(f"[AdminStuffRouter] 批量更新参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[AdminStuffRouter] 批量更新失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_stuff_stats(
    admin: str = Depends(get_admin_auth)
):
    """
    获取物资统计信息（管理员）
    
    返回物资的总体统计数据
    """
    try:
        logger.info(f"[AdminStuffRouter] 管理员 {admin} 请求物资统计")
        
        # 获取所有物资以计算统计
        result = AdminStuffService.get_all_stuff_admin()
        
        # 提取统计信息
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
        logger.error(f"[AdminStuffRouter] 获取统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/detail/{stuff_id}")
async def get_stuff_detail(
    stuff_id: str,
    admin: str = Depends(get_admin_auth)
):
    """
    获取物资详情（管理员）
    
    返回单个物资的完整信息，包括借用历史
    """
    try:
        logger.info(f"[AdminStuffRouter] 管理员 {admin} 查看物资详情: {stuff_id}")
        
        from app.models.stuff import Stuff
        from app.models.stuff_borrow import StuffBorrow
        
        # 查找物资
        stuff = Stuff.objects(stuff_id=stuff_id).first()
        if not stuff:
            raise ValueError(f"物资不存在: {stuff_id}")
        
        # 获取相关的借用记录
        borrow_records = []
        all_borrows = StuffBorrow.objects()
        
        for borrow in all_borrows:
            # 检查借用列表中是否包含此物资
            for item in borrow.stuff_list:
                if stuff.stuff_name in item.get('stuff', ''):
                    borrow_records.append({
                        'sb_id': borrow.sb_id,
                        'borrower': borrow.name,
                        'start_time': borrow.start_time.isoformat() if borrow.start_time else None,
                        'deadline': borrow.deadline.isoformat() if borrow.deadline else None,
                        'state': borrow.state,
                        'state_text': ['未审核', '被打回', '通过未归还', '已归还'][borrow.state]
                    })
                    break
        
        # 构建响应
        detail = stuff.to_dict(include_admin_fields=True)
        detail['borrow_history'] = borrow_records
        detail['borrow_count'] = len(borrow_records)
        
        return {
            "code": 200,
            "message": "获取物资详情成功",
            "data": detail
        }
        
    except ValueError as e:
        logger.warning(f"[AdminStuffRouter] 获取物资详情失败: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[AdminStuffRouter] 获取物资详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))