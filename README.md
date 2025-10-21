# Image → 3D Model → Voxel File Automation

This Python script automates the conversion of images to 3D models using Meshy API, then converts them to voxel files using the Drububu voxelizer.

## Setup

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
python main.py
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