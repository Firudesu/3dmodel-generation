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
    """Convert mesh to voxel grid (cubic)"""
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

def voxelize_mesh_with_dimensions(vertices, faces, voxel_dims):
    """Convert mesh to voxel grid with custom dimensions"""
    if len(vertices) == 0:
        return np.zeros(tuple(voxel_dims), dtype=bool)
    
    # Find bounding box
    min_coords = vertices.min(axis=0)
    max_coords = vertices.max(axis=0)
    
    # Add padding
    padding = (max_coords - min_coords) * 0.1
    min_coords -= padding
    max_coords += padding
    
    # Calculate scale factors for each dimension
    model_dimensions = max_coords - min_coords
    scales = []
    for i in range(3):
        if model_dimensions[i] > 0:
            scales.append((voxel_dims[i] - 1) / model_dimensions[i])
        else:
            scales.append(1.0)
    
    # Create voxel grid
    voxel_grid = np.zeros(tuple(voxel_dims), dtype=bool)
    
    # Voxelize each face
    for face in faces:
        if len(face) < 3:
            continue
            
        # Get face vertices
        face_verts = vertices[face]
        
        # Transform to voxel space
        voxel_verts = np.zeros_like(face_verts)
        for i in range(3):
            voxel_verts[:, i] = (face_verts[:, i] - min_coords[i]) * scales[i]
        
        voxel_verts = np.clip(voxel_verts, 0, np.array(voxel_dims) - 1).astype(int)
        
        # Rasterize triangle (simple approach - fill bounding box)
        min_v = voxel_verts.min(axis=0)
        max_v = voxel_verts.max(axis=0)
        
        for x in range(min_v[0], min(max_v[0] + 1, voxel_dims[0])):
            for y in range(min_v[1], min(max_v[1] + 1, voxel_dims[1])):
                for z in range(min_v[2], min(max_v[2] + 1, voxel_dims[2])):
                    voxel_grid[x, y, z] = True
    
    # Fill interior (flood fill from edges to find exterior, then invert)
    filled = flood_fill_exterior_with_dimensions(voxel_grid)
    
    return filled

def flood_fill_exterior(voxel_grid):
    """Fill the interior of the voxel model (cubic)"""
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

def flood_fill_exterior_with_dimensions(voxel_grid):
    """Fill the interior of the voxel model (custom dimensions)"""
    dims = voxel_grid.shape
    filled = voxel_grid.copy()
    
    # Create a slightly larger grid to ensure we can flood fill from outside
    padded_dims = [d + 2 for d in dims]
    padded = np.zeros(padded_dims, dtype=bool)
    
    # Copy the original grid with padding
    slices = tuple(slice(1, -1) for _ in dims)
    padded[slices] = voxel_grid
    
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
    interior = ~exterior[slices]
    
    # Combine boundary and interior
    return voxel_grid | interior

def create_vox_file(voxel_grid, output_path, palette_idx=1):
    """Create a VOX file from voxel grid (cubic)"""
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

def create_vox_file_with_dimensions(voxel_grid, output_path, voxel_dims, palette_idx=1):
    """Create a VOX file from voxel grid with custom dimensions"""
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
        f.write(struct.pack('<I', voxel_dims[0]))  # Size X
        f.write(struct.pack('<I', voxel_dims[1]))  # Size Y
        f.write(struct.pack('<I', voxel_dims[2]))  # Size Z
        
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

def convert_obj_to_vox(obj_path, output_path=None, voxel_size=None):
    """Main conversion function"""
    if output_path is None:
        output_path = Path(obj_path).with_suffix('.vox')
    
    print(f"Converting {obj_path} to voxels...")
    
    # Parse OBJ file
    vertices, faces = parse_obj_file(obj_path)
    print(f"Loaded {len(vertices)} vertices and {len(faces)} faces")
    
    if len(vertices) == 0:
        raise ValueError("No vertices found in OBJ file")
    
    # Calculate model dimensions and determine voxel grid size
    min_coords = vertices.min(axis=0)
    max_coords = vertices.max(axis=0)
    model_dimensions = max_coords - min_coords
    
    print(f"Model bounding box: {model_dimensions}")
    print(f"Model size: {model_dimensions[0]:.3f} x {model_dimensions[1]:.3f} x {model_dimensions[2]:.3f}")
    
    # If no voxel_size specified, calculate based on model dimensions
    if voxel_size is None:
        # Use the largest dimension as the base size, with a minimum of 32
        max_dimension = model_dimensions.max()
        voxel_size = max(32, int(max_dimension * 20))  # Scale factor of 20 voxels per unit
        print(f"Auto-calculated voxel size: {voxel_size}")
    else:
        print(f"Using specified voxel size: {voxel_size}")
    
    # Calculate individual dimensions for non-cubic voxel grid
    voxel_dims = []
    for i in range(3):
        if model_dimensions[i] > 0:
            # Scale proportionally to the largest dimension
            dim_size = int((model_dimensions[i] / max_dimension) * voxel_size)
            dim_size = max(1, dim_size)  # At least 1 voxel
        else:
            dim_size = 1
        voxel_dims.append(dim_size)
    
    print(f"Voxel grid dimensions: {voxel_dims[0]}x{voxel_dims[1]}x{voxel_dims[2]}")
    
    # Voxelize with calculated dimensions
    voxel_grid = voxelize_mesh_with_dimensions(vertices, faces, voxel_dims)
    
    num_voxels = np.sum(voxel_grid)
    print(f"Generated {num_voxels} voxels")
    
    if num_voxels == 0:
        raise ValueError("No voxels generated - model might be too small or invalid")
    
    # Create VOX file
    create_vox_file_with_dimensions(voxel_grid, output_path, voxel_dims)
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