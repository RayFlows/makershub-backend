#db.py
"""
数据库连接模块 (Database Connection Module)

该模块提供了与MongoDB数据库和MinIO对象存储的连接管理功能。
包含连接/断开MongoDB的函数，以及用于MinIO操作的客户端封装类。
"""

import mongoengine
import os
import json
from minio import Minio
from minio.error import S3Error
from fastapi import HTTPException
from app.core.config import settings
from loguru import logger
from typing import Union
from datetime import timedelta

def connect_to_mongodb():
    """
    连接到MongoDB数据库
    
    使用环境变量中的MongoDB URI建立数据库连接。
    成功连接后记录日志，失败则记录错误并抛出异常。
    
    Raises:
        Exception: 连接失败时抛出的异常
    """
    try:
        logger.info("正在连接到MongoDB...")
        # 从环境变量获取MongoDB连接URI
        logger.info(os.getenv("MONGODB_URI"))
        mongoengine.connect(host=os.getenv("MONGODB_URI"))
        logger.info("MongoDB连接成功")
    except Exception as e:
        logger.error(f"连接MongoDB失败: {e}")
        raise e

def disconnect_from_mongodb():
    """
    断开MongoDB数据库连接
    
    关闭当前与MongoDB的连接，释放资源。
    操作结果记录到日志中。
    
    Raises:
        Exception: 关闭连接失败时可能产生异常(但不会抛出)
    """
    try:
        logger.info("正在关闭MongoDB连接...")
        mongoengine.disconnect()
        logger.info("MongoDB连接已关闭")
    except Exception as e:
        logger.error(f"关闭MongoDB连接失败: {e}")

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
            # 存储桶字典引用
            self.buckets = settings.MINIO_BUCKETS
            logger.info(f"Connecting to Minio successfully")
        except Exception as e:
            logger.error(f"MinIO connection failed: {e}")
            raise e

    def get_file(self, filename: str, expire_seconds=3600, bucket_type="AVATARS") -> dict:
        """
        获取文件的预签名URL
        
        为指定的文件生成一个临时的预签名URL，允许在不具有MinIO凭据的情况下访问文件。
        
        Args:
            filename: 要获取的文件名
            expire: URL的过期时间(秒)，默认为1小时(3600秒)
            bucket_type: 存储桶类型，默认为AVATARS，可选值：AVATARS, POSTERS, PUBLIC
            
        Returns:
            dict: 包含预签名URL的字典，格式为{"url": "预签名URL"}

        注意：暂时注释掉了生成预签名URL的部分，改为直接生成可访问的URL。
        该方法将根据配置生成一个可直接访问的URL，而不是预签名的URL。
        这意味着生成的URL不需要额外的签名验证，可以直接访问。
            
        Raises:
            S3Error: MinIO操作失败时可能抛出错误
        """
        try:    
            # 获取对应的存储桶名称
            bucket = self.buckets.get(bucket_type, self.buckets["AVATARS"])

            # try:
            #     expire_seconds = int(expire_seconds)
            # except (TypeError, ValueError):
            #     expire_seconds = 3600

            # # from datetime import timedelta
            # expire_delta = timedelta(seconds=expire_seconds)

            # logger.debug(f"过期时间计算完成: {expire_seconds}秒")


            # # 生成原始URL
            # url = self.client.presigned_get_object(
            #     bucket,
            #     filename,
            #     expires=expire_delta
            # )

            # 替换内网地址为公网地址（关键修改）
            # if settings.MINIO_PUBLIC_URL:
            #     endpoint = settings.MINIO_ENDPOINT
            #     current_url = f"https://{endpoint}" if self.secure else f"http://{endpoint}"
            #     public_url = url.replace(current_url, settings.MINIO_PUBLIC_URL.rstrip('/'))
            #     logger.info(f"生成公网URL: {public_url}")
            #     return {"url": public_url}
            # else:
            #     logger.info(f"生成的预签名URL: {url}")
            #     return {"url": url}

            # 生成直接访问URL（无签名）
            if settings.MINIO_PUBLIC_URL:
                # 使用公网地址
                direct_url = f"{settings.MINIO_PUBLIC_URL.rstrip('/')}/{bucket}/{filename}"
            else:
                # 使用内网地址构建直接URL
                protocol = "https" if self.secure else "http"
                direct_url = f"{protocol}://{settings.MINIO_ENDPOINT}/{bucket}/{filename}"

            logger.info(f"生成直接访问URL: {direct_url}")
            return {"url": direct_url}
               
        except S3Error as e:
            # 记录错误并返回错误信息
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
            
            # 上传文件
            self.client.put_object(
                bucket,
                file_path,
                file_data,
                length=len(file_data),
                content_type=content_type
            )
            return True
        except Exception as e:
            logger.error(f"上传文件失败: {str(e)}")
            return False

# 初始化全局MinIO客户端实例
minio_client = MinioClient()

