# FFMPEG-Image-To-Video
![](favicon.png)

A Python Tkinter GUI that converts a series of images into a video with transitions using FFmpeg.

[![CI](https://github.com/abduznik/FFMPEG-Image-To-Video/actions/workflows/ci.yml/badge.svg)](https://github.com/abduznik/FFMPEG-Image-To-Video/actions/workflows/ci.yml)

## Features

- Select source directory containing images (PNG, JPG, JPEG, BMP)
- Select destination directory and custom output filename
- Set individual image duration and transition duration
- Choose from 55+ FFmpeg xfade transitions or randomize them
- **Image sort order** — by name or random
- **Custom resolution** — configurable width/height (default 1920×1080)
- **NVIDIA NVENC hardware acceleration** — GPU-encoded H.264 with one click
- Select FFmpeg encoding preset (ultrafast → veryslow)
- Adjust CRF value for video quality control
- **Auto-download FFmpeg** if not found on your system
- **Cancel button** to stop video creation mid-process
- Progress bar with status feedback

## How to Use

### 1. Clone and Run from Source

```bash
git clone https://github.com/abduznik/FFMPEG-Image-To-Video.git
cd FFMPEG-Image-To-Video
pip install -r requirements.txt
python app.py
```

FFmpeg will be downloaded automatically on first use. You can also place `ffmpeg.exe` in the `ffmpeg/` directory or add it to your system PATH.

### 2. Download from Releases

Download the latest `ImageToVideo.exe` from the [Releases page](https://github.com/abduznik/FFMPEG-Image-To-Video/releases).

The executable is standalone — FFmpeg is bundled inside. No Python or manual setup required.

## Usage Tips

- Images are automatically scaled and padded to the target resolution
- Transition duration must be less than image duration
- CRF range: 0–51 (lower = better quality, larger file)
- NVENC preset mapping: ultrafast→p1, medium→p6, veryslow→p7

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

## License

This project is open source under the [MIT License](LICENSE).

FFmpeg is distributed under the [GNU GPL v3](ffmpeg/LICENSE.txt). See `ffmpeg/LICENSE.txt` for details.

> All emojis designed by [OpenMoji](https://openmoji.org/) – the open-source emoji and icon project. License: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/#)
