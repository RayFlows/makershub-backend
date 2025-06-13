from app.models.event import Event
from app.core.db import minio_client
from loguru import logger
from fastapi import HTTPException
from datetime import datetime
from app.core.utils import parse_datetime
from io import BytesIO

class EventService:
    """事件服务类：处理事件相关的业务逻辑"""
    
    async def update_event_poster(self, event_id: str, file_data: bytes) -> bool:
        """更新事件海报"""
        logger.info(f"🔧 开始更新海报 | 事件ID: {event_id} | 文件大小: {len(file_data)}字节")
        try:
            # 查找事件
            event = Event.objects(event_id=event_id).first()
            if not event:
                raise HTTPException(status_code=404, detail="事件不存在")

            # 检查是否已有海报 - 避免重复上传
            if event.poster:
                logger.warning(f"事件 {event_id} 已有海报，将被覆盖")
            
            # 上传海报到MinIO
            file_name = f"poster_{event_id}.jpg"
            logger.debug(f"准备上传到MinIO | 桶类型: POSTERS")
            result = minio_client.upload_file(
                file_data=file_data,
                file_path=file_name,
                content_type="image/jpeg",
                bucket_type="POSTERS"
            )
            
            if not result:
                logger.error(f"MinIO上传失败 | 桶: {bucket_type} | 文件名: {file_name}")
                raise HTTPException(status_code=500, detail="海报上传失败")
            
            # 更新事件海报URL
            # event.poster = minio_client.get_file(
            #     file_name, 
            #     expire_seconds=3600,
            #     # bucket_type="POSTERS"
            #     bucket_type="poster"
            # )["url"]
            url_result = minio_client.get_file(
                file_name, 
                expire_seconds=3600,
                bucket_type="POSTERS"
            )
            poster_url = url_result.get("url", "")  # 仅提取URL字符串
            
            event.poster = poster_url
            # 检查是否已完成所有上传
            if event.poster and event.event_name:
                event.is_completed = 1
                
            if not isinstance(event.poster, str):
                logger.error(f"无效的海报URL类型: {type(event.poster)}")
                event.poster = ""    
            event.save()
            return poster_url

        except Exception as e:
            logger.error(f"更新海报失败: {str(e)}")
            raise HTTPException(status_code=500, detail="更新海报失败")
        except ConnectionError as e:
            logger.error(f"MinIO连接失败: {str(e)}")
            raise HTTPException(status_code=503, detail="存储服务不可用")
    
    async def update_event_details(self, event_id: str, event_data: dict) -> Event:
        """更新事件详细信息"""
        try:
            # 查找事件
            event = Event.objects(event_id=event_id).first()
            if not event:
                raise HTTPException(status_code=404, detail="事件不存在")
            
            # 更新事件信息
            event.event_name = event_data["event_name"]
            event.description = event_data["description"]
            event.participant = event_data.get("participant", "允许全体成员")
            event.location = event_data["location"]
            event.link = event_data["link"]
            event.start_time = event_data["start_time"]
            event.end_time = event_data["end_time"]
            event.registration_deadline = event_data["registration_deadline"]
            
            # 检查是否已完成所有上传
            if event.poster and event.event_name:
                event.is_completed = 1
                
            event.save()
            return event
        except Exception as e:
            logger.error(f"更新事件失败: {str(e)}")
            raise HTTPException(status_code=500, detail="更新事件失败")

    async def get_upcoming_events(self, current_time: str) -> list:
        """
        获取未开展的所有活动
        
        未开展指的是活动的开始时间(start_time)晚于当前时间
        
        Args:
            current_time: 当前时间(ISO 8601格式)
            
        Returns:
            list: 包含活动信息的列表
        """
        try:
            logger.info(f"查询未开展活动 | 当前时间: {current_time}")
            
            # 查询条件：活动已标记完成(is_completed=1)且开始时间大于当前时间
            events = Event.objects(
                is_completed=1,
                start_time__gt=current_time
            ).only(
                "event_id", 
                "event_name", 
                "poster", 
                "start_time"
            )
            
            # 转换为字典列表
            event_list = []
            for event in events:
                event_list.append({
                    "event_id": event.event_id,
                    "event_name": event.event_name,
                    "poster": event.poster,
                    "start_time": event.start_time
                })
            
            logger.info(f"找到 {len(event_list)} 个未开展活动")
            return event_list
        except Exception as e:
            logger.error(f"查询未开展活动失败: {str(e)}")
            raise HTTPException(status_code=500, detail="查询活动失败")

    # 获取活动详情的方法
    async def get_event_details(self, event_id: str) -> dict:
        """
        获取特定活动的详情
        
        Args:
            event_id: 活动ID
            
        Returns:
            dict: 包含活动详情的字典，如果活动不存在则返回None
        """
        try:
            logger.info(f"查询活动详情 | 活动ID: {event_id}")
            
            # 查询活动记录
            event = Event.objects(event_id=event_id).first()
            
            # 如果活动不存在，返回None
            if not event:
                logger.warning(f"活动不存在 | 活动ID: {event_id}")
                return None
            
            # 转换为字典并返回
            event_dict = {
                "event_id": event.event_id,
                "event_name": event.event_name,
                "poster": event.poster,
                "description": event.description,
                "participant": event.participant,
                "location": event.location,
                "link": event.link,
                "start_time": event.start_time,
                "end_time": event.end_time,
                "registration_deadline": event.registration_deadline
            }
            
            logger.info(f"成功获取活动详情 | 活动ID: {event_id}")
            return event_dict
        except Exception as e:
            logger.error(f"查询活动详情失败: {str(e)}")
            raise HTTPException(status_code=500, detail="查询活动详情失败")
    
    async def cleanup_incomplete_events(self):
        """清理未完成的事件（5分钟未完成）"""
        try:
            from datetime import datetime, timedelta
            # 计算5分钟前的时间
            five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
            
            # 查找未完成且超过5分钟的事件
            incomplete_events = Event.objects(
                is_completed=0,
                created_at__lte=five_minutes_ago
            )
            
            # 删除这些事件
            for event in incomplete_events:
                event.delete()
                logger.info(f"已清理未完成事件: {event.event_id}")
                
            return {"cleaned": incomplete_events.count()}
        except Exception as e:
            logger.error(f"清理未完成事件失败: {str(e)}")
            return {"error": str(e)}