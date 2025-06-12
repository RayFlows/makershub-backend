from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from app.services.event_service import EventService
from app.core.auth import require_permission_level
from app.models.event import Event
from app.core.config import settings
from app.core.utils import parse_datetime
from loguru import logger
import asyncio
from datetime import datetime

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