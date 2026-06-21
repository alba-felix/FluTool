"""分类标签页组件"""
import os
from typing import List, Dict, Any, Optional, Set

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout,
    QScrollArea, QFrame, QAction,
)
from qfluentwidgets import isDarkTheme, RoundMenu

from . import (
    CARD_WIDTH, DEFAULT_ICON_SIZE, GRID_VIEW, LIST_VIEW,
)
from .cards import AppCard, AddAppCard


class CategoryTab(QScrollArea):
    """分类标签页内容 - 使用 ScrollArea 作为容器"""

    app_clicked = pyqtSignal(dict)
    app_deleted = pyqtSignal(dict)
    app_edited = pyqtSignal(dict)
    app_favorited = pyqtSignal(dict)
    add_app_clicked = pyqtSignal()
    app_selection_changed = pyqtSignal(int, bool)

    def __init__(self, category_id: Optional[int], parent=None):
        super().__init__(parent)
        self.category_id = category_id
        self._is_drag_over = False
        self._view_mode = GRID_VIEW
        self._icon_size = DEFAULT_ICON_SIZE
        self._batch_mode = False
        self._selected_ids: Set[int] = set()
        self._search_keyword = ""
        self._apps: List[Dict[str, Any]] = []
        self._rebuilding = False
        self._setup_ui()
        self._apply_style()

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # 启用拖拽
        self.setAcceptDrops(True)

    def _setup_ui(self):
        """设置界面"""
        # 设置滚动区域属性
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setFrameShape(QFrame.NoFrame)

        # 创建内容容器 - 这是卡片组的背景板
        self.content_widget = QWidget()
        self.content_widget.setObjectName("contentWidget")
        self.content_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.content_widget.customContextMenuRequested.connect(self._show_context_menu)

        # 内容容器的布局
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(0)

        # 卡片网格容器 - 这也是背景板的一部分
        self.grid_container = QWidget()
        self.grid_container.setObjectName("gridContainer")

        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.grid_container)
        layout.addStretch()

        self.setWidget(self.content_widget)

    def _apply_style(self):
        """应用样式"""
        # 为整个标签页设置背景
        if isDarkTheme():
            self.setStyleSheet("""
                QScrollArea {
                    background-color: #1a1a1a;
                    border: none;
                }
            """)
            self.content_widget.setStyleSheet("""
                QWidget#contentWidget {
                    background-color: #1a1a1a;
                    border-radius: 8px;
                }
                QWidget#gridContainer {
                    background-color: transparent;
                }
            """)
        else:
            self.setStyleSheet("""
                QScrollArea {
                    background-color: #f5f5f5;
                    border: none;
                }
            """)
            self.content_widget.setStyleSheet("""
                QWidget#contentWidget {
                    background-color: #f5f5f5;
                    border-radius: 8px;
                }
                QWidget#gridContainer {
                    background-color: transparent;
                }
            """)



    def showEvent(self, event):
        """确保每次显示时样式正确"""
        super().showEvent(event)
        self._apply_style()

    def _show_context_menu(self, pos):
        """显示右键菜单"""
        menu = RoundMenu(parent=self)
        add_action = QAction("添加应用", self)
        add_action.triggered.connect(self.add_app_clicked.emit)
        menu.addAction(add_action)
        menu.exec_(self.mapToGlobal(pos))

    def set_display_options(
        self,
        view_mode: str,
        icon_size: int,
        batch_mode: bool,
        selected_ids: Set[int],
        search_keyword: str
    ) -> None:
        """设置显示参数"""
        self._view_mode = view_mode
        self._icon_size = icon_size
        self._batch_mode = batch_mode
        self._selected_ids = set(selected_ids)
        self._search_keyword = search_keyword

    def refresh_apps(self, apps: List[Dict[str, Any]]):
        """刷新应用列表（增量更新）"""
        self._apps = list(apps)
        self._rebuilding = True

        # 收集现有卡片
        existing_cards: Dict[int, AppCard] = {}
        add_card: Optional[AddAppCard] = None
        stale_widgets: List[QWidget] = []

        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                w = item.widget()
                if isinstance(w, AppCard):
                    app_id = w.app_data.get("id")
                    if app_id is not None and app_id not in existing_cards:
                        existing_cards[app_id] = w
                    else:
                        stale_widgets.append(w)
                elif isinstance(w, AddAppCard):
                    add_card = w
                else:
                    stale_widgets.append(w)

        # 确定新列表中的 app_id 集合
        new_app_ids: Set[int] = set()
        for app_data in apps:
            app_id = app_data.get("id")
            if app_id is not None:
                new_app_ids.add(app_id)

        # 移除不再存在的卡片
        for app_id in list(existing_cards.keys()):
            if app_id not in new_app_ids:
                w = existing_cards.pop(app_id)
                self.grid_layout.removeWidget(w)
                w.setParent(None)

        for w in stale_widgets:
            self.grid_layout.removeWidget(w)
            w.setParent(None)

        # 清空布局，准备重新排列
        while self.grid_layout.count():
            self.grid_layout.takeAt(0)

        # 增量更新或创建卡片
        for idx, app_data in enumerate(apps):
            app_id = app_data.get("id")
            card = existing_cards.get(app_id) if app_id is not None else None

            if card is not None:
                # 增量更新现有卡片
                card.app_data = app_data
                card.view_mode = self._view_mode
                card.icon_size = self._icon_size
                card.batch_mode = self._batch_mode
                card.search_keyword = self._search_keyword
                card._is_selected = app_id in self._selected_ids if app_id is not None else False

                if card._icon_label:
                    card._icon_label.setFixedSize(self._icon_size, self._icon_size)
                if card._select_checkbox:
                    card._select_checkbox.setChecked(card._is_selected)

                card._apply_view_mode()
                card._update_display_text()
                card._update_text_color()
                card._update_checkbox_visibility()
                card.update()
            else:
                # 创建新卡片
                card = AppCard(
                    app_data,
                    view_mode=self._view_mode,
                    icon_size=self._icon_size,
                    batch_mode=self._batch_mode,
                    selected=app_id in self._selected_ids if app_id is not None else False,
                    search_keyword=self._search_keyword,
                    parent=self.grid_container
                )
                card.app_clicked.connect(self.app_clicked.emit)
                card.app_deleted.connect(self.app_deleted.emit)
                card.app_edited.connect(self.app_edited.emit)
                card.app_favorited.connect(self.app_favorited.emit)
                card.selection_changed.connect(self.app_selection_changed.emit)

            self.grid_layout.addWidget(card, idx, 0)

        # 处理添加卡片
        if not self._batch_mode:
            if add_card is not None:
                add_card.set_view_mode(self._view_mode)
                add_card.set_icon_size(self._icon_size)
            else:
                add_card = AddAppCard(self._view_mode, self._icon_size, self.grid_container)
                add_card.clicked.connect(self.add_app_clicked.emit)
            self.grid_layout.addWidget(add_card, len(apps), 0)
        elif add_card is not None:
            self.grid_layout.removeWidget(add_card)
            add_card.setParent(None)

        self._rebuilding = False
        self._update_grid_columns()

    def resizeEvent(self, event):
        """调整大小时更新网格列数"""
        super().resizeEvent(event)
        self._update_grid_columns()

    def _update_grid_columns(self):
        """更新网格列数"""
        if self._rebuilding:
            return
        self._rebuilding = True

        if not hasattr(self, 'grid_layout') or not self.grid_layout:
            self._rebuilding = False
            return

        widgets = []
        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                widgets.append(item.widget())

        while self.grid_layout.count():
            self.grid_layout.takeAt(0)

        if self._view_mode == LIST_VIEW:
            cols = 1
        else:
            available_width = max(100, self.viewport().width() - 40)
            spacing = self.grid_layout.spacing()
            card_width = max(CARD_WIDTH, 120 + max(0, self._icon_size - DEFAULT_ICON_SIZE) * 2)
            cols = max(1, int((available_width + spacing) / (card_width + spacing)))

        for i, widget in enumerate(widgets):
            row = i // cols
            col = i % cols
            self.grid_layout.addWidget(widget, row, col)

        self._rebuilding = False

    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._is_drag_over = True
            self.update()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """拖拽离开事件"""
        self._is_drag_over = False
        self.update()

    def dropEvent(self, event):
        """拖拽放下事件"""
        self._is_drag_over = False
        self.update()

        urls = event.mimeData().urls()
        if not urls:
            return

        launcher_widget = self._find_launcher_widget()
        if launcher_widget is None:
            event.ignore()
            return

        target_category_id = self.category_id if isinstance(self.category_id, int) else None
        for url in urls:
            file_path = url.toLocalFile()
            if not os.path.exists(file_path):
                continue
            launcher_widget._add_app_with_path(file_path, target_category_id)

        event.acceptProposedAction()

    def _find_launcher_widget(self):
        """向上查找 AppLauncherWidget，避免被 QTabWidget 重设父对象后丢失引用"""
        parent = self.parentWidget()
        while parent is not None:
            if hasattr(parent, "_add_app_with_path"):
                return parent
            parent = parent.parentWidget()
        return None

    def paintEvent(self, event):
        """绘制事件 - 添加拖拽视觉反馈"""
        super().paintEvent(event)

        if self._is_drag_over:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            # 绘制半透明覆盖层
            overlay_color = QColor(0, 159, 170, 30) if not isDarkTheme() else QColor(0, 159, 170, 50)
            painter.fillRect(self.rect(), overlay_color)

            # 绘制边框
            border_color = QColor(0, 159, 170, 150)
            pen = QPen(border_color, 3, Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(self.rect().adjusted(5, 5, -5, -5), 8, 8)
