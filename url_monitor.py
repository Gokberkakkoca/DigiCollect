import re
import time
import threading
import win32clipboard
import logging
from urllib.parse import urlparse

logger = logging.getLogger('DigiCollect.URLMonitor')

class URLMonitor:
    def __init__(self, callback=None):
        """
        URL izleyici sınıfı
        
        Args:
            callback: URL algılandığında çağrılacak fonksiyon
        """
        self.callback = callback
        self.running = False
        self.last_url = None
        self._monitor_thread = None
        
        # Desteklenen platformlar için URL kalıpları
        self.url_patterns = {
            'youtube': r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]+)',
            'twitter': r'(?:https?:\/\/)?(?:www\.)?(?:twitter\.com|x\.com)\/\w+\/status\/\d+',
            'instagram': r'(?:https?:\/\/)?(?:www\.)?instagram\.com\/(?:p|reel)\/[a-zA-Z0-9_-]+',
            'spotify': r'(?:https?:\/\/)?open\.spotify\.com\/(?:track|album|playlist|artist)\/[a-zA-Z0-9]+',
            'pinterest': r'(?:https?:\/\/)?(?:www\.)?pinterest\.com\/pin\/\d+',
            'tiktok': r'(?:https?:\/\/)?(?:www\.)?(?:tiktok\.com\/@[\w.]+\/video\/\d+)',
            'vimeo': r'(?:https?:\/\/)?(?:www\.)?vimeo\.com\/\d+'
        }
    
    def start(self):
        """İzlemeyi başlat"""
        if self._monitor_thread is None or not self._monitor_thread.is_alive():
            self.running = True
            self._monitor_thread = threading.Thread(target=self._monitor_clipboard)
            self._monitor_thread.daemon = True
            self._monitor_thread.start()
            logger.info('URL izleme başlatıldı')
    
    def stop(self):
        """İzlemeyi durdur"""
        self.running = False
        if self._monitor_thread:
            self._monitor_thread.join()
            self._monitor_thread = None
        logger.info('URL izleme durduruldu')
    
    def _monitor_clipboard(self):
        """Pano içeriğini sürekli izle"""
        while self.running:
            try:
                win32clipboard.OpenClipboard()
                if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_TEXT):
                    clipboard_text = win32clipboard.GetClipboardData(win32clipboard.CF_TEXT)
                    if isinstance(clipboard_text, bytes):
                        clipboard_text = clipboard_text.decode('utf-8')
                win32clipboard.CloseClipboard()
                
                # URL'yi bul
                url = self._extract_url(clipboard_text)
                
                # Yeni ve geçerli bir URL ise callback'i çağır
                if url and url != self.last_url:
                    self.last_url = url
                    logger.info(f'Yeni URL algılandı: {url}')
                    if self.callback:
                        self.callback(url)
                
            except Exception as e:
                logger.error(f'Pano izleme hatası: {e}')
            
            time.sleep(0.5)  # CPU kullanımını azaltmak için kısa bekle
    
    def _extract_url(self, text):
        """Metinden desteklenen bir URL çıkar"""
        if not text:
            return None
            
        # Önce genel URL kontrolü
        urls = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*', text)
        if not urls:
            return None
            
        url = urls[0]
        domain = urlparse(url).netloc.replace('www.', '')
        
        # Desteklenen platformları kontrol et
        for platform, pattern in self.url_patterns.items():
            if re.match(pattern, url):
                logger.debug(f'Platform algılandı: {platform}')
                return url
        
        # Genel web sayfası URL'si
        if domain:
            return url
            
        return None
    
    def is_supported_url(self, url):
        """URL'nin desteklenen bir platforma ait olup olmadığını kontrol et"""
        for pattern in self.url_patterns.values():
            if re.match(pattern, url):
                return True
        return False
