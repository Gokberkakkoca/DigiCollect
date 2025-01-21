from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, Collection, CollectionItem, CollectionFollower, Category
import bcrypt
import json

class Database:
    def __init__(self, db_path='digicollect.db'):
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def create_user(self, email, name, password):
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user = User(
            email=email,
            name=name,
            password_hash=password_hash.decode('utf-8'),
            premium_type='free'
        )
        self.session.add(user)
        self.session.commit()
        return user
    
    def update_user_profile(self, user_id, profile_picture=None, name=None):
        user = self.session.query(User).filter_by(user_id=user_id).first()
        if user:
            if profile_picture:
                user.profile_picture = profile_picture
            if name:
                user.name = name
            self.session.commit()
            return True
        return False
    
    def upgrade_premium(self, user_id, premium_type):
        user = self.session.query(User).filter_by(user_id=user_id).first()
        if user:
            user.premium_type = premium_type
            self.session.commit()
            return True
        return False
    
    def create_collection(self, user_id, name, description, category, subcategory=None, is_public=True):
        # Kullanıcının premium durumunu kontrol et
        user = self.session.query(User).filter_by(user_id=user_id).first()
        if not user:
            return None
        
        # Kullanıcının koleksiyon sayısını kontrol et
        collection_count = self.session.query(Collection).filter_by(user_id=user_id).count()
        max_collections = {
            'free': 1,
            'starter': 2,
            'standard': 3,
            'pro': 4,
            'unlimited': float('inf')
        }
        
        if collection_count >= max_collections.get(user.premium_type, 0):
            return None
        
        collection = Collection(
            user_id=user_id,
            name=name,
            description=description,
            category=category,
            subcategory=subcategory,
            is_public=is_public
        )
        self.session.add(collection)
        self.session.commit()
        return collection
    
    def add_item_to_collection(self, collection_id, user_id, content_data):
        collection = self.session.query(Collection).filter_by(
            collection_id=collection_id,
            user_id=user_id
        ).first()
        
        if not collection:
            return False
        
        # Koleksiyonun toplam içerik limitini kontrol et
        max_items = {
            'free': 20,
            'starter': 25,
            'standard': 30,
            'pro': 35,
            'unlimited': 40
        }
        
        user = self.session.query(User).filter_by(user_id=user_id).first()
        if collection.total_items_added >= max_items.get(user.premium_type, 0):
            return False
        
        item = CollectionItem(
            collection_id=collection_id,
            user_id=user_id,
            content_type=content_data['type'],
            source_url=content_data['url'],
            title=content_data.get('title'),
            description=content_data.get('description'),
            thumbnail_url=content_data.get('thumbnail'),
            note=content_data.get('note'),
            cut_data=json.dumps(content_data.get('cut_data', {}))
        )
        
        self.session.add(item)
        collection.item_count += 1
        collection.total_items_added += 1
        self.session.commit()
        return True
    
    def remove_item_from_collection(self, collection_id, item_id, user_id):
        item = self.session.query(CollectionItem).filter_by(
            item_id=item_id,
            collection_id=collection_id,
            user_id=user_id
        ).first()
        
        if not item:
            return False
        
        collection = self.session.query(Collection).filter_by(
            collection_id=collection_id
        ).first()
        
        if collection:
            collection.item_count -= 1
            # total_items_added değişmez
        
        self.session.delete(item)
        self.session.commit()
        return True
    
    def follow_collection(self, collection_id, follower_id):
        # Koleksiyonun public olduğunu kontrol et
        collection = self.session.query(Collection).filter_by(
            collection_id=collection_id,
            is_public=True
        ).first()
        
        if not collection:
            return False
        
        # Zaten takip edilip edilmediğini kontrol et
        existing = self.session.query(CollectionFollower).filter_by(
            collection_id=collection_id,
            follower_id=follower_id
        ).first()
        
        if existing:
            return False
        
        follower = CollectionFollower(
            collection_id=collection_id,
            follower_id=follower_id
        )
        
        self.session.add(follower)
        collection.followers_count += 1
        self.session.commit()
        return True
    
    def unfollow_collection(self, collection_id, follower_id):
        follower = self.session.query(CollectionFollower).filter_by(
            collection_id=collection_id,
            follower_id=follower_id
        ).first()
        
        if not follower:
            return False
        
        collection = self.session.query(Collection).filter_by(
            collection_id=collection_id
        ).first()
        
        if collection:
            collection.followers_count -= 1
        
        self.session.delete(follower)
        self.session.commit()
        return True
    
    def get_user_collections(self, user_id):
        return self.session.query(Collection).filter_by(user_id=user_id).all()
    
    def get_collection_items(self, collection_id, user_id=None):
        query = self.session.query(CollectionItem).filter_by(collection_id=collection_id)
        if user_id:
            query = query.filter_by(user_id=user_id)
        return query.all()
    
    def get_followed_collections(self, user_id):
        return self.session.query(Collection).join(
            CollectionFollower,
            Collection.collection_id == CollectionFollower.collection_id
        ).filter(
            CollectionFollower.follower_id == user_id,
            Collection.is_public == True
        ).all()
    
    def get_trending_collections(self, limit=10):
        return self.session.query(Collection).filter_by(
            is_public=True
        ).order_by(
            Collection.followers_count.desc()
        ).limit(limit).all()
    
    def search_collections(self, query, category=None, limit=20):
        q = self.session.query(Collection).filter(
            Collection.is_public == True,
            Collection.name.ilike(f'%{query}%')
        )
        
        if category:
            q = q.filter(Collection.category == category)
        
        return q.limit(limit).all()
    
    def get_collection_suggestions(self, user_id, limit=10):
        # Kullanıcının takip ettiği koleksiyonların kategorilerine göre öneriler
        followed = self.get_followed_collections(user_id)
        categories = set(c.category for c in followed)
        
        suggestions = []
        for category in categories:
            category_suggestions = self.session.query(Collection).filter(
                Collection.category == category,
                Collection.is_public == True,
                ~Collection.collection_id.in_([c.collection_id for c in followed])
            ).order_by(
                Collection.followers_count.desc()
            ).limit(limit // len(categories)).all()
            
            suggestions.extend(category_suggestions)
        
        return suggestions[:limit]
