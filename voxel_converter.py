#!/usr/bin/env python3
"""
Real voxel conversion from OBJ to VOX format
Converts 3D models to voxel format using Python with texture support
"""

import numpy as np
import struct
from pathlib import Path
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: PIL not available. Texture mapping will be disabled.")

def parse_obj_file(obj_path):
    """Parse OBJ file and extract vertices, faces, and texture coordinates"""
    vertices = []
    faces = []
    texture_coords = []
    texture_faces = []  # Store texture coordinate indices for faces
    
    with open(obj_path, 'r') as f:
        for line in f:
            if line.startswith('v '):
                # Vertex
                parts = line.strip().split()
                vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif line.startswith('vt '):
                # Texture coordinate
                parts = line.strip().split()
                texture_coords.append([float(parts[1]), float(parts[2])])
            elif line.startswith('f '):
                # Face
                parts = line.strip().split()[1:]
                face = []
                tex_face = []
                for part in parts:
                    # Handle face formats: vertex, vertex/texture, vertex/texture/normal, vertex//normal
                    indices = part.split('/')
                    vertex_idx = int(indices[0]) - 1  # OBJ indices start at 1
                    face.append(vertex_idx)
                    
                    # Get texture coordinate index if available
                    if len(indices) > 1 and indices[1]:
                        tex_idx = int(indices[1]) - 1
                        tex_face.append(tex_idx)
                    else:
                        tex_face.append(-1)  # No texture coordinate
                        
                faces.append(face)
                texture_faces.append(tex_face)
    
    return np.array(vertices), faces, np.array(texture_coords) if texture_coords else None, texture_faces

def calculate_voxel_dimensions(vertices, max_size=256, min_size=32):
    """Calculate optimal voxel dimensions based on model proportions"""
    if len(vertices) == 0:
        return 64, 64, 64
    
    # Find bounding box
    min_coords = vertices.min(axis=0)
    max_coords = vertices.max(axis=0)
    dimensions = max_coords - min_coords
    
    # Handle degenerate cases
    if np.any(dimensions <= 0):
        return 64, 64, 64
    
    # Find the maximum dimension
    max_dim = dimensions.max()
    if max_dim == 0:
        return 64, 64, 64
    
    # Calculate proportional sizes
    proportions = dimensions / max_dim
    
    # Start with max dimension at 64 (can be adjusted)
    base_size = 64
    voxel_dims = (proportions * base_size).astype(int)
    
    # Ensure minimum size
    voxel_dims = np.maximum(voxel_dims, min_size)
    
    # Ensure maximum size
    voxel_dims = np.minimum(voxel_dims, max_size)
    
    # Make sure no dimension is 0
    voxel_dims = np.maximum(voxel_dims, 1)
    
    return tuple(voxel_dims)

def voxelize_mesh(vertices, faces, voxel_dims=None, texture_coords=None, texture_faces=None, texture_image=None):
    """Convert mesh to voxel grid with optional texture mapping"""
    if len(vertices) == 0:
        if voxel_dims is None:
            voxel_dims = (64, 64, 64)
        return np.zeros(voxel_dims, dtype=np.uint8)
    
    # Calculate dimensions if not provided
    if voxel_dims is None:
        voxel_dims = calculate_voxel_dimensions(vertices)
    
    # Find bounding box
    min_coords = vertices.min(axis=0)
    max_coords = vertices.max(axis=0)
    
    # Add padding
    padding = (max_coords - min_coords) * 0.1
    min_coords -= padding
    max_coords += padding
    
    # Calculate scale for each dimension
    dimensions = max_coords - min_coords
    # Avoid division by zero for flat models
    dimensions = np.maximum(dimensions, 0.001)
    scale = np.array(voxel_dims) / dimensions
    
    # Create voxel grid with color indices (0 = empty, 1-255 = palette indices)
    voxel_grid = np.zeros(voxel_dims, dtype=np.uint8)
    
    # Prepare texture color mapping if available
    has_texture = (texture_image is not None and texture_coords is not None and 
                  texture_faces is not None and PIL_AVAILABLE)
    
    if has_texture:
        # Convert texture image to numpy array
        if isinstance(texture_image, str):
            texture_image = Image.open(texture_image)
        tex_array = np.array(texture_image)
        tex_height, tex_width = tex_array.shape[:2]
    
    # Voxelize each face
    for face_idx, face in enumerate(faces):
        if len(face) < 3:
            continue
            
        # Get face vertices
        face_verts = vertices[face]
        
        # Transform to voxel space
        voxel_verts = (face_verts - min_coords) * scale
        voxel_verts = np.clip(voxel_verts, 0, np.array(voxel_dims) - 1).astype(int)
        
        # Get color for this face from texture
        color_idx = 1  # Default color index
        if has_texture and face_idx < len(texture_faces):
            tex_face = texture_faces[face_idx]
            if tex_face and tex_face[0] >= 0:
                # Get average texture coordinate for face
                avg_tex_coord = np.mean([texture_coords[idx] for idx in tex_face if idx >= 0], axis=0)
                # Sample texture at this coordinate
                tex_x = int(avg_tex_coord[0] * tex_width) % tex_width
                tex_y = int((1.0 - avg_tex_coord[1]) * tex_height) % tex_height  # Flip Y
                
                # Get RGB color from texture
                if len(tex_array.shape) >= 3:
                    color = tex_array[tex_y, tex_x, :3]
                else:
                    color = [tex_array[tex_y, tex_x]] * 3
                
                # Map to palette index (simple quantization)
                # We'll use indices 1-255 for colors
                color_idx = 1 + (color[0] // 32) * 36 + (color[1] // 32) * 6 + (color[2] // 32)
                color_idx = min(255, max(1, color_idx))
        
        # Rasterize triangle (simple approach - fill bounding box)
        min_v = voxel_verts.min(axis=0)
        max_v = voxel_verts.max(axis=0)
        
        for x in range(min_v[0], min(max_v[0] + 1, voxel_dims[0])):
            for y in range(min_v[1], min(max_v[1] + 1, voxel_dims[1])):
                for z in range(min_v[2], min(max_v[2] + 1, voxel_dims[2])):
                    voxel_grid[x, y, z] = color_idx
    
    # Fill interior (flood fill from edges to find exterior, then invert)
    filled = flood_fill_exterior(voxel_grid)
    
    return filled

def flood_fill_exterior(voxel_grid):
    """Fill the interior of the voxel model"""
    dims = voxel_grid.shape
    filled = voxel_grid.copy()
    
    # Create a slightly larger grid to ensure we can flood fill from outside
    padded = np.zeros((dims[0] + 2, dims[1] + 2, dims[2] + 2), dtype=np.uint8)
    padded[1:-1, 1:-1, 1:-1] = voxel_grid
    
    # Flood fill from corner
    stack = [(0, 0, 0)]
    exterior = np.zeros_like(padded, dtype=bool)
    
    while stack:
        x, y, z = stack.pop()
        
        if x < 0 or x >= padded.shape[0] or y < 0 or y >= padded.shape[1] or z < 0 or z >= padded.shape[2]:
            continue
            
        if exterior[x, y, z] or padded[x, y, z] > 0:
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
    
    # Fill interior with the same color as nearby voxels
    result = voxel_grid.copy()
    interior_mask = interior & (voxel_grid == 0)
    
    # Find nearest non-zero voxel color for each interior point
    for x in range(dims[0]):
        for y in range(dims[1]):
            for z in range(dims[2]):
                if interior_mask[x, y, z]:
                    # Look for nearest colored voxel
                    found = False
                    for radius in range(1, 10):
                        for dx in range(-radius, radius + 1):
                            for dy in range(-radius, radius + 1):
                                for dz in range(-radius, radius + 1):
                                    nx, ny, nz = x + dx, y + dy, z + dz
                                    if (0 <= nx < dims[0] and 0 <= ny < dims[1] and 0 <= nz < dims[2] and
                                        voxel_grid[nx, ny, nz] > 0):
                                        result[x, y, z] = voxel_grid[nx, ny, nz]
                                        found = True
                                        break
                                if found:
                                    break
                            if found:
                                break
                        if found:
                            break
                    if not found:
                        result[x, y, z] = 1  # Default color
    
    return result

def create_palette_chunk():
    """Create a palette chunk with a variety of colors"""
    palette = []
    
    # Generate a simple palette with gradients
    for r in range(8):
        for g in range(8):
            for b in range(8):
                if len(palette) < 255:
                    palette.append({
                        'r': r * 36,
                        'g': g * 36, 
                        'b': b * 36,
                        'a': 255
                    })
    
    # Fill remaining with white
    while len(palette) < 255:
        palette.append({'r': 255, 'g': 255, 'b': 255, 'a': 255})
    
    # Add black at the end (index 255)
    palette.append({'r': 0, 'g': 0, 'b': 0, 'a': 255})
    
    return palette

def create_vox_file(voxel_grid, output_path, texture_image=None):
    """Create a VOX file from voxel grid with color support"""
    dims = voxel_grid.shape
    
    # Get non-zero voxel positions and their color indices
    voxel_positions = np.argwhere(voxel_grid > 0)
    num_voxels = len(voxel_positions)
    
    # Create palette
    palette = create_palette_chunk()
    palette_chunk_size = 256 * 4  # 256 colors * 4 bytes each
    
    with open(output_path, 'wb') as f:
        # VOX header
        f.write(b'VOX ')
        f.write(struct.pack('<I', 150))  # Version
        
        # Calculate chunk sizes
        size_chunk_size = 12
        xyzi_chunk_size = 4 + num_voxels * 4
        rgba_chunk_size = palette_chunk_size
        main_children_size = (12 + size_chunk_size) + (12 + xyzi_chunk_size) + (12 + rgba_chunk_size)
        
        # MAIN chunk
        f.write(b'MAIN')
        f.write(struct.pack('<I', 0))  # MAIN chunk has no content
        f.write(struct.pack('<I', main_children_size))
        
        # SIZE chunk
        f.write(b'SIZE')
        f.write(struct.pack('<I', size_chunk_size))
        f.write(struct.pack('<I', 0))  # No children
        f.write(struct.pack('<I', dims[0]))  # Size X
        f.write(struct.pack('<I', dims[1]))  # Size Y
        f.write(struct.pack('<I', dims[2]))  # Size Z
        
        # XYZI chunk
        f.write(b'XYZI')
        f.write(struct.pack('<I', xyzi_chunk_size))
        f.write(struct.pack('<I', 0))  # No children
        f.write(struct.pack('<I', num_voxels))  # Number of voxels
        
        # Write voxel data with color indices
        for i, pos in enumerate(voxel_positions):
            x, y, z = pos
            color_idx = voxel_grid[x, y, z]
            f.write(struct.pack('BBBB', x, y, z, color_idx))
        
        # RGBA chunk (palette)
        f.write(b'RGBA')
        f.write(struct.pack('<I', rgba_chunk_size))
        f.write(struct.pack('<I', 0))  # No children
        
        # Write palette data
        for color in palette:
            f.write(struct.pack('BBBB', color['r'], color['g'], color['b'], color['a']))
    
    return output_path

def convert_obj_to_vox(obj_path, output_path=None, voxel_size=None, texture_path=None):
    """Main conversion function with texture support"""
    if output_path is None:
        output_path = Path(obj_path).with_suffix('.vox')
    
    print(f"Converting {obj_path} to voxels...")
    
    # Parse OBJ file
    vertices, faces, texture_coords, texture_faces = parse_obj_file(obj_path)
    print(f"Loaded {len(vertices)} vertices and {len(faces)} faces")
    
    if len(vertices) == 0:
        raise ValueError("No vertices found in OBJ file")
    
    # Load texture if provided
    texture_image = None
    if texture_path and PIL_AVAILABLE:
        try:
            texture_image = Image.open(texture_path)
            print(f"Loaded texture: {texture_path} ({texture_image.size[0]}x{texture_image.size[1]})") 
        except Exception as e:
            print(f"Warning: Could not load texture: {e}")
    
    # Calculate voxel dimensions based on model
    if voxel_size is not None:
        # If a single size is specified, use it for all dimensions
        if isinstance(voxel_size, int):
            voxel_dims = (voxel_size, voxel_size, voxel_size)
        else:
            voxel_dims = voxel_size
    else:
        # Calculate dimensions based on model proportions
        voxel_dims = calculate_voxel_dimensions(vertices)
    
    print(f"Voxelizing to {voxel_dims[0]}x{voxel_dims[1]}x{voxel_dims[2]} grid...")
    
    # Voxelize with texture support
    voxel_grid = voxelize_mesh(vertices, faces, voxel_dims, texture_coords, texture_faces, texture_image)
    
    # Fill interior
    voxel_grid = flood_fill_exterior(voxel_grid)
    
    num_voxels = np.sum(voxel_grid > 0)
    print(f"Generated {num_voxels} voxels")
    
    if num_voxels == 0:
        raise ValueError("No voxels generated - model might be too small or invalid")
    
    # Create VOX file with color palette
    create_vox_file(voxel_grid, output_path, texture_image)
    print(f"Saved VOX file: {output_path}")
    
    return output_path

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        obj_file = sys.argv[1]
        vox_file = sys.argv[2] if len(sys.argv) > 2 else None
        texture_file = sys.argv[3] if len(sys.argv) > 3 else None
        convert_obj_to_vox(obj_file, vox_file, texture_path=texture_file)
    else:
        print("Usage: python voxel_converter.py input.obj [output.vox] [texture.png]")