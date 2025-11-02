# app/services/publicity_link_service.py
"""
秀米链接服务类：处理秀米链接相关的业务逻辑
[v0.2 SQLAlchemy 重构版]
"""
from typing import Optional, List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger
from datetime import datetime
import random

from app.models.publicity_link import PublicityLink
from app.models.user import User

class PublicityLinkService:
    """
    秀米链接服务类，封装了所有提交、查询和审核秀米链接的业务逻辑。
    在v0.2重构中，所有逻辑都已基于外键和ORM关系进行重写。
    """

    @staticmethod
    def _generate_link_id() -> str:
        """生成全局唯一的链接ID。"""
        now = datetime.utcnow()
        timestamp = now.strftime("%Y%m%d%H%M%S%f")[:-3]
        random_suffix = f"{random.randint(0, 999):03d}"
        logger.debug(f"生成新的秀米链接ID: PL{timestamp}_{random_suffix}")
        return f"PL{timestamp}_{random_suffix}"
    
    def _link_to_dict(self, link: PublicityLink) -> Optional[Dict[str, Any]]:
        """
        [v0.2 兼容性保障] 辅助函数：将 PublicityLink ORM 对象转换为兼容旧版API的字典。
        
        Args:
            link: SQLAlchemy的PublicityLink模型实例，必须已预加载了 user 关系。
        
        Returns:
            一个包含链接信息的字典，其中 name 和 userid 是为了API兼容而添加的。
        """
        if not link or not link.user:
            logger.warning(f"序列化秀米链接失败：对象为空或 user 关系未加载。Link ID: {link.link_id if link else 'N/A'}")
            return None
        
        return {
            "link_id": link.link_id,
            "title": link.title,
            # [核心兼容] 通过 relationship 访问 user 对象的属性，伪造出旧的字段
            "name": link.user.real_name,
            "userid": link.user.userid, # openid
            "link": link.link,
            "state": link.state,
            "review": link.review,
            "create_time": link.created_at.isoformat() + "Z" if link.created_at else None,
        }

    async def get_link_by_id(self, db: AsyncSession, link_id: str) -> Optional[PublicityLink]:
        """[v0.2] 通过业务ID (link_id) 获取秀米链接的 ORM 实例，并预加载提交人信息。"""
        logger.debug(f"正在通过 link_id 查询秀米链接 ORM: {link_id}")
        stmt = select(PublicityLink).where(PublicityLink.link_id == link_id).options(selectinload(PublicityLink.user))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_link(self, db: AsyncSession, user: User, title: str, link_url: str) -> PublicityLink:
        """
        [v0.2] 创建新的秀米链接提交。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            user: 提交链接的 User ORM 对象。
            title: 推文标题。
            link_url: 推文链接。
            
        Returns:
            新创建的PublicityLink ORM实例。
        """
        logger.info(f"用户 {user.real_name} (ID: {user.id}) 正在创建秀米链接...")
        new_link = PublicityLink(
            link_id=self._generate_link_id(),
            user_id=user.id, # [核心改造] 使用 user.id 作为外键
            title=title,
            link=link_url,
            state=0  # 初始状态为待审核
        )
        db.add(new_link)
        await db.flush()
        await db.refresh(new_link)
        logger.success(f"✅ 秀米链接创建成功 | Link ID: {new_link.link_id} | User ID: {user.id}")
        return new_link

    async def get_all_links(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """[v0.2] 获取所有秀米链接，按创建时间降序排列。"""
        logger.info("正在查询所有秀米链接...")
        stmt = select(PublicityLink).order_by(PublicityLink.created_at.desc()).options(selectinload(PublicityLink.user))
        result = await db.execute(stmt)
        links = result.scalars().all()
        logger.info(f"查询到 {len(links)} 条秀米链接记录。")
        return [self._link_to_dict(link) for link in links]

    async def get_user_links(self, user: User) -> List[Dict[str, Any]]:
        """
        [v0.2] 获取指定用户提交的所有秀米链接。
        
        Args:
            user: 已预加载了 publicity_links 关系的 User ORM 对象。
            
        Returns:
            一个包含该用户所有链接信息字典的列表。
        """
        logger.info(f"正在获取用户 {user.real_name} (ID: {user.id}) 的秀米链接列表...")
        # [核心改造] 直接访问已加载的 relationship 属性，无需再次查询数据库
        links = sorted(user.publicity_links, key=lambda l: l.created_at, reverse=True)
        logger.info(f"为用户 {user.real_name} 获取到 {len(links)} 条秀米链接。")
        return [self._link_to_dict(link) for link in links]

    async def update_link(self, db: AsyncSession, link_id: str, user_id: int, update_data: Dict[str, Any]) -> Optional[PublicityLink]:
        """
        [v0.2] 更新一个秀米链接。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            link_id: 要更新的链接的业务ID。
            user_id: 操作用户的内部ID (users.id)，用于权限验证。
            update_data: 包含要更新字段的字典。
            
        Returns:
            更新后的PublicityLink ORM实例，如果链接不存在则返回None。
        """
        logger.info(f"用户 (ID: {user_id}) 请求更新秀米链接: {link_id}")
        link = await self.get_link_by_id(db, link_id)
        if not link:
            logger.warning(f"更新失败：未找到 Link ID 为 {link_id} 的链接。")
            return None

        # 权限与状态检查
        if link.user_id != user_id:
            logger.warning(f"权限错误: 用户 {user_id} 尝试更新不属于自己的链接 (Owner ID: {link.user_id})")
            raise PermissionError("Forbidden to update others' link")
        if link.state not in [0, 1]: # 0=待审核, 1=已打回
            logger.warning(f"状态错误: 尝试更新一个状态为 {link.state} 的链接，操作被禁止。")
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
        logger.success(f"✅ 链接已更新 | Link ID: {link_id} | 更新字段: {list(update_data.keys())}")
        return link

    async def review_link(self, db: AsyncSession, link_id: str, state: int, review: str) -> Optional[PublicityLink]:
        """
        [v0.2] 审核一个秀米链接。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            link_id: 要审核的链接的业务ID。
            state: 新的审核状态 (1=打回, 2=通过)。
            review: 审核反馈。
            
        Returns:
            审核后的PublicityLink ORM实例，如果链接不存在则返回None。
        """
        logger.info(f"管理员请求审核秀米链接: {link_id}, 新状态: {state}")
        link = await self.get_link_by_id(db, link_id)
        if not link:
            logger.warning(f"审核失败：未找到 Link ID 为 {link_id} 的链接。")
            return None

        # 状态检查
        if link.state != 0: # 必须是待审核状态
            logger.warning(f"状态错误: 尝试审核一个非待审核状态的链接 (当前状态: {link.state})。")
            raise ValueError(f"Link not in pending state. Current state: {link.state}")
        
        link.state = state
        link.review = review
        
        db.add(link)
        await db.flush()
        await db.refresh(link)
        logger.success(f"✅ 链接已审核 | Link ID: {link_id} | 新状态: {state}")
        return link