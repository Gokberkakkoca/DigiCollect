from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime

@dataclass
class PremiumPlan:
    name: str
    collection_limit: int
    items_per_collection: int
    monthly_price: float
    yearly_price: float
    description: str

class PremiumManager:
    PLANS = {
        'free': PremiumPlan(
            name='Ücretsiz Plan',
            collection_limit=1,
            items_per_collection=20,
            monthly_price=0,
            yearly_price=0,
            description='Tek koleksiyon ve her koleksiyonda 20 içerik'
        ),
        'starter': PremiumPlan(
            name='Başlangıç Planı',
            collection_limit=2,
            items_per_collection=25,
            monthly_price=50,
            yearly_price=500,
            description='2 koleksiyon ve her koleksiyonda 25 içerik'
        ),
        'standard': PremiumPlan(
            name='Standart Plan',
            collection_limit=3,
            items_per_collection=30,
            monthly_price=100,
            yearly_price=1000,
            description='3 koleksiyon ve her koleksiyonda 30 içerik'
        ),
        'pro': PremiumPlan(
            name='Pro Plan',
            collection_limit=4,
            items_per_collection=35,
            monthly_price=150,
            yearly_price=1500,
            description='4 koleksiyon ve her koleksiyonda 35 içerik'
        ),
        'unlimited': PremiumPlan(
            name='Sınırsız Plan',
            collection_limit=float('inf'),
            items_per_collection=40,
            monthly_price=200,
            yearly_price=2000,
            description='Sınırsız koleksiyon ve her koleksiyonda 40 içerik'
        )
    }

    def __init__(self, db):
        self.db = db

    def get_plan(self, plan_name: str) -> Optional[PremiumPlan]:
        """Plan detaylarını getir"""
        return self.PLANS.get(plan_name)

    def get_user_limits(self, user_id: str) -> Dict[str, int]:
        """Kullanıcının plan limitlerini getir"""
        user = self.db.get_user_by_id(user_id)
        if not user:
            return {'collection_limit': 0, 'items_per_collection': 0}
        
        plan = self.get_plan(user.premium_type)
        if not plan:
            return {'collection_limit': 0, 'items_per_collection': 0}
        
        return {
            'collection_limit': plan.collection_limit,
            'items_per_collection': plan.items_per_collection
        }

    def can_create_collection(self, user_id: str) -> bool:
        """Kullanıcı yeni koleksiyon oluşturabilir mi"""
        user = self.db.get_user_by_id(user_id)
        if not user:
            return False
        
        plan = self.get_plan(user.premium_type)
        if not plan:
            return False
        
        current_collections = len(self.db.get_user_collections(user_id))
        return current_collections < plan.collection_limit

    def can_add_item_to_collection(self, user_id: str, collection_id: str) -> bool:
        """Koleksiyona yeni içerik eklenebilir mi"""
        user = self.db.get_user_by_id(user_id)
        if not user:
            return False
        
        plan = self.get_plan(user.premium_type)
        if not plan:
            return False
        
        collection = self.db.get_collection_by_id(collection_id)
        if not collection:
            return False
        
        return collection.total_items_added < plan.items_per_collection

    def upgrade_plan(self, user_id: str, new_plan: str, payment_period: str = 'monthly') -> bool:
        """Kullanıcının planını yükselt"""
        try:
            if new_plan not in self.PLANS:
                return False
            
            user = self.db.get_user_by_id(user_id)
            if not user:
                return False
            
            # Plan yükseltme işlemi
            self.db.update_user_premium(
                user_id=user_id,
                premium_type=new_plan,
                premium_expiry=self._calculate_expiry(payment_period)
            )
            
            return True
            
        except Exception as e:
            print(f"Plan yükseltme hatası: {str(e)}")
            return False

    @staticmethod
    def _calculate_expiry(payment_period: str) -> str:
        """Planın bitiş tarihini hesapla"""
        now = datetime.now()
        if payment_period == 'yearly':
            expiry = now.replace(year=now.year + 1)
        else:  # monthly
            if now.month == 12:
                expiry = now.replace(year=now.year + 1, month=1)
            else:
                expiry = now.replace(month=now.month + 1)
        
        return expiry.strftime('%Y-%m-%d %H:%M:%S')
