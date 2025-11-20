# AD Agent API Service

AI-powered advertising video generation service with RESTful API.

## 快速开始

### 1. 安装依赖

```bash
cd backend/service
uv pip install -e .
```

### 2. 配置环境变量

创建 `.env` 文件(参考 `backend/workflow/.env`):

```bash
# 复制 workflow 的环境变量
cp ../workflow/.env .env
```

可选配置项：

```bash
# 最大并发任务数（默认为 5）
MAX_CONCURRENT_TASKS=5
```

> **注意**: `MAX_CONCURRENT_TASKS` 用于限制同时执行的任务数量，避免一次性耗光服务提供者的 token。如果当前运行的任务数已达到上限，创建新任务的请求将返回 HTTP 429 错误。

### 3. 启动服务

```bash
python run.py
```

服务将在 `http://localhost:8000` 启动。

### 4. 查看 API 文档

启动后访问:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 端点

### 创建任务

```bash
curl -X POST http://localhost:8000/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "product_name": "Polaroid Camera",
    "brand_identity": "Nostalgia, Artistic, Instant Sharing",
    "must_have_shots": "Friends sharing photos, Camera close-up",
    "product_images": "https://example.com/polaroid.jpg",
    "video_format": "16:9",
    "max_shots": 5
  }'
```

响应:
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

### 查询任务(非流式)

```bash
curl http://localhost:8000/v1/tasks/123e4567-e89b-12d3-a456-426614174000
```

### 查询任务(流式 SSE)

```bash
curl -N http://localhost:8000/v1/tasks/123e4567-e89b-12d3-a456-426614174000?stream=true
```

### 取消任务

```bash
curl -X POST http://localhost:8000/v1/tasks/123e4567-e89b-12d3-a456-426614174000/cancel
```

## 架构说明

```
service/
├── main.py                 # FastAPI 应用和路由
├── models.py               # Pydantic 数据模型
├── database.py             # SQLite 数据库操作
├── task_manager.py         # 任务管理器(异步执行)
├── workflow_executor.py    # Workflow 执行器
├── run.py                  # 启动脚本
└── pyproject.toml          # 项目依赖
```

### 关键特性

1. **异步任务管理**: 使用线程池执行长时间运行的 workflow
2. **并发限制**: 可配置的并发任务数量限制，防止资源耗尽
3. **SQLite 持久化**: 任务状态和内容块存储在 SQLite 数据库
4. **SSE 流式输出**: 支持实时推送任务进度和内容
5. **任务取消**: 支持取消正在运行的任务
6. **内容拦截**: 自动记录 LLM 输出和工具调用

### 数据库 Schema

#### tasks 表
```sql
CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    stage TEXT NOT NULL,
    product_name TEXT NOT NULL,
    brand_identity TEXT NOT NULL,
    must_have_shots TEXT NOT NULL,
    product_images TEXT NOT NULL,
    video_format TEXT NOT NULL,
    max_shots INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    error_message TEXT,
    final_video_url TEXT,
    final_video_with_bgm_url TEXT
);
```

#### contents 表
```sql
CREATE TABLE contents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    content_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    data_json TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
);
```

## 开发

### 运行测试

```bash
pytest
```

### 代码风格

```bash
ruff check .
ruff format .
```

## 生产部署

### 使用 Docker

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN pip install -e .

CMD ["uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 使用 systemd

创建 `/etc/systemd/system/ad-agent.service`:

```ini
[Unit]
Description=AD Agent API Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/ad-agent/backend/service
ExecStart=/usr/bin/python3 run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务:
```bash
sudo systemctl enable ad-agent
sudo systemctl start ad-agent
```

## 许可证

Copyright © 2025 AD Agent. All rights reserved.

