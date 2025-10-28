# app/core/admin_auth.py
"""
管理员认证模块
独立于微信小程序认证系统的管理员认证
"""

from datetime import datetime, timedelta
from typing import Optional
import jwt
import os
from loguru import logger
from fastapi import HTTPException, Header, Depends

# 管理员JWT配置（独立于小程序的JWT）
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "Admin_MakerHub_2024_Secret_Key")
ADMIN_ALGORITHM = "HS256"
ADMIN_TOKEN_EXPIRE_HOURS = 24  # 管理员token有效期24小时

def create_admin_token(username: str) -> str:
    """
    创建管理员JWT令牌
    
    Args:
        username: 管理员用户名
        
    Returns:
        str: 编码后的JWT令牌
    """
    expire = datetime.utcnow() + timedelta(hours=ADMIN_TOKEN_EXPIRE_HOURS)
    payload = {
        "exp": expire,
        "sub": username,
        "type": "admin",  # 标识为管理员token
        "iat": datetime.utcnow()
    }
    token = jwt.encode(payload, ADMIN_SECRET_KEY, algorithm=ADMIN_ALGORITHM)
    logger.info(f"创建管理员token成功: {username}")
    return token

def verify_admin_token(token: str) -> Optional[str]:
    """
    验证管理员JWT令牌
    
    Args:
        token: JWT令牌字符串
        
    Returns:
        Optional[str]: 成功返回用户名，失败返回None
    """
    try:
        payload = jwt.decode(token, ADMIN_SECRET_KEY, algorithms=[ADMIN_ALGORITHM])
        
        # 验证token类型
        if payload.get("type") != "admin":
            logger.warning("Token类型不匹配：非管理员token")
            return None
            
        username = payload.get("sub")
        logger.debug(f"管理员token验证成功: {username}")
        return username
        
    except jwt.ExpiredSignatureError:
        logger.warning("管理员token已过期")
        return None
    except jwt.PyJWTError as e:
        logger.warning(f"管理员token验证失败: {str(e)}")
        return None

async def get_admin_auth(authorization: Optional[str] = Header(None)) -> str:
    """
    一个FastAPI依赖项，用于保护管理员路由。
    
    它从请求头中提取Bearer Token，使用`verify_admin_token`进行验证，
    如果验证成功，则返回管理员用户名。如果失败，则抛出HTTPException。
    """
    if not authorization:
        logger.warning("[AdminAuth] 未提供认证Token")
        raise HTTPException(status_code=401, detail="未提供认证token")
    
    try:
        # 兼容 "Bearer <token>" 格式
        if " " in authorization:
            scheme, token = authorization.split()
            if scheme.lower() != 'bearer':
                raise HTTPException(status_code=401, detail="认证格式错误，应为'Bearer token'")
        else:
            token = authorization
    except ValueError:
        raise HTTPException(status_code=401, detail="认证格式错误，应为'Bearer token'")

    username = verify_admin_token(token)
    if not username:
        logger.warning("[AdminAuth] 无效的管理员Token")
        raise HTTPException(status_code=403, detail="无效的认证token或权限不足")
    
    logger.debug(f"[AdminAuth] 管理员认证成功: {username}")
    return username