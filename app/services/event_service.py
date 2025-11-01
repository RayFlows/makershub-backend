# app/services/event_service.py
"""
活动服务类：处理与活动相关的所有业务逻辑
[v2.0 SQLAlchemy 迁移版]
"""
from typing import Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from datetime import datetime, timedelta
import random
from dateutil import parser

from app.models.event import Event
from app.core.storage import minio_client

class EventService:
    """
    活动服务类，封装了所有面向小程序用户的活动相关业务逻辑。
    所有方法都接收一个AsyncSession对象来执行数据库操作。
    """
    
    @staticmethod
    def _generate_event_id() -> str:
        """
        生成全局唯一的事件ID。
        格式: EV + 当前时间戳(YYYYMMDDHHMMSSms) + 3位随机数。
        
        Returns:
            str: 生成的唯一事件ID。
        """
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d%H%M%S%f")[:-3]
        random_suffix = f"{random.randint(0, 999):03d}"
        return f"EV{timestamp}_{random_suffix}"

    def _event_to_dict(self, event: Event, with_poster_url: bool = False) -> Optional[dict]:
        """
        辅助函数：将SQLAlchemy Event ORM对象安全地转换为字典。
        用于API响应序列化，以保持与旧接口的数据结构兼容。
        
        Args:
            event: SQLAlchemy的Event模型实例。
            with_poster_url: 是否需要将海报对象名转换为可访问的URL。
        
        Returns:
            一个包含活动信息的字典，如果输入为None则返回None。
        """
        if not event:
            return None
        
        poster_value = event.poster
        if with_poster_url and event.poster:
            url_result = minio_client.get_file(event.poster, bucket_type="POSTERS")
            poster_value = url_result.get("url", "")

        return {
            "event_id": event.event_id,
            "event_name": event.event_name,
            "poster": poster_value,
            "description": event.description,
            "participant": event.participant,
            "location": event.location,
            "link": event.link,
            "start_time": event.start_time.isoformat() if event.start_time else None,
            "end_time": event.end_time.isoformat() if event.end_time else None,
            "registration_deadline": event.registration_deadline.isoformat() if event.registration_deadline else None,
            "created_at": event.created_at.isoformat() if event.created_at else None,
            "updated_at": event.updated_at.isoformat() if event.updated_at else None,
            # is_completed 字段是内部状态，通常不需要对外暴露
        }
        
    async def get_event_orm_by_id(self, db: AsyncSession, event_id: str) -> Optional[Event]:
        """
        根据event_id获取活动的ORM实例。
        这是一个内部使用的辅助方法，方便其他服务方法直接获取可操作的ORM对象。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            event_id: 活动的业务ID。
            
        Returns:
            Event ORM实例，如果未找到则返回None。
        """
        stmt = select(Event).where(Event.event_id == event_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def precreate_event(self, db: AsyncSession) -> Event:
        """
        预创建活动，仅在数据库中插入一条包含唯一event_id的记录。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            
        Returns:
            新创建的Event ORM实例。
        """
        try:
            event_id = self._generate_event_id()
            logger.info(f"正在预创建活动，ID: {event_id}")
            
            new_event = Event(event_id=event_id, is_completed=False)
            db.add(new_event)
            # 注意：此处不 commit，由 get_db 依赖项统一处理
            await db.flush() # flush 会将对象发送到数据库并获取ID等默认值，但事务尚未提交
            await db.refresh(new_event)
            
            logger.success(f"活动预创建成功: {event_id}")
            return new_event
        except Exception as e:
            logger.error(f"预创建活动失败: {e}", exc_info=True)
            raise

    async def update_event_details(self, db: AsyncSession, event_id: str, event_data: dict) -> Optional[Event]:
        """
        更新活动的详细文本信息。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            event_id: 要更新的活动的ID。
            event_data: 包含活动新信息的字典。
            
        Returns:
            更新后的Event ORM实例，如果活动不存在则返回None。
        """
        try:
            event = await self.get_event_orm_by_id(db, event_id)
            if not event:
                logger.warning(f"尝试更新一个不存在的活动: {event_id}")
                return None

            logger.info(f"正在更新活动详情: {event_id}")
            # 更新字段
            event.event_name = event_data.get("event_name")
            event.description = event_data.get("description")
            event.participant = event_data.get("participant", "允许全体成员")
            event.location = event_data.get("location")
            event.link = event_data.get("link")

            # 安全地解析和更新时间字段
            for field in ["start_time", "end_time", "registration_deadline"]:
                if time_str := event_data.get(field):
                    setattr(event, field, parser.isoparse(time_str))

            # 如果海报已上传，则将活动标记为已完成
            if event.poster:
                event.is_completed = True
            
            db.add(event)
            await db.flush()
            await db.refresh(event)
            logger.success(f"活动详情更新成功: {event_id}")
            return event
        except Exception as e:
            logger.error(f"更新活动详情失败: {e}", exc_info=True)
            raise

    async def update_event_poster(self, db: AsyncSession, event_id: str, file_data: bytes) -> Optional[str]:
        """
        更新活动海报，上传至MinIO并更新数据库记录。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            event_id: 活动的ID。
            file_data: 海报文件的二进制数据。
            
        Returns:
            上传成功后海报在MinIO中的对象名，如果活动不存在则返回None。
        """
        try:
            event = await self.get_event_orm_by_id(db, event_id)
            if not event:
                logger.warning(f"尝试为不存在的活动上传海报: {event_id}")
                return None
            
            file_name = f"poster_{event_id}.jpg"
            logger.info(f"正在上传海报到MinIO: {file_name}")
            
            minio_client.upload_file(
                file_data=file_data,
                file_path=file_name,
                content_type="image/jpeg",
                bucket_type="POSTERS"
            )
            
            event.poster = file_name
            # 如果活动详情已填写，则将活动标记为已完成
            if event.event_name:
                event.is_completed = True

            db.add(event)
            await db.flush()
            await db.refresh(event)
            logger.success(f"活动海报更新成功: {event_id}")
            return file_name
        except Exception as e:
            logger.error(f"更新活动海报失败: {e}", exc_info=True)
            raise

    async def get_upcoming_events(self, db: AsyncSession, current_time: datetime) -> list[dict]:
        """
        获取所有即将开始的、已完成信息录入的活动。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            current_time: 当前时间（时区感知）。
            
        Returns:
            一个包含活动基本信息字典的列表。
        """
        try:
            logger.info(f"查询未开展活动 | 当前时间: {current_time.isoformat()}")
            stmt = select(Event).where(
                Event.is_completed == True,
                Event.start_time > current_time
            ).order_by(Event.start_time.asc())
            
            result = await db.execute(stmt)
            events = result.scalars().all()
            
            event_list = [self._event_to_dict(event, with_poster_url=True) for event in events]
            
            # 过滤掉poster URL获取失败的None值
            event_list = [e for e in event_list if e and e.get("poster")]
            
            logger.info(f"找到 {len(event_list)} 个未开展活动")
            return event_list
        except Exception as e:
            logger.error(f"查询未开展活动失败: {e}", exc_info=True)
            raise

    async def cleanup_incomplete_events(self, db: AsyncSession) -> int:
        """
        使用单个DELETE语句清理所有超时的、未完成信息录入的活动。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
        
        Returns:
            被清理的活动数量。
        """
        try:
            five_minutes_ago = datetime.now().astimezone() - timedelta(minutes=5)
            logger.info(f"开始清理创建于 {five_minutes_ago.isoformat()} 之前且未完成的活动")
            
            stmt = delete(Event).where(
                Event.is_completed == False,
                Event.created_at <= five_minutes_ago
            )
            
            result = await db.execute(stmt)
            deleted_count = result.rowcount
            
            if deleted_count > 0:
                logger.info(f"成功清理 {deleted_count} 个未完成的活动。")
            else:
                logger.info("没有需要清理的未完成活动。")
            
            return deleted_count
        except Exception as e:
            logger.error(f"清理未完成活动失败: {e}", exc_info=True)
            raise