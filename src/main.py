import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import subprocess
import json
import os
import threading
import sys
import re
import instaloader
import urllib.request
import webbrowser
from PIL import Image, ImageTk, ImageOps, ImageDraw
from io import BytesIO

CURRENT_VERSION = "v1.3.0"
GITHUB_REPO = "RyuOuO/YT-Downloder"

class App(ttk.Window):
    def __init__(self):
        super().__init__(themename="darkly")
        self.title(f"Universal Downloader {CURRENT_VERSION}")
        self.geometry("900x800")
        
        # --- High DPI Support ---
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass

        # --- Config & Paths ---
        self.user_home = os.path.expanduser("~")
        self.config_path = os.path.join(self.user_home, ".yt_downloader_config.json")

        if getattr(sys, 'frozen', False):
            self.base_path = sys._MEIPASS
        else:
            self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        exe_ext = ".exe" if sys.platform == "win32" else ""
        self.yt_dlp_path = os.path.join(self.base_path, "bin", f"yt-dlp{exe_ext}")
        self.ffmpeg_path = os.path.join(self.base_path, "bin")

        self.video_formats = []
        self.audio_formats = []
        self.last_analyzed_url = ""
        self.analysis_timer = None
        self.thumbnail_image = None
        
        # --- UI Construction ---
        self.create_widgets()
        
        # --- Init ---
        self.load_config()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.after(1000, self.check_for_updates)
        self.bind("<FocusIn>", self.check_clipboard)

        # Log buffering
        self.log_queue = []
        self.is_log_updating = False
        self.update_log_interval = 100

    def create_widgets(self):
        # Custom Fonts
        title_font = ("Helvetica", 16, "bold")
        header_font = ("Helvetica", 11, "bold")
        
        # Main Container
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=BOTH, expand=True)

        # --- Header ---
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=X, pady=(0, 20))
        ttk.Label(header_frame, text="⬇ Universal Downloader", font=title_font, bootstyle="inverse-primary").pack(side=LEFT, padx=5, ipady=5, ipadx=10)
        ttk.Label(header_frame, text="YouTube • Instagram • Facebook • Threads", font=("Helvetica", 9), bootstyle="secondary").pack(side=LEFT, padx=10)

        # --- Input Section ---
        input_group = ttk.Labelframe(main_frame, text=" 🔗 Link Input ", padding=15, bootstyle="info")
        input_group.pack(fill=X, pady=(0, 15))
        
        self.url_var = tk.StringVar()
        self.url_var.trace("w", self.on_url_change)
        
        url_container = ttk.Frame(input_group)
        url_container.pack(fill=X)
        
        url_entry = ttk.Entry(url_container, textvariable=self.url_var, font=("Consolas", 10))
        url_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 10))
        
        self.analyze_button = ttk.Button(url_container, text="🔍 Analyze", command=self.start_analysis, bootstyle="info", width=10)
        self.analyze_button.pack(side=LEFT)

        # --- Settings & Preview Grid ---
        grid_frame = ttk.Frame(main_frame)
        grid_frame.pack(fill=BOTH, expand=True, pady=(0, 15))
        grid_frame.columnconfigure(0, weight=3) # Left Settings
        grid_frame.columnconfigure(1, weight=2) # Right Preview

        # Left Column: Settings
        settings_frame = ttk.Labelframe(grid_frame, text=" ⚙️ Settings ", padding=15, bootstyle="default")
        settings_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # Mode Selection
        ttk.Label(settings_frame, text="Download Mode:", font=header_font).pack(anchor="w", pady=(0, 5))
        self.output_format = tk.StringVar(value="mp4")
        self.output_format.trace("w", self.on_mode_change)
        
        mode_box = ttk.Frame(settings_frame)
        mode_box.pack(fill=X, pady=(0, 15))
        
        # Custom styled radio buttons
        modes = [(" Video (MP4)", "mp4"), (" Video (MKV)", "mkv"), (" Audio (MP3)", "mp3"), (" IG Photo", "ig_photo")]
        for text, val in modes:
            ttk.Radiobutton(mode_box, text=text, variable=self.output_format, value=val, bootstyle="info-toolbutton").pack(side=LEFT, fill=X, expand=True, padx=2)

        # Quality Selection
        ttk.Label(settings_frame, text="Quality:", font=header_font).pack(anchor="w", pady=(0, 5))
        self.video_format_combo = ttk.Combobox(settings_frame, state="readonly", bootstyle="primary")
        self.video_format_combo.pack(fill=X, pady=(0, 5))
        self.video_format_combo.set("Waiting for analysis...")
        
        self.audio_format_combo = ttk.Combobox(settings_frame, state="readonly", bootstyle="secondary")
        self.audio_format_combo.pack(fill=X, pady=(0, 15))
        self.audio_format_combo.set("Waiting for analysis...")

        # Subtitles & Extras
        ttk.Label(settings_frame, text="Extras:", font=header_font).pack(anchor="w", pady=(0, 5))
        extras_box = ttk.Frame(settings_frame)
        extras_box.pack(fill=X)
        
        self.embed_subs_var = tk.BooleanVar(value=False)
        self.subs_check = ttk.Checkbutton(extras_box, text="Embed Subtitles", variable=self.embed_subs_var, command=self.on_subs_change, bootstyle="round-toggle")
        self.subs_check.pack(side=LEFT)
        
        self.sub_lang_var = tk.StringVar()
        self.sub_lang_combo = ttk.Combobox(extras_box, textvariable=self.sub_lang_var, state="readonly", width=15)
        self.sub_lang_combo.pack(side=LEFT, padx=10)
        self.sub_lang_combo.set("No Subtitles")
        
        # Save Location
        ttk.Label(settings_frame, text="Save Location:", font=header_font).pack(anchor="w", pady=(15, 5))
        save_box = ttk.Frame(settings_frame)
        save_box.pack(fill=X)
        
        self.save_path_var = tk.StringVar()
        ttk.Entry(save_box, textvariable=self.save_path_var, state="readonly", bootstyle="secondary").pack(side=LEFT, fill=X, expand=True)
        ttk.Button(save_box, text="📂", width=3, command=self.select_save_directory, bootstyle="secondary-outline").pack(side=LEFT, padx=(5, 0))

        # Right Column: Preview
        preview_frame = ttk.Labelframe(grid_frame, text=" 🖼️ Preview ", padding=10, bootstyle="warning")
        preview_frame.grid(row=0, column=1, sticky="nsew")
        
        self.thumb_label = ttk.Label(preview_frame, text="No Media Selected", anchor="center", font=("Helvetica", 10))
        self.thumb_label.pack(fill=BOTH, expand=True)

        # --- Bottom Section ---
        self.download_button = ttk.Button(main_frame, text="🚀 START DOWNLOAD", command=self.download_content, state="disabled", bootstyle="success-lg", width=30)
        self.download_button.pack(pady=10)

        # Progress
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=X)
        self.progress_var = tk.DoubleVar()
        self.progressbar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100, bootstyle="striped-success")
        self.progressbar.pack(fill=X)

        # Log
        log_frame = ttk.Labelframe(main_frame, text="Log Output", padding=5, bootstyle="secondary")
        log_frame.pack(fill=BOTH, expand=True, pady=(5, 0))
        
        self.output_text = scrolledtext.ScrolledText(log_frame, height=8, font=("Consolas", 9), bg="#222", fg="#ddd", insertbackground="white")
        self.output_text.pack(fill=BOTH, expand=True)

    # --- Logic (Kept mostly same, adjusted for new widgets) ---
    # ... [Same helper methods as before: check_clipboard, load_thumbnail, etc.] ...
    
    def load_thumbnail(self, url):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as u:
                raw_data = u.read()
            image = Image.open(BytesIO(raw_data))
            
            # Smart Resize: fit into preview area while keeping aspect ratio
            target_w, target_h = 300, 250 
            image.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
            
            self.thumbnail_image = ImageTk.PhotoImage(image)
            self.thumb_label.configure(image=self.thumbnail_image, text="")
        except Exception as e:
            self.log(f"Thumbnail error: {e}")
            self.thumb_label.configure(image='', text="(No Preview)")

    # ... [Rest of logic: check_clipboard, on_url_change, on_mode_change, log, process_log_queue, load_config, save_config, select_save_directory, on_closing, check_for_updates, prompt_update, start_analysis, analyze_url, download_content, download_ig_photo, download_video, run_download_process] ...
    # I will inject the previous logic here to ensure completeness without typing it all out again if not needed, 
    # but since I'm overwriting the file, I must include EVERYTHING.

    def check_clipboard(self, event=None):
        try:
            content = self.clipboard_get()
            if (content.startswith("http") and 
                content != self.url_var.get() and 
                content != self.last_analyzed_url):
                self.url_var.set(content)
                self.log(f"Detected: {content}")
        except: pass

    def on_url_change(self, *args):
        url = self.url_var.get().strip()
        if not url: return
        if self.analysis_timer: self.after_cancel(self.analysis_timer)

        if "instagram.com/p/" in url or "instagram.com/reel/" in url:
            if self.output_format.get() != "ig_photo":
                self.output_format.set("ig_photo")
        else:
            if self.output_format.get() == "ig_photo":
                self.output_format.set("mp4")
            
            if url != self.last_analyzed_url:
                self.analysis_timer = self.after(800, self.start_analysis)

    def on_mode_change(self, *args):
        mode = self.output_format.get()
        if mode == "ig_photo":
            self.download_button["state"] = "normal"
            self.analyze_button["state"] = "disabled"
            self.subs_check["state"] = "disabled"
            self.sub_lang_combo["state"] = "disabled"
            self.video_format_combo.set("Not applicable")
            self.audio_format_combo.set("Not applicable")
        else:
            if not self.video_formats and not self.audio_formats:
                self.download_button["state"] = "disabled"
                self.video_format_combo.set("Waiting for analysis...")
                self.audio_format_combo.set("Waiting for analysis...")
            else:
                self.download_button["state"] = "normal"
                # Restore previous selections if available
                if self.video_formats: self.video_format_combo.current(0)
                
            self.analyze_button["state"] = "normal"
            self.subs_check["state"] = "normal"
            self.on_subs_change()

    def on_subs_change(self):
        if self.embed_subs_var.get() and self.sub_lang_combo['values']:
             if self.sub_lang_combo.get() != "No Subtitles":
                self.sub_lang_combo["state"] = "readonly"
        else:
            self.sub_lang_combo["state"] = "disabled"

    def log(self, message):
        self.log_queue.append(message.strip())
        if not self.is_log_updating:
            self.is_log_updating = True
            self.after(self.update_log_interval, self.process_log_queue)

    def process_log_queue(self):
        if self.log_queue:
            messages = "\n".join(self.log_queue)
            self.log_queue = []
            self.output_text.insert(tk.END, messages + "\n")
            self.output_text.see(tk.END)
        self.is_log_updating = False
        if self.log_queue:
             self.is_log_updating = True
             self.after(self.update_log_interval, self.process_log_queue)

    def load_config(self):
        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)
                path = config.get("save_path")
                if path and os.path.isdir(path):
                    self.save_path_var.set(path)
                else:
                    self.save_path_var.set(os.path.join(os.path.expanduser("~"), "Downloads"))
                self.embed_subs_var.set(config.get("embed_subs", False))
        except:
            self.save_path_var.set(os.path.join(os.path.expanduser("~"), "Downloads"))

    def save_config(self):
        config = {
            "save_path": self.save_path_var.get(),
            "embed_subs": self.embed_subs_var.get()
        }
        with open(self.config_path, "w") as f:
            json.dump(config, f)

    def select_save_directory(self):
        path = filedialog.askdirectory(initialdir=self.save_path_var.get())
        if path:
            self.save_path_var.set(path)

    def on_closing(self):
        try: self.save_config() # pylint: disable=no-member
        except: pass
        self.destroy()
        os._exit(0)

    def check_for_updates(self):
        def _check():
            try:
                url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
                with urllib.request.urlopen(url) as response:
                    data = json.loads(response.read().decode())
                    latest_version = data.get("tag_name", "")
                    if latest_version and latest_version != CURRENT_VERSION:
                        v1 = [int(x) for x in latest_version.lstrip('v').split('.')]
                        v2 = [int(x) for x in CURRENT_VERSION.lstrip('v').split('.')]
                        if v1 > v2:
                            self.after_idle(lambda: self.prompt_update(latest_version, data.get("html_url")))
            except: pass
        threading.Thread(target=_check, daemon=True).start()

    def prompt_update(self, version, url):
        if messagebox.askyesno("Update Available", f"New version {version} available!\nDownload now?"):
            webbrowser.open(url)

    def start_analysis(self):
        if self.output_format.get() == "ig_photo": return
        self.analyze_button["state"] = "disabled"
        self.download_button["state"] = "disabled"
        self.log("Auto-analyzing...")
        self.thumb_label.configure(image='', text="Loading...")
        threading.Thread(target=self.analyze_url, daemon=True).start()

    def analyze_url(self):
        url = self.url_entry.get()
        if not url:
            self.analyze_button["state"] = "normal"
            return
        
        if "threads.com" in url:
            url = url.replace("threads.com", "threads.net")
            self.url_var.set(url)

        try:
            si = None
            if sys.platform == "win32":
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE

            command = [self.yt_dlp_path, "--dump-json", url, "--js-runtimes", "node", "--playlist-items", "1"]
            process = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', check=False, startupinfo=si, errors='replace') 

            if not process.stdout.strip():
                raise Exception("No data received.")

            info = json.loads(process.stdout.strip().split('\n')[0])
            self.winfo_toplevel().title(f"Universal Downloader - {info.get('title', 'Unknown')}")
            
            thumb_url = info.get('thumbnail')
            if thumb_url: self.after_idle(self.load_thumbnail, thumb_url)

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
            
            subs = info.get('subtitles', {})
            auto_subs = info.get('automatic_captions', {})
            manual_subs_list = []
            auto_subs_list = []
            seen_langs = set()
            def process_subs(source, target_list, tag):
                for lang_code, sub_list in source.items():
                    name = sub_list[0].get('name', lang_code)
                    label = f"[{tag}] {lang_code} - {name}"
                    target_list.append(label)
            process_subs(subs, manual_subs_list, "Manual")
            process_subs(auto_subs, auto_subs_list, "Auto")
            manual_subs_list.sort()
            auto_subs_list.sort()
            available_subs = manual_subs_list + auto_subs_list

            if available_subs:
                self.sub_lang_combo['values'] = available_subs
                self.sub_lang_combo.set(available_subs[0])
                self.subs_check["state"] = "normal"
                if self.embed_subs_var.get():
                    self.sub_lang_combo["state"] = "readonly"
            else:
                self.sub_lang_combo.set("No Subtitles")
                self.sub_lang_combo['values'] = []
                self.sub_lang_combo["state"] = "disabled"
                self.subs_check["state"] = "disabled"

            self.log(f"Analysis complete: {info.get('title', 'Unknown')}")
            self.download_button["state"] = "normal"
        except Exception as e:
            self.log(f"Analysis error: {e}")
            self.thumb_label.configure(text="Error loading info")
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
        if not save_dir: messagebox.showerror("Error", "Select save dir."); return
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
            if not match: raise ValueError("No shortcode found.")
            shortcode = match.group(1)
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            cwd = os.getcwd()
            try:
                os.chdir(save_dir)
                L.download_post(post, target=shortcode)
            finally:
                os.chdir(cwd)
            self.progress_var.set(100)
            self.log("Complete!")
            messagebox.showinfo("Success", f"Saved to {shortcode}")
            self.after_idle(self.reset_ui)
        except Exception as e:
            self.log(f"Error: {e}")
            messagebox.showerror("Error", f"{e}")
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
                 else: messagebox.showerror("Error", "Analyze first."); return
            if video_desc: video_id = next((v[1] for v in self.video_formats if v[0] == video_desc), None)

        if audio_desc: audio_id = next((a[1] for a in self.audio_formats if a[0] == audio_desc), None)

        title = self.winfo_toplevel().title()
        sanitized_title = "".join(c for c in title if c.isalnum() or c in (' ', '.', '_')).rstrip()
        # Keep title clean but informative
        if "Universal Downloader" in title: sanitized_title = "Video" 
        
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

        if self.embed_subs_var.get():
            full_text = self.sub_lang_combo.get()
            if " - " in full_text:
                try:
                    prefix_part = full_text.split(" - ")[0]
                    lang_code = prefix_part.split(" ")[-1]
                    command.extend(["--write-subs", "--write-auto-subs", "--embed-subs", "--sub-langs", lang_code])
                except:
                    command.extend(["--write-subs", "--write-auto-subs", "--embed-subs", "--sub-langs", "all,-live_chat"])
            else:
                command.extend(["--write-subs", "--write-auto-subs", "--embed-subs", "--sub-langs", "all,-live_chat"])
            command.extend(["--sleep-subtitles", "2"])

        command.extend([
            "--ffmpeg-location", self.ffmpeg_path, "-o", save_path, 
            url, "--progress", "--newline", "--js-runtimes", "node", "--no-playlist"
        ])
        
        self.progress_var.set(0)
        self.download_button["state"] = "disabled"
        self.analyze_button["state"] = "disabled"
        self.log("Downloading...")
        threading.Thread(target=self.run_download_process, args=(command,), daemon=True).start()

    def run_download_process(self, command):
        try:
            si = None
            if sys.platform == "win32":
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', startupinfo=si)
            progress_regex = re.compile(r"[download]\s+([0-9.]+)%\s*")
            for line in iter(process.stdout.readline, ''):
                self.log(line)
                match = progress_regex.search(line)
                if match: self.after_idle(self.progress_var.set, float(match.group(1)))
            process.stdout.close()
            if process.wait() == 0:
                self.after_idle(self.progress_var.set, 100)
                messagebox.showinfo("Success", "Download complete!")
                self.after_idle(self.reset_ui)
                self.after_idle(lambda: self.thumb_label.configure(image='', text="No Thumbnail"))
            else:
                self.after_idle(self.progress_var.set, 0)
                messagebox.showerror("Error", "Download failed.")
        except Exception as e:
            self.log(f"Error: {e}")
        finally:
            self.download_button["state"] = "normal"
            self.analyze_button["state"] = "normal"
            self.on_mode_change()

if __name__ == "__main__":
    app = App()
    app.mainloop()
