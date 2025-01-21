from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import AsyncImage
from kivy.properties import NumericProperty, StringProperty, ObjectProperty
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.animation import Animation

from services.music_cutter import MusicCutter
import threading
import os

class MusicCutterScreen(Screen):
    current_time = NumericProperty(0)
    music_duration = NumericProperty(0)
    start_time = NumericProperty(0)
    end_time = NumericProperty(0)
    waveform_path = StringProperty('')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.music_cutter = MusicCutter()
        self.music_info = None
        
    def on_enter(self, *args):
        """Ekran açıldığında çalışır"""
        # Paylaşılan URL'i al
        shared_url = self.manager.shared_url
        if shared_url:
            self.process_music(shared_url)
    
    def process_music(self, url):
        """Müzik URL'ini işle"""
        # Yükleniyor göstergesini başlat
        self.ids.loading_indicator.active = True
        
        # Arka planda müzik indirme işlemini başlat
        threading.Thread(target=self._download_music, args=(url,)).start()
    
    def _download_music(self, url):
        """Arka planda müzik indirme"""
        result = self.music_cutter.download_music(url)
        
        # Ana thread'de UI güncelleme
        Clock.schedule_once(lambda dt: self._handle_download_result(result))
    
    def _handle_download_result(self, result):
        """İndirme sonucunu işle"""
        self.ids.loading_indicator.active = False
        
        if result['status'] == 'success':
            # Müzik bilgilerini sakla
            self.music_info = result
            
            # Müzik süresini ayarla
            music_info = self.music_cutter.get_music_info(result['file_path'])
            if music_info['status'] == 'success':
                self.music_duration = music_info['duration']
                self.end_time = music_info['duration']
            
            # Dalga formunu oluştur
            self._generate_waveform()
            
            # Müzik bilgilerini göster
            self.ids.music_title.text = result['title']
            if 'artist' in result:
                self.ids.music_artist.text = result['artist']
            self.ids.music_duration_label.text = self._format_time(self.music_duration)
            
            # Kesme kontrollerini etkinleştir
            self.ids.time_slider.disabled = False
            self.ids.cut_button.disabled = False
            
        else:
            # Hata mesajını göster
            self.ids.error_label.text = f"Müzik yüklenemedi: {result['error']}"
            self.ids.error_label.opacity = 1
    
    def _generate_waveform(self):
        """Dalga formu görüntüsü oluştur"""
        if self.music_info:
            result = self.music_cutter.generate_waveform(
                self.music_info['file_path'],
                width=int(self.width * 2),  # Retina display için 2x
                height=400
            )
            
            if result['status'] == 'success':
                self.waveform_path = result['waveform_path']
    
    def update_time_selection(self, value):
        """Zaman seçimini güncelle"""
        if isinstance(value, tuple):
            self.start_time, self.end_time = value
            
            # Etiketleri güncelle
            self.ids.start_time_label.text = self._format_time(self.start_time)
            self.ids.end_time_label.text = self._format_time(self.end_time)
    
    def cut_music(self):
        """Seçili aralıkta müziği kes"""
        if self.music_info:
            # Yükleniyor göstergesini başlat
            self.ids.loading_indicator.active = True
            
            # Arka planda kesme işlemini başlat
            threading.Thread(target=self._cut_music).start()
    
    def _cut_music(self):
        """Arka planda müzik kesme"""
        result = self.music_cutter.cut_music(
            self.music_info['file_path'],
            self.start_time,
            self.end_time
        )
        
        # Ana thread'de UI güncelleme
        Clock.schedule_once(lambda dt: self._handle_cut_result(result))
    
    def _handle_cut_result(self, result):
        """Kesme sonucunu işle"""
        self.ids.loading_indicator.active = False
        
        if result['status'] == 'success':
            # Kesilen müziği koleksiyona ekle
            self._save_to_collection(result['output_path'])
        else:
            # Hata mesajını göster
            self.ids.error_label.text = f"Müzik kesilemedi: {result['error']}"
            self.ids.error_label.opacity = 1
    
    def _save_to_collection(self, music_path):
        """Kesilen müziği koleksiyona ekle"""
        if self.music_info:
            collection_item = {
                'content_type': 'music',
                'source_url': self.manager.shared_url,
                'cut_data': {
                    'start_time': self.start_time,
                    'end_time': self.end_time,
                    'duration': self.end_time - self.start_time
                },
                'title': self.music_info['title'],
                'artist': self.music_info.get('artist', ''),
                'waveform': self.waveform_path,
                'metadata': self.music_info.get('metadata', {})
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
        if hasattr(self, 'music_cutter'):
            self.music_cutter.cleanup()
