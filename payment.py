import os
import stripe
from datetime import datetime
from typing import Optional, Dict, Tuple
from dotenv import load_dotenv
from models import PremiumType

load_dotenv()

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

class Payment:
    PLANS = {
        PremiumType.STARTER: {
            'monthly': {
                'amount': 5000,  # 50 TL
                'stripe_price_id': 'price_starter_monthly'
            },
            'yearly': {
                'amount': 50000,  # 500 TL
                'stripe_price_id': 'price_starter_yearly'
            }
        },
        PremiumType.STANDARD: {
            'monthly': {
                'amount': 10000,  # 100 TL
                'stripe_price_id': 'price_standard_monthly'
            },
            'yearly': {
                'amount': 100000,  # 1000 TL
                'stripe_price_id': 'price_standard_yearly'
            }
        },
        PremiumType.PRO: {
            'monthly': {
                'amount': 15000,  # 150 TL
                'stripe_price_id': 'price_pro_monthly'
            },
            'yearly': {
                'amount': 150000,  # 1500 TL
                'stripe_price_id': 'price_pro_yearly'
            }
        },
        PremiumType.UNLIMITED: {
            'monthly': {
                'amount': 20000,  # 200 TL
                'stripe_price_id': 'price_unlimited_monthly'
            },
            'yearly': {
                'amount': 200000,  # 2000 TL
                'stripe_price_id': 'price_unlimited_yearly'
            }
        }
    }
    
    def __init__(self, db):
        self.db = db
    
    def create_checkout_session(self, user_id: str, plan_type: PremiumType, interval: str) -> Optional[str]:
        """Ödeme sayfası oluştur"""
        try:
            user = self.db.get_user(user_id)
            if not user:
                return None
            
            plan = self.PLANS.get(plan_type, {}).get(interval)
            if not plan:
                return None
            
            session = stripe.checkout.Session.create(
                customer_email=user.email,
                payment_method_types=['card'],
                line_items=[{
                    'price': plan['stripe_price_id'],
                    'quantity': 1,
                }],
                mode='subscription',
                success_url='http://localhost:8000/payment/success?session_id={CHECKOUT_SESSION_ID}',
                cancel_url='http://localhost:8000/payment/cancel',
                metadata={
                    'user_id': user_id,
                    'plan_type': plan_type.value,
                    'interval': interval
                }
            )
            
            return session.id
            
        except Exception as e:
            print(f"Ödeme sayfası oluşturma hatası: {str(e)}")
            return None
    
    def handle_webhook(self, event_data: Dict) -> Tuple[bool, str]:
        """Stripe webhook'unu işle"""
        try:
            event_type = event_data['type']
            
            if event_type == 'checkout.session.completed':
                session = event_data['data']['object']
                user_id = session['metadata']['user_id']
                plan_type = PremiumType(session['metadata']['plan_type'])
                interval = session['metadata']['interval']
                
                # Kullanıcının premium planını güncelle
                subscription_end = datetime.now()
                if interval == 'monthly':
                    subscription_end = subscription_end.replace(month=subscription_end.month + 1)
                else:  # yearly
                    subscription_end = subscription_end.replace(year=subscription_end.year + 1)
                
                self.db.update_user(user_id, {
                    'premium_type': plan_type,
                    'subscription_end': str(subscription_end)
                })
                
                return True, "Ödeme başarılı"
                
            elif event_type == 'customer.subscription.deleted':
                subscription = event_data['data']['object']
                user_id = subscription['metadata']['user_id']
                
                # Kullanıcıyı ücretsiz plana düşür
                self.db.update_user(user_id, {
                    'premium_type': PremiumType.FREE,
                    'subscription_end': None
                })
                
                return True, "Abonelik iptal edildi"
            
            return True, "Event işlendi"
            
        except Exception as e:
            return False, str(e)
    
    def cancel_subscription(self, user_id: str) -> Tuple[bool, str]:
        """Aboneliği iptal et"""
        try:
            user = self.db.get_user(user_id)
            if not user:
                return False, "Kullanıcı bulunamadı"
            
            if not user.stripe_subscription_id:
                return False, "Aktif abonelik bulunamadı"
            
            # Stripe aboneliğini iptal et
            subscription = stripe.Subscription.delete(user.stripe_subscription_id)
            
            if subscription.status == 'canceled':
                # Kullanıcıyı ücretsiz plana düşür
                self.db.update_user(user_id, {
                    'premium_type': PremiumType.FREE,
                    'subscription_end': None,
                    'stripe_subscription_id': None
                })
                
                return True, "Abonelik başarıyla iptal edildi"
            
            return False, "Abonelik iptal edilemedi"
            
        except Exception as e:
            return False, str(e)
