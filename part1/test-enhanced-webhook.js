const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios');

const app = express();
const PORT = 3002;

app.use(bodyParser.json());

// 模拟对话历史数据
const mockConversationHistory = [
    {
        role: 'user',
        content: '你好，我想了解一下iPhone 15 Pro',
        timestamp: '2024-01-01T10:00:00.000Z',
        type: 'text'
    },
    {
        role: 'assistant',
        content: '您好！😊 iPhone 15 Pro是我们的最新旗舰机型，搭载A17 Pro芯片，性能强劲。',
        timestamp: '2024-01-01T10:00:15.000Z',
        type: 'text'
    },
    {
        role: 'user',
        content: '价格是多少？有什么颜色？',
        timestamp: '2024-01-01T10:01:00.000Z',
        type: 'text'
    }
];

// 测试端点
app.post('/test-webhook', async (req, res) => {
    console.log('=== 增强Webhook测试 ===');
    console.log('时间:', new Date().toLocaleString());
    console.log('数据:', JSON.stringify(req.body, null, 2));
    
    const { message, userId, conversationHistory = [] } = req.body;
    console.log(`用户消息: ${message}`);
    console.log(`历史消息数: ${conversationHistory.length}`);
    
    if (conversationHistory.length > 0) {
        console.log('最近对话历史:');
        conversationHistory.slice(-3).forEach((msg, index) => {
            console.log(`  ${index + 1}. [${msg.role}] ${msg.content}`);
        });
    }
    
    console.log('---');
    
    res.json({ 
        success: true, 
        message: '增强Webhook接收成功',
        contextReceived: conversationHistory.length,
        timestamp: new Date().toISOString()
    });
});

// 测试AI服务的上下文功能
app.get('/test-ai-context', async (req, res) => {
    try {
        console.log('测试AI服务上下文功能...');
        
        const testData = {
            message: '那有什么优惠活动吗？',
            conversationHistory: mockConversationHistory
        };
        
        const response = await axios.post('http://localhost:3001/test-context', testData, {
            headers: { 'Content-Type': 'application/json' },
            timeout: 10000
        });
        
        console.log('AI回复:', response.data.reply);
        console.log('上下文长度:', response.data.contextLength);
        
        res.json({
            success: true,
            aiReply: response.data.reply,
            contextLength: response.data.contextLength
        });
        
    } catch (error) {
        console.error('测试失败:', error.message);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// 测试图片识别工具
app.get('/test-image-tool', async (req, res) => {
    try {
        console.log('测试图片识别工具...');
        
        // 使用现有上传的图片文件（如果存在）
        const testImageUrl = '/uploads/d1726a1b-e840-422f-ade7-6dd093214588.jpg'; // 修改为实际的图片路径
        
        const testData = {
            message: '请帮我看看这张图片是什么内容',
            fileUrl: testImageUrl,
            type: 'image'
        };
        
        const response = await axios.post('http://localhost:3001/test-tools', testData, {
            headers: { 'Content-Type': 'application/json' },
            timeout: 30000 // 图片分析可能需要更长时间
        });
        
        console.log('图片分析结果:', response.data.reply);
        
        res.json({
            success: true,
            imageUrl: testImageUrl,
            analysisResult: response.data.reply,
            timestamp: response.data.timestamp
        });
        
    } catch (error) {
        console.error('图片识别测试失败:', error.message);
        res.status(500).json({
            success: false,
            error: error.message,
            details: error.response?.data
        });
    }
});

// 测试压缩包解压工具（需要先有压缩包文件）
app.get('/test-archive-tool', async (req, res) => {
    try {
        console.log('测试压缩包解压工具...');
        
        // 需要先上传一个压缩包文件到uploads目录
        const testArchiveUrl = '/uploads/test.zip'; // 修改为实际的压缩包路径
        
        const testData = {
            message: '请帮我看看这个压缩包里有什么',
            fileUrl: testArchiveUrl,
            type: 'file'
        };
        
        const response = await axios.post('http://localhost:3001/test-tools', testData, {
            headers: { 'Content-Type': 'application/json' },
            timeout: 60000 // 压缩包分析可能需要更长时间
        });
        
        console.log('压缩包分析结果:', response.data.reply);
        
        res.json({
            success: true,
            archiveUrl: testArchiveUrl,
            analysisResult: response.data.reply,
            timestamp: response.data.timestamp
        });
        
    } catch (error) {
        console.error('压缩包解压测试失败:', error.message);
        res.status(500).json({
            success: false,
            error: error.message,
            details: error.response?.data
        });
    }
});

// 模拟连续消息测试
app.get('/test-debounce', async (req, res) => {
    try {
        console.log('开始测试防抖动机制...');
        
        const userId = 'test_user_' + Date.now();
        const messages = [
            '你好',
            '我想买iPhone',
            '什么价格',
            '有优惠吗'
        ];
        
        // 快速发送多条消息
        for (let i = 0; i < messages.length; i++) {
            const webhookData = {
                message: messages[i],
                userId: userId,
                timestamp: new Date().toISOString(),
                type: 'text',
                conversationHistory: mockConversationHistory
            };
            
            console.log(`发送消息 ${i + 1}: ${messages[i]}`);
            
            try {
                await axios.post('http://localhost:3001/ai-webhook', webhookData, {
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer default-token'
                    },
                    timeout: 5000
                });
            } catch (err) {
                console.log(`消息 ${i + 1} 发送失败:`, err.message);
            }
            
            // 短间隔发送，触发防抖动
            await new Promise(resolve => setTimeout(resolve, 500));
        }
        
        res.json({
            success: true,
            message: '防抖动测试完成，查看控制台输出',
            messagesSent: messages.length
        });
        
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// 测试长消息分段功能
app.get('/test-long-message', async (req, res) => {
    try {
        console.log('测试长消息分段功能...');
        
        const longMessage = `iPhone 15 Pro是苹果公司最新推出的旗舰手机，搭载了全新的A17 Pro芯片，采用3纳米工艺制程，性能相比上一代提升显著。该手机拥有6.1英寸Super Retina XDR显示屏，支持ProMotion技术，刷新率可达120Hz。相机系统也有重大升级，主摄像头为4800万像素，支持2倍和3倍光学变焦，夜景模式和人像模式都有明显改进。电池续航能力也得到加强，支持快速充电和无线充电。目前我们有多种颜色可选，包括深空黑、银色、金色和天蓝色。价格方面，128GB版本售价7999元，256GB版本售价8999元，512GB版本售价10999元。现在购买还有限时优惠活动，可以享受24期免息分期付款，以及免费的AppleCare+服务一年。如果您是老用户换新机，还可以享受以旧换新服务，根据您旧手机的型号和成色，可以抵扣300-2000元不等的费用。`;
        
        const response = await axios.post('http://localhost:3000/api/ai/reply', {
            userId: 'test_long_message',
            message: longMessage,
            type: 'text'
        }, {
            headers: { 'Content-Type': 'application/json' },
            timeout: 10000
        });
        
        console.log('分段回复测试结果:', response.data);
        
        res.json({
            success: true,
            messageCount: response.data.messageCount,
            originalLength: longMessage.length
        });
        
    } catch (error) {
        console.error('长消息测试失败:', error.message);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// 检查AI服务工具状态
app.get('/check-tools', async (req, res) => {
    try {
        console.log('检查AI服务工具状态...');
        
        const response = await axios.get('http://localhost:3001/status', {
            timeout: 5000
        });
        
        console.log('AI服务状态:', response.data);
        
        res.json({
            success: true,
            aiServiceStatus: response.data,
            availableTools: response.data.available_tools || [],
            features: response.data.features || []
        });
        
    } catch (error) {
        console.error('检查工具状态失败:', error.message);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// 状态检查
app.get('/status', (req, res) => {
    res.json({ 
        status: 'running', 
        port: PORT,
        message: '增强Webhook测试服务器运行中',
        features: [
            '防抖动机制测试',
            '上下文功能测试',
            '长消息分段测试',
            'Webhook数据验证',
            '图片识别工具测试',
            '压缩包解压工具测试'
        ]
    });
});

// 主页面
app.get('/', (req, res) => {
    res.send(`
        <html>
        <head><title>增强Webhook测试工具</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h1>🧪 增强Webhook测试工具</h1>
            <h2>基础测试功能:</h2>
            <ul>
                <li><a href="/test-ai-context">测试AI上下文功能</a></li>
                <li><a href="/test-debounce">测试防抖动机制</a></li>
                <li><a href="/test-long-message">测试长消息分段</a></li>
                <li><a href="/check-tools">检查AI服务工具状态</a></li>
            </ul>
            
            <h2>🆕 工具测试功能:</h2>
            <ul>
                <li><a href="/test-image-tool">🖼️ 测试图片识别工具</a></li>
                <li><a href="/test-archive-tool">📦 测试压缩包解压工具</a></li>
            </ul>
            
            <h2>系统状态:</h2>
            <ul>
                <li><a href="/status">查看测试服务状态</a></li>
            </ul>
            
            <h2>使用说明:</h2>
            <ol>
                <li>确保主服务器 (port 3000) 正在运行</li>
                <li>确保AI服务 (port 3001) 正在运行</li>
                <li>对于图片识别测试，需要先上传图片到uploads目录</li>
                <li>对于压缩包测试，需要先上传zip/rar/7z文件到uploads目录</li>
                <li>点击上面的链接进行各项功能测试</li>
                <li>观察控制台输出查看测试结果</li>
            </ol>
            
            <h2>Webhook端点:</h2>
            <p><code>POST /test-webhook</code> - 接收webhook测试数据</p>
            
            <h2>工具测试说明:</h2>
            <div style="background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px;">
                <h3>🖼️ 图片识别工具</h3>
                <p>支持格式: JPG, PNG, GIF, BMP, WEBP, TIFF</p>
                <p>功能: 识别图片中的文字和内容，提供尺寸等基本信息</p>
                
                <h3>📦 压缩包解压工具</h3>
                <p>支持格式: ZIP, RAR, 7Z</p>
                <p>功能: 解压并分析压缩包内容，读取文本文件，识别图片文件，列出其他文件信息</p>
            </div>
            
            <script>
                setInterval(() => {
                    fetch('/status')
                        .then(r => r.json())
                        .then(data => console.log('服务状态:', data))
                        .catch(e => console.error('状态检查失败:', e));
                }, 30000);
            </script>
        </body>
        </html>
    `);
});

app.listen(PORT, () => {
    console.log(`🧪 增强Webhook测试服务器运行在 http://localhost:${PORT}`);
    console.log(`📡 Webhook端点: http://localhost:${PORT}/test-webhook`);
    console.log(`🔍 状态检查: http://localhost:${PORT}/status`);
    console.log(`🌐 测试页面: http://localhost:${PORT}`);
    console.log('');
    console.log('可用测试:');
    console.log('  - 上下文功能: GET /test-ai-context');
    console.log('  - 防抖动机制: GET /test-debounce');
    console.log('  - 长消息分段: GET /test-long-message');
    console.log('  - 🖼️ 图片识别: GET /test-image-tool');
    console.log('  - 📦 压缩包解压: GET /test-archive-tool');
    console.log('  - 工具状态检查: GET /check-tools');
    console.log('');
    console.log('注意: 工具测试需要先上传对应类型的文件到uploads目录');
    console.log('等待测试请求...');
}); 