"""网站信息异步获取"""

import os
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal, QUrl


class WebsiteInfoFetcher(QThread):
    """异步获取网站信息"""
    
    finished = pyqtSignal(str, str, str)
    error = pyqtSignal(str, str)
    
    def __init__(self, url: str, icons_dir: Path):
        super().__init__()
        self.url = url
        self.icons_dir = icons_dir
    
    def run(self):
        """获取网站标题和图标"""
        import requests
        from charset_normalizer import from_bytes
        from bs4 import BeautifulSoup
        
        title = QUrl(self.url).host() or self.url
        icon_path = ""
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(self.url, headers=headers, timeout=10)
            response.raise_for_status()
            
            result = from_bytes(response.content).best()
            if result:
                response.encoding = result.encoding
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            title_tag = soup.find('title')
            if title_tag and title_tag.string:
                title = title_tag.string.strip()
                if self._is_garbled(title):
                    title = QUrl(self.url).host()
            
            icon_path = self._fetch_icon(soup, headers)
            
            if not icon_path:
                icon_path = self._fetch_default_favicon(headers)
            
        except Exception as e:
            self.error.emit(self.url, str(e))
            return
        
        if not icon_path:
            icon_path = self._create_default_icon()
        
        self.finished.emit(self.url, title, icon_path)
    
    def _is_garbled(self, text: str) -> bool:
        """检查文本是否乱码"""
        if not text:
            return True
        non_ascii = sum(1 for c in text if ord(c) > 127)
        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in text)
        return non_ascii > 0 and not has_chinese
    
    def _fetch_icon(self, soup, headers: dict) -> str:
        """获取网站图标"""
        import requests
        
        icon_url = None
        icon_link = soup.find('link', rel=lambda r: r and ('icon' in r.lower() or 'shortcut icon' in r.lower()))
        
        if icon_link and icon_link.get('href'):
            icon_href = icon_link['href']
            domain = QUrl(self.url).host()
            
            if icon_href.startswith('//'):
                icon_url = 'https:' + icon_href
            elif icon_href.startswith('/'):
                icon_url = f"https://{domain}{icon_href}"
            elif icon_href.startswith('http'):
                icon_url = icon_href.replace('http://', 'https://', 1)
            else:
                icon_url = f"https://{domain}/{icon_href.lstrip('/')}"
        
        if not icon_url:
            return ""
        
        return self._download_icon(icon_url, headers)
    
    def _fetch_default_favicon(self, headers: dict) -> str:
        """尝试获取默认的 /favicon.ico"""
        import requests
        
        domain = QUrl(self.url).host()
        if not domain:
            return ""
        
        icon_url = f"https://{domain}/favicon.ico"
        return self._download_icon(icon_url, headers)
    
    def _download_icon(self, icon_url: str, headers: dict) -> str:
        """下载图标并保存"""
        import requests
        
        try:
            response = requests.get(icon_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            icon_data = response.content
            if len(icon_data) < 100:
                return ""
            
            content_type = response.headers.get('Content-Type', '')
            
            ext_map = [
                ('image/png', 'png'),
                ('image/svg+xml', 'svg'),
                ('image/jpeg', 'jpg'),
                ('image/x-icon', 'ico'),
                ('image/vnd.microsoft.icon', 'ico'),
            ]
            
            ext = 'ico'
            for ct, e in ext_map:
                if ct in content_type:
                    ext = e
                    break
            
            if icon_url.endswith('.png'):
                ext = 'png'
            elif icon_url.endswith('.svg'):
                ext = 'svg'
            elif icon_url.endswith('.jpg') or icon_url.endswith('.jpeg'):
                ext = 'jpg'
            
            self.icons_dir.mkdir(parents=True, exist_ok=True)
            
            domain = QUrl(self.url).host()
            icon_filename = f"{domain}.{ext}"
            icon_path = self.icons_dir / icon_filename
            
            with open(icon_path, 'wb') as f:
                f.write(icon_data)
            
            return f"data/icons/{icon_filename}"
            
        except Exception:
            return ""
    
    def _create_default_icon(self) -> str:
        """创建默认图标"""
        self.icons_dir.mkdir(parents=True, exist_ok=True)
        default_icon_path = self.icons_dir / "default.ico"
        
        if not default_icon_path.exists():
            with open(default_icon_path, 'wb') as f:
                f.write(b'')
        
        return "data/icons/default.ico"
