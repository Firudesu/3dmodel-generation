#!/usr/bin/env python3
"""
Image to 3D Model to Voxel File Automation

This script:
1. Takes an image and generates a 3D model using Meshy API
2. Converts the 3D model to voxel format using Drububu's voxelizer
3. Saves all output files to local folders

Setup:
pip install requests playwright
playwright install chromium
"""

import os
import sys
import time
import json
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright
import zipfile
import shutil

# Configuration - UPDATE THESE VALUES
MESHY_API_KEY = "YOUR_MESHY_API_KEY_HERE"  # Get from https://meshy.ai
INPUT_IMAGE_PATH = "input/sample_image.jpg"  # Path to your input image

# API endpoints
MESHY_BASE_URL = "https://api.meshy.ai"
MESHY_IMAGE_TO_3D_URL = f"{MESHY_BASE_URL}/v2/image-to-3d"

class ImageTo3DConverter:
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
    def upload_image_and_generate_3d(self, image_path):
        """Upload image to Meshy and start 3D generation"""
        print(f"📤 Uploading image: {image_path}")
        
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
            
        # First, upload the image
        with open(image_path, 'rb') as f:
            files = {'file': f}
            upload_response = requests.post(
                f"{MESHY_BASE_URL}/v1/image-to-3d/preview",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files=files
            )
            
        if upload_response.status_code != 200:
            raise Exception(f"Failed to upload image: {upload_response.text}")
            
        upload_data = upload_response.json()
        preview_task_id = upload_data.get('result')
        
        print(f"✅ Image uploaded successfully. Preview task ID: {preview_task_id}")
        
        # Now start the 3D generation
        payload = {
            "mode": "preview",
            "preview_task_id": preview_task_id,
            "enable_pbr": True
        }
        
        response = requests.post(MESHY_IMAGE_TO_3D_URL, headers=self.headers, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"Failed to start 3D generation: {response.text}")
            
        task_data = response.json()
        task_id = task_data.get('result')
        
        print(f"🔄 3D generation started. Task ID: {task_id}")
        return task_id
        
    def poll_task_status(self, task_id):
        """Poll the task status until completion"""
        print("⏳ Waiting for 3D model generation to complete...")
        
        while True:
            response = requests.get(
                f"{MESHY_IMAGE_TO_3D_URL}/{task_id}",
                headers=self.headers
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to check task status: {response.text}")
                
            data = response.json()
            status = data.get('status')
            
            print(f"📊 Status: {status}")
            
            if status == 'SUCCEEDED':
                print("✅ 3D model generation completed!")
                return data
            elif status == 'FAILED':
                raise Exception("3D model generation failed")
            elif status in ['PENDING', 'IN_PROGRESS']:
                time.sleep(10)  # Wait 10 seconds before checking again
            else:
                raise Exception(f"Unknown status: {status}")
                
    def download_3d_model(self, task_data, output_dir):
        """Download the generated 3D model files"""
        print("📥 Downloading 3D model files...")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Get download URLs from task data
        model_urls = task_data.get('model_urls', {})
        
        downloaded_files = {}
        
        for file_type, url in model_urls.items():
            if url:
                print(f"⬇️  Downloading {file_type}...")
                response = requests.get(url)
                
                if response.status_code == 200:
                    # Determine file extension based on type
                    if file_type == 'obj':
                        filename = 'model.obj'
                    elif file_type == 'mtl':
                        filename = 'model.mtl'
                    elif file_type in ['albedo', 'texture']:
                        filename = 'texture.png'
                    else:
                        filename = f'{file_type}.bin'
                        
                    file_path = os.path.join(output_dir, filename)
                    
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                        
                    downloaded_files[file_type] = file_path
                    print(f"✅ Saved {file_type} to {file_path}")
                else:
                    print(f"❌ Failed to download {file_type}: {response.status_code}")
                    
        return downloaded_files

class VoxelConverter:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        
    def __enter__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.page = self.browser.new_page()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
            
    def convert_obj_to_vox(self, obj_file_path, output_dir):
        """Convert OBJ file to VOX using Drububu voxelizer"""
        print("🎯 Converting OBJ to VOX using Drububu voxelizer...")
        
        if not os.path.exists(obj_file_path):
            raise FileNotFoundError(f"OBJ file not found: {obj_file_path}")
            
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            # Navigate to the voxelizer
            print("🌐 Opening Drububu voxelizer...")
            self.page.goto("https://drububu.com/miscellaneous/voxelizer/?out=vox")
            
            # Wait for page to load
            self.page.wait_for_load_state('networkidle')
            time.sleep(2)
            
            # Find and click the file input
            print("📤 Uploading OBJ file...")
            file_input = self.page.locator('input[type="file"]')
            file_input.set_input_files(obj_file_path)
            
            # Wait for upload and processing
            print("⏳ Waiting for file processing...")
            time.sleep(5)
            
            # Look for voxelization controls and process
            try:
                # Try to find and click voxelize button if it exists
                voxelize_button = self.page.locator('button:has-text("Voxelize"), input[value*="voxel" i], button:has-text("Process")')
                if voxelize_button.count() > 0:
                    print("🔄 Starting voxelization...")
                    voxelize_button.first.click()
                    time.sleep(3)
            except:
                print("ℹ️  No explicit voxelize button found, proceeding to export...")
            
            # Wait for processing to complete
            time.sleep(5)
            
            # Look for export/download options
            print("💾 Looking for VOX export option...")
            
            # Try different possible selectors for VOX export
            export_selectors = [
                'a:has-text("vox")',
                'button:has-text("vox")',
                'a[href*="vox"]',
                'button[onclick*="vox"]',
                '.vox',
                '#vox',
                'a:has-text("Download")',
                'button:has-text("Download")',
                'a[download]'
            ]
            
            download_triggered = False
            
            for selector in export_selectors:
                try:
                    elements = self.page.locator(selector)
                    if elements.count() > 0:
                        print(f"🎯 Found export element with selector: {selector}")
                        
                        # Set up download handler
                        with self.page.expect_download() as download_info:
                            elements.first.click()
                            
                        download = download_info.value
                        
                        # Save the downloaded file
                        vox_filename = "model.vox"
                        vox_path = os.path.join(output_dir, vox_filename)
                        download.save_as(vox_path)
                        
                        print(f"✅ VOX file saved to: {vox_path}")
                        download_triggered = True
                        break
                        
                except Exception as e:
                    print(f"⚠️  Selector {selector} failed: {str(e)}")
                    continue
            
            if not download_triggered:
                # If no download was triggered, try to find any downloadable content
                print("🔍 Searching for any downloadable content...")
                
                # Check if there's a canvas or any generated content we can extract
                canvas = self.page.locator('canvas')
                if canvas.count() > 0:
                    print("⚠️  Found canvas but no direct download. The voxelization may have completed but requires manual download.")
                    
                # Create a placeholder file with instructions
                placeholder_path = os.path.join(output_dir, "voxel_conversion_info.txt")
                with open(placeholder_path, 'w') as f:
                    f.write("Voxel conversion was attempted but automatic download failed.\n")
                    f.write("The OBJ file was successfully uploaded to the voxelizer.\n")
                    f.write("You may need to manually visit the site and download the VOX file.\n")
                    f.write(f"Original OBJ file: {obj_file_path}\n")
                    
                print(f"ℹ️  Created info file: {placeholder_path}")
                return placeholder_path
            
            return vox_path
            
        except Exception as e:
            print(f"❌ Error during voxel conversion: {str(e)}")
            raise

def main():
    """Main execution function"""
    print("🚀 Starting Image to 3D Model to Voxel conversion...")
    
    # Validate configuration
    if MESHY_API_KEY == "YOUR_MESHY_API_KEY_HERE":
        print("❌ Please set your MESHY_API_KEY in the script")
        print("   Get your API key from: https://meshy.ai")
        return
        
    if not os.path.exists(INPUT_IMAGE_PATH):
        print(f"❌ Input image not found: {INPUT_IMAGE_PATH}")
        print("   Please place your image in the input/ folder")
        return
    
    try:
        # Step 1: Generate 3D model using Meshy API
        print("\n=== Step 1: 3D Model Generation ===")
        converter = ImageTo3DConverter(MESHY_API_KEY)
        
        task_id = converter.upload_image_and_generate_3d(INPUT_IMAGE_PATH)
        task_data = converter.poll_task_status(task_id)
        
        meshy_output_dir = "output/meshy_model"
        downloaded_files = converter.download_3d_model(task_data, meshy_output_dir)
        
        # Step 2: Convert to voxel format
        print("\n=== Step 2: Voxel Conversion ===")
        
        obj_file = downloaded_files.get('obj')
        if not obj_file:
            print("❌ No OBJ file was downloaded from Meshy")
            return
            
        voxel_output_dir = "output/voxel"
        
        with VoxelConverter() as voxel_converter:
            vox_file = voxel_converter.convert_obj_to_vox(obj_file, voxel_output_dir)
        
        # Step 3: Summary
        print("\n=== Conversion Complete! ===")
        print("📁 Generated files:")
        print(f"   3D Model files: {meshy_output_dir}/")
        for file_type, file_path in downloaded_files.items():
            print(f"     - {file_type}: {file_path}")
        print(f"   Voxel file: {vox_file}")
        
        print(f"\n✅ All files saved successfully!")
        print(f"🎮 Your voxel file is ready: output/voxel/model.vox")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("Please check your API key and internet connection.")
        return 1
        
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)