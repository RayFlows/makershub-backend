# app/services/publicity_link_service.py
"""
秀米链接服务类：处理秀米链接相关的业务逻辑
[v2.0 SQLAlchemy 迁移版]
"""
from typing import Optional, List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from datetime import datetime
import random

from app.models.publicity_link import PublicityLink

class PublicityLinkService:
    """
    秀米链接服务类，封装了所有提交、查询和审核秀米链接的业务逻辑。
    """

    @staticmethod
    def _generate_link_id() -> str:
        """
        生成全局唯一的链接ID。
        格式: PL + 当前时间戳(YYYYMMDDHHMMSSms) + 3位随机数。
        
        Returns:
            str: 生成的唯一链接ID。
        """
        now = datetime.utcnow()
        timestamp = now.strftime("%Y%m%d%H%M%S%f")[:-3]
        random_suffix = f"{random.randint(0, 999):03d}"
        return f"PL{timestamp}_{random_suffix}"
    
    def _link_to_dict(self, link: PublicityLink) -> Optional[Dict[str, Any]]:
        """
        辅助函数：将SQLAlchemy PublicityLink ORM对象安全地转换为字典。
        用于API响应序列化，以保持与旧接口的数据结构兼容。
        
        Args:
            link: SQLAlchemy的PublicityLink模型实例。
        
        Returns:
            一个包含链接信息的字典，如果输入为None则返回None。
        """
        if not link:
            return None
        
        # 为了API兼容性，将 created_at 映射回 create_time
        return {
            "link_id": link.link_id,
            "title": link.title,
            "name": link.name,
            "userid": link.userid,
            "link": link.link,
            "state": link.state,
            "review": link.review,
            "create_time": link.created_at.isoformat() + "Z" if link.created_at else None,
        }

    async def create_link(self, db: AsyncSession, userid: str, name: str, title: str, link_url: str) -> PublicityLink:
        """
        创建新的秀米链接提交。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            userid: 提交用户的openid。
            name: 提交用户的姓名。
            title: 推文标题。
            link_url: 推文链接。
            
        Returns:
            新创建的PublicityLink ORM实例。
        """
        try:
            new_link = PublicityLink(
                link_id=self._generate_link_id(),
                userid=userid,
                name=name,
                title=title,
                link=link_url,
                state=0  # 初始状态为待审核
            )
            db.add(new_link)
            await db.flush()
            await db.refresh(new_link)
            logger.info(f"秀米链接创建成功 | Link ID: {new_link.link_id} | User: {userid}")
            return new_link
        except Exception as e:
            logger.error(f"创建秀米链接失败: {e}", exc_info=True)
            raise

    async def get_all_links(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """
        获取所有秀米链接，按创建时间降序排列。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            
        Returns:
            一个包含所有链接信息字典的列表。
        """
        try:
            stmt = select(PublicityLink).order_by(PublicityLink.created_at.desc())
            result = await db.execute(stmt)
            links = result.scalars().all()
            return [self._link_to_dict(link) for link in links]
        except Exception as e:
            logger.error(f"获取所有秀米链接失败: {e}", exc_info=True)
            raise

    async def get_user_links(self, db: AsyncSession, userid: str) -> List[Dict[str, Any]]:
        """
        获取指定用户提交的所有秀米链接。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            userid: 用户的openid。
            
        Returns:
            一个包含该用户所有链接信息字典的列表。
        """
        try:
            stmt = select(PublicityLink).where(PublicityLink.userid == userid).order_by(PublicityLink.created_at.desc())
            result = await db.execute(stmt)
            links = result.scalars().all()
            return [self._link_to_dict(link) for link in links]
        except Exception as e:
            logger.error(f"获取用户秀米链接失败: {e} | UserID: {userid}", exc_info=True)
            raise

    async def update_link(self, db: AsyncSession, link_id: str, userid: str, update_data: Dict[str, Any]) -> Optional[PublicityLink]:
        """
        更新一个秀米链接。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            link_id: 要更新的链接的业务ID。
            userid: 操作用户的openid，用于权限验证。
            update_data: 包含要更新字段的字典。
            
        Returns:
            更新后的PublicityLink ORM实例，如果链接不存在则返回None。
        """
        stmt = select(PublicityLink).where(PublicityLink.link_id == link_id)
        result = await db.execute(stmt)
        link = result.scalar_one_or_none()

        if not link:
            return None

        # 权限与状态检查
        if link.userid != userid:
            raise PermissionError("Forbidden to update others' link")
        if link.state not in [0, 2]: # 0=待审核, 2=已打回
            raise ValueError(f"Link state forbids update. Current state: {link.state}")

        # 更新字段
        for field, value in update_data.items():
            if hasattr(link, field):
                setattr(link, field, value)
        
        # 用户重新编辑后，状态重置为待审核
        link.state = 0
        link.review = None # 清空旧的审核反馈
        
        db.add(link)
        await db.flush()
        await db.refresh(link)
        logger.info(f"链接已更新 | Link ID: {link_id} | 更新字段: {list(update_data.keys())}")
        return link

    async def review_link(self, db: AsyncSession, link_id: str, state: int, review: str) -> Optional[PublicityLink]:
        """
        审核一个秀米链接。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            link_id: 要审核的链接的业务ID。
            state: 新的审核状态 (1=通过, 2=打回)。
            review: 审核反馈。
            
        Returns:
            审核后的PublicityLink ORM实例，如果链接不存在则返回None。
        """
        stmt = select(PublicityLink).where(PublicityLink.link_id == link_id)
        result = await db.execute(stmt)
        link = result.scalar_one_or_none()

        if not link:
            return None

        # 状态检查
        if link.state != 0: # 必须是待审核状态
            raise ValueError(f"Link not in pending state. Current state: {link.state}")
        
        link.state = state
        link.review = review
        
        db.add(link)
        await db.flush()
        await db.refresh(link)
        logger.info(f"链接已审核 | Link ID: {link_id} | 新状态: {state}")
        return link