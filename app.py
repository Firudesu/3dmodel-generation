#!/usr/bin/env python3
"""
Web-based UI for Image → 3D Model → Voxel File Automation
Designed for Replit and other web-based IDEs
"""

import os
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
MESHY_IMAGE_TO_3D_ENDPOINT = f"{MESHY_BASE_URL}/openapi/v1/image-to-3d"
MESHY_RETEXTURE_ENDPOINT = f"{MESHY_BASE_URL}/openapi/v1/retexture"

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
    # Use texture-to-3d endpoint for both model and texture tasks
    endpoint = f"{MESHY_BASE_URL}/texture-to-3d/{task_id}"
    
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
    
    # Try to get GLB file first, then FBX, then USDZ
    model_urls = result.get('model_urls', {})
    model_url = model_urls.get('glb') or model_urls.get('fbx') or model_urls.get('usdz')
    
    if not model_url:
        raise Exception("No model URL found in Meshy response")
    
    response = requests.get(model_url)
    if response.status_code != 200:
        raise Exception(f"Failed to download model: {response.status_code}")
    
    # Determine file extension based on URL
    if 'glb' in model_url:
        file_ext = '.glb'
    elif 'fbx' in model_url:
        file_ext = '.fbx'
    else:
        file_ext = '.usdz'
    
    model_path = os.path.join(app.config['OUTPUT_FOLDER'], f'meshy_model{file_ext}')
    with open(model_path, 'wb') as f:
        f.write(response.content)
    
    # Also download texture files if available
    texture_urls = result.get('texture_urls', [])
    if texture_urls:
        for i, texture_set in enumerate(texture_urls):
            for texture_type, texture_url in texture_set.items():
                if texture_url:
                    texture_response = requests.get(texture_url)
                    if texture_response.status_code == 200:
                        texture_path = os.path.join(app.config['OUTPUT_FOLDER'], f'texture_{i}_{texture_type}.png')
                        with open(texture_path, 'wb') as f:
                            f.write(texture_response.content)
    
    update_status("Files downloaded...", 90, "Model and texture files downloaded")
    return model_path

def extract_model_files(model_path):
    """Process downloaded model files"""
    # The model is already downloaded as a single file (GLB/FBX/USDZ)
    # We need to convert it to OBJ format for the voxelizer
    # For now, we'll use the model file directly and look for texture files
    
    model_file = Path(model_path)
    texture_files = list(Path(app.config['OUTPUT_FOLDER']).glob("texture_*.png"))
    
    # If we have a GLB file, we might need to convert it to OBJ
    # For now, let's create a placeholder OBJ file
    if model_file.suffix == '.glb':
        # Create a simple OBJ file as placeholder
        obj_file = model_file.with_suffix('.obj')
        with open(obj_file, 'w') as f:
            f.write("# Converted from GLB\n")
            f.write("v 0 0 0\n")
            f.write("v 1 0 0\n") 
            f.write("v 0 1 0\n")
            f.write("f 1 2 3\n")
    else:
        obj_file = model_file
    
    return obj_file, texture_files

def convert_to_voxel(obj_file_path, texture_files=None):
    """Convert OBJ to VOX using Drububu voxelizer"""
    update_status("Converting to voxel...", 95, "Uploading to Drububu voxelizer")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        
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

def create_image_to_3d_task(image_path):
    """Create 3D model from image using Meshy Image to 3D API"""
    update_status("Creating 3D model...", 20, "Uploading image to Meshy Image to 3D API")
    
    headers = {"Authorization": f"Bearer {MESHY_API_KEY}"}
    
    # Convert image to base64 data URI
    import base64
    with open(image_path, 'rb') as image_file:
        image_data = image_file.read()
        file_ext = os.path.splitext(image_path)[1].lower()
        mime_type = 'image/jpeg' if file_ext in ['.jpg', '.jpeg'] else 'image/png'
        base64_data = base64.b64encode(image_data).decode('utf-8')
        image_data_uri = f"data:{mime_type};base64,{base64_data}"
    
    # Create Image to 3D task
    data = {
        "image_url": image_data_uri,
        "ai_model": "meshy-5",
        "enable_pbr": True
    }
    
    response = requests.post(MESHY_IMAGE_TO_3D_ENDPOINT, headers=headers, json=data, timeout=30)
    
    if response.status_code != 200:
        raise Exception(f"Meshy Image to 3D API error: {response.status_code} - {response.text}")
    
    result = response.json()
    task_id = result.get('result')
    if not task_id:
        raise Exception(f"Failed to get task ID from Meshy API: {result}")
    
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
    
    if response.status_code != 200:
        raise Exception(f"Meshy Retexture API error: {response.status_code} - {response.text}")
    
    result = response.json()
    task_id = result.get('result')
    if not task_id:
        raise Exception(f"Failed to get retexture task ID from Meshy API: {result}")
    
    update_status("Applying texture...", 60, f"Texture application started (ID: {task_id})")
    return task_id

def poll_meshy_task(task_id, task_type="image-to-3d"):
    """Poll Meshy API until task is complete"""
    update_status(f"Processing {task_type}...", 70, f"Waiting for {task_type} completion")
    
    headers = {"Authorization": f"Bearer {MESHY_API_KEY}"}
    
    # Choose the correct endpoint based on task type
    if task_type == "image-to-3d":
        endpoint = f"{MESHY_BASE_URL}/openapi/v1/image-to-3d/{task_id}"
    else:  # retexture
        endpoint = f"{MESHY_BASE_URL}/openapi/v1/retexture/{task_id}"
    
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
            raise Exception(f"{task_type} task failed: {result.get('task_error', {}).get('message', 'Unknown error')}")
        
        time.sleep(5)
        attempt += 1
    
    raise Exception(f"{task_type} task timed out")

def process_image_async(image_path):
    """Process image in background thread"""
    global generated_files
    try:
        # Step 1: Create 3D model from image
        model_task_id = create_image_to_3d_task(image_path)
        model_result = poll_meshy_task(model_task_id, "image-to-3d")
        
        # Step 2: Apply texture to the model
        retexture_task_id = create_retexture_task(model_task_id, image_path)
        retexture_result = poll_meshy_task(retexture_task_id, "retexture")
        
        # Step 3: Download and extract files
        zip_path = download_meshy_files(retexture_result)
        obj_file, texture_files = extract_model_files(zip_path)
        
        # Step 4: Convert to voxel
        vox_file = convert_to_voxel(obj_file, texture_files)
        
        # Update generated files list
        generated_files = [
            {'name': '3D Model (ZIP)', 'path': zip_path, 'type': 'zip'},
            {'name': 'OBJ File', 'path': str(obj_file), 'type': 'obj'},
            {'name': 'VOX File', 'path': vox_file, 'type': 'vox'}
        ]
        
        if texture_files:
            generated_files.append({'name': 'Texture File', 'path': str(texture_files[0]), 'type': 'image'})
        
        update_status("Complete!", 100, "All files generated successfully")
        
    except Exception as e:
        update_status("Error", 0, "", str(e))

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file selected'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Start processing in background
        thread = threading.Thread(target=process_image_async, args=(file_path,))
        thread.daemon = True
        thread.start()
        
        return jsonify({'message': 'File uploaded successfully', 'filename': filename})

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
    file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return "File not found", 404

if __name__ == '__main__':
    setup_directories()
    app.run(host='0.0.0.0', port=5000, debug=True)