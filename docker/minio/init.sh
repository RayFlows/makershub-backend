#!/bin/sh
# docker/minio/init.sh

# 等待 MinIO 服务启动
echo "Waiting for MinIO to be ready..."
sleep 5

# 尝试设置别名并重试直到成功
# 注意：这里使用 docker-compose 传入的 MINIO_ROOT_USER 等变量
until mc alias set myminio http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null 2>&1
do
  echo "Waiting for MinIO to be ready..."
  sleep 2
done

echo "MinIO is ready. Creating buckets..."

# 使用环境变量创建桶 (不再写死名字)
# 这些变量来自 docker-compose.yml 的 environment 部分
mc mb myminio/"$MINIO_AVATAR_BUCKET" --ignore-existing
mc mb myminio/"$MINIO_POSTER_BUCKET" --ignore-existing
mc mb myminio/"$MINIO_PUBLIC_BUCKET" --ignore-existing

# 上传初始图片
echo "Uploading default images to $MINIO_AVATAR_BUCKET..."
mc cp /docker-entrypoint-init.d/images/* myminio/"$MINIO_AVATAR_BUCKET"/ || echo "No images to copy or path doesn't exist"

# 设置公共桶的访问策略
echo "Setting public access policies..."
mc anonymous set public myminio/"$MINIO_AVATAR_BUCKET"
mc anonymous set public myminio/"$MINIO_POSTER_BUCKET"
mc anonymous set public myminio/"$MINIO_PUBLIC_BUCKET"

echo "MinIO initialization complete!"