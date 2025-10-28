# app/services/site_service.py
"""
场地服务类（小程序端）
处理场地相关的业务逻辑。
[v2.0 SQLAlchemy 迁移版]
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from fastapi import HTTPException
from datetime import datetime
import random

from app.models.site import Site

class SiteService:
    """场地服务类：处理场地相关的业务逻辑。"""
    
    @staticmethod
    def _generate_site_id() -> str:
        """
        生成场地ID: ST + 当前时间戳(精确到毫秒) + 3位随机数。
        这是一个辅助业务逻辑函数，从模型层移动至此。
        """
        now = datetime.utcnow()
        timestamp = now.strftime("%Y%m%d%H%M%S%f")[:-3]
        random_suffix = f"{random.randint(0,999):03d}"
        return f"ST{timestamp}_{random_suffix}"

    async def add_site(self, db: AsyncSession, site_data: dict):
        """
        添加场地及多个工位信息。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            site_data: 包含场地信息的字典，格式如:
                {
                    "site": "二基楼B208+",
                    "details": [{"number": 1}, {"number": 2}]
                }
        """
        try:
            site_name = site_data["site"]
            details = site_data["details"]
            
            # 1. 生成一个唯一的 site_id 供本次批量创建的所有工位共享
            site_id = self._generate_site_id()
            logger.info(f"添加场地 | 场地位置: {site_name} | 工位数: {len(details)} | SiteID: {site_id}")
            
            # 2. 创建所有工位的ORM实例
            new_sites = [
                Site(
                    site_id=site_id,
                    site=site_name,
                    number=detail["number"],
                    is_occupied=False
                )
                for detail in details
            ]
            
            # 3. 使用 add_all 批量添加到会话，并用一次 commit 提交
            if new_sites:
                db.add_all(new_sites)
                await db.commit()
                logger.info(f"成功将 {len(new_sites)} 个新工位提交到数据库。")
            
            return {
                "code": 200,
                "message": "场地添加成功",
                "site_id": site_id
            }
        except Exception as e:
            await db.rollback() # 发生任何错误时回滚事务
            logger.error(f"添加场地失败: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="添加场地失败")
    
    async def get_all_sites(self, db: AsyncSession):
        """
        获取所有场地信息，并按场地名称分组。
        
        Args:
            db: SQLAlchemy的异步数据库会话。
            
        Returns:
            list: 包含所有场地信息的列表。
        """
        try:
            logger.info("开始获取所有场地信息...")
            
            # 1. 从数据库获取所有工位记录，并按场地和工位号排序
            stmt = select(Site).order_by(Site.site, Site.number)
            result = await db.execute(stmt)
            all_sites = result.scalars().all()
            logger.info(f"成功获取 {len(all_sites)} 个工位记录。")
            
            # 2. 在Python内存中按场地位置进行分组 (业务逻辑不变)
            sites_grouped = {}
            for site_record in all_sites:
                if site_record.site not in sites_grouped:
                    sites_grouped[site_record.site] = {
                        "site_id": site_record.site_id,
                        "site": site_record.site,
                        "details": []
                    }
                
                sites_grouped[site_record.site]["details"].append({
                    "number": site_record.number,
                    "is_occupied": site_record.is_occupied
                })
            
            # 3. 转换为API所需的列表格式
            site_list = list(sites_grouped.values())
            logger.info(f"获取场地信息成功 | 共 {len(site_list)} 个场地")
            
            return {
                "code": 200,
                "message": "successfully get all sites",
                "sites": site_list
            }

        except Exception as e:
            logger.error(f"获取场地信息失败: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="获取场地信息失败")