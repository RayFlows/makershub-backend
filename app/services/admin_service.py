# app/services/admin_service.py
"""
管理员服务层
处理管理员相关的业务逻辑，主要是提供系统全局的概览统计数据。
[v2.0 SQLAlchemy 迁移版 - 最终完整功能]
"""

from typing import Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
import asyncio # 我们仍然需要导入它，只是不再使用 gather

# --- 导入所有需要进行统计的模型 ---
from app.models.user import User
from app.models.stuff import Stuff
from app.models.site import Site
from app.models.stuff_borrow import StuffBorrow
from app.models.site_borrow import SiteBorrow

class AdminService:
    """管理员服务类：处理管理员相关的业务逻辑"""
    
    async def get_overview_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """
        获取系统概览统计数据。
        所有查询将串行执行，以确保会话状态的正确性。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
        
        Returns:
            Dict: 包含各种真实统计数据的字典。
        """
        try:
            logger.info("[AdminService] 开始获取系统全局概览统计数据...")

            # --- 1. 【关键修复】串行执行所有统计查询 ---

            # 用户统计
            total_users = (await db.execute(select(func.count(User.id)))).scalar_one()
            active_users = (await db.execute(select(func.count(User.id)).where(User.state == 1))).scalar_one()
            banned_users = (await db.execute(select(func.count(User.id)).where(User.state == 0))).scalar_one()
            logger.info(f"用户统计完成: 总数={total_users}, 活跃={active_users}, 封禁={banned_users}")

            # 物资统计
            total_stuff = (await db.execute(select(func.count(Stuff.id)))).scalar_one()
            stuff_borrow_pending = (await db.execute(select(func.count(StuffBorrow.id)).where(StuffBorrow.state == 0))).scalar_one()
            stuff_borrow_active = (await db.execute(select(func.count(StuffBorrow.id)).where(StuffBorrow.state == 2))).scalar_one()
            logger.info(f"物资统计完成: 种类总数={total_stuff}, 待审核={stuff_borrow_pending}, 未归还={stuff_borrow_active}")

            # 场地统计
            total_sites = (await db.execute(select(func.count(func.distinct(Site.site))))).scalar_one()
            total_workstations = (await db.execute(select(func.count(Site.id)))).scalar_one()
            occupied_sites = (await db.execute(select(func.count(Site.id)).where(Site.is_occupied == True))).scalar_one()
            site_borrow_pending = (await db.execute(select(func.count(SiteBorrow.id)).where(SiteBorrow.state == 0))).scalar_one()
            site_borrow_active = (await db.execute(select(func.count(SiteBorrow.id)).where(SiteBorrow.state == 2))).scalar_one()
            logger.info(f"场地统计完成: 场地数={total_sites}, 工位数={total_workstations}, 已占用={occupied_sites}, 待审核={site_borrow_pending}, 未归还={site_borrow_active}")
            
            logger.success("[AdminService] 所有概览统计数据已成功获取。")

            # --- 2. 组装并返回最终数据结构 ---
            return {
                "users": {
                    "total": total_users,
                    "active": active_users,
                    "banned": banned_users
                },
                "stuff": {
                    "total": total_stuff,
                    "borrow_pending": stuff_borrow_pending,
                    "borrow_active": stuff_borrow_active
                },
                "sites": {
                    "total": total_sites,
                    "occupied": occupied_sites,
                    "available": total_workstations - occupied_sites,
                    "borrow_pending": site_borrow_pending,
                    "borrow_active": site_borrow_active
                }
            }
        except Exception as e:
            logger.error(f"获取系统概览统计数据时发生未知错误: {e}", exc_info=True)
            raise e