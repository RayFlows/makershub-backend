# app/models/project.py
"""
项目模型模块 (Project Model Module)

该模块定义了项目部相关的核心实体：
1. Project: 项目主表
2. ProjectMember: 项目成员关联表 (多对多中间表)
3. ProjectMaterial: 项目结项材料表
"""
from __future__ import annotations
from typing import List, Optional
from datetime import datetime

from sqlalchemy import String, Integer, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from .base import BaseMixin

# 避免类型检查时的循环导入
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .user import User

class Project(Base, BaseMixin):
    """
    项目主表 (Project)
    对应设计文档 4.2
    """
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, comment="自增主键")
    project_id: Mapped[str | None] = mapped_column(String(128), unique=True, index=True, nullable=True, comment="项目业务编号(提交后生成)")
    
    project_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="项目名称")
    project_type: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="项目类型: 0=个人, 1=比赛")
    
    description: Mapped[str] = mapped_column(Text, nullable=False, comment="项目详细描述")
    finish_description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="结项总结/描述")
    
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="预计开始时间")
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="预计结束时间")
    
    # 外键关联：项目负责人
    leader_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="项目负责人ID")
    
    mentor_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="指导老师姓名")
    mentor_phone: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="指导老师电话")
    
    state: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True, comment="状态: 0=待审核, 1=进行中, 2=已打回, 3=待结项, 4=已结束")
    is_recruiting: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否开放招募")
    
    review: Mapped[str | None] = mapped_column(Text, nullable=True, comment="立项审核意见")
    finish_review: Mapped[str | None] = mapped_column(Text, nullable=True, comment="结项审核意见")

    # --- SQLAlchemy 关系定义 ---
    
    # 1. 负责人关系 (多对一)
    leader: Mapped["User"] = relationship("User", foreign_keys=[leader_id])

    # 2. 项目成员 (多对多，通过 ProjectMember 关联)
    members: Mapped[List["ProjectMember"]] = relationship("ProjectMember", back_populates="project")

    # 3. 结项材料 (一对多)
    materials: Mapped[List["ProjectMaterial"]] = relationship("ProjectMaterial", back_populates="project")


class ProjectMember(Base, BaseMixin):
    """
    项目成员关联表 (Project_Member)
    对应设计文档 4.3
    这是一个关联对象(Association Object)，链接 Project 和 User
    """
    __tablename__ = "project_members"

    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), primary_key=True, comment="项目ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True, comment="用户ID")
    
    # BaseMixin 已包含 created_at (加入时间) 和 updated_at

    # --- 关系定义 ---
    project: Mapped["Project"] = relationship("Project", back_populates="members")
    user: Mapped["User"] = relationship("User")


class ProjectMaterial(Base, BaseMixin):
    """
    项目结项材料表 (Project_Materials)
    对应设计文档 4.4
    """
    __tablename__ = "project_materials"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, comment="自增主键")
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, comment="所属项目ID")
    
    file_name: Mapped[str] = mapped_column(String(512), nullable=False, comment="MinIO对象名")
    file_type: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="文件类型")
    description: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="文件描述")

    # --- 关系定义 ---
    project: Mapped["Project"] = relationship("Project", back_populates="materials")