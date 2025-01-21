import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

def send_test_email(to_email: str) -> bool:
    """Test email gönder"""
    try:
        # Email oluştur
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "DigiCollect - Test Email"
        msg['From'] = os.getenv('SMTP_USERNAME')
        msg['To'] = to_email
        
        # HTML içeriği
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
        
        # HTML içeriği ekle
        html_part = MIMEText(body_html, 'html')
        msg.attach(html_part)
        
        # SMTP bağlantısı
        with smtplib.SMTP(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT'))) as server:
            server.starttls()
            server.login(os.getenv('SMTP_USERNAME'), os.getenv('SMTP_PASSWORD'))
            server.send_message(msg)
        
        print("Email başarıyla gönderildi!")
        return True
        
    except Exception as e:
        print(f"Email gönderme hatası: {str(e)}")
        return False

if __name__ == "__main__":
    send_test_email("digicollectcontact@gmail.com")
