#!/bin/bash
# Build script for Render deployment
echo "==> Starting build process..."
echo "==> Installing Python dependencies..."
pip install --no-cache-dir -r requirements.txt
echo "==> Build complete!"