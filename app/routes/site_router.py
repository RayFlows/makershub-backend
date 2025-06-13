from fastapi import APIRouter, HTTPException, Depends
from app.services.site_service import SiteService
from app.core.auth import require_permission_level
from loguru import logger

router = APIRouter()
site_service = SiteService()

# 添加场地（临时接口）
@router.post("/add")
async def add_site(
    site_data: dict,
    # user: dict = Depends(require_permission_level(2))  # 需要权限2
):
    """
    添加场地信息（临时接口）
    
    用于初始化场地数据，后续将改为管理员面板使用
    """
    try:
        # 验证必要字段
        if "site" not in site_data or "details" not in site_data:
            raise HTTPException(status_code=400, detail="缺少必要字段")
        
        # 调用服务层添加场地
        result = await site_service.add_site(site_data)
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"添加场地失败: {str(e)}")
        raise HTTPException(status_code=500, detail="添加场地失败")

# 获取所有场地
@router.get("/get-all")
async def get_all_sites(
    user: dict = Depends(require_permission_level(0))  # 允许权限0,1,2
):
    """
    获取所有场地信息
    
    返回所有场地及其工位状态
    """
    try:
        # 调用服务层获取场地信息
        return await site_service.get_all_sites()
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"获取场地信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取场地信息失败")