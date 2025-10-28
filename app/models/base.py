# app/models/base.py
"""
SQLAlchemy基础模型模块 (SQLAlchemy Base Model Module)

该模块为所有SQLAlchemy ORM模型定义了一个共享的基类`BaseMixin`。
它提供了自动化的`created_at`和`updated_at`时间戳字段，其功能与原项目中的
`BaseModel`类似，但利用了SQLAlchemy和数据库层面的特性来实现，更加高效。
"""

from sqlalchemy import func, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from typing import Annotated
from datetime import datetime

# --- 类型注解别名 (Type Annotation Alias) ---
# 使用Python的`Annotated`类型，为我们的时间戳字段创建一个可重用的、带有元数据的类型别名。
# 这样做的好处是：
# 1. DRY原则：避免在每个模型中重复定义相同的列属性。
# 2. 可读性：`Mapped[TimestampMixin]`比一长串`mapped_column`定义更清晰。
# 3. 现代风格：这是SQLAlchemy 2.0推荐的、更现代的类型注解方式。
TimestampMixin = Annotated[
    datetime,
    mapped_column(nullable=False)
]

class BaseMixin:
    """
    SQLAlchemy模型的共享基类 (Mixin)

    此类不直接映射为数据库表 (`__abstract__ = True`)，而是被其他具体模型继承，
    为它们统一添加`created_at`和`updated_at`字段。

    Attributes:
        created_at (datetime): 记录创建的时间戳。该值在记录首次插入时，由数据库自动设置。
        updated_at (datetime): 记录最后一次更新的时间戳。该值在记录首次插入时自动设置，
                               并在每次记录更新时由数据库自动更新。
    """
    __abstract__ = True

    # 创建时间字段
    # `server_default=func.now()`: 告诉数据库在插入新记录时，如果这个字段没有被提供值，
    #                            就使用数据库服务器的当前时间(NOW()函数)作为默认值。
    #                            这是最高效的方式，因为它减少了应用服务器和数据库服务器之间的时间同步问题。
    created_at: Mapped[TimestampMixin] = mapped_column(
        server_default=func.now()
    )

    # 更新时间字段
    # `onupdate=func.now()`: 这是一个数据库层面的触发器。每当这条记录被更新(UPDATE)时，
    #                       数据库会自动将这个字段的值更新为当前时间。这保证了时间戳的准确性，
    #                       且无需在应用代码中手动管理。
    updated_at: Mapped[TimestampMixin] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )