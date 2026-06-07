from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFileDialog, QStackedWidget, QListWidget, QListWidgetItem,
    QFontComboBox
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont
from qfluentwidgets import (
    MessageBoxBase, SwitchSettingCard, FluentIcon as FIF,
    PushSettingCard, InfoBar, InfoBarPosition,
    ComboBox, CaptionLabel, StrongBodyLabel, CardWidget, ConfigItem,
    isDarkTheme
)

from ..core.runtime import get_notes_runtime
from ..core.path_util import PathUtil
from ..services.config_service import ConfigService
from ..services.data_service import DataService


class SettingsDialog(MessageBoxBase):
    """设置对话框 - 左右分布布局（简化版，无 WebDAV）"""

    def __init__(self, parent=None, runtime=None):
        super().__init__(parent)
        self._runtime = runtime or get_notes_runtime()
        self._theme_manager = self._runtime.theme_manager
        self._config_service = ConfigService()
        self._current_index = 0
        self._config = self._load_config()
        self._init_ui()
        self._theme_refresh_cb = lambda _theme: self._sync_theme_ui()
        self._theme_manager.register_callback(self._theme_refresh_cb)

    def _load_config(self):
        """加载配置文件"""
        return {
            'ui_scale': self._config_service.get('ui_scale', '100%'),
            'editor_font': self._config_service.get('editor_font', 'Consolas'),
            'auto_save': self._config_service.get('auto_save', True),
            'dark_theme': self._config_service.get('dark_theme', self._theme_manager.is_dark()),
        }

    def _save_config(self, key, value):
        """保存配置"""
        self._config[key] = value
        self._config_service.set(key, value)
        self._config_service.save()

    def _init_ui(self):
        main_layout = QHBoxLayout()
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(200)
        self._update_nav_list_style()

        nav_items = [
            (FIF.BRUSH, '\u5e38\u89c4\u8bbe\u7f6e'),
            (FIF.FONT, '\u7f16\u8f91\u5668\u8bbe\u7f6e'),
            (FIF.MENU, '\u5feb\u6377\u952e'),
            (FIF.FOLDER, '\u6570\u636e\u7ba1\u7406'),
        ]

        for icon, text in nav_items:
            item = QListWidgetItem(icon.icon(), text)
            item.setSizeHint(QSize(200, 44))
            self.nav_list.addItem(item)

        self.nav_list.setCurrentRow(0)
        self.nav_list.itemClicked.connect(self._on_nav_clicked)

        main_layout.addWidget(self.nav_list)

        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet('background: transparent; border: none;')

        self.stacked_widget.addWidget(self._create_general_page())
        self.stacked_widget.addWidget(self._create_editor_page())
        self.stacked_widget.addWidget(self._create_shortcut_page())
        self.stacked_widget.addWidget(self._create_data_page())

        main_layout.addWidget(self.stacked_widget)

        from qfluentwidgets import ToolButton, FluentIcon
        self.close_btn = ToolButton(FluentIcon.CLOSE.icon())
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setStyleSheet('''
            QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        ''')
        self.close_btn.clicked.connect(self.close)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addStretch()
        top_layout.addWidget(self.close_btn)

        self.viewLayout.insertLayout(0, top_layout)
        self.viewLayout.addLayout(main_layout)

        self.yesButton.hide()
        self.cancelButton.hide()
        if hasattr(self, 'buttonLayout'):
            self.buttonLayout.setContentsMargins(0, 0, 0, 0)
            self.buttonLayout.setSpacing(0)

        if hasattr(self, 'buttonGroup'):
            self.buttonGroup.hide()

        self.widget.setMinimumWidth(700)
        self.widget.setMinimumHeight(500)

        self._update_nav_list_style()

    def _update_nav_list_style(self):
        """更新导航列表样式（支持主题切换）"""
        if isDarkTheme():
            self.nav_list.setStyleSheet('''
                QListWidget {
                    border: none;
                    background: transparent;
                    outline: none;
                    color: #ffffff;
                }
                QListWidget::item {
                    height: 44px;
                    border-radius: 6px;
                    margin: 2px 8px;
                    padding-left: 16px;
                    color: #ffffff;
                }
                QListWidget::item:selected {
                    background: rgba(0, 120, 212, 0.15);
                    color: #4cc2ff;
                }
                QListWidget::item:hover {
                    background: rgba(255, 255, 255, 0.06);
                }
            ''')
        else:
            self.nav_list.setStyleSheet('''
                QListWidget {
                    border: none;
                    background: transparent;
                    outline: none;
                    color: #333333;
                }
                QListWidget::item {
                    height: 44px;
                    border-radius: 6px;
                    margin: 2px 8px;
                    padding-left: 16px;
                    color: #333333;
                }
                QListWidget::item:selected {
                    background: rgba(0, 120, 212, 0.08);
                    color: #0078d4;
                }
                QListWidget::item:hover {
                    background: rgba(0, 0, 0, 0.04);
                }
            ''')

    def _on_nav_clicked(self, item):
        """导航项点击事件"""
        index = self.nav_list.row(item)
        self.stacked_widget.setCurrentIndex(index)

    def _sync_theme_ui(self):
        """同步主题相关 UI 状态。"""
        self.theme_card.setChecked(self._theme_manager.is_dark())
        self._update_nav_list_style()

    def _create_general_page(self):
        """创建常规设置页面"""
        widget = CardWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 8, 16, 16)
        layout.setSpacing(12)

        title = StrongBodyLabel('\u5e38\u89c4\u8bbe\u7f6e')
        title.setStyleSheet('color: #333333;')
        layout.addWidget(title)

        theme_config = ConfigItem('dark_theme', '\u4f7f\u7528\u6df1\u8272\u4e3b\u9898', True)
        self.theme_card = SwitchSettingCard(
            FIF.BRUSH,
            '\u5e94\u7528\u4e3b\u9898',
            '\u6df1\u8272/\u6d45\u8272\u4e3b\u9898\u5207\u6362',
            theme_config
        )
        self.theme_card.setChecked(self._theme_manager.is_dark())
        self.theme_card.checkedChanged.connect(self._on_theme_changed)
        layout.addWidget(self.theme_card)

        scale_layout = QHBoxLayout()
        scale_label = CaptionLabel('\u754c\u9762\u7f29\u653e')
        scale_label.setStyleSheet('color: #666666;')
        scale_layout.addWidget(scale_label)

        self.scale_combo = ComboBox()
        scale_options = ['100%', '125%', '150%', '175%', '200%']
        current_scale = self._config.get('ui_scale', '100%')
        self.scale_combo.addItems(scale_options)
        self.scale_combo.setCurrentText(current_scale)
        self.scale_combo.currentTextChanged.connect(self._on_scale_changed)
        scale_layout.addWidget(self.scale_combo)
        scale_layout.addStretch()
        layout.addLayout(scale_layout)

        layout.addStretch()

        return widget

    def _create_editor_page(self):
        """创建编辑器设置页面"""
        widget = CardWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 8, 16, 16)
        layout.setSpacing(12)

        title = StrongBodyLabel('\u7f16\u8f91\u5668\u8bbe\u7f6e')
        title.setStyleSheet('color: #333333;')
        layout.addWidget(title)

        font_layout = QHBoxLayout()
        font_label = CaptionLabel('\u7f16\u8f91\u5668\u5b57\u4f53')
        font_label.setStyleSheet('color: #666666;')
        font_layout.addWidget(font_label)

        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont(self._config.get('editor_font', 'Consolas')))
        self.font_combo.currentFontChanged.connect(self._on_font_changed)
        font_layout.addWidget(self.font_combo, 1)
        layout.addLayout(font_layout)

        auto_save_config = ConfigItem('auto_save', '\u542f\u7528\u81ea\u52a8\u4fdd\u5b58', True)
        self.auto_save_card = SwitchSettingCard(
            FIF.SAVE,
            '\u81ea\u52a8\u4fdd\u5b58',
            '\u7f16\u8f91\u65f6\u81ea\u52a8\u4fdd\u5b58\u7b14\u8bb0',
            auto_save_config
        )
        self.auto_save_card.checkedChanged.connect(self._on_auto_save_changed)
        layout.addWidget(self.auto_save_card)

        layout.addStretch()

        return widget

    def _create_shortcut_page(self):
        """创建快捷键设置页面"""
        widget = CardWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 8, 16, 16)
        layout.setSpacing(12)

        title = StrongBodyLabel('\u5feb\u6377\u952e')
        title.setStyleSheet('color: #333333;')
        layout.addWidget(title)

        shortcuts = [
            ('Ctrl + N', '\u65b0\u5efa\u7b14\u8bb0'),
            ('Ctrl + F', '\u641c\u7d22\u7b14\u8bb0'),
            ('Ctrl + S', '\u4fdd\u5b58\u7b14\u8bb0'),
            ('Ctrl + D', '\u5220\u9664\u7b14\u8bb0'),
            ('Ctrl + E', '\u7f16\u8f91\u7b14\u8bb0'),
            ('Ctrl + T', '\u5207\u6362\u4e3b\u9898'),
        ]

        for shortcut, desc in shortcuts:
            row_layout = QHBoxLayout()
            shortcut_label = CaptionLabel(shortcut)
            shortcut_label.setStyleSheet('color: #0078d4; font-weight: bold; min-width: 100px;')
            row_layout.addWidget(shortcut_label)
            desc_label = CaptionLabel(desc)
            desc_label.setStyleSheet('color: #666666;')
            row_layout.addWidget(desc_label)
            row_layout.addStretch()
            layout.addLayout(row_layout)

        layout.addStretch()

        return widget

    def _create_data_page(self):
        """创建数据管理页面"""
        widget = CardWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 8, 16, 16)
        layout.setSpacing(12)

        title = StrongBodyLabel('\u6570\u636e\u7ba1\u7406')
        title.setStyleSheet('color: #333333;')
        layout.addWidget(title)

        self.backup_card = PushSettingCard(
            '\u5907\u4efd\u6570\u636e',
            FIF.SAVE,
            '\u6570\u636e\u5907\u4efd',
            '\u5c06\u6240\u6709\u7b14\u8bb0\u6570\u636e\u5bfc\u51fa\u4e3a\u538b\u7f29\u5305',
            self
        )
        self.backup_card.clicked.connect(self._backup_data)
        layout.addWidget(self.backup_card)

        self.import_card = PushSettingCard(
            '\u5bfc\u5165\u6570\u636e',
            FIF.DOWNLOAD,
            '\u6570\u636e\u5bfc\u5165',
            '\u4ece\u5907\u4efd\u6587\u4ef6\u6062\u590d\u7b14\u8bb0\u6570\u636e',
            self
        )
        self.import_card.clicked.connect(self._import_data)
        layout.addWidget(self.import_card)

        layout.addStretch()

        return widget

    def _on_theme_changed(self, checked):
        """主题切换"""
        if checked != self._theme_manager.is_dark():
            self._theme_manager.toggle()
        self._save_config('dark_theme', checked)
        self._update_nav_list_style()

        theme_name = '\u6df1\u8272' if checked else '\u6d45\u8272'
        InfoBar.success(
            title='\u4e3b\u9898\u5207\u6362',
            content=f'\u5df2\u5207\u6362\u5230{theme_name}\u4e3b\u9898',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=1500,
            parent=self
        )

    def _on_scale_changed(self, scale):
        """界面缩放"""
        self._save_config('ui_scale', scale)
        InfoBar.info(
            title='\u7f29\u653e\u8bbe\u7f6e',
            content=f'\u7f29\u653e\u6bd4\u4f8b\u5df2\u8bbe\u7f6e\u4e3a {scale}\uff0c\u91cd\u542f\u5e94\u7528\u540e\u751f\u6548',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def _on_font_changed(self, font):
        """字体改变"""
        self._save_config('editor_font', font.family())
        InfoBar.success(
            title='\u5b57\u4f53\u8bbe\u7f6e',
            content=f'\u7f16\u8f91\u5668\u5b57\u4f53\u5df2\u8bbe\u7f6e\u4e3a {font.family()}',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=1500,
            parent=self
        )

    def _on_auto_save_changed(self, checked):
        """自动保存"""
        self._save_config('auto_save', checked)
        status = '\u5f00\u542f' if checked else '\u5173\u95ed'
        InfoBar.success(
            title='\u81ea\u52a8\u4fdd\u5b58',
            content=f'\u81ea\u52a8\u4fdd\u5b58\u5df2{status}',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=1500,
            parent=self
        )

    def _backup_data(self):
        """备份数据"""
        default_name = "NotesBackup.zip"
        save_path, _ = QFileDialog.getSaveFileName(
            self, '保存备份', default_name, '压缩文件 (*.zip)'
        )
        if not save_path:
            return
        success, message = DataService.backup_data(save_path)
        if success:
            InfoBar.success(
                title='备份成功', content=message,
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self
            )
        else:
            InfoBar.error(
                title='备份失败', content=message,
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=3000, parent=self
            )

    def _import_data(self):
        """导入数据"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, '选择备份文件', '', '压缩文件 (*.zip)'
        )
        if not file_path:
            return
        success, message = DataService.import_data(file_path)
        if success:
            InfoBar.success(
                title='导入成功', content=message,
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=3000, parent=self
            )
        else:
            InfoBar.error(
                title='导入失败', content=message,
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=3000, parent=self
            )

    def closeEvent(self, event):
        """关闭事件"""
        if hasattr(self, '_theme_refresh_cb'):
            self._theme_manager.unregister_callback(self._theme_refresh_cb)
        super().closeEvent(event)
