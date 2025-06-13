from app.models.site import Site
from loguru import logger
from fastapi import HTTPException

class SiteService:
    """场地服务类：处理场地相关的业务逻辑"""
    
    async def add_site(self, site_data: dict):
        """
        添加场地信息
        
        Args:
            site_data: 包含场地信息的字典
                {
                    "site": "二基楼B208+",
                    "details": [
                        {"number": 1},
                        {"number": 2},
                        {"number": 3}
                    ]
                }
        """
        try:
            # 生成场地ID
            site_id = Site.generate_site_id()
            logger.info(f"添加场地 | 场地位置: {site_data['site']} | 工位数: {len(site_data['details'])}")
            
            # 创建场地记录
            for detail in site_data["details"]:
                site = Site(
                    site_id=site_id,
                    site=site_data["site"],
                    number=detail["number"],
                    is_occupied=False
                )
                site.save()
            
            return {
                "code": 200,
                "message": "场地添加成功",
                "site_id": site_id
            }
        except Exception as e:
            logger.error(f"添加场地失败: {str(e)}")
            raise HTTPException(status_code=500, detail="添加场地失败")
    
    async def get_all_sites(self):
        """
        获取所有场地信息
        
        Returns:
            list: 包含所有场地信息的列表
        """
        try:
            logger.info("获取所有场地信息")
            
            # 按场地位置分组
            sites = {}
            for site in Site.objects():
                if site.site not in sites:
                    sites[site.site] = {
                        "site_id": site.site_id,
                        "site": site.site,
                        "details": []
                    }
                
                sites[site.site]["details"].append({
                    "number": site.number,
                    "is_occupied": site.is_occupied
                })
            
            # 转换为列表格式
            site_list = list(sites.values())
            
            return {
                "code": 200,
                "message": "successfully get all sites",
                "sites": site_list
            }
        except Exception as e:
            logger.error(f"获取场地信息失败: {str(e)}")
            raise HTTPException(status_code=500, detail="获取场地信息失败")