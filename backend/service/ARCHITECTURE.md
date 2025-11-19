"""
AD Agent 后端服务完整实现总结

本文档说明了如何将 LangGraph workflow 服务化,实现完整的 RESTful API。
"""

# ============================================================================
# 项目结构
# ============================================================================

backend/
├── service/                          # 🆕 API 服务目录
│   ├── __init__.py                  # 包初始化
│   ├── main.py                      # FastAPI 应用和路由
│   ├── models.py                    # Pydantic 数据模型
│   ├── database.py                  # SQLite 数据库操作
│   ├── task_manager.py              # 任务管理器(异步执行)
│   ├── workflow_executor.py         # Workflow 执行器
│   ├── run.py                       # 启动脚本
│   ├── test_client.py              # 测试客户端
│   ├── pyproject.toml              # 项目依赖
│   ├── README.md                    # 项目说明
│   └── QUICKSTART.md               # 快速开始指南
│
├── workflow/                         # 现有的 workflow
│   ├── main.py
│   ├── workers/
│   └── ...
│
└── agent/                           # 现有的 agents
    ├── script_gen_agent/
    ├── storyboard_gen_agent/
    └── ...


# ============================================================================
# 核心设计决策
# ============================================================================

## 1. 任务 ID 管理

❌ 不复用 LangChain 的执行 ID
✅ 创建独立的 UUID 作为 task_id

原因:
- LangGraph 没有持久化的任务 ID
- 不支持异步和长时间运行
- 不支持任务取消和状态查询

## 2. 数据库选择

✅ SQLite (开发和小规模部署)
- 零配置
- 文件存储
- 适合单机部署

🔄 可升级到 PostgreSQL (生产环境)
- 修改 database.py 中的连接字符串即可
- 保持相同的接口

## 3. 任务执行模式

✅ 线程池 + 后台执行
- 简单实用
- 适合中小规模
- 支持取消和状态查询

🔄 可升级到 Celery (大规模)
- 分布式任务队列
- 更强的容错能力
- 支持横向扩展

## 4. 内容记录机制

✅ 拦截式记录
- 在 workflow_executor.py 中拦截每个阶段的输出
- 自动记录 LLM 输出和工具调用
- 存储到 SQLite 数据库

特点:
- 对现有 workflow 无侵入
- 易于扩展和修改
- 支持流式推送


# ============================================================================
# API 端点实现
# ============================================================================

## 1. POST /v1/tasks - 创建任务 ✅

实现位置: service/main.py:create_task()

流程:
1. 接收 CreateTaskRequest
2. 生成 UUID 作为 task_id
3. 在数据库中创建任务记录
4. 启动后台线程执行 workflow
5. 立即返回 task_id

关键代码:
```python
task_id = task_manager.create_task(request)
# TaskManager 会:
# 1. 创建数据库记录
# 2. 创建取消标志
# 3. 启动后台线程
```

## 2. GET /v1/tasks/{task_id} - 查询任务 ✅

实现位置: service/main.py:get_task()

支持两种模式:

### 非流式 (stream=false)
- 返回当前状态快照
- 包含所有已生成的内容块

### 流式 (stream=true)
- Server-Sent Events (SSE)
- 实时推送新内容
- 自动检测任务完成

关键代码:
```python
if stream:
    return StreamingResponse(_stream_task_updates(task_id), ...)
else:
    return task_manager.get_task_status(task_id)
```

## 3. POST /v1/tasks/{task_id}/cancel - 取消任务 ✅

实现位置: service/main.py:cancel_task()

取消机制:
1. 设置 threading.Event 标志
2. workflow_executor 在各阶段检查标志
3. 如果已取消,抛出 TaskCancelledException
4. TaskManager 捕获异常并更新状态

特点:
- 协作式取消(不是强制终止)
- 只在检查点生效
- 安全且可靠

## 4. POST /v1/tasks/{task_id}/assessment - 评估 ✅

实现位置: service/main.py:submit_assessment()

当前实现:
- 接收评估请求
- 记录到日志
- 返回成功响应

TODO:
- 可以扩展为反馈机制
- 用于人工审核流程


# ============================================================================
# 数据库设计
# ============================================================================

## tasks 表 - 任务主表

字段说明:
- task_id: UUID,主键
- status: created/processing/completed/failed/cancelled
- stage: 当前执行阶段
- product_name, brand_identity, etc: 任务参数
- created_at, updated_at: 时间戳
- error_message: 失败时的错误信息
- final_video_url: 最终视频 URL
- final_video_with_bgm_url: 带 BGM 的视频 URL

索引:
- PRIMARY KEY (task_id)
- INDEX (status) - 用于查询运行中的任务

## contents 表 - 内容块表

字段说明:
- id: 自增主键
- task_id: 外键 → tasks.task_id
- content_type: llm_output / tool_calling
- timestamp: ISO 8601 时间戳
- data_json: JSON 格式的数据
- created_at: 创建时间

索引:
- PRIMARY KEY (id)
- INDEX (task_id) - 用于查询任务的所有内容
- FOREIGN KEY (task_id)

特点:
- 有序存储(通过 id 自增)
- 支持增量查询(id > last_id)
- 适合流式推送


# ============================================================================
# 内容拦截机制
# ============================================================================

## 实现位置: workflow_executor.py

### 拦截点

1. **脚本生成阶段** (script_gen_agent)
   - 记录生成的镜头列表
   - 记录推理过程

2. **故事板生成阶段** (storyboard_gen_agent)
   - 记录每个 beat 的结果
   - 记录图片生成和产品替换

3. **视频生成阶段** (video_generator)
   - 记录每个视频的生成
   - 记录视频 URL

4. **视频拼接阶段** (video_concatenater)
   - 记录最终视频 URL
   - 记录视频时长

5. **BGM 生成阶段** (bgm_generator)
   - 记录音乐生成
   - 记录最终带 BGM 的视频

### 记录方式

```python
# LLM 输出
task_manager.add_llm_output(
    task_id=task_id,
    stage=stage,
    message="Generated 3 shots",
    output={"shots": [...], "total_shots": 3},
    reasoning="Analyzed brand identity...",
)

# 工具调用
task_manager.add_tool_calling(
    task_id=task_id,
    stage=stage,
    tool_name="midjourney_imagine",
    input_data={"prompt": "..."},
    output_data={"image_url": "..."},
    success=True,
)
```


# ============================================================================
# 流式推送实现
# ============================================================================

## Server-Sent Events (SSE)

实现位置: service/main.py:_stream_task_updates()

### 流程:

1. **发送初始状态**
   ```
   event: update
   data: {"stage": "script_gen_agent", "status": "processing"}
   ```

2. **发送已有内容**
   ```
   event: content
   data: {"type": "llm_output", "timestamp": "...", "data": {...}}
   ```

3. **持续推送新内容**
   - 每秒查询一次数据库
   - 使用 `get_contents_after(last_id)` 获取增量
   - 推送新内容块

4. **发送完成事件**
   ```
   event: complete
   data: {"task_id": "...", "status": "completed"}
   ```

### 优点:

- ✅ 实时推送,低延迟
- ✅ 自动重连(浏览器原生支持)
- ✅ 简单易用(比 WebSocket 简单)
- ✅ 单向通信(适合进度推送)


# ============================================================================
# 任务取消机制
# ============================================================================

## 实现位置: task_manager.py + workflow_executor.py

### 取消流程:

1. **客户端调用** POST /v1/tasks/{task_id}/cancel

2. **设置取消标志**
   ```python
   self.cancel_flags[task_id].set()  # threading.Event
   ```

3. **Workflow 检查**
   ```python
   def _check_cancelled(task_manager, task_id):
       if task_manager.is_cancelled(task_id):
           raise TaskCancelledException()
   ```

4. **更新状态**
   ```python
   except TaskCancelledException:
       db.update_task_status(task_id, TaskStatus.CANCELLED)
   ```

### 特点:

- ✅ 协作式取消(安全)
- ✅ 在每个阶段开始前检查
- ✅ 不会破坏数据一致性
- ⚠️ 不是立即终止


# ============================================================================
# 使用示例
# ============================================================================

## 启动服务

```bash
cd backend/service
python run.py
```

## 创建任务

```bash
curl -X POST http://localhost:8000/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "product_name": "Polaroid Camera",
    "brand_identity": "Nostalgia, Artistic",
    "must_have_shots": "Friends sharing photos",
    "product_images": "https://example.com/image.jpg",
    "video_format": "16:9",
    "max_shots": 3
  }'
```

## 流式查询

```bash
curl -N http://localhost:8000/v1/tasks/{task_id}?stream=true
```

## 使用 Python 客户端

```python
from test_client import ADAgentClient

client = ADAgentClient()
task_id = client.create_task(...)

for event in client.stream_task(task_id):
    print(event)
```


# ============================================================================
# 扩展和优化建议
# ============================================================================

## 短期优化

1. **添加工具调用拦截**
   - 在 Agent 的工具调用中添加钩子
   - 记录每个工具的输入/输出

2. **优化内容记录**
   - 添加更详细的推理过程
   - 记录中间结果(如 MidJourney 的 4 张图)

3. **添加认证**
   - API Key 认证
   - JWT Token

4. **添加速率限制**
   - 防止滥用
   - 保护资源

## 长期优化

1. **切换到 PostgreSQL**
   - 更好的并发性能
   - 更强的事务支持

2. **使用 Celery**
   - 分布式任务队列
   - 更强的容错能力
   - 支持优先级队列

3. **添加缓存**
   - Redis 缓存任务状态
   - 减少数据库查询

4. **添加监控**
   - Prometheus + Grafana
   - 任务成功率、执行时间等指标

5. **添加 WebSocket**
   - 双向通信
   - 支持交互式反馈


# ============================================================================
# 总结
# ============================================================================

✅ 完成的工作:

1. 设计了完整的数据库 schema
2. 实现了 TaskManager 异步任务管理
3. 实现了所有 API 端点
4. 集成了现有的 LangGraph workflow
5. 实现了内容拦截和记录机制
6. 实现了任务取消功能
7. 实现了 SSE 流式推送
8. 提供了测试客户端和文档

📝 核心特性:

- ✅ 异步任务执行
- ✅ SQLite 持久化
- ✅ 实时流式推送
- ✅ 任务取消支持
- ✅ 完整的 API 文档
- ✅ 易于扩展

🚀 可以直接使用:

```bash
cd backend/service
python run.py
```

访问 http://localhost:8000/docs 查看 API 文档!
"""

