# app/core/config.py
import pydantic
import os
from dotenv import load_dotenv
from typing import Dict, List

load_dotenv()

class Settings(pydantic.ConfigDict):
    # --- 项目基础设置 ---
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "MakersHub")
    
    # --- 日志设置 (新增映射，方便代码调用) ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
    LOG_PATH: str = os.getenv("LOG_PATH", "./logs/app.log")

    # --- 管理员设置 ---
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD")
    ADMIN_SECRET_KEY: str = os.getenv("ADMIN_SECRET_KEY")

    # --- MinIO 对象存储设置 ---
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "minio:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY")
    MINIO_PUBLIC_URL: str = os.getenv("MINIO_PUBLIC_URL")

    # 项目结项材料桶
    MINIO_MATERIAL_BUCKET: str = os.getenv("MINIO_MATERIAL_BUCKET", "makershub-materials")
    
    MINIO_BUCKETS: Dict[str, str] = {
        "AVATARS": os.getenv("MINIO_AVATAR_BUCKET", "makershub-avatars"),
        "POSTERS": os.getenv("MINIO_POSTER_BUCKET", "makershub-posters"),
        "PUBLIC": os.getenv("MINIO_PUBLIC_BUCKET", "makershub-public"),
        "MATERIALS": os.getenv("MINIO_MATERIAL_BUCKET", "makershub-materials"),
    }
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"

    # --- JWT 安全设置 ---
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))

    # --- 权限等级定义 ---
    PERMISSION_LEVELS: Dict[str, int] = {
        "USER": 0, "ADMIN": 1, "SUPER": 2
    }

    # --- 应用运行设置 ---
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    WORKERS: int = int(os.getenv("WORKERS", "4"))

    # --- CORS 设置 ---
    CORS_ORIGINS: List[str] = [
        origin.strip() for origin in os.getenv("CORS_ORIGINS_LIST", "").split(',') if origin
    ]

    # --- 微信小程序设置 ---
    WECHAT_APPID: str = os.getenv("WX_APP_ID")
    WECHAT_SECRET: str = os.getenv("WX_APP_SECRET")
    WECHAT_LOGIN_URL: str = "https://api.weixin.qq.com/sns/jscode2session"

    # --- 业务逻辑设置 ---
    EVENT_PURGE_TIMEOUT: int = 5 # 事件过期时间设置

    class Config:
        case_sensitive = True

settings = Settings()