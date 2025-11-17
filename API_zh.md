# AD Agent API 文档

版本: 1.0.0  
最后更新: 2025-11-17

## 概述

AD Agent API 是一个 RESTful 服务,利用 AI 代理自动生成广告视频。它提供异步任务管理,支持实时进度追踪和可流式传输的输出。

### 基础 URL

```
生产环境: https://api.ad-agent.example.com/v1
开发环境: http://localhost:8000/v1
```

### 身份验证

所有 API 请求必须在请求头中包含 API 密钥:

```http
Authorization: Bearer YOUR_API_KEY
```

---

## API 端点

### 1. 创建任务(异步)

创建一个新的广告视频生成任务。这是一个异步操作,会立即返回任务 ID。

**端点:** `POST /tasks`

**请求体:**

```json
{
  "product_name": "string",
  "brand_identity": "string",
  "must_have_shots": "string",
  "product_images": "string",
  "video_format": "string",
  "max_shots": "integer"
}
```

**参数:**

| 参数 | 类型 | 必需 | 描述 |
|-----|------|------|------|
| `product_name` | string | 是 | 要宣传的产品名称 |
| `brand_identity` | string | 是 | 品牌定位和身份(例如 "怀旧, 艺术, 即时分享") |
| `must_have_shots` | string | 是 | 必须包含的镜头描述(逗号分隔,例如 "朋友们分享照片, 相机特写") |
| `product_images` | string | 是 | 产品图片的 URL |
| `video_format` | string | 是 | 视频纵横比(例如 "16:9", "9:16", "1:1") |
| `max_shots` | integer | 是 | 要生成的最大镜头数 |

**响应:** `201 Created`

```json
{
  "task_id": "string"
}
```

**响应字段:**

| 字段 | 类型 | 描述 |
|-----|------|------|
| `task_id` | string | 创建的任务的唯一标识符(UUID 格式) |

**请求示例:**

```bash
curl -X POST https://api.ad-agent.example.com/v1/tasks \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "product_name": "宝丽来相机",
    "brand_identity": "怀旧, 艺术, 即时分享",
    "must_have_shots": "朋友们分享照片, 相机特写",
    "product_images": "https://example.com/polaroid.jpg",
    "video_format": "16:9",
    "max_shots": 5
  }'
```

**响应示例:**

```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**错误响应:**

| 状态码 | 描述 |
|--------|------|
| `400 Bad Request` | 输入参数无效(缺少必需字段或值无效) |
| `401 Unauthorized` | 缺少或无效的 API 密钥 |
| `500 Internal Server Error` | 服务器错误 |

---

### 2. 取消任务(异步)

取消正在运行的任务。这是一个异步操作。

**端点:** `POST /tasks/{task_id}/cancel`

**参数:**

| 参数 | 类型 | 必需 | 描述 |
|-----|------|------|------|
| `task_id` | string | 是 | 任务标识符(路径参数) |

**请求体:**

无需提供。

**响应:** `200 OK`

```json
{
  "success": true,
  "message": "任务取消已启动"
}
```

**请求示例:**

```bash
curl -X POST https://api.ad-agent.example.com/v1/tasks/123e4567-e89b-12d3-a456-426614174000/cancel \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**响应示例:**

```json
{
  "success": true,
  "message": "任务取消已启动"
}
```

**错误响应:**

| 状态码 | 描述 |
|--------|------|
| `404 Not Found` | 未找到任务 |
| `400 Bad Request` | 任务无法取消(已完成或失败) |
| `401 Unauthorized` | 缺少或无效的 API 密钥 |
| `500 Internal Server Error` | 服务器错误 |

---

### 3. 查询任务

查询任务的当前状态和结果。支持流式输出以获取实时更新。

**端点:** `GET /tasks/{task_id}`

**参数:**

| 参数 | 类型 | 必需 | 描述 |
|-----|------|------|------|
| `task_id` | string | 是 | 任务标识符(路径参数) |
| `stream` | boolean | 否 | 启用流式响应以获取实时更新(查询参数) |

**响应:** `200 OK`

```json
{
  "task_id": "string",
  "stage": "string",
  "status": "string",
  "contents": [
    {
      "type": "string",
      "timestamp": "string",
      "data": "object"
    }
  ]
}
```

**响应字段:**

| 字段 | 类型 | 描述 |
|-----|------|------|
| `task_id` | string | 任务标识符 |
| `stage` | string | 当前处理阶段(见下方阶段值) |
| `status` | string | 任务状态: "created", "processing", "completed", "failed", "cancelled" |
| `contents` | array | 有序的处理块列表(可流式传输,见下方内容块) |

**阶段值:**

| 阶段 | 描述 |
|-----|------|
| `script_gen_agent` | 使用脚本生成 Agent 生成广告脚本 |
| `storyboard_gen_agent` | 使用分镜图 Agent 创建分镜图像并进行产品合成 |
| `video_generator` | 从图片生成视频 |
| `video_concatenater` | 拼接视频片段 |
| `bgm_generator` | 生成并添加背景音乐 |
| `completed` | 所有处理完成 |

#### 内容块

`contents` 数组包含有序的处理块。每个块代表工作流中的一个步骤。有两种类型的块:

##### 块类型 1: LLM 输出

```json
{
  "type": "llm_output",
  "timestamp": "2025-11-17T12:00:00Z",
  "data": {
    "stage": "string",
    "message": "string",
    "reasoning": "string",
    "output": "object"
  }
}
```

**字段:**

| 字段 | 类型 | 描述 |
|-----|------|------|
| `type` | string | 始终为 "llm_output" |
| `timestamp` | string | 输出生成时的 ISO 8601 时间戳 |
| `data.stage` | string | 此输出所属的工作流阶段 |
| `data.message` | string | 描述所做工作的人类可读消息 |
| `data.reasoning` | string | LLM 的推理过程(可选) |
| `data.output` | object | LLM 的结构化输出(特定于阶段) |

##### 块类型 2: 工具调用

```json
{
  "type": "tool_calling",
  "timestamp": "2025-11-17T12:00:05Z",
  "data": {
    "tool_name": "string",
    "stage": "string",
    "input": "object",
    "output": "object",
    "success": "boolean",
    "error": "string"
  }
}
```

**字段:**

| 字段 | 类型 | 描述 |
|-----|------|------|
| `type` | string | 始终为 "tool_calling" |
| `timestamp` | string | 工具调用时的 ISO 8601 时间戳 |
| `data.tool_name` | string | 被调用的工具名称(见下方工具规范) |
| `data.stage` | string | 调用工具时的工作流阶段 |
| `data.input` | object | 传递给工具的输入参数(特定于工具的结构) |
| `data.output` | object | 工具返回的输出(特定于工具的结构) |
| `data.success` | boolean | 工具调用是否成功 |
| `data.error` | string | 如果 success 为 false 时的错误消息(可选) |

---

## 工具规范

本节定义工作流中使用的每个工具的确切输入/输出结构。

### 脚本生成 Agent 工具

#### 1. web_search

搜索网络以获取事实/背景信息。

**输入:**
```json
{
  "query": "string"
}
```

| 字段 | 类型 | 必需 | 描述 |
|-----|------|------|------|
| `query` | string | 是 | 搜索查询字符串 |

**输出:**
```json
{
  "results": [
    {
      "title": "string",
      "url": "string",
      "content": "string"
    }
  ],
  "result_count": "integer"
}
```

| 字段 | 类型 | 描述 |
|-----|------|------|
| `results` | array | 搜索结果数组(最多 5 个) |
| `results[].title` | string | 网页标题 |
| `results[].url` | string | 网页 URL |
| `results[].content` | string | 页面摘录(最多 300 字符) |
| `result_count` | integer | 返回的结果数量 |

#### 2. remember

在会话内存中存储一条笔记。

**输入:**
```json
{
  "note": "string"
}
```

| 字段 | 类型 | 必需 | 描述 |
|-----|------|------|------|
| `note` | string | 是 | 要记住的笔记 |

**输出:**
```json
{
  "message": "string"
}
```

| 字段 | 类型 | 描述 |
|-----|------|------|
| `message` | string | 确认消息 |

#### 3. recall

从会话内存中检索笔记。

**输入:**
```json
{
  "query": "string"
}
```

| 字段 | 类型 | 必需 | 描述 |
|-----|------|------|------|
| `query` | string | 否 | 可选的搜索查询(空则返回所有笔记) |

**输出:**
```json
{
  "notes": ["string"],
  "count": "integer"
}
```

| 字段 | 类型 | 描述 |
|-----|------|------|
| `notes` | array | 存储的笔记数组 |
| `count` | integer | 检索到的笔记数量 |

---

### 分镜图生成 Agent 工具

#### 4. list_tags

列出 PixelHub 中可用的图片标签。

**输入:**
```json
{
  "page": "integer",
  "limit": "integer"
}
```

| 字段 | 类型 | 必需 | 默认值 | 描述 |
|-----|------|------|--------|------|
| `page` | integer | 否 | 1 | 分页的页码 |
| `limit` | integer | 否 | 1000 | 每页标签数(最多 1000) |

**输出:**
```json
{
  "tags": ["string"],
  "total": "integer",
  "page": "integer",
  "limit": "integer"
}
```

| 字段 | 类型 | 描述 |
|-----|------|------|
| `tags` | array | 可用标签名称数组 |
| `total` | integer | 标签总数 |
| `page` | integer | 当前页码 |
| `limit` | integer | 每页标签数 |

#### 5. search_images_by_tags

通过标签搜索图片,使用相关性排名(OR 逻辑)。

**输入:**
```json
{
  "tags": ["string"],
  "page": "integer",
  "limit": "integer"
}
```

| 字段 | 类型 | 必需 | 默认值 | 描述 |
|-----|------|------|--------|------|
| `tags` | array | 是 | - | 要搜索的标签列表(必须来自 list_tags) |
| `page` | integer | 否 | 1 | 分页的页码 |
| `limit` | integer | 否 | 20 | 每页图片数(最多 100) |

**输出:**
```json
{
  "images": [
    {
      "url": "string",
      "description": "string",
      "matched_tags": ["string"],
      "match_count": "integer"
    }
  ],
  "total": "integer",
  "page": "integer",
  "limit": "integer"
}
```

| 字段 | 类型 | 描述 |
|-----|------|------|
| `images` | array | 按相关性排序的匹配图片数组 |
| `images[].url` | string | 图片 URL |
| `images[].description` | string | 图片描述 |
| `images[].matched_tags` | array | 匹配的标签 |
| `images[].match_count` | integer | 匹配的标签数 |
| `total` | integer | 匹配图片总数 |
| `page` | integer | 当前页码 |
| `limit` | integer | 每页图片数 |

#### 6. extract_color_palette

从图片中提取主色调。

**输入:**
```json
{
  "image_url": "string"
}
```

| 字段 | 类型 | 必需 | 描述 |
|-----|------|------|------|
| `image_url` | string | 是 | 要分析的图片 URL |

**输出:**
```json
{
  "palette": [
    {
      "hex": "string",
      "rgb": [integer, integer, integer],
      "percentage": "number"
    }
  ],
  "dominant_color": "string"
}
```

| 字段 | 类型 | 描述 |
|-----|------|------|
| `palette` | array | 主色调数组(通常 5-8 种颜色) |
| `palette[].hex` | string | 十六进制颜色代码(例如 "#FF5733") |
| `palette[].rgb` | array | RGB 值 [R, G, B] |
| `palette[].percentage` | number | 图片中包含该颜色的百分比 |
| `dominant_color` | string | 最主要颜色的十六进制代码 |

#### 7. midjourney_imagine

使用 Midjourney 生成图片。

**输入:**
```json
{
  "prompt": "string"
}
```

| 字段 | 类型 | 必需 | 描述 |
|-----|------|------|------|
| `prompt` | string | 是 | 图片生成提示词(支持 Midjourney 参数如 --ar, --v 等) |

**输出:**
```json
{
  "task_id": "string",
  "status": "string",
  "image_url": "string",
  "prompt": "string"
}
```

| 字段 | 类型 | 描述 |
|-----|------|------|
| `task_id` | string | Midjourney 任务标识符 |
| `status` | string | 任务状态("completed", "failed") |
| `image_url` | string | 生成的 2x2 网格图片 URL(4 个变体) |
| `prompt` | string | 使用的提示词 |

#### 8. midjourney_upscale

放大 Midjourney 任务中的特定图片。

**输入:**
```json
{
  "task_id": "string",
  "index": "integer"
}
```

| 字段 | 类型 | 必需 | 描述 |
|-----|------|------|------|
| `task_id` | string | 是 | imagine 的 Midjourney 任务 ID |
| `index` | integer | 是 | 要放大的图片索引(1-4: 1=左上, 2=右上, 3=左下, 4=右下) |

**输出:**
```json
{
  "task_id": "string",
  "status": "string",
  "image_url": "string",
  "original_task_id": "string",
  "index": "integer"
}
```

| 字段 | 类型 | 描述 |
|-----|------|------|
| `task_id` | string | 放大任务标识符 |
| `status` | string | 任务状态("completed", "failed") |
| `image_url` | string | 放大后的图片 URL |
| `original_task_id` | string | 原始 imagine 任务 ID |
| `index` | integer | 放大图片的索引 |

#### 9. check_image_distortion

检查 AI 生成图片中的解剖失真。

**输入:**
```json
{
  "image_path": "string"
}
```

| 字段 | 类型 | 必需 | 描述 |
|-----|------|------|------|
| `image_path` | string | 是 | 图片的路径或 URL |

**输出:**
```json
{
  "has_distortion": "boolean",
  "distortion_count": "integer",
  "distortions": [
    {
      "type": "string",
      "severity": "string",
      "location": "string",
      "confidence": "number"
    }
  ],
  "passed": "boolean"
}
```

| 字段 | 类型 | 描述 |
|-----|------|------|
| `has_distortion` | boolean | 是否检测到任何失真 |
| `distortion_count` | integer | 发现的失真总数 |
| `distortions` | array | 检测到的失真数组 |
| `distortions[].type` | string | 失真类型(例如 "extra_fingers", "missing_limb") |
| `distortions[].severity` | string | 严重程度级别("low", "medium", "high") |
| `distortions[].location` | string | 图片中的位置(例如 "left_hand", "face") |
| `distortions[].confidence` | number | 检测置信度(0.0-1.0) |
| `passed` | boolean | 图片是否通过质量检查 |

#### 10. nanobanana_generate

使用 Google Gemini (Nanobanana) 生成或修改图片。

**输入:**
```json
{
  "prompt": "string",
  "input_image_paths": "string or array",
  "upload_to_cos": "boolean"
}
```

| 字段 | 类型 | 必需 | 默认值 | 描述 |
|-----|------|------|--------|------|
| `prompt` | string | 是 | - | 生成或修改提示词 |
| `input_image_paths` | string or array | 是 | - | 输入图片的路径或 URL |
| `upload_to_cos` | boolean | 否 | true | 是否将结果上传到 COS |

**输出:**
```json
{
  "image_url": "string",
  "uploaded": "boolean",
  "prompt": "string"
}
```

| 字段 | 类型 | 描述 |
|-----|------|------|
| `image_url` | string | 生成/修改后的图片 URL |
| `uploaded` | boolean | 图片是否已上传到 COS |
| `prompt` | string | 使用的提示词 |

---

### 视频生成工具

#### 11. veo_generate_video

使用 Google Veo 3 从图片生成视频。

**输入:**
```json
{
  "prompt": "string",
  "image_url": "string",
  "upload_to_cos": "boolean"
}
```

| 字段 | 类型 | 必需 | 默认值 | 描述 |
|-----|------|------|--------|------|
| `prompt` | string | 是 | - | 视频生成提示词 |
| `image_url` | string | 是 | - | 首帧图片的 URL |
| `upload_to_cos` | boolean | 否 | true | 是否将结果上传到 COS |

**输出:**
```json
{
  "video_url": "string",
  "duration": "number",
  "uploaded": "boolean",
  "prompt": "string"
}
```

| 字段 | 类型 | 描述 |
|-----|------|------|
| `video_url` | string | 生成的视频 URL |
| `duration` | number | 视频时长(秒) |
| `uploaded` | boolean | 视频是否已上传到 COS |
| `prompt` | string | 使用的提示词 |

#### 12. kling_generate_video

使用 Kling AI 生成视频。

**输入:**
```json
{
  "image_url": "string",
  "prompt": "string",
  "duration": "string",
  "mode": "string",
  "cfg_scale": "number",
  "upload_to_cos": "boolean"
}
```

| 字段 | 类型 | 必需 | 默认值 | 描述 |
|-----|------|------|--------|------|
| `image_url` | string | 是 | - | 首帧图片的 URL |
| `prompt` | string | 是 | - | 视频生成提示词 |
| `duration` | string | 否 | "5" | 视频时长: "5" 或 "10" |
| `mode` | string | 否 | "pro" | 生成模式: "std" 或 "pro" |
| `cfg_scale` | number | 否 | 0.5 | CFG 比例(0.0-1.0) |
| `upload_to_cos` | boolean | 否 | true | 是否将结果上传到 COS |

**输出:**
```json
{
  "video_url": "string",
  "duration": "number",
  "task_id": "string",
  "uploaded": "boolean"
}
```

| 字段 | 类型 | 描述 |
|-----|------|------|
| `video_url` | string | 生成的视频 URL |
| `duration` | number | 视频时长(秒) |
| `task_id` | string | Kling 任务标识符 |
| `uploaded` | boolean | 视频是否已上传到 COS |

#### 13. seedance_generate_video

使用 Seedance 生成视频。

**输入:**
```json
{
  "prompt": "string",
  "image_url": "string",
  "resolution": "string",
  "duration": "integer",
  "camera_fixed": "boolean",
  "upload_to_cos": "boolean"
}
```

| 字段 | 类型 | 必需 | 默认值 | 描述 |
|-----|------|------|--------|------|
| `prompt` | string | 是 | - | 视频生成提示词 |
| `image_url` | string | 否 | null | 可选的首帧图片 URL |
| `resolution` | string | 否 | "1080p" | 视频分辨率: "720p", "1080p" |
| `duration` | integer | 否 | 5 | 视频时长(秒, 5-10) |
| `camera_fixed` | boolean | 否 | false | 是否固定相机位置 |
| `upload_to_cos` | boolean | 否 | true | 是否将结果上传到 COS |

**输出:**
```json
{
  "video_url": "string",
  "duration": "integer",
  "resolution": "string",
  "uploaded": "boolean"
}
```

| 字段 | 类型 | 描述 |
|-----|------|------|
| `video_url` | string | 生成的视频 URL |
| `duration` | integer | 视频时长(秒) |
| `resolution` | string | 视频分辨率 |
| `uploaded` | boolean | 视频是否已上传到 COS |

---

### 音乐生成工具

#### 14. suno_generate_music

使用 Suno AI 生成背景音乐。

**输入:**
```json
{
  "prompt": "string",
  "style": "string",
  "duration": "integer",
  "instrumental": "boolean"
}
```

| 字段 | 类型 | 必需 | 默认值 | 描述 |
|-----|------|------|--------|------|
| `prompt` | string | 是 | - | 音乐生成提示词 |
| `style` | string | 否 | "" | 音乐风格(例如 "电子", "古典") |
| `duration` | integer | 否 | 30 | 音乐时长(秒) |
| `instrumental` | boolean | 否 | true | 是否生成纯音乐(无人声) |

**输出:**
```json
{
  "music_url": "string",
  "duration": "integer",
  "style": "string",
  "task_id": "string"
}
```

| 字段 | 类型 | 描述 |
|-----|------|------|
| `music_url` | string | 生成的音乐 URL |
| `duration` | integer | 音乐时长(秒) |
| `style` | string | 生成的音乐风格 |
| `task_id` | string | Suno 任务标识符 |

---

## 响应示例

**请求示例:**

```bash
curl -X GET https://api.ad-agent.example.com/v1/tasks/123e4567-e89b-12d3-a456-426614174000 \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**响应示例:**

```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "stage": "video_generator",
  "status": "processing",
  "contents": [
    {
      "type": "llm_output",
      "timestamp": "2025-11-17T12:00:00Z",
      "data": {
        "stage": "script_gen_agent",
        "message": "为宝丽来相机生成了 5 个镜头",
        "reasoning": "分析了品牌定位,强调怀旧和即时分享",
        "output": {
          "shots": [
            {
              "shot_number": 1,
              "description": "朋友们围在一起,笑着分享即时照片"
            },
            {
              "shot_number": 2,
              "description": "手拿着刚打印的宝丽来照片的特写"
            }
          ],
          "total_shots": 5
        }
      }
    },
    {
      "type": "tool_calling",
      "timestamp": "2025-11-17T12:01:30Z",
      "data": {
        "tool_name": "web_search",
        "stage": "script_gen_agent",
        "input": {
          "query": "宝丽来相机即时摄影趋势 2025"
        },
        "output": {
          "results": [
            {
              "title": "2025 年即时摄影的回归",
              "url": "https://example.com/article",
              "content": "即时摄影正在年轻一代中卷土重来..."
            }
          ],
          "result_count": 5
        },
        "success": true
      }
    },
    {
      "type": "tool_calling",
      "timestamp": "2025-11-17T12:05:30Z",
      "data": {
        "tool_name": "midjourney_imagine",
        "stage": "storyboard_gen_agent",
        "input": {
          "prompt": "朋友们围在一起,笑着分享即时照片,怀旧氛围,温暖的灯光 --ar 16:9 --v 6"
        },
        "output": {
          "task_id": "mj_abc123",
          "status": "completed",
          "image_url": "https://cdn.example.com/mj_abc123.jpg",
          "prompt": "朋友们围在一起,笑着分享即时照片,怀旧氛围,温暖的灯光 --ar 16:9 --v 6"
        },
        "success": true
      }
    },
    {
      "type": "tool_calling",
      "timestamp": "2025-11-17T12:08:15Z",
      "data": {
        "tool_name": "check_image_distortion",
        "stage": "storyboard_gen_agent",
        "input": {
          "image_path": "https://cdn.example.com/mj_abc123.jpg"
        },
        "output": {
          "has_distortion": false,
          "distortion_count": 0,
          "distortions": [],
          "passed": true
        },
        "success": true
      }
    },
    {
      "type": "tool_calling",
      "timestamp": "2025-11-17T12:10:45Z",
      "data": {
        "tool_name": "nanobanana_generate",
        "stage": "storyboard_gen_agent",
        "input": {
          "prompt": "将通用相机替换为这款宝丽来相机产品,保持自然放置",
          "input_image_paths": "https://cdn.example.com/mj_abc123.jpg",
          "upload_to_cos": true
        },
        "output": {
          "image_url": "https://cos.example.com/final_shot1.jpg",
          "uploaded": true,
          "prompt": "将通用相机替换为这款宝丽来相机产品,保持自然放置"
        },
        "success": true
      }
    },
    {
      "type": "tool_calling",
      "timestamp": "2025-11-17T12:15:20Z",
      "data": {
        "tool_name": "kling_generate_video",
        "stage": "video_generator",
        "input": {
          "image_url": "https://cos.example.com/final_shot1.jpg",
          "prompt": "相机慢慢拉近朋友们,他们抬头看向镜头并微笑",
          "duration": "5",
          "mode": "pro",
          "cfg_scale": 0.5,
          "upload_to_cos": true
        },
        "output": {
          "video_url": "https://cos.example.com/video_shot1.mp4",
          "duration": 5,
          "task_id": "kling_xyz789",
          "uploaded": true
        },
        "success": true
      }
    }
  ]
}
```

**流式响应:**

启用流式传输以实时接收更新:

```bash
curl -X GET "https://api.ad-agent.example.com/v1/tasks/123e4567-e89b-12d3-a456-426614174000?stream=true" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Accept: text/event-stream"
```

服务器发送事件(SSE)格式:
```
event: update
data: {"type": "status", "stage": "script_gen_agent", "status": "processing"}

event: content
data: {"type": "llm_output", "timestamp": "2025-11-17T12:00:00Z", "data": {...}}

event: content
data: {"type": "tool_calling", "timestamp": "2025-11-17T12:00:05Z", "data": {...}}

event: complete
data: {"task_id": "123e4567-e89b-12d3-a456-426614174000", "status": "completed"}
```

**错误响应:**

| 状态码 | 描述 |
|--------|------|
| `404 Not Found` | 未找到任务 |
| `401 Unauthorized` | 缺少或无效的 API 密钥 |
| `500 Internal Server Error` | 服务器错误 |

---

### 4. 评估

为任务的特定阶段提交反馈或评估。

**端点:** `POST /tasks/{task_id}/assessment`

**参数:**

| 参数 | 类型 | 必需 | 描述 |
|-----|------|------|------|
| `task_id` | string | 是 | 任务标识符(路径参数) |

**请求体:**

```json
{
  "task_id": "string",
  "stage": "string",
  "comment": "string"
}
```

**参数:**

| 参数 | 类型 | 必需 | 描述 |
|-----|------|------|------|
| `task_id` | string | 是 | 任务标识符(必须与路径参数匹配) |
| `stage` | string | 是 | 要评估的阶段: "script_gen_agent", "storyboard_gen_agent", "video_generator", "video_concatenater", "bgm_generator" |
| `comment` | string | 否 | 可选的反馈评论 |

**响应:** `200 OK`

```json
{
  "success": true,
  "message": "评估已收到"
}
```

**请求示例:**

```bash
curl -X POST https://api.ad-agent.example.com/v1/tasks/123e4567-e89b-12d3-a456-426614174000/assessment \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "123e4567-e89b-12d3-a456-426614174000",
    "stage": "script_gen_agent",
    "comment": "脚本看起来很棒,请继续"
  }'
```

**响应示例:**

```json
{
  "success": true,
  "message": "评估已收到"
}
```

**错误响应:**

| 状态码 | 描述 |
|--------|------|
| `404 Not Found` | 未找到任务 |
| `400 Bad Request` | 无效的阶段或评估数据 |
| `401 Unauthorized` | 缺少或无效的 API 密钥 |
| `500 Internal Server Error` | 服务器错误 |

---

## 工作流程

AD Agent API 遵循多阶段工作流:

```
1. script_gen_agent
   ↓ 使用 ReAct 的脚本生成 Agent
   ↓ 工具: web_search, remember, recall
   
2. storyboard_gen_agent
   ↓ 分镜图 Agent 创建视觉合成
   ↓ 工具: list_tags, search_images_by_tags, extract_color_palette,
   ↓      midjourney_imagine, midjourney_upscale, check_image_distortion,
   ↓      nanobanana_generate, remember, recall
   
3. video_generator
   ↓ 从分镜图图片生成视频
   ↓ 工具: veo_generate_video, kling_generate_video, 或 seedance_generate_video
   
4. video_concatenater
   ↓ 拼接所有视频片段
   ↓ 工具: 基于 FFmpeg 的视频拼接
   
5. bgm_generator
   ↓ 生成并合成背景音乐
   ↓ 工具: suno_generate_music, 基于 FFmpeg 的音频合成
   
6. 完成
```

### 工作流程详情

| 阶段 | 描述 | 主要工具 |
|-----|------|---------|
| `script_gen_agent` | AI 驱动的脚本写作,含市场调研 | web_search, remember, recall |
| `storyboard_gen_agent` | 产品图像合成,保持色调一致 | list_tags, search_images_by_tags, extract_color_palette, midjourney_imagine, midjourney_upscale, check_image_distortion, nanobanana_generate |
| `video_generator` | 视频合成,镜头平滑过渡 | veo_generate_video, kling_generate_video, seedance_generate_video |
| `video_concatenater` | 视频片段拼接 | FFmpeg |
| `bgm_generator` | 背景音乐生成和合成 | suno_generate_music, FFmpeg |

---

## 错误代码

### HTTP 状态码

| 代码 | 描述 |
|------|------|
| `200` | 成功 |
| `201` | 已创建 |
| `400` | 错误请求 |
| `401` | 未授权 |
| `404` | 未找到 |
| `500` | 内部服务器错误 |

### 应用错误格式

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": "object"
  }
}
```

---

## 支持

- **文档:** https://docs.ad-agent.example.com
- **邮箱:** support@ad-agent.example.com
- **GitHub:** https://github.com/ad-agent/api

---

## 更新日志

### 版本 1.0.0 (2025-11-17)
- 首次 API 发布
- 3 个 API 端点(创建、取消、查询)
- 评估端点
- 14 个工具规范
- 5 阶段工作流程

---

## 许可证

版权所有 © 2025 AD Agent。保留所有权利。
