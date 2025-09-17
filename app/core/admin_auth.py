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