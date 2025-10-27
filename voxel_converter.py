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
    """Parse OBJ file and extract vertices, faces, and texture coordinates (simplified)"""
    vertices = []
    faces = []
    texture_coords = []
    face_textures = []
    
    with open(obj_path, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
                
            if line.startswith('v '):
                # Vertex
                parts = line.split()
                if len(parts) >= 4:
                    vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif line.startswith('vt '):
                # Texture coordinate
                parts = line.split()
                if len(parts) >= 3:
                    texture_coords.append([float(parts[1]), float(parts[2])])
            elif line.startswith('f '):
                # Face
                parts = line.split()[1:]
                face = []
                face_tex = []
                for part in parts:
                    # Skip empty parts
                    if not part:
                        continue
                    # Handle face formats: vertex, vertex/texture, vertex/texture/normal, vertex//normal
                    components = part.split('/')
                    if components[0]:  # Make sure vertex index exists
                        vertex_idx = int(components[0]) - 1  # OBJ indices start at 1
                        face.append(vertex_idx)
                        
                        # Get texture coordinate index if available
                        if len(components) > 1 and components[1]:
                            tex_idx = int(components[1]) - 1
                            face_tex.append(tex_idx)
                
                if len(face) >= 3:  # Only add faces with at least 3 vertices
                    faces.append(face)
                    if face_tex:
                        face_textures.append(face_tex)
                    else:
                        face_textures.append([])
    
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
    """Sample color from texture at UV coordinates with improved sampling"""
    if texture_array is None:
        return (128, 128, 128)  # Default gray color
    
    h, w = texture_array.shape[:2]
    
    # Clamp UV coordinates to [0, 1] range
    u = max(0.0, min(1.0, u))
    v = max(0.0, min(1.0, v))
    
    # Convert to pixel coordinates with sub-pixel accuracy
    x = u * (w - 1)
    y = (1.0 - v) * (h - 1)  # Flip V coordinate for proper texture orientation
    
    # Bilinear sampling for better color accuracy
    x1 = int(x)
    y1 = int(y)
    x2 = min(x1 + 1, w - 1)
    y2 = min(y1 + 1, h - 1)
    
    # Clamp to array bounds (shouldn't be needed but safety first)
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
    
    return tuple(np.clip(result.astype(int), 0, 255))

def calculate_voxel_size_from_obj(vertices):
    """Calculate voxel size to match OBJ dimensions"""
    if len(vertices) == 0:
        return 64
    
    # Find bounding box
    min_coords = vertices.min(axis=0)
    max_coords = vertices.max(axis=0)
    dimensions = max_coords - min_coords
    
    # Get the longest dimension
    max_dimension = dimensions.max()
    
    # Scale voxel size to match the model's actual dimensions
    # Use the longest dimension as the base for voxel size
    voxel_size = int(max_dimension * 64)  # Scale factor of 64 per unit
    
    # Ensure reasonable bounds
    voxel_size = max(32, min(512, voxel_size))  # Between 32 and 512
    
    print(f"Model dimensions: {dimensions}")
    print(f"Longest dimension: {max_dimension}")
    print(f"Calculated voxel size: {voxel_size}")
    
    return voxel_size

def voxelize_mesh_simple(vertices, faces, texture_coords, face_textures, texture_array, voxel_size=64):
    """Simple voxelization with direct UV mapping from OBJ file"""
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
    voxel_colors = {}
    
    print(f"Processing {len(faces)} faces...")
    print(f"Texture coords available: {len(texture_coords)}")
    print(f"Face textures available: {len(face_textures)}")
    
    # Process each face with direct UV mapping
    for face_idx, face in enumerate(faces):
        if len(face) < 3:
            continue
            
        # Get face vertices
        face_verts = vertices[face]
        
        # Get UV coordinates for this face directly from OBJ
        face_uvs = None
        if (texture_array is not None and 
            face_idx < len(face_textures) and 
            face_textures[face_idx] and 
            len(face_textures[face_idx]) >= 3):
            
            face_tex = face_textures[face_idx]
            if texture_coords and face_tex:
                face_uvs = [texture_coords[tex_idx] for tex_idx in face_tex[:3] if tex_idx < len(texture_coords)]
                print(f"Face {face_idx}: UV coords = {face_uvs}")
        
        # Transform to voxel space
        voxel_verts = (face_verts - min_coords) * scale
        voxel_verts = np.clip(voxel_verts, 0, voxel_size - 1).astype(int)
        
        # Get bounding box for this face
        min_v = voxel_verts.min(axis=0)
        max_v = voxel_verts.max(axis=0)
        
        # Fill voxels in the bounding box
        for x in range(min_v[0], min(max_v[0] + 1, voxel_size)):
            for y in range(min_v[1], min(max_v[1] + 1, voxel_size)):
                for z in range(min_v[2], min(max_v[2] + 1, voxel_size)):
                    # Convert voxel position back to 3D space
                    voxel_3d = np.array([x, y, z]) / scale + min_coords
                    
                    # Check if this voxel is inside the face
                    if is_point_in_face(voxel_3d, face_verts):
                        voxel_grid[x, y, z] = True
                        
                        # Use UV coordinates directly from OBJ file
                        if face_uvs and len(face_uvs) >= 3:
                            # Interpolate UV coordinates for this voxel
                            u, v = interpolate_uv(voxel_3d, face_verts, face_uvs)
                            color = get_texture_color(texture_array, u, v)
                        else:
                            # No UV coordinates - use face index for color variation
                            color = get_face_color(face_idx)
                        
                        voxel_colors[(x, y, z)] = color
    
    # Simple flood fill for interior
    filled = flood_fill_exterior(voxel_grid)
    
    # Update colors for filled voxels (interior)
    new_voxels = np.argwhere(filled & ~voxel_grid)
    for voxel in new_voxels:
        x, y, z = voxel
        if not (x, y, z) in voxel_colors:
            voxel_colors[(x, y, z)] = (128, 128, 128)
    
    return filled, voxel_colors

def get_face_color(face_idx):
    """Generate a color based on face index for debugging"""
    colors = [
        (255, 0, 0),    # Red
        (0, 255, 0),    # Green  
        (0, 0, 255),    # Blue
        (255, 255, 0),  # Yellow
        (255, 0, 255),  # Magenta
        (0, 255, 255),  # Cyan
    ]
    return colors[face_idx % len(colors)]

def is_point_in_face(point, face_vertices):
    """Check if a 3D point is inside a triangular face (simplified)"""
    if len(face_vertices) < 3:
        return False
    
    # Use barycentric coordinates for triangle
    v0, v1, v2 = face_vertices[:3]
    
    # Calculate vectors
    v0v1 = v1 - v0
    v0v2 = v2 - v0
    v0p = point - v0
    
    # Calculate dot products
    dot00 = np.dot(v0v2, v0v2)
    dot01 = np.dot(v0v2, v0v1)
    dot02 = np.dot(v0v2, v0p)
    dot11 = np.dot(v0v1, v0v1)
    dot12 = np.dot(v0v1, v0p)
    
    # Calculate barycentric coordinates
    inv_denom = 1 / (dot00 * dot11 - dot01 * dot01)
    u = (dot11 * dot02 - dot01 * dot12) * inv_denom
    v = (dot00 * dot12 - dot01 * dot02) * inv_denom
    
    # Check if point is in triangle
    return (u >= 0) and (v >= 0) and (u + v <= 1)

def interpolate_uv(point, face_vertices, face_uvs):
    """Interpolate UV coordinates for a point inside a triangular face using barycentric coordinates"""
    if len(face_vertices) < 3 or len(face_uvs) < 3:
        return 0.5, 0.5  # Default UV
    
    v0, v1, v2 = face_vertices[:3]
    uv0, uv1, uv2 = face_uvs[:3]
    
    # Calculate barycentric coordinates
    v0v1 = v1 - v0
    v0v2 = v2 - v0
    v0p = point - v0
    
    # Calculate dot products
    dot00 = np.dot(v0v2, v0v2)
    dot01 = np.dot(v0v2, v0v1)
    dot02 = np.dot(v0v2, v0p)
    dot11 = np.dot(v0v1, v0v1)
    dot12 = np.dot(v0v1, v0p)
    
    # Calculate barycentric coordinates
    inv_denom = 1 / (dot00 * dot11 - dot01 * dot01)
    u = (dot11 * dot02 - dot01 * dot12) * inv_denom
    v = (dot00 * dot12 - dot01 * dot02) * inv_denom
    w = 1 - u - v
    
    # Clamp barycentric coordinates to [0,1]
    u = max(0, min(1, u))
    v = max(0, min(1, v))
    w = max(0, min(1, w))
    
    # Normalize to ensure they sum to 1
    total = u + v + w
    if total > 0:
        u /= total
        v /= total
        w /= total
    
    # Interpolate UV coordinates
    u_coord = w * uv0[0] + u * uv1[0] + v * uv2[0]
    v_coord = w * uv0[1] + u * uv1[1] + v * uv2[1]
    
    return u_coord, v_coord

def voxelize_mesh(vertices, faces, texture_coords, face_textures, face_materials, materials, texture_array, voxel_size=64):
    """Convert mesh to voxel grid with colors (complex version - kept for compatibility)"""
    # Just call the simple version
    return voxelize_mesh_simple(vertices, faces, texture_coords, face_textures, texture_array, voxel_size)

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
    """Main conversion function with simple texture support"""
    if output_path is None:
        output_path = Path(obj_path).with_suffix('.vox')
    
    print(f"Converting {obj_path} to voxels...")
    
    # Parse OBJ file (simplified)
    vertices, faces, texture_coords, face_textures = parse_obj_file(obj_path)
    print(f"Loaded {len(vertices)} vertices and {len(faces)} faces")
    print(f"Found {len(texture_coords)} texture coordinates")
    
    if len(vertices) == 0:
        raise ValueError("No vertices found in OBJ file")
    
    # Load texture if provided
    texture_array = None
    if texture_path and os.path.exists(texture_path):
        print(f"Loading texture: {texture_path}")
        texture_array = load_texture(texture_path)
        if texture_array is not None:
            print(f"Texture loaded: {texture_array.shape}")
            print(f"Texture color range: {texture_array.min()} - {texture_array.max()}")
        else:
            print("Failed to load texture, using default colors")
    else:
        print("No texture provided, using default colors")
    
    # Use provided voxel size or calculate appropriate size
    if voxel_size is None:
        voxel_size = calculate_voxel_size_from_obj(vertices)
    print(f"Using voxel size: {voxel_size}x{voxel_size}x{voxel_size}")
    
    # Voxelize with improved texture mapping
    print(f"Voxelizing to {voxel_size}x{voxel_size}x{voxel_size} grid...")
    print(f"Processing {len(faces)} faces with texture mapping...")
    voxel_grid, voxel_colors = voxelize_mesh_simple(vertices, faces, texture_coords, face_textures, texture_array, voxel_size)
    
    num_voxels = np.sum(voxel_grid)
    print(f"Generated {num_voxels} voxels")
    
    if voxel_colors:
        unique_colors = len(set(voxel_colors.values()))
        print(f"Applied {unique_colors} unique colors from texture")
    else:
        print("No colors applied - using default gray")
    
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