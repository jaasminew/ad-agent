"""Test script for concurrent task limit feature"""

import os
import requests
import time

# Set environment variable for testing
os.environ["MAX_CONCURRENT_TASKS"] = "2"

BASE_URL = "http://localhost:8000"

def create_task():
    """Create a test task"""
    payload = {
        "product_name": "Test Product",
        "brand_identity": "Test Brand",
        "must_have_shots": "Test shots",
        "product_images": "https://example.com/test.jpg",
        "video_format": "16:9",
        "max_shots": 3
    }
    
    response = requests.post(f"{BASE_URL}/v1/tasks", json=payload)
    return response

def main():
    print("Testing concurrent task limit...")
    print(f"MAX_CONCURRENT_TASKS = 2")
    print("-" * 60)
    
    # Create first task
    print("\n1. Creating first task...")
    resp1 = create_task()
    if resp1.status_code == 201:
        task1 = resp1.json()
        print(f"   ✓ Task 1 created: {task1['task_id']}")
    else:
        print(f"   ✗ Failed: {resp1.status_code} - {resp1.text}")
        return
    
    # Create second task
    print("\n2. Creating second task...")
    resp2 = create_task()
    if resp2.status_code == 201:
        task2 = resp2.json()
        print(f"   ✓ Task 2 created: {task2['task_id']}")
    else:
        print(f"   ✗ Failed: {resp2.status_code} - {resp2.text}")
        return
    
    # Try to create third task (should fail)
    print("\n3. Attempting to create third task (should fail with 429)...")
    resp3 = create_task()
    if resp3.status_code == 429:
        print(f"   ✓ Correctly rejected with HTTP 429")
        print(f"   Error message: {resp3.json()['detail']}")
    else:
        print(f"   ✗ Unexpected response: {resp3.status_code}")
        print(f"   Response: {resp3.text}")
    
    print("\n" + "-" * 60)
    print("Test completed!")
    print("\nNote: This test requires the API server to be running.")
    print("Start with: cd backend/service && python run.py")

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to API server.")
        print("Please start the server first: cd backend/service && python run.py")

