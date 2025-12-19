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
        
        # Start building the UI inside the scrollable frame
        frame = tk.Frame(self.scrollable_frame, bg="#BFBFBF")
        frame.pack(fill="both", expand=False, padx=20, pady=10)
        image_label = tk.Label(frame, image=self.logo, bg="#BFBFBF")
        image_label.pack(side="top", anchor="center")
        tk.Label(frame, text="Convert2mp3",bg="#BFBFBF", fg="#000080", font=("Helvetica", 15, "bold")).pack(side="top", anchor="center") 

        #tk.Label(self.root, image=self.logo, ).pack(pady=5, padx=5, anchor="nw", side="left")

        self.download_directory = ""
        self.downloading = False
        self.cancel_download = False
        self.update_queue = queue.Queue()

        # Create main content frame
        content_frame = tk.Frame(self.scrollable_frame, bg="#BFBFBF")
        content_frame.pack(fill="both", expand=False, padx=20, pady=10)

        tk.Label(content_frame, text="Enter YouTube URL:", bg="#BFBFBF", fg="black", font=("Helvetica", 10, "bold")).pack(pady=5, anchor="w")
        self.url_entry = tk.Entry(content_frame, width=50)
        self.url_entry.pack(pady=5)

        tk.Label(content_frame, text="Destination Folder:", bg="#BFBFBF", fg="black").pack(pady=5, anchor="w")
        self.destination_text = tk.Label(content_frame, width=60,text="please select a folder",font=("Helvetica", 10),  relief="sunken")
        self.destination_text.pack(pady=5)
        self.destination_button = tk.Button(content_frame, text="Select Folder", bg="#D4D0C8", fg="black", relief="ridge", font=("Helvetica", 11), command=self.set_destination_folder)
        self.destination_button.pack(pady=5)

        tk.Label(content_frame, text="Artist:", bg="#BFBFBF", fg="black").pack(pady=5, anchor="w")
        self.artist_entry = tk.Entry(content_frame, width=50)
        self.artist_entry.pack(pady=5)

        tk.Label(content_frame, text="Album:", bg="#BFBFBF", fg="black" ).pack(pady=5, anchor="w")
        self.album_entry = tk.Entry(content_frame, width=50)
        self.album_entry.pack(pady=5)

        # Add quality selection
        tk.Label(content_frame, text="Audio Quality:", bg="#BFBFBF", fg="black").pack(pady=5, anchor="w")
        self.quality_var = tk.StringVar(value="128")
        quality_frame = tk.Frame(content_frame, bg="#BFBFBF")
        quality_frame.pack(pady=5)
        
        tk.Radiobutton(quality_frame, text="128 kbps", variable=self.quality_var, value="128", bg="#BFBFBF").pack(side="left")
        tk.Radiobutton(quality_frame, text="192 kbps", variable=self.quality_var, value="192", bg="#BFBFBF").pack(side="left")
        tk.Radiobutton(quality_frame, text="320 kbps", variable=self.quality_var, value="320", bg="#BFBFBF").pack(side="left")

        # Add conversion speed preference
        tk.Label(content_frame, text="Conversion Speed:", bg="#BFBFBF", fg="black").pack(pady=5, anchor="w")
        self.conversion_speed = tk.StringVar(value="fast")
        conversion_frame = tk.Frame(content_frame, bg="#BFBFBF")
        conversion_frame.pack(pady=5)
        
        tk.Radiobutton(conversion_frame, text="Fast", variable=self.conversion_speed, value="fast", bg="#BFBFBF").pack(side="left")
        tk.Radiobutton(conversion_frame, text="Balanced", variable=self.conversion_speed, value="balanced", bg="#BFBFBF").pack(side="left")
        tk.Radiobutton(conversion_frame, text="High Quality", variable=self.conversion_speed, value="quality", bg="#BFBFBF").pack(side="left")

        # Add download speed preference
        speed_frame = tk.Frame(content_frame, bg="#BFBFBF")
        speed_frame.pack(pady=5)
        self.fast_download = tk.BooleanVar(value=True)
        tk.Checkbutton(speed_frame, text="Fast Download (avoid HLS)", variable=self.fast_download, 
                      bg="#BFBFBF", selectcolor="#D4D0C8").pack(side="left")
        
        # Add cookie usage preference
        cookie_frame = tk.Frame(content_frame, bg="#BFBFBF")
        cookie_frame.pack(pady=5)
        self.use_cookies = tk.BooleanVar(value=False)  # Default to False to avoid keychain requests
        tk.Checkbutton(cookie_frame, text="Use Browser Cookies (may require keychain access)", 
                      variable=self.use_cookies, bg="#BFBFBF", selectcolor="#D4D0C8").pack(side="left")
        
        # Add manual cookie file option
        cookie_file_frame = tk.Frame(content_frame, bg="#BFBFBF")
        cookie_file_frame.pack(pady=5)
        self.use_cookie_file = tk.BooleanVar(value=False)
        tk.Checkbutton(cookie_file_frame, text="Use Cookie File (manual export)", 
                      variable=self.use_cookie_file, bg="#BFBFBF", selectcolor="#D4D0C8").pack(side="left")
        
        # Cookie file path entry
        self.cookie_file_path = tk.StringVar()
        cookie_path_frame = tk.Frame(content_frame, bg="#BFBFBF")
        cookie_path_frame.pack(pady=2)
        tk.Label(cookie_path_frame, text="Cookie File Path:", bg="#BFBFBF", fg="black").pack(side="left")
        tk.Entry(cookie_path_frame, textvariable=self.cookie_file_path, width=30).pack(side="left", padx=5)
        tk.Button(cookie_path_frame, text="Browse", bg="#D4D0C8", fg="black", 
                 command=self.browse_cookie_file).pack(side="left")

        # Add format preference
        tk.Label(content_frame, text="Format Preference:", bg="#BFBFBF", fg="black").pack(pady=5, anchor="w")
        self.format_var = tk.StringVar(value="auto")
        format_frame = tk.Frame(content_frame, bg="#BFBFBF")
        format_frame.pack(pady=5)
        
        tk.Radiobutton(format_frame, text="Auto (Smart)", variable=self.format_var, value="auto", bg="#BFBFBF").pack(side="left")
        tk.Radiobutton(format_frame, text="Direct (Fast)", variable=self.format_var, value="direct", bg="#BFBFBF").pack(side="left")
        tk.Radiobutton(format_frame, text="HLS (Compatible)", variable=self.format_var, value="hls", bg="#BFBFBF").pack(side="left")

        buttonframe = tk.Frame(content_frame, bg="#BFBFBF")
        buttonframe.columnconfigure(0, weight=1)
        buttonframe.columnconfigure(1, weight=1)
        buttonframe.columnconfigure(2, weight=1)

        clear_button = tk.Button(buttonframe, text="Clear",bg="#D4D0C8", fg="black", relief="ridge", font=("Helvetica", 12, "bold"), command=self.clear)
        clear_button.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        check_formats_button = tk.Button(buttonframe, text="Check Formats", bg="#D4D0C8", fg="black", relief="ridge", font=("Helvetica", 12, "bold"), command=self.check_available_formats)
        check_formats_button.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        self.download_button = tk.Button(buttonframe, text="Download MP3", bg="#D4D0C8", fg="black" , relief="ridge", font=("Helvetica", 12, "bold"), command=self.start_download)
        self.download_button.grid(row=0, column=2,sticky="ew", padx=5, pady=5)

        buttonframe.pack(pady=10)
        
        # Add cancel button (inside content_frame, not root)
        self.cancel_button = tk.Button(content_frame, text="Cancel", bg="#FF6B6B", fg="white", 
                                      relief="ridge", font=("Helvetica", 12, "bold"), 
                                      command=self.cancel_download_process)
        self.cancel_button.pack(pady=5)
        self.cancel_button.config(state="disabled")
        
        # Add collapsible Advanced Tools section
        self.advanced_frame = tk.Frame(content_frame, bg="#BFBFBF")
        self.advanced_frame.pack(pady=5, fill="x")
        
        # Advanced Tools header with toggle button
        advanced_header_frame = tk.Frame(self.advanced_frame, bg="#BFBFBF")
        advanced_header_frame.pack(fill="x")
        
        self.advanced_toggle = tk.Button(advanced_header_frame, text="🔧 Advanced Tools", 
                                        bg="#E0E0E0", fg="#333333", relief="flat",
                                        font=("Helvetica", 10, "bold"),
                                        command=self.toggle_advanced_tools)
        self.advanced_toggle.pack(side="left")
        
        # Advanced Tools content (initially hidden)
        self.advanced_content = tk.Frame(self.advanced_frame, bg="#BFBFBF")
        self.advanced_content.pack(fill="x", pady=(5, 0))
        
        # Test YouTube Access button
        test_button = tk.Button(self.advanced_content, text="Test YouTube Access", 
                               bg="#D4D0C8", fg="black", relief="ridge", 
                               font=("Helvetica", 10, "bold"),
                               command=self.test_youtube_access)
        test_button.pack(pady=2, fill="x")
        
        # Test yt-dlp Command Line button
        cmd_test_button = tk.Button(self.advanced_content, text="Test yt-dlp Command Line", 
                                   bg="#D4D0C8", fg="black", relief="ridge", 
                                   font=("Helvetica", 10, "bold"),
                                   command=self.test_ytdlp_command)
        cmd_test_button.pack(pady=2, fill="x")
        
        # Diagnose Python Environment button
        diag_button = tk.Button(self.advanced_content, text="Diagnose Python Environment", 
                               bg="#D4D0C8", fg="black", relief="ridge", 
                               font=("Helvetica", 10, "bold"),
                               command=self.diagnose_python_environment)
        diag_button.pack(pady=2, fill="x")
        
        # Initially hide advanced content
        self.advanced_content.pack_forget()
        self.advanced_expanded = False
        
        # Replace indeterminate progress bar with determinate one
        self.progressbar = ttk.Progressbar(content_frame, orient="horizontal", length=200, mode="determinate", style="TProgressbar")
        self.progressbar.pack(pady=10)
        
        # Add status label
        self.status_label = tk.Label(content_frame, text="Ready", bg="#BFBFBF", fg="black")
        self.status_label.pack(pady=5)

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
        
        # Build download strategies based on user preferences
        download_strategies = []
        
        # Define different client types to try (to avoid SABR streaming issues)
        client_types = ['android', 'web', 'ios', 'tv_embedded']
        
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
        # Don't skip DASH/HLS as they might be the only formats available
        # Instead, we'll try different client types to avoid SABR streaming
        common_opts = {
            'nocheckcertificate': True,
        }
        
        # Only skip formats if user explicitly wants to avoid HLS
        if self.fast_download.get() and self.format_var.get() != "hls":
            # Try to avoid HLS but allow DASH (which is often necessary)
            common_opts['extractor_args'] = {
                'youtube': {
                    'skip': ['hls'],  # Only skip HLS, allow DASH
                }
            }
        
        # Only add cookie support if user explicitly enables it
        if self.use_cookies.get():
            common_opts['cookiesfrombrowser'] = ('chrome',)
            logger.info("Using browser cookies for authentication")
        elif self.use_cookie_file.get():
            cookie_path = self.cookie_file_path.get()
            if cookie_path:
                try:
                    with open(cookie_path, 'r') as f:
                        cookie_data = f.read()
                    common_opts['cookies'] = cookie_data
                    logger.info(f"Using cookie file from: {cookie_path}")
                except FileNotFoundError:
                    error_msg = f"Cookie file not found at: {cookie_path}\nPlease select a valid cookie file."
                    messagebox.showerror("Cookie Error", error_msg)
                    logger.error(f"Cookie file not found: {cookie_path}")
                    return
                except Exception as e:
                    error_msg = f"Error reading cookie file {cookie_path}: {str(e)}\nPlease ensure it's a valid cookie file."
                    messagebox.showerror("Cookie Error", error_msg)
                    logger.error(f"Error reading cookie file {cookie_path}: {e}")
                    return
            else:
                error_msg = "Please select a cookie file path."
                messagebox.showerror("Cookie Error", error_msg)
                logger.error("No cookie file path selected.")
                return
        else:
            logger.info("Skipping browser cookies and cookie file to avoid keychain access")
        
        if self.format_var.get() == "direct" or (self.format_var.get() == "auto" and self.fast_download.get()):
            # Fast strategies that avoid HLS - try with different client types
            for client in client_types[:2]:  # Try android and web first
                opts = common_opts.copy()
                opts['extractor_args'] = {
                    'youtube': {
                        'skip': ['hls'],
                        'player_client': [client],  # Try different client to avoid SABR
                    }
                }
                download_strategies.extend([
                    # Strategy: Direct audio formats with specific client
                    {
                        'format': 'bestaudio[ext=mp3]/bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio[protocol!=m3u8]/bestaudio',
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
                    },
                    # Strategy: More permissive format selection with client
                    {
                        'format': 'bestaudio[protocol!=m3u8]/bestaudio/best[height<=480]',
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
                ])
        
        if self.format_var.get() == "hls" or (self.format_var.get() == "auto" and not self.fast_download.get()):
            # Include HLS formats for compatibility - try with different clients
            for client in client_types:
                opts = common_opts.copy()
                opts['extractor_args'] = {
                    'youtube': {
                        'player_client': [client],
                    }
                }
                download_strategies.append({
                    'format': 'bestaudio/best',
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
                })
        
        # Always add fallback strategies with different client types
        for client in client_types:
            opts = common_opts.copy()
            opts['extractor_args'] = {
                'youtube': {
                    'player_client': [client],
                }
            }
            # Fallback 1: Try bestaudio
            download_strategies.append({
                'format': 'bestaudio/best',
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
            })
            # Fallback 2: Try any format (video+audio, then extract audio)
            download_strategies.append({
                'format': 'best[height<=720]/best',  # Try video formats too, then extract audio
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
            })

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
        self.progressbar.stop()
        self.progressbar['value'] = 0
        self.downloading = False
        self.cancel_download = False
        self.cancel_button.config(state="disabled")
        self.download_button.config(state="normal")
        self.update_progress('status', text="Ready")

    def progress_hook(self, d):
        """Progress hook for yt-dlp to update progress bar"""
        if d['status'] == 'downloading':
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
        elif d['status'] == 'finished':
            self.update_progress('status', text="Converting to MP3...")
            # Reset progress bar for conversion phase
            self.update_progress('progress', value=0)
        elif d['status'] == 'postprocessing':
            self.update_progress('status', text="Processing audio...")
            # Show some progress during postprocessing
            self.update_progress('progress', value=50)

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
                        try:
                            with open(cookie_path, 'r') as f:
                                cookie_data = f.read()
                            ydl_opts['cookies'] = cookie_data
                            logger.info(f"Using cookie file for format check: {cookie_path}")
                        except FileNotFoundError:
                            error_msg = f"Cookie file not found at: {cookie_path}\nPlease select a valid cookie file."
                            messagebox.showerror("Cookie Error", error_msg)
                            logger.error(f"Cookie file not found for format check: {cookie_path}")
                            return
                        except Exception as e:
                            error_msg = f"Error reading cookie file {cookie_path} for format check: {str(e)}\nPlease ensure it's a valid cookie file."
                            messagebox.showerror("Cookie Error", error_msg)
                            logger.error(f"Error reading cookie file {cookie_path} for format check: {e}")
                            return
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
                    if cookie_path:
                        try:
                            with open(cookie_path, 'r') as f:
                                cookie_data = f.read()
                            ydl_opts['cookies'] = cookie_data
                        except:
                            pass
                
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

    def test_youtube_access(self):
        """Test if yt-dlp can access YouTube at all"""
        self.status_label.config(text="Testing YouTube access...")
        self.progressbar['value'] = 0
        
        # Run test in separate thread
        test_thread = threading.Thread(target=self._test_youtube_worker)
        test_thread.start()
    
    def _test_youtube_worker(self):
        """Worker thread to test YouTube access"""
        try:
            # Test with a simple, popular video that should work
            test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # "Me at the zoo" - YouTube's first video, always available
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': False,
                'extract_flat': False,
            }
            
            # Try to use cookies if available
            if self.use_cookies.get():
                ydl_opts['cookiesfrombrowser'] = ('chrome',)
                logger.info("Testing YouTube access with browser cookies")
            elif self.use_cookie_file.get():
                cookie_path = self.cookie_file_path.get()
                if cookie_path:
                    try:
                        with open(cookie_path, 'r') as f:
                            cookie_data = f.read()
                        ydl_opts['cookies'] = cookie_data
                        logger.info(f"Testing YouTube access with cookie file: {cookie_path}")
                    except Exception as e:
                        logger.error(f"Failed to read cookie file: {e}")
                        # Continue without cookies
                else:
                    logger.info("Testing YouTube access without cookies (no cookie file path)")
            else:
                logger.info("Testing YouTube access without cookies")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Just try to get video info
                info = ydl.extract_info(test_url, download=False)
                
                if info:
                    title = info.get('title', 'Unknown')
                    duration = info.get('duration', 0)
                    
                    result = f"✅ YouTube Access Working!\n\nVideo: {title}\nDuration: {duration//60}:{duration%60:02d}\n\nYour yt-dlp installation is working correctly."
                    
                    # Show result
                    self.show_test_result(result, "success")
                    logger.info("YouTube access test successful")
                else:
                    self.show_test_result("❌ Could not extract video information", "error")
                    
        except Exception as e:
            error_msg = f"❌ YouTube Access Failed!\n\nError: {str(e)}\n\nThis means:\n1. yt-dlp is outdated\n2. YouTube blocked access\n3. Network issues\n4. yt-dlp installation problem"
            self.show_test_result(error_msg, "error")
            logger.error(f"YouTube access test failed: {e}")
        finally:
            self.status_label.config(text="Ready")
            self.progressbar['value'] = 0
    
    def show_test_result(self, result_text, result_type):
        """Show the test result in a new window"""
        # Create a new window
        result_window = tk.Toplevel(self.root)
        result_window.title("YouTube Access Test")
        result_window.geometry("500x300")
        
        if result_type == "success":
            result_window.configure(bg="#E8F5E8")  # Light green
            title_color = "#2E7D32"  # Dark green
        else:
            result_window.configure(bg="#FFEBEE")  # Light red
            title_color = "#C62828"  # Dark red
        
        # Add title
        title_label = tk.Label(result_window, text="YouTube Access Test Result", 
                              bg=result_window.cget('bg'), fg=title_color, 
                              font=("Helvetica", 14, "bold"))
        title_label.pack(pady=10)
        
        # Add result text
        text_widget = tk.Text(result_window, wrap="word", bg="white", fg="black", 
                             font=("Arial", 11), height=10)
        text_widget.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Insert the result text
        text_widget.insert("1.0", result_text)
        text_widget.config(state="disabled")  # Make read-only
        
        # Add close button
        close_button = tk.Button(result_window, text="Close", bg="#D4D0C8", fg="black",
                                relief="ridge", font=("Helvetica", 12, "bold"),
                                command=result_window.destroy)
        close_button.pack(pady=10)

    def test_ytdlp_command(self):
        """Test yt-dlp directly from command line"""
        self.status_label.config(text="Testing yt-dlp command line...")
        self.progressbar['value'] = 0
        
        # Run command line test in separate thread
        test_thread = threading.Thread(target=self._test_ytdlp_command_worker)
        test_thread.start()
    
    def _test_ytdlp_command_worker(self):
        """Worker thread to test yt-dlp command line"""
        try:
            import subprocess
            import sys
            
            # Test 1: Check yt-dlp version
            try:
                result = subprocess.run([sys.executable, '-m', 'yt_dlp', '--version'], 
                                      capture_output=True, text=True, timeout=10)
                version = result.stdout.strip()
                logger.info(f"yt-dlp version: {version}")
            except Exception as e:
                version = f"Error getting version: {e}"
                logger.error(f"Failed to get yt-dlp version: {e}")
            
            # Test 2: Try to extract info from a simple video
            test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
            
            try:
                cmd = [sys.executable, '-m', 'yt_dlp', '--dump-json', '--no-playlist', test_url]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    # Success - parse the JSON output
                    import json
                    try:
                        video_info = json.loads(result.stdout)
                        title = video_info.get('title', 'Unknown')
                        duration = video_info.get('duration', 0)
                        
                        result_text = f"✅ yt-dlp Command Line Working!\n\n"
                        result_text += f"Version: {version}\n"
                        result_text += f"Video: {title}\n"
                        if duration > 0:
                            result_text += f"Duration: {duration//60}:{duration%60:02d}\n"
                        result_text += f"\nThe command line version works, but the Python module doesn't.\n"
                        result_text += f"This suggests a Python environment issue."
                        
                        self.show_test_result(result_text, "success")
                        logger.info("yt-dlp command line test successful")
                        
                    except json.JSONDecodeError:
                        result_text = f"✅ yt-dlp Command Line Working!\n\n"
                        result_text += f"Version: {version}\n"
                        result_text += f"Raw output: {result.stdout[:200]}...\n\n"
                        result_text += f"The command line version works, but output format is unexpected."
                        
                        self.show_test_result(result_text, "success")
                        logger.info("yt-dlp command line test successful (unexpected output format)")
                        
                else:
                    # Command failed
                    error_output = result.stderr
                    result_text = f"❌ yt-dlp Command Line Failed!\n\n"
                    result_text += f"Version: {version}\n"
                    result_text += f"Error: {error_output}\n\n"
                    result_text += f"This confirms yt-dlp is completely broken.\n"
                    result_text += f"Try: pip uninstall yt-dlp && pip install yt-dlp --upgrade"
                    
                    self.show_test_result(result_text, "error")
                    logger.error(f"yt-dlp command line test failed: {error_output}")
                    
            except subprocess.TimeoutExpired:
                result_text = f"❌ yt-dlp Command Line Test Timed Out!\n\n"
                result_text += f"Version: {version}\n"
                result_text += f"The command took too long to complete.\n"
                result_text += f"This suggests network or YouTube access issues."
                
                self.show_test_result(result_text, "error")
                logger.error("yt-dlp command line test timed out")
                
            except Exception as e:
                result_text = f"❌ yt-dlp Command Line Test Error!\n\n"
                result_text += f"Version: {version}\n"
                result_text += f"Error: {str(e)}\n\n"
                result_text += f"This suggests a system-level problem with yt-dlp."
                
                self.show_test_result(result_text, "error")
                logger.error(f"yt-dlp command line test error: {e}")
                
        except Exception as e:
            result_text = f"❌ yt-dlp Command Line Test Failed!\n\n"
            result_text += f"Unexpected error: {str(e)}\n\n"
            result_text += f"This suggests a fundamental problem with the test."
            
            self.show_test_result(result_text, "error")
            logger.error(f"yt-dlp command line test unexpected error: {e}")
            
        finally:
            self.status_label.config(text="Ready")
            self.progressbar['value'] = 0

    def diagnose_python_environment(self):
        """Diagnose Python environment issues"""
        self.status_label.config(text="Diagnosing Python environment...")
        self.progressbar['value'] = 0
        
        # Run diagnosis in separate thread
        diag_thread = threading.Thread(target=self._diagnose_python_environment_worker)
        diag_thread.start()
    
    def _diagnose_python_environment_worker(self):
        """Worker thread to diagnose Python environment"""
        try:
            import sys
            import subprocess
            import importlib.util
            
            diagnosis = []
            diagnosis.append("🔍 Python Environment Diagnosis")
            diagnosis.append("=" * 50)
            
            # 1. Python version and executable
            diagnosis.append(f"\n🐍 Python Version: {sys.version}")
            diagnosis.append(f"🐍 Python Executable: {sys.executable}")
            diagnosis.append(f"🐍 Python Path: {sys.path[0]}")
            
            # 2. Check if yt-dlp module can be imported
            try:
                import yt_dlp
                diagnosis.append(f"\n✅ yt-dlp Module Import: SUCCESS")
                diagnosis.append(f"📦 Module Location: {yt_dlp.__file__}")
                diagnosis.append(f"📦 Module Version: {yt_dlp.version.__version__}")
            except ImportError as e:
                diagnosis.append(f"\n❌ yt-dlp Module Import: FAILED")
                diagnosis.append(f"🚨 Error: {e}")
            except Exception as e:
                diagnosis.append(f"\n⚠️ yt-dlp Module Import: ERROR")
                diagnosis.append(f"🚨 Error: {e}")
            
            # 3. Check pip list for yt-dlp
            try:
                result = subprocess.run([sys.executable, '-m', 'pip', 'list'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    pip_output = result.stdout
                    if 'yt-dlp' in pip_output:
                        # Extract yt-dlp version from pip list
                        for line in pip_output.split('\n'):
                            if 'yt-dlp' in line:
                                diagnosis.append(f"\n📦 Pip List yt-dlp: {line.strip()}")
                                break
                    else:
                        diagnosis.append(f"\n❌ Pip List yt-dlp: NOT FOUND")
                else:
                    diagnosis.append(f"\n⚠️ Pip List: FAILED - {result.stderr}")
            except Exception as e:
                diagnosis.append(f"\n⚠️ Pip List Check: ERROR - {e}")
            
            # 4. Check sys.modules for yt-dlp
            if 'yt_dlp' in sys.modules:
                diagnosis.append(f"\n📚 Sys Modules yt-dlp: LOADED")
                diagnosis.append(f"📚 Module Object: {sys.modules['yt_dlp']}")
            else:
                diagnosis.append(f"\n❌ Sys Modules yt-dlp: NOT LOADED")
            
            # 5. Check importlib for yt-dlp
            try:
                spec = importlib.util.find_spec('yt_dlp')
                if spec:
                    diagnosis.append(f"\n🔍 Importlib yt-dlp: FOUND")
                    diagnosis.append(f"🔍 Spec Location: {spec.origin}")
                    diagnosis.append(f"🔍 Spec Loader: {spec.loader}")
                else:
                    diagnosis.append(f"\n❌ Importlib yt-dlp: NOT FOUND")
            except Exception as e:
                diagnosis.append(f"\n⚠️ Importlib Check: ERROR - {e}")
            
            # 6. Check if there are multiple Python installations
            try:
                result = subprocess.run(['which', 'python'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    which_python = result.stdout.strip()
                    diagnosis.append(f"\n🔍 System Python: {which_python}")
                    if which_python != sys.executable:
                        diagnosis.append(f"⚠️ WARNING: System Python differs from current Python!")
                        diagnosis.append(f"   System: {which_python}")
                        diagnosis.append(f"   Current: {sys.executable}")
                else:
                    diagnosis.append(f"\n🔍 System Python: NOT FOUND")
            except Exception as e:
                diagnosis.append(f"\n⚠️ System Python Check: ERROR - {e}")
            
            # 7. Check virtual environment
            if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
                diagnosis.append(f"\n🌍 Virtual Environment: ACTIVE")
                diagnosis.append(f"🌍 Base Prefix: {getattr(sys, 'base_prefix', 'N/A')}")
                diagnosis.append(f"🌍 Real Prefix: {getattr(sys, 'real_prefix', 'N/A')}")
            else:
                diagnosis.append(f"\n🌍 Virtual Environment: NOT ACTIVE")
                diagnosis.append(f"🌍 Prefix: {sys.prefix}")
            
            # 8. Summary and recommendations
            diagnosis.append(f"\n" + "=" * 50)
            diagnosis.append("💡 RECOMMENDATIONS:")
            
            if 'yt_dlp' in sys.modules:
                diagnosis.append("✅ yt-dlp module is loaded - the issue might be elsewhere")
            else:
                diagnosis.append("❌ yt-dlp module cannot be imported")
                diagnosis.append("   Try: pip install yt-dlp --upgrade --force-reinstall")
                diagnosis.append("   Or: python -m pip install yt-dlp --upgrade --force-reinstall")
            
            if 'Virtual Environment: ACTIVE' in '\n'.join(diagnosis):
                diagnosis.append("🌍 You're in a virtual environment")
                diagnosis.append("   Make sure to install yt-dlp in the SAME environment")
            
            # Show the diagnosis
            self.show_diagnosis_result('\n'.join(diagnosis))
            
        except Exception as e:
            error_msg = f"❌ Diagnosis Failed!\n\nError: {str(e)}\n\nThis suggests a fundamental problem with the diagnostic function."
            self.show_test_result(error_msg, "error")
            logger.error(f"Python environment diagnosis failed: {e}")
        finally:
            self.status_label.config(text="Ready")
            self.progressbar['value'] = 0
    
    def show_diagnosis_result(self, diagnosis_text):
        """Show the diagnosis result in a new window"""
        # Create a new window
        result_window = tk.Toplevel(self.root)
        result_window.title("Python Environment Diagnosis")
        result_window.geometry("700x600")
        result_window.configure(bg="#BFBFBF")
        
        # Add title
        title_label = tk.Label(result_window, text="Python Environment Diagnosis", 
                              bg="#BFBFBF", fg="#000080", font=("Helvetica", 14, "bold"))
        title_label.pack(pady=10)
        
        # Add scrollable text area
        text_frame = tk.Frame(result_window, bg="#BFBFBF")
        text_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        text_widget = tk.Text(text_frame, wrap="word", bg="white", fg="black", 
                             font=("Courier", 9), height=25)
        scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Insert the diagnosis text
        text_widget.insert("1.0", diagnosis_text)
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

    def toggle_advanced_tools(self):
        """
        Toggles the visibility of the advanced tools section.
        """
        if self.advanced_expanded:
            self.advanced_content.pack_forget()
            self.advanced_toggle.config(text="🔧 Advanced Tools")
        else:
            self.advanced_content.pack(fill="x", pady=(5, 0))
            self.advanced_toggle.config(text="🔓 Collapse Advanced Tools")
        self.advanced_expanded = not self.advanced_expanded

    def _on_mousewheel(self, event):
        """
        Handles mouse wheel scrolling for the canvas.
        """
        self.main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

myapp = MyGUI()
