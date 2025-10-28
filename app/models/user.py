# app/models/user.py
"""
用户模型模块 (User Model Module)

该模块定义了`User` ORM模型，用于映射数据库中的`users`表。
它存储了所有与微信小程序用户相关的信息，并继承自`BaseMixin`以获得自动时间戳功能。
"""

from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from .base import BaseMixin

class User(Base, BaseMixin):
    """
    用户数据模型 (ORM Class)

    映射到`users`表，存储用户基本信息、权限、状态等。
    字段的类型注解 (如 `Mapped[int]`) 和 `mapped_column` 函数共同定义了
    Python对象属性与数据库表列之间的映射关系。

    Attributes:
        id (int): 自增主键，数据库内部唯一标识。
        userid (str): 用户的微信openid，作为业务逻辑上的唯一标识符，建立了唯一索引以加速查询。
        maker_id (str, optional): 分配给用户的协会唯一标识符。
        role (int): 用户权限级别 (0=普通, 1=干事, 2=部长及以上)，有索引。
        department (int): 用户所属部门的数字代码，有索引。
        real_name (str): 用户的真实姓名。
        phone_num (str, optional): 用户的手机号，有索引。
        motto (str): 用户的个性签名。
        state (int): 用户账号状态 (0=封禁, 1=正常)，有索引。
        profile_photo (str, optional): 用户头像在MinIO中的对象名称/路径。
        score (int): 用户的积分。
        total_dutytime (int): 用户的总值班时长（单位：分钟）。
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, comment="自增主键ID")
    userid: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False, comment="微信openid，业务唯一标识")
    maker_id: Mapped[str | None] = mapped_column(String(128), index=True, comment="协会ID")
    role: Mapped[int] = mapped_column(Integer, default=1, nullable=False, index=True, comment="权限级别: 0=普通, 1=干事, 2=部长")
    department: Mapped[int] = mapped_column(Integer, default=999, nullable=False, index=True, comment="所属部门ID")
    real_name: Mapped[str] = mapped_column(String(100), default="猫猫", nullable=False, comment="真实姓名")
    phone_num: Mapped[str | None] = mapped_column(String(20), index=True, comment="手机号")
    motto: Mapped[str] = mapped_column(String(255), default="这个人很懒，什么都没写~", nullable=False, comment="个性签名")
    state: Mapped[int] = mapped_column(Integer, default=1, nullable=False, index=True, comment="账号状态: 0=封禁, 1=正常")
    profile_photo: Mapped[str | None] = mapped_column(String(255), comment="MinIO中的头像对象名")
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="用户积分")
    total_dutytime: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="总值班时长（分钟）")