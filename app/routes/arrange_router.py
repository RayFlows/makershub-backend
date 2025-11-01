# app/routes/arrange_router.py
"""
排班安排路由模块 (Arrange Router Module)
本模块负责处理所有与学年工作排班相关的API路由。
[v2.0 SQLAlchemy 迁移版]
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from pydantic import BaseModel
from typing import Dict, List, Any

from app.services.arrange_service import ArrangeService
from app.core.auth import require_permission_level
from app.core.database import get_db
from app.models.user import User

router = APIRouter()

# --- Pydantic Schemas for Request Validation ---

class ArrangePerson(BaseModel):
    name: str
    order: int
    current: bool
    maker_id: str

class BatchArrangeRequest(BaseModel):
    # 使用 Pydantic 的 Dict 类型进行更严格的验证
    __root__: Dict[str, List[ArrangePerson]]

# --- API Endpoints ---

@router.get("/get-arrangement", summary="获取所有排班安排", dependencies=[Depends(require_permission_level(1))])
async def get_arrangements(db: AsyncSession = Depends(get_db)):
    """获取所有任务类型的排班安排，按类型分组。"""
    try:
        service = ArrangeService()
        arrangements = await service.get_all_arrangements(db)
        return {
            "code": 200,
            "message": "successfully get all arrangements",
            "data": arrangements
        }
    except Exception as e:
        logger.error(f"获取排班安排失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取排班安排失败")

@router.get("/get-current", summary="获取当前所有值班人员", dependencies=[Depends(require_permission_level(1))])
async def get_current_arrangers(db: AsyncSession = Depends(get_db)):
    """获取宣传部三个任务当前轮到的值班人员信息。"""
    try:
        service = ArrangeService()
        current_makers = await service.get_current_makers(db)
        return {
            "code": 200,
            "message": "successfully get current maker",
            "data": current_makers
        }
    except Exception as e:
        logger.error(f"获取当前值班人员失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取当前值班人员失败")

@router.post("/arrangements/batch", summary="批量创建/重置排班安排")
async def batch_create_arrangements(
    # 使用 Pydantic 模型进行验证，而不是原始字典
    request_data: BatchArrangeRequest,
    # TODO: 生产环境中应启用权限检查
    # user: User = Depends(require_permission_level(2)),
    db: AsyncSession = Depends(get_db)
):
    """
    (管理员权限) 批量创建或重置所有任务类型的排班安排。
    此操作会先清空所有旧的排班数据，然后插入新的数据，整个过程是原子性的。
    """
    try:
        service = ArrangeService()
        # Pydantic 模型会自动解析 __root__，所以我们直接传入 request_data.dict()['__root__']
        validated_data = request_data.dict()['__root__']
        
        # 验证 task_type key 是否为 "1", "2", "3"
        valid_keys = {"1", "2", "3"}
        if not set(validated_data.keys()).issubset(valid_keys):
            raise HTTPException(status_code=400, detail="请求数据中包含无效的任务类型键。只接受 '1', '2', '3'。")

        result = await service.batch_create_arrangements(db, validated_data)
        
        return {
            "code": 200,
            "message": "successfully batch create arrangements",
            "data": result
        }
    except Exception as e:
        logger.error(f"批量创建排班失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="批量创建排班失败")