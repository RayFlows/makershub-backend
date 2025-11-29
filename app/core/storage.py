# app/core/storage.py

import os
from datetime import timedelta
from minio import Minio
from minio.error import S3Error
from loguru import logger
from io import BytesIO
from app.core.config import settings
from urllib.parse import urlparse

class MinioClient:
    """
    MinIO客户端封装类
    
    封装了与MinIO对象存储服务的交互，提供文件URL生成等功能。
    初始化时建立与MinIO服务的连接。
    """
    
    def __init__(self):
        """
        初始化MinIO客户端
        
        使用配置信息连接MinIO服务，如连接失败则抛出异常。
        
        Raises:
            Exception: 连接MinIO失败时抛出的异常
        """
        try:
            logger.info(f"Connecting to MinIO at {settings.MINIO_ENDPOINT}")
            logger.info(f"Secure: {settings.MINIO_SECURE}")
            # 创建MinIO客户端实例

            # 确定要使用的endpoint
            endpoint = settings.MINIO_ENDPOINT

            self.secure = settings.MINIO_SECURE  # Store the secure flag
            self.client = Minio(
                endpoint,                              # MinIO服务地址
                access_key=settings.MINIO_ACCESS_KEY,  # 访问密钥
                secret_key=settings.MINIO_SECRET_KEY,  # 秘密密钥
                secure=settings.MINIO_SECURE,          # 是否使用HTTPS
                http_client=None                       # 使用默认HTTP客户端
            )
            # 2. 外部签名客户端 (仅用于生成预签名URL - 纯离线计算)
            # 我们解析 MINIO_PUBLIC_URL 拿到域名 (例如 dev-s3.makershub.cn)
            # 这样生成的签名才匹配浏览器的 Host Header
            self.public_signer = None
            if settings.MINIO_PUBLIC_URL:
                parsed = urlparse(settings.MINIO_PUBLIC_URL)
                public_endpoint = parsed.netloc  # 获取域名部分，如 dev-s3.makershub.cn
                is_secure = (parsed.scheme == 'https')
                
                logger.info(f"Initializing Public Signer with endpoint: {public_endpoint}")
                self.public_signer = Minio(
                    public_endpoint,
                    access_key=settings.MINIO_ACCESS_KEY,
                    secret_key=settings.MINIO_SECRET_KEY,
                    secure=is_secure
                )

            # 存储桶字典引用
            self.buckets = settings.MINIO_BUCKETS
            logger.info(f"Connecting to Minio successfully")
        except Exception as e:
            logger.error(f"MinIO connection failed: {e}")
            raise e

    def get_file(self, filename: str, expire_seconds=3600, bucket_type="AVATARS") -> dict:
        """
        获取文件URL
        
        策略：
        1. PUBLIC 桶: 继续生成短的、永久的直接访问链接。
        2. 其他所有桶 (MATERIALS, AVATARS, POSTERS): 全部生成带签名的、有效期的安全链接。
        """
        try:    
            bucket = self.buckets.get(bucket_type, self.buckets["AVATARS"])

            # --- 策略 A: 纯公开桶 (PUBLIC) ---
            if bucket_type == "PUBLIC":
                if settings.MINIO_PUBLIC_URL:
                    direct_url = f"{settings.MINIO_PUBLIC_URL.rstrip('/')}/{bucket}/{filename}"
                else:
                    protocol = "https" if settings.MINIO_SECURE else "http"
                    direct_url = f"{protocol}://{settings.MINIO_ENDPOINT}/{bucket}/{filename}"

                logger.info(f"生成公开文件直接URL: {direct_url}")
                return {"url": direct_url}

            # --- 策略 B: 私有桶 (MATERIALS, AVATARS, POSTERS) ---
            else:
                expire_delta = timedelta(seconds=expire_seconds)
                
                # 使用 public_signer 生成签名 (这是我们刚才验证成功的逻辑)
                if self.public_signer:
                    url = self.public_signer.presigned_get_object(
                        bucket,
                        filename,
                        expires=expire_delta
                    )
                    # logger.debug(f"生成私有签名URL: {url}") # 调试时可以打开，生产环境日志可能太多
                    return {"url": url}
                else:
                    # 回退逻辑
                    url = self.internal_client.presigned_get_object(
                        bucket,
                        filename,
                        expires=expire_delta
                    )
                    return {"url": url}
               
        except S3Error as e:
            logger.error(f"获取文件URL失败: {str(e)}")
            return {"error": f"获取文件URL失败: {str(e)}"}

    def upload_file(self, file_data, file_path, content_type="image/jpeg", bucket_type="AVATARS"):
        """
        上传文件到MinIO
        
        Args:
            file_data: 文件二进制数据
            file_path: 文件存储路径
            content_type: 文件内容类型
            bucket_type: 存储桶类型，默认为AVATARS
            
        Returns:
            bool: 上传成功返回True，失败返回False
        """
        try:
            # 获取对应的存储桶名称
            bucket = self.buckets.get(bucket_type, self.buckets["AVATARS"])
            logger.info(f"上传文件 | 文件路径: {file_path} | 桶类型: {bucket_type} | 实际桶名: {bucket}")

            # 修复：正确处理bytes和BytesIO类型
            if isinstance(file_data, bytes):
                length = len(file_data)
                data_stream = BytesIO(file_data)
            else:
                # BytesIO对象
                file_data.seek(0, 2)  # 移动到文件末尾
                length = file_data.tell()
                file_data.seek(0)  # 重置指针
                data_stream = file_data

            # 上传文件
            self.client.put_object(
                bucket,
                file_path,
                # file_data,
                data_stream,
                # length=len(file_data),
                length=length,
                content_type=content_type
            )

            return True
        except Exception as e:
            logger.error(f"上传文件失败: {str(e)}")
            return False

# 初始化全局MinIO客户端实例
minio_client = MinioClient()