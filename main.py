"""
Python GUI application to download audio from YouTube videos as MP3 files.
"""
import os
import logging
import threading
import requests
import tkinter as tk
from tkinter import messagebox, filedialog, PhotoImage, ttk
from PIL import ImageTk, Image
import yt_dlp
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
import re
import queue

logger = logging.getLogger(__name__)
logging.basicConfig(filename="app.log", level=logging.DEBUG, format="%(asctime)s:%(levelname)s:%(message)s")

class MyGUI:
    """
    class for the GUI and application logic
    """
    def __init__(self):
        self.root = tk.Tk()

        self.style = ttk.Style()
        self.style.configure("TProgressbar", troughcolor="white", background="#BFBFBF", thickness=10)
        

        # Set window title and size
        self.root.title("YouTube MP3 Downloader")
        self.root.geometry("450x600")
        self.root.configure(bg="#BFBFBF")
        
        # Make window resizable and set minimum size
        self.root.resizable(True, True)
        self.root.minsize(400, 500)

        # Set window icon
        # Load, resize, convert
        logo_img = Image.open("media/logo.png")
        logo_img = logo_img.resize((50, 50), Image.Resampling.LANCZOS)

        self.logo = ImageTk.PhotoImage(logo_img)

        # Set window icon
        self.root.iconphoto(False, self.logo)

        # Create main scrollable frame
        self.main_canvas = tk.Canvas(self.root, bg="#BFBFBF", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.main_canvas.yview)
        self.scrollable_frame = tk.Frame(self.main_canvas, bg="#BFBFBF")
        
        # Create the window in the canvas
        self.canvas_window = self.main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.main_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Pack the canvas and scrollbar
        self.main_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel scrolling
        self.main_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # Update scroll region and make frame expand to canvas width
        def on_frame_configure(event):
            self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        
        def on_canvas_configure(event):
            self.main_canvas.itemconfig(self.canvas_window, width=event.width)
        
        self.scrollable_frame.bind("<Configure>", on_frame_configure)
        self.main_canvas.bind("<Configure>", on_canvas_configure)
        
        # Shared Windows-95-style look, kept as one set of constants so every
        # widget in the form uses the same palette/spacing/relief consistently.
        BG = "#BFBFBF"
        BTN_BG = "#D4D0C8"
        ACCENT = "#000080"
        FONT_LABEL = ("Helvetica", 10, "bold")
        FONT_BUTTON = ("Helvetica", 12, "bold")
        FONT_BUTTON_SMALL = ("Helvetica", 11)
        GROUP_KW = dict(bg=BG, fg="black", relief="groove", bd=2, font=FONT_LABEL)
        SECTION_GAP = 10

        # Start building the UI inside the scrollable frame
        header_frame = tk.Frame(self.scrollable_frame, bg=BG)
        header_frame.pack(fill="both", expand=False, padx=20, pady=10)
        image_label = tk.Label(header_frame, image=self.logo, bg=BG)
        image_label.pack(side="top", anchor="center")
        tk.Label(header_frame, text="Convert2mp3", bg=BG, fg=ACCENT, font=("Helvetica", 15, "bold")).pack(side="top", anchor="center")

        self.download_directory = ""
        self.downloading = False
        self.cancel_download = False
        self.in_postprocessing = False
        self.update_queue = queue.Queue()

        # Create main content frame
        content_frame = tk.Frame(self.scrollable_frame, bg=BG)
        content_frame.pack(fill="both", expand=False, padx=20, pady=10)

        tk.Label(content_frame, text="Enter YouTube URL:", bg=BG, fg="black", font=FONT_LABEL).pack(pady=(0, 4), anchor="w")
        self.url_entry = tk.Entry(content_frame, width=50)
        self.url_entry.pack(pady=(0, SECTION_GAP))

        tk.Label(content_frame, text="Destination Folder:", bg=BG, fg="black", font=FONT_LABEL).pack(pady=(0, 4), anchor="w")
        self.destination_text = tk.Label(content_frame, width=60, text="please select a folder", font=("Helvetica", 10), relief="sunken", bg="white")
        self.destination_text.pack(pady=(0, 6))
        self.destination_button = tk.Button(content_frame, text="Select Folder", bg=BTN_BG, fg="black", relief="ridge", font=FONT_BUTTON_SMALL, command=self.set_destination_folder)
        self.destination_button.pack(pady=(0, SECTION_GAP))

        # Metadata group
        metadata_group = tk.LabelFrame(content_frame, text="Metadata (optional)", **GROUP_KW)
        metadata_group.pack(fill="x", pady=(0, SECTION_GAP))
        tk.Label(metadata_group, text="Artist:", bg=BG, fg="black").pack(pady=(6, 2), anchor="w", padx=8)
        self.artist_entry = tk.Entry(metadata_group, width=48)
        self.artist_entry.pack(pady=(0, 6), padx=8)
        tk.Label(metadata_group, text="Album:", bg=BG, fg="black").pack(pady=(0, 2), anchor="w", padx=8)
        self.album_entry = tk.Entry(metadata_group, width=48)
        self.album_entry.pack(pady=(0, 8), padx=8)

        # Audio quality group
        quality_group = tk.LabelFrame(content_frame, text="Audio Quality", **GROUP_KW)
        quality_group.pack(fill="x", pady=(0, SECTION_GAP))
        self.quality_var = tk.StringVar(value="128")
        for text, value in (("128 kbps", "128"), ("192 kbps", "192"), ("320 kbps", "320")):
            tk.Radiobutton(quality_group, text=text, variable=self.quality_var, value=value, bg=BG).pack(side="left", padx=8, pady=6)

        # Conversion speed group
        speed_group = tk.LabelFrame(content_frame, text="Conversion Speed", **GROUP_KW)
        speed_group.pack(fill="x", pady=(0, SECTION_GAP))
        self.conversion_speed = tk.StringVar(value="fast")
        for text, value in (("Fast", "fast"), ("Balanced", "balanced"), ("High Quality", "quality")):
            tk.Radiobutton(speed_group, text=text, variable=self.conversion_speed, value=value, bg=BG).pack(side="left", padx=8, pady=6)

        # Format preference + fast-download behaviour group (these two settings interact)
        format_group = tk.LabelFrame(content_frame, text="Format & Download Behavior", **GROUP_KW)
        format_group.pack(fill="x", pady=(0, SECTION_GAP))
        self.format_var = tk.StringVar(value="auto")
        format_radios = tk.Frame(format_group, bg=BG)
        format_radios.pack(fill="x", padx=8, pady=(6, 2))
        for text, value in (("Auto (Smart)", "auto"), ("Direct (Fast)", "direct"), ("HLS (Compatible)", "hls")):
            tk.Radiobutton(format_radios, text=text, variable=self.format_var, value=value, bg=BG).pack(side="left")
        self.fast_download = tk.BooleanVar(value=True)
        tk.Checkbutton(format_group, text="Fast Download (avoid HLS)", variable=self.fast_download,
                       bg=BG, selectcolor=BTN_BG).pack(anchor="w", padx=8, pady=(0, 8))

        # Authentication group (cookies)
        auth_group = tk.LabelFrame(content_frame, text="Authentication (optional)", **GROUP_KW)
        auth_group.pack(fill="x", pady=(0, SECTION_GAP))
        self.use_cookies = tk.BooleanVar(value=False)  # Default to False to avoid keychain requests
        tk.Checkbutton(auth_group, text="Use Browser Cookies (may require keychain access)",
                       variable=self.use_cookies, bg=BG, selectcolor=BTN_BG).pack(anchor="w", padx=8, pady=(6, 2))
        self.use_cookie_file = tk.BooleanVar(value=False)
        tk.Checkbutton(auth_group, text="Use Cookie File (manual export)",
                       variable=self.use_cookie_file, bg=BG, selectcolor=BTN_BG).pack(anchor="w", padx=8, pady=2)
        self.cookie_file_path = tk.StringVar()
        cookie_path_frame = tk.Frame(auth_group, bg=BG)
        cookie_path_frame.pack(fill="x", padx=8, pady=(2, 8))
        tk.Label(cookie_path_frame, text="Cookie File Path:", bg=BG, fg="black").pack(side="left")
        tk.Entry(cookie_path_frame, textvariable=self.cookie_file_path, width=26).pack(side="left", padx=5)
        tk.Button(cookie_path_frame, text="Browse", bg=BTN_BG, fg="black", relief="ridge", font=FONT_BUTTON_SMALL,
                  command=self.browse_cookie_file).pack(side="left")

        buttonframe = tk.Frame(content_frame, bg=BG)
        buttonframe.columnconfigure(0, weight=1)
        buttonframe.columnconfigure(1, weight=1)
        buttonframe.columnconfigure(2, weight=1)

        clear_button = tk.Button(buttonframe, text="Clear", bg=BTN_BG, fg="black", relief="ridge", font=FONT_BUTTON, command=self.clear)
        clear_button.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        check_formats_button = tk.Button(buttonframe, text="Check Formats", bg=BTN_BG, fg="black", relief="ridge", font=FONT_BUTTON, command=self.check_available_formats)
        check_formats_button.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        self.download_button = tk.Button(buttonframe, text="Download MP3", bg=BTN_BG, fg="black", relief="ridge", font=FONT_BUTTON, command=self.start_download)
        self.download_button.grid(row=0, column=2, sticky="ew", padx=5, pady=5)

        buttonframe.pack(fill="x", pady=(0, 6))

        # Add cancel button (inside content_frame, not root)
        self.cancel_button = tk.Button(content_frame, text="Cancel", bg="#FF6B6B", fg="white",
                                      relief="ridge", font=FONT_BUTTON,
                                      command=self.cancel_download_process)
        self.cancel_button.pack(pady=(0, SECTION_GAP))
        self.cancel_button.config(state="disabled")

        # Progress bar - determinate while downloading, indeterminate during conversion
        self.progressbar = ttk.Progressbar(content_frame, orient="horizontal", length=200, mode="determinate", style="TProgressbar")
        self.progressbar.pack(pady=(0, 6))

        # Add status label
        self.status_label = tk.Label(content_frame, text="Ready", bg=BG, fg="black")
        self.status_label.pack(pady=(0, 4))

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Start checking for updates from download thread
        self.root.after(100, self.check_queue)
        
        logger.info("Application started.")
        self.root.mainloop()
        
    def check_queue(self):
        """Check for updates from download thread"""
        try:
            while True:
                update = self.update_queue.get_nowait()
                if update['type'] == 'progress':
                    self.progressbar['value'] = update['value']
                elif update['type'] == 'status':
                    self.status_label.config(text=update['text'])
                elif update['type'] == 'mode':
                    if update['value'] == 'indeterminate':
                        self.progressbar.config(mode='indeterminate')
                        self.progressbar.start(10)
                    else:
                        self.progressbar.stop()
                        self.progressbar.config(mode='determinate')
                        self.progressbar['value'] = 0
                elif update['type'] == 'download_finished':
                    self.cancel_button.config(state="disabled")
                    self.download_button.config(state="normal")
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.check_queue)
    
    def update_progress(self, progress_type, **kwargs):
        """Thread-safe way to update UI"""
        self.update_queue.put({'type': progress_type, **kwargs})

    def is_valid_youtube_url(self, url):
        """Validate YouTube URL format"""
        youtube_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+',
            r'(?:https?://)?(?:www\.)?youtu\.be/[\w-]+',
            r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=[\w-]+'
        ]
        return any(re.match(pattern, url) for pattern in youtube_patterns)

    def sanitize_filename(self, filename):
        """Remove invalid characters from filename"""
        # Remove invalid characters for file systems
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        # Limit length
        if len(filename) > 200:
            filename = filename[:200]
        return filename

    def _finish_download_ui(self):
        """Reset progress bar, flags and buttons after a download attempt ends (success, failure, or cancel)"""
        self.in_postprocessing = False
        self.update_progress('mode', value='determinate')
        self.downloading = False
        self.cancel_download = False
        self.update_progress('download_finished')
        self.update_progress('status', text="Ready")

    def _build_ydl_opts(self, format_spec, client, skip_hls, common_opts, output_template,
                         quality, ffmpeg_preset, ffmpeg_threads, ffmpeg_loglevel):
        """Build a single yt-dlp options dict for one (client, format) download strategy"""
        opts = common_opts.copy()
        extractor_args = {'player_client': [client]}  # Try different client to avoid SABR streaming
        if skip_hls:
            extractor_args['skip'] = ['hls']
        opts['extractor_args'] = {'youtube': extractor_args}
        return {
            'format': format_spec,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': quality,
            }],
            'outtmpl': output_template,
            'postprocessor_args': ['-preset', ffmpeg_preset, '-threads', ffmpeg_threads, '-loglevel', ffmpeg_loglevel],
            'progress_hooks': [self.progress_hook],
            'verbose': True,
            **opts
        }

    def download_audio(self, video_url, output_folder="/Desktop/downloads", artist="Unknown", album="Unknown"):
        """
        Downloads the audio from a YouTube video as an MP3 file and sets metadata.
        
        :param video_url: URL of the YouTube video.
        :param output_folder: Folder to save the MP3 file.
        :param artist: Artist name to set in metadata.
        :param album: Album name to set in metadata.
        """
        # Check if output directory is writable
        try:
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
            # Test write access by creating a temporary file
            test_file = os.path.join(output_folder, ".test_write_access")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
        except PermissionError:
            error_msg = f"Permission denied: Cannot write to '{output_folder}'\n\nThis usually means:\n1. The folder is on a read-only drive\n2. You don't have write permissions\n3. The drive is not properly mounted\n\nTry selecting a different folder (like Desktop or Documents)."
            messagebox.showerror("Permission Error", error_msg)
            logger.error(f"Permission denied for output folder: {output_folder}")
            return
        except Exception as e:
            error_msg = f"Cannot access output folder '{output_folder}': {str(e)}\n\nPlease select a different folder."
            messagebox.showerror("Folder Error", error_msg)
            logger.error(f"Cannot access output folder {output_folder}: {e}")
            return

        quality = self.quality_var.get()
        output_template = f'{output_folder}/%(title)s.%(ext)s'

        # Set FFmpeg settings based on conversion speed preference
        if self.conversion_speed.get() == "fast":
            ffmpeg_preset = "ultrafast"
            ffmpeg_threads = "0"  # Use all available CPU cores
            ffmpeg_loglevel = "error"  # Minimal logging for speed
        elif self.conversion_speed.get() == "balanced":
            ffmpeg_preset = "veryfast"
            ffmpeg_threads = "0"
            ffmpeg_loglevel = "warning"
        else:  # quality
            ffmpeg_preset = "fast"
            ffmpeg_threads = "0"
            ffmpeg_loglevel = "info"

        # Common yt-dlp options for all strategies
        common_opts = {
            'nocheckcertificate': True,
        }

        # Only add cookie support if user explicitly enables it
        if self.use_cookies.get():
            common_opts['cookiesfrombrowser'] = ('chrome',)
            logger.info("Using browser cookies for authentication")
        elif self.use_cookie_file.get():
            cookie_path = self.cookie_file_path.get()
            if cookie_path:
                if not os.path.isfile(cookie_path):
                    error_msg = f"Cookie file not found at: {cookie_path}\nPlease select a valid cookie file."
                    messagebox.showerror("Cookie Error", error_msg)
                    logger.error(f"Cookie file not found: {cookie_path}")
                    return
                common_opts['cookiefile'] = cookie_path
                logger.info(f"Using cookie file from: {cookie_path}")
            else:
                error_msg = "Please select a cookie file path."
                messagebox.showerror("Cookie Error", error_msg)
                logger.error("No cookie file path selected.")
                return
        else:
            logger.info("Skipping browser cookies and cookie file to avoid keychain access")

        # Define different client types to try (to avoid SABR streaming issues), and which
        # (clients, formats, skip_hls) phases to attempt based on the user's preferences.
        client_types = ['android', 'web', 'ios', 'tv_embedded']
        phases = []

        if self.format_var.get() == "direct" or (self.format_var.get() == "auto" and self.fast_download.get()):
            # Fast strategies that avoid HLS - try android and web first
            phases.append((client_types[:2], [
                'bestaudio[ext=mp3]/bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio[protocol!=m3u8]/bestaudio',
                'bestaudio[protocol!=m3u8]/bestaudio/best[height<=480]',
            ], True))

        if self.format_var.get() == "hls" or (self.format_var.get() == "auto" and not self.fast_download.get()):
            # Include HLS formats for compatibility - try all client types
            phases.append((client_types, ['bestaudio/best'], False))

        # Always add fallback strategies with different client types
        phases.append((client_types, [
            'bestaudio/best',
            'best[height<=720]/best',  # Try video formats too, then extract audio
        ], False))

        download_strategies = [
            self._build_ydl_opts(format_spec, client, skip_hls, common_opts, output_template,
                                  quality, ffmpeg_preset, ffmpeg_threads, ffmpeg_loglevel)
            for clients, format_specs, skip_hls in phases
            for client in clients
            for format_spec in format_specs
        ]

        for i, ydl_opts in enumerate(download_strategies):
            try:
                self.update_progress('status', text=f"Trying download method {i+1}...")
                logger.info(f"Attempting download with strategy {i+1}")
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=True)

                    if '_type' in info and info['_type'] == 'playlist':
                        for entry in info['entries']:
                            if self.cancel_download:
                                break
                            filename = ydl.prepare_filename(entry).replace(".webm", ".mp3").replace(".m4a", ".mp3").replace(".mp4", ".mp3")
                            audio = EasyID3(filename)
                            audio["artist"] = artist
                            audio["album"] = album
                            audio["title"] = entry.get("title", "Unknown Title")
                            audio.save()
                            thumbnail_path = self.save_thumbnail(entry, filename)
                    else:
                        filename = ydl.prepare_filename(info).replace(".webm", ".mp3").replace(".m4a", ".mp3").replace(".mp4", ".mp3")
                        # Add metadata using mutagen
                        audio = EasyID3(filename)
                        audio["artist"] = artist
                        audio["album"] = album
                        audio["title"] = info.get("title", "Unknown Title")
                        audio.save()

                        # Save the thumbnail
                        thumbnail_path = self.save_thumbnail(info, filename) 

                # If we get here, download was successful
                if not self.cancel_download:
                    self._finish_download_ui()
                    messagebox.showinfo("Success", f"Download complete with metadata and thumbnail!\nUsed method {i+1}")
                    logger.info(f"Successfully downloaded audio from {video_url} to {output_folder} using strategy {i+1}")
                    return
                    
            except yt_dlp.DownloadError as e:
                error_msg = f"Strategy {i+1} failed: {str(e)}"
                if "audio conversion failed" in str(e).lower():
                    error_msg += "\n\nThis usually means FFmpeg couldn't convert the audio format."
                elif "permission denied" in str(e).lower() or "unable to create directory" in str(e).lower():
                    error_msg += "\n\nThis is a permission issue. Try selecting a different folder."
                elif "sign in to confirm you're not a bot" in str(e).lower() or "authentication" in str(e).lower():
                    error_msg += "\n\nYouTube is asking for authentication. This usually means:\n1. The video requires age verification\n2. YouTube thinks you're a bot\n3. The video has restricted access\n\nTry:\n1. A different video\n2. Using a different YouTube account\n3. Waiting a bit before trying again"
                elif "no formats found" in str(e).lower() or "only images are available" in str(e).lower():
                    error_msg += "\n\nNo downloadable formats found. This might be:\n1. A private/restricted video\n2. A live stream that ended\n3. A region-restricted video\n4. A video with only images (no audio/video content)"
                elif "requested format is not available" in str(e).lower():
                    error_msg += "\n\nThe requested audio format is not available for this video.\nThis usually means:\n1. The video has no audio content\n2. Only images are available\n3. The video format is restricted\n\nTry:\n1. A different video with audio content\n2. Check if the video actually has sound"
                logger.warning(f"Download strategy {i+1} failed: {e}")
                
                if i == len(download_strategies) - 1:  # Last strategy
                    error_msg += "\n\nAll download methods failed. Try:\n1. Check if the video has audio content\n2. Try a different video\n3. Check available disk space\n4. Verify FFmpeg installation\n5. Try a different output folder\n6. Wait a bit before trying again (YouTube rate limiting)\n7. This video might only have images (no audio)"
                    messagebox.showerror("Download Error", error_msg)
                    logger.error(f"All download strategies failed for {video_url}")
                else:
                    continue  # Try next strategy
                    
            except Exception as e:
                error_msg = f"Strategy {i+1} failed with unexpected error: {str(e)}"
                if "permission" in str(e).lower():
                    error_msg += "\n\nThis appears to be a permission issue. Try selecting a different folder."
                elif "authentication" in str(e).lower() or "bot" in str(e).lower():
                    error_msg += "\n\nThis appears to be an authentication issue. Try a different video or wait before trying again."
                logger.warning(f"Unexpected error with strategy {i+1}: {e}")
                
                if i == len(download_strategies) - 1:  # Last strategy
                    error_msg += "\n\nAll download methods failed. This might be due to:\n- Unsupported audio format\n- Corrupted download\n- Insufficient disk space\n- Permission issues\n- YouTube authentication issues"
                    messagebox.showerror("Error", error_msg)
                    logger.error(f"All download strategies failed for {video_url}")
                else:
                    continue  # Try next strategy
                    
        # Cleanup after all strategies are tried
        self._finish_download_ui()

    def progress_hook(self, d):
        """Progress hook for yt-dlp to update progress bar"""
        if d['status'] == 'downloading':
            if self.in_postprocessing:
                self.in_postprocessing = False
                self.update_progress('mode', value='determinate')
            if 'total_bytes' in d and d['total_bytes']:
                percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                self.update_progress('progress', value=percent)
                self.update_progress('status', text=f"Downloading... {percent:.1f}%")
            elif 'total_bytes_estimate' in d and d['total_bytes_estimate']:
                percent = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
                self.update_progress('progress', value=percent)
                self.update_progress('status', text=f"Downloading... {percent:.1f}%")
            elif 'downloaded_bytes' in d:
                # For HLS or unknown total size, show downloaded amount
                downloaded_mb = d['downloaded_bytes'] / (1024 * 1024)
                self.update_progress('status', text=f"Downloading... {downloaded_mb:.1f} MB")
        elif d['status'] in ('finished', 'postprocessing'):
            # yt-dlp/ffmpeg don't expose real conversion progress, so show an
            # indeterminate (bouncing) bar instead of a misleading fixed value.
            if not self.in_postprocessing:
                self.in_postprocessing = True
                self.update_progress('mode', value='indeterminate')
            text = "Converting to MP3..." if d['status'] == 'finished' else "Processing audio..."
            self.update_progress('status', text=text)

    def save_thumbnail(self, info, filename):
        """
        Downloads a thumbnail image from a URL and saves it to the selected download folder.

        :param info: Dictionary containing video information (including the thumbnail URL).
        :return: Path to the saved thumbnail file (or None if failed).
        """
        
        try:
            if "thumbnail" in info:
                thumbnail_url = info["thumbnail"]
                thumbnail_name = f"{info['title']}.jpg"
                thumbnail_name = thumbnail_name.replace(" ", "_")
                thumbnail_path = os.path.join(self.download_directory, thumbnail_name)

                thumbnail = requests.get(thumbnail_url, stream=True)
                if thumbnail.status_code == 200:
                    with open(thumbnail_path, "wb") as file:
                        for chunk in thumbnail.iter_content(1024):
                            file.write(chunk)
                    
                    # Resize the image to max 500x500 pixels
                    img = Image.open(thumbnail_path)
                    img.thumbnail((500, 500))
                    img.save(thumbnail_path, "JPEG", quality=85)

                    logger.info(f"Thumbnail saved and resized: {thumbnail_path}")
                    audio_file = MP3(filename, ID3=ID3)
                    # Ensure the file has ID3 tags
                    try:
                        audio_file.add_tags()
                    except Exception:
                        pass
                    with open(thumbnail_path, "rb") as img:
                        audio_file.tags.add(
                            APIC(
                                encoding=3, 
                                mime="image/jpeg",
                                type=3,  
                                desc="Cover",
                                data=img.read(),
                            )
                        )
                    audio_file.save(v2_version=3)
                    os.remove(thumbnail_path)
        except Exception as e:
            logger.error(f"Failed to save thumbnail: {e}")
            return None

                


    def set_destination_folder(self):
        """
        Clearing the entry fields
        """
        self.download_directory = filedialog.askdirectory()
        self.destination_text.config(text=self.download_directory)

    def start_download(self):
        """
        starts the download process
        """
        video_url = self.url_entry.get().strip()
        artist = self.artist_entry.get().strip()
        album = self.album_entry.get().strip()
        
        if not video_url:
            messagebox.showwarning("Warning", "Please enter a YouTube URL.")
            return
            
        if not self.is_valid_youtube_url(video_url):
            messagebox.showerror("Error", "Please enter a valid YouTube URL.")
            return
            
        if not self.download_directory:
            messagebox.showerror("Error", "Please select a destination folder.")
            return

        logging.info(f"Downloading audio from {video_url} to {self.download_directory}")
        self.progressbar['value'] = 0
        self.downloading = True
        self.cancel_download = False
        self.cancel_button.config(state="normal")
        self.download_button.config(state="disabled")
        self.update_progress('status', text="Starting download...")
        download_thread = threading.Thread(target=self.download_audio, args=(video_url, self.download_directory, artist, album))
        download_thread.start() 
            
    def cancel_download_process(self):
        """Cancel ongoing download"""
        self.cancel_download = True
        self.downloading = False
        self.cancel_button.config(state="disabled")
        self.download_button.config(state="normal")
        self.update_progress('status', text="Download cancelled")
        self.progressbar.stop()
        self.progressbar['value'] = 0

    def clear(self):
        """
        clear the entry fields
        """
        self.artist_entry.delete(0, tk.END)
        self.album_entry.delete(0, tk.END)
        self.url_entry.delete(0, tk.END)
        self.destination_text.config(text="please select a folder")

    def on_closing(self):
        """
        Confirm the user wants to quit the application.
        """
        if messagebox.askyesno("Quit?", "Are you sure you want to quit?"):
            self.root.destroy()
            logger.info("Application closed on user request.")

    def check_available_formats(self):
        """Check what formats are available for the given URL"""
        video_url = self.url_entry.get().strip()
        
        if not video_url:
            messagebox.showwarning("Warning", "Please enter a YouTube URL first.")
            return
            
        if not self.is_valid_youtube_url(video_url):
            messagebox.showerror("Error", "Please enter a valid YouTube URL.")
            return
        
        # Show checking status
        self.status_label.config(text="Checking available formats...")
        self.progressbar['value'] = 0
        
        # Run format check in separate thread
        check_thread = threading.Thread(target=self._check_formats_worker, args=(video_url,))
        check_thread.start()
    
    def _check_formats_worker(self, video_url):
        """Worker thread to check available formats"""
        try:
            # Try different client types to see which one works best
            client_types = ['android', 'web', 'ios', 'tv_embedded']
            all_formats_info = []
            
            for client in client_types:
                # Basic yt-dlp options for format checking
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': False,
                    'extract_flat': False,
                    'extractor_args': {
                        'youtube': {
                            'player_client': [client],
                        }
                    }
                }
                
                # Add cookies if enabled
                if self.use_cookies.get():
                    ydl_opts['cookiesfrombrowser'] = ('chrome',)
                elif self.use_cookie_file.get():
                    cookie_path = self.cookie_file_path.get()
                    if cookie_path:
                        if not os.path.isfile(cookie_path):
                            error_msg = f"Cookie file not found at: {cookie_path}\nPlease select a valid cookie file."
                            messagebox.showerror("Cookie Error", error_msg)
                            logger.error(f"Cookie file not found for format check: {cookie_path}")
                            return
                        ydl_opts['cookiefile'] = cookie_path
                        logger.info(f"Using cookie file for format check: {cookie_path}")
                    else:
                        error_msg = "Please select a cookie file path for format check."
                        messagebox.showerror("Cookie Error", error_msg)
                        logger.error("No cookie file path selected for format check.")
                        return
                else:
                    logger.info(f"Checking formats with {client} client (no cookies)")
                
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        # Get video info without downloading
                        info = ydl.extract_info(video_url, download=False)
                        if info:
                            all_formats_info.append((client, info))
                except Exception as e:
                    logger.warning(f"Failed to get formats with {client} client: {e}")
                    continue
            
            # Use the first successful client's info, or try without client specification
            if not all_formats_info:
                # Fallback: try without client specification
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': False,
                    'extract_flat': False,
                }
                if self.use_cookies.get():
                    ydl_opts['cookiesfrombrowser'] = ('chrome',)
                elif self.use_cookie_file.get():
                    cookie_path = self.cookie_file_path.get()
                    if cookie_path and os.path.isfile(cookie_path):
                        ydl_opts['cookiefile'] = cookie_path
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=False)
                    if info:
                        all_formats_info.append(('default', info))
            
            if not all_formats_info:
                messagebox.showerror("Error", "Could not extract video information with any client type.")
                return
            
            # Use the first successful extraction
            client_used, info = all_formats_info[0]
                
            # Extract format information
            formats = info.get('formats', [])
            title = info.get('title', 'Unknown Title')
            duration = info.get('duration', 0)
            
            # Filter and categorize formats
            audio_formats = []
            video_formats = []
            other_formats = []
            
            for fmt in formats:
                format_id = fmt.get('format_id', 'N/A')
                ext = fmt.get('ext', 'N/A')
                filesize = fmt.get('filesize', 0)
                vcodec = fmt.get('vcodec', 'none')
                acodec = fmt.get('acodec', 'none')
                protocol = fmt.get('protocol', 'N/A')
                
                format_info = f"ID: {format_id}, Ext: {ext}, Size: {filesize/1024/1024:.1f}MB, Protocol: {protocol}"
                
                if acodec != 'none' and acodec != 'N/A':
                    audio_formats.append(format_info)
                elif vcodec != 'none' and vcodec != 'N/A':
                    video_formats.append(format_info)
                else:
                    other_formats.append(format_info)
            
            # Build result message
            result = f"Video: {title}\n"
            if duration > 0:
                result += f"Duration: {duration//60}:{duration%60:02d}\n"
            result += f"\n✅ Working Client: {client_used}\n"
            result += f"📁 Available Formats:\n"
            
            if audio_formats:
                result += f"\n🎵 Audio Formats ({len(audio_formats)}):\n"
                for fmt in audio_formats[:5]:  # Show first 5
                    result += f"  • {fmt}\n"
                if len(audio_formats) > 5:
                    result += f"  ... and {len(audio_formats)-5} more\n"
            else:
                result += "\n❌ No audio formats found!\n"
            
            if video_formats:
                result += f"\n🎬 Video Formats ({len(video_formats)}):\n"
                for fmt in video_formats[:3]:  # Show first 3
                    result += f"  • {fmt}\n"
                if len(video_formats) > 3:
                    result += f"  ... and {len(video_formats)-3} more\n"
            
            if other_formats:
                result += f"\n📄 Other Formats ({len(other_formats)}):\n"
                for fmt in other_formats[:3]:  # Show first 3
                    result += f"  • {fmt}\n"
            
            if not audio_formats and not video_formats:
                result += "\n⚠️  This video appears to have no downloadable audio or video content.\n"
                result += "It might be:\n"
                result += "• A slideshow with only images\n"
                result += "• A restricted/private video\n"
                result += "• A live stream that ended\n"
                result += "• Region-restricted content\n"
                result += f"\n💡 Tried clients: {', '.join([c for c, _ in all_formats_info])}"
            
            # Show result in a scrollable text box
            self.show_formats_result(result)
                    
        except Exception as e:
            error_msg = f"Error checking formats: {str(e)}"
            if "sign in to confirm you're not a bot" in str(e).lower():
                error_msg += "\n\nYouTube is blocking access. Try:\n1. Using browser cookies\n2. A different video\n3. Waiting before retrying"
            messagebox.showerror("Format Check Error", error_msg)
            logger.error(f"Format check failed: {e}")
        finally:
            self.status_label.config(text="Ready")
            self.progressbar['value'] = 0
    
    def show_formats_result(self, result_text):
        """Show the formats result in a new window"""
        # Create a new window
        result_window = tk.Toplevel(self.root)
        result_window.title("Available Formats")
        result_window.geometry("600x500")
        result_window.configure(bg="#BFBFBF")
        
        # Add title
        title_label = tk.Label(result_window, text="Video Format Analysis", 
                              bg="#BFBFBF", fg="#000080", font=("Helvetica", 14, "bold"))
        title_label.pack(pady=10)
        
        # Add scrollable text area
        text_frame = tk.Frame(result_window, bg="#BFBFBF")
        text_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        text_widget = tk.Text(text_frame, wrap="word", bg="white", fg="black", 
                             font=("Courier", 10), height=20)
        scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Insert the result text
        text_widget.insert("1.0", result_text)
        text_widget.config(state="disabled")  # Make read-only
        
        # Add close button
        close_button = tk.Button(result_window, text="Close", bg="#D4D0C8", fg="black",
                                relief="ridge", font=("Helvetica", 12, "bold"),
                                command=result_window.destroy)
        close_button.pack(pady=10)

    def browse_cookie_file(self):
        """
        Opens a file dialog to select a cookie file.
        """
        file_path = filedialog.askopenfilename(
            title="Select Cookie File",
            filetypes=(("Cookie files", "*.txt"), ("All files", "*.*"))
        )
        if file_path:
            self.cookie_file_path.set(file_path)
            logger.info(f"Selected cookie file: {file_path}")

    def _on_mousewheel(self, event):
        """
        Handles mouse wheel scrolling for the canvas.
        """
        self.main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

myapp = MyGUI()
