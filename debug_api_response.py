#!/usr/bin/env python3
"""Debug what the API actually returns when a task succeeds"""

import requests
import base64
import time
import json

MESHY_API_KEY = "msy_pQhyJ89ykjyGorHDhFJn7NJ2GzPNGMQ4qE77"
MESHY_BASE_URL = "https://api.meshy.ai"

def test_complete_flow():
    headers = {"Authorization": f"Bearer {MESHY_API_KEY}"}
    
    # Use the test image we created
    with open('/workspace/input/simple_test.jpg', 'rb') as f:
        image_data = f.read()
    
    print(f"Image size: {len(image_data)} bytes")
    
    # Convert to base64
    base64_data = base64.b64encode(image_data).decode('utf-8')
    image_data_uri = f"data:image/jpeg;base64,{base64_data}"
    
    # Create task
    endpoint = f"{MESHY_BASE_URL}/v1/image-to-3d"
    data = {
        "image_url": image_data_uri,
        "ai_model": "meshy-4",
        "enable_pbr": True
    }
    
    print("Creating task...")
    response = requests.post(endpoint, headers=headers, json=data, timeout=30)
    
    if response.status_code not in [200, 202]:
        print(f"Failed to create task: {response.text}")
        return
    
    result = response.json()
    task_id = result.get('result')
    print(f"✅ Task created: {task_id}")
    
    # Poll until complete
    poll_endpoint = f"{MESHY_BASE_URL}/openapi/v1/image-to-3d/{task_id}"
    print(f"Polling: {poll_endpoint}")
    print("Note: This URL requires API key in header, not accessible via browser")
    
    max_attempts = 120
    for attempt in range(max_attempts):
        time.sleep(5)
        
        response = requests.get(poll_endpoint, headers=headers)
        if response.status_code != 200:
            print(f"Poll error: {response.status_code}")
            break
        
        data = response.json()
        status = data.get('status')
        progress = data.get('progress', 0)
        
        if attempt % 6 == 0:  # Log every 30 seconds
            print(f"Status: {status}, Progress: {progress}%")
        
        if status == 'SUCCEEDED':
            print("\n" + "="*60)
            print("✅ TASK SUCCEEDED!")
            print("="*60)
            print("\nFull response data:")
            print(json.dumps(data, indent=2))
            
            # Check what URLs we got
            print("\n" + "="*60)
            print("Checking for downloadable content:")
            
            if 'model_urls' in data:
                print("\n✅ Found model_urls:")
                for key, url in data['model_urls'].items():
                    print(f"  - {key}: {url}")
                    
            if 'model_url' in data:
                print(f"\n✅ Found model_url: {data['model_url']}")
                
            if 'thumbnail_url' in data:
                print(f"\n✅ Found thumbnail: {data['thumbnail_url']}")
                
            # Try to download one of the URLs
            if 'model_urls' in data and data['model_urls']:
                first_type = list(data['model_urls'].keys())[0]
                test_url = data['model_urls'][first_type]
                print(f"\n🔍 Testing download of {first_type} from: {test_url[:100]}...")
                
                try:
                    download_response = requests.get(test_url, timeout=10)
                    print(f"Download response: {download_response.status_code}")
                    print(f"Content-Type: {download_response.headers.get('content-type')}")
                    print(f"Content-Length: {download_response.headers.get('content-length')} bytes")
                    
                    if download_response.status_code == 200:
                        print("✅ Download successful!")
                    else:
                        print(f"❌ Download failed: {download_response.text[:200]}")
                except Exception as e:
                    print(f"❌ Download error: {e}")
            
            break
            
        elif status == 'FAILED':
            print(f"\n❌ Task failed: {data.get('task_error')}")
            break
            
    else:
        print("\n⏱️ Task timed out")
    
    print("\n" + "="*60)
    print("Debug complete!")

if __name__ == "__main__":
    test_complete_flow()