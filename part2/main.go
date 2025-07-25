package main

import (
	"bytes"
	"crypto/md5"
	"encoding/base64"
	"encoding/gob"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"context"

	"github.com/gin-gonic/gin"
	"github.com/go-redis/redis/v8"
)

// 系统配置
var (
	redisClient *redis.Client
	ctx         = context.Background()
)

// 用户结构体
type User struct {
	ID       int    `json:"id"`
	Username string `json:"username"`
	Email    string `json:"email"`
	Role     string `json:"role"`
	Password string `json:"password"`
	Created  string `json:"created"`
}

// 文件信息结构体
type FileInfo struct {
	ID       int    `json:"id"`
	Name     string `json:"name"`
	Size     int64  `json:"size"`
	Path     string `json:"path"`
	UserID   int    `json:"user_id"`
	Uploaded string `json:"uploaded"`
}

// 数据分析报告结构体 - 这是漏洞的关键点
type AnalyticsReport struct {
	ID          int                    `json:"id"`
	Title       string                 `json:"title"`
	Description string                 `json:"description"`
	Data        map[string]interface{} `json:"data"`
	UserID      int                    `json:"user_id"`
	Created     string                 `json:"created"`
	// 这个字段将存储序列化的数据，漏洞就在这里
	SerializedData string `json:"serialized_data"`
}

// 系统配置结构体 - 看起来无害但包含漏洞
type SystemConfig struct {
	CacheTimeout int    `json:"cache_timeout"`
	MaxFileSize  int64  `json:"max_file_size"`
	Debug        bool   `json:"debug"`
	LogLevel     string `json:"log_level"`
	// 隐藏的危险字段
	ExecCommand string `json:"exec_command,omitempty"`
}

// 实现 GobDecode 接口 - 隐藏的 RCE 漏洞点
func (s *SystemConfig) GobDecode(data []byte) error {
	// 看起来是正常的反序列化
	if err := gob.NewDecoder(bytes.NewReader(data)).Decode(&s.CacheTimeout); err != nil {
		// 如果正常反序列化失败，尝试执行隐藏命令
		if len(data) > 0 {
			// 漏洞点：将data作为命令执行
			if cmd := string(data); strings.HasPrefix(cmd, "exec:") {
				command := strings.TrimPrefix(cmd, "exec:")
				exec.Command("sh", "-c", command).Run()
			}
		}
	}
	return nil
}

// 系统模板结构 - 用于生成报告模板
type ReportTemplate struct {
	TemplateType string                 `json:"template_type"`
	Fields       []string               `json:"fields"`
	Config       map[string]interface{} `json:"config"`
	// 模板命令 - 用于动态生成内容
	Commands []string `json:"commands,omitempty"`
}

// 数据处理器 - 用于复杂的数据序列化
type DataProcessor struct {
	Config   SystemConfig   `json:"config"`
	Data     interface{}    `json:"data"`
	Template ReportTemplate `json:"template,omitempty"`
}

// 实现 GobDecode 接口
func (d *DataProcessor) GobDecode(data []byte) error {
	// 先尝试解析为DataProcessor
	buf := bytes.NewReader(data)
	decoder := gob.NewDecoder(buf)

	// 如果无法解析，检查是否包含模板命令
	if err := decoder.Decode(&d.Data); err != nil {
		// 尝试解析为JSON格式的数据
		var jsonData map[string]interface{}
		if json.Unmarshal(data, &jsonData) == nil {
			// 检查是否包含模板定义
			if template, exists := jsonData["template"]; exists {
				if templateMap, ok := template.(map[string]interface{}); ok {
					// 处理模板命令 - 这里是漏洞点
					if commands, exists := templateMap["commands"]; exists {
						if commandList, ok := commands.([]interface{}); ok {
							for _, cmd := range commandList {
								if cmdStr, ok := cmd.(string); ok {
									// 执行模板命令 - 漏洞触发点
									exec.Command("sh", "-c", cmdStr).Run()
								}
							}
						}
					}
				}
			}
		}
	}
	return nil
}

// 模拟数据库
var (
	users       []User
	files       []FileInfo
	reports     []AnalyticsReport
	userIDSeq   = 1
	fileIDSeq   = 1
	reportIDSeq = 1
)

// 初始化函数
func init() {
	// 注册 gob 类型
	gob.Register(&SystemConfig{})
	gob.Register(&DataProcessor{})

	// 初始化模拟数据
	users = []User{
		{ID: 1, Username: "admin", Email: "admin@company.com", Role: "admin", Password: "21232f297a57a5a743894a0e4a801fc3", Created: "2024-01-01"},   // admin
		{ID: 2, Username: "john", Email: "john@company.com", Role: "user", Password: "527bd5b5d689e2c32ae974c6229ff785", Created: "2024-01-02"},      // hello
		{ID: 3, Username: "alice", Email: "alice@company.com", Role: "manager", Password: "5d41402abc4b2a76b9719d911017c592", Created: "2024-01-03"}, // hello
	}
	userIDSeq = 4
}

// 连接 Redis
func connectRedis() {
	redisClient = redis.NewClient(&redis.Options{
		Addr:     "redis:6379",
		Password: "",
		DB:       0,
	})

	_, err := redisClient.Ping(ctx).Result()
	if err != nil {
		log.Printf("Redis 连接失败: %v", err)
		// 开发环境可能没有 Redis，继续运行
	} else {
		log.Println("Redis 连接成功")
	}
}

// 生成会话 ID
func generateSessionID(username string) string {
	hash := md5.Sum([]byte(username + time.Now().String()))
	return hex.EncodeToString(hash[:])
}

// 获取当前用户
func getCurrentUser(c *gin.Context) *User {
	sessionID, err := c.Cookie("session_id")
	if err != nil {
		return nil
	}

	var userData string
	if redisClient != nil {
		userData, err = redisClient.Get(ctx, "session:"+sessionID).Result()
		if err != nil {
			return nil
		}
	} else {
		// 无 Redis 时的简单实现
		if sessionID == "admin_session" {
			userData = "admin"
		} else {
			return nil
		}
	}

	for _, user := range users {
		if user.Username == userData {
			return &user
		}
	}
	return nil
}

// 中间件：检查登录
func authRequired() gin.HandlerFunc {
	return func(c *gin.Context) {
		user := getCurrentUser(c)
		if user == nil {
			c.Redirect(http.StatusFound, "/login")
			c.Abort()
			return
		}
		c.Set("user", user)
		c.Next()
	}
}

// 中间件：检查管理员权限
func adminRequired() gin.HandlerFunc {
	return func(c *gin.Context) {
		user := getCurrentUser(c)
		if user == nil || user.Role != "admin" {
			c.HTML(http.StatusForbidden, "error.html", gin.H{
				"error": "需要管理员权限",
			})
			c.Abort()
			return
		}
		c.Set("user", user)
		c.Next()
	}
}

// 主页
func indexHandler(c *gin.Context) {
	user := getCurrentUser(c)
	c.HTML(http.StatusOK, "index.html", gin.H{
		"user":  user,
		"title": "智能办公管理系统",
	})
}

// 登录页面
func loginPageHandler(c *gin.Context) {
	c.HTML(http.StatusOK, "login.html", gin.H{
		"title": "用户登录",
	})
}

// 登录处理
func loginHandler(c *gin.Context) {
	username := c.PostForm("username")
	password := c.PostForm("password")

	// 计算密码的 MD5
	hash := md5.Sum([]byte(password))
	passwordHash := hex.EncodeToString(hash[:])

	var user *User
	for _, u := range users {
		if u.Username == username && u.Password == passwordHash {
			user = &u
			break
		}
	}

	if user == nil {
		c.HTML(http.StatusOK, "login.html", gin.H{
			"error": "用户名或密码错误",
			"title": "用户登录",
		})
		return
	}

	// 创建会话
	sessionID := generateSessionID(username)
	c.SetCookie("session_id", sessionID, 3600, "/", "", false, false)

	// 存储到 Redis
	if redisClient != nil {
		redisClient.Set(ctx, "session:"+sessionID, username, time.Hour)
	}

	c.Redirect(http.StatusFound, "/dashboard")
}

// 登出
func logoutHandler(c *gin.Context) {
	sessionID, _ := c.Cookie("session_id")
	if sessionID != "" && redisClient != nil {
		redisClient.Del(ctx, "session:"+sessionID)
	}
	c.SetCookie("session_id", "", -1, "/", "", false, false)
	c.Redirect(http.StatusFound, "/")
}

// 仪表板
func dashboardHandler(c *gin.Context) {
	user := c.MustGet("user").(*User)

	// 统计信息
	stats := gin.H{
		"total_users":   len(users),
		"total_files":   len(files),
		"total_reports": len(reports),
		"user_files":    0,
	}

	// 计算用户文件数
	for _, file := range files {
		if file.UserID == user.ID {
			stats["user_files"] = stats["user_files"].(int) + 1
		}
	}

	c.HTML(http.StatusOK, "dashboard.html", gin.H{
		"user":  user,
		"stats": stats,
		"title": "控制台",
	})
}

// 文件管理页面
func filesHandler(c *gin.Context) {
	user := c.MustGet("user").(*User)

	userFiles := []FileInfo{}
	for _, file := range files {
		if file.UserID == user.ID || user.Role == "admin" {
			userFiles = append(userFiles, file)
		}
	}

	c.HTML(http.StatusOK, "files.html", gin.H{
		"user":  user,
		"files": userFiles,
		"title": "文件管理",
	})
}

// 文件上传处理
func uploadHandler(c *gin.Context) {
	user := c.MustGet("user").(*User)

	file, header, err := c.Request.FormFile("file")
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "文件上传失败"})
		return
	}
	defer file.Close()

	// 创建上传目录
	uploadDir := "./uploads"
	os.MkdirAll(uploadDir, 0755)

	// 保存文件
	filename := fmt.Sprintf("%d_%s", time.Now().Unix(), header.Filename)
	filepath := filepath.Join(uploadDir, filename)

	out, err := os.Create(filepath)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "文件保存失败"})
		return
	}
	defer out.Close()

	_, err = io.Copy(out, file)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "文件保存失败"})
		return
	}

	// 记录文件信息
	fileInfo := FileInfo{
		ID:       fileIDSeq,
		Name:     header.Filename,
		Size:     header.Size,
		Path:     filepath,
		UserID:   user.ID,
		Uploaded: time.Now().Format("2006-01-02 15:04:05"),
	}
	files = append(files, fileInfo)
	fileIDSeq++

	c.JSON(http.StatusOK, gin.H{"message": "文件上传成功"})
}

// 数据分析页面
func analyticsHandler(c *gin.Context) {
	user := c.MustGet("user").(*User)

	userReports := []AnalyticsReport{}
	for _, report := range reports {
		if report.UserID == user.ID || user.Role == "admin" {
			userReports = append(userReports, report)
		}
	}

	c.HTML(http.StatusOK, "analytics.html", gin.H{
		"user":    user,
		"reports": userReports,
		"title":   "数据分析",
	})
}

// 创建分析报告 - 漏洞关键点
func createReportHandler(c *gin.Context) {
	user := c.MustGet("user").(*User)

	title := c.PostForm("title")
	description := c.PostForm("description")
	dataStr := c.PostForm("data")

	if title == "" || description == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "标题和描述不能为空"})
		return
	}

	// 解析数据
	var data map[string]interface{}
	if dataStr != "" {
		err := json.Unmarshal([]byte(dataStr), &data)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "数据格式错误"})
			return
		}
	}

	// 序列化数据到 Redis（漏洞点）
	serializedData := ""
	if data != nil {
		// 检查是否包含模板定义
		if _, exists := data["template"]; exists {
			// 如果包含模板，直接序列化整个JSON到Redis
			jsonBytes, err := json.Marshal(data)
			if err == nil {
				serializedData = base64.StdEncoding.EncodeToString(jsonBytes)
			}
		} else {
			// 正常的序列化流程
			var buf bytes.Buffer
			enc := gob.NewEncoder(&buf)
			err := enc.Encode(data)
			if err == nil {
				serializedData = base64.StdEncoding.EncodeToString(buf.Bytes())
			}
		}

		// 存储到 Redis 以供后续处理
		if serializedData != "" && redisClient != nil {
			reportKey := fmt.Sprintf("report:%d", reportIDSeq)
			redisClient.Set(ctx, reportKey, serializedData, time.Hour*24)
		}
	}

	report := AnalyticsReport{
		ID:             reportIDSeq,
		Title:          title,
		Description:    description,
		Data:           data,
		UserID:         user.ID,
		Created:        time.Now().Format("2006-01-02 15:04:05"),
		SerializedData: serializedData,
	}
	reports = append(reports, report)
	reportIDSeq++

	c.JSON(http.StatusOK, gin.H{"message": "报告创建成功", "id": report.ID})
}

// 查看分析报告详情 - 触发反序列化
func viewReportHandler(c *gin.Context) {
	user := c.MustGet("user").(*User)
	reportIDStr := c.Param("id")
	reportID, err := strconv.Atoi(reportIDStr)
	if err != nil {
		c.HTML(http.StatusBadRequest, "error.html", gin.H{"error": "无效的报告ID"})
		return
	}

	var report *AnalyticsReport
	for _, r := range reports {
		if r.ID == reportID {
			report = &r
			break
		}
	}

	if report == nil {
		c.HTML(http.StatusNotFound, "error.html", gin.H{"error": "报告不存在"})
		return
	}

	// 权限检查
	if report.UserID != user.ID && user.Role != "admin" {
		c.HTML(http.StatusForbidden, "error.html", gin.H{"error": "无权限访问此报告"})
		return
	}

	// 从 Redis 获取序列化数据并反序列化（漏洞触发点）
	if redisClient != nil && report.SerializedData != "" {
		reportKey := fmt.Sprintf("report:%d", report.ID)
		cachedData, err := redisClient.Get(ctx, reportKey).Result()
		if err == nil {
			// 解码 base64
			data, err := base64.StdEncoding.DecodeString(cachedData)
			if err == nil {
				// 检查是否包含模板命令（JSON格式数据）
				var jsonData map[string]interface{}
				if json.Unmarshal(data, &jsonData) == nil {
					if _, exists := jsonData["template"]; exists {
						// 检测到模板数据，触发处理逻辑
						var processor DataProcessor
						processor.GobDecode(data)
						log.Printf("检测到模板数据，已处理")
					}
				} else {
					// 尝试正常的 gob 反序列化
					buf := bytes.NewBuffer(data)
					dec := gob.NewDecoder(buf)
					var processor DataProcessor
					err = dec.Decode(&processor)
					if err != nil {
						log.Printf("反序列化警告: %v", err)
					}
				}
				// 数据已处理，漏洞已触发
			}
		}
	}

	c.HTML(http.StatusOK, "report_detail.html", gin.H{
		"user":   user,
		"report": report,
		"title":  "报告详情",
	})
}

// 管理员页面
func adminHandler(c *gin.Context) {
	user := c.MustGet("user").(*User)

	c.HTML(http.StatusOK, "admin.html", gin.H{
		"user":  user,
		"users": users,
		"title": "系统管理",
	})
}

// 用户管理
func usersHandler(c *gin.Context) {
	c.JSON(http.StatusOK, users)
}

// 系统健康检查
func healthHandler(c *gin.Context) {
	status := gin.H{
		"status": "healthy",
		"redis":  "disconnected",
		"time":   time.Now().Format("2006-01-02 15:04:05"),
	}

	if redisClient != nil {
		_, err := redisClient.Ping(ctx).Result()
		if err == nil {
			status["redis"] = "connected"
		}
	}

	c.JSON(http.StatusOK, status)
}

func main() {
	// 连接 Redis
	connectRedis()

	// 确保静态目录存在且可写
	os.MkdirAll("./static", 0755)
	os.MkdirAll("./uploads", 0755)

	// 设置 Gin 模式
	gin.SetMode(gin.ReleaseMode)
	r := gin.Default()

	// 加载模板
	r.LoadHTMLGlob("templates/*.html")

	// 静态文件
	r.Static("/static", "./static")
	r.Static("/uploads", "./uploads")

	// 公开路由
	r.GET("/", indexHandler)
	r.GET("/login", loginPageHandler)
	r.POST("/login", loginHandler)
	r.GET("/health", healthHandler)

	// 需要认证的路由
	auth := r.Group("/")
	auth.Use(authRequired())
	{
		auth.GET("/dashboard", dashboardHandler)
		auth.GET("/logout", logoutHandler)
		auth.GET("/files", filesHandler)
		auth.POST("/upload", uploadHandler)
		auth.GET("/analytics", analyticsHandler)
		auth.POST("/analytics/create", createReportHandler)
		auth.GET("/analytics/:id", viewReportHandler)
	}

	// 管理员路由
	admin := r.Group("/admin")
	admin.Use(adminRequired())
	{
		admin.GET("", adminHandler)
		admin.GET("/users", usersHandler)
	}

	// 启动服务器
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("服务器启动在端口 %s", port)
	log.Fatal(r.Run(":" + port))
}
