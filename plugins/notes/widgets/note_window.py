"""笔记独立窗口 - QWidget 版本"""

from typing import Optional, List
from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QStackedWidget, QLineEdit, QApplication, QAbstractButton, QMenu, QAction,
    QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QEasingCurve, QPoint, QRect, QSize, QVariantAnimation, QTimer
from PyQt5.QtGui import QFont, QPainter, QColor, QIcon, QPen, QPixmap, QCursor
from qfluentwidgets import (
    FluentIcon as FIF, FluentStyleSheet, isDarkTheme,
    NavigationWidget, SmoothScrollArea, StrongBodyLabel,
    BodyLabel, CaptionLabel, SearchLineEdit, PushButton,
    PrimaryPushButton, InfoBar, InfoBarPosition, drawIcon,
    TransparentToolButton,
)
from qfluentwidgets.common.font import setFont
from qfluentwidgets.common.icon import toQIcon

from ..core.runtime import get_notes_runtime
from ..models.note import Note
from ..services.category_service import CategoryService
from ..services.note_service import NoteService
from .note_card import NoteCard
from .table_grid import TableGrid


class ScrollableNavButton(NavigationWidget):
    """可滚动导航按钮"""
    clicked = pyqtSignal(bool)

    def __init__(self, icon, text: str, parent=None):
        super().__init__(True, parent)
        self._icon = icon
        self._text = text
        self._expandWidth = 180
        setFont(self)
        self.setToolTip(text)

    def text(self):
        return self._text

    def setText(self, text: str):
        self._text = text
        self.update()

    def icon(self):
        return toQIcon(self._icon)

    def setIcon(self, icon):
        self._icon = icon
        self.update()

    def setExpandWidth(self, width: int):
        self._expandWidth = width
        if not self.isCompacted:
            self.setFixedWidth(width)

    def setCompacted(self, isCompacted: bool):
        if isCompacted == self.isCompacted:
            return
        self.isCompacted = isCompacted
        if isCompacted:
            self.setFixedSize(48, 36)
        else:
            self.setFixedSize(self._expandWidth, 36)
        self.update()

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        painter.setPen(Qt.NoPen)
        if self.isPressed:
            painter.setOpacity(0.7)
        if not self.isEnabled():
            painter.setOpacity(0.4)
        c = 255 if isDarkTheme() else 0
        if self.isSelected:
            painter.setBrush(QColor(c, c, c, 6 if self.isEnter else 10))
            painter.drawRoundedRect(self.rect(), 5, 5)
            painter.setBrush(QColor(0, 153, 255) if not isDarkTheme() else QColor(0, 153, 255))
            painter.drawRoundedRect(0, 10, 3, 16, 1.5, 1.5)
        elif self.isEnter and self.isEnabled():
            painter.setBrush(QColor(c, c, c, 10))
            painter.drawRoundedRect(self.rect(), 5, 5)
        drawIcon(self._icon, painter, QRect(12, 10, 16, 16))
        if not self.isCompacted:
            painter.setFont(self.font())
            painter.setPen(self.textColor())
            painter.drawText(QRect(40, 0, self.width() - 48, self.height()), Qt.AlignVCenter, self._text)

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        self.clicked.emit(True)


class ScrollableNavigationPanel(QWidget):
    """可滚动导航面板"""
    displayModeChanged = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._isExpanded = True
        self._expandWidth = 180
        self._items = {}
        self._currentKey = None

        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(0)

        self._scroll_area = SmoothScrollArea(self)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setStyleSheet("""
            QScrollArea, SmoothScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(128, 128, 128, 0.4);
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(128, 128, 128, 0.6);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

        self._scroll_widget = QWidget()
        self._scroll_layout = QVBoxLayout(self._scroll_widget)
        self._scroll_layout.setContentsMargins(4, 4, 4, 4)
        self._scroll_layout.setSpacing(4)
        self._scroll_layout.setAlignment(Qt.AlignTop)
        self._scroll_widget.setStyleSheet("background: transparent;")

        self._scroll_area.setWidget(self._scroll_widget)

        self.vBoxLayout.addWidget(self._scroll_area, 1)

        self.setFixedWidth(self._expandWidth)
        self.setAttribute(Qt.WA_StyledBackground)
        FluentStyleSheet.NAVIGATION_INTERFACE.apply(self)

    def addItem(self, routeKey: str, icon, text: str, onClick=None, position=None):
        if routeKey in self._items:
            return
        btn = ScrollableNavButton(icon, text, self._scroll_widget)
        btn.setExpandWidth(self._expandWidth)
        btn.clicked.connect(lambda: self._on_item_clicked(routeKey))
        if onClick:
            btn.clicked.connect(onClick)
        btn.setCompacted(not self._isExpanded)
        self._items[routeKey] = btn
        self._scroll_layout.addWidget(btn, 0, Qt.AlignTop)
        return btn

    def removeItem(self, routeKey: str):
        if routeKey not in self._items:
            return
        btn = self._items.pop(routeKey)
        self._scroll_layout.removeWidget(btn)
        btn.deleteLater()

    def setCurrentItem(self, routeKey: str):
        if routeKey not in self._items:
            return
        if self._currentKey and self._currentKey in self._items:
            self._items[self._currentKey].setSelected(False)
        self._currentKey = routeKey
        self._items[routeKey].setSelected(True)

    def currentItem(self):
        return self._items.get(self._currentKey)

    def _on_item_clicked(self, routeKey: str):
        self.setCurrentItem(routeKey)

    def expand(self):
        self._isExpanded = True
        self.setFixedWidth(self._expandWidth)
        for btn in self._items.values():
            btn.setCompacted(False)
        self.displayModeChanged.emit(True)

    def collapse(self):
        self._isExpanded = False
        self.setFixedWidth(48)
        for btn in self._items.values():
            btn.setCompacted(True)
        self.displayModeChanged.emit(False)

    def isExpanded(self):
        return self._isExpanded

    def setExpandWidth(self, width: int):
        self._expandWidth = width

    def resizeEvent(self, e):
        super().resizeEvent(e)


class NoteListWidget(QWidget):
    """笔记列表组件 - 懒渲染"""
    note_edit_clicked = pyqtSignal(int)
    note_delete_clicked = pyqtSignal(int)
    note_favorite_clicked = pyqtSignal(int)
    note_archive_clicked = pyqtSignal(int)
    note_content_updated = pyqtSignal(int, str)

    CARD_HEIGHT = 130
    CARD_SPACING = 12
    BUFFER_SIZE = 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self._notes: List[Note] = []
        self._rendered_indices: set = set()
        self._card_cache: dict = {}
        self._empty_label = None
        self._note_manager = None
        self._init_ui()

    def set_note_manager(self, note_manager):
        self._note_manager = note_manager

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setStyleSheet("background: transparent;")

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(128, 128, 128, 0.4);
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(128, 128, 128, 0.6);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(16, 16, 16, 16)
        self.scroll_layout.setSpacing(self.CARD_SPACING)
        self.scroll_layout.addStretch()

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)

        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll_changed)

    def _on_scroll_changed(self, value):
        self._update_visible_cards()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_visible_cards()

    def set_notes(self, notes: List[Note]):
        self._clear_all()
        self._notes = notes
        if not notes:
            self._show_empty_message()
            return
        QTimer.singleShot(0, self._update_visible_cards)

    def _update_visible_cards(self):
        if not self._notes:
            return
        viewport_height = self.scroll_area.viewport().height()
        scroll_value = self.scroll_area.verticalScrollBar().value()
        card_total_height = self.CARD_HEIGHT + self.CARD_SPACING
        start_index = max(0, int((scroll_value - 16) / card_total_height) - self.BUFFER_SIZE)
        end_index = min(
            len(self._notes),
            int((scroll_value + viewport_height - 16) / card_total_height) + self.BUFFER_SIZE + 2
        )
        for i in range(start_index, end_index):
            if i not in self._rendered_indices:
                self._create_and_insert_card(i)

    def _create_and_insert_card(self, index: int):
        if index < 0 or index >= len(self._notes):
            return
        note = self._notes[index]
        card = NoteCard(note)
        if self._note_manager:
            card.set_note_manager(self._note_manager)
        card.edit_clicked.connect(self.note_edit_clicked.emit)
        card.delete_clicked.connect(self.note_delete_clicked.emit)
        card.favorite_clicked.connect(self.note_favorite_clicked.emit)
        card.archive_clicked.connect(self.note_archive_clicked.emit)
        card.content_updated.connect(self.note_content_updated.emit)
        insert_pos = 0
        for i in sorted(self._rendered_indices):
            if i < index:
                insert_pos += 1
            else:
                break
        self.scroll_layout.insertWidget(insert_pos, card)
        self._rendered_indices.add(index)
        self._card_cache[index] = card

    def _clear_all(self):
        while self.scroll_layout.count() > 1:
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._rendered_indices.clear()
        self._card_cache.clear()
        self._clear_empty_message()

    def refresh_styles(self):
        """主题切换时刷新所有已渲染卡片的样式"""
        for card in self._card_cache.values():
            card.update_style()

    def _clear_empty_message(self):
        if self._empty_label:
            self._empty_label.deleteLater()
            self._empty_label = None

    def _show_empty_message(self):
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.setSpacing(12)
        empty_layout.setAlignment(Qt.AlignCenter)
        icon_label = QLabel()
        icon_label.setText("📝")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 48px;")
        empty_layout.addWidget(icon_label)
        self._empty_label = BodyLabel("暂无笔记")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet("color: #888; font-size: 16px;")
        empty_layout.addWidget(self._empty_label)
        hint_label = CaptionLabel("点击右上角「快速添加」或「完整添加」创建笔记")
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet("color: #666; font-size: 12px;")
        empty_layout.addWidget(hint_label)
        self.scroll_layout.insertWidget(0, empty_widget)


class NotesWindow(QWidget):
    """笔记管理独立窗口"""

    NAV_ALL = "all"
    NAV_FAVORITES = "favorites"
    NAV_ARCHIVED = "archived"

    def __init__(self, parent=None, runtime=None):
        super().__init__(parent)
        self._allow_close = False
        self._runtime = runtime or get_notes_runtime()
        self.setWindowTitle("笔记管理")
        self.setWindowFlags(Qt.Window)
        self.resize(1100, 700)
        self.setMinimumSize(700, 500)
        self.setAttribute(Qt.WA_StyledBackground)

        self._note_service: NoteService = self._runtime.note_service
        self._category_service: CategoryService = self._runtime.category_service
        self._theme_manager = self._runtime.theme_manager
        self._event_bus = self._runtime.event_bus
        self._current_nav_key: str = self.NAV_ALL
        self._current_category_id: Optional[int] = None
        self._search_keyword: str = ""

        self._setup_ui()
        self._update_window_background()
        self._connect_signals()
        self._load_notes()

    def focusOutEvent(self, event):
        """失去焦点（如点击主窗口）时把笔记窗口移到主窗口下方，保持可见"""
        super().focusOutEvent(event)
        if self._allow_close:
            return
        QTimer.singleShot(0, self._move_below_main_window)

    def _is_focus_inside(self) -> bool:
        """当前焦点是否在本窗口或其子窗口内"""
        focus_widget = QApplication.focusWidget()
        if focus_widget is None:
            return True
        current = focus_widget.window()
        while current is not None:
            if current is self:
                return True
            current = current.parentWidget()
        return False

    def _move_below_main_window(self):
        """把笔记窗口移到主窗口正下方（屏幕放不下则移到上方）"""
        if self._allow_close or not self.isVisible():
            return
        if self._is_focus_inside():
            return
        from .. import NotesWindowManager
        mw = NotesWindowManager.get_main_window()
        if mw is None or not mw.isVisible():
            return
        notes_geom = self.geometry()
        mw_geom = mw.geometry()
        x = mw_geom.x() + (mw_geom.width() - notes_geom.width()) // 2
        y = mw_geom.y() + mw_geom.height() + 8
        screen_rect = QApplication.primaryScreen().availableGeometry()
        if y + notes_geom.height() > screen_rect.bottom():
            y = mw_geom.y() - notes_geom.height() - 8
        self.move(x, y)

    def _update_window_background(self):
        """根据当前主题设置窗口背景色"""
        is_dark = isDarkTheme()
        bg = "#202020" if is_dark else "#f7f7f7"
        self.setStyleSheet(f"background-color: {bg};")

    def _setup_ui(self):
        """构建界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部工具栏
        self._toolbar = QWidget()
        self._toolbar.setFixedHeight(48)
        self._toolbar.setObjectName("notesToolbar")
        self._toolbar.setStyleSheet("""
            QWidget#notesToolbar {
                background-color: transparent;
                border-bottom: 1px solid rgba(128, 128, 128, 0.2);
            }
        """)
        toolbar_layout = QHBoxLayout(self._toolbar)
        toolbar_layout.setContentsMargins(16, 0, 16, 0)

        self.title_label = StrongBodyLabel("全部笔记")
        toolbar_layout.addWidget(self.title_label)

        self.note_count_label = CaptionLabel("共 0 条笔记")
        self.note_count_label.setStyleSheet("color: #888888;")
        toolbar_layout.addWidget(self.note_count_label)

        toolbar_layout.addStretch()

        self.search_input = SearchLineEdit()
        self.search_input.setPlaceholderText("搜索笔记...")
        self.search_input.setFixedWidth(160)
        self.search_input.searchSignal.connect(self._on_search)
        self.search_input.clearSignal.connect(self._on_clear_search)
        toolbar_layout.addWidget(self.search_input)

        # 布局切换：卡片 | 表格
        self._layout_switch = PushButton("表格")
        self._layout_switch.setFixedSize(64, 32)
        self._layout_switch.setCheckable(True)
        self._layout_switch.setIcon(FIF.VIEW)
        self._layout_switch.setToolTip("切换到表格视图（迷你 Excel）")
        self._layout_switch.clicked.connect(self._toggle_layout)
        toolbar_layout.addWidget(self._layout_switch)

        self.manage_category_btn = PushButton("分类管理")
        self.manage_category_btn.setFixedHeight(32)
        self.manage_category_btn.setIcon(FIF.SETTING)
        self.manage_category_btn.clicked.connect(self._show_category_manager)
        toolbar_layout.addWidget(self.manage_category_btn)

        self.quick_add_btn = PushButton("快速添加")
        self.quick_add_btn.setFixedHeight(32)
        self.quick_add_btn.setIcon(FIF.ADD)
        self.quick_add_btn.clicked.connect(self._show_quick_add)
        toolbar_layout.addWidget(self.quick_add_btn)

        self.full_add_btn = PrimaryPushButton("完整添加")
        self.full_add_btn.setFixedHeight(32)
        self.full_add_btn.setIcon(FIF.EDIT)
        self.full_add_btn.clicked.connect(self._show_full_add)
        toolbar_layout.addWidget(self.full_add_btn)

        # 主题切换
        self._theme_btn = TransparentToolButton(FIF.CONSTRACT, self._toolbar)
        self._theme_btn.setFixedSize(32, 32)
        self._theme_btn.setIconSize(QSize(14, 14))
        self._theme_btn.setToolTip("切换主题")
        self._theme_btn.clicked.connect(self._toggle_theme)
        toolbar_layout.addWidget(self._theme_btn)

        main_layout.addWidget(self._toolbar)

        # 内容区：导航 + 笔记列表
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.navigation = ScrollableNavigationPanel(content)
        content_layout.addWidget(self.navigation)

        self.note_list = NoteListWidget()
        self.note_list.set_note_manager(self._note_service)
        self.note_list.note_edit_clicked.connect(self._edit_note)
        self.note_list.note_delete_clicked.connect(self._delete_note)
        self.note_list.note_favorite_clicked.connect(self._toggle_favorite)
        self.note_list.note_archive_clicked.connect(self._toggle_archive)
        self.note_list.note_content_updated.connect(self._on_note_content_updated)

        # 内容堆叠：卡片视图(0) / 表格视图(1)
        self._view_stack = QStackedWidget()
        self._view_stack.addWidget(self.note_list)

        self.table_grid = TableGrid(self._note_service)
        self._view_stack.addWidget(self.table_grid)

        content_layout.addWidget(self._view_stack, 1)

        main_layout.addWidget(content, 1)

        # 初始化导航项
        self._setup_navigation_items()
        self.navigation.setCurrentItem(self.NAV_ALL)

    def _setup_navigation_items(self):
        self.navigation.addItem(
            routeKey=self.NAV_ALL,
            icon=FIF.DOCUMENT,
            text="全部笔记",
            onClick=lambda: self._on_nav_changed(self.NAV_ALL)
        )
        self.navigation.addItem(
            routeKey=self.NAV_FAVORITES,
            icon=FIF.HEART,
            text="收藏",
            onClick=lambda: self._on_nav_changed(self.NAV_FAVORITES)
        )
        self.navigation.addItem(
            routeKey=self.NAV_ARCHIVED,
            icon=FIF.FOLDER,
            text="归档",
            onClick=lambda: self._on_nav_changed(self.NAV_ARCHIVED)
        )
        self._refresh_category_navigation()

    def _refresh_category_navigation(self):
        categories = self._category_service.get_all()
        for category in categories:
            route_key = f"category_{category.id}"
            try:
                self.navigation.removeItem(route_key)
            except Exception:
                pass
            self.navigation.addItem(
                routeKey=route_key,
                icon=FIF.TAG,
                text=category.name,
                onClick=lambda checked=False, cid=category.id: self._on_category_nav_changed(cid)
            )

    def _connect_signals(self):
        self._event_bus.note_created.connect(self._on_note_changed)
        self._event_bus.note_updated.connect(self._on_note_changed)
        self._event_bus.note_deleted.connect(self._on_note_changed)
        self._event_bus.note_favorited.connect(self._on_note_changed)
        self._event_bus.note_archived.connect(self._on_note_changed)
        self._event_bus.category_created.connect(self._on_category_changed)
        self._event_bus.category_updated.connect(self._on_category_changed)
        self._event_bus.category_deleted.connect(self._on_category_changed)
        self._event_bus.category_changed.connect(self._on_category_changed)
        self._theme_refresh_cb = lambda _: self._on_theme_changed()
        self._theme_manager.register_callback(self._theme_refresh_cb)
        self._theme_manager.notify_current_theme()

    def _on_nav_changed(self, nav_key: str):
        self._current_nav_key = nav_key
        self._current_category_id = None
        self._search_keyword = ""
        titles = {
            self.NAV_ALL: "全部笔记",
            self.NAV_FAVORITES: "收藏",
            self.NAV_ARCHIVED: "归档",
        }
        self.title_label.setText(titles.get(nav_key, "笔记"))
        self._load_notes()

    def _on_category_nav_changed(self, category_id: int):
        if category_id is None or category_id <= 0:
            return
        self._current_nav_key = f"category_{category_id}"
        self._current_category_id = category_id
        self._search_keyword = ""
        category = self._category_service.get_by_id(category_id)
        self.title_label.setText(category.name if category else "笔记")
        self._load_notes()

    def _on_search(self, keyword: str):
        self._search_keyword = keyword.strip() if keyword else ""
        self._load_notes()

    def _on_clear_search(self):
        self._search_keyword = ""
        self._load_notes()

    def _toggle_layout(self):
        """切换 卡片/表格 布局"""
        is_table = self._view_stack.currentIndex() == 1
        if is_table:
            self._view_stack.setCurrentIndex(0)
            self._layout_switch.setText("表格")
            self._layout_switch.setToolTip("切换到表格视图（迷你 Excel）")
        else:
            self._view_stack.setCurrentIndex(1)
            self._layout_switch.setText("卡片")
            self._layout_switch.setToolTip("切换到卡片视图")
            self.table_grid._refresh_table_list()

    def _load_notes(self):
        notes = []
        if self._search_keyword:
            notes = self._note_service.search(self._search_keyword)
        elif self._current_nav_key == self.NAV_ALL:
            notes = self._note_service.get_all()
        elif self._current_nav_key == self.NAV_FAVORITES:
            notes = self._note_service.get_favorites()
        elif self._current_nav_key == self.NAV_ARCHIVED:
            notes = self._note_service.get_archived()
        elif self._current_category_id:
            notes = self._note_service.get_by_category(self._current_category_id)
        self.note_list.set_notes(notes)
        self.note_count_label.setText(f"共 {len(notes)} 条笔记")

    def _on_note_changed(self, *_args):
        self._load_notes()

    def _on_note_content_updated(self, note_id: int, new_content: str):
        InfoBar.success(
            title="保存成功",
            content="笔记内容已保存到数据库",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=1500,
            parent=self,
        )

    def _on_category_changed(self, *_args):
        self._refresh_category_navigation()
        if self._current_category_id and not self._category_service.get_by_id(self._current_category_id):
            self._current_category_id = None
            self._current_nav_key = self.NAV_ALL
            self.navigation.setCurrentItem(self.NAV_ALL)
            self.title_label.setText("全部笔记")
        self._load_notes()

    def _show_quick_add(self):
        from .quick_note_dialog import QuickNoteDialog
        dialog = QuickNoteDialog(
            self,
            current_category_id=self._current_category_id,
            category_service=self._category_service,
        )
        if dialog.exec():
            title = dialog.get_title()
            content = dialog.get_content()
            category_id = dialog.get_category_id()
            if content:
                self._note_service.add_note(
                    title=title, content=content, category_id=category_id
                )
                InfoBar.success(
                    title="成功",
                    content="笔记已添加",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )

    def _show_full_add(self):
        from .note_editor_dialog import NoteEditorDialog
        dialog = NoteEditorDialog(
            parent=self,
            current_category_id=self._current_category_id,
            note_service=self._note_service,
            category_service=self._category_service,
        )
        if dialog.exec():
            data = dialog.get_note_data()
            if data["content"]:
                self._note_service.add_note(
                    title=data["title"],
                    content=data["content"],
                    category_id=data["category_id"],
                    tags=data["tags"],
                    code_blocks=data["code_blocks"],
                    remarks=data["remarks"],
                    images=data["images"],
                )
                InfoBar.success(
                    title="成功",
                    content="笔记已添加",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )

    def _edit_note(self, note_id: int):
        from .note_editor_dialog import NoteEditorDialog
        note = self._note_service.get_by_id(note_id)
        if not note:
            return
        from qfluentwidgets import MessageBox
        dialog = NoteEditorDialog(
            note,
            self,
            note_service=self._note_service,
            category_service=self._category_service,
        )
        if dialog.exec():
            data = dialog.get_note_data()
            if data["content"]:
                note.title = data["title"]
                note.content = data["content"]
                note.category_id = data["category_id"]
                note.tags = data["tags"]
                from ..models.note import CodeBlock
                note.code_blocks = [CodeBlock.from_dict(cb) for cb in data["code_blocks"]]
                note.remarks = data["remarks"]
                note.images = data["images"]
                self._note_service.update_note(note)
                InfoBar.success(
                    title="成功",
                    content="笔记已更新",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )

    def _delete_note(self, note_id: int):
        from qfluentwidgets import MessageBox
        msg = MessageBox("删除笔记", "确定要删除这条笔记吗？此操作不可撤销。", self)
        msg.yesButton.setText("删除")
        msg.cancelButton.setText("取消")
        if msg.exec():
            self._note_service.delete_note(note_id)
            InfoBar.success(
                title="成功",
                content="笔记已删除",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )

    def _toggle_favorite(self, note_id: int):
        self._note_service.toggle_favorite(note_id)

    def _on_theme_changed(self):
        """主题切换时刷新窗口和列表样式"""
        self._update_window_background()
        self._apply_theme_styles()
        self.note_list.refresh_styles()

    def _apply_theme_styles(self):
        """根据当前主题更新窗口级样式"""
        is_dark = isDarkTheme()
        # 工具栏分割线颜色
        border_color = "rgba(255, 255, 255, 0.15)" if is_dark else "rgba(0, 0, 0, 0.1)"
        self._toolbar.setStyleSheet(f"""
            QWidget#notesToolbar {{
                background-color: transparent;
                border-bottom: 1px solid {border_color};
            }}
        """)

    def _toggle_theme(self):
        """切换主题并刷新卡片样式"""
        self._theme_manager.toggle()

    def _toggle_archive(self, note_id: int):
        self._note_service.toggle_archive(note_id)

    def _show_category_manager(self):
        from .category_manager_dialog import CategoryManagerDialog
        dialog = CategoryManagerDialog(self, category_service=self._category_service)
        dialog.exec()

    def closeEvent(self, event):
        """关闭窗口时默认仅隐藏（保留信号连接），只在插件退出时真正销毁"""
        if self._allow_close:
            self._cleanup_signals()
            event.accept()
        else:
            event.ignore()
            self.hide()

    def allow_close(self) -> None:
        """允许真正关闭窗口（由 NotesWindowManager 在销毁前调用）"""
        self._allow_close = True

    def _cleanup_signals(self) -> None:
        """清理事件总线信号连接，避免内存泄漏"""
        try:
            self._event_bus.note_created.disconnect(self._on_note_changed)
            self._event_bus.note_updated.disconnect(self._on_note_changed)
            self._event_bus.note_deleted.disconnect(self._on_note_changed)
            self._event_bus.note_favorited.disconnect(self._on_note_changed)
            self._event_bus.note_archived.disconnect(self._on_note_changed)
            self._event_bus.category_created.disconnect(self._on_category_changed)
            self._event_bus.category_updated.disconnect(self._on_category_changed)
            self._event_bus.category_deleted.disconnect(self._on_category_changed)
            self._event_bus.category_changed.disconnect(self._on_category_changed)
        except (TypeError, RuntimeError):
            pass
        if hasattr(self, '_theme_refresh_cb'):
            self._theme_manager.unregister_callback(self._theme_refresh_cb)
