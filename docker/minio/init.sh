#init.sh

# 等待 MinIO 服务启动
# until curl -f http://minio:9000/minio/health/live; do
#   echo "Waiting for MinIO to be ready..."
#   sleep 2
# done
echo "Waiting for MinIO to be ready..."
sleep 5  # 初始等待

# 创建桶
# mc alias set myminio http://minio:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD
# 尝试设置别名并重试直到成功
until mc alias set myminio http://minio:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD >/dev/null 2>&1
do
  echo "Waiting for MinIO to be ready..."
  sleep 2
done

echo "MinIO is ready. Creating buckets..."

# mc mb myminio/$MINIO_BUCKET
mc mb myminio/makerhub-avatars --ignore-existing
mc mb myminio/makerhub-posters --ignore-existing
mc mb myminio/makerhub-public --ignore-existing

# 上传初始图片
# mc cp /docker-entrypoint-init.d/images/* myminio/$MINIO_BUCKET/
mc cp /docker-entrypoint-init.d/images/* myminio/makerhub-avatars/ || echo "No images to copy or path doesn't exist"

# 设置公共桶的访问策略
mc anonymous set public myminio/makerhub-avatars
mc anonymous set public myminio/makerhub-posters
mc anonymous set public myminio/makerhub-public

echo "MinIO initialization complete!"