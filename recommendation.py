from typing import List, Dict, Any
from collections import Counter
from models import Collection, CollectionItem
from database import Database

class RecommendationEngine:
    def __init__(self, db: Database):
        self.db = db

    def get_similar_collections(self, collection_id: str, limit: int = 5) -> List[Collection]:
        """Benzer koleksiyonları bul"""
        try:
            # Mevcut koleksiyonun özelliklerini al
            collection = self.db.get_collection_by_id(collection_id)
            if not collection:
                return []
            
            # Benzer koleksiyonları bul
            similar_collections = []
            all_collections = self.db.get_all_public_collections()
            
            for other in all_collections:
                if other.collection_id == collection_id:
                    continue
                
                similarity_score = self._calculate_similarity(collection, other)
                if similarity_score > 0:
                    similar_collections.append((other, similarity_score))
            
            # En benzer koleksiyonları döndür
            similar_collections.sort(key=lambda x: x[1], reverse=True)
            return [c[0] for c in similar_collections[:limit]]
            
        except Exception as e:
            print(f"Benzer koleksiyon bulma hatası: {str(e)}")
            return []

    def get_content_recommendations(self, item: CollectionItem, limit: int = 5) -> List[Dict[str, Any]]:
        """Benzer içerikleri öner"""
        try:
            # İçeriğin türünü ve etiketlerini al
            content_type = item.content_type
            tags = item.tags
            
            # Benzer içerikleri bul
            similar_items = []
            all_items = self.db.get_all_public_items()
            
            for other in all_items:
                if other.id == item.id:
                    continue
                
                if other.content_type == content_type:
                    similarity_score = self._calculate_content_similarity(item, other)
                    if similarity_score > 0:
                        similar_items.append((other, similarity_score))
            
            # En benzer içerikleri döndür
            similar_items.sort(key=lambda x: x[1], reverse=True)
            return [self._prepare_recommendation(i[0]) for i in similar_items[:limit]]
            
        except Exception as e:
            print(f"İçerik önerisi hatası: {str(e)}")
            return []

    def get_trending_collections(self, time_period: str = 'daily', limit: int = 10) -> List[Collection]:
        """Trend olan koleksiyonları getir"""
        try:
            # Zaman periyoduna göre koleksiyonları filtrele
            collections = self.db.get_trending_collections(time_period)
            
            # Popülerlik skorlarını hesapla
            scored_collections = []
            for collection in collections:
                score = self._calculate_popularity_score(collection)
                scored_collections.append((collection, score))
            
            # En popüler koleksiyonları döndür
            scored_collections.sort(key=lambda x: x[1], reverse=True)
            return [c[0] for c in scored_collections[:limit]]
            
        except Exception as e:
            print(f"Trend koleksiyon getirme hatası: {str(e)}")
            return []

    def _calculate_similarity(self, collection1: Collection, collection2: Collection) -> float:
        """İki koleksiyon arasındaki benzerliği hesapla"""
        score = 0.0
        
        # Kategori benzerliği
        if collection1.category == collection2.category:
            score += 0.4
            if collection1.subcategory == collection2.subcategory:
                score += 0.2
        
        # Etiket benzerliği
        common_tags = set(collection1.tags) & set(collection2.tags)
        if common_tags:
            score += 0.2 * (len(common_tags) / max(len(collection1.tags), len(collection2.tags)))
        
        # İçerik türü benzerliği
        items1 = self.db.get_collection_items(collection1.collection_id)
        items2 = self.db.get_collection_items(collection2.collection_id)
        
        types1 = Counter(item.content_type for item in items1)
        types2 = Counter(item.content_type for item in items2)
        
        common_types = set(types1.keys()) & set(types2.keys())
        if common_types:
            score += 0.2 * (len(common_types) / max(len(types1), len(types2)))
        
        return score

    def _calculate_content_similarity(self, item1: CollectionItem, item2: CollectionItem) -> float:
        """İki içerik arasındaki benzerliği hesapla"""
        score = 0.0
        
        # İçerik türü benzerliği
        if item1.content_type == item2.content_type:
            score += 0.4
        
        # Etiket benzerliği
        common_tags = set(item1.tags) & set(item2.tags)
        if common_tags:
            score += 0.4 * (len(common_tags) / max(len(item1.tags), len(item2.tags)))
        
        # Kaynak benzerliği
        if self._get_domain(item1.source_url) == self._get_domain(item2.source_url):
            score += 0.2
        
        return score

    def _calculate_popularity_score(self, collection: Collection) -> float:
        """Koleksiyonun popülerlik skorunu hesapla"""
        score = 0.0
        
        # Takipçi sayısı
        score += len(collection.followers) * 0.4
        
        # İçerik sayısı
        score += collection.item_count * 0.3
        
        # Görüntülenme sayısı (bu özellik eklenecek)
        # score += collection.views * 0.3
        
        return score

    def _prepare_recommendation(self, item: CollectionItem) -> Dict[str, Any]:
        """Önerilen içeriği hazırla"""
        collection = self.db.get_collection_by_id(item.collection_id)
        return {
            'id': item.id,
            'title': item.title,
            'content_type': item.content_type,
            'source_url': item.source_url,
            'collection_name': collection.name if collection else '',
            'collection_id': collection.collection_id if collection else '',
            'tags': item.tags
        }

    @staticmethod
    def _get_domain(url: str) -> str:
        """URL'den alan adını çıkar"""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except:
            return ""
