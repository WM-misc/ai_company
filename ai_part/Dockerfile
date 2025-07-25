# 使用官方Python镜像
FROM ubuntu:noble

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    gcc \
    g++ \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements.txt
COPY requirements.txt .
COPY flag /flag

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt --break-system-packages

# 复制应用代码
COPY . .
RUN sh /app/init.sh &&\ 
     rm -rf /app/flag && \
     rm -rf /app/init.sh

# 暴露端口
EXPOSE 3001

# 启动应用
CMD ["python3", "app.py"] 