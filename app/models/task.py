# app/models/task.py
"""
任务模型模块 (Task Model Module)

该模块定义了`Task` ORM模型，用于映射数据库中的`tasks`表。
它存储了所有与任务分配、状态跟踪相关的信息。
"""

from sqlalchemy import String, Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from app.core.database import Base
from .base import BaseMixin

class Task(Base, BaseMixin):
    """
    任务数据模型 (ORM Class)

    映射到`tasks`表，存储任务的类型、内容、负责人、状态和截止日期。

    Attributes:
        id (int): 自增主键，数据库内部唯一标识。
        task_id (str): 业务逻辑上的唯一标识符 (格式: TS+时间戳+随机数)。
        department (int): 任务所属部门的ID。
        task_type (int): 任务类型 (0:其他, 1:活动文案, 2:推文, 3:新闻稿)。
        maker_id (str): 负责人的协会ID (maker_id)。
        name (str): 负责人的真实姓名 (为方便展示而冗余)。
        content (str): 任务的具体内容。
        state (int): 任务状态 (0:未完成, 1:已完成, 2:已取消)。
        deadline (datetime): 任务的截止日期和时间。
    """
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, comment="自增主键ID")
    task_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False, comment="业务唯一ID (TS+时间戳)")
    
    department: Mapped[int] = mapped_column(Integer, index=True, nullable=False, comment="所属部门ID")
    task_type: Mapped[int] = mapped_column(Integer, index=True, nullable=False, comment="任务类型 (0:其他, 1:文案, 2:推文, 3:新闻稿)")
    
    # TODO (v0.2): 技术债务 - 外键规范化
    # 当前的 maker_id 存储的是 users.maker_id，name 是冗余字段。
    # 未来应使用 user_id 外键关联到 users.id，并通过 JOIN 获取姓名。
    maker_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False, comment="负责人的协会ID")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="负责人姓名 (冗余)")

    content: Mapped[str] = mapped_column(Text, nullable=False, comment="任务具体内容")
    state: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True, comment="任务状态 (0:未完成, 1:已完成, 2:已取消)")
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True, comment="任务截止时间")