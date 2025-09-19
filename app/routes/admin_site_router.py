# app/routes/admin_site_router.py
"""
管理员场地路由模块
提供管理员端的场地管理API接口
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Header
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.core.logging import logger
from app.core.admin_auth import verify_admin_token
from app.services.admin_site_service import AdminSiteService

router = APIRouter()

# ========== 请求模型定义 ==========

class SiteCreateRequest(BaseModel):
    """场地创建请求模型"""
    site: str = Field(..., description="场地名称")
    workstations: List[int] = Field(..., description="工位号列表")
    
    class Config:
        schema_extra = {
            "example": {
                "site": "二基楼B208+",
                "workstations": [1, 2, 3, 4, 5, 6]
            }
        }

class SiteUpdateRequest(BaseModel):
    """场地更新请求模型"""
    new_name: Optional[str] = Field(None, description="新场地名称")
    add_workstations: Optional[List[int]] = Field(None, description="新增工位列表")
    remove_workstations: Optional[List[int]] = Field(None, description="删除工位列表")
    
    class Config:
        schema_extra = {
            "example": {
                "new_name": "二基楼B208+实验室",
                "add_workstations": [7, 8],
                "remove_workstations": [1]
            }
        }

# ========== 认证依赖 ==========

async def get_admin_auth(authorization: Optional[str] = Header(None)):
    """
    验证管理员token
    从Header中获取Authorization并验证
    """
    if not authorization:
        logger.warning("[AdminSiteRouter] 未提供认证token")
        raise HTTPException(status_code=401, detail="未提供认证token")
    
    # 移除 "Bearer " 前缀
    token = authorization.replace("Bearer ", "")
    
    # 使用管理员认证验证token
    username = verify_admin_token(token)
    
    if not username:
        logger.warning("[AdminSiteRouter] 无效的认证token")
        raise HTTPException(status_code=401, detail="无效的认证token")
    
    logger.debug(f"[AdminSiteRouter] 管理员认证成功: {username}")
    return username

# ========== API路由 ==========

@router.get("/list")
async def get_site_list(
    admin: str = Depends(get_admin_auth),
    site: Optional[str] = Query(None, description="场地位置"),
    is_occupied: Optional[str] = Query(None, description="占用状态")
):
    """
    获取场地列表（管理员）
    
    支持按场地位置和占用状态筛选
    """
    try:
        logger.info(f"[AdminSiteRouter] 管理员 {admin} 请求场地列表")
        
        # 构建筛选条件
        filters = {}
        if site:
            filters['site'] = site
        if is_occupied is not None:
            filters['is_occupied'] = is_occupied
        
        result = AdminSiteService.get_all_sites_admin(filters)
        return result
        
    except Exception as e:
        logger.error(f"[AdminSiteRouter] 获取场地列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create")
async def create_site(
    request: SiteCreateRequest,
    admin: str = Depends(get_admin_auth)
):
    """
    创建新场地（管理员）
    
    批量创建指定场地的多个工位
    """
    try:
        logger.info(f"[AdminSiteRouter] 管理员 {admin} 创建场地: {request.site}")
        
        result = AdminSiteService.create_site_admin(request.dict())
        
        # 记录操作日志
        logger.info(f"管理员操作日志 | 操作人: {admin} | 操作: 创建场地 | "
                   f"场地: {request.site} | 工位数: {len(request.workstations)}")
        
        return result
        
    except ValueError as e:
        logger.warning(f"[AdminSiteRouter] 创建场地参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[AdminSiteRouter] 创建场地失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/update/{site_name}")
async def update_site(
    site_name: str,
    request: SiteUpdateRequest,
    admin: str = Depends(get_admin_auth)
):
    """
    更新场地信息（管理员）
    
    支持修改场地名称、增加工位、删除工位
    """
    try:
        logger.info(f"[AdminSiteRouter] 管理员 {admin} 更新场地: {site_name}")
        
        # 过滤掉None值，只更新提供的字段
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        
        if not update_data:
            raise ValueError("没有提供要更新的数据")
        
        result = AdminSiteService.update_site_admin(site_name, update_data)
        
        # 记录操作日志
        logger.info(f"管理员操作日志 | 操作人: {admin} | 操作: 更新场地 | "
                   f"场地: {site_name} | 更新内容: {list(update_data.keys())}")
        
        return result
        
    except ValueError as e:
        logger.warning(f"[AdminSiteRouter] 更新场地参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[AdminSiteRouter] 更新场地失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete/{site_name}")
async def delete_site(
    site_name: str,
    admin: str = Depends(get_admin_auth)
):
    """
    删除场地（管理员）
    
    只有当场地所有工位都未被占用且无未完成借用申请时才能删除
    """
    try:
        logger.info(f"[AdminSiteRouter] 管理员 {admin} 删除场地: {site_name}")
        
        result = AdminSiteService.delete_site_admin(site_name)
        
        # 记录操作日志
        logger.info(f"管理员操作日志 | 操作人: {admin} | 操作: 删除场地 | 场地: {site_name}")
        
        return result
        
    except ValueError as e:
        logger.warning(f"[AdminSiteRouter] 删除场地失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[AdminSiteRouter] 删除场地失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/borrow-history/{site_name}")
async def get_site_borrow_history(
    site_name: str,
    admin: str = Depends(get_admin_auth)
):
    """
    获取场地借用历史（管理员）
    
    查看指定场地的所有借用记录
    """
    try:
        logger.info(f"[AdminSiteRouter] 管理员 {admin} 查看场地借用历史: {site_name}")
        
        result = AdminSiteService.get_site_borrow_history(site_name)
        return result
        
    except Exception as e:
        logger.error(f"[AdminSiteRouter] 获取借用历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_site_stats(
    admin: str = Depends(get_admin_auth)
):
    """
    获取场地统计信息（管理员）
    
    返回场地的总体统计数据
    """
    try:
        logger.info(f"[AdminSiteRouter] 管理员 {admin} 请求场地统计")
        
        # 获取所有场地以计算统计
        result = AdminSiteService.get_all_sites_admin()
        
        # 提取统计信息
        if result['code'] == 200:
            stats_data = {
                "code": 200,
                "message": "获取统计信息成功",
                "data": {
                    "stats": result['data']['stats'],
                    "site_distribution": {}  # 场地分布
                }
            }
            
            # 计算每个场地的占用率
            for site in result['data']['sites_list']:
                stats_data['data']['site_distribution'][site['site']] = {
                    'total': site['total_count'],
                    'occupied': site['occupied_count'],
                    'available': site['available_count'],
                    'occupancy_rate': round(
                        (site['occupied_count'] / site['total_count'] * 100) if site['total_count'] > 0 else 0,
                        1
                    )
                }
            
            return stats_data
        else:
            return result
        
    except Exception as e:
        logger.error(f"[AdminSiteRouter] 获取统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/review-borrow/{apply_id}")
async def review_site_borrow(
    apply_id: str,
    review_data: Dict[str, Any],
    admin: str = Depends(get_admin_auth)
):
    """
    审核场地借用申请（管理员）
    
    Args:
        apply_id: 申请ID
        review_data: {"state": 1/2, "review": "审核意见"}
    """
    try:
        logger.info(f"[AdminSiteRouter] 管理员 {admin} 审核场地申请: {apply_id}")
        
        from app.services.site_borrow_service import SiteBorrowService
        service = SiteBorrowService()
        
        state = review_data.get('state')
        review = review_data.get('review', '')
        
        if state not in [1, 2]:
            raise ValueError("状态值无效，1=打回，2=通过")
        
        # 调用原有的审核服务
        result = await service.review_application(apply_id, state, review)
        
        # 记录操作日志
        logger.info(f"管理员操作日志 | 操作人: {admin} | 操作: 审核场地申请 | "
                   f"申请ID: {apply_id} | 结果: {'通过' if state == 2 else '打回'}")
        
        return {
            "code": 200,
            "message": "审核成功",
            "data": {
                "apply_id": result[0],
                "state": result[1],
                "review": result[2]
            }
        }
        
    except ValueError as e:
        logger.warning(f"[AdminSiteRouter] 审核参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"[AdminSiteRouter] 审核失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/return-borrow/{apply_id}")
async def return_site_borrow(
    apply_id: str,
    admin: str = Depends(get_admin_auth)
):
    """
    确认场地归还（管理员）
    
    将借用状态从"通过未归还"改为"已归还"
    """
    try:
        logger.info(f"[AdminSiteRouter] 管理员 {admin} 确认场地归还: {apply_id}")
        
        from app.services.site_borrow_service import SiteBorrowService
        service = SiteBorrowService()
        
        # 调用归还服务
        result = await service.return_borrow_application(apply_id, admin)
        
        # 记录操作日志
        logger.info(f"管理员操作日志 | 操作人: {admin} | 操作: 确认场地归还 | 申请ID: {apply_id}")
        
        return {
            "code": 200,
            "message": "场地归还成功",
            "data": {
                "apply_id": result[0],
                "state": result[1]
            }
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"[AdminSiteRouter] 归还失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))