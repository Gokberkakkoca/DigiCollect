from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, NumericProperty, ObjectProperty
from kivy.clock import Clock
from services.content_processor import ContentProcessor

class ContentCutterScreen(Screen):
    content_type = StringProperty('')
    content_data = ObjectProperty(None)
    
    # Video/Ses özellikleri
    media_duration = NumericProperty(0)
    current_time = NumericProperty(0)
    start_time = NumericProperty(0)
    end_time = NumericProperty(0)
    
    # Metin özellikleri
    text_content = StringProperty('')
    selected_text = StringProperty('')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.content_processor = ContentProcessor()
    
    def set_content(self, content_data):
        """İçeriği ayarla ve uygun kesme aracını göster"""
        self.content_data = content_data
        self.content_type = content_data.get('type', '')
        
        if self.content_type in ['video', 'audio']:
            self.setup_media_cutter()
        elif self.content_type == 'text':
            self.setup_text_cutter()
        elif self.content_type == 'image':
            self.setup_image_cutter()
    
    def setup_media_cutter(self):
        """Video/Ses kesme aracını hazırla"""
        # Medya süresini al
        duration = float(self.content_data.get('duration', 0))
        self.media_duration = duration
        self.end_time = duration
        
        # Medya oynatıcıyı hazırla
        # TODO: Medya oynatıcı widget'ı eklenecek
    
    def setup_text_cutter(self):
        """Metin kesme aracını hazırla"""
        self.text_content = self.content_data.get('content', '')
    
    def setup_image_cutter(self):
        """Görsel kesme aracını hazırla"""
        # TODO: Görsel kırpma widget'ı eklenecek
        pass
    
    def seek_media(self, time):
        """Medyada belirtilen zamana git"""
        self.current_time = time
        # TODO: Medya oynatıcıyı güncelle
    
    def set_start_time(self):
        """Kesit başlangıç zamanını ayarla"""
        self.start_time = self.current_time
    
    def set_end_time(self):
        """Kesit bitiş zamanını ayarla"""
        self.end_time = self.current_time
    
    def update_text_selection(self):
        """Seçili metni güncelle"""
        text_input = self.ids.text_content
        if text_input.selection_text:
            self.selected_text = text_input.selection_text
    
    def preview_cut(self):
        """Kesiti önizle"""
        if self.content_type in ['video', 'audio']:
            cut_params = {
                'start_time': self.start_time,
                'end_time': self.end_time
            }
        elif self.content_type == 'text':
            text_input = self.ids.text_content
            cut_params = {
                'start_index': text_input.selection_from,
                'end_index': text_input.selection_to
            }
        elif self.content_type == 'image':
            crop_tool = self.ids.crop_tool
            cut_params = {
                'x': crop_tool.x,
                'y': crop_tool.y,
                'width': crop_tool.width,
                'height': crop_tool.height
            }
        else:
            return
        
        # İçeriği kes
        cut_result = self.content_processor.cut_content(
            self.content_data,
            cut_params
        )
        
        # Önizleme göster
        if cut_result.get('error'):
            self.show_error(cut_result['error'])
        else:
            self.show_preview(cut_result)
    
    def save_cut(self):
        """Kesiti kaydet"""
        # TODO: Kesiti koleksiyona kaydet
        pass
    
    def format_time(self, seconds):
        """Saniyeyi dakika:saniye formatına çevir"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def go_back(self):
        """Önceki ekrana dön"""
        self.manager.current = 'content_share'
    
    def show_error(self, message):
        """Hata mesajı göster"""
        # TODO: Hata mesajı gösterme widget'ı eklenecek
        pass
    
    def show_preview(self, cut_result):
        """Kesit önizlemesi göster"""
        # TODO: Önizleme widget'ı eklenecek
        pass
