from fastapi import APIRouter, HTTPException, Depends
from typing import List
from pydantic import BaseModel
from loguru import logger
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
    """
    获取所有物资，按类型分组返回
    
    Args:
        user: 当前用户信息（权限级别0及以上）
        
    Returns:
        Dict: 按类型分组的物资列表
    """
    try:
        result = StuffService.get_all_stuff_grouped_by_type()
        return result
    except Exception as e:
        logger.error(f"获取物资列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add")
def add_stuff(request: AddStuffRequest):  # user: dict = Depends(require_permission_level(1))  # 需要权限1,2
    """
    批量添加物资
    
    Args:
        request: 添加物资请求数据（包含物资类型和详情）
        
    Returns:
        Dict: 添加结果
    """
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
        logger.warning(f"添加物资参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"添加物资失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))