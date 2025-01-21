from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.properties import StringProperty, ListProperty, NumericProperty, ObjectProperty, BooleanProperty
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.button import Button
from kivy.core.clipboard import Clipboard
from kivy.utils import get_color_from_hex

from services.collection_manager import CollectionManager
import threading
from datetime import datetime

class CollectionCard(BoxLayout):
    """Koleksiyon kartı"""
    collection_id = NumericProperty(0)
    name = StringProperty('')
    description = StringProperty('')
    cover_image = StringProperty('')
    item_count = NumericProperty(0)
    created_at = StringProperty('')
    visibility = StringProperty('private')
    is_owner = BooleanProperty(False)
    is_following = BooleanProperty(False)
    follower_count = NumericProperty(0)
    share_token = StringProperty('')
    
    def __init__(self, collection_data, **kwargs):
        super().__init__(**kwargs)
        self.collection_id = collection_data['id']
        self.name = collection_data['name']
        self.description = collection_data.get('description', '')
        self.cover_image = collection_data.get('cover_image', '')
        self.item_count = collection_data['item_count']
        self.visibility = collection_data.get('visibility', 'private')
        self.is_owner = collection_data.get('is_owner', False)
        self.is_following = collection_data.get('is_following', False)
        self.follower_count = collection_data.get('follower_count', 0)
        self.share_token = collection_data.get('share_token', '')
        
        # Tarihi formatla
        created_at = datetime.fromisoformat(collection_data['created_at'])
        self.created_at = created_at.strftime("%d %b %Y")
    
    def toggle_follow(self):
        """Takip durumunu değiştir"""
        app = App.get_running_app()
        if self.is_following:
            result = app.collection_manager.unfollow_collection(
                app.current_user_id,
                self.collection_id
            )
        else:
            result = app.collection_manager.follow_collection(
                app.current_user_id,
                self.collection_id
            )
        
        if result['status'] == 'success':
            self.is_following = not self.is_following
            self.follower_count += 1 if self.is_following else -1
    
    def share_collection(self):
        """Koleksiyonu paylaş"""
        share_text = f"DigiCollect Koleksiyonu: {self.name}\n\n"
        
        if self.visibility == 'unlisted':
            share_url = f"https://digicollect.app/c/{self.share_token}"
        else:
            share_url = f"https://digicollect.app/collections/{self.collection_id}"
        
        share_text += share_url
        
        # Panoya kopyala
        Clipboard.copy(share_text)
        
        # Bildirim göster
        toast("Paylaşım bağlantısı kopyalandı!")
    
    def show_visibility_dialog(self):
        """Görünürlük ayarları dialogunu göster"""
        if not self.is_owner:
            return
            
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        
        # Görünürlük seçenekleri
        visibility_group = BoxLayout(orientation='vertical', spacing=dp(5))
        
        private_btn = ToggleButton(
            text='Özel',
            group='visibility',
            state='down' if self.visibility == 'private' else 'normal'
        )
        public_btn = ToggleButton(
            text='Herkese Açık',
            group='visibility',
            state='down' if self.visibility == 'public' else 'normal'
        )
        unlisted_btn = ToggleButton(
            text='Bağlantıya Sahip Olanlar',
            group='visibility',
            state='down' if self.visibility == 'unlisted' else 'normal'
        )
        
        visibility_group.add_widget(private_btn)
        visibility_group.add_widget(public_btn)
        visibility_group.add_widget(unlisted_btn)
        
        content.add_widget(visibility_group)
        
        # Kaydet butonu
        def save_visibility(instance):
            if private_btn.state == 'down':
                new_visibility = 'private'
            elif public_btn.state == 'down':
                new_visibility = 'public'
            else:
                new_visibility = 'unlisted'
            
            app = App.get_running_app()
            result = app.collection_manager.set_visibility(self.collection_id, new_visibility)
            
            if result['status'] == 'success':
                self.visibility = new_visibility
                if new_visibility == 'unlisted':
                    self.share_token = result['share_token']
                popup.dismiss()
                
                # Bildirim göster
                toast("Görünürlük ayarları güncellendi!")
        
        save_btn = Button(
            text='Kaydet',
            size_hint_y=None,
            height=dp(50)
        )
        save_btn.bind(on_release=save_visibility)
        
        content.add_widget(save_btn)
        
        # Popup oluştur
        popup = Popup(
            title='Görünürlük Ayarları',
            content=content,
            size_hint=(0.8, 0.4)
        )
        
        popup.open()

class ItemCard(BoxLayout):
    """Koleksiyon öğesi kartı"""
    item_id = NumericProperty(0)
    content_type = StringProperty('')
    title = StringProperty('')
    description = StringProperty('')
    thumbnail = StringProperty('')
    created_at = StringProperty('')
    
    def __init__(self, item_data, **kwargs):
        super().__init__(**kwargs)
        self.item_id = item_data['id']
        self.content_type = item_data['content_type']
        self.title = item_data.get('title', '')
        self.description = item_data.get('description', '')
        self.thumbnail = item_data.get('thumbnail_path', '')
        
        # Tarihi formatla
        created_at = datetime.fromisoformat(item_data['created_at'])
        self.created_at = created_at.strftime("%d %b %Y")

class CreateCollectionPopup(Popup):
    """Yeni koleksiyon oluşturma popup'ı"""
    def __init__(self, on_create=None, **kwargs):
        super().__init__(**kwargs)
        self.on_create = on_create
    
    def create_collection(self):
        """Yeni koleksiyon oluştur"""
        name = self.ids.name_input.text.strip()
        description = self.ids.description_input.text.strip()
        
        if name:
            if self.on_create:
                self.on_create(name, description)
            self.dismiss()

class CollectionManagerScreen(Screen):
    current_collection_id = NumericProperty(None)
    current_tab = StringProperty('my_collections')  # my_collections, public, following
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.collection_manager = CollectionManager()
        
        # Koleksiyonları yükle
        self.load_collections()
    
    def switch_tab(self, tab_name):
        """Sekme değiştir"""
        self.current_tab = tab_name
        self.load_collections()
    
    def load_collections(self):
        """Koleksiyonları yükle"""
        # Yükleniyor göstergesini başlat
        self.ids.loading_indicator.active = True
        
        # Arka planda koleksiyonları çek
        threading.Thread(target=self._load_collections).start()
    
    def _load_collections(self):
        """Arka planda koleksiyonları çek"""
        app = App.get_running_app()
        
        if self.current_tab == 'my_collections':
            result = self.collection_manager.list_collections()
        elif self.current_tab == 'public':
            result = self.collection_manager.get_public_collections()
        else:  # following
            result = self.collection_manager.get_followed_collections(app.current_user_id)
        
        # Ana thread'de UI güncelleme
        Clock.schedule_once(lambda dt: self._handle_collections_result(result))
    
    def _handle_collections_result(self, result):
        """Koleksiyon sonucunu işle"""
        self.ids.loading_indicator.active = False
        
        if result['status'] == 'success':
            # Koleksiyon container'ı temizle
            self.ids.collections_container.clear_widgets()
            
            # Her koleksiyon için kart oluştur
            for collection in result['collections']:
                # Koleksiyon sahibini belirle
                app = App.get_running_app()
                is_owner = collection.get('owner', {}).get('id') == app.current_user_id
                
                # Takip durumunu belirle
                is_following = False
                if not is_owner and self.current_tab != 'following':
                    follow_result = self.collection_manager.is_following(
                        app.current_user_id,
                        collection['id']
                    )
                    is_following = follow_result.get('is_following', False)
                elif self.current_tab == 'following':
                    is_following = True
                
                # Kart verilerini hazırla
                card_data = {
                    **collection,
                    'is_owner': is_owner,
                    'is_following': is_following
                }
                
                card = CollectionCard(card_data)
                self.ids.collections_container.add_widget(card)
            
        else:
            # Hata mesajını göster
            self.ids.error_label.text = f"Koleksiyonlar yüklenemedi: {result['error']}"
            self.ids.error_label.opacity = 1
    
    def show_collection(self, collection_id):
        """Koleksiyon detaylarını göster"""
        self.current_collection_id = collection_id
        
        # Yükleniyor göstergesini başlat
        self.ids.loading_indicator.active = True
        
        # Arka planda koleksiyon öğelerini çek
        threading.Thread(target=self._load_collection_items, args=(collection_id,)).start()
    
    def _load_collection_items(self, collection_id):
        """Arka planda koleksiyon öğelerini çek"""
        result = self.collection_manager.get_collection_items(collection_id)
        
        # Ana thread'de UI güncelleme
        Clock.schedule_once(lambda dt: self._handle_items_result(result))
    
    def _handle_items_result(self, result):
        """Öğe sonucunu işle"""
        self.ids.loading_indicator.active = False
        
        if result['status'] == 'success':
            # Öğe container'ı temizle
            self.ids.items_container.clear_widgets()
            
            # Her öğe için kart oluştur
            for item in result['items']:
                card = ItemCard(item)
                self.ids.items_container.add_widget(card)
            
            # Koleksiyon görünümüne geç
            self.ids.screen_manager.current = 'collection_view'
            
        else:
            # Hata mesajını göster
            self.ids.error_label.text = f"Öğeler yüklenemedi: {result['error']}"
            self.ids.error_label.opacity = 1
    
    def show_create_collection_popup(self):
        """Koleksiyon oluşturma popup'ını göster"""
        popup = CreateCollectionPopup(
            on_create=self.create_collection,
            title='Yeni Koleksiyon',
            size_hint=(0.8, 0.6)
        )
        popup.open()
    
    def create_collection(self, name, description=None):
        """Yeni koleksiyon oluştur"""
        result = self.collection_manager.create_collection(name, description)
        
        if result['status'] == 'success':
            # Koleksiyonları yeniden yükle
            self.load_collections()
        else:
            # Hata mesajını göster
            self.ids.error_label.text = f"Koleksiyon oluşturulamadı: {result['error']}"
            self.ids.error_label.opacity = 1
    
    def delete_collection(self, collection_id):
        """Koleksiyonu sil"""
        result = self.collection_manager.delete_collection(collection_id)
        
        if result['status'] == 'success':
            # Koleksiyonları yeniden yükle
            self.load_collections()
            
            # Ana görünüme dön
            self.ids.screen_manager.current = 'collections_list'
        else:
            # Hata mesajını göster
            self.ids.error_label.text = f"Koleksiyon silinemedi: {result['error']}"
            self.ids.error_label.opacity = 1
    
    def remove_item(self, item_id):
        """Koleksiyondan öğe kaldır"""
        if self.current_collection_id:
            result = self.collection_manager.remove_item(
                self.current_collection_id,
                item_id
            )
            
            if result['status'] == 'success':
                # Öğeleri yeniden yükle
                self._load_collection_items(self.current_collection_id)
            else:
                # Hata mesajını göster
                self.ids.error_label.text = f"Öğe kaldırılamadı: {result['error']}"
                self.ids.error_label.opacity = 1
    
    def back_to_collections(self):
        """Koleksiyon listesine dön"""
        self.current_collection_id = None
        self.ids.screen_manager.current = 'collections_list'
