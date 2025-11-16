# Suno 音乐生成工具使用说明

## 概述

已成功创建 Suno 音乐生成工具及相关的视频背景音乐合成工具,用于广告视频的最终音乐处理。

## 新增文件

### 1. `tools/suno_music.py`
Suno 音乐生成工具的核心实现。

**主要功能:**
- 调用 Suno API 生成音乐(支持纯音乐和带歌词)
- 使用轮询方式获取生成结果(不依赖回调)
- 自动下载生成的音乐文件
- 可选上传到腾讯云 COS

**关键类和函数:**
- `SunoMusicClient`: 主要客户端类
- `suno_generate_music`: LangChain 工具包装函数

**支持的参数:**
- `prompt`: 音乐描述提示词(必需)
- `style`: 音乐风格(如:古典、流行、摇滚、电子、爵士)
- `title`: 音乐标题(可选)
- `instrumental`: 是否生成纯音乐(默认: False)
- `model`: 模型版本(默认: "V3_5")
- `vocal_gender`: 人声性别 "m"(男) / "f"(女)
- `negative_tags`: 要避免的标签
- `upload_to_cos`: 是否上传到 COS(默认: True)

### 2. `tools/video_add_bgm.py`
视频背景音乐合成工具。

**主要功能:**
- 将音乐添加到视频中作为 BGM
- 自动检测视频是否已有音轨并混音
- 支持音量调节和淡出效果
- 音乐自动裁剪到视频时长
- 上传最终视频到腾讯云 COS

**关键类和函数:**
- `VideoAddBGMClient`: 主要客户端类
- `video_add_bgm_tool`: LangChain 工具包装函数

**支持的参数:**
- `video_url`: 视频 URL 或本地路径(必需)
- `audio_url`: 音频 URL 或本地路径(必需)
- `audio_volume`: BGM 音量 0.0-1.0(默认: 0.3 即 30%)
- `fade_out_duration`: 淡出时长(秒)(默认: 2.0)

### 3. `examples/test_suno_music.py`
Suno 工具的测试脚本,包含多个测试用例。

**测试场景:**
1. 基础纯音乐生成(钢琴)
2. 带歌词的流行歌曲
3. LangChain 工具包装测试
4. 摇滚音乐生成

### 4. `workflow.md` (已更新)
更新了工作流程文档,添加了第 9 步:生成背景音乐并合成。

## 环境变量配置

使用这些工具前需要设置以下环境变量:

```bash
# Suno API Token (必需)
export SUNO_API_TOKEN='your-suno-token-here'

# 腾讯云 COS 配置(可选,用于上传)
export COS_SECRET_ID='your-cos-secret-id'
export COS_SECRET_KEY='your-cos-secret-key'
export COS_BUCKET='your-bucket-name'
export COS_REGION='ap-guangzhou'  # 或其他地区
```

## 使用示例

### 1. 直接使用客户端

```python
from tools.suno_music import SunoMusicClient

client = SunoMusicClient()

# 生成纯音乐
result = client.generate_music(
    prompt="一段平静舒缓的钢琴曲，带有柔和的旋律",
    style="古典",
    title="宁静钢琴冥想",
    instrumental=True,
    model="V3_5",
)

if result["success"]:
    for track in result["tracks"]:
        print(f"Title: {track['title']}")
        print(f"Local Path: {track['local_path']}")
```

### 2. 作为 LangChain 工具

```python
from tools.suno_music import suno_generate_music

result = suno_generate_music.invoke({
    "prompt": "一段轻快的电子音乐，适合作为视频背景音乐",
    "style": "电子",
    "instrumental": True,
})
print(result)
```

### 3. 视频添加 BGM

```python
from tools.video_add_bgm import add_bgm_to_video

# 将音乐合成到视频
video_url = add_bgm_to_video(
    video_url="https://example.com/video.mp4",
    audio_url="https://example.com/music.mp3",
    audio_volume=0.3,  # 30% 音量
    fade_out_duration=2.0  # 最后 2 秒淡出
)
print(f"Video with BGM: {video_url}")
```

## 工作流程集成

在广告视频生成工作流中,新增的步骤 9 将:

1. **LLM 生成音乐提示词**: 根据商品定位、品牌调性和所有分镜描述,生成符合广告氛围的音乐提示词
2. **调用 Suno 生成音乐**: 使用生成的提示词创建背景音乐(纯音乐,无歌词)
3. **合成到视频**: 将生成的音乐添加到拼接完成的广告视频中
4. **上传最终视频**: 将带有背景音乐的完整广告视频上传到 COS

## 技术特点

### Suno 工具
- ✅ 使用轮询机制,不需要回调 URL
- ✅ 自动处理任务状态(PENDING → TEXT_SUCCESS → FIRST_SUCCESS → SUCCESS)
- ✅ 支持多种音乐风格和参数配置
- ✅ 通常生成 2 首音乐供选择
- ✅ 自动下载和 COS 上传

### BGM 合成工具
- ✅ 使用 ffmpeg 进行专业音视频处理
- ✅ 智能检测视频是否已有音轨
- ✅ 支持音量调节和淡出效果
- ✅ 自动裁剪音乐到视频时长
- ✅ 保持视频质量(copy 视频流)

## 依赖项

所有必需的依赖已包含在 `pyproject.toml` 中:
- `requests`: HTTP 请求
- `langchain`: LangChain 集成
- `cos-python-sdk-v5`: 腾讯云 COS SDK

额外系统依赖:
- `ffmpeg`: 用于视频音频处理(需单独安装)

## 运行测试

```bash
# 设置环境变量
export SUNO_API_TOKEN='your-token'

# 运行测试
python examples/test_suno_music.py
```

## 注意事项

1. **Suno API**: 确保有有效的 Suno API Token
2. **ffmpeg**: 视频 BGM 合成需要系统安装 ffmpeg
3. **生成时长**: 音乐生成通常需要 1-3 分钟,取决于服务器负载
4. **音乐时长**: Suno 生成的音乐时长可能固定(如 2-3 分钟),会自动裁剪到视频时长
5. **COS 上传**: 如果不需要上传到 COS,设置 `upload_to_cos=False`

## 后续改进建议

1. 支持音乐循环播放(当音乐短于视频时)
2. 添加音乐淡入效果
3. 支持多段音乐拼接
4. 添加音频均衡器调节
5. 支持更多音频格式

