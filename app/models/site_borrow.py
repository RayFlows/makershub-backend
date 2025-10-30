# app/models/site_borrow.py
"""
场地借用模型模块 (Site Borrow Model Module)

该模块定义了`SiteBorrow` ORM模型，用于映射数据库中的`site_borrows`表。
[v2.0 SQLAlchemy 迁移版]
"""
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import random

from app.core.database import Base
from .base import BaseMixin

class SiteBorrow(Base, BaseMixin):
    """
    场地借用数据模型 (ORM Class)
    
    映射到`site_borrows`表，存储场地借用申请的详细信息。
    
    Attributes:
        id (int): 自增主键。
        apply_id (str): 申请的唯一业务ID。
        userid (str): 申请人的用户ID (微信openid)，外键关联到`users`表。
        site_id (str): 借用场地的ID，外键关联到`sites`表。
        number (int): 借用场地的工位号。
        state (int): 申请状态 (0:未审核, 1:打回, 2:通过未归还, 3:已归还, 4:取消)。
        start_time (datetime): 借用开始时间。
        end_time (datetime): 借用结束时间。
    """
    __tablename__ = "site_borrows"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, comment="自增主键ID")
    apply_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True, comment="申请唯一业务ID")
    userid: Mapped[str] = mapped_column(String(128), ForeignKey("users.userid"), nullable=False, index=True, comment="申请人用户ID")
    
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="借用人姓名")
    student_id: Mapped[str] = mapped_column(String(50), nullable=False, comment="学号")
    phone_num: Mapped[str] = mapped_column(String(20), nullable=False, comment="电话号码")
    email: Mapped[str] = mapped_column(String(100), nullable=False, comment="邮箱地址")
    purpose: Mapped[str] = mapped_column(Text, nullable=False, comment="借用目的")
    project_id: Mapped[str | None] = mapped_column(String(50), comment="项目编号")
    mentor_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="指导老师姓名")
    mentor_phone_num: Mapped[str] = mapped_column(String(20), nullable=False, comment="指导老师电话")
    
    # --- 关联场地信息 ---
    # 虽然原始模型中有 site_id, site, number 三个字段，
    # 在关系型设计中，我们只需要一个外键指向 sites 表的主键即可。
    # 但为了保持API兼容性和简化查询，我们暂时保留这些冗余字段。
    # 更好的设计是只保留一个 site_fk，然后通过 relationship 访问 Site 对象。
    site_id: Mapped[str] = mapped_column(String(50), ForeignKey("sites.site_id"), nullable=False, index=True, comment="场地ID")
    site: Mapped[str] = mapped_column(String(100), nullable=False, comment="场地位置名称")
    number: Mapped[int] = mapped_column(Integer, nullable=False, comment="场地工位号")
    
    # --- 时间字段 ---
    # 使用 DateTime 类型替代 StringField，更符合数据类型
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="开始时间")
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="结束时间")
    
    state: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True, comment="状态 (0:未审核, 1:打回, 2:通过, 3:已归还, 4:取消)")
    review: Mapped[str | None] = mapped_column(Text, default="", comment="审核反馈")

    # 注意：generate_apply_id 将移至 Service 层