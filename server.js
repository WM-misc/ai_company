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

    // 如果是用户消息，发送webhook到AI服务
    if (socket.userType === 'customer') {
      try {
        await sendWebhookToAI(messageObj);
      } catch (error) {
        console.error('Webhook发送失败:', error);
      }
    }
  });

  // 断开连接
  socket.on('disconnect', () => {
    console.log('用户断开连接:', socket.id);
  });
});

// Webhook发送到AI服务
async function sendWebhookToAI(messageObj) {
  const webhookUrl = process.env.AI_WEBHOOK_URL || 'http://localhost:3001/ai-webhook';
  
  try {
    await axios.post(webhookUrl, {
      message: messageObj.message,
      userId: messageObj.userId,
      timestamp: messageObj.timestamp,
      type: messageObj.type,
      fileUrl: messageObj.fileUrl
    }, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.AI_WEBHOOK_TOKEN || 'default-token'}`
      },
      timeout: 5000
    });
    console.log('Webhook发送成功');
  } catch (error) {
    console.error('Webhook发送失败:', error.message);
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

// 客服回复接口
app.post('/api/service/reply', async (req, res) => {
  const { userId, message, type = 'text', fileUrl } = req.body;
  
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

  // 通过Socket.IO发送消息
  io.to('customer-room').to('service-room').emit('new-message', messageObj);

  // 客服回复不触发webhook，只有用户消息才触发

  res.json({ success: true, message: messageObj });
});

// 获取所有对话列表（客服端使用）
app.get('/api/service/conversations', (req, res) => {
  const conversationList = Array.from(conversations.entries()).map(([userId, messages]) => ({
    userId,
    lastMessage: messages[messages.length - 1],
    messageCount: messages.length
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