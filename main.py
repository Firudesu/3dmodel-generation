#!/usr/bin/env python3
"""
Image → 3D Model → Voxel File Automation
Converts an image to a 3D model using Meshy API, then to a voxel file using Drububu.
"""

import os
import sys
import time
import json
import base64
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright
from typing import Optional, Dict, Any

# Configuration
MESHY_API_KEY = os.getenv('MESHY_API_KEY', 'YOUR_MESHY_API_KEY_HERE')  # Replace with your API key
MESHY_API_BASE_URL = 'https://api.meshy.ai'
DRUBUBU_URL = 'https://drububu.com/miscellaneous/voxelizer/?out=vox'

# File paths
INPUT_IMAGE_PATH = 'input/sample_image.jpg'  # Change this to your input image
OUTPUT_DIR = Path('output')
MESHY_OUTPUT_DIR = OUTPUT_DIR / 'meshy_model'
VOXEL_OUTPUT_DIR = OUTPUT_DIR / 'voxel'

# Ensure output directories exist
MESHY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
VOXEL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class MeshyAPI:
    """Handles interaction with Meshy API for 3D model generation."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    def create_image_to_3d_task(self, image_path: str) -> Optional[str]:
        """
        Creates an image-to-3d task using Meshy API.
        Returns task ID if successful, None otherwise.
        """
        print(f"📤 Uploading image to Meshy API: {image_path}")
        
        # Read and encode image
        try:
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
        except FileNotFoundError:
            print(f"❌ Error: Image file not found: {image_path}")
            return None
        
        # Determine image mime type
        mime_type = 'image/jpeg'
        if image_path.lower().endswith('.png'):
            mime_type = 'image/png'
        
        # Prepare request data - using correct Meshy API format
        data = {
            'image_url': f'data:{mime_type};base64,{image_data}',
            'enable_pbr': True,
            'ai_model': 'meshy-4',  # Using latest model
            'topology': 'quad',  # or 'triangle'
            'target_polycount': 30000  # Reasonable poly count for voxelization
        }
        
        # Make API request
        try:
            response = requests.post(
                f'{MESHY_API_BASE_URL}/v2/image-to-3d',
                headers=self.headers,
                json=data,
                timeout=30
            )
            
            if response.status_code in [200, 201, 202]:
                task_data = response.json()
                task_id = task_data.get('result') or task_data.get('task_id') or task_data.get('id')
                if task_id:
                    print(f"✅ Task created successfully. Task ID: {task_id}")
                    return task_id
                else:
                    print(f"❌ No task ID in response: {task_data}")
                    return None
            else:
                print(f"❌ Failed to create task. Status: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ API request failed: {e}")
            return None
    
    def check_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Check the status of a Meshy task.
        Returns task data including status and URLs when ready.
        """
        try:
            response = requests.get(
                f'{MESHY_API_BASE_URL}/v2/image-to-3d/{task_id}',
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Failed to check status. Status: {response.status_code}")
                return {}
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Status check failed: {e}")
            return {}
    
    def wait_for_completion(self, task_id: str, max_wait: int = 600) -> Optional[Dict[str, Any]]:
        """
        Wait for a task to complete, polling every 5 seconds.
        Returns task data when complete or None if timeout/error.
        """
        print("⏳ Waiting for 3D model generation...")
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            task_data = self.check_task_status(task_id)
            
            # Handle different status field names
            status = (task_data.get('status') or 
                     task_data.get('task_status') or 
                     'UNKNOWN').upper()
            
            if status in ['SUCCEEDED', 'SUCCESS', 'COMPLETED', 'DONE']:
                print("✅ 3D model generated successfully!")
                return task_data
            elif status in ['FAILED', 'ERROR', 'CANCELLED']:
                error_msg = (task_data.get('message') or 
                           task_data.get('error') or 
                           task_data.get('error_message') or 
                           'Unknown error')
                print(f"❌ Task failed: {error_msg}")
                return None
            elif status in ['PENDING', 'IN_PROGRESS', 'PROCESSING', 'RUNNING']:
                progress = task_data.get('progress', 0)
                print(f"⏳ Status: {status} - Progress: {progress}%")
                time.sleep(5)
            else:
                print(f"❓ Unknown status: {status}")
                # Check if we have model URLs anyway
                if task_data.get('model_urls') or task_data.get('model_url'):
                    print("✅ Model appears ready despite unknown status")
                    return task_data
                time.sleep(5)
        
        print("❌ Timeout: Model generation took too long")
        return None
    
    def download_model_files(self, task_data: Dict[str, Any], output_dir: Path) -> bool:
        """
        Download model files (OBJ, MTL, textures) from completed task.
        Returns True if successful, False otherwise.
        """
        print("📥 Downloading 3D model files...")
        
        # Try different possible response structures
        model_urls = (task_data.get('model_urls') or 
                     task_data.get('model') or 
                     task_data.get('outputs') or 
                     {})
        
        # If model_urls is a string (single URL), convert to dict
        if isinstance(model_urls, str):
            model_urls = {'obj': model_urls}
        
        # Also check for direct URL fields
        if not model_urls:
            if task_data.get('obj_url'):
                model_urls['obj'] = task_data['obj_url']
            if task_data.get('mtl_url'):
                model_urls['mtl'] = task_data['mtl_url']
            if task_data.get('texture_urls'):
                model_urls['textures'] = task_data['texture_urls']
        
        if not model_urls:
            print("❌ No model URLs found in task data")
            print(f"Task data keys: {list(task_data.keys())}")
            return False
        
        files_downloaded = []
        
        # Download OBJ file
        obj_url = model_urls.get('obj') or model_urls.get('obj_url')
        if obj_url:
            obj_path = output_dir / 'model.obj'
            if self._download_file(obj_url, obj_path):
                files_downloaded.append('model.obj')
        
        # Download MTL file
        mtl_url = model_urls.get('mtl') or model_urls.get('mtl_url')
        if mtl_url:
            mtl_path = output_dir / 'model.mtl'
            if self._download_file(mtl_url, mtl_path):
                files_downloaded.append('model.mtl')
        
        # Download texture files
        textures = model_urls.get('textures') or model_urls.get('texture_urls') or []
        if isinstance(textures, str):
            textures = [textures]
        
        for i, texture_url in enumerate(textures):
            texture_path = output_dir / f'texture_{i}.png'
            if self._download_file(texture_url, texture_path):
                files_downloaded.append(f'texture_{i}.png')
        
        # Try downloading a GLB file if available (alternative format)
        glb_url = model_urls.get('glb') or model_urls.get('glb_url')
        if glb_url:
            glb_path = output_dir / 'model.glb'
            if self._download_file(glb_url, glb_path):
                files_downloaded.append('model.glb')
        
        if files_downloaded:
            print(f"✅ Downloaded files: {', '.join(files_downloaded)}")
            return True
        else:
            print("❌ Failed to download any model files")
            return False
    
    def _download_file(self, url: str, output_path: Path) -> bool:
        """Helper method to download a file from URL."""
        try:
            response = requests.get(url, timeout=30, stream=True)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
        except Exception as e:
            print(f"❌ Failed to download {output_path.name}: {e}")
        return False


class DrububuVoxelizer:
    """Handles browser automation for Drububu voxelizer."""
    
    def __init__(self):
        self.browser = None
        self.page = None
    
    def convert_to_voxel(self, obj_file_path: Path, output_dir: Path) -> bool:
        """
        Convert OBJ file to VOX using Drububu voxelizer.
        Returns True if successful, False otherwise.
        """
        print(f"🌐 Opening Drububu voxelizer...")
        
        with sync_playwright() as p:
            try:
                # Launch browser (headless for automation)
                self.browser = p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
                context = self.browser.new_context(
                    accept_downloads=True
                )
                self.page = context.new_page()
                
                # Set download path
                self.page.context.set_default_timeout(60000)  # 60 second timeout
                
                # Navigate to Drububu
                print(f"📍 Navigating to: {DRUBUBU_URL}")
                self.page.goto(DRUBUBU_URL, wait_until='networkidle')
                time.sleep(3)  # Give page time to fully load
                
                # Upload OBJ file
                print(f"📤 Uploading OBJ file: {obj_file_path}")
                
                # Try multiple file input selectors
                file_input_selectors = [
                    'input[type="file"]',
                    '#fileInput',
                    '.file-input',
                    'input[accept*=".obj"]'
                ]
                
                file_uploaded = False
                for selector in file_input_selectors:
                    try:
                        if self.page.locator(selector).count() > 0:
                            self.page.locator(selector).first.set_input_files(str(obj_file_path))
                            file_uploaded = True
                            print(f"✅ File uploaded using selector: {selector}")
                            break
                    except Exception:
                        continue
                
                if not file_uploaded:
                    print("❌ Could not find file input element")
                    return False
                
                # Wait for processing
                print("⏳ Waiting for voxelization to complete...")
                time.sleep(8)  # Give more time for processing
                
                # Look for export options
                print("🔍 Looking for export options...")
                
                # Try to find and click VOX export button
                # Updated selectors based on common patterns
                vox_export_selectors = [
                    'button:has-text("VOX")',
                    'a:has-text("VOX")',
                    'button:has-text("Export as VOX")',
                    'button:has-text("Download VOX")',
                    'button:has-text("Download as VOX")',
                    '[data-format="vox"]',
                    '.export-vox',
                    '#export-vox',
                    'button[onclick*="vox"]',
                    'a[href*=".vox"]',
                    'button:has-text("Export")',
                    'button:has-text("Download")'
                ]
                
                download_triggered = False
                for selector in vox_export_selectors:
                    try:
                        elements = self.page.locator(selector).all()
                        for element in elements:
                            try:
                                # Check if element is visible
                                if element.is_visible():
                                    print(f"✅ Found potential export button: {selector}")
                                    
                                    # Start waiting for download before clicking
                                    with self.page.expect_download(timeout=5000) as download_info:
                                        element.click()
                                        download = download_info.value
                                        
                                        # Save the downloaded file
                                        vox_path = output_dir / 'model.vox'
                                        download.save_as(str(vox_path))
                                        print(f"✅ VOX file saved to: {vox_path}")
                                        download_triggered = True
                                        break
                            except Exception:
                                continue
                        
                        if download_triggered:
                            break
                    except Exception:
                        continue
                
                if not download_triggered:
                    # Try to trigger download via JavaScript console commands
                    print("⚠️ Standard export not found, trying JavaScript methods...")
                    
                    js_commands = [
                        "exportVOX()",
                        "downloadVOX()",
                        "exportModel('vox')",
                        "download('vox')",
                        "saveAs('vox')",
                        "document.querySelector('button').click()",  # Click first button
                    ]
                    
                    for js_cmd in js_commands:
                        try:
                            print(f"Trying JS: {js_cmd}")
                            with self.page.expect_download(timeout=3000) as download_info:
                                self.page.evaluate(js_cmd)
                                download = download_info.value
                                vox_path = output_dir / 'model.vox'
                                download.save_as(str(vox_path))
                                print(f"✅ VOX file saved via JS: {vox_path}")
                                download_triggered = True
                                break
                        except Exception:
                            continue
                
                if not download_triggered:
                    print("\n" + "="*60)
                    print("❌ Automated download failed. The site structure may have changed.")
                    print("\n📋 Manual conversion steps:")
                    print("1. Open: https://drububu.com/miscellaneous/voxelizer/?out=vox")
                    print(f"2. Upload: {obj_file_path.absolute()}")
                    print("3. Select VOX format and download")
                    print("4. Save to: output/voxel/")
                    print("="*60)
                    return False
                
                return True
                
            except Exception as e:
                print(f"❌ Browser automation failed: {e}")
                import traceback
                traceback.print_exc()
                return False
            finally:
                if self.browser:
                    self.browser.close()


def main():
    """Main workflow orchestration."""
    print("=" * 60)
    print("🎨 Image → 3D Model → Voxel File Automation")
    print("=" * 60)
    
    # Check if API key is set
    if MESHY_API_KEY == 'YOUR_MESHY_API_KEY_HERE':
        print("❌ Error: Please set your MESHY_API_KEY in the script or environment")
        print("   You can get an API key from: https://www.meshy.ai")
        sys.exit(1)
    
    # Check if input image exists
    if not Path(INPUT_IMAGE_PATH).exists():
        print(f"❌ Error: Input image not found: {INPUT_IMAGE_PATH}")
        print("   Please place your image in the input/ folder")
        sys.exit(1)
    
    # Step 1: Generate 3D model with Meshy
    print("\n📦 Step 1: Generating 3D model with Meshy API")
    print("-" * 40)
    
    meshy = MeshyAPI(MESHY_API_KEY)
    
    # Create task
    task_id = meshy.create_image_to_3d_task(INPUT_IMAGE_PATH)
    if not task_id:
        print("❌ Failed to create Meshy task")
        sys.exit(1)
    
    # Wait for completion
    task_data = meshy.wait_for_completion(task_id)
    if not task_data:
        print("❌ Failed to generate 3D model")
        sys.exit(1)
    
    # Download model files
    if not meshy.download_model_files(task_data, MESHY_OUTPUT_DIR):
        print("❌ Failed to download model files")
        sys.exit(1)
    
    print(f"✅ 3D model files saved to: {MESHY_OUTPUT_DIR}")
    
    # Step 2: Convert to voxel with Drububu
    print("\n🧊 Step 2: Converting to voxel with Drububu")
    print("-" * 40)
    
    obj_file = MESHY_OUTPUT_DIR / 'model.obj'
    if not obj_file.exists():
        print("❌ Error: OBJ file not found")
        sys.exit(1)
    
    voxelizer = DrububuVoxelizer()
    if not voxelizer.convert_to_voxel(obj_file, VOXEL_OUTPUT_DIR):
        print("❌ Failed to convert to voxel")
        print("💡 You can try manually at: https://drububu.com/miscellaneous/voxelizer/")
        sys.exit(1)
    
    # Success!
    print("\n" + "=" * 60)
    print("🎉 Conversion complete!")
    print(f"📁 Files saved to:")
    print(f"   • 3D Model: {MESHY_OUTPUT_DIR.absolute()}")
    print(f"   • Voxel:    {VOXEL_OUTPUT_DIR.absolute()}")
    print("=" * 60)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)