#!/usr/bin/env python3
"""
Simple analysis of VOX and OBJ files without numpy
"""
import struct

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
        
        return {
            'dimensions': (size_x, size_y, size_z),
            'num_voxels': num_voxels,
            'voxels': voxels
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
    
    # Calculate bounding box
    if vertices:
        min_x = min(v[0] for v in vertices)
        max_x = max(v[0] for v in vertices)
        min_y = min(v[1] for v in vertices)
        max_y = max(v[1] for v in vertices)
        min_z = min(v[2] for v in vertices)
        max_z = max(v[2] for v in vertices)
        
        dimensions = (max_x - min_x, max_y - min_y, max_z - min_z)
        max_dimension = max(dimensions)
    else:
        dimensions = (0, 0, 0)
        max_dimension = 0
    
    print(f"OBJ Analysis:")
    print(f"Vertices: {len(vertices)}")
    print(f"Faces: {len(faces)}")
    print(f"Bounding box: ({min_x:.6f}, {min_y:.6f}, {min_z:.6f}) to ({max_x:.6f}, {max_y:.6f}, {max_z:.6f})")
    print(f"Dimensions: {dimensions}")
    print(f"Max dimension: {max_dimension}")
    
    return {
        'vertices': len(vertices),
        'faces': len(faces),
        'dimensions': dimensions,
        'max_dimension': max_dimension
    }

if __name__ == "__main__":
    print("=== VOX File Analysis ===")
    vox_data = analyze_vox_file("/workspace/output/voxel/improved_model.vox")
    
    print("\n=== OBJ File Analysis ===")
    obj_data = analyze_obj_file("/workspace/model.obj")
    
    print("\n=== Comparison ===")
    print(f"OBJ has {obj_data['vertices']} vertices, {obj_data['faces']} faces")
    print(f"VOX has {vox_data['num_voxels']} voxels in {vox_data['dimensions']} grid")
    print(f"OBJ dimensions: {obj_data['dimensions']}")
    print(f"Expected voxel size for 32 voxels/unit: {int(32 * obj_data['max_dimension'])}")
    print(f"Actual voxel size: {max(vox_data['dimensions'])}")
    
    # Check if the conversion makes sense
    if vox_data['num_voxels'] < 100:
        print("\n❌ PROBLEM: Very few voxels generated - conversion likely failed")
    if max(vox_data['dimensions']) < 10:
        print("❌ PROBLEM: Voxel grid is too small")
    if obj_data['max_dimension'] > 0 and max(vox_data['dimensions']) < int(32 * obj_data['max_dimension'] * 0.1):
        print("❌ PROBLEM: Voxel grid is much smaller than expected for the model size")