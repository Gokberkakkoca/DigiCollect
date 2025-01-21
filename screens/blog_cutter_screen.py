from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.properties import StringProperty, ObjectProperty, NumericProperty
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.window import Window

from services.blog_extractor import BlogExtractor
import threading
import re

class BlogCutterScreen(Screen):
    content = StringProperty('')
    selected_text = StringProperty('')
    reading_time = NumericProperty(0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.blog_extractor = BlogExtractor()
        self.article_info = None
        
    def on_enter(self, *args):
        """Ekran açıldığında çalışır"""
        # Paylaşılan URL'i al
        shared_url = self.manager.shared_url
        if shared_url:
            self.process_blog(shared_url)
    
    def process_blog(self, url):
        """Blog URL'ini işle"""
        # Yükleniyor göstergesini başlat
        self.ids.loading_indicator.active = True
        
        # Arka planda blog içeriğini çek
        threading.Thread(target=self._extract_blog, args=(url,)).start()
    
    def _extract_blog(self, url):
        """Arka planda blog içeriğini çek"""
        result = self.blog_extractor.extract_content(url)
        
        # Ana thread'de UI güncelleme
        Clock.schedule_once(lambda dt: self._handle_extraction_result(result))
    
    def _handle_extraction_result(self, result):
        """Çekme sonucunu işle"""
        self.ids.loading_indicator.active = False
        
        if result['status'] == 'success':
            # Blog bilgilerini sakla
            self.article_info = result
            
            # İçeriği göster
            self.content = result['content']
            
            # Blog bilgilerini göster
            self.ids.blog_title.text = result['title']
            self.ids.blog_author.text = f"Yazar: {result['author']}"
            
            # Okuma süresini hesapla ve göster
            self.reading_time = self.blog_extractor.get_reading_time(result['content'])
            self.ids.reading_time.text = f"Okuma Süresi: {self.reading_time} dk"
            
            # Metin seçiciyi etkinleştir
            self.ids.content_input.disabled = False
            
        else:
            # Hata mesajını göster
            self.ids.error_label.text = f"Blog yüklenemedi: {result['error']}"
            self.ids.error_label.opacity = 1
    
    def on_text_selection(self, instance, value):
        """Metin seçimi değiştiğinde"""
        if value:
            start = instance.selection_from
            end = instance.selection_to
            
            if start > end:
                start, end = end, start
                
            self.selected_text = instance.text[start:end]
            
            # Seçili metni önizle
            self.ids.preview_label.text = self.selected_text[:200] + "..." if len(self.selected_text) > 200 else self.selected_text
            
            # Kaydet butonunu etkinleştir
            self.ids.save_button.disabled = False
    
    def save_selection(self):
        """Seçili metni koleksiyona kaydet"""
        if self.article_info and self.selected_text:
            collection_item = {
                'content_type': 'blog',
                'source_url': self.article_info['url'],
                'title': self.article_info['title'],
                'author': self.article_info['author'],
                'platform': self.article_info.get('platform', 'website'),
                'selected_content': self.selected_text,
                'reading_time': self.blog_extractor.get_reading_time(self.selected_text),
                'metadata': {
                    'original_title': self.article_info['title'],
                    'original_author': self.article_info['author'],
                    'original_date': self.article_info['date'],
                    'selection_length': len(self.selected_text)
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
        self.content = ''
        self.selected_text = ''
        self.article_info = None
