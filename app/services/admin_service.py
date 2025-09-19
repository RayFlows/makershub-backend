# app/services/admin_service.py
"""
管理员服务层
处理管理员相关的业务逻辑，直接操作数据库
"""

from typing import List, Dict, Any, Optional
from app.models.user import User
from app.models.stuff import Stuff
from app.models.site import Site
from app.models.stuff_borrow import StuffBorrow
from app.models.site_borrow import SiteBorrow
from loguru import logger
import time
import random

class AdminService:
    """管理员服务类：处理管理员相关的业务逻辑"""
    
    async def get_overview_stats(self) -> Dict[str, Any]:
        """
        获取系统概览统计数据
        
        Returns:
            Dict: 包含各种统计数据的字典
        """
        try:
            # 统计用户数据
            total_users = User.objects().count()
            active_users = User.objects(state=1).count()
            banned_users = User.objects(state=0).count()
            
            # 统计物资数据
            total_stuff = Stuff.objects().count()
            
            # 统计场地数据
            total_sites = Site.objects().count()
            occupied_sites = Site.objects(is_occupied=True).count()
            
            # 统计借用数据
            stuff_borrow_pending = StuffBorrow.objects(state=0).count()  # 未审核
            stuff_borrow_approved = StuffBorrow.objects(state=2).count()  # 通过未归还
            
            site_borrow_pending = SiteBorrow.objects(state=0).count()  # 未审核
            site_borrow_approved = SiteBorrow.objects(state=2).count()  # 通过未归还
            
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
                    "available": total_sites - occupied_sites,
                    "borrow_pending": site_borrow_pending,
                    "borrow_active": site_borrow_approved
                }
            }
        except Exception as e:
            logger.error(f"获取统计数据失败: {str(e)}")
            raise e