# app/services/file_service.py
from loguru import logger
from app.core.db import minio_client
from app.core.config import settings
import uuid
from io import BytesIO
from datetime import datetime

class FileService:
    """文件存储服务，处理不同类型文件的上传和获取"""
    
    BUCKET_MAPPING = {
        "profile": "makerhub-avatars",
        "poster": "makerhub-posters",
        "material": "makerhub-public"
    }
        
    async def upload_file(self, file_type: str, file_data: bytes, 
                          owner_id: str, filename: str = None) -> dict:
        """
        上传文件到MinIO
        
        Args:
            file_type: 文件类型 (profile, poster, material)
            file_data: 文件二进制数据
            owner_id: 拥有者ID (用户ID,活动ID等)
            filename: 原始文件名 (可选)
            
        Returns:
            dict: 包含上传结果的字典
        """
        try:
            bucket = self.BUCKET_MAPPING.get(file_type)
            if not bucket:
                return {"success": False, "error": "Invalid file type"}
                
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            name = filename or f"{uuid.uuid4()}"
            file_path = f"{owner_id}/{timestamp}_{name}"
            
            # 上传到MinIO
            minio_client.client.put_object(
                bucket,
                file_path,
                BytesIO(file_data),
                length=len(file_data),
                content_type=self._get_content_type(filename)
            )
            
            # 生成预签名URL
            url = minio_client.get_file(f"{bucket}/{file_path}", 3600)
            
            return {
                "success": True,
                "bucket": bucket,
                "path": file_path,
                "url": url.get("url") if url else None
            }
        except Exception as e:
            logger.error(f"File upload failed: {e}")
            return {"success": False, "error": str(e)}
            
    def _get_content_type(self, filename: str) -> str:
        """根据文件名确定内容类型"""
        if not filename:
            return "application/octet-stream"
            
        ext = filename.lower().split(".")[-1]
        content_types = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "pdf": "application/pdf"
        }
        return content_types.get(ext, "application/octet-stream")
