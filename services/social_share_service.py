import os
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, List, Optional, Union
import logging
from abc import ABC, abstractmethod

# Google/YouTube API
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Twitter API
import tweepy

# Instagram API
from instabot import Bot as InstaBot

# TikTok API
from tiktok_api import TikTokApi

# Spotify API
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Blog APIs
from wordpress_xmlrpc import Client as WPClient
from wordpress_xmlrpc.methods import posts
from blogger import blogger
import medium

# Diğer
import requests
from requests_oauthlib import OAuth1Session, OAuth2Session

class SocialPlatform(ABC):
    """Sosyal medya platformu temel sınıfı"""
    
    def __init__(self, credentials_dir: Path):
        self.credentials_dir = credentials_dir
        self.credentials_file = self.credentials_dir / f"{self.platform_name.lower()}_credentials.json"
        self.credentials = self._load_credentials()
        self.api = None
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Platform adı"""
        pass
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Platforma giriş yap"""
        pass
    
    @abstractmethod
    def share_content(self, content: Dict) -> Dict:
        """İçerik paylaş"""
        pass
    
    def _load_credentials(self) -> Dict:
        """Kimlik bilgilerini yükle"""
        try:
            if self.credentials_file.exists():
                with open(self.credentials_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Kimlik bilgileri yüklenemedi: {e}")
        return {}
    
    def _save_credentials(self, credentials: Dict):
        """Kimlik bilgilerini kaydet"""
        try:
            self.credentials_dir.mkdir(parents=True, exist_ok=True)
            with open(self.credentials_file, 'w') as f:
                json.dump(credentials, f)
        except Exception as e:
            logging.error(f"Kimlik bilgileri kaydedilemedi: {e}")

class YouTube(SocialPlatform):
    """YouTube platform entegrasyonu"""
    
    @property
    def platform_name(self) -> str:
        return "YouTube"
    
    def authenticate(self) -> bool:
        try:
            scopes = ['https://www.googleapis.com/auth/youtube.upload']
            
            creds = None
            if self.credentials:
                creds = Credentials.from_authorized_user_info(self.credentials, scopes)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_dir / 'youtube_client_secrets.json',
                        scopes
                    )
                    creds = flow.run_local_server(port=0)
                
                self._save_credentials(json.loads(creds.to_json()))
            
            self.api = build('youtube', 'v3', credentials=creds)
            return True
            
        except Exception as e:
            logging.error(f"YouTube kimlik doğrulama hatası: {e}")
            return False
    
    def share_content(self, content: Dict) -> Dict:
        try:
            if not self.api:
                raise ValueError("API bağlantısı yok")
            
            # Video yükle
            request = self.api.videos().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": content.get('title', ''),
                        "description": content.get('description', ''),
                        "tags": content.get('tags', []),
                        "categoryId": content.get('category_id', '22')
                    },
                    "status": {
                        "privacyStatus": content.get('privacy', 'private')
                    }
                },
                media_body=content['file_path']
            )
            
            response = request.execute()
            
            return {
                'status': 'success',
                'platform': self.platform_name,
                'post_id': response['id'],
                'url': f"https://youtube.com/watch?v={response['id']}"
            }
            
        except Exception as e:
            logging.error(f"YouTube paylaşım hatası: {e}")
            return {
                'status': 'error',
                'platform': self.platform_name,
                'error': str(e)
            }

class Instagram(SocialPlatform):
    """Instagram platform entegrasyonu"""
    
    @property
    def platform_name(self) -> str:
        return "Instagram"
    
    def authenticate(self) -> bool:
        try:
            self.api = InstaBot()
            self.api.login(
                username=self.credentials.get('username'),
                password=self.credentials.get('password')
            )
            return True
            
        except Exception as e:
            logging.error(f"Instagram kimlik doğrulama hatası: {e}")
            return False
    
    def share_content(self, content: Dict) -> Dict:
        try:
            if not self.api:
                raise ValueError("API bağlantısı yok")
            
            # Medya türüne göre paylaş
            if content.get('type') == 'photo':
                uploaded = self.api.upload_photo(
                    content['file_path'],
                    caption=content.get('caption', '')
                )
            elif content.get('type') == 'video':
                uploaded = self.api.upload_video(
                    content['file_path'],
                    caption=content.get('caption', '')
                )
            elif content.get('type') == 'album':
                uploaded = self.api.upload_album(
                    content['file_paths'],
                    caption=content.get('caption', '')
                )
            else:
                raise ValueError("Geçersiz medya türü")
            
            if uploaded:
                media_id = self.api.get_media_id(content['file_path'])
                return {
                    'status': 'success',
                    'platform': self.platform_name,
                    'post_id': media_id,
                    'url': f"https://instagram.com/p/{media_id}"
                }
            else:
                raise Exception("Medya yüklenemedi")
            
        except Exception as e:
            logging.error(f"Instagram paylaşım hatası: {e}")
            return {
                'status': 'error',
                'platform': self.platform_name,
                'error': str(e)
            }

class TikTok(SocialPlatform):
    """TikTok platform entegrasyonu"""
    
    @property
    def platform_name(self) -> str:
        return "TikTok"
    
    def authenticate(self) -> bool:
        try:
            self.api = TikTokApi()
            self.api.login(
                username=self.credentials.get('username'),
                password=self.credentials.get('password')
            )
            return True
            
        except Exception as e:
            logging.error(f"TikTok kimlik doğrulama hatası: {e}")
            return False
    
    def share_content(self, content: Dict) -> Dict:
        try:
            if not self.api:
                raise ValueError("API bağlantısı yok")
            
            # Video paylaş
            response = self.api.upload_video(
                video_path=content['file_path'],
                description=content.get('description', ''),
                thumbnail_path=content.get('thumbnail_path')
            )
            
            return {
                'status': 'success',
                'platform': self.platform_name,
                'post_id': response['video_id'],
                'url': f"https://tiktok.com/@{self.credentials['username']}/video/{response['video_id']}"
            }
            
        except Exception as e:
            logging.error(f"TikTok paylaşım hatası: {e}")
            return {
                'status': 'error',
                'platform': self.platform_name,
                'error': str(e)
            }

class Twitter(SocialPlatform):
    """Twitter platform entegrasyonu"""
    
    @property
    def platform_name(self) -> str:
        return "Twitter"
    
    def authenticate(self) -> bool:
        try:
            auth = tweepy.OAuthHandler(
                self.credentials.get('api_key'),
                self.credentials.get('api_secret')
            )
            auth.set_access_token(
                self.credentials.get('access_token'),
                self.credentials.get('access_token_secret')
            )
            
            self.api = tweepy.API(auth)
            self.api.verify_credentials()
            
            return True
            
        except Exception as e:
            logging.error(f"Twitter kimlik doğrulama hatası: {e}")
            return False
    
    def share_content(self, content: Dict) -> Dict:
        try:
            if not self.api:
                raise ValueError("API bağlantısı yok")
            
            # Medya varsa yükle
            media_ids = []
            if content.get('media_paths'):
                for media_path in content['media_paths']:
                    media = self.api.media_upload(media_path)
                    media_ids.append(media.media_id)
            
            # Tweet at
            tweet = self.api.update_status(
                status=content.get('text', ''),
                media_ids=media_ids if media_ids else None
            )
            
            return {
                'status': 'success',
                'platform': self.platform_name,
                'post_id': tweet.id,
                'url': f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}"
            }
            
        except Exception as e:
            logging.error(f"Twitter paylaşım hatası: {e}")
            return {
                'status': 'error',
                'platform': self.platform_name,
                'error': str(e)
            }

class Spotify(SocialPlatform):
    """Spotify platform entegrasyonu"""
    
    @property
    def platform_name(self) -> str:
        return "Spotify"
    
    def authenticate(self) -> bool:
        try:
            self.api = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=self.credentials.get('client_id'),
                client_secret=self.credentials.get('client_secret'),
                redirect_uri=self.credentials.get('redirect_uri'),
                scope='playlist-modify-public playlist-modify-private'
            ))
            return True
            
        except Exception as e:
            logging.error(f"Spotify kimlik doğrulama hatası: {e}")
            return False
    
    def share_content(self, content: Dict) -> Dict:
        try:
            if not self.api:
                raise ValueError("API bağlantısı yok")
            
            # Çalma listesi oluştur
            playlist = self.api.user_playlist_create(
                user=self.api.current_user()['id'],
                name=content.get('name', ''),
                public=content.get('public', False),
                description=content.get('description', '')
            )
            
            # Şarkıları ekle
            if content.get('track_uris'):
                self.api.playlist_add_items(
                    playlist_id=playlist['id'],
                    items=content['track_uris']
                )
            
            return {
                'status': 'success',
                'platform': self.platform_name,
                'post_id': playlist['id'],
                'url': playlist['external_urls']['spotify']
            }
            
        except Exception as e:
            logging.error(f"Spotify paylaşım hatası: {e}")
            return {
                'status': 'error',
                'platform': self.platform_name,
                'error': str(e)
            }

class Blogger(SocialPlatform):
    """Blogger platform entegrasyonu"""
    
    @property
    def platform_name(self) -> str:
        return "Blogger"
    
    def authenticate(self) -> bool:
        try:
            self.api = blogger.Blogger(
                client_id=self.credentials.get('client_id'),
                client_secret=self.credentials.get('client_secret'),
                redirect_uri=self.credentials.get('redirect_uri')
            )
            self.api.authenticate()
            return True
            
        except Exception as e:
            logging.error(f"Blogger kimlik doğrulama hatası: {e}")
            return False
    
    def share_content(self, content: Dict) -> Dict:
        try:
            if not self.api:
                raise ValueError("API bağlantısı yok")
            
            # Blog yazısı oluştur
            post = self.api.posts().insert(
                blogId=content.get('blog_id'),
                body={
                    'kind': 'blogger#post',
                    'title': content.get('title', ''),
                    'content': content.get('content', '')
                }
            ).execute()
            
            return {
                'status': 'success',
                'platform': self.platform_name,
                'post_id': post['id'],
                'url': post['url']
            }
            
        except Exception as e:
            logging.error(f"Blogger paylaşım hatası: {e}")
            return {
                'status': 'error',
                'platform': self.platform_name,
                'error': str(e)
            }

class SocialShareService:
    """Sosyal medya paylaşım servisi"""
    
    def __init__(self):
        self.credentials_dir = Path.home() / 'DigiCollect' / 'credentials'
        self.platforms = {
            'youtube': YouTube(self.credentials_dir),
            'instagram': Instagram(self.credentials_dir),
            'tiktok': TikTok(self.credentials_dir),
            'twitter': Twitter(self.credentials_dir),
            'spotify': Spotify(self.credentials_dir),
            'blogger': Blogger(self.credentials_dir)
        }
    
    def authenticate_platform(self, platform_name: str) -> Dict:
        """Platforma giriş yap"""
        try:
            platform = self.platforms.get(platform_name.lower())
            if not platform:
                raise ValueError(f"Platform bulunamadı: {platform_name}")
            
            success = platform.authenticate()
            
            return {
                'status': 'success' if success else 'error',
                'platform': platform_name,
                'error': None if success else "Kimlik doğrulama başarısız"
            }
            
        except Exception as e:
            logging.error(f"Platform kimlik doğrulama hatası: {e}")
            return {
                'status': 'error',
                'platform': platform_name,
                'error': str(e)
            }
    
    def share_content(self, platform_name: str, content: Dict) -> Dict:
        """İçeriği paylaş"""
        try:
            platform = self.platforms.get(platform_name.lower())
            if not platform:
                raise ValueError(f"Platform bulunamadı: {platform_name}")
            
            # Platforma giriş yap
            auth_result = self.authenticate_platform(platform_name)
            if auth_result['status'] != 'success':
                return auth_result
            
            # İçeriği paylaş
            return platform.share_content(content)
            
        except Exception as e:
            logging.error(f"İçerik paylaşım hatası: {e}")
            return {
                'status': 'error',
                'platform': platform_name,
                'error': str(e)
            }
    
    def share_to_multiple(self, platforms: List[str], content: Dict) -> Dict:
        """İçeriği birden fazla platforma paylaş"""
        results = {}
        
        for platform in platforms:
            results[platform] = self.share_content(platform, content)
        
        return {
            'status': 'success' if all(r['status'] == 'success' for r in results.values()) else 'error',
            'results': results
        }
