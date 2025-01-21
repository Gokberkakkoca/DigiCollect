from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional

Base = declarative_base()

class PremiumType(Enum):
    FREE = "free"
    STARTER = "starter"
    STANDARD = "standard"
    PRO = "pro"
    UNLIMITED = "unlimited"

class PremiumPlan:
    PLANS = {
        PremiumType.FREE: {"collections": 1, "items_per_collection": 20, "price_monthly": 0, "price_yearly": 0},
        PremiumType.STARTER: {"collections": 2, "items_per_collection": 25, "price_monthly": 50, "price_yearly": 500},
        PremiumType.STANDARD: {"collections": 3, "items_per_collection": 30, "price_monthly": 100, "price_yearly": 1000},
        PremiumType.PRO: {"collections": 4, "items_per_collection": 35, "price_monthly": 150, "price_yearly": 1500},
        PremiumType.UNLIMITED: {"collections": float('inf'), "items_per_collection": 40, "price_monthly": 200, "price_yearly": 2000},
    }

class Category:
    CATEGORIES = {
        "music": {
            "name": "Müzik",
            "icon": "music",
            "subcategories": []
        },
        "movies": {
            "name": "Film & Dizi",
            "icon": "movie",
            "subcategories": []
        },
        "comedy": {
            "name": "Komedi & Eğlence",
            "icon": "emoticon-happy",
            "subcategories": ["Stand-up", "Skeçler", "Mizah İçerikleri", "Komik Anlar", "Yazılar"]
        },
        "sports": {
            "name": "Spor",
            "icon": "basketball",
            "subcategories": ["Futbol", "Basketbol", "Fitness", "E-Spor", "Extreme Sporlar", "Spor Anları", "Antrenman İpuçları"]
        },
        "education": {
            "name": "Eğitim",
            "icon": "school",
            "subcategories": ["Akademik", "Dil Öğrenimi", "Yazılım", "Matematik", "Fen Bilimleri", "Tarih", "Kişisel Gelişim", "Diğer"]
        },
        "gaming": {
            "name": "Oyun",
            "icon": "gamepad-variant",
            "subcategories": []
        },
        "food": {
            "name": "Yemek",
            "icon": "food",
            "subcategories": []
        },
        "fashion": {
            "name": "Moda & Güzellik",
            "icon": "hanger",
            "subcategories": ["Stil İpuçları", "Makyaj", "Saç Modelleri", "Moda Trendleri", "Bakım Önerileri", "Alışveriş Önerileri"]
        },
        "technology": {
            "name": "Teknoloji",
            "icon": "laptop",
            "subcategories": ["Yazılım", "Donanım", "Mobil", "Yapay Zeka", "Yeni Ürünler", "İncelemeler", "İpuçları"]
        },
        "travel": {
            "name": "Seyahat",
            "icon": "airplane",
            "subcategories": []
        },
        "art": {
            "name": "Sanat",
            "icon": "palette",
            "subcategories": ["Resim", "Heykel", "Dijital Sanat", "Fotoğrafçılık", "El Sanatları", "Sokak Sanatı"]
        },
        "animals": {
            "name": "Hayvanlar",
            "icon": "paw",
            "subcategories": []
        },
        "beauty": {
            "name": "Güzeller",
            "icon": "face-woman",
            "subcategories": []
        },
        "handsome": {
            "name": "Yakışıklılar",
            "icon": "face-man",
            "subcategories": []
        },
        "celebrity": {
            "name": "Ünlüler/Magazin",
            "icon": "star",
            "subcategories": []
        }
    }
    
    @staticmethod
    def get_all_categories():
        return [{"id": k, **v} for k, v in Category.CATEGORIES.items()]
    
    @staticmethod
    def get_category(category_id: str):
        return Category.CATEGORIES.get(category_id)
    
    @staticmethod
    def get_subcategories(category_id: str):
        category = Category.CATEGORIES.get(category_id)
        return category["subcategories"] if category else []

class User(Base):
    __tablename__ = 'users'
    
    user_id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    profile_picture = Column(String)  # Profil resmi yolu
    premium_type = Column(String, default='free')  # free, starter, standard, pro, unlimited
    created_at = Column(DateTime, default=datetime.utcnow)
    
    collections = relationship("Collection", back_populates="user")

class Collection(Base):
    __tablename__ = 'collections'
    
    collection_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    name = Column(String, nullable=False)
    description = Column(String)
    category = Column(String, nullable=False)
    subcategory = Column(String)
    is_public = Column(Boolean, default=True)
    item_count = Column(Integer, default=0)  # Mevcut içerik sayısı
    total_items_added = Column(Integer, default=0)  # Toplam eklenmiş içerik sayısı (silinse bile)
    followers_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="collections")
    items = relationship("CollectionItem", back_populates="collection")
    followers = relationship("CollectionFollower", back_populates="collection")

class CollectionItem(Base):
    __tablename__ = 'collection_items'
    
    item_id = Column(Integer, primary_key=True)
    collection_id = Column(Integer, ForeignKey('collections.collection_id'))
    user_id = Column(Integer, ForeignKey('users.user_id'))
    content_type = Column(String, nullable=False)  # video, audio, text, image, spotify, podcast
    source_url = Column(String, nullable=False)
    title = Column(String)
    description = Column(String)
    thumbnail_url = Column(String)
    note = Column(String)  # Kullanıcı notu
    cut_data = Column(String)  # JSON formatında kesme bilgileri
    created_at = Column(DateTime, default=datetime.utcnow)
    
    collection = relationship("Collection", back_populates="items")

class CollectionFollower(Base):
    __tablename__ = 'collection_followers'
    
    id = Column(Integer, primary_key=True)
    collection_id = Column(Integer, ForeignKey('collections.collection_id'))
    follower_id = Column(Integer, ForeignKey('users.user_id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    collection = relationship("Collection", back_populates="followers")

class Category(Base):
    __tablename__ = 'categories'
    
    category_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    parent_id = Column(Integer, ForeignKey('categories.category_id'))
    
    subcategories = relationship("Category", 
                               backref=ForeignKey("categories.parent_id"),
                               remote_side=[category_id])

@dataclass
class CollectionTheme:
    background_color: str = "#FFFFFF"
    text_color: str = "#000000"
    accent_color: str = "#2196F3"
    icon: str = "folder"
    layout_type: str = "grid"  # grid, list, masonry

@dataclass
class Collection:
    collection_id: str
    user_id: str
    name: str
    description: str
    category: str
    subcategory: Optional[str] = None
    is_public: bool = True
    followers: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    item_count: int = 0
    total_items_added: int = 0
    theme: CollectionTheme = field(default_factory=CollectionTheme)
    created_at: str = str(datetime.now())
    followers_count: int = 0
    content_added_count: int = 0
    
    def __init__(self, collection_id=None, user_id=None, name=None, description=None, 
                 category=None, is_public=None, item_count=None, created_at=None, 
                 followers_count=0, content_added_count=0):
        self.collection_id = collection_id
        self.user_id = user_id
        self.name = name
        self.description = description
        self.category = category
        self.is_public = is_public
        self.item_count = item_count
        self.created_at = created_at
        self.followers_count = followers_count
        self.content_added_count = content_added_count

    def can_add_item(self, user: 'User') -> bool:
        """Koleksiyona yeni içerik eklenebilir mi kontrol et"""
        return user.can_add_item_to_collection(self.total_items_added)

    def to_dict(self) -> dict:
        """Koleksiyonu sözlüğe dönüştür"""
        return {
            'id': self.collection_id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'subcategory': self.subcategory,
            'tags': self.tags,
            'item_count': self.item_count,
            'theme': {
                'background_color': self.theme.background_color,
                'text_color': self.theme.text_color,
                'accent_color': self.theme.accent_color,
                'icon': self.theme.icon,
                'layout_type': self.theme.layout_type
            }
        }

@dataclass
class CollectionItem:
    id: str
    collection_id: str
    user_id: str
    title: str
    content_type: str
    source_url: str
    cut_data: dict
    created_at: str = str(datetime.now())
    updated_at: str = str(datetime.now())
    notes: str = ""
    tags: List[str] = field(default_factory=list)

@dataclass
class Subscription:
    id: str
    user_id: str
    plan_type: str  # 'free', 'premium', 'pro'
    start_date: str
    end_date: str
    status: str  # 'active', 'expired', 'cancelled'
    payment_method: str
    auto_renew: bool = True
    created_at: str = str(datetime.now())
    updated_at: str = str(datetime.now())

@dataclass
class PaymentHistory:
    id: str
    user_id: str
    subscription_id: str
    amount: float
    currency: str
    payment_method: str
    status: str  # 'success', 'failed', 'pending', 'refunded'
    created_at: str = str(datetime.now())
