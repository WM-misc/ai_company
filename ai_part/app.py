from flask import Flask, request, jsonify
import requests
import json
from datetime import datetime
from langchain.chat_models import init_chat_model
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate
from config.config import OPENAI_API_KEY, OPENAI_API_BASE, OPENAI_API_MODEL
from tools import AVAILABLE_TOOLS, is_image_file, is_archive_file

app = Flask(__name__)

# 初始化大模型
llm = init_chat_model(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_API_BASE,
    model=OPENAI_API_MODEL,
    model_provider="openai",
    max_retries=3,
)

# 配置参数
import os
SERVER_BASE_URL = os.environ.get("SERVER_BASE_URL", "http://part1:3000")
AI_WEBHOOK_TOKEN = "default-token"  # 用于验证webhook请求

# 智能客服系统提示词
SYSTEM_PROMPT = """你是一个专业的电商客服助手，请遵循以下指导原则：

1. 身份设定：你是一个友好、专业、耐心的在线客服代表。
2. 服务态度：始终保持礼貌、热情、积极的服务态度。
3. 回复风格：简洁明了，重点突出，易于理解，模仿淘宝商家的客服风格。
4. 其他要求：不要让用户察觉到你是AI助手，全力模拟人类客服的交流方式。
5. 专业领域：
   - 商品咨询（iPhone 15 Pro、MacBook Air M2、AirPods Pro、iPad Air等）
   - 订单查询和处理
   - 售后服务支持
   - 技术问题解答
   - 购买建议和推荐

6. 商品信息：
   - iPhone 15 Pro: ¥7999，搭载A17 Pro芯片，最新款iPhone
   - MacBook Air M2: ¥8999，轻薄便携的笔记本电脑
   - AirPods Pro: ¥1999，主动降噪无线耳机
   - iPad Air: ¥4399，轻薄强大的平板电脑

7. 回复要求：
   - 每次回复控制在150字以内，如果内容较多可以分段回复
   - 如果用户询问不在专业范围内的问题，礼貌引导到相关产品或服务
   - 对于文件或图片消息，主动询问具体需要什么帮助
   - 提供具体的解决方案或建议
   - 适当使用表情符号增加亲和力
   - 根据对话历史提供连贯的回复，避免重复信息
   - 不要使用markdown语法，直接使用文本回复

8. 工具使用指南：
   - 当用户发送图片时，使用analyze_image_content工具分析图片内容，然后基于分析结果提供专业建议
   - 当用户发送压缩包文件（zip、rar、7z）时，使用extract_and_analyze_archive工具解压并分析内容
   - 在分析完文件后，要结合商品信息给出专业的购买建议或解决方案
   - 如果文件分析失败，要礼貌地说明原因并建议替代方案

请根据用户的消息内容和对话历史提供专业、有帮助的回复。当遇到图片或压缩包文件时，主动使用相应的工具进行分析。"""

# 创建agent提示模板
prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("placeholder", "{chat_history}"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

# 创建工具调用代理
agent = create_tool_calling_agent(llm, AVAILABLE_TOOLS, prompt)
agent_executor = AgentExecutor(agent=agent, tools=AVAILABLE_TOOLS, verbose=True)

def build_conversation_context(conversation_history, current_message, message_type="text", file_url=None):
    """构建包含历史上下文的对话"""
    chat_history = []
    
    # 添加历史对话
    if conversation_history:
        for msg in conversation_history[:-1]:  # 排除最后一条消息（当前消息）
            content = msg.get('content', '')
            if msg.get('type') == 'image' and msg.get('fileUrl'):
                content += f" [发送了图片: {msg.get('fileUrl')}]"
            elif msg.get('type') == 'file' and msg.get('fileUrl'):
                content += f" [发送了文件: {msg.get('fileUrl')}]"
            
            if content.strip():
                role = msg.get('role', 'user')
                if role == 'user':
                    chat_history.append(("human", content))
                else:
                    chat_history.append(("ai", content))
    
    # 构建当前消息
    current_content = current_message
    
    # 检查是否需要使用工具
    tool_hint = ""
    if message_type == "image" and file_url:
        current_content += f" [用户发送了一张图片: {file_url}]"
        tool_hint = "请使用analyze_image_content工具分析这张图片的内容。"
    elif message_type == "file" and file_url:
        # 检查文件类型
        if is_archive_file(file_url):
            current_content += f" [用户发送了一个压缩包文件: {file_url}]"
            tool_hint = "请使用extract_and_analyze_archive工具解压并分析这个压缩包的内容。"
        elif is_image_file(file_url):
            current_content += f" [用户发送了一张图片: {file_url}]"
            tool_hint = "请使用analyze_image_content工具分析这张图片的内容。"
        else:
            current_content += f" [用户发送了一个文件: {file_url}]"
    
    if tool_hint:
        current_content += f" {tool_hint}"
    
    return chat_history, current_content

def get_ai_response_with_context_and_tools(user_message, conversation_history=None, message_type="text", file_url=None):
    """调用大模型获取智能回复（包含上下文和工具调用）"""
    try:
        print(f"开始处理用户消息: {user_message}")
        print(f"消息类型: {message_type}, 文件URL: {file_url}")
        
        # 构建包含历史上下文的对话
        chat_history, current_input = build_conversation_context(
            conversation_history, user_message, message_type, file_url
        )
        
        print(f"发送给大模型的历史消息数: {len(chat_history)}")
        print(f"当前输入: {current_input}")
        
        # 使用agent执行器调用大模型（支持工具调用）
        result = agent_executor.invoke({
            "input": current_input,
            "chat_history": chat_history
        })
        
        response = result.get("output", "")
        print(f"AI回复: {response}")
        
        return response.strip() if response else "抱歉，我没能理解您的问题，请您再详细描述一下。"
        
    except Exception as e:
        print(f"大模型调用失败: {e}")
        return "我也不太清楚这个问题呢。"

def send_ai_reply_to_server(user_id, reply_message):
    """将AI回复发送回server.js（使用新的AI回复接口）"""
    try:
        url = f"{SERVER_BASE_URL}/api/ai/reply"
        data = {
            "userId": user_id,
            "message": reply_message,
            "type": "text"
        }
        
        response = requests.post(url, json=data, timeout=5)
        if response.status_code == 200:
            result = response.json()
            message_count = result.get('messageCount', 1)
            print(f"成功发送AI回复到用户 {user_id}, 分段数: {message_count}")
            return True
        else:
            print(f"发送AI回复失败，状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"发送AI回复到服务器失败: {e}")
        return False

@app.route('/ai-webhook', methods=['POST'])
def webhook_handler():
    """处理来自server.js的webhook请求（支持历史上下文和工具调用）"""
    try:
        # 验证请求头
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer ') or auth_header.split(' ')[1] != AI_WEBHOOK_TOKEN:
            return jsonify({"error": "未授权的请求"}), 401
        
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({"error": "无效的JSON数据"}), 400
        
        # 提取消息信息
        user_message = data.get('message', '')
        user_id = data.get('userId', '')
        message_type = data.get('type', 'text')
        file_url = data.get('fileUrl')
        timestamp = data.get('timestamp', '')
        conversation_history = data.get('conversationHistory', [])
        
        print(f"收到用户消息webhook:")
        print(f"时间: {timestamp}")
        print(f"用户ID: {user_id}")
        print(f"消息内容: {user_message}")
        print(f"消息类型: {message_type}")
        print(f"文件URL: {file_url}")
        print(f"历史消息数: {len(conversation_history)}")
        
        # 验证必要参数
        if not user_message or not user_id:
            return jsonify({"error": "缺少必要参数"}), 400
        
        # 获取AI回复（包含历史上下文和工具调用）
        ai_reply = get_ai_response_with_context_and_tools(
            user_message, 
            conversation_history, 
            message_type, 
            file_url
        )
        print(f"最终AI回复: {ai_reply}")
        
        # 发送回复到server.js
        success = send_ai_reply_to_server(user_id, ai_reply)
        
        if success:
            return jsonify({
                "success": True,
                "message": "AI回复发送成功",
                "reply": ai_reply,
                "contextLength": len(conversation_history),
                "toolsUsed": message_type in ['image', 'file'],
                "timestamp": datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "AI回复发送失败",
                "reply": ai_reply,
                "timestamp": datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        print(f"Webhook处理错误: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/status', methods=['GET'])
def status_check():
    """健康检查端点"""
    return jsonify({
        "status": "running",
        "service": "AI智能客服Webhook服务",
        "model": OPENAI_API_MODEL,
        "features": [
            "对话历史上下文支持",
            "防抖动机制",
            "智能分段回复",
            "文件消息处理",
            "图片内容识别",
            "压缩包解压分析"
        ],
        "available_tools": [tool.name for tool in AVAILABLE_TOOLS],
        "timestamp": datetime.now().isoformat()
    })

@app.route('/test', methods=['GET'])
def test_ai():
    """测试AI模型连接"""
    try:
        test_response = llm.invoke("你好，请简单介绍一下自己，控制在50字以内")
        return jsonify({
            "success": True,
            "test_response": test_response.content,
            "model": OPENAI_API_MODEL,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/test-context', methods=['POST'])
def test_context():
    """测试上下文功能"""
    try:
        data = request.get_json()
        user_message = data.get('message', '你好')
        conversation_history = data.get('conversationHistory', [])
        
        ai_reply = get_ai_response_with_context_and_tools(user_message, conversation_history)
        
        return jsonify({
            "success": True,
            "reply": ai_reply,
            "contextLength": len(conversation_history),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/test-tools', methods=['POST'])
def test_tools():
    """测试工具调用功能"""
    try:
        data = request.get_json()
        message = data.get('message', '请帮我分析一下')
        file_url = data.get('fileUrl', '')
        message_type = data.get('type', 'text')
        
        if not file_url:
            return jsonify({
                "success": False,
                "error": "需要提供file_url参数"
            }), 400
        
        ai_reply = get_ai_response_with_context_and_tools(
            message, [], message_type, file_url
        )
        
        return jsonify({
            "success": True,
            "reply": ai_reply,
            "fileUrl": file_url,
            "messageType": message_type,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    print("🤖 AI智能客服Webhook服务启动中...")
    print(f"📡 Webhook端点: http://localhost:3001/ai-webhook")
    print(f"🔍 状态检查: http://localhost:3001/status")
    print(f"🧪 AI测试: http://localhost:3001/test")
    print(f"📋 上下文测试: http://localhost:3001/test-context")
    print(f"🛠️ 工具测试: http://localhost:3001/test-tools")
    print(f"🎯 使用模型: {OPENAI_API_MODEL}")
    print("✨ 新功能:")
    print("  - 支持对话历史上下文")
    print("  - 防抖动机制处理连续消息")
    print("  - 智能分段回复长消息")
    print("  - 优化的文件消息处理")
    print("  - 🖼️ 图片内容识别和分析")
    print("  - 📦 压缩包解压和文件分析")
    print(f"🛠️ 可用工具: {[tool.name for tool in AVAILABLE_TOOLS]}")
    print("等待接收用户消息...")
    
    app.run(host='0.0.0.0', port=3001, debug=True)