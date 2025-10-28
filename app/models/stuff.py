# app/models/stuff.py
"""
物资模型模块 (Stuff Model Module)

定义了`Stuff` ORM模型，用于映射数据库中的`stuffs`表。
存储了社团所有物资的详细信息，包括基础信息和用于后台管理的扩展仓储信息。
"""

from sqlalchemy import String, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from .base import BaseMixin

class Stuff(Base, BaseMixin):
    """
    物资数据模型 (ORM Class)

    映射到`stuffs`表，存储物资的类型、名称、数量、描述和位置等信息。

    Attributes:
        id (int): 自增主键。
        stuff_id (str): 物资的唯一业务ID，保持与旧系统兼容，建立了唯一索引。
        type_id (str, optional): 物资类型的ID。
        type (str): 物资类型的名称，如“电子模块”、“工具”等，有索引。
        stuff_name (str): 物资的具体名称，如“ESP32开发板”，有索引。
        number_total (int): 该物资的总库存数量。
        number_remain (int): 当前剩余可借用的数量。
        description (str): 物资的详细描述，使用Text类型以支持更长内容。
        location (str, optional): 物资存放的大致位置，如“i创街”、“101”。
        cabinet (str, optional): 所在的具体展柜编号，如“A”、“BC”。
        layer (int, optional): 在展柜中的层数。
    """
    __tablename__ = "stuffs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, comment="自增主键ID")
    stuff_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True, comment="物资唯一业务ID")
    type_id: Mapped[str | None] = mapped_column(String(50), comment="物资类型ID")
    type: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="物资类型名称")
    stuff_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True, comment="物资具体名称")
    number_total: Mapped[int] = mapped_column(Integer, nullable=False, comment="总数量")
    number_remain: Mapped[int] = mapped_column(Integer, nullable=False, comment="剩余数量")
    description: Mapped[str] = mapped_column(Text, nullable=False, comment="物资详细描述")
    
    # --- 扩展字段（管理员后台专用） ---
    location: Mapped[str | None] = mapped_column(String(50), default="", comment="存放场地")
    cabinet: Mapped[str | None] = mapped_column(String(10), default="", comment="展柜编号")
    layer: Mapped[int | None] = mapped_column(Integer, default=1, comment="所在层数")