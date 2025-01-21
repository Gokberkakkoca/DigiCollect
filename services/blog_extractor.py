import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
from datetime import datetime
import re
import html2text
import readability
from readability import Document

class BlogExtractor:
    def __init__(self):
        self.h2t = html2text.HTML2Text()
        self.h2t.ignore_links = False
        self.h2t.ignore_images = False
        self.h2t.ignore_emphasis = False
        
        # Desteklenen platformlar
        self.PLATFORMS = {
            'medium.com': self._extract_medium,
            'wordpress.com': self._extract_wordpress,
            'blogger.com': self._extract_blogger,
            'substack.com': self._extract_substack
        }
    
    def extract_content(self, url):
        """URL'den blog içeriğini çek ve işle"""
        try:
            # Sayfa içeriğini al
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            # Platform'a özel çıkarıcıyı kullan veya genel çıkarıcıya geç
            domain = urlparse(url).netloc
            extractor = None
            
            for platform_domain, platform_extractor in self.PLATFORMS.items():
                if platform_domain in domain:
                    extractor = platform_extractor
                    break
            
            if extractor:
                content = extractor(response.text, url)
            else:
                content = self._extract_general(response.text, url)
            
            return {
                'status': 'success',
                **content
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'url': url
            }
    
    def _extract_medium(self, html, url):
        """Medium makalelerini çıkar"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Medium'a özel meta veriler
        article = soup.find('article')
        if article:
            title = article.find('h1').text.strip()
            author = soup.find('meta', property='author')['content']
            date = soup.find('meta', property='article:published_time')['content']
            
            # İçerik paragraflarını topla
            content_divs = article.find_all(['p', 'h1', 'h2', 'h3', 'blockquote'])
            content = '\n\n'.join([div.text.strip() for div in content_divs])
            
            return {
                'title': title,
                'author': author,
                'date': date,
                'content': content,
                'platform': 'medium',
                'url': url
            }
    
    def _extract_wordpress(self, html, url):
        """WordPress blog yazılarını çıkar"""
        soup = BeautifulSoup(html, 'html.parser')
        
        title = soup.find('h1', class_='entry-title').text.strip()
        content_div = soup.find('div', class_='entry-content')
        
        # Yazarı bul
        author = soup.find('a', rel='author')
        if author:
            author = author.text.strip()
        else:
            author = 'Bilinmeyen Yazar'
        
        # Tarihi bul
        date = soup.find('time', class_='entry-date')
        if date:
            date = date['datetime']
        else:
            date = str(datetime.now())
        
        return {
            'title': title,
            'author': author,
            'date': date,
            'content': self.h2t.handle(str(content_div)),
            'platform': 'wordpress',
            'url': url
        }
    
    def _extract_blogger(self, html, url):
        """Blogger yazılarını çıkar"""
        soup = BeautifulSoup(html, 'html.parser')
        
        title = soup.find('h3', class_='post-title').text.strip()
        content_div = soup.find('div', class_='post-body')
        
        author = soup.find('span', class_='post-author')
        if author:
            author = author.text.strip()
        else:
            author = 'Bilinmeyen Yazar'
        
        date = soup.find('span', class_='post-timestamp')
        if date:
            date = date.find('time')['datetime']
        else:
            date = str(datetime.now())
        
        return {
            'title': title,
            'author': author,
            'date': date,
            'content': self.h2t.handle(str(content_div)),
            'platform': 'blogger',
            'url': url
        }
    
    def _extract_substack(self, html, url):
        """Substack yazılarını çıkar"""
        soup = BeautifulSoup(html, 'html.parser')
        
        title = soup.find('h1', class_='post-title').text.strip()
        content_div = soup.find('div', class_='post-content')
        
        author = soup.find('a', class_='post-author')
        if author:
            author = author.text.strip()
        else:
            author = 'Bilinmeyen Yazar'
        
        date = soup.find('time')
        if date:
            date = date['datetime']
        else:
            date = str(datetime.now())
        
        return {
            'title': title,
            'author': author,
            'date': date,
            'content': self.h2t.handle(str(content_div)),
            'platform': 'substack',
            'url': url
        }
    
    def _extract_general(self, html, url):
        """Genel web sayfalarından içerik çıkar"""
        # Readability ile ana içeriği çıkar
        doc = Document(html)
        
        # BeautifulSoup ile meta verileri çıkar
        soup = BeautifulSoup(html, 'html.parser')
        
        # Başlık
        title = doc.title()
        
        # Yazar
        author = None
        author_meta = soup.find('meta', {'name': ['author', 'article:author']})
        if author_meta:
            author = author_meta['content']
        else:
            author = 'Bilinmeyen Yazar'
        
        # Tarih
        date = None
        date_meta = soup.find('meta', {'name': ['date', 'article:published_time']})
        if date_meta:
            date = date_meta['content']
        else:
            date = str(datetime.now())
        
        # Ana içerik
        content = doc.summary()
        clean_content = self.h2t.handle(content)
        
        return {
            'title': title,
            'author': author,
            'date': date,
            'content': clean_content,
            'platform': 'website',
            'url': url
        }
    
    def extract_selection(self, content, start_index, end_index):
        """İçerikten seçili bölümü çıkar"""
        try:
            selected_content = content[start_index:end_index]
            
            # Paragraf bütünlüğünü koru
            paragraphs = selected_content.split('\n\n')
            
            # HTML formatını temizle
            clean_paragraphs = [re.sub(r'<[^>]+>', '', p) for p in paragraphs]
            
            return {
                'status': 'success',
                'content': '\n\n'.join(clean_paragraphs)
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_reading_time(self, content):
        """İçeriğin tahmini okuma süresini hesapla"""
        # Ortalama okuma hızı: dakikada 200 kelime
        words = len(content.split())
        minutes = round(words / 200)
        return max(1, minutes)  # En az 1 dakika
