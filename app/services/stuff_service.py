from typing import List, Dict, Any, Optional
from app.models.stuff import Stuff
from mongoengine.errors import NotUniqueError, ValidationError
from loguru import logger
import time
import random

class StuffService:
    
    @staticmethod
    def get_all_stuff_grouped_by_type() -> Dict[str, Any]:
        """
        获取所有物资，按类型分组返回
        
        Returns:
            Dict: 包含分组后的物资数据
        """
        try:
            # 获取所有物资
            all_stuff = Stuff.objects()
            
            # 按类型分组
            types_dict = {}
            
            for stuff in all_stuff:
                type_name = stuff.type
                
                if type_name not in types_dict:
                    types_dict[type_name] = {
                        "type_id": stuff.type_id or StuffService._generate_type_id(),
                        "type": type_name,
                        "details": []
                    }
                
                # 添加物资详情
                types_dict[type_name]["details"].append({
                    "stuff_id": stuff.stuff_id,
                    "stuff_name": stuff.stuff_name,
                    "number_remain": stuff.number_remain,
                    "description": stuff.description
                })
            
            # 转换为列表格式
            types_list = list(types_dict.values())
            
            return {
                "code": 200,
                "message": "successfully get all stuff",
                "types": types_list
            }
            
        except Exception as e:
            raise Exception(f"获取物资失败: {str(e)}")

    @staticmethod
    def add_stuff_batch(types_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量添加物资
        
        Args:
            types_data: 包含类型和物资详情的列表
            
        Returns:
            Dict: 添加结果
        """
        try:
            added_count = 0
            current_time = int(time.time() * 1000)
            counter = 0
            
            for type_data in types_data:
                type_name = type_data.get("type")
                details = type_data.get("details", [])
                
                # 生成或获取 type_id
                type_id = StuffService._get_or_create_type_id(type_name, current_time)
                
                # 添加该类型下的所有物资
                for detail in details:
                    counter += 1
                    
                    # 检查是否已存在相同名称的物资
                    if StuffService._is_stuff_exists(type_name, detail.get("stuff_name")):
                        logger.warning(f"物资 '{detail.get('stuff_name')}' 在类型 '{type_name}' 中已存在，跳过添加")
                        continue
                    
                    # 生成唯一的 stuff_id
                    stuff_id = StuffService._generate_unique_stuff_id(current_time, counter)
                    
                    # 创建新物资
                    new_stuff = Stuff(
                        type_id=type_id,
                        stuff_id=stuff_id,
                        type=type_name,
                        stuff_name=detail.get("stuff_name"),
                        number_total=detail.get("number_remain"),  # 初始总数等于剩余数
                        number_remain=detail.get("number_remain"),
                        description=detail.get("description", "")
                    )
                    
                    new_stuff.save()
                    added_count += 1
                    logger.debug(f"已添加物资: {detail.get('stuff_name')} (ID: {stuff_id})")
            
            return {
                "code": 200,
                "message": f"successfully added {added_count} items",
                "added_count": added_count
            }
            
        except ValidationError as e:
            raise ValueError(f"数据验证失败: {str(e)}")
        except NotUniqueError as e:
            raise ValueError("物品编号重复")
        except Exception as e:
            logger.error(f"添加物资时出错: {str(e)}", exc_info=True)
            raise Exception(f"添加物资失败: {str(e)}")

    @staticmethod
    def _generate_type_id() -> str:
        """生成类型ID"""
        return f"TP{int(time.time() * 1000)}_{random.randint(100, 999)}"

    @staticmethod
    def _get_or_create_type_id(type_name: str, current_time: int) -> str:
        """获取或创建类型ID"""
        existing_stuff = Stuff.objects(type=type_name).first()
        if existing_stuff and existing_stuff.type_id:
            return existing_stuff.type_id
        else:
            return f"TP{current_time}_{random.randint(100, 999)}"

    @staticmethod
    def _generate_unique_stuff_id(current_time: int, counter: int) -> str:
        """生成唯一的物资ID"""
        stuff_id = f"ST{current_time}_{counter:03d}_{random.randint(100, 999)}"
        
        # 确保 stuff_id 唯一
        retry_count = 0
        while Stuff.objects(stuff_id=stuff_id).first() and retry_count < 10:
            retry_count += 1
            stuff_id = f"ST{current_time}_{counter:03d}_{random.randint(100, 999)}_{retry_count}"
        
        return stuff_id

    @staticmethod
    def _is_stuff_exists(type_name: str, stuff_name: str) -> bool:
        """检查物资是否已存在"""
        return Stuff.objects(type=type_name, stuff_name=stuff_name).first() is not None

    @staticmethod
    def get_stuff_by_id(stuff_id: str) -> Optional[Stuff]:
        """根据ID获取物资"""
        return Stuff.objects(stuff_id=stuff_id).first()

    @staticmethod
    def get_stuff_by_type(type_name: str) -> List[Stuff]:
        """根据类型获取物资列表"""
        return list(Stuff.objects(type=type_name))

    @staticmethod
    def delete_stuff(stuff_id: str) -> bool:
        """删除物资"""
        stuff = Stuff.objects(stuff_id=stuff_id).first()
        if stuff:
            stuff.delete()
            return True
        return False

    @staticmethod
    def update_stuff_quantity(stuff_id: str, new_remain: int) -> bool:
        """更新物资数量"""
        stuff = Stuff.objects(stuff_id=stuff_id).first()
        if stuff:
            stuff.number_remain = new_remain
            stuff.save()
            return True
        return False