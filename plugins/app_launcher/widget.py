"""应用启动主组件"""
import os
import sys
import json
import re
import subprocess
from typing import List, Dict, Any, Optional, Set

from PyQt5.QtCore import Qt, QSize, QTimer, QFileInfo
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QFileDialog, QFileIconProvider,
    QTabWidget, QAction, QScrollArea,
)
from qfluentwidgets import (
    PushButton, LineEdit, FluentIcon as FIF,
    InfoBar, InfoBarPosition, TransparentToolButton,
    MessageBox, isDarkTheme, ComboBox, qconfig, RoundMenu,
)

from core import get_app_data_path
from plugins.app_launcher.service import AppLauncherService

from . import (
    GRID_VIEW, LIST_VIEW, DEFAULT_ICON_SIZE,
    get_non_transparent_rect, normalize_search_text,
    score_search_match, highlight_text,
    get_menu_style,
)
from .utils import get_python_executable, get_plugins_sourcecode_dir
from .tab_bar import CustomTabBar
from .dialogs import AppEditDialog, BatchMoveDialog, BatchEditDialog, CategoryEditDialog
from .category_tab import CategoryTab


class AppLauncherWidget(QWidget):
    """应用启动组件"""

    PLUGIN_ID = "app_launcher"

    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.service = AppLauncherService(self.PLUGIN_ID)
        self.category_tabs = {}  # 缓存标签页
        self.selected_app_ids: Set[int] = set()
        self.batch_mode = False
        self._current_sort_by = "sort_order"
        self._ignore_tab_move = False
        self._running_py_processes: Dict[str, 'QProcess'] = {}
        self._init_paths()
        self._load_view_preferences()
        self._init_scroll_buttons()
        self._setup_ui()
        self._apply_styles()

        # 监听主题变化
        qconfig.themeChangedFinished.connect(self._on_theme_changed)

    def _init_scroll_buttons(self):
        """初始化滚动按钮"""
        self._up_btn = PushButton("", self)
        self._up_btn.setIcon(FIF.CARE_UP_SOLID)
        self._up_btn.setFixedSize(48, 24)
        self._up_btn.setCursor(Qt.PointingHandCursor)
        self._up_btn.hide()
        self._up_btn.clicked.connect(self._scroll_up)

        self._down_btn = PushButton("", self)
        self._down_btn.setIcon(FIF.CARE_DOWN_SOLID)
        self._down_btn.setFixedSize(48, 24)
        self._down_btn.setCursor(Qt.PointingHandCursor)
        self._down_btn.hide()
        self._down_btn.clicked.connect(self._scroll_down)

    def _scroll_up(self):
        current_tab = self.tab_widget.currentWidget()
        if current_tab and isinstance(current_tab, QScrollArea):
            bar = current_tab.verticalScrollBar()
            bar.setValue(bar.value() - 100)

    def _scroll_down(self):
        current_tab = self.tab_widget.currentWidget()
        if current_tab and isinstance(current_tab, QScrollArea):
            bar = current_tab.verticalScrollBar()
            bar.setValue(bar.value() + 100)

    def _check_scroll_buttons(self):
        """检查并更新滚动按钮显示"""
        current_tab = self.tab_widget.currentWidget()
        if not current_tab or not isinstance(current_tab, QScrollArea):
            self._up_btn.hide()
            self._down_btn.hide()
            return

        scroll_area = current_tab
        widget_height = scroll_area.widget().height() if scroll_area.widget() else 0
        viewport_height = scroll_area.viewport().height()

        if widget_height > viewport_height:
            bar = scroll_area.verticalScrollBar()
            self._up_btn.setVisible(bar.value() > 0)
            self._down_btn.setVisible(bar.value() < bar.maximum())
        else:
            self._up_btn.hide()
            self._down_btn.hide()

    def _on_tab_changed(self, index):
        """标签页切换时检查滚动按钮"""
        self._check_scroll_buttons()

    def _init_paths(self):
        """初始化路径"""
        self.icon_dir = get_app_data_path("data/app_icons")
        self.icon_dir.mkdir(parents=True, exist_ok=True)
        self.view_settings_path = get_app_data_path("data/app_launcher_view.json")

    def _load_view_preferences(self) -> None:
        """加载视图偏好"""
        self.view_mode = GRID_VIEW
        self.icon_size = DEFAULT_ICON_SIZE

        if not self.view_settings_path.exists():
            return

        try:
            data = json.loads(self.view_settings_path.read_text(encoding="utf-8"))
        except Exception:
            return

        self.view_mode = data.get("view_mode", GRID_VIEW)
        self.icon_size = int(data.get("icon_size", DEFAULT_ICON_SIZE) or DEFAULT_ICON_SIZE)

    def _save_view_preferences(self) -> None:
        """保存视图偏好"""
        try:
            self.view_settings_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "view_mode": self.view_mode,
                "icon_size": self.icon_size,
            }
            self.view_settings_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            self.core.logger.warning(f"保存应用视图偏好失败: {e}")

    def _configure_tab_display(self, tab: CategoryTab) -> None:
        """向标签页同步显示参数"""
        tab.set_display_options(
            self.view_mode,
            self.icon_size,
            self.batch_mode,
            self.selected_app_ids,
            self.search_input.text().strip() if hasattr(self, "search_input") else "",
        )

    def _refresh_all_tabs(self) -> None:
        """刷新所有标签页内容"""
        for category_id, tab in self.category_tabs.items():
            if not isinstance(tab, CategoryTab):
                continue
            self._configure_tab_display(tab)
            tab.refresh_apps(self._get_display_apps(category_id))
        self._update_batch_controls()
        self._check_scroll_buttons()

    def _get_display_apps(self, category_id) -> List[Dict[str, Any]]:
        """获取指定标签页的显示数据"""
        if category_id == "recent":
            apps = self._get_recent_apps()
        elif category_id == "favorite":
            apps = self._get_favorite_apps()
        else:
            apps = self.service.list_apps(category_id if isinstance(category_id, int) else None)

        apps = self._sort_app_list(apps, self._current_sort_by)
        keyword = self.search_input.text().strip() if hasattr(self, "search_input") else ""
        return self._search_apps_advanced(apps, keyword)

    def _sort_app_list(self, apps: List[Dict[str, Any]], sort_by: str) -> List[Dict[str, Any]]:
        """排序应用列表"""
        app_items = list(apps)
        if sort_by == 'name':
            app_items.sort(key=lambda x: x.get('name', '').lower())
        elif sort_by == 'created_at':
            app_items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        elif sort_by == 'updated_at':
            app_items.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        elif sort_by == 'launch_count':
            app_items.sort(key=lambda x: x.get('launch_count', 0), reverse=True)
        elif sort_by == 'last_launch_time':
            app_items.sort(key=lambda x: x.get('last_launch_time', ''), reverse=True)
        else:
            app_items.sort(key=lambda x: (x.get('sort_order', 0), x.get('id', 0)))
        return app_items

    def _search_apps_advanced(self, apps: List[Dict[str, Any]], keyword: str) -> List[Dict[str, Any]]:
        """执行增强搜索"""
        normalized_keyword = normalize_search_text(keyword)
        if not normalized_keyword:
            return list(apps)

        matched_apps = []
        for app in apps:
            score_value, match_mode = score_search_match(keyword, app)
            if score_value < 40:
                continue

            item = dict(app)
            item["_search_score"] = score_value
            item["_search_mode"] = match_mode
            item["_display_name_html"] = highlight_text(item.get("name", ""), keyword)
            subtitle_parts = [item.get("target_path", "")]
            notes = item.get("notes", "").strip()
            if notes:
                subtitle_parts.append(notes)
            item["_display_subtitle_html"] = highlight_text(" | ".join(filter(None, subtitle_parts)), keyword)
            matched_apps.append(item)

        matched_apps.sort(
            key=lambda item: (
                -item.get("_search_score", 0),
                -item.get("launch_count", 0),
                item.get("name", "").lower()
            )
        )
        return matched_apps

    def _get_selected_apps(self) -> List[Dict[str, Any]]:
        """获取已选中的应用"""
        if not self.selected_app_ids:
            return []

        apps = self.service.list_apps()
        return [app for app in apps if app.get("id") in self.selected_app_ids]

    def _on_card_selection_changed(self, app_id: int, selected: bool) -> None:
        """处理卡片选择变化"""
        if selected:
            self.selected_app_ids.add(app_id)
        else:
            self.selected_app_ids.discard(app_id)
        self._update_batch_controls()

    def _update_batch_controls(self) -> None:
        """更新批量操作按钮状态"""
        selected_count = len(self.selected_app_ids)
        if hasattr(self, "batch_btn"):
            self.batch_btn.setText(f"批量模式 ({selected_count})" if self.batch_mode else "批量模式")
        for attr_name in ("batch_delete_btn", "batch_move_btn", "batch_edit_btn", "batch_select_current_btn", "batch_clear_btn"):
            button = getattr(self, attr_name, None)
            if button is not None:
                button.setVisible(self.batch_mode)
        for attr_name in ("batch_delete_btn", "batch_move_btn", "batch_edit_btn", "batch_clear_btn"):
            button = getattr(self, attr_name, None)
            if button is not None:
                button.setEnabled(selected_count > 0)

    def _set_batch_mode(self, enabled: bool) -> None:
        """设置批量模式"""
        self.batch_mode = enabled
        if not enabled:
            self.selected_app_ids.clear()
        self._refresh_all_tabs()

    def _toggle_batch_mode(self) -> None:
        """切换批量模式"""
        self._set_batch_mode(not self.batch_mode)

    def _clear_selection(self) -> None:
        """清空当前选择"""
        self.selected_app_ids.clear()
        self._refresh_all_tabs()

    def _select_current_tab_apps(self) -> None:
        """全选当前页应用"""
        current_tab = self.tab_widget.currentWidget()
        if not isinstance(current_tab, CategoryTab):
            return

        current_ids = [app.get("id") for app in current_tab._apps if app.get("id") is not None]
        self.selected_app_ids.update(current_ids)
        self._refresh_all_tabs()

    def _setup_ui(self):
        """构建界面"""
        self.setObjectName("appLauncherWidget")

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 搜索区域
        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)
        search_layout.setContentsMargins(20, 20, 20, 10)

        self.search_input = LineEdit(self)
        self.search_input.setPlaceholderText("搜索应用...")
        self.search_input.setClearButtonEnabled(True)

        # 搜索延迟
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)
        self.search_input.textChanged.connect(lambda: self.search_timer.start(200))

        # 排序按钮
        self.sort_btn = PushButton("排序", self)
        self.sort_btn.setIcon(FIF.ARROW_DOWN)
        self.sort_btn.setFixedWidth(80)
        self.sort_btn.clicked.connect(self._show_sort_menu)

        self.view_combo = ComboBox(self)
        self.view_combo.addItems(["网格视图", "列表视图"])
        self.view_combo.setCurrentIndex(0 if self.view_mode == GRID_VIEW else 1)
        self.view_combo.currentIndexChanged.connect(self._on_view_mode_changed)

        self.icon_size_combo = ComboBox(self)
        self.icon_size_combo.addItems(["小图标", "中图标", "大图标"])
        self.icon_size_combo.setCurrentIndex({20: 0, 24: 1, 32: 2}.get(self.icon_size, 1))
        self.icon_size_combo.currentIndexChanged.connect(self._on_icon_size_changed)

        self.batch_btn = PushButton("批量模式", self)
        self.batch_btn.setIcon(FIF.EDIT)
        self.batch_btn.clicked.connect(self._toggle_batch_mode)

        self.batch_select_current_btn = PushButton("全选当前页", self)
        self.batch_select_current_btn.clicked.connect(self._select_current_tab_apps)

        self.batch_clear_btn = PushButton("清空选择", self)
        self.batch_clear_btn.clicked.connect(self._clear_selection)

        self.batch_move_btn = PushButton("批量移动", self)
        self.batch_move_btn.clicked.connect(self._batch_move_selected)

        self.batch_edit_btn = PushButton("批量修改", self)
        self.batch_edit_btn.clicked.connect(self._batch_edit_selected)

        self.batch_delete_btn = PushButton("批量删除", self)
        self.batch_delete_btn.clicked.connect(self._batch_delete_selected)

        scan_btn = PushButton("扫描应用", self)
        scan_btn.setIcon(FIF.SEARCH)
        scan_btn.clicked.connect(self._scan_apps)

        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.sort_btn)
        search_layout.addWidget(self.view_combo)
        search_layout.addWidget(self.icon_size_combo)
        search_layout.addWidget(self.batch_btn)
        search_layout.addWidget(self.batch_select_current_btn)
        search_layout.addWidget(self.batch_clear_btn)
        search_layout.addWidget(self.batch_move_btn)
        search_layout.addWidget(self.batch_edit_btn)
        search_layout.addWidget(self.batch_delete_btn)
        search_layout.addWidget(scan_btn)

        # 向上滚动按钮
        self._up_btn_container = QWidget()
        self._up_btn_container.setObjectName("scrollBtnContainer")
        up_layout = QHBoxLayout(self._up_btn_container)
        up_layout.setContentsMargins(0, 0, 0, 0)
        up_layout.addStretch()
        up_layout.addWidget(self._up_btn)

        # 标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.setDocumentMode(True)

        # 使用自定义 TabBar
        custom_tab_bar = CustomTabBar(self)
        custom_tab_bar.category_context_menu_requested.connect(self._show_category_menu)
        custom_tab_bar.setMovable(True)
        custom_tab_bar.tabMoved.connect(self._on_category_tab_moved)
        self.tab_widget.setTabBar(custom_tab_bar)

        # 向下滚动按钮
        self._down_btn_container = QWidget()
        self._down_btn_container.setObjectName("scrollBtnContainer")
        down_layout = QHBoxLayout(self._down_btn_container)
        down_layout.setContentsMargins(0, 0, 0, 0)
        down_layout.addStretch()
        down_layout.addWidget(self._down_btn)

        # 添加到主布局
        main_layout.addLayout(search_layout)
        main_layout.addWidget(self._up_btn_container)
        main_layout.addWidget(self.tab_widget, 1)
        main_layout.addWidget(self._down_btn_container)

        # 连接标签页切换信号
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        self._update_batch_controls()

    def _apply_styles(self):
        """应用样式"""
        # 为整个组件设置背景
        if isDarkTheme():
            self.setStyleSheet("""
                QWidget#appLauncherWidget {
                    background-color: #1a1a1a;
                }
                QWidget#scrollBtnContainer {
                    background-color: transparent;
                }
                QTabWidget::pane {
                    border: none;
                    background-color: #1a1a1a;
                }
                QTabWidget::tab-bar {
                    background-color: #1a1a1a;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget#appLauncherWidget {
                    background-color: #f5f5f5;
                }
                QWidget#scrollBtnContainer {
                    background-color: transparent;
                }
                QTabWidget::pane {
                    border: none;
                    background-color: #f5f5f5;
                }
                QTabWidget::tab-bar {
                    background-color: #f5f5f5;
                }
            """)

        # 确保 corner widget 可见
        corner_widget = self.tab_widget.cornerWidget()
        if corner_widget:
            corner_widget.setVisible(True)
            corner_widget.raise_()

        # 为已存在的标签页应用样式
        for tab in self.category_tabs.values():
            if isinstance(tab, CategoryTab):
                tab._apply_style()

        # 刷新自定义 TabBar
        if hasattr(self.tab_widget, 'tabBar'):
            self.tab_widget.tabBar().update()

    def _on_theme_changed(self):
        """主题变化时更新样式"""
        QTimer.singleShot(0, self._refresh_theme_styles)

    def _refresh_theme_styles(self):
        """延迟刷新主题样式，避免阻塞全局主题切换"""
        self._apply_styles()
        self._refresh_all_tabs()

    def load_data(self) -> None:
        """加载应用数据"""
        self._scan_plugins_sourcecode()
        self._load_categories()

    def _scan_plugins_sourcecode(self) -> None:
        """扫描 plugins_sourcecode 目录，自动添加 .py 文件到'源码工具'分类"""
        source_dir = get_plugins_sourcecode_dir()
        if not source_dir.exists():
            return

        # 获取或创建"源码工具"分类
        cat_id = self.service.get_or_create_category("源码工具")

        # 获取已有应用的路径集合，避免重复添加
        existing_apps = self.service.list_apps(cat_id)
        existing_paths = {app.get('target_path', '') for app in existing_apps}

        # 扫描 .py 文件
        py_files = list(source_dir.glob("*.py"))
        added_count = 0
        for py_file in py_files:
            file_path = str(py_file)
            if file_path in existing_paths:
                continue

            name = py_file.stem.replace("_", " ").title()
            icon_path = self._extract_icon(file_path)

            self.service.add_app(
                name=name,
                target_path=file_path,
                category_id=cat_id,
                icon_path=icon_path
            )
            added_count += 1

        if added_count > 0:
            if hasattr(self, 'core') and self.core and hasattr(self.core, 'logger'):
                self.core.logger.info(f"已自动添加 {added_count} 个源码工具应用")

    def _load_categories(self):
        """加载分类"""
        current_tab_key = None
        current_index = self.tab_widget.currentIndex()
        if current_index >= 0:
            current_tab_key = self.tab_widget.tabBar().tabData(current_index)

        self.tab_widget.clear()
        self.category_tabs.clear()
        tab_bar = self.tab_widget.tabBar()
        if isinstance(tab_bar, CustomTabBar):
            tab_bar.clear_category_meta()

        categories = self.service.list_categories()

        # 创建"全部"标签页
        all_tab = CategoryTab(None, self)
        all_tab.app_clicked.connect(self._launch_app)
        all_tab.app_deleted.connect(self._delete_app)
        all_tab.app_edited.connect(self._edit_app)
        all_tab.app_favorited.connect(self._toggle_favorite)
        all_tab.add_app_clicked.connect(self._add_app)
        all_tab.app_selection_changed.connect(self._on_card_selection_changed)
        all_tab_index = self.tab_widget.addTab(all_tab, "全部")
        self.tab_widget.tabBar().setTabData(all_tab_index, None)
        self.category_tabs[None] = all_tab

        # 创建"最近使用"标签页
        recent_tab = CategoryTab('recent', self)
        recent_tab.app_clicked.connect(self._launch_app)
        recent_tab.app_deleted.connect(self._delete_app)
        recent_tab.app_edited.connect(self._edit_app)
        recent_tab.app_favorited.connect(self._toggle_favorite)
        recent_tab.add_app_clicked.connect(self._add_app)
        recent_tab.app_selection_changed.connect(self._on_card_selection_changed)
        recent_tab_index = self.tab_widget.addTab(recent_tab, "最近使用")
        self.tab_widget.tabBar().setTabData(recent_tab_index, 'recent')
        self.category_tabs['recent'] = recent_tab

        # 创建"收藏"标签页
        favorite_tab = CategoryTab('favorite', self)
        favorite_tab.app_clicked.connect(self._launch_app)
        favorite_tab.app_deleted.connect(self._delete_app)
        favorite_tab.app_edited.connect(self._edit_app)
        favorite_tab.app_favorited.connect(self._toggle_favorite)
        favorite_tab.add_app_clicked.connect(self._add_app)
        favorite_tab.app_selection_changed.connect(self._on_card_selection_changed)
        favorite_tab_index = self.tab_widget.addTab(favorite_tab, "收藏")
        self.tab_widget.tabBar().setTabData(favorite_tab_index, 'favorite')
        self.category_tabs['favorite'] = favorite_tab

        # 创建分类标签页
        for category in categories:
            tab = CategoryTab(category['id'], self)
            tab.app_clicked.connect(self._launch_app)
            tab.app_deleted.connect(self._delete_app)
            tab.app_edited.connect(self._edit_app)
            tab.app_favorited.connect(self._toggle_favorite)
            tab.add_app_clicked.connect(lambda cat_id=category['id']: self._add_app(cat_id))
            tab.app_selection_changed.connect(self._on_card_selection_changed)
            tab_index = self.tab_widget.addTab(tab, category['name'])
            self.tab_widget.tabBar().setTabData(tab_index, category['id'])
            if isinstance(tab_bar, CustomTabBar):
                tab_bar.set_category_meta(tab_index, category)
            self.category_tabs[category['id']] = tab

        # 添加分类按钮
        add_btn = TransparentToolButton(FIF.ADD, self)
        add_btn.setFixedSize(32, 32)
        add_btn.clicked.connect(self._add_category)
        self.tab_widget.setCornerWidget(add_btn)

        # 应用样式
        self._apply_styles()
        self._refresh_all_tabs()

        if current_tab_key in self.category_tabs:
            for index in range(self.tab_widget.count()):
                if self.tab_widget.tabBar().tabData(index) == current_tab_key:
                    self.tab_widget.setCurrentIndex(index)
                    break

    def _add_category(self):
        """添加分类"""
        dialog = CategoryEditDialog("添加分类", parent=self)
        if dialog.exec():
            data = dialog.get_data()
            name = data.get("name", "")
            if name:
                existing_categories = [cat.get("name") for cat in self.service.list_categories()]
                if name not in existing_categories:
                    category_id = self.service.add_category(name)
                    self.service.update_category(
                        category_id,
                        icon_name=data.get("icon_name", ""),
                        color=data.get("color", "")
                    )
                    self._load_categories()
                else:
                    InfoBar.warning(
                        title="警告",
                        content="该分类已存在！",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )

    def _show_category_menu(self, category_id: int, pos):
        """显示分类右键菜单"""
        menu = RoundMenu(parent=self)

        edit_action = QAction("编辑分类", self)
        edit_action.triggered.connect(lambda: self._edit_category(category_id))
        menu.addAction(edit_action)

        move_left_action = QAction("左移分类", self)
        move_left_action.triggered.connect(lambda: self._move_category_tab(category_id, -1))
        menu.addAction(move_left_action)

        move_right_action = QAction("右移分类", self)
        move_right_action.triggered.connect(lambda: self._move_category_tab(category_id, 1))
        menu.addAction(move_right_action)

        delete_action = QAction("删除分类", self)
        delete_action.triggered.connect(lambda: self._delete_category(category_id))
        menu.addAction(delete_action)

        menu.exec_(pos)

    def _edit_category(self, category_id: int):
        """编辑分类"""
        categories = self.service.list_categories()
        current_category = self._find_category_by_id(category_id)
        if current_category is None:
            return

        dialog = CategoryEditDialog("编辑分类", current_category, self)
        if dialog.exec():
            data = dialog.get_data()
            new_name = data.get("name", "")
            if not new_name:
                return

            existing_categories = [
                cat.get("name") for cat in categories
                if cat.get("id") != category_id
            ]
            if new_name in existing_categories:
                InfoBar.warning(
                    title="警告",
                    content="该分类名称已存在！",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return

            self.service.update_category(
                category_id,
                name=new_name,
                icon_name=data.get("icon_name", ""),
                color=data.get("color", "")
            )
            self._load_categories()
            InfoBar.success(
                title="修改成功",
                content=f"分类已更新为 {new_name}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def _find_category_by_id(self, category_id: int) -> Optional[Dict[str, Any]]:
        """根据 ID 查找分类"""
        return self.service.get_category(category_id)

    def _on_category_tab_moved(self, from_index: int, to_index: int) -> None:
        """处理分类拖拽排序"""
        if self._ignore_tab_move:
            return

        if from_index < 3 or to_index < 3:
            self._ignore_tab_move = True
            self.tab_widget.tabBar().moveTab(to_index, from_index)
            self._ignore_tab_move = False
            return

        category_ids = []
        for index in range(3, self.tab_widget.count()):
            category_id = self.tab_widget.tabBar().tabData(index)
            if isinstance(category_id, int):
                category_ids.append(category_id)
        self.service.update_category_sort_orders(category_ids)
        self._load_categories()

    def _move_category_tab(self, category_id: int, step: int) -> None:
        """通过菜单移动分类顺序"""
        tab_bar = self.tab_widget.tabBar()
        current_index = next(
            (index for index in range(self.tab_widget.count()) if tab_bar.tabData(index) == category_id),
            -1
        )
        if current_index < 3:
            return

        target_index = current_index + step
        if target_index < 3 or target_index >= self.tab_widget.count():
            return

        self._ignore_tab_move = True
        tab_bar.moveTab(current_index, target_index)
        self._ignore_tab_move = False
        self._on_category_tab_moved(current_index, target_index)

    def _delete_category(self, category_id: int):
        """删除分类"""
        category = self.service.get_category(category_id)
        category_name = category['name'] if category else ""

        box = MessageBox("删除分类", f"确定要删除分类 '{category_name}' 吗？\n该分类下的应用将移至\"全部\"分类。", self)
        if box.exec():
            apps = self.service.list_apps(category_id)
            for app in apps:
                icon_path = app.get('icon_path', '')
                if icon_path:
                    abs_icon_path = get_app_data_path(icon_path)
                    if abs_icon_path.exists():
                        try:
                            abs_icon_path.unlink()
                        except Exception:
                            pass

            self.service.delete_category(category_id)
            self._load_categories()

            InfoBar.success(
                title="删除成功",
                content=f"已删除分类 {category_name}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def _on_view_mode_changed(self, index: int) -> None:
        """切换视图模式"""
        self.view_mode = GRID_VIEW if index == 0 else LIST_VIEW
        self._save_view_preferences()
        self._refresh_all_tabs()

    def _on_icon_size_changed(self, index: int) -> None:
        """切换图标尺寸"""
        icon_size_map = {0: 20, 1: 24, 2: 32}
        self.icon_size = icon_size_map.get(index, DEFAULT_ICON_SIZE)
        self._save_view_preferences()
        self._refresh_all_tabs()

    def _batch_move_selected(self) -> None:
        """批量移动应用分类"""
        selected_apps = self._get_selected_apps()
        if not selected_apps:
            return

        categories = self.service.list_categories()
        dialog = BatchMoveDialog(categories, self)
        if not dialog.exec():
            return

        category_id = dialog.get_category_id(categories)
        updated_count = self.service.batch_update_apps(
            list(self.selected_app_ids),
            category_id=category_id
        )
        self._refresh_all_tabs()
        InfoBar.success(
            title="批量移动完成",
            content=f"已更新 {updated_count} 个应用的分类",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def _batch_edit_selected(self) -> None:
        """批量修改应用属性"""
        if not self.selected_app_ids:
            return

        dialog = BatchEditDialog(self)
        if not dialog.exec():
            return

        updates = dialog.get_updates()
        if not updates:
            InfoBar.info(
                title="未修改",
                content="没有填写任何需要批量修改的内容",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1500,
                parent=self
            )
            return

        updated_count = self.service.batch_update_apps(
            list(self.selected_app_ids),
            **updates
        )
        self._refresh_all_tabs()
        InfoBar.success(
            title="批量修改完成",
            content=f"已更新 {updated_count} 个应用",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def _batch_delete_selected(self) -> None:
        """批量删除应用"""
        selected_apps = self._get_selected_apps()
        if not selected_apps:
            return

        box = MessageBox("批量删除", f"确定要删除选中的 {len(selected_apps)} 个应用吗？", self)
        if not box.exec():
            return

        for app in selected_apps:
            icon_path = app.get("icon_path", "")
            if not icon_path:
                continue
            abs_icon_path = get_app_data_path(icon_path)
            if not abs_icon_path.exists():
                continue
            try:
                abs_icon_path.unlink()
            except Exception as e:
                self.core.logger.warning(f"删除图标文件失败: {e}")

        deleted_count = self.service.batch_delete_apps(list(self.selected_app_ids))
        self.selected_app_ids.clear()
        self._refresh_all_tabs()
        InfoBar.success(
            title="批量删除完成",
            content=f"已删除 {deleted_count} 个应用",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def _add_app(self, category_id: Optional[int] = None):
        """添加应用"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择应用", "",
            "所有支持的文件 (*.exe *.py *.bat *.cmd *.ps1 *.vbs);;"
            "可执行文件 (*.exe);;"
            "Python 脚本 (*.py);;"
            "批处理文件 (*.bat *.cmd);;"
            "PowerShell 脚本 (*.ps1);;"
            "VBScript (*.vbs);;"
            "所有文件 (*.*)"
        )

        if file_path:
            name = os.path.splitext(os.path.basename(file_path))[0]

            if self.service.app_exists(name, file_path):
                InfoBar.warning(
                    title="应用已存在",
                    content=f"{name} 已在列表中",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return

            icon_path = self._extract_icon(file_path)

            self.service.add_app(
                name=name,
                target_path=file_path,
                category_id=category_id,
                icon_path=icon_path
            )

            self._load_categories()

            InfoBar.success(
                title="添加成功",
                content=f"已添加 {name}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def _add_app_with_path(self, file_path: str, category_id: Optional[int] = None):
        """通过拖拽添加应用"""
        if not file_path or not os.path.exists(file_path):
            return

        name = os.path.splitext(os.path.basename(file_path))[0]

        if self.service.app_exists(name, file_path):
            InfoBar.warning(
                title="应用已存在",
                content=f"{name} 已在列表中",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        icon_path = self._extract_icon(file_path)

        self.service.add_app(
            name=name,
            target_path=file_path,
            category_id=category_id,
            icon_path=icon_path
        )

        self._load_categories()

        InfoBar.success(
            title="添加成功",
            content=f"已添加 {name}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def _extract_icon(self, file_path: str) -> str:
        """从文件中提取图标并保存"""
        try:
            if not self.icon_dir.exists():
                self.icon_dir.mkdir(parents=True, exist_ok=True)

            file_info = QFileInfo(file_path)
            icon_provider = QFileIconProvider()
            file_icon = icon_provider.icon(file_info)

            if file_icon.isNull():
                return ""

            import hashlib
            hash_val = hashlib.md5(file_path.encode('utf-8', errors='ignore')).hexdigest()[:8]
            icon_name = f"icon_{hash_val}.png"
            icon_save_path = self.icon_dir / icon_name

            # 获取图标最大可用尺寸
            max_size = 0
            for size in [16, 32, 48, 64, 128, 256]:
                if not file_icon.actualSize(QSize(size, size)).isNull():
                    max_size = size

            # 使用最大尺寸提取图标
            pixmap = file_icon.pixmap(max_size, max_size)
            if pixmap.isNull():
                return ""

            # 裁剪掉空白区域
            content_rect = get_non_transparent_rect(pixmap)
            if not content_rect.isNull() and pixmap.size() != content_rect.size():
                pixmap = pixmap.copy(content_rect)

            # 缩放到合理的保存尺寸(最大128)
            save_size = min(128, max(pixmap.width(), pixmap.height()))
            if pixmap.width() > save_size or pixmap.height() > save_size:
                pixmap = pixmap.scaled(
                    save_size, save_size,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )

            if pixmap.save(str(icon_save_path), "PNG"):
                return f"data/app_icons/{icon_name}"

        except Exception as e:
            self.core.logger.error(f"图标提取失败: {e}")

        return ""

    def _launch_app(self, app_data: Dict[str, Any]):
        """启动应用"""
        try:
            target_path = app_data.get('target_path', '')

            if not target_path:
                InfoBar.warning(
                    title="启动失败",
                    content="应用路径为空",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return

            arguments = app_data.get('arguments', '') or ''

            if not os.path.exists(target_path):
                InfoBar.warning(
                    title="启动失败",
                    content="应用文件不存在",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return

            self._launch_by_type(target_path, arguments)

            # 记录启动次数和时间
            app_id = app_data.get('id')
            if app_id is not None:
                self._record_launch(app_id)

            InfoBar.success(
                title="启动成功",
                content=f"已启动 {app_data.get('name', 'Unknown')}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            self.core.logger.error(f"启动失败: {e}")
            InfoBar.error(
                title="启动失败",
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def _get_recent_apps(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近使用的应用"""
        try:
            return self.service.list_recent_apps(limit)
        except Exception as e:
            self.core.logger.error(f"获取最近使用应用失败: {e}")
            return []

    def _get_favorite_apps(self) -> List[Dict[str, Any]]:
        """获取收藏的应用"""
        try:
            return self.service.list_favorite_apps()
        except Exception as e:
            self.core.logger.error(f"获取收藏应用失败: {e}")
            return []

    def _record_launch(self, app_id: int):
        """记录应用启动"""
        try:
            self.service.record_launch(app_id)
        except Exception as e:
            self.core.logger.error(f"记录启动失败: {e}")

    def _launch_by_type(self, target_path: str, arguments: str = ''):
        """根据文件类型选择启动方式"""
        if os.path.isdir(target_path):
            os.startfile(target_path)
            return

        ext = os.path.splitext(target_path)[1].lower()

        if ext == '.py':
            self._launch_py_script(target_path, arguments)
            return
        elif ext in ('.bat', '.cmd'):
            if arguments:
                subprocess.Popen(f'"{target_path}" {arguments}', shell=True)
            else:
                subprocess.Popen(f'"{target_path}"', shell=True)
        elif ext == '.ps1':
            if arguments:
                subprocess.Popen(f'powershell -ExecutionPolicy Bypass -File "{target_path}" {arguments}', shell=True)
            else:
                subprocess.Popen(f'powershell -ExecutionPolicy Bypass -File "{target_path}"', shell=True)
        elif ext == '.vbs':
            if arguments:
                subprocess.Popen(f'wscript "{target_path}" {arguments}', shell=True)
            else:
                subprocess.Popen(f'wscript "{target_path}"', shell=True)
        else:
            if arguments:
                subprocess.Popen(f'"{target_path}" {arguments}', shell=True)
            else:
                os.startfile(target_path)

    def _launch_py_script(self, target_path: str, arguments: str = ''):
        """异步执行 Python 脚本并反馈结果"""
        from PyQt5.QtCore import QProcess

        # 如果已有同名脚本在运行，先断开旧进程
        old_proc = self._running_py_processes.get(target_path)
        if old_proc is not None:
            try:
                old_proc.finished.disconnect()
                old_proc.errorOccurred.disconnect()
            except TypeError:
                pass
            old_proc.deleteLater()

        proc = QProcess(self)
        proc.setProcessChannelMode(QProcess.MergedChannels)

        if getattr(sys, 'frozen', False):
            cmd = sys.executable
            args = ['--run-script', target_path]
        else:
            cmd = get_python_executable()
            args = [target_path]
        if arguments:
            import shlex
            args.extend(shlex.split(arguments))

        proc.finished.connect(
            lambda exit_code, _: self._on_py_script_done(
                target_path, exit_code
            )
        )
        proc.errorOccurred.connect(
            lambda error: self._on_py_script_error(
                target_path, error
            )
        )
        self._running_py_processes[target_path] = proc
        proc.start(cmd, args)

    def _on_py_script_done(self, target_path: str, exit_code: int) -> None:
        """Python 脚本执行完毕后的回调"""
        proc = self._running_py_processes.pop(target_path, None)
        if proc is None:
            return

        output = proc.readAllStandardOutput().data().decode("utf-8", errors="replace").strip()
        basename = os.path.basename(target_path)
        output_lines = output.splitlines()

        if exit_code == 0:
            display = output[:200] if output else f"{basename} 已执行完毕"
            InfoBar.success(
                title="执行完成",
                content=display,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self,
            )
            self._open_script_output(output_lines)
        else:
            display = output[-300:] if output else f"{basename} 退出码 {exit_code}"
            InfoBar.error(
                title="执行出错",
                content=display,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=6000,
                parent=self,
            )
        proc.deleteLater()

    def _on_py_script_error(self, target_path: str, error) -> None:
        """Python 脚本启动失败的回调"""
        self._running_py_processes.pop(target_path, None)
        basename = os.path.basename(target_path)
        error_name = {
            0: "连接失败",
            1: "启动失败",
            2: "崩溃",
            3: "超时",
            4: "写错误",
            5: "读错误",
            6: "未知错误",
        }.get(error, f"错误码 {error}")
        self.core.logger.error(f"脚本启动失败 {basename}: {error_name}")
        InfoBar.error(
            title="启动失败",
            content=f"{basename}: {error_name}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=4000,
            parent=self,
        )

    _OUTPUT_FILE_EXTENSIONS = re.compile(
        r'[\'"]([^\'"]+\.(html?|csv|json|xml|md|txt|log|png|jpg|jpeg|gif|pdf|docx?|xlsx?|pptx?))[\'"]'
        r'|'
        r'(?:^|\s)((?:[a-zA-Z]:\\[^\s<>"]+\.(?:html?|csv|json|xml|md|txt|log|png|jpg|jpeg|gif|pdf|docx?|xlsx?|pptx?)))',
        re.IGNORECASE,
    )

    def _open_script_output(self, output_lines) -> None:
        """从脚本输出中检测生成的文件并打开"""
        for line in output_lines:
            for match in self._OUTPUT_FILE_EXTENSIONS.finditer(line):
                file_path = match.group(1) or match.group(2)
                if os.path.exists(file_path):
                    try:
                        os.startfile(file_path)
                    except Exception:
                        pass
                    return

    def _toggle_favorite(self, app_data: Dict[str, Any]):
        """切换收藏状态"""
        app_id = app_data.get('id')
        if app_id is None:
            return

        is_favorite = app_data.get('is_favorite', 0)
        new_status = 0 if is_favorite else 1

        try:
            self.service.set_favorite(app_id, bool(new_status))

            self._refresh_all_tabs()

            action = "取消收藏" if is_favorite else "收藏"
            InfoBar.success(
                title="操作成功",
                content=f"已{action} {app_data.get('name', 'Unknown')}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1500,
                parent=self
            )
        except Exception as e:
            self.core.logger.error(f"切换收藏状态失败: {e}")
            InfoBar.error(
                title="操作失败",
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def _edit_app(self, app_data: Dict[str, Any]):
        """编辑应用"""
        categories = self.service.list_categories()
        dialog = AppEditDialog(app_data, categories, self)

        if dialog.exec():
            new_data = dialog.get_data()
            app_id = app_data.get('id')

            if app_id is not None:
                # 检查路径是否改变，如果改变则重新提取图标
                old_path = app_data.get('target_path', '')
                new_path = new_data['target_path']
                icon_path = app_data.get('icon_path', '')

                if old_path != new_path:
                    # 路径改变，重新提取图标
                    if icon_path:
                        abs_icon_path = get_app_data_path(icon_path)
                        if abs_icon_path.exists():
                            try:
                                abs_icon_path.unlink()
                            except Exception:
                                pass
                    icon_path = self._extract_icon(new_path)

                # 更新数据库
                self.service.update_app(
                    app_id,
                    name=new_data['name'],
                    target_path=new_data['target_path'],
                    category_id=new_data['category_id'],
                    arguments=new_data['arguments'],
                    notes=new_data['notes'],
                    icon_path=icon_path
                )

                self._refresh_all_tabs()

                InfoBar.success(
                    title="修改成功",
                    content=f"已更新 {new_data['name']}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )

    def _delete_app(self, app_data: Dict[str, Any]):
        """删除应用"""
        box = MessageBox("删除应用", f"确定要删除 '{app_data.get('name', 'Unknown')}' 吗？", self)
        if box.exec():
            app_id = app_data.get('id')
            if app_id is not None:
                icon_path = app_data.get('icon_path', '')
                if icon_path:
                    abs_icon_path = get_app_data_path(icon_path)
                    if abs_icon_path.exists():
                        try:
                            abs_icon_path.unlink()
                        except Exception as e:
                            self.core.logger.warning(f"删除图标文件失败: {e}")

                self.service.delete_app(app_id)
                self.selected_app_ids.discard(app_id)
                self._refresh_all_tabs()

                InfoBar.success(
                    title="删除成功",
                    content=f"已删除 {app_data.get('name', 'Unknown')}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )

    def _perform_search(self):
        """执行搜索"""
        text = self.search_input.text().strip()

        self._refresh_all_tabs()
        if text:
            self.tab_widget.setCurrentIndex(0)

    def _show_sort_menu(self):
        """显示排序菜单"""
        menu = RoundMenu(parent=self)

        # 按名称排序
        name_action = QAction("按名称排序", self)
        name_action.triggered.connect(lambda: self._sort_apps('name'))
        menu.addAction(name_action)

        # 按添加时间排序
        time_action = QAction("按添加时间排序", self)
        time_action.triggered.connect(lambda: self._sort_apps('created_at'))
        menu.addAction(time_action)

        # 按更新时间排序
        update_action = QAction("按更新时间排序", self)
        update_action.triggered.connect(lambda: self._sort_apps('updated_at'))
        menu.addAction(update_action)

        # 按使用频率排序
        frequency_action = QAction("按使用频率排序", self)
        frequency_action.triggered.connect(lambda: self._sort_apps('launch_count'))
        menu.addAction(frequency_action)

        # 按最近使用排序
        recent_action = QAction("按最近使用排序", self)
        recent_action.triggered.connect(lambda: self._sort_apps('last_launch_time'))
        menu.addAction(recent_action)

        menu.exec_(QCursor.pos())

    def _sort_apps(self, sort_by: str):
        """排序应用"""
        self._current_sort_by = sort_by
        self._refresh_all_tabs()

        InfoBar.success(
            title="排序完成",
            content=f"已按{sort_by}排序",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=1500,
            parent=self
        )

    def _scan_apps(self):
        """扫描系统应用"""
        InfoBar.info(
            title="功能开发中",
            content="扫描功能正在开发中",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
