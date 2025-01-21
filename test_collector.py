from content_collector import ContentCollector
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

logger = logging.getLogger('DigiCollect')

def main():
    print("DigiCollect - İçerik Toplayıcı Test")
    print("-----------------------------------")
    
    collector = ContentCollector()
    
    while True:
        print("\nSeçenekler:")
        print("1. İçerik Getir")
        print("2. Çıkış")
        
        choice = input("\nSeçiminiz (1-2): ")
        
        if choice == "1":
            url = input("\nURL girin: ")
            if not url.strip():
                print("URL boş olamaz!")
                continue
            
            try:
                logger.info(f'İçerik getiriliyor: {url}')
                content = collector.collect_content(url)
                
                if content:
                    print("\nİçerik Bilgileri:")
                    print(f"Başlık: {content.get('title', 'Başlık yok')}")
                    print(f"Tür: {content.get('type', 'Bilinmiyor')}")
                    print(f"Açıklama: {content.get('description', 'Açıklama yok')}")
                    logger.info('İçerik başarıyla yüklendi')
                else:
                    print("\nİçerik getirilemedi!")
                    logger.error('İçerik getirilemedi')
                    
            except Exception as e:
                print(f"\nHata: {str(e)}")
                logger.exception(f"İçerik getirme hatası: {e}")
                
        elif choice == "2":
            print("\nProgram kapatılıyor...")
            break
        else:
            print("\nGeçersiz seçim!")

if __name__ == '__main__':
    main()
