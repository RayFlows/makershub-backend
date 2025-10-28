# app/services/admin_service.py
"""
管理员服务层
处理管理员相关的业务逻辑，直接操作数据库。
[v2.0 SQLAlchemy 迁移版 - 修复并完善统计]
"""

from typing import Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

# --- 导入所有已迁移的模型 ---
from app.models.user import User
from app.models.stuff import Stuff
from app.models.site import Site
# from app.models.stuff_borrow import StuffBorrow # 暂时不导入
# from app.models.site_borrow import SiteBorrow # 暂时不导入

class AdminService:
    """管理员服务类：处理管理员相关的业务逻辑。"""
    
    async def get_overview_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """
        获取系统概览统计数据。
        [迁移中]：用户、物资、场地统计为实时数据。借用统计暂时返回0。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
        
        Returns:
            Dict: 包含各种统计数据的字典。
        """
        try:
            logger.info("开始获取系统概览统计数据...")

            # --- 1. 统计用户数据 ---
            total_users_stmt = select(func.count(User.id))
            active_users_stmt = select(func.count(User.id)).where(User.state == 1)
            banned_users_stmt = select(func.count(User.id)).where(User.state == 0)
            
            total_users_res, active_users_res, banned_users_res = await db.execute(total_users_stmt), await db.execute(active_users_stmt), await db.execute(banned_users_stmt)
            
            total_users = total_users_res.scalar_one()
            active_users = active_users_res.scalar_one()
            banned_users = banned_users_res.scalar_one()
            logger.info(f"用户统计完成: 总数={total_users}, 活跃={active_users}, 封禁={banned_users}")

            # --- 2. 统计物资数据 ---
            total_stuff_stmt = select(func.count(Stuff.id)) # 统计物资种类总数
            total_stuff_res = await db.execute(total_stuff_stmt)
            total_stuff = total_stuff_res.scalar_one()
            logger.info(f"物资统计完成: 种类总数={total_stuff}")

            # --- 3. 统计场地数据 ---
            total_sites_stmt = select(func.count(func.distinct(Site.site)))
            total_workstations_stmt = select(func.count(Site.id))
            occupied_sites_stmt = select(func.count(Site.id)).where(Site.is_occupied == True)

            total_sites_res, total_workstations_res, occupied_sites_res = await db.execute(total_sites_stmt), await db.execute(total_workstations_stmt), await db.execute(occupied_sites_stmt)
            
            total_sites = total_sites_res.scalar_one()
            total_workstations = total_workstations_res.scalar_one()
            occupied_sites = occupied_sites_res.scalar_one()
            logger.info(f"场地统计完成: 场地数={total_sites}, 工位总数={total_workstations}, 已占用={occupied_sites}")
            
            # --- 4. 未迁移：借用数据仍然返回模拟/固定数据 ---
            logger.warning("借用模块尚未迁移，相关统计数据将返回0。")
            stuff_borrow_pending = 0
            stuff_borrow_approved = 0
            site_borrow_pending = 0
            site_borrow_approved = 0
            
            return {
                "users": {
                    "total": total_users,
                    "active": active_users,
                    "banned": banned_users
                },
                "stuff": {
                    "total": total_stuff,
                    "borrow_pending": stuff_borrow_pending,
                    "borrow_active": stuff_borrow_approved
                },
                "sites": {
                    "total": total_sites,
                    "occupied": occupied_sites,
                    "available": total_workstations - occupied_sites,
                    "borrow_pending": site_borrow_pending,
                    "borrow_active": site_borrow_approved
                }
            }
        except Exception as e:
            logger.error(f"获取统计数据失败: {e}", exc_info=True)
            raise e