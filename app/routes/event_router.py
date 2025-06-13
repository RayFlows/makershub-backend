from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from app.services.event_service import EventService
from app.core.auth import require_permission_level
from app.models.event import Event
from app.core.config import settings
from app.core.utils import parse_datetime
from loguru import logger
import asyncio
from datetime import datetime
import re

router = APIRouter()
event_service = EventService()

# 预创建事件 - 返回event_id
@router.get("/precreate-event")
async def precreate_event():
    """
    预创建事件，返回生成的event_id
    前端应使用此event_id上传表单和海报
    """
    try:
        # 创建只包含event_id的事件记录
        event_id = Event.generate_event_id()
        event = Event(event_id=event_id)
        event.save()
        
        logger.info(f"预创建事件成功: {event.event_id}")
        return {
            "code": 200,
            "event_id": event.event_id
        }
    except Exception as e:
        logger.error(f"预创建事件失败: {str(e)}")
        raise HTTPException(status_code=500, detail="预创建事件失败")

# 发布事件详情
@router.post("/post/{event_id}")
async def post_event(
    event_id: str, 
    event_data: dict,
    user: dict = Depends(require_permission_level(1))  # 需要权限1或2
):
    """
    发布事件详细信息
    使用预先生成的event_id
    """
    try:
        # 验证时间格式
        for time_field in ["start_time", "end_time", "registration_deadline"]:
            if not parse_datetime(event_data.get(time_field, "")):
                raise HTTPException(
                    status_code=400,
                    detail=f"时间格式错误: {time_field}"
                )
        
        # 更新事件详情
        event = await event_service.update_event_details(event_id, event_data)
        return {
            "code": 200,
            "message": "活动创建成功",
            "data": {"event_id": event.event_id}
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"发布事件失败: {str(e)}")
        raise HTTPException(status_code=500, detail="发布事件失败")

# 上传海报
@router.post("/poster/{event_id}")
async def upload_poster(
    event_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(require_permission_level(1))  # 需要权限1或2
):
    """
    上传事件海报
    使用预先生成的event_id
    """
    logger.info(f"▶️ 开始处理海报上传 | 事件ID: {event_id}")
    try:
        # 读取文件内容
        contents = await file.read()
        logger.info(f"📁 文件已读取 | 大小: {len(contents)}字节")

        # 获取上传后的海报URL
        poster_url = await event_service.update_event_poster(event_id, contents)
        logger.debug(f"传回的url：{poster_url}")

        # 更新事件海报
        await event_service.update_event_poster(event_id, contents)
        return {
            "code": 200,
            "message": "海报上传成功",
            "data": {"poster": poster_url}
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"上传海报失败: {str(e)}")
        raise HTTPException(status_code=500, detail="上传海报失败")

# 获取未开展活动列表
@router.get("/view")
async def get_upcoming_events(
    user: dict = Depends(require_permission_level(0))  # 允许权限0,1,2
):
    """
    获取未开展的所有活动列表
    
    未开展指的是活动的开始时间(start_time)晚于当前时间
    """
    try:
        # 获取当前UTC时间
        current_time = datetime.utcnow().isoformat() + "Z"
        logger.info(f"获取未开展活动列表 | 当前时间: {current_time}")
        
        # 调用服务层获取活动列表
        events = await event_service.get_upcoming_events(current_time)
        
        return {
            "code": 200,
            "message": "successfully get event-list",
            "data": {
                "total": len(events),
                "events": events
            }
        }
    except Exception as e:
        logger.error(f"获取活动列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取活动列表失败")

# 获取特定活动详情
@router.get("/details/{event_id}")
async def get_event_details(
    event_id: str,
    user: dict = Depends(require_permission_level(0))  # 允许权限0,1,2
):
    """
    获取特定活动的详情
    
    Args:
        event_id: 活动ID，格式为EV开头加时间戳
        
    Returns:
        活动详情信息
    """
    try:
        # 验证event_id格式
        if not re.match(r'^EV\d+_\d{3}$', event_id):
            return {
                "code": 400,
                "message": "wrong event_id format",
                "data": {
                    "target": "request.params.event_id",
                    "expected": "EV%Y%M%D%hh%mmxxx",
                    "actual": event_id
                }
            }
        
        # 调用服务层获取活动详情
        event = await event_service.get_event_details(event_id)
        
        if not event:
            return {
                "code": 404,
                "message": "record does not exist"
            }
        
        return {
            "code": 200,
            "message": "successfully get event-detail",
            "data": event
        }
    except Exception as e:
        logger.error(f"获取活动详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取活动详情失败")