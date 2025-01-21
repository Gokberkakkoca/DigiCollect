from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from auth import Auth

class LoginScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 10
        self.spacing = 10
        
        # Email girişi
        self.email_input = TextInput(
            multiline=False,
            hint_text='Email',
            size_hint_y=None,
            height=40
        )
        self.add_widget(self.email_input)
        
        # Test email gönder butonu
        self.test_button = Button(
            text='Test Email Gönder',
            size_hint_y=None,
            height=40
        )
        self.test_button.bind(on_press=self.send_test_email)
        self.add_widget(self.test_button)
        
        # Sonuç etiketi
        self.result_label = Label(text='')
        self.add_widget(self.result_label)
    
    def send_test_email(self, instance):
        email = self.email_input.text
        if email:
            try:
                if Auth.send_test_email(email):
                    self.result_label.text = f'Test email {email} adresine gönderildi!'
                else:
                    self.result_label.text = 'Email gönderilemedi!'
            except Exception as e:
                self.result_label.text = f'Hata: {str(e)}'
        else:
            self.result_label.text = 'Lütfen email adresinizi girin!'

class TestApp(App):
    def build(self):
        return LoginScreen()

if __name__ == '__main__':
    TestApp().run()
