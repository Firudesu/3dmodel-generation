# Image → 3D Model → Voxel File Automation

This Python automation converts a single image into a textured 3D model using the Meshy API, then automatically converts it to a voxel (.vox) file using Drububu's online voxelizer.

## 🎯 What it does

1. **Takes a single image** (JPG or PNG)
2. **Generates a 3D model** using Meshy AI's image-to-3D API
3. **Downloads the 3D files** (.obj, .mtl, textures)
4. **Converts to voxel format** using Drububu's voxelizer
5. **Saves everything** to organized output folders

## 📁 Project Structure

```
project/
├── main.py              # Main automation script
├── setup.py             # Setup and dependency installer
├── requirements.txt     # Python dependencies
├── input/
│   └── sample_image.jpg # Your input images go here
├── output/
│   ├── meshy_model/     # 3D model files from Meshy
│   └── voxel/          # Final .vox files
└── README.md
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Install dependencies and setup
python setup.py
```

This will:
- Install Python packages (requests, playwright, Pillow)
- Install Chromium browser for Playwright
- Create a sample test image

### 2. Configure API Key

Edit `main.py` and set your Meshy API key:

```python
MESHY_API_KEY = "your_actual_api_key_here"
```

Get your API key from: https://meshy.ai

### 3. Run the Automation

```bash
python main.py
```

## 📋 Configuration

Edit these variables in `main.py`:

```python
MESHY_API_KEY = "YOUR_MESHY_API_KEY_HERE"  # Required: Get from meshy.ai
INPUT_IMAGE_PATH = "input/sample_image.jpg"  # Path to your input image
```

## 🔧 Manual Setup (Alternative)

If you prefer manual setup:

```bash
# Install Python dependencies
pip install requests playwright Pillow

# Install Playwright browser
playwright install chromium

# Run the script
python main.py
```

## 📤 Output Files

After successful execution, you'll find:

### 3D Model Files (`output/meshy_model/`)
- `model.obj` - 3D mesh geometry
- `model.mtl` - Material definitions  
- `texture.png` - Texture image

### Voxel Files (`output/voxel/`)
- `model.vox` - Final voxel file ready for use

## 🎮 Using the Voxel File

The generated `.vox` file can be used in:
- **MagicaVoxel** - Popular voxel editor
- **Minecraft** - With appropriate converters
- **Game engines** - Unity, Unreal Engine (with voxel plugins)
- **3D printing** - Convert to STL format

## 🛠️ Troubleshooting

### API Issues
- Verify your Meshy API key is correct
- Check your Meshy account has sufficient credits
- Ensure stable internet connection

### Browser Automation Issues
- The script uses headless Chromium via Playwright
- If Drububu's website changes, the automation may need updates
- Check that the .obj file was generated successfully first

### File Issues
- Ensure input image exists and is readable
- Check that output directories have write permissions
- Supported image formats: JPG, PNG

## 🔄 Workflow Details

### Step 1: Meshy 3D Generation
1. Uploads your image to Meshy AI
2. Starts image-to-3D conversion process
3. Polls for completion (can take 2-10 minutes)
4. Downloads generated 3D model files

### Step 2: Voxel Conversion
1. Opens Drububu voxelizer in headless browser
2. Uploads the .obj file automatically
3. Processes the voxelization
4. Downloads the resulting .vox file

## 📝 Notes

- **Processing time**: 3D generation typically takes 2-10 minutes
- **Image quality**: Higher quality input images produce better 3D models
- **Internet required**: Both Meshy API and Drububu require internet access
- **Headless operation**: Runs completely automated, no manual clicks needed

## 🆘 Support

If you encounter issues:

1. Check that all dependencies are installed correctly
2. Verify your Meshy API key and credits
3. Ensure stable internet connection
4. Check the console output for specific error messages

The script includes detailed progress messages to help identify where issues occur.

## 📄 License

This project is provided as-is for educational and personal use.