import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import random
import shutil
import subprocess
import sys
import sv_ttk
import threading
import queue

def get_ffmpeg_path() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, "ffmpeg.exe")
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg", "ffmpeg.exe")
    if os.path.exists(local_path):
        return local_path
    which_path = shutil.which("ffmpeg")
    if which_path:
        return which_path
    return "ffmpeg.exe"

def get_icon_path() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, "favicon.ico")
    else:
        return "favicon.ico"

def download_ffmpeg() -> str | None:
    import urllib.request
    import zipfile
    import io
    ffmpeg_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg")
    os.makedirs(ffmpeg_dir, exist_ok=True)
    dest = os.path.join(ffmpeg_dir, "ffmpeg.exe")
    url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    try:
        with urllib.request.urlopen(url, timeout=300) as resp:
            data = resp.read()
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for name in zf.namelist():
                if name.replace("\\", "/").endswith("/ffmpeg.exe"):
                    with zf.open(name) as src, open(dest, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    return dest
    except Exception:
        return None
    return None

XFADE_TRANSITIONS = [
    "fade", "fadeblack", "fadewhite", "distance", "wipeleft", "wiperight", "wipeup", "wipedown",
    "slideleft", "slideright", "slideup", "slidedown", "smoothleft", "smoothright",
    "smoothup", "smoothdown", "circlecrop", "rectcrop", "circleclose", "circleopen",
    "horzclose", "horzopen", "vertclose", "vertopen", "diagbl", "diagbr", "diagtl", "diagtr",
    "hlslice", "hrslice", "vuslice", "vdslice", "dissolve", "pixelize", "radial",
    "hblur", "wipetl", "wipetr", "wipebl", "wipebr", "zoomin", "fadegrays",
    "squeezev", "squeezeh", "hlwind", "hrwind", "vuwind", "vdwind",
    "coverleft", "coverright", "coverup", "coverdown", "revealleft", "revealright", "revealup", "revealdown"
]

NVENC_PRESET_MAP = {
    "ultrafast": "p1", "superfast": "p2", "veryfast": "p3", "faster": "p4",
    "fast": "p5", "medium": "p6", "slow": "p7", "slower": "p7", "veryslow": "p7"
}

cancel_event = threading.Event()
selected_custom_transitions: list[str] = []
checkbox_vars: dict[str, tk.BooleanVar] = {}
last_used_transition: str | None = None

def create_video_worker(q: queue.Queue) -> None:
    source_dir = source_dir_var.get()
    dest_dir = dest_dir_var.get()
    duration = duration_var.get()
    fade_duration = fade_duration_var.get()
    randomize_transitions = randomize_transitions_var.get()
    selected_transition = selected_transition_var.get()
    selected_preset = preset_var.get()
    crf_value = crf_var.get()

    ffmpeg_path = get_ffmpeg_path()
    if not os.path.exists(ffmpeg_path):
        q.put(("info", "FFmpeg not found, downloading..."))
        ffmpeg_path = download_ffmpeg()
        if not ffmpeg_path:
            q.put(("error", "Could not locate or download FFmpeg. Please install it manually."))
            return

    if not source_dir or not dest_dir:
        q.put(("error", "Please select source and destination directories."))
        return

    if duration <= 0:
        q.put(("error", "Image duration must be greater than 0."))
        return

    if fade_duration < 0:
        q.put(("error", "Transition duration must be non-negative."))
        return

    if fade_duration >= duration:
        q.put(("error", "Transition duration must be less than image duration."))
        return

    if crf_value < 0 or crf_value > 51:
        q.put(("error", "CRF must be between 0 and 51."))
        return

    width = width_var.get()
    height = height_var.get()
    if width <= 0 or height <= 0:
        q.put(("error", "Resolution must be positive values."))
        return

    output_filename = output_name_var.get().strip()
    if not output_filename:
        q.put(("error", "Output filename cannot be empty."))
        return
    if not output_filename.endswith('.mp4'):
        output_filename += '.mp4'

    if cancel_event.is_set():
        q.put(("error", "Video creation cancelled."))
        return

    image_files = []
    for f in os.listdir(source_dir):
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            image_files.append(os.path.join(source_dir, f))

    if not image_files:
        q.put(("error", "No image files found in the selected directory."))
        return

    if sort_order_var.get() == "by name":
        image_files.sort(key=lambda x: os.path.basename(x).lower())
    else:
        random.shuffle(image_files)

    output_file = os.path.join(dest_dir, output_filename)

    input_args = []
    filter_complex_parts = []
    processed_video_streams = []

    for i, image_file in enumerate(image_files):
        input_args.extend(['-loop', '1', '-t', str(duration), '-r', '25', '-i', image_file])
        filter_complex_parts.append(
            f'[{i}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,'
            f'pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p,'
            f'trim=duration={duration},setpts=PTS-STARTPTS,fps=25[v{i}];'
        )
        processed_video_streams.append(f'[v{i}]')

    if cancel_event.is_set():
        q.put(("error", "Video creation cancelled."))
        return

    if len(image_files) > 1:
        xfade_chain = []
        current_input_stream = processed_video_streams[0]
        for i in range(len(image_files) - 1):
            next_input_stream = processed_video_streams[i+1]
            output_stream_name = f'out_v{i}' if i < len(image_files) - 2 else 'final_output'
            transition_name = selected_transition
            if randomize_transitions:
                available_transitions = list(selected_custom_transitions) if selected_custom_transitions else list(XFADE_TRANSITIONS)
                global last_used_transition
                if last_used_transition and len(available_transitions) > 1 and last_used_transition in available_transitions:
                    available_transitions.remove(last_used_transition)
                transition_name = random.choice(available_transitions)
                last_used_transition = transition_name
            offset = (i + 1) * duration - (i + 1) * fade_duration
            xfade_chain.append(
                f'{current_input_stream}{next_input_stream}xfade=transition={transition_name}:'
                f'duration={fade_duration}:offset={offset}[{output_stream_name}];'
            )
            current_input_stream = f'[{output_stream_name}]'
        filter_complex_parts.extend(xfade_chain)
        final_output_stream = '[final_output]'
    else:
        final_output_stream = processed_video_streams[0]

    filter_complex = "".join(filter_complex_parts)
    total_video_duration = len(image_files) * duration - (fade_duration * (len(image_files) - 1))
    if len(image_files) == 1:
        total_video_duration = duration

    use_hw = use_hw_accel_var.get()
    ffmpeg_command = [ffmpeg_path]
    video_args = [
        *input_args,
        '-filter_complex', filter_complex,
        '-map', final_output_stream,
        '-t', str(total_video_duration),
        '-y',
        output_file
    ]
    if use_hw:
        video_args.extend([
            '-c:v', 'h264_nvenc',
            '-preset', NVENC_PRESET_MAP.get(selected_preset, "p6"),
            '-cq', str(crf_value),
        ])
    else:
        video_args.extend([
            '-preset', selected_preset,
            '-threads', '0',
            '-crf', str(crf_value),
        ])
    ffmpeg_command.extend(video_args)

    try:
        process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')

        stderr_lines = []
        stderr_thread = threading.Thread(target=lambda: stderr_lines.append(process.stderr.read()), daemon=True)
        stderr_thread.start()

        while process.poll() is None:
            if cancel_event.is_set():
                process.terminate()
                try:
                    process.wait(timeout=5)
                except:
                    process.kill()
                    process.wait()
                q.put(("error", "Video creation cancelled."))
                return
            cancel_event.wait(0.5)

        stderr_thread.join(timeout=2)
        stderr = stderr_lines[0] if stderr_lines else ""
        process.stdout.close()

        if process.returncode == 0:
            q.put(("success", f"Video created successfully at {output_file}"))
        else:
            error_message = f"ffmpeg command failed with return code {process.returncode}\n"
            error_message += f"Stderr:\n{stderr}"
            q.put(("error", error_message))

    except FileNotFoundError:
        q.put(("error", "ffmpeg not found. Please make sure it's installed and in your system's PATH or in the same directory as the app."))
    except Exception as e:
        q.put(("error", f"An error occurred: {e}"))

def create_video() -> None:
    cancel_event.clear()
    status_label.config(text="")
    progress_bar.grid(row=13, column=0, columnspan=3, sticky="ew", pady=10)
    progress_bar.start()
    create_video_button.config(state="disabled")
    cancel_button.config(state="normal")

    q = queue.Queue()
    threading.Thread(target=create_video_worker, args=(q,), daemon=True).start()
    root.after(100, process_queue, q)

def process_queue(q: queue.Queue) -> None:
    try:
        message_type, message = q.get_nowait()
        if message_type == "success":
            progress_bar.stop()
            progress_bar.grid_remove()
            create_video_button.config(state="normal")
            cancel_button.config(state="disabled")
            status_label.config(text="")
            messagebox.showinfo("Success", message)
        elif message_type == "error":
            progress_bar.stop()
            progress_bar.grid_remove()
            create_video_button.config(state="normal")
            cancel_button.config(state="disabled")
            status_label.config(text="")
            messagebox.showerror("Error", message)
        elif message_type == "info":
            status_label.config(text=message)
            root.after(100, process_queue, q)
    except queue.Empty:
        root.after(100, process_queue, q)

def select_source_dir() -> None:
    path = filedialog.askdirectory()
    if path:
        source_dir_var.set(path)

def select_dest_dir() -> None:
    path = filedialog.askdirectory()
    if path:
        dest_dir_var.set(path)

def toggle_transition_options() -> None:
    state = "disabled" if randomize_transitions_var.get() else "normal"
    transition_option_menu.config(state=state)

def cancel_video() -> None:
    cancel_event.set()

def open_custom_transitions_window() -> None:
    custom_transitions_window = tk.Toplevel(root)
    custom_transitions_window.title("Select Custom Transitions")
    frame = ttk.Frame(custom_transitions_window, padding=10)
    frame.pack(fill="both", expand=True)
    for i, transition in enumerate(XFADE_TRANSITIONS):
        checkbox_vars[transition] = tk.BooleanVar(value=(transition in selected_custom_transitions))
        cb = ttk.Checkbutton(frame, text=transition, variable=checkbox_vars[transition])
        cb.grid(row=i // 4, column=i % 4, sticky="w", padx=5, pady=2)
    button_frame = ttk.Frame(custom_transitions_window, padding=10)
    button_frame.pack(fill="x")
    ttk.Button(button_frame, text="Save", command=lambda: save_custom_transitions(custom_transitions_window)).pack(side="left", padx=5)
    ttk.Button(button_frame, text="Cancel", command=custom_transitions_window.destroy).pack(side="left", padx=5)

def save_custom_transitions(window: tk.Toplevel) -> None:
    global selected_custom_transitions
    selected_custom_transitions = [t for t, var in checkbox_vars.items() if var.get()]
    window.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Image to Video Creator")
    root.iconbitmap(get_icon_path())
    sv_ttk.set_theme("dark")
    style = ttk.Style()
    style.configure("TLabel", padding=5)
    style.configure("TButton", padding=5)
    style.configure("TEntry", padding=5)
    frame = ttk.Frame(root, padding=10)
    frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    source_dir_var = tk.StringVar()
    dest_dir_var = tk.StringVar()
    duration_var = tk.DoubleVar(value=3.0)
    fade_duration_var = tk.DoubleVar(value=0.3)
    randomize_transitions_var = tk.BooleanVar(value=False)
    selected_transition_var = tk.StringVar(value="fade")
    preset_var = tk.StringVar(value="medium")
    crf_var = tk.IntVar(value=23)
    width_var = tk.IntVar(value=1920)
    height_var = tk.IntVar(value=1080)
    output_name_var = tk.StringVar(value="output.mp4")
    sort_order_var = tk.StringVar(value="by name")
    use_hw_accel_var = tk.BooleanVar(value=False)

    ttk.Label(frame, text="Source Image Directory:").grid(row=0, column=0, sticky="w")
    ttk.Entry(frame, textvariable=source_dir_var, width=50).grid(row=0, column=1)
    ttk.Button(frame, text="Browse...", command=select_source_dir).grid(row=0, column=2)
    ttk.Label(frame, text="Destination Directory:").grid(row=1, column=0, sticky="w")
    ttk.Entry(frame, textvariable=dest_dir_var, width=50).grid(row=1, column=1)
    ttk.Button(frame, text="Browse...", command=select_dest_dir).grid(row=1, column=2)
    ttk.Label(frame, text="Image Duration (s):").grid(row=2, column=0, sticky="w")
    ttk.Entry(frame, textvariable=duration_var, width=10).grid(row=2, column=1, sticky="w")
    ttk.Label(frame, text="Transition Duration (s):").grid(row=3, column=0, sticky="w")
    ttk.Entry(frame, textvariable=fade_duration_var, width=10).grid(row=3, column=1, sticky="w")
    ttk.Checkbutton(frame, text="Randomize Transitions", variable=randomize_transitions_var, command=toggle_transition_options).grid(row=4, column=0, sticky="w")
    ttk.Label(frame, text="Select Transition:").grid(row=5, column=0, sticky="w")
    transition_option_menu = ttk.OptionMenu(frame, selected_transition_var, selected_transition_var.get(), *XFADE_TRANSITIONS)
    transition_option_menu.grid(row=5, column=1, sticky="w")
    ttk.Button(frame, text="Select Custom Transitions...", command=open_custom_transitions_window).grid(row=5, column=2, sticky="w")

    presets = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]
    ttk.Label(frame, text="Select Preset:").grid(row=6, column=0, sticky="w")
    preset_combobox = ttk.Combobox(frame, textvariable=preset_var, values=presets, state="readonly")
    preset_combobox.grid(row=6, column=1, sticky="w")

    ttk.Label(frame, text="CRF Value (Higher is worse quality):").grid(row=7, column=0, sticky="w")
    crf_scale = ttk.Scale(frame, from_=0, to=51, variable=crf_var, orient=tk.HORIZONTAL)
    crf_scale.grid(row=7, column=1, sticky="ew")
    crf_label = ttk.Label(frame, text="23")
    crf_label.grid(row=7, column=2, sticky="w")

    def update_crf_label(val: str) -> None:
        crf_label.config(text=f"{int(float(val))}")

    crf_var.trace_add("write", lambda name, index, mode: update_crf_label(crf_var.get()))

    ttk.Label(frame, text="Image Order:").grid(row=8, column=0, sticky="w")
    sort_combobox = ttk.Combobox(frame, textvariable=sort_order_var, values=["by name", "random"], state="readonly", width=10)
    sort_combobox.grid(row=8, column=1, sticky="w")

    ttk.Label(frame, text="Resolution:").grid(row=9, column=0, sticky="w")
    res_frame = ttk.Frame(frame)
    res_frame.grid(row=9, column=1, sticky="w")
    ttk.Entry(res_frame, textvariable=width_var, width=6).pack(side="left", padx=(0, 2))
    ttk.Label(res_frame, text="x").pack(side="left", padx=2)
    ttk.Entry(res_frame, textvariable=height_var, width=6).pack(side="left", padx=(2, 0))

    ttk.Label(frame, text="Output Filename:").grid(row=10, column=0, sticky="w")
    ttk.Entry(frame, textvariable=output_name_var, width=20).grid(row=10, column=1, sticky="w")

    ttk.Checkbutton(frame, text="Use NVIDIA GPU Acceleration (NVENC)", variable=use_hw_accel_var).grid(row=11, column=0, columnspan=2, sticky="w")

    create_video_button = ttk.Button(frame, text="Create Video", command=create_video)
    create_video_button.grid(row=12, column=1, pady=10)

    cancel_button = ttk.Button(frame, text="Cancel", command=cancel_video, state="disabled")
    cancel_button.grid(row=12, column=2, pady=10)

    progress_bar = ttk.Progressbar(frame, orient="horizontal", length=300, mode="indeterminate")
    status_label = ttk.Label(frame, text="")
    status_label.grid(row=14, column=0, columnspan=3, sticky="ew")

    for child in frame.winfo_children():
        child.grid_configure(padx=5, pady=5)

    toggle_transition_options()
    root.mainloop()