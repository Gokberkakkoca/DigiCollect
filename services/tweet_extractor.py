import tweepy
import re
import os
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import json
from dotenv import load_dotenv

class TweetExtractor:
    def __init__(self):
        # .env dosyasından API anahtarlarını yükle
        load_dotenv()
        
        # Twitter API kimlik bilgileri
        self.api_key = os.getenv('TWITTER_API_KEY')
        self.api_secret = os.getenv('TWITTER_API_SECRET')
        self.access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        self.access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        self.bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        
        # API istemcisini başlat
        if all([self.api_key, self.api_secret, self.bearer_token]):
            self.client = tweepy.Client(
                bearer_token=self.bearer_token,
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
                wait_on_rate_limit=True
            )
        else:
            raise ValueError("Twitter API kimlik bilgileri eksik. Lütfen .env dosyasını kontrol edin.")
    
    def extract_tweet_id(self, url):
        """Tweet URL'inden tweet ID'sini çıkar"""
        try:
            # URL'i parse et
            parsed_url = urlparse(url)
            
            # Twitter URL formatlarını kontrol et
            if parsed_url.netloc in ['twitter.com', 'x.com']:
                # /status/ formatı
                if '/status/' in url:
                    tweet_id = url.split('/status/')[1].split('?')[0]
                    return tweet_id
                
                # ?id= formatı
                query_params = parse_qs(parsed_url.query)
                if 'id' in query_params:
                    return query_params['id'][0]
            
            raise ValueError("Geçersiz tweet URL'i")
            
        except Exception as e:
            raise ValueError(f"Tweet ID çıkarılamadı: {str(e)}")
    
    def get_tweet(self, url):
        """Tweet URL'inden tweet bilgilerini al"""
        try:
            # Tweet ID'sini çıkar
            tweet_id = self.extract_tweet_id(url)
            
            # Tweet'i al
            tweet = self.client.get_tweet(
                tweet_id,
                expansions=['author_id', 'attachments.media_keys'],
                tweet_fields=['created_at', 'public_metrics', 'entities'],
                user_fields=['name', 'username', 'profile_image_url'],
                media_fields=['url', 'preview_image_url']
            )
            
            if not tweet.data:
                raise ValueError("Tweet bulunamadı")
            
            # Tweet sahibi bilgilerini al
            author = tweet.includes['users'][0] if 'users' in tweet.includes else None
            
            # Medya bilgilerini al
            media = tweet.includes.get('media', [])
            media_urls = []
            for m in media:
                if hasattr(m, 'url'):
                    media_urls.append(m.url)
                elif hasattr(m, 'preview_image_url'):
                    media_urls.append(m.preview_image_url)
            
            # Tweet verilerini yapılandır
            tweet_data = {
                'id': tweet.data.id,
                'text': tweet.data.text,
                'created_at': tweet.data.created_at.isoformat(),
                'metrics': tweet.data.public_metrics,
                'author': {
                    'id': author.id if author else None,
                    'name': author.name if author else None,
                    'username': author.username if author else None,
                    'profile_image': author.profile_image_url if author else None
                },
                'media': media_urls,
                'url': url
            }
            
            return {
                'status': 'success',
                'tweet': tweet_data
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_thread(self, url):
        """Tweet thread'ini al"""
        try:
            # İlk tweet'i al
            result = self.get_tweet(url)
            if result['status'] != 'success':
                return result
            
            tweet_data = result['tweet']
            thread = [tweet_data]
            
            # Thread'i bul
            conversation_id = tweet_data['id']
            author_id = tweet_data['author']['id']
            
            # Thread'deki diğer tweet'leri al
            tweets = self.client.search_recent_tweets(
                query=f"conversation_id:{conversation_id} from:{author_id}",
                tweet_fields=['created_at', 'public_metrics', 'in_reply_to_user_id'],
                user_fields=['name', 'username', 'profile_image_url'],
                media_fields=['url', 'preview_image_url'],
                expansions=['author_id', 'attachments.media_keys']
            )
            
            if tweets.data:
                for tweet in tweets.data:
                    # Tweet verilerini yapılandır
                    thread_tweet = {
                        'id': tweet.id,
                        'text': tweet.text,
                        'created_at': tweet.created_at.isoformat(),
                        'metrics': tweet.public_metrics,
                        'author': tweet_data['author'],  # Ana tweet'in yazarı
                        'media': []  # Medya bilgileri
                    }
                    
                    # Medya varsa ekle
                    if hasattr(tweet, 'attachments') and 'media_keys' in tweet.attachments:
                        for media in tweets.includes.get('media', []):
                            if hasattr(media, 'url'):
                                thread_tweet['media'].append(media.url)
                            elif hasattr(media, 'preview_image_url'):
                                thread_tweet['media'].append(media.preview_image_url)
                    
                    thread.append(thread_tweet)
            
            # Thread'i tarihe göre sırala
            thread.sort(key=lambda x: x['created_at'])
            
            return {
                'status': 'success',
                'thread': thread
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def format_tweet_text(self, text):
        """Tweet metnini formatla"""
        # Mention'ları vurgula
        text = re.sub(r'@(\w+)', r'**@\1**', text)
        
        # Hashtag'leri vurgula
        text = re.sub(r'#(\w+)', r'**#\1**', text)
        
        # URL'leri temizle
        text = re.sub(r'https?://\S+', '', text)
        
        return text.strip()
    
    def get_tweet_stats(self, tweet_data):
        """Tweet istatistiklerini al"""
        metrics = tweet_data['metrics']
        return {
            'likes': metrics['like_count'],
            'retweets': metrics['retweet_count'],
            'replies': metrics['reply_count'],
            'quotes': metrics.get('quote_count', 0)
        }
