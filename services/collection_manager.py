from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, ForeignKey, Table, Boolean, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json
import os
from pathlib import Path
import enum
import secrets

Base = declarative_base()

class VisibilityType(enum.Enum):
    """Koleksiyon görünürlük türleri"""
    PRIVATE = "private"      # Sadece sahibi görebilir
    PUBLIC = "public"        # Herkes görebilir
    UNLISTED = "unlisted"   # Bağlantıya sahip olanlar görebilir

class User(Base):
    """Kullanıcı modeli"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    content_count = Column(Integer, default=0)  # Toplam eklenen içerik sayısı
    plan_limit = Column(Integer, default=25)    # Kullanıcının plan sınırı
    
    # İlişkiler
    collections = relationship('Collection', back_populates='user')
    followed_collections = relationship(
        'Collection',
        secondary='collection_followers',
        backref='followers'
    )

# Koleksiyon ve öğe arasındaki ilişki tablosu
collection_items = Table(
    'collection_items',
    Base.metadata,
    Column('collection_id', Integer, ForeignKey('collections.id')),
    Column('item_id', Integer, ForeignKey('items.id'))
)

# Koleksiyon takipçileri tablosu
collection_followers = Table(
    'collection_followers',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('collection_id', Integer, ForeignKey('collections.id')),
    Column('followed_at', DateTime, default=datetime.utcnow)
)

class Collection(Base):
    """Koleksiyon modeli"""
    __tablename__ = 'collections'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    cover_image = Column(String)  # Kapak resmi yolu
    visibility = Column(Enum(VisibilityType), default=VisibilityType.PRIVATE)
    share_token = Column(String, unique=True)  # Paylaşım bağlantısı için benzersiz token
    
    # Kullanıcı ilişkisi
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship('User', back_populates='collections')
    
    # İlişkiler
    items = relationship(
        'Item',
        secondary=collection_items,
        back_populates='collections'
    )

class Item(Base):
    """Koleksiyon öğesi modeli"""
    __tablename__ = 'items'
    
    id = Column(Integer, primary_key=True)
    content_type = Column(String, nullable=False)  # video, music, blog, tweet, instagram
    source_url = Column(String)
    title = Column(String)
    description = Column(String)
    content_path = Column(String)  # İndirilen içeriğin yolu
    thumbnail_path = Column(String)  # Küçük resim yolu
    metadata = Column(JSON)  # İçerik türüne özel meta veriler
    created_at = Column(DateTime, default=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)  # Silinme durumu
    
    # İlişkiler
    collections = relationship(
        'Collection',
        secondary=collection_items,
        back_populates='items'
    )

class CollectionManager:
    def __init__(self):
        # Veritabanı dizini
        self.db_dir = Path.home() / 'DigiCollect' / 'data'
        self.db_dir.mkdir(parents=True, exist_ok=True)
        
        # SQLite veritabanı bağlantısı
        self.engine = create_engine(f'sqlite:///{self.db_dir}/collections.db')
        Base.metadata.create_all(self.engine)
        
        # Oturum oluşturucu
        self.Session = sessionmaker(bind=self.engine)
        
        # Varsayılan kullanıcıyı oluştur veya al
        self._ensure_default_user()
    
    def _ensure_default_user(self):
        """Varsayılan kullanıcıyı oluştur veya al"""
        session = self.Session()
        try:
            user = session.query(User).filter_by(username='default').first()
            if not user:
                user = User(username='default', plan_limit=25)
                session.add(user)
                session.commit()
            self.default_user_id = user.id
        finally:
            session.close()
    
    def can_add_content(self, user_id=None):
        """Kullanıcının içerik ekleyip ekleyemeyeceğini kontrol et"""
        if user_id is None:
            user_id = self.default_user_id
            
        session = self.Session()
        try:
            user = session.query(User).get(user_id)
            if not user:
                return False
            return user.content_count < user.plan_limit
        finally:
            session.close()
    
    def increment_content_count(self, user_id=None):
        """Kullanıcının içerik sayacını artır"""
        if user_id is None:
            user_id = self.default_user_id
            
        session = self.Session()
        try:
            user = session.query(User).get(user_id)
            if not user:
                return False
            user.content_count += 1
            session.commit()
            return True
        finally:
            session.close()

    def create_collection(self, name, description=None, cover_image=None):
        """Yeni koleksiyon oluştur"""
        try:
            session = self.Session()
            
            # Aynı isimde koleksiyon var mı kontrol et
            existing = session.query(Collection).filter_by(name=name).first()
            if existing:
                raise ValueError(f"'{name}' isimli koleksiyon zaten var")
            
            # Yeni koleksiyon oluştur
            collection = Collection(
                name=name,
                description=description,
                cover_image=cover_image
            )
            
            session.add(collection)
            session.commit()
            
            return {
                'status': 'success',
                'collection_id': collection.id
            }
            
        except Exception as e:
            session.rollback()
            return {
                'status': 'error',
                'error': str(e)
            }
        finally:
            session.close()
    
    def get_collection(self, collection_id):
        """Koleksiyon bilgilerini al"""
        try:
            session = self.Session()
            
            collection = session.query(Collection).get(collection_id)
            if not collection:
                raise ValueError(f"Koleksiyon bulunamadı: {collection_id}")
            
            return {
                'status': 'success',
                'collection': {
                    'id': collection.id,
                    'name': collection.name,
                    'description': collection.description,
                    'cover_image': collection.cover_image,
                    'created_at': collection.created_at.isoformat(),
                    'updated_at': collection.updated_at.isoformat(),
                    'item_count': len(collection.items)
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
        finally:
            session.close()
    
    def list_collections(self):
        """Tüm koleksiyonları listele"""
        try:
            session = self.Session()
            
            collections = session.query(Collection).all()
            collection_list = []
            
            for collection in collections:
                collection_list.append({
                    'id': collection.id,
                    'name': collection.name,
                    'description': collection.description,
                    'cover_image': collection.cover_image,
                    'created_at': collection.created_at.isoformat(),
                    'updated_at': collection.updated_at.isoformat(),
                    'item_count': len(collection.items)
                })
            
            return {
                'status': 'success',
                'collections': collection_list
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
        finally:
            session.close()
    
    def add_item(self, collection_id, item_data):
        """Koleksiyona öğe ekle"""
        try:
            session = self.Session()
            
            # Koleksiyonu bul
            collection = session.query(Collection).get(collection_id)
            if not collection:
                raise ValueError(f"Koleksiyon bulunamadı: {collection_id}")
            
            # İçerik ekleme sınırını kontrol et
            if not self.can_add_content(collection.user_id):
                raise ValueError("İçerik ekleme sınırına ulaşıldı")
            
            # Yeni öğe oluştur
            item = Item(
                content_type=item_data['content_type'],
                source_url=item_data.get('source_url'),
                title=item_data.get('title'),
                description=item_data.get('description'),
                content_path=item_data.get('content_path'),
                thumbnail_path=item_data.get('thumbnail_path'),
                metadata=item_data.get('metadata', {})
            )
            
            # Öğeyi koleksiyona ekle
            collection.items.append(item)
            session.add(item)
            
            # İçerik sayacını artır
            self.increment_content_count(collection.user_id)
            
            session.commit()
            
            return {
                'status': 'success',
                'item_id': item.id
            }
            
        except Exception as e:
            session.rollback()
            return {
                'status': 'error',
                'error': str(e)
            }
        finally:
            session.close()
    
    def get_collection_items(self, collection_id):
        """Koleksiyondaki öğeleri al"""
        try:
            session = self.Session()
            
            collection = session.query(Collection).get(collection_id)
            if not collection:
                raise ValueError(f"Koleksiyon bulunamadı: {collection_id}")
            
            items = []
            for item in collection.items:
                items.append({
                    'id': item.id,
                    'content_type': item.content_type,
                    'source_url': item.source_url,
                    'title': item.title,
                    'description': item.description,
                    'content_path': item.content_path,
                    'thumbnail_path': item.thumbnail_path,
                    'metadata': item.metadata,
                    'created_at': item.created_at.isoformat()
                })
            
            return {
                'status': 'success',
                'items': items
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
        finally:
            session.close()
    
    def update_collection(self, collection_id, name=None, description=None, cover_image=None):
        """Koleksiyon bilgilerini güncelle"""
        try:
            session = self.Session()
            
            collection = session.query(Collection).get(collection_id)
            if not collection:
                raise ValueError(f"Koleksiyon bulunamadı: {collection_id}")
            
            if name is not None:
                collection.name = name
            if description is not None:
                collection.description = description
            if cover_image is not None:
                collection.cover_image = cover_image
            
            session.commit()
            
            return {
                'status': 'success'
            }
            
        except Exception as e:
            session.rollback()
            return {
                'status': 'error',
                'error': str(e)
            }
        finally:
            session.close()
    
    def delete_collection(self, collection_id):
        """Koleksiyonu sil"""
        try:
            session = self.Session()
            
            collection = session.query(Collection).get(collection_id)
            if not collection:
                raise ValueError(f"Koleksiyon bulunamadı: {collection_id}")
            
            session.delete(collection)
            session.commit()
            
            return {
                'status': 'success'
            }
            
        except Exception as e:
            session.rollback()
            return {
                'status': 'error',
                'error': str(e)
            }
        finally:
            session.close()
    
    def remove_item(self, collection_id, item_id):
        """Koleksiyondan öğe kaldır"""
        try:
            session = self.Session()
            
            collection = session.query(Collection).get(collection_id)
            if not collection:
                raise ValueError(f"Koleksiyon bulunamadı: {collection_id}")
            
            item = session.query(Item).get(item_id)
            if not item:
                raise ValueError(f"Öğe bulunamadı: {item_id}")
            
            # Öğeyi koleksiyondan kaldır
            collection.items.remove(item)
            
            # Öğeyi silindi olarak işaretle ama sayaçtan düşme
            item.is_deleted = True
            
            session.commit()
            
            return {
                'status': 'success'
            }
            
        except Exception as e:
            session.rollback()
            return {
                'status': 'error',
                'error': str(e)
            }
        finally:
            session.close()
    
    def move_item(self, item_id, source_collection_id, target_collection_id):
        """Öğeyi bir koleksiyondan diğerine taşı"""
        try:
            session = self.Session()
            
            source = session.query(Collection).get(source_collection_id)
            if not source:
                raise ValueError(f"Kaynak koleksiyon bulunamadı: {source_collection_id}")
            
            target = session.query(Collection).get(target_collection_id)
            if not target:
                raise ValueError(f"Hedef koleksiyon bulunamadı: {target_collection_id}")
            
            item = session.query(Item).get(item_id)
            if not item:
                raise ValueError(f"Öğe bulunamadı: {item_id}")
            
            source.items.remove(item)
            target.items.append(item)
            session.commit()
            
            return {
                'status': 'success'
            }
            
        except Exception as e:
            session.rollback()
            return {
                'status': 'error',
                'error': str(e)
            }
        finally:
            session.close()

    def set_visibility(self, collection_id, visibility_type):
        """Koleksiyon görünürlüğünü ayarla"""
        try:
            session = self.Session()
            
            collection = session.query(Collection).get(collection_id)
            if not collection:
                raise ValueError(f"Koleksiyon bulunamadı: {collection_id}")
            
            collection.visibility = VisibilityType(visibility_type)
            
            # Unlisted görünürlük için paylaşım tokeni oluştur
            if visibility_type == VisibilityType.UNLISTED and not collection.share_token:
                collection.share_token = secrets.token_urlsafe(16)
            
            session.commit()
            
            return {
                'status': 'success',
                'share_token': collection.share_token if visibility_type == VisibilityType.UNLISTED else None
            }
            
        except Exception as e:
            session.rollback()
            return {
                'status': 'error',
                'error': str(e)
            }
        finally:
            session.close()
    
    def follow_collection(self, user_id, collection_id):
        """Koleksiyonu takip et"""
        try:
            session = self.Session()
            
            collection = session.query(Collection).get(collection_id)
            if not collection:
                raise ValueError(f"Koleksiyon bulunamadı: {collection_id}")
            
            # Koleksiyonun görünürlüğünü kontrol et
            if collection.visibility == VisibilityType.PRIVATE:
                raise ValueError("Bu koleksiyon özel")
            
            # Kullanıcıyı bul
            user = session.query(User).get(user_id)
            if not user:
                raise ValueError(f"Kullanıcı bulunamadı: {user_id}")
            
            # Zaten takip ediyor mu kontrol et
            if collection in user.followed_collections:
                raise ValueError("Bu koleksiyon zaten takip ediliyor")
            
            # Takip et
            collection.followers.append(user)
            session.commit()
            
            return {
                'status': 'success'
            }
            
        except Exception as e:
            session.rollback()
            return {
                'status': 'error',
                'error': str(e)
            }
        finally:
            session.close()
    
    def unfollow_collection(self, user_id, collection_id):
        """Koleksiyon takibini bırak"""
        try:
            session = self.Session()
            
            collection = session.query(Collection).get(collection_id)
            if not collection:
                raise ValueError(f"Koleksiyon bulunamadı: {collection_id}")
            
            # Kullanıcıyı bul
            user = session.query(User).get(user_id)
            if not user:
                raise ValueError(f"Kullanıcı bulunamadı: {user_id}")
            
            # Takibi kontrol et
            if collection not in user.followed_collections:
                raise ValueError("Bu koleksiyon takip edilmiyor")
            
            # Takibi bırak
            collection.followers.remove(user)
            session.commit()
            
            return {
                'status': 'success'
            }
            
        except Exception as e:
            session.rollback()
            return {
                'status': 'error',
                'error': str(e)
            }
        finally:
            session.close()
    
    def get_collection_followers(self, collection_id):
        """Koleksiyon takipçilerini getir"""
        try:
            session = self.Session()
            
            collection = session.query(Collection).get(collection_id)
            if not collection:
                raise ValueError(f"Koleksiyon bulunamadı: {collection_id}")
            
            followers = []
            for user in collection.followers:
                followers.append({
                    'id': user.id,
                    'username': user.username,
                    'followed_at': session.query(collection_followers).filter_by(
                        user_id=user.id,
                        collection_id=collection_id
                    ).first().followed_at.isoformat()
                })
            
            return {
                'status': 'success',
                'followers': followers
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
        finally:
            session.close()
    
    def get_followed_collections(self, user_id):
        """Kullanıcının takip ettiği koleksiyonları getir"""
        try:
            session = self.Session()
            
            user = session.query(User).get(user_id)
            if not user:
                raise ValueError(f"Kullanıcı bulunamadı: {user_id}")
            
            collections = []
            for collection in user.followed_collections:
                collections.append({
                    'id': collection.id,
                    'name': collection.name,
                    'description': collection.description,
                    'cover_image': collection.cover_image,
                    'owner': {
                        'id': collection.user.id,
                        'username': collection.user.username
                    },
                    'followed_at': session.query(collection_followers).filter_by(
                        user_id=user_id,
                        collection_id=collection.id
                    ).first().followed_at.isoformat()
                })
            
            return {
                'status': 'success',
                'collections': collections
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
        finally:
            session.close()
    
    def get_public_collections(self):
        """Herkese açık koleksiyonları getir"""
        try:
            session = self.Session()
            
            collections = []
            for collection in session.query(Collection).filter_by(visibility=VisibilityType.PUBLIC).all():
                collections.append({
                    'id': collection.id,
                    'name': collection.name,
                    'description': collection.description,
                    'cover_image': collection.cover_image,
                    'owner': {
                        'id': collection.user.id,
                        'username': collection.user.username
                    },
                    'follower_count': len(collection.followers)
                })
            
            return {
                'status': 'success',
                'collections': collections
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
        finally:
            session.close()
    
    def get_collection_by_token(self, share_token):
        """Paylaşım tokeni ile koleksiyon getir"""
        try:
            session = self.Session()
            
            collection = session.query(Collection).filter_by(
                share_token=share_token,
                visibility=VisibilityType.UNLISTED
            ).first()
            
            if not collection:
                raise ValueError("Geçersiz paylaşım bağlantısı")
            
            return {
                'status': 'success',
                'collection': {
                    'id': collection.id,
                    'name': collection.name,
                    'description': collection.description,
                    'cover_image': collection.cover_image,
                    'owner': {
                        'id': collection.user.id,
                        'username': collection.user.username
                    },
                    'follower_count': len(collection.followers)
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
        finally:
            session.close()
