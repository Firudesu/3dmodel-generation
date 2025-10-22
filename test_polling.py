#!/usr/bin/env python3
"""Test script to verify correct polling endpoint"""

import requests
import json
import time

# Configuration
MESHY_API_KEY = "msy_pQhyJ89ykjyGorHDhFJn7NJ2GzPNGMQ4qE77"
MESHY_BASE_URL = "https://api.meshy.ai"

def test_polling():
    """Test polling endpoints with a real task"""
    headers = {"Authorization": f"Bearer {MESHY_API_KEY}"}
    
    # First, create a task to get a real task ID
    print("Creating a test task...")
    endpoint = f"{MESHY_BASE_URL}/v1/image-to-3d"
    
    # Create a small test image
    test_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01\xd5Z\xd5\x00\x00\x00\x00\x00IEND\xaeB`\x82'
    
    import base64
    base64_data = base64.b64encode(test_image).decode('utf-8')
    image_data_uri = f"data:image/png;base64,{base64_data}"
    
    data = {
        "image_url": image_data_uri,
        "ai_model": "meshy-4",
        "enable_pbr": True
    }
    
    response = requests.post(endpoint, headers=headers, json=data, timeout=5)
    if response.status_code not in [200, 202]:
        print(f"Failed to create task: {response.status_code} - {response.text}")
        return
    
    result = response.json()
    task_id = result.get('result')
    print(f"✅ Task created: {task_id}")
    print(f"Creation endpoint: {endpoint}")
    
    # Now test polling endpoints
    print("\n" + "=" * 60)
    print("Testing polling endpoints...")
    
    polling_endpoints = [
        f"{MESHY_BASE_URL}/v1/image-to-3d/{task_id}",
        f"{MESHY_BASE_URL}/openapi/v1/image-to-3d/{task_id}",
        f"{MESHY_BASE_URL}/v2/image-to-3d/{task_id}",
        f"{MESHY_BASE_URL}/v1/texture-to-3d/{task_id}",
    ]
    
    for poll_endpoint in polling_endpoints:
        print(f"\nTrying: {poll_endpoint}")
        try:
            response = requests.get(poll_endpoint, headers=headers, timeout=5)
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"  ✅ Success!")
                data = response.json()
                print(f"  Task status: {data.get('status', 'unknown')}")
                if 'progress' in data:
                    print(f"  Progress: {data.get('progress')}%")
                break
            elif response.status_code == 404:
                print(f"  ❌ 404 - Endpoint not found")
                print(f"  Response: {response.text[:200]}")
            else:
                print(f"  Response: {response.text[:200]}")
        except Exception as e:
            print(f"  Error: {e}")
    
    print("\n" + "=" * 60)
    print("Conclusion: The correct polling endpoint for v1/image-to-3d creation is likely the same path with task_id appended")

if __name__ == "__main__":
    test_polling()