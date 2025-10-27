#!/usr/bin/env python3
"""
Analyze VOX file structure and compare with OBJ
"""
import struct
import numpy as np

def analyze_vox_file(vox_path):
    """Analyze VOX file structure"""
    with open(vox_path, 'rb') as f:
        # Read header
        magic = f.read(4)
        version = struct.unpack('<I', f.read(4))[0]
        print(f"Magic: {magic}")
        print(f"Version: {version}")
        
        # Read MAIN chunk
        main_id = f.read(4)
        main_content_size = struct.unpack('<I', f.read(4))[0]
        main_children_size = struct.unpack('<I', f.read(4))[0]
        print(f"MAIN chunk - Content: {main_content_size}, Children: {main_children_size}")
        
        # Read SIZE chunk
        size_id = f.read(4)
        size_content_size = struct.unpack('<I', f.read(4))[0]
        size_children_size = struct.unpack('<I', f.read(4))[0]
        size_x = struct.unpack('<I', f.read(4))[0]
        size_y = struct.unpack('<I', f.read(4))[0]
        size_z = struct.unpack('<I', f.read(4))[0]
        print(f"SIZE chunk - Dimensions: {size_x}x{size_y}x{size_z}")
        
        # Read XYZI chunk
        xyzi_id = f.read(4)
        xyzi_content_size = struct.unpack('<I', f.read(4))[0]
        xyzi_children_size = struct.unpack('<I', f.read(4))[0]
        num_voxels = struct.unpack('<I', f.read(4))[0]
        print(f"XYZI chunk - Voxels: {num_voxels}")
        
        # Read voxel data
        voxels = []
        for i in range(min(num_voxels, 20)):  # Show first 20 voxels
            x, y, z, color = struct.unpack('BBBB', f.read(4))
            voxels.append((x, y, z, color))
            print(f"Voxel {i}: ({x}, {y}, {z}) color={color}")
        
        if num_voxels > 20:
            print(f"... and {num_voxels - 20} more voxels")
        
        # Read RGBA chunk
        rgba_id = f.read(4)
        rgba_content_size = struct.unpack('<I', f.read(4))[0]
        rgba_children_size = struct.unpack('<I', f.read(4))[0]
        print(f"RGBA chunk - Content: {rgba_content_size}")
        
        # Read palette
        palette = []
        for i in range(min(256, rgba_content_size // 4)):
            r, g, b, a = struct.unpack('BBBB', f.read(4))
            palette.append((r, g, b, a))
            if i < 10:  # Show first 10 colors
                print(f"Color {i}: RGB({r}, {g}, {b}) A({a})")
        
        return {
            'dimensions': (size_x, size_y, size_z),
            'num_voxels': num_voxels,
            'voxels': voxels,
            'palette': palette
        }

def analyze_obj_file(obj_path):
    """Analyze OBJ file structure"""
    vertices = []
    faces = []
    
    with open(obj_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('v '):
                parts = line.split()
                if len(parts) >= 4:
                    vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif line.startswith('f '):
                parts = line.split()[1:]
                face = []
                for part in parts:
                    if part and '/' in part:
                        vertex_idx = int(part.split('/')[0]) - 1
                        face.append(vertex_idx)
                if len(face) >= 3:
                    faces.append(face)
    
    vertices = np.array(vertices)
    
    # Calculate bounding box
    min_coords = vertices.min(axis=0)
    max_coords = vertices.max(axis=0)
    dimensions = max_coords - min_coords
    
    print(f"OBJ Analysis:")
    print(f"Vertices: {len(vertices)}")
    print(f"Faces: {len(faces)}")
    print(f"Bounding box: {min_coords} to {max_coords}")
    print(f"Dimensions: {dimensions}")
    print(f"Max dimension: {dimensions.max()}")
    
    return {
        'vertices': len(vertices),
        'faces': len(faces),
        'min_coords': min_coords,
        'max_coords': max_coords,
        'dimensions': dimensions
    }

if __name__ == "__main__":
    print("=== VOX File Analysis ===")
    vox_data = analyze_vox_file("/workspace/model (11).vox")
    
    print("\n=== OBJ File Analysis ===")
    obj_data = analyze_obj_file("/workspace/model.obj")
    
    print("\n=== Comparison ===")
    print(f"OBJ has {obj_data['vertices']} vertices, {obj_data['faces']} faces")
    print(f"VOX has {vox_data['num_voxels']} voxels in {vox_data['dimensions']} grid")
    print(f"OBJ dimensions: {obj_data['dimensions']}")
    print(f"Expected voxel size for 32 voxels/unit: {int(32 * obj_data['dimensions'].max())}")
    print(f"Actual voxel size: {max(vox_data['dimensions'])}")