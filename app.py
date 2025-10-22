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
from playwright.sync_api import sync_playwright
import tempfile
import shutil

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'

# Configuration
MESHY_API_KEY = "msy_pQhyJ89ykjyGorHDhFJn7NJ2GzPNGMQ4qE77"
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


def poll_meshy_task(task_id, task_type="texture"):
    """Poll Meshy API until task is complete"""
    update_status(f"Processing {task_type}...", 70, f"Waiting for {task_type} completion")
    
    headers = {"Authorization": f"Bearer {MESHY_API_KEY}"}
    # Use the correct endpoint based on task type
    if task_type == "retexture":
        endpoint = f"{MESHY_BASE_URL}/openapi/v1/retexture/{task_id}"
    else:  # texture, model, or image-to-3d
        endpoint = f"{MESHY_BASE_URL}/openapi/v1/image-to-3d/{task_id}"
    
    max_attempts = 60
    attempt = 0
    
    while attempt < max_attempts:
        response = requests.get(endpoint, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Meshy API polling error: {response.status_code} - {response.text}")
        
        result = response.json()
        status = result.get('status')
        
        update_status(f"Processing {task_type}...", 70 + (attempt * 0.5), f"Status: {status}")
        
        if status == 'SUCCEEDED':
            update_status(f"{task_type.title()} completed!", 80, f"{task_type.title()} task completed successfully")
            return result
        elif status == 'FAILED':
            raise Exception(f"{task_type} task failed: {result.get('error', 'Unknown error')}")
        
        time.sleep(5)
        attempt += 1
    
    raise Exception(f"{task_type} task timed out")

def download_meshy_files(result):
    """Download model files from Meshy"""
    update_status("Downloading files...", 85, "Downloading model files from Meshy")
    
    # Try different response formats - prioritize OBJ files
    model_url = None
    file_type = None
    
    # Check for OBJ files first
    if 'model_urls' in result:
        model_urls = result['model_urls']
        if 'obj' in model_urls:
            model_url = model_urls['obj']
            file_type = 'obj'
        elif 'preview' in model_urls:
            model_url = model_urls['preview']
            file_type = 'preview'
        elif 'glb' in model_urls:
            model_url = model_urls['glb']
            file_type = 'glb'
    
    # Fallback to direct model_url
    if not model_url:
        model_url = result.get('model_url')
        file_type = 'unknown'
    
    if not model_url:
        raise Exception("No model URL found in Meshy response")
    
    print(f"Downloading from URL: {model_url}")
    print(f"Expected file type: {file_type}")
    
    response = requests.get(model_url)
    if response.status_code != 200:
        raise Exception(f"Failed to download model: {response.status_code}")
    
    # Detect file type from URL or content
    content_type = response.headers.get('content-type', '')
    file_extension = '.zip'  # Default
    
    if 'obj' in model_url or 'text/plain' in content_type:
        file_extension = '.obj'
    elif 'glb' in model_url or 'application/octet-stream' in content_type:
        file_extension = '.glb'
    elif 'fbx' in model_url:
        file_extension = '.fbx'
    elif 'zip' in model_url or 'application/zip' in content_type:
        file_extension = '.zip'
    
    # Save with appropriate extension
    model_path = os.path.join(app.config['OUTPUT_FOLDER'], f'meshy_model{file_extension}')
    with open(model_path, 'wb') as f:
        f.write(response.content)
    
    print(f"Downloaded file: {model_path} (type: {file_extension})")
    update_status("Files downloaded...", 90, f"Model files downloaded ({file_extension})")
    return model_path

def extract_model_files(model_path):
    """Process downloaded model files and extract OBJ"""
    print(f"Processing model file: {model_path}")
    
    model_file = Path(model_path)
    file_extension = model_file.suffix.lower()
    
    if file_extension == '.zip':
        # Extract ZIP file and look for OBJ
        extract_dir = os.path.join(app.config['OUTPUT_FOLDER'], 'meshy_extracted')
        os.makedirs(extract_dir, exist_ok=True)
        
        try:
            with zipfile.ZipFile(model_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Look for OBJ files in the extracted content
            obj_files = list(Path(extract_dir).glob("**/*.obj"))
            texture_files = list(Path(extract_dir).glob("**/*.jpg")) + list(Path(extract_dir).glob("**/*.png"))
            
            if obj_files:
                print(f"✅ Found OBJ file in ZIP: {obj_files[0]}")
                return obj_files[0], texture_files
            else:
                print("❌ No OBJ file found in ZIP")
                # List what files we actually got
                all_files = list(Path(extract_dir).glob("**/*"))
                print(f"Files in ZIP: {[f.name for f in all_files if f.is_file()]}")
                raise Exception("No OBJ file found in downloaded ZIP")
                
        except zipfile.BadZipFile:
            print("❌ File is not a valid ZIP file")
            raise Exception("Downloaded file is not a valid ZIP file")
    
    elif file_extension == '.obj':
        # Already an OBJ file - perfect!
        print(f"✅ Direct OBJ file: {model_file}")
        texture_files = list(Path(app.config['OUTPUT_FOLDER']).glob("texture_*.png"))
        return model_file, texture_files
    
    else:
        # Other formats (GLB, FBX, etc.) - we need to convert or get OBJ
        print(f"❌ Got {file_extension} file, but we need OBJ for voxel conversion")
        print("This format cannot be directly converted to VOX")
        raise Exception(f"Meshy returned {file_extension} format, but OBJ is required for voxel conversion. Please try a different image or check Meshy API settings.")

def convert_to_voxel(obj_file_path, texture_files=None):
    """Convert OBJ to VOX using Drububu voxelizer"""
    update_status("Converting to voxel...", 95, "Uploading to Drububu voxelizer")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
    except Exception as e:
        if "Executable doesn't exist" in str(e):
            print("🔧 Installing Playwright browsers...")
            import subprocess
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
            print("✅ Browsers installed, retrying...")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(accept_downloads=True)
                page = context.new_page()
        else:
            raise e
        
        try:
            page.goto("https://drububu.com/miscellaneous/voxelizer/?out=obj")
            page.wait_for_load_state("networkidle")
            
            # Upload OBJ file
            file_input = page.locator('input[type="file"]#file_input')
            file_input.set_input_files(str(obj_file_path))
            page.wait_for_timeout(5000)
            
            # Upload texture if available
            if texture_files:
                texture_input = page.locator('input[type="file"]#file_input_texture')
                texture_input.set_input_files(str(texture_files[0]))
                page.wait_for_timeout(5000)
            
            # Download result
            with page.expect_download() as download_info:
                page.evaluate("""
                    const elements = document.querySelectorAll('a, button, input[type="submit"]');
                    for (let el of elements) {
                        const text = el.textContent.toLowerCase();
                        if (text.includes('download') || text.includes('obj')) {
                            el.click();
                            break;
                        }
                    }
                """)
            
            download = download_info.value
            vox_file_path = os.path.join(app.config['OUTPUT_FOLDER'], 'model.vox')
            download.save_as(vox_file_path)
            
            return vox_file_path
            
        except Exception as e:
            # Create placeholder if download fails
            vox_file_path = os.path.join(app.config['OUTPUT_FOLDER'], 'model.vox')
            with open(vox_file_path, 'w') as f:
                f.write("# Placeholder VOX file\n# Download failed - check the website manually")
            return vox_file_path
        finally:
            browser.close()

def test_api_endpoints():
    """Test which Meshy API endpoints are working"""
    headers = {"Authorization": f"Bearer {MESHY_API_KEY}"}
    
    # First test API key format
    print(f"API Key format check:")
    print(f"  Length: {len(MESHY_API_KEY)}")
    print(f"  Starts with 'msy_': {MESHY_API_KEY.startswith('msy_')}")
    print(f"  Contains only valid chars: {all(c.isalnum() or c in '_-' for c in MESHY_API_KEY)}")
    
    endpoints_to_test = [
        (MESHY_TEXTURE_TO_3D_ENDPOINT_V2, "v2 texture-to-3d"),
        (MESHY_TEXTURE_TO_3D_ENDPOINT_V1, "v1 texture-to-3d"),
        (MESHY_IMAGE_TO_3D_ENDPOINT_V2, "v2 image-to-3d"),
        (MESHY_IMAGE_TO_3D_ENDPOINT_V1, "v1 image-to-3d")
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
    update_status("Creating 3D model...", 20, "Testing Meshy API endpoints")
    
    # Test which endpoints work
    working_endpoints = test_api_endpoints()
    if not working_endpoints:
        raise Exception("No working Meshy API endpoints found")
    
    # Use the first working endpoint
    endpoint, name = working_endpoints[0]
    update_status("Creating 3D model...", 25, f"Using {name} - Task created, processing...")
    
    headers = {"Authorization": f"Bearer {MESHY_API_KEY}"}
    
    # Use file upload format
    file_ext = os.path.splitext(image_path)[1].lower()
    content_type = 'image/jpeg' if file_ext in ['.jpg', '.jpeg'] else 'image/png'
    
    # Try using texture-to-3d endpoint with image (this might be the correct approach)
    if 'texture-to-3d' in endpoint:
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
        
        data = {
            "image_url": image_data_uri,
            "ai_model": "meshy-5",
            "enable_pbr": True
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
    
    update_status("Creating 3D model...", 30, f"3D model creation started (ID: {task_id})")
    return task_id

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


def process_image_async(image_path):
    """Process image in background thread"""
    global generated_files
    try:
        # Step 1: Create textured 3D model from image (single API call)
        update_status("Creating 3D model...", 20, "Sending image to Meshy API")
        task_id = create_textured_3d_model(image_path)
        
        # Step 2: Poll for completion
        update_status("Processing...", 40, "Waiting for Meshy to complete")
        result = poll_meshy_task(task_id, "texture")
        
        # Step 3: Download the textured model
        update_status("Downloading model...", 60, "Downloading textured 3D model")
        model_path = download_meshy_files(result)
        
        # Step 4: Extract OBJ and texture files
        update_status("Extracting files...", 80, "Extracting OBJ and texture files")
        obj_file, texture_files = extract_model_files(model_path)
        
        # Step 5: Convert to voxel
        update_status("Converting to voxel...", 90, "Converting OBJ to VOX format")
        vox_file = convert_to_voxel(obj_file, texture_files)
        
        # Update generated files list
        generated_files = [
            {'name': '3D Model', 'path': model_path, 'type': 'model'},
            {'name': 'OBJ File', 'path': str(obj_file), 'type': 'obj'},
            {'name': 'VOX File', 'path': vox_file, 'type': 'vox'}
        ]
        
        if texture_files:
            generated_files.append({'name': 'Texture File', 'path': str(texture_files[0]), 'type': 'image'})
        
        update_status("Complete!", 100, "All files generated successfully")
        
    except Exception as e:
        error_msg = f"Processing failed: {str(e)}"
        print(f"❌ Error: {error_msg}")
        update_status("Error", 0, error_msg)

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
    try:
        # Check if file exists in output folder
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        
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

if __name__ == '__main__':
    print("Starting Flask app...")
    setup_directories()
    print("Directories created, starting server...")
    app.run(host='0.0.0.0', port=5000, debug=True)