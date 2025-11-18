"""测试客户端 - 演示如何使用 AD Agent API"""

import requests
import json
import time
from typing import Optional

API_BASE_URL = "http://localhost:8000/v1"


class ADAgentClient:
    """AD Agent API 客户端"""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
    
    def create_task(
        self,
        product_name: str,
        brand_identity: str,
        must_have_shots: str,
        product_images: str,
        video_format: str = "16:9",
        max_shots: int = 5,
    ) -> str:
        """创建任务
        
        Returns:
            task_id: 任务 ID
        """
        response = requests.post(
            f"{self.base_url}/tasks",
            json={
                "product_name": product_name,
                "brand_identity": brand_identity,
                "must_have_shots": must_have_shots,
                "product_images": product_images,
                "video_format": video_format,
                "max_shots": max_shots,
            },
        )
        response.raise_for_status()
        return response.json()["task_id"]
    
    def get_task(self, task_id: str) -> dict:
        """查询任务状态(非流式)
        
        Returns:
            任务状态
        """
        response = requests.get(f"{self.base_url}/tasks/{task_id}")
        response.raise_for_status()
        return response.json()
    
    def stream_task(self, task_id: str):
        """流式查询任务(SSE)
        
        Yields:
            事件字典
        """
        response = requests.get(
            f"{self.base_url}/tasks/{task_id}?stream=true",
            stream=True,
            headers={"Accept": "text/event-stream"},
        )
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                
                if line.startswith('event:'):
                    event_type = line.split(':', 1)[1].strip()
                elif line.startswith('data:'):
                    data = line.split(':', 1)[1].strip()
                    try:
                        data_json = json.loads(data)
                        yield {"event": event_type, "data": data_json}
                    except json.JSONDecodeError:
                        continue
    
    def cancel_task(self, task_id: str) -> dict:
        """取消任务
        
        Returns:
            取消结果
        """
        response = requests.post(f"{self.base_url}/tasks/{task_id}/cancel")
        response.raise_for_status()
        return response.json()
    
    def submit_assessment(
        self,
        task_id: str,
        stage: str,
        comment: Optional[str] = None,
    ) -> dict:
        """提交评估
        
        Returns:
            评估结果
        """
        response = requests.post(
            f"{self.base_url}/tasks/{task_id}/assessment",
            json={
                "task_id": task_id,
                "stage": stage,
                "comment": comment,
            },
        )
        response.raise_for_status()
        return response.json()


def example_non_streaming():
    """示例: 非流式查询"""
    print("=" * 80)
    print("示例 1: 非流式查询")
    print("=" * 80)
    
    client = ADAgentClient()
    
    # 创建任务
    print("\n1. 创建任务...")
    task_id = client.create_task(
        product_name="Polaroid Camera",
        brand_identity="Nostalgia, Artistic, Instant Sharing",
        must_have_shots="Friends sharing photos, Camera close-up",
        product_images="https://m.media-amazon.com/images/I/71a0-JzaiEL._AC_SL1500_.jpg",
        video_format="16:9",
        max_shots=3,
    )
    print(f"✓ 任务创建成功: {task_id}")
    
    # 轮询查询状态
    print("\n2. 查询任务状态...")
    while True:
        task = client.get_task(task_id)
        status = task["status"]
        stage = task["stage"]
        content_count = len(task["contents"])
        
        print(f"  状态: {status}, 阶段: {stage}, 内容块数: {content_count}")
        
        if status in ["completed", "failed", "cancelled"]:
            break
        
        time.sleep(5)
    
    # 打印最终结果
    print("\n3. 最终结果:")
    print(json.dumps(task, indent=2, ensure_ascii=False))


def example_streaming():
    """示例: 流式查询"""
    print("=" * 80)
    print("示例 2: 流式查询 (SSE)")
    print("=" * 80)
    
    client = ADAgentClient()
    
    # 创建任务
    print("\n1. 创建任务...")
    task_id = client.create_task(
        product_name="Polaroid Camera",
        brand_identity="Nostalgia, Artistic, Instant Sharing",
        must_have_shots="Friends sharing photos, Camera close-up",
        product_images="https://m.media-amazon.com/images/I/71a0-JzaiEL._AC_SL1500_.jpg",
        video_format="16:9",
        max_shots=3,
    )
    print(f"✓ 任务创建成功: {task_id}")
    
    # 流式接收更新
    print("\n2. 流式接收更新...")
    for event in client.stream_task(task_id):
        event_type = event["event"]
        data = event["data"]
        
        if event_type == "update":
            print(f"\n[更新] 状态: {data['status']}, 阶段: {data['stage']}")
        
        elif event_type == "content":
            content_type = data["type"]
            timestamp = data["timestamp"]
            
            if content_type == "llm_output":
                message = data["data"]["message"]
                print(f"\n[LLM 输出] {timestamp}")
                print(f"  消息: {message}")
            
            elif content_type == "tool_calling":
                tool_name = data["data"]["tool_name"]
                success = data["data"]["success"]
                print(f"\n[工具调用] {timestamp}")
                print(f"  工具: {tool_name}, 成功: {success}")
        
        elif event_type == "complete":
            print(f"\n[完成] 任务状态: {data['status']}")
            break
        
        elif event_type == "error":
            print(f"\n[错误] {data['error']}")
            break


def example_cancel_task():
    """示例: 取消任务"""
    print("=" * 80)
    print("示例 3: 取消任务")
    print("=" * 80)
    
    client = ADAgentClient()
    
    # 创建任务
    print("\n1. 创建任务...")
    task_id = client.create_task(
        product_name="Polaroid Camera",
        brand_identity="Nostalgia, Artistic, Instant Sharing",
        must_have_shots="Friends sharing photos, Camera close-up",
        product_images="https://m.media-amazon.com/images/I/71a0-JzaiEL._AC_SL1500_.jpg",
        video_format="16:9",
        max_shots=3,
    )
    print(f"✓ 任务创建成功: {task_id}")
    
    # 等待一会儿
    print("\n2. 等待 10 秒...")
    time.sleep(10)
    
    # 取消任务
    print("\n3. 取消任务...")
    result = client.cancel_task(task_id)
    print(f"✓ 取消结果: {result}")
    
    # 检查状态
    print("\n4. 检查最终状态...")
    time.sleep(2)
    task = client.get_task(task_id)
    print(f"  状态: {task['status']}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python test_client.py [non_streaming|streaming|cancel]")
        sys.exit(1)
    
    mode = sys.argv[1]
    
    if mode == "non_streaming":
        example_non_streaming()
    elif mode == "streaming":
        example_streaming()
    elif mode == "cancel":
        example_cancel_task()
    else:
        print(f"未知模式: {mode}")
        sys.exit(1)

