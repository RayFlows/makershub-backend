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
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from app.core.database import AsyncSessionLocal, get_db

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
        "/users/test-user", # 测试用户接口（测试用）
        "/site/add",       # 添加场地接口（测试用）
        "/arrange/arrangements/batch"  # 批量创建排班安排（测试用）
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
                logger.debug("Token starts with 'Bearer', extracting actual token part.")
                token = token.split(" ")[1]

            userid = decode_token(token)    
            if not userid:
                 raise HTTPException(status_code=401, detail="Invalid token")
            
            # 我们不能在类方法中使用Depends，所以需要手动创建会话。
            async with AsyncSessionLocal() as session:
                stmt = select(User).where(User.userid == userid)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

            if not user:
                # 用户不存在，可能是令牌伪造或用户已被删除
                logger.warning(f"User not found for userid: {userid}")
                raise HTTPException(status_code=404, detail="User not found")
            return user
        except HTTPException as e:
            # 直接重新抛出已知的HTTP异常
            raise e
        except Exception as e:
            logger.error(f"Auth error during get_current_user: {e}", exc_info=True)
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
            if not token:
                raise HTTPException(status_code=401, detail="Authorization header missing")
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
        user: User = Depends(AuthMiddleware.get_current_user)  # 重命名参数为 user
    ):
        # 确保用户对象有效
        if not user or not hasattr(user, 'role'):
            logger.error("❌ 无效的用户对象")
            raise HTTPException(status_code=401, detail="用户信息异常")
        
        # 检查权限等级
        if user.role < required_level:  # 使用正确的变量名 user
            logger.warning(
                f"⛔ 权限不足 | 用户: {user.userid} | "
                f"当前权限: {user.role} | 要求权限: {required_level}"
            )
            raise HTTPException(
                status_code=403,
                detail=f"需要权限等级 {required_level}, 当前等级 {user.role}"
            )
            
        logger.info(f"✅ 权限验证通过 | 用户: {user.userid}")
        return user  # 返回验证通过的用户对象
        
    return check_permission_level

# 便捷的权限检查装饰器，用于常用权限等级
require_admin = require_permission_level(settings.PERMISSION_LEVELS["ADMIN"])  # 协会成员权限
require_super = require_permission_level(settings.PERMISSION_LEVELS["SUPER"])  # 协会管理员权限