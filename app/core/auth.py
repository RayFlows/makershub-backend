#auth.py
"""
认证模块 (Authentication Module)

该模块实现了基于JWT的认证系统，包括令牌生成、验证和权限控制功能。
主要组件包括JWT工具函数、认证中间件和权限检查装饰器。
"""

from datetime import datetime, timedelta
from typing import Optional
import jwt
from fastapi import Request, HTTPException, Header, Depends
from fastapi.security import HTTPBearer
from app.core.config import settings
from app.models.user import User
from loguru import logger

# 初始化HTTP Bearer安全方案，用于提取请求头中的Bearer令牌
security = HTTPBearer()

def create_access_token(openid: str) -> str:
    """
    创建JWT访问令牌
    
    生成一个包含用户标识和过期时间的JWT令牌。
    
    Args:
        openid: 用户的唯一标识符(微信openid)
        
    Returns:
        str: 编码后的JWT令牌字符串
    """
    # 设置令牌过期时间
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # 构建JWT负载，包含过期时间和用户标识
    to_encode = {"exp": expire, "sub": str(openid)}
    # 使用应用密钥和指定算法对payload进行编码
    return jwt.encode(to_encode, settings.SECRET_KEY, settings.ALGORITHM)

def decode_token(token: str) -> Optional[str]:
    """
    解码JWT令牌
    
    验证并解码JWT令牌，提取用户标识。
    
    Args:
        token: 要解码的JWT令牌字符串
        
    Returns:
        Optional[str]: 成功解码返回用户标识(openid)，失败返回None
    """
    try:
        # 使用应用密钥和指定算法解码令牌
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # 从payload中提取用户标识
        return payload.get("sub")
    except jwt.PyJWTError:
        # JWT解码失败(令牌无效或已过期)
        return None
        

class AuthMiddleware:
    """
    认证中间件
    
    实现FastAPI/Starlette中间件，用于验证请求中的JWT令牌。
    可以自动排除不需要认证的路径。
    """
    
    # 无需认证即可访问的路径集合
    NO_AUTH_PATHS = {
        "/users/wx-login",  # 微信登录接口
        "/docs",            # Swagger文档
        "/redoc",           # ReDoc文档
        "/openapi.json",    # OpenAPI规范
        "/health",          # 健康检查
        "/favicon.ico",     # 网站图标
        "/",                 # 根路径
        "/users/test-user"
    }

    @classmethod
    async def get_current_user(cls, token: str = Header(..., alias="Authorization")) -> User:
        """
        获取当前认证用户
        
        从请求头中的Authorization解析JWT令牌，验证并获取用户信息。
        
        Args:
            token: 请求头中的Authorization值，格式为'Bearer <token>'
            
        Returns:
            User: 当前认证用户的数据模型实例
            
        Raises:
            HTTPException: 认证失败(401)或用户不存在(404)时抛出
        """
        try:
            # 如果是Bearer格式，提取实际令牌部分
            if token.startswith("Bearer "):
                token = token.split(" ")[1]
            # 解码令牌获取用户ID
            userid = decode_token(token)
            # 根据用户ID查询用户信息
            user = User.objects(userid=userid).first()
            if not user:
                # 用户不存在，可能是令牌伪造或用户已被删除
                raise HTTPException(status_code=404, detail="User not found")
            return user
        except Exception as e:
            # 记录认证错误并抛出401异常
            logger.error(f"Auth error: {e}")
            raise HTTPException(status_code=401, detail="Authentication failed")

    async def __call__(self, request: Request, call_next):
        """
        中间件调用方法
        
        处理传入的HTTP请求，验证认证状态，并在通过认证后将用户信息
        附加到请求状态中供后续处理使用。
        
        Args:
            request: 传入的HTTP请求对象
            call_next: 调用链中的下一个处理函数
            
        Returns:
            响应对象
            
        Raises:
            HTTPException: 认证失败时抛出401异常
        """
        # 检查请求路径是否在免认证列表中
        if self.NO_AUTH_PATHS.intersection({request.url.path}):
            # 无需认证，直接传递给下一个处理函数
            return await call_next(request)

        try:
            # 从请求头获取认证令牌
            token = request.headers.get("Authorization")
            # 验证令牌并获取用户信息
            user = await self.get_current_user(token)
            # 将用户信息附加到请求状态中，供路由处理函数使用
            request.state.user = user
            # 继续处理请求
            return await call_next(request)
        except HTTPException:
            # 向上传递HTTP异常，保持原始状态码和详情
            raise
        except Exception as e:
            # 记录其他类型的认证错误
            logger.error(f"认证错误: {str(e)}")
            # 抛出通用认证失败异常
            raise HTTPException(status_code=401, detail="认证失败")

def require_permission_level(required_level: int):
    """
    权限等级要求装饰器
    
    创建一个依赖项，用于检查当前用户是否具有所需的权限等级。
    用于装饰路由处理函数，限制只有特定权限等级的用户才能访问。
    
    Args:
        required_level: 访问所需的最小权限等级
        
    Returns:
        一个依赖函数，用于检查用户权限
    """
    
    async def check_permission_level(
        auth_level: int = Depends(AuthMiddleware.get_current_user)
    ):
        """
        检查用户权限等级
        
        依赖函数，检查当前认证用户的权限等级是否满足要求。
        
        Args:
            auth_level: 通过AuthMiddleware获取的当前用户对象
            
        Returns:
            通过验证的用户对象
            
        Raises:
            HTTPException: 权限不足时抛出403异常
        """
        if auth_level.level < required_level:
            # 用户权限等级不足，拒绝访问
            raise HTTPException(
                status_code=403,
                detail=f"需要权限等级 {required_level}, 当前等级 {auth_level.level}"
            )
        return auth_level
    return check_permission_level

# 便捷的权限检查装饰器，用于常用权限等级
require_admin = require_permission_level(settings.PERMISSION_LEVELS["ADMIN"])  # 管理员权限
require_super = require_permission_level(settings.PERMISSION_LEVELS["SUPER"])  # 超级管理员权限