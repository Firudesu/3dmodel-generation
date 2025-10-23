#!/usr/bin/env python3
"""
Real voxel conversion from OBJ to VOX format
Converts 3D models to voxel format using Python
"""

import numpy as np
import struct
from pathlib import Path

def parse_obj_file(obj_path):
    """Parse OBJ file and extract vertices and faces"""
    vertices = []
    faces = []
    
    with open(obj_path, 'r') as f:
        for line in f:
            if line.startswith('v '):
                # Vertex
                parts = line.strip().split()
                vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif line.startswith('f '):
                # Face
                parts = line.strip().split()[1:]
                face = []
                for part in parts:
                    # Handle face formats: vertex, vertex/texture, vertex/texture/normal, vertex//normal
                    vertex_idx = int(part.split('/')[0]) - 1  # OBJ indices start at 1
                    face.append(vertex_idx)
                faces.append(face)
    
    return np.array(vertices), faces

def voxelize_mesh(vertices, faces, voxel_size=32):
    """Convert mesh to voxel grid"""
    if len(vertices) == 0:
        return np.zeros((voxel_size, voxel_size, voxel_size), dtype=bool)
    
    # Find bounding box
    min_coords = vertices.min(axis=0)
    max_coords = vertices.max(axis=0)
    
    # Add padding
    padding = (max_coords - min_coords) * 0.1
    min_coords -= padding
    max_coords += padding
    
    # Scale to voxel grid
    scale = voxel_size / (max_coords - min_coords).max()
    
    # Create voxel grid
    voxel_grid = np.zeros((voxel_size, voxel_size, voxel_size), dtype=bool)
    
    # Voxelize each face
    for face in faces:
        if len(face) < 3:
            continue
            
        # Get face vertices
        face_verts = vertices[face]
        
        # Transform to voxel space
        voxel_verts = (face_verts - min_coords) * scale
        voxel_verts = np.clip(voxel_verts, 0, voxel_size - 1).astype(int)
        
        # Rasterize triangle (simple approach - fill bounding box)
        min_v = voxel_verts.min(axis=0)
        max_v = voxel_verts.max(axis=0)
        
        for x in range(min_v[0], min(max_v[0] + 1, voxel_size)):
            for y in range(min_v[1], min(max_v[1] + 1, voxel_size)):
                for z in range(min_v[2], min(max_v[2] + 1, voxel_size)):
                    voxel_grid[x, y, z] = True
    
    # Fill interior (flood fill from edges to find exterior, then invert)
    filled = flood_fill_exterior(voxel_grid)
    
    return filled

def flood_fill_exterior(voxel_grid):
    """Fill the interior of the voxel model"""
    size = voxel_grid.shape[0]
    filled = voxel_grid.copy()
    
    # Create a slightly larger grid to ensure we can flood fill from outside
    padded = np.zeros((size + 2, size + 2, size + 2), dtype=bool)
    padded[1:-1, 1:-1, 1:-1] = voxel_grid
    
    # Flood fill from corner
    stack = [(0, 0, 0)]
    exterior = np.zeros_like(padded, dtype=bool)
    
    while stack:
        x, y, z = stack.pop()
        
        if x < 0 or x >= padded.shape[0] or y < 0 or y >= padded.shape[1] or z < 0 or z >= padded.shape[2]:
            continue
            
        if exterior[x, y, z] or padded[x, y, z]:
            continue
            
        exterior[x, y, z] = True
        
        # Add neighbors
        stack.extend([
            (x+1, y, z), (x-1, y, z),
            (x, y+1, z), (x, y-1, z),
            (x, y, z+1), (x, y, z-1)
        ])
    
    # Interior = not exterior and not boundary
    interior = ~exterior[1:-1, 1:-1, 1:-1]
    
    # Combine boundary and interior
    return voxel_grid | interior

def create_vox_file(voxel_grid, output_path, palette_idx=1):
    """Create a VOX file from voxel grid"""
    size = voxel_grid.shape[0]
    
    # Get voxel positions
    voxel_positions = np.argwhere(voxel_grid)
    num_voxels = len(voxel_positions)
    
    with open(output_path, 'wb') as f:
        # VOX header
        f.write(b'VOX ')
        f.write(struct.pack('<I', 150))  # Version
        
        # Calculate chunk sizes
        size_chunk_size = 12
        xyzi_chunk_size = 4 + num_voxels * 4
        main_children_size = (12 + size_chunk_size) + (12 + xyzi_chunk_size)
        
        # MAIN chunk
        f.write(b'MAIN')
        f.write(struct.pack('<I', 0))  # MAIN chunk has no content
        f.write(struct.pack('<I', main_children_size))
        
        # SIZE chunk
        f.write(b'SIZE')
        f.write(struct.pack('<I', size_chunk_size))
        f.write(struct.pack('<I', 0))  # No children
        f.write(struct.pack('<I', size))  # Size X
        f.write(struct.pack('<I', size))  # Size Y
        f.write(struct.pack('<I', size))  # Size Z
        
        # XYZI chunk
        f.write(b'XYZI')
        f.write(struct.pack('<I', xyzi_chunk_size))
        f.write(struct.pack('<I', 0))  # No children
        f.write(struct.pack('<I', num_voxels))  # Number of voxels
        
        # Write voxel data
        for pos in voxel_positions:
            x, y, z = pos
            f.write(struct.pack('BBBB', x, y, z, palette_idx))
    
    return output_path

def convert_obj_to_vox(obj_path, output_path=None, voxel_size=64):
    """Main conversion function"""
    if output_path is None:
        output_path = Path(obj_path).with_suffix('.vox')
    
    print(f"Converting {obj_path} to voxels...")
    
    # Parse OBJ file
    vertices, faces = parse_obj_file(obj_path)
    print(f"Loaded {len(vertices)} vertices and {len(faces)} faces")
    
    if len(vertices) == 0:
        raise ValueError("No vertices found in OBJ file")
    
    # Voxelize
    print(f"Voxelizing to {voxel_size}x{voxel_size}x{voxel_size} grid...")
    voxel_grid = voxelize_mesh(vertices, faces, voxel_size)
    
    num_voxels = np.sum(voxel_grid)
    print(f"Generated {num_voxels} voxels")
    
    if num_voxels == 0:
        raise ValueError("No voxels generated - model might be too small or invalid")
    
    # Create VOX file
    create_vox_file(voxel_grid, output_path)
    print(f"Saved VOX file: {output_path}")
    
    return output_path

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        obj_file = sys.argv[1]
        vox_file = sys.argv[2] if len(sys.argv) > 2 else None
        convert_obj_to_vox(obj_file, vox_file)
    else:
        print("Usage: python voxel_converter.py input.obj [output.vox]")