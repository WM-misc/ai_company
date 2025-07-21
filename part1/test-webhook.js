const express = require('express');
const bodyParser = require('body-parser');

const app = express();
const PORT = 3001;

app.use(bodyParser.json());

// Webhook接收端点
app.post('/ai-webhook', (req, res) => {
    console.log('收到用户消息webhook:');
    console.log('时间:', new Date().toLocaleString());
    console.log('消息内容:', req.body.message);
    console.log('用户ID:', req.body.userId);
    console.log('消息类型:', req.body.type);
    console.log('文件URL:', req.body.fileUrl);
    console.log('完整数据:', JSON.stringify(req.body, null, 2));
    console.log('---');
    
    res.json({ 
        success: true, 
        message: '用户消息Webhook接收成功',
        timestamp: new Date().toISOString()
    });
});

// 状态检查端点
app.get('/status', (req, res) => {
    res.json({ 
        status: 'running', 
        port: PORT,
        message: 'AI服务webhook测试服务器运行中 - 监听用户消息'
    });
});

app.listen(PORT, () => {
    console.log(`AI服务webhook测试服务器运行在 http://localhost:${PORT}`);
    console.log(`Webhook端点: http://localhost:${PORT}/ai-webhook`);
    console.log(`状态检查: http://localhost:${PORT}/status`);
    console.log('等待接收用户消息webhook...');
}); 