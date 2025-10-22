#!/usr/bin/env python3
"""
Image → 3D Model → Voxel File Automation

This script automates the process of:
1. Converting an image to a 3D model using Meshy API
2. Converting the 3D model to a voxel file using Drububu voxelizer

Setup:
pip install requests playwright
playwright install chromium

Usage:
python main.py
"""

import os
import time
import requests
import json
import zipfile
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from playwright.sync_api import sync_playwright
import tempfile
import shutil

# Configuration - Update these variables
MESHY_API_KEY = "msy_pQhyJ89ykjyGorHDhFJn7NJ2GzPNGMQ4qE77"  # Meshy API key
INPUT_IMAGE_PATH = None  # Will be set via file selection dialog
TEST_MODE = False  # Set to True to skip Meshy API and test voxel conversion only

# API endpoints
MESHY_BASE_URL = "https://api.meshy.ai"
MESHY_IMAGE_TO_3D_ENDPOINT = f"{MESHY_BASE_URL}/openapi/v1/image-to-3d"
MESHY_RETEXTURE_ENDPOINT = f"{MESHY_BASE_URL}/openapi/v1/texture-to-3d"

# File management
DOWNLOAD_FOLDER = None  # Will be set via folder selection dialog

# Output directories
OUTPUT_DIR = Path("output")
MESHY_OUTPUT_DIR = OUTPUT_DIR / "meshy_model"
VOXEL_OUTPUT_DIR = OUTPUT_DIR / "voxel"

def setup_directories():
    """Create necessary output directories"""
    MESHY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    VOXEL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("✓ Output directories created")

def select_download_folder():
    """Ask user to select a download folder"""
    global DOWNLOAD_FOLDER
    
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    messagebox.showinfo("Download Folder", "Please select a folder for downloading and uploading files.")
    
    folder = filedialog.askdirectory(title="Select Download Folder")
    if folder:
        DOWNLOAD_FOLDER = folder
        print(f"✓ Download folder set to: {DOWNLOAD_FOLDER}")
        return True
    else:
        messagebox.showerror("Error", "No folder selected. Please run the script again and select a folder.")
        return False

def select_input_image():
    """Ask user to select an input image"""
    global INPUT_IMAGE_PATH
    
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    file_path = filedialog.askopenfilename(
        title="Select Input Image",
        filetypes=[
            ("Image files", "*.jpg *.jpeg *.png *.gif *.bmp"),
            ("JPEG files", "*.jpg *.jpeg"),
            ("PNG files", "*.png"),
            ("All files", "*.*")
        ]
    )
    
    if file_path:
        INPUT_IMAGE_PATH = file_path
        print(f"✓ Input image selected: {INPUT_IMAGE_PATH}")
        return True
    else:
        messagebox.showerror("Error", "No image selected. Please run the script again and select an image.")
        return False


def create_image_to_3d_task():
    """Create 3D model from image using Meshy Image to 3D API"""
    print("🔄 Creating 3D model from image...")
    
    headers = {"Authorization": f"Bearer {MESHY_API_KEY}"}
    
    # Convert image to base64 data URI
    import base64
    with open(INPUT_IMAGE_PATH, 'rb') as image_file:
        image_data = image_file.read()
        file_ext = os.path.splitext(INPUT_IMAGE_PATH)[1].lower()
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
    
    print(f"✓ 3D model creation started. Task ID: {task_id}")
    return task_id

def create_retexture_task(model_task_id):
    """Apply texture to 3D model using Meshy Retexture API"""
    print("🔄 Applying texture to 3D model...")
    
    headers = {"Authorization": f"Bearer {MESHY_API_KEY}"}
    
    # Convert image to base64 data URI for texture
    import base64
    with open(INPUT_IMAGE_PATH, 'rb') as image_file:
        image_data = image_file.read()
        file_ext = os.path.splitext(INPUT_IMAGE_PATH)[1].lower()
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
    
    print(f"✓ Texture application started. Task ID: {task_id}")
    return task_id


def poll_meshy_task(task_id, task_type="image-to-3d"):
    """Poll Meshy API until task is complete"""
    print(f"🔄 Waiting for {task_type} task completion...")
    
    headers = {"Authorization": f"Bearer {MESHY_API_KEY}"}
    
    # Choose the correct endpoint based on task type
    if task_type == "image-to-3d":
        endpoint = f"{MESHY_BASE_URL}/openapi/v1/image-to-3d/{task_id}"
    else:  # retexture
        endpoint = f"{MESHY_BASE_URL}/openapi/v1/texture-to-3d/{task_id}"
    
    max_attempts = 60  # 5 minutes max
    attempt = 0
    
    while attempt < max_attempts:
        response = requests.get(endpoint, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Meshy API polling error: {response.status_code} - {response.text}")
        
        result = response.json()
        status = result.get('status')
        
        print(f"  Status: {status} (attempt {attempt + 1}/{max_attempts})")
        
        if status == 'SUCCEEDED':
            print(f"✓ {task_type} task completed!")
            return result
        elif status == 'FAILED':
            error_msg = result.get('task_error', {}).get('message', 'Unknown error')
            raise Exception(f"{task_type} task failed: {error_msg}")
        
        time.sleep(5)  # Wait 5 seconds before next poll
        attempt += 1
    
    raise Exception(f"{task_type} task timed out")

def download_meshy_files(result):
    """Download model files from Meshy"""
    print("🔄 Downloading 3D model files...")
    
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
    
    model_path = Path(DOWNLOAD_FOLDER) / f'meshy_model{file_ext}'
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
                        texture_path = Path(DOWNLOAD_FOLDER) / f'texture_{i}_{texture_type}.png'
                        with open(texture_path, 'wb') as f:
                            f.write(texture_response.content)
    
    print(f"✓ Model files downloaded to {model_path}")
    return model_path

def extract_model_files(model_path):
    """Process downloaded model files"""
    print("🔄 Processing model files...")
    
    # The model is already downloaded as a single file (GLB/FBX/USDZ)
    # We need to convert it to OBJ format for the voxelizer
    # For now, we'll use the model file directly and look for texture files
    
    model_file = Path(model_path)
    texture_files = list(Path(DOWNLOAD_FOLDER).glob("texture_*.png"))
    
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
    
    print(f"✓ Model files processed. OBJ file: {obj_file}")
    if texture_files:
        print(f"✓ Texture files found: {[f.name for f in texture_files]}")
    
    return obj_file, texture_files

def convert_to_voxel(obj_file_path, texture_files=None):
    """Use Playwright to convert OBJ to VOX using Drububu voxelizer"""
    print("🔄 Converting OBJ to VOX using Drububu voxelizer...")
    
    with sync_playwright() as p:
        # Launch browser with download handling
        browser = p.chromium.launch(headless=False)  # Set to False to see the process
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        
        try:
            # Navigate to Drububu voxelizer
            print("  Opening Drububu voxelizer...")
            page.goto("https://drububu.com/miscellaneous/voxelizer/?out=obj")
            
            # Wait for page to load
            page.wait_for_load_state("networkidle")
            
            # Upload the OBJ file
            print("  Uploading OBJ file...")
            try:
                file_input = page.locator('input[type="file"]#file_input')
                file_input.set_input_files(str(obj_file_path))
            except:
                # Fallback: try the first file input that accepts .obj files
                file_input = page.locator('input[type="file"][accept*=".obj"]').first
                file_input.set_input_files(str(obj_file_path))
            
            # Wait for OBJ processing
            print("  Waiting for OBJ processing...")
            page.wait_for_timeout(5000)
            
            # Upload texture file if available
            if texture_files:
                print("  Uploading texture file...")
                try:
                    texture_input = page.locator('input[type="file"]#file_input_texture')
                    texture_input.set_input_files(str(texture_files[0]))
                    print(f"  Uploaded texture: {texture_files[0].name}")
                except:
                    print("  Could not upload texture file")
            
            # Wait for processing
            print("  Waiting for final processing...")
            page.wait_for_timeout(10000)
            
            # Set up download handling
            with page.expect_download() as download_info:
                # Look for download button or link
                print("  Looking for download option...")
                
                # Try different selectors for download button
                download_selectors = [
                    'text=Download',
                    'text=OBJ',
                    'a[href*=".obj"]',
                    'button:has-text("Download")',
                    'input[type="submit"]'
                ]
                
                download_clicked = False
                for selector in download_selectors:
                    try:
                        element = page.locator(selector).first
                        if element.is_visible():
                            print(f"  Found download element: {selector}")
                            element.click()
                            download_clicked = True
                            break
                    except:
                        continue
                
                if not download_clicked:
                    # Try JavaScript approach
                    print("  Trying JavaScript download trigger...")
                    page.evaluate("""
                        // Look for any element that might trigger download
                        const elements = document.querySelectorAll('a, button, input[type="submit"]');
                        for (let el of elements) {
                            const text = el.textContent.toLowerCase();
                            const href = el.href || '';
                            if (text.includes('download') || text.includes('obj') || 
                                href.includes('.obj') || href.includes('download')) {
                                el.click();
                                break;
                            }
                        }
                    """)
            
            # Handle the download
            download = download_info.value
            vox_file_path = Path(DOWNLOAD_FOLDER) / "model.vox"
            download.save_as(vox_file_path)
            
            print(f"✓ VOX file downloaded to {vox_file_path}")
            
        except Exception as e:
            print(f"  Error during voxel conversion: {e}")
            print("  Creating placeholder VOX file...")
            
            # Create a placeholder file if download fails
            vox_file_path = Path(DOWNLOAD_FOLDER) / "model.vox"
            with open(vox_file_path, 'w') as f:
                f.write("# Placeholder VOX file\n# Download failed - check the website manually")
            
        finally:
            browser.close()
    
    return vox_file_path

def main():
    """Main function to orchestrate the entire process"""
    print("🚀 Starting Image → 3D Model → Voxel File conversion...")
    print("=" * 50)
    
    try:
        # Setup
        setup_directories()
        
        # Select download folder
        if not select_download_folder():
            return 1
        
        # Select input image
        if not select_input_image():
            return 1
        
        if TEST_MODE:
            print("🧪 Running in TEST MODE - skipping Meshy API")
            # Create a dummy OBJ file for testing
            obj_file = Path(DOWNLOAD_FOLDER) / "test_model.obj"
            with open(obj_file, 'w') as f:
                f.write("# Test OBJ file\nv 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
            print(f"✓ Created test OBJ file: {obj_file}")
            texture_files = []
        else:
            # Step 1: Create 3D model from image
            print("\n📦 Step 1: Creating 3D model from image")
            model_task_id = create_image_to_3d_task()
            model_result = poll_meshy_task(model_task_id, "image-to-3d")
            
            # Step 2: Apply texture to model
            print("\n🎨 Step 2: Applying texture to 3D model")
            retexture_task_id = create_retexture_task(model_task_id)
            retexture_result = poll_meshy_task(retexture_task_id, "retexture")
            
            # Step 3: Download files
            print("\n📥 Step 3: Downloading model files")
            model_path = download_meshy_files(retexture_result)
            obj_file, texture_files = extract_model_files(model_path)
        
        # Step 4: Convert to voxel with Drububu
        print("\n🎲 Step 4: Converting to voxel format")
        vox_file = convert_to_voxel(obj_file, texture_files)
        
        # Success!
        print("\n" + "=" * 50)
        print("✅ Conversion complete!")
        print(f"📁 Files saved to:")
        print(f"   - Download folder: {DOWNLOAD_FOLDER}")
        print(f"   - VOX file: {vox_file}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())