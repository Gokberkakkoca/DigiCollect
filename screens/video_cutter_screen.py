from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import AsyncImage
from kivy.properties import NumericProperty, StringProperty, ObjectProperty
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.animation import Animation

from services.video_cutter import VideoCutter
import threading
import os

class VideoCutterScreen(Screen):
    current_time = NumericProperty(0)
    video_duration = NumericProperty(0)
    start_time = NumericProperty(0)
    end_time = NumericProperty(0)
    thumbnail_path = StringProperty('')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.video_cutter = VideoCutter()
        self.video_info = None
        
    def on_enter(self, *args):
        """Ekran açıldığında çalışır"""
        # Paylaşılan URL'i al
        shared_url = self.manager.shared_url
        if shared_url:
            self.process_video(shared_url)
    
    def process_video(self, url):
        """Video URL'ini işle"""
        # Yükleniyor göstergesini başlat
        self.ids.loading_indicator.active = True
        
        # Arka planda video indirme işlemini başlat
        threading.Thread(target=self._download_video, args=(url,)).start()
    
    def _download_video(self, url):
        """Arka planda video indirme"""
        result = self.video_cutter.download_video(url)
        
        # Ana thread'de UI güncelleme
        Clock.schedule_once(lambda dt: self._handle_download_result(result))
    
    def _handle_download_result(self, result):
        """İndirme sonucunu işle"""
        self.ids.loading_indicator.active = False
        
        if result['status'] == 'success':
            # Video bilgilerini sakla
            self.video_info = result
            
            # Video süresini ayarla
            self.video_duration = result['duration']
            self.end_time = result['duration']
            
            # Thumbnail'i göster
            self.thumbnail_path = result['thumbnail']
            
            # Video bilgilerini göster
            self.ids.video_title.text = result['title']
            self.ids.video_duration_label.text = self._format_time(result['duration'])
            
            # Kesme kontrollerini etkinleştir
            self.ids.time_slider.disabled = False
            self.ids.cut_button.disabled = False
            
        else:
            # Hata mesajını göster
            self.ids.error_label.text = f"Video yüklenemedi: {result['error']}"
            self.ids.error_label.opacity = 1
    
    def update_time_selection(self, value):
        """Zaman seçimini güncelle"""
        if isinstance(value, tuple):
            self.start_time, self.end_time = value
            
            # Etiketleri güncelle
            self.ids.start_time_label.text = self._format_time(self.start_time)
            self.ids.end_time_label.text = self._format_time(self.end_time)
            
            # Seçili aralığın thumbnail'ini oluştur
            self._generate_preview()
    
    def _generate_preview(self):
        """Seçili zaman aralığından önizleme oluştur"""
        if self.video_info:
            # Ortadaki zamandan thumbnail oluştur
            preview_time = (self.start_time + self.end_time) / 2
            result = self.video_cutter.generate_thumbnail(
                self.video_info['file_path'],
                preview_time
            )
            
            if result['status'] == 'success':
                self.thumbnail_path = result['thumbnail_path']
    
    def cut_video(self):
        """Seçili aralıkta videoyu kes"""
        if self.video_info:
            # Yükleniyor göstergesini başlat
            self.ids.loading_indicator.active = True
            
            # Arka planda kesme işlemini başlat
            threading.Thread(target=self._cut_video).start()
    
    def _cut_video(self):
        """Arka planda video kesme"""
        result = self.video_cutter.cut_video(
            self.video_info['file_path'],
            self.start_time,
            self.end_time
        )
        
        # Ana thread'de UI güncelleme
        Clock.schedule_once(lambda dt: self._handle_cut_result(result))
    
    def _handle_cut_result(self, result):
        """Kesme sonucunu işle"""
        self.ids.loading_indicator.active = False
        
        if result['status'] == 'success':
            # Kesilen videoyu koleksiyona ekle
            self._save_to_collection(result['output_path'])
        else:
            # Hata mesajını göster
            self.ids.error_label.text = f"Video kesilemedi: {result['error']}"
            self.ids.error_label.opacity = 1
    
    def _save_to_collection(self, video_path):
        """Kesilen videoyu koleksiyona ekle"""
        if self.video_info:
            collection_item = {
                'content_type': 'video',
                'source_url': self.manager.shared_url,
                'cut_data': {
                    'start_time': self.start_time,
                    'end_time': self.end_time,
                    'duration': self.end_time - self.start_time
                },
                'title': self.video_info['title'],
                'thumbnail': self.thumbnail_path,
                'metadata': self.video_info['metadata']
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
    
    def _format_time(self, seconds):
        """Saniyeyi dakika:saniye formatına çevir"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def on_leave(self):
        """Ekrandan çıkıldığında temizlik yap"""
        if hasattr(self, 'video_cutter'):
            self.video_cutter.cleanup()
