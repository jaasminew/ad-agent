# AD Agent - AI驱动的广告视频生成系统

> 一个借助智能规划、参考检索与迭代视觉润色,将脚本化为电影级商业广告的视频智能体系统

## 🌟 项目概述

AD Agent 是一个全栈 AI 应用,结合 LangGraph 工作流编排和现代 Web 技术,实现从产品描述到完整广告视频的自动化生成流程。

### 核心特性

- ✅ **智能脚本生成** - 基于品牌定位自动生成广告脚本
- ✅ **AI 分镜设计** - 生成符合品牌调性的视觉分镜
- ✅ **视频自动生成** - 调用 AI 视频模型生成高质量素材
- ✅ **智能拼接** - 自动剪辑和转场处理
- ✅ **BGM 生成** - 定制化背景音乐创作
- ✅ **实时进度跟踪** - 流式更新工作流进度
- ✅ **双语支持** - 中英文界面切换
- ✅ **响应式设计** - 桌面和移动端适配

## 📁 项目结构

```
ad-agent/
├── backend/                    # 后端服务
│   ├── main.py                # FastAPI 服务入口
│   ├── service/               # API 服务层
│   │   ├── app.py            # FastAPI 应用
│   │   ├── models.py         # 数据模型
│   │   ├── database.py       # SQLite 数据库
│   │   ├── task_manager.py   # 任务管理
│   │   └── workflow_executor.py  # 工作流执行器
│   ├── agent/                 # AI Agents
│   │   ├── script_gen_agent/
│   │   └── storyboard_gen_agent/
│   └── workflow/              # LangGraph 工作流
│       ├── main.py
│       ├── workers/           # 工作流节点
│       └── tools/             # 工具函数
│
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── App.tsx           # 主应用组件
│   │   ├── services/api.ts   # API 客户端
│   │   ├── store/            # Zustand 状态管理
│   │   ├── components/ui/    # Shadcn UI 组件
│   │   └── locales.ts        # 国际化
│   ├── package.json
│   └── vite.config.ts
│
├── start.sh                    # 一键启动脚本
├── INTEGRATION.md              # 前后端对接文档
└── README.md                   # 本文档
```

## 🚀 快速开始

### 前置要求

- **Python** >= 3.10
- **Node.js** >= 18
- **uv** (Python 包管理器)
- **API Keys**:
  - Anthropic API Key (Claude)
  - Midjourney API Key
  - 其他视频/音频 API

### 一键启动 (推荐)

```bash
# 1. 配置后端环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env 填入你的 API Keys

# 2. 一键启动前后端
./start.sh
```

启动后访问:
- 🌐 **前端界面**: http://localhost:5173
- 📡 **后端 API**: http://localhost:8000
- 📚 **API 文档**: http://localhost:8000/docs

### 分别启动

#### 后端

```bash
cd backend

# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 API Keys

# 2. 启动服务
uv run main.py
```

详见: [backend/README.md](backend/README.md)

#### 前端

```bash
cd frontend

# 配置环境变量
echo "VITE_API_BASE_URL=http://localhost:8000" > .env

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

详见: [frontend/INTEGRATION.md](frontend/INTEGRATION.md)

## 📖 文档

- **[API 文档 (中文)](API_zh.md)** - 完整的 API 接口说明
- **[API 文档 (English)](API_en.md)** - Complete API reference
- **[后端架构](backend/service/ARCHITECTURE.md)** - Backend architecture
- **[快速开始](backend/QUICKSTART.md)** - Backend quick start
- **[前后端对接](INTEGRATION.md)** - Frontend-Backend integration
- **[前端 UI 设计](frontend_ui_plan_zh.md)** - Frontend UI design
- **[工作流说明](workflow.md)** - Workflow documentation

## 🔧 技术栈

### 后端

- **FastAPI** - 高性能 API 框架
- **LangChain** - LLM 应用框架
- **LangGraph** - 工作流编排
- **SQLite** - 轻量级数据库
- **SSE** - Server-Sent Events 流式更新
- **Pydantic** - 数据验证

### 前端

- **React 19** - UI 框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **Tailwind CSS** - 样式框架
- **Shadcn UI** - 组件库
- **Zustand** - 状态管理
- **Lucide React** - 图标库

## 🎯 工作流程

```
用户输入
  ↓
创建任务 (POST /v1/tasks)
  ↓
┌─────────────────┐
│ 脚本生成 Agent  │ → 分析品牌定位,生成广告脚本
└─────────────────┘
  ↓
┌─────────────────┐
│ 分镜生成 Agent  │ → 根据脚本生成视觉分镜
└─────────────────┘
  ↓
┌─────────────────┐
│ 视频生成        │ → 调用 AI 模型生成视频片段
└─────────────────┘
  ↓
┌─────────────────┐
│ 视频拼接        │ → 剪辑、转场、调色
└─────────────────┘
  ↓
┌─────────────────┐
│ BGM 生成        │ → 创作并混音背景音乐
└─────────────────┘
  ↓
最终视频输出
```

整个过程通过 SSE 实时推送进度到前端。

## 🔌 API 接口

### 创建任务

```bash
POST /v1/tasks
Content-Type: application/json

{
  "product_name": "NOVA 耳机",
  "brand_identity": "科技感、未来主义",
  "must_have_shots": "产品特写, 使用场景, Logo",
  "product_images": "https://...",
  "video_format": "16:9",
  "max_shots": 6
}
```

### 流式查询

```bash
GET /v1/tasks/{task_id}?stream=true
Accept: text/event-stream
```

### 取消任务

```bash
POST /v1/tasks/{task_id}/cancel
```

完整 API 文档: http://localhost:8000/docs

## 🧪 开发

### 后端开发

```bash
cd backend

# 安装依赖
uv pip install -e .

# 运行测试
pytest

# 代码格式化
ruff check .
ruff format .
```

### 前端开发

```bash
cd frontend

# 启动开发服务器
npm run dev

# 类型检查
npm run build

# Lint
npm run lint
```

## 📦 部署

### Docker (推荐)

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d
```

### 手动部署

#### 后端

```bash
cd backend
uv pip install -e .
uvicorn service.app:app --host 0.0.0.0 --port 8000
```

#### 前端

```bash
cd frontend
npm run build
# 将 dist/ 目录部署到 Nginx/Vercel/Netlify
```

## 🐛 故障排查

### 后端无法启动

```bash
# 检查 Python 版本
python --version  # 应该 >= 3.10

# 重新安装依赖
cd backend
uv pip install -e . --force-reinstall
```

### 前端连接失败

1. 确认后端已启动: `curl http://localhost:8000/health`
2. 检查 `frontend/.env` 中的 `VITE_API_BASE_URL`
3. 查看浏览器控制台的 CORS 错误

### 端口被占用

```bash
# 查找占用端口的进程
lsof -ti:8000 | xargs kill -9  # 后端
lsof -ti:5173 | xargs kill -9  # 前端
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request!

## 📄 许可证

Copyright © 2025 AD Agent. All rights reserved.

---

## 🎉 开始使用

```bash
# 一键启动
./start.sh

# 然后在浏览器打开
# http://localhost:5173
```

尽情体验 AI 驱动的广告视频生成! 🚀

