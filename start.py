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
        import numpy
        from PIL import Image
        return True
    except ImportError:
        return False

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    try:
        # Install Python packages
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("✅ Python packages installed")
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
    
    # Verify voxel converter dependencies
    print("🔍 Verifying voxel converter...")
    try:
        from voxel_converter import convert_obj_to_vox
        import numpy as np
        from PIL import Image
        print("✅ Voxel converter verified")
    except Exception as e:
        print(f"⚠️ Voxel converter check failed: {e}")
        print("⚠️ The app may not work properly for voxel conversion")
    
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
        
        # Use environment PORT if available, otherwise try default ports
        env_port = os.environ.get('PORT')
        if env_port:
            port = int(env_port)
            print(f"🌐 Using environment PORT: {port}")
            app.run(host='0.0.0.0', port=port, debug=False)
        else:
            # Try different ports in case 5000 is in use
            ports = [5000, 8080, 3000, 8000]
            for port in ports:
                try:
                    print(f"🌐 Trying to start on port {port}...")
                    app.run(host='0.0.0.0', port=port, debug=False)
                    break
                except OSError as e:
                    if "Address already in use" in str(e):
                        print(f"⚠️ Port {port} is in use, trying next port...")
                        continue
                    else:
                        raise e
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    except Exception as e:
        print(f"❌ Error starting web app: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())