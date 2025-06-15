from fastapi import APIRouter, HTTPException, Depends
from loguru import logger
from app.services.publicity_link_service import PublicityLinkService
from app.core.auth import AuthMiddleware
from app.models.user import User
from app.models.publicity_link import PublicityLink
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()
service = PublicityLinkService()


# 请求模型：提交秀米链接
class SubmitLinkRequest(BaseModel):
    link_url: str  # 需包含 https://


# 请求模型：审核操作
class AuditRequest(BaseModel):
    pass_audit: bool  # 是否通过
    comment: Optional[str] = ""  # 审核意见


@router.post("/submit")
async def submit_publicity_link(
        request: SubmitLinkRequest,
        current_user: User = Depends(AuthMiddleware.get_current_user)
):
    """提交秀米链接（权限 ≥1 可访问）"""
    if current_user.role < 1:
        raise HTTPException(status_code=403, detail="权限不足（需 ≥1）")

    link = await service.create_link(current_user.userid, request.link_url)
    if not link:
        raise HTTPException(status_code=500, detail="提交失败，请检查链接格式或重试")

    return {
        "code": 200,
        "message": "提交成功，等待审核",
        "data": link.to_dict()
    }


@router.get("/all", response_model=List[PublicityLink])
async def get_all_links(
        current_user: User = Depends(AuthMiddleware.get_current_user)
):
    """获取所有秀米链接（权限 = 2 可访问）"""
    if current_user.role != 2:
        raise HTTPException(status_code=403, detail="权限不足（需 = 2）")

    links = await service.get_all_links()
    return [link.to_dict() for link in links]


@router.get("/user", response_model=List[PublicityLink])
async def get_user_links(
        current_user: User = Depends(AuthMiddleware.get_current_user)
):
    """获取当前用户提交的秀米链接（所有角色可访问自己的）"""
    links = await service.get_user_links(current_user.userid)
    return [link.to_dict() for link in links]


@router.delete("/{link_id}")
async def delete_link(
        link_id: str,
        current_user: User = Depends(AuthMiddleware.get_current_user)
):
    """删除秀米链接（需是提交人或权限 ≥2）"""
    link = PublicityLink.objects(id=link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="链接不存在")

    # 校验权限：提交人或权限 ≥2
    if link.submitter.userid != current_user.userid and current_user.role < 2:
        raise HTTPException(status_code=403, detail="权限不足（仅提交人或权限 ≥2 可删除）")

    success = await service.delete_link(link_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除失败")

    return {
        "code": 200,
        "message": "删除成功"
    }


@router.patch("/{link_id}/audit")
async def audit_link(
        link_id: str,
        request: AuditRequest,
        current_user: User = Depends(AuthMiddleware.get_current_user)
):
    """审核秀米链接（权限 ≥2 可访问）"""
    if current_user.role < 2:
        raise HTTPException(status_code=403, detail="权限不足（需 ≥2）")

    link = await service.audit_link(
        link_id,
        current_user,
        request.pass_audit,
        request.comment
    )
    if not link:
        raise HTTPException(status_code=500, detail="审核失败")

    # TODO: 这里可扩展「通知提交人」逻辑（调用微信服务等）
    return {
        "code": 200,
        "message": "审核完成",
        "data": link.to_dict()
    }


@router.patch("/{link_id}")
async def update_link(
        link_id: str,
        request: AuditRequest,  # 若需更灵活更新，可自定义 UpdateRequest
        current_user: User = Depends(AuthMiddleware.get_current_user)
):
    """更新秀米链接（一般用于审核补充，实际可根据需求扩展字段）"""
    # 简单示例：仅允许审核人员更新（可扩展更细权限）
    if current_user.role < 2:
        raise HTTPException(status_code=403, detail="权限不足（需 ≥2）")

    link = await service.update_link(
        link_id,
        audit_status=1 if request.pass_audit else 2,
        audit_comment=request.comment,
        auditor=current_user,
        audit_time=datetime.now()
    )
    if not link:
        raise HTTPException(status_code=500, detail="更新失败")

    return {
        "code": 200,
        "message": "更新成功",
        "data": link.to_dict()
    }