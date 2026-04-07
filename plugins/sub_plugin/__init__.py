"""子插件 - 支持标签页管理和溢出处理"""

from typing import Optional, Dict, Any, List, Type
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QApplication, QStackedWidget,
    QFrame, QLabel, QTreeWidgetItem
)
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal
from PyQt5.QtGui import QCursor
from qfluentwidgets import (
    isDarkTheme, FluentIcon as FIF,
    PushButton, TransparentToolButton, StrongBodyLabel,
    TreeWidget, LineEdit, ComboBox, MessageBoxBase, SubtitleLabel,
    TextEdit, SpinBox
)

from core import PluginInterface
from storage import DatabaseManager


class TabPageInterface:
    """标签页接口 - 所有标签页必须实现此接口"""
    
    page_id: str = ""
    page_name: str = ""
    page_icon: Optional[FIF] = None
    
    @classmethod
    def create(cls, parent=None) -> QWidget:
        """创建标签页内容"""
        raise NotImplementedError


class OverflowPopup(QWidget):
    """溢出标签页弹出窗口"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._click_callback = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setFixedWidth(300)
        self.setMaximumHeight(600)
        
        self._main_frame = QFrame(self)
        self._main_frame.setObjectName("overflowMainFrame")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._main_frame)
        
        frame_layout = QVBoxLayout(self._main_frame)
        frame_layout.setContentsMargins(8, 8, 8, 8)
        frame_layout.setSpacing(2)
        
        scroll_area = QScrollArea(self._main_frame)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        frame_layout.addWidget(scroll_area)
        
        self._list_widget = QWidget()
        self._list_widget.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(2)
        scroll_area.setWidget(self._list_widget)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._apply_style()

    def _apply_style(self) -> None:
        if isDarkTheme():
            self._main_frame.setStyleSheet("""
                QFrame#overflowMainFrame {
                    background-color: #2d2d2d;
                    border: 1px solid #3d3d3d;
                    border-radius: 8px;
                }
            """)
        else:
            self._main_frame.setStyleSheet("""
                QFrame#overflowMainFrame {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                }
            """)

    def show_tabs(self, tabs: List[Dict[str, Any]], on_click_callback) -> None:
        self._click_callback = on_click_callback
        
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        for tab in tabs:
            btn = PushButton(tab['text'], self._list_widget)
            btn.setFixedHeight(36)
            btn.clicked.connect(lambda checked, t=tab: self._on_tab_click(t))
            self._list_layout.addWidget(btn)
        
        self.adjustSize()

    def _on_tab_click(self, tab: Dict[str, Any]) -> None:
        self.hide()
        if self._click_callback:
            self._click_callback(tab)

    def show_at(self, global_pos: QPoint, max_height: int) -> None:
        self.setMaximumHeight(min(max_height, 600))
        self.adjustSize()
        
        x = global_pos.x() - self.width()
        y = global_pos.y()
        
        screen = QApplication.screenAt(global_pos)
        if screen:
            screen_rect = screen.availableGeometry()
            if x < screen_rect.left():
                x = screen_rect.left()
            if y + self.height() > screen_rect.bottom():
                y = screen_rect.bottom() - self.height()
        
        self.move(x, y)
        self.show()
        self.setFocus()


class CustomTabBar(QWidget):
    """自定义标签页栏"""

    currentChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tabs: List[Dict[str, Any]] = []
        self._current_index = 0
        self._visible_count = 0
        self._overflow_popup: Optional[OverflowPopup] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setFixedHeight(46)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        
        self._tab_container = QWidget(self)
        self._tab_layout = QHBoxLayout(self._tab_container)
        self._tab_layout.setContentsMargins(0, 0, 0, 0)
        self._tab_layout.setSpacing(2)
        self._tab_layout.addStretch()
        layout.addWidget(self._tab_container, 1)
        
        self._overflow_btn = TransparentToolButton(FIF.MORE, self)
        self._overflow_btn.setFixedSize(36, 36)
        self._overflow_btn.setToolTip("更多标签页")
        self._overflow_btn.clicked.connect(self._show_overflow)
        self._overflow_btn.hide()
        layout.addWidget(self._overflow_btn)

    def addTab(self, page_id: str, text: str) -> int:
        """添加标签页，返回页面索引"""
        page_index = len(self._tabs)
        self._tabs.append({
            'page_id': page_id,
            'text': text,
            'widget_index': page_index,
            'button': None
        })
        self._update_visible_tabs()
        return page_index

    def _update_visible_tabs(self) -> None:
        while self._tab_layout.count() > 1:
            item = self._tab_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        total_width = 0
        tab_buttons = []
        
        for i, tab in enumerate(self._tabs):
            btn = PushButton(tab['text'], self)
            btn.setFixedHeight(36)
            btn.setMinimumWidth(64)
            btn.setMaximumWidth(150)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, idx=i: self._on_tab_click(idx))
            
            if i == self._current_index:
                btn.setChecked(True)
            
            self._tab_layout.insertWidget(i, btn)
            btn.adjustSize()
            
            tab_width = btn.width() + 2
            total_width += tab_width
            tab_buttons.append((i, tab, btn, tab_width))
        
        available_width = self.width() - 50
        need_overflow = total_width > available_width
        
        if need_overflow:
            current_width = 0
            self._visible_count = 0
            
            for i, tab, btn, tab_width in tab_buttons:
                if current_width + tab_width <= available_width - 50:
                    current_width += tab_width
                    self._visible_count += 1
                    tab['button'] = btn
                else:
                    self._tab_layout.removeWidget(btn)
                    btn.deleteLater()
                    tab['button'] = None
        else:
            self._visible_count = len(self._tabs)
            for i, tab, btn, _ in tab_buttons:
                tab['button'] = btn
        
        if len(self._tabs) > self._visible_count:
            self._overflow_btn.show()
        else:
            self._overflow_btn.hide()

    def _on_tab_click(self, index: int) -> None:
        self.setCurrentIndex(index)

    def setCurrentIndex(self, index: int) -> None:
        if 0 <= index < len(self._tabs):
            self._current_index = index
            for i, tab in enumerate(self._tabs):
                if tab['button']:
                    tab['button'].setChecked(i == index)
            widget_index = self._tabs[index]['widget_index']
            self.currentChanged.emit(widget_index)

    def _show_overflow(self) -> None:
        hidden_tabs = self._tabs[self._visible_count:]
        if not hidden_tabs:
            return
        
        if self._overflow_popup is None:
            self._overflow_popup = OverflowPopup()
        
        main_window = self.window()
        max_height = main_window.height() - 100 if main_window else 400
        btn_pos = self._overflow_btn.mapToGlobal(QPoint(0, self._overflow_btn.height()))
        
        self._overflow_popup.show_tabs(hidden_tabs, self._on_overflow_tab_click)
        self._overflow_popup.show_at(btn_pos, max_height)

    def _on_overflow_tab_click(self, tab: Dict[str, Any]) -> None:
        clicked_index = self._tabs.index(tab)
        
        if self._visible_count > 0 and clicked_index >= self._visible_count:
            last_visible_index = self._visible_count - 1
            self._tabs[clicked_index], self._tabs[last_visible_index] = \
                self._tabs[last_visible_index], self._tabs[clicked_index]
            self._current_index = last_visible_index
        else:
            self._current_index = clicked_index
        
        self._update_visible_tabs()
        widget_index = self._tabs[self._current_index]['widget_index']
        self.currentChanged.emit(widget_index)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, self._update_visible_tabs)


class TabManager:
    """标签页管理器 - 管理所有标签页的注册和创建"""

    def __init__(self):
        self._pages: List[Type[TabPageInterface]] = []

    def register(self, page_class: Type[TabPageInterface]) -> None:
        """注册标签页"""
        self._pages.append(page_class)

    def get_pages(self) -> List[Type[TabPageInterface]]:
        """获取所有已注册的标签页"""
        return self._pages.copy()

    def create_all(self, parent=None) -> List[QWidget]:
        """创建所有标签页内容"""
        return [page.create(parent) for page in self._pages]


class MCPManagerPage(TabPageInterface):
    """MCP 管理页面"""

    page_id = "mcp_manager"
    page_name = "MCP 管理"

    @classmethod
    def create(cls, parent=None) -> QWidget:
        return MCPManagerWidget(parent)


class MCPServerDialog(MessageBoxBase):
    """MCP 服务器配置对话框"""

    def __init__(self, parent=None, server_data: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self._server_data = server_data or {}
        self._setup_ui()
        self._load_data()

    def _setup_ui(self) -> None:
        self.titleLabel = SubtitleLabel("MCP 服务器配置", self)
        self.viewLayout.addWidget(self.titleLabel)
        
        form_widget = QWidget(self)
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(12)
        form_layout.setContentsMargins(0, 10, 0, 0)
        
        self._name_edit = LineEdit(form_widget)
        self._name_edit.setPlaceholderText("服务器名称")
        self._name_edit.setClearButtonEnabled(True)
        form_layout.addWidget(self._create_form_row("名称:", self._name_edit))
        
        self._type_combo = ComboBox(form_widget)
        self._type_combo.addItems(["STDIO", "SSE"])
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        form_layout.addWidget(self._create_form_row("类型:", self._type_combo))
        
        self._command_edit = LineEdit(form_widget)
        self._command_edit.setPlaceholderText("例如: npx")
        self._command_edit.setClearButtonEnabled(True)
        form_layout.addWidget(self._create_form_row("命令:", self._command_edit))
        
        self._args_edit = TextEdit(form_widget)
        self._args_edit.setPlaceholderText('参数列表，每行一个\n例如:\n-y\n@microsoft/mcp-server-playwright')
        self._args_edit.setFixedHeight(80)
        form_layout.addWidget(self._create_form_row("参数:", self._args_edit))
        
        self._url_edit = LineEdit(form_widget)
        self._url_edit.setPlaceholderText("例如: http://localhost:8080/mcp")
        self._url_edit.setClearButtonEnabled(True)
        self._url_edit.setEnabled(False)
        form_layout.addWidget(self._create_form_row("URL:", self._url_edit))
        
        self._env_edit = TextEdit(form_widget)
        self._env_edit.setPlaceholderText('环境变量 (JSON 格式)\n例如:\n{"API_KEY": "your-key"}')
        self._env_edit.setFixedHeight(80)
        form_layout.addWidget(self._create_form_row("环境变量:", self._env_edit))
        
        self._desc_edit = TextEdit(form_widget)
        self._desc_edit.setPlaceholderText("服务器描述（可选）")
        self._desc_edit.setFixedHeight(60)
        form_layout.addWidget(self._create_form_row("描述:", self._desc_edit))
        
        self.viewLayout.addWidget(form_widget)
        
        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")
        
        self.widget.setMinimumWidth(500)

    def _create_form_row(self, label_text: str, widget: QWidget) -> QWidget:
        row_widget = QWidget(self)
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)
        
        label = QLabel(label_text, row_widget)
        label.setFixedWidth(70)
        row_layout.addWidget(label)
        row_layout.addWidget(widget, 1)
        
        return row_widget

    def _load_data(self) -> None:
        if not self._server_data:
            return
        
        self._name_edit.setText(self._server_data.get('name', ''))
        
        server_type = self._server_data.get('server_type', 'stdio').upper()
        index = self._type_combo.findText(server_type)
        if index >= 0:
            self._type_combo.setCurrentIndex(index)
        
        self._command_edit.setText(self._server_data.get('command', ''))
        
        args = self._server_data.get('args', '[]')
        if isinstance(args, str):
            try:
                import json
                args_list = json.loads(args)
                self._args_edit.setText('\n'.join(args_list))
            except:
                self._args_edit.setText(args)
        elif isinstance(args, list):
            self._args_edit.setText('\n'.join(args))
        
        self._url_edit.setText(self._server_data.get('url', ''))
        
        env = self._server_data.get('env', '{}')
        if isinstance(env, str):
            self._env_edit.setText(env)
        elif isinstance(env, dict):
            import json
            self._env_edit.setText(json.dumps(env, indent=2))
        
        self._desc_edit.setText(self._server_data.get('description', ''))
        
        self._on_type_changed(self._type_combo.currentIndex())

    def _on_type_changed(self, index: int) -> None:
        is_sse = self._type_combo.currentText() == "SSE"
        self._command_edit.setEnabled(not is_sse)
        self._args_edit.setEnabled(not is_sse)
        self._url_edit.setEnabled(is_sse)

    def get_server_data(self) -> Dict[str, Any]:
        import json
        
        args_text = self._args_edit.toPlainText().strip()
        args_list = []
        if args_text:
            args_list = [line.strip() for line in args_text.split('\n') if line.strip()]
        
        env_text = self._env_edit.toPlainText().strip()
        env_dict = {}
        if env_text:
            try:
                env_dict = json.loads(env_text)
            except json.JSONDecodeError:
                env_dict = {}
        
        return {
            'name': self._name_edit.text().strip(),
            'server_type': self._type_combo.currentText().lower(),
            'command': self._command_edit.text().strip(),
            'args': json.dumps(args_list),
            'env': json.dumps(env_dict),
            'url': self._url_edit.text().strip(),
            'description': self._desc_edit.toPlainText().strip()
        }

    def validate(self) -> bool:
        if not self._name_edit.text().strip():
            return False
        
        server_type = self._type_combo.currentText()
        if server_type == "SSE":
            if not self._url_edit.text().strip():
                return False
        else:
            if not self._command_edit.text().strip():
                return False
        
        return True


class MCPManagerWidget(QWidget):
    """MCP 管理界面"""

    PLUGIN_ID = "mcp_manager"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._db = DatabaseManager()
        self._setup_ui()
        # 延迟初始化，确保数据库已准备好
        QTimer.singleShot(100, self._delayed_init)
    
    def _delayed_init(self) -> None:
        """延迟初始化，确保数据库已准备好"""
        self._init_mcp_table()
        self._load_data()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.setObjectName("mcpManagerView")
        self.setStyleSheet("QWidget#mcpManagerView { background-color: transparent; }")

        # 标题栏
        header_layout = QHBoxLayout()
        title_label = StrongBodyLabel("MCP 服务器管理", self)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        self._search_edit = LineEdit(self)
        self._search_edit.setPlaceholderText("搜索服务器...")
        self._search_edit.setFixedWidth(200)
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.textChanged.connect(self._on_search)
        header_layout.addWidget(self._search_edit)

        # 添加按钮
        self._add_btn = PushButton("添加服务器", self)
        self._add_btn.setFixedHeight(32)
        self._add_btn.clicked.connect(self._on_add_server)
        header_layout.addWidget(self._add_btn)

        # 刷新按钮
        self._refresh_btn = PushButton("刷新", self)
        self._refresh_btn.setFixedHeight(32)
        self._refresh_btn.clicked.connect(self._load_data)
        header_layout.addWidget(self._refresh_btn)

        layout.addLayout(header_layout)

        # 服务器列表
        self._tree = TreeWidget(self)
        self._tree.setHeaderLabels(["名称", "类型", "状态", "地址"])
        self._tree.setAlternatingRowColors(True)
        self._tree.setRootIsDecorated(False)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._tree)

    def _init_mcp_table(self) -> None:
        """初始化 MCP 数据库表"""
        try:
            with self._db.get_connection() as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS mcp_servers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        server_type TEXT NOT NULL DEFAULT 'stdio',
                        command TEXT DEFAULT '',
                        args TEXT DEFAULT '[]',
                        env TEXT DEFAULT '{}',
                        url TEXT DEFAULT '',
                        enabled INTEGER DEFAULT 1,
                        description TEXT DEFAULT '',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()
        except Exception as e:
            print(f"[MCPManager] Error initializing table: {e}")

    def _load_data(self) -> None:
        """加载数据"""
        self._tree.clear()
        
        try:
            with self._db.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT id, name, server_type, enabled, command, url FROM mcp_servers ORDER BY id"
                )
                servers = cursor.fetchall()
        except Exception as e:
            print(f"[MCPManager] Error loading data: {e}")
            servers = []
        
        for server in servers:
            server_id, name, server_type, enabled, command, url = server
            status = "启用" if enabled else "禁用"
            address = url if server_type == "sse" else command
            
            item = QTreeWidgetItem([name, server_type.upper(), status, address or ""])
            item.setData(0, Qt.UserRole, server_id)
            self._tree.addTopLevelItem(item)
        
        self._tree.resizeColumnToContents(0)
        self._tree.resizeColumnToContents(1)
        self._tree.resizeColumnToContents(2)

    def _on_search(self, text: str) -> None:
        """搜索服务器"""
        search_text = text.strip().lower()
        
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            if search_text:
                name = item.text(0).lower()
                server_type = item.text(1).lower()
                address = item.text(3).lower()
                
                visible = (search_text in name or 
                          search_text in server_type or 
                          search_text in address)
                item.setHidden(not visible)
            else:
                item.setHidden(False)

    def _on_add_server(self) -> None:
        """添加服务器"""
        dialog = MCPServerDialog(self)
        if dialog.exec_():
            if not dialog.validate():
                from qfluentwidgets import InfoBar, InfoBarPosition
                InfoBar.error(
                    title="验证失败",
                    content="请填写必填字段：名称和命令（STDIO）或 URL（SSE）",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                return
            
            server_data = dialog.get_server_data()
            
            with self._db.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM mcp_servers WHERE name = ?",
                    (server_data['name'],)
                )
                if cursor.fetchone()[0] > 0:
                    from qfluentwidgets import InfoBar, InfoBarPosition
                    InfoBar.warning(
                        title="名称已存在",
                        content=f"服务器名称 '{server_data['name']}' 已被使用，请使用其他名称",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
                    return
                
                conn.execute('''
                    INSERT INTO mcp_servers 
                    (name, server_type, command, args, env, url, description, enabled)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                ''', (
                    server_data['name'],
                    server_data['server_type'],
                    server_data['command'],
                    server_data['args'],
                    server_data['env'],
                    server_data['url'],
                    server_data['description']
                ))
                conn.commit()
            
            self._load_data()
            
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.success(
                title="成功",
                content=f"服务器 '{server_data['name']}' 已添加",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """双击项目编辑"""
        self._on_edit_server(item)

    def _show_context_menu(self, pos) -> None:
        """显示右键菜单"""
        item = self._tree.itemAt(pos)
        if not item:
            return
        
        from qfluentwidgets import RoundMenu
        from PyQt5.QtWidgets import QAction
        menu = RoundMenu(parent=self)
        
        edit_action = QAction("编辑", menu)
        test_action = QAction("测试连接", menu)
        delete_action = QAction("删除", menu)
        toggle_action = QAction("禁用" if item.text(2) == "启用" else "启用", menu)
        
        edit_action.triggered.connect(lambda: self._on_edit_server(item))
        test_action.triggered.connect(lambda: self._on_test_connection(item))
        delete_action.triggered.connect(lambda: self._on_delete_server(item))
        toggle_action.triggered.connect(lambda: self._on_toggle_server(item))
        
        menu.addAction(edit_action)
        menu.addAction(test_action)
        menu.addAction(delete_action)
        menu.addSeparator()
        menu.addAction(toggle_action)
        
        menu.exec(QCursor.pos())

    def _on_edit_server(self, item: QTreeWidgetItem) -> None:
        """编辑服务器"""
        server_id = item.data(0, Qt.UserRole)
        
        with self._db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM mcp_servers WHERE id = ?",
                (server_id,)
            )
            server_data = cursor.fetchone()
        
        if not server_data:
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.error(
                title="错误",
                content="服务器不存在",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        server_dict = {
            'name': server_data[1],
            'server_type': server_data[2],
            'command': server_data[3],
            'args': server_data[4],
            'env': server_data[5],
            'url': server_data[6],
            'description': server_data[8]
        }
        
        dialog = MCPServerDialog(self, server_dict)
        if dialog.exec_():
            if not dialog.validate():
                from qfluentwidgets import InfoBar, InfoBarPosition
                InfoBar.error(
                    title="验证失败",
                    content="请填写必填字段：名称和命令（STDIO）或 URL（SSE）",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                return
            
            updated_data = dialog.get_server_data()
            
            with self._db.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM mcp_servers WHERE name = ? AND id != ?",
                    (updated_data['name'], server_id)
                )
                if cursor.fetchone()[0] > 0:
                    from qfluentwidgets import InfoBar, InfoBarPosition
                    InfoBar.warning(
                        title="名称已存在",
                        content=f"服务器名称 '{updated_data['name']}' 已被使用，请使用其他名称",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
                    return
                
                conn.execute('''
                    UPDATE mcp_servers 
                    SET name=?, server_type=?, command=?, args=?, env=?, url=?, 
                        description=?, updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                ''', (
                    updated_data['name'],
                    updated_data['server_type'],
                    updated_data['command'],
                    updated_data['args'],
                    updated_data['env'],
                    updated_data['url'],
                    updated_data['description'],
                    server_id
                ))
                conn.commit()
            
            self._load_data()
            
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.success(
                title="成功",
                content=f"服务器 '{updated_data['name']}' 已更新",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def _on_delete_server(self, item: QTreeWidgetItem) -> None:
        """删除服务器"""
        server_id = item.data(0, Qt.UserRole)
        server_name = item.text(0)
        
        from qfluentwidgets import MessageBox
        box = MessageBox(
            "确认删除",
            f"确定要删除服务器 '{server_name}' 吗？\n此操作无法撤销。",
            self
        )
        box.yesButton.setText("删除")
        box.cancelButton.setText("取消")
        
        if box.exec_():
            with self._db.get_connection() as conn:
                conn.execute("DELETE FROM mcp_servers WHERE id = ?", (server_id,))
                conn.commit()
            
            self._load_data()
            
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.success(
                title="成功",
                content=f"服务器 '{server_name}' 已删除",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def _on_toggle_server(self, item: QTreeWidgetItem) -> None:
        """切换服务器状态"""
        server_id = item.data(0, Qt.UserRole)
        new_status = 0 if item.text(2) == "启用" else 1
        
        with self._db.get_connection() as conn:
            conn.execute(
                "UPDATE mcp_servers SET enabled = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_status, server_id)
            )
            conn.commit()
        
        self._load_data()

    def _on_test_connection(self, item: QTreeWidgetItem) -> None:
        """测试服务器连接"""
        server_id = item.data(0, Qt.UserRole)
        server_name = item.text(0)
        
        with self._db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT server_type, command, args, url FROM mcp_servers WHERE id = ?",
                (server_id,)
            )
            server_data = cursor.fetchone()
        
        if not server_data:
            return
        
        server_type, command, args_json, url = server_data
        
        from qfluentwidgets import InfoBar, InfoBarPosition
        import shutil
        
        try:
            if server_type.lower() == "sse":
                if not url:
                    raise ValueError("URL 不能为空")
                
                InfoBar.success(
                    title="配置有效",
                    content=f"服务器 '{server_name}' SSE 配置正确",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
            else:
                if not command:
                    raise ValueError("命令不能为空")
                
                cmd_path = shutil.which(command)
                if cmd_path:
                    InfoBar.success(
                        title="命令可用",
                        content=f"服务器 '{server_name}' 命令 '{command}' 已找到: {cmd_path}",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
                else:
                    raise FileNotFoundError(f"命令 '{command}' 未找到")
                    
        except ValueError as e:
            InfoBar.warning(
                title="配置错误",
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        except FileNotFoundError as e:
            InfoBar.error(
                title="命令未找到",
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        except Exception as e:
            InfoBar.error(
                title="测试失败",
                content=f"服务器 '{server_name}' 测试失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )


class SubPluginWidget(QWidget):
    """子插件主界面"""

    PLUGIN_ID = "sub_plugin"

    def __init__(self, core, tab_manager: TabManager, parent=None):
        super().__init__(parent)
        self.core = core
        self._tab_manager = tab_manager
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.setObjectName("subPluginView")
        self.setStyleSheet("QWidget#subPluginView { background-color: transparent; }")

        self.tab_bar = CustomTabBar(self)
        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tab_bar)

        self.stacked_widget = QStackedWidget(self)
        layout.addWidget(self.stacked_widget)

        self._init_tabs()

    def _on_tab_changed(self, index: int) -> None:
        self.stacked_widget.setCurrentIndex(index)

    def _init_tabs(self) -> None:
        """初始化所有已注册的标签页"""
        pages = self._tab_manager.get_pages()
        widgets = self._tab_manager.create_all(self)
        
        for page_class, widget in zip(pages, widgets):
            self.tab_bar.addTab(page_class.page_id, page_class.page_name)
            widget.setStyleSheet("background-color: transparent;")
            self.stacked_widget.addWidget(widget)
        
        if widgets:
            self.stacked_widget.setCurrentIndex(0)


class Plugin(PluginInterface):
    """子插件"""

    PLUGIN_ID = "sub_plugin"
    PLUGIN_NAME = "子插件"
    PLUGIN_ICON = FIF.TILES
    PLUGIN_PRIORITY = 8.2

    def initialize(self, core) -> None:
        self.core = core
        core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")

        self._tab_manager = TabManager()
        self._tab_manager.register(MCPManagerPage)

        self._widget = None

    def _create_widget(self, parent=None) -> QWidget:
        if self._widget is None:
            self._widget = SubPluginWidget(self.core, self._tab_manager, parent)
        return self._widget

    def shutdown(self) -> None:
        """关闭插件，释放资源"""
        pass
