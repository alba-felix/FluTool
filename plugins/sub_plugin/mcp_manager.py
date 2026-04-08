"""MCP 管理标签页"""

from typing import Optional, Dict, Any
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidgetItem,
    QFrame, QLabel, QAction
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
from qfluentwidgets import (
    FluentIcon as FIF,
    PushButton, TransparentToolButton, StrongBodyLabel,
    TreeWidget, LineEdit, ComboBox, MessageBoxBase, SubtitleLabel,
    TextEdit, RoundMenu, InfoBar, InfoBarPosition, MessageBox
)

from storage import DatabaseManager

from .page_interface import TabPageInterface


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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._db = DatabaseManager()
        self._setup_ui()
        # 延迟初始化，确保数据库已准备好
        from PyQt5.QtCore import QTimer
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


class MCPManagerPage(TabPageInterface):
    """MCP 管理页面"""

    page_id = "mcp_manager"
    page_name = "MCP 管理"

    @classmethod
    def create(cls, parent=None) -> QWidget:
        return MCPManagerWidget(parent)
