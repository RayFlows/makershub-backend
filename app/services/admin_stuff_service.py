# app/services/admin_stuff_service.py
"""
管理员物资服务层
处理管理员端物资管理的业务逻辑，包含扩展字段的处理。
[v2.0 SQLAlchemy 迁移版]
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
import time
import random
from datetime import datetime

from app.models.stuff import Stuff
# TODO: 待Site模块迁移后，需要从这里导入Site模型
# from app.models.site import Site

class AdminStuffService:
    """管理员物资服务类：处理管理员端物资相关的业务逻辑。"""
    
    @staticmethod
    def _stuff_to_admin_dict(stuff: Stuff) -> dict:
        """辅助函数：将Stuff ORM对象转换为管理员视图所需的完整字典格式。"""
        data = {
            'id': stuff.id,
            'type_id': stuff.type_id,
            'stuff_id': stuff.stuff_id,
            'type': stuff.type,
            'stuff_name': stuff.stuff_name,
            'number_total': stuff.number_total,
            'number_remain': stuff.number_remain,
            'description': stuff.description,
            'location': stuff.location or "",
            'cabinet': stuff.cabinet or "",
            'layer': stuff.layer or 1,
            'created_at': stuff.created_at.isoformat() + "Z" if stuff.created_at else None,
            'updated_at': stuff.updated_at.isoformat() + "Z" if stuff.updated_at else None,
        }
        # 计算衍生字段
        data['number_borrowed'] = data['number_total'] - data['number_remain']
        data['borrow_rate'] = round(
            (data['number_borrowed'] / data['number_total'] * 100) if data['number_total'] > 0 else 0, 1
        )
        return data

    @staticmethod
    async def get_all_stuff_admin(db: AsyncSession, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        获取所有物资（管理员视图，包含扩展字段）。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            filters: 包含筛选条件的字典。
        
        Returns:
            包含物资列表和统计信息的字典。
        """
        try:
            logger.info(f"[AdminStuffService] 开始获取物资列表，筛选条件: {filters}")
            
            stmt = select(Stuff).order_by(Stuff.created_at.desc())

            # 构建动态查询条件
            if filters:
                if filters.get('type'):
                    stmt = stmt.where(Stuff.type == filters['type'])
                    logger.debug(f"添加类型筛选: {filters['type']}")
                if filters.get('location'):
                    stmt = stmt.where(Stuff.location == filters['location'])
                    logger.debug(f"添加场地筛选: {filters['location']}")
                if filters.get('cabinet'):
                    stmt = stmt.where(Stuff.cabinet == filters['cabinet'])
                    logger.debug(f"添加展柜筛选: {filters['cabinet']}")
                if filters.get('layer') is not None and str(filters.get('layer')).strip():
                    try:
                        layer_value = int(filters['layer'])
                        stmt = stmt.where(Stuff.layer == layer_value)
                        logger.debug(f"添加层数筛选: {layer_value}")
                    except (ValueError, TypeError):
                        logger.warning(f"无效的层数值: {filters.get('layer')}")
                if filters.get('search'):
                    search_term = f"%{filters['search']}%"
                    stmt = stmt.where(Stuff.stuff_name.ilike(search_term))
                    logger.debug(f"添加名称搜索: {filters['search']}")
            
            # 执行查询
            result = await db.execute(stmt)
            all_stuff = result.scalars().all()
            logger.info(f"查询到 {len(all_stuff)} 条物资记录")
            
            # 获取可用场地列表
            available_locations = await AdminStuffService._get_available_locations(db)
            
            # 统计信息
            stats = {
                'total_count': len(all_stuff),
                'total_items': sum(s.number_total for s in all_stuff),
                'total_remain': sum(s.number_remain for s in all_stuff),
                'total_borrowed': sum(s.number_total - s.number_remain for s in all_stuff)
            }
            
            # 按类型分组统计
            type_stats = {}
            for stuff in all_stuff:
                if stuff.type not in type_stats:
                    type_stats[stuff.type] = {'count': 0, 'total': 0, 'remain': 0}
                type_stats[stuff.type]['count'] += 1
                type_stats[stuff.type]['total'] += stuff.number_total
                type_stats[stuff.type]['remain'] += stuff.number_remain
            
            stuff_data = [AdminStuffService._stuff_to_admin_dict(s) for s in all_stuff]
            
            logger.info(f"[AdminStuffService] 物资列表获取成功，返回 {len(stuff_data)} 条数据")
            
            return {
                "code": 200, "message": "获取物资列表成功",
                "data": {
                    "stuff_list": stuff_data, "stats": stats, "type_stats": type_stats,
                    "available_locations": available_locations,
                    "available_cabinets": AdminStuffService._get_available_cabinets()
                }
            }
        except Exception as e:
            logger.error(f"[AdminStuffService] 获取物资列表失败: {e}", exc_info=True)
            raise Exception(f"获取物资列表失败: {str(e)}")

    @staticmethod
    async def create_stuff_admin(db: AsyncSession, stuff_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建新物资（管理员）。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            stuff_data: 物资数据字典。
        
        Returns:
            创建结果的字典。
        """
        try:
            logger.info(f"[AdminStuffService] 开始创建物资: {stuff_data.get('stuff_name')}")
            
            timestamp = int(time.time() * 1000)
            random_suffix = random.randint(100, 999)
            stuff_id = f"ST{timestamp}_{random_suffix}"
            
            # 获取或创建类型ID
            type_name = stuff_data.get('type')
            stmt = select(Stuff.type_id).where(Stuff.type == type_name, Stuff.type_id.isnot(None)).limit(1)
            result = await db.execute(stmt)
            type_id = result.scalar_one_or_none() or f"TP{timestamp}_{random.randint(100, 999)}"
            logger.debug(f"生成的stuff_id: {stuff_id}, type_id: {type_id}")
            
            new_stuff = Stuff(
                type_id=type_id,
                stuff_id=stuff_id,
                **stuff_data
            )
            
            db.add(new_stuff)
            await db.commit()
            await db.refresh(new_stuff)
            
            logger.info(f"[AdminStuffService] 物资创建成功: {stuff_id} - {stuff_data.get('stuff_name')}")
            logger.info(f"管理员创建物资 | ID: {stuff_id} | 名称: {stuff_data.get('stuff_name')} | 位置: {stuff_data.get('location')}-{stuff_data.get('cabinet')}-{stuff_data.get('layer')}层")
            
            return {"code": 200, "message": "物资创建成功", "data": AdminStuffService._stuff_to_admin_dict(new_stuff)}
        except Exception as e:
            await db.rollback()
            logger.error(f"[AdminStuffService] 创建物资失败: {e}", exc_info=True)
            raise Exception(f"创建物资失败: {str(e)}")

    @staticmethod
    async def update_stuff_admin(db: AsyncSession, stuff_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新物资信息（管理员）。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            stuff_id: 要更新的物资ID。
            update_data: 包含更新字段的字典。
        
        Returns:
            更新结果的字典。
        """
        try:
            logger.info(f"[AdminStuffService] 开始更新物资: {stuff_id}")
            logger.debug(f"更新数据: {update_data}")
            
            stmt = select(Stuff).where(Stuff.stuff_id == stuff_id)
            result = await db.execute(stmt)
            stuff = result.scalar_one_or_none()

            if not stuff:
                logger.warning(f"[AdminStuffService] 物资不存在: {stuff_id}")
                raise ValueError(f"物资不存在: {stuff_id}")

            original_data = AdminStuffService._stuff_to_admin_dict(stuff)

            for field, value in update_data.items():
                if hasattr(stuff, field):
                    setattr(stuff, field, value)
            
            db.add(stuff)
            await db.commit()
            await db.refresh(stuff)

            changed_fields = []
            for key, new_value in update_data.items():
                old_value = original_data.get(key)
                if str(old_value) != str(new_value):
                    changed_fields.append(f"{key}: {old_value} -> {new_value}")
            if changed_fields:
                logger.info(f"[AdminStuffService] 物资更新成功 | ID: {stuff_id} | 变更: {', '.join(changed_fields)}")
            
            return {"code": 200, "message": "物资更新成功", "data": AdminStuffService._stuff_to_admin_dict(stuff)}
        except ValueError as e:
            raise e
        except Exception as e:
            await db.rollback()
            logger.error(f"[AdminStuffService] 更新物资失败: {e}", exc_info=True)
            raise Exception(f"更新物资失败: {str(e)}")

    @staticmethod
    async def delete_stuff_admin(db: AsyncSession, stuff_id: str) -> Dict[str, Any]:
        """
        删除物资（管理员）。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            stuff_id: 要删除的物资ID。
        
        Returns:
            删除结果的字典。
        """
        try:
            logger.info(f"[AdminStuffService] 开始删除物资: {stuff_id}")
            
            stmt = select(Stuff).where(Stuff.stuff_id == stuff_id)
            result = await db.execute(stmt)
            stuff = result.scalar_one_or_none()

            if not stuff:
                logger.warning(f"[AdminStuffService] 物资不存在: {stuff_id}")
                raise ValueError(f"物资不存在: {stuff_id}")

            if stuff.number_remain < stuff.number_total:
                borrowed_count = stuff.number_total - stuff.number_remain
                logger.warning(f"[AdminStuffService] 物资有未归还记录，不能删除: {stuff_id}, 借出数量: {borrowed_count}")
                raise ValueError(f"该物资还有 {borrowed_count} 件未归还，不能删除")

            deleted_info = {
                "stuff_id": stuff.stuff_id, "stuff_name": stuff.stuff_name, "type": stuff.type,
                "location": f"{stuff.location}-{stuff.cabinet}-{stuff.layer}层"
            }
            
            await db.delete(stuff)
            await db.commit()
            
            logger.info(f"[AdminStuffService] 物资删除成功 | ID: {stuff_id} | 名称: {deleted_info['stuff_name']} | 类型: {deleted_info['type']} | 位置: {deleted_info['location']}")
            
            return {
                "code": 200, "message": "物资删除成功",
                "data": {"deleted_stuff": deleted_info, "delete_time": datetime.utcnow().isoformat() + "Z"}
            }
        except ValueError as e:
            raise e
        except Exception as e:
            await db.rollback()
            logger.error(f"[AdminStuffService] 删除物资失败: {e}", exc_info=True)
            raise Exception(f"删除物资失败: {str(e)}")

    @staticmethod
    async def batch_update_stuff_admin(db: AsyncSession, update_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量更新物资（管理员）。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            update_list: 更新列表，每项包含stuff_id和更新数据。
        
        Returns:
            批量更新结果的字典。
        """
        try:
            logger.info(f"[AdminStuffService] 开始批量更新物资，数量: {len(update_list)}")
            
            success_count = 0
            failed_items = []
            
            # 在一个事务中处理所有更新
            async with db.begin_nested() if db.in_transaction() else db.begin() as transaction:
                for item in update_list:
                    stuff_id = item.get('stuff_id')
                    update_data = item.get('update_data', {})
                    try:
                        # 复用单个更新的逻辑，但不提交
                        stmt = select(Stuff).where(Stuff.stuff_id == stuff_id)
                        result = await db.execute(stmt)
                        stuff = result.scalar_one_or_none()
                        if not stuff:
                            raise ValueError("物资不存在")
                        for field, value in update_data.items():
                            if hasattr(stuff, field):
                                setattr(stuff, field, value)
                        db.add(stuff)
                        success_count += 1
                    except Exception as e:
                        # 如果单个更新失败，记录下来，但不中止整个批量操作
                        failed_items.append({'stuff_id': stuff_id, 'error': str(e)})
                        logger.warning(f"批量更新中失败项: {stuff_id}, 错误: {str(e)}")
            
            logger.info(f"[AdminStuffService] 批量更新完成 | 成功: {success_count} | 失败: {len(failed_items)}")
            
            return {
                "code": 200,
                "message": f"批量更新完成，成功 {success_count} 项，失败 {len(failed_items)} 项",
                "data": {"success_count": success_count, "failed_items": failed_items}
            }
        except Exception as e:
            logger.error(f"[AdminStuffService] 批量更新失败: {e}", exc_info=True)
            raise Exception(f"批量更新失败: {str(e)}")

    @staticmethod
    async def _get_available_locations(db: AsyncSession) -> List[str]:
        """
        获取可用的场地列表。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
        
        Returns:
            场地名称列表。
        """
        try:
            # TODO: 待Site模块迁移后，这里的查询需要修改为 `select(Site.site).distinct()`
            # from app.models.site import Site
            # stmt = select(Site.site).distinct()
            # result = await db.execute(stmt)
            # sites = result.scalars().all()

            # 临时的硬编码实现
            sites = ["i创街", "101", "208+"]
            
            if sites:
                logger.debug(f"获取到场地列表: {sites}")
                return sites
            else:
                default_sites = ["i创街", "101", "208+"]
                logger.debug(f"场地列表为空，使用默认值: {default_sites}")
                return default_sites
        except Exception as e:
            logger.warning(f"获取场地列表失败，使用默认值: {e}")
            return ["i创街", "101", "208+"]

    @staticmethod
    def _get_available_cabinets() -> List[str]:
        """
        获取可用的展柜编号列表 (逻辑不变)。
        
        Returns:
            展柜编号列表。
        """
        cabinets = [chr(65 + i) for i in range(26)] # A-Z
        # AA-AZ (如果需要)
        # for i in range(26):
        #     cabinets.append(f"A{chr(65 + i)}")
        return cabinets