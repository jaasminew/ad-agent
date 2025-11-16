# SUNO API

## 生成音乐

```bash
curl --request POST \
  --url https://api.sunoapi.org/api/v1/generate \
  --header 'Authorization: Bearer <token>' \
  --header 'Content-Type: application/json' \
  --data '{
  "prompt": "一段平静舒缓的钢琴曲，带有柔和的旋律",
  "style": "古典",
  "title": "宁静钢琴冥想",
  "customMode": true,
  "instrumental": true,
  "personaId": "persona_123",
  "model": "V3_5",
  "negativeTags": "重金属, 强节奏鼓点",
  "vocalGender": "m",
  "styleWeight": 0.65,
  "weirdnessConstraint": 0.65,
  "audioWeight": 0.65,
  "callBackUrl": "https://api.example.com/callback"
}'
```

返回体：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "taskId": "5c79****be8e"
  }
}
```

## 获取音乐生成详情

```bash
curl --request GET \
  --url https://api.sunoapi.org/api/v1/generate/record-info \
  --header 'Authorization: Bearer <token>'
```

返回体：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "taskId": "5c79****be8e",
    "parentMusicId": "",
    "param": "{\"prompt\":\"A calm piano track\",\"style\":\"Classical\",\"title\":\"Peaceful Piano\",\"customMode\":true,\"instrumental\":true,\"model\":\"V3_5\"}",
    "response": {
      "taskId": "5c79****be8e",
      "sunoData": [
        {
          "id": "8551****662c",
          "audioUrl": "https://example.cn/****.mp3",
          "streamAudioUrl": "https://example.cn/****",
          "imageUrl": "https://example.cn/****.jpeg",
          "prompt": "[Verse] 夜晚城市 灯火辉煌",
          "modelName": "chirp-v3-5",
          "title": "钢铁侠",
          "tags": "electrifying, rock",
          "createTime": "2025-01-01 00:00:00",
          "duration": 198.44
        }
      ]
    },
    "status": "SUCCESS",
    "type": "GENERATE",
    "errorCode": null,
    "errorMessage": null
  }
}
```

状态说明：

- PENDING: 任务正在等待处理
- TEXT_SUCCESS: 歌词/文本生成已成功完成
- FIRST_SUCCESS: 第一首曲目生成已成功完成
- SUCCESS: 所有曲目已成功生成
- CREATE_TASK_FAILED: 创建生成任务失败
- GENERATE_AUDIO_FAILED: 生成音乐曲目失败
- CALLBACK_EXCEPTION: 回调过程中发生错误
- SENSITIVE_WORD_ERROR: 内容包含禁用词

​
开发者注意事项：

- 对于纯音乐曲目（instrumental=true），响应中不会包含歌词数据
- 可以使用此接口检查任务状态，而不必等待回调
