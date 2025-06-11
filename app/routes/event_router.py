from fastapi import APIRouter, Request, Depends, HTTPException, status
from app.models.event import Event
from app.models.user import User
from app.services.event_service import EventService
from app.core.auth import AuthMiddleware, require_admin
from typing import Dict
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/post", response_model=Dict)
async def post_event(
    request: Request,
    event_data: Dict = None,
    current_user: User = Depends(require_admin)
):
    """
    创建新活动
    
    权限要求: 管理员(1)或超级管理员(2)
    
    Request Body 示例:
    {
      "event_name": "活动名称",
      "description": "活动描述",
      "location": "活动地点",
      "link": "https://example.com",
      "start_time": "2024-05-01T09:00:00Z",
      "end_time": "2024-05-01T17:00:00Z",
      "registration_deadline": "2024-04-25T23:59:59Z"
    }
    """
    # 验证请求类型是否为JSON
    if request.headers.get("content-type") != "application/json":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 400,
                "message": "expect json, receiving others"
            }
        )
    
    # 验证核心字段是否存在
    required_fields = ['event_name', 'description', 'location', 
                       'start_time', 'end_time', 'registration_deadline']
    for field in required_fields:
        if field not in event_data:
            raise HTTPException(
                status_code=400,
                detail=f"缺少必填字段: {field}"
            )
    
    # 使用服务层创建活动
    result = await EventService.create_event(event_data, current_user)
    return {
        "code": 200,
        "message": "successfully create new activity",
        "data": result
    }
