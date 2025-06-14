from fastapi import APIRouter, HTTPException, Depends
from typing import List
from pydantic import BaseModel
from app.core.auth import require_permission_level
from app.services.stuff_service import StuffService

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
        result = StuffService.get_all_stuff_grouped_by_type()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add")
def add_stuff(request: AddStuffRequest):  # user: dict = Depends(require_permission_level(1))  # 需要权限1,2
    """批量添加物资"""
    try:
        # 将 Pydantic 模型转换为字典
        types_data = []
        for type_item in request.types:
            type_dict = {
                "type": type_item.type,
                "details": []
            }
            for detail in type_item.details:
                detail_dict = {
                    "stuff_name": detail.stuff_name,
                    "number_remain": detail.number_remain,
                    "description": detail.description
                }
                type_dict["details"].append(detail_dict)
            types_data.append(type_dict)
        
        result = StuffService.add_stuff_batch(types_data)
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))