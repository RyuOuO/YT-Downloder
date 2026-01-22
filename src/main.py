import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import subprocess
import json
import os
import threading
import sys
import re
import instaloader
import urllib.request
import webbrowser
from PIL import Image, ImageTk
from io import BytesIO

CURRENT_VERSION = "v1.2.2"
GITHUB_REPO = "RyuOuO/YT-Downloder"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Universal Video & IG Photo Downloader ({CURRENT_VERSION})")
        self.geometry("900x850")
        
        # --- High DPI Support ---
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass

        # --- Theme Config ---
        self.dark_mode = False
        self.colors = {
            "light": {"bg": "#f0f0f0", "fg": "black", "entry_bg": "white", "text_bg": "white"},
            "dark": {"bg": "#2d2d2d", "fg": "white", "entry_bg": "#404040", "text_bg": "#404040"}
        }

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

        # --- UI Construction ---
        self.create_widgets()
        
        # --- State ---
        self.video_formats = []
        self.audio_formats = []
        self.last_analyzed_url = ""
        self.analysis_timer = None
        self.thumbnail_image = None
        
        # --- Init ---
        self.load_config()
        self.apply_theme()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.after(1000, self.check_for_updates)
        self.bind("<FocusIn>", self.check_clipboard)

        # Log buffering
        self.log_queue = []
        self.is_log_updating = False
        self.update_log_interval = 100

    def create_widgets(self):
        # Top Frame
        top_frame = ttk.Frame(self)
        top_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        top_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(top_frame, text="Video/Photo URL:").grid(row=0, column=0, sticky="w")
        self.url_var = tk.StringVar()
        self.url_var.trace("w", self.on_url_change)
        self.url_entry = ttk.Entry(top_frame, textvariable=self.url_var)
        self.url_entry.grid(row=1, column=0, sticky="ew")
        
        btn_frame = ttk.Frame(top_frame)
        btn_frame.grid(row=1, column=1, padx=5)
        self.analyze_button = ttk.Button(btn_frame, text="Analyze", command=self.start_analysis)
        self.analyze_button.pack(side="left")
        self.theme_btn = ttk.Button(btn_frame, text="☀/🌙", width=5, command=self.toggle_theme)
        self.theme_btn.pack(side="left", padx=5)

        # Options
        opts_frame = ttk.Frame(top_frame)
        opts_frame.grid(row=2, column=0, columnspan=2, sticky="w", pady=5)
        
        self.embed_subs_var = tk.BooleanVar(value=False)
        self.subs_check = ttk.Checkbutton(opts_frame, text="Embed Subtitles", variable=self.embed_subs_var, command=self.on_subs_change)
        self.subs_check.pack(side="left", padx=5)
        
        self.sub_lang_var = tk.StringVar()
        self.sub_lang_combo = ttk.Combobox(opts_frame, textvariable=self.sub_lang_var, state="readonly", width=30)
        self.sub_lang_combo.pack(side="left", padx=5)
        self.sub_lang_combo.set("Analyze to see subtitles")
        self.sub_lang_combo["state"] = "disabled"

        # Save Directory
        ttk.Label(top_frame, text="Save to:").grid(row=3, column=0, sticky="w", pady=(5, 0))
        self.save_path_var = tk.StringVar()
        save_entry = ttk.Entry(top_frame, textvariable=self.save_path_var, state="readonly")
        save_entry.grid(row=4, column=0, sticky="ew")
        self.browse_button = ttk.Button(top_frame, text="Browse...", command=self.select_save_directory)
        self.browse_button.grid(row=4, column=1, padx=(5, 0))

        # Thumbnail Area
        self.thumb_label = ttk.Label(self, text="No Thumbnail", anchor="center")
        self.thumb_label.grid(row=1, column=0, columnspan=2, pady=10)

        # Format Selection
        formats_frame = ttk.LabelFrame(self, text="Format Selection")
        formats_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        formats_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(formats_frame, text="Video Quality:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.video_format_combo = ttk.Combobox(formats_frame, state="readonly")
        self.video_format_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(formats_frame, text="Audio Quality:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.audio_format_combo = ttk.Combobox(formats_frame, state="readonly")
        self.audio_format_combo.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(formats_frame, text="Mode:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.output_format = tk.StringVar(value="mp4")
        self.output_format.trace("w", self.on_mode_change)
        
        radio_frame = ttk.Frame(formats_frame)
        radio_frame.grid(row=2, column=1, sticky="w")
        ttk.Radiobutton(radio_frame, text="MP4", variable=self.output_format, value="mp4").pack(side="left", padx=5)
        ttk.Radiobutton(radio_frame, text="MKV", variable=self.output_format, value="mkv").pack(side="left", padx=5)
        ttk.Radiobutton(radio_frame, text="Audio (MP3)", variable=self.output_format, value="mp3").pack(side="left", padx=5)
        ttk.Radiobutton(radio_frame, text="IG Photo", variable=self.output_format, value="ig_photo").pack(side="left", padx=5)

        # Download Button
        self.download_button = ttk.Button(self, text="Download", command=self.download_content, state="disabled")
        self.download_button.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Progress & Log
        self.progress_var = tk.DoubleVar()
        self.progressbar = ttk.Progressbar(self, variable=self.progress_var, maximum=100)
        self.progressbar.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        self.output_text = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=12)
        self.output_text.grid(row=5, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
        self.grid_rowconfigure(5, weight=1)

    def on_subs_change(self):
        if self.embed_subs_var.get() and self.sub_lang_combo['values']:
             # Only enable if there are values to select (i.e. after analysis)
             if self.sub_lang_combo.get() != "No Subtitles":
                self.sub_lang_combo["state"] = "readonly"
        else:
            self.sub_lang_combo["state"] = "disabled"

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()

    def apply_theme(self):
        theme = "dark" if self.dark_mode else "light"
        c = self.colors[theme]
        
        self.configure(bg=c["bg"])
        style = ttk.Style()
        style.configure("TFrame", background=c["bg"])
        style.configure("TLabel", background=c["bg"], foreground=c["fg"])
        style.configure("TLabelframe", background=c["bg"], foreground=c["fg"])
        style.configure("TLabelframe.Label", background=c["bg"], foreground=c["fg"])
        style.configure("TRadiobutton", background=c["bg"], foreground=c["fg"])
        style.configure("TCheckbutton", background=c["bg"], foreground=c["fg"])
        
        self.output_text.configure(bg=c["text_bg"], fg=c["fg"], insertbackground=c["fg"])
        self.url_entry.configure(background=c["entry_bg"])

    def load_thumbnail(self, url):
        try:
            with urllib.request.urlopen(url) as u:
                raw_data = u.read()
            image = Image.open(BytesIO(raw_data))
            image.thumbnail((320, 180)) 
            self.thumbnail_image = ImageTk.PhotoImage(image)
            self.thumb_label.configure(image=self.thumbnail_image, text="")
        except Exception as e:
            self.log(f"Thumbnail error: {e}")
            self.thumb_label.configure(image='', text="(No Thumbnail)")

    def check_clipboard(self, event=None):
        try:
            content = self.clipboard_get()
            if (content.startswith("http") and 
                content != self.url_var.get() and 
                content != self.last_analyzed_url):
                self.url_var.set(content)
                self.log(f"Pasted: {content}")
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
        if self.output_format.get() == "ig_photo":
            self.download_button["state"] = "normal"
            self.analyze_button["state"] = "disabled"
            self.subs_check["state"] = "disabled"
            self.sub_lang_combo["state"] = "disabled"
        else:
            if not self.video_formats and not self.audio_formats:
                self.download_button["state"] = "disabled"
            self.analyze_button["state"] = "normal"
            self.subs_check["state"] = "normal"
            # Re-enable sub combo if checked and has values
            if self.embed_subs_var.get() and self.sub_lang_combo.get() != "No Subtitles" and self.sub_lang_combo.get() != "Analyze to see subtitles":
                 self.sub_lang_combo["state"] = "readonly"

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
                
                self.dark_mode = config.get("dark_mode", False)
                self.embed_subs_var.set(config.get("embed_subs", False))
        except:
            self.save_path_var.set(os.path.join(os.path.expanduser("~"), "Downloads"))

    def save_config(self):
        config = {
            "save_path": self.save_path_var.get(),
            "dark_mode": self.dark_mode,
            "embed_subs": self.embed_subs_var.get()
        }
        with open(self.config_path, "w") as f:
            json.dump(config, f)

    def select_save_directory(self):
        path = filedialog.askdirectory(initialdir=self.save_path_var.get())
        if path:
            self.save_path_var.set(path)
            self.log(f"Save directory: {path}")

    def on_closing(self):
        self.save_config()
        self.destroy()
        sys.exit(0)

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
            self.winfo_toplevel().title(info.get('title', 'Video Downloader'))
            
            # Thumbnail
            thumb_url = info.get('thumbnail')
            if thumb_url: self.after_idle(self.load_thumbnail, thumb_url)

            # Formats
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
            
            # --- Dynamic Subtitle Parsing ---
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
        save_path = filedialog.asksaveasfilename(
            initialdir=self.save_path_var.get(),
            initialfile=f"{sanitized_title}.{output_format}",
            defaultextension=f".{output_format}",
            filetypes=[(f"{output_format.upper()} Files", f"*.{output_format}"), ("All Files", "*.* אמיתי")]
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
            
            # Prevent rate limiting
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
