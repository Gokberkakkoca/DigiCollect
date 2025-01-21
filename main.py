from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDFloatingActionButton
from kivymd.uix.card import MDCard
from kivy.core.window import Window
from kivy.properties import StringProperty, BooleanProperty, NumericProperty
from kivy.metrics import dp
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineListItem
from kivymd.uix.menu import MDDropdownMenu
from content_collector import ContentCollector
from content_cutter import ContentCutter
from url_monitor import URLMonitor
from auth import Auth
from database import Database
import webbrowser
import pyperclip
import uuid
from datetime import datetime, timedelta
import os
import shutil
import logging
import threading
from kivy.uix.floatlayout import FloatLayout
from kivy.utils import platform
from services.floating_button_service import FloatingButtonService

# Loglama ayarları
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('digicollect_debug.log')
    ]
)

logger = logging.getLogger('DigiCollect')

# Pencere boyutunu ayarla
Window.size = (400, 700)

class LoginScreen(MDScreen):
    pass

class RegisterScreen(MDScreen):
    pass

class HomeScreen(MDScreen):
    pass

class CollectionScreen(MDScreen):
    pass

class ProfileScreen(MDScreen):
    profile_picture = StringProperty(None)
    username = StringProperty("")
    premium_type = StringProperty("")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        
    def on_enter(self):
        self.load_user_data()
        self.load_collections()
    
    def load_user_data(self):
        user = self.app.current_user
        if user:
            self.username = user.name
            self.premium_type = user.premium_type.value
            self.profile_picture = user.profile_picture
    
    def load_collections(self):
        collections = self.app.db.get_user_collections(self.app.current_user.user_id)
        collections_grid = self.ids.collections_grid
        collections_grid.clear_widgets()
        
        for collection in collections:
            card = CollectionCard(
                collection_id=collection.collection_id,
                name=collection.name,
                item_count=collection.item_count,
                followers_count=collection.followers_count,
                is_following=False  # Bu değer veritabanından kontrol edilmeli
            )
            collections_grid.add_widget(card)
    
    def change_profile_picture(self):
        filechooser.open_file(
            on_selection=self._handle_profile_picture_selection,
            filters=['*.png', '*.jpg', '*.jpeg']
        )
    
    def _handle_profile_picture_selection(self, selection):
        if selection:
            file_path = selection[0]
            # Resmi assets klasörüne kopyala
            new_path = f'assets/profile_pictures/user_{self.app.current_user.user_id}.png'
            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            shutil.copy2(file_path, new_path)
            
            # Veritabanını güncelle
            self.app.db.update_user(
                self.app.current_user.user_id,
                {'profile_picture': new_path}
            )
            
            # UI'ı güncelle
            self.profile_picture = new_path

class CollectionCard(BoxLayout):
    collection_id = NumericProperty(None)
    name = StringProperty("")
    item_count = NumericProperty(0)
    followers_count = NumericProperty(0)
    is_following = BooleanProperty(False)
    thumbnail = StringProperty(None)
    
    def toggle_follow(self):
        app = App.get_running_app()
        if self.is_following:
            app.db.unfollow_collection(self.collection_id, app.current_user.user_id)
            self.followers_count -= 1
        else:
            app.db.follow_collection(self.collection_id, app.current_user.user_id)
            self.followers_count += 1
        self.is_following = not self.is_following

class ContentCollectorScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.collector = ContentCollector()
        self.content_data = None
        self.logger = logging.getLogger('DigiCollect.ContentCollector')
    
    def fetch_content(self):
        url = self.ids.url_input.text.strip()
        if not url:
            self.logger.warning('URL boş olamaz')
            return
        
        try:
            self.logger.info(f'İçerik getiriliyor: {url}')
            
            # İçerik meta verilerini al
            preview_data = self.collector.get_preview_data(url)
            
            # Önizleme alanını güncelle
            preview_box = self.ids.preview_box
            preview_box.opacity = 1
            
            # Başlık ve açıklama
            self.ids.preview_title.text = preview_data['title']
            self.ids.preview_description.text = preview_data['description']
            
            # Önizleme görseli
            if preview_data['preview_image']:
                self.ids.preview_image.source = preview_data['preview_image']
            
            # İçerik türüne göre kontrolleri göster
            cut_controls = self.ids.cut_controls
            media_controls = self.ids.media_controls
            text_content = self.ids.text_content
            
            cut_controls.opacity = 1
            if preview_data['content_type'] in ['video', 'audio']:
                media_controls.opacity = 1
                text_content.opacity = 0
            else:
                media_controls.opacity = 0
                text_content.opacity = 1
                if preview_data.get('text_content'):
                    text_content.text = preview_data['text_content']
            
            # Koleksiyon seçimini göster
            self.ids.collection_box.opacity = 1
            
            # Önizleme verilerini sakla
            self.preview_data = preview_data
            self.content_type = preview_data['content_type']
            
        except Exception as e:
            self.logger.exception(f"İçerik getirme hatası: {e}")

class ContentPreviewCard(BoxLayout):
    title = StringProperty("")
    description = StringProperty("")
    thumbnail = StringProperty("")
    content_type = StringProperty("")
    
    def __init__(self, content_data=None, **kwargs):
        super().__init__(**kwargs)
        self.content_data = content_data
    
    def show_cut_dialog(self):
        app = App.get_running_app()
        app.switch_screen('content_cutter', content_data=self.content_data)

class ContentCutterScreen(Screen):
    content_type = StringProperty("")
    media_duration = NumericProperty(0)
    image_url = StringProperty("")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cutter = ContentCutter()
        self.content_data = None
    
    def on_enter(self, *args):
        if hasattr(self, 'content_data'):
            self.setup_cutter_interface()
    
    def setup_cutter_interface(self):
        self.content_type = self.content_data.get('type', '')
        
        if self.content_type in ['video', 'audio', 'spotify', 'podcast']:
            self.media_duration = self.content_data.get('duration', 0)
            self.ids.time_slider.max = self.media_duration
        
        elif self.content_type == 'image':
            self.image_url = self.content_data.get('image', '')
        
        elif self.content_type == 'text':
            self.ids.text_content.text = self.content_data.get('content', '')
    
    def save_cut(self):
        try:
            cut_params = {}
            
            if self.content_type in ['video', 'audio', 'spotify', 'podcast']:
                cut_params = {
                    'start_time': float(self.ids.start_time.text or 0),
                    'end_time': float(self.ids.end_time.text or self.media_duration)
                }
            
            elif self.content_type == 'image':
                cut_params = {
                    'x': int(self.ids.crop_x.text or 0),
                    'y': int(self.ids.crop_y.text or 0),
                    'width': int(self.ids.crop_width.text or 0),
                    'height': int(self.ids.crop_height.text or 0)
                }
            
            elif self.content_type == 'text':
                selected_text = self.ids.text_content.selection_text
                if selected_text:
                    text = self.ids.text_content.text
                    start_index = text.find(selected_text)
                    end_index = start_index + len(selected_text)
                    cut_params = {
                        'start_index': start_index,
                        'end_index': end_index
                    }
            
            # İçeriği kes
            cut_content = self.cutter.cut_content(self.content_data, cut_params)
            if cut_content:
                self.show_collection_dialog(cut_content)
        
        except Exception as e:
            logger.exception(f"İçerik kesme hatası: {e}")
    
    def show_collection_dialog(self, cut_content):
        app = App.get_running_app()
        dialog = CollectionSelectDialog(cut_content=cut_content)
        dialog.open()

class CollectionSelectDialog(MDDialog):
    def __init__(self, cut_content=None, **kwargs):
        super().__init__(**kwargs)
        self.cut_content = cut_content
        self.load_collections()
    
    def load_collections(self):
        app = App.get_running_app()
        collections = app.db.get_user_collections(app.current_user.user_id)
        
        collection_list = self.ids.collection_list
        for collection in collections:
            item = CollectionSelectItem(
                collection_id=collection.collection_id,
                name=collection.name,
                item_count=collection.item_count
            )
            collection_list.add_widget(item)

class CollectionSelectItem(BoxLayout):
    collection_id = NumericProperty(None)
    name = StringProperty("")
    item_count = NumericProperty(0)
    
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            app = App.get_running_app()
            dialog = self.parent.parent.parent.parent
            
            # İçeriği koleksiyona ekle
            app.db.add_item_to_collection(
                self.collection_id,
                app.current_user.user_id,
                dialog.cut_content
            )
            
            dialog.dismiss()
            app.switch_screen('collection_manager')
            return True
        return super().on_touch_down(touch)

class CollectionManagerScreen(MDScreen):
    pass

class CreateCollectionDialog(MDDialog):
    pass

class ContentPreviewScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_item = None

class PremiumScreen(MDScreen):
    pass

class DiscoveryScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.load_content()
    
    def load_content(self):
        # Örnek veriler (backend hazır olduğunda gerçek verilerle değiştirilecek)
        self.trending_collections = [
            {"title": "En İyi Fotoğraflar", "owner": "ahmet", "likes": 150},
            {"title": "Doğa Manzaraları", "owner": "ayse", "likes": 120},
            {"title": "Şehir Hayatı", "owner": "mehmet", "likes": 90}
        ]
        
        self.popular_content = [
            {"title": "Güneş Batımı", "owner": "zeynep", "likes": 200},
            {"title": "Tarihi Yapılar", "owner": "can", "likes": 180},
            {"title": "Deniz Manzarası", "owner": "elif", "likes": 160}
        ]

class DigiCollectApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.content_collector = ContentCollector()
        self.content_cutter = ContentCutter()
        self.database = Database()
        self.auth = Auth(self.database)
        self.url_monitor = URLMonitor(callback=self.on_url_detected)
        self.current_user = None
        self.floating_button = None
    
    def build(self):
        # Floating butonu başlat
        if platform == 'android':
            self.floating_button = FloatingButtonService()
            self.floating_button.show()
        
        # Tema ayarları
        self.theme_cls.primary_palette = "DeepPurple"
        self.theme_cls.theme_style = "Light"
        
        # Pencere ayarları
        self.title = "DigiCollect"
        Window.size = (400, 600)
        
        # KV dosyasını yükle
        Builder.load_file('digicollect.kv')
        
        # Ekran yöneticisi
        self.sm = ScreenManager()
        self.sm.add_widget(LoginScreen(name='login'))
        self.sm.add_widget(RegisterScreen(name='register'))
        self.sm.add_widget(HomeScreen(name='home'))
        self.sm.add_widget(ProfileScreen(name='profile'))
        self.sm.add_widget(ContentCollectorScreen(name='content_collector'))
        self.sm.add_widget(CollectionManagerScreen(name='collection_manager'))
        self.sm.add_widget(ContentPreviewScreen(name='content_preview'))
        self.sm.add_widget(PremiumScreen(name='premium'))
        self.sm.add_widget(DiscoveryScreen(name='discovery'))
        self.sm.add_widget(ContentCutterScreen(name='content_cutter'))
        
        # Ana layout
        layout = FloatLayout()
        
        # Floating Action Button'u ekle
        fab = MDFloatingActionButton()
        fab.bind(on_action_selected=self.handle_action)
        layout.add_widget(fab)
        
        # Ekran yöneticisini ekle
        layout.add_widget(self.sm)
        
        # Başlangıç ekranı
        self.sm.current = 'login'
        
        return layout
    
    def login(self):
        """Kullanıcı girişi"""
        email = self.root.get_screen('login').ids.email.text
        password = self.root.get_screen('login').ids.password.text
        
        if not email or not password:
            self.show_error("Lütfen email ve şifrenizi girin")
            return
        
        success, message, user = self.auth.login_user(email, password)
        
        if success:
            self.current_user = user
            self.root.current = 'home'
            self.show_success(message)
        else:
            self.show_error(message)

    def register(self):
        try:
            name = self.sm.get_screen('register').ids.name.text
            email = self.sm.get_screen('register').ids.email.text
            password = self.sm.get_screen('register').ids.password.text
            password_confirm = self.sm.get_screen('register').ids.password_confirm.text
            
            print(f"Name: {name}")
            print(f"Email: {email}")
            print(f"Password: {password}")
            print(f"Password Confirm: {password_confirm}")
            
            if password != password_confirm:
                Snackbar(text="Şifreler eşleşmiyor!").open()
                return
            
            try:
                success, message = self.auth.register_user(email, password, name)
                print(f"Register result - Success: {success}, Message: {message}")
                if success:
                    self.sm.current = 'login'
                    Snackbar(text=message).open()
                else:
                    Snackbar(text=message).open()
            except Exception as e:
                print(f"Auth error: {str(e)}")
                Snackbar(text=str(e)).open()
        except Exception as e:
            print(f"Main error: {str(e)}")
            Snackbar(text=str(e)).open()

    def on_start(self):
        """Uygulama başladığında çağrılır"""
        # Başlangıçta login ekranını göster
        self.sm.current = 'login'

    def fetch_content(self):
        """URL'den içeriği getir ve önizle"""
        url = self.root.get_screen('content_collector').ids.url_input.text
        
        try:
            # İçerik meta verilerini al
            preview_data = self.content_collector.get_preview_data(url)
            
            # Önizleme alanını güncelle
            preview_box = self.root.get_screen('content_collector').ids.preview_box
            preview_box.opacity = 1
            
            # Başlık ve açıklama
            self.root.get_screen('content_collector').ids.preview_title.text = preview_data['title']
            self.root.get_screen('content_collector').ids.preview_description.text = preview_data['description']
            
            # Önizleme görseli
            if preview_data['preview_image']:
                self.root.get_screen('content_collector').ids.preview_image.source = preview_data['preview_image']
            
            # İçerik türüne göre kontrolleri göster
            cut_controls = self.root.get_screen('content_collector').ids.cut_controls
            media_controls = self.root.get_screen('content_collector').ids.media_controls
            text_content = self.root.get_screen('content_collector').ids.text_content
            
            cut_controls.opacity = 1
            if preview_data['content_type'] in ['video', 'audio']:
                media_controls.opacity = 1
                text_content.opacity = 0
            else:
                media_controls.opacity = 0
                text_content.opacity = 1
                if preview_data.get('text_content'):
                    text_content.text = preview_data['text_content']
            
            # Koleksiyon seçimini göster
            self.root.get_screen('content_collector').ids.collection_box.opacity = 1
            
            # Önizleme verilerini sakla
            self.root.get_screen('content_collector').preview_data = preview_data
            self.root.get_screen('content_collector').content_type = preview_data['content_type']
            
        except Exception as e:
            self.show_error_dialog(str(e))

    def cut_and_save(self):
        """İçeriği kes ve koleksiyona kaydet"""
        screen = self.root.get_screen('content_collector')
        
        try:
            # Koleksiyon kontrolü
            collection_id = getattr(screen.ids.collection_dropdown, 'collection_id', None)
            if not collection_id:
                raise ValueError("Lütfen bir koleksiyon seçin")
            
            # Kesme verilerini hazırla
            cut_data = {}
            if screen.content_type in ['video', 'audio']:
                start_time = float(screen.ids.start_time.text or 0)
                end_time = float(screen.ids.end_time.text or 0)
                
                if screen.content_type == 'video':
                    cut_data = self.content_cutter.cut_video(
                        screen.preview_data['url'],
                        start_time,
                        end_time
                    )
                else:
                    cut_data = self.content_cutter.cut_audio(
                        screen.preview_data['url'],
                        start_time,
                        end_time
                    )
            else:
                selected_text = screen.ids.text_content.text
                if not selected_text:
                    raise ValueError("Lütfen bir metin seçin")
                
                cut_data = self.content_cutter.cut_text(
                    screen.preview_data.get('text_content', ''),
                    screen.preview_data.get('text_content', '').find(selected_text),
                    screen.preview_data.get('text_content', '').find(selected_text) + len(selected_text)
                )
            
            # İçeriği koleksiyona ekle
            self.database.add_item(
                collection_id=collection_id,
                user_id=self.current_user['id'],
                content_type=screen.content_type,
                source_url=screen.preview_data['url'],
                cut_data=cut_data,
                notes=screen.ids.content_note.text
            )
            
            # Başarı mesajı göster
            self.show_success_dialog("İçerik başarıyla eklendi!")
            
            # Ana ekrana dön
            self.root.current = 'home'
            
        except Exception as e:
            self.show_error_dialog(str(e))
        finally:
            # Geçici dosyaları temizle
            if cut_data and 'temp_file' in cut_data:
                self.content_cutter.cleanup_temp_files(cut_data)

    def show_collections(self):
        """Kullanıcının koleksiyonlarını göster"""
        collections = self.database.get_user_collections(self.current_user['id'])
        
        if not collections:
            self.show_error_dialog("Önce bir koleksiyon oluşturmalısınız!")
            return
        
        menu_items = [
            {
                "text": f"{col['name']} ({col['item_count']}/{self.get_collection_limit()})",
                "viewclass": "OneLineListItem",
                "on_release": lambda x=col: self.select_collection(x),
            } for col in collections
        ]
        
        MDDropdownMenu(
            caller=self.root.get_screen('content_collector').ids.collection_dropdown,
            items=menu_items,
            width_mult=4,
        ).open()

    def select_collection(self, collection):
        """Koleksiyon seç"""
        dropdown = self.root.get_screen('content_collector').ids.collection_dropdown
        dropdown.text = collection['name']
        dropdown.collection_id = collection['id']

    def get_collection_limit(self):
        """Kullanıcının koleksiyon başına içerik limitini döndür"""
        limits = {
            'free': 20,
            'starter': 25,
            'standard': 30,
            'pro': 35,
            'unlimited': 40
        }
        return limits.get(self.current_user['premium_type'], 20)

    def show_collection_dialog(self, collection=None):
        """Koleksiyon oluşturma/düzenleme dialogunu göster"""
        dialog = CreateCollectionDialog()
        
        if collection:
            # Düzenleme modu
            dialog.title = "Koleksiyonu Düzenle"
            dialog.content_cls.ids.name.text = collection.name
            dialog.content_cls.ids.description.text = collection.description
            dialog.content_cls.ids.category.text = collection.category
            dialog.content_cls.ids.is_public.active = collection.is_public
            dialog.content_cls.ids.tags.text = ", ".join(collection.tags)
            dialog.buttons = [
                ["İptal", lambda x: dialog.dismiss()],
                ["Kaydet", lambda x: self.update_collection(collection, dialog.content_cls)]
            ]
        
        dialog.open()

    def show_categories(self):
        """Kategori listesini göster"""
        categories = [
            "Müzik",
            "Film & Dizi",
            "Komedi & Eğlence",
            "Spor",
            "Eğitim",
            "Oyun",
            "Yemek",
            "Moda & Güzellik",
            "Teknoloji",
            "Seyahat",
            "Sanat",
            "Hayvanlar",
            "Güzeller",
            "Yakışıklılar",
            "Ünlüler/Magazin"
        ]
        
        menu_items = [
            {
                "text": category,
                "viewclass": "OneLineListItem",
                "on_release": lambda x=category: self.select_category(x),
            } for category in categories
        ]
        
        self.category_menu = MDDropdownMenu(
            caller=self.root.get_screen('collection_manager').ids.category,
            items=menu_items,
            width_mult=4,
        )
        self.category_menu.open()

    def select_category(self, category):
        """Kategori seç"""
        self.root.get_screen('collection_manager').ids.category.text = category
        self.category_menu.dismiss()
        
        # Alt kategori dropdown'ını güncelle
        subcategory_dropdown = self.root.get_screen('collection_manager').ids.subcategory
        if category == "Video":
            subcategory_dropdown.disabled = False
            subcategory_dropdown.text = "Alt kategori seçin"
        else:
            subcategory_dropdown.disabled = True
            subcategory_dropdown.text = "Alt kategori yok"
    
    def show_subcategory_menu(self, caller):
        category_dropdown = self.root.get_screen('collection_manager').ids.category
        category = category_dropdown.text
        
        if category != "Video":
            return
            
        subcategories = [
            "Film",
            "Dizi",
            "Müzik",
            "Belgesel"
        ]
        menu_items = [
            {
                "text": subcategory,
                "viewclass": "OneLineListItem",
                "on_release": lambda x=subcategory: self.select_subcategory(caller, x),
            }
            for subcategory in subcategories
        ]
        
        self.subcategory_menu = MDDropdownMenu(
            caller=caller,
            items=menu_items,
            width_mult=4,
        )
        self.subcategory_menu.open()
    
    def select_subcategory(self, caller, subcategory):
        caller.text = subcategory
        caller.current_item = subcategory
        self.subcategory_menu.dismiss()
    
    def create_collection(self, name, description, category_id, subcategory=None, is_public=True):
        if not self.current_user:
            self.show_error_dialog("Lütfen önce giriş yapın")
            return
            
        if not name:
            self.show_error_dialog("Koleksiyon adı gerekli")
            return
            
        if not category_id:
            self.show_error_dialog("Kategori seçimi gerekli")
            return
            
        collection = self.db.create_collection(
            user_id=self.current_user.user_id,
            name=name,
            description=description,
            category=category_id,
            subcategory=subcategory,
            is_public=is_public
        )
        
        if collection:
            self.show_success_dialog("Koleksiyon başarıyla oluşturuldu")
            self.root.get_screen('home').ids.create_collection_dialog.dismiss()
            self.refresh_collections()
        else:
            self.show_error_dialog("Koleksiyon oluşturulamadı")

    def update_collection(self, collection, content):
        """Koleksiyonu güncelle"""
        try:
            # Alanları kontrol et
            name = content.ids.name.text.strip()
            if not name:
                raise ValueError("Koleksiyon adı zorunludur")
            
            # Koleksiyonu güncelle
            updated = self.database.update_collection(
                collection_id=collection.id,
                user_id=self.current_user['id'],
                name=name,
                description=content.ids.description.text.strip(),
                category=content.ids.category.text,
                is_public=content.ids.is_public.active,
                tags=content.ids.tags.text.strip().split(',')
            )
            
            # Koleksiyon listesini güncelle
            self.load_collections()
            
            # Başarı mesajı göster
            self.show_success_dialog("Koleksiyon başarıyla güncellendi!")
            
        except Exception as e:
            self.show_error_dialog(str(e))
        finally:
            content.parent.parent.dismiss()

    def delete_collection(self, collection):
        """Koleksiyonu sil"""
        def confirm_delete(dialog):
            try:
                self.database.delete_collection(collection.id, self.current_user['id'])
                self.load_collections()
                self.show_success_dialog("Koleksiyon başarıyla silindi!")
            except Exception as e:
                self.show_error_dialog(str(e))
            finally:
                dialog.dismiss()
        
        dialog = MDDialog(
            title="Koleksiyonu Sil",
            text=f"{collection.name} koleksiyonunu silmek istediğinize emin misiniz?",
            buttons=[
                MDFlatButton(
                    text="İptal",
                    on_release=lambda x: dialog.dismiss()
                ),
                MDFlatButton(
                    text="Sil",
                    on_release=lambda x: confirm_delete(dialog)
                ),
            ],
        )
        dialog.open()

    def load_collections(self):
        """Kullanıcının koleksiyonlarını yükle"""
        collections = self.database.get_user_collections(self.current_user['id'])
        
        # Koleksiyon listesini temizle
        collection_list = self.root.get_screen('collection_manager').ids.collection_list
        collection_list.clear_widgets()
        
        # Koleksiyonları ekle
        for col in collections:
            card = CollectionCard(
                name=col['name'],
                description=col['description'],
                category=col['category'],
                is_public=col['is_public'],
                item_count=col['item_count']
            )
            collection_list.add_widget(card)

    def preview_content(self, item_id: str):
        """İçerik önizleme ekranını göster"""
        try:
            # İçeriği getir
            item = self.database.get_item(item_id)
            if not item:
                raise ValueError("İçerik bulunamadı")
            
            # Ekranı hazırla
            screen = self.root.get_screen('content_preview')
            screen.current_item = item
            
            # İçerik türüne göre önizleme göster
            if item['content_type'] in ['video', 'audio']:
                # Media player ekle
                from kivy.uix.videoplayer import VideoPlayer
                player = VideoPlayer(
                    source=item['cut_data']['temp_file'],
                    state='play',
                    options={'allow_stretch': True}
                )
                screen.ids.media_player.add_widget(player)
            else:
                # Metin içeriğini göster
                screen.ids.text_content.text = item['cut_data'].get('cut_text', '')
            
            # Kaynak URL'yi göster
            screen.ids.source_url.text = item['source_url']
            
            # Notları göster
            screen.ids.notes.text = item.get('notes', '')
            
            # Ekranı göster
            self.root.current = 'content_preview'
            
        except Exception as e:
            self.show_error_dialog(str(e))

    def share_content(self):
        """İçerik paylaşım menüsünü göster"""
        try:
            screen = self.root.get_screen('content_preview')
            item = screen.current_item
            
            if not item:
                raise ValueError("Paylaşılacak içerik bulunamadı")
            
            # Paylaşım menüsünü göster
            menu_items = [
                {
                    "text": "WhatsApp",
                    "viewclass": "OneLineListItem",
                    "on_release": lambda x="whatsapp": self.share_to(x),
                },
                {
                    "text": "Twitter",
                    "viewclass": "OneLineListItem",
                    "on_release": lambda x="twitter": self.share_to(x),
                },
                {
                    "text": "Facebook",
                    "viewclass": "OneLineListItem",
                    "on_release": lambda x="facebook": self.share_to(x),
                },
                {
                    "text": "Bağlantıyı Kopyala",
                    "viewclass": "OneLineListItem",
                    "on_release": lambda x="copy": self.copy_link(),
                }
            ]
            
            MDDropdownMenu(
                caller=self.root.get_screen('content_preview').ids.share_button,
                items=menu_items,
                width_mult=4,
            ).open()
            
        except Exception as e:
            self.show_error_dialog(str(e))

    def share_to(self, platform: str):
        """İçeriği belirtilen platformda paylaş"""
        try:
            screen = self.root.get_screen('content_preview')
            item = screen.current_item
            
            if not item:
                raise ValueError("Paylaşılacak içerik bulunamadı")
            
            # Paylaşım URL'si oluştur
            share_url = f"https://digicollect.app/share/{item['id']}"
            
            # Platforma göre paylaşım URL'si
            if platform == "whatsapp":
                url = f"https://wa.me/?text={share_url}"
            elif platform == "twitter":
                url = f"https://twitter.com/intent/tweet?url={share_url}"
            elif platform == "facebook":
                url = f"https://www.facebook.com/sharer/sharer.php?u={share_url}"
            else:
                raise ValueError("Geçersiz platform")
            
            # Tarayıcıda aç
            webbrowser.open(url)
            
        except Exception as e:
            self.show_error_dialog(str(e))

    def copy_link(self):
        """Paylaşım bağlantısını panoya kopyala"""
        try:
            screen = self.root.get_screen('content_preview')
            item = screen.current_item
            
            if not item:
                raise ValueError("İçerik bulunamadı")
            
            # Paylaşım URL'sini oluştur ve kopyala
            share_url = f"https://digicollect.app/share/{item['id']}"
            pyperclip.copy(share_url)
            
            # Başarı mesajı göster
            self.show_success_dialog("Bağlantı panoya kopyalandı!")
            
        except Exception as e:
            self.show_error_dialog(str(e))

    def open_source(self):
        """Kaynak URL'yi tarayıcıda aç"""
        try:
            screen = self.root.get_screen('content_preview')
            item = screen.current_item
            
            if not item:
                raise ValueError("İçerik bulunamadı")
            
            # URL'yi tarayıcıda aç
            webbrowser.open(item['source_url'])
            
        except Exception as e:
            self.show_error_dialog(str(e))

    def save_notes(self):
        """İçerik notlarını kaydet"""
        try:
            screen = self.root.get_screen('content_preview')
            item = screen.current_item
            
            if not item:
                raise ValueError("İçerik bulunamadı")
            
            # Notları güncelle
            self.database.update_item_notes(
                item['id'],
                self.current_user['id'],
                screen.ids.notes.text
            )
            
            # Başarı mesajı göster
            self.show_success_dialog("Notlar kaydedildi!")
            
        except Exception as e:
            self.show_error_dialog(str(e))

    def upgrade_premium(self, plan_type: str):
        if not self.current_user:
            self.show_error_dialog("Lütfen önce giriş yapın")
            return
            
        premium_type = {
            'starter': PremiumType.STARTER,
            'standard': PremiumType.STANDARD,
            'pro': PremiumType.PRO,
            'unlimited': PremiumType.UNLIMITED
        }.get(plan_type)
        
        if not premium_type:
            self.show_error_dialog("Geçersiz plan türü")
            return
            
        # Burada ödeme işlemi yapılacak
        # Şimdilik direk yükseltiyoruz
        success = self.db.upgrade_user_premium(self.current_user.user_id, premium_type)
        
        if success:
            self.show_success_dialog(f"Premium planınız {plan_type} olarak güncellendi!")
            self.current_user.premium_type = premium_type
        else:
            self.show_error_dialog("Premium yükseltme başarısız oldu")

    def show_success_dialog(self, message: str):
        dialog = MDDialog(
            text=message,
            buttons=[
                MDFlatButton(
                    text="TAMAM",
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        dialog.open()
    
    def show_error_dialog(self, message: str):
        dialog = MDDialog(
            text=message,
            buttons=[
                MDFlatButton(
                    text="TAMAM",
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        dialog.open()

    def upgrade_to_premium(self, plan_type: str):
        """Premium üyeliğe geçiş işlemi"""
        try:
            if not self.current_user:
                raise ValueError("Lütfen önce giriş yapın")
            
            # Plan fiyatları
            prices = {
                'premium': 49.99,
                'pro': 99.99
            }
            
            # Ödeme diyalogu göster
            self.payment_dialog = MDDialog(
                title=f"{plan_type.capitalize()} Plan",
                text=f"Aylık ₺{prices[plan_type]} tutarında ödeme alınacaktır.\nDevam etmek istiyor musunuz?",
                buttons=[
                    MDFlatButton(
                        text="İPTAL",
                        on_release=lambda x: self.payment_dialog.dismiss()
                    ),
                    MDRaisedButton(
                        text="ÖDEME YAP",
                        on_release=lambda x: self.process_payment(plan_type, prices[plan_type])
                    )
                ]
            )
            self.payment_dialog.open()
            
        except Exception as e:
            self.show_error_dialog(str(e))

    def process_payment(self, plan_type: str, amount: float):
        """Ödeme işlemini gerçekleştir"""
        try:
            # Ödeme diyalogunu kapat
            self.payment_dialog.dismiss()
            
            # Ödeme işlemi simülasyonu
            # Gerçek uygulamada burada ödeme API'si kullanılacak
            payment_id = str(uuid.uuid4())
            subscription_id = str(uuid.uuid4())
            
            # Abonelik oluştur
            subscription = {
                'id': subscription_id,
                'user_id': self.current_user['id'],
                'plan_type': plan_type,
                'start_date': str(datetime.now()),
                'end_date': str(datetime.now() + timedelta(days=30)),
                'status': 'active',
                'payment_method': 'credit_card',
                'auto_renew': True,
                'created_at': str(datetime.now()),
                'updated_at': str(datetime.now())
            }
            
            # Ödeme kaydı oluştur
            payment = {
                'id': payment_id,
                'user_id': self.current_user['id'],
                'subscription_id': subscription_id,
                'amount': amount,
                'currency': 'TRY',
                'payment_method': 'credit_card',
                'status': 'success',
                'created_at': str(datetime.now())
            }
            
            # Veritabanına kaydet
            self.database.create_subscription(subscription)
            self.database.create_payment(payment)
            
            # Başarı mesajı göster
            self.show_success_dialog(
                f"{plan_type.capitalize()} üyeliğiniz başarıyla aktifleştirildi!"
            )
            
            # Ana ekrana dön
            self.root.current = 'home'
            
        except Exception as e:
            self.show_error_dialog(str(e))

    def check_subscription(self) -> bool:
        """Kullanıcının aktif premium üyeliği var mı kontrol et"""
        try:
            if not self.current_user:
                return False
            
            # Aktif aboneliği kontrol et
            subscription = self.database.get_active_subscription(
                self.current_user['id']
            )
            
            return bool(subscription)
            
        except Exception:
            return False

    def is_premium_feature(self, feature: str) -> bool:
        """Özellik premium mu kontrol et"""
        premium_features = {
            'unlimited_collections': True,
            'advanced_content_cutting': True,
            'ad_free': True,
            'ai_suggestions': True,
            'custom_themes': True,
            'priority_support': True
        }
        
        return premium_features.get(feature, False)

    def check_feature_access(self, feature: str) -> bool:
        """Kullanıcının özelliğe erişimi var mı kontrol et"""
        try:
            # Premium özellik değilse herkes kullanabilir
            if not self.is_premium_feature(feature):
                return True
            
            # Premium özellik ise abonelik kontrolü yap
            return self.check_subscription()
            
        except Exception:
            return False

    def show_category_menu(self, button):
        """Kategori menüsünü göster"""
        menu_items = [
            {
                "text": "Video",
                "viewclass": "OneLineListItem",
                "on_release": lambda x="video": self.select_category(x),
            },
            {
                "text": "Ses",
                "viewclass": "OneLineListItem",
                "on_release": lambda x="audio": self.select_category(x),
            },
            {
                "text": "Metin",
                "viewclass": "OneLineListItem",
                "on_release": lambda x="text": self.select_category(x),
            },
            {
                "text": "Resim",
                "viewclass": "OneLineListItem",
                "on_release": lambda x="image": self.select_category(x),
            }
        ]
        
        self.category_menu = MDDropdownMenu(
            caller=button,
            items=menu_items,
            width_mult=4,
        )
        self.category_menu.open()
    
    def select_category(self, category):
        category_dropdown = self.root.get_screen('collection_manager').ids.category
        category_dropdown.text = category
        self.category_menu.dismiss()
        
        # Alt kategori dropdown'ını güncelle
        subcategory_dropdown = self.root.get_screen('collection_manager').ids.subcategory
        if category == "Video":
            subcategory_dropdown.disabled = False
            subcategory_dropdown.text = "Alt kategori seçin"
        else:
            subcategory_dropdown.disabled = True
            subcategory_dropdown.text = "Alt kategori yok"
    
    def show_subcategory_menu(self, caller):
        category_dropdown = self.root.get_screen('collection_manager').ids.category
        category = category_dropdown.text
        
        if category != "Video":
            return
            
        subcategories = [
            "Film",
            "Dizi",
            "Müzik",
            "Belgesel"
        ]
        menu_items = [
            {
                "text": subcategory,
                "viewclass": "OneLineListItem",
                "on_release": lambda x=subcategory: self.select_subcategory(caller, x),
            }
            for subcategory in subcategories
        ]
        
        self.subcategory_menu = MDDropdownMenu(
            caller=caller,
            items=menu_items,
            width_mult=4,
        )
        self.subcategory_menu.open()
    
    def select_subcategory(self, caller, subcategory):
        caller.text = subcategory
        caller.current_item = subcategory
        self.subcategory_menu.dismiss()
    
    def create_collection(self, name, description, category_id, subcategory=None, is_public=True):
        if not self.current_user:
            self.show_error_dialog("Lütfen önce giriş yapın")
            return
            
        if not name:
            self.show_error_dialog("Koleksiyon adı gerekli")
            return
            
        if not category_id:
            self.show_error_dialog("Kategori seçimi gerekli")
            return
            
        collection = self.db.create_collection(
            user_id=self.current_user.user_id,
            name=name,
            description=description,
            category=category_id,
            subcategory=subcategory,
            is_public=is_public
        )
        
        if collection:
            self.show_success_dialog("Koleksiyon başarıyla oluşturuldu")
            self.root.get_screen('home').ids.create_collection_dialog.dismiss()
            self.refresh_collections()
        else:
            self.show_error_dialog("Koleksiyon oluşturulamadı")

    def show_category_filter_menu(self, caller):
        menu_items = [
            {
                "text": "Tüm Kategoriler",
                "viewclass": "OneLineListItem",
                "on_release": lambda: self.select_category_filter(caller, None),
            }
        ] + [
            {
                "text": f"{category['name']}",
                "viewclass": "OneLineIconListItem",
                "icon": category['icon'],
                "on_release": lambda x=category['id']: self.select_category_filter(caller, x),
            }
            for category in Category.get_all_categories()
        ]
        
        self.category_filter_menu = MDDropdownMenu(
            caller=caller,
            items=menu_items,
            width_mult=4,
        )
        self.category_filter_menu.open()
    
    def select_category_filter(self, caller, category_id):
        if category_id is None:
            caller.text = "Tüm Kategoriler"
        else:
            category = Category.get_category(category_id)
            if not category:
                return
            
            caller.text = category['name']
            caller.current_item = category_id
            self.category_filter_menu.dismiss()
        
        # Alt kategori dropdown'ını güncelle
        subcategory_filter = self.root.get_screen('discovery').ids.subcategory_filter
        
        if category_id:
            subcategories = Category.get_subcategories(category_id)
            if subcategories:
                subcategory_filter.disabled = False
                subcategory_filter.text = "Alt kategori seçin"
            else:
                subcategory_filter.disabled = True
                subcategory_filter.text = "Alt kategori yok"
        else:
            subcategory_filter.disabled = True
            subcategory_filter.text = "Alt kategori"
        
        # Koleksiyonları filtrele
        self.filter_collections(category_id)
    
    def show_subcategory_filter_menu(self, caller):
        category_filter = self.root.get_screen('discovery').ids.category_filter
        category_id = category_filter.current_item
        
        if not category_id:
            return
            
        subcategories = Category.get_subcategories(category_id)
        menu_items = [
            {
                "text": "Tüm Alt Kategoriler",
                "viewclass": "OneLineListItem",
                "on_release": lambda: self.select_subcategory_filter(caller, None),
            }
        ] + [
            {
                "text": subcategory,
                "viewclass": "OneLineListItem",
                "on_release": lambda x=subcategory: self.select_subcategory_filter(caller, x),
            }
            for subcategory in subcategories
        ]
        
        self.subcategory_filter_menu = MDDropdownMenu(
            caller=caller,
            items=menu_items,
            width_mult=4,
        )
        self.subcategory_filter_menu.open()
    
    def select_subcategory_filter(self, caller, subcategory):
        caller.text = subcategory if subcategory else "Tüm Alt Kategoriler"
        caller.current_item = subcategory
        self.subcategory_filter_menu.dismiss()
        
        # Koleksiyonları filtrele
        category_filter = self.root.get_screen('discovery').ids.category_filter
        self.filter_collections(category_filter.current_item, subcategory)
    
    def filter_collections(self, category_id=None, subcategory=None):
        """Koleksiyonları kategoriye göre filtrele"""
        collections = self.db.get_trending_collections()
        trending_collections = self.root.get_screen('discovery').ids.trending_collections
        trending_collections.clear_widgets()
        
        for collection in collections:
            if (not category_id or collection.category == category_id) and \
               (not subcategory or collection.subcategory == subcategory):
                card = MDCard(
                    size_hint_y=None,
                    height="100dp",
                    padding="10dp"
                )
                
                box = MDBoxLayout(orientation='vertical')
                box.add_widget(MDLabel(
                    text=collection.name,
                    font_style="H6"
                ))
                box.add_widget(MDLabel(
                    text=f"{collection.user_name} tarafından",
                    theme_text_color="Secondary"
                ))
                box.add_widget(MDLabel(
                    text=f"{collection.like_count} beğeni",
                    theme_text_color="Secondary"
                ))
                
                card.add_widget(box)
                trending_collections.add_widget(card)

    def go_to_discovery(self, *args):
        self.sm.current = 'discovery'

    def go_to_profile(self, *args):
        self.sm.current = 'profile'

    def toggle_nav_drawer(self, *args):
        pass  # Şimdilik boş bırakıyoruz

    def go_back(self, *args):
        self.sm.current = 'profile'

    def go_home(self, *args):
        self.sm.current = 'home'

    def show_error(self, message: str):
        """Hata mesajı göster"""
        Snackbar(text=message, bg_color=(1, 0, 0, 1)).open()
    
    def show_success(self, message: str):
        """Başarı mesajı göster"""
        Snackbar(text=message, bg_color=(0, 1, 0, 1)).open()

    def on_url_detected(self, url):
        """URL algılandığında çağrılacak fonksiyon"""
        logger.info(f'Yeni URL algılandı: {url}')
        threading.Thread(target=self.root.get_screen('content_collector').ids.url_input.text, args=(url,)).start()
        self.root.current = 'content_collector'
        threading.Thread(target=self.root.get_screen('content_collector').fetch_content, args=()).start()

    def handle_action(self, instance, action_type):
        """Floating button'dan bir eylem seçildiğinde"""
        if action_type == 'video':
            self.show_video_cutter()
        elif action_type == 'music':
            self.show_music_cutter()
        elif action_type == 'blog':
            self.show_blog_cutter()
        elif action_type == 'tweet':
            self.show_tweet_collector()
        elif action_type == 'instagram':
            self.show_instagram_collector()
    
    def show_video_cutter(self):
        """Video kesme ekranını göster"""
        # Video kesme ekranını aç
        pass
    
    def show_music_cutter(self):
        """Müzik kesme ekranını göster"""
        # Müzik kesme ekranını aç
        pass
    
    def show_blog_cutter(self):
        """Blog yazısı kesme ekranını göster"""
        # Blog kesme ekranını aç
        pass
    
    def show_tweet_collector(self):
        """Tweet toplama ekranını göster"""
        # Tweet toplama ekranını aç
        pass
    
    def show_instagram_collector(self):
        """Instagram içeriği toplama ekranını göster"""
        # Instagram toplama ekranını aç
        pass

def main():
    DigiCollectApp().run()

if __name__ == '__main__':
    main()
