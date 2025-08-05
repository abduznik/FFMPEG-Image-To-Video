# Commands for FFMPEG-Image-To-Video

## One-Time Setup

1.  Install the **Termux:X11** app from the F-Droid store.

2.  Install all necessary packages in Termux with a single command:
    ```bash
    pkg install openbox python-tkinter ffmpeg termux-x11 -y
    ```

## How to Run the App (Step-by-Step)

1.  Start the X11 server in a separate Termux session:
    ```bash
    termux-x11 :0
    ```

2.  In your original Termux session, run the Python application:
    ```bash
    DISPLAY=:0 python app.py
    ```

---

### Note on Zsh and Mounted Directories

Termux can sometimes have issues with permissions and paths when using shells like Zsh on mounted directories (like your shared storage). This can cause scripts to fail when they try to access files or execute commands.

If you encounter errors, running the commands using the default Bash shell often resolves these issues.
