# Webhook功能测试说明

## 🔄 修改说明

**修改前**：客服端发送消息时触发webhook  
**修改后**：用户端发送消息时触发webhook

## 🧪 测试步骤

### 1. 启动测试环境
```bash
# 终端1：启动主服务器
npm start

# 终端2：启动webhook测试服务器
node test-webhook.js
```

### 2. 测试用户消息触发webhook
1. 打开浏览器访问：http://localhost:3000/customer
2. 在用户端发送任意消息
3. 观察webhook测试服务器控制台输出
4. 应该看到类似以下日志：
   ```
   收到用户消息webhook:
   时间: 2024-01-01 12:00:00
   消息内容: 你好，我需要帮助
   用户ID: user_abc123
   消息类型: text
   文件URL: null
   ```

### 3. 测试客服回复不触发webhook
1. 打开另一个浏览器窗口访问：http://localhost:3000/service
2. 在客服端选择用户对话并回复
3. 观察webhook测试服务器控制台
4. **不应该**看到新的webhook日志

### 4. 测试文件上传触发webhook
1. 在用户端上传图片或文件
2. 观察webhook测试服务器控制台
3. 应该看到包含文件URL的webhook数据

## ✅ 验证要点

### 用户消息应该触发webhook
- [ ] 文字消息触发webhook
- [ ] 图片上传触发webhook
- [ ] 文件上传触发webhook
- [ ] Webhook数据格式正确

### 客服回复不应该触发webhook
- [ ] 客服文字回复不触发webhook
- [ ] 客服文件发送不触发webhook
- [ ] 客服端操作完全静默

## 📊 Webhook数据格式

用户消息触发的webhook数据格式：
```json
{
  "message": "用户消息内容",
  "userId": "用户ID",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "type": "text|image|file",
  "fileUrl": "文件URL（如果有）"
}
```

## 🔍 调试信息

### 主服务器日志
- 用户连接/断开
- 消息发送/接收
- Webhook发送状态

### Webhook测试服务器日志
- 接收到的webhook数据
- 时间戳和消息内容
- 用户ID和消息类型

## 🚨 常见问题

### 1. Webhook没有触发
- 检查用户端是否正确发送消息
- 确认webhook测试服务器正在运行
- 查看主服务器控制台错误信息

### 2. 客服回复也触发了webhook
- 确认服务器代码已正确修改
- 重启主服务器
- 检查Socket.IO连接状态

### 3. 文件上传webhook数据不完整
- 检查文件上传是否成功
- 确认文件URL是否正确生成
- 查看文件上传API响应

## 📝 测试记录

| 测试项目 | 预期结果 | 实际结果 | 状态 |
|---------|---------|---------|------|
| 用户文字消息 | 触发webhook | | |
| 用户图片上传 | 触发webhook | | |
| 用户文件上传 | 触发webhook | | |
| 客服文字回复 | 不触发webhook | | |
| 客服文件发送 | 不触发webhook | | |

## 🎯 测试完成标准

- [ ] 所有用户消息都能正确触发webhook
- [ ] 所有客服回复都不会触发webhook
- [ ] Webhook数据格式完整正确
- [ ] 文件上传webhook包含正确的URL
- [ ] 系统运行稳定无错误 