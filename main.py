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
        self.root.geometry("400x500")
        self.root.configure(bg="#BFBFBF")

        # Set window icon
        self.logo = PhotoImage(file="media/logo.png")
        self.root.iconphoto(False, self.logo)
        self.logo = Image.open("media/logo.png")
        self.logo = self.logo.resize((50, 50), Image.Resampling.LANCZOS)
        self.logo = ImageTk.PhotoImage(self.logo)

        frame = tk.Frame(self.root, bg="#BFBFBF")
        frame.pack(anchor="center")
        image_label = tk.Label(frame, image=self.logo, bg="#BFBFBF")
        image_label.pack(side="top", anchor="center")
        tk.Label(frame, text="Convert2mp3",bg="#BFBFBF", fg="#000080", font=("Microsoft Sans Serif", 15, "bold")).pack(side="top", anchor="center") 

        #tk.Label(self.root, image=self.logo, ).pack(pady=5, padx=5, anchor="nw", side="left")

        self.download_directory = ""

        tk.Label(self.root, text="Enter YouTube URL:", bg="#BFBFBF", fg="black", font=("Microsoft Sans Serif", 10, "bold")).pack(pady=5, anchor="w")
        self.url_entry = tk.Entry(self.root, width=50)
        self.url_entry.pack(pady=5)

        tk.Label(self.root, text="Destination Folder:", bg="#BFBFBF", fg="black").pack(pady=5, anchor="w")
        self.destination_text = tk.Label(self.root, width=60,text="please select a folder",font=("Microsoft Sans Serif", 10),  relief="sunken")
        self.destination_text.pack(pady=5)
        self.destination_button = tk.Button(self.root, text="Select Folder", bg="#D4D0C8", fg="black", relief="ridge", font=("Microsoft Sans Serif", 11), command=self.set_destination_folder)
        self.destination_button.pack(pady=5)

        tk.Label(self.root, text="Artist:", bg="#BFBFBF", fg="black").pack(pady=5, anchor="w")
        self.artist_entry = tk.Entry(self.root, width=50)
        self.artist_entry.pack(pady=5)

        tk.Label(self.root, text="Album:", bg="#BFBFBF", fg="black" ).pack(pady=5, anchor="w")
        self.album_entry = tk.Entry(self.root, width=50)
        self.album_entry.pack(pady=5)

        buttonframe = tk.Frame(self.root, bg="#BFBFBF")
        buttonframe.columnconfigure(0, weight=1)
        buttonframe.columnconfigure(1, weight=1)

        clear_button = tk.Button(buttonframe, text="Clear",bg="#D4D0C8", fg="black", relief="ridge", font=("Microsoft Sans Serif", 12, "bold"), command=self.clear)
        clear_button.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        download_button = tk.Button(buttonframe, text="Download MP3", bg="#D4D0C8", fg="black" , relief="ridge", font=("Microsoft Sans Serif", 12, "bold"), command=self.start_download)
        download_button.grid(row=0, column=1,sticky="ew", padx=5, pady=5)

        buttonframe.pack(pady=10)
        
        
        self.progressbar = ttk.Progressbar(self.root, orient="horizontal", length=200, mode="indeterminate", style="TProgressbar")
        self.progressbar.pack(pady=10)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        logger.info("Application started.")
        self.root.mainloop()
        

    def download_audio(self, video_url, output_folder="/Desktop/downloads", artist="Unknown", album="Unknown"):
        """
        Downloads the audio from a YouTube video as an MP3 file and sets metadata.
        
        :param video_url: URL of the YouTube video.
        :param output_folder: Folder to save the MP3 file.
        :param artist: Artist name to set in metadata.
        :param album: Album name to set in metadata.
        """
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        output_template = f'{output_folder}/%(title)s.%(ext)s'
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
            'outtmpl': output_template,
            'postprocessor_args': ['-preset', 'ultrafast'],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)

                 

                if '_type' in info and info['_type'] == 'playlist':
                    for entry in info['entries']:
                        filename = ydl.prepare_filename(entry).replace(".webm", ".mp3").replace(".m4a", ".mp3")
                        audio = EasyID3(filename)
                        audio["artist"] = artist
                        audio["album"] = album
                        audio["title"] = entry.get("title", "Unknown Title")
                        audio.save()
                        

                else:
                    filename = ydl.prepare_filename(info).replace(".webm", ".mp3").replace(".m4a", ".mp3")

                    # Add metadata using mutagen
                    audio = EasyID3(filename)
                    audio["artist"] = artist
                    audio["album"] = album
                    audio["title"] = info.get("title", "Unknown Title")
                    audio.save()

                    # Save the thumbnail
                    thumbnail_path = self.save_thumbnail(info) 
                    audio_file = MP3(filename, ID3=ID3)
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
                    audio_file.save()
                    os.remove(thumbnail_path)

            messagebox.showinfo("Success", "Download complete with metadata and thumbnail!")
            logger.info(f"Successfully downloaded audio from {video_url} to {output_folder}")
            self.progressbar.stop()
        except Exception as e:
            messagebox.showerror("Error", f"Download failed: {e}")
            logger.error(f"Download failed: {e}")

    def save_thumbnail(self, info):
        """
        Downloads a thumbnail image from a URL and saves it to the selected download folder.

        :param info: Dictionary containing video information (including the thumbnail URL).
        :return: Path to the saved thumbnail file (or None if failed).
        """
        try:
            if "thumbnail" in info:
                thumbnail_url = info["thumbnail"]
                thumbnail_name = f"{info['title']}.jpg"
                thumbnail_path = os.path.join(self.download_directory, thumbnail_name)

                thumbnail = requests.get(thumbnail_url, stream=True)
                if thumbnail.status_code == 200:
                    with open(thumbnail_path, "wb") as file:
                        for chunk in thumbnail.iter_content(1024):
                            file.write(chunk)
                    logger.info(f"Thumbnail saved: {thumbnail_path}")
                    return thumbnail_path
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
        video_url = self.url_entry.get()
        artist = self.artist_entry.get()
        album = self.album_entry.get()
        if video_url:
            logging.info(f"Downloading audio from {video_url} to {self.download_directory}")
            self.progressbar.start()
            download_thread = threading.Thread(target=self.download_audio, args=(video_url, self.download_directory, artist, album))
            download_thread.start() 
            
        else:
            messagebox.showwarning("Warning", "Please enter a valid YouTube URL.")

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

myapp = MyGUI()
