# app/models/borrow_item.py
"""
借用物品清单模型模块 (Borrow Item Model Module)

定义了`BorrowItem` ORM模型，这是一个关联表（也叫连接表）。
它将“物资借用申请”和“物资”多对多地（通过数量）关联起来，实现了数据库的规范化设计。
"""
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from app.core.database import Base

if TYPE_CHECKING:
    from .stuff_borrow import StuffBorrow
    from .stuff import Stuff

class BorrowItem(Base):
    """
    借用物品清单数据模型 (ORM Class)

    映射到`borrow_items`表。表中的每一行都代表一个借用申请中某一种物资的借用条目。
    这是解决原MongoDB中`stuff_list`嵌套列表的关键。

    Attributes:
        id (int): 自增主键。
        borrow_id (int): 外键，关联到`stuff_borrows`表的`id`列，指明此条目属于哪个借用申请。
        stuff_id (str): 外键，关联到`stuffs`表的`stuff_id`列，指明借用的是哪种物资。
        quantity (int): 借用该物资的数量。
        borrow_application (StuffBorrow): 通过ORM关系加载的、对此条目所属的`StuffBorrow`对象的引用。
    """
    __tablename__ = "borrow_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, comment="自增主键ID")
    
    # 外键，指向`stuff_borrows`表的主键
    borrow_id: Mapped[int] = mapped_column(Integer, ForeignKey("stuff_borrows.id"), nullable=False, comment="关联的借用申请ID")
    
    # 外键，指向`stuffs`表的业务ID
    stuff_id: Mapped[str] = mapped_column(String(50), ForeignKey("stuffs.stuff_id"), nullable=False, comment="关联的物资业务ID")
    
    # 借用的数量
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, comment="借用数量")

    # --- 关系定义 (Relationship) ---
    # `back_populates="borrow_items"`: 建立与`StuffBorrow`模型的双向关系。
    #                                 在`StuffBorrow`中，这个关系由`borrow_items`属性表示。
    borrow_application: Mapped["StuffBorrow"] = relationship(
        "StuffBorrow", back_populates="borrow_items"
    )

    # 也可以选择性地建立与Stuff模型的直接关系
    # stuff_info: Mapped["Stuff"] = relationship(foreign_keys=[stuff_id])