import yt_dlp
import ffmpeg
import os
from pathlib import Path
import json
import tempfile
from datetime import datetime
import requests
from bs4 import BeautifulSoup

class MusicCutter:
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / 'digicollect'
        self.temp_dir.mkdir(exist_ok=True)
        
        # yt-dlp yapılandırması
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': str(self.temp_dir / '%(id)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
    
    def download_music(self, url):
        """Müzik URL'inden ses dosyası indir"""
        try:
            # URL'in Spotify olup olmadığını kontrol et
            if 'spotify.com' in url:
                return self._handle_spotify(url)
            
            # YouTube veya diğer kaynaklar için yt-dlp kullan
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                return {
                    'status': 'success',
                    'track_id': info['id'],
                    'title': info['title'],
                    'duration': info['duration'],
                    'thumbnail': info.get('thumbnail'),
                    'file_path': str(self.temp_dir / f"{info['id']}.mp3"),
                    'metadata': {
                        'artist': info.get('artist', ''),
                        'album': info.get('album', ''),
                        'track': info.get('track', ''),
                        'release_date': info.get('release_date', ''),
                    }
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _handle_spotify(self, url):
        """Spotify URL'inden meta verileri çek"""
        try:
            # Spotify web sayfasından meta verileri çek
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Meta verilerden bilgileri al
            title = soup.find('meta', property='og:title')['content']
            description = soup.find('meta', property='og:description')['content']
            image = soup.find('meta', property='og:image')['content']
            
            # Sanatçı adını açıklamadan çıkar
            artist = description.split('·')[0].strip()
            
            return {
                'status': 'success',
                'title': title,
                'artist': artist,
                'thumbnail': image,
                'platform': 'spotify',
                'url': url
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def cut_music(self, music_path, start_time, end_time, output_path=None):
        """Müziği belirtilen zaman aralığında kes"""
        try:
            if not output_path:
                output_path = str(self.temp_dir / f'cut_{datetime.now().timestamp()}.mp3')
            
            # FFmpeg ile kesme işlemi
            stream = ffmpeg.input(music_path)
            
            # Zaman aralığını ayarla
            stream = stream.filter_('atrim', start=start_time, end=end_time)
            
            # Ses dosyasını kaydet
            stream = ffmpeg.output(stream, output_path, acodec='libmp3lame', q=2)
            
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
    
    def generate_waveform(self, music_path, width=800, height=200):
        """Ses dosyasından dalga formu görüntüsü oluştur"""
        try:
            output_path = str(self.temp_dir / f'waveform_{datetime.now().timestamp()}.png')
            
            # FFmpeg ile dalga formu oluştur
            stream = ffmpeg.input(music_path)
            stream = ffmpeg.filter(stream, 'showwaves', 
                                 s=f'{width}x{height}',
                                 mode='line',
                                 rate=25,
                                 colors='blue')
            
            stream = ffmpeg.output(stream, output_path)
            ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
            
            return {
                'status': 'success',
                'waveform_path': output_path
            }
            
        except ffmpeg.Error as e:
            return {
                'status': 'error',
                'error': str(e.stderr, 'utf-8')
            }
    
    def get_music_info(self, music_path):
        """Ses dosyası hakkında bilgi al"""
        try:
            probe = ffmpeg.probe(music_path)
            audio_info = next(s for s in probe['streams'] if s['codec_type'] == 'audio')
            
            return {
                'status': 'success',
                'duration': float(probe['format']['duration']),
                'sample_rate': int(audio_info['sample_rate']),
                'channels': int(audio_info['channels']),
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
