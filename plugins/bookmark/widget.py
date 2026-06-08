"""书签管理界面"""

import os
import webbrowser
from pathlib import Path
from functools import partial
from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidgetItem,
    QAction, QFileDialog, QHeaderView,
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QIcon
from qfluentwidgets import (
    StrongBodyLabel, PushButton, LineEdit,
    FluentIcon as FIF, InfoBar, InfoBarPosition, TreeWidget,
    setCustomStyleSheet, isDarkTheme, qconfig, IndeterminateProgressBar,
    MessageBoxBase, SubtitleLabel, MessageBox, SingleDirectionScrollArea,
    TransparentToolButton, RoundMenu
)

from core.utils import get_app_data_path
from ui.common import InputDialog
from .service import BookmarkService
from .workers import WebsiteInfoFetcher


class AddBookmarkDialog(MessageBoxBase):
    """添加书签对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("添加书签", self)
        self.viewLayout.addWidget(self.titleLabel)

        self.url_edit = LineEdit(self)
        self.url_edit.setPlaceholderText("请输入网站地址")
        self.url_edit.setClearButtonEnabled(True)
        self.url_edit.returnPressed.connect(lambda: self.yesButton.click())
        self.viewLayout.addWidget(self.url_edit)

        self.name_edit = LineEdit(self)
        self.name_edit.setPlaceholderText("请输入网站名称（可选，留空自动获取）")
        self.name_edit.setClearButtonEnabled(True)
        self.name_edit.returnPressed.connect(lambda: self.yesButton.click())
        self.viewLayout.addWidget(self.name_edit)

        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(400)

        self.url_edit.setFocus()

    def get_url(self) -> str:
        return self.url_edit.text().strip()

    def get_name(self) -> str:
        return self.name_edit.text().strip()

    def validate(self) -> bool:
        return bool(self.get_url())


class BookmarkWidget(QWidget):
    """书签管理界面"""
    
    PLUGIN_ID = "bookmark"
    
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.service = BookmarkService(self.PLUGIN_ID)
        self._current_category_id = None
        self._current_category_name = "全部"
        self._category_buttons = []
        self._fetcher: Optional[WebsiteInfoFetcher] = None
        self._batch_mode = False
        self._init_paths()
        self._setup_ui()
        self._setup_event_listeners()

    def _setup_event_listeners(self) -> None:
        """设置事件监听器"""
        if hasattr(self, 'core') and self.core and hasattr(self.core, 'event_bus'):
            self.core.event_bus.listen("data_restored", lambda _: self._on_data_restored())

    def _on_data_restored(self) -> None:
        """数据恢复后刷新"""
        self.load_data()
    
    def _init_paths(self) -> None:
        """初始化路径"""
        self.icons_dir = get_app_data_path("data/icons")
        self.icons_dir.mkdir(parents=True, exist_ok=True)
    
    def _setup_ui(self) -> None:
        """构建界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)
        
        self.setObjectName("bookmarkView")
        setCustomStyleSheet(
            self,
            "QWidget#bookmarkView { background-color: transparent; }",
            "QWidget#bookmarkView { background-color: transparent; }"
        )
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.add_btn = PushButton("添加", self)
        self.add_btn.setIcon(FIF.ADD)
        self.add_btn.clicked.connect(self._show_add_dialog)
        header_layout.addWidget(self.add_btn)

        self.search_edit = LineEdit(self)
        self.search_edit.setPlaceholderText("搜索...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._filter_websites)
        self.search_edit.setFixedWidth(150)
        header_layout.addWidget(self.search_edit)

        self.url_edit = LineEdit(self)
        self.url_edit.setPlaceholderText("输入网址，按回车添加...")
        self.url_edit.setClearButtonEnabled(True)
        self.url_edit.returnPressed.connect(self._on_url_return_pressed)
        header_layout.addWidget(self.url_edit, 1)
        
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

        self.scroll_area = SingleDirectionScrollArea(self, orient=Qt.Horizontal)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFixedHeight(36)

        scroll_content = QWidget()
        scroll_content.setObjectName("categoryContent")
        setCustomStyleSheet(
            scroll_content,
            "QWidget#categoryContent { background-color: transparent; }",
            "QWidget#categoryContent { background-color: transparent; }"
        )
        self.category_layout = QHBoxLayout(scroll_content)
        self.category_layout.setContentsMargins(5, 2, 5, 2)
        self.category_layout.setSpacing(4)
        self.category_layout.setAlignment(Qt.AlignLeft)
        self.scroll_area.setWidget(scroll_content)
        self.scroll_area.enableTransparentBackground()
        self.scroll_area.viewport().setAutoFillBackground(False)
        self.scroll_area.viewport().setStyleSheet("background: transparent;")

        setCustomStyleSheet(
            self.scroll_area,
            """
            QScrollArea { background-color: transparent; border: none; }
            QScrollArea > QWidget > QWidget { background-color: transparent; }
            """,
            """
            QScrollArea { background-color: transparent; border: none; }
            QScrollArea > QWidget > QWidget { background-color: transparent; }
            """
        )
        layout.addWidget(self.scroll_area)

        self.all_btn = PushButton("全部", self)
        self.all_btn.clicked.connect(self._show_all)
        self.category_layout.addWidget(self.all_btn)

        self.add_category_btn = TransparentToolButton(FIF.ADD, self)
        self.add_category_btn.setToolTip("添加分类")
        self.add_category_btn.clicked.connect(self._add_category)
        self.category_layout.addWidget(self.add_category_btn)
        self.category_layout.addStretch()

        self.scroll_area.wheelEvent = self._on_category_wheel_event

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
        
        categories = self.service.list_categories()
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
        
        menu = RoundMenu(parent=self)
        
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
                    self.service.rename_category(category['id'], new_name)
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
    
    def _on_category_wheel_event(self, event):
        """处理分类区域的滚轮事件"""
        from PyQt5.QtCore import QPoint
        h_scrollbar = self.scroll_area.horizontalScrollBar()
        if h_scrollbar:
            delta = event.angleDelta().y()
            if delta != 0:
                h_scrollbar.setValue(h_scrollbar.value() - delta)
                event.accept()
                return
        from qfluentwidgets import SingleDirectionScrollArea
        SingleDirectionScrollArea.wheelEvent(self.scroll_area, event)

    def _delete_category(self, category: dict) -> None:
        """删除分类"""
        box = MessageBox("删除分类", f"确定要删除分类 '{category['name']}' 吗？\n该分类下的书签将移至\"全部\"分类。", self)
        if box.exec():
            self.service.delete_category(category['id'])
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
            if hasattr(self, 'core') and self.core and hasattr(self.core, 'logger'):
                self.core.logger.log_operation("DELETE", f"删除分类: {category['name']}")
    
    def _load_bookmarks(self) -> None:
        """加载书签列表"""
        self.tree.clear()
        bookmarks = self.service.list_bookmarks(self._current_category_id)
        
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
        """应用树形列表样式"""
        if not hasattr(self, "tree"):
            return

        header = self.tree.header()
        if isDarkTheme():
            header.setStyleSheet(
                "QHeaderView { background-color: transparent; }"
                "QHeaderView::section { background-color: #1f1f1f; color: #dddddd; border: none; padding: 4px 6px; }"
            )
            self.tree.setStyleSheet(
                "QTreeWidget { background-color: transparent; alternate-background-color: #252525; }"
                "QTreeWidget::item { padding: 3px; }"
                "QTreeWidget::item:selected { background-color: #0078d4; color: white; }"
            )
        else:
            header.setStyleSheet(
                "QHeaderView { background-color: transparent; }"
                "QHeaderView::section { background-color: #f5f5f5; color: #202020; border: none; padding: 4px 6px; }"
            )
            self.tree.setStyleSheet(
                "QTreeWidget { background-color: transparent; alternate-background-color: #f0f0f0; }"
                "QTreeWidget::item { padding: 3px; }"
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
        
        url = self.service.normalize_url(url)
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
    
    def _show_add_dialog(self) -> None:
        """显示添加书签对话框"""
        dialog = AddBookmarkDialog(parent=self)
        if dialog.exec():
            url = dialog.get_url()
            name = dialog.get_name()

            if not url:
                return

            url = self.service.normalize_url(url)
            if not url:
                InfoBar.warning(
                    title="输入错误",
                    content="请输入有效的网站地址",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return

            if not name:
                name = QUrl(url).host() or url

            self._add_bookmark_with_name(url, name)

    def _add_bookmark_with_name(self, url: str, name: str) -> None:
        """使用指定名称添加书签"""
        category_name = self._current_category_name if self._current_category_name != "全部" else None

        self.service.add_bookmark(
            name=name,
            url=url,
            category_name=category_name,
            icon="",
            notes=""
        )

        self.load_data()

        InfoBar.success(
            title="添加成功",
            content=f"已添加书签: {name}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

        if hasattr(self, 'core') and self.core and hasattr(self.core, 'logger'):
            self.core.logger.log_operation("CREATE", f"添加书签: {name} ({url})")

    def _add_website(self) -> None:
        """添加网站（右键菜单用）"""
        dialog = InputDialog("添加网站", "请输入网站URL", parent=self)
        if dialog.exec():
            url = dialog.get_text()
            if not url:
                return

            url = self.service.normalize_url(url)
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

        InfoBar.warning(
            title="获取失败",
            content=f"无法获取 {url} 的信息，书签已使用默认名称添加",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=4000,
            parent=self
        )

        self._add_bookmark_with_name(
            url=url,
            name=QUrl(url).host() or url,
        )

        if self._fetcher:
            self._fetcher.deleteLater()
            self._fetcher = None
    
    def _on_fetch_finished(self, url: str, title: str, icon_path: str) -> None:
        """网站信息获取完成"""
        self.progress_bar.setVisible(False)
        self._set_ui_enabled(True)

        dialog = InputDialog("备注", "请输入备注（可选）", parent=self, validator=lambda t: True)
        notes = ""
        if dialog.exec():
            notes = dialog.get_text()

        category_name = self._current_category_name if self._current_category_name != "全部" else None

        self.service.add_bookmark(
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

        if hasattr(self, 'core') and self.core and hasattr(self.core, 'logger'):
            self.core.logger.log_operation("CREATE", f"添加书签: {title} ({url})")

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

            self.service.add_category(name)
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
            if hasattr(self, 'core') and self.core and hasattr(self.core, 'logger'):
                self.core.logger.log_operation("CREATE", f"添加分类: {name}")
    
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
        
        menu = RoundMenu(parent=self)
        
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
        
        move_menu = RoundMenu("移动分类", self)
        menu.addMenu(move_menu)
        current_cat = item.text(2) if item.columnCount() > 2 else ""
        all_categories = self.service.list_categories()
        for cat in all_categories:
            if cat['name'] == current_cat:
                continue
            cat_action = QAction(cat['name'], self)
            cat_action.triggered.connect(partial(self._move_bookmark, item, cat['id']))
            move_menu.addAction(cat_action)
        if move_menu.isEmpty():
            move_menu.setEnabled(False)
        
        menu.addSeparator()
        
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(partial(self._delete_bookmark, item))
        menu.addAction(delete_action)
        
        menu.exec_(self.tree.viewport().mapToGlobal(pos))
    
    def _move_bookmark(self, item: QTreeWidgetItem, new_category_id: int) -> None:
        """移动书签到指定分类"""
        bm_id = item.data(0, Qt.UserRole)
        name = item.text(0)
        
        self.service.update_bookmark(bm_id, category_id=new_category_id)
        self._load_bookmarks()
        
        InfoBar.success(
            title="移动成功",
            content=f"已将 '{name}' 移动到新分类",
            orient=Qt.Horizontal, isClosable=True,
            position=InfoBarPosition.TOP, duration=2000, parent=self
        )
        if hasattr(self, 'core') and self.core and hasattr(self.core, 'logger'):
            self.core.logger.log_operation("UPDATE", f"移动书签 '{name}' 到分类ID: {new_category_id}")
    
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

        url = self.service.normalize_url(url)
        self.service.update_bookmark(bm_id, name=name, url=url)
        self._load_bookmarks()

        if hasattr(self, 'core') and self.core and hasattr(self.core, 'logger'):
            self.core.logger.log_operation("UPDATE", f"编辑书签: {item.text(0)} -> {name}")
    
    def _edit_notes(self, item: QTreeWidgetItem) -> None:
        """编辑备注"""
        bm_id = item.data(0, Qt.UserRole)
        dialog = InputDialog("编辑备注", "备注:", default_text=item.text(3), parent=self)
        if not dialog.exec():
            return
        notes = dialog.get_text()
        
        self.service.update_bookmark(bm_id, notes=notes)
        item.setText(3, notes)
    
    def _set_icon(self, item: QTreeWidgetItem) -> None:
        """设置图标"""
        import shutil
        
        bm_id = item.data(0, Qt.UserRole)
        url = item.text(1)
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图标文件", "",
            "图片文件 (*.png *.ico *.jpg *.svg);;所有文件 (*)"
        )
        
        if not file_path:
            return
        
        domain = QUrl(url).host() or str(bm_id)
        ext = os.path.splitext(file_path)[1]
        icon_filename = f"{domain}{ext}"
        icon_path = self.icons_dir / icon_filename
        
        shutil.copy2(file_path, icon_path)
        
        relative_path = f"data/icons/{icon_filename}"
        self.service.update_bookmark(bm_id, icon=relative_path)
        
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
            self.service.delete_bookmark(bm_id)
            self._load_bookmarks()
            if hasattr(self, 'core') and self.core and hasattr(self.core, 'logger'):
                self.core.logger.log_operation("DELETE", f"删除书签: {name}")
    
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
            bm_ids = [item.data(0, Qt.UserRole) for item in selected_items]
            deleted_names = [item.text(0) for item in selected_items]
            self.service.batch_delete_bookmarks(bm_ids)

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

            if hasattr(self, 'core') and self.core and hasattr(self.core, 'logger'):
                names_str = ", ".join(deleted_names[:5])
                if len(deleted_names) > 5:
                    names_str += f" 等共{len(deleted_names)}个"
                self.core.logger.log_operation("DELETE", f"批量删除书签: {names_str}")
