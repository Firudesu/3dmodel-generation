# Image → 3D Model → Voxel File Automation

A web-based application that automates the conversion of images to 3D models using Meshy API, then converts them to voxel files using the Drububu voxelizer.

## 🌐 **Web Interface Features**

- **🎨 Beautiful UI** - Modern, responsive web interface
- **📁 Drag & Drop Upload** - Easy image file selection
- **📊 Real-time Progress** - Live status updates and progress tracking
- **📥 Instant Downloads** - Direct download links for all generated files
- **🔄 Two-step Meshy Workflow** - 3D model creation + texture application
- **📦 Auto-extraction** - Handles zipped model files automatically
- **🌍 Replit Ready** - Works perfectly in Replit and other web IDEs

## 🚀 **Quick Start (Replit)**

1. **Click "Run"** in Replit - the web app starts automatically!
2. **Upload your image** using drag & drop or click to select
3. **Click "Start Conversion"** and watch the progress
4. **Download your files** when complete!

## 🖥️ **Local Usage**

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Start the web app
python3 app.py

# Open http://localhost:5000 in your browser
```

## Quick Start (Replit/GitHub Codespaces)

1. **Get a Meshy API key** from [Meshy AI](https://meshy.ai/)
2. **Update configuration** in `main.py`:
   - Set your `MESHY_API_KEY`
   - Set the `INPUT_IMAGE_PATH` to your image file
3. **Place your image** in the `input/` directory
4. **Run the automation**:
   ```bash
   python3 run.py
   ```

## Manual Setup

1. Install dependencies:
```bash
pip install requests playwright
playwright install chromium
```

2. Get a Meshy API key from [Meshy AI](https://meshy.ai/)

3. Update the configuration in `main.py`:
   - Set your `MESHY_API_KEY`
   - Set the `INPUT_IMAGE_PATH` to your image file

4. Place your input image in the `input/` directory

## Usage

```bash
python3 main.py
```

## Output

The script will create:
- `output/meshy_model/` - Contains the 3D model files (.obj, .mtl, textures)
- `output/voxel/` - Contains the final .vox file

## File Structure

```
project/
├── main.py
├── requirements.txt
├── README.md
├── input/
│   └── sample_image.jpg
└── output/
    ├── meshy_model/
    └── voxel/
```

## Features

- ✅ Automated Meshy API integration
- ✅ Playwright browser automation for Drububu voxelizer
- ✅ Progress messages and error handling
- ✅ Organized output file structure
- ✅ Works in web-based IDEs (Replit, GitHub Codespaces)

## Notes

- The script uses Meshy's preview mode for faster generation
- Browser automation handles the Drububu voxelizer upload/download
- All files are automatically organized in the output directory