from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.properties import StringProperty, NumericProperty
from kivy.animation import Animation
from kivy.core.window import Window
from kivy.metrics import dp

class FloatingButton(ButtonBehavior, FloatLayout):
    icon = StringProperty('plus')
    background_color = StringProperty('#2196F3')
    elevation = NumericProperty(8)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(56), dp(56))
        self.pos_hint = {'right': 0.95, 'top': 0.1}
        self._create_button()
        
    def _create_button(self):
        self.button_image = Image(
            source=f'assets/icons/{self.icon}.png',
            size_hint=(None, None),
            size=(dp(24), dp(24)),
            pos_hint={'center_x': .5, 'center_y': .5}
        )
        self.add_widget(self.button_image)
        
    def on_press(self):
        anim = Animation(elevation=2, duration=0.1)
        anim.start(self)
        
    def on_release(self):
        anim = Animation(elevation=8, duration=0.1)
        anim.start(self)
        
    def show(self):
        anim = Animation(opacity=1, duration=0.2)
        anim.start(self)
        
    def hide(self):
        anim = Animation(opacity=0, duration=0.2)
        anim.start(self)
