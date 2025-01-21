from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.properties import StringProperty, ListProperty, BooleanProperty, NumericProperty
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.uix.image import AsyncImage

from services.instagram_extractor import InstagramExtractor
import threading
from datetime import datetime

class MediaPreview(BoxLayout):
    """Medya önizleme kartı"""
    media_url = StringProperty('')
    media_type = StringProperty('image')
    is_selected = BooleanProperty(False)
    index = NumericProperty(0)
    
    def __init__(self, media_data, index, **kwargs):
        super().__init__(**kwargs)
        self.media_data = media_data
        self.index = index
        self.media_type = media_data['type']
        
        if media_data['type'] == 'video':
            self.media_url = media_data['thumbnail_url']
        else:
            self.media_url = media_data['url']
    
    def toggle_selection(self):
        """Medya seçimini değiştir"""
        self.is_selected = not self.is_selected

class InstagramCutterScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.instagram_extractor = InstagramExtractor()
        self.post_data = None
        self.selected_media = set()
    
    def on_enter(self, *args):
        """Ekran açıldığında çalışır"""
        # Paylaşılan URL'i al
        shared_url = self.manager.shared_url
        if shared_url:
            self.process_post(shared_url)
    
    def process_post(self, url):
        """Instagram gönderisini işle"""
        # Yükleniyor göstergesini başlat
        self.ids.loading_indicator.active = True
        
        # Arka planda gönderiyi çek
        threading.Thread(target=self._extract_post, args=(url,)).start()
    
    def _extract_post(self, url):
        """Arka planda gönderiyi çek"""
        result = self.instagram_extractor.get_post(url)
        
        # Ana thread'de UI güncelleme
        Clock.schedule_once(lambda dt: self._handle_post_result(result))
    
    def _handle_post_result(self, result):
        """Gönderi sonucunu işle"""
        self.ids.loading_indicator.active = False
        
        if result['status'] == 'success':
            # Gönderi verilerini sakla
            self.post_data = result['post']
            
            # Gönderi bilgilerini göster
            self.ids.username.text = f"@{self.post_data['author']['username']}"
            self.ids.full_name.text = self.post_data['author']['full_name']
            self.ids.caption.text = self.instagram_extractor.format_caption(
                self.post_data['caption']
            )
            
            # Profil resmini ayarla
            self.ids.profile_image.source = self.post_data['author']['profile_pic_url']
            
            # Medya önizlemelerini oluştur
            self._create_media_previews()
            
            # İstatistikleri göster
            self.ids.stats_label.text = (
                f"❤️ {self.post_data['likes']} "
                f"💬 {self.post_data['comments']}"
            )
            
            if self.post_data['location']:
                self.ids.location.text = f"📍 {self.post_data['location']}"
            
        else:
            # Hata mesajını göster
            self.ids.error_label.text = f"Gönderi yüklenemedi: {result['error']}"
            self.ids.error_label.opacity = 1
    
    def _create_media_previews(self):
        """Medya önizlemelerini oluştur"""
        # Medya container'ı temizle
        self.ids.media_container.clear_widgets()
        
        # Her medya için önizleme oluştur
        for i, media in enumerate(self.post_data['media']):
            preview = MediaPreview(media, i)
            self.ids.media_container.add_widget(preview)
    
    def on_media_selection(self, media_preview):
        """Medya seçimi değiştiğinde"""
        if media_preview.is_selected:
            self.selected_media.add(media_preview.index)
        else:
            self.selected_media.discard(media_preview.index)
        
        # Kaydet butonunu güncelle
        self.ids.save_button.disabled = len(self.selected_media) == 0
    
    def save_selection(self):
        """Seçili medyaları koleksiyona kaydet"""
        if self.post_data and self.selected_media:
            # Seçili medyaları filtrele
            selected_media = [
                self.post_data['media'][i]
                for i in sorted(self.selected_media)
            ]
            
            collection_item = {
                'content_type': 'instagram',
                'source_url': self.manager.shared_url,
                'media': selected_media,
                'caption': self.post_data['caption'],
                'author': self.post_data['author'],
                'created_at': self.post_data['created_at'],
                'is_carousel': self.post_data['is_carousel'],
                'metadata': {
                    'media_count': len(selected_media),
                    'likes': self.post_data['likes'],
                    'comments': self.post_data['comments'],
                    'location': self.post_data['location'],
                    'hashtags': self.post_data['hashtags'],
                    'mentions': self.post_data['mentions']
                }
            }
            
            # Koleksiyon servisini çağır
            success = self.manager.add_to_collection(
                self.ids.collection_spinner.text,
                collection_item
            )
            
            if success:
                # Başarılı mesajı göster ve ana ekrana dön
                self.show_success_message()
                Clock.schedule_once(lambda dt: self.manager.goto_main(), 2)
            else:
                # Hata mesajı göster
                self.show_error_message()
    
    def on_leave(self):
        """Ekrandan çıkıldığında temizlik yap"""
        if hasattr(self, 'instagram_extractor'):
            self.instagram_extractor.cleanup()
        self.post_data = None
        self.selected_media.clear()
