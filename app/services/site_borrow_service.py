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

    async def get_application_detail(self, apply_id: str) -> dict:
        """
        获取场地借用申请详情
        
        Args:
            apply_id: 申请ID
            
        Returns:
            dict: 包含申请详情的字典
            
        Raises:
            HTTPException: 申请不存在时抛出404错误
        """
        try:
            logger.info(f"查询场地借用详情 | 申请ID: {apply_id}")
            
            # 查询申请记录
            application = SiteBorrow.objects(apply_id=apply_id).first()
            if not application:
                logger.warning(f"申请不存在 | 申请ID: {apply_id}")
                raise HTTPException(
                    status_code=404,
                    detail="no such application",
                    headers={"X-Error": "Application not found"}
                )
            
            # 构建响应数据
            return {
                "apply_id": application.apply_id,
                "name": application.name,
                "student_id": application.student_id,
                "phone_num": application.phone_num,
                "email": application.email,
                "purpose": application.purpose,
                "project_id": application.project_id,
                "mentor_name": application.mentor_name,
                "mentor_phone_num": application.mentor_phone_num,
                "site": application.site,
                "number": application.number,
                "start_time": application.start_time,
                "end_time": application.end_time,
                "state": application.state,
                "review": application.review
            }
        except Exception as e:
            logger.error(f"获取申请详情失败: {str(e)}")
            raise HTTPException(status_code=500, detail="获取申请详情失败")
    
    async def get_all_applications(self) -> dict:
        """
        获取所有场地借用申请
        
        Returns:
            dict: 包含申请总数和简化列表的字典
        """
        try:
            logger.info("查询所有场地借用申请")
            
            # 查询所有申请记录
            applications = SiteBorrow.objects().only(
                "apply_id", "state", "created_at", "site", "number"
            )
            
            # 构建响应数据
            application_list = []
            for app in applications:
                application_list.append({
                    "apply_id": app.apply_id,  
                    "state": app.state,
                    "created_time": app.created_at.isoformat() + "Z",
                    "site": app.site,
                    "number": app.number
                })
            
            logger.info(f"找到 {len(application_list)} 条场地借用申请")
            
            return {
                "total": len(application_list),
                "list": application_list
            }
        except Exception as e:
            logger.error(f"获取全部场地申请失败: {str(e)}")
            raise HTTPException(status_code=500, detail="获取全部场地申请失败")

    async def get_user_applications(self, userid: str) -> dict:
        """
        获取指定用户的所有场地借用申请
        
        Args:
            userid: 用户ID
            
        Returns:
            dict: 包含申请总数和简化列表的字典
        """
        try:
            logger.info(f"查询用户场地借用申请 | 用户ID: {userid}")
            
            # 查询该用户的所有申请记录
            applications = SiteBorrow.objects(userid=userid).only(
                "apply_id", "state", "created_at", "site", "number"
            )
            
            # 构建响应数据
            application_list = []
            for app in applications:
                application_list.append({
                    "apply_id": app.apply_id,
                    "state": app.state,
                    "created_time": app.created_at.isoformat() + "Z",
                    "site": app.site,
                    "number": app.number
                })
            
            logger.info(f"找到 {len(application_list)} 条用户场地借用申请")
            
            return {
                "total": len(application_list),
                "list": application_list
            }
        except Exception as e:
            logger.error(f"获取用户场地申请列表失败: {str(e)}")
            raise HTTPException(status_code=500, detail="获取用户场地申请列表失败")

    async def cancel_application(self, apply_id: str, userid: str):
        """
        取消场地借用申请
        
        Args:
            apply_id: 申请ID
            userid: 当前用户ID（用于验证权限）
        
        Returns:
            apply_id: 取消成功的申请ID
        
        Raises:
            HTTPException: 各种错误情况
        """
        try:
            logger.info(f"取消场地申请 | 申请ID: {apply_id} | 用户: {userid}")
            
            # 查询申请记录
            application = SiteBorrow.objects(apply_id=apply_id).first()
            if not application:
                logger.warning(f"申请不存在 | 申请ID: {apply_id}")
                raise HTTPException(
                    status_code=404,
                    detail="no such application",
                    headers={"X-Error": "Application not found"}
                )
            
            # 检查当前用户是否是申请人
            if application.userid != userid:
                logger.warning(f"用户无权限取消该申请 | 当前用户: {userid} | 申请人: {application.userid}")
                raise HTTPException(
                    status_code=403,
                    detail="forbidden to cancel others' application"
                )
            
            # 检查申请状态是否为0（未审核）或1（打回）
            if application.state not in [0, 1]:
                logger.warning(f"申请状态不允许取消 | 当前状态: {application.state}")
                # 按照接口要求返回400，并附带目标状态和实际状态
                raise HTTPException(
                    status_code=400,
                    detail="forbiddened application state",
                    headers={"X-Error": "Application state not allowed"},
                    data={
                        "target": "0 or 1",
                        "actual": application.state
                    }
                )
            
            # 执行取消操作：更新申请状态，并释放场地
            # 注意：这里使用原子操作，先更新申请，再更新场地
            # 更新申请状态为4（取消）
            application.state = 4
            application.save()
            
            # 根据申请中的site_id和number找到场地，将其is_occupied置为false
            site = Site.objects(site_id=application.site_id, number=application.number).first()
            if site:
                site.is_occupied = False
                site.save()
                logger.info(f"场地已释放 | 场地ID: {application.site_id} | 工位号: {application.number}")
            else:
                # 场地不存在，记录错误但继续（因为申请已经取消）
                logger.error(f"场地不存在，无法释放 | 场地ID: {application.site_id} | 工位号: {application.number}")
            
            logger.info(f"申请已取消 | 申请ID: {apply_id}")
            return apply_id
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"取消场地申请失败: {str(e)}")
            raise HTTPException(status_code=500, detail="cancel site-application failed")

    async def review_application(self, apply_id: str, state: int, review: str = ""):
        """
        审核场地借用申请
        
        Args:
            apply_id: 申请ID
            state: 新状态 (1:打回, 2:通过)
            review: 审核反馈
        
        Returns:
            tuple: (apply_id, state, review)
        
        Raises:
            HTTPException: 各种错误情况
        """
        try:
            logger.info(f"审核场地申请 | 申请ID: {apply_id} | 新状态: {state} | 反馈: {review}")
            
            # 查询申请记录
            application = SiteBorrow.objects(apply_id=apply_id).first()
            if not application:
                logger.warning(f"申请不存在 | 申请ID: {apply_id}")
                raise HTTPException(
                    status_code=404,
                    detail="no such application",
                    headers={"X-Error": "Application not found"}
                )
            
            # 检查当前状态是否允许审核 (只有未审核状态才能审核)
            if application.state != 0:
                logger.warning(f"申请状态不允许审核 | 当前状态: {application.state}")
                raise HTTPException(
                    status_code=400,
                    detail="application not in pending state",
                    data={
                        "required": 0,
                        "actual": application.state
                    }
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
            
            # 检查审核反馈 (打回时必须提供反馈)
            if state == 1 and not review:
                logger.warning(f"打回申请时必须提供审核反馈")
                raise HTTPException(
                    status_code=400,
                    detail="review feedback required for rejected applications"
                )
            
            # 更新申请状态
            application.state = state
            application.review = review
            application.save()
            
            logger.info(f"申请已更新 | 申请ID: {apply_id} | 新状态: {state}")
            return (apply_id, state, review)
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"审核场地申请失败: {str(e)}")
            raise HTTPException(status_code=500, detail="review site-application failed")

    async def update_application(self, apply_id: str, userid: str, update_data: dict):
        """
        更新场地借用申请
        
        Args:
            apply_id: 申请ID
            userid: 当前用户ID（用于验证权限）
            update_data: 包含更新字段的字典
        
        Returns:
            tuple: (apply_id, 实际更新的字段字典)
        
        Raises:
            HTTPException: 各种错误情况
        """
        try:
            logger.info(f"更新场地申请 | 申请ID: {apply_id} | 用户: {userid}")
            
            # 查询申请记录
            application = SiteBorrow.objects(apply_id=apply_id).first()
            if not application:
                logger.warning(f"申请不存在 | 申请ID: {apply_id}")
                raise HTTPException(
                    status_code=404,
                    detail="no such application",
                    headers={"X-Error": "Application not found"}
                )
            
            # 检查当前用户是否是申请人
            if application.userid != userid:
                logger.warning(f"用户无权限更新该申请 | 当前用户: {userid} | 申请人: {application.userid}")
                raise HTTPException(
                    status_code=403,
                    detail="forbidden to update others' application"
                )
            
            # 检查申请状态是否为0（未审核）或1（打回）
            if application.state not in [0, 1]:
                logger.warning(f"申请状态不允许更新 | 当前状态: {application.state}")
                # 按照接口要求返回400，并附带目标状态和实际状态
                raise HTTPException(
                    status_code=400,
                    detail="forbiddened application state",
                    data={
                        "target": "0 or 1",
                        "actual": application.state
                    }
                )
            
            # 定义允许更新的字段列表
            allowed_fields = [
                "email", "end_time", "mentor_name", "mentor_phone_num", "name",
                "number", "phone_num", "project_id", "purpose", "site",
                "start_time", "student_id"
            ]
            
            # 记录实际更新的字段
            changed_fields = {}
            
            # 遍历更新数据，只更新允许的字段
            for field, value in update_data.items():
                if field in allowed_fields:
                    # 检查时间字段格式
                    if field in ["start_time", "end_time"]:
                        if not parse_datetime(value):
                            detail_msg = f"时间格式错误: {field} - 应为ISO 8601兼容格式 (如: 2024-02-13)"
                            logger.error(f"时间格式验证失败 | 字段: {field} | 值: {value}")
                            raise HTTPException(status_code=400, detail=detail_msg)
                    
                    # 记录更改
                    changed_fields[field] = {
                        "old": getattr(application, field),
                        "new": value
                    }
                    
                    # 更新字段值
                    setattr(application, field, value)
            
            # 如果有更新字段，保存申请并更新场地占用状态
            if changed_fields:
                # 重置审核状态为未审核（如果之前是打回状态）
                if application.state == 1:
                    application.state = 0
                    application.review = ""  # 清空之前的审核反馈
                
                application.save()
                logger.info(f"申请已更新 | 申请ID: {apply_id} | 更新字段数: {len(changed_fields)}")
                
                # 如果场地编号有变更，需要更新场地占用状态
                if "number" in changed_fields or "site_id" in changed_fields:
                    # 释放原场地
                    old_site = Site.objects(site_id=application.site_id, number=changed_fields.get("number", {}).get("old", application.number)).first()
                    if old_site:
                        old_site.is_occupied = False
                        old_site.save()
                        logger.info(f"原场地已释放 | 场地ID: {application.site_id} | 工位号: {changed_fields.get('number', {}).get('old', application.number)}")
                    
                    # 占用新场地
                    new_site = Site.objects(site_id=application.site_id, number=application.number).first()
                    if new_site:
                        new_site.is_occupied = True
                        new_site.save()
                        logger.info(f"新场地已占用 | 场地ID: {application.site_id} | 工位号: {application.number}")
                    else:
                        logger.error(f"新场地不存在 | 场地ID: {application.site_id} | 工位号: {application.number}")
            
            return (apply_id, changed_fields)
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"更新场地申请失败: {str(e)}")
            raise HTTPException(status_code=500, detail="update site-application failed")

    async def return_borrow_application(self, apply_id: str, userid: str):
        """
        归还已借用的场地
        
        Args:
            apply_id: 申请ID
            userid: 当前用户ID（用于验证权限）
        
        Returns:
            tuple: (apply_id, new_state)
        
        Raises:
            HTTPException: 各种错误情况
        """
        try:
            logger.info(f"处理场地归还 | 申请ID: {apply_id} | 用户: {userid}")
            
            # 查询申请记录
            application = SiteBorrow.objects(apply_id=apply_id).first()
            if not application:
                logger.warning(f"申请不存在 | 申请ID: {apply_id}")
                raise HTTPException(
                    status_code=404,
                    detail="no such application",
                    headers={"X-Error": "Application not found"}
                )
            
            # 检查当前用户是否是申请人
            if application.userid != userid:
                logger.warning(f"用户无权限归还该场地 | 当前用户: {userid} | 申请人: {application.userid}")
                raise HTTPException(
                    status_code=403,
                    detail="forbidden to return others' application"
                )
            
            # 检查申请状态是否为2（通过未归还）
            if application.state != 2:
                logger.warning(f"申请状态不允许归还 | 当前状态: {application.state}")
                raise HTTPException(
                    status_code=400,
                    detail="forbiddened application state",
                    data={
                        "target": 2,
                        "actual": application.state
                    }
                )
            
            # 更新申请状态为3（已归还）
            application.state = 3
            application.save()
            
            # 释放场地占用状态
            site = Site.objects(site_id=application.site_id, number=application.number).first()
            if site:
                site.is_occupied = False
                site.save()
                logger.info(f"场地已释放 | 场地ID: {application.site_id} | 工位号: {application.number}")
            else:
                logger.error(f"场地不存在，无法释放 | 场地ID: {application.site_id} | 工位号: {application.number}")
            
            logger.info(f"场地已成功归还 | 申请ID: {apply_id}")
            return (apply_id, 3)
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"归还场地失败: {str(e)}")
            raise HTTPException(status_code=500, detail="return site failed")