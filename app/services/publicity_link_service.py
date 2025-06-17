from app.models.publicity_link import PublicityLink
from loguru import logger
from fastapi import HTTPException
from app.core.utils import parse_datetime

class PublicityLinkService:
    """秀米链接服务类：处理秀米链接相关的业务逻辑"""
    
    async def create_link(self, userid: str, name: str, title: str, link_url: str):
        """
        创建秀米链接
        
        Args:
            userid: 用户ID
            name: 发布人姓名
            title: 推文标题
            link_url: 链接地址
            
        Returns:
            str: 创建的链接ID
        """
        try:
            # 验证URL格式
            if not link_url.startswith(("http://", "https://")):
                raise HTTPException(
                    status_code=400,
                    detail="无效的URL格式，必须以http://或https://开头"
                )
            
            # 创建新链接
            link = PublicityLink(
                link_id=PublicityLink.generate_link_id(),
                userid=userid,
                name=name,
                title=title,
                link=link_url,
                state=0  # 初始状态为待审核
            )
            link.save()
            
            logger.info(f"秀米链接创建成功 | 链接ID: {link.link_id} | 用户: {userid}")
            return link.link_id
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"创建秀米链接失败: {str(e)}")
            raise HTTPException(status_code=500, detail="创建秀米链接失败")
    
    async def get_all_links(self):
        """
        获取所有秀米链接
        
        Returns:
            list: 包含所有链接的字典列表
        """
        try:
            links = PublicityLink.objects().order_by("-create_time")
            return [{
                "link_id": link.link_id,
                "title": link.title,
                "create_time": link.create_time.isoformat() + "Z",
                "name": link.name,
                "link": link.link,
                "state": link.state,
                "review": link.review
            } for link in links]
        except Exception as e:
            logger.error(f"获取所有秀米链接失败: {str(e)}")
            raise HTTPException(status_code=500, detail="获取所有秀米链接失败")
    
    async def get_user_links(self, userid: str):
        """
        获取用户的所有秀米链接
        
        Args:
            userid: 用户ID
            
        Returns:
            list: 包含用户链接的字典列表
        """
        try:
            links = PublicityLink.objects(userid=userid).order_by("-create_time")
            return [{
                "link_id": link.link_id,
                "title": link.title,
                "create_time": link.create_time.isoformat() + "Z",
                "name": link.name,
                "link": link.link,
                "state": link.state,
                "review": link.review
            } for link in links]
        except Exception as e:
            logger.error(f"获取用户秀米链接失败: {str(e)} | 用户ID: {userid}")
            raise HTTPException(status_code=500, detail="获取用户秀米链接失败")
    
    async def update_link(self, link_id: str, userid: str, update_data: dict):
        """
        更新秀米链接
        
        Args:
            link_id: 链接ID
            userid: 用户ID（用于验证权限）
            update_data: 更新数据
            
        Returns:
            tuple: (link_id, 实际更新的字段字典)
        """
        try:
            # 查询链接记录
            link = PublicityLink.objects(link_id=link_id).first()
            if not link:
                logger.warning(f"链接不存在 | 链接ID: {link_id}")
                raise HTTPException(
                    status_code=404,
                    detail="no such link",
                    headers={"X-Error": "Link not found"}
                )
            
            # 检查当前用户是否是提交人
            if link.userid != userid:
                logger.warning(f"用户无权限更新该链接 | 当前用户: {userid} | 提交人: {link.userid}")
                raise HTTPException(
                    status_code=403,
                    detail="forbidden to update others' link"
                )
            
            # 检查链接状态是否为0（待审核）或2（已打回）
            if link.state not in [0, 2]:
                logger.warning(f"链接状态不允许更新 | 当前状态: {link.state}")
                raise HTTPException(
                    status_code=400,
                    detail="forbiddened link state",
                    data={
                        "target": "0 or 2",
                        "actual": link.state
                    }
                )
            
            # 定义允许更新的字段
            allowed_fields = ["title", "name", "link"]
            
            # 记录实际更新的字段
            changed_fields = {}
            
            # 遍历更新数据，只更新允许的字段
            for field, value in update_data.items():
                if field in allowed_fields:
                    # 特殊处理链接字段
                    if field == "link" and not value.startswith(("http://", "https://")):
                        raise HTTPException(
                            status_code=400,
                            detail="无效的URL格式，必须以http://或https://开头"
                        )
                    
                    # 记录更改
                    changed_fields[field] = {
                        "old": getattr(link, field),
                        "new": value
                    }
                    
                    # 更新字段值
                    setattr(link, field, value)
            
            # 如果有更新字段，保存并重置状态为待审核
            if changed_fields:
                link.state = 0  # 重置为待审核状态
                link.review = ""  # 清空审核反馈
                link.save()
                logger.info(f"链接已更新 | 链接ID: {link_id} | 更新字段数: {len(changed_fields)}")
            
            return (link_id, {k: v["new"] for k, v in changed_fields.items()})
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"更新秀米链接失败: {str(e)}")
            raise HTTPException(status_code=500, detail="update link failed")
    
    async def review_link(self, link_id: str, state: int, review: str = ""):
        """
        审核秀米链接
        
        Args:
            link_id: 链接ID
            state: 新状态 (1:通过, 2:打回)
            review: 审核反馈
            
        Returns:
            tuple: (link_id, state, review)
        """
        try:
            # 查询链接记录
            link = PublicityLink.objects(link_id=link_id).first()
            if not link:
                logger.warning(f"链接不存在 | 链接ID: {link_id}")
                raise HTTPException(
                    status_code=404,
                    detail="no such link",
                    headers={"X-Error": "Link not found"}
                )
            
            # 验证新状态值
            if state not in [1, 2]:
                logger.warning(f"无效的新状态值: {state}")
                raise HTTPException(
                    status_code=400,
                    detail="invalid state value",
                    data={
                        "allowed": [1, 2],
                        "actual": state
                    }
                )
            
            # 检查当前状态是否为0（待审核）
            if link.state != 0:
                logger.warning(f"链接状态不允许审核 | 当前状态: {link.state}")
                raise HTTPException(
                    status_code=400,
                    detail="link not in pending state",
                    data={
                        "required": 0,
                        "actual": link.state
                    }
                )
            
            # 更新链接状态
            link.state = state
            link.review = review
            link.save()
            
            logger.info(f"链接已审核 | 链接ID: {link_id} | 新状态: {state}")
            return (link_id, state, review)
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"审核秀米链接失败: {str(e)}")
            raise HTTPException(status_code=500, detail="review link failed")