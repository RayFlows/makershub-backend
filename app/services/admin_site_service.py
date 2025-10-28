# app/services/admin_site_service.py
"""
管理员场地服务层
处理管理员端场地管理的业务逻辑。
[v.20 SQLAlchemy 迁移版]
"""
from typing import List, Dict, Any, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from datetime import datetime
import random

from app.models.site import Site
# TODO: 待SiteBorrow模块迁移后，需要从这里导入SiteBorrow模型
# from app.models.site_borrow import SiteBorrow

class AdminSiteService:
    """管理员场地服务类：处理管理员端场地相关的业务逻辑。"""
    
    @staticmethod
    def _generate_site_id() -> str:
        """
        生成场地ID: ST + 当前时间戳(精确到毫秒) + 3位随机数。
        这是一个独立的辅助函数，用于生成唯一的场地标识。
        """
        now = datetime.utcnow()
        timestamp = now.strftime("%Y%m%d%H%M%S%f")[:-3]
        random_suffix = f"{random.randint(0,999):03d}"
        return f"ST{timestamp}_{random_suffix}"
    
    @staticmethod
    def _site_to_admin_dict(site: Site) -> dict:
        """辅助函数：将Site ORM对象转换为管理员视图的工位详情字典。"""
        return {
            'number': site.number,
            'is_occupied': site.is_occupied,
            'created_at': site.created_at.isoformat() + "Z" if site.created_at else None
        }

    @staticmethod
    async def get_all_sites_admin(db: AsyncSession, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        获取所有场地（管理员视图）。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            filters: 筛选条件。
        
        Returns:
            包含场地列表和统计信息的字典。
        """
        try:
            logger.info(f"[AdminSiteService] 开始获取场地列表，筛选条件: {filters}")
            
            stmt = select(Site).order_by(Site.site, Site.number)
            # 构建动态查询条件
            if filters:
                if filters.get('site'):
                    stmt = stmt.where(Site.site == filters.get('site'))
                if filters.get('is_occupied') is not None:
                    is_occupied_val = str(filters.get('is_occupied')).lower() == 'true'
                    stmt = stmt.where(Site.is_occupied == is_occupied_val)

            result = await db.execute(stmt)
            all_sites = result.scalars().all()
            logger.info(f"查询到 {len(all_sites)} 个场地工位")
            
            # 按场地位置分组 (业务逻辑不变)
            sites_grouped = {}
            for site in all_sites:
                if site.site not in sites_grouped:
                    sites_grouped[site.site] = {
                        'site_id': site.site_id, 'site': site.site, 'details': [],
                        'total_count': 0, 'occupied_count': 0, 'available_count': 0
                    }
                sites_grouped[site.site]['details'].append(AdminSiteService._site_to_admin_dict(site))
                sites_grouped[site.site]['total_count'] += 1
                if site.is_occupied:
                    sites_grouped[site.site]['occupied_count'] += 1
                else:
                    sites_grouped[site.site]['available_count'] += 1
            
            # TODO: 借用信息获取逻辑将在SiteBorrow模块迁移后恢复。
            logger.warning("[AdminSiteService] 场地借用信息获取功能暂未迁移，将返回空数据。")

            sites_list = list(sites_grouped.values())
            
            # 统计信息 (基于当前查询结果)
            total_workstations = len(all_sites)
            total_occupied = sum(1 for site in all_sites if site.is_occupied)
            stats = {
                'total_sites': len(sites_grouped),
                'total_workstations': total_workstations,
                'total_occupied': total_occupied,
                'total_available': total_workstations - total_occupied,
                'occupancy_rate': round((total_occupied / total_workstations * 100) if total_workstations > 0 else 0, 1)
            }
            
            # 获取所有场地名称用于筛选框
            all_sites_names_stmt = select(Site.site).distinct().order_by(Site.site)
            res = await db.execute(all_sites_names_stmt)
            available_locations = res.scalars().all()
            
            logger.info(f"[AdminSiteService] 场地列表获取成功，返回 {len(sites_list)} 个场地")
            
            return {
                "code": 200, "message": "获取场地列表成功",
                "data": {"sites_list": sites_list, "stats": stats, "available_locations": available_locations}
            }
        except Exception as e:
            logger.error(f"[AdminSiteService] 获取场地列表失败: {e}", exc_info=True)
            raise Exception(f"获取场地列表失败: {str(e)}")
    
    @staticmethod
    async def create_site_admin(db: AsyncSession, site_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建新场地（管理员）。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            site_data: 包含场地名称和工位号列表的字典。
        
        Returns:
            创建结果的字典。
        """
        try:
            site_name = site_data.get('site')
            workstations = site_data.get('workstations', [])
            
            if not site_name: raise ValueError("场地名称不能为空")
            if not workstations: raise ValueError("至少需要一个工位")
            
            logger.info(f"[AdminSiteService] 开始创建场地: {site_name}, 工位数: {len(workstations)}")
            
            stmt = select(Site.id).where(Site.site == site_name).limit(1)
            if (await db.execute(stmt)).scalar_one_or_none():
                raise ValueError(f"场地 '{site_name}' 已存在")
            
            site_id = AdminSiteService._generate_site_id()
            logger.debug(f"生成的site_id: {site_id}")
            
            new_sites = [
                Site(site_id=site_id, site=site_name, number=int(number), is_occupied=False)
                for number in workstations
            ]
            
            db.add_all(new_sites)
            await db.commit()
            
            logger.info(f"[AdminSiteService] 场地创建成功: {site_id} - {site_name}, 创建了 {len(new_sites)} 个工位")
            return {
                "code": 200, "message": "场地创建成功",
                "data": {"site_id": site_id, "site": site_name, "created_count": len(new_sites)}
            }
        except ValueError as e:
            await db.rollback()
            logger.warning(f"[AdminSiteService] 场地数据验证失败: {e}")
            raise ValueError(str(e))
        except Exception as e:
            await db.rollback()
            logger.error(f"[AdminSiteService] 创建场地失败: {e}", exc_info=True)
            raise Exception(f"创建场地失败: {str(e)}")

    @staticmethod
    async def delete_site_admin(db: AsyncSession, site_name: str) -> Dict[str, Any]:
        """
        删除整个场地及其所有工位（管理员）。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            site_name: 要删除的场地名称。
        
        Returns:
            删除结果的字典。
        """
        try:
            logger.info(f"[AdminSiteService] 开始删除场地: {site_name}")
            
            stmt = select(Site).where(Site.site == site_name)
            result = await db.execute(stmt)
            sites_to_delete = result.scalars().all()

            if not sites_to_delete:
                logger.warning(f"[AdminSiteService] 场地不存在: {site_name}")
                raise ValueError(f"场地不存在: {site_name}")
            
            occupied_count = sum(1 for s in sites_to_delete if s.is_occupied)
            if occupied_count > 0:
                logger.warning(f"[AdminSiteService] 场地有 {occupied_count} 个工位被占用，不能删除")
                raise ValueError(f"该场地有 {occupied_count} 个工位正在被占用，不能删除")

            # TODO: 待SiteBorrow模块迁移后，需要在这里添加检查是否有未完成的借用申请。
            logger.warning(f"[AdminSiteService] 场地借用申请检查功能暂未迁移，将直接执行删除。")
            
            total_workstations = len(sites_to_delete)
            site_id = sites_to_delete[0].site_id

            for site in sites_to_delete:
                await db.delete(site)
            await db.commit()
            
            logger.info(f"[AdminSiteService] 场地删除成功 | ID: {site_id} | 名称: {site_name} | 删除工位数: {total_workstations}")
            return {
                "code": 200, "message": "场地删除成功",
                "data": {"site_id": site_id, "site": site_name, "deleted_workstations": total_workstations}
            }
        except ValueError as e:
            await db.rollback()
            raise e
        except Exception as e:
            await db.rollback()
            logger.error(f"[AdminSiteService] 删除场地失败: {e}", exc_info=True)
            raise Exception(f"删除场地失败: {str(e)}")

    # 其他 admin_site_service.py 中的方法 (update_site_admin, get_site_borrow_history) 
    # 依赖更复杂的逻辑或 SiteBorrow，我们将暂时将它们从服务中移除或简化，
    # 在迁移 SiteBorrow 模块时再完整实现。
    # 这样做可以确保我们当前提交的代码是可运行的。
    

    # @staticmethod
    # def update_site_admin(site_name: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    #     """
    #     更新场地信息（管理员）
        
    #     Args:
    #         site_name: 场地名称
    #         update_data: 更新数据
    #             {
    #                 "new_name": "新场地名称",
    #                 "add_workstations": [4, 5],  # 新增工位
    #                 "remove_workstations": [1]    # 删除工位
    #             }
        
    #     Returns:
    #         Dict: 更新结果
    #     """
    #     try:
    #         logger.info(f"[AdminSiteService] 开始更新场地: {site_name}")
    #         logger.debug(f"更新数据: {update_data}")
            
    #         # 查找场地
    #         sites = Site.objects(site=site_name)
    #         if not sites:
    #             logger.warning(f"[AdminSiteService] 场地不存在: {site_name}")
    #             raise ValueError(f"场地不存在: {site_name}")
            
    #         site_id = sites.first().site_id
    #         changes = []
            
    #         # 更新场地名称
    #         new_name = update_data.get('new_name')
    #         if new_name and new_name != site_name:
    #             # 检查新名称是否已存在
    #             if Site.objects(site=new_name).first():
    #                 raise ValueError(f"场地名称 '{new_name}' 已存在")
                
    #             # 更新所有工位的场地名称
    #             sites.update(site=new_name)
    #             changes.append(f"场地名称: {site_name} -> {new_name}")
    #             logger.info(f"场地名称更新: {site_name} -> {new_name}")
                
    #             # 同时更新借用记录中的场地名称
    #             SiteBorrow.objects(site=site_name).update(site=new_name)
    #             site_name = new_name  # 更新后续操作的场地名称
            
    #         # 添加新工位
    #         add_workstations = update_data.get('add_workstations', [])
    #         added_count = 0
    #         for number in add_workstations:
    #             if Site.objects(site=site_name, number=number).first():
    #                 logger.warning(f"工位 {number} 已存在，跳过")
    #                 continue
                
    #             new_site = Site(
    #                 site_id=site_id,
    #                 site=site_name,
    #                 number=int(number),
    #                 is_occupied=False
    #             )
    #             new_site.save()
    #             added_count += 1
            
    #         if added_count > 0:
    #             changes.append(f"新增 {added_count} 个工位")
            
    #         # 删除工位
    #         remove_workstations = update_data.get('remove_workstations', [])
    #         removed_count = 0
    #         for number in remove_workstations:
    #             site_to_remove = Site.objects(site=site_name, number=number).first()
    #             if not site_to_remove:
    #                 logger.warning(f"工位 {number} 不存在，跳过")
    #                 continue
                
    #             # 检查工位是否被占用
    #             if site_to_remove.is_occupied:
    #                 logger.warning(f"工位 {number} 正在被占用，不能删除")
    #                 raise ValueError(f"工位 {number} 正在被占用，不能删除")
                
    #             site_to_remove.delete()
    #             removed_count += 1
            
    #         if removed_count > 0:
    #             changes.append(f"删除 {removed_count} 个工位")
            
    #         logger.info(f"[AdminSiteService] 场地更新成功，变更: {', '.join(changes)}")
            
    #         return {
    #             "code": 200,
    #             "message": "场地更新成功",
    #             "data": {
    #                 "site": site_name,
    #                 "changes": changes
    #             }
    #         }
            
    #     except ValueError as e:
    #         raise e
    #     except Exception as e:
    #         logger.error(f"[AdminSiteService] 更新场地失败: {str(e)}", exc_info=True)
    #         raise Exception(f"更新场地失败: {str(e)}")
    
    
    # @staticmethod
    # def get_site_borrow_history(site_name: str) -> Dict[str, Any]:
    #     """
    #     获取场地借用历史（管理员）
        
    #     Args:
    #         site_name: 场地名称
        
    #     Returns:
    #         Dict: 借用历史记录
    #     """
    #     try:
    #         logger.info(f"[AdminSiteService] 获取场地借用历史: {site_name}")
            
    #         # 查询该场地的所有借用记录
    #         borrows = SiteBorrow.objects(site=site_name).order_by('-created_at')
            
    #         borrow_list = []
    #         for borrow in borrows:
    #             borrow_list.append({
    #                 'apply_id': borrow.apply_id,
    #                 'borrower': borrow.name,
    #                 'student_id': borrow.student_id,
    #                 'phone': borrow.phone_num,
    #                 'workstation': borrow.number,
    #                 'purpose': borrow.purpose,
    #                 'start_time': borrow.start_time,
    #                 'end_time': borrow.end_time,
    #                 'state': borrow.state,
    #                 'state_text': ['未审核', '打回', '通过未归还', '已归还', '取消'][borrow.state] if borrow.state < 5 else '未知',
    #                 'review': borrow.review,
    #                 'created_at': borrow.created_at.isoformat() + "Z" if borrow.created_at else None
    #             })
            
    #         # 统计
    #         stats = {
    #             'total_borrows': len(borrow_list),
    #             'pending': sum(1 for b in borrows if b.state == 0),
    #             'rejected': sum(1 for b in borrows if b.state == 1),
    #             'approved': sum(1 for b in borrows if b.state == 2),
    #             'returned': sum(1 for b in borrows if b.state == 3),
    #             'cancelled': sum(1 for b in borrows if b.state == 4)
    #         }
            
    #         return {
    #             "code": 200,
    #             "message": "获取借用历史成功",
    #             "data": {
    #                 "site": site_name,
    #                 "borrow_history": borrow_list,
    #                 "stats": stats
    #             }
    #         }
            
    #     except Exception as e:
    #         logger.error(f"[AdminSiteService] 获取借用历史失败: {str(e)}", exc_info=True)
    #         raise Exception(f"获取借用历史失败: {str(e)}")