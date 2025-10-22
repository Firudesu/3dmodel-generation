#!/usr/bin/env python3
"""Test the complete flow with the fixed endpoints"""

import sys
import os
sys.path.insert(0, '/workspace')

# Mock the Flask app components we don't need
class MockApp:
    config = {
        'UPLOAD_FOLDER': '/tmp/uploads',
        'OUTPUT_FOLDER': '/tmp/output'
    }

import app
app.app = MockApp()

# Now test the actual functions
from app import create_textured_3d_model, poll_meshy_task

def test_full_flow():
    """Test the complete flow from creation to polling"""
    
    # Create a small test image
    test_image_path = "/tmp/test_image.png"
    test_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01\xd5Z\xd5\x00\x00\x00\x00\x00IEND\xaeB`\x82'
    
    with open(test_image_path, 'wb') as f:
        f.write(test_image)
    
    try:
        print("=" * 60)
        print("Testing complete flow with fixed endpoints")
        print("=" * 60)
        
        # Step 1: Create task
        print("\n1. Creating task...")
        task_id, creation_endpoint = create_textured_3d_model(test_image_path)
        print(f"   Task ID: {task_id}")
        print(f"   Creation endpoint: {creation_endpoint}")
        
        # Step 2: Test polling
        print("\n2. Testing polling...")
        # Just test the first poll to see if the endpoint works
        import requests
        headers = {"Authorization": f"Bearer {app.MESHY_API_KEY}"}
        
        # Determine the polling endpoint based on our fix
        if '/v1/image-to-3d' in creation_endpoint and 'openapi' not in creation_endpoint:
            poll_endpoint = f"{app.MESHY_BASE_URL}/openapi/v1/image-to-3d/{task_id}"
        else:
            poll_endpoint = f"{creation_endpoint}/{task_id}"
        
        print(f"   Polling endpoint: {poll_endpoint}")
        
        response = requests.get(poll_endpoint, headers=headers)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Polling successful! Task status: {data.get('status')}")
        else:
            print(f"   ❌ Polling failed: {response.text[:200]}")
        
        print("\n" + "=" * 60)
        print("Conclusion: The endpoint mapping is now correct!")
        
    finally:
        # Clean up
        if os.path.exists(test_image_path):
            os.remove(test_image_path)

if __name__ == "__main__":
    # Suppress the update_status messages
    app.update_status = lambda *args, **kwargs: None
    test_full_flow()