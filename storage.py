import os
import sqlite3
import shutil
from typing import Optional, BinaryIO
from datetime import datetime
import uuid
from pathlib import Path

class Storage:
    def __init__(self):
        # Ana depolama klasörünü oluştur
        self.storage_path = Path("storage")
        self.storage_path.mkdir(exist_ok=True)
        
        # Veritabanı bağlantısını oluştur
        self.db_path = self.storage_path / "storage.db"
        self.conn = sqlite3.connect(str(self.db_path))
        self.create_tables()
    
    def create_tables(self):
        """Gerekli tabloları oluştur"""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                original_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
    
    def upload_file(self, name: str, file: BinaryIO) -> Optional[str]:
        """Dosya yükle ve dosya adını döndür"""
        try:
            # Dosya yolu oluştur
            file_path = self.storage_path / name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Dosyayı kaydet
            with open(file_path, 'wb') as f:
                f.write(file.read())
            
            # Veritabanına kaydet
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO files (id, user_id, original_name, file_path, file_size) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), name.split('/')[0], name.split('/')[-1], str(file_path), file_path.stat().st_size)
            )
            self.conn.commit()
            
            return name
        except Exception as e:
            print(f"Dosya yükleme hatası: {str(e)}")
            return None
    
    def download_file(self, name: str) -> Optional[bytes]:
        """Dosyayı indir"""
        try:
            file_path = self.storage_path / name
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            print(f"Dosya indirme hatası: {str(e)}")
            return None
    
    def delete_file(self, name: str) -> bool:
        """Dosyayı sil"""
        try:
            file_path = self.storage_path / name
            if file_path.exists():
                file_path.unlink()
                
                # Veritabanından sil
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM files WHERE file_path = ?", (str(file_path),))
                self.conn.commit()
                
                return True
            return False
        except Exception as e:
            print(f"Dosya silme hatası: {str(e)}")
            return False
    
    def get_file_url(self, name: str) -> Optional[str]:
        """Dosyanın yerel yolunu al"""
        try:
            file_path = self.storage_path / name
            return str(file_path.absolute()) if file_path.exists() else None
        except Exception as e:
            print(f"Dosya yolu alma hatası: {str(e)}")
            return None
    
    def list_files(self, prefix: str = "") -> list:
        """Dosyaları listele"""
        try:
            cursor = self.conn.cursor()
            if prefix:
                cursor.execute("SELECT file_path FROM files WHERE user_id = ?", (prefix,))
            else:
                cursor.execute("SELECT file_path FROM files")
            return [Path(row[0]).name for row in cursor.fetchall()]
        except Exception as e:
            print(f"Dosya listeleme hatası: {str(e)}")
            return []
    
    def generate_filename(self, original_name: str, user_id: str) -> str:
        """Benzersiz dosya adı oluştur"""
        ext = os.path.splitext(original_name)[1]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{user_id}/{timestamp}_{unique_id}{ext}"
    
    def get_file_size(self, name: str) -> Optional[int]:
        """Dosya boyutunu al"""
        try:
            file_path = self.storage_path / name
            return file_path.stat().st_size if file_path.exists() else None
        except Exception as e:
            print(f"Dosya boyutu alma hatası: {str(e)}")
            return None
    
    def copy_file(self, source: str, destination: str) -> bool:
        """Dosyayı kopyala"""
        try:
            source_path = self.storage_path / source
            dest_path = self.storage_path / destination
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(source_path, dest_path)
            
            # Yeni dosyayı veritabanına ekle
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO files (id, user_id, original_name, file_path, file_size) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), destination.split('/')[0], destination.split('/')[-1], str(dest_path), dest_path.stat().st_size)
            )
            self.conn.commit()
            
            return True
        except Exception as e:
            print(f"Dosya kopyalama hatası: {str(e)}")
            return False
    
    def __del__(self):
        """Veritabanı bağlantısını kapat"""
        if hasattr(self, 'conn'):
            self.conn.close()
