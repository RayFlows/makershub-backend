# app/routes/publicity_link_router.py
"""
秀米链接路由模块 (PublicityLink Router Module)
本模块负责处理所有与秀米链接提交和审核相关的API路由。
[v2.0 SQLAlchemy 迁移版]
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from loguru import logger

from app.services.publicity_link_service import PublicityLinkService
from app.core.auth import require_permission_level
from app.models.user import User
from app.core.database import get_db

router = APIRouter()
# 我们不再需要全局实例化 service
# service = PublicityLinkService()

# --- Pydantic Schemas for Request Validation ---

class SubmitLinkRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=50)
    # link: HttpUrl # 使用 Pydantic 的 URL 类型进行自动验证
    link: str # 改回 str 类型以兼容不带协议的链接

class UpdateLinkRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    # link: Optional[HttpUrl] = None # 使用 Pydantic 的 URL 类型进行自动验证
    link: str # 改回 str 类型以兼容不带协议的链接

class ReviewRequest(BaseModel):
    state: int = Field(..., ge=1, le=2) # 状态必须是 1 (通过) 或 2 (打回)
    review: str = ""

# --- API Endpoints ---

@router.post("/post", summary="提交秀米链接", dependencies=[Depends(require_permission_level(1))])
async def submit_publicity_link(
    request: SubmitLinkRequest,
    current_user: User = Depends(require_permission_level(1)),
    db: AsyncSession = Depends(get_db)
):
    """提交一个新的秀米链接以供审核。"""
    try:
        service = PublicityLinkService()
        logger.info(f"用户 {current_user.userid} 正在提交秀米链接: {request.title}")
        
        new_link = await service.create_link(
            db=db,
            userid=current_user.userid,
            name=request.name,
            title=request.title,
            link_url=str(request.link)
        )
        
        return {
            "code": 200,
            "message": "successfully post xiumi link",
            "data": {"link_id": new_link.link_id}
        }
    except Exception as e:
        logger.error(f"提交秀米链接失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误，提交失败")

@router.get("/view-all", summary="获取所有秀米链接 (管理员)", dependencies=[Depends(require_permission_level(2))])
async def get_all_links(db: AsyncSession = Depends(get_db)):
    """获取所有已提交的秀米链接，用于审核。"""
    try:
        service = PublicityLinkService()
        links = await service.get_all_links(db)
        return {
            "code": 200,
            "message": "successfully get all xiumi link",
            "data": {
                "total": len(links),
                "list": links
            }
        }
    except Exception as e:
        logger.error(f"获取所有秀米链接失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误，获取失败")

@router.get("/view-my", summary="获取我的秀米链接", dependencies=[Depends(require_permission_level(1))])
async def get_user_links(
    current_user: User = Depends(require_permission_level(1)),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户提交的所有秀米链接。"""
    try:
        service = PublicityLinkService()
        links = await service.get_user_links(db, current_user.userid)
        return {
            "code": 200,
            "message": "successfully get my xiumi link",
            "data": {
                "total": len(links),
                "list": links
            }
        }
    except Exception as e:
        logger.error(f"获取我的秀米链接失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误，获取失败")

@router.patch("/update/{link_id}", summary="更新我的秀米链接", dependencies=[Depends(require_permission_level(1))])
async def update_link(
    link_id: str,
    request: UpdateLinkRequest,
    current_user: User = Depends(require_permission_level(1)),
    db: AsyncSession = Depends(get_db)
):
    """更新一个已提交但未审核通过的秀米链接。"""
    try:
        service = PublicityLinkService()
        # exclude_unset=True 确保我们只传递用户真正想要更新的字段
        update_data = request.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields provided for update")

        # 将 Pydantic 的 HttpUrl 对象转换为字符串
        if 'link' in update_data:
            update_data['link'] = str(update_data['link'])

        updated_link = await service.update_link(db, link_id, current_user.userid, update_data)
        
        if updated_link is None:
            raise HTTPException(status_code=404, detail="Link not found")

        return {
            "code": 200,
            "message": "successfully update xiumi-link",
            "data": {
                "link_id": updated_link.link_id,
                "changed": update_data
            }
        }
    except PermissionError as e:
        logger.warning(f"权限错误: {e} | User: {current_user.userid}, LinkID: {link_id}")
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        logger.warning(f"值错误: {e} | User: {current_user.userid}, LinkID: {link_id}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新秀米链接失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误，更新失败")

@router.patch("/review/{link_id}", summary="审核秀米链接 (管理员)", dependencies=[Depends(require_permission_level(2))])
async def review_link(
    link_id: str,
    request: ReviewRequest,
    db: AsyncSession = Depends(get_db)
):
    """审核一个待处理的秀米链接。"""
    try:
        service = PublicityLinkService()
        reviewed_link = await service.review_link(db, link_id, request.state, request.review)

        if reviewed_link is None:
            raise HTTPException(status_code=404, detail="Link not found")

        return {
            "code": 200,
            "message": "successfully reviewed xiumi-link",
            "data": service._link_to_dict(reviewed_link)
        }
    except ValueError as e:
        logger.warning(f"审核操作值错误: {e} | LinkID: {link_id}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"审核秀米链接失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误，审核失败")