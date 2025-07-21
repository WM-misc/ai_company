# 使用官方Node.js镜像
FROM node:18-alpine

# 设置工作目录
WORKDIR /app

# 复制package.json和package-lock.json
COPY package*.json ./

# 安装依赖
RUN npm install

# 复制应用代码
COPY . .

# 创建uploads目录
RUN mkdir -p uploads

# 暴露端口
EXPOSE 3000

# 启动应用
CMD ["npm", "start"]
