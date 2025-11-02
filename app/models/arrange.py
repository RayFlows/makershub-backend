# app/models/arrange.py
"""
排班安排模型模块 (Arrange Model Module)

该模块定义了`Arrange` ORM模型，用于映射数据库中的`arrangements`表。
它存储了特定任务类型的人员排班顺序和当前值班状态。
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, Boolean, UniqueConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from .base import BaseMixin

if TYPE_CHECKING:
    from .user import User # 仅在类型检查时导入，避免循环依赖

class Arrange(Base, BaseMixin):
    """
    排班安排数据模型 (ORM Class)

    映射到`arrangements`表，定义了每个任务类型的值班人员、顺序和当前状态。
    在v0.2重构中，移除了冗余的`name`字段，并将人员关联改为指向`users`表的`id`的外键。

    Attributes:
        id (int): 自增主键。
        arrange_id (str): 业务逻辑上的唯一标识符。
        user_id (int): [v0.2 重构] 排班人员的外键ID，指向users.id。
        task_type (int): 任务类型。
        order (int): 在该任务类型中的排班顺序。
        current (bool): 是否为当前值班人员。
        user (User): [v0.2 新增] SQLAlchemy正向关系，可通过 arrange.user 访问关联的User对象。
    """
    __tablename__ = "arrangements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, comment="自增主键ID")
    arrange_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False, comment="业务唯一ID (AR+时间戳)")
    
    # [v0.2 重构] 移除冗余的 name 字段，并将 maker_id 替换为 user_id 外键
    # name: Mapped[str] = mapped_column(String(100), nullable=False, comment="排班人员姓名 (冗余)")
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False, comment="排班人员的外键ID")
    
    task_type: Mapped[int] = mapped_column(Integer, index=True, nullable=False, comment="任务类型 (1:文案, 2:推文, 3:新闻稿)")
    order: Mapped[int] = mapped_column(Integer, nullable=False, comment="排班顺序 (从0开始)")
    current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True, comment="是否为当前值班")

    # --- [v0.2 新增] SQLAlchemy 正向关系 ---
    user: Mapped["User"] = relationship(back_populates="arrangements")

    __table_args__ = (
        # 确保在同一个任务类型中，每个人的排班顺序是唯一的
        UniqueConstraint('task_type', 'order', name='uq_arrange_task_type_order'),
        # [v0.2 重构] 将唯一性约束从 maker_id 改为 user_id
        # 确保在同一个任务类型中，一个用户只能被安排一次
        UniqueConstraint('task_type', 'user_id', name='uq_arrange_task_type_user_id'),
    )