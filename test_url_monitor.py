from url_monitor import URLMonitor
import logging

# Loglama ayarları
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('digicollect_debug.log')
    ]
)

def on_url_detected(url):
    """URL algılandığında çağrılacak fonksiyon"""
    print(f"\nYeni URL algılandı: {url}")
    print("URL'yi kesmek için 'K', çıkmak için 'Q' tuşuna basın...")

def main():
    print("DigiCollect - URL İzleyici Test")
    print("--------------------------------")
    print("Herhangi bir uygulamadan URL kopyalayın...")
    print("Çıkmak için 'Q' tuşuna basın...")
    
    # URL izleyiciyi başlat
    monitor = URLMonitor(callback=on_url_detected)
    monitor.start()
    
    # Kullanıcı girişini bekle
    while True:
        cmd = input().strip().upper()
        if cmd == 'Q':
            break
    
    # İzleyiciyi durdur
    monitor.stop()
    print("\nProgram kapatılıyor...")

if __name__ == '__main__':
    main()
