# app/models/task.py
"""
任务模型模块 (Task Model Module)

该模块定义了`Task` ORM模型，用于映射数据库中的`tasks`表。
它存储了所有与任务分配、状态跟踪相关的信息。
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.core.database import Base
from .base import BaseMixin

if TYPE_CHECKING:
    from .user import User # 仅在类型检查时导入，避免循环依赖

class Task(Base, BaseMixin):
    """
    任务数据模型 (ORM Class)

    映射到`tasks`表，存储任务的类型、内容、负责人、状态和截止日期。
    在v0.2重构中，移除了冗余的`name`字段，并将负责人关联改为指向`users`表的`id`的外键。

    Attributes:
        id (int): 自增主键。
        task_id (str): 业务逻辑上的唯一标识符。
        department (int): 任务所属部门的ID。
        task_type (int): 任务类型。
        user_id (int): [v0.2 重构] 负责人的外键ID，指向users.id。
        content (str): 任务的具体内容。
        state (int): 任务状态。
        deadline (datetime): 任务的截止日期和时间。
        user (User): [v0.2 新增] SQLAlchemy正向关系，可通过 task.user 访问关联的User对象。
    """
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, comment="自增主键ID")
    task_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False, comment="业务唯一ID (TS+时间戳)")
    
    department: Mapped[int] = mapped_column(Integer, index=True, nullable=False, comment="所属部门ID")
    task_type: Mapped[int] = mapped_column(Integer, index=True, nullable=False, comment="任务类型 (0:其他, 1:文案, 2:推文, 3:新闻稿)")
    
    # [v0.2 重构] 移除冗余的 name 字段，并将 maker_id 替换为 user_id 外键
    # name: Mapped[str] = mapped_column(String(100), nullable=False, comment="负责人姓名 (冗余)")
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False, comment="负责人的外键ID")

    content: Mapped[str] = mapped_column(Text, nullable=False, comment="任务具体内容")
    state: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True, comment="任务状态 (0:未完成, 1:已完成, 2:已取消)")
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True, comment="任务截止时间")
    
    # --- [v0.2 新增] SQLAlchemy 正向关系 ---
    # `back_populates` 参数指向 User 模型中对应的 `tasks` 关系，建立双向链接。
    user: Mapped["User"] = relationship(back_populates="tasks")