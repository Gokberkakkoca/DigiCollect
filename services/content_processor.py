from urllib.parse import urlparse
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import json

class ContentProcessor:
    def __init__(self):
        # Desteklenen platformlar ve domain eşleşmeleri
        self.PLATFORMS = {
            'youtube': ['youtube.com', 'youtu.be'],
            'spotify': ['spotify.com'],
            'twitter': ['twitter.com', 'x.com'],
            'instagram': ['instagram.com'],
            'medium': ['medium.com'],
            'pinterest': ['pinterest.com'],
            'podcast': ['anchor.fm', 'spotify.com/show']
        }
        
    def process_shared_content(self, shared_url):
        """Paylaşılan içeriği işle ve metadata'sını çıkar"""
        try:
            # URL'i doğrula ve platform türünü belirle
            platform, clean_url = self.detect_platform(shared_url)
            
            # İçerik meta verilerini çek
            metadata = self.fetch_metadata(clean_url, platform)
            
            # Kaynak bilgisini oluştur
            source_info = self.create_source_info(metadata, platform)
            
            return {
                'status': 'success',
                'platform': platform,
                'url': clean_url,
                'metadata': metadata,
                'source_info': source_info,
                'timestamp': str(datetime.now())
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'url': shared_url
            }
    
    def detect_platform(self, url):
        """URL'den platform türünü tespit et"""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        for platform, domains in self.PLATFORMS.items():
            if any(d in domain for d in domains):
                return platform, url
                
        # Eğer özel bir platform değilse, genel web sitesi olarak işaretle
        return 'website', url
    
    def fetch_metadata(self, url, platform):
        """Platform türüne göre meta verileri çek"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            metadata = {
                'title': self.get_title(soup),
                'description': self.get_description(soup),
                'image': self.get_image(soup),
                'author': self.get_author(soup, platform),
                'date': self.get_date(soup),
                'platform_specific': self.get_platform_specific(soup, platform)
            }
            
            return metadata
            
        except Exception as e:
            return {
                'error': f'Metadata çekilemedi: {str(e)}'
            }
    
    def get_title(self, soup):
        """Sayfa başlığını çek"""
        # Önce Open Graph başlığını dene
        og_title = soup.find('meta', property='og:title')
        if og_title:
            return og_title.get('content')
            
        # Normal başlığı dene
        title = soup.find('title')
        if title:
            return title.text
            
        return 'Başlık bulunamadı'
    
    def get_description(self, soup):
        """Sayfa açıklamasını çek"""
        # Open Graph açıklaması
        og_desc = soup.find('meta', property='og:description')
        if og_desc:
            return og_desc.get('content')
            
        # Meta açıklama
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc:
            return meta_desc.get('content')
            
        return ''
    
    def get_image(self, soup):
        """Sayfa görselini çek"""
        # Open Graph görseli
        og_image = soup.find('meta', property='og:image')
        if og_image:
            return og_image.get('content')
            
        return None
    
    def get_author(self, soup, platform):
        """İçerik sahibini platform'a göre çek"""
        if platform == 'twitter':
            # Twitter kullanıcı adını bul
            author = soup.find('meta', property='og:title')
            if author:
                username = re.search(r'@(\w+)', author.get('content'))
                if username:
                    return username.group(1)
        
        elif platform == 'instagram':
            # Instagram kullanıcı adını bul
            author = soup.find('meta', property='og:title')
            if author:
                return author.get('content').split(' on Instagram')[0]
        
        # Genel author meta tag'i
        author = soup.find('meta', {'name': 'author'})
        if author:
            return author.get('content')
            
        return 'Bilinmeyen Yazar'
    
    def get_date(self, soup):
        """Yayın tarihini çek"""
        # Publish date meta tag'i
        published = soup.find('meta', {'name': ['publishedDate', 'publication_date', 'date']})
        if published:
            return published.get('content')
            
        return str(datetime.now())
    
    def get_platform_specific(self, soup, platform):
        """Platforma özel meta verileri çek"""
        if platform == 'youtube':
            return {
                'duration': self._get_youtube_duration(soup),
                'views': self._get_youtube_views(soup)
            }
        elif platform == 'spotify':
            return {
                'type': self._get_spotify_type(soup),
                'duration': self._get_spotify_duration(soup)
            }
        
        return {}
    
    def create_source_info(self, metadata, platform):
        """Kaynak bilgisi oluştur"""
        source = {
            'platform': platform,
            'author': metadata.get('author', 'Bilinmeyen Yazar'),
            'date': metadata.get('date', str(datetime.now())),
            'title': metadata.get('title', ''),
        }
        
        # Platform'a özel formatlama
        if platform == 'twitter':
            source['display'] = f"@{source['author']} tarafından Twitter'da paylaşıldı"
        elif platform == 'instagram':
            source['display'] = f"{source['author']} tarafından Instagram'da paylaşıldı"
        elif platform == 'youtube':
            source['display'] = f"{source['author']} YouTube kanalında yayınlandı"
        elif platform == 'spotify':
            source['display'] = f"Spotify'da {source['author']} tarafından"
        else:
            source['display'] = f"{source['author']} tarafından {platform}'de paylaşıldı"
            
        return source
    
    # Platform özel yardımcı metodları
    def _get_youtube_duration(self, soup):
        duration = soup.find('meta', {'itemprop': 'duration'})
        return duration.get('content') if duration else None
    
    def _get_youtube_views(self, soup):
        views = soup.find('meta', {'itemprop': 'interactionCount'})
        return views.get('content') if views else None
    
    def _get_spotify_type(self, soup):
        og_type = soup.find('meta', property='og:type')
        return og_type.get('content') if og_type else None
    
    def _get_spotify_duration(self, soup):
        duration = soup.find('meta', property='music:duration')
        return duration.get('content') if duration else None

    def process_pinterest_image(self, url):
        """Pinterest görselini işle"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Pinterest görseli meta verilerini çek
            image_url = soup.find('meta', property='og:image').get('content')
            description = soup.find('meta', property='og:description').get('content')
            pinner = soup.find('meta', property='og:title').get('content').split(' on Pinterest')[0]
            
            return {
                'type': 'pinterest',
                'image_url': image_url,
                'description': description,
                'pinner': pinner,
                'source_url': url
            }
        except Exception as e:
            return {'error': f'Pinterest görseli işlenemedi: {str(e)}'}
    
    def process_podcast(self, url):
        """Podcast bölümünü işle"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Podcast meta verilerini çek
            title = soup.find('meta', property='og:title').get('content')
            description = soup.find('meta', property='og:description').get('content')
            audio_url = soup.find('meta', property='og:audio').get('content')
            duration = soup.find('meta', property='og:audio:duration').get('content')
            
            return {
                'type': 'podcast',
                'title': title,
                'description': description,
                'audio_url': audio_url,
                'duration': duration,
                'source_url': url
            }
        except Exception as e:
            return {'error': f'Podcast bölümü işlenemedi: {str(e)}'}
    
    def process_spotify_track(self, url):
        """Spotify şarkısını işle"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Spotify şarkı meta verilerini çek
            title = soup.find('meta', property='og:title').get('content')
            artist = soup.find('meta', property='og:description').get('content')
            preview_url = soup.find('meta', property='og:audio').get('content')
            duration = soup.find('meta', property='music:duration').get('content')
            
            return {
                'type': 'spotify',
                'title': title,
                'artist': artist,
                'preview_url': preview_url,
                'duration': duration,
                'source_url': url
            }
        except Exception as e:
            return {'error': f'Spotify şarkısı işlenemedi: {str(e)}'}
    
    def cut_content(self, content_data, cut_params):
        """İçeriği belirtilen parametrelere göre kes"""
        content_type = content_data.get('type')
        
        if content_type == 'video':
            return self.cut_video(content_data, cut_params)
        elif content_type == 'audio':
            return self.cut_audio(content_data, cut_params)
        elif content_type == 'text':
            return self.cut_text(content_data, cut_params)
        elif content_type == 'image':
            return self.cut_image(content_data, cut_params)
        else:
            return {'error': 'Desteklenmeyen içerik türü'}
    
    def cut_video(self, video_data, cut_params):
        """Video kesiti oluştur"""
        try:
            start_time = cut_params.get('start_time', 0)  # Saniye cinsinden
            end_time = cut_params.get('end_time', 0)      # Saniye cinsinden
            
            if end_time <= start_time:
                raise ValueError("Bitiş zamanı başlangıç zamanından büyük olmalı")
            
            return {
                'type': 'video_cut',
                'original_url': video_data.get('source_url'),
                'start_time': start_time,
                'end_time': end_time,
                'duration': end_time - start_time,
                'metadata': video_data
            }
        except Exception as e:
            return {'error': f'Video kesilemedi: {str(e)}'}
    
    def cut_audio(self, audio_data, cut_params):
        """Ses kesiti oluştur"""
        try:
            start_time = cut_params.get('start_time', 0)  # Saniye cinsinden
            end_time = cut_params.get('end_time', 0)      # Saniye cinsinden
            
            if end_time <= start_time:
                raise ValueError("Bitiş zamanı başlangıç zamanından büyük olmalı")
            
            return {
                'type': 'audio_cut',
                'original_url': audio_data.get('source_url'),
                'start_time': start_time,
                'end_time': end_time,
                'duration': end_time - start_time,
                'metadata': audio_data
            }
        except Exception as e:
            return {'error': f'Ses kesilemedi: {str(e)}'}
    
    def cut_text(self, text_data, cut_params):
        """Metin kesiti oluştur"""
        try:
            start_index = cut_params.get('start_index', 0)
            end_index = cut_params.get('end_index', 0)
            
            if end_index <= start_index:
                raise ValueError("Bitiş indeksi başlangıç indeksinden büyük olmalı")
            
            full_text = text_data.get('content', '')
            cut_text = full_text[start_index:end_index]
            
            return {
                'type': 'text_cut',
                'original_url': text_data.get('source_url'),
                'text': cut_text,
                'start_index': start_index,
                'end_index': end_index,
                'metadata': text_data
            }
        except Exception as e:
            return {'error': f'Metin kesilemedi: {str(e)}'}
    
    def cut_image(self, image_data, cut_params):
        """Görsel kesiti oluştur (kırpma koordinatları ile)"""
        try:
            x = cut_params.get('x', 0)
            y = cut_params.get('y', 0)
            width = cut_params.get('width', 0)
            height = cut_params.get('height', 0)
            
            return {
                'type': 'image_cut',
                'original_url': image_data.get('source_url'),
                'crop_coords': {
                    'x': x,
                    'y': y,
                    'width': width,
                    'height': height
                },
                'metadata': image_data
            }
        except Exception as e:
            return {'error': f'Görsel kesilemedi: {str(e)}'}
