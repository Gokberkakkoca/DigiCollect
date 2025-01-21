from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.modalview import ModalView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.properties import StringProperty, NumericProperty, ListProperty
from kivy.animation import Animation
from kivy.metrics import dp
from kivy.clock import Clock

class FloatingActionButton(ButtonBehavior, FloatLayout):
    icon = StringProperty('plus')
    background_color = ListProperty([0.129, 0.588, 0.953, 1])  # Material Blue
    elevation = NumericProperty(6)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(56), dp(56))
        self.pos_hint = {'right': 0.95, 'y': 0.1}
        self._create_button()
        self._create_menu()
        self.register_event_type('on_action_selected')
        
    def _create_button(self):
        """Ana floating button'u oluştur"""
        self.button_image = Image(
            source=f'assets/icons/{self.icon}.png',
            size_hint=(None, None),
            size=(dp(24), dp(24)),
            pos_hint={'center_x': .5, 'center_y': .5}
        )
        self.add_widget(self.button_image)
        
    def _create_menu(self):
        """Floating button menüsünü oluştur"""
        self.menu = FloatingActionMenu()
        self.menu.add_action(
            icon='video',
            text='Video Kesiti',
            on_press=lambda x: self.dispatch('on_action_selected', 'video')
        )
        self.menu.add_action(
            icon='music-note',
            text='Müzik Kesiti',
            on_press=lambda x: self.dispatch('on_action_selected', 'music')
        )
        self.menu.add_action(
            icon='text',
            text='Blog Yazısı',
            on_press=lambda x: self.dispatch('on_action_selected', 'blog')
        )
        self.menu.add_action(
            icon='twitter',
            text='Tweet',
            on_press=lambda x: self.dispatch('on_action_selected', 'tweet')
        )
        self.menu.add_action(
            icon='instagram',
            text='Instagram',
            on_press=lambda x: self.dispatch('on_action_selected', 'instagram')
        )
        
    def on_press(self):
        """Butona basıldığında menüyü göster"""
        anim = Animation(elevation=2, duration=0.1)
        anim.start(self)
        self.menu.open()
        
    def on_release(self):
        """Buton bırakıldığında animasyonu geri al"""
        anim = Animation(elevation=6, duration=0.1)
        anim.start(self)
        
    def on_action_selected(self, action_type):
        """Menüden bir eylem seçildiğinde"""
        pass

class FloatingActionMenu(ModalView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(200), dp(300))
        self.background_color = [0, 0, 0, 0.5]
        self.auto_dismiss = True
        
        self.layout = GridLayout(
            cols=1,
            spacing=dp(8),
            padding=dp(8),
            size_hint_y=None
        )
        self.layout.bind(minimum_height=self.layout.setter('height'))
        self.add_widget(self.layout)
        
    def add_action(self, icon, text, on_press):
        """Menüye yeni bir eylem ekle"""
        action = FloatingActionMenuItem(
            icon=icon,
            text=text,
            on_press=on_press
        )
        self.layout.add_widget(action)
        
class FloatingActionMenuItem(ButtonBehavior, GridLayout):
    def __init__(self, icon, text, **kwargs):
        super().__init__(**kwargs)
        self.cols = 2
        self.size_hint_y = None
        self.height = dp(48)
        self.padding = [dp(16), dp(8)]
        self.spacing = dp(16)
        
        # İkon
        self.icon = Image(
            source=f'assets/icons/{icon}.png',
            size_hint=(None, None),
            size=(dp(24), dp(24))
        )
        
        # Metin
        self.label = Label(
            text=text,
            color=[0, 0, 0, 1],
            size_hint_x=None,
            width=dp(120),
            halign='left'
        )
        
        self.add_widget(self.icon)
        self.add_widget(self.label)
