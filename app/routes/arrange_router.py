from fastapi import APIRouter, HTTPException, Depends
from app.services.arrange_service import ArrangeService
from app.core.auth import require_permission_level
from loguru import logger
from pydantic import BaseModel
from typing import Dict, List, Any

router = APIRouter()

# 排班人员数据结构
class ArrangePerson(BaseModel):
    name: str
    order: int
    current: bool
    maker_id: str  

# 获取排班安排
@router.get("/get-arrangement")
async def get_arrangements(
    user: dict = Depends(require_permission_level(1)),  # 需要权限1或2
    service: ArrangeService = Depends(ArrangeService)
):
    """获取所有排班安排"""
    try:
        logger.info(f"获取排班安排 | 用户: {user.userid}")
        
        # 调用服务层获取排班安排
        arrangements = await service.get_all_arrangements()
        
        return {
            "code": 200,
            "message": "successfully get all arrangements",
            "data": arrangements
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"获取排班安排失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取排班安排失败")

@router.get("/get-current")
async def get_current_arrangers(
    user: dict = Depends(require_permission_level(1)),  # 需要权限1或2
    service: ArrangeService = Depends(ArrangeService)
):
    """获取本次宣传部三个任务轮到的干事的信息"""
    try:
        logger.info(f"获取当前值班人员 | 用户: {user.userid}")
        
        # 调用服务层获取当前值班人员
        current_makers = await service.get_current_makers()
        
        return {
            "code": 200,
            "message": "successfully get current maker",
            "data": current_makers
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"获取当前值班人员失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "message": "获取当前值班人员失败"
            }
        )

# 批量创建排班安排
@router.post("/arrangements/batch")
async def batch_create_arrangements(
    request_data: Dict[str, List[Dict[str, Any]]],  # 直接接收字典结构
    # user: dict = Depends(require_permission_level(2)),  # 需要权限2
    service: ArrangeService = Depends(ArrangeService)
):
    """批量创建排班安排（测试用）"""
    try:
        # logger.info(f"批量创建排班安排 | 用户: {user.userid}")
        
        # 验证和转换请求数据
        validated_data = {}
        for task_type, person_list in request_data.items():
            # 验证任务类型
            if task_type not in ["1", "2", "3"]:
                logger.warning(f"跳过无效的任务类型: {task_type}")
                continue
            
            # 验证人员列表
            validated_list = []
            for person in person_list:
                try:
                    # 确保包含必要字段
                    if not all(key in person for key in ["name", "order", "current", "maker_id"]):
                                logger.warning(f"人员数据缺少必要字段: {person}")
                                continue
                    
                    validated_list.append({
                        "name": person["name"],
                        "order": person["order"],
                        "current": person["current"],
                        "maker_id": person["maker_id"]
                    })
                except Exception as e:
                    logger.warning(f"解析人员数据失败: {str(e)} | 数据: {person}")
            
            validated_data[task_type] = validated_list
        
        # 调用服务层批量创建
        result = await service.batch_create_arrangements(validated_data)
        
        return {
            "code": 200,
            "message": "successfully batch create arrangements",
            "data": result
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"批量创建排班失败: {str(e)}")
        raise HTTPException(status_code=500, detail="批量创建排班失败")