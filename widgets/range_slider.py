from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ReferenceListProperty, ListProperty
from kivy.metrics import dp
from kivy.core.window import Window

class RangeSlider(Widget):
    min = NumericProperty(0)
    max = NumericProperty(100)
    start = NumericProperty(0)
    end = NumericProperty(100)
    value = ReferenceListProperty(start, end)
    
    # Kaydırıcı renkleri
    track_color = ListProperty([0.3, 0.3, 0.3, 1])
    active_color = ListProperty([0.2, 0.6, 1, 1])
    handle_color = ListProperty([0.2, 0.6, 1, 1])
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(size=self._update_value_pos)
        self.bind(pos=self._update_value_pos)
        self._dragging = None  # 'start' veya 'end' tutacağı sürükleniyor mu
        
        # Minimum tutacak aralığı (saniye cinsinden)
        self.min_range = 3
        
        # Tutacak boyutları
        self.handle_width = dp(20)
        self.handle_height = dp(30)
    
    def _update_value_pos(self, *args):
        """Değer pozisyonlarını güncelle"""
        self.value_pos = (
            self.x + (self.start - self.min) * self.width / (self.max - self.min),
            self.x + (self.end - self.min) * self.width / (self.max - self.min)
        )
    
    def _get_value_from_pos(self, pos):
        """Pozisyondan değer hesapla"""
        x = pos[0]
        value = self.min + (x - self.x) * (self.max - self.min) / self.width
        return min(max(value, self.min), self.max)
    
    def _is_handle_touched(self, touch_x, handle_x):
        """Tutacağa dokunuldu mu kontrol et"""
        return abs(touch_x - handle_x) <= self.handle_width / 2
    
    def on_touch_down(self, touch):
        """Dokunma başladığında"""
        if self.collide_point(*touch.pos):
            # Hangi tutacağa dokunulduğunu kontrol et
            if self._is_handle_touched(touch.x, self.value_pos[0]):
                self._dragging = 'start'
                return True
            elif self._is_handle_touched(touch.x, self.value_pos[1]):
                self._dragging = 'end'
                return True
            
            # Tutacaklar arasındaki çubuğa dokunuldu mu
            if self.value_pos[0] <= touch.x <= self.value_pos[1]:
                self._dragging = 'both'
                self._drag_offset = (
                    touch.x - self.value_pos[0],
                    self.value_pos[1] - touch.x
                )
                return True
        return super().on_touch_down(touch)
    
    def on_touch_move(self, touch):
        """Dokunma hareket ettiğinde"""
        if self._dragging:
            if self._dragging == 'start':
                # Başlangıç tutacağını sürükle
                new_start = self._get_value_from_pos(touch.pos)
                if new_start < self.end - self.min_range:
                    self.start = new_start
                
            elif self._dragging == 'end':
                # Bitiş tutacağını sürükle
                new_end = self._get_value_from_pos(touch.pos)
                if new_end > self.start + self.min_range:
                    self.end = new_end
                    
            elif self._dragging == 'both':
                # Her iki tutacağı birlikte sürükle
                new_start = self._get_value_from_pos((touch.x - self._drag_offset[0], touch.y))
                new_end = self._get_value_from_pos((touch.x + self._drag_offset[1], touch.y))
                
                # Sınırları kontrol et
                if new_start >= self.min and new_end <= self.max:
                    self.start = new_start
                    self.end = new_end
            
            self._update_value_pos()
            return True
        return super().on_touch_move(touch)
    
    def on_touch_up(self, touch):
        """Dokunma bittiğinde"""
        if self._dragging:
            self._dragging = None
            return True
        return super().on_touch_up(touch)
