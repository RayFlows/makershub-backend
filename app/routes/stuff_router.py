# app/routes/stuff_router.py
"""
物资路由模块（小程序端）
提供面向小程序用户的物资查询和（未来可能的）其他操作接口。
[v2.0 SQLAlchemy 迁移版]
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from pydantic import BaseModel
from loguru import logger

from app.core.auth import require_permission_level
from app.services.stuff_service import StuffService
from app.core.database import get_db
from app.models.user import User # 导入User模型用于依赖注入

router = APIRouter()
stuff_service = StuffService()

# --- Pydantic 模型定义 (与旧版本完全兼容) ---
class StuffDetail(BaseModel):
    stuff_name: str
    number_remain: int
    description: str

class StuffType(BaseModel):
    type: str
    details: List[StuffDetail]

class AddStuffRequest(BaseModel):
    types: List[StuffType]

@router.get("/get-all", summary="获取所有物资列表（分组）")
async def get_all_stuff(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission_level(0)) # 允许所有已登录用户
):
    """
    获取所有物资，并按类型进行分组返回。
    
    Args:
        db: 数据库会话依赖。
        user: 当前认证通过的用户对象，用于权限检查。
        
    Returns:
        Dict: 按类型分组的物资列表。
    """
    try:
        logger.info(f"用户 {user.userid} 请求获取所有物资列表。")
        # 调用重构后的服务方法，并传入db会话
        result = await stuff_service.get_all_stuff_grouped_by_type(db)
        return result
    except Exception as e:
        logger.error(f"获取物资列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add", summary="批量添加物资（测试用）")
async def add_stuff(
    request: AddStuffRequest,
    db: AsyncSession = Depends(get_db)
    # user: User = Depends(require_permission_level(1)) # 权限暂时注释，方便测试
):
    """
    批量添加多种类型的物资。
    
    Args:
        request: 包含待添加物资信息的请求体。
        db: 数据库会话依赖。
        
    Returns:
        Dict: 添加操作的结果。
    """
    try:
        # 将Pydantic模型转换为字典列表 (业务逻辑不变)
        types_data = [t.dict() for t in request.types]
        logger.info(f"收到批量添加物资请求，共 {len(types_data)} 个类型。")
        
        # 调用重构后的服务方法，并传入db会话
        result = await stuff_service.add_stuff_batch(db, types_data)
        return result
    except ValueError as e:
        logger.warning(f"添加物资参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"添加物资失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))