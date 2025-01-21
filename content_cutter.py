import os
import json
from moviepy.editor import VideoFileClip, AudioFileClip
from PIL import Image
import requests
from io import BytesIO
import tempfile

class ContentCutter:
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
    
    def cut_content(self, content_data, cut_params):
        """İçeriği kes"""
        content_type = content_data.get('type')
        
        if content_type in ['video', 'audio', 'spotify', 'podcast']:
            return self._cut_media(content_data, cut_params)
        elif content_type == 'image':
            return self._cut_image(content_data, cut_params)
        elif content_type == 'text':
            return self._cut_text(content_data, cut_params)
        
        return None
    
    def _cut_media(self, content_data, cut_params):
        """Video veya ses kesiti al"""
        try:
            url = content_data['url']
            start_time = cut_params.get('start_time', 0)
            end_time = cut_params.get('end_time', 0)
            
            # Geçici dosya oluştur
            temp_file = os.path.join(self.temp_dir, 'temp_media')
            
            if content_data['type'] == 'video':
                clip = VideoFileClip(url).subclip(start_time, end_time)
            else:
                clip = AudioFileClip(url).subclip(start_time, end_time)
            
            # Kesiti kaydet
            clip.write_videofile(temp_file) if content_data['type'] == 'video' else clip.write_audiofile(temp_file)
            clip.close()
            
            # Kesit bilgilerini döndür
            return {
                **content_data,
                'cut_data': {
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': end_time - start_time
                }
            }
            
        except Exception as e:
            print(f"Medya kesme hatası: {e}")
            return None
    
    def _cut_image(self, content_data, cut_params):
        """Görsel kesiti al"""
        try:
            # Görseli indir
            response = requests.get(content_data['image'])
            image = Image.open(BytesIO(response.content))
            
            # Kırpma koordinatları
            x = cut_params.get('x', 0)
            y = cut_params.get('y', 0)
            width = cut_params.get('width', image.width)
            height = cut_params.get('height', image.height)
            
            # Görseli kırp
            cropped = image.crop((x, y, x + width, y + height))
            
            # Geçici dosyaya kaydet
            temp_file = os.path.join(self.temp_dir, 'temp_image.jpg')
            cropped.save(temp_file, 'JPEG')
            
            # Kesit bilgilerini döndür
            return {
                **content_data,
                'cut_data': {
                    'x': x,
                    'y': y,
                    'width': width,
                    'height': height
                }
            }
            
        except Exception as e:
            print(f"Görsel kesme hatası: {e}")
            return None
    
    def _cut_text(self, content_data, cut_params):
        """Metin kesiti al"""
        try:
            text = content_data.get('content', '')
            start_index = cut_params.get('start_index', 0)
            end_index = cut_params.get('end_index', len(text))
            
            # Metni kes
            cut_text = text[start_index:end_index]
            
            # Kesit bilgilerini döndür
            return {
                **content_data,
                'content': cut_text,
                'cut_data': {
                    'start_index': start_index,
                    'end_index': end_index,
                    'length': len(cut_text)
                }
            }
            
        except Exception as e:
            print(f"Metin kesme hatası: {e}")
            return None
    
    def _download_media(self, url, temp_file):
        """Medyayı geçici dosyaya indir"""
        try:
            response = requests.get(url, stream=True)
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
        except Exception as e:
            print(f"Medya indirme hatası: {e}")
            return False
