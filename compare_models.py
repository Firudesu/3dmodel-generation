#!/usr/bin/env python3
"""
Compare the original and improved voxel models
"""
import struct

def analyze_vox_file(vox_path):
    """Analyze VOX file structure"""
    with open(vox_path, 'rb') as f:
        # Read header
        magic = f.read(4)
        version = struct.unpack('<I', f.read(4))[0]
        
        # Read MAIN chunk
        main_id = f.read(4)
        main_content_size = struct.unpack('<I', f.read(4))[0]
        main_children_size = struct.unpack('<I', f.read(4))[0]
        
        # Read SIZE chunk
        size_id = f.read(4)
        size_content_size = struct.unpack('<I', f.read(4))[0]
        size_children_size = struct.unpack('<I', f.read(4))[0]
        size_x = struct.unpack('<I', f.read(4))[0]
        size_y = struct.unpack('<I', f.read(4))[0]
        size_z = struct.unpack('<I', f.read(4))[0]
        
        # Read XYZI chunk
        xyzi_id = f.read(4)
        xyzi_content_size = struct.unpack('<I', f.read(4))[0]
        xyzi_children_size = struct.unpack('<I', f.read(4))[0]
        num_voxels = struct.unpack('<I', f.read(4))[0]
        
        return {
            'dimensions': (size_x, size_y, size_z),
            'num_voxels': num_voxels,
            'file_size': main_children_size
        }

def main():
    print("=== VOX Model Comparison ===\n")
    
    # Analyze original model
    try:
        original = analyze_vox_file("/workspace/model (11).vox")
        print("Original Model (model (11).vox):")
        print(f"  Dimensions: {original['dimensions'][0]}x{original['dimensions'][1]}x{original['dimensions'][2]}")
        print(f"  Voxels: {original['num_voxels']}")
        print(f"  File size: {original['file_size']} bytes")
    except FileNotFoundError:
        print("Original model not found")
        original = None
    
    # Analyze improved model
    try:
        improved = analyze_vox_file("/workspace/output/voxel/improved_model.vox")
        print("\nImproved Model (improved_model.vox):")
        print(f"  Dimensions: {improved['dimensions'][0]}x{improved['dimensions'][1]}x{improved['dimensions'][2]}")
        print(f"  Voxels: {improved['num_voxels']}")
        print(f"  File size: {improved['file_size']} bytes")
    except FileNotFoundError:
        print("Improved model not found")
        improved = None
    
    # Compare
    if original and improved:
        print("\n=== Improvements ===")
        voxel_improvement = improved['num_voxels'] / original['num_voxels']
        print(f"Voxel count: {voxel_improvement:.1f}x increase ({original['num_voxels']} → {improved['num_voxels']})")
        
        # Calculate voxel density
        orig_density = original['num_voxels'] / (original['dimensions'][0] * original['dimensions'][1] * original['dimensions'][2])
        impr_density = improved['num_voxels'] / (improved['dimensions'][0] * improved['dimensions'][1] * improved['dimensions'][2])
        print(f"Voxel density: {impr_density/orig_density:.1f}x increase ({orig_density:.3f} → {impr_density:.3f})")
        
        print(f"File size: {improved['file_size']/original['file_size']:.1f}x increase ({original['file_size']} → {improved['file_size']} bytes)")
        
        print("\n=== Quality Assessment ===")
        if improved['num_voxels'] > 1000:
            print("✅ Good voxel density - model should be well-represented")
        else:
            print("❌ Low voxel density - model may appear sparse")
            
        if improved['num_voxels'] > original['num_voxels'] * 2:
            print("✅ Significant improvement in detail")
        else:
            print("⚠️  Modest improvement - may need further optimization")

if __name__ == "__main__":
    main()