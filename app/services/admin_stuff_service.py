# app/services/admin_stuff_service.py
"""
管理员物资服务层
处理管理员端物资管理的业务逻辑，包含扩展字段的处理
"""

from typing import List, Dict, Any, Optional
from app.models.stuff import Stuff
from app.models.site import Site
from mongoengine.errors import NotUniqueError, ValidationError
from app.core.logging import logger
import time
import random
from datetime import datetime

class AdminStuffService:
    """管理员物资服务类：处理管理员端物资相关的业务逻辑"""
    
    @staticmethod
    def get_all_stuff_admin(filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        获取所有物资（管理员视图，包含扩展字段）
        
        Args:
            filters: 筛选条件
                - type: 物资类型
                - location: 所在场地
                - cabinet: 展柜位置
                - layer: 层数
                - search: 搜索关键词（物资名称）
        
        Returns:
            Dict: 包含物资列表和统计信息
        """
        try:
            logger.info(f"[AdminStuffService] 开始获取物资列表，筛选条件: {filters}")
            
            # 构建查询条件
            query = {}
            if filters:
                if filters.get('type'):
                    query['type'] = filters['type']
                    logger.debug(f"添加类型筛选: {filters['type']}")
                
                if filters.get('location'):
                    query['location'] = filters['location']
                    logger.debug(f"添加场地筛选: {filters['location']}")
                
                if filters.get('cabinet'):
                    query['cabinet'] = filters['cabinet']
                    logger.debug(f"添加展柜筛选: {filters['cabinet']}")
                
                # 修正层数筛选的处理
                if filters.get('layer') is not None and str(filters.get('layer')).strip():
                    try:
                        layer_value = int(filters['layer'])
                        query['layer'] = layer_value
                        logger.debug(f"添加层数筛选: {layer_value}")
                    except (ValueError, TypeError):
                        logger.warning(f"无效的层数值: {filters.get('layer')}")
                
                if filters.get('search'):
                    # 模糊搜索物资名称
                    query['stuff_name__icontains'] = filters['search']
                    logger.debug(f"添加名称搜索: {filters['search']}")
            
            # 执行查询
            stuff_list = Stuff.objects(**query).order_by('-created_at')
            logger.info(f"查询到 {len(stuff_list)} 条物资记录")
            
            # 获取可用场地列表（从Site集合动态获取）
            available_locations = AdminStuffService._get_available_locations()
            
            # 统计信息
            stats = {
                'total_count': len(stuff_list),
                'total_items': sum(s.number_total for s in stuff_list),
                'total_remain': sum(s.number_remain for s in stuff_list),
                'total_borrowed': sum(s.number_total - s.number_remain for s in stuff_list)
            }
            
            # 按类型分组统计
            type_stats = {}
            for stuff in stuff_list:
                if stuff.type not in type_stats:
                    type_stats[stuff.type] = {
                        'count': 0,
                        'total': 0,
                        'remain': 0
                    }
                type_stats[stuff.type]['count'] += 1
                type_stats[stuff.type]['total'] += stuff.number_total
                type_stats[stuff.type]['remain'] += stuff.number_remain
            
            # 转换为字典列表（包含管理员字段）
            stuff_data = []
            for stuff in stuff_list:
                data = stuff.to_dict(include_admin_fields=True)
                # 计算借出数量
                data['number_borrowed'] = stuff.number_total - stuff.number_remain
                # 计算借出率
                data['borrow_rate'] = round(
                    (data['number_borrowed'] / stuff.number_total * 100) if stuff.number_total > 0 else 0,
                    1
                )
                stuff_data.append(data)
            
            logger.info(f"[AdminStuffService] 物资列表获取成功，返回 {len(stuff_data)} 条数据")
            
            return {
                "code": 200,
                "message": "获取物资列表成功",
                "data": {
                    "stuff_list": stuff_data,
                    "stats": stats,
                    "type_stats": type_stats,
                    "available_locations": available_locations,
                    "available_cabinets": AdminStuffService._get_available_cabinets()
                }
            }
            
        except Exception as e:
            logger.error(f"[AdminStuffService] 获取物资列表失败: {str(e)}", exc_info=True)
            raise Exception(f"获取物资列表失败: {str(e)}")
    
    @staticmethod
    def create_stuff_admin(stuff_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建新物资（管理员）
        
        Args:
            stuff_data: 物资数据，包含所有字段
        
        Returns:
            Dict: 创建结果
        """
        try:
            logger.info(f"[AdminStuffService] 开始创建物资: {stuff_data.get('stuff_name')}")
            
            # 生成物资ID
            timestamp = int(time.time() * 1000)
            random_suffix = random.randint(100, 999)
            stuff_id = f"ST{timestamp}_{random_suffix}"
            
            # 生成或获取类型ID
            type_name = stuff_data.get('type')
            existing_type = Stuff.objects(type=type_name).first()
            if existing_type and existing_type.type_id:
                type_id = existing_type.type_id
            else:
                type_id = f"TP{timestamp}_{random.randint(100, 999)}"
            
            logger.debug(f"生成的stuff_id: {stuff_id}, type_id: {type_id}")
            
            # 创建物资实例
            new_stuff = Stuff(
                type_id=type_id,
                stuff_id=stuff_id,
                type=type_name,
                stuff_name=stuff_data.get('stuff_name'),
                number_total=int(stuff_data.get('number_total', 0)),
                number_remain=int(stuff_data.get('number_remain', 0)),
                description=stuff_data.get('description', ''),
                # 管理员扩展字段
                location=stuff_data.get('location', ''),
                cabinet=stuff_data.get('cabinet', ''),
                layer=int(stuff_data.get('layer', 1))
            )
            
            # 保存到数据库
            new_stuff.save()
            logger.info(f"[AdminStuffService] 物资创建成功: {stuff_id} - {stuff_data.get('stuff_name')}")
            
            # 记录操作日志
            logger.info(f"管理员创建物资 | ID: {stuff_id} | 名称: {stuff_data.get('stuff_name')} | "
                       f"位置: {stuff_data.get('location')}-{stuff_data.get('cabinet')}-{stuff_data.get('layer')}层")
            
            return {
                "code": 200,
                "message": "物资创建成功",
                "data": new_stuff.to_dict(include_admin_fields=True)
            }
            
        except ValidationError as e:
            logger.warning(f"[AdminStuffService] 物资数据验证失败: {str(e)}")
            raise ValueError(f"数据验证失败: {str(e)}")
        except NotUniqueError as e:
            logger.warning(f"[AdminStuffService] 物资ID重复: {str(e)}")
            raise ValueError("物资编号重复，请重试")
        except Exception as e:
            logger.error(f"[AdminStuffService] 创建物资失败: {str(e)}", exc_info=True)
            raise Exception(f"创建物资失败: {str(e)}")
    
    @staticmethod
    def update_stuff_admin(stuff_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新物资信息（管理员）
        
        Args:
            stuff_id: 物资ID
            update_data: 更新数据
        
        Returns:
            Dict: 更新结果
        """
        try:
            logger.info(f"[AdminStuffService] 开始更新物资: {stuff_id}")
            logger.debug(f"更新数据: {update_data}")
            
            # 查找物资
            stuff = Stuff.objects(stuff_id=stuff_id).first()
            if not stuff:
                logger.warning(f"[AdminStuffService] 物资不存在: {stuff_id}")
                raise ValueError(f"物资不存在: {stuff_id}")
            
            # 记录原始数据用于日志
            original_data = stuff.to_dict(include_admin_fields=True)
            
            # 更新基础字段
            if 'type' in update_data:
                stuff.type = update_data['type']
            if 'stuff_name' in update_data:
                stuff.stuff_name = update_data['stuff_name']
            if 'number_total' in update_data:
                stuff.number_total = int(update_data['number_total'])
            if 'number_remain' in update_data:
                stuff.number_remain = int(update_data['number_remain'])
            if 'description' in update_data:
                stuff.description = update_data['description']
            
            # 更新管理员扩展字段
            if 'location' in update_data:
                stuff.location = update_data['location']
            if 'cabinet' in update_data:
                stuff.cabinet = update_data['cabinet']
            if 'layer' in update_data:
                stuff.layer = int(update_data['layer'])
            
            # 保存更改
            stuff.save()
            
            # 记录变更日志
            changed_fields = []
            for key, new_value in update_data.items():
                old_value = original_data.get(key)
                if old_value != new_value:
                    changed_fields.append(f"{key}: {old_value} -> {new_value}")
            
            if changed_fields:
                logger.info(f"[AdminStuffService] 物资更新成功 | ID: {stuff_id} | 变更: {', '.join(changed_fields)}")
            
            return {
                "code": 200,
                "message": "物资更新成功",
                "data": stuff.to_dict(include_admin_fields=True)
            }
            
        except ValueError as e:
            raise e
        except ValidationError as e:
            logger.warning(f"[AdminStuffService] 更新数据验证失败: {str(e)}")
            raise ValueError(f"数据验证失败: {str(e)}")
        except Exception as e:
            logger.error(f"[AdminStuffService] 更新物资失败: {str(e)}", exc_info=True)
            raise Exception(f"更新物资失败: {str(e)}")
    
    @staticmethod
    def delete_stuff_admin(stuff_id: str) -> Dict[str, Any]:
        """
        删除物资（管理员）
        
        Args:
            stuff_id: 物资ID
        
        Returns:
            Dict: 删除结果
        """
        try:
            logger.info(f"[AdminStuffService] 开始删除物资: {stuff_id}")
            
            # 查找物资
            stuff = Stuff.objects(stuff_id=stuff_id).first()
            if not stuff:
                logger.warning(f"[AdminStuffService] 物资不存在: {stuff_id}")
                raise ValueError(f"物资不存在: {stuff_id}")
            
            # 检查是否有未归还的借用记录
            if stuff.number_remain < stuff.number_total:
                borrowed_count = stuff.number_total - stuff.number_remain
                logger.warning(f"[AdminStuffService] 物资有未归还记录，不能删除: {stuff_id}, 借出数量: {borrowed_count}")
                raise ValueError(f"该物资还有 {borrowed_count} 件未归还，不能删除")
            
            # 记录删除信息用于日志
            deleted_info = {
                "stuff_id": stuff.stuff_id,
                "stuff_name": stuff.stuff_name,
                "type": stuff.type,
                "location": f"{stuff.location}-{stuff.cabinet}-{stuff.layer}层"
            }
            
            # 执行删除
            stuff.delete()
            
            logger.info(f"[AdminStuffService] 物资删除成功 | ID: {stuff_id} | 名称: {deleted_info['stuff_name']} | "
                       f"类型: {deleted_info['type']} | 位置: {deleted_info['location']}")
            
            return {
                "code": 200,
                "message": "物资删除成功",
                "data": {
                    "deleted_stuff": deleted_info,
                    "delete_time": datetime.utcnow().isoformat() + "Z"
                }
            }
            
        except ValueError as e:
            raise e
        except Exception as e:
            logger.error(f"[AdminStuffService] 删除物资失败: {str(e)}", exc_info=True)
            raise Exception(f"删除物资失败: {str(e)}")
    
    @staticmethod
    def batch_update_stuff_admin(update_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量更新物资（管理员）
        
        Args:
            update_list: 更新列表，每项包含stuff_id和更新数据
        
        Returns:
            Dict: 批量更新结果
        """
        try:
            logger.info(f"[AdminStuffService] 开始批量更新物资，数量: {len(update_list)}")
            
            success_count = 0
            failed_items = []
            
            for item in update_list:
                stuff_id = item.get('stuff_id')
                update_data = item.get('update_data', {})
                
                try:
                    AdminStuffService.update_stuff_admin(stuff_id, update_data)
                    success_count += 1
                except Exception as e:
                    failed_items.append({
                        'stuff_id': stuff_id,
                        'error': str(e)
                    })
                    logger.warning(f"批量更新中失败项: {stuff_id}, 错误: {str(e)}")
            
            logger.info(f"[AdminStuffService] 批量更新完成 | 成功: {success_count} | 失败: {len(failed_items)}")
            
            return {
                "code": 200,
                "message": f"批量更新完成，成功 {success_count} 项，失败 {len(failed_items)} 项",
                "data": {
                    "success_count": success_count,
                    "failed_items": failed_items
                }
            }
            
        except Exception as e:
            logger.error(f"[AdminStuffService] 批量更新失败: {str(e)}", exc_info=True)
            raise Exception(f"批量更新失败: {str(e)}")
    
    @staticmethod
    def _get_available_locations() -> List[str]:
        """
        获取可用的场地列表
        
        Returns:
            List[str]: 场地名称列表
        """
        try:
            # 从Site集合获取所有不重复的场地名称
            sites = Site.objects().distinct('site')
            if sites:
                logger.debug(f"从数据库获取到场地列表: {sites}")
                return sites
            else:
                # 如果没有数据，返回默认值
                default_sites = ["i创街", "101", "208+"]
                logger.debug(f"使用默认场地列表: {default_sites}")
                return default_sites
        except Exception as e:
            logger.warning(f"获取场地列表失败，使用默认值: {str(e)}")
            return ["i创街", "101", "208+"]
    
    @staticmethod
    def _get_available_cabinets() -> List[str]:
        """
        获取可用的展柜编号列表
        
        Returns:
            List[str]: 展柜编号列表
        """
        # 生成A-Z和AA-AZ的展柜编号
        cabinets = []
        # A-Z
        for i in range(26):
            cabinets.append(chr(65 + i))
        # AA-AZ (如果需要更多)
        for i in range(26):
            cabinets.append(f"A{chr(65 + i)}")
        return cabinets