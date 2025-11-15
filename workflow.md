# AD Agent Workflow

利用 AI agent 的能力生成广告视频

## 初始输入

- product_name: 类型为字符串，表示商品名称
- brand_identity: 类型为字符串，表示商品品牌定位
- product_images: 类型为字符串，是商品图片的 URL
- must_have_shots: 类型为字符串，用半角逗号分割，商品广告中必须有的分镜

## 最终输出

- 广告视频

## 工作流程

### 1. 编写广告脚本

输入（全部来自初始输入）：
- product_name
- brand_identity
- must_have_shots

利用大模型语言能力生成分镜列表。

输出：
- shots: 分镜列表

下一步：对每个 shot 并发执行步骤 2-7

---

**注意：从步骤 2 开始，每个 shot 独立处理，并发执行。每个 shot 最终生成一个独立的视频。**

以下步骤针对**单个 shot** 进行处理：

---

### 2. 搜索风格图片（针对单个 shot）

输入：
- **shot**: 单个分镜描述（从 shots 列表中取一个）
- product_name
- brand_identity

1. 调用工具 list_tags 获取 pixelhub 风格图片库中所有的标签。
2. 利用大语言模型根据**这个 shot**找到与输入最接近的标签。
3. 调用工具 search_images_by_tags 查询最贴切的风格图片，并选取第一张。

输出：
- style_image_url: 该 shot 的风格图片

下一步：3

### 3. 提取主色调（针对单个 shot）

输入：
- style_image_url: 该 shot 的风格图片

调用工具 extract_color_palette 获取图片的四个主色

输出：
- palette: 该 shot 图片的四个主色

下一步：4

### 4. 调用 Midjourney 生成图片（针对单个 shot）

输入：
- style_image_url: 该 shot 的风格图片
- palette: 该 shot 的主色调
- **shot**: 单个分镜描述

1. 利用大模型能力，根据**这个 shot** 和 palette 生成喂给 Midjourney 的 prompt
2. 调用工具 midjourney_imagine，输入应当是 style_image_url 在前，prompt 在后的形式，Midjourney 会生成四张图拼在一起的缩略图
3. 调用工具 midjourney_upscale 选择第一张图片

输出：
- midjourney_image: 该 shot 的 Midjourney 生成图片

下一步：5

### 5. 检查图片是否失真畸变（针对单个 shot）

输入：
- midjourney_image: 该 shot 的图片

1. 调用工具 check_image_distortion 检查图片是否畸变失真
2. 利用大模型能力判断检查结果，根据结果选择下一步

下一步：
- 如果失真，则到 4 重新生成该 shot 的图片
- 如果真实，则到 6

### 6. 调用 nanobanana 将商品放入图片中（针对单个 shot）

输入：
- midjourney_image: 该 shot 的图片（已包含商品的场景图）
- product_images: 真实的商品图片
- **shot**: 单个分镜描述（用于指导如何替换商品）

1. 利用 LLM 分析分镜描述，生成 nanobanana 的提示词，指导如何将图片中的商品**替换**为真实的产品图片
2. 调用工具 nanobanana_generate 将 Midjourney 生成图片中的商品替换为真实商品图片（即图片+图片+文字生成新的图片）

输出：
- nanobanana_image: 该 shot 的合成图片（商品已被替换为真实产品）

下一步：7

### 7. 调用 veo3 生成视频（针对单个 shot）

输入：
- nanobanana_image: 该 shot 的合成图片
- **shot**: 该分镜描述
- generate_video: 是否生成视频的控制标志

1. 使用 LLM 生成视频提示词（video_prompt）
2. 如果 generate_video 为 true，调用工具 veo_generate_video 生成视频；否则只生成提示词

输出：
- video_prompt: 该 shot 的视频提示词（总是生成）
- veo3_video: 该 shot 的最终视频（仅当 generate_video=true 时）

---

**中间汇总：**
所有 shots 并发处理完成后，得到：
- 如果 generate_video=true: 多个独立的视频片段（每个 shot 一个视频）
- 如果 generate_video=false: 多个合成图片和视频提示词

下一步：8

---

### 8. 拼接视频（最终汇总）

输入：
- shot_results: 所有 shots 的处理结果
- generate_video: 是否生成视频的控制标志

1. 汇总所有 shots 的结果
2. 如果 generate_video 为 true:
   - 收集所有 shots 的视频 URL
   - 调用工具 video_concat 按顺序拼接所有视频
   - 上传拼接后的完整视频到 COS
3. 如果 generate_video 为 false:
   - 只汇总结果，不进行视频拼接

输出：
- aggregated_summary: 汇总统计信息
- final_outputs: 每个 shot 的详细输出
- final_video_url: 拼接后的完整视频 URL（仅当 generate_video=true 时）

---

**最终输出：**
- 如果 generate_video=true: 一个完整的广告视频（所有 shots 拼接）
- 如果 generate_video=false: 所有 shots 的合成图片和视频提示词
