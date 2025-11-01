# app/models/event.py
"""
活动模型模块 (Event Model Module)

该模块定义了`Event` ORM模型，用于映射数据库中的`events`表。
它存储了所有与活动发布相关的信息，并继承自`BaseMixin`以获得自动时间戳功能。
"""

from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from .base import BaseMixin

class Event(Base, BaseMixin):
    """
    活动数据模型 (ORM Class)

    映射到`events`表，存储活动的基本信息。
    在v2.0迁移中，对字段类型进行了优化，特别是将日期字符串改为了标准的DateTime类型。

    Attributes:
        id (int): 自增主键，数据库内部唯一标识。
        event_id (str): 业务逻辑上的唯一标识符 (格式: EV+时间戳+随机数)，建立了唯一索引。
        event_name (str, optional): 活动的完整名称。
        poster (str, optional): 活动海报在MinIO中的对象名称/路径。
        description (str, optional): 活动的详细描述，使用Text类型以支持长文本。
        participant (str, optional): 活动的参与对象说明。
        location (str, optional): 活动的举办地点。
        link (str, optional): 活动的外部链接，例如报名问卷。
        start_time (datetime, optional): 活动开始时间，使用带时区的时间类型。
        end_time (datetime, optional): 活动结束时间，使用带时区的时间类型。
        registration_deadline (datetime, optional): 报名截止时间，使用带时区的时间类型。
        is_completed (bool): 标记活动信息是否已补全。False表示仅预创建了ID，True表示信息完整可展示。
    """
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, comment="自增主键ID")
    event_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False, comment="业务唯一ID (EV+时间戳)")
    
    event_name: Mapped[str | None] = mapped_column(String(255), comment="活动名称")
    poster: Mapped[str | None] = mapped_column(String(512), comment="海报在MinIO中的对象名")
    description: Mapped[str | None] = mapped_column(Text, comment="活动详细描述")
    participant: Mapped[str | None] = mapped_column(String(255), comment="参与对象")
    location: Mapped[str | None] = mapped_column(String(255), comment="活动地点")
    link: Mapped[str | None] = mapped_column(String(512), comment="相关链接（如报名问卷）")
    
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True, comment="活动开始时间")
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True, comment="活动结束时间")
    registration_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="报名截止时间")
    
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="信息是否已补全 (True:已补全, False:未补全)")