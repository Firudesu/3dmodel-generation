#!/usr/bin/env python3
"""
Quick run script for Replit/GitHub Codespaces
This script handles setup and runs the main automation
"""

import subprocess
import sys
import os

def install_dependencies():
    """Install required dependencies"""
    print("🔄 Installing dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("✓ Dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Image → 3D Model → Voxel File Automation")
    print("=" * 50)
    
    # Check if dependencies are installed
    try:
        import requests
        import numpy
        from PIL import Image
        print("✓ Dependencies already installed")
    except ImportError:
        print("📦 Installing dependencies...")
        if not install_dependencies():
            return 1
    
    # Run the main script
    print("\n🎯 Starting automation...")
    try:
        from main import main as run_main
        return run_main()
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())