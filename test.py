import requests
import json

# 构建文件上传请求
url = "http://localhost:3002/api/v1/files/"
headers = {
    "Accept": "application/json",
    "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImQ4NzRiMjYzLTdhZDMtNGEyYi1iNmM1LWYwMDkzOWM0ZjBhYyJ9.Vwyh0EC2Y0kzj28hUZDHuZLKqwBS4Y5rmIoIrVTljtQ",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "Origin": "http://localhost:3002",
    "Referer": "http://localhost:3002/"
}

# 准备文件数据
file_content = "9"
files = {
    "file": ("../../../app/backend/111", file_content, "application/json")
}

# 发送POST请求
response = requests.post(url, headers=headers, files=files)
print(response.status_code)
print(response.text)