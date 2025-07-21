# AI智能客服服务

## 📖 项目简介

这是一个基于Flask和LangChain的AI智能客服服务，能够接收来自main server的webhook消息，使用大模型进行智能回复，并将回复发送回客服系统。

## 🚀 快速开始

### 方式一：使用启动脚本（推荐）
```bash
cd ai_part
python start_ai_service.py
```

### 方式二：手动启动
```bash
cd ai_part

# 安装依赖
pip install -r requirements.txt

# 启动服务
python app.py
```

## 🔧 配置说明

### API配置
编辑 `config/config.py` 文件：
```python
OPENAI_API_KEY = "your-api-key"
OPENAI_API_BASE = "https://api.deepseek.com"
OPENAI_API_MODEL = "deepseek-chat"
```

### 服务配置
在 `app.py` 中可以修改以下配置：
- `SERVER_BASE_URL`: 主服务器地址（默认: http://localhost:3000）
- `AI_WEBHOOK_TOKEN`: webhook验证token（默认: default-token）
- `SYSTEM_PROMPT`: AI客服的系统提示词

## 📡 API端点

### Webhook接收端点
```http
POST /ai-webhook
Content-Type: application/json
Authorization: Bearer default-token

{
    "message": "用户消息内容",
    "userId": "用户ID",
    "timestamp": "2024-01-01T12:00:00.000Z",
    "type": "text|image|file",
    "fileUrl": "文件URL（可选）"
}
```

### 状态检查
```http
GET /status
```

### AI测试
```http
GET /test
```

## 🔄 工作流程

1. **接收消息**: 用户在前端发送消息
2. **Webhook触发**: server.js发送webhook到AI服务
3. **AI处理**: 使用大模型生成智能回复
4. **发送回复**: 将AI回复发送回server.js
5. **实时推送**: 通过Socket.IO推送给用户

## 🧪 测试步骤

### 1. 启动完整系统
```bash
# 终端1: 启动主服务器
npm start

# 终端2: 启动AI服务
cd ai_part
python app.py
```

### 2. 测试AI服务
```bash
# 检查服务状态
curl http://localhost:3001/status

# 测试AI模型
curl http://localhost:3001/test
```

### 3. 端到端测试
1. 访问用户端：http://localhost:3000/customer
2. 发送消息："你好，我想了解iPhone 15 Pro"
3. 观察AI服务控制台输出
4. 查看用户端收到的智能回复

## 🤖 AI客服功能

### 专业领域
- 商品咨询（iPhone、MacBook、AirPods、iPad等）
- 订单查询和处理
- 售后服务支持
- 技术问题解答
- 购买建议和推荐

### 商品信息
- **iPhone 15 Pro**: ¥7999，搭载A17 Pro芯片
- **MacBook Air M2**: ¥8999，轻薄便携笔记本
- **AirPods Pro**: ¥1999，主动降噪无线耳机
- **iPad Air**: ¥4399，轻薄强大平板电脑

### 回复特点
- 简洁明了，控制在150字以内
- 专业友好的服务态度
- 针对文件/图片主动询问需求
- 适当使用表情符号增加亲和力

## 🔍 调试信息

### 控制台日志
```
收到用户消息webhook:
时间: 2024-01-01T12:00:00.000Z
用户ID: user_abc123
消息内容: 你好，我想了解iPhone 15 Pro
消息类型: text
文件URL: None
AI回复: 您好！😊 iPhone 15 Pro是我们的最新旗舰机型...
成功发送回复到用户 user_abc123
```

### 错误处理
- API调用失败时返回友好的错误提示
- 网络超时自动重试
- 详细的错误日志记录

## 🛠️ 技术栈

- **Web框架**: Flask
- **AI框架**: LangChain
- **HTTP客户端**: requests
- **大模型**: DeepSeek/OpenAI兼容API
- **部署**: Python 3.8+

## 📋 依赖要求

```
Flask==2.3.3
requests==2.31.0
langchain==0.1.0
langchain-openai==0.0.5
python-dotenv==1.0.0
```

## 🚨 注意事项

1. **API密钥**: 确保配置文件中的API密钥有效
2. **网络连接**: 确保能访问大模型API服务
3. **端口占用**: 默认使用3001端口，确保无冲突
4. **服务依赖**: 需要主服务器在3000端口运行

## 📞 故障排除

### 常见问题

1. **AI服务启动失败**
   - 检查Python版本（需要3.8+）
   - 检查依赖是否安装完整
   - 检查配置文件是否正确

2. **Webhook接收失败**
   - 检查端口3001是否被占用
   - 确认主服务器webhook配置正确
   - 验证Authorization token

3. **AI回复失败**
   - 检查API密钥和服务地址
   - 查看控制台错误日志
   - 测试网络连接

4. **回复发送失败**
   - 确认主服务器运行正常
   - 检查/api/service/reply端点可用性
   - 查看网络连接状态

## 📈 性能优化

- 使用连接池优化HTTP请求
- 实现缓存机制减少API调用
- 异步处理提高响应速度
- 添加请求队列防止过载

## 🔒 安全考虑

- Webhook请求需要Bearer token验证
- 输入参数验证和清理
- 错误信息脱敏处理
- API密钥安全存储 