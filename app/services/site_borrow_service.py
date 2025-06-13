from app.models.site_borrow import SiteBorrow
from app.models.site import Site
from loguru import logger
from fastapi import HTTPException
from datetime import datetime
from app.core.utils import parse_datetime
import asyncio

class SiteBorrowService:
    """场地借用服务类：处理场地借用相关的业务逻辑"""

    def _db_operations(self, application_data: dict, userid: str):
        """
        【同步函数】封装所有数据库读写操作。
        这个函数不应直接 await，而是通过 asyncio.to_thread 运行。
        """
        site_id = application_data.get("site_id")
        number = application_data.get("number")

        logger.info(f"检查场地状态 | 场地ID: {site_id} | 工位号: {number}")

        # 1. 检查场地是否存在
        site = Site.objects(site_id=site_id, number=number).first()
        if not site:
            logger.warning(f"场地不存在 | 场地ID: {site_id} | 工位号: {number}")
            return "NOT_FOUND", "场地不存在"

        # 2. 检查场地是否已被占用 - 这是关键逻辑
        if site.is_occupied:
            logger.warning(f"场地已被占用 | 场地ID: {site_id} | 工位号: {number}")
            # 返回一个明确的状态码，让异步函数来处理并抛出正确的HTTPException
            return "OCCUPIED", "该场地当前已被占用，无法申请。"
        
        # --- 只有在场地未被占用时，才执行以下创建操作 ---
        try:
            apply_id = SiteBorrow.generate_apply_id()
            
            borrow = SiteBorrow(
                apply_id=apply_id,
                userid=userid,
                name=application_data["name"],
                student_id=application_data["student_id"],
                phone_num=application_data["phone_num"],
                email=application_data["email"],
                purpose=application_data["purpose"],
                project_id=application_data.get("project_id", ""),
                mentor_name=application_data["mentor_name"],
                mentor_phone_num=application_data["mentor_phone_num"],
                site_id=site_id,
                site=application_data["site"],
                number=number,
                start_time=application_data["start_time"],
                end_time=application_data["end_time"],
                state=0
            )
            borrow.save()
            
            logger.info(f"标记场地为已占用 | 场地ID: {site_id} | 工位号: {number}")
            site.is_occupied = True
            site.save()
            
            logger.info(f"场地借用申请创建成功 | 申请ID: {apply_id}")
            return "SUCCESS", apply_id
        except Exception as e:
            logger.error(f"在数据库操作中创建场地借用申请失败: {str(e)}")
            return "DB_ERROR", str(e)
    
    async def create_borrow_application(self, application_data: dict, userid: str):
        """
        【异步函数】创建场地借用申请的主入口。
        负责调用同步数据库函数并处理返回结果。
        """
        logger.info(f"开始创建场地借用申请 | 用户: {userid}")
        
        # 1. 前置验证（例如时间格式）
        for time_field in ["start_time", "end_time"]:
            time_value = application_data.get(time_field, "")
            if not parse_datetime(time_value):
                detail_msg = f"时间格式错误: {time_field} - 应为ISO 8601兼容格式 (如: 2024-02-13)"
                logger.error(f"时间格式验证失败 | 字段: {time_field} | 值: {time_value}")
                raise HTTPException(status_code=400, detail=detail_msg)
        
        try:
            # 2. 异步执行所有数据库相关操作
            status, result = await asyncio.to_thread(
                self._db_operations, application_data, userid
            )

            # 3. 根据同步函数返回的状态码，抛出相应的 HTTP 异常
            if status == "NOT_FOUND":
                raise HTTPException(status_code=404, detail=result)
            
            if status == "OCCUPIED":
                # 这是最关键的修复：现在我们从这里抛出正确的异常
                raise HTTPException(status_code=409, detail=result) # 409 Conflict 是更合适的代码

            if status == "DB_ERROR":
                 raise HTTPException(status_code=500, detail=f"数据库服务异常: {result}")

            # 4. 如果一切顺利，result 就是 apply_id
            return result
            
            logger.info(f"场地借用申请创建成功 | 申请ID: {apply_id} | 场地: {application_data['site']} | 工位号: {number}")
            return apply_id
        
        except HTTPException as he:
            # 重新抛出已知的HTTP异常，让FastAPI框架处理
            raise he    
        except Exception as e:
            logger.error(f"创建场地借用申请失败: {str(e)}")
            raise HTTPException(status_code=500, detail="创建场地借用申请失败")