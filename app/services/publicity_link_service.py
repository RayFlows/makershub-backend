from typing import List, Optional
from app.models.publicity_link import PublicityLink
from app.models.user import User
from loguru import logger
from datetime import datetime

class PublicityLinkService:
    """
    秀米链接业务逻辑层
    - 负责增删改查、审核流程等操作
    """

    async def create_link(self, submitter_id: str, link_url: str) -> Optional[PublicityLink]:
        """提交秀米链接"""
        try:
            submitter = User.objects(userid=submitter_id).first()
            if not submitter:
                logger.error(f"提交人不存在: {submitter_id}")
                return None

            # 检查权限（权限 ≥1 可提交）
            if submitter.role < 1:
                logger.error(f"用户 {submitter_id} 权限不足（需 ≥1）")
                return None

            link = PublicityLink(
                submitter=submitter,
                link_url=link_url,
                audit_status=0  # 初始待审核
            )
            link.save()
            return link
        except Exception as e:
            logger.error(f"创建秀米链接失败: {e}")
            return None

    async def get_all_links(self) -> List[PublicityLink]:
        """获取所有秀米链接（权限校验在路由层做）"""
        try:
            return PublicityLink.objects().order_by("-submit_time")
        except Exception as e:
            logger.error(f"查询所有秀米链接失败: {e}")
            return []

    async def get_user_links(self, user_id: str) -> List[PublicityLink]:
        """获取某用户提交的秀米链接"""
        try:
            return PublicityLink.objects(submitter__userid=user_id).order_by("-submit_time")
        except Exception as e:
            logger.error(f"查询用户 {user_id} 的秀米链接失败: {e}")
            return []

    async def delete_link(self, link_id: str) -> bool:
        """删除秀米链接（需校验权限，建议路由层处理）"""
        try:
            link = PublicityLink.objects(id=link_id).first()
            if link:
                link.delete()
                return True
            return False
        except Exception as e:
            logger.error(f"删除秀米链接 {link_id} 失败: {e}")
            return False

    async def update_link(self, link_id: str, **kwargs) -> Optional[PublicityLink]:
        """更新秀米链接（一般用于补充审核信息）"""
        try:
            link = PublicityLink.objects(id=link_id).first()
            if not link:
                return None

            # 仅允许更新审核相关字段（可根据需求扩展）
            allowed_fields = ["audit_status", "audit_comment", "auditor", "audit_time"]
            for field, value in kwargs.items():
                if field in allowed_fields and hasattr(link, field):
                    setattr(link, field, value)

            link.audit_time = datetime.now()  # 自动更新审核时间
            link.save()
            return link
        except Exception as e:
            logger.error(f"更新秀米链接 {link_id} 失败: {e}")
            return None

    async def audit_link(
        self,
        link_id: str,
        auditor: User,
        pass_status: bool,
        comment: str = ""
    ) -> Optional[PublicityLink]:
        """执行审核操作（封装更新逻辑）"""
        status = 1 if pass_status else 2
        return await self.update_link(
            link_id,
            audit_status=status,
            audit_comment=comment,
            auditor=auditor,
            audit_time=datetime.now()
        )