import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QLineEdit, QPushButton, QLabel, QTextEdit, QSystemTrayIcon,
                           QMenu, QAction)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from content_collector import ContentCollector
from content_cutter import ContentCutter
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

logger = logging.getLogger('DigiCollect')

class DigiCollectApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.collector = ContentCollector()
        self.cutter = ContentCutter()
        self.url_monitor = URLMonitor(callback=self.on_url_detected)
        self.initUI()
        self.setupTrayIcon()
        
        # URL izleyiciyi başlat
        self.url_monitor.start()
    
    def initUI(self):
        # Ana pencere ayarları
        self.setWindowTitle('DigiCollect - Dijital Koleksiyoncu')
        self.setGeometry(100, 100, 800, 600)
        
        # Ana widget ve layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Başlık
        title = QLabel('DigiCollect - Dijital Koleksiyoncu')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size: 20px; margin: 10px;')
        layout.addWidget(title)
        
        # URL girişi
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('URL girin veya herhangi bir yerden URL kopyalayın...')
        layout.addWidget(self.url_input)
        
        # İçerik getir butonu
        fetch_button = QPushButton('İçeriği Getir')
        fetch_button.clicked.connect(self.fetch_content)
        fetch_button.setStyleSheet('''
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        ''')
        layout.addWidget(fetch_button)
        
        # İçerik önizleme alanı
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText('İçerik burada görüntülenecek...')
        layout.addWidget(self.preview)
    
    def setupTrayIcon(self):
        # Sistem tray ikonunu oluştur
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip('DigiCollect - URL İzleyici Aktif')
        
        # Tray menüsü
        tray_menu = QMenu()
        show_action = QAction('Göster', self)
        quit_action = QAction('Çıkış', self)
        
        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(self.quit_app)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
    
    def on_url_detected(self, url):
        """URL algılandığında çağrılacak fonksiyon"""
        logger.info(f'Yeni URL algılandı: {url}')
        self.url_input.setText(url)
        self.show()  # Pencereyi göster
        self.fetch_content()  # İçeriği otomatik getir
    
    def fetch_content(self):
        url = self.url_input.text().strip()
        if not url:
            logger.warning('URL boş olamaz')
            self.preview.setText('Lütfen bir URL girin!')
            return
        
        try:
            logger.info(f'İçerik getiriliyor: {url}')
            content = self.collector.collect_content(url)
            
            if content:
                preview_text = f"""
İçerik Bilgileri:
----------------
Başlık: {content.get('title', 'Başlık yok')}
Tür: {content.get('type', 'Bilinmiyor')}
Açıklama: {content.get('description', 'Açıklama yok')}

İçeriği kesmek için sağ üst köşedeki kesme aracını kullanın.
                """
                self.preview.setText(preview_text)
                logger.info('İçerik başarıyla yüklendi')
            else:
                self.preview.setText('İçerik getirilemedi!')
                logger.error('İçerik getirilemedi')
                
        except Exception as e:
            self.preview.setText(f'Hata: {str(e)}')
            logger.exception(f"İçerik getirme hatası: {e}")
    
    def closeEvent(self, event):
        """Pencere kapatıldığında sistem tray'e küçült"""
        event.ignore()
        self.hide()
    
    def quit_app(self):
        """Uygulamayı tamamen kapat"""
        self.url_monitor.stop()
        QApplication.quit()

def main():
    app = QApplication(sys.argv)
    window = DigiCollectApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
