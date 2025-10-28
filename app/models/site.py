# app/models/site.py
"""
场地模型模块 (Site Model Module)

该模块定义了`Site` ORM模型，用于映射数据库中的`sites`表。
它存储了所有场地工位的详细信息。
[v2.0 SQLAlchemy 迁移版]
"""
from sqlalchemy import String, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import random

from app.core.database import Base
from .base import BaseMixin

class Site(Base, BaseMixin):
    """
    场地数据模型 (ORM Class)
    
    映射到`sites`表，表中的每一行代表一个具体的工位。
    例如，"B208+"场地的1号工位是一行记录，2号工位是另一行记录。
    
    Attributes:
        id (int): 自增主键。
        site_id (str): 场地ID，同一场地的所有工位共享相同的site_id，用于逻辑分组。
        site (str): 场地位置的名称，如 "二基楼B208+"。
        number (int): 该场地内的工位号。
        is_occupied (bool): 当前工位是否被占用。
    """
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, comment="自增主键ID")
    site_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="场地ID，用于标识同一批创建的工位")
    site: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="场地位置名称")
    number: Mapped[int] = mapped_column(Integer, nullable=False, comment="工位号")
    is_occupied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否被占用")

    # 注意： generate_site_id 是一个业务逻辑函数，它不属于模型定义的一部分。
    # 我们将把它移动到 Service 层，因为 Service 负责处理业务逻辑。
    # 模型（Model）应该只关注数据结构和与数据库表的映射。

    # 注意： to_dict 方法在 SQLAlchemy 中通常不是必需的。
    # 在 Service 或 Route 层，我们会直接访问ORM对象的属性，
    # 或者使用 Pydantic 模型来进行序列化，以实现更好的解耦。