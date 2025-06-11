from app.models.event import Event
from app.models.user import User
from datetime import datetime
import logging
from app.core.auth import require_admin, require_super
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

class EventService:
    @staticmethod
    async def create_event(event_data: dict, creator: User) -> dict:
        """
        创建新活动
        
        Args:
            event_data: 活动数据字典
            creator: 创建者User实例
            
        Returns:
            包含事件ID的字典
            
        Raises:
            HTTPException: 无效时间格式时抛出
        """
        try:
            # 验证时间格式
            time_fields = ['start_time', 'end_time', 'registration_deadline']
            validated_data = {}
            for field in time_fields:
                try:
                    validated_data[field] = datetime.fromisoformat(event_data[field])
                except (TypeError, ValueError):
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "code": 400,
                            "message": "wrong format of time",
                            "data": {
                                "target": f"request.body.{field}",
                                "expected": "ISO8601 format",
                                "actual": event_data.get(field)
                            }
                        }
                    )
            
            # 生成唯一活动ID（EV + YYYYMMDD + 3位序号）
            today = datetime.utcnow().strftime("%Y%m%d")
            last_event = Event.objects().order_by('-event_id').first()
            sequence = 1 if not last_event else int(last_event.event_id[10:]) + 1
            event_id = f"EV{today}{sequence:03d}"
            
            # 创建活动实例
            new_event = Event(
                event_id=event_id,
                event_name=event_data['event_name'],
                description=event_data['description'],
                location=event_data['location'],
                link=event_data.get('link', ''),
                created_by=creator,
                last_modified_by=creator,
                **validated_data
            )
            new_event.save()
            
            logger.info(f"活动创建成功: {event_id} - {event_data['event_name']}")
            return {"event_id": event_id}
            
        except Exception as e:
            logger.error(f"创建活动失败: {e}")
            raise HTTPException(status_code=500, detail="创建活动时发生内部错误")
