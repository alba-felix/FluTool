import os
import sys
import datetime
import configparser
from pathlib import Path
from typing import Optional, Dict, Any, List

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidgetItem,
    QMenu, QAction, QFormLayout,
    QApplication
)
from PyQt5.QtCore import Qt, QTimer, QTimer
from PyQt5.QtGui import QColor

from qfluentwidgets import (
    StrongBodyLabel, PushButton, LineEdit, TextEdit, BodyLabel,
    FluentIcon as FIF, InfoBar, InfoBarPosition, TreeWidget,
    setCustomStyleSheet, isDarkTheme, qconfig, MessageBoxBase, SubtitleLabel,
    MessageBox
)

from core import PluginInterface
from storage import DatabaseManager
from utils import CharCryptoTool
from core import get_app_data_path, SearchResult

# 尝试导入定时密码功能，失败时优雅处理
try:
    from .time_lock import TimeLockDialog
    HAS_TIME_LOCK = True
except ImportError:
    TimeLockDialog = None
    HAS_TIME_LOCK = False


class InputDialog(MessageBoxBase):
    """Fluent 风格输入对话框"""
    
    def __init__(self, title: str, label: str, default_text: str = "", 
                 is_password: bool = False, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel(title, self)
        self.viewLayout.addWidget(self.titleLabel)
        
        self.input_edit = LineEdit(self)
        self.input_edit.setText(default_text)
        self.input_edit.setPlaceholderText(label)
        self.input_edit.setClearButtonEnabled(True)
        if is_password:
            self.input_edit.setEchoMode(LineEdit.Password)
        self.viewLayout.addWidget(self.input_edit)
        
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(350)
        
        self.input_edit.setFocus()
    
    def get_text(self) -> str:
        return self.input_edit.text().strip()


class SetMasterPasswordDialog(MessageBoxBase):
    """设置/修改主密码的对话框"""
    
    def __init__(self, parent=None, is_modify: bool = False):
        super().__init__(parent)
        self.is_modify = is_modify
        
        title = "修改主密码" if self.is_modify else "设置主密码"
        self.titleLabel = SubtitleLabel(title, self)
        self.viewLayout.addWidget(self.titleLabel)
        
        form = QFormLayout()
        
        if self.is_modify:
            self.old_password_edit = LineEdit(self)
            self.old_password_edit.setEchoMode(LineEdit.Password)
            self.old_password_edit.setPlaceholderText("请输入当前主密码")
            self.old_password_edit.returnPressed.connect(lambda: self.yesButton.click())
            form.addRow("当前密码:", self.old_password_edit)
        
        self.new_password_edit = LineEdit(self)
        self.new_password_edit.setEchoMode(LineEdit.Password)
        self.new_password_edit.setPlaceholderText("请输入新密码")
        self.new_password_edit.returnPressed.connect(lambda: self.yesButton.click())
        form.addRow("新密码:", self.new_password_edit)
        
        self.confirm_password_edit = LineEdit(self)
        self.confirm_password_edit.setEchoMode(LineEdit.Password)
        self.confirm_password_edit.setPlaceholderText("请再次输入新密码")
        self.confirm_password_edit.returnPressed.connect(lambda: self.yesButton.click())
        form.addRow("确认密码:", self.confirm_password_edit)
        
        self.viewLayout.addLayout(form)
        
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(400)
    
    def validate(self) -> bool:
        if self.is_modify:
            old_pwd = self.old_password_edit.text()
            if not old_pwd:
                InfoBar.warning(title="提示", content="请输入当前密码", parent=self)
                return False
        
        new_pwd = self.new_password_edit.text()
        confirm_pwd = self.confirm_password_edit.text()
        
        if not new_pwd:
            InfoBar.warning(title="提示", content="请输入新密码", parent=self)
            return False
        
        if len(new_pwd) < 4:
            InfoBar.warning(title="提示", content="密码长度至少4位", parent=self)
            return False
        
        if new_pwd != confirm_pwd:
            InfoBar.warning(title="提示", content="两次输入的密码不一致", parent=self)
            return False
        
        return True
    
    def get_data(self) -> dict:
        result = {"new_password": self.new_password_edit.text()}
        if self.is_modify:
            result["old_password"] = self.old_password_edit.text()
        return result


class AddPasswordDialog(MessageBoxBase):
    """添加密码的对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.titleLabel = SubtitleLabel("添加密码", self)
        self.viewLayout.addWidget(self.titleLabel)
        
        form = QFormLayout()
        
        self.platform_edit = LineEdit(self)
        self.platform_edit.setPlaceholderText("平台/网站名称")
        self.platform_edit.returnPressed.connect(lambda: self.yesButton.click())
        form.addRow("平台/网站:", self.platform_edit)
        
        self.username_edit = LineEdit(self)
        self.username_edit.setPlaceholderText("用户名")
        self.username_edit.returnPressed.connect(lambda: self.yesButton.click())
        form.addRow("用户名:", self.username_edit)
        
        self.password_edit = LineEdit(self)
        self.password_edit.setEchoMode(LineEdit.Password)
        self.password_edit.setPlaceholderText("密码")
        self.password_edit.returnPressed.connect(lambda: self.yesButton.click())
        form.addRow("密码:", self.password_edit)
        
        self.email_edit = LineEdit(self)
        self.email_edit.setPlaceholderText("邮箱/手机号")
        self.email_edit.returnPressed.connect(lambda: self.yesButton.click())
        form.addRow("邮箱/手机号:", self.email_edit)
        
        self.notes_edit = TextEdit(self)
        self.notes_edit.setPlaceholderText("备注信息")
        self.notes_edit.setFixedHeight(80)
        form.addRow("备注:", self.notes_edit)
        
        self.viewLayout.addLayout(form)
        
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(450)
    
    def validate(self) -> bool:
        if not self.platform_edit.text().strip():
            InfoBar.warning(title="提示", content="请输入平台/网站名称", parent=self)
            return False
        return True
    
    def get_data(self):
        return {
            "platform": self.platform_edit.text().strip(),
            "username": self.username_edit.text().strip(),
            "password": self.password_edit.text(),
            "email": self.email_edit.text().strip(),
            "notes": self.notes_edit.toPlainText()
        }
    
    def set_data(self, data: dict):
        self.platform_edit.setText(data.get("platform", ""))
        self.username_edit.setText(data.get("username", ""))
        self.password_edit.setText(data.get("password", ""))
        self.email_edit.setText(data.get("email", ""))
        self.notes_edit.setPlainText(data.get("notes", ""))


class PasswordWidget(QWidget):
    """密码管理界面"""
    
    PLUGIN_ID = "password"
    
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.db = DatabaseManager()
        self.crypto_tool = CharCryptoTool()
        self.is_decrypted = False
        self.encryption_key = 42
        self.master_password = ""
        self.settings_file = str(get_app_data_path("config/local_settings.ini"))
        self.config = configparser.ConfigParser()
        self._need_set_password = False
        
        self._load_master_password()
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 顶部控制栏
        top_layout = QHBoxLayout()

        # 只在导入成功时添加定时密码按钮
        if HAS_TIME_LOCK:
            self.time_lock_btn = PushButton("定时密码", self)
            self.time_lock_btn.setIcon(FIF.HISTORY)
            self.time_lock_btn.setToolTip("设置定时查看的密码")
            self.time_lock_btn.clicked.connect(self._open_time_lock)
            top_layout.addWidget(self.time_lock_btn)

        self.add_btn = PushButton("添加密码", self)
        self.add_btn.setIcon(FIF.ADD)
        self.add_btn.clicked.connect(self._add_password)
        top_layout.addWidget(self.add_btn)
        
        self.add_category_btn = PushButton("添加分类", self)
        self.add_category_btn.setIcon(FIF.FOLDER_ADD)
        self.add_category_btn.clicked.connect(self._add_category)
        top_layout.addWidget(self.add_category_btn)
        
        self.decrypt_btn = PushButton("解密", self)
        self.decrypt_btn.setIcon(FIF.FINGERPRINT)
        self.decrypt_btn.clicked.connect(self._toggle_decrypt)
        top_layout.addWidget(self.decrypt_btn)
        
        self.modify_pwd_btn = PushButton("修改密码", self)
        self.modify_pwd_btn.setIcon(FIF.EDIT)
        self.modify_pwd_btn.clicked.connect(self._modify_master_password)
        top_layout.addWidget(self.modify_pwd_btn)
        
        self.search_edit = LineEdit(self)
        self.search_edit.setPlaceholderText("搜索密码...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._filter_passwords)
        top_layout.addWidget(self.search_edit)
        
        layout.addLayout(top_layout)
        
        # 密码树形列表
        self.tree = TreeWidget(self)
        self.tree.setHeaderLabels(["平台/网站", "用户名", "密码", "邮箱/手机号", "备注(双击可跳转)"])
        self.tree.setColumnWidth(0, 150)
        self.tree.setColumnWidth(1, 150)
        self.tree.setColumnWidth(2, 120)
        self.tree.setColumnWidth(3, 150)
        self.tree.setColumnWidth(4, 200)
        
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        self._apply_tree_style()
        qconfig.themeChangedFinished.connect(self._apply_tree_style)
        
        layout.addWidget(self.tree)
        
        if self.is_decrypted:
            self.decrypt_btn.setText("已解密")
    
    def load_data(self):
        """加载数据"""
        if self._need_set_password:
            # 延迟显示对话框，确保 UI 已准备好
            QTimer.singleShot(100, self._show_set_password_dialog)
        self._load_passwords()
    
    def _show_set_password_dialog(self):
        """延迟显示设置密码对话框"""
        if not self._need_set_password:
            return
        self._need_set_password = False
        self._do_set_new_password()
    
    def _load_master_password(self):
        """加载主密码"""
        if not os.path.exists(self.settings_file):
            self._create_default_config()
        else:
            self.config.read(self.settings_file, encoding='utf-8')
        
        if 'Password' in self.config and 'encrypted_password' in self.config['Password']:
            encrypted = self.config['Password']['encrypted_password']
            try:
                self.master_password = self.crypto_tool.shift_decrypt(encrypted, self.encryption_key)
                
                if 'last_password_time' in self.config['Password']:
                    last_time_str = self.config['Password']['last_password_time']
                    try:
                        last_time = datetime.datetime.strptime(last_time_str, '%Y-%m-%d %H:%M:%S')
                        if (datetime.datetime.now() - last_time).days < 30:
                            self.is_decrypted = True
                    except:
                        pass
            except:
                self._need_set_password = True
        else:
            self._need_set_password = True
    
    def _create_default_config(self):
        """创建默认配置"""
        self.config['General'] = {'theme': 'blue', 'pinned_tabs': '0'}
        self.config['auto_backup'] = {'enabled': 'false'}
        os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            self.config.write(f)
    
    def _do_set_new_password(self) -> bool:
        """设置新主密码"""
        dialog = SetMasterPasswordDialog(self, is_modify=False)
        if dialog.exec():
            data = dialog.get_data()
            encrypted = self.crypto_tool.shift_encrypt(data['new_password'], self.encryption_key)
            
            if 'Password' not in self.config:
                self.config['Password'] = {}
            self.config['Password']['encrypted_password'] = encrypted
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
            
            self.master_password = data['new_password']
            self.is_decrypted = True
            self.decrypt_btn.setText("已解密")
            return True
        return False
    
    def _modify_master_password(self):
        """修改主密码"""
        dialog = SetMasterPasswordDialog(self, is_modify=True)
        if dialog.exec():
            data = dialog.get_data()
            
            if data.get('old_password') != self.master_password:
                MessageBox("错误", "当前密码不正确", self).exec()
                return
            
            encrypted = self.crypto_tool.shift_encrypt(data['new_password'], self.encryption_key)
            
            if 'Password' not in self.config:
                self.config['Password'] = {}
            self.config['Password']['encrypted_password'] = encrypted
            if 'last_password_time' in self.config['Password']:
                del self.config['Password']['last_password_time']
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
            
            self.master_password = data['new_password']
            self.is_decrypted = True
            self.decrypt_btn.setText("已解密")
            
            InfoBar.success(
                title="成功", content="主密码修改成功",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self
            )
    
    def _load_passwords(self):
        """加载密码列表"""
        self.tree.clear()
        
        categories = self.db.get_categories(self.PLUGIN_ID)
        
        for category in categories:
            category_item = QTreeWidgetItem(self.tree)
            category_item.setText(0, category['name'])
            category_item.setData(0, Qt.UserRole, category['id'])
            
            passwords = self.db.get_passwords(self.PLUGIN_ID, category['id'])
            
            for pwd in passwords:
                password_item = QTreeWidgetItem(category_item)
                password_item.setText(0, pwd.get('platform', ''))
                password_item.setText(1, pwd.get('username', ''))
                password_item.setText(2, "*" * 8)
                password_item.setText(3, pwd.get('email', ''))
                password_item.setText(4, pwd.get('notes', ''))
                
                password_item.setData(0, Qt.UserRole, pwd['id'])
                password_item.setData(1, Qt.UserRole, pwd.get('password', ''))
        
        self.tree.expandAll()
    
    def _apply_tree_style(self) -> None:
        """应用树形列表样式，包括表头和交替行颜色"""
        if not hasattr(self, 'tree'):
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
    
    def _open_time_lock(self):
        """打开定时密码锁对话框"""
        if HAS_TIME_LOCK:
            dialog = TimeLockDialog(self)
            dialog.exec()

    def _add_category(self):
        """添加分类"""
        dialog = InputDialog("添加分类", "请输入分类名称", parent=self)
        if dialog.exec():
            name = dialog.get_text()
            if name:
                self.db.add_category(self.PLUGIN_ID, name)
                self._load_passwords()
                InfoBar.success(
                    title="成功", content=f"已添加分类 {name}",
                    orient=Qt.Horizontal, isClosable=True,
                    position=InfoBarPosition.TOP, duration=2000, parent=self
                )
    
    def _add_password(self):
        """添加密码"""
        selected = self.tree.selectedItems()
        category_id = None
        
        if selected:
            item = selected[0]
            if item.parent():
                category_id = item.parent().data(0, Qt.UserRole)
            else:
                category_id = item.data(0, Qt.UserRole)
        else:
            categories = self.db.get_categories(self.PLUGIN_ID)
            if categories:
                category_id = categories[0]['id']
            else:
                category_id = self.db.add_category(self.PLUGIN_ID, "默认分类")
        
        dialog = AddPasswordDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            encrypted = self.crypto_tool.shift_encrypt(data['password'], self.encryption_key)
            
            self.db.add_password(
                plugin_id=self.PLUGIN_ID,
                username=data['username'],
                password=f"encrypted:{encrypted}",
                platform=data['platform'],
                category_id=category_id,
                email=data['email'],
                notes=data['notes']
            )
            
            self._load_passwords()
            InfoBar.success(
                title="成功", content="已添加密码",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self
            )
    
    def _on_item_double_clicked(self, item, column):
        """双击项目时根据列复制对应内容，备注列支持链接跳转"""
        if not item.parent():
            return
        
        if not self.is_decrypted:
            MessageBox("未解密", "请先点击'解密'按钮并输入口令！", self).exec()
            return
        
        platform = item.text(0)
        username = item.text(1)
        encrypted_pwd = item.data(1, Qt.UserRole)
        email = item.text(3)
        notes = item.text(4)
        
        # 双击备注列时检查是否有链接
        if column == 4:
            import re
            import webbrowser
            
            # 匹配URL模式（支持 http/https，以及被文本包围的链接）
            url_pattern = r'https?://[^\s<>"\')\]]+'
            urls = re.findall(url_pattern, notes)
            
            if urls:
                # 打开第一个找到的链接
                url = urls[0]
                webbrowser.open(url)
                InfoBar.success(
                    title="正在打开",
                    content=f"正在浏览器中打开链接",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return
        
        password = ""
        if encrypted_pwd and encrypted_pwd.startswith("encrypted:"):
            try:
                password = self.crypto_tool.shift_decrypt(
                    encrypted_pwd.replace("encrypted:", ""), self.encryption_key
                )
            except Exception:
                pass
        
        copy_map = {
            0: (platform, "平台/网站"),
            1: (username, "用户名"),
            2: (password, "密码"),
            3: (email, "邮箱/手机号"),
            4: (notes, "备注"),
        }
        
        if column in copy_map:
            value, label = copy_map[column]
            if value:
                QApplication.clipboard().setText(value)
                InfoBar.success(
                    title="已复制",
                    content=f"{label}已复制到剪贴板",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
    
    def _view_password(self, item):
        """查看密码"""
        if not item.parent():
            return
        
        encrypted_pwd = item.data(1, Qt.UserRole)
        platform = item.text(0)
        username = item.text(1)
        email = item.text(3)
        notes = item.text(4)
        
        if encrypted_pwd and encrypted_pwd.startswith("encrypted:") and not self.is_decrypted:
            MessageBox("未解密", "请先点击'解密'按钮并输入口令来查看密码！", self).exec()
            return
        
        password = encrypted_pwd
        if encrypted_pwd and encrypted_pwd.startswith("encrypted:") and self.is_decrypted:
            try:
                password = self.crypto_tool.shift_decrypt(
                    encrypted_pwd.replace("encrypted:", ""), self.encryption_key
                )
            except Exception as e:
                MessageBox("解密失败", str(e), self).exec()
                return
        
        dialog = MessageBoxBase(self)
        dialog.titleLabel = SubtitleLabel(f"查看密码 - {platform}", dialog)
        dialog.viewLayout.addWidget(dialog.titleLabel)
        
        form = QFormLayout()
        form.addRow("平台/网站:", BodyLabel(platform))
        
        for label_text, value in [("用户名:", username), ("密码:", password), ("邮箱/手机号:", email)]:
            label = BodyLabel(value)
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            form.addRow(label_text, label)
        
        notes_label = BodyLabel(notes if notes else "无")
        notes_label.setWordWrap(True)
        form.addRow("备注:", notes_label)
        
        dialog.viewLayout.addLayout(form)
        dialog.yesButton.setText("关闭")
        dialog.cancelButton.hide()
        dialog.widget.setMinimumWidth(450)
        
        dialog.exec()
    
    def _show_context_menu(self, pos):
        """右键菜单"""
        item = self.tree.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        
        if item.parent():
            encrypted_pwd = item.data(1, Qt.UserRole)
            if encrypted_pwd and encrypted_pwd.startswith("encrypted:") and not self.is_decrypted:
                view_action = QAction("查看密码 (需要解密)", self)
                view_action.setEnabled(False)
                menu.addAction(view_action)
            else:
                view_action = QAction("查看密码", self)
                view_action.triggered.connect(lambda: self._view_password(item))
                menu.addAction(view_action)
            
            edit_action = QAction("编辑", self)
            edit_action.triggered.connect(lambda: self._edit_password(item))
            menu.addAction(edit_action)
            
            delete_action = QAction("删除", self)
            delete_action.triggered.connect(lambda: self._delete_password(item))
            menu.addAction(delete_action)
        else:
            add_action = QAction("添加密码", self)
            add_action.triggered.connect(lambda: self._add_password_to_category(item))
            menu.addAction(add_action)
            
            delete_action = QAction("删除分类", self)
            delete_action.triggered.connect(lambda: self._delete_category(item))
            menu.addAction(delete_action)
        
        menu.exec_(self.tree.viewport().mapToGlobal(pos))
    
    def _add_password_to_category(self, category_item):
        self.tree.setCurrentItem(category_item)
        self._add_password()
    
    def _edit_password(self, item):
        """编辑密码"""
        password_id = item.data(0, Qt.UserRole)
        encrypted_pwd = item.data(1, Qt.UserRole)
        
        password = encrypted_pwd
        if encrypted_pwd and encrypted_pwd.startswith("encrypted:"):
            try:
                password = self.crypto_tool.shift_decrypt(
                    encrypted_pwd.replace("encrypted:", ""), self.encryption_key
                )
            except:
                password = ""
        
        dialog = AddPasswordDialog(self)
        dialog.set_data({
            "platform": item.text(0),
            "username": item.text(1),
            "password": password,
            "email": item.text(3),
            "notes": item.text(4)
        })
        
        if dialog.exec():
            data = dialog.get_data()
            new_encrypted = self.crypto_tool.shift_encrypt(data['password'], self.encryption_key)
            
            self.db.update_password(
                self.PLUGIN_ID, password_id,
                platform=data['platform'],
                username=data['username'],
                password=f"encrypted:{new_encrypted}",
                email=data['email'],
                notes=data['notes']
            )
            
            self._load_passwords()
            InfoBar.success(
                title="成功", content="密码已更新",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self
            )
    
    def _delete_password(self, item):
        """删除密码"""
        if MessageBox(
            "确认删除", 
            f"确定要删除密码 '{item.text(0)}' 吗？",
            self
        ).exec():
            self.db.delete_password(self.PLUGIN_ID, item.data(0, Qt.UserRole))
            self._load_passwords()
    
    def _delete_category(self, item):
        """删除分类"""
        if MessageBox(
            "确认删除", 
            f"确定要删除分类 '{item.text(0)}' 吗？",
            self
        ).exec():
            self.db.delete_category(self.PLUGIN_ID, item.data(0, Qt.UserRole))
            self._load_passwords()
    
    def _filter_passwords(self, text):
        """搜索过滤"""
        for i in range(self.tree.topLevelItemCount()):
            cat_item = self.tree.topLevelItem(i)
            cat_visible = text.lower() in cat_item.text(0).lower()
            
            for j in range(cat_item.childCount()):
                pwd_item = cat_item.child(j)
                # 搜索所有列：平台、用户名、密码、邮箱/手机号、备注
                pwd_visible = any(
                    text.lower() in pwd_item.text(col).lower()
                    for col in range(5)
                )
                pwd_item.setHidden(not pwd_visible)
                cat_visible = cat_visible or pwd_visible
            
            cat_item.setHidden(not cat_visible)
            if cat_visible:
                self.tree.expandItem(cat_item)
    
    def _toggle_decrypt(self):
        """解密/锁定切换"""
        if self.is_decrypted:
            if MessageBox("确认锁定", "确定要锁定密码吗？", self).exec():
                self.is_decrypted = False
                self.decrypt_btn.setText("解密")
        else:
            dialog = InputDialog("输入口令", "请输入口令", is_password=True, parent=self)
            if dialog.exec():
                pwd = dialog.get_text()
                if pwd:
                    if pwd == self.master_password:
                        self.is_decrypted = True
                        self.decrypt_btn.setText("已解密")
                        
                        if 'Password' not in self.config:
                            self.config['Password'] = {}
                        self.config['Password']['last_password_time'] = datetime.datetime.now().strftime(
                            '%Y-%m-%d %H:%M:%S')
                        with open(self.settings_file, 'w', encoding='utf-8') as f:
                            self.config.write(f)
                    else:
                        MessageBox("错误", "口令不正确", self).exec()
    
    def _copy_to_clipboard(self, text: str):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        InfoBar.success(
            title="已复制", content="内容已复制到剪贴板",
            orient=Qt.Horizontal, isClosable=True,
            position=InfoBarPosition.TOP, duration=1500, parent=self
        )


class Plugin(PluginInterface):
    """密码管理插件"""
    PLUGIN_ID = "password"
    PLUGIN_NAME = "密码管理"
    PLUGIN_ICON = FIF.FINGERPRINT
    PLUGIN_PRIORITY = 3
    
    def initialize(self, core) -> None:
        self.core = core
        core.logger.info(f"Plugin '{self.get_name()}' initialized")
    
    def shutdown(self) -> None:
        self.core.logger.info(f"Plugin '{self.get_name()}' shutdown")
    
    def _create_widget(self, parent=None) -> QWidget:
        return PasswordWidget(self.core, parent)
    
    def _do_load_data(self) -> None:
        if self._widget:
            self._widget.load_data()
    
    def supports_search(self) -> bool:
        return True
    
    def search(self, query: str):
        db = DatabaseManager()
        results = []
        passwords = db.search_passwords(self.PLUGIN_ID, query)
        for pwd in passwords[:20]:
            result = SearchResult(
                plugin_id=self.PLUGIN_ID,
                plugin_name=self.get_name(),
                title=pwd.get('platform', '') or pwd.get('username', ''),
                description=f"{pwd.get('username', '')} - {pwd.get('email', '')}",
                icon=self.PLUGIN_ICON,
                relevance=1.0 if query in pwd.get('platform', '').lower() else 0.5,
                action=lambda: None,
                metadata={'password_id': pwd['id']}
            )
            results.append(result)
        return results


__all__ = ['Plugin']
