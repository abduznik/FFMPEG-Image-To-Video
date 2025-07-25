# FFMPEG-Image-To-Video
![](favicon.png)


This is a Python application built with Tkinter that allows you to convert a series of images into a video using FFmpeg. It provides a user-friendly graphical interface to configure various video settings.

## Features:
- Select source directory containing images (PNG, JPG, JPEG, BMP).
- Select destination directory for the output video.
- Set individual image duration in the video.
- Configure transition duration between images.
- Option to randomize transitions or select a specific transition.
- Choose from a variety of FFmpeg xfade transitions.
- Select FFmpeg encoding preset (e.g., ultrafast, medium, slow).
- Adjust CRF (Constant Rate Factor) value for video quality control.

## How to Use:

### 1. Clone and Run from Source:
1. **Clone the repository:**
   ```bash
   git clone https://github.com/abduznik/FFMPEG-Image-To-Video.git
   cd FFMPEG-Image-To-Video
   ```
2. **Install dependencies (if any, though this app primarily relies on built-in Python modules and FFmpeg):**
   ```bash
   # You might need to install sv_ttk if not already present
   pip install sv_ttk
   ```
3. **Ensure FFmpeg is available:**
   - Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html).
   - Place `ffmpeg.exe` in the same directory as `app.py` or ensure it's in your system's PATH.
4. **Run the application:**
   ```bash
   python app.py
   ```

### 2. Download from Releases:
You can download the latest executable release from the [Releases](https://github.com/abduznik/FFMPEG-Image-To-Video/releases) section of this repository.

1. Go to the [Releases page](https://github.com/abduznik/FFMPEG-Image-To-Video/releases).
2. Download the latest `.zip` or `.exe` file.
3. Extract the contents (if it's a `.zip` file).
4. Ensure `ffmpeg.exe` is in the same directory as the executable.
5. Run the executable.

> All emojis designed by [OpenMoji](https://openmoji.org/) – the open-source emoji and icon project. License: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/#)
