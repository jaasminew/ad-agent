# AD Agent API Documentation

Version: 1.0.0  
Last Updated: 2025-11-17

## Overview

The AD Agent API is a RESTful service that automatically generates advertising videos using AI agents. It provides asynchronous task management with real-time progress tracking and streamable output.

### Base URL

```
Production: https://api.ad-agent.example.com/v1
Development: http://localhost:8000/v1
```

### Authentication

All API requests must include an API key in the header:

```http
Authorization: Bearer YOUR_API_KEY
```

---

## API Endpoints

### 1. Create Task (Async)

Create a new advertising video generation task. This is an asynchronous operation that returns immediately with a task ID.

**Endpoint:** `POST /tasks`

**Request Body:**

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

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `product_name` | string | Yes | Name of the product to advertise |
| `brand_identity` | string | Yes | Brand positioning and identity (e.g., "Nostalgia, Artistic, Instant Sharing") |
| `must_have_shots` | string | Yes | Required shots description (comma-separated, e.g., "Friends sharing photos, Camera close-up") |
| `product_images` | string | Yes | URL of the product image |
| `video_format` | string | Yes | Video aspect ratio (e.g., "16:9", "9:16", "1:1") |
| `max_shots` | integer | Yes | Maximum number of shots/scenes to generate |

**Response:** `201 Created`

```json
{
  "task_id": "string"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Unique identifier for the created task (UUID format) |

**Example Request:**

```bash
curl -X POST https://api.ad-agent.example.com/v1/tasks \
  -H "Authorization: Bearer YOUR_API_KEY" \
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

**Example Response:**

```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Error Responses:**

| Status Code | Description |
|-------------|-------------|
| `400 Bad Request` | Invalid input parameters (missing required fields or invalid values) |
| `401 Unauthorized` | Missing or invalid API key |
| `500 Internal Server Error` | Server error |

---

### 2. Cancel Task (Async)

Cancel a running task. This is an asynchronous operation.

**Endpoint:** `POST /tasks/{task_id}/cancel`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | string | Yes | Task identifier (path parameter) |

**Request Body:**

None required.

**Response:** `200 OK`

```json
{
  "success": true,
  "message": "Task cancellation initiated"
}
```

**Example Request:**

```bash
curl -X POST https://api.ad-agent.example.com/v1/tasks/123e4567-e89b-12d3-a456-426614174000/cancel \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Example Response:**

```json
{
  "success": true,
  "message": "Task cancellation initiated"
}
```

**Error Responses:**

| Status Code | Description |
|-------------|-------------|
| `404 Not Found` | Task not found |
| `400 Bad Request` | Task cannot be cancelled (already completed or failed) |
| `401 Unauthorized` | Missing or invalid API key |
| `500 Internal Server Error` | Server error |

---

### 3. Query Task

Query the current status and results of a task. Supports streamable output for real-time updates.

**Endpoint:** `GET /tasks/{task_id}`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | string | Yes | Task identifier (path parameter) |
| `stream` | boolean | No | Enable streaming response for real-time updates (query parameter) |

**Response:** `200 OK`

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

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Task identifier |
| `stage` | string | Current processing stage (see Stage Values below) |
| `status` | string | Task status: "created", "processing", "completed", "failed", "cancelled" |
| `contents` | array | Ordered list of processing blocks (streamable, see Content Blocks below) |

**Stage Values:**

| Stage | Description |
|-------|-------------|
| `script_gen_agent` | Generating advertising script using Script Generation Agent |
| `storyboard_gen_agent` | Creating storyboard images with product composition using Storyboard Agent |
| `video_generator` | Generating videos from images |
| `video_concatenater` | Stitching video clips together |
| `bgm_generator` | Generating and adding background music |
| `completed` | All processing completed |

#### Content Blocks

The `contents` array contains ordered processing blocks. Each block represents a step in the workflow. There are two types of blocks:

##### Block Type 1: LLM Output

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

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always "llm_output" |
| `timestamp` | string | ISO 8601 timestamp when the output was generated |
| `data.stage` | string | The workflow stage this output belongs to |
| `data.message` | string | Human-readable message describing what was done |
| `data.reasoning` | string | LLM's reasoning process (optional) |
| `data.output` | object | Structured output from the LLM (stage-specific) |

##### Block Type 2: Tool Calling

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

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always "tool_calling" |
| `timestamp` | string | ISO 8601 timestamp when the tool was called |
| `data.tool_name` | string | Name of the tool that was called (see Tool Specifications below) |
| `data.stage` | string | The workflow stage during which the tool was called |
| `data.input` | object | Input parameters passed to the tool (tool-specific structure) |
| `data.output` | object | Output returned by the tool (tool-specific structure) |
| `data.success` | boolean | Whether the tool call succeeded |
| `data.error` | string | Error message if success is false (optional) |

---

## Tool Specifications

This section defines the exact input/output structure for each tool used in the workflow.

### Script Generation Agent Tools

#### 1. web_search

Search the web for factual/background context.

**Input:**
```json
{
  "query": "string"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | Search query string |

**Output:**
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

| Field | Type | Description |
|-------|------|-------------|
| `results` | array | Array of search results (max 5) |
| `results[].title` | string | Title of the web page |
| `results[].url` | string | URL of the web page |
| `results[].content` | string | Excerpt from the page (max 300 chars) |
| `result_count` | integer | Number of results returned |

#### 2. remember

Store a note in session memory.

**Input:**
```json
{
  "note": "string"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `note` | string | Yes | Note to remember |

**Output:**
```json
{
  "message": "string"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `message` | string | Confirmation message |

#### 3. recall

Retrieve notes from session memory.

**Input:**
```json
{
  "query": "string"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | No | Optional search query (empty returns all notes) |

**Output:**
```json
{
  "notes": ["string"],
  "count": "integer"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `notes` | array | Array of stored notes |
| `count` | integer | Number of notes retrieved |

---

### Storyboard Generation Agent Tools

#### 4. list_tags

List available image tags from PixelHub.

**Input:**
```json
{
  "page": "integer",
  "limit": "integer"
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `page` | integer | No | 1 | Page number for pagination |
| `limit` | integer | No | 1000 | Number of tags per page (max 1000) |

**Output:**
```json
{
  "tags": ["string"],
  "total": "integer",
  "page": "integer",
  "limit": "integer"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `tags` | array | Array of available tag names |
| `total` | integer | Total number of tags |
| `page` | integer | Current page number |
| `limit` | integer | Tags per page |

#### 5. search_images_by_tags

Search for images by tags using relevance ranking (OR logic).

**Input:**
```json
{
  "tags": ["string"],
  "page": "integer",
  "limit": "integer"
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `tags` | array | Yes | - | List of tags to search (must be from list_tags) |
| `page` | integer | No | 1 | Page number for pagination |
| `limit` | integer | No | 20 | Number of images per page (max 100) |

**Output:**
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

| Field | Type | Description |
|-------|------|-------------|
| `images` | array | Array of matching images sorted by relevance |
| `images[].url` | string | Image URL |
| `images[].description` | string | Image description |
| `images[].matched_tags` | array | Tags that matched |
| `images[].match_count` | integer | Number of matching tags |
| `total` | integer | Total number of matching images |
| `page` | integer | Current page number |
| `limit` | integer | Images per page |

#### 6. extract_color_palette

Extract dominant colors from an image.

**Input:**
```json
{
  "image_url": "string"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `image_url` | string | Yes | URL of the image to analyze |

**Output:**
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

| Field | Type | Description |
|-------|------|-------------|
| `palette` | array | Array of dominant colors (typically 5-8 colors) |
| `palette[].hex` | string | Hex color code (e.g., "#FF5733") |
| `palette[].rgb` | array | RGB values [R, G, B] |
| `palette[].percentage` | number | Percentage of image containing this color |
| `dominant_color` | string | Hex code of the most dominant color |

#### 7. midjourney_imagine

Generate an image using Midjourney.

**Input:**
```json
{
  "prompt": "string"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | Yes | Image generation prompt (supports Midjourney parameters like --ar, --v, etc.) |

**Output:**
```json
{
  "task_id": "string",
  "status": "string",
  "image_url": "string",
  "prompt": "string"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Midjourney task identifier |
| `status` | string | Task status ("completed", "failed") |
| `image_url` | string | URL of the generated 2x2 grid image (4 variations) |
| `prompt` | string | The prompt that was used |

#### 8. midjourney_upscale

Upscale a specific image from a Midjourney task.

**Input:**
```json
{
  "task_id": "string",
  "index": "integer"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `task_id` | string | Yes | Midjourney task ID from imagine |
| `index` | integer | Yes | Image index to upscale (1-4: 1=top-left, 2=top-right, 3=bottom-left, 4=bottom-right) |

**Output:**
```json
{
  "task_id": "string",
  "status": "string",
  "image_url": "string",
  "original_task_id": "string",
  "index": "integer"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Upscale task identifier |
| `status` | string | Task status ("completed", "failed") |
| `image_url` | string | URL of the upscaled image |
| `original_task_id` | string | Original imagine task ID |
| `index` | integer | Index of the upscaled image |

#### 9. check_image_distortion

Check for anatomical distortions in AI-generated images.

**Input:**
```json
{
  "image_path": "string"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `image_path` | string | Yes | Path or URL to the image |

**Output:**
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

| Field | Type | Description |
|-------|------|-------------|
| `has_distortion` | boolean | Whether any distortions were detected |
| `distortion_count` | integer | Total number of distortions found |
| `distortions` | array | Array of detected distortions |
| `distortions[].type` | string | Type of distortion (e.g., "extra_fingers", "missing_limb") |
| `distortions[].severity` | string | Severity level ("low", "medium", "high") |
| `distortions[].location` | string | Location in image (e.g., "left_hand", "face") |
| `distortions[].confidence` | number | Detection confidence (0.0-1.0) |
| `passed` | boolean | Whether the image passed quality check |

#### 10. nanobanana_generate

Generate or modify images using Google Gemini (Nanobanana).

**Input:**
```json
{
  "prompt": "string",
  "input_image_paths": "string or array",
  "upload_to_cos": "boolean"
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `prompt` | string | Yes | - | Generation or modification prompt |
| `input_image_paths` | string or array | Yes | - | Path(s) or URL(s) to input image(s) |
| `upload_to_cos` | boolean | No | true | Whether to upload result to COS |

**Output:**
```json
{
  "image_url": "string",
  "uploaded": "boolean",
  "prompt": "string"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `image_url` | string | URL of the generated/modified image |
| `uploaded` | boolean | Whether the image was uploaded to COS |
| `prompt` | string | The prompt that was used |

---

### Video Generation Tools

#### 11. veo_generate_video

Generate video from image using Google Veo 3.

**Input:**
```json
{
  "prompt": "string",
  "image_url": "string",
  "upload_to_cos": "boolean"
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `prompt` | string | Yes | - | Video generation prompt |
| `image_url` | string | Yes | - | URL of the first frame image |
| `upload_to_cos` | boolean | No | true | Whether to upload result to COS |

**Output:**
```json
{
  "video_url": "string",
  "duration": "number",
  "uploaded": "boolean",
  "prompt": "string"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `video_url` | string | URL of the generated video |
| `duration` | number | Video duration in seconds |
| `uploaded` | boolean | Whether the video was uploaded to COS |
| `prompt` | string | The prompt that was used |

#### 12. kling_generate_video

Generate video using Kling AI.

**Input:**
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

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `image_url` | string | Yes | - | URL of the first frame image |
| `prompt` | string | Yes | - | Video generation prompt |
| `duration` | string | No | "5" | Video duration: "5" or "10" |
| `mode` | string | No | "pro" | Generation mode: "std" or "pro" |
| `cfg_scale` | number | No | 0.5 | CFG scale (0.0-1.0) |
| `upload_to_cos` | boolean | No | true | Whether to upload result to COS |

**Output:**
```json
{
  "video_url": "string",
  "duration": "number",
  "task_id": "string",
  "uploaded": "boolean"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `video_url` | string | URL of the generated video |
| `duration` | number | Video duration in seconds |
| `task_id` | string | Kling task identifier |
| `uploaded` | boolean | Whether the video was uploaded to COS |

#### 13. seedance_generate_video

Generate video using Seedance.

**Input:**
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

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `prompt` | string | Yes | - | Video generation prompt |
| `image_url` | string | No | null | Optional first frame image URL |
| `resolution` | string | No | "1080p" | Video resolution: "720p", "1080p" |
| `duration` | integer | No | 5 | Video duration in seconds (5-10) |
| `camera_fixed` | boolean | No | false | Whether to fix camera position |
| `upload_to_cos` | boolean | No | true | Whether to upload result to COS |

**Output:**
```json
{
  "video_url": "string",
  "duration": "integer",
  "resolution": "string",
  "uploaded": "boolean"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `video_url` | string | URL of the generated video |
| `duration` | integer | Video duration in seconds |
| `resolution` | string | Video resolution |
| `uploaded` | boolean | Whether the video was uploaded to COS |

---

### Music Generation Tools

#### 14. suno_generate_music

Generate background music using Suno AI.

**Input:**
```json
{
  "prompt": "string",
  "style": "string",
  "duration": "integer",
  "instrumental": "boolean"
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `prompt` | string | Yes | - | Music generation prompt |
| `style` | string | No | "" | Music style (e.g., "electronic", "classical") |
| `duration` | integer | No | 30 | Music duration in seconds |
| `instrumental` | boolean | No | true | Whether to generate instrumental music (no vocals) |

**Output:**
```json
{
  "music_url": "string",
  "duration": "integer",
  "style": "string",
  "task_id": "string"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `music_url` | string | URL of the generated music |
| `duration` | integer | Music duration in seconds |
| `style` | string | Generated music style |
| `task_id` | string | Suno task identifier |

---

## Example Response

**Example Request:**

```bash
curl -X GET https://api.ad-agent.example.com/v1/tasks/123e4567-e89b-12d3-a456-426614174000 \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Example Response:**

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
        "message": "Generated 5 shots for Polaroid Camera",
        "reasoning": "Analyzed brand identity emphasizing nostalgia and instant sharing",
        "output": {
          "shots": [
            {
              "shot_number": 1,
              "description": "Friends gathering around, laughing and sharing instant photos"
            },
            {
              "shot_number": 2,
              "description": "Close-up of hands holding a freshly printed Polaroid photo"
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
          "query": "Polaroid camera instant photography trends 2025"
        },
        "output": {
          "results": [
            {
              "title": "The Return of Instant Photography in 2025",
              "url": "https://example.com/article",
              "content": "Instant photography is making a comeback with younger generations..."
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
          "prompt": "Friends gathering around, laughing and sharing instant photos, nostalgic atmosphere, warm lighting --ar 16:9 --v 6"
        },
        "output": {
          "task_id": "mj_abc123",
          "status": "completed",
          "image_url": "https://cdn.example.com/mj_abc123.jpg",
          "prompt": "Friends gathering around, laughing and sharing instant photos, nostalgic atmosphere, warm lighting --ar 16:9 --v 6"
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
          "prompt": "Replace the generic camera with this Polaroid camera product, maintaining natural placement",
          "input_image_paths": "https://cdn.example.com/mj_abc123.jpg",
          "upload_to_cos": true
        },
        "output": {
          "image_url": "https://cos.example.com/final_shot1.jpg",
          "uploaded": true,
          "prompt": "Replace the generic camera with this Polaroid camera product, maintaining natural placement"
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
          "prompt": "Camera slowly zooms in on the group of friends, they look up and smile at the camera",
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

**Streaming Response:**

Enable streaming to receive real-time updates:

```bash
curl -X GET "https://api.ad-agent.example.com/v1/tasks/123e4567-e89b-12d3-a456-426614174000?stream=true" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Accept: text/event-stream"
```

Server-Sent Events (SSE) format:
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

**Error Responses:**

| Status Code | Description |
|-------------|-------------|
| `404 Not Found` | Task not found |
| `401 Unauthorized` | Missing or invalid API key |
| `500 Internal Server Error` | Server error |

---

### 4. Assessment

Submit feedback or assessment for a specific stage of a task.

**Endpoint:** `POST /tasks/{task_id}/assessment`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | string | Yes | Task identifier (path parameter) |

**Request Body:**

```json
{
  "task_id": "string",
  "stage": "string",
  "comment": "string"
}
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | string | Yes | Task identifier (must match path parameter) |
| `stage` | string | Yes | Stage to assess: "script_gen_agent", "storyboard_gen_agent", "video_generator", "video_concatenater", "bgm_generator" |
| `comment` | string | No | Optional feedback comment |

**Response:** `200 OK`

```json
{
  "success": true,
  "message": "Assessment received"
}
```

**Example Request:**

```bash
curl -X POST https://api.ad-agent.example.com/v1/tasks/123e4567-e89b-12d3-a456-426614174000/assessment \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "123e4567-e89b-12d3-a456-426614174000",
    "stage": "script_gen_agent",
    "comment": "The script looks great, please proceed"
  }'
```

**Example Response:**

```json
{
  "success": true,
  "message": "Assessment received"
}
```

**Error Responses:**

| Status Code | Description |
|-------------|-------------|
| `404 Not Found` | Task not found |
| `400 Bad Request` | Invalid stage or assessment data |
| `401 Unauthorized` | Missing or invalid API key |
| `500 Internal Server Error` | Server error |

---

## Workflow

The AD Agent API follows a multi-stage workflow:

```
1. script_gen_agent
   ↓ Script Generation Agent with ReAct
   ↓ Tools: web_search, remember, recall
   
2. storyboard_gen_agent
   ↓ Storyboard Agent creates visual compositions
   ↓ Tools: list_tags, search_images_by_tags, extract_color_palette,
   ↓        midjourney_imagine, midjourney_upscale, check_image_distortion,
   ↓        nanobanana_generate, remember, recall
   
3. video_generator
   ↓ Generate videos from storyboard images
   ↓ Tools: veo_generate_video, kling_generate_video, or seedance_generate_video
   
4. video_concatenater
   ↓ Stitch all video clips together
   ↓ Tools: FFmpeg-based video concatenation
   
5. bgm_generator
   ↓ Generate and compose background music
   ↓ Tools: suno_generate_music, FFmpeg-based audio composition
   
6. Completed
```

### Workflow Details

| Stage | Description | Primary Tools |
|-------|-------------|---------------|
| `script_gen_agent` | AI-powered script writing with market research | web_search, remember, recall |
| `storyboard_gen_agent` | Product image composition with consistent colors | list_tags, search_images_by_tags, extract_color_palette, midjourney_imagine, midjourney_upscale, check_image_distortion, nanobanana_generate |
| `video_generator` | Video synthesis with smooth transitions | veo_generate_video, kling_generate_video, seedance_generate_video |
| `video_concatenater` | Video clip concatenation | FFmpeg |
| `bgm_generator` | Background music generation and composition | suno_generate_music, FFmpeg |

---

## Error Codes

### HTTP Status Codes

| Code | Description |
|------|-------------|
| `200` | Success |
| `201` | Created |
| `400` | Bad Request |
| `401` | Unauthorized |
| `404` | Not Found |
| `500` | Internal Server Error |

### Application Error Format

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

## Support

- **Documentation:** https://docs.ad-agent.example.com
- **Email:** support@ad-agent.example.com
- **GitHub:** https://github.com/ad-agent/api

---

## Changelog

### Version 1.0.0 (2025-11-17)
- Initial API release
- 3 API endpoints (Create, Cancel, Query)
- Assessment endpoint
- 14 tool specifications
- 5-stage workflow

---

## License

Copyright © 2025 AD Agent. All rights reserved.
