# app/services/admin_site_service.py
"""
管理员场地服务层
处理管理员端场地管理的业务逻辑。
[v.20 SQLAlchemy 迁移版]
"""
from typing import List, Dict, Any, Optional
from sqlalchemy import select, func, and_, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from datetime import datetime
import random

from app.models.site import Site
from app.models.site_borrow import SiteBorrow

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
        获取所有场地（管理员视图），并附带实时的借用信息。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            filters: 筛选条件，例如 {'site': 'B208+', 'is_occupied': True}。
        
        Returns:
            包含场地列表、实时借用信息和统计信息的字典。
        """
        try:
            logger.info(f"[AdminSiteService] 开始获取场地列表，筛选条件: {filters}")
            
            # 1. 查询所有场地工位，并根据筛选条件进行过滤
            stmt = select(Site).order_by(Site.site, Site.number)
            if filters:
                if filters.get('site'):
                    stmt = stmt.where(Site.site == filters.get('site'))
                    logger.debug(f"添加场地位置筛选: {filters.get('site')}")
                if filters.get('is_occupied') is not None:
                    is_occupied_val = str(filters.get('is_occupied')).lower() == 'true'
                    stmt = stmt.where(Site.is_occupied == is_occupied_val)
                    logger.debug(f"添加占用状态筛选: {is_occupied_val}")
            
            result = await db.execute(stmt)
            all_sites = result.scalars().all()
            logger.info(f"查询到 {len(all_sites)} 个场地工位")

            # 2. 【新】获取所有活跃的（未审核/已通过）借用申请，以丰富前端展示信息
            logger.debug("[AdminSiteService] 开始查询活跃的场地借用信息以附加到工位详情...")
            active_borrows_stmt = select(SiteBorrow).where(SiteBorrow.state.in_([0, 2])) # 0:未审核, 2:通过未归还
            active_borrows_res = await db.execute(active_borrows_stmt)
            active_borrows = active_borrows_res.scalars().all()
            
            # 构建一个便于快速查找的借用信息映射，键为 "site_id_number"
            borrow_map = {f"{borrow.site_id}_{borrow.number}": borrow for borrow in active_borrows}
            logger.debug(f"找到 {len(borrow_map)} 条活跃的借用记录。")

            # 3. 在内存中按场地位置分组，并附加借用信息
            sites_grouped = {}
            for site in all_sites:
                if site.site not in sites_grouped:
                    sites_grouped[site.site] = {
                        'site_id': site.site_id,
                        'site': site.site,
                        'details': [],
                        'total_count': 0,
                        'occupied_count': 0,
                        'available_count': 0
                    }
                
                detail = AdminSiteService._site_to_admin_dict(site)
                
                # 检查是否存在与此工位关联的活跃借用申请
                borrow_key = f"{site.site_id}_{site.number}"
                if borrow_key in borrow_map:
                    borrow_info = borrow_map[borrow_key]
                    state_map = {0: "待审核", 2: "已占用"}
                    detail['borrow_info'] = {
                        'apply_id': borrow_info.apply_id,
                        'borrower': borrow_info.name,
                        'purpose': borrow_info.purpose,
                        'state': borrow_info.state,
                        'state_text': state_map.get(borrow_info.state, "未知"),
                        'start_time': borrow_info.start_time.isoformat() if borrow_info.start_time else None,
                        'end_time': borrow_info.end_time.isoformat() if borrow_info.end_time else None,
                    }
                
                sites_grouped[site.site]['details'].append(detail)
                sites_grouped[site.site]['total_count'] += 1
                if site.is_occupied:
                    sites_grouped[site.site]['occupied_count'] += 1
                else:
                    sites_grouped[site.site]['available_count'] += 1
            
            sites_list = list(sites_grouped.values())
            
            # 4. 计算并组装全局统计信息
            total_workstations = len(all_sites)
            total_occupied = sum(1 for site in all_sites if site.is_occupied)
            stats = {
                'total_sites': len(sites_grouped),
                'total_workstations': total_workstations,
                'total_occupied': total_occupied,
                'total_available': total_workstations - total_occupied,
                'occupancy_rate': round((total_occupied / total_workstations * 100) if total_workstations > 0 else 0, 1)
            }
            
            # 5. 获取所有不重复的场地名称，用于前端筛选器的下拉列表
            all_sites_names_stmt = select(Site.site).distinct().order_by(Site.site)
            res = await db.execute(all_sites_names_stmt)
            available_locations = res.scalars().all()
            
            logger.success(f"[AdminSiteService] 场地列表及借用信息获取成功，返回 {len(sites_list)} 个场地")
            
            return {
                "code": 200,
                "message": "获取场地列表成功",
                "data": {
                    "sites_list": sites_list,
                    "stats": stats,
                    "available_locations": available_locations
                }
            }
        except Exception as e:
            logger.error(f"[AdminSiteService] 获取场地列表时发生未知错误: {e}", exc_info=True)
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
    async def update_site_admin(db: AsyncSession, site_name: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        【TODO 已完成】【事务】更新场地信息（管理员），包括修改名称、增删工位。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            site_name: 需要更新的场地名称。
            update_data: 更新数据，格式如 {"new_name": "...", "add_workstations": [...], "remove_workstations": [...]}。
        
        Returns:
            Dict: 更新结果。
        """
        async with db.begin_nested() as transaction:
            try:
                logger.info(f"[AdminSiteService] 开始更新场地: {site_name}")
                logger.debug(f"更新数据: {update_data}")
                
                # 1. 锁定该场地的所有工位记录
                stmt = select(Site).where(Site.site == site_name).with_for_update()
                result = await db.execute(stmt)
                sites = result.scalars().all()

                if not sites:
                    logger.warning(f"[AdminSiteService] 场地不存在: {site_name}")
                    raise ValueError(f"场地不存在: {site_name}")
                
                site_id = sites[0].site_id
                changes = []
                
                # 2. 更新场地名称
                new_name = update_data.get('new_name')
                if new_name and new_name != site_name:
                    logger.info(f"准备更新场地名称: {site_name} -> {new_name}")
                    # 检查新名称是否已存在
                    if (await db.execute(select(Site.id).where(Site.site == new_name).limit(1))).scalar_one_or_none():
                        raise ValueError(f"场地名称 '{new_name}' 已存在")
                    
                    # 更新所有相关工位的场地名称
                    for site in sites:
                        site.site = new_name
                        db.add(site)
                    
                    # 【重要】同步更新所有相关借用申请记录中的场地名称
                    await db.execute(update(SiteBorrow).where(SiteBorrow.site == site_name).values(site=new_name))
                    
                    changes.append(f"场地名称: {site_name} -> {new_name}")
                    site_name = new_name # 更新后续操作的场地名称
                
                # 3. 添加新工位
                add_workstations = update_data.get('add_workstations', [])
                if add_workstations:
                    existing_numbers = {s.number for s in sites}
                    added_count = 0
                    for number in add_workstations:
                        if number in existing_numbers:
                            logger.warning(f"工位 {number} 在场地 {site_name} 已存在，跳过新增")
                            continue
                        new_site = Site(site_id=site_id, site=site_name, number=int(number), is_occupied=False)
                        db.add(new_site)
                        added_count += 1
                    if added_count > 0:
                        changes.append(f"新增 {added_count} 个工位")

                # 4. 删除工位
                remove_workstations = update_data.get('remove_workstations', [])
                if remove_workstations:
                    removed_count = 0
                    sites_to_remove = {s.number: s for s in sites if s.number in remove_workstations}
                    for number in remove_workstations:
                        if number not in sites_to_remove:
                            logger.warning(f"工位 {number} 在场地 {site_name} 不存在，跳过删除")
                            continue
                        
                        site_to_remove = sites_to_remove[number]
                        if site_to_remove.is_occupied:
                            logger.warning(f"工位 {number} 正在被占用，不能删除")
                            raise ValueError(f"工位 {number} 正在被占用，不能删除")
                        
                        await db.delete(site_to_remove)
                        removed_count += 1
                    if removed_count > 0:
                        changes.append(f"删除 {removed_count} 个工位")
                
                if not changes:
                    return {"code": 200, "message": "没有任何变更", "data": {"site": site_name, "changes": []}}
                
                logger.success(f"[AdminSiteService] 场地 {site_name} 更新成功，变更: {', '.join(changes)}")
                return {"code": 200, "message": "场地更新成功", "data": {"site": site_name, "changes": changes}}
            
            except ValueError as e:
                await transaction.rollback()
                raise e
            except Exception as e:
                await transaction.rollback()
                logger.error(f"[AdminSiteService] 更新场地失败: {e}", exc_info=True)
                raise Exception(f"更新场地失败: {str(e)}")

    @staticmethod
    async def delete_site_admin(db: AsyncSession, site_name: str) -> Dict[str, Any]:
        """
        【事务】删除整个场地及其所有工位（管理员）。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            site_name: 要删除的场地名称。
        
        Returns:
            删除结果的字典。
        """
        async with db.begin_nested() as transaction:
            try:
                logger.info(f"[AdminSiteService] 开始删除场地: {site_name}")
                
                # 1. 查找并锁定该场地的所有工位
                stmt = select(Site).where(Site.site == site_name).with_for_update()
                result = await db.execute(stmt)
                sites_to_delete = result.scalars().all()

                if not sites_to_delete:
                    raise ValueError(f"场地不存在: {site_name}")
                
                # 2. 检查是否有被占用的工位
                occupied_count = sum(1 for s in sites_to_delete if s.is_occupied)
                if occupied_count > 0:
                    raise ValueError(f"该场地有 {occupied_count} 个工位正在被占用，不能删除")

                # 3. 【新】检查是否有未完成的借用申请
                active_borrows_stmt = select(func.count(SiteBorrow.id)).where(
                    SiteBorrow.site == site_name,
                    SiteBorrow.state.in_([0, 1, 2]) # 0:未审核, 1:打回, 2:通过未归还
                )
                active_borrows_count = (await db.execute(active_borrows_stmt)).scalar_one()
                if active_borrows_count > 0:
                    logger.warning(f"[AdminSiteService] 场地 {site_name} 有 {active_borrows_count} 个未完成的借用申请，无法删除。")
                    raise ValueError(f"该场地有 {active_borrows_count} 个未完成的借用申请，不能删除")
                
                # 4. 执行删除
                site_id = sites_to_delete[0].site_id
                total_workstations = len(sites_to_delete)
                
                # SQLAlchemy 2.0 style bulk delete
                delete_stmt = delete(Site).where(Site.site == site_name)
                await db.execute(delete_stmt)
                
                logger.success(f"[AdminSiteService] 场地删除成功 | ID: {site_id} | 名称: {site_name} | 删除工位数: {total_workstations}")
                return {
                    "code": 200, "message": "场地删除成功",
                    "data": {"site_id": site_id, "site": site_name, "deleted_workstations": total_workstations}
                }
            except ValueError as e:
                await transaction.rollback()
                raise e
            except Exception as e:
                await transaction.rollback()
                logger.error(f"[AdminSiteService] 删除场地失败: {e}", exc_info=True)
                raise Exception(f"删除场地失败: {str(e)}")

    @staticmethod
    async def get_site_borrow_history(db: AsyncSession, site_name: str) -> Dict[str, Any]:
        """
        获取场地借用历史（管理员）。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            site_name: 场地名称。
        
        Returns:
            Dict: 借用历史记录。
        """
        try:
            logger.info(f"[AdminSiteService] 获取场地 '{site_name}' 的借用历史...")
            
            stmt = select(SiteBorrow).where(SiteBorrow.site == site_name).order_by(SiteBorrow.created_at.desc())
            result = await db.execute(stmt)
            borrows = result.scalars().all()
            
            borrow_list = []
            state_map = {0: "未审核", 1: "已打回", 2: "通过未归还", 3: "已归还", 4: "已取消"}
            for borrow in borrows:
                borrow_list.append({
                    'apply_id': borrow.apply_id, 'borrower': borrow.name, 'student_id': borrow.student_id,
                    'phone': borrow.phone_num, 'workstation': borrow.number, 'purpose': borrow.purpose,
                    'start_time': borrow.start_time.isoformat() if borrow.start_time else None,
                    'end_time': borrow.end_time.isoformat() if borrow.end_time else None,
                    'state': borrow.state, 'state_text': state_map.get(borrow.state, "未知状态"),
                    'review': borrow.review,
                    'created_at': borrow.created_at.isoformat() + "Z" if borrow.created_at else None
                })
            
            stats = {
                'total_borrows': len(borrow_list),
                'pending': sum(1 for b in borrows if b.state == 0),
                'rejected': sum(1 for b in borrows if b.state == 1),
                'approved': sum(1 for b in borrows if b.state == 2),
                'returned': sum(1 for b in borrows if b.state == 3),
                'cancelled': sum(1 for b in borrows if b.state == 4)
            }
            
            logger.success(f"成功获取场地 '{site_name}' 的 {len(borrow_list)} 条借用历史。")
            return {
                "code": 200, "message": "获取借用历史成功",
                "data": {"site": site_name, "borrow_history": borrow_list, "stats": stats}
            }
        except Exception as e:
            logger.error(f"[AdminSiteService] 获取借用历史失败: {e}", exc_info=True)
            raise Exception(f"获取借用历史失败: {str(e)}")