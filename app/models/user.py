# app/models/user.py
"""
用户模型模块 (User Model Module)

该模块定义了`User` ORM模型，用于映射数据库中的`users`表。
它存储了所有与微信小程序用户相关的信息，并是多个其他模型的外键关联中心。
"""
from __future__ import annotations # 关键导入，用于在模型内部类型提示自身或其他模型
from typing import List

from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from .base import BaseMixin

# 避免在类型检查时产生循环导入问题
class Task:
    pass
class Arrange:
    pass
class PublicityLink:
    pass

class User(Base, BaseMixin):
    """
    用户数据模型 (ORM Class)

    映射到`users`表，存储用户基本信息、权限、状态等。
    在v0.2重构中，添加了`college`字段，并建立了与Task, Arrange, PublicityLink等模型的反向关系。
    在v0.3扩充中，添加了`student_id`和`qq`字段，用于借用系统锚定。

    Attributes:
        id (int): 自增主键，数据库内部唯一标识。
        userid (str): 用户的微信openid，作为业务逻辑上的唯一标识符。
        maker_id (str, optional): 分配给用户的协会唯一标识符。
        student_id (str, optional): [v0.3 新增] 学号，唯一，业务上借用物资必填。
        qq (str, optional): [v0.3 新增] QQ号，联系方式。
        role (int): 用户权限级别。
        department (int): 用户所属部门的数字代码。
        real_name (str): 用户的真实姓名。
        phone_num (str, optional): 用户的手机号。
        college (str, optional): 用户所属学院，为项目部功能新增。
        grade (str, optional): 用户所属年级。
        motto (str): 用户的个性签名。
        state (int): 用户账号状态。
        profile_photo (str, optional): 用户头像在MinIO中的对象名称/路径。
        score (int): 用户的积分。
        total_dutytime (int): 用户的总值班时长（单位：分钟）。
        
        tasks (List["Task"]): [v0.2 新增] SQLAlchemy反向关系，可通过 user.tasks 访问该用户负责的所有任务。
        arrangements (List["Arrange"]): [v0.2 新增] SQLAlchemy反向关系，可通过 user.arrangements 访问该用户的所有排班记录。
        publicity_links (List["PublicityLink"]): [v0.2 新增] SQLAlchemy反向关系，可通过 user.publicity_links 访问该用户提交的所有秀米链接。
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, comment="自增主键ID")
    userid: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False, comment="微信openid，业务唯一标识")
    maker_id: Mapped[str | None] = mapped_column(String(128), index=True, comment="协会ID")
    
    # [v0.3 新增字段] 借用系统核心字段
    # 注意：为了兼容旧数据，数据库层面允许 NULL，但业务逻辑会在借用时强制检查
    student_id: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True, comment="学号")
    qq: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="QQ号")

    role: Mapped[int] = mapped_column(Integer, default=1, nullable=False, index=True, comment="权限级别: 0=普通, 1=干事, 2=部长")
    department: Mapped[int] = mapped_column(Integer, default=999, nullable=False, index=True, comment="所属部门ID")
    real_name: Mapped[str] = mapped_column(String(100), default="猫猫", nullable=False, comment="真实姓名")
    phone_num: Mapped[str | None] = mapped_column(String(20), index=True, comment="手机号")
    
    # [v0.2 新增字段] 为项目部功能添加学院信息
    college: Mapped[str | None] = mapped_column(String(100), index=True, comment="学院")
    grade: Mapped[str | None] = mapped_column(String(20), index=True, nullable=True, comment="年级")

    motto: Mapped[str] = mapped_column(String(255), default="这个人很懒，什么都没写~", nullable=False, comment="个性签名")
    state: Mapped[int] = mapped_column(Integer, default=1, nullable=False, index=True, comment="账号状态: 0=封禁, 1=正常")
    profile_photo: Mapped[str | None] = mapped_column(String(255), comment="MinIO中的头像对象名")
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="用户积分")
    total_dutytime: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="总值班时长（分钟）")

    # --- [v0.2 新增] SQLAlchemy 反向关系 ---
    tasks: Mapped[List["Task"]] = relationship(back_populates="user")
    arrangements: Mapped[List["Arrange"]] = relationship(back_populates="user")
    publicity_links: Mapped[List["PublicityLink"]] = relationship(back_populates="user")