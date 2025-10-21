#!/usr/bin/env python3
"""
Command Line Interface for Image → 3D Model → Voxel File Automation
"""

import sys
import os
from pathlib import Path

def main():
    print("🚀 Image → 3D Model → Voxel File Automation")
    print("=" * 50)
    print()
    print("This automation now has a web-based interface!")
    print()
    print("🌐 To use the web interface:")
    print("   python3 app.py")
    print("   Then open http://localhost:5000 in your browser")
    print()
    print("📱 For Replit users:")
    print("   Just click the 'Run' button - it will start the web app automatically!")
    print()
    print("💡 The web interface provides:")
    print("   ✅ Easy file upload with drag & drop")
    print("   ✅ Real-time progress tracking")
    print("   ✅ Download links for all generated files")
    print("   ✅ Works perfectly in Replit and other web IDEs")
    print()
    
    # Check if running in Replit
    if os.path.exists('/home/runner'):
        print("🔧 Detected Replit environment - starting web app...")
        os.system("python3 app.py")
    else:
        print("💻 To start the web app, run: python3 app.py")

if __name__ == "__main__":
    main()