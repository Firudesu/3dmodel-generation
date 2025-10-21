#!/usr/bin/env python3
"""
Setup script for Image to Voxel automation

This script installs the required dependencies and sets up the environment.
"""

import subprocess
import sys
import os
from PIL import Image, ImageDraw

def install_dependencies():
    """Install required Python packages"""
    print("📦 Installing Python dependencies...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Python dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Python dependencies: {e}")
        return False
    
    return True

def install_playwright():
    """Install Playwright browser"""
    print("🎭 Installing Playwright Chromium browser...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        print("✅ Playwright Chromium installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Playwright browser: {e}")
        return False
    
    return True

def create_sample_image():
    """Create a sample image for testing"""
    print("🖼️  Creating sample image...")
    
    # Create a simple test image
    img = Image.new('RGB', (512, 512), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw a simple house-like shape
    # Base
    draw.rectangle([150, 300, 350, 450], fill='#8B4513', outline='black', width=2)
    
    # Roof
    draw.polygon([100, 300, 250, 200, 400, 300], fill='red', outline='black')
    
    # Door
    draw.rectangle([220, 350, 280, 450], fill='#654321', outline='black', width=2)
    
    # Windows
    draw.rectangle([170, 320, 210, 360], fill='#ADD8E6', outline='black', width=2)
    draw.rectangle([290, 320, 330, 360], fill='#ADD8E6', outline='black', width=2)
    
    # Save the image
    sample_path = "input/sample_image.jpg"
    img.save(sample_path, "JPEG")
    print(f"✅ Sample image created: {sample_path}")
    
    return True

def main():
    """Main setup function"""
    print("🚀 Setting up Image to Voxel automation environment...\n")
    
    # Check if we're in the right directory
    if not os.path.exists("requirements.txt"):
        print("❌ requirements.txt not found. Please run this script from the project root.")
        return 1
    
    # Install dependencies
    if not install_dependencies():
        return 1
    
    # Install Playwright
    if not install_playwright():
        return 1
    
    # Create sample image
    if not create_sample_image():
        return 1
    
    print("\n✅ Setup complete!")
    print("\n📋 Next steps:")
    print("1. Edit main.py and set your MESHY_API_KEY")
    print("   Get your API key from: https://meshy.ai")
    print("2. (Optional) Replace input/sample_image.jpg with your own image")
    print("3. Run: python main.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())