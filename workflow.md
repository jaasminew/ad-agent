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
- midjourney_image: 该 shot 的图片
- product_images: 商品图片

1. 调用工具 nanobanana_generate 将商品放到该 shot 的 Midjourney 生成的分镜图片中（即图片+图片+文字生成新的图片）

输出：
- nanobanana_image: 该 shot 的合成图片

下一步：7

### 7. 调用 veo3 生成视频（针对单个 shot）

输入：
- nanobanana_image: 该 shot 的合成图片
- **shot**: 该分镜描述

1. 调用工具 veo_generate_video，利用**这个 shot** 的描述和合成图片生成视频。

输出：
- veo3_video: 该 shot 的最终视频

---

**最终汇总：**
所有 shots 并发处理完成后，得到多个独立的视频片段（每个 shot 一个视频）。
