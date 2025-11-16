# AD Agent Workflow

利用 AI agent 的能力生成广告视频

## 初始输入

- product_name: 类型为字符串,表示商品名称
- brand_identity: 类型为字符串,表示商品品牌定位
- product_images: 类型为字符串,是商品图片的 URL
- must_have_shots: 类型为字符串,用半角逗号分割,商品广告中必须有的分镜
- generate_video: 类型为布尔值,控制是否生成视频(默认 true)

## 最终输出

- 如果 generate_video=true: 一个完整的广告视频(所有 shots 拼接 + 背景音乐)
- 如果 generate_video=false: 所有 shots 的合成图片和视频提示词

## 工作流程

### 1. 编写广告脚本

输入(全部来自初始输入):
- product_name
- brand_identity
- must_have_shots

利用大模型语言能力生成分镜列表。

输出:
- shots: 分镜列表

下一步: 2

---

### 2. 调用 Storyboard Agent 生成合成图片

**这一步替代了原来的步骤 2-6(搜索风格图片、提取主色调、生成图片、检查失真、商品替换)**

输入(构造 EpisodeConfig):
- title: 广告标题(可以使用商品名称或品牌信息)
- product_config: 商品配置
  - product_image_url: 真实商品图片 URL
  - target_object: 要替换的目标物体(如 "laptop", "phone", "shoes" 等)
- beats: 分镜列表(来自步骤 1)
  - beat: 分镜序号
  - heading: 分镜标题
  - shot_description: 场景描述
  - action: 动作描述

**Storyboard Agent 内部处理(黑盒)**:
- Agent 自动协调多个工具完成整个生成流程
- 内部使用: PixelHub, Midjourney, Distortion Checker, Nanobanana, Palette Extractor 等
- 串行处理每个 beat,自动管理色调一致性、质量检查、智能重试等
- 具体实现细节(包括 prompt 工程)无需关注,作为黑盒使用

输出(EpisodeResult):
- episode_id: 生成的唯一 episode ID
- title: episode 标题
- episode_palette: 统一的色调方案(hex 颜色列表)
- beats: 每个 beat 的详细处理结果(BeatResult 列表):
  - beat_number: beat 序号
  - shot_text: 规范化的分镜文本
  - reference_image_url: 参考图片 URL(来自 PixelHub)
  - color_palette: 该 beat 的色板(首个 beat 会设置全局色板)
  - attempts: 所有生成尝试的详细信息
  - total_attempts: 总尝试次数(1-3)
  - storyboard_image_url: 最终选择的分镜图片 URL(Midjourney 生成)
  - storyboard_task_id: Midjourney 任务 ID
  - quality_check_passed: 质量检查是否通过
  - final_image_url: 商品合成后的最终图片 URL(Nanobanana 输出)
  - product_replacement_success: 商品替换是否成功
  - product_replacement_error: 商品替换错误信息(如果有)
  - flagged_for_review: 是否需要人工审核
  - review_reason: 标记原因
- total_beats: 总 beat 数
- successful_beats: 成功完成商品替换的 beat 数
- flagged_beats: 标记需要审核的 beat 数
- product_url_memory: beat 序号到最终商品图片 URL 的映射
- global_memory: 全局记忆条目(用于跨 beat 的状态共享)
  - **重要**: global_memory 的第一条是 `uploaded_final_urls`,包含所有已上传到 COS 的最终商品合成图片列表
  - 这是 Agent 最重要的输出产物,包含了所有成功生成的商品合成图片 URL

**关键输出获取方式**:
```python
# 方式 1: 从 global_memory 中提取(推荐,最直接)
final_urls = []
for item in episode_result.global_memory:
    if item.startswith("uploaded_final_urls:"):
        import json
        final_urls = json.loads(item.split(":", 1)[1].strip())
        break

# 方式 2: 从 beats 中收集
final_urls = [
    beat.final_image_url 
    for beat in episode_result.beats 
    if beat.final_image_url and beat.product_replacement_success
]
```

> **TODO**: 未来优化 - 应该将 `uploaded_final_urls` 作为 EpisodeResult 的顶层字段直接返回,而不是埋藏在 global_memory 中。这是 Storyboard Agent 的核心输出,应该更易于访问。

下一步: 3

---

### 3. 串行生成视频(针对每个 beat)

**注意:这一步改为串行执行,以便考虑相邻镜头的过渡连贯性**

对于每个 beat,按顺序执行:

输入:
- episode_result: Storyboard Agent 的完整输出(来自步骤 2)
  - **推荐**: 从 episode_result.global_memory 中提取 `uploaded_final_urls` 列表
  - 或从 episode_result.beats 中提取每个 beat 的 final_image_url(商品合成图)
  - 使用 beat 的 shot_text, heading, action 等信息
- generate_video: 是否生成视频的控制标志

处理流程(对每个 beat):
1. 使用 LLM 生成视频提示词(video_prompt)
   - 输入: 当前 beat 的 final_image_url(作为视频首帧)
   - 参考: 当前 beat 的 shot_text 和 action
   - 考虑: previous_beat 的信息(如果存在),确保过渡连贯
   - 考虑: next_beat 的信息(如果存在),规划镜头走向
   - 生成能够确保镜头间连贯性的视频提示词
2. 如果 generate_video 为 true:
   - 调用工具 veo_generate_video(image_url, video_prompt)
   - 等待视频生成完成
   - 记录视频 URL
3. 如果 generate_video 为 false:
   - 只生成和记录提示词,不调用视频生成

输出:
- beat_video_results: 每个 beat 的视频生成结果列表
  - beat_number: beat 序号
  - source_image_url: 源合成图片 URL(来自 uploaded_final_urls 或 episode_result.beats[i].final_image_url)
  - video_prompt: 生成的视频提示词
  - video_url: 生成的视频 URL(仅当 generate_video=true 时)
  - success: 是否成功生成

下一步: 4

---

### 4. 拼接视频(最终汇总)

输入:
- episode_result: Storyboard Agent 的完整输出(来自步骤 2)
- beat_video_results: 所有 beats 的视频生成结果(来自步骤 3)
- generate_video: 是否生成视频的控制标志

处理流程:
1. 汇总所有 beats 的结果
2. 如果 generate_video 为 true:
   - 从 beat_video_results 收集所有 beats 的视频 URL
   - 调用工具 video_concat 按顺序拼接所有视频
   - 上传拼接后的完整视频到 COS
3. 如果 generate_video 为 false:
   - 只汇总结果,不进行视频拼接
   - 准备所有合成图片和视频提示词供用户查看

输出:
- aggregated_summary: 汇总统计信息
  - total_beats: 总 beat 数
  - successful_image_beats: 成功生成合成图片的 beat 数
  - successful_video_beats: 成功生成视频的 beat 数(如果 generate_video=true)
  - flagged_beats: 需要人工审核的 beat 数
- final_outputs: 每个 beat 的完整输出
  - beat_number: beat 序号
  - storyboard_image_url: Midjourney 原始图(来自 episode_result)
  - final_image_url: 商品合成图(来自 episode_result)
  - video_prompt: 视频提示词(来自 beat_video_results)
  - video_url: 视频 URL(如果 generate_video=true)
  - flagged_for_review: 是否需要审核
- final_video_url: 拼接后的完整视频 URL(仅当 generate_video=true 时)
- video_duration: 拼接后视频的总时长(秒)(仅当 generate_video=true 时)

下一步: 5(如果 generate_video=true)

---

### 5. 生成背景音乐并合成(仅当 generate_video=true)

输入:
- final_video_url: 步骤 4 拼接后的完整视频
- video_duration: 视频总时长(秒)
- product_name: 商品名称
- brand_identity: 品牌定位
- shots: 所有分镜描述

处理流程:
1. 利用 LLM 根据广告内容生成音乐提示词
   - 分析商品定位和品牌调性
   - 结合所有分镜的情绪和节奏
   - 生成符合广告氛围的音乐描述
   - 确定音乐风格(如:轻快、舒缓、激昂、科技感等)
2. 调用工具 suno_generate_music 生成背景音乐
   - 使用 LLM 生成的音乐提示词
   - 设置 instrumental=true(纯音乐,无歌词)
   - 音乐时长需要与 video_duration 匹配或稍长
3. 调用工具 video_add_bgm 将背景音乐合成到视频中
   - 如果音乐过长,自动裁剪到视频时长
   - 如果音乐过短,可以循环播放或淡出
   - 调整音量,确保不会盖过视频原声(如果有)
4. 上传最终带音乐的视频到 COS

输出:
- music_prompt: BGM 提示词
- bgm_url: 生成的背景音乐 URL
- final_video_with_bgm_url: 合成背景音乐后的完整广告视频 URL

---

## 工作流程图

```
初始输入
  ↓
[1] 编写广告脚本
  ↓
  shots(分镜列表)
  ↓
[2] Storyboard Agent (黑盒处理)
  │
  │  输入: EpisodeConfig (title, product_config, beats)
  │  
  │  内部自动处理:
  │  - 风格搜索与色调管理
  │  - 图片生成与质量检查
  │  - 商品替换与失真检测
  │  - 智能重试与状态管理
  │  
  │  输出: EpisodeResult (包含所有 beats 的合成图片)
  │
  ↓
  EpisodeResult.global_memory["uploaded_final_urls"]
  (所有商品合成图片 URL 列表)
  ↓
[3] 串行生成视频 (考虑相邻镜头过渡)
  │
  ├─ 对每个 beat (按顺序):
  │   ├─ 从 uploaded_final_urls 获取合成图
  │   ├─ 生成视频提示词 (考虑 previous/next beat)
  │   └─ 生成视频 (Veo3, 如果 generate_video=true)
  │
  ↓
  beat_video_results
  ↓
[4] 拼接视频
  │
  ├─ 汇总所有 beats 的结果
  └─ 拼接所有视频片段 (如果 generate_video=true)
  ↓
  final_video_url (如果 generate_video=true)
  ↓
[5] 生成并合成背景音乐 (如果 generate_video=true)
  ↓
  final_video_with_bgm_url
```

## 关键改进点

### 1. Storyboard Agent 集成(黑盒设计)
- **统一处理**: 原步骤 2-6 合并为一个 Storyboard Agent,提供清晰的输入输出接口
- **黑盒封装**: 内部实现(包括 prompt 工程、工具协调、重试逻辑等)完全封装,无需关注
- **自动化能力**: 
  - 自动管理色调一致性(首个 beat 色调作为全局色调)
  - 自动质量检查和智能重试(最多 3 次)
  - 自动标记问题 beat,不会因单个失败而中断
  - 自动状态管理和跨 beat 信息共享
- **输入**: 只需提供 `EpisodeConfig` (title, product_config, beats)
- **输出**: 获得结构化的 `EpisodeResult`,包含所有生成结果和状态信息

### 2. 明确的数据流
- **EpisodeConfig 输入**: 清晰定义 title, product_config(product_image_url, target_object), beats
- **EpisodeResult 输出**: 完整的结构化输出,包含每个 beat 的详细信息
  - 每个 beat 有独立的 BeatResult,包含所有尝试记录和最终结果
  - 提供 storyboard_image_url(Midjourney 原图)和 final_image_url(商品合成图)
  - 包含质量检查、商品替换状态、标记信息等
- **数据传递**: episode_result.beats[i].final_image_url 直接传递到视频生成步骤

### 3. 串行视频生成
- **过渡连贯**: 生成视频时考虑 previous_beat 和 next_beat,确保镜头间平滑过渡
- **上下文感知**: 每个 beat 的视频提示词都包含前后镜头信息,提升整体流畅度
- **顺序依赖**: 必须串行执行,因为需要知道相邻镜头的状态
- **图生视频**: 使用 final_image_url(已包含真实商品)作为视频首帧

### 4. 灵活的执行模式
- **generate_video 标志**: 可以选择只生成合成图片和提示词,不生成实际视频
- **快速迭代**: 在 generate_video=false 模式下可以快速验证分镜和商品合成效果
- **成本控制**: 视频生成成本较高,可以先验证图片效果再决定是否生成视频
- **完整输出**: 即使不生成视频,也能获得所有合成图片和视频提示词

## 技术栈

- **Storyboard Agent**: LangChain ReAct Agent
  - 支持任何 LangChain 兼容的 LLM(GPT-4, Claude Sonnet 4 等)
  - 当前推荐: GPT-4o-mini(成本效益好)或 Claude Sonnet 4(质量高)
- **风格搜索**: PixelHub API
- **主色调提取**: palette_extractor
- **图片生成**: Midjourney Proxy
- **失真检测**: Distortion Checker (MediaPipe)
- **商品替换**: Nanobanana (Google Gemini)
- **视频生成**: Veo 3 (Google)
- **音乐生成**: Suno AI
- **视频处理**: FFmpeg (拼接、合成音乐)
- **存储**: 腾讯云 COS

## 注意事项

### Storyboard Agent 的使用说明
1. **黑盒使用**: Agent 作为黑盒使用,内部实现细节(prompt、工具调用顺序等)无需修改
2. **接口稳定**: 只关注输入(EpisodeConfig)和输出(EpisodeResult)的数据结构
3. **串行处理**: Agent 目前串行处理每个 beat,大量 beats 时处理时间较长
4. **依赖外部服务**: 依赖多个外部 API(PixelHub, Midjourney, Nanobanana 等),确保服务可用
5. **成本考虑**: 每次重试都会产生 API 费用,特别是 Midjourney 和 Nanobanana

### 建议的优化方向
1. **优化输出结构 (高优先级)**: 
   - 将 `uploaded_final_urls` 提升为 `EpisodeResult` 的顶层字段
   - 这是 Agent 的核心输出产物,不应埋藏在 `global_memory` 中
   - 建议添加: `final_image_urls: List[str]` 字段到 `EpisodeResult`
2. **并行化**: 未来可考虑并行处理多个 beats,但需要解决色调共享问题
3. **缓存机制**: 相同的分镜可以复用之前的生成结果
4. **质量阈值配置**: 允许自定义失真容忍度
5. **备用方案**: 当 Nanobanana 失败时,可以保留 Midjourney 原图作为备选
