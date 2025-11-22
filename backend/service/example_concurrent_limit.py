"""并发限制示例

演示如何处理并发任务限制和 HTTP 429 错误。
"""

import requests
import time
from typing import Optional


class ADAgentClient:
    """AD Agent API 客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def create_task(
        self,
        product_name: str,
        brand_identity: str,
        product_images: str,
        video_format: str = "16:9",
        max_shots: int = 3,
        must_have_shots: str = "",
    ) -> Optional[str]:
        """创建任务
        
        Returns:
            task_id 如果成功, None 如果达到并发限制
        """
        payload = {
            "product_name": product_name,
            "brand_identity": brand_identity,
            "must_have_shots": must_have_shots,
            "product_images": product_images,
            "video_format": video_format,
            "max_shots": max_shots,
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/v1/tasks",
                json=payload,
                timeout=10,
            )
            
            if response.status_code == 201:
                task_id = response.json()["task_id"]
                print(f"✓ 任务创建成功: {task_id}")
                return task_id
            
            elif response.status_code == 429:
                error_msg = response.json().get("detail", "并发限制")
                print(f"⚠ 达到并发限制: {error_msg}")
                return None
            
            else:
                print(f"✗ 创建失败: {response.status_code} - {response.text}")
                return None
        
        except requests.exceptions.RequestException as e:
            print(f"✗ 请求失败: {e}")
            return None
    
    def get_task_status(self, task_id: str) -> dict:
        """查询任务状态"""
        response = requests.get(f"{self.base_url}/v1/tasks/{task_id}")
        return response.json()


def example_with_retry():
    """示例: 带重试的任务创建"""
    print("=" * 60)
    print("示例 1: 带重试机制的任务创建")
    print("=" * 60)
    
    client = ADAgentClient()
    
    # 任务参数
    task_config = {
        "product_name": "智能手表",
        "brand_identity": "科技, 健康, 时尚",
        "product_images": "https://example.com/watch.jpg",
        "video_format": "9:16",
        "max_shots": 3,
    }
    
    # 尝试创建任务,如果达到限制则等待重试
    max_retries = 5
    retry_delay = 10  # 秒
    
    for attempt in range(max_retries):
        print(f"\n尝试 {attempt + 1}/{max_retries}...")
        task_id = client.create_task(**task_config)
        
        if task_id:
            print(f"\n✓ 任务创建成功!")
            print(f"  任务ID: {task_id}")
            return task_id
        
        if attempt < max_retries - 1:
            print(f"  等待 {retry_delay} 秒后重试...")
            time.sleep(retry_delay)
    
    print("\n✗ 达到最大重试次数,创建失败")
    return None


def example_batch_with_limit():
    """示例: 批量创建任务(考虑并发限制)"""
    print("\n" + "=" * 60)
    print("示例 2: 批量创建任务(智能等待)")
    print("=" * 60)
    
    client = ADAgentClient()
    
    # 要创建的任务列表
    tasks = [
        {"product_name": "产品 A", "brand_identity": "品牌 A"},
        {"product_name": "产品 B", "brand_identity": "品牌 B"},
        {"product_name": "产品 C", "brand_identity": "品牌 C"},
        {"product_name": "产品 D", "brand_identity": "品牌 D"},
        {"product_name": "产品 E", "brand_identity": "品牌 E"},
    ]
    
    created_tasks = []
    pending_tasks = tasks.copy()
    
    while pending_tasks:
        task_config = pending_tasks[0]
        task_config.update({
            "product_images": "https://example.com/product.jpg",
            "video_format": "16:9",
            "max_shots": 3,
        })
        
        task_id = client.create_task(**task_config)
        
        if task_id:
            # 成功创建,移除队列
            created_tasks.append(task_id)
            pending_tasks.pop(0)
            print(f"  进度: {len(created_tasks)}/{len(tasks)}")
        else:
            # 达到限制,等待后重试
            print(f"  等待 10 秒后继续...")
            time.sleep(10)
    
    print(f"\n✓ 所有任务创建完成!")
    print(f"  成功创建: {len(created_tasks)} 个任务")
    for i, task_id in enumerate(created_tasks, 1):
        print(f"    {i}. {task_id}")


def example_check_capacity():
    """示例: 检查系统容量"""
    print("\n" + "=" * 60)
    print("示例 3: 测试并发限制")
    print("=" * 60)
    
    client = ADAgentClient()
    
    # 快速创建多个任务,找出限制
    task_ids = []
    for i in range(10):
        task_id = client.create_task(
            product_name=f"测试产品 {i+1}",
            brand_identity="测试品牌",
            product_images="https://example.com/test.jpg",
        )
        
        if task_id:
            task_ids.append(task_id)
        else:
            print(f"\n发现并发限制: {len(task_ids)} 个任务")
            break
        
        time.sleep(0.5)  # 短暂延迟
    
    if len(task_ids) == 10:
        print(f"\n未达到限制,成功创建 {len(task_ids)} 个任务")


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║         AD Agent 并发限制处理示例                          ║
╚════════════════════════════════════════════════════════════╝

本脚本演示如何处理 API 的并发任务限制。

前置条件:
1. 服务已启动: cd backend/service && python run.py
2. 设置环境变量: MAX_CONCURRENT_TASKS=3 (用于测试)

""")
    
    try:
        # 示例 1: 带重试的任务创建
        example_with_retry()
        
        # 示例 2: 批量创建任务
        # example_batch_with_limit()
        
        # 示例 3: 检查系统容量
        # example_check_capacity()
        
    except KeyboardInterrupt:
        print("\n\n✓ 用户中断")
    except Exception as e:
        print(f"\n✗ 错误: {e}")

