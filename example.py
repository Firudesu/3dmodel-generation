#!/usr/bin/env python3
"""
Example usage of the Image → 3D Model → Voxel File Automation

This script demonstrates how to use the automation with different configurations.
"""

import os
import shutil
from pathlib import Path

def create_sample_image():
    """Create a simple test image for demonstration"""
    print("🔄 Creating sample image...")
    
    # This is a placeholder - in a real scenario, you'd have an actual image
    sample_text = """This is a placeholder for a sample image.
In a real scenario, you would place an actual JPG or PNG file here.
The image should be placed in the input/ directory."""
    
    with open("input/sample_image.jpg", "w") as f:
        f.write(sample_text)
    
    print("✓ Sample image placeholder created")

def run_automation():
    """Run the main automation script"""
    print("🔄 Running automation...")
    
    # Import and run the main function
    from main import main as run_main
    return run_main()

def cleanup_output():
    """Clean up output files for fresh test"""
    print("🔄 Cleaning up previous output...")
    
    output_dir = Path("output")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    
    # Recreate directories
    os.makedirs("output/meshy_model", exist_ok=True)
    os.makedirs("output/voxel", exist_ok=True)
    
    print("✓ Output cleaned up")

def main():
    """Example usage"""
    print("📚 Image → 3D Model → Voxel File Automation Example")
    print("=" * 60)
    
    # Step 1: Setup
    print("\n1️⃣ Setting up example...")
    create_sample_image()
    
    # Step 2: Clean previous output
    print("\n2️⃣ Cleaning previous output...")
    cleanup_output()
    
    # Step 3: Run automation
    print("\n3️⃣ Running automation...")
    result = run_automation()
    
    # Step 4: Show results
    print("\n4️⃣ Results:")
    if result == 0:
        print("✅ Automation completed successfully!")
        
        # List output files
        output_dir = Path("output")
        if output_dir.exists():
            print("\n📁 Output files:")
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    file_path = Path(root) / file
                    print(f"   {file_path}")
    else:
        print("❌ Automation failed!")
    
    return result

if __name__ == "__main__":
    exit(main())