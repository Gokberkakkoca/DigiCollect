import instaloader
from instagram_api import InstagramAPI
import os
from datetime import datetime
import tempfile
from pathlib import Path
import json
import re
from urllib.parse import urlparse
from dotenv import load_dotenv

class InstagramExtractor:
    def __init__(self):
        # .env dosyasından kimlik bilgilerini yükle
        load_dotenv()
        
        # Instagram API kimlik bilgileri
        self.username = os.getenv('INSTAGRAM_USERNAME')
        self.password = os.getenv('INSTAGRAM_PASSWORD')
        
        # Instaloader ve Instagram API istemcilerini başlat
        self.L = instaloader.Instaloader(
            download_pictures=True,
            download_videos=True,
            download_video_thumbnails=True,
            compress_json=False,
            save_metadata=True
        )
        
        # Geçici dizin
        self.temp_dir = Path(tempfile.gettempdir()) / 'digicollect' / 'instagram'
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # API istemcisini başlat
        if self.username and self.password:
            try:
                self.L.login(self.username, self.password)
                self.api = InstagramAPI(self.username, self.password)
                self.api.login()
            except Exception as e:
                print(f"Instagram girişi başarısız: {e}")
                self.api = None
    
    def extract_shortcode(self, url):
        """Instagram URL'inden shortcode çıkar"""
        try:
            # URL'i parse et
            parsed = urlparse(url)
            path = parsed.path
            
            # /p/{shortcode} formatı
            if '/p/' in path:
                return path.split('/p/')[1].split('/')[0]
            
            # /reel/{shortcode} formatı
            if '/reel/' in path:
                return path.split('/reel/')[1].split('/')[0]
            
            raise ValueError("Geçersiz Instagram URL'i")
            
        except Exception as e:
            raise ValueError(f"Shortcode çıkarılamadı: {str(e)}")
    
    def get_post(self, url):
        """Instagram gönderisini al"""
        try:
            # Shortcode'u çıkar
            shortcode = self.extract_shortcode(url)
            
            # Gönderiyi al
            post = instaloader.Post.from_shortcode(self.L.context, shortcode)
            
            # Medya dosyalarını indir
            media_files = []
            temp_post_dir = self.temp_dir / shortcode
            temp_post_dir.mkdir(exist_ok=True)
            
            # Tek resim/video
            if not post.is_sidecar:
                if post.is_video:
                    # Video ve küçük resim indir
                    video_path = temp_post_dir / f"{shortcode}_video.mp4"
                    thumb_path = temp_post_dir / f"{shortcode}_thumb.jpg"
                    
                    self.L.download_video(post, temp_post_dir)
                    self.L.download_pic(post, temp_post_dir)
                    
                    media_files.append({
                        'type': 'video',
                        'video_url': str(video_path),
                        'thumbnail_url': str(thumb_path)
                    })
                else:
                    # Resim indir
                    pic_path = temp_post_dir / f"{shortcode}.jpg"
                    self.L.download_pic(post, temp_post_dir)
                    
                    media_files.append({
                        'type': 'image',
                        'url': str(pic_path)
                    })
            
            # Çoklu medya (carousel)
            else:
                for i, node in enumerate(post.get_sidecar_nodes()):
                    if node.is_video:
                        # Video ve küçük resim indir
                        video_path = temp_post_dir / f"{shortcode}_{i}_video.mp4"
                        thumb_path = temp_post_dir / f"{shortcode}_{i}_thumb.jpg"
                        
                        self.L.download_video(node, temp_post_dir)
                        self.L.download_pic(node, temp_post_dir)
                        
                        media_files.append({
                            'type': 'video',
                            'video_url': str(video_path),
                            'thumbnail_url': str(thumb_path)
                        })
                    else:
                        # Resim indir
                        pic_path = temp_post_dir / f"{shortcode}_{i}.jpg"
                        self.L.download_pic(node, temp_post_dir)
                        
                        media_files.append({
                            'type': 'image',
                            'url': str(pic_path)
                        })
            
            # Gönderi verilerini yapılandır
            post_data = {
                'shortcode': shortcode,
                'caption': post.caption if post.caption else '',
                'created_at': post.date_local.isoformat(),
                'author': {
                    'username': post.owner_username,
                    'full_name': post.owner_profile.full_name,
                    'profile_pic_url': post.owner_profile.profile_pic_url
                },
                'media': media_files,
                'is_video': post.is_video,
                'is_carousel': post.is_sidecar,
                'likes': post.likes,
                'comments': post.comments,
                'location': post.location.name if post.location else None,
                'hashtags': list(post.caption_hashtags) if post.caption else [],
                'mentions': list(post.caption_mentions) if post.caption else [],
                'url': url
            }
            
            return {
                'status': 'success',
                'post': post_data
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_carousel_item(self, post_data, index):
        """Carousel gönderisinden belirli bir öğeyi al"""
        try:
            if not post_data['is_carousel']:
                raise ValueError("Bu gönderi bir carousel değil")
            
            if index >= len(post_data['media']):
                raise ValueError("Geçersiz carousel indeksi")
            
            return {
                'status': 'success',
                'media': post_data['media'][index],
                'caption': post_data['caption'],
                'author': post_data['author']
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def format_caption(self, caption):
        """Gönderi açıklamasını formatla"""
        # Mention'ları vurgula
        caption = re.sub(r'@(\w+)', r'**@\1**', caption)
        
        # Hashtag'leri vurgula
        caption = re.sub(r'#(\w+)', r'**#\1**', caption)
        
        return caption.strip()
    
    def cleanup(self):
        """Geçici dosyaları temizle"""
        try:
            for item in self.temp_dir.glob('*'):
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    for subitem in item.glob('*'):
                        subitem.unlink()
                    item.rmdir()
        except Exception as e:
            print(f"Temizleme hatası: {e}")
    
    def __del__(self):
        """Nesne silindiğinde geçici dosyaları temizle"""
        self.cleanup()
