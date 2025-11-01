# app/models/arrange.py
"""
排班安排模型模块 (Arrange Model Module)

该模块定义了`Arrange` ORM模型，用于映射数据库中的`arrangements`表。
它存储了特定任务类型的人员排班顺序和当前值班状态。
"""

from sqlalchemy import String, Integer, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from .base import BaseMixin

class Arrange(Base, BaseMixin):
    """
    排班安排数据模型 (ORM Class)

    映射到`arrangements`表，定义了每个任务类型的值班人员、顺序和当前状态。

    Attributes:
        id (int): 自增主键。
        arrange_id (str): 业务逻辑上的唯一标识符。
        name (str): 排班人员姓名 (冗余)。
        maker_id (str): 排班人员的协会ID。
        task_type (int): 任务类型 (1:活动文案, 2:推文, 3:新闻稿)。
        order (int): 在该任务类型中的排班顺序，从0开始。
        current (bool): 是否为当前值班人员。
    """
    __tablename__ = "arrangements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, comment="自增主键ID")
    arrange_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False, comment="业务唯一ID (AR+时间戳)")
    
    # TODO (v0.2): 技术债务 - 外键规范化
    # 当前的 maker_id 存储的是 users.maker_id，name 是冗余字段。
    # 未来应使用 user_id 外键关联到 users.id。
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="排班人员姓名 (冗余)")
    maker_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False, comment="排班人员协会ID")
    
    task_type: Mapped[int] = mapped_column(Integer, index=True, nullable=False, comment="任务类型 (1:文案, 2:推文, 3:新闻稿)")
    order: Mapped[int] = mapped_column(Integer, nullable=False, comment="排班顺序 (从0开始)")
    current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True, comment="是否为当前值班")

    __table_args__ = (
        # 确保在同一个任务类型中，每个人的排班顺序是唯一的
        UniqueConstraint('task_type', 'order', name='uq_task_type_order'),
        # 确保在同一个任务类型中，maker_id 是唯一的
        UniqueConstraint('task_type', 'maker_id', name='uq_task_type_maker_id'),
    )