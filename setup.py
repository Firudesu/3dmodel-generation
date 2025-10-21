#!/usr/bin/env python3
"""
Setup script for Image → 3D Model → Voxel File Automation
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during {description}: {e}")
        print(f"   Command: {command}")
        print(f"   Error: {e.stderr}")
        return False

def main():
    """Setup the environment"""
    print("🚀 Setting up Image → 3D Model → Voxel File Automation")
    print("=" * 60)
    
    # Install Python dependencies
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        return 1
    
    # Install Playwright browsers
    if not run_command("playwright install chromium", "Installing Playwright Chromium browser"):
        return 1
    
    # Create directories
    print("🔄 Creating directories...")
    os.makedirs("input", exist_ok=True)
    os.makedirs("output/meshy_model", exist_ok=True)
    os.makedirs("output/voxel", exist_ok=True)
    print("✓ Directories created")
    
    print("\n" + "=" * 60)
    print("✅ Setup complete!")
    print("\nNext steps:")
    print("1. Get a Meshy API key from https://meshy.ai/")
    print("2. Update MESHY_API_KEY in main.py")
    print("3. Place your image in input/ directory")
    print("4. Run: python main.py")
    
    return 0

if __name__ == "__main__":
    exit(main())