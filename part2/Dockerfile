FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建flag文件
RUN echo "wmctf{P1ckl3_D3s3r14l1z4t10n_1s_D4ng3r0us_4nd_RCE}" > /flag
RUN chmod 644 /flag

# 创建非root用户
RUN useradd -m ctfuser
RUN chown -R ctfuser:ctfuser /app

# 切换到非root用户
USER ctfuser

# 暴露端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# 启动应用
CMD ["python", "app.py"] 