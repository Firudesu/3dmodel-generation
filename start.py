#!/usr/bin/env python3
"""
Startup script for Image → 3D Model → Voxel File Automation
"""

import os
import sys
import subprocess

def check_dependencies():
    """Check if required packages are installed"""
    try:
        import flask
        import requests
        from playwright.sync_api import sync_playwright
        return True
    except ImportError:
        return False

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def main():
    """Main startup function"""
    print("🚀 Image → 3D Model → Voxel File Automation")
    print("=" * 50)
    
    # Check if we're in Replit
    if os.path.exists('/home/runner'):
        print("🔧 Detected Replit environment")
    else:
        print("💻 Local environment detected")
    
    # Check dependencies
    if not check_dependencies():
        print("📦 Installing missing dependencies...")
        if not install_dependencies():
            print("❌ Failed to install dependencies. Please run manually:")
            print("   pip install -r requirements.txt")
            print("   playwright install chromium")
            return 1
    
    # Create necessary directories
    print("📁 Creating directories...")
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('output', exist_ok=True)
    print("✅ Directories created")
    
    # Start the web app
    print("🌐 Starting web application...")
    print("📱 Open your browser and navigate to the URL shown below")
    print("=" * 50)
    
    try:
        from app import app
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    except Exception as e:
        print(f"❌ Error starting web app: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())