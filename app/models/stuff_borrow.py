# app/models/stuff_borrow.py
"""
物资借用申请主模型模块 (Stuff Borrow Main Model Module)

定义了`StuffBorrow` ORM模型，这是物资借用业务的核心。
它存储了每一次借用申请的完整信息，并与借用物品清单(`BorrowItem`)建立了一对多关系。
"""
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, TYPE_CHECKING
from datetime import datetime

from app.core.database import Base
from .base import BaseMixin

# 使用TYPE_CHECKING来避免循环导入问题，这是Python类型提示的标准实践。
# 在运行时，TYPE_CHECKING为False，导入不会发生；在类型检查时为True。
if TYPE_CHECKING:
    from .borrow_item import BorrowItem
    from .user import User

class StuffBorrow(Base, BaseMixin):
    """
    物资借用申请数据模型 (ORM Class)

    映射到`stuff_borrows`表，记录了所有借用申请的元数据。
    这是关系型设计的核心，将原先的嵌套列表拆分为一个独立的关系。

    Attributes:
        id (int): 自增主键。
        sb_id (str): 申请的唯一业务ID，保持与旧系统兼容。
        user_id (str): 申请人的`userid` (微信openid)，外键关联到`users`表。
        type (int): 借用类型，0为个人，1为团队。
        state (int): 申请的当前状态 (0-未审核, 1-被打回, 2-通过, 3-已归还)。
        borrow_items (List[BorrowItem]): 通过ORM关系加载的借用物品清单。
                                         这是一个Python列表，包含了所有与此申请关联的`BorrowItem`对象。
    """
    __tablename__ = "stuff_borrows"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, comment="自增主键ID")
    sb_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True, comment="申请唯一业务ID")
    
    # 注意：在关系型数据库中，外键通常关联到对方表的主键(如users.id)。
    # 但为了保持API兼容性（可能API仍使用userid），我们暂时将外键关联到users.userid字段。
    # 这是一个设计上的权衡，关联到`id`会更规范、性能更好。
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.userid"), index=True, comment="申请人UserID(关联users.userid)")

    type: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="借用类型: 0=个人, 1=团队")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="申请人姓名")
    student_id: Mapped[str] = mapped_column(String(50), nullable=False, comment="学号")
    phone_num: Mapped[str] = mapped_column(String(20), nullable=False, comment="手机号")
    email: Mapped[str] = mapped_column(String(100), nullable=False, comment="邮箱")
    grade: Mapped[str] = mapped_column(String(20), nullable=False, comment="年级")
    major: Mapped[str] = mapped_column(String(100), nullable=False, comment="专业")
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="预计借用开始时间")
    deadline: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="预计归还时间")
    reason: Mapped[str] = mapped_column(Text, nullable=False, comment="借用事由")
    state: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True, comment="申请状态: 0=未审, 1=打回, 2=通过, 3=归还")
    review: Mapped[str | None] = mapped_column(Text, default='', comment="审核意见")
    
    # --- 团队借物字段 ---
    project_number: Mapped[str | None] = mapped_column(String(50), comment="项目编号")
    supervisor_name: Mapped[str | None] = mapped_column(String(100), comment="指导老师姓名")
    supervisor_phone: Mapped[str | None] = mapped_column(String(20), comment="指导老师电话")
    
    # --- 关系定义 (Relationship) ---
    # `relationship`是ORM的魔法所在，它在Python对象层面建立了表之间的关联。
    # "BorrowItem": 关联的模型类名。
    # `back_populates="borrow_application"`: 这建立了一个双向关系。它告诉SQLAlchemy，
    #                                      在`BorrowItem`模型中，有一个名为`borrow_application`的属性
    #                                      会反向引用回这个`StuffBorrow`实例。
    # `cascade="all, delete-orphan"`: 级联操作。
    #    - all: 对`StuffBorrow`的所有操作（保存、删除等）都会传递到关联的`borrow_items`上。
    #    - delete-orphan: 如果一个`BorrowItem`对象从`stuff_borrow.borrow_items`这个列表中被移除，
    #                     那么这个`BorrowItem`记录将从数据库中被删除。这是管理一对多关系最常用的设置。
    borrow_items: Mapped[List["BorrowItem"]] = relationship(
        "BorrowItem", back_populates="borrow_application", cascade="all, delete-orphan"
    )

    # 也可以选择性地建立与User模型的直接关系
    # applicant: Mapped["User"] = relationship(foreign_keys=[user_id])