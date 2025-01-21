from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.image import AsyncImage
from kivy.properties import StringProperty, ObjectProperty
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.utils import platform
import pyperclip
import uuid

from services.content_processor import ContentProcessor

class ContentShareScreen(Screen):
    visibility = StringProperty('PRIVATE')
    share_link = StringProperty('')
    collection = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.content_processor = ContentProcessor()
        self._generate_share_link()
        
    def on_enter(self, *args):
        """Ekran açıldığında çalışır"""
        # Paylaşılan URL'i al ve işle
        shared_url = self.manager.shared_url
        if shared_url:
            self.process_shared_content(shared_url)
    
    def process_shared_content(self, url):
        """Paylaşılan içeriği işle"""
        # İçerik işleme servisini çağır
        result = self.content_processor.process_shared_content(url)
        
        if result['status'] == 'success':
            # Önizleme kartını oluştur
            preview_card = ContentPreviewCard()
            preview_card.title = result['metadata']['title']
            preview_card.description = result['metadata']['description']
            preview_card.source_info = result['source_info']['display']
            
            if result['metadata']['image']:
                preview_card.thumbnail = result['metadata']['image']
            
            # Kartı ekrana ekle
            self.ids.content_preview.clear_widgets()
            self.ids.content_preview.add_widget(preview_card)
            
            # Meta verileri sakla
            self.current_content = result
        else:
            # Hata durumunda kullanıcıya bilgi ver
            error_label = Label(
                text='İçerik yüklenirken bir hata oluştu.\nLütfen tekrar deneyin.',
                color=(1, 0, 0, 1)
            )
            self.ids.content_preview.clear_widgets()
            self.ids.content_preview.add_widget(error_label)
    
    def save_to_collection(self):
        """İçeriği seçili koleksiyona kaydet"""
        if hasattr(self, 'current_content'):
            collection_id = self.ids.collection_spinner.text
            
            # Koleksiyona kaydetme işlemi
            collection_item = {
                'content_type': self.current_content['platform'],
                'source_url': self.current_content['url'],
                'title': self.current_content['metadata']['title'],
                'description': self.current_content['metadata']['description'],
                'thumbnail_url': self.current_content['metadata'].get('image'),
                'source_info': self.current_content['source_info'],
                'metadata': self.current_content['metadata']
            }
            
            # Koleksiyon servisini çağır
            success = self.manager.add_to_collection(collection_id, collection_item)
            
            if success:
                # Başarılı mesajı göster ve ana ekrana dön
                self.show_success_message()
                Clock.schedule_once(lambda dt: self.manager.goto_main(), 2)
            else:
                # Hata mesajı göster
                self.show_error_message()
    
    def set_collection(self, collection):
        """Paylaşılacak koleksiyonu ayarla"""
        self.collection = collection
        self._generate_share_link()
    
    def set_visibility(self, visibility):
        """Koleksiyon görünürlüğünü ayarla"""
        self.visibility = visibility
        if visibility == 'UNLISTED':
            self._generate_share_link()
    
    def _generate_share_link(self):
        """Paylaşım linki oluştur"""
        if not self.collection:
            return
            
        base_url = "https://digicollect.app/collection"
        collection_id = self.collection.id
        share_token = str(uuid.uuid4())[:8]  # Kısa bir token oluştur
        
        self.share_link = f"{base_url}/{collection_id}?token={share_token}"
    
    def get_invite_message(self):
        """Davet mesajı oluştur"""
        if not self.collection:
            return ""
            
        collection_name = self.collection.name
        return f"Merhaba! DigiCollect'te '{collection_name}' adlı koleksiyonumu seninle paylaşmak istiyorum. İşte link: {self.share_link}"
    
    def copy_link(self):
        """Paylaşım linkini panoya kopyala"""
        pyperclip.copy(self.share_link)
        self._show_toast("Link kopyalandı!")
    
    def copy_invite_message(self):
        """Davet mesajını panoya kopyala"""
        pyperclip.copy(self.get_invite_message())
        self._show_toast("Davet mesajı kopyalandı!")
    
    def share(self):
        """Koleksiyonu paylaş"""
        if not self.collection:
            return
            
        # Koleksiyon görünürlüğünü güncelle
        self.collection.visibility = self.visibility
        self.collection.share_token = self.share_link.split("token=")[-1] if self.visibility == 'UNLISTED' else None
        self.collection.save()
        
        self._show_toast("Koleksiyon paylaşıldı!")
        self.manager.current = 'collection_view'
    
    def cancel(self):
        """İptal et ve geri dön"""
        self.manager.current = 'collection_view'
    
    def _show_toast(self, message):
        """Toast mesajı göster"""
        # Toast widget'ı eklenecek
        pass

class ContentPreviewCard(BoxLayout):
    title = StringProperty('')
    description = StringProperty('')
    thumbnail = StringProperty('')
    source_info = StringProperty('')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = dp(16)
        self.spacing = dp(8)
        
        # Thumbnail
        self.thumb = AsyncImage(
            source=self.thumbnail,
            size_hint_y=None,
            height=dp(200)
        )
        self.add_widget(self.thumb)
        
        # Başlık
        self.title_label = Label(
            text=self.title,
            size_hint_y=None,
            height=dp(40),
            bold=True
        )
        self.add_widget(self.title_label)
        
        # Açıklama
        self.desc_label = Label(
            text=self.description,
            size_hint_y=None,
            height=dp(60)
        )
        self.add_widget(self.desc_label)
        
        # Kaynak bilgisi
        self.source_label = Label(
            text=self.source_info,
            size_hint_y=None,
            height=dp(30),
            color=(0.5, 0.5, 0.5, 1)
        )
        self.add_widget(self.source_label)
