import yt_dlp
import ffmpeg
import os
from pathlib import Path
import json
import tempfile
from datetime import datetime

class VideoCutter:
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / 'digicollect'
        self.temp_dir.mkdir(exist_ok=True)
        
        # yt-dlp yapılandırması
        self.ydl_opts = {
            'format': 'best[height<=720]',  # 720p veya daha düşük kalite
            'outtmpl': str(self.temp_dir / '%(id)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
    
    def download_video(self, url):
        """Video URL'inden video indir"""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                # Video bilgilerini al
                info = ydl.extract_info(url, download=True)
                
                return {
                    'status': 'success',
                    'video_id': info['id'],
                    'title': info['title'],
                    'duration': info['duration'],
                    'thumbnail': info['thumbnail'],
                    'file_path': str(self.temp_dir / f"{info['id']}.{info['ext']}"),
                    'metadata': {
                        'uploader': info.get('uploader', ''),
                        'view_count': info.get('view_count', 0),
                        'like_count': info.get('like_count', 0),
                        'upload_date': info.get('upload_date', ''),
                    }
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def cut_video(self, video_path, start_time, end_time, output_path=None):
        """Videoyu belirtilen zaman aralığında kes"""
        try:
            if not output_path:
                # Geçici dosya oluştur
                output_path = str(self.temp_dir / f'cut_{datetime.now().timestamp()}.mp4')
            
            # FFmpeg ile kesme işlemi
            stream = ffmpeg.input(video_path)
            
            # Zaman aralığını ayarla
            stream = stream.trim(start=start_time, end=end_time)
            
            # Ses ve görüntüyü birleştir
            stream = ffmpeg.output(stream, output_path, acodec='aac', vcodec='h264')
            
            # Kesme işlemini gerçekleştir
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
            
            return {
                'status': 'success',
                'output_path': output_path
            }
            
        except ffmpeg.Error as e:
            return {
                'status': 'error',
                'error': str(e.stderr, 'utf-8')
            }
    
    def generate_thumbnail(self, video_path, time_position, output_path=None):
        """Videodan belirli bir anda thumbnail oluştur"""
        try:
            if not output_path:
                output_path = str(self.temp_dir / f'thumb_{datetime.now().timestamp()}.jpg')
            
            # FFmpeg ile thumbnail oluştur
            stream = ffmpeg.input(video_path, ss=time_position)
            stream = ffmpeg.output(stream, output_path, vframes=1)
            ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
            
            return {
                'status': 'success',
                'thumbnail_path': output_path
            }
            
        except ffmpeg.Error as e:
            return {
                'status': 'error',
                'error': str(e.stderr, 'utf-8')
            }
    
    def get_video_info(self, video_path):
        """Video dosyası hakkında bilgi al"""
        try:
            probe = ffmpeg.probe(video_path)
            video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            
            return {
                'status': 'success',
                'duration': float(probe['format']['duration']),
                'width': int(video_info['width']),
                'height': int(video_info['height']),
                'format': probe['format']['format_name']
            }
            
        except ffmpeg.Error as e:
            return {
                'status': 'error',
                'error': str(e.stderr, 'utf-8')
            }
    
    def cleanup(self):
        """Geçici dosyaları temizle"""
        try:
            for file in self.temp_dir.glob('*'):
                if file.is_file():
                    file.unlink()
        except Exception as e:
            print(f"Temizleme hatası: {e}")
            
    def __del__(self):
        """Nesne silindiğinde geçici dosyaları temizle"""
        self.cleanup()
