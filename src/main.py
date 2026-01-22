import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import subprocess
import json
import os
import threading
import sys
import re
import instaloader

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Universal Video & IG Photo Downloader")
        self.geometry("850x750")
        
        # --- High DPI Support (macOS & Windows) ---
        try:
            # Windows
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
            
        # macOS High DPI is usually handled automatically by Tkinter 8.6+, 
        # but we ensure the scaling is reasonable.
        # scaling = self.call('tk', 'scaling') 

        # --- Performance Optimization: Log Buffering ---
        self.log_queue = []
        self.is_log_updating = False
        self.update_log_interval = 100 # ms

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
        ttk.Label(top_frame, text="Video/Photo URL:").grid(row=0, column=0, sticky="w")
        self.url_var = tk.StringVar()
        self.url_var.trace("w", self.on_url_change)
        self.url_entry = ttk.Entry(top_frame, textvariable=self.url_var)
        self.url_entry.grid(row=1, column=0, sticky="ew")
        self.analyze_button = ttk.Button(top_frame, text="Analyze URL (Video Only)", command=self.start_analysis)
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
        
        ttk.Label(formats_frame, text="Video Quality:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.video_format_combo = ttk.Combobox(formats_frame, state="readonly")
        self.video_format_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(formats_frame, text="Audio Quality:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.audio_format_combo = ttk.Combobox(formats_frame, state="readonly")
        self.audio_format_combo.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(formats_frame, text="Mode:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.output_format = tk.StringVar(value="mp4")
        
        radio_frame = ttk.Frame(formats_frame)
        radio_frame.grid(row=2, column=1, sticky="w")
        
        ttk.Radiobutton(radio_frame, text="Video (MP4)", variable=self.output_format, value="mp4").pack(side="left", padx=5)
        ttk.Radiobutton(radio_frame, text="Video (MKV)", variable=self.output_format, value="mkv").pack(side="left", padx=5)
        ttk.Radiobutton(radio_frame, text="Audio (MP3)", variable=self.output_format, value="mp3").pack(side="left", padx=5)
        ttk.Radiobutton(radio_frame, text="IG Photo", variable=self.output_format, value="ig_photo").pack(side="left", padx=5)

        # Download & Output
        self.download_button = ttk.Button(self, text="Download", command=self.download_content, state="disabled")
        self.download_button.grid(row=2, column=0, columnspan=2, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progressbar = ttk.Progressbar(self, variable=self.progress_var, maximum=100)
        self.progressbar.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        self.output_text = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=15)
        self.output_text.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.grid_rowconfigure(4, weight=1)
        
        self.video_formats = []
        self.audio_formats = []
        self.last_analyzed_url = ""
        self.analysis_timer = None
        
        self.load_config()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.output_format.trace("w", self.on_mode_change)
        
        # Clipboard check on focus
        self.bind("<FocusIn>", self.check_clipboard)

    def check_clipboard(self, event=None):
        try:
            content = self.clipboard_get()
            # Simple check if it looks like a URL and is different from current
            if content.startswith("http") and content != self.url_var.get():
                self.url_var.set(content)
                self.log(f"Auto-pasted from clipboard: {content}")
        except:
            pass

    def on_url_change(self, *args):
        """Auto-detects mode and triggers analysis."""
        url = self.url_var.get().strip()
        if not url: return

        # Cancel any pending analysis
        if self.analysis_timer:
            self.after_cancel(self.analysis_timer)

        # Mode switching logic
        if "instagram.com/p/" in url or "instagram.com/reel/" in url:
            if self.output_format.get() != "ig_photo":
                self.output_format.set("ig_photo")
                self.log("Auto-switched to IG Photo mode.")
        else:
            # Switch back to Video mode if currently in IG Photo mode
            if self.output_format.get() == "ig_photo":
                self.output_format.set("mp4")
                self.log("Auto-switched to Video mode.")
            
            # Debounce auto-analysis: wait 800ms after user stops typing/pasting
            if url != self.last_analyzed_url:
                self.analysis_timer = self.after(800, self.start_analysis)

    def on_mode_change(self, *args):
        if self.output_format.get() == "ig_photo":
            self.download_button["state"] = "normal"
            self.analyze_button["state"] = "disabled"
        else:
            if not self.video_formats and not self.audio_formats:
                self.download_button["state"] = "disabled"
            self.analyze_button["state"] = "normal"

    def on_closing(self):
        try:
            self.save_config()
        except:
            pass
        self.destroy()
        # Force exit to ensure all threads are killed, especially on macOS
        sys.exit(0)

    def reset_ui(self):
        self.url_entry.delete(0, tk.END)
        self.video_format_combo.set('')
        self.video_format_combo['values'] = []
        self.audio_format_combo.set('')
        self.audio_format_combo['values'] = []
        self.progress_var.set(0)
        self.video_formats = []
        self.audio_formats = []
        self.last_analyzed_url = ""
        self.log("Ready.")
        self.on_mode_change()

    def load_config(self):
        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)
                path = config.get("save_path")
                if path and os.path.isdir(path):
                    self.save_path_var.set(path)
                else:
                    self.save_path_var.set(os.path.join(os.path.expanduser("~"), "Downloads"))
        except:
            self.save_path_var.set(os.path.join(os.path.expanduser("~"), "Downloads"))

    def save_config(self):
        config = {"save_path": self.save_path_var.get()}
        with open(self.config_path, "w") as f:
            json.dump(config, f)
            
    def select_save_directory(self):
        path = filedialog.askdirectory(initialdir=self.save_path_var.get())
        if path:
            self.save_path_var.set(path)
            self.log(f"Save directory: {path}")

    def log(self, message):
        """Buffers log messages to prevent UI freezing."""
        self.log_queue.append(message.strip())
        if not self.is_log_updating:
            self.is_log_updating = True
            self.after(self.update_log_interval, self.process_log_queue)

    def process_log_queue(self):
        """Updates the UI with buffered messages."""
        if self.log_queue:
            # Batch insert
            messages = "\n".join(self.log_queue)
            self.log_queue = [] # Clear buffer
            
            self.output_text.insert(tk.END, messages + "\n")
            self.output_text.see(tk.END)
        
        # Keep checking if there are more messages coming in (if process still running)
        # But if queue is empty, we can stop the loop until next log call to save CPU
        self.is_log_updating = False
        if self.log_queue: # If new messages arrived while processing
             self.is_log_updating = True
             self.after(self.update_log_interval, self.process_log_queue)

    def start_analysis(self):
        url = self.url_var.get().strip()
        if not url: return
        if self.output_format.get() == "ig_photo":
            return
            
        self.last_analyzed_url = url
        self.analyze_button["state"] = "disabled"
        self.download_button["state"] = "disabled"
        self.log("Auto-analyzing...")
        threading.Thread(target=self.analyze_url, daemon=True).start()

    def analyze_url(self):
        url = self.url_entry.get()
        if not url:
            self.analyze_button["state"] = "normal"
            return
        
        if "threads.com" in url:
            url = url.replace("threads.com", "threads.net")
            self.url_var.set(url) # Update variable instead of widget directly

        try:
            si = None
            if sys.platform == "win32":
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE

            command = [self.yt_dlp_path, "--dump-json", url, "--js-runtimes", "node", "--playlist-items", "1"]
            process = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', check=False, startupinfo=si, errors='replace') 

            if not process.stdout.strip():
                raise Exception("No data received. URL might be private or invalid.")

            info = json.loads(process.stdout.strip().split('\n')[0])
            self.winfo_toplevel().title(info.get('title', 'Video Downloader'))
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
                elif f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    desc = f"Container: {f.get('height', 'N/A')}p ({f.get('ext')}) - {size_mb}"
                    self.video_formats.append((desc, f['format_id']))

            self.video_format_combo['values'] = [v[0] for v in self.video_formats]
            self.audio_format_combo['values'] = [a[0] for a in self.audio_formats]
            if self.video_formats: self.video_format_combo.set(self.video_formats[-1][0])
            if self.audio_formats: self.audio_format_combo.set(self.audio_formats[-1][0])
            self.log(f"Analysis complete: {info.get('title', 'Unknown')}")
            self.download_button["state"] = "normal"
        except Exception as e:
            self.log(f"Analysis error: {e}")
            # messagebox.showerror("Error", f"Analysis error: {e}") # Suppress popup for auto-analysis to avoid annoyance
        finally:
            self.analyze_button["state"] = "normal"

    def download_content(self):
        mode = self.output_format.get()
        if mode == "ig_photo":
            threading.Thread(target=self.download_ig_photo, daemon=True).start()
        else:
            self.download_video()

    def download_ig_photo(self):
        url = self.url_entry.get()
        save_dir = self.save_path_var.get()
        if not save_dir:
            messagebox.showerror("Error", "Select a save directory.")
            return

        self.log("Starting IG Photo download...")
        self.download_button["state"] = "disabled"
        self.analyze_button["state"] = "disabled"
        self.progress_var.set(10)

        try:
            L = instaloader.Instaloader(
                download_pictures=True, download_videos=False, 
                download_video_thumbnails=False, download_geotags=False, 
                download_comments=False, save_metadata=False, compress_json=False
            )
            match = re.search(r"instagram\.com/(?:p|reel)/([^/?#&]+)", url)
            if not match:
                raise ValueError("Could not extract shortcode.")
            
            shortcode = match.group(1)
            self.log(f"Shortcode: {shortcode}")
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            
            original_cwd = os.getcwd()
            try:
                os.chdir(save_dir)
                self.log(f"Downloading to: {os.path.join(save_dir, shortcode)}")
                L.download_post(post, target=shortcode)
            finally:
                os.chdir(original_cwd)
            
            self.progress_var.set(100)
            self.log("Download complete!")
            messagebox.showinfo("Success", f"Photos saved to folder:\n{os.path.join(save_dir, shortcode)}")
            self.after_idle(self.reset_ui)
        except Exception as e:
            self.log(f"Error: {e}")
            messagebox.showerror("Error", f"Failed: {e}")
            self.progress_var.set(0)
        finally:
            self.download_button["state"] = "normal"
            self.on_mode_change()

    def download_video(self):
        url = self.url_entry.get()
        output_format = self.output_format.get()
        is_mp3 = output_format == 'mp3'
        video_desc = self.video_format_combo.get()
        audio_desc = self.audio_format_combo.get()

        if not is_mp3:
            if not video_desc and not audio_desc:
                 if self.video_formats: video_id = self.video_formats[-1][1]
                 else: messagebox.showerror("Error", "Analyze URL first."); return
            if video_desc: video_id = next((v[1] for v in self.video_formats if v[0] == video_desc), None)

        if audio_desc: audio_id = next((a[1] for a in self.audio_formats if a[0] == audio_desc), None)

        title = self.winfo_toplevel().title()
        sanitized_title = "".join(c for c in title if c.isalnum() or c in (' ', '.', '_')).rstrip()
        save_path = filedialog.asksaveasfilename(
            initialdir=self.save_path_var.get(),
            initialfile=f"{sanitized_title}.{output_format}",
            defaultextension=f".{output_format}",
            filetypes=[(f"{output_format.upper()} Files", f"*.{output_format}"), ("All Files", "*.*")]
        )

        if not save_path: return

        command = [self.yt_dlp_path]
        if is_mp3:
            if audio_id: command.extend(["-f", audio_id])
            else: command.extend(["-f", "ba/b"])
            command.extend(["-x", "--audio-format", "mp3"])
        else:
            if video_id and audio_id: command.extend(["-f", f"{video_id}+{audio_id}"])
            elif video_id: command.extend(["-f", f"{video_id}"])
            if output_format in ['mp4', 'mkv']: command.extend(["--merge-output-format", output_format])

        command.extend([
            "--ffmpeg-location", self.ffmpeg_path, "-o", save_path, 
            url, "--progress", "--newline", "--js-runtimes", "node", "--no-playlist"
        ])
        
        self.progress_var.set(0)
        self.download_button["state"] = "disabled"
        self.analyze_button["state"] = "disabled"
        self.browse_button["state"] = "disabled"
        self.log(f"Starting download...")
        threading.Thread(target=self.run_download_process, args=(command,), daemon=True).start()

    def run_download_process(self, command):
        try:
            si = None
            if sys.platform == "win32":
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', startupinfo=si)
            progress_regex = re.compile(r"[download]\s+([0-9.]+)%\s+of\s+.* at .* ETA ")
            for line in iter(process.stdout.readline, ''):
                self.log(line)
                match = progress_regex.search(line)
                if match: self.after_idle(self.progress_var.set, float(match.group(1)))
            process.stdout.close()
            if process.wait() == 0:
                self.after_idle(self.progress_var.set, 100)
                messagebox.showinfo("Success", "Download complete!")
                self.after_idle(self.reset_ui)
            else:
                self.after_idle(self.progress_var.set, 0)
                messagebox.showerror("Error", "Download failed.")
        except Exception as e:
            self.log(f"Error: {e}")
        finally:
            self.download_button["state"] = "normal"
            self.analyze_button["state"] = "normal"
            self.browse_button["state"] = "normal"
            self.on_mode_change()

if __name__ == "__main__":
    app = App()
    app.mainloop()
