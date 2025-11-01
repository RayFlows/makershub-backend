# app/routes/event_router.py
"""
活动路由模块 (Event Router Module)
本模块负责处理所有与活动相关的API路由，包括活动的创建、信息更新、海报上传和列表查看。
[v2.0 SQLAlchemy 迁移版]
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime
from loguru import logger
import re

from app.services.event_service import EventService
from app.core.auth import require_permission_level
from app.models.user import User
from app.core.database import get_db
from app.core.storage import minio_client

router = APIRouter()
event_service = EventService()

# --- Pydantic Schemas for Request Validation ---

class EventDetailsPayload(BaseModel):
    event_name: str = Field(..., min_length=1, max_length=100, description="活动名称")
    description: str = Field(..., description="活动详细描述")
    participant: Optional[str] = Field("允许全体成员", max_length=100, description="参与对象")
    location: str = Field(..., max_length=100, description="活动地点")
    link: Optional[str] = Field(None, description="相关链接（如报名问卷）")
    # Pydantic 的 `HttpUrl` 类型非常严格，它要求值必须是一个包含协议方案（如 `http://` 或 `https://`）的完整 URL。
    # link: Optional[HttpUrl] = Field(None, description="相关链接（如报名问卷）")
    start_time: str = Field(..., description="活动开始时间 (ISO 8601格式, e.g., '2023-10-27T10:00:00+08:00')")
    end_time: str = Field(..., description="活动结束时间 (ISO 8601格式)")
    registration_deadline: str = Field(..., description="报名截止时间 (ISO 8601格式)")

# --- API Endpoints ---

@router.get("/precreate-event",
    summary="预创建活动",
    description="为前端创建一个临时的活动条目，并返回一个唯一的event_id。前端后续应使用此ID上传活动详情和海报。",
    dependencies=[Depends(require_permission_level(1))] # 权限：干事及以上
)
async def precreate_event(db: AsyncSession = Depends(get_db)):
    """
    预创建事件，返回生成的event_id。
    """
    try:
        logger.info("接收到预创建活动请求")
        new_event = await event_service.precreate_event(db)
        logger.success(f"活动预创建成功: {new_event.event_id}")
        return {
            "code": 200,
            "message": "活动预创建成功",
            "event_id": new_event.event_id
        }
    except Exception as e:
        logger.error(f"预创建活动失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误，预创建活动失败")

@router.post("/post/{event_id}",
    summary="发布或更新活动详情",
    dependencies=[Depends(require_permission_level(1))] # 权限：干事及以上
)
async def post_event(
    event_id: str, 
    event_data: EventDetailsPayload,
    db: AsyncSession = Depends(get_db)
):
    """
    发布或更新活动的详细文本信息。
    """
    try:
        logger.info(f"接收到更新活动详情请求: {event_id}")
        event = await event_service.update_event_details(db, event_id, event_data.dict())
        if not event:
            logger.warning(f"更新活动详情失败，未找到活动: {event_id}")
            raise HTTPException(status_code=404, detail=f"Event with id {event_id} not found")
        
        logger.success(f"活动详情更新成功: {event_id}")
        return {
            "code": 200,
            "message": "活动详情更新成功",
            "data": {"event_id": event.event_id}
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"更新活动详情时发生未知错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.post("/poster/{event_id}",
    summary="上传活动海报",
    dependencies=[Depends(require_permission_level(1))] # 权限：干事及以上
)
async def upload_poster(
    event_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    上传活动海报，并将其与指定event_id的活动关联。
    """
    logger.info(f"接收到海报上传请求: {event_id}")
    try:
        contents = await file.read()
        if not contents:
             raise HTTPException(status_code=400, detail="上传的文件为空")
        
        logger.debug(f"文件已读取，大小: {len(contents)}字节，准备调用服务层")
        poster_object_name = await event_service.update_event_poster(db, event_id, contents)
        
        if poster_object_name is None:
             raise HTTPException(status_code=404, detail=f"Event with id {event_id} not found")
        
        # 获取刚上传文件的可访问URL
        url_result = minio_client.get_file(poster_object_name, bucket_type="POSTERS")
        poster_url = url_result.get("url", "")
        if not poster_url:
            logger.error(f"海报上传成功但获取URL失败: {poster_object_name}")
            raise HTTPException(status_code=500, detail="海报处理失败")

        logger.success(f"海报上传并更新记录成功: {event_id}")
        return {
            "code": 200,
            "message": "海报上传成功",
            "data": {"poster": poster_url}
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"上传海报失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="上传海报时发生服务器内部错误")

@router.get("/view",
    summary="获取未开展的活动列表",
    dependencies=[Depends(require_permission_level(0))] # 权限：所有登录用户
)
async def get_upcoming_events(db: AsyncSession = Depends(get_db)):
    """
    获取所有即将开始的活动列表。
    """
    try:
        # 获取当前带时区的时间
        current_time = datetime.now().astimezone()
        logger.info(f"获取未开展活动列表 | 当前时间: {current_time.isoformat()}")
        
        events = await event_service.get_upcoming_events(db, current_time)
        
        return {
            "code": 200,
            "message": "successfully get event-list",
            "data": {
                "total": len(events),
                "events": events
            }
        }
    except Exception as e:
        logger.error(f"获取活动列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取活动列表失败")

@router.get("/details/{event_id}",
    summary="获取特定活动详情",
    dependencies=[Depends(require_permission_level(0))] # 权限：所有登录用户
)
async def get_event_details(event_id: str, db: AsyncSession = Depends(get_db)):
    """
    根据event_id获取单个活动的详细信息。
    """
    try:
        # 简单的格式验证
        if not re.match(r'^EV\d+_\d{3}$', event_id):
            logger.warning(f"收到格式错误的event_id: {event_id}")
            raise HTTPException(status_code=400, detail="无效的event_id格式")
        
        logger.info(f"查询活动详情: {event_id}")
        event_orm = await event_service.get_event_orm_by_id(db, event_id)
        
        if not event_orm:
            logger.warning(f"未找到活动: {event_id}")
            raise HTTPException(status_code=404, detail="活动不存在")
        
        # 序列化并获取海报URL
        event_dict = event_service._event_to_dict(event_orm, with_poster_url=True)
        
        return {
            "code": 200,
            "message": "successfully get event-detail",
            "data": event_dict
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"获取活动详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取活动详情失败")