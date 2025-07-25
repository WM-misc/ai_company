const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const multer = require('multer');
const cors = require('cors');
const bodyParser = require('body-parser');
const path = require('path');
const fs = require('fs');
const { v4: uuidv4 } = require('uuid');
const axios = require('axios');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

// 中间件
app.use(cors());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.static('public'));

// 创建上传目录
const uploadDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir, { recursive: true });
}

// 文件上传配置
const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    cb(null, uploadDir);
  },
  filename: function (req, file, cb) {
    const uniqueName = uuidv4() + path.extname(file.originalname);
    cb(null, uniqueName);
  }
});

const upload = multer({ 
  storage: storage,
  limits: {
    fileSize: 10 * 1024 * 1024 // 10MB限制
  }
});

// 数据存储（内存中，生产环境应使用数据库）
const users = new Map();
const conversations = new Map();
const webhookTimers = new Map(); // 用于防抖动的定时器
const aiResponseStatus = new Map(); // 记录AI回复状态
const serviceReplyQueue = new Map(); // 客服回复队列

const products = [
  {
    id: 1,
    name: "iPhone 15 Pro",
    price: 7999,
    image: "/images/iphone.jpg",
    description: "最新款iPhone，搭载A17 Pro芯片"
  },
  {
    id: 2,
    name: "MacBook Air M2",
    price: 8999,
    image: "/images/macbook.jpg",
    description: "轻薄便携的MacBook Air"
  },
  {
    id: 3,
    name: "AirPods Pro",
    price: 1999,
    image: "/images/airpods.jpg",
    description: "主动降噪无线耳机"
  },
  {
    id: 4,
    name: "iPad Air",
    price: 4399,
    image: "/images/ipad.jpg",
    description: "轻薄强大的iPad Air"
  }
];

// Socket.IO 连接管理
io.on('connection', (socket) => {
  console.log('用户连接:', socket.id);

  // 用户加入聊天
  socket.on('join-chat', (data) => {
    const { userId, userType } = data;
    socket.userId = userId;
    socket.userType = userType;
    
    if (userType === 'customer') {
      socket.join('customer-room');
    } else if (userType === 'service') {
      socket.join('service-room');
    }
    
    console.log(`${userType} 用户 ${userId} 加入聊天`);
  });

  // 发送消息
  socket.on('send-message', async (data) => {
    const { message, type, fileUrl } = data;
    const timestamp = new Date().toISOString();
    
    const messageObj = {
      id: uuidv4(),
      userId: socket.userId,
      userType: socket.userType,
      message,
      type: type || 'text',
      fileUrl,
      timestamp
    };

    // 保存消息到对话记录
    if (!conversations.has(socket.userId)) {
      conversations.set(socket.userId, []);
    }
    conversations.get(socket.userId).push(messageObj);

    // 广播消息
    io.to('customer-room').to('service-room').emit('new-message', messageObj);

    // 如果是用户消息，使用防抖动机制发送webhook到AI服务
    if (socket.userType === 'customer') {
      handleCustomerMessageWithDebounce(socket.userId, messageObj);
    }
  });

  // 断开连接
  socket.on('disconnect', () => {
    console.log('用户断开连接:', socket.id);
    // 清理该用户的定时器
    if (webhookTimers.has(socket.userId)) {
      clearTimeout(webhookTimers.get(socket.userId));
      webhookTimers.delete(socket.userId);
    }
  });
});

// 处理用户消息的防抖动机制
function handleCustomerMessageWithDebounce(userId, messageObj) {
  // 如果AI正在处理这个用户的消息，暂时不发送新的webhook
  if (aiResponseStatus.get(userId) === 'processing') {
    console.log(`用户 ${userId} 的AI正在处理中，暂缓发送webhook`);
    return;
  }

  // 清除之前的定时器
  if (webhookTimers.has(userId)) {
    clearTimeout(webhookTimers.get(userId));
  }

  // 设置新的定时器，1.5秒后发送webhook（防抖动）
  const timer = setTimeout(async () => {
    try {
      console.log(`发送防抖动webhook给用户 ${userId}`);
      await sendWebhookToAIWithContext(userId);
      webhookTimers.delete(userId);
    } catch (error) {
      console.error('Webhook发送失败:', error);
    }
  }, 1500); // 1.5秒防抖动

  webhookTimers.set(userId, timer);
}

// 发送包含上下文的Webhook到AI服务
async function sendWebhookToAIWithContext(userId) {
  const webhookUrl = process.env.AI_WEBHOOK_URL || 'http://localhost:3001/ai-webhook';
  
  try {
    // 标记AI正在处理
    aiResponseStatus.set(userId, 'processing');

    // 获取该用户的对话历史
    const conversation = conversations.get(userId) || [];
    
    // 过滤出最近的消息（最多10条，包含用户和客服的消息）
    const recentMessages = conversation.slice(-10);
    
    // 获取最新的用户消息
    const latestUserMessage = conversation
      .filter(msg => msg.userType === 'customer')
      .slice(-1)[0];

    if (!latestUserMessage) {
      aiResponseStatus.delete(userId);
      return;
    }

    const webhookData = {
      message: latestUserMessage.message,
      userId: userId,
      timestamp: latestUserMessage.timestamp,
      type: latestUserMessage.type,
      fileUrl: latestUserMessage.fileUrl,
      conversationHistory: recentMessages.map(msg => ({
        role: msg.userType === 'customer' ? 'user' : 'assistant',
        content: msg.message,
        timestamp: msg.timestamp,
        type: msg.type,
        fileUrl: msg.fileUrl
      }))
    };

    await axios.post(webhookUrl, webhookData, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.AI_WEBHOOK_TOKEN || 'default-token'}`
      },
      timeout: 10000 // 增加超时时间到10秒
    });
    
    console.log(`Webhook发送成功，用户: ${userId}, 历史消息数: ${recentMessages.length}`);
  } catch (error) {
    console.error('Webhook发送失败:', error.message);
    // 发送失败时清除状态
    aiResponseStatus.delete(userId);
  }
}

// API路由

// 获取商品列表
app.get('/api/products', (req, res) => {
  res.json(products);
});

// 获取商品详情
app.get('/api/products/:id', (req, res) => {
  const product = products.find(p => p.id == req.params.id);
  if (product) {
    res.json(product);
  } else {
    res.status(404).json({ error: '商品不存在' });
  }
});

// 文件上传
app.post('/api/upload', upload.single('file'), (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: '没有文件上传' });
  }
  
  const fileUrl = `/uploads/${req.file.filename}`;
  res.json({
    success: true,
    fileUrl,
    filename: req.file.originalname,
    size: req.file.size
  });
});

// 获取对话记录
app.get('/api/conversations/:userId', (req, res) => {
  const { userId } = req.params;
  const conversation = conversations.get(userId) || [];
  res.json(conversation);
});

// 客服回复接口（支持批量回复）
app.post('/api/service/reply', async (req, res) => {
  const { userId, message, type = 'text', fileUrl, isBatch = false } = req.body;
  
  if (!userId || !message) {
    return res.status(400).json({ error: '缺少必要参数' });
  }

  const messageObj = {
    id: uuidv4(),
    userId: 'service',
    userType: 'service',
    message,
    type,
    fileUrl,
    timestamp: new Date().toISOString()
  };

  // 保存消息
  if (!conversations.has(userId)) {
    conversations.set(userId, []);
  }
  conversations.get(userId).push(messageObj);

  // 如果是批量回复，添加到队列
  if (isBatch) {
    if (!serviceReplyQueue.has(userId)) {
      serviceReplyQueue.set(userId, []);
    }
    serviceReplyQueue.get(userId).push(messageObj);
    
    // 设置延时发送，让真人客服可以继续输入
    setTimeout(() => {
      flushServiceReplyQueue(userId);
    }, 2000); // 2秒后发送积累的消息
  } else {
    // 立即发送单条消息
    io.to('customer-room').to('service-room').emit('new-message', messageObj);
  }

  res.json({ success: true, message: messageObj });
});

// 批量发送客服回复
function flushServiceReplyQueue(userId) {
  const queue = serviceReplyQueue.get(userId);
  if (queue && queue.length > 0) {
    // 发送所有排队的消息
    queue.forEach(messageObj => {
      io.to('customer-room').to('service-room').emit('new-message', messageObj);
    });
    
    // 清空队列
    serviceReplyQueue.delete(userId);
    console.log(`批量发送客服回复给用户 ${userId}, 消息数: ${queue.length}`);
  }
}

// AI回复接口（由AI服务调用）
app.post('/api/ai/reply', async (req, res) => {
  const { userId, message, type = 'text', fileUrl } = req.body;
  
  if (!userId || !message) {
    return res.status(400).json({ error: '缺少必要参数' });
  }

  try {
    // 检查是否需要分段发送长回复
    const messages = splitLongMessage(message);
    
    for (let i = 0; i < messages.length; i++) {
      const messageObj = {
        id: uuidv4(),
        userId: 'ai-service',
        userType: 'service',
        message: messages[i],
        type,
        fileUrl: i === 0 ? fileUrl : null, // 文件只在第一条消息中包含
        timestamp: new Date().toISOString()
      };

      // 保存消息
      if (!conversations.has(userId)) {
        conversations.set(userId, []);
      }
      conversations.get(userId).push(messageObj);

      // 分段发送，模拟真人输入
      setTimeout(() => {
        io.to('customer-room').to('service-room').emit('new-message', messageObj);
      }, i * 1000); // 每条消息间隔1秒
    }

    // AI处理完成，清除状态
    aiResponseStatus.delete(userId);
    
    res.json({ 
      success: true, 
      message: '回复发送成功',
      messageCount: messages.length 
    });
  } catch (error) {
    console.error('AI回复处理失败:', error);
    aiResponseStatus.delete(userId);
    res.status(500).json({ error: '回复处理失败' });
  }
});

// 分割长消息
function splitLongMessage(message, maxLength = 150) {
  if (message.length <= maxLength) {
    return [message];
  }

  const messages = [];
  let current = '';
  const sentences = message.split(/[。！？!?]/).filter(s => s.trim());
  
  for (const sentence of sentences) {
    if (current.length + sentence.length + 1 <= maxLength) {
      current += sentence + '。';
    } else {
      if (current) {
        messages.push(current.trim());
      }
      current = sentence + '。';
    }
  }
  
  if (current) {
    messages.push(current.trim());
  }
  
  return messages.length > 0 ? messages : [message];
}

// 获取所有对话列表（客服端使用）
app.get('/api/service/conversations', (req, res) => {
  const conversationList = Array.from(conversations.entries()).map(([userId, messages]) => ({
    userId,
    lastMessage: messages[messages.length - 1],
    messageCount: messages.length,
    aiStatus: aiResponseStatus.get(userId) || 'idle'
  }));
  res.json(conversationList);
});

// 静态文件服务
app.use('/uploads', express.static(uploadDir));

// 主页路由
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.get('/customer', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'customer.html'));
});

app.get('/service', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'service.html'));
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`服务器运行在 http://localhost:${PORT}`);
  console.log(`商城首页: http://localhost:${PORT}`);
  console.log(`用户端: http://localhost:${PORT}/customer`);
  console.log(`客服端: http://localhost:${PORT}/service`);
}); 