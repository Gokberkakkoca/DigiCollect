import pystray
from PIL import Image
import keyboard
import pyperclip
import threading
import webbrowser
from pathlib import Path
import json
import os

class DigiCollectTray:
    def __init__(self):
        self.icon = None
        self.active = True
        self.setup_tray()
        self.setup_hotkeys()
        
    def setup_tray(self):
        # İkon dosyasının yolu
        icon_path = Path(__file__).parent / 'assets' / 'icons' / 'tray_icon.png'
        
        # Menü öğelerini oluştur
        menu = (
            pystray.MenuItem('DigiCollect', self.show_main_window),
            pystray.MenuItem('Ayarlar', self.show_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Çıkış', self.quit_app)
        )
        
        # System tray ikonunu oluştur
        self.icon = pystray.Icon(
            'DigiCollect',
            Image.open(icon_path),
            'DigiCollect',
            menu
        )
    
    def setup_hotkeys(self):
        # Ctrl+Shift+D kısayolu için listener ekle
        keyboard.add_hotkey('ctrl+shift+d', self.capture_content)
        
    def capture_content(self):
        """Seçili içeriği yakala ve DigiCollect'e gönder"""
        content = pyperclip.paste()
        if content:
            # İçeriği geçici olarak kaydet
            temp_data = {
                'content': content,
                'type': self.detect_content_type(content),
                'timestamp': str(datetime.now())
            }
            
            with open(Path.home() / '.digicollect' / 'temp_content.json', 'w') as f:
                json.dump(temp_data, f)
            
            # Ana uygulamayı aç
            self.show_main_window()
    
    def detect_content_type(self, content):
        """İçerik türünü tespit et"""
        # URL kontrolü
        if content.startswith(('http://', 'https://')):
            if any(service in content.lower() for service in ['youtube.com', 'youtu.be']):
                return 'video'
            elif any(service in content.lower() for service in ['spotify.com']):
                return 'music'
            elif any(service in content.lower() for service in ['twitter.com', 'x.com']):
                return 'tweet'
            elif any(service in content.lower() for service in ['instagram.com']):
                return 'instagram'
            return 'url'
        
        # Metin kontrolü
        return 'text'
    
    def show_main_window(self):
        """Ana DigiCollect penceresini göster"""
        # Ana uygulama çalışmıyorsa başlat
        if not self.is_app_running():
            self.start_main_app()
    
    def show_settings(self):
        """Ayarlar penceresini göster"""
        pass
    
    def quit_app(self):
        """Uygulamadan çık"""
        self.active = False
        self.icon.stop()
    
    def is_app_running(self):
        """Ana uygulamanın çalışıp çalışmadığını kontrol et"""
        # Burada process kontrolü yapılabilir
        return False
    
    def start_main_app(self):
        """Ana uygulamayı başlat"""
        app_path = Path(__file__).parent / 'main.py'
        os.system(f'python {app_path}')
    
    def run(self):
        """System tray uygulamasını başlat"""
        self.icon.run()

if __name__ == '__main__':
    tray = DigiCollectTray()
    tray.run()
