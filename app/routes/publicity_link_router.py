from fastapi import APIRouter, HTTPException, Depends
from app.services.publicity_link_service import PublicityLinkService
from app.core.auth import require_permission_level
from loguru import logger
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter()

# 请求模型：提交秀米链接
class SubmitLinkRequest(BaseModel):
    title: str
    name: str
    link: str

# 请求模型：更新秀米链接
class UpdateLinkRequest(BaseModel):
    title: Optional[str] = None
    name: Optional[str] = None
    link: Optional[str] = None

# 请求模型：审核秀米链接
class ReviewRequest(BaseModel):
    state: int
    review: str = ""

# 提交秀米链接
@router.post("/post")
async def submit_publicity_link(
    request: SubmitLinkRequest,
    user: dict = Depends(require_permission_level(1)),  # 需要权限1或2
    service: PublicityLinkService = Depends(PublicityLinkService)
):
    """提交秀米链接"""
    try:
        logger.info(f"提交秀米链接 | 用户: {user.userid}")
        
        # 调用服务层创建链接
        link_id = await service.create_link(
            userid=user.userid,
            name=request.name,
            title=request.title,
            link_url=request.link
        )
        
        return {
            "code": 200,
            "message": "successfully post xiumi link",
            "data": {
                "link_id": link_id
            }
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"提交秀米链接失败: {str(e)}")
        raise HTTPException(status_code=500, detail="提交秀米链接失败")

# 获取所有秀米链接
@router.get("/view-all")
async def get_all_links(
    user: dict = Depends(require_permission_level(2)),  # 需要权限2
    service: PublicityLinkService = Depends(PublicityLinkService)
):
    """获取所有秀米链接（审核页面使用）"""
    try:
        logger.info(f"获取所有秀米链接 | 请求用户: {user.userid}")
        
        # 调用服务层获取所有链接
        links = await service.get_all_links()
        
        return {
            "code": 200,
            "message": "successfully get all xiumi link",
            "data": {
                "total": len(links),
                "list": links
            }
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"获取所有秀米链接失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取所有秀米链接失败")

# 获取用户秀米链接
@router.get("/view-my")
async def get_user_links(
    user: dict = Depends(require_permission_level(1)),  # 需要权限1或2
    service: PublicityLinkService = Depends(PublicityLinkService)
):
    """获取当前用户的秀米链接"""
    try:
        logger.info(f"获取用户秀米链接 | 用户: {user.userid}")
        
        # 调用服务层获取用户链接
        links = await service.get_user_links(user.userid)
        
        return {
            "code": 200,
            "message": "successfully get my xiumi link",
            "data": {
                "total": len(links),
                "list": links
            }
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"获取用户秀米链接失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户秀米链接失败")

# 更新秀米链接
@router.patch("/update/{link_id}")
async def update_link(
    link_id: str,
    request: UpdateLinkRequest,
    user: dict = Depends(require_permission_level(1)),  # 需要权限1或2
    service: PublicityLinkService = Depends(PublicityLinkService)
):
    """更新秀米链接"""
    try:
        logger.info(f"更新秀米链接 | 链接ID: {link_id} | 用户: {user.userid}")
        
        # 转换为字典并移除空值
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        
        if not update_data:
            logger.warning("没有提供更新字段")
            raise HTTPException(
                status_code=400,
                detail="no fields provided for update"
            )
        
        # 调用服务层更新链接
        result = await service.update_link(link_id, user.userid, update_data)
        
        return {
            "code": 200,
            "message": "successfully update xiumi-link",
            "data": {
                "link_id": result[0],
                "changed": result[1]
            }
        }
    except HTTPException as he:
        if he.status_code == 400 and hasattr(he, 'data'):
            return JSONResponse(
                status_code=400,
                content={
                    "code": 400,
                    "message": he.detail,
                    "data": he.data
                }
            )
        raise he
    except Exception as e:
        logger.error(f"更新秀米链接失败: {str(e)}")
        raise HTTPException(status_code=500, detail="update link failed")

# 审核秀米链接
@router.patch("/review/{link_id}")
async def review_link(
    link_id: str,
    request: ReviewRequest,
    user: dict = Depends(require_permission_level(2)),  # 需要权限2
    service: PublicityLinkService = Depends(PublicityLinkService)
):
    """审核秀米链接"""
    try:
        logger.info(f"审核秀米链接 | 链接ID: {link_id} | 审核员: {user.userid}")
        
        # 调用服务层审核链接
        result = await service.review_link(link_id, request.state, request.review)
        
        return {
            "code": 200,
            "message": "successfully reviewed xiumi-link",
            "data": {
                "link_id": result[0],
                "state": result[1],
                "review": result[2]
            }
        }
    except HTTPException as he:
        if he.status_code == 400 and hasattr(he, 'data'):
            return JSONResponse(
                status_code=400,
                content={
                    "code": 400,
                    "message": he.detail,
                    "data": he.data
                }
            )
        raise he
    except Exception as e:
        logger.error(f"审核秀米链接失败: {str(e)}")
        raise HTTPException(status_code=500, detail="review link failed")