# app/models/publicity_link.py
"""
秀米链接模型模块 (PublicityLink Model Module)

该模块定义了`PublicityLink` ORM模型，用于映射数据库中的`publicity_links`表。
它存储了所有与秀米推文链接提交和审核相关的信息。
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from .base import BaseMixin

if TYPE_CHECKING:
    from .user import User # 仅在类型检查时导入，避免循环依赖

class PublicityLink(Base, BaseMixin):
    """
    秀米链接数据模型 (ORM Class)

    映射到`publicity_links`表，存储推文链接的标题、提交人、链接地址、审核状态等。
    在v0.2重构中，移除了冗余的`name`字段，并将提交人关联改为指向`users`表的`id`的外键。

    Attributes:
        id (int): 自增主键。
        link_id (str): 业务逻辑上的唯一标识符。
        title (str): 推文的标题。
        user_id (int): [v0.2 重构] 提交用户的外键ID，指向users.id。
        link (str): 完整的推文链接地址。
        state (int): 审核状态。
        review (str): 审核员给出的反馈或打回理由。
        user (User): [v0.2 新增] SQLAlchemy正向关系，可通过 link.user 访问关联的User对象。
    """
    __tablename__ = "publicity_links"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, comment="自增主-键ID")
    link_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False, comment="业务唯一ID (PL+时间戳)")
    
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="推文标题")
    
    # [v0.2 重构] 移除冗余的 name 字段，并将 userid 替换为 user_id 外键
    # name: Mapped[str] = mapped_column(String(100), nullable=False, comment="提交人姓名")
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False, comment="提交用户的外键ID")

    link: Mapped[str] = mapped_column(Text, nullable=False, comment="推文链接地址")
    
    state: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True, comment="审核状态 (0:待审核, 1:已打回, 2:审核通过)")
    review: Mapped[str | None] = mapped_column(Text, comment="审核反馈或打回理由")

    # --- [v0.2 新增] SQLAlchemy 正向关系 ---
    user: Mapped["User"] = relationship(back_populates="publicity_links")