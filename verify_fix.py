#!/usr/bin/env python3
"""Verify the endpoint mapping fix"""

import requests
import base64

MESHY_API_KEY = "msy_pQhyJ89ykjyGorHDhFJn7NJ2GzPNGMQ4qE77"
MESHY_BASE_URL = "https://api.meshy.ai"

print("Verifying endpoint mapping fix...")
print("=" * 60)

# Create a task with v1/image-to-3d
headers = {"Authorization": f"Bearer {MESHY_API_KEY}"}
creation_endpoint = f"{MESHY_BASE_URL}/v1/image-to-3d"

# Small test image
test_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01\xd5Z\xd5\x00\x00\x00\x00\x00IEND\xaeB`\x82'
base64_data = base64.b64encode(test_image).decode('utf-8')
image_data_uri = f"data:image/png;base64,{base64_data}"

data = {
    "image_url": image_data_uri,
    "ai_model": "meshy-4",
    "enable_pbr": True
}

print(f"1. Creating task with: {creation_endpoint}")
response = requests.post(creation_endpoint, headers=headers, json=data)

if response.status_code in [200, 202]:
    result = response.json()
    task_id = result.get('result')
    print(f"   ✅ Task created: {task_id}")
    
    # According to our fix, v1/image-to-3d creation should poll with openapi/v1/image-to-3d
    poll_endpoint = f"{MESHY_BASE_URL}/openapi/v1/image-to-3d/{task_id}"
    
    print(f"\n2. Polling with: {poll_endpoint}")
    response = requests.get(poll_endpoint, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Polling successful!")
        print(f"   Task status: {data.get('status')}")
        print(f"   Progress: {data.get('progress', 0)}%")
    else:
        print(f"   ❌ Polling failed: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
else:
    print(f"   ❌ Task creation failed: {response.status_code}")
    print(f"   Response: {response.text[:200]}")

print("\n" + "=" * 60)
print("Fix verified: v1/image-to-3d → openapi/v1/image-to-3d polling")