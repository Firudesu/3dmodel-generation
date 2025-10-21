#!/usr/bin/env python3
"""
Test script to verify the setup is working correctly
"""

import os
import sys
from pathlib import Path

def test_imports():
    """Test if all required modules can be imported"""
    print("🔄 Testing imports...")
    
    try:
        import requests
        print("✓ requests imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import requests: {e}")
        return False
    
    try:
        from playwright.sync_api import sync_playwright
        print("✓ playwright imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import playwright: {e}")
        return False
    
    return True

def test_playwright_browser():
    """Test if Playwright can launch a browser"""
    print("🔄 Testing Playwright browser...")
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://www.google.com")
            title = page.title()
            browser.close()
            
        print(f"✓ Browser test successful - page title: {title}")
        return True
    except Exception as e:
        print(f"❌ Browser test failed: {e}")
        return False

def test_directories():
    """Test if all required directories exist"""
    print("🔄 Testing directories...")
    
    required_dirs = [
        "input",
        "output",
        "output/meshy_model",
        "output/voxel"
    ]
    
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            print(f"❌ Directory missing: {dir_path}")
            return False
        else:
            print(f"✓ Directory exists: {dir_path}")
    
    return True

def test_configuration():
    """Test configuration variables"""
    print("🔄 Testing configuration...")
    
    # Read main.py to check configuration
    with open("main.py", "r") as f:
        content = f.read()
    
    if "YOUR_MESHY_API_KEY_HERE" in content:
        print("⚠️  MESHY_API_KEY not configured (this is expected for testing)")
    else:
        print("✓ MESHY_API_KEY appears to be configured")
    
    if "input/sample_image.jpg" in content:
        print("✓ INPUT_IMAGE_PATH is configured")
    else:
        print("❌ INPUT_IMAGE_PATH not found in configuration")
        return False
    
    return True

def main():
    """Run all tests"""
    print("🧪 Running setup tests...")
    print("=" * 40)
    
    tests = [
        ("Import Test", test_imports),
        ("Directory Test", test_directories),
        ("Configuration Test", test_configuration),
        ("Browser Test", test_playwright_browser),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed")
    
    print("\n" + "=" * 40)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! Setup is ready.")
        return 0
    else:
        print("❌ Some tests failed. Please check the setup.")
        return 1

if __name__ == "__main__":
    exit(main())