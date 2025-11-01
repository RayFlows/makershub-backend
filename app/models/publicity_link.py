# app/models/publicity_link.py
"""
秀米链接模型模块 (PublicityLink Model Module)

该模块定义了`PublicityLink` ORM模型，用于映射数据库中的`publicity_links`表。
它存储了所有与秀米推文链接提交和审核相关的信息。
"""

from sqlalchemy import String, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from .base import BaseMixin

class PublicityLink(Base, BaseMixin):
    """
    秀米链接数据模型 (ORM Class)

    映射到`publicity_links`表，存储推文链接的标题、提交人、链接地址、审核状态等。

    Attributes:
        id (int): 自增主键，数据库内部唯一标识。
        link_id (str): 业务逻辑上的唯一标识符 (格式: PL+时间戳+随机数)，建立了唯一索引。
        title (str): 推文的标题。
        name (str): 提交人的真实姓名（为方便后台展示而冗余的字段）。
        userid (str): 提交用户的微信openid，建立了索引以加速个人链接的查询。
        link (str): 完整的推文链接地址，使用Text类型以支持长链接。
        state (int): 审核状态。0=待审核, 1=审核通过, 2=已打回/已拒绝。建立了索引。
        review (str): 审核员给出的反馈或打回理由，使用Text类型。
    """
    __tablename__ = "publicity_links"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, comment="自增主键ID")
    link_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False, comment="业务唯一ID (PL+时间戳)")
    
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="推文标题")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="提交人姓名")
    
    # TODO (v0.2): 技术债务 - 外键规范化
    # 当前的 userid 存储的是 users.userid (openid)，这是为了在迁移阶段(v0.1)保持API兼容性。
    # 在未来的优化阶段(v0.2)，这里应该被一个名为 user_id 的整型外键取代，
    # 该外键将直接关联到 users 表的自增主键 id。
    # FOREIGN KEY (user_id) REFERENCES users(id)
    userid: Mapped[str] = mapped_column(String(128), index=True, nullable=False, comment="提交用户的openid")
    
    link: Mapped[str] = mapped_column(Text, nullable=False, comment="推文链接地址")
    
    state: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True, comment="审核状态 (0:待审核, 1:审核通过, 2:已打回)")
    review: Mapped[str | None] = mapped_column(Text, comment="审核反馈或打回理由")