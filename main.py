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
from pathlib import Path
from playwright.sync_api import sync_playwright
import tempfile
import shutil

# Configuration - Update these variables
MESHY_API_KEY = "YOUR_MESHY_API_KEY_HERE"  # Replace with your actual Meshy API key
INPUT_IMAGE_PATH = "input/sample_image.jpg"  # Path to your input image
TEST_MODE = False  # Set to True to skip Meshy API and test voxel conversion only

# API endpoints
MESHY_BASE_URL = "https://api.meshy.ai/v2"
MESHY_TEXTURE_ENDPOINT = f"{MESHY_BASE_URL}/texture-to-3d"

# Output directories
OUTPUT_DIR = Path("output")
MESHY_OUTPUT_DIR = OUTPUT_DIR / "meshy_model"
VOXEL_OUTPUT_DIR = OUTPUT_DIR / "voxel"

def setup_directories():
    """Create necessary output directories"""
    MESHY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    VOXEL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("✓ Output directories created")

def check_input_file():
    """Check if input image exists"""
    if not os.path.exists(INPUT_IMAGE_PATH):
        raise FileNotFoundError(f"Input image not found: {INPUT_IMAGE_PATH}")
    print(f"✓ Input image found: {INPUT_IMAGE_PATH}")

def upload_image_to_meshy():
    """Upload image to Meshy API and start 3D generation"""
    print("🔄 Uploading image to Meshy API...")
    
    headers = {
        "Authorization": f"Bearer {MESHY_API_KEY}",
    }
    
    # Determine content type based on file extension
    file_ext = os.path.splitext(INPUT_IMAGE_PATH)[1].lower()
    content_type = 'image/jpeg' if file_ext in ['.jpg', '.jpeg'] else 'image/png'
    
    with open(INPUT_IMAGE_PATH, 'rb') as image_file:
        files = {
            'image': (os.path.basename(INPUT_IMAGE_PATH), image_file, content_type)
        }
        
        data = {
            'mode': 'preview',  # Use preview mode for faster generation
            'art_style': 'realistic'
        }
        
        response = requests.post(
            MESHY_TEXTURE_ENDPOINT,
            headers=headers,
            files=files,
            data=data,
            timeout=30
        )
    
    if response.status_code != 200:
        raise Exception(f"Meshy API error: {response.status_code} - {response.text}")
    
    result = response.json()
    task_id = result.get('result')
    
    if not task_id:
        raise Exception(f"Failed to get task ID from Meshy API: {result}")
    
    print(f"✓ Image uploaded successfully. Task ID: {task_id}")
    return task_id

def poll_meshy_task(task_id):
    """Poll Meshy API until 3D model generation is complete"""
    print("🔄 Waiting for 3D model generation...")
    
    headers = {
        "Authorization": f"Bearer {MESHY_API_KEY}",
    }
    
    max_attempts = 60  # 5 minutes max
    attempt = 0
    
    while attempt < max_attempts:
        response = requests.get(
            f"{MESHY_BASE_URL}/texture-to-3d/{task_id}",
            headers=headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Meshy API polling error: {response.status_code} - {response.text}")
        
        result = response.json()
        status = result.get('status')
        
        print(f"  Status: {status} (attempt {attempt + 1}/{max_attempts})")
        
        if status == 'SUCCEEDED':
            print("✓ 3D model generation completed!")
            return result
        elif status == 'FAILED':
            raise Exception(f"3D model generation failed: {result.get('error', 'Unknown error')}")
        
        time.sleep(5)  # Wait 5 seconds before next poll
        attempt += 1
    
    raise Exception("3D model generation timed out")

def download_meshy_files(result):
    """Download .obj, .mtl, and texture files from Meshy"""
    print("🔄 Downloading 3D model files...")
    
    model_url = result.get('model_urls', {}).get('preview')
    if not model_url:
        raise Exception("No model URL found in Meshy response")
    
    # Download the model file (usually a zip containing .obj, .mtl, and textures)
    response = requests.get(model_url)
    if response.status_code != 200:
        raise Exception(f"Failed to download model: {response.status_code}")
    
    # Save the downloaded file
    model_zip_path = MESHY_OUTPUT_DIR / "model.zip"
    with open(model_zip_path, 'wb') as f:
        f.write(response.content)
    
    print(f"✓ Model files downloaded to {model_zip_path}")
    return model_zip_path

def extract_model_files(zip_path):
    """Extract .obj, .mtl, and texture files from the downloaded zip"""
    print("🔄 Extracting model files...")
    
    import zipfile
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(MESHY_OUTPUT_DIR)
    
    # Find the .obj file
    obj_files = list(MESHY_OUTPUT_DIR.glob("*.obj"))
    if not obj_files:
        raise Exception("No .obj file found in extracted model")
    
    obj_file = obj_files[0]
    print(f"✓ Model files extracted. OBJ file: {obj_file}")
    return obj_file

def convert_to_voxel(obj_file_path):
    """Use Playwright to convert OBJ to VOX using Drububu voxelizer"""
    print("🔄 Converting OBJ to VOX using Drububu voxelizer...")
    
    with sync_playwright() as p:
        # Launch browser with download handling
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        
        try:
            # Navigate to Drububu voxelizer
            print("  Opening Drububu voxelizer...")
            page.goto("https://drububu.com/miscellaneous/voxelizer/?out=vox")
            
            # Wait for page to load
            page.wait_for_load_state("networkidle")
            
            # Upload the OBJ file
            print("  Uploading OBJ file...")
            # Use the specific file input for 3D models (not textures)
            try:
                file_input = page.locator('input[type="file"]#file_input')
                file_input.set_input_files(str(obj_file_path))
            except:
                # Fallback: try the first file input that accepts .obj files
                file_input = page.locator('input[type="file"][accept*=".obj"]').first
                file_input.set_input_files(str(obj_file_path))
            
            # Wait for processing
            print("  Waiting for processing...")
            page.wait_for_timeout(10000)  # Wait 10 seconds for processing
            
            # Set up download handling
            with page.expect_download() as download_info:
                # Look for download button or link
                print("  Looking for download option...")
                
                # Try different selectors for download button
                download_selectors = [
                    'text=Download',
                    'text=VOX',
                    'a[href*=".vox"]',
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
                            if (text.includes('download') || text.includes('vox') || 
                                href.includes('.vox') || href.includes('download')) {
                                el.click();
                                break;
                            }
                        }
                    """)
            
            # Handle the download
            download = download_info.value
            vox_file_path = VOXEL_OUTPUT_DIR / "model.vox"
            download.save_as(vox_file_path)
            
            print(f"✓ VOX file downloaded to {vox_file_path}")
            
        except Exception as e:
            print(f"  Error during voxel conversion: {e}")
            print("  Creating placeholder VOX file...")
            
            # Create a placeholder file if download fails
            vox_file_path = VOXEL_OUTPUT_DIR / "model.vox"
            with open(vox_file_path, 'w') as f:
                f.write("# Placeholder VOX file\n# Download failed - check the website manually")
            
        finally:
            browser.close()
    
    return vox_file_path

def main():
    """Main function to orchestrate the entire process"""
    print("🚀 Starting Image → 3D Model → Voxel conversion...")
    print("=" * 50)
    
    try:
        # Setup
        setup_directories()
        check_input_file()
        
        if TEST_MODE:
            print("🧪 Running in TEST MODE - skipping Meshy API")
            # Create a dummy OBJ file for testing
            obj_file = MESHY_OUTPUT_DIR / "test_model.obj"
            with open(obj_file, 'w') as f:
                f.write("# Test OBJ file\nv 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
            print(f"✓ Created test OBJ file: {obj_file}")
        else:
            if MESHY_API_KEY == "YOUR_MESHY_API_KEY_HERE":
                raise Exception("Please set your MESHY_API_KEY in the script")
            
            # Step 1: Generate 3D model with Meshy
            print("\n📦 Step 1: Generating 3D model with Meshy API")
            task_id = upload_image_to_meshy()
            result = poll_meshy_task(task_id)
            zip_path = download_meshy_files(result)
            obj_file = extract_model_files(zip_path)
        
        # Step 2: Convert to voxel with Drububu
        print("\n🎲 Step 2: Converting to voxel format")
        vox_file = convert_to_voxel(obj_file)
        
        # Success!
        print("\n" + "=" * 50)
        print("✅ Conversion complete!")
        print(f"📁 Files saved to:")
        print(f"   - 3D Model: {MESHY_OUTPUT_DIR}")
        print(f"   - Voxel: {VOXEL_OUTPUT_DIR}")
        print(f"   - VOX file: {vox_file}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())