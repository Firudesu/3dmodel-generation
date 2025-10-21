#!/bin/bash
# Quick setup script for Image → Voxel Automation

echo "🚀 Setting up Image → Voxel Automation"
echo "======================================"

# Install Python dependencies
echo "📦 Installing Python packages..."
pip install -r requirements.txt

# Install Playwright browser
echo ""
echo "🌐 Installing Chromium browser..."
playwright install chromium

# Create directories if they don't exist
echo ""
echo "📁 Creating directory structure..."
mkdir -p input output/meshy_model output/voxel

# Check for .env file
if [ ! -f .env ]; then
    echo ""
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your MESHY_API_KEY"
fi

echo ""
echo "======================================"
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your MESHY_API_KEY"
echo "2. Place your image in input/ folder"
echo "3. Run: python3 main.py"
echo "======================================"