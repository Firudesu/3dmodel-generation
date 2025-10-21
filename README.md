# 🎨 Image → 3D Model → Voxel File Automation

A Python automation tool that converts a single image into a 3D model using the Meshy API, then automatically converts it to a voxel file (.vox) using the Drububu voxelizer.

## 🚀 Features

- **Automated 3D Generation**: Uses Meshy AI to generate textured 3D models from a single image
- **Voxel Conversion**: Automatically uploads and converts the 3D model to VOX format
- **Browser Automation**: Uses Playwright to handle Drububu website interactions
- **Complete Pipeline**: End-to-end automation from image to voxel file
- **Progress Tracking**: Real-time status updates throughout the process

## 📁 Project Structure

```
project/
├── main.py                 # Main automation script
├── input/                  # Input images directory
│   └── sample_image.jpg    # Sample test image
├── output/                 # Output files directory
│   ├── meshy_model/       # 3D model files (.obj, .mtl, textures)
│   └── voxel/             # Voxel files (.vox)
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## 🛠️ Setup Instructions

### 1. Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Install Playwright browser (Chromium)
playwright install chromium
```

### 2. Get Meshy API Key

1. Visit [Meshy.ai](https://www.meshy.ai)
2. Sign up for an account
3. Navigate to API settings
4. Generate an API key

### 3. Configure the Script

Edit `main.py` and update the following variables:

```python
# Set your Meshy API key (line ~17)
MESHY_API_KEY = 'YOUR_MESHY_API_KEY_HERE'

# Set your input image path (line ~22)
INPUT_IMAGE_PATH = 'input/your_image.jpg'
```

Alternatively, set the API key as an environment variable:

```bash
export MESHY_API_KEY='your_api_key_here'
```

## 📖 Usage

### Basic Usage

```bash
python main.py
```

### Using Custom Images

1. Place your image in the `input/` folder
2. Update `INPUT_IMAGE_PATH` in `main.py`
3. Run the script

### Expected Output

The script will:
1. Upload your image to Meshy API
2. Generate a 3D model (this may take 2-5 minutes)
3. Download the model files (.obj, .mtl, textures)
4. Open Drububu voxelizer in a headless browser
5. Upload and convert the model to VOX format
6. Save all files to the `output/` directory

Final files will be saved to:
- `output/meshy_model/` - 3D model files
- `output/voxel/` - Voxel file (.vox)

## 🔧 Troubleshooting

### Common Issues

1. **"MESHY_API_KEY not set"**
   - Make sure to set your API key in the script or environment

2. **"Input image not found"**
   - Verify the image path is correct
   - Ensure the image exists in the `input/` folder

3. **Browser automation fails**
   - Run `playwright install chromium` to install browser
   - Check if Drububu website is accessible
   - The site may have changed; manual conversion might be needed

4. **Meshy API timeout**
   - Complex images may take longer to process
   - The script waits up to 10 minutes by default

### Manual Fallback

If the Drububu automation fails, you can manually convert:
1. Visit https://drububu.com/miscellaneous/voxelizer/?out=vox
2. Upload the `.obj` file from `output/meshy_model/`
3. Select VOX format and download

## 🌐 Running in Web IDEs

This script is designed to work in web-based environments:

### Replit
```bash
# In Shell
pip install -r requirements.txt
playwright install chromium
python main.py
```

### GitHub Codespaces
```bash
# In Terminal
pip install -r requirements.txt
playwright install chromium
python main.py
```

## 📝 Environment Variables

You can use a `.env` file for configuration:

```env
MESHY_API_KEY=your_api_key_here
```

The script will automatically load variables from `.env` if present.

## ⚙️ Advanced Configuration

### Meshy API Settings

In `main.py`, you can modify:
- `enable_pbr`: Enable/disable PBR textures (line ~51)
- `ai_model`: Choose AI model version (line ~52)
- `max_wait`: Maximum wait time for generation (line ~108)

### Playwright Settings

- `headless`: Set to `False` to see browser (line ~218)
- `timeout`: Adjust page timeouts (line ~225)

## 🎯 Supported File Formats

### Input
- JPG/JPEG
- PNG
- Other image formats supported by Meshy API

### Output
- `.obj` - 3D model geometry
- `.mtl` - Material definitions
- `.png` - Texture files
- `.vox` - Voxel file (MagicaVoxel format)

## 📊 Performance

- Image upload: ~5-10 seconds
- 3D generation: ~2-5 minutes
- Voxel conversion: ~30-60 seconds
- Total time: ~3-7 minutes

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

## 📄 License

This project is provided as-is for educational and personal use.

## 🙏 Credits

- [Meshy.ai](https://www.meshy.ai) - 3D model generation
- [Drububu Voxelizer](https://drububu.com/miscellaneous/voxelizer/) - Voxel conversion
- [Playwright](https://playwright.dev/) - Browser automation

## 💡 Tips

1. **Better Results**: Use clear, well-lit images with simple backgrounds
2. **File Size**: Keep input images under 10MB for faster processing
3. **API Limits**: Check your Meshy API usage limits
4. **Voxel Resolution**: The Drububu voxelizer may have resolution limits

## 🐛 Debug Mode

To enable verbose logging, modify `main.py`:

```python
# Add at the top of the file
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

**Note**: This tool requires an active internet connection and valid Meshy API credentials.