import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import subprocess
import json
import os
import threading
import sys
import re

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Downloader")
        self.geometry("850x750")

        # --- Paths & Config ---
        if getattr(sys, 'frozen', False):
            self.base_path = sys._MEIPASS
            self.config_path = os.path.join(os.path.dirname(sys.executable), "config.json")
        else:
            self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.config_path = os.path.join(self.base_path, "config.json")

        exe_ext = ".exe" if sys.platform == "win32" else ""
        self.yt_dlp_path = os.path.join(self.base_path, "bin", f"yt-dlp{exe_ext}")
        self.ffmpeg_path = os.path.join(self.base_path, "bin")

        self.grid_columnconfigure(0, weight=1)

        # --- UI Elements ---
        top_frame = ttk.Frame(self)
        top_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        top_frame.grid_columnconfigure(0, weight=1)

        # URL Input
        ttk.Label(top_frame, text="Video URL:").grid(row=0, column=0, sticky="w")
        self.url_entry = ttk.Entry(top_frame)
        self.url_entry.grid(row=1, column=0, sticky="ew")
        self.analyze_button = ttk.Button(top_frame, text="Analyze URL", command=self.start_analysis)
        self.analyze_button.grid(row=1, column=1, padx=(5, 0))
        
        # Save Directory
        ttk.Label(top_frame, text="Save to:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.save_path_var = tk.StringVar()
        save_entry = ttk.Entry(top_frame, textvariable=self.save_path_var, state="readonly")
        save_entry.grid(row=3, column=0, sticky="ew")
        self.browse_button = ttk.Button(top_frame, text="Browse...", command=self.select_save_directory)
        self.browse_button.grid(row=3, column=1, padx=(5, 0))

        # Format Selection
        formats_frame = ttk.LabelFrame(self, text="Format Selection")
        formats_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        formats_frame.grid_columnconfigure(1, weight=1)
        # ... (rest of format selection widgets are the same)
        ttk.Label(formats_frame, text="Video Quality:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.video_format_combo = ttk.Combobox(formats_frame, state="readonly")
        self.video_format_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Label(formats_frame, text="Audio Quality:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.audio_format_combo = ttk.Combobox(formats_frame, state="readonly")
        self.audio_format_combo.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ttk.Label(formats_frame, text="Output Format:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.output_format = tk.StringVar(value="mp4")
        ttk.Radiobutton(formats_frame, text="MP4", variable=self.output_format, value="mp4").grid(row=2, column=1, padx=5, sticky="w")
        ttk.Radiobutton(formats_frame, text="MKV", variable=self.output_format, value="mkv").grid(row=2, column=1, padx=5)
        ttk.Radiobutton(formats_frame, text="MP3", variable=self.output_format, value="mp3").grid(row=2, column=1, padx=5, sticky="e")

        # Download & Output
        self.download_button = ttk.Button(self, text="Download", command=self.download_video, state="disabled")
        self.download_button.grid(row=2, column=0, columnspan=2, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progressbar = ttk.Progressbar(self, variable=self.progress_var, maximum=100)
        self.progressbar.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        self.output_text = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=15)
        self.output_text.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.grid_rowconfigure(4, weight=1)
        
        self.video_formats = []
        self.audio_formats = []
        
        self.load_config()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        self.save_config()
        self.destroy()

    def load_config(self):
        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)
                path = config.get("save_path")
                if path and os.path.isdir(path):
                    self.save_path_var.set(path)
                else:
                    self.save_path_var.set(os.path.join(os.path.expanduser("~"), "Downloads"))
        except (FileNotFoundError, json.JSONDecodeError):
            self.save_path_var.set(os.path.join(os.path.expanduser("~"), "Downloads"))

    def save_config(self):
        config = {"save_path": self.save_path_var.get()}
        with open(self.config_path, "w") as f:
            json.dump(config, f)
            
    def select_save_directory(self):
        path = filedialog.askdirectory(initialdir=self.save_path_var.get())
        if path:
            self.save_path_var.set(path)
            self.log(f"Save directory set to: {path}")

    def log(self, message):
        self.output_text.insert(tk.END, message.strip() + "\n")
        self.output_text.see(tk.END)

    def start_analysis(self):
        # ... (same as before)
        self.analyze_button["state"] = "disabled"
        self.download_button["state"] = "disabled"
        self.log("Starting analysis...")
        threading.Thread(target=self.analyze_url, daemon=True).start()

    def analyze_url(self):
        # ... (same as before, just ensuring title is set)
        url = self.url_entry.get()
        if not url:
            messagebox.showerror("Error", "Please enter a URL.")
            self.analyze_button["state"] = "normal"
            return
        try:
            # Hide console window on Windows
            si = None
            if sys.platform == "win32":
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE

            command = [self.yt_dlp_path, "--dump-json", url, "--js-runtimes", "node", "--playlist-items", "1"]
            process = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', check=False, startupinfo=si, errors='replace') # check=False to handle warnings

            if process.returncode != 0:
                self.log(f"yt-dlp exited with warnings or errors (Code: {process.returncode}):")
                self.log(process.stderr)
                # Still try to parse stdout, as it might contain partial info
            
            if not process.stdout.strip():
                raise Exception("No data received from yt-dlp analysis.")

            # Parse only the first line to handle potential multi-JSON output (e.g. playlists) safely
            first_line = process.stdout.strip().split('\n')[0]
            info = json.loads(first_line)
            
            self.winfo_toplevel().title(info.get('title', 'YouTube Downloader'))
            formats = info.get("formats", [])
            self.video_formats.clear()
            self.audio_formats.clear()

            for f in formats:
                filesize = f.get('filesize') or f.get('filesize_approx')
                size_mb = f"~{filesize / (1024*1024):.1f}MB" if filesize else "N/A"
                
                if f.get('vcodec') != 'none' and f.get('acodec') == 'none':
                    desc = f"{f.get('height', 'N/A')}p ({f.get('ext')}, {f.get('vcodec')}) - {size_mb}"
                    self.video_formats.append((desc, f['format_id']))
                elif f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    desc = f"{f.get('abr', 0)}k ({f.get('ext')}, {f.get('acodec')}) - {size_mb}"
                    self.audio_formats.append((desc, f['format_id']))

            self.video_format_combo['values'] = [v[0] for v in self.video_formats]
            self.audio_format_combo['values'] = [a[0] for a in self.audio_formats]
            if self.video_formats: self.video_format_combo.set(self.video_formats[-1][0])
            if self.audio_formats: self.audio_format_combo.set(self.audio_formats[-1][0])
            
            self.log(f"Analysis complete for: {info.get('title', 'Unknown title')}")
            self.download_button["state"] = "normal"
        except Exception as e:
            self.log(f"An unexpected error occurred during analysis: {e}")
            messagebox.showerror("Error", f"An unexpected error occurred during analysis: {e}")
        finally:
            self.analyze_button["state"] = "normal"

    def reset_ui(self):
        """Resets the UI elements to their initial state."""
        self.url_entry.delete(0, tk.END)
        self.video_format_combo.set('')
        self.video_format_combo['values'] = []
        self.audio_format_combo.set('')
        self.audio_format_combo['values'] = []
        self.progress_var.set(0)
        self.video_formats = []
        self.audio_formats = []
        self.log("Ready for next download.")

    def download_video(self):
        url = self.url_entry.get()
        if not url:
            messagebox.showerror("Error", "Please enter a URL.")
            return

        output_format = self.output_format.get()
        is_mp3 = output_format == 'mp3'
        
        # User requested "change to download single video", so we prioritize single video mode.
        # We will strictly enforce --no-playlist to avoid accidental bulk downloads.
        is_playlist = False 

        video_id = None
        audio_id = None
        
        # Get selected format IDs
        video_desc = self.video_format_combo.get()
        audio_desc = self.audio_format_combo.get()

        # If not MP3, we need video format. If MP3, we only strictly need audio.
        if not is_mp3:
            if not video_desc or not audio_desc:
                messagebox.showerror("Error", "Please analyze a URL and select formats first.")
                return
            video_id = next((v[1] for v in self.video_formats if v[0] == video_desc), None)

        # Always try to get audio ID if selected
        if audio_desc:
            audio_id = next((a[1] for a in self.audio_formats if a[0] == audio_desc), None)

        if not is_mp3 and (not video_id or not audio_id):
            messagebox.showerror("Error", "Could not find the selected format IDs. Please re-analyze.")
            return

        # Sanitize title for use as a filename
        title = self.winfo_toplevel().title()
        sanitized_title = "".join(c for c in title if c.isalnum() or c in (' ', '.', '_')).rstrip()
        initial_filename = f"{sanitized_title}.{output_format}"
        
        save_path = filedialog.asksaveasfilename(
            initialdir=self.save_path_var.get(),
            initialfile=initial_filename,
            defaultextension=f".{output_format}",
            filetypes=[(f"{output_format.upper()} Files", f"*.{output_format}"), ("All Files", "*.*")]
        )

        if not save_path:
            self.log("Download cancelled by user.")
            return

        command = [self.yt_dlp_path]

        if is_mp3:
             # Audio Only Logic
            if audio_id:
                command.extend(["-f", audio_id])
            else:
                command.extend(["-f", "ba/b"]) # Best audio
            
            command.append("-x") # Extract audio
            command.extend(["--audio-format", "mp3"])
        else:
            # Video + Audio Logic
            command.extend(["-f", f"{video_id}+{audio_id}"])
            command.extend(["--merge-output-format", output_format])

        command.extend([
            "--ffmpeg-location", self.ffmpeg_path,
            "-o", save_path, 
            url,
            "--progress",
            "--newline",
            "--js-runtimes", "node",
            "--no-playlist" # Force single video download
        ])

        self.progress_var.set(0)
        self.download_button["state"] = "disabled"
        self.analyze_button["state"] = "disabled"
        self.browse_button["state"] = "disabled"
        self.log(f"Starting download to {save_path}...")
        threading.Thread(target=self.run_download_process, args=(command,), daemon=True).start()

    def run_download_process(self, command):
        try:
            si = None
            if sys.platform == "win32":
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE

            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', startupinfo=si)
            
            # Regex to capture yt-dlp's progress percentage
            progress_regex = re.compile(r"\[download\]\s+([0-9.]+)%")

            for line in iter(process.stdout.readline, ''):
                self.log(line)
                match = progress_regex.search(line)
                if match:
                    percentage = float(match.group(1))
                    # Schedule GUI update from the main thread
                    self.after_idle(self.progress_var.set, percentage)
            
            process.stdout.close()
            return_code = process.wait()

            if return_code == 0:
                self.after_idle(self.progress_var.set, 100)
                self.log("Download completed successfully!")
                messagebox.showinfo("Success", f"Download complete!\nFile saved to: {command[command.index('-o') + 1]}")
                # Reset UI after successful download
                self.after_idle(self.reset_ui)
            else:
                self.after_idle(self.progress_var.set, 0)
                self.log(f"Download failed with return code: {return_code}")
                messagebox.showerror("Download Failed", "The download process failed. Check the log.")
        except Exception as e:
            self.log(f"An unexpected error occurred: {e}")
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
        finally:
            self.download_button["state"] = "normal"
            self.analyze_button["state"] = "normal"
            self.browse_button["state"] = "normal"

if __name__ == "__main__":
    app = App()
    app.mainloop()
