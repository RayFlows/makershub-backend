# app/services/admin_site_service.py
"""
管理员场地服务层
处理管理员端场地管理的业务逻辑
"""

from typing import List, Dict, Any, Optional
from app.models.site import Site
from app.models.site_borrow import SiteBorrow
from mongoengine.errors import NotUniqueError, ValidationError
from app.core.logging import logger
from datetime import datetime

class AdminSiteService:
    """管理员场地服务类：处理管理员端场地相关的业务逻辑"""
    
    @staticmethod
    def get_all_sites_admin(filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        获取所有场地（管理员视图）
        
        Args:
            filters: 筛选条件
                - site: 场地位置
                - is_occupied: 占用状态
        
        Returns:
            Dict: 包含场地列表和统计信息
        """
        try:
            logger.info(f"[AdminSiteService] 开始获取场地列表，筛选条件: {filters}")
            
            # 构建查询条件
            query = {}
            if filters:
                if filters.get('site'):
                    query['site'] = filters['site']
                    logger.debug(f"添加场地位置筛选: {filters['site']}")
                
                if filters.get('is_occupied') is not None:
                    # 处理字符串转布尔值
                    if isinstance(filters['is_occupied'], str):
                        query['is_occupied'] = filters['is_occupied'].lower() == 'true'
                    else:
                        query['is_occupied'] = bool(filters['is_occupied'])
                    logger.debug(f"添加占用状态筛选: {query['is_occupied']}")
            
            # 执行查询
            all_sites = Site.objects(**query).order_by('site', 'number')
            logger.info(f"查询到 {len(all_sites)} 个场地工位")
            
            # 按场地位置分组
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
                
                sites_grouped[site.site]['details'].append({
                    'number': site.number,
                    'is_occupied': site.is_occupied,
                    'created_at': site.created_at.isoformat() + "Z" if site.created_at else None
                })
                
                # 更新统计
                sites_grouped[site.site]['total_count'] += 1
                if site.is_occupied:
                    sites_grouped[site.site]['occupied_count'] += 1
                else:
                    sites_grouped[site.site]['available_count'] += 1
            
            # 获取借用信息
            active_borrows = SiteBorrow.objects(state__in=[0, 1, 2]).only(
                'site_id', 'site', 'number', 'name', 'purpose', 'state', 'start_time', 'end_time'
            )
            
            # 构建借用映射
            borrow_map = {}
            for borrow in active_borrows:
                key = f"{borrow.site}_{borrow.number}"
                borrow_map[key] = {
                    'apply_id': borrow.apply_id,
                    'borrower': borrow.name,
                    'purpose': borrow.purpose,
                    'state': borrow.state,
                    'state_text': ['未审核', '打回', '通过未归还', '已归还', '取消'][borrow.state] if borrow.state < 5 else '未知',
                    'start_time': borrow.start_time,
                    'end_time': borrow.end_time
                }
            
            # 将借用信息附加到场地详情中
            for site_name, site_data in sites_grouped.items():
                for detail in site_data['details']:
                    key = f"{site_name}_{detail['number']}"
                    if key in borrow_map:
                        detail['borrow_info'] = borrow_map[key]
            
            # 转换为列表格式
            sites_list = list(sites_grouped.values())
            
            # 统计信息
            stats = {
                'total_sites': len(sites_grouped),  # 场地数量
                'total_workstations': len(all_sites),  # 工位总数
                'total_occupied': sum(1 for site in all_sites if site.is_occupied),
                'total_available': sum(1 for site in all_sites if not site.is_occupied),
                'occupancy_rate': round(
                    (sum(1 for site in all_sites if site.is_occupied) / len(all_sites) * 100) if all_sites else 0,
                    1
                )
            }
            
            # 获取可用场地位置列表
            available_locations = Site.objects().distinct('site')
            
            logger.info(f"[AdminSiteService] 场地列表获取成功，返回 {len(sites_list)} 个场地")
            
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
            logger.error(f"[AdminSiteService] 获取场地列表失败: {str(e)}", exc_info=True)
            raise Exception(f"获取场地列表失败: {str(e)}")
    
    @staticmethod
    def create_site_admin(site_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建新场地（管理员）
        
        Args:
            site_data: 场地数据
                {
                    "site": "场地名称",
                    "workstations": [1, 2, 3, ...]  # 工位号列表
                }
        
        Returns:
            Dict: 创建结果
        """
        try:
            site_name = site_data.get('site')
            workstations = site_data.get('workstations', [])
            
            if not site_name:
                raise ValueError("场地名称不能为空")
            if not workstations:
                raise ValueError("至少需要一个工位")
            
            logger.info(f"[AdminSiteService] 开始创建场地: {site_name}, 工位数: {len(workstations)}")
            
            # 检查场地是否已存在
            existing = Site.objects(site=site_name).first()
            if existing:
                raise ValueError(f"场地 '{site_name}' 已存在")
            
            # 生成场地ID
            site_id = Site.generate_site_id()
            logger.debug(f"生成的site_id: {site_id}")
            
            # 批量创建工位
            created_count = 0
            for number in workstations:
                # 检查工位号是否重复
                if Site.objects(site=site_name, number=number).first():
                    logger.warning(f"工位 {number} 在场地 {site_name} 已存在，跳过")
                    continue
                
                new_site = Site(
                    site_id=site_id,
                    site=site_name,
                    number=int(number),
                    is_occupied=False
                )
                new_site.save()
                created_count += 1
            
            logger.info(f"[AdminSiteService] 场地创建成功: {site_id} - {site_name}, 创建了 {created_count} 个工位")
            
            return {
                "code": 200,
                "message": "场地创建成功",
                "data": {
                    "site_id": site_id,
                    "site": site_name,
                    "created_count": created_count
                }
            }
            
        except ValueError as e:
            logger.warning(f"[AdminSiteService] 场地数据验证失败: {str(e)}")
            raise ValueError(str(e))
        except Exception as e:
            logger.error(f"[AdminSiteService] 创建场地失败: {str(e)}", exc_info=True)
            raise Exception(f"创建场地失败: {str(e)}")
    
    @staticmethod
    def update_site_admin(site_name: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新场地信息（管理员）
        
        Args:
            site_name: 场地名称
            update_data: 更新数据
                {
                    "new_name": "新场地名称",
                    "add_workstations": [4, 5],  # 新增工位
                    "remove_workstations": [1]    # 删除工位
                }
        
        Returns:
            Dict: 更新结果
        """
        try:
            logger.info(f"[AdminSiteService] 开始更新场地: {site_name}")
            logger.debug(f"更新数据: {update_data}")
            
            # 查找场地
            sites = Site.objects(site=site_name)
            if not sites:
                logger.warning(f"[AdminSiteService] 场地不存在: {site_name}")
                raise ValueError(f"场地不存在: {site_name}")
            
            site_id = sites.first().site_id
            changes = []
            
            # 更新场地名称
            new_name = update_data.get('new_name')
            if new_name and new_name != site_name:
                # 检查新名称是否已存在
                if Site.objects(site=new_name).first():
                    raise ValueError(f"场地名称 '{new_name}' 已存在")
                
                # 更新所有工位的场地名称
                sites.update(site=new_name)
                changes.append(f"场地名称: {site_name} -> {new_name}")
                logger.info(f"场地名称更新: {site_name} -> {new_name}")
                
                # 同时更新借用记录中的场地名称
                SiteBorrow.objects(site=site_name).update(site=new_name)
                site_name = new_name  # 更新后续操作的场地名称
            
            # 添加新工位
            add_workstations = update_data.get('add_workstations', [])
            added_count = 0
            for number in add_workstations:
                if Site.objects(site=site_name, number=number).first():
                    logger.warning(f"工位 {number} 已存在，跳过")
                    continue
                
                new_site = Site(
                    site_id=site_id,
                    site=site_name,
                    number=int(number),
                    is_occupied=False
                )
                new_site.save()
                added_count += 1
            
            if added_count > 0:
                changes.append(f"新增 {added_count} 个工位")
            
            # 删除工位
            remove_workstations = update_data.get('remove_workstations', [])
            removed_count = 0
            for number in remove_workstations:
                site_to_remove = Site.objects(site=site_name, number=number).first()
                if not site_to_remove:
                    logger.warning(f"工位 {number} 不存在，跳过")
                    continue
                
                # 检查工位是否被占用
                if site_to_remove.is_occupied:
                    logger.warning(f"工位 {number} 正在被占用，不能删除")
                    raise ValueError(f"工位 {number} 正在被占用，不能删除")
                
                site_to_remove.delete()
                removed_count += 1
            
            if removed_count > 0:
                changes.append(f"删除 {removed_count} 个工位")
            
            logger.info(f"[AdminSiteService] 场地更新成功，变更: {', '.join(changes)}")
            
            return {
                "code": 200,
                "message": "场地更新成功",
                "data": {
                    "site": site_name,
                    "changes": changes
                }
            }
            
        except ValueError as e:
            raise e
        except Exception as e:
            logger.error(f"[AdminSiteService] 更新场地失败: {str(e)}", exc_info=True)
            raise Exception(f"更新场地失败: {str(e)}")
    
    @staticmethod
    def delete_site_admin(site_name: str) -> Dict[str, Any]:
        """
        删除场地（管理员）
        
        Args:
            site_name: 场地名称
        
        Returns:
            Dict: 删除结果
        """
        try:
            logger.info(f"[AdminSiteService] 开始删除场地: {site_name}")
            
            # 查找场地所有工位
            sites = Site.objects(site=site_name)
            if not sites:
                logger.warning(f"[AdminSiteService] 场地不存在: {site_name}")
                raise ValueError(f"场地不存在: {site_name}")
            
            # 检查是否有被占用的工位
            occupied_count = sites.filter(is_occupied=True).count()
            if occupied_count > 0:
                logger.warning(f"[AdminSiteService] 场地有 {occupied_count} 个工位被占用，不能删除")
                raise ValueError(f"该场地有 {occupied_count} 个工位正在被占用，不能删除")
            
            # 检查是否有未完成的借用申请
            active_borrows = SiteBorrow.objects(site=site_name, state__in=[0, 1, 2]).count()
            if active_borrows > 0:
                logger.warning(f"[AdminSiteService] 场地有 {active_borrows} 个未完成的借用申请")
                raise ValueError(f"该场地有 {active_borrows} 个未完成的借用申请，不能删除")
            
            # 记录删除信息
            total_workstations = sites.count()
            site_id = sites.first().site_id
            
            # 执行删除
            sites.delete()
            
            logger.info(f"[AdminSiteService] 场地删除成功 | ID: {site_id} | 名称: {site_name} | 删除工位数: {total_workstations}")
            
            return {
                "code": 200,
                "message": "场地删除成功",
                "data": {
                    "site_id": site_id,
                    "site": site_name,
                    "deleted_workstations": total_workstations,
                    "delete_time": datetime.utcnow().isoformat() + "Z"
                }
            }
            
        except ValueError as e:
            raise e
        except Exception as e:
            logger.error(f"[AdminSiteService] 删除场地失败: {str(e)}", exc_info=True)
            raise Exception(f"删除场地失败: {str(e)}")
    
    @staticmethod
    def get_site_borrow_history(site_name: str) -> Dict[str, Any]:
        """
        获取场地借用历史（管理员）
        
        Args:
            site_name: 场地名称
        
        Returns:
            Dict: 借用历史记录
        """
        try:
            logger.info(f"[AdminSiteService] 获取场地借用历史: {site_name}")
            
            # 查询该场地的所有借用记录
            borrows = SiteBorrow.objects(site=site_name).order_by('-created_at')
            
            borrow_list = []
            for borrow in borrows:
                borrow_list.append({
                    'apply_id': borrow.apply_id,
                    'borrower': borrow.name,
                    'student_id': borrow.student_id,
                    'phone': borrow.phone_num,
                    'workstation': borrow.number,
                    'purpose': borrow.purpose,
                    'start_time': borrow.start_time,
                    'end_time': borrow.end_time,
                    'state': borrow.state,
                    'state_text': ['未审核', '打回', '通过未归还', '已归还', '取消'][borrow.state] if borrow.state < 5 else '未知',
                    'review': borrow.review,
                    'created_at': borrow.created_at.isoformat() + "Z" if borrow.created_at else None
                })
            
            # 统计
            stats = {
                'total_borrows': len(borrow_list),
                'pending': sum(1 for b in borrows if b.state == 0),
                'rejected': sum(1 for b in borrows if b.state == 1),
                'approved': sum(1 for b in borrows if b.state == 2),
                'returned': sum(1 for b in borrows if b.state == 3),
                'cancelled': sum(1 for b in borrows if b.state == 4)
            }
            
            return {
                "code": 200,
                "message": "获取借用历史成功",
                "data": {
                    "site": site_name,
                    "borrow_history": borrow_list,
                    "stats": stats
                }
            }
            
        except Exception as e:
            logger.error(f"[AdminSiteService] 获取借用历史失败: {str(e)}", exc_info=True)
            raise Exception(f"获取借用历史失败: {str(e)}")