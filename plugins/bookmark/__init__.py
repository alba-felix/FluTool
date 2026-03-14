import os
import sys
import webbrowser
from pathlib import Path
from typing import Optional, Tuple
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidgetItem,
    QMenu, QAction, QFileDialog, QHeaderView,
    QApplication
)
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal
from PyQt5.QtGui import QIcon
from qfluentwidgets import (
    StrongBodyLabel, PushButton, LineEdit,
    FluentIcon as FIF, InfoBar, InfoBarPosition, TreeWidget,
    setCustomStyleSheet, isDarkTheme, qconfig, IndeterminateProgressBar,
    MessageBoxBase, SubtitleLabel, MessageBox
)
from core import PluginInterface
from storage import DatabaseManager
from functools import partial


def get_app_data_path(relative_path: str) -> Path:
    """获取应用数据路径（可读写）"""
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).parent.parent.parent
    return base_path / relative_path


class InputDialog(MessageBoxBase):
    """Fluent 风格输入对话框"""
    
    def __init__(self, title: str, label: str, default_text: str = "", parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel(title, self)
        self.viewLayout.addWidget(self.titleLabel)
        
        self.input_edit = LineEdit(self)
        self.input_edit.setText(default_text)
        self.input_edit.setPlaceholderText(label)
        self.input_edit.setClearButtonEnabled(True)
        self.viewLayout.addWidget(self.input_edit)
        
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(350)
        
        self.input_edit.setFocus()
    
    def get_text(self) -> str:
        return self.input_edit.text().strip()
    
    def validate(self) -> bool:
        return True


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
            print(f"[DEBUG] 正在获取: {self.url}")
            response = requests.get(self.url, headers=headers, timeout=10)
            response.raise_for_status()
            print(f"[DEBUG] HTTP状态码: {response.status_code}")
            
            result = from_bytes(response.content).best()
            if result:
                response.encoding = result.encoding
                print(f"[DEBUG] 检测到编码: {result.encoding}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            title_tag = soup.find('title')
            if title_tag and title_tag.string:
                title = title_tag.string.strip()
                print(f"[DEBUG] 获取到标题: {title}")
                if self._is_garbled(title):
                    title = QUrl(self.url).host()
                    print(f"[DEBUG] 标题乱码，使用域名: {title}")
            
            icon_path = self._fetch_icon(soup, headers)
            print(f"[DEBUG] 从页面获取图标: {icon_path}")
            
            if not icon_path:
                icon_path = self._fetch_default_favicon(headers)
                print(f"[DEBUG] 从favicon.ico获取图标: {icon_path}")
            
        except Exception as e:
            print(f"[DEBUG] 获取网站信息异常: {e}")
            self.error.emit(self.url, str(e))
            return
        
        if not icon_path:
            icon_path = self._create_default_icon()
            print(f"[DEBUG] 使用默认图标: {icon_path}")
        
        print(f"[DEBUG] 最终结果 - 标题: {title}, 图标: {icon_path}")
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
            print(f"[DEBUG] 下载图标: {icon_url}")
            response = requests.get(icon_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            icon_data = response.content
            print(f"[DEBUG] 图标大小: {len(icon_data)} bytes")
            if len(icon_data) < 100:
                print(f"[DEBUG] 图标太小，跳过")
                return ""
            
            content_type = response.headers.get('Content-Type', '')
            print(f"[DEBUG] Content-Type: {content_type}")
            
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
            
            print(f"[DEBUG] 图标已保存: {icon_path}")
            return f"data/icons/{icon_filename}"
            
        except Exception as e:
            print(f"[DEBUG] 下载图标失败: {e}")
            return ""
    
    def _create_default_icon(self) -> str:
        """创建默认图标"""
        self.icons_dir.mkdir(parents=True, exist_ok=True)
        default_icon_path = self.icons_dir / "default.ico"
        
        if not default_icon_path.exists():
            with open(default_icon_path, 'wb') as f:
                f.write(b'')
        
        return "data/icons/default.ico"


class BookmarkWidget(QWidget):
    """书签管理界面"""
    
    PLUGIN_ID = "bookmark"
    
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.db = DatabaseManager()
        self._current_category_id = None
        self._current_category_name = "全部"
        self._category_buttons = []
        self._fetcher: Optional[WebsiteInfoFetcher] = None
        self._batch_mode = False
        self._init_paths()
        self._setup_ui()
    
    def _init_paths(self) -> None:
        """初始化路径"""
        self.icons_dir = get_app_data_path("data/icons")
        self.icons_dir.mkdir(parents=True, exist_ok=True)
    
    def _setup_ui(self) -> None:
        """构建界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        self.setObjectName("bookmarkView")
        setCustomStyleSheet(
            self,
            "QWidget#bookmarkView { background-color: transparent; }",
            "QWidget#bookmarkView { background-color: transparent; }"
        )
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        self.url_edit = LineEdit(self)
        self.url_edit.setPlaceholderText("输入网址，按回车添加...")
        self.url_edit.setClearButtonEnabled(True)
        self.url_edit.returnPressed.connect(self._on_url_return_pressed)
        header_layout.addWidget(self.url_edit, 1)
        
        self.search_edit = LineEdit(self)
        self.search_edit.setPlaceholderText("搜索...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._filter_websites)
        self.search_edit.setFixedWidth(150)
        header_layout.addWidget(self.search_edit)
        
        self.batch_btn = PushButton("批量删除", self)
        self.batch_btn.setIcon(FIF.DELETE)
        self.batch_btn.clicked.connect(self._toggle_batch_mode)
        header_layout.addWidget(self.batch_btn)
        
        self.confirm_delete_btn = PushButton("确认", self)
        self.confirm_delete_btn.setIcon(FIF.ACCEPT)
        self.confirm_delete_btn.clicked.connect(self._execute_batch_delete)
        self.confirm_delete_btn.setVisible(False)
        header_layout.addWidget(self.confirm_delete_btn)
        
        self.cancel_btn = PushButton("取消", self)
        self.cancel_btn.setIcon(FIF.CANCEL)
        self.cancel_btn.clicked.connect(self._exit_batch_mode)
        self.cancel_btn.setVisible(False)
        header_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(header_layout)
        
        self.progress_bar = IndeterminateProgressBar(self)
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.category_layout = QHBoxLayout()
        self.category_layout.setSpacing(5)
        
        self.all_btn = PushButton("全部", self)
        self.all_btn.clicked.connect(self._show_all)
        self.category_layout.addWidget(self.all_btn)
        
        self.add_category_btn = PushButton("+", self)
        self.add_category_btn.clicked.connect(self._add_category)
        self.category_layout.addWidget(self.add_category_btn)
        self.category_layout.addStretch()
        layout.addLayout(self.category_layout)
        
        self.tree = TreeWidget(self)
        self.tree.setHeaderLabels(["网站名称", "网址", "分类", "备注"])
        self.tree.header().setSectionResizeMode(QHeaderView.Interactive)
        self.tree.setColumnWidth(0, 200)
        self.tree.setColumnWidth(1, 300)
        self.tree.setColumnWidth(2, 100)
        self.tree.setColumnWidth(3, 150)
        self._apply_header_style()
        qconfig.themeChangedFinished.connect(self._apply_header_style)
        self.tree.itemDoubleClicked.connect(self._open_website)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.tree)
    
    def load_data(self) -> None:
        """加载书签数据"""
        self.tree.clear()
        self._load_categories()
        self._load_bookmarks()
    
    def _load_categories(self) -> None:
        """加载分类按钮"""
        for btn in self._category_buttons:
            btn.deleteLater()
        self._category_buttons.clear()
        
        categories = self.db.get_categories(self.PLUGIN_ID)
        for cat in categories:
            btn = PushButton(cat['name'], self)
            btn.clicked.connect(partial(self._show_category, cat))
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(partial(self._show_category_menu, cat))
            self.category_layout.insertWidget(self.category_layout.count() - 2, btn)
            self._category_buttons.append(btn)
    
    def _show_category_menu(self, category: dict, pos) -> None:
        """显示分类右键菜单"""
        from PyQt5.QtGui import QCursor
        
        menu = QMenu(self)
        menu.setAttribute(Qt.WA_DeleteOnClose)
        
        edit_action = QAction("编辑分类", self)
        edit_action.triggered.connect(partial(self._edit_category, category))
        menu.addAction(edit_action)
        
        delete_action = QAction("删除分类", self)
        delete_action.triggered.connect(partial(self._delete_category, category))
        menu.addAction(delete_action)
        
        menu.exec_(QCursor.pos())
    
    def _edit_category(self, category: dict) -> None:
        """编辑分类"""
        dialog = InputDialog("编辑分类", "请输入新的分类名称", category['name'], self)
        if dialog.exec():
            new_name = dialog.get_text()
            if new_name and new_name != category['name']:
                existing_names = [btn.text() for btn in self._category_buttons]
                if new_name not in existing_names:
                    self.db.update_category(self.PLUGIN_ID, category['id'], new_name)
                    self._load_categories()
                    InfoBar.success(
                        title="修改成功",
                        content=f"分类已重命名为 {new_name}",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
                else:
                    InfoBar.warning(
                        title="警告",
                        content="该分类名称已存在！",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
    
    def _delete_category(self, category: dict) -> None:
        """删除分类"""
        box = MessageBox("删除分类", f"确定要删除分类 '{category['name']}' 吗？\n该分类下的书签将移至\"全部\"分类。", self)
        if box.exec():
            self.db.delete_category(self.PLUGIN_ID, category['id'])
            self._load_categories()
            if self._current_category_id == category['id']:
                self._show_all()
            InfoBar.success(
                title="删除成功",
                content=f"已删除分类 {category['name']}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _load_bookmarks(self) -> None:
        """加载书签列表"""
        self.tree.clear()
        bookmarks = self.db.get_bookmarks(self.PLUGIN_ID, self._current_category_id)
        
        for bm in bookmarks:
            item = QTreeWidgetItem(self.tree)
            item.setText(0, bm['name'])
            item.setText(1, bm['url'])
            item.setText(2, bm.get('category_name', ''))
            item.setText(3, bm.get('notes', ''))
            item.setData(0, Qt.UserRole, bm['id'])
            
            icon_path = bm.get('icon', '')
            if icon_path:
                abs_icon_path = self._get_icon_path(icon_path)
                if abs_icon_path and os.path.exists(abs_icon_path):
                    item.setIcon(0, QIcon(abs_icon_path))

    def _apply_header_style(self) -> None:
        """应用树形列表样式，包括表头和交替行颜色"""
        if not hasattr(self, "tree"):
            return
        
        header = self.tree.header()
        if isDarkTheme():
            header.setStyleSheet(
                "QHeaderView { background-color: transparent; }"
                "QHeaderView::section { background-color: #1f1f1f; color: #dddddd; border: none; padding: 6px 8px; }"
            )
            self.tree.setStyleSheet(
                "QTreeWidget { background-color: transparent; alternate-background-color: #252525; }"
                "QTreeWidget::item { padding: 4px; }"
                "QTreeWidget::item:selected { background-color: #0078d4; color: white; }"
            )
        else:
            header.setStyleSheet(
                "QHeaderView { background-color: transparent; }"
                "QHeaderView::section { background-color: #f5f5f5; color: #202020; border: none; padding: 6px 8px; }"
            )
            self.tree.setStyleSheet(
                "QTreeWidget { background-color: transparent; alternate-background-color: #f0f0f0; }"
                "QTreeWidget::item { padding: 4px; }"
                "QTreeWidget::item:selected { background-color: #0078d4; color: white; }"
            )
        
        self.tree.setAlternatingRowColors(True)
    
    def _get_icon_path(self, icon_path: str) -> Optional[str]:
        """获取图标绝对路径"""
        if not icon_path:
            return None
        full_path = get_app_data_path(icon_path)
        if full_path.exists():
            return str(full_path)
        return None
    
    def _on_url_return_pressed(self) -> None:
        """URL输入框回车事件处理"""
        url = self.url_edit.text().strip()
        if not url:
            return
        
        url = self._normalize_url(url)
        if not url:
            InfoBar.warning(
                title="输入错误",
                content="请用完整网站路径",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        self.url_edit.clear()
        self._start_fetch_website(url)
    
    def _add_website(self) -> None:
        """添加网站"""
        dialog = InputDialog("添加网站", "请输入网站URL", parent=self)
        if dialog.exec():
            url = dialog.get_text()
            if not url:
                return
            
            url = self._normalize_url(url)
            if not url:
                InfoBar.warning(
                    title="输入错误",
                    content="请用完整网站路径",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return
            
            self._start_fetch_website(url)
    
    def _normalize_url(self, url: str) -> str:
        """规范化URL，确保有协议和www前缀，无效URL返回空字符串"""
        url = url.strip()
        if not url:
            return ""
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        qurl = QUrl(url)
        host = qurl.host()
        print(f"[DEBUG] normalize_url - 原始host: {host}")
        
        if not host:
            return ""
        
        if not host.startswith('www.') and '.' not in host:
            new_host = f'www.{host}.com'
            url = url.replace(f'://{host}', f'://{new_host}')
            print(f"[DEBUG] normalize_url - 补全为: {new_host}")
        elif not host.startswith('www.') and host.count('.') == 1:
            new_host = f'www.{host}'
            url = url.replace(f'://{host}', f'://{new_host}')
            print(f"[DEBUG] normalize_url - 添加www: {new_host}")
        
        new_host = QUrl(url).host()
        if not new_host or '.' not in new_host:
            return ""
        
        print(f"[DEBUG] normalize_url - 最终URL: {url}")
        return url
    
    def _start_fetch_website(self, url: str) -> None:
        """开始获取网站信息"""
        self._set_ui_enabled(False)
        self.progress_bar.setVisible(True)
        
        self._fetcher = WebsiteInfoFetcher(url, self.icons_dir)
        self._fetcher.finished.connect(self._on_fetch_finished)
        self._fetcher.error.connect(self._on_fetch_error)
        self._fetcher.start()
    
    def _on_fetch_error(self, url: str, error_msg: str) -> None:
        """获取网站信息失败"""
        self.progress_bar.setVisible(False)
        self._set_ui_enabled(True)
        
        print(f"[ERROR] 获取网站信息失败 - {url}: {error_msg}")
        
        if self._fetcher:
            self._fetcher.deleteLater()
            self._fetcher = None
    
    def _on_fetch_finished(self, url: str, title: str, icon_path: str) -> None:
        """网站信息获取完成"""
        self.progress_bar.setVisible(False)
        self._set_ui_enabled(True)
        
        dialog = InputDialog("备注", "请输入备注（可选）", parent=self)
        notes = ""
        if dialog.exec():
            notes = dialog.get_text()
        
        category_name = self._current_category_name if self._current_category_name != "全部" else None
        
        self.db.add_bookmark(
            plugin_id=self.PLUGIN_ID,
            name=title,
            url=url,
            category_name=category_name,
            icon=icon_path,
            notes=notes
        )
        
        self._load_bookmarks()
        
        InfoBar.success(
            title="添加成功",
            content=f"已添加 {title}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
        
        if self._fetcher:
            self._fetcher.deleteLater()
            self._fetcher = None
    
    def _set_ui_enabled(self, enabled: bool) -> None:
        """设置UI启用状态"""
        self.url_edit.setEnabled(enabled)
        self.search_edit.setEnabled(enabled)
        self.tree.setEnabled(enabled)
        self.all_btn.setEnabled(enabled)
        self.add_category_btn.setEnabled(enabled)
        for btn in self._category_buttons:
            btn.setEnabled(enabled)
    
    def _add_category(self) -> None:
        """添加分类"""
        dialog = InputDialog("添加分类", "请输入分类名称", parent=self)
        if dialog.exec():
            name = dialog.get_text()
            if not name:
                return
            
            self.db.add_category(self.PLUGIN_ID, name)
            self._load_categories()
            
            InfoBar.success(
                title="添加成功",
                content=f"已添加分类 {name}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _show_all(self) -> None:
        """显示全部书签"""
        self._current_category_id = None
        self._current_category_name = "全部"
        self._load_bookmarks()
    
    def _show_category(self, category: dict) -> None:
        """显示指定分类的书签"""
        self._current_category_id = category['id']
        self._current_category_name = category['name']
        self._load_bookmarks()
    
    def _filter_websites(self) -> None:
        """过滤网站"""
        keyword = self.search_edit.text().lower()
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            visible = (
                keyword in item.text(0).lower() or
                keyword in item.text(1).lower() or
                keyword in item.text(3).lower()
            )
            item.setHidden(not visible)
    
    def _open_website(self, item: QTreeWidgetItem) -> None:
        """打开网站"""
        url = item.text(1)
        if url:
            webbrowser.open(url)
    
    def _show_context_menu(self, pos) -> None:
        """显示右键菜单"""
        item = self.tree.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        menu.setAttribute(Qt.WA_DeleteOnClose)
        
        open_action = QAction("打开网站", self)
        open_action.triggered.connect(partial(self._open_website, item))
        menu.addAction(open_action)
        
        menu.addSeparator()
        
        edit_action = QAction("编辑", self)
        edit_action.triggered.connect(partial(self._edit_bookmark, item))
        menu.addAction(edit_action)
        
        edit_notes_action = QAction("编辑备注", self)
        edit_notes_action.triggered.connect(partial(self._edit_notes, item))
        menu.addAction(edit_notes_action)
        
        set_icon_action = QAction("设置图标", self)
        set_icon_action.triggered.connect(partial(self._set_icon, item))
        menu.addAction(set_icon_action)
        
        menu.addSeparator()
        
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(partial(self._delete_bookmark, item))
        menu.addAction(delete_action)
        
        menu.exec_(self.tree.viewport().mapToGlobal(pos))
    
    def _edit_bookmark(self, item: QTreeWidgetItem) -> None:
        """编辑书签"""
        bm_id = item.data(0, Qt.UserRole)
        
        dialog = InputDialog("编辑名称", "名称:", default_text=item.text(0), parent=self)
        if not dialog.exec():
            return
        name = dialog.get_text()
        
        dialog = InputDialog("编辑网址", "网址:", default_text=item.text(1), parent=self)
        if not dialog.exec():
            return
        url = dialog.get_text()
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        self.db.update_bookmark(self.PLUGIN_ID, bm_id, name=name, url=url)
        self._load_bookmarks()
    
    def _edit_notes(self, item: QTreeWidgetItem) -> None:
        """编辑备注"""
        bm_id = item.data(0, Qt.UserRole)
        dialog = InputDialog("编辑备注", "备注:", default_text=item.text(3), parent=self)
        if not dialog.exec():
            return
        notes = dialog.get_text()
        
        self.db.update_bookmark(self.PLUGIN_ID, bm_id, notes=notes)
        item.setText(3, notes)
    
    def _set_icon(self, item: QTreeWidgetItem) -> None:
        """设置图标"""
        bm_id = item.data(0, Qt.UserRole)
        url = item.text(1)
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图标文件", "",
            "图片文件 (*.png *.ico *.jpg *.svg);;所有文件 (*)"
        )
        
        if not file_path:
            return
        
        import shutil
        domain = QUrl(url).host() or str(bm_id)
        ext = os.path.splitext(file_path)[1]
        icon_filename = f"{domain}{ext}"
        icon_path = self.icons_dir / icon_filename
        
        shutil.copy2(file_path, icon_path)
        
        relative_path = f"data/icons/{icon_filename}"
        self.db.update_bookmark(self.PLUGIN_ID, bm_id, icon=relative_path)
        
        item.setIcon(0, QIcon(str(icon_path)))
        
        InfoBar.success(
            title="设置成功",
            content="图标已更新",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
    
    def _delete_bookmark(self, item: QTreeWidgetItem) -> None:
        """删除书签"""
        bm_id = item.data(0, Qt.UserRole)
        name = item.text(0)
        
        if MessageBox("确认删除", f"确定要删除 '{name}' 吗？", self).exec():
            self.db.delete_bookmark(self.PLUGIN_ID, bm_id)
            self._load_bookmarks()
    
    def _toggle_batch_mode(self) -> None:
        """切换批量删除模式"""
        self._batch_mode = True
        self._update_batch_ui()
        
        self.tree.setSelectionMode(TreeWidget.MultiSelection)
        
        InfoBar.info(
            title="批量删除模式",
            content="请选择要删除的书签，然后点击确认删除",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
    
    def _exit_batch_mode(self) -> None:
        """退出批量删除模式"""
        self._batch_mode = False
        self._update_batch_ui()
        
        self.tree.setSelectionMode(TreeWidget.SingleSelection)
        for i in range(self.tree.topLevelItemCount()):
            self.tree.topLevelItem(i).setSelected(False)
    
    def _update_batch_ui(self) -> None:
        """更新批量删除模式UI"""
        self.batch_btn.setVisible(not self._batch_mode)
        self.confirm_delete_btn.setVisible(self._batch_mode)
        self.cancel_btn.setVisible(self._batch_mode)
    
    def _execute_batch_delete(self) -> None:
        """执行批量删除"""
        selected_items = self.tree.selectedItems()
        if not selected_items:
            InfoBar.warning(
                title="未选择",
                content="请先选择要删除的书签",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        if MessageBox(
            "确认批量删除", 
            f"确定要删除选中的 {len(selected_items)} 个书签吗？", 
            self
        ).exec():
            for item in selected_items:
                bm_id = item.data(0, Qt.UserRole)
                self.db.delete_bookmark(self.PLUGIN_ID, bm_id)
            
            self._exit_batch_mode()
            self._load_bookmarks()
            
            InfoBar.success(
                title="删除成功",
                content=f"已删除 {len(selected_items)} 个书签",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )


class Plugin(PluginInterface):
    """书签插件"""
    PLUGIN_ID = "bookmark"
    PLUGIN_NAME = "网站书签"
    PLUGIN_ICON = FIF.TAG
    PLUGIN_PRIORITY = 1

    def initialize(self, core) -> None:
        self.core = core
        core.logger.info(f"Plugin '{self.get_name()}' initialized")

    def shutdown(self) -> None:
        self.core.logger.info(f"Plugin '{self.get_name()}' shutdown")

    def _create_widget(self, parent=None) -> QWidget:
        return BookmarkWidget(self.core, parent)

    def _do_load_data(self) -> None:
        """加载数据：直接从数据库读取"""
        if self._widget is None:
            return
        self._widget.load_data()
