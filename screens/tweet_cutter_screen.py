from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.properties import StringProperty, ListProperty, BooleanProperty
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.window import Window

from services.tweet_extractor import TweetExtractor
import threading
from datetime import datetime

class TweetCard(BoxLayout):
    """Tek bir tweet'i gösteren kart"""
    text = StringProperty('')
    author_name = StringProperty('')
    author_username = StringProperty('')
    profile_image = StringProperty('')
    created_at = StringProperty('')
    media_urls = ListProperty([])
    is_selected = BooleanProperty(False)
    
    def __init__(self, tweet_data, **kwargs):
        super().__init__(**kwargs)
        self.tweet_data = tweet_data
        self.text = tweet_data['text']
        self.author_name = tweet_data['author']['name']
        self.author_username = tweet_data['author']['username']
        self.profile_image = tweet_data['author']['profile_image']
        
        # Tarihi formatla
        created_at = datetime.fromisoformat(tweet_data['created_at'])
        self.created_at = created_at.strftime("%d %b %Y, %H:%M")
        
        # Medya URL'lerini ayarla
        self.media_urls = tweet_data['media']
    
    def toggle_selection(self):
        """Tweet seçimini değiştir"""
        self.is_selected = not self.is_selected

class TweetCutterScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tweet_extractor = TweetExtractor()
        self.thread = []
        self.selected_tweets = set()
    
    def on_enter(self, *args):
        """Ekran açıldığında çalışır"""
        # Paylaşılan URL'i al
        shared_url = self.manager.shared_url
        if shared_url:
            self.process_tweet(shared_url)
    
    def process_tweet(self, url):
        """Tweet URL'ini işle"""
        # Yükleniyor göstergesini başlat
        self.ids.loading_indicator.active = True
        
        # Arka planda tweet'i çek
        threading.Thread(target=self._extract_tweet, args=(url,)).start()
    
    def _extract_tweet(self, url):
        """Arka planda tweet'i çek"""
        # Önce thread olup olmadığını kontrol et
        result = self.tweet_extractor.get_thread(url)
        
        if result['status'] == 'success' and len(result['thread']) > 1:
            # Thread bulundu
            Clock.schedule_once(lambda dt: self._handle_thread_result(result))
        else:
            # Tek tweet
            result = self.tweet_extractor.get_tweet(url)
            Clock.schedule_once(lambda dt: self._handle_tweet_result(result))
    
    def _handle_tweet_result(self, result):
        """Tek tweet sonucunu işle"""
        self.ids.loading_indicator.active = False
        
        if result['status'] == 'success':
            # Tweet'i thread listesine ekle
            self.thread = [result['tweet']]
            
            # Tweet kartını oluştur ve göster
            self._create_tweet_cards()
            
        else:
            # Hata mesajını göster
            self.ids.error_label.text = f"Tweet yüklenemedi: {result['error']}"
            self.ids.error_label.opacity = 1
    
    def _handle_thread_result(self, result):
        """Thread sonucunu işle"""
        self.ids.loading_indicator.active = False
        
        if result['status'] == 'success':
            # Thread'i sakla
            self.thread = result['thread']
            
            # Tweet kartlarını oluştur ve göster
            self._create_tweet_cards()
            
        else:
            # Hata mesajını göster
            self.ids.error_label.text = f"Thread yüklenemedi: {result['error']}"
            self.ids.error_label.opacity = 1
    
    def _create_tweet_cards(self):
        """Tweet kartlarını oluştur"""
        # Tweet container'ı temizle
        self.ids.tweets_container.clear_widgets()
        
        # Her tweet için kart oluştur
        for tweet in self.thread:
            card = TweetCard(tweet)
            self.ids.tweets_container.add_widget(card)
    
    def on_tweet_selection(self, tweet_card):
        """Tweet seçimi değiştiğinde"""
        tweet_id = tweet_card.tweet_data['id']
        
        if tweet_card.is_selected:
            self.selected_tweets.add(tweet_id)
        else:
            self.selected_tweets.discard(tweet_id)
        
        # Kaydet butonunu güncelle
        self.ids.save_button.disabled = len(self.selected_tweets) == 0
    
    def save_selection(self):
        """Seçili tweet'leri koleksiyona kaydet"""
        if self.thread and self.selected_tweets:
            # Seçili tweet'leri filtrele
            selected_tweets = [
                tweet for tweet in self.thread
                if tweet['id'] in self.selected_tweets
            ]
            
            collection_item = {
                'content_type': 'tweet',
                'source_url': self.manager.shared_url,
                'tweets': selected_tweets,
                'author': selected_tweets[0]['author'],
                'created_at': selected_tweets[0]['created_at'],
                'is_thread': len(selected_tweets) > 1,
                'metadata': {
                    'tweet_count': len(selected_tweets),
                    'media_count': sum(len(t['media']) for t in selected_tweets),
                    'stats': {
                        'total_likes': sum(t['metrics']['like_count'] for t in selected_tweets),
                        'total_retweets': sum(t['metrics']['retweet_count'] for t in selected_tweets),
                        'total_replies': sum(t['metrics']['reply_count'] for t in selected_tweets)
                    }
                }
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
    
    def on_leave(self):
        """Ekrandan çıkıldığında temizlik yap"""
        self.thread = []
        self.selected_tweets.clear()
