# app/services/stuff_service.py
"""
物资服务类（小程序端）
处理面向小程序用户的物资相关业务逻辑。
[v2.0 SQLAlchemy 迁移版]
"""
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
import time
import random

from app.models.stuff import Stuff

class StuffService:
    
    @staticmethod
    async def get_all_stuff_grouped_by_type(db: AsyncSession) -> Dict[str, Any]:
        """
        获取所有物资，按类型分组返回。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            
        Returns:
            Dict: 包含分组后的物资数据。
        """
        try:
            # 从数据库获取所有物资
            logger.info("开始从数据库获取所有物资...")
            stmt = select(Stuff)
            result = await db.execute(stmt)
            all_stuff = result.scalars().all()
            logger.info(f"成功获取 {len(all_stuff)} 条物资记录。")
            
            # 按类型分组 (业务逻辑保持不变)
            types_dict = {}
            for stuff in all_stuff:
                type_name = stuff.type
                
                if type_name not in types_dict:
                    types_dict[type_name] = {
                        "type_id": stuff.type_id or StuffService._generate_type_id(), # 兼容可能为空的旧数据
                        "type": type_name,
                        "details": []
                    }
                
                # 添加物资详情 (业务逻辑保持不变)
                types_dict[type_name]["details"].append({
                    "stuff_id": stuff.stuff_id,
                    "stuff_name": stuff.stuff_name,
                    "number_remain": stuff.number_remain,
                    "description": stuff.description
                })
            
            # 转换为列表格式 (业务逻辑保持不变)
            types_list = list(types_dict.values())
            
            return {
                "code": 200,
                "message": "successfully get all stuff",
                "types": types_list
            }
            
        except Exception as e:
            logger.error(f"获取物资失败: {e}", exc_info=True)
            raise Exception(f"获取物资失败: {str(e)}")

    @staticmethod
    async def add_stuff_batch(db: AsyncSession, types_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量添加物资。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            types_data: 包含类型和物资详情的列表。
            
        Returns:
            Dict: 添加结果。
        """
        try:
            added_count = 0
            current_time = int(time.time() * 1000)
            counter = 0
            
            new_stuffs_to_add = [] # 用于收集所有待添加的Stuff对象

            for type_data in types_data:
                type_name = type_data.get("type")
                details = type_data.get("details", [])
                
                # 获取或创建 type_id (已重构为异步)
                type_id = await StuffService._get_or_create_type_id(db, type_name, current_time)
                
                for detail in details:
                    counter += 1
                    
                    # 检查物资是否存在 (已重构为异步)
                    if await StuffService._is_stuff_exists(db, type_name, detail.get("stuff_name")):
                        logger.warning(f"物资 '{detail.get('stuff_name')}' 在类型 '{type_name}' 中已存在，跳过添加")
                        continue
                    
                    # 生成唯一的 stuff_id (已重构为异步)
                    stuff_id = await StuffService._generate_unique_stuff_id(db, current_time, counter)
                    
                    # 创建新物资的ORM实例 (业务逻辑保持不变)
                    new_stuff = Stuff(
                        type_id=type_id,
                        stuff_id=stuff_id,
                        type=type_name,
                        stuff_name=detail.get("stuff_name"),
                        number_total=detail.get("number_remain"),
                        number_remain=detail.get("number_remain"),
                        description=detail.get("description", "")
                    )
                    new_stuffs_to_add.append(new_stuff)
                    added_count += 1
                    logger.debug(f"准备添加物资: {detail.get('stuff_name')} (ID: {stuff_id})")
            
            # 批量一次性提交到数据库
            if new_stuffs_to_add:
                db.add_all(new_stuffs_to_add)
                await db.commit()
                logger.info(f"成功批量提交 {len(new_stuffs_to_add)} 个新物资到数据库。")
            
            return {
                "code": 200,
                "message": f"successfully added {added_count} items",
                "added_count": added_count
            }
        except Exception as e:
            await db.rollback() # 确保在任何异常时回滚事务
            logger.error(f"批量添加物资时出错: {e}", exc_info=True)
            raise Exception(f"添加物资失败: {str(e)}")

    @staticmethod
    def _generate_type_id() -> str:
        """生成类型ID (逻辑不变)"""
        return f"TP{int(time.time() * 1000)}_{random.randint(100, 999)}"

    @staticmethod
    async def _get_or_create_type_id(db: AsyncSession, type_name: str, current_time: int) -> str:
        """获取或创建类型ID (已重构为异步)"""
        stmt = select(Stuff.type_id).where(Stuff.type == type_name, Stuff.type_id.isnot(None)).limit(1)
        result = await db.execute(stmt)
        existing_type_id = result.scalar_one_or_none()
        if existing_type_id:
            return existing_type_id
        else:
            return f"TP{current_time}_{random.randint(100, 999)}"

    @staticmethod
    async def _generate_unique_stuff_id(db: AsyncSession, current_time: int, counter: int) -> str:
        """生成唯一的物资ID (已重构为异步)"""
        for i in range(10): # 最多重试10次
            stuff_id = f"ST{current_time}_{counter:03d}_{random.randint(100, 999)}_{i}"
            stmt = select(Stuff.id).where(Stuff.stuff_id == stuff_id).limit(1)
            result = await db.execute(stmt)
            if result.scalar_one_or_none() is None:
                return stuff_id
        logger.error("在10次重试后仍无法生成唯一的stuff_id")
        raise Exception("无法生成唯一的stuff_id")

    @staticmethod
    async def _is_stuff_exists(db: AsyncSession, type_name: str, stuff_name: str) -> bool:
        """检查物资是否已存在 (已重构为异步)"""
        stmt = select(Stuff.id).where(Stuff.type == type_name, Stuff.stuff_name == stuff_name).limit(1)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    # --- 以下是旧 service 中未在 router 中使用的方法，暂时保留并重构，以备将来使用 ---

    @staticmethod
    async def get_stuff_by_id(db: AsyncSession, stuff_id: str) -> Optional[Stuff]:
        """根据ID获取物资ORM实例"""
        stmt = select(Stuff).where(Stuff.stuff_id == stuff_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_stuff(db: AsyncSession, stuff_id: str) -> bool:
        """删除物资"""
        try:
            stuff = await StuffService.get_stuff_by_id(db, stuff_id)
            if stuff:
                await db.delete(stuff)
                await db.commit()
                return True
            return False
        except Exception as e:
            await db.rollback()
            logger.error(f"删除物资 {stuff_id} 失败: {e}", exc_info=True)
            return False