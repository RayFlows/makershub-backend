# app/routes/arrange_router.py
"""
排班安排路由模块 (Arrange Router Module)
本模块负责处理小程序端与学年工作排班相关的API路由。
[v0.2 SQLAlchemy 重构版]
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.services.arrange_service import ArrangeService
from app.core.auth import require_permission_level
from app.core.database import get_db

router = APIRouter()

# --- API Endpoints ---

@router.get("/get-arrangement", summary="获取所有排班安排", dependencies=[Depends(require_permission_level(1))])
async def get_arrangements(db: AsyncSession = Depends(get_db)):
    """获取所有任务类型的排班安排，按类型分组。"""
    try:
        service = ArrangeService()
        logger.info("路由层: 正在请求所有排班安排...")
        arrangements = await service.get_all_arrangements(db)
        logger.info("路由层: 成功获取排班安排。")
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
        logger.info("路由层: 正在请求当前所有值班人员...")
        current_makers = await service.get_current_makers(db)
        logger.info("路由层: 成功获取当前值班人员。")
        return {
            "code": 200,
            "message": "successfully get current maker",
            "data": current_makers
        }
    except Exception as e:
        logger.error(f"获取当前值班人员失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取当前值班人员失败")