# WMCTF2025 MISC Shopping Company 部署指南
本环境为 WMCTF2025 MISC Shopping Company 题目环境，包含 AI 聊天机器人和视觉模型服务。以下是详细的部署步骤：
## 1. 环境准备
* 申请 deepseek api key：https://platform.deepseek.com/api_keys
* 申请 字节方舟 视觉模型 api key：https://console.volcengine.com/ark/region:ark+cn-beijing/endpoint，模型选用doubao-seed 1.6即可。

## 2. 克隆代码仓库
```bash
git clone https://github.com/WM-misc/ai_company.git
cd ai_company
```
## 3.修改ai_part/config/config.py
修改对应位置为deepseek和字节方舟的api key

## 4. 启动
在根目录下 docker compose up -d 即可启动服务
```bash
docker compose up -d
```

## 5. 访问
浏览器访问 http://localhost:3000 即可。


