# app/routes/publicity_link_router.py
"""
秀米链接路由模块 (PublicityLink Router Module)
本模块负责处理所有与秀米链接提交和审核相关的API路由。
[v0.2 SQLAlchemy 重构版]
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from loguru import logger

from app.services.publicity_link_service import PublicityLinkService
from app.core.auth import require_permission_level
from app.models.user import User
from app.core.database import get_db

router = APIRouter()

# --- Pydantic Schemas for Request Validation ---

class SubmitLinkRequest(BaseModel):
    """提交秀米链接的请求体模型"""
    title: str = Field(..., min_length=1, max_length=100)
    # [v0.2 移除] name 不再由前端提供，将通过当前登录用户自动获取
    # name: str
    link: str # 保持 str 类型以兼容不带协议的链接

class UpdateLinkRequest(BaseModel):
    """更新秀米链接的请求体模型"""
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    # [v0.2 移除] name 不再可被直接更新
    # name: Optional[str] = None
    link: Optional[str] = None

class ReviewRequest(BaseModel):
    """审核秀米链接的请求体模型"""
    state: int = Field(..., ge=1, le=2) # 状态必须是 1 (打回) 或 2 (通过)
    review: str = ""

# --- API Endpoints ---

@router.post("/post", summary="提交秀米链接", dependencies=[Depends(require_permission_level(1))])
async def submit_publicity_link(
    request: SubmitLinkRequest,
    current_user: User = Depends(require_permission_level(1)),
    db: AsyncSession = Depends(get_db)
):
    """(成员权限) 提交一个新的秀米链接以供审核。"""
    logger.info(f"路由层: 用户 {current_user.userid} 正在提交秀米链接: {request.title}")
    try:
        service = PublicityLinkService()
        # [v0.2 适配] 不再传入 name，而是传入完整的 current_user 对象
        new_link = await service.create_link(
            db=db,
            user=current_user,
            title=request.title,
            link_url=request.link
        )
        logger.success(f"路由层: 秀米链接创建成功, LinkID: {new_link.link_id}")
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
    """(管理员权限) 获取所有已提交的秀米链接，用于审核页面。"""
    logger.info("路由层: 管理员正在请求所有秀米链接...")
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
    # [v0.2 改造] 我们需要一个预加载了关系的 User 对象
    # 为此，创建一个新的依赖项来处理
    current_user: User = Depends(require_permission_level(1)),
    db: AsyncSession = Depends(get_db)
):
    """(成员权限) 获取当前用户提交的所有秀米链接。"""
    logger.info(f"路由层: 正在获取用户 {current_user.userid} 的秀米链接...")
    try:
        service = PublicityLinkService()
        
        # [关键修复]
        # 1. 将从 auth 中获取的、处于“游离”状态的 current_user 对象，合并（merge）到当前路由的数据库会话（db）中。
        #    db.merge() 会返回一个附加到当前会话的、全新的 User 实例。
        merged_user = await db.merge(current_user)
        
        # 2. 对这个新合并的、属于当前会话的 merged_user 对象执行 refresh 操作来加载关系。
        await db.refresh(merged_user, attribute_names=['publicity_links'])
        
        # 3. 将这个“完全体”的 user 对象传递给 service。
        links = await service.get_user_links(merged_user)
        
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
    """(成员权限) 更新一个已提交但未审核通过的秀米链接。"""
    logger.info(f"路由层: 用户 {current_user.userid} 正在更新秀米链接: {link_id}")
    try:
        service = PublicityLinkService()
        update_data = request.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields provided for update")

        # [v0.2 适配] Service 现在需要 user.id 进行权限检查
        updated_link = await service.update_link(db, link_id, current_user.id, update_data)
        
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
        logger.warning(f"权限错误: {e} | UserID: {current_user.id}, LinkID: {link_id}")
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        logger.warning(f"值错误: {e} | UserID: {current_user.id}, LinkID: {link_id}")
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
    """(管理员权限) 审核一个待处理的秀米链接。"""
    logger.info(f"路由层: 管理员正在审核秀米链接: {link_id}")
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