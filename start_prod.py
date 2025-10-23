#!/usr/bin/env python3
"""
Production startup script for Render deployment
"""

import os
import sys

def setup_directories():
    """Create necessary directories"""
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('output', exist_ok=True)
    os.makedirs('output/voxel', exist_ok=True)
    os.makedirs('output/meshy_model', exist_ok=True)
    print("✅ Directories created")

if __name__ == "__main__":
    print("🚀 3D Model Generator - Production Server")
    print("=" * 50)
    
    # Setup directories
    setup_directories()
    
    # The actual server is started by Gunicorn via the render.yaml config
    print("✅ Ready for Gunicorn to start the server")
    print("=" * 50)