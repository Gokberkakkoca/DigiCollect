import os
import jwt
import uuid
import bcrypt
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Tuple
from dotenv import load_dotenv
from models import User
from database import Database

load_dotenv()

class Auth:
    def __init__(self, db):
        self.db = db
        self.jwt_secret = os.getenv('JWT_SECRET_KEY')
        self.smtp_server = os.getenv('SMTP_SERVER')
        self.smtp_port = int(os.getenv('SMTP_PORT'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
    
    def register_user(self, email: str, password: str, name: str) -> Tuple[bool, str]:
        """Yeni kullanıcı kaydı"""
        try:
            # Email kontrolü
            if self.db.get_user_by_email(email):
                return False, "Bu email zaten kayıtlı"
            
            # Şifre hash'leme
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            
            # Kullanıcıyı kaydet
            user = self.db.register_user(
                email=email,
                password=hashed.decode('utf-8'),
                name=name,
                verification_token=None
            )
            
            if not user:
                return False, "Kullanıcı oluşturulamadı"
            
            # Hoş geldiniz emaili gönder
            try:
                msg = MIMEMultipart()
                msg['From'] = self.smtp_username
                msg['To'] = email
                msg['Subject'] = "DigiCollect'e Hoş Geldiniz!"
                
                body = f"""
                <html>
                    <body style="font-family: Arial, sans-serif;">
                        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                            <h1 style="color: #333;">DigiCollect'e Hoş Geldiniz!</h1>
                            <p style="color: #666;">Merhaba {name},</p>
                            <p style="color: #666;">DigiCollect'e kayıt olduğunuz için teşekkür ederiz. Artık dijital içeriklerinizi kolayca toplayabilir, düzenleyebilir ve paylaşabilirsiniz.</p>
                            <p style="color: #666;">Başlamak için yapabileceğiniz bazı şeyler:</p>
                            <ul style="color: #666;">
                                <li>İlk koleksiyonunuzu oluşturun</li>
                                <li>Sevdiğiniz içerikleri kaydedin</li>
                                <li>Başkalarının koleksiyonlarını keşfedin</li>
                            </ul>
                            <p style="color: #666;">Herhangi bir sorunuz olursa bize ulaşmaktan çekinmeyin.</p>
                            <p style="color: #666;">İyi koleksiyonlar!</p>
                            <p style="color: #666;">DigiCollect Ekibi</p>
                        </div>
                    </body>
                </html>
                """
                
                msg.attach(MIMEText(body, 'html'))
                
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)
            except Exception as e:
                print(f"Email gönderme hatası: {str(e)}")
            
            return True, "Kayıt başarılı. Giriş yapabilirsiniz."
            
        except Exception as e:
            return False, str(e)
    
    def verify_email(self, token: str) -> Tuple[bool, str]:
        """Email doğrulama"""
        try:
            # Token'ı decode et
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            email = payload['email']
            
            # Kullanıcıyı bul ve doğrula
            user = self.db.get_user_by_email(email)
            if not user:
                return False, "Kullanıcı bulunamadı"
            
            if user.is_verified:
                return False, "Email zaten doğrulanmış"
            
            if user.verification_token != token:
                return False, "Geçersiz doğrulama kodu"
            
            # Kullanıcıyı doğrulanmış olarak işaretle
            self.db.update_user(user.user_id, {"is_verified": True, "verification_token": None})
            
            return True, "Email başarıyla doğrulandı"
            
        except jwt.ExpiredSignatureError:
            return False, "Doğrulama kodunun süresi dolmuş"
        except jwt.InvalidTokenError:
            return False, "Geçersiz doğrulama kodu"
        except Exception as e:
            return False, str(e)
    
    def login_user(self, email: str, password: str) -> Tuple[bool, str, Optional[User]]:
        """Kullanıcı girişi"""
        try:
            # Kullanıcıyı bul
            user = self.db.get_user_by_email(email)
            if not user:
                return False, "Email veya şifre hatalı", None
            
            # Şifreyi kontrol et
            try:
                if bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
                    return True, "Giriş başarılı", user
                else:
                    return False, "Email veya şifre hatalı", None
            except Exception as e:
                print(f"Şifre kontrolü hatası: {str(e)}")
                return False, "Email veya şifre hatalı", None
            
        except Exception as e:
            print(f"Giriş hatası: {str(e)}")
            return False, str(e), None
    
    def send_verification_email(self, email: str, token: str):
        """Doğrulama emaili gönder"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = email
            msg['Subject'] = "DigiCollect - Email Doğrulama"
            
            verification_url = f"http://localhost:5000/verify/{token}"
            
            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h1 style="color: #333;">DigiCollect'e Hoş Geldiniz!</h1>
                        <p style="color: #666;">Email adresinizi doğrulamak için aşağıdaki butona tıklayın:</p>
                        <a href="{verification_url}" 
                           style="display: inline-block; 
                                  background-color: #4CAF50; 
                                  color: white; 
                                  padding: 10px 20px; 
                                  text-decoration: none; 
                                  border-radius: 4px; 
                                  margin: 20px 0;">
                            Email Adresimi Doğrula
                        </a>
                        <p style="color: #666;">
                            Ya da bu linki tarayıcınızda açın:<br>
                            <a href="{verification_url}">{verification_url}</a>
                        </p>
                        <p style="color: #999; font-size: 12px;">
                            Bu email DigiCollect tarafından gönderilmiştir. 
                            Eğer bu işlemi siz yapmadıysanız, bu emaili görmezden gelebilirsiniz.
                        </p>
                    </div>
                </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
                
        except Exception as e:
            print(f"Email gönderme hatası: {str(e)}")
            raise e
    
    def send_password_reset_email(self, email: str) -> Tuple[bool, str]:
        """Şifre sıfırlama emaili gönder"""
        try:
            user = self.db.get_user_by_email(email)
            if not user:
                return False, "Bu email ile kayıtlı kullanıcı bulunamadı"
            
            # Reset token oluştur
            reset_token = jwt.encode(
                {
                    'user_id': user.user_id,
                    'exp': datetime.utcnow() + timedelta(hours=1)
                },
                self.jwt_secret,
                algorithm='HS256'
            )
            
            # Token'ı kullanıcıya kaydet
            self.db.update_user(user.user_id, {"reset_token": reset_token})
            
            # Email gönder
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = email
            msg['Subject'] = "DigiCollect Şifre Sıfırlama"
            
            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h1 style="color: #333;">DigiCollect Şifre Sıfırlama</h1>
                        <p style="color: #666;">Şifrenizi sıfırlamak için aşağıdaki butona tıklayın:</p>
                        <a href="http://localhost:8000/reset-password?token={reset_token}" 
                           style="display: inline-block; 
                                  background-color: #4CAF50; 
                                  color: white; 
                                  padding: 10px 20px; 
                                  text-decoration: none; 
                                  border-radius: 4px; 
                                  margin: 20px 0;">
                            Şifremi Sıfırla
                        </a>
                        <p style="color: #666;">
                            Ya da bu linki tarayıcınızda açın:<br>
                            <a href="http://localhost:8000/reset-password?token={reset_token}">http://localhost:8000/reset-password?token={reset_token}</a>
                        </p>
                        <p style="color: #999; font-size: 12px;">
                            Bu email DigiCollect tarafından gönderilmiştir. 
                            Eğer bu işlemi siz yapmadıysanız, bu emaili görmezden gelebilirsiniz.
                        </p>
                    </div>
                </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            return True, "Şifre sıfırlama linki email'inize gönderildi"
            
        except Exception as e:
            return False, str(e)
    
    def reset_password(self, token: str, new_password: str) -> Tuple[bool, str]:
        """Şifre sıfırlama"""
        try:
            # Token'ı decode et
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            user_id = payload['user_id']
            
            # Kullanıcıyı bul
            user = self.db.get_user(user_id)
            if not user:
                return False, "Kullanıcı bulunamadı"
            
            if user.reset_token != token:
                return False, "Geçersiz veya kullanılmış sıfırlama kodu"
            
            # Yeni şifreyi hash'le
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(new_password.encode('utf-8'), salt)
            
            # Şifreyi güncelle ve reset token'ı temizle
            self.db.update_user(user_id, {
                "password": hashed.decode('utf-8'),
                "reset_token": None
            })
            
            return True, "Şifreniz başarıyla güncellendi"
            
        except jwt.ExpiredSignatureError:
            return False, "Sıfırlama kodunun süresi dolmuş"
        except jwt.InvalidTokenError:
            return False, "Geçersiz sıfırlama kodu"
        except Exception as e:
            return False, str(e)

    def update_profile_image(self, user_id: str, image_path: str) -> Tuple[bool, str]:
        """Kullanıcının profil resmini güncelle"""
        try:
            # Resmi kontrol et
            if not os.path.exists(image_path):
                return False, "Resim dosyası bulunamadı"
            
            # Resmi doğrula
            try:
                from PIL import Image
                img = Image.open(image_path)
                img.verify()
            except Exception:
                return False, "Geçersiz resim dosyası"
            
            # Resmi assets/profile_images klasörüne kopyala
            profile_dir = os.path.join(os.path.dirname(__file__), 'assets', 'profile_images')
            os.makedirs(profile_dir, exist_ok=True)
            
            # Yeni dosya adı oluştur
            file_ext = os.path.splitext(image_path)[1]
            new_filename = f"{user_id}{file_ext}"
            new_path = os.path.join(profile_dir, new_filename)
            
            # Resmi kopyala
            import shutil
            shutil.copy2(image_path, new_path)
            
            # Veritabanını güncelle
            self.db.cursor.execute('''
                UPDATE users
                SET profile_image = ?
                WHERE id = ?
            ''', (new_filename, user_id))
            
            self.db.conn.commit()
            return True, "Profil resmi güncellendi"
            
        except Exception as e:
            return False, str(e)

    def remove_profile_image(self, user_id: str) -> Tuple[bool, str]:
        """Kullanıcının profil resmini kaldır"""
        try:
            # Mevcut profil resmini bul
            self.db.cursor.execute('SELECT profile_image FROM users WHERE id = ?', (user_id,))
            result = self.db.cursor.fetchone()
            
            if result and result[0]:
                # Resim dosyasını sil
                profile_dir = os.path.join(os.path.dirname(__file__), 'assets', 'profile_images')
                image_path = os.path.join(profile_dir, result[0])
                
                if os.path.exists(image_path):
                    os.remove(image_path)
            
            # Veritabanını güncelle
            self.db.cursor.execute('''
                UPDATE users
                SET profile_image = NULL
                WHERE id = ?
            ''', (user_id,))
            
            self.db.conn.commit()
            return True, "Profil resmi kaldırıldı"
            
        except Exception as e:
            return False, str(e)

    @staticmethod
    def send_email(to_email: str, subject: str, body_html: str) -> bool:
        """Email gönderme fonksiyonu"""
        try:
            # Email oluştur
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = os.getenv('SMTP_USERNAME')
            msg['To'] = to_email
            
            # HTML içeriği ekle
            html_part = MIMEText(body_html, 'html')
            msg.attach(html_part)
            
            # SMTP bağlantısı
            with smtplib.SMTP(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT'))) as server:
                server.starttls()
                server.login(os.getenv('SMTP_USERNAME'), os.getenv('SMTP_PASSWORD'))
                server.send_message(msg)
            
            return True
        except Exception as e:
            print(f"Email gönderme hatası: {str(e)}")
            return False
    
    @staticmethod
    def send_test_email(to_email: str) -> bool:
        """Test email gönder"""
        subject = "DigiCollect - Test Email"
        body_html = """
        <html>
            <body>
                <h2>DigiCollect Email Sistemi Test</h2>
                <p>Bu bir test emailidir. Email sistemi başarıyla çalışıyor!</p>
                <br>
                <p>Saygılarımızla,<br>DigiCollect Ekibi</p>
            </body>
        </html>
        """
        return Auth.send_email(to_email, subject, body_html)
