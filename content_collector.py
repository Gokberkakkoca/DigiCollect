import re
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import yt_dlp
import logging

logger = logging.getLogger('DigiCollect.ContentCollector')

class ContentCollector:
    def __init__(self):
        self.supported_domains = {
            'youtube.com': self._collect_youtube,
            'youtu.be': self._collect_youtube,
            'twitter.com': self._collect_twitter,
            'x.com': self._collect_twitter,
            'instagram.com': self._collect_instagram,
            'open.spotify.com': self._collect_spotify,
            'pinterest.com': self._collect_pinterest
        }
        logger.info('ContentCollector başlatıldı')
    
    def collect_content(self, url):
        """URL'den içerik topla"""
        try:
            domain = urlparse(url).netloc.replace('www.', '')
            logger.debug(f'Domain: {domain}')
            
            # Desteklenen domain kontrolü
            collector = self.supported_domains.get(domain)
            if collector:
                logger.info(f'Desteklenen domain bulundu: {domain}')
                return collector(url)
            
            # Genel web sayfası
            logger.info('Genel web sayfası olarak işleniyor')
            return self._collect_webpage(url)
            
        except Exception as e:
            logger.exception(f"İçerik toplama hatası: {e}")
            return None
    
    def _collect_youtube(self, url):
        """YouTube videosu topla"""
        logger.info(f'YouTube videosu toplanıyor: {url}')
        
        ydl_opts = {
            'format': 'best',
            'extract_flat': True,
            'no_warnings': True,
            'quiet': True
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.debug('Video bilgileri çekiliyor')
                info = ydl.extract_info(url, download=False)
                
                data = {
                    'type': 'video',
                    'url': url,
                    'title': info.get('title', ''),
                    'description': info.get('description', ''),
                    'thumbnail': info.get('thumbnail', ''),
                    'duration': info.get('duration', 0)
                }
                
                logger.debug(f'Video bilgileri: {data}')
                return data
                
        except Exception as e:
            logger.exception(f"YouTube video toplama hatası: {e}")
            return None
    
    def _collect_twitter(self, url):
        """Twitter gönderisi topla"""
        logger.info(f'Twitter gönderisi toplanıyor: {url}')
        
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Meta etiketlerinden bilgi çek
            title = soup.find('meta', property='og:title')
            description = soup.find('meta', property='og:description')
            image = soup.find('meta', property='og:image')
            
            data = {
                'type': 'text',
                'url': url,
                'title': title.get('content', '') if title else '',
                'description': description.get('content', '') if description else '',
                'thumbnail': image.get('content', '') if image else '',
                'content': description.get('content', '') if description else ''
            }
            
            logger.debug(f'Twitter gönderisi bilgileri: {data}')
            return data
            
        except Exception as e:
            logger.exception(f"Twitter gönderisi toplama hatası: {e}")
            return None
    
    def _collect_instagram(self, url):
        """Instagram gönderisi topla"""
        logger.info(f'Instagram gönderisi toplanıyor: {url}')
        
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Meta etiketlerinden bilgi çek
            title = soup.find('meta', property='og:title')
            description = soup.find('meta', property='og:description')
            image = soup.find('meta', property='og:image')
            type_meta = soup.find('meta', property='og:type')
            
            content_type = 'video' if type_meta and 'video' in type_meta.get('content', '') else 'image'
            
            data = {
                'type': content_type,
                'url': url,
                'title': title.get('content', '') if title else '',
                'description': description.get('content', '') if description else '',
                'thumbnail': image.get('content', '') if image else '',
                'image': image.get('content', '') if image else ''
            }
            
            logger.debug(f'Instagram gönderisi bilgileri: {data}')
            return data
            
        except Exception as e:
            logger.exception(f"Instagram gönderisi toplama hatası: {e}")
            return None
    
    def _collect_spotify(self, url):
        """Spotify şarkısı topla"""
        logger.info(f'Spotify şarkısı toplanıyor: {url}')
        
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Meta etiketlerinden bilgi çek
            title = soup.find('meta', property='og:title')
            description = soup.find('meta', property='og:description')
            image = soup.find('meta', property='og:image')
            duration = soup.find('meta', property='music:duration')
            
            data = {
                'type': 'spotify',
                'url': url,
                'title': title.get('content', '') if title else '',
                'description': description.get('content', '') if description else '',
                'thumbnail': image.get('content', '') if image else '',
                'duration': int(duration.get('content', 0)) if duration else 0
            }
            
            logger.debug(f'Spotify şarkısı bilgileri: {data}')
            return data
            
        except Exception as e:
            logger.exception(f"Spotify şarkısı toplama hatası: {e}")
            return None
    
    def _collect_pinterest(self, url):
        """Pinterest görseli topla"""
        logger.info(f'Pinterest görseli toplanıyor: {url}')
        
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Meta etiketlerinden bilgi çek
            title = soup.find('meta', property='og:title')
            description = soup.find('meta', property='og:description')
            image = soup.find('meta', property='og:image')
            
            data = {
                'type': 'image',
                'url': url,
                'title': title.get('content', '') if title else '',
                'description': description.get('content', '') if description else '',
                'thumbnail': image.get('content', '') if image else '',
                'image': image.get('content', '') if image else ''
            }
            
            logger.debug(f'Pinterest görseli bilgileri: {data}')
            return data
            
        except Exception as e:
            logger.exception(f"Pinterest görseli toplama hatası: {e}")
            return None
    
    def _collect_webpage(self, url):
        """Genel web sayfası topla"""
        logger.info(f'Web sayfası toplanıyor: {url}')
        
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Meta etiketlerinden bilgi çek
            title = soup.find('meta', property='og:title') or soup.find('title')
            description = soup.find('meta', property='og:description') or soup.find('meta', {'name': 'description'})
            image = soup.find('meta', property='og:image')
            
            # Ana içeriği bul
            content = ''
            article = soup.find('article') or soup.find(class_=re.compile(r'article|post|content|entry'))
            if article:
                paragraphs = article.find_all('p')
                content = '\n\n'.join(p.get_text().strip() for p in paragraphs)
            
            data = {
                'type': 'text',
                'url': url,
                'title': title.get('content', '') if hasattr(title, 'get') else title.string if title else '',
                'description': description.get('content', '') if hasattr(description, 'get') else description.string if description else '',
                'thumbnail': image.get('content', '') if image else '',
                'content': content
            }
            
            logger.debug(f'Web sayfası bilgileri: {data}')
            return data
            
        except Exception as e:
            logger.exception(f"Web sayfası toplama hatası: {e}")
            return None
