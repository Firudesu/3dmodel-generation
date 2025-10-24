#!/usr/bin/env python3
"""
Real voxel conversion from OBJ to VOX format with texture support
Converts 3D models to voxel format using Python
"""

import numpy as np
import struct
from pathlib import Path
from PIL import Image
import os

def parse_obj_file(obj_path):
    """Parse OBJ file and extract vertices, faces, and texture coordinates"""
    vertices = []
    faces = []
    texture_coords = []
    face_textures = []
    
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
                face_tex = []
                for part in parts:
                    # Handle face formats: vertex, vertex/texture, vertex/texture/normal, vertex//normal
                    components = part.split('/')
                    vertex_idx = int(components[0]) - 1  # OBJ indices start at 1
                    face.append(vertex_idx)
                    
                    # Get texture coordinate index if available
                    if len(components) > 1 and components[1]:
                        tex_idx = int(components[1]) - 1
                        face_tex.append(tex_idx)
                
                faces.append(face)
                if face_tex:
                    face_textures.append(face_tex)
    
    return np.array(vertices), faces, texture_coords, face_textures

def load_texture(texture_path):
    """Load texture image and convert to color array"""
    if not texture_path or not os.path.exists(texture_path):
        return None
    
    try:
        img = Image.open(texture_path)
        img = img.convert('RGB')
        return np.array(img)
    except Exception as e:
        print(f"Failed to load texture: {e}")
        return None

def get_texture_color(texture_array, u, v):
    """Sample color from texture at UV coordinates with better sampling"""
    if texture_array is None:
        return (128, 128, 128)  # Default gray color
    
    h, w = texture_array.shape[:2]
    
    # Wrap UV coordinates
    u = u % 1.0
    v = v % 1.0
    
    # Convert to pixel coordinates with sub-pixel accuracy
    x = u * (w - 1)
    y = (1.0 - v) * (h - 1)  # Flip V coordinate
    
    # Bilinear sampling for better color accuracy
    x1 = int(x)
    y1 = int(y)
    x2 = min(x1 + 1, w - 1)
    y2 = min(y1 + 1, h - 1)
    
    # Clamp to array bounds
    x1 = max(0, min(x1, w - 1))
    y1 = max(0, min(y1, h - 1))
    x2 = max(0, min(x2, w - 1))
    y2 = max(0, min(y2, h - 1))
    
    # Get fractional parts
    fx = x - x1
    fy = y - y1
    
    # Sample four corners
    c11 = texture_array[y1, x1]
    c12 = texture_array[y2, x1]
    c21 = texture_array[y1, x2]
    c22 = texture_array[y2, x2]
    
    # Bilinear interpolation
    c1 = c11 * (1 - fx) + c21 * fx
    c2 = c12 * (1 - fx) + c22 * fx
    result = c1 * (1 - fy) + c2 * fy
    
    return tuple(result.astype(int))

def calculate_voxel_size_from_obj(vertices):
    """Calculate appropriate voxel size based on OBJ dimensions"""
    if len(vertices) == 0:
        return 64
    
    # Find bounding box
    min_coords = vertices.min(axis=0)
    max_coords = vertices.max(axis=0)
    dimensions = max_coords - min_coords
    
    # Get the longest dimension
    max_dimension = dimensions.max()
    
    # Calculate voxel size based on model complexity
    # Aim for reasonable detail while keeping file size manageable
    if max_dimension < 1.0:
        # Very small model - use higher resolution
        return 128
    elif max_dimension < 10.0:
        # Small to medium model
        return 64
    elif max_dimension < 100.0:
        # Medium to large model
        return 64
    else:
        # Very large model - may need lower resolution
        return 32
    
    # Always return 64 as default for now (can be adjusted based on needs)
    return 64

def voxelize_mesh(vertices, faces, texture_coords, face_textures, texture_array, voxel_size=64):
    """Convert mesh to voxel grid with colors"""
    if len(vertices) == 0:
        return np.zeros((voxel_size, voxel_size, voxel_size), dtype=bool), {}
    
    # Find bounding box
    min_coords = vertices.min(axis=0)
    max_coords = vertices.max(axis=0)
    
    # Add padding
    padding = (max_coords - min_coords) * 0.1
    min_coords -= padding
    max_coords += padding
    
    # Scale to voxel grid
    scale = voxel_size / (max_coords - min_coords).max()
    
    # Create voxel grid and color map
    voxel_grid = np.zeros((voxel_size, voxel_size, voxel_size), dtype=bool)
    voxel_colors = {}  # Dictionary to store colors for each voxel position
    
    # Voxelize each face
    for face_idx, face in enumerate(faces):
        if len(face) < 3:
            continue
            
        # Get face vertices
        face_verts = vertices[face]
        
        # Get texture coordinates if available
        face_color = (128, 128, 128)  # Default gray
        if texture_array is not None and face_idx < len(face_textures) and face_textures[face_idx]:
            # Sample multiple points on the face for better color representation
            face_tex = face_textures[face_idx]
            if texture_coords and face_tex:
                uvs = [texture_coords[tex_idx] for tex_idx in face_tex if tex_idx < len(texture_coords)]
                if uvs:
                    # Sample center of face
                    avg_u = np.mean([uv[0] for uv in uvs])
                    avg_v = np.mean([uv[1] for uv in uvs])
                    face_color = get_texture_color(texture_array, avg_u, avg_v)
        
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
                    
                    # Sample texture color for this specific voxel position
                    if texture_array is not None and face_idx < len(face_textures) and face_textures[face_idx]:
                        face_tex = face_textures[face_idx]
                        if texture_coords and face_tex:
                            # Interpolate UV coordinates for this voxel position
                            voxel_pos = np.array([x, y, z])
                            
                            # Find barycentric coordinates within the face
                            v0, v1, v2 = face_verts
                            v0_vox, v1_vox, v2_vox = voxel_verts
                            
                            # Calculate barycentric coordinates
                            denom = (v1_vox[1] - v2_vox[1]) * (v0_vox[0] - v2_vox[0]) + (v2_vox[0] - v1_vox[0]) * (v0_vox[1] - v2_vox[1])
                            if abs(denom) > 1e-10:
                                a = ((v1_vox[1] - v2_vox[1]) * (voxel_pos[0] - v2_vox[0]) + (v2_vox[0] - v1_vox[0]) * (voxel_pos[1] - v2_vox[1])) / denom
                                b = ((v2_vox[1] - v0_vox[1]) * (voxel_pos[0] - v2_vox[0]) + (v0_vox[0] - v2_vox[0]) * (voxel_pos[1] - v2_vox[1])) / denom
                                c = 1 - a - b
                                
                                # Clamp to valid range
                                a = max(0, min(1, a))
                                b = max(0, min(1, b))
                                c = max(0, min(1, c))
                                
                                # Normalize
                                total = a + b + c
                                if total > 0:
                                    a /= total
                                    b /= total
                                    c /= total
                                
                                # Interpolate UV coordinates
                                if len(face_tex) >= 3:
                                    uv0 = texture_coords[face_tex[0]]
                                    uv1 = texture_coords[face_tex[1]]
                                    uv2 = texture_coords[face_tex[2]]
                                    
                                    u = a * uv0[0] + b * uv1[0] + c * uv2[0]
                                    v = a * uv0[1] + b * uv1[1] + c * uv2[1]
                                    
                                    voxel_color = get_texture_color(texture_array, u, v)
                                    voxel_colors[(x, y, z)] = voxel_color
                                else:
                                    voxel_colors[(x, y, z)] = face_color
                            else:
                                voxel_colors[(x, y, z)] = face_color
                        else:
                            voxel_colors[(x, y, z)] = face_color
                    else:
                        voxel_colors[(x, y, z)] = face_color
    
    # Fill interior (flood fill from edges to find exterior, then invert)
    filled = flood_fill_exterior(voxel_grid)
    
    # Update colors for filled voxels (use nearest surface color)
    new_voxels = np.argwhere(filled & ~voxel_grid)
    for voxel in new_voxels:
        x, y, z = voxel
        # Find nearest colored voxel
        if not (x, y, z) in voxel_colors:
            # Use default color for interior
            voxel_colors[(x, y, z)] = (128, 128, 128)
    
    return filled, voxel_colors

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

def rgb_to_palette_index(r, g, b, palette_colors=None):
    """Convert RGB color to VOX palette index using actual texture colors"""
    if palette_colors is None:
        # Fallback to simple mapping if no palette provided
        if r > 200 and g > 200 and b > 200:
            return 1   # White
        elif r > 200 and g < 100 and b < 100:
            return 2   # Red
        elif r < 100 and g > 200 and b < 100:
            return 3   # Green
        elif r < 100 and g < 100 and b > 200:
            return 4   # Blue
        elif r > 200 and g > 200 and b < 100:
            return 5   # Yellow
        elif r > 200 and g < 100 and b > 200:
            return 6   # Magenta
        elif r < 100 and g > 200 and b > 200:
            return 7   # Cyan
        elif r < 50 and g < 50 and b < 50:
            return 8   # Black
        else:
            # Default gray based on brightness
            brightness = (r + g + b) // 3
            return 9 + (brightness // 32)  # Maps to indices 9-16
    
    # Find closest color in palette
    target_color = np.array([r, g, b])
    min_distance = float('inf')
    best_index = 1  # Default to white
    
    for i, palette_color in enumerate(palette_colors):
        if i == 0:  # Skip transparent
            continue
        distance = np.linalg.norm(np.array(palette_color[:3]) - target_color)
        if distance < min_distance:
            min_distance = distance
            best_index = i
    
    return best_index

def create_vox_file(voxel_grid, voxel_colors, output_path):
    """Create a VOX file from voxel grid with colors"""
    size = voxel_grid.shape[0]
    
    # Get voxel positions
    voxel_positions = np.argwhere(voxel_grid)
    num_voxels = len(voxel_positions)
    
    # Generate palette from actual texture colors
    palette_colors = generate_palette_from_colors(voxel_colors)
    
    with open(output_path, 'wb') as f:
        # VOX header
        f.write(b'VOX ')
        f.write(struct.pack('<I', 150))  # Version
        
        # Calculate chunk sizes
        size_chunk_size = 12
        xyzi_chunk_size = 4 + num_voxels * 4
        
        # Add palette chunk size
        rgba_chunk_size = 256 * 4
        
        main_children_size = (12 + size_chunk_size) + (12 + xyzi_chunk_size) + (12 + rgba_chunk_size)
        
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
        
        # Write voxel data with colors
        for pos in voxel_positions:
            x, y, z = pos
            color = voxel_colors.get((x, y, z), (128, 128, 128))
            palette_idx = rgb_to_palette_index(*color, palette_colors)
            f.write(struct.pack('BBBB', x, y, z, palette_idx))
        
        # RGBA chunk (palette)
        f.write(b'RGBA')
        f.write(struct.pack('<I', rgba_chunk_size))
        f.write(struct.pack('<I', 0))  # No children
        
        # Write palette
        for color in palette_colors[:256]:
            f.write(struct.pack('BBBB', *color))
    
    return output_path

def generate_palette_from_colors(voxel_colors):
    """Generate a 256-color palette from actual texture colors"""
    if not voxel_colors:
        return get_default_palette()
    
    # Collect all unique colors
    unique_colors = list(set(voxel_colors.values()))
    print(f"Found {len(unique_colors)} unique colors in texture")
    
    # Start with essential colors
    palette = [
        (0, 0, 0, 0),        # 0: Transparent
        (255, 255, 255, 255), # 1: White
        (0, 0, 0, 255),       # 2: Black
    ]
    
    # Add actual texture colors (up to 253 more)
    for color in unique_colors[:253]:
        if len(palette) >= 256:
            break
        palette.append((*color, 255))  # Add alpha channel
    
    # Fill remaining slots with default colors if needed
    if len(palette) < 256:
        default_colors = [
            (255, 0, 0, 255),     # Red
            (0, 255, 0, 255),     # Green
            (0, 0, 255, 255),     # Blue
            (255, 255, 0, 255),   # Yellow
            (255, 0, 255, 255),   # Magenta
            (0, 255, 255, 255),   # Cyan
        ]
        
        for color in default_colors:
            if len(palette) >= 256:
                break
            palette.append(color)
    
    # Fill rest with grayscale
    while len(palette) < 256:
        gray = ((len(palette) - 3) * 10) % 256
        palette.append((gray, gray, gray, 255))
    
    return palette[:256]

def get_default_palette():
    """Get default VOX palette"""
    palette = [
        (0, 0, 0, 0),        # 0: Transparent
        (255, 255, 255, 255), # 1: White
        (255, 0, 0, 255),     # 2: Red
        (0, 255, 0, 255),     # 3: Green
        (0, 0, 255, 255),     # 4: Blue
        (255, 255, 0, 255),   # 5: Yellow
        (255, 0, 255, 255),   # 6: Magenta
        (0, 255, 255, 255),   # 7: Cyan
        (0, 0, 0, 255),       # 8: Black
    ]
    
    # Add gray scale
    for i in range(9, 17):
        gray = ((i - 9) * 32)
        palette.append((gray, gray, gray, 255))
    
    # Fill rest with more colors
    for i in range(len(palette), 256):
        # Generate a varied palette
        r = (i * 37) % 256
        g = (i * 67) % 256
        b = (i * 97) % 256
        palette.append((r, g, b, 255))
    
    return palette

def convert_obj_to_vox(obj_path, texture_path=None, output_path=None, voxel_size=None):
    """Main conversion function with texture support"""
    if output_path is None:
        output_path = Path(obj_path).with_suffix('.vox')
    
    print(f"Converting {obj_path} to voxels...")
    
    # Parse OBJ file
    vertices, faces, texture_coords, face_textures = parse_obj_file(obj_path)
    print(f"Loaded {len(vertices)} vertices and {len(faces)} faces")
    
    if len(vertices) == 0:
        raise ValueError("No vertices found in OBJ file")
    
    # Load texture if provided
    texture_array = None
    if texture_path:
        print(f"Loading texture from {texture_path}")
        texture_array = load_texture(texture_path)
        if texture_array is not None:
            print(f"Texture loaded: {texture_array.shape}")
    
    # Determine voxel size based on OBJ dimensions if not specified
    if voxel_size is None:
        voxel_size = calculate_voxel_size_from_obj(vertices)
        print(f"Auto-determined voxel size: {voxel_size}x{voxel_size}x{voxel_size}")
    else:
        print(f"Using specified voxel size: {voxel_size}x{voxel_size}x{voxel_size}")
    
    # Ensure voxel size is always 64x64x64 as default
    if voxel_size != 64:
        voxel_size = 64
        print(f"Overriding to standard size: 64x64x64")
    
    # Voxelize with texture information
    print(f"Voxelizing to {voxel_size}x{voxel_size}x{voxel_size} grid...")
    voxel_grid, voxel_colors = voxelize_mesh(vertices, faces, texture_coords, face_textures, texture_array, voxel_size)
    
    num_voxels = np.sum(voxel_grid)
    print(f"Generated {num_voxels} voxels")
    
    if num_voxels == 0:
        raise ValueError("No voxels generated - model might be too small or invalid")
    
    # Create VOX file with colors
    create_vox_file(voxel_grid, voxel_colors, output_path)
    print(f"Saved VOX file: {output_path}")
    
    return output_path

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        obj_file = sys.argv[1]
        texture_file = sys.argv[2] if len(sys.argv) > 2 else None
        vox_file = sys.argv[3] if len(sys.argv) > 3 else None
        convert_obj_to_vox(obj_file, texture_file, vox_file)
    else:
        print("Usage: python voxel_converter.py input.obj [texture.png] [output.vox]")