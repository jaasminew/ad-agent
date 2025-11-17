# 可灵 AI API

## 通用信息

### 调用域名

https://api-beijing.klingai.com

### 接口鉴权

1. Step-1：获取 AccessKey + SecretKey
2. Step-2：您每次请求API的时候，需要按照固定加密方法生成API Token
    - 加密方法：遵循JWT（Json Web Token, RFC 7519）标准
    - JWT由三个部分组成：Header、Payload、Signature

```python
import time
import jwt

ak = "" # 填写access key
sk = "" # 填写secret key

def encode_jwt_token(ak, sk):
    headers = {
        "alg": "HS256",
        "typ": "JWT"
    }
    payload = {
        "iss": ak,
        "exp": int(time.time()) + 1800, # 有效时间，此处示例代表当前时间+1800s(30min)
        "nbf": int(time.time()) - 5 # 开始生效的时间，此处示例代表当前时间-5秒
    }
    token = jwt.encode(payload, sk, headers=headers)
    return token

api_token = encode_jwt_token(ak, sk)
print(api_token) # 打印生成的API_TOKEN
```

3. Step-3：用第二步生成的API Token组装成Authorization，填写到 Request Header 里
    - 组装方式：Authorization = “Bearer XXX”， 其中XXX填写第二步生成的API Token（注意Bearer跟XXX之间有空格）

### 错误码

| HTTP状态码 | 业务码 | 业务码定义 | 业务码解释 | 建议解决方案 |
| --- | --- | --- | --- | --- |
| 200 | 0 | 请求成功 | - | - |
| 401 | 1000 | 身份验证失败 | 身份验证失败 | 检查Authorization是否正确 |
| 401 | 1001 | 身份验证失败 | Authorization为空 | 在RequestHeader中填写正确的Authorization |
| 401 | 1002 | 身份验证失败 | Authorization值非法 | 在RequestHeader中填写正确的Authorization |
| 401 | 1003 | 身份验证失败 | Authorization未到有效时间 | 检查token的开始生效时间，等待生效或重新签发 |
| 401 | 1004 | 身份验证失败 | Authorization已失效 | 检查token的有效期，重新签发 |
| 429 | 1100 | 账户异常 | 账户异常 | 检查账户配置信息 |
| 429 | 1101 | 账户异常 | 账户欠费 (后付费场景) | 进行账户充值，确保余额充足 |
| 429 | 1102 | 账户异常 | 资源包已用完/已过期（预付费场景） | 购买额外的资源包，或开通后付费服务（如有） |
| 403 | 1103 | 账户异常 | 请求的资源无权限，如接口/模型 | 检查账户权限 |
| 400 | 1200 | 请求参数非法 | 请求参数非法 | 检查请求参数是否正确 |
| 400 | 1201 | 请求参数非法 | 参数非法，如key写错或value非法 | 参考返回体中message字段的具体信息，修改请求参数 |
| 404 | 1202 | 请求参数非法 | 请求的method无效 | 查看接口文档，使用正确的requestmethod |
| 404 | 1203 | 请求参数非法 | 请求的资源不存在，如模型 | 参考返回体中message字段的具体信息，修改请求参数 |
| 400 | 1300 | 触发策略 | 触发平台策略 | 检查是否触发平台策略 |
| 400 | 1301 | 触发策略 | 触发平台的内容安全策略 | 检查输入内容，修改后重新发起请求 |
| 429 | 1302 | 触发策略 | API请求过快，超过平台速率限制 | 降低请求频率、稍后重试，或联系客服增加限额 |
| 429 | 1303 | 触发策略 | 并发或QPS超出预付费资源包限制 | 降低请求频率、稍后重试，或联系客服增加限额 |
| 429 | 1304 | 触发策略 | 触发平台的IP白名单策略 | 联系客服 |
| 500 | 5000 | 内部错误 | 服务器内部错误 | 稍后重试，或联系客服 |
| 503 | 5001 | 内部错误 | 服务器暂时不可用，通常是在维护 | 稍后重试，或联系客服 |
| 504 | 5002 | 内部错误 | 服务器内部超时，通常是发生积压 | 稍后重试，或联系客服 |

## 图生视频

### 创建任务

| 网络协议 | 请求地址 | 请求方法 | 请求格式 | 响应格式 |
| --- | --- | --- | --- | --- |
| https | /v1/videos/image2video | POST | application/json | application/json |

#### 请求头

| 字段 | 值 | 描述 |
| --- | --- | --- |
| Content-Type | application/json | 数据交换格式 |
| Authorization | 鉴权信息，参考接口鉴权 | 鉴权信息，参考接口鉴权 |

```bash
curl --location --request POST 'https://api-beijing.klingai.com/v1/videos/image2video' \
--header 'Authorization: Bearer xxx' \
--header 'Content-Type: application/json' \
--data-raw '{
    "model_name": "kling-v1",
    "mode": "pro",
    "duration": "5",
    "image": "https://h2.inkwai.com/bs2/upload-ylab-stunt/se/ai_portal_queue_mmu_image_upscale_aiweb/3214b798-e1b4-4b00-b7af-72b5b0417420_raw_image_0.jpg",
    "prompt": "宇航员站起身走了",
    "cfg_scale": 0.5,
    "static_mask": "https://h2.inkwai.com/bs2/upload-ylab-stunt/ai_portal/1732888177/cOLNrShrSO/static_mask.png",
    "dynamic_masks": [
      {
        "mask": "https://h2.inkwai.com/bs2/upload-ylab-stunt/ai_portal/1732888130/WU8spl23dA/dynamic_mask_1.png",
        "trajectories": [
          {"x":279,"y":219},{"x":417,"y":65}
        ]
      }
    ]
}'
```

#### 响应体

```json
{
  "code": 0, //错误码；具体定义见错误码
  "message": "string", //错误信息
  "request_id": "string", //请求ID，系统生成，用于跟踪请求、排查问题
  "data": {
    "task_id": "string", //任务ID，系统生成
    "task_info": {
      //任务创建时的参数信息
      "external_task_id": "string" //客户自定义任务ID
    },
    "task_status": "string", //任务状态，枚举值：submitted（已提交）、processing（处理中）、succeed（成功）、failed（失败）
    "created_at": 1722769557708, //任务创建时间，Unix时间戳、单位ms
    "updated_at": 1722769557708 //任务更新时间，Unix时间戳、单位ms
  }
}
```

### 查询任务（单个）

| 网络协议 | 请求地址 | 请求方法 | 请求格式 | 响应格式 |
| --- | --- | --- | --- | --- |
| https | /v1/videos/image2video/{id} | GET | application/json | application/json |

#### 请求头

| 字段 | 值 | 描述 |
| --- | --- | --- |
| Content-Type | application/json | 数据交换格式 |
| Authorization | 鉴权信息，参考接口鉴权 | 鉴权信息，参考接口鉴权 |

#### 请求路径参数

| 字段 | 类型 | 必填 | 默认值 | 描述 |
| --- | --- | --- | --- | --- |
| task_id | string | 可选 | 无 | 图生视频的任务ID |
| 请求路径参数，直接将值填写在请求路径中，与external_task_id两种查询方式二选一 |
| external_task_id | string | 可选 | 无 | 图生视频的自定义任务ID |

创建任务时填写的external_task_id，与task_id两种查询方式二选一

#### 请求体

无

#### 响应体

```json
{
  "code": 0, //错误码；具体定义见错误码
  "message": "string", //错误信息
  "request_id": "string", //请求ID，系统生成，用于跟踪请求、排查问题
  "data":{
  	"task_id": "string", //任务ID，系统生成
    "task_status": "string", //任务状态，枚举值：submitted（已提交）、processing（处理中）、succeed（成功）、failed（失败）
    "task_status_msg": "string", //任务状态信息，当任务失败时展示失败原因（如触发平台的内容风控等）
    "task_info": { //任务创建时的参数信息
      "external_task_id": "string"//客户自定义任务ID
    },
    "task_result":{
      "videos":[
        {
        	"id": "string", //生成的视频ID；全局唯一
      		"url": "string", //生成视频的URL，例如https://p1.a.kwimgs.com/bs2/upload-ylab-stunt/special-effect/output/HB1_PROD_ai_web_46554461/-2878350957757294165/output.mp4（请注意，为保障信息安全，生成的图片/视频会在30天后被清理，请及时转存）
      		"duration": "string" //视频总时长，单位s
        }
      ]
    }
    "created_at": 1722769557708, //任务创建时间，Unix时间戳、单位ms
    "updated_at": 1722769557708, //任务更新时间，Unix时间戳、单位ms
  }
}
```