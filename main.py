#main 

import yt_dlp
import os

def download_video(video_url, output_folder="/home/finn/Desktop/convert2mp3/downloads"):
	if not os.path.exists(output_folder):
		os.makedirs(output_folder)
		
	ydl_opts = {
		'format': 'bestaudio/best',
		'postprocessors': [{
			'key': 'FFmpegExtractAudio',
			'preferredcodec': 'mp3',
			'preferredquality': 192,
		}],
		'outtmpl': f'{output_folder}/%(title)s.%(ext)s'
		}
		
	with yt_dlp.YoutubeDL(ydl_opts) as ydl:
		ydl.download([video_url])
		
	print("download complete")
	
if __name__ == "__main__":
	video_url = input("Enter the Video URL: ")
	download_video(video_url)
	
