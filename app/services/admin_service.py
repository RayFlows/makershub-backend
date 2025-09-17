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
    
    # ========== 物资管理 ==========
    
    async def get_all_stuff(self) -> Dict[str, Any]:
        """获取所有物资（管理员视角）"""
        try:
            all_stuff = Stuff.objects()
            
            # 按类型分组
            stuff_dict = {}
            for item in all_stuff:
                if item.type not in stuff_dict:
                    stuff_dict[item.type] = []
                
                stuff_dict[item.type].append({
                    "stuff_id": item.stuff_id,
                    "stuff_name": item.stuff_name,
                    "number_total": item.number_total,
                    "number_remain": item.number_remain,
                    "description": item.description,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                    "updated_at": item.updated_at.isoformat() if item.updated_at else None
                })
            
            return {
                "total": all_stuff.count(),
                "types": stuff_dict
            }
        except Exception as e:
            logger.error(f"获取物资列表失败: {str(e)}")
            raise e
    
    async def add_stuff(self, stuff_data: dict) -> Dict[str, Any]:
        """添加物资"""
        try:
            # 生成物资ID
            timestamp = int(time.time() * 1000)
            stuff_id = f"ST{timestamp}_{random.randint(100, 999)}"
            
            new_stuff = Stuff(
                stuff_id=stuff_id,
                type=stuff_data.get("type"),
                stuff_name=stuff_data.get("stuff_name"),
                number_total=stuff_data.get("number_total", 0),
                number_remain=stuff_data.get("number_remain", 0),
                description=stuff_data.get("description", "")
            )
            
            # 如果提供了type_id，使用它；否则生成一个
            if stuff_data.get("type_id"):
                new_stuff.type_id = stuff_data.get("type_id")
            else:
                new_stuff.type_id = f"TP{timestamp}_{random.randint(100, 999)}"
            
            new_stuff.save()
            
            logger.info(f"添加物资成功: {stuff_id}")
            return {"stuff_id": stuff_id}
            
        except Exception as e:
            logger.error(f"添加物资失败: {str(e)}")
            raise e
    
    async def update_stuff(self, stuff_id: str, stuff_data: dict) -> Dict[str, Any]:
        """更新物资信息"""
        try:
            stuff = Stuff.objects(stuff_id=stuff_id).first()
            if not stuff:
                raise ValueError(f"物资不存在: {stuff_id}")
            
            # 更新字段
            if "stuff_name" in stuff_data:
                stuff.stuff_name = stuff_data["stuff_name"]
            if "number_total" in stuff_data:
                stuff.number_total = stuff_data["number_total"]
            if "number_remain" in stuff_data:
                stuff.number_remain = stuff_data["number_remain"]
            if "description" in stuff_data:
                stuff.description = stuff_data["description"]
            
            stuff.save()
            
            logger.info(f"更新物资成功: {stuff_id}")
            return {"stuff_id": stuff_id}
            
        except Exception as e:
            logger.error(f"更新物资失败: {str(e)}")
            raise e
    
    async def delete_stuff(self, stuff_id: str) -> bool:
        """删除物资"""
        try:
            stuff = Stuff.objects(stuff_id=stuff_id).first()
            if not stuff:
                raise ValueError(f"物资不存在: {stuff_id}")
            
            # 检查是否有未归还的借用记录
            active_borrows = StuffBorrow.objects(state__in=[0, 1, 2]).filter(
                stuff_list__contains=stuff.stuff_name
            ).count()
            
            if active_borrows > 0:
                raise ValueError(f"该物资有{active_borrows}个未完成的借用记录，无法删除")
            
            stuff.delete()
            logger.info(f"删除物资成功: {stuff_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除物资失败: {str(e)}")
            raise e
    
    # ========== 场地管理 ==========
    
    async def get_all_sites(self) -> Dict[str, Any]:
        """获取所有场地（管理员视角）"""
        try:
            all_sites = Site.objects()
            
            # 按场地位置分组
            sites_dict = {}
            for site in all_sites:
                if site.site not in sites_dict:
                    sites_dict[site.site] = {
                        "site_id": site.site_id,
                        "site": site.site,
                        "workstations": []
                    }
                
                sites_dict[site.site]["workstations"].append({
                    "number": site.number,
                    "is_occupied": site.is_occupied
                })
            
            # 转换为列表
            sites_list = list(sites_dict.values())
            
            return {
                "total": all_sites.count(),
                "sites": sites_list
            }
        except Exception as e:
            logger.error(f"获取场地列表失败: {str(e)}")
            raise e
    
    async def add_site(self, site_data: dict) -> Dict[str, Any]:
        """添加场地"""
        try:
            # 生成场地ID
            site_id = Site.generate_site_id()
            
            # 批量创建工位
            site_location = site_data.get("site")
            workstations = site_data.get("workstations", [])
            
            created_count = 0
            for ws in workstations:
                new_site = Site(
                    site_id=site_id,
                    site=site_location,
                    number=ws.get("number"),
                    is_occupied=False
                )
                new_site.save()
                created_count += 1
            
            logger.info(f"添加场地成功: {site_id}, 创建{created_count}个工位")
            return {
                "site_id": site_id,
                "created": created_count
            }
            
        except Exception as e:
            logger.error(f"添加场地失败: {str(e)}")
            raise e
    
    async def update_site(self, site_id: str, site_data: dict) -> Dict[str, Any]:
        """更新场地信息"""
        try:
            sites = Site.objects(site_id=site_id)
            if not sites:
                raise ValueError(f"场地不存在: {site_id}")
            
            updated_count = 0
            
            # 更新场地名称
            if "site" in site_data:
                for site in sites:
                    site.site = site_data["site"]
                    site.save()
                    updated_count += 1
            
            logger.info(f"更新场地成功: {site_id}, 更新{updated_count}条记录")
            return {
                "site_id": site_id,
                "updated": updated_count
            }
            
        except Exception as e:
            logger.error(f"更新场地失败: {str(e)}")
            raise e
    
    async def delete_site(self, site_id: str) -> bool:
        """删除场地"""
        try:
            sites = Site.objects(site_id=site_id)
            if not sites:
                raise ValueError(f"场地不存在: {site_id}")
            
            # 检查是否有占用的工位
            occupied_count = sites.filter(is_occupied=True).count()
            if occupied_count > 0:
                raise ValueError(f"该场地有{occupied_count}个工位正在使用中，无法删除")
            
            # 删除所有工位
            deleted_count = sites.delete()
            logger.info(f"删除场地成功: {site_id}, 删除{deleted_count}个工位")
            return True
            
        except Exception as e:
            logger.error(f"删除场地失败: {str(e)}")
            raise e
    
    # ========== 用户管理 ==========
    
    async def get_all_users(self) -> Dict[str, Any]:
        """获取所有用户（管理员视角）"""
        try:
            all_users = User.objects()
            
            users_list = []
            for user in all_users:
                users_list.append({
                    "userid": user.userid,
                    "maker_id": user.maker_id,
                    "real_name": user.real_name,
                    "phone_num": user.phone_num,
                    "role": user.role,
                    "department": user.department,
                    "state": user.state,
                    "score": user.score,
                    "total_dutytime": user.total_dutytime,
                    "created_at": user.created_at.isoformat() if user.created_at else None
                })
            
            return {
                "total": len(users_list),
                "users": users_list
            }
        except Exception as e:
            logger.error(f"获取用户列表失败: {str(e)}")
            raise e
    
    async def ban_user(self, user_id: str) -> bool:
        """封禁用户"""
        try:
            user = User.objects(userid=user_id).first()
            if not user:
                raise ValueError(f"用户不存在: {user_id}")
            
            user.state = 0  # 0表示封禁
            user.save()
            
            logger.info(f"封禁用户成功: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"封禁用户失败: {str(e)}")
            raise e
    
    async def unban_user(self, user_id: str) -> bool:
        """解封用户"""
        try:
            user = User.objects(userid=user_id).first()
            if not user:
                raise ValueError(f"用户不存在: {user_id}")
            
            user.state = 1  # 1表示正常
            user.save()
            
            logger.info(f"解封用户成功: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"解封用户失败: {str(e)}")
            raise e
    
    async def update_user_role(self, user_id: str, new_role: int) -> bool:
        """更新用户角色"""
        try:
            user = User.objects(userid=user_id).first()
            if not user:
                raise ValueError(f"用户不存在: {user_id}")
            
            user.role = new_role
            user.save()
            
            logger.info(f"更新用户角色成功: {user_id} -> 角色{new_role}")
            return True
            
        except Exception as e:
            logger.error(f"更新用户角色失败: {str(e)}")
            raise e