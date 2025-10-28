# app/routes/site_router.py
"""
场地路由模块（小程序端）
提供面向小程序用户的场地查询等接口。
[v2.0 SQLAlchemy 迁移版]
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.services.site_service import SiteService
from app.core.auth import require_permission_level
from app.core.database import get_db
from app.models.user import User # 导入User模型用于依赖注入

router = APIRouter()
site_service = SiteService()

# 添加场地（临时接口）
@router.post("/add", summary="添加场地（临时接口）")
async def add_site(
    site_data: dict,
    db: AsyncSession = Depends(get_db)
    # user: User = Depends(require_permission_level(2))  # 权限暂时注释，方便测试
):
    """
    添加场地信息（临时接口）。
    用于初始化场地数据，后续将由管理员面板的功能替代。
    
    Args:
        site_data: 包含场地名称和工位号列表的字典。
        db: 数据库会话依赖。
    """
    try:
        # 验证必要字段 (业务逻辑不变)
        if "site" not in site_data or "details" not in site_data:
            logger.warning(f"添加场地请求缺少必要字段: {site_data}")
            raise HTTPException(status_code=400, detail="缺少 'site' 或 'details' 字段")
        
        logger.info(f"收到添加场地请求: {site_data.get('site')}")
        # 调用服务层添加场地
        result = await site_service.add_site(db, site_data)
        return result
    except HTTPException as he:
        # 直接重新抛出已知的HTTP异常
        raise he
    except Exception as e:
        logger.error(f"添加场地失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="添加场地失败")

# 获取所有场地
@router.get("/get-all", summary="获取所有场地工位信息")
async def get_all_sites(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission_level(0))  # 允许所有已登录用户
):
    """
    获取所有场地信息。
    返回所有场地及其工位状态，按场地名称分组。
    
    Args:
        db: 数据库会话依赖。
        user: 当前认证用户，用于权限检查。
    """
    try:
        logger.info(f"用户 {user.userid} 请求获取所有场地信息。")
        # 调用服务层获取场地信息
        return await site_service.get_all_sites(db)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"获取场地信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取场地信息失败")