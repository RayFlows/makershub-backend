#user_router.py
# 用户路由模块 (User Router Module) 
# 本模块负责处理所有与用户相关的API路由，包括微信登录和用户信息管理
# 通过FastAPI框架实现RESTful API接口，集成了微信小程序登录验证流程

from fastapi import APIRouter, HTTPException, File, UploadFile, Depends
from loguru import logger  # 引入高级日志记录器，用于详细记录API调用情况
from app.services.user_service import UserService  # 引入用户服务层处理业务逻辑
from app.core.config import settings  # 导入应用配置，包含微信相关密钥
from app.core.auth import AuthMiddleware  # 导入认证中间件获取当前用户
from app.models.user import User  # 导入用户模型
import aiohttp  # 异步HTTP客户端库，用于非阻塞网络请求
from aiohttp import TCPConnector, ClientTimeout  # TCP连接器和超时控制组件
import asyncio  # Python异步编程支持库
import async_timeout  # 异步超时控制工具，防止请求无限等待
from fastapi.responses import JSONResponse  # JSON响应格式化工具
from typing import Optional, Dict, Any  # 类型提示工具
from pydantic import BaseModel  # 数据验证和序列化基础模型
import json  # JSON数据处理工具
import requests  # 同步HTTP请求库（备用）
from datetime import timedelta  
from app.core.db import minio_client


router = APIRouter()  # 创建API路由器实例
user_service = UserService()  # 初始化用户服务实例

# 添加一个测试路由来打印完整用户对象
@router.get("/test-user")
async def test_user(openid: str):
    try:
        user = User.objects(userid=openid).first()
        if not user:
            return {"error": "User not found", "openid": openid}
        
        # 转换为字典以便查看所有字段
        user_dict = user.to_dict()
        # 额外添加MongoDB文档信息
        mongo_data = user.to_mongo().to_dict()
        
        logger.info(f"User object: {mongo_data}")
        return {
            "user_dict": user_dict,
            "mongo_data": mongo_data
        }
    except Exception as e:
        logger.error(f"测试用户信息失败: {str(e)}")
        return {"error": str(e)}


class WxLoginRequest(BaseModel):
    """微信登录请求模型，验证并处理前端传入的登录码"""
    code: str  # 微信登录临时凭证code，用于换取用户openid

@router.post("/wx-login")
async def wx_login(request: WxLoginRequest):
    """
    微信小程序登录接口 
    
    接收前端传来的临时登录码(code)，向微信服务器验证并获取用户openid
    成功后创建或更新用户信息并返回登录结果
    """
    try:
        # 构建微信登录API请求URL，包含小程序appid、secret和用户临时code
        url = f"{settings.WECHAT_LOGIN_URL}?appid={settings.WECHAT_APPID}&secret={settings.WECHAT_SECRET}&js_code={request.code}&grant_type=authorization_code"
        
        logger.info(f"Calling WeChat API: {url}")  # 记录微信API调用信息（注意不要在生产环境记录完整URL避免泄露secret）

        # 创建专用TCP连接池配置，优化网络性能
        bypass_connector = TCPConnector(
            limit_per_host=10,  # 限制每个主机的最大连接数，防止连接资源耗尽
            ssl=False,          # 禁用SSL验证以提高性能（注意：生产环境建议启用SSL）
            force_close=True    # 强制关闭连接，防止连接池资源泄漏
        )
        

        # 使用async_timeout进行请求超时控制，增强系统稳定性
        async with async_timeout.timeout(10):  # 设置10秒超时阈值，防止长时间阻塞
            logger.info("Sending request to WeChat API")  # 记录发送请求日志
            async with aiohttp.ClientSession(
                connector=bypass_connector,  # 使用自定义连接池
                timeout=aiohttp.ClientTimeout(total=8)  # 客户端超时设置为8秒
            ) as session:
                async with session.get(url) as response:  # 发起GET请求
                    logger.info(f"WeChat API response status: {response.status}")  # 记录响应状态码
                    data = await response.text()  # 异步读取响应文本
                    wx_response = json.loads(data)  # 解析JSON响应
                    logger.info(f"WeChat API response: {wx_response}")  # 记录响应内容


        logger.info(wx_response)  # 记录完整响应数据
        # 检查微信API返回是否包含错误码
        if 'errcode' in wx_response and wx_response['errcode'] != 0:
            error_msg = wx_response.get('errmsg')  # 获取错误信息
            logger.error(f"微信的傻逼接口返回错误：{error_msg}")  # 记录详细错误（注意生产环境应使用更专业的措辞）
            raise HTTPException(
                status_code=500,  # 设置HTTP 500服务器内部错误
                detail=f"微信登录失败:{error_msg}"  # 返回给客户端的错误详情
            )

        # 从响应中提取用户openid
        openid = wx_response.get("openid")

        # 验证openid是否存在
        if not openid:
            logger.error("微信登录失败: openid不存在")  # 记录错误日志
            raise HTTPException(status_code=500, detail="微信登录失败: openid不存在")  # 抛出HTTP异常

        logger.info(openid)  # 记录获取到的openid（生产环境应考虑隐藏部分信息）

        # 调用用户服务创建或更新用户信息
        return await user_service.create_or_update_wx_user(openid)


    # 异步超时异常处理
    except async_timeout.TimeoutError:
        logger.error("WeChat API timeout after 10 seconds")  # 记录超时错误
        raise HTTPException(status_code=504, detail="微信服务响应超时")  # 返回504网关超时错误

    # 网络客户端异常处理
    except aiohttp.ClientError as e:
        logger.error(f"WeChat API client error: {e}")  # 记录客户端错误详情
        raise HTTPException(status_code=502, detail="微信服务异常")  # 返回502错误表示上游服务异常

    # 通用异常处理
    except Exception as e:
        logger.error(f"微信登录失败: {str(e)}")  # 记录未预期的异常
        raise HTTPException(status_code=500, detail="登录失败")  # 返回通用服务器错误

@router.get("/profile")
async def get_user_profile(current_user: User = Depends(AuthMiddleware.get_current_user)):
    """
    获取当前用户个人资料
    
    通过JWT令牌识别用户，返回完整的用户信息
    所有角色(0,1,2)均可访问
    
    Returns:
        dict: 包含用户详细信息的响应
    """
    try:
        # 用户信息已通过AuthMiddleware.get_current_user获取
        # 转换为字典格式
        user_data = current_user.to_dict()
        # 处理头像URL
        try:
            from app.core.db import minio_client
            from datetime import timedelta
   
            profile_photo = user_data.get("profile_photo") or "default-profile-photo.jpg"
            
            # 生成预签名URL
            photo_url = minio_client.get_file(
                user_data["profile_photo"], 
                expire_seconds=3600,
                bucket_type="AVATARS"
            )
            
            if photo_url and "url" in photo_url:
                user_data["profile_photo"] = photo_url["url"]
            else:
                # 如果获取URL失败，记录错误
                logger.error(f"获取头像URL失败: {photo_url.get('error', 'Unknown error')}")
                user_data["profile_photo"] = ""

        except Exception as e:
            logger.error(f"头像处理失败: {e}")
            user_data["profile_photo"] = ""

        return {
            "code": 200,
            "message": "successfully get user profile",
            "data": {
                "real_name": user_data.get("real_name", ""),
                "role": user_data.get("role", 0),
                "phone_num": user_data.get("phone_num", ""),
                "state": user_data.get("state", 1),
                "profile_photo": user_data.get("profile_photo", ""),
                "motto": user_data.get("motto", ""),
                "score": user_data.get("score", 0)
            }
        }
    except HTTPException:
        # 重新抛出HTTP异常，保持原始状态码
        raise
    except Exception as e:
        logger.error(f"获取用户资料失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户资料失败")


class UserProfileUpdate(BaseModel):
    """用户资料更新请求模型，所有字段都是可选的"""
    real_name: Optional[str] = None
    phone_num: Optional[str] = None
    motto: Optional[str] = None

# 在 user_router.py 中
class UserProfileUpdateRequest(BaseModel):
    """修改后的用户资料更新请求模型"""
    data: Optional[UserProfileUpdate] = UserProfileUpdate()

@router.patch("/profile")
async def update_user_profile(
    # profile_update: UserProfileUpdate,
    request: UserProfileUpdateRequest,  # 使用新请求模型
    current_user: User = Depends(AuthMiddleware.get_current_user)
):
    """
    更新当前用户个人资料
    
    通过JWT令牌识别用户，部分更新用户资料
    所有角色(0,1,2)均可访问
    
    Args:
        profile_update: 包含要更新字段的请求体
        current_user: 当前登录用户(通过认证中间件获取)
        
    Returns:
        dict: 包含更新后字段的响应
    """
    try:
        # 将请求模型转换为字典，过滤掉None值
        # update_data = {k: v for k, v in profile_update.dict().items() if v is not None}
        update_data = request.data.dict(exclude_unset=True)
        
        if not update_data:
            # 没有提供有效更新字段
            return {
                "code": 400,
                "message": "没有提供有效的更新字段"
            }

        # 调试日志：打印更新内容
        logger.info(f"用户ID={current_user.userid} 更新资料: {update_data}")
        
        # 更新用户信息
        # for field, value in update_data.items():
        #     setattr(current_user, field, value)
        for field, value in update_data.items():
            # 确保字段存在于用户模型中
            if hasattr(current_user, field):
                setattr(current_user, field, value)
            else:
                logger.warning(f"尝试更新不存在的字段: {field}")
         
        # 调试日志：打印更新前的数据
        logger.info(f"更新前用户信息: {current_user.to_dict()}")
            
        # 保存更新
        try:
            current_user.save()
            # 刷新对象以获取最新状态
            current_user.reload()
            logger.info("用户资料更新成功")
        except Exception as e:
            logger.error(f"保存用户更新失败: {e}")
            return {
                "code": 500,
                "message": "资料保存失败"
            }
        
        # 调试：验证更新是否生效
        logger.info(f"更新后用户信息: {current_user.to_dict()}")

        # 返回成功响应
        # return {
        #     "code": 200,
        #     "message": "successfully update user profile",
        #     "data": update_data
        # }
        return {
            "code": 200,
            "message": "用户资料更新成功",
            "data": {
                "updated_fields": list(update_data.keys())
            }
        }

    except Exception as e:
        logger.error(f"更新用户资料失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"message": "服务器内部错误"}
        )


@router.post("/profile-photo")
async def upload_profile_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(AuthMiddleware.get_current_user)
):
    """
    上传用户头像
    
    接收图片文件并存储到MinIO，更新用户资料中的头像URL
    所有角色(0,1,2)均可访问，但用户状态必须为正常(1)
    
    Returns:
        dict: 包含上传结果和头像URL的响应
    """
    try:
         # 打印请求信息
        logger.info(f"收到头像上传请求 - 用户ID: {current_user.userid}")
        logger.info(f"文件信息 - 文件名: {file.filename}, 内容类型: {file.content_type}")
        
        # 读取并打印文件大小
        contents = await file.read()
        file_size = len(contents)
        logger.info(f"文件大小: {file_size} 字节")


        # # 检查用户状态
        # if current_user.state != 1:
        #     return {
        #         "code": 403,
        #         "message": "forbidden user"
        #     }
            
        # # 读取文件内容
        # contents = await file.read()
        
        # 调用用户服务上传头像
        result = await user_service.update_user_profile_photo(current_user.userid, contents)

        url = result.get("url")

        logger.info(f"返回链接：{url}")
        
        if not result.get("success"):
            return {
                "code": 400,
                "message": "upload failed"
            }

            
        return {
            "code": 200,
            "message": "successfully post profile photo",
            "data": {
                "profile_photo": result.get("url","")
            }
        }
        
    except Exception as e:
        logger.error(f"上传头像失败: {str(e)}")
        return {
            "code": 400,
            "message": "upload failed"
        }



    