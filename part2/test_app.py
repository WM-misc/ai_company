#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试脚本，验证应用是否能正常启动
"""

import sys
import os
import time
import threading
import requests
from app import app, init_db

def test_basic_functionality():
    """测试基本功能"""
    print("正在测试基本功能...")
    
    try:
        # 测试首页重定向
        response = requests.get("http://localhost:5000/", timeout=5)
        if response.status_code == 200:
            print("✓ 首页访问正常")
        
        # 测试登录页面
        response = requests.get("http://localhost:5000/login", timeout=5)
        if response.status_code == 200 and "员工绩效管理系统" in response.text:
            print("✓ 登录页面正常")
        
        # 测试登录功能
        login_data = {
            'username': 'admin',
            'password': 'admin@2024'
        }
        session = requests.Session()
        response = session.post("http://localhost:5000/login", data=login_data)
        if response.status_code == 200:
            print("✓ 登录功能正常")
            
            # 测试管理员页面
            response = session.get("http://localhost:5000/admin/templates")
            if response.status_code == 200:
                print("✓ 管理员功能正常")
            
            # 测试漏洞端点
            test_payload = {
                "content": "测试内容 {{test}}",
                "variables": '{"test": "value"}'
            }
            response = session.post(
                "http://localhost:5000/admin/templates/preview",
                json=test_payload,
                headers={'Content-Type': 'application/json'}
            )
            if response.status_code == 200:
                print("✓ 漏洞端点可访问")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False

def run_server():
    """在后台运行服务器"""
    print("正在启动Flask服务器...")
    app.run(host='127.0.0.1', port=5000, debug=False)

def main():
    """主测试函数"""
    print("=" * 50)
    print("CTF题目应用测试")
    print("=" * 50)
    
    # 初始化数据库
    print("初始化数据库...")
    init_db()
    print("✓ 数据库初始化完成")
    
    # 在后台启动服务器
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # 等待服务器启动
    print("等待服务器启动...")
    time.sleep(3)
    
    # 运行测试
    if test_basic_functionality():
        print("\n✅ 所有测试通过！应用运行正常")
        print("\n🔗 访问地址: http://localhost:5000")
        print("🔑 管理员账户: admin / admin@2024")
        print("📝 攻击路径: 系统管理 → 模板管理 → 创建新模板 → 预览效果")
        print("\n按 Ctrl+C 停止服务器...")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n服务器已停止")
    else:
        print("\n❌ 测试失败！请检查代码")
        sys.exit(1)

if __name__ == "__main__":
    main() 