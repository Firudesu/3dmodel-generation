#!/usr/bin/env python3
"""
Real voxel conversion from OBJ to VOX format
Converts 3D models to voxel format using Python
"""

import numpy as np
import struct
import os
from pathlib import Path

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️ PIL not available - texture processing will be limited")

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

def voxelize_mesh(vertices, faces, voxel_size=None):
    """Convert mesh to voxel grid"""
    if len(vertices) == 0:
        # Use default size if no vertices
        size = voxel_size or 64
        return np.zeros((size, size, size), dtype=bool)
    
    # Find bounding box
    min_coords = vertices.min(axis=0)
    max_coords = vertices.max(axis=0)
    dimensions = max_coords - min_coords
    
    # Determine voxel size based on model dimensions if not specified
    if voxel_size is None:
        # Calculate appropriate voxel size based on model scale
        max_dimension = dimensions.max()
        if max_dimension > 100:
            voxel_size = 128  # Large models
        elif max_dimension > 10:
            voxel_size = 64   # Medium models
        else:
            voxel_size = 32   # Small models
        
        print(f"Auto-detected voxel size: {voxel_size}x{voxel_size}x{voxel_size} (model dimensions: {dimensions})")
    
    # Add padding
    padding = dimensions * 0.1
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

def process_texture_for_voxels(texture_path, voxel_grid):
    """Process texture image and map colors to voxel positions"""
    if not PIL_AVAILABLE:
        print("⚠️ PIL not available - skipping texture processing")
        return None
    
    try:
        # Load and process texture image
        with Image.open(texture_path) as img:
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize to reasonable size for processing
            img = img.resize((64, 64), Image.Resampling.LANCZOS)
            img_array = np.array(img)
            
            # Get voxel positions
            voxel_positions = np.argwhere(voxel_grid)
            
            if len(voxel_positions) == 0:
                return None
            
            # Map voxel positions to texture coordinates
            grid_size = voxel_grid.shape[0]
            texture_colors = []
            
            for pos in voxel_positions:
                # Map 3D position to 2D texture coordinates
                # Use X and Y coordinates, normalize to texture size
                tex_x = int((pos[0] / grid_size) * (img_array.shape[1] - 1))
                tex_y = int((pos[1] / grid_size) * (img_array.shape[0] - 1))
                
                # Clamp coordinates
                tex_x = max(0, min(tex_x, img_array.shape[1] - 1))
                tex_y = max(0, min(tex_y, img_array.shape[0] - 1))
                
                # Get RGB color
                r, g, b = img_array[tex_y, tex_x]
                
                # Convert RGB to palette index (simplified)
                # For now, use a simple mapping - could be improved with proper palette generation
                color_idx = ((r >> 5) << 5) | ((g >> 5) << 2) | (b >> 6)
                color_idx = max(1, min(color_idx, 255))  # Ensure valid palette range
                
                texture_colors.append(color_idx)
            
            print(f"✅ Processed texture with {len(texture_colors)} color mappings")
            return texture_colors
            
    except Exception as e:
        print(f"⚠️ Error processing texture: {e}")
        return None

def create_vox_file(voxel_grid, output_path, palette_idx=1, texture_colors=None):
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
        for i, pos in enumerate(voxel_positions):
            x, y, z = pos
            # Use texture color if available, otherwise default palette index
            color_idx = palette_idx
            if texture_colors is not None and i < len(texture_colors):
                color_idx = texture_colors[i]
            f.write(struct.pack('BBBB', x, y, z, color_idx))
    
    return output_path

def convert_obj_to_vox(obj_path, output_path=None, voxel_size=None, texture_path=None):
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
    voxel_grid = voxelize_mesh(vertices, faces, voxel_size)
    actual_size = voxel_grid.shape[0]
    print(f"Voxelizing to {actual_size}x{actual_size}x{actual_size} grid...")
    
    num_voxels = np.sum(voxel_grid)
    print(f"Generated {num_voxels} voxels")
    
    if num_voxels == 0:
        raise ValueError("No voxels generated - model might be too small or invalid")
    
    # Process texture if provided
    texture_colors = None
    if texture_path and os.path.exists(texture_path):
        print(f"Processing texture: {texture_path}")
        texture_colors = process_texture_for_voxels(texture_path, voxel_grid)
    
    # Create VOX file
    create_vox_file(voxel_grid, output_path, palette_idx=1, texture_colors=texture_colors)
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