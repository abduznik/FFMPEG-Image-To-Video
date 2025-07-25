import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import random
import subprocess
import sys
import sv_ttk
import threading
import queue

def get_ffmpeg_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, "ffmpeg.exe")
    else:
        return "ffmpeg.exe"

def get_icon_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, "favicon.ico")
    else:
        return "favicon.ico"

XFADE_TRANSITIONS = [
    "fade", "fadeblack", "fadewhite", "distance", "wipeleft", "wiperight", "wipeup", "wipedown",
    "slideleft", "slideright", "slideup", "slidedown", "smoothleft", "smoothright",
    "smoothup", "smoothdown", "circlecrop", "rectcrop", "circleclose", "circleopen",
    "horzclose", "horzopen", "vertclose", "vertopen", "diagbl", "diagbr", "diagtl", "diagtr",
    "hlslice", "hrslice", "vuslice", "vdslice", "dissolve", "pixelize", "radial",
    "hblur", "wipetl", "wipetr", "wipebl", "wipetr", "zoomin", "fadegrays",
    "squeezev", "squeezeh", "hlwind", "hrwind", "vuwind", "vdwind",
    "coverleft", "coverright", "coverup", "coverdown", "revealleft", "revealright", "revealup", "revealdown"
]

def create_video_worker(q):
    source_dir = source_dir_var.get()
    dest_dir = dest_dir_var.get()
    duration = duration_var.get()
    fade_duration = fade_duration_var.get()
    randomize_transitions = randomize_transitions_var.get()
    selected_transition = selected_transition_var.get()
    selected_preset = preset_var.get()
    crf_value = crf_var.get()

    if not source_dir or not dest_dir:
        q.put(("error", "Please select source and destination directories."))
        return

    if fade_duration >= duration:
        q.put(("error", "Transition duration must be less than image duration."))
        return

    image_files = []
    for f in os.listdir(source_dir):
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            image_files.append(os.path.join(source_dir, f))

    if not image_files:
        q.put(("error", "No image files found in the selected directory."))
        return

    random.shuffle(image_files)
    output_file = os.path.join(dest_dir, "output.mp4")

    input_args = []
    filter_complex_parts = []
    processed_video_streams = []

    for i, image_file in enumerate(image_files):
        input_args.extend(['-loop', '1', '-t', str(duration), '-r', '25', '-i', image_file])
        filter_complex_parts.append(
            f'[{i}:v]scale=1920:1080:force_original_aspect_ratio=decrease,'
            f'pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p,'
            f'trim=duration={duration},setpts=PTS-STARTPTS,fps=25[v{i}];'
        )
        processed_video_streams.append(f'[v{i}]')

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

    ffmpeg_command = [get_ffmpeg_path()]
    ffmpeg_command.extend([
        *input_args,
        '-filter_complex', filter_complex,
        '-map', final_output_stream,
        '-preset', selected_preset,
        '-threads', '0',
        '-crf', str(crf_value),
        '-t', str(total_video_duration),
        '-y',
        output_file
    ])

    

    try:
        process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        
        stdout, stderr = process.communicate()

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

def create_video():
    progress_bar.grid(row=10, column=0, columnspan=3, sticky="ew", pady=10)
    progress_bar["value"] = 0
    create_video_button.config(state="disabled")
    
    q = queue.Queue()
    threading.Thread(target=create_video_worker, args=(q,)).start()
    root.after(100, process_queue, q)

def process_queue(q):
    try:
        message_type, message = q.get_nowait()
        if message_type == "success":
            messagebox.showinfo("Success", message)
            progress_bar.grid_remove()
            create_video_button.config(state="normal")
        elif message_type == "error":
            messagebox.showerror("Error", message)
            progress_bar.grid_remove()
            create_video_button.config(state="normal")
    except queue.Empty:
        root.after(100, process_queue, q)

def select_source_dir():
    path = filedialog.askdirectory()
    if path:
        source_dir_var.set(path)

def select_dest_dir():
    path = filedialog.askdirectory()
    if path:
        dest_dir_var.set(path)

def toggle_transition_options():
    state = "disabled" if randomize_transitions_var.get() else "normal"
    transition_option_menu.config(state=state)

def open_custom_transitions_window():
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

def save_custom_transitions(window):
    global selected_custom_transitions
    selected_custom_transitions = [t for t, var in checkbox_vars.items() if var.get()]
    window.destroy()

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
selected_custom_transitions = []
checkbox_vars = {}
last_used_transition = None

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

def update_crf_label(val):
    crf_label.config(text=f"{int(float(val))}")

crf_var.trace_add("write", lambda name, index, mode: update_crf_label(crf_var.get()))



create_video_button = ttk.Button(frame, text="Create Video", command=create_video)
create_video_button.grid(row=9, column=1, pady=10)

progress_bar = ttk.Progressbar(frame, orient="horizontal", length=300, mode="determinate")

for child in frame.winfo_children():
    child.grid_configure(padx=5, pady=5)

toggle_transition_options()
root.mainloop()