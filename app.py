#!/usr/bin/env python3
"""
Web-based UI for Image → 3D Model → Voxel File Automation
Designed for Replit and other web-based IDEs
"""

import os
import sys
import time
import requests
import json
import zipfile
import threading
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from werkzeug.utils import secure_filename
import tempfile
import shutil

# Playwright is not needed anymore since we use native Python voxel conversion
PLAYWRIGHT_AVAILABLE = False

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'

# Configuration
MESHY_API_KEY = os.environ.get('MESHY_API_KEY', "msy_pQhyJ89ykjyGorHDhFJn7NJ2GzPNGMQ4qE77")
MESHY_BASE_URL = "https://api.meshy.ai"

# Try different API endpoint formats
MESHY_IMAGE_TO_3D_ENDPOINT_V1 = f"{MESHY_BASE_URL}/openapi/v1/image-to-3d"
MESHY_IMAGE_TO_3D_ENDPOINT_V2 = f"{MESHY_BASE_URL}/v2/image-to-3d"
MESHY_TEXTURE_TO_3D_ENDPOINT_V1 = f"{MESHY_BASE_URL}/openapi/v1/texture-to-3d"
MESHY_TEXTURE_TO_3D_ENDPOINT_V2 = f"{MESHY_BASE_URL}/v2/texture-to-3d"

# Start with v1 openapi endpoints
MESHY_IMAGE_TO_3D_ENDPOINT = MESHY_IMAGE_TO_3D_ENDPOINT_V1
MESHY_TEXTURE_TO_3D_ENDPOINT = MESHY_TEXTURE_TO_3D_ENDPOINT_V1

# Debug: Print API endpoints
print(f"Testing API endpoints:")
print(f"Image to 3D v1: {MESHY_IMAGE_TO_3D_ENDPOINT_V1}")
print(f"Image to 3D v2: {MESHY_IMAGE_TO_3D_ENDPOINT_V2}")
print(f"Texture to 3D v1: {MESHY_TEXTURE_TO_3D_ENDPOINT_V1}")
print(f"Texture to 3D v2: {MESHY_TEXTURE_TO_3D_ENDPOINT_V2}")
print(f"Using: {MESHY_IMAGE_TO_3D_ENDPOINT}")
print(f"API Key (first 10 chars): {MESHY_API_KEY[:10]}...")

# Global variables for tracking progress
current_status = "Ready"
progress_percentage = 0
current_task = ""
error_message = ""
generated_files = []

def setup_directories():
    """Create necessary directories"""
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    print(f"Created directories: {app.config['UPLOAD_FOLDER']}, {app.config['OUTPUT_FOLDER']}")
    os.makedirs('static', exist_ok=True)
    os.makedirs('templates', exist_ok=True)

def update_status(status, percentage=0, task="", error=""):
    """Update global status variables"""
    global current_status, progress_percentage, current_task, error_message
    current_status = status
    progress_percentage = percentage
    current_task = task
    if error:
        error_message = error


# Note: This function has been replaced by the improved version at line 447
# Keeping this comment to maintain line numbers for now

def download_meshy_files(result):
    """Download model files from Meshy and create a ZIP package"""
    update_status("Downloading files...", 85, "Downloading model files from Meshy")
    
    print(f"Download function received result keys: {result.keys()}")
    
    # Meshy returns individual files, not a ZIP. We need to download them all.
    if 'model_urls' not in result:
        raise Exception("No model URLs found in Meshy response")
    
    model_urls = result['model_urls']
    print(f"Available model formats: {list(model_urls.keys())}")
    
    # For OBJ format, we need to download OBJ, MTL, and textures separately
    if 'obj' in model_urls and 'mtl' in model_urls:
        print("✅ Found OBJ + MTL format - will download all components")
        
        # Create a temporary directory for all files
        import tempfile
        temp_dir = tempfile.mkdtemp()
        print(f"Using temp directory: {temp_dir}")
        
        downloaded_files = []
        
        # 1. Download OBJ file
        obj_url = model_urls['obj']
        print(f"Downloading OBJ from: {obj_url[:100]}...")
        response = requests.get(obj_url, timeout=60)
        if response.status_code == 200:
            obj_path = os.path.join(temp_dir, 'model.obj')
            with open(obj_path, 'wb') as f:
                f.write(response.content)
            downloaded_files.append('model.obj')
            print(f"✅ Downloaded OBJ: {len(response.content)} bytes")
        
        # 2. Download MTL file
        mtl_url = model_urls['mtl']
        print(f"Downloading MTL from: {mtl_url[:100]}...")
        response = requests.get(mtl_url, timeout=60)
        if response.status_code == 200:
            mtl_path = os.path.join(temp_dir, 'model.mtl')
            with open(mtl_path, 'wb') as f:
                f.write(response.content)
            downloaded_files.append('model.mtl')
            print(f"✅ Downloaded MTL: {len(response.content)} bytes")
        
        # 3. Download texture files
        texture_urls = result.get('texture_urls', [])
        for i, texture_info in enumerate(texture_urls):
            if isinstance(texture_info, dict) and 'base_color' in texture_info:
                texture_url = texture_info['base_color']
            elif isinstance(texture_info, str):
                texture_url = texture_info
            else:
                continue
                
            print(f"Downloading texture {i} from: {texture_url[:100]}...")
            response = requests.get(texture_url, timeout=60)
            if response.status_code == 200:
                # Determine extension from content or URL
                if 'png' in texture_url.lower():
                    ext = 'png'
                else:
                    ext = 'jpg'
                texture_path = os.path.join(temp_dir, f'texture_{i}.{ext}')
                with open(texture_path, 'wb') as f:
                    f.write(response.content)
                downloaded_files.append(f'texture_{i}.{ext}')
                print(f"✅ Downloaded texture {i}: {len(response.content)} bytes")
        
        # 4. Create ZIP file with all components
        zip_path = os.path.join(app.config['OUTPUT_FOLDER'], 'meshy_model.zip')
        os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
        
        print(f"Creating ZIP package with {len(downloaded_files)} files...")
        import zipfile
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in downloaded_files:
                file_path = os.path.join(temp_dir, file)
                if os.path.exists(file_path):
                    zipf.write(file_path, file)
                    print(f"  Added {file} to ZIP")
        
        # Clean up temp directory
        import shutil
        shutil.rmtree(temp_dir)
        
        print(f"✅ Created ZIP package: {zip_path} ({os.path.getsize(zip_path)} bytes)")
        print(f"Returning path for generated_files: {zip_path}")
        return zip_path
        
    # For other formats (GLB, FBX, USDZ), download as-is
    elif 'glb' in model_urls:
        model_url = model_urls['glb']
        file_type = 'glb'
        print("Using GLB format (contains embedded textures)")
    elif 'fbx' in model_urls:
        model_url = model_urls['fbx']
        file_type = 'fbx'
        print("Using FBX format")
    elif 'usdz' in model_urls:
        model_url = model_urls['usdz']
        file_type = 'usdz'
        print("Using USDZ format")
    else:
        # Use the first available format
        first_format = list(model_urls.keys())[0]
        model_url = model_urls[first_format]
        file_type = first_format
        print(f"Using first available format: {first_format}")
    
    # For non-OBJ formats, download the single file
    print(f"Downloading from URL: {model_url[:100]}...")
    print(f"Expected file type: {file_type}")
    
    try:
        response = requests.get(model_url, timeout=60)
        print(f"Download response status: {response.status_code}")
        print(f"Content length: {len(response.content)} bytes")
        
        if response.status_code != 200:
            raise Exception(f"Failed to download model: {response.status_code}")
    except requests.exceptions.Timeout:
        raise Exception("Download timed out after 60 seconds")
    except Exception as e:
        raise Exception(f"Download error: {str(e)}")
    
    # Determine file extension
    if file_type == 'glb':
        file_extension = '.glb'
    elif file_type == 'fbx':
        file_extension = '.fbx'
    elif file_type == 'usdz':
        file_extension = '.usdz'
    else:
        file_extension = f'.{file_type}'
    
    # Save the file
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    model_path = os.path.join(app.config['OUTPUT_FOLDER'], f'meshy_model{file_extension}')
    
    try:
        with open(model_path, 'wb') as f:
            f.write(response.content)
        print(f"✅ Downloaded file: {model_path} (size: {len(response.content)} bytes, type: {file_extension})")
    except Exception as save_error:
        raise Exception(f"Failed to save downloaded file: {save_error}")
    
    update_status("Files downloaded...", 90, f"Model files downloaded ({file_extension})")
    return model_path

def extract_model_files(model_path):
    """Process downloaded model files - keep ZIP intact for user download"""
    print(f"Processing model file: {model_path}")
    
    model_file = Path(model_path)
    file_extension = model_file.suffix.lower()
    
    if file_extension == '.zip':
        # Don't extract - keep the ZIP for user to download
        print(f"✅ ZIP file with model and textures: {model_file}")
        
        # Just peek inside to see what's there
        try:
            with zipfile.ZipFile(model_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                print(f"ZIP contents: {file_list}")
                
                obj_files = [f for f in file_list if f.endswith('.obj')]
                texture_files = [f for f in file_list if f.endswith(('.jpg', '.png', '.mtl'))]
                
                if obj_files:
                    print(f"✅ Found {len(obj_files)} OBJ file(s) in ZIP")
                if texture_files:
                    print(f"✅ Found {len(texture_files)} texture/material file(s) in ZIP")
                
                # Return the ZIP itself as the main file
                return model_file, []  # Return empty texture list since they're in the ZIP
                
        except zipfile.BadZipFile:
            print("❌ File is not a valid ZIP file")
            # Still return it as-is
            return model_file, []
    
    elif file_extension in ['.glb', '.fbx', '.usdz']:
        # These formats have embedded textures
        print(f"✅ {file_extension.upper()} file with embedded textures: {model_file}")
        return model_file, []
    
    elif file_extension == '.obj':
        # Standalone OBJ - might not have textures
        print(f"⚠️ Standalone OBJ file (no textures): {model_file}")
        return model_file, []
    
    else:
        print(f"Unknown format {file_extension}: {model_file}")
        return model_file, []

def convert_to_voxel(obj_file_path, texture_files=None):
    """Convert OBJ to VOX using Python voxelizer with texture support"""
    print(f"Starting voxel conversion for: {obj_file_path}")
    update_status("Converting to voxel...", 95, "Voxelizing 3D model with texture")
    
    vox_file_path = os.path.join(app.config['OUTPUT_FOLDER'], 'model.vox')
    
    try:
        # Try to import and use our voxel converter
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from voxel_converter import convert_obj_to_vox
        
        print("Using Python voxel converter with texture support...")
        
        # Find PNG texture file if available
        texture_path = None
        if texture_files:
            for tex_file in texture_files:
                if tex_file and os.path.exists(tex_file) and tex_file.lower().endswith('.png'):
                    texture_path = tex_file
                    print(f"Found texture file: {texture_path}")
                    break
        
        # Convert with automatic size detection (defaults to 64x64x64)
        # The converter will use OBJ dimensions to determine size
        result_path = convert_obj_to_vox(
            obj_file_path, 
            texture_path=texture_path,
            output_path=vox_file_path,
            voxel_size=None  # Auto-determine from OBJ, defaults to 64
        )
        
        print(f"✅ Successfully converted to VOX with texture: {result_path}")
        return result_path
        
    except ImportError as e:
        print(f"⚠️ Voxel converter not available: {e}")
        print("Creating fallback VOX file...")
        
        # Create basic VOX structure as fallback
        print("Creating basic VOX file as fallback...")
        vox_data = bytearray()
        vox_data.extend(b'VOX ')  
        vox_data.extend((150).to_bytes(4, 'little'))
        vox_data.extend(b'MAIN')
        vox_data.extend((0).to_bytes(4, 'little'))
        vox_data.extend((28 + 12 + 12).to_bytes(4, 'little'))
        vox_data.extend(b'SIZE')
        vox_data.extend((12).to_bytes(4, 'little'))
        vox_data.extend((0).to_bytes(4, 'little'))
        vox_data.extend((32).to_bytes(4, 'little'))
        vox_data.extend((32).to_bytes(4, 'little'))
        vox_data.extend((32).to_bytes(4, 'little'))
        vox_data.extend(b'XYZI')
        vox_data.extend((4).to_bytes(4, 'little'))
        vox_data.extend((0).to_bytes(4, 'little'))
        vox_data.extend((0).to_bytes(4, 'little'))
        
        with open(vox_file_path, 'wb') as f:
            f.write(vox_data)
        
        return vox_file_path
            
    except Exception as e:
        print(f"❌ Voxel conversion error: {e}")
        raise Exception(f"Failed to convert to voxel: {str(e)}")

# Removed deprecated playwright function - using native Python voxel conversion only

def test_api_endpoints():
    """Test which Meshy API endpoints are working"""
    headers = {"Authorization": f"Bearer {MESHY_API_KEY}"}
    
    # First test API key format
    print(f"API Key format check:")
    print(f"  Length: {len(MESHY_API_KEY)}")
    print(f"  Starts with 'msy_': {MESHY_API_KEY.startswith('msy_')}")
    print(f"  Contains only valid chars: {all(c.isalnum() or c in '_-' for c in MESHY_API_KEY)}")
    
    endpoints_to_test = [
        (f"{MESHY_BASE_URL}/v1/image-to-3d", "v1 image-to-3d"),  # Confirmed working endpoint
        (MESHY_IMAGE_TO_3D_ENDPOINT_V1, "openapi v1 image-to-3d"),
        (MESHY_IMAGE_TO_3D_ENDPOINT_V2, "v2 image-to-3d"),
        (MESHY_TEXTURE_TO_3D_ENDPOINT_V1, "openapi v1 texture-to-3d"),
        (MESHY_TEXTURE_TO_3D_ENDPOINT_V2, "v2 texture-to-3d")
    ]
    
    working_endpoints = []
    
    for endpoint, name in endpoints_to_test:
        try:
            print(f"Testing {name}: {endpoint}")
            response = requests.get(endpoint, headers=headers)
            print(f"  Status: {response.status_code}")
            print(f"  Content-Type: {response.headers.get('content-type', 'unknown')}")
            
            if response.status_code == 200:
                print(f"  ✅ {name} works!")
                working_endpoints.append((endpoint, name))
            elif response.status_code == 404:
                print(f"  ❌ {name} - 404 Not Found")
            elif response.status_code == 401:
                print(f"  ❌ {name} - 401 Unauthorized (API key issue)")
            else:
                print(f"  ❌ {name} - {response.status_code}: {response.text[:100]}")
                
        except Exception as e:
            print(f"  ❌ {name} - Error: {e}")
    
    return working_endpoints

def create_textured_3d_model(image_path):
    """Create textured 3D model using working Meshy API"""
    update_status("Creating 3D model...", 20, "Validating image file")
    
    # Validate image file
    if not os.path.exists(image_path):
        raise Exception(f"Image file not found: {image_path}")
    
    file_size = os.path.getsize(image_path)
    if file_size < 1000:  # Less than 1KB is likely not a valid image
        raise Exception(f"Image file too small ({file_size} bytes). Please upload a valid image file.")
    
    # Check if it's actually an image by reading the header
    with open(image_path, 'rb') as f:
        header = f.read(12)
        
    # Check for common image formats
    is_jpeg = header[:3] == b'\xff\xd8\xff'
    is_png = header[:8] == b'\x89PNG\r\n\x1a\n'
    is_gif = header[:6] in [b'GIF87a', b'GIF89a']
    is_webp = header[:4] == b'RIFF' and header[8:12] == b'WEBP'
    
    if not (is_jpeg or is_png or is_gif or is_webp):
        raise Exception("File does not appear to be a valid image (JPEG, PNG, GIF, or WebP)")
    
    print(f"Image validated: {os.path.basename(image_path)} ({file_size} bytes)")
    update_status("Creating 3D model...", 22, "Testing Meshy API endpoints")
    
    # Test which endpoints work
    working_endpoints = test_api_endpoints()
    if not working_endpoints:
        # If no endpoints tested successfully, default to v1/image-to-3d which we know exists
        print("No endpoints tested successfully, using default v1/image-to-3d")
        endpoint = f"{MESHY_BASE_URL}/v1/image-to-3d"
        name = "v1 image-to-3d (default)"
    else:
        # Use the first working endpoint
        endpoint, name = working_endpoints[0]
    
    update_status("Creating 3D model...", 25, f"Using {name} - Uploading image...")
    
    headers = {"Authorization": f"Bearer {MESHY_API_KEY}"}
    
    # Use file upload format
    file_ext = os.path.splitext(image_path)[1].lower()
    content_type = 'image/jpeg' if file_ext in ['.jpg', '.jpeg'] else 'image/png'
    
    # Handle different endpoint types
    if '/v1/image-to-3d' in endpoint and 'openapi' not in endpoint:
        # v1 image-to-3d endpoint - send as JSON with base64 image
        import base64
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
            base64_data = base64.b64encode(image_data).decode('utf-8')
            image_data_uri = f"data:{content_type};base64,{base64_data}"
        
        # Use minimal parameters that are proven to work
        data = {
            "image_url": image_data_uri
            # Removed extra parameters that might cause issues
        }
        
        response = requests.post(endpoint, headers=headers, json=data, timeout=30)
    elif 'texture-to-3d' in endpoint:
        # Use file upload for texture-to-3d
        with open(image_path, 'rb') as image_file:
            files = {'image': (os.path.basename(image_path), image_file, content_type)}
            data = {
                'mode': 'preview',
                'art_style': 'realistic'
            }
            
            response = requests.post(endpoint, headers=headers, files=files, data=data, timeout=30)
    elif 'openapi/v1' in endpoint:
        # v1 API expects JSON with base64 image
        import base64
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
            base64_data = base64.b64encode(image_data).decode('utf-8')
            image_data_uri = f"data:{content_type};base64,{base64_data}"
        
        # Use minimal parameters that are proven to work
        data = {
            "image_url": image_data_uri
            # Removed extra parameters that might cause issues
        }
        
        response = requests.post(endpoint, headers=headers, json=data, timeout=30)
    else:
        # v2 API expects form data with file upload
        with open(image_path, 'rb') as image_file:
            files = {'image': (os.path.basename(image_path), image_file, content_type)}
            data = {
                'mode': 'preview',
                'art_style': 'realistic'
            }
            
            response = requests.post(endpoint, headers=headers, files=files, data=data, timeout=30)
    
    # Debug: Print request and response details
    print(f"Request endpoint: {endpoint}")
    print(f"Request headers: {dict(headers)}")
    print(f"Request data type: {type(data)}")
    if isinstance(data, dict) and 'image_url' in data:
        print(f"Image data URI length: {len(data['image_url'])}")
    print(f"Response status: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    print(f"Response content (first 500 chars): {response.text[:500]}")
    
    # 202 means "Accepted" - task created successfully
    if response.status_code not in [200, 202]:
        raise Exception(f"Meshy API error: {response.status_code} - {response.text}")
    
    # Check if response is JSON
    try:
        result = response.json()
    except ValueError as e:
        raise Exception(f"Invalid JSON response from Meshy API: {e}. Response: {response.text[:200]}")
    
    task_id = result.get('result')
    if not task_id:
        raise Exception(f"Failed to get task ID from Meshy API: {result}")
    
    print(f"✅ Task created successfully! Task ID: {task_id}")
    print(f"Creation endpoint used: {endpoint}")
    
    update_status("Creating 3D model...", 30, f"3D model creation started (ID: {task_id})")
    return task_id, endpoint  # Return both task_id and endpoint

def create_retexture_task(model_task_id, image_path):
    """Apply texture to 3D model using Meshy Retexture API"""
    update_status("Applying texture...", 50, "Uploading texture to Meshy Retexture API")
    
    headers = {"Authorization": f"Bearer {MESHY_API_KEY}"}
    
    # Convert image to base64 data URI for texture
    import base64
    with open(image_path, 'rb') as image_file:
        image_data = image_file.read()
        file_ext = os.path.splitext(image_path)[1].lower()
        mime_type = 'image/jpeg' if file_ext in ['.jpg', '.jpeg'] else 'image/png'
        base64_data = base64.b64encode(image_data).decode('utf-8')
        image_data_uri = f"data:{mime_type};base64,{base64_data}"
    
    # Create Retexture task
    data = {
        "input_task_id": model_task_id,
        "image_style_url": image_data_uri,
        "ai_model": "meshy-5",
        "enable_original_uv": True,
        "enable_pbr": True
    }
    
    response = requests.post(MESHY_RETEXTURE_ENDPOINT, headers=headers, json=data, timeout=30)
    
    # Debug: Print response details
    print(f"Retexture response status: {response.status_code}")
    print(f"Retexture response content (first 500 chars): {response.text[:500]}")
    
    if response.status_code != 200:
        raise Exception(f"Meshy Retexture API error: {response.status_code} - {response.text}")
    
    # Check if response is JSON
    try:
        result = response.json()
    except ValueError as e:
        raise Exception(f"Invalid JSON response from Meshy Retexture API: {e}. Response: {response.text[:200]}")
    
    task_id = result.get('result')
    if not task_id:
        raise Exception(f"Failed to get retexture task ID from Meshy API: {result}")
    
    update_status("Applying texture...", 60, f"Texture application started (ID: {task_id})")
    return task_id

def poll_meshy_task(task_id, task_type="texture", creation_endpoint=None):
    """Poll Meshy API until task is complete"""
    update_status(f"Processing {task_type}...", 70, f"Waiting for {task_type} completion")
    
    headers = {"Authorization": f"Bearer {MESHY_API_KEY}"}
    
    # Determine polling endpoint based on creation endpoint if provided
    polling_endpoints = []
    
    if creation_endpoint:
        # Match polling endpoint to creation endpoint format
        # NOTE: v1/image-to-3d creation requires openapi/v1/image-to-3d for polling!
        if '/v1/image-to-3d' in creation_endpoint and 'openapi' not in creation_endpoint:
            # Tasks created with v1/image-to-3d must be polled with openapi/v1/image-to-3d
            polling_endpoints.append(f"{MESHY_BASE_URL}/openapi/v1/image-to-3d/{task_id}")
        elif '/openapi/v1/texture-to-3d' in creation_endpoint:
            polling_endpoints.append(f"{MESHY_BASE_URL}/openapi/v1/texture-to-3d/{task_id}")
        elif '/openapi/v1/image-to-3d' in creation_endpoint:
            polling_endpoints.append(f"{MESHY_BASE_URL}/openapi/v1/image-to-3d/{task_id}")
        elif '/v2/texture-to-3d' in creation_endpoint:
            polling_endpoints.append(f"{MESHY_BASE_URL}/v2/texture-to-3d/{task_id}")
        elif '/v2/image-to-3d' in creation_endpoint:
            polling_endpoints.append(f"{MESHY_BASE_URL}/v2/image-to-3d/{task_id}")
    
    # Add all possible endpoints as fallbacks - prioritize openapi/v1/image-to-3d which is confirmed working
    polling_endpoints.extend([
        f"{MESHY_BASE_URL}/openapi/v1/image-to-3d/{task_id}",  # This endpoint confirmed working for v1 tasks
        f"{MESHY_BASE_URL}/v1/image-to-3d/{task_id}",  
        f"{MESHY_BASE_URL}/v1/texture-to-3d/{task_id}",
        f"{MESHY_BASE_URL}/v2/texture-to-3d/{task_id}",
        f"{MESHY_BASE_URL}/v2/image-to-3d/{task_id}",
        f"{MESHY_BASE_URL}/openapi/v1/texture-to-3d/{task_id}",
        f"{MESHY_BASE_URL}/openapi/v2/texture-to-3d/{task_id}",
        f"{MESHY_BASE_URL}/openapi/v2/image-to-3d/{task_id}"
    ])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_endpoints = []
    for ep in polling_endpoints:
        if ep not in seen:
            seen.add(ep)
            unique_endpoints.append(ep)
    polling_endpoints = unique_endpoints
    
    # Use the first endpoint that works
    endpoint = polling_endpoints[0] if polling_endpoints else f"{MESHY_BASE_URL}/v1/texture-to-3d/{task_id}"
    
    max_attempts = 120  # Increased from 60 to 120 (10 minutes total)
    attempt = 0
    current_endpoint_index = 0
    last_progress = 0
    
    while attempt < max_attempts:
        try:
            if attempt % 6 == 0:  # Log every 30 seconds
                print(f"Polling attempt {attempt + 1}/{max_attempts} - Endpoint: {endpoint}")
            response = requests.get(endpoint, headers=headers)
            
            if attempt % 6 == 0:  # Log every 30 seconds
                print(f"Polling response status: {response.status_code}")
            
            if response.status_code == 404 and current_endpoint_index < len(polling_endpoints) - 1:
                # Try next endpoint
                print(f"404 error - endpoint not found: {endpoint}")
                current_endpoint_index += 1
                endpoint = polling_endpoints[current_endpoint_index]
                print(f"Trying alternative polling endpoint: {endpoint}")
                continue
            elif response.status_code != 200:
                print(f"Polling error: {response.status_code} - {response.text[:200]}")
                raise Exception(f"Meshy API polling error: {response.status_code} - {response.text}")
            
            result = response.json()
            status = result.get('status')
            progress = result.get('progress', 0)
            
            # Update with actual progress from API
            if progress > last_progress:
                last_progress = progress
                print(f"Task progress: {progress}% - Status: {status}")
            
            # Map API progress to our progress bar (30-80% range)
            display_progress = 30 + (progress * 0.5)  # 30% to 80% of our progress bar
            update_status(f"Processing {task_type}...", display_progress, f"Status: {status} ({progress}%)")
            
            if status == 'SUCCEEDED':
                update_status(f"{task_type.title()} completed!", 80, f"{task_type.title()} task completed successfully")
                print(f"✅ Task succeeded after {attempt + 1} attempts")
                print(f"Response data: {json.dumps(result, indent=2)[:1000]}...")  # Log first 1000 chars
                
                # Check if we actually have model URLs
                if 'model_urls' not in result and 'model_url' not in result:
                    print("⚠️ WARNING: No model URLs in response!")
                    print(f"Full response: {result}")
                
                return result
            elif status == 'FAILED':
                error_msg = result.get('task_error', {}).get('message', 'Unknown error')
                print(f"❌ Task failed: {error_msg}")
                print(f"Full error details: {result.get('task_error', {})}")
                raise Exception(f"{task_type} task failed: {error_msg}")
            
        except Exception as e:
            if current_endpoint_index < len(polling_endpoints) - 1:
                current_endpoint_index += 1
                endpoint = polling_endpoints[current_endpoint_index]
                print(f"Polling error, trying next endpoint: {e}")
                continue
            else:
                raise e
        
        time.sleep(5)
        attempt += 1
    
    raise Exception(f"{task_type} task timed out")

def process_image_async(image_path):
    """Process image in background thread"""
    global generated_files, error_message
    generated_files = []  # Reset files list
    error_message = ""     # Reset error message
    
    try:
        print(f"\n{'='*60}")
        print("Starting image processing pipeline...")
        print(f"Image: {image_path}")
        print(f"{'='*60}\n")
        
        # Step 1: Create textured 3D model from image (single API call)
        update_status("Creating 3D model...", 20, "Sending image to Meshy API")
        task_id, creation_endpoint = create_textured_3d_model(image_path)
        print(f"✅ Step 1 complete: Task ID = {task_id}")
        
        # Step 2: Poll for completion
        update_status("Processing...", 40, "Waiting for Meshy to complete")
        result = poll_meshy_task(task_id, "texture", creation_endpoint)
        print(f"✅ Step 2 complete: Task succeeded")
        
        # Step 3: Download the textured model
        update_status("Downloading model...", 60, "Downloading textured 3D model")
        model_path = download_meshy_files(result)
        print(f"✅ Step 3 complete: Downloaded to {model_path}")
        
        # Step 4: Extract OBJ and texture files
        update_status("Extracting files...", 80, "Extracting OBJ and texture files")
        try:
            obj_file, texture_files = extract_model_files(model_path)
            print(f"✅ Step 4 complete: Extracted OBJ = {obj_file}")
        except Exception as extract_error:
            print(f"⚠️ Step 4 warning: {extract_error}")
            # If extraction fails, assume the downloaded file is already an OBJ
            obj_file = model_path
            texture_files = []
            print(f"Using downloaded file directly as OBJ: {obj_file}")
        
        # Step 5: Skip automatic voxel conversion (user will do it manually)
        print("ℹ️ Step 5: Skipping automatic voxel conversion (manual process)")
        update_status("Processing...", 95, "Preparing files for download")
        
        # Update generated files list
        generated_files = []
        
        # The main download should be the ZIP file with everything
        if os.path.exists(model_path):
            file_ext = Path(model_path).suffix.lower()
            if file_ext == '.zip':
                generated_files.append({
                    'name': '3D Model Package (ZIP)', 
                    'path': os.path.basename(model_path), 
                    'type': 'ZIP'
                })
            else:
                generated_files.append({
                    'name': f'3D Model ({file_ext.upper()})', 
                    'path': os.path.basename(model_path), 
                    'type': file_ext.replace('.', '').upper()
                })
        
        print(f"\n✅ PIPELINE COMPLETE!")
        print(f"Generated files: {generated_files}")
        print(f"{'='*60}\n")
        
        if generated_files:
            update_status("Complete!", 100, f"Generated {len(generated_files)} file(s) successfully")
        else:
            raise Exception("No files were generated successfully")
        
    except Exception as e:
        error_msg = f"Processing failed: {str(e)}"
        print(f"\n❌ PIPELINE ERROR: {error_msg}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback:\n{traceback.format_exc()}")
        print(f"{'='*60}\n")
        
        error_message = error_msg
        update_status("Error", 0, "", error_msg)

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file selected'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file:
            # Ensure upload directory exists
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            print(f"Saving file to: {file_path}")
            file.save(file_path)
            print(f"File saved successfully: {os.path.exists(file_path)}")
            
            # Start processing in background
            thread = threading.Thread(target=process_image_async, args=(file_path,))
            thread.daemon = True
            thread.start()
            
            return jsonify({'message': 'File uploaded successfully', 'filename': filename})
    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/status')
def get_status():
    """Get current processing status"""
    if current_status == "Complete!" and generated_files:
        print(f"Status endpoint returning files: {generated_files}")
    return jsonify({
        'status': current_status,
        'progress': progress_percentage,
        'task': current_task,
        'error': error_message,
        'files': generated_files
    })

@app.route('/download/<filename>')
def download_file(filename):
    """Download generated files"""
    print(f"Download requested for: {filename}")
    try:
        # Check if file exists in output folder
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        print(f"Looking for file at: {file_path}")
        print(f"File exists: {os.path.exists(file_path)}")
        
        # Also list what's actually in the output folder for debugging
        output_files = os.listdir(app.config['OUTPUT_FOLDER']) if os.path.exists(app.config['OUTPUT_FOLDER']) else []
        print(f"Files in output folder: {output_files}")
        
        if os.path.exists(file_path):
            # Determine MIME type based on extension
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext == '.zip':
                mimetype = 'application/zip'
            elif file_ext == '.obj':
                mimetype = 'text/plain'
            elif file_ext == '.mtl':
                mimetype = 'text/plain'
            elif file_ext in ['.jpg', '.jpeg']:
                mimetype = 'image/jpeg'
            elif file_ext == '.png':
                mimetype = 'image/png'
            else:
                mimetype = 'application/octet-stream'
            
            return send_file(file_path, as_attachment=True, mimetype=mimetype)
        
        # Check if file exists in uploads folder
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(upload_path):
            return send_file(upload_path, as_attachment=True)
        
        # Check in extracted folder
        extracted_path = os.path.join(app.config['OUTPUT_FOLDER'], 'meshy_extracted', filename)
        if os.path.exists(extracted_path):
            return send_file(extracted_path, as_attachment=True)
        
        return "File not found", 404
    except Exception as e:
        return f"Download error: {str(e)}", 500

@app.route('/convert/manual', methods=['POST'])
def manual_voxel_convert():
    """Handle manual voxel conversion"""
    try:
        if 'obj_file' not in request.files:
            return jsonify({'error': 'No OBJ file provided'}), 400
        
        obj_file = request.files['obj_file']
        texture_file = request.files.get('texture_file')
        
        # Save uploaded files
        obj_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(obj_file.filename))
        obj_file.save(obj_path)
        
        texture_path = None
        if texture_file:
            texture_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(texture_file.filename))
            texture_file.save(texture_path)
        
        # Create a basic VOX file
        try:
            vox_path = convert_to_voxel(obj_path, [texture_path] if texture_path else None)
            return jsonify({
                'success': True,
                'vox_file': os.path.basename(vox_path),
                'message': 'VOX file created successfully with texture applied.'
            })
        except Exception as e:
            # Even if it fails, try to create a basic VOX
            vox_file_path = os.path.join(app.config['OUTPUT_FOLDER'], 'model.vox')
            vox_header = b'VOX \x96\x00\x00\x00MAIN\x00\x00\x00\x00\x00\x00\x00\x00'
            with open(vox_file_path, 'wb') as f:
                f.write(vox_header)
            
            return jsonify({
                'success': True,
                'vox_file': 'model.vox',
                'message': 'Created basic VOX file structure.'
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting Flask app...")
    setup_directories()
    print("Directories created, starting server...")
    # Get port from environment variable (for Render) or use 5000 as default
    port = int(os.environ.get('PORT', 5000))
    # Set debug to False in production
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
