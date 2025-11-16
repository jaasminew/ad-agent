# 广告视频生成工作流程图

```mermaid
graph TD
    A[开始: 输入商品信息] --> B[步骤1: 编写广告脚本]
    B --> C{生成分镜列表}
    
    C --> D1[Shot 1 处理]
    C --> D2[Shot 2 处理]
    C --> D3[Shot N 处理]
    
    D1 --> E1[步骤2: 搜索风格图片]
    D2 --> E2[步骤2: 搜索风格图片]
    D3 --> E3[步骤2: 搜索风格图片]
    
    E1 --> F1[步骤3: 提取主色调]
    E2 --> F2[步骤3: 提取主色调]
    E3 --> F3[步骤3: 提取主色调]
    
    F1 --> G1[步骤4: Midjourney 生成图片]
    F2 --> G2[步骤4: Midjourney 生成图片]
    F3 --> G3[步骤4: Midjourney 生成图片]
    
    G1 --> H1{步骤5: 检查失真?}
    G2 --> H2{步骤5: 检查失真?}
    G3 --> H3{步骤5: 检查失真?}
    
    H1 -->|失真| G1
    H2 -->|失真| G2
    H3 -->|失真| G3
    
    H1 -->|正常| I1[步骤6: NanoBanana 合成商品]
    H2 -->|正常| I2[步骤6: NanoBanana 合成商品]
    H3 -->|正常| I3[步骤6: NanoBanana 合成商品]
    
    I1 --> J1[步骤7: Veo3 生成视频]
    I2 --> J2[步骤7: Veo3 生成视频]
    I3 --> J3[步骤7: Veo3 生成视频]
    
    J1 --> K[步骤8: 拼接所有视频]
    J2 --> K
    J3 --> K
    
    K --> L{generate_video?}
    
    L -->|false| M[输出: 图片+提示词]
    L -->|true| N[输出: 完整视频]
    
    N --> O[步骤9: 生成背景音乐]
    
    O --> P[Suno 生成 BGM]
    P --> Q[合成音乐到视频]
    Q --> R[上传最终视频]
    
    R --> S[完成: 带 BGM 的广告视频]
    M --> T[完成: 中间产物]
    
    style A fill:#e1f5ff
    style B fill:#fff4e1
    style D1 fill:#f0f0f0
    style D2 fill:#f0f0f0
    style D3 fill:#f0f0f0
    style K fill:#ffe1f5
    style O fill:#e1ffe1
    style P fill:#e1ffe1
    style Q fill:#e1ffe1
    style S fill:#90EE90
    style T fill:#FFE4B5
```

## 关键步骤说明

### 并发处理阶段(步骤 2-7)
- 每个分镜(Shot)独立并发处理
- 各自生成独立的视频片段
- 互不干扰,提高效率

### 汇总阶段(步骤 8)
- 收集所有分镜的视频
- 按顺序拼接成完整视频
- 计算总时长

### 音乐合成阶段(步骤 9) 🆕
- LLM 分析广告内容生成音乐提示词
- Suno API 生成符合氛围的背景音乐
- ffmpeg 将音乐合成到视频中
- 自动淡出、音量调节

## 数据流

```
初始输入
├── product_name (商品名称)
├── brand_identity (品牌定位)
├── product_images (商品图片 URL)
└── must_have_shots (必需分镜)

↓

步骤 1 输出
└── shots[] (分镜列表)

↓ (并发)

步骤 2-7 输出(每个 shot)
├── style_image_url (风格图片)
├── palette (主色调)
├── midjourney_image (MJ 图片)
├── nanobanana_image (合成图片)
└── veo3_video (视频) [可选]

↓

步骤 8 输出
├── final_video_url (拼接视频)
└── video_duration (视频时长)

↓

步骤 9 输出
├── music_prompt (音乐提示词)
├── bgm_url (背景音乐)
└── final_video_with_bgm_url (最终视频) ✨
```

## 工具依赖关系

```
LangChain Tools
├── pixelhub
│   ├── list_tags
│   └── search_images_by_tags
├── palette_extractor
│   └── extract_color_palette
├── midjourney
│   ├── midjourney_imagine
│   └── midjourney_upscale
├── distortion_checker
│   └── check_image_distortion
├── nanobanana
│   └── nanobanana_generate
├── veo_video
│   └── veo_generate_video
├── video_concat
│   └── concat_videos
├── suno_music 🆕
│   └── suno_generate_music
└── video_add_bgm 🆕
    └── video_add_bgm_tool
```

## 时间估算

假设生成 3 个分镜的广告:

| 步骤 | 耗时 | 说明 |
|------|------|------|
| 1. 脚本编写 | ~30s | LLM 生成 |
| 2-7. 单个 Shot 处理 | ~5-8min | 并发执行 |
| 8. 视频拼接 | ~30s | ffmpeg 处理 |
| 9. BGM 生成 | ~2-3min | Suno API |
| 9. BGM 合成 | ~30s | ffmpeg 处理 |
| **总计** | **~8-12min** | 含并发优化 |

## 控制标志

### `generate_video`
- `true`: 生成完整视频(包含步骤 9)
- `false`: 只生成图片和提示词(跳过步骤 8-9)

用途:
- 快速预览:设置为 `false`,快速查看图片效果
- 完整生成:设置为 `true`,生成最终可用的广告视频

