from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from app.models.stuff import Stuff
from pydantic import BaseModel
from mongoengine.errors import NotUniqueError, ValidationError
from app.core.auth import require_permission_level
import time
import random
import uuid

router = APIRouter()

# Pydantic 模型定义
class StuffDetail(BaseModel):
    stuff_name: str
    number_remain: int
    description: str

class StuffType(BaseModel):
    type: str
    details: List[StuffDetail]

class AddStuffRequest(BaseModel):
    types: List[StuffType]

@router.get("/get-all")
def get_all_stuff(user: dict = Depends(require_permission_level(0))):  # 允许权限0,1,2
    """获取所有物资，按类型分组返回"""
    try:
        # 获取所有物资
        all_stuff = Stuff.objects()
        
        # 按类型分组
        types_dict = {}
        
        for stuff in all_stuff:
            type_name = stuff.type
            
            if type_name not in types_dict:
                types_dict[type_name] = {
                    "type_id": stuff.type_id or f"TP{int(time.time() * 1000)}_{random.randint(100, 999)}",
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
        raise HTTPException(status_code=500, detail=f"获取物资失败: {str(e)}")

@router.post("/add")
def add_stuff(request: AddStuffRequest):  # user: dict = Depends(require_permission_level(1))  # 需要权限1,2
    """批量添加物资"""
    try:
        added_count = 0
        current_time = int(time.time() * 1000)
        counter = 0
        
        for type_data in request.types:
            type_name = type_data.type
            
            # 生成或获取 type_id
            existing_stuff = Stuff.objects(type=type_name).first()
            if existing_stuff and existing_stuff.type_id:
                type_id = existing_stuff.type_id
            else:
                type_id = f"TP{current_time}_{random.randint(100, 999)}"
            
            # 添加该类型下的所有物资
            for detail in type_data.details:
                counter += 1
                
                # 使用更可靠的唯一ID生成方式
                stuff_id = f"ST{current_time}_{counter:03d}_{random.randint(100, 999)}"
                
                # 确保 stuff_id 唯一
                retry_count = 0
                while Stuff.objects(stuff_id=stuff_id).first() and retry_count < 10:
                    retry_count += 1
                    stuff_id = f"ST{current_time}_{counter:03d}_{random.randint(100, 999)}_{retry_count}"
                
                # 检查是否已存在相同名称的物资
                existing_item = Stuff.objects(
                    type=type_name,
                    stuff_name=detail.stuff_name
                ).first()
                
                if existing_item:
                    print(f"警告: 物资 '{detail.stuff_name}' 在类型 '{type_name}' 中已存在，跳过添加")
                    continue
                
                # 创建新物资
                new_stuff = Stuff(
                    type_id=type_id,
                    stuff_id=stuff_id,
                    type=type_name,
                    stuff_name=detail.stuff_name,
                    number_total=detail.number_remain,  # 初始总数等于剩余数
                    number_remain=detail.number_remain,
                    description=detail.description
                )
                
                new_stuff.save()
                added_count += 1
                print(f"已添加物资: {detail.stuff_name} (ID: {stuff_id})")
        
        return {
            "code": 200,
            "message": f"successfully added {added_count} items",
            "added_count": added_count
        }
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"数据验证失败: {str(e)}")
    except NotUniqueError as e:
        raise HTTPException(status_code=400, detail="物品编号重复")
    except Exception as e:
        print(f"添加物资时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"添加物资失败: {str(e)}")