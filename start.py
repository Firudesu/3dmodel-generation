#!/usr/bin/env python3
"""
Production start script for Render
Simply starts gunicorn - no dependency installation
"""
import os
import sys
import subprocess

print("=" * 60)
print("🚀 3D Model Generator - Starting Production Server")
print("=" * 60)

# Create necessary directories
os.makedirs('uploads', exist_ok=True)
os.makedirs('output', exist_ok=True)
os.makedirs('output/voxel', exist_ok=True)
os.makedirs('output/meshy_model', exist_ok=True)
print("✅ Directories created")

# Get port from environment
port = os.environ.get('PORT', '10000')
print(f"📡 Starting server on port {port}")

# Start gunicorn
cmd = [
    'gunicorn',
    'app:app',
    '--bind', f'0.0.0.0:{port}',
    '--timeout', '120',
    '--workers', '1',
    '--threads', '2'
]

print(f"🚀 Running: {' '.join(cmd)}")
print("=" * 60)

# Execute gunicorn
os.execvp('gunicorn', cmd)