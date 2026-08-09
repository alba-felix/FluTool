"""
剪切板插件 - 图片图库模块

由原「图片助手」插件合并而来，提供图片图库浏览：粘贴、添加、
复制、另存、删除、缩放预览与网格搜索。

数据沿用旧版图片助手格式，旧数据无缝兼容：
- 图片文件保存在 data/img/
- 索引保存在 data/img/image_list.json
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QCursor, QImage, QPixmap
from PyQt5.QtWidgets import (
    QAbstractItemView, QAction, QApplication, QFileDialog, QFrame,
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QScrollArea,
    QSplitter, QVBoxLayout, QWidget,
)

from qfluentwidgets import (
    CaptionLabel, FluentIcon as FIF, InfoBar, InfoBarPosition, LineEdit,
    MessageDialog, PushButton, RoundMenu, TransparentToolButton, qconfig,
)
from qfluentwidgets import isDarkTheme as is_dark_theme

from core import get_app_data_path

THUMBNAIL_SIZE = 96
# 每批异步加载的缩略图数量，避免一次全部加载阻塞 UI
THUMBNAIL_BATCH = 6


def _show_info(parent: QWidget, title: str, content: str, success: bool = True):
    """统一 InfoBar 提示"""
    cls = InfoBar.success if success else InfoBar.error
    cls(
        title=title,
        content=content,
        orient=Qt.Horizontal,
        isClosable=True,
        position=InfoBarPosition.TOP,
        duration=1800,
        parent=parent,
    )


class ImageLibrary:
    """图片图库数据服务（兼容旧版 image_list.json）"""

    def __init__(self, core=None) -> None:
        self.core = core
        self.data_dir = Path(get_app_data_path("data/img"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.images: List[Dict] = []
        self._load()

    def _load(self) -> None:
        """加载图片索引，过滤掉丢失文件"""
        list_file = self.data_dir / "image_list.json"
        try:
            if list_file.exists():
                with open(list_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self.images = [
                        img for img in data
                        if isinstance(img, dict) and img.get("filename")
                        and os.path.exists(img.get("path", ""))
                    ]
                    if len(self.images) != len(data):
                        self._save()
        except Exception as e:
            if self.core:
                self.core.logger.error(f"加载图片列表失败: {e}")
            self.images = []

    def _save(self) -> None:
        """持久化图片索引"""
        try:
            list_file = self.data_dir / "image_list.json"
            with open(list_file, "w", encoding="utf-8") as f:
                json.dump(self.images, f, ensure_ascii=False, indent=2)
        except Exception as e:
            if self.core:
                self.core.logger.error(f"保存图片列表失败: {e}")

    def count(self) -> int:
        """图片数量"""
        return len(self.images)

    def list(self) -> List[Dict]:
        """全部图片条目"""
        return self.images

    def get(self, index: int) -> Optional[Dict]:
        """按索引取图片条目"""
        if 0 <= index < len(self.images):
            return self.images[index]
        return None

    def add_image(self, pixmap: QPixmap, source: str = "") -> Optional[Dict]:
        """保存图片到图库，返回索引条目"""
        if pixmap.isNull():
            return None
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"img_{timestamp}.png"
        save_path = self.data_dir / filename
        if not pixmap.save(str(save_path), "PNG"):
            return None
        entry = {
            "path": str(save_path),
            "filename": filename,
            "source": source,
            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.images.insert(0, entry)
        self._save()
        return entry

    def delete(self, index: int) -> bool:
        """删除图片（先删文件再删索引）"""
        if not (0 <= index < len(self.images)):
            return False
        entry = self.images[index]
        path = entry.get("path", "")
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            if self.core:
                self.core.logger.error(f"删除图片文件失败: {e}")
            return False
        self.images.pop(index)
        self._save()
        return True

    def index_of(self, path: str) -> int:
        """按路径定位索引"""
        for i, e in enumerate(self.images):
            if e.get("path") == path:
                return i
        return -1


class GalleryPreviewWidget(QWidget):
    """图库预览组件（支持缩放与自适应窗口）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._original_pixmap = None
        self._scale_factor = 1.0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("galleryScrollContent")
        self.scroll_content.setStyleSheet("background: transparent;")
        content_layout = QHBoxLayout(self.scroll_content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setAlignment(Qt.AlignCenter)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self.preview_label)

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)

        self._apply_style()

    def _apply_style(self):
        """预览区样式（随主题刷新）"""
        dark = is_dark_theme()
        border = "#3d3d3d" if dark else "#d0d0d0"
        bg = "#252525" if dark else "#ffffff"
        scroll_handle = "#4d4d4d" if dark else "#c0c0c0"
        self.preview_label.setStyleSheet(
            f"QLabel {{ background-color: {bg}; border: 2px dashed {border};"
            f" border-radius: 8px; }}"
        )
        self.scroll_area.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            f"QScrollBar:vertical {{ background: transparent; width: 10px;"
            f" border-radius: 5px; margin: 2px; }}"
            f"QScrollBar::handle:vertical {{ background: {scroll_handle};"
            f" min-height: 30px; border-radius: 5px; }}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}"
            f"QScrollBar:horizontal {{ background: transparent; height: 10px;"
            f" border-radius: 5px; margin: 2px; }}"
            f"QScrollBar::handle:horizontal {{ background: {scroll_handle};"
            f" min-width: 30px; border-radius: 5px; }}"
            f"QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}"
        )

    def set_image(self, pixmap: QPixmap):
        """设置待预览图片并自适应窗口"""
        self._original_pixmap = pixmap
        self._scale_factor = 1.0
        self.fit_to_window()

    def clear(self):
        """清空预览"""
        self._original_pixmap = None
        self.preview_label.clear()
        self.preview_label.setFixedSize(0, 0)
        self.scroll_content.setFixedSize(0, 0)

    def has_image(self) -> bool:
        return self._original_pixmap is not None and not self._original_pixmap.isNull()

    def _update_preview(self):
        if not self.has_image():
            return
        scaled = self._original_pixmap.scaled(
            self._original_pixmap.size() * self._scale_factor,
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        self.preview_label.setPixmap(scaled)
        self.preview_label.setFixedSize(scaled.size())
        margins = self.scroll_content.layout().contentsMargins()
        self.scroll_content.setFixedSize(
            scaled.width() + margins.left() + margins.right(),
            scaled.height() + margins.top() + margins.bottom(),
        )

    def zoom_in(self):
        """放大"""
        self._scale_factor = min(self._scale_factor * 1.2, 5.0)
        self._update_preview()

    def zoom_out(self):
        """缩小"""
        self._scale_factor = max(self._scale_factor / 1.2, 0.1)
        self._update_preview()

    def fit_to_window(self):
        """自适应窗口"""
        if not self.has_image():
            return
        img = self._original_pixmap.size()
        if img.width() <= 0 or img.height() <= 0:
            return
        viewport = self.scroll_area.viewport().size()
        margins = self.scroll_content.layout().contentsMargins()
        avail_w = viewport.width() - margins.left() - margins.right()
        avail_h = viewport.height() - margins.top() - margins.bottom()
        if avail_w <= 0 or avail_h <= 0:
            return
        self._scale_factor = min(avail_w / img.width(), avail_h / img.height(), 1.0)
        self._update_preview()

    def reset_scale(self):
        """原始大小"""
        self._scale_factor = 1.0
        self._update_preview()

    def image_info(self, source: str = "", added_at: str = "") -> str:
        """生成预览信息文本"""
        if not self.has_image():
            return ""
        size = self._original_pixmap.size()
        info = f"尺寸: {size.width()} x {size.height()}"
        if source:
            info += f" | 来源: {source}"
        if added_at:
            info += f" | 时间: {added_at}"
        return info


class GalleryTileWidget(QWidget):
    """图库缩略图磁贴（横向：左侧缩略图 + 右侧文件名）

    缩略图采用异步加载：构造时仅显示占位，由外部调用
    set_thumbnail_pixmap() 填充，避免大量图片时阻塞界面。
    """

    def __init__(self, entry: Dict, parent=None):
        super().__init__(parent)
        self.entry = entry
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedHeight(THUMBNAIL_SIZE + 16)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        self.thumb_label = QLabel(self)
        self.thumb_label.setFixedSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setObjectName("galleryThumb")
        self._show_placeholder()
        layout.addWidget(self.thumb_label, 0, Qt.AlignVCenter)

        name = self.entry.get("filename", "")
        self.name_label = CaptionLabel(name, self)
        self.name_label.setObjectName("galleryTileName")
        self.name_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.name_label.setWordWrap(True)
        layout.addWidget(self.name_label, 1)

    def _show_placeholder(self):
        """显示加载占位"""
        self.thumb_label.clear()
        self.thumb_label.setText("…")
        self.thumb_label.setStyleSheet(
            "QLabel#galleryThumb { background: rgba(128, 128, 128, 0.12);"
            " border-radius: 4px; color: rgba(128, 128, 128, 0.6); font-size: 20px; }"
        )

    def set_thumbnail_pixmap(self, pixmap: QPixmap):
        """异步加载完成后填充缩略图"""
        self.thumb_label.setPixmap(pixmap)
        self.thumb_label.setStyleSheet("QLabel#galleryThumb { background: transparent; }")


class ImageGalleryWidget(QWidget):
    """图库主视图：左侧缩略图网格 + 右侧预览"""

    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.library = ImageLibrary(core)
        self.images: List[Dict] = []
        self._thumb_cache: Dict[str, QPixmap] = {}
        self._load_timer = QTimer(self)
        self._load_timer.setSingleShot(True)
        self._load_timer.timeout.connect(self._load_next_batch)
        self._pending_batches: List[List[Dict]] = []
        self._setup_ui()
        self._load_images()
        self._refresh_grid()
        qconfig.themeChangedFinished.connect(self._on_theme_changed)

    def _on_theme_changed(self):
        """主题切换后刷新样式"""
        self._apply_grid_style()
        self.preview._apply_style()

    def _setup_ui(self):
        self.setObjectName("imageGalleryWidget")
        self.setStyleSheet("QWidget#imageGalleryWidget { background: transparent; }")

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(16, 12, 16, 16)

        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setHandleWidth(1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.search_input = LineEdit(left)
        self.search_input.setPlaceholderText("搜索图片文件名...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._refresh_grid)
        left_layout.addWidget(self.search_input)

        self.grid = QListWidget(left)
        self.grid.setSpacing(2)
        self.grid.setFlow(QListWidget.TopToBottom)
        self.grid.setViewMode(QListWidget.ListMode)
        self.grid.setSelectionMode(QAbstractItemView.SingleSelection)
        self.grid.itemClicked.connect(self._on_grid_selected)
        self.grid.itemDoubleClicked.connect(lambda item: self._copy_image())
        self.grid.setContextMenuPolicy(Qt.CustomContextMenu)
        self.grid.customContextMenuRequested.connect(self._show_context_menu)
        self.grid.verticalScrollBar().valueChanged.connect(self._on_scroll_thumbnails)
        self._apply_grid_style()
        left_layout.addWidget(self.grid)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("图片预览", right)
        title.setObjectName("galleryPreviewTitle")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        right_layout.addWidget(title)

        self.preview = GalleryPreviewWidget(right)
        right_layout.addWidget(self.preview)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([280, 620])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        main_layout.addWidget(splitter, 1)

        # 工具栏（放在底部，避免与预览组件创建顺序耦合）
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        self.paste_btn = PushButton("粘贴", self)
        self.paste_btn.setIcon(FIF.PASTE)
        self.paste_btn.clicked.connect(self._paste_from_clipboard)
        toolbar.addWidget(self.paste_btn)

        self.add_btn = PushButton("添加", self)
        self.add_btn.setIcon(FIF.ADD)
        self.add_btn.clicked.connect(self._add_image)
        toolbar.addWidget(self.add_btn)

        self.copy_btn = PushButton("复制", self)
        self.copy_btn.setIcon(FIF.COPY)
        self.copy_btn.clicked.connect(self._copy_image)
        toolbar.addWidget(self.copy_btn)

        self.save_btn = PushButton("另存为", self)
        self.save_btn.setIcon(FIF.SAVE)
        self.save_btn.clicked.connect(self._save_image)
        toolbar.addWidget(self.save_btn)

        self.delete_btn = PushButton("删除", self)
        self.delete_btn.setIcon(FIF.DELETE)
        self.delete_btn.clicked.connect(self._delete_image)
        toolbar.addWidget(self.delete_btn)

        toolbar.addStretch()

        self.zoom_out_btn = TransparentToolButton(FIF.ZOOM_OUT, self)
        self.zoom_out_btn.setToolTip("缩小")
        self.zoom_out_btn.clicked.connect(self.preview.zoom_out)
        toolbar.addWidget(self.zoom_out_btn)

        self.zoom_in_btn = TransparentToolButton(FIF.ZOOM_IN, self)
        self.zoom_in_btn.setToolTip("放大")
        self.zoom_in_btn.clicked.connect(self.preview.zoom_in)
        toolbar.addWidget(self.zoom_in_btn)

        self.fit_btn = TransparentToolButton(FIF.FULL_SCREEN, self)
        self.fit_btn.setToolTip("自适应窗口")
        self.fit_btn.clicked.connect(self.preview.fit_to_window)
        toolbar.addWidget(self.fit_btn)

        self.reset_btn = TransparentToolButton(FIF.SYNC, self)
        self.reset_btn.setToolTip("原始大小")
        self.reset_btn.clicked.connect(self.preview.reset_scale)
        toolbar.addWidget(self.reset_btn)

        main_layout.addLayout(toolbar)

        self.status_label = CaptionLabel("就绪", self)
        main_layout.addWidget(self.status_label)

    def _apply_grid_style(self):
        dark = is_dark_theme()
        hover = "#3d3d3d" if dark else "#eef0f4"
        selected = "#3a5a5a" if dark else "#ddecec"
        name_color = "#e0e0e0" if dark else "#333333"
        scroll_bg = "transparent" if dark else "transparent"
        scroll_handle = "#4d4d4d" if dark else "#c0c0c0"
        self.grid.setStyleSheet(
            f"QListWidget {{ background: transparent; border: none; outline: none; }}"
            f"QListWidget::item {{ background: transparent; padding: 2px;"
            f" border-radius: 6px; }}"
            f"QListWidget::item:hover {{ background: {hover}; }}"
            f"QListWidget::item:selected {{ background: {selected}; }}"
            f"QLabel#galleryTileName {{ color: {name_color}; background: transparent; }}"
            f"QLabel#galleryThumb {{ background: transparent; }}"
            f"QScrollBar:vertical {{ background: {scroll_bg}; width: 10px;"
            f" border-radius: 5px; margin: 2px; }}"
            f"QScrollBar::handle:vertical {{ background: {scroll_handle};"
            f" min-height: 30px; border-radius: 5px; }}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}"
        )

    def _load_images(self):
        """从图库服务同步到本地列表"""
        self.images = list(self.library.images)

    def _refresh_grid(self):
        """按当前搜索关键词刷新网格（先占位，后异步加载缩略图）"""
        query = self.search_input.text().strip().lower()
        self.grid.blockSignals(True)
        self.grid.clear()
        for entry in self.library.images:
            if query and query not in entry.get("filename", "").lower():
                continue
            item = QListWidgetItem(self.grid)
            item.setSizeHint(QSize(0, THUMBNAIL_SIZE + 16))
            item.setData(Qt.UserRole, entry)
            tile = GalleryTileWidget(entry, self.grid)
            self.grid.setItemWidget(item, tile)
        self.grid.blockSignals(False)
        self.status_label.setText(f"共 {self.library.count()} 张图片")
        self._schedule_thumbnail_loads()

    def _schedule_thumbnail_loads(self):
        """按可见区域分批调度缩略图加载"""
        self._pending_batches = self._build_pending_batches()
        if self._pending_batches:
            self._load_timer.start(0)

    def _build_pending_batches(self) -> List[List[Dict]]:
        """构建待加载批次：可见项优先，其余按顺序补齐"""
        cache = self._thumb_cache
        visible = set()
        pending = []

        viewport = self.grid.viewport().rect()
        for i in range(self.grid.count()):
            item = self.grid.item(i)
            entry = item.data(Qt.UserRole)
            if not isinstance(entry, dict):
                continue
            path = entry.get("path", "")
            if path in cache:
                self._apply_thumb(item, cache[path])
                continue
            if self.grid.visualItemRect(item).intersects(viewport):
                visible.add(path)
            pending.append(entry)

        ordered = [e for e in pending if e.get("path") in visible]
        ordered += [e for e in pending if e.get("path") not in visible]
        return [
            ordered[i:i + THUMBNAIL_BATCH]
            for i in range(0, len(ordered), THUMBNAIL_BATCH)
        ]

    def _load_next_batch(self):
        """加载下一批缩略图（每批加载完成释放事件循环）"""
        if not self._pending_batches:
            return
        batch = self._pending_batches.pop(0)
        for entry in batch:
            path = entry.get("path", "")
            if not path or path in self._thumb_cache:
                continue
            image = QImage(path)
            if image.isNull():
                continue
            thumb = QPixmap.fromImage(
                image.scaled(
                    THUMBNAIL_SIZE, THUMBNAIL_SIZE,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation,
                )
            )
            self._thumb_cache[path] = thumb
            for i in range(self.grid.count()):
                item = self.grid.item(i)
                data = item.data(Qt.UserRole)
                if isinstance(data, dict) and data.get("path") == path:
                    self._apply_thumb(item, thumb)
                    break
        loaded = len(self._thumb_cache)
        self.status_label.setText(f"共 {self.library.count()} 张图片 · 已加载 {loaded} 张缩略图")
        if self._pending_batches:
            self._load_timer.start(0)

    def _apply_thumb(self, item: QListWidgetItem, pixmap: QPixmap):
        """将缩略图应用到 item 对应的磁贴"""
        tile = self.grid.itemWidget(item)
        if tile is not None:
            tile.set_thumbnail_pixmap(pixmap)

    def _on_scroll_thumbnails(self):
        """滚动时加载新进入可见区域的缩略图"""
        if self._pending_batches:
            return
        pending = self._build_pending_batches()
        if pending:
            self._pending_batches = pending
            self._load_timer.start(0)

    def _on_grid_selected(self, item):
        entry = item.data(Qt.UserRole)
        if not isinstance(entry, dict):
            return
        pixmap = QPixmap(entry.get("path", ""))
        if pixmap.isNull():
            return
        self.preview.set_image(pixmap)
        self.status_label.setText(
            self.preview.image_info(entry.get("source", ""), entry.get("added_at", ""))
        )

    def _current_entry(self) -> Optional[Dict]:
        item = self.grid.currentItem()
        if item is None:
            return None
        entry = item.data(Qt.UserRole)
        return entry if isinstance(entry, dict) else None

    def _paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        if not clipboard.mimeData().hasImage():
            _show_info(self, "提示", "剪切板中没有图片", success=False)
            return
        pixmap = clipboard.pixmap()
        if pixmap and not pixmap.isNull():
            self._add_pixmap(pixmap, "从剪切板粘贴")

    def _add_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;所有文件 (*.*)",
        )
        if not file_path:
            return
        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            _show_info(self, "错误", "无法加载图片", success=False)
            return
        self._add_pixmap(pixmap, os.path.basename(file_path))

    def _add_pixmap(self, pixmap: QPixmap, source: str):
        entry = self.library.add_image(pixmap, source)
        if entry is None:
            _show_info(self, "错误", "保存图片失败", success=False)
            return
        self._refresh_grid()
        _show_info(self, "添加成功", f"已添加图片 {entry['filename']}")

    def _copy_image(self):
        entry = self._current_entry()
        if not entry:
            return
        pixmap = QPixmap(entry.get("path", ""))
        if pixmap.isNull():
            return
        QApplication.clipboard().setPixmap(pixmap)
        self.status_label.setText("已复制图片到剪切板")
        _show_info(self, "复制成功", "已复制图片到剪切板")

    def _save_image(self):
        entry = self._current_entry()
        if not entry:
            return
        pixmap = QPixmap(entry.get("path", ""))
        if pixmap.isNull():
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存图片", entry.get("filename", "image.png"),
            "PNG 文件 (*.png);;JPEG 文件 (*.jpg);;所有文件 (*.*)",
        )
        if file_path and pixmap.save(file_path):
            _show_info(self, "保存成功", f"已保存到 {os.path.basename(file_path)}")
        elif file_path:
            _show_info(self, "保存失败", "无法保存图片", success=False)

    def _delete_image(self):
        entry = self._current_entry()
        if not entry:
            return
        box = MessageDialog(
            "确认删除", f"确定要删除图片 {entry.get('filename', '')} 吗？", self
        )
        if not box.exec():
            return
        index = self.library.index_of(entry.get("path", ""))
        if index < 0:
            return
        if self.library.delete(index):
            self._thumb_cache.pop(entry.get("path", ""), None)
            self.preview.clear()
            self._refresh_grid()
            _show_info(self, "删除成功", "已删除图片")
        else:
            _show_info(self, "删除失败", "无法删除图片文件", success=False)

    def _show_context_menu(self, pos):
        item = self.grid.itemAt(pos)
        if item is None:
            return
        self.grid.setCurrentItem(item)
        menu = RoundMenu(parent=self)
        copy_action = QAction("复制", self)
        copy_action.triggered.connect(self._copy_image)
        menu.addAction(copy_action)
        save_action = QAction("另存为", self)
        save_action.triggered.connect(self._save_image)
        menu.addAction(save_action)
        menu.addSeparator()
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(self._delete_image)
        menu.addAction(delete_action)
        menu.exec(QCursor.pos())

    def load_data(self) -> None:
        """数据加载入口（插件生命周期）"""
        self._load_images()
        self._refresh_grid()