# AD Agent API 服务 - 快速开始

## 📋 目录

1. [安装](#安装)
2. [启动服务](#启动服务)
3. [API 使用示例](#api-使用示例)
4. [测试客户端](#测试客户端)
5. [架构说明](#架构说明)

---

## 🚀 安装

### 前置要求

- Python 3.10+
- uv (推荐) 或 pip

### 安装步骤

```bash
# 1. 进入 service 目录
cd backend/service

# 2. 安装依赖 (使用 uv)
uv pip install -e .

# 或使用 pip
pip install -e .
```

---

## ▶️ 启动服务

### 1. 配置环境变量

创建 `.env` 文件(复制 workflow 的配置):

```bash
cp ../workflow/.env .env
```

确保包含以下配置:
```env
# Anthropic API Key (用于 LLM)
ANTHROPIC_API_KEY=your_key_here

# MidJourney API
MIDJOURNEY_API_URL=...
MIDJOURNEY_API_KEY=...

# 并发任务限制(可选,默认为 5)
MAX_CONCURRENT_TASKS=5

# 其他服务配置...
```

> **注意**: `MAX_CONCURRENT_TASKS` 用于限制同时执行的任务数量，避免一次性耗光服务提供者的 token。如果当前运行的任务数已达到上限，创建新任务的请求将返回 HTTP 429 错误。

### 2. 启动服务

```bash
python run.py
```

服务将在 `http://localhost:8000` 启动。

### 3. 访问 API 文档

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 📝 API 使用示例

### 1. 创建任务

**请求:**

```bash
curl -X POST http://localhost:8000/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "product_name": "Polaroid Camera",
    "brand_identity": "Nostalgia, Artistic, Instant Sharing",
    "must_have_shots": "Friends sharing photos, Camera close-up",
    "product_images": "https://m.media-amazon.com/images/I/71a0-JzaiEL._AC_SL1500_.jpg",
    "video_format": "16:9",
    "max_shots": 3
  }'
```

**响应:**

```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

### 2. 查询任务(非流式)

**请求:**

```bash
curl http://localhost:8000/v1/tasks/123e4567-e89b-12d3-a456-426614174000
```

**响应:**

```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "stage": "script_gen_agent",
  "status": "processing",
  "contents": [
    {
      "type": "llm_output",
      "timestamp": "2025-11-18T12:00:00Z",
      "data": {
        "stage": "script_gen_agent",
        "message": "Generated 3 shots for Polaroid Camera",
        "output": {
          "shots": [
            {"shot_number": 1, "description": "Friends gathering..."},
            {"shot_number": 2, "description": "Close-up of camera..."},
            {"shot_number": 3, "description": "Photo sharing moment..."}
          ],
          "total_shots": 3
        }
      }
    }
  ]
}
```

### 3. 查询任务(流式 SSE)

**请求:**

```bash
curl -N http://localhost:8000/v1/tasks/123e4567-e89b-12d3-a456-426614174000?stream=true
```

**响应 (Server-Sent Events):**

```
event: update
data: {"stage": "script_gen_agent", "status": "processing"}

event: content
data: {"type": "llm_output", "timestamp": "2025-11-18T12:00:00Z", "data": {...}}

event: content
data: {"type": "tool_calling", "timestamp": "2025-11-18T12:00:05Z", "data": {...}}

event: complete
data: {"task_id": "123e4567-e89b-12d3-a456-426614174000", "status": "completed"}
```

### 4. 取消任务

**请求:**

```bash
curl -X POST http://localhost:8000/v1/tasks/123e4567-e89b-12d3-a456-426614174000/cancel
```

**响应:**

```json
{
  "success": true,
  "message": "Task cancellation initiated"
}
```

---

## 🧪 测试客户端

我们提供了一个 Python 测试客户端来演示如何使用 API。

### 非流式查询

```bash
python test_client.py non_streaming
```

### 流式查询 (SSE)

```bash
python test_client.py streaming
```

### 取消任务

```bash
python test_client.py cancel
```

### Python 代码示例

```python
from test_client import ADAgentClient

# 创建客户端
client = ADAgentClient()

# 创建任务
task_id = client.create_task(
    product_name="Polaroid Camera",
    brand_identity="Nostalgia, Artistic, Instant Sharing",
    must_have_shots="Friends sharing photos",
    product_images="https://example.com/image.jpg",
    video_format="16:9",
    max_shots=3,
)

# 流式接收更新
for event in client.stream_task(task_id):
    event_type = event["event"]
    data = event["data"]
    
    if event_type == "content":
        print(f"收到内容: {data['type']}")
    elif event_type == "complete":
        print("任务完成!")
        break
```

---

## 🏗️ 架构说明

### 整体架构

```
┌─────────────┐
│   Client    │
│  (Frontend) │
└──────┬──────┘
       │ HTTP/SSE
       ↓
┌─────────────────────────────────────┐
│         FastAPI Service             │
│  ┌──────────────────────────────┐  │
│  │   API Routes (main.py)       │  │
│  └────────────┬─────────────────┘  │
│               ↓                     │
│  ┌──────────────────────────────┐  │
│  │  TaskManager                 │  │
│  │  - 异步任务执行              │  │
│  │  - 线程管理                  │  │
│  │  - 内容记录                  │  │
│  └────────────┬─────────────────┘  │
│               ↓                     │
│  ┌──────────────────────────────┐  │
│  │  WorkflowExecutor            │  │
│  │  - 执行 LangGraph workflow   │  │
│  │  - 拦截和记录输出            │  │
│  └────────────┬─────────────────┘  │
│               ↓                     │
│  ┌──────────────────────────────┐  │
│  │  Database (SQLite)           │  │
│  │  - tasks 表                  │  │
│  │  - contents 表               │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

### 核心组件

#### 1. **FastAPI 应用 (main.py)**
- 定义 RESTful API 端点
- 处理 HTTP 请求/响应
- 提供 SSE 流式支持

#### 2. **任务管理器 (task_manager.py)**
- 创建和管理异步任务
- 使用线程池执行 workflow
- 实现任务取消机制
- 记录内容块到数据库

#### 3. **数据库层 (database.py)**
- SQLite 数据库操作
- 任务 CRUD
- 内容块存储和查询

#### 4. **Workflow 执行器 (workflow_executor.py)**
- 集成现有的 LangGraph workflow
- 拦截和记录各阶段输出
- 检查任务取消状态

#### 5. **数据模型 (models.py)**
- Pydantic 模型定义
- API 请求/响应模型
- 数据库记录模型

### 工作流程

1. **客户端发起请求** → 调用 `POST /v1/tasks`
2. **创建任务记录** → 在数据库中创建任务
3. **启动后台线程** → TaskManager 启动异步执行
4. **执行 Workflow** → WorkflowExecutor 调用 LangGraph
5. **记录内容块** → 每个阶段的输出记录到数据库
6. **客户端查询** → 通过轮询或 SSE 获取更新
7. **任务完成** → 更新状态为 completed/failed

### 数据库 Schema

#### tasks 表

| 字段 | 类型 | 说明 |
|------|------|------|
| task_id | TEXT | 主键,UUID |
| status | TEXT | created/processing/completed/failed/cancelled |
| stage | TEXT | 当前阶段 |
| product_name | TEXT | 产品名称 |
| brand_identity | TEXT | 品牌定位 |
| must_have_shots | TEXT | 必需镜头 |
| product_images | TEXT | 产品图片 URL |
| video_format | TEXT | 视频格式 |
| max_shots | INTEGER | 最大镜头数 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |
| error_message | TEXT | 错误信息(可选) |
| final_video_url | TEXT | 最终视频 URL(可选) |
| final_video_with_bgm_url | TEXT | 带 BGM 的视频 URL(可选) |

#### contents 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键,自增 |
| task_id | TEXT | 外键 → tasks.task_id |
| content_type | TEXT | llm_output/tool_calling |
| timestamp | TEXT | ISO 8601 时间戳 |
| data_json | TEXT | JSON 数据 |
| created_at | TIMESTAMP | 创建时间 |

---

## 🔧 开发和调试

### 查看日志

服务会输出详细日志:

```
2025-11-18 12:00:00 [INFO] service.main - ✓ Service started successfully
2025-11-18 12:00:01 [INFO] service.task_manager - ✓ Task created and started: 123e4567...
2025-11-18 12:00:05 [INFO] service.workflow_executor - [Task 123e4567] Stage 1: Script Generation
```

### 查看数据库

```bash
sqlite3 ad_agent.db

# 查看任务
SELECT task_id, status, stage FROM tasks;

# 查看内容块
SELECT task_id, content_type, timestamp FROM contents;
```

### 测试 API

```bash
# 健康检查
curl http://localhost:8000/health

# API 信息
curl http://localhost:8000/
```

---

## 📚 相关文档

- [API 完整文档](../../API_zh.md)
- [Workflow 说明](../workflow/README.md)
- [Agent 文档](../agent/README.md)

---

## ⚠️ 注意事项

1. **SQLite 限制**: 默认使用 SQLite,适合开发和小规模部署。生产环境建议使用 PostgreSQL。

2. **并发限制**: 通过 `MAX_CONCURRENT_TASKS` 环境变量配置(默认5)。超过限制时,新任务请求将返回 HTTP 429 错误。可以使用 Celery 等任务队列进一步扩展。

3. **内容存储**: 所有内容块都存储在数据库中,大规模使用时注意数据库大小。

4. **取消机制**: 任务取消是协作式的,只在检查点生效,不是立即终止。

---

## 🚀 下一步

- 集成前端 UI
- 添加用户认证
- 部署到生产环境
- 监控和告警

祝使用愉快! 🎉

