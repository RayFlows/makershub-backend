# Dockerfile

# 使用腾讯云加速的Python官方镜像
FROM mirror.ccs.tencentyun.com/library/python:3.9-slim-bookworm

# 工作目录设置
WORKDIR /app

# 步骤1：APT网络优化配置 (参考: https://wiki.debian.org/AptConfiguration)
RUN echo 'Acquire::Queue-Mode "host";' > /etc/apt/apt.conf.d/99docker && \
    echo 'Acquire::http::Timeout "5";' >> /etc/apt/apt.conf.d/99docker && \
    echo 'Acquire::http::Dl-Limit "500";' >> /etc/apt/apt.conf.d/99docker && \
    echo 'Acquire::Retries "1";' >> /etc/apt/apt.conf.d/99docker

# 步骤2：设置腾讯云镜像源 (参考: https://mirrors.cloud.tencent.com/help/debian.html)
RUN echo "deb http://mirrors.cloud.tencent.com/debian/ bookworm main non-free contrib" > /etc/apt/sources.list && \
    echo "deb http://mirrors.cloud.tencent.com/debian-security/ bookworm-security main non-free contrib" >> /etc/apt/sources.list

# 步骤3：安装系统依赖 (单层合并，缩减镜像大小)
RUN apt-get update -o APT::Get::Assume-Yes=true && \
    apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    libssl-dev \
    curl && \
    apt-mark auto build-essential > /dev/null && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 步骤4：设置腾讯云PyPI镜像 (参考: https://mirrors.cloud.tencent.com/help/pypi.html)
RUN pip config set global.index-url https://mirrors.cloud.tencent.com/pypi/simple && \
    pip config set global.timeout 30

# 复制依赖文件（单独层，利用构建缓存）
COPY requirements.txt .

# 安装Python依赖（带缓存清理）
RUN pip install --no-cache-dir -r requirements.txt && \
    rm -f requirements.txt

# 复制应用代码
COPY app/ ./app/

# 创建日志目录
RUN mkdir -p /app/logs && chmod 777 /app/logs

# 环境变量配置
ENV PYTHONPATH=/app \
    PORT=8000 \
    PIP_NO_CACHE_DIR=true

# 暴露端口
EXPOSE ${PORT}

# 启动命令（非root用户模式）
# RUN groupadd -r appuser && useradd -r -g appuser appuser && \
#     chown -R appuser:appuser /app
# USER appuser

# Google SRE推荐的启动策略: https://sre.google/sre-book/terminology/
CMD ["uvicorn", "app.main:app", "--host=0.0.0.0", "--port=8000", "--reload"]
