import os
import zipfile
import shutil
from pathlib import Path
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFileDialog
from PyQt5.QtCore import Qt
from qfluentwidgets import (
    ScrollArea, SettingCardGroup, SwitchSettingCard,
    RangeSettingCard, FluentIcon as FIF,
    setCustomStyleSheet, PushSettingCard, MessageBox,
    InfoBar, InfoBarPosition
)
from core import get_app_data_path


class SettingsInterface(ScrollArea):
    """
    应用设置界面
    
    集成 qfluentwidgets 设置卡片组件，提供可视化配置管理。
    """
    
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.setObjectName("settings")
        self._init_paths()
        self._setup_ui()

    def _init_paths(self) -> None:
        """初始化路径"""
        self.data_dir = get_app_data_path("data")
        self.project_root = self.data_dir.parent

    def _setup_ui(self) -> None:
        """构建设置界面布局"""
        self.view = QWidget(self)
        self.view.setObjectName("settingsView")
        self.vBoxLayout = QVBoxLayout(self.view)
        self.vBoxLayout.setSpacing(20)
        self.vBoxLayout.setContentsMargins(20, 20, 20, 20)
        self._create_general_group()
        self._create_window_group()
        self._create_data_group()
        self.vBoxLayout.addStretch(1)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.enableTransparentBackground()

    def _create_general_group(self) -> None:
        """创建通用设置组"""
        self.generalGroup = SettingCardGroup("通用设置", self.view)
        self.autoSaveCard = SwitchSettingCard(
            FIF.SAVE,
            "自动保存",
            "编辑后自动保存数据",
            configItem=self.core.config.auto_save
        )
        self.autoSaveCard.checkedChanged.connect(self._on_auto_save_changed)
        self.generalGroup.addSettingCard(self.autoSaveCard)
        self.vBoxLayout.addWidget(self.generalGroup)

    def _create_window_group(self) -> None:
        """创建窗口设置组"""
        self.windowGroup = SettingCardGroup("窗口设置", self.view)
        self.widthCard = RangeSettingCard(
            self.core.config.window_width,
            FIF.FULL_SCREEN,
            "窗口宽度",
            "调整应用窗口的默认宽度",
            parent=self.view
        )
        self.widthCard.valueChanged.connect(self._on_window_size_changed)
        self.windowGroup.addSettingCard(self.widthCard)
        self.heightCard = RangeSettingCard(
            self.core.config.window_height,
            FIF.FULL_SCREEN,
            "窗口高度",
            "调整应用窗口的默认高度",
            parent=self.view
        )
        self.heightCard.valueChanged.connect(self._on_window_size_changed)
        self.windowGroup.addSettingCard(self.heightCard)
        self.navExpandedCard = SwitchSettingCard(
            FIF.MENU,
            "展开导航栏",
            "启动时展开侧边导航栏",
            configItem=self.core.config.nav_expanded
        )
        self.navExpandedCard.checkedChanged.connect(self._on_nav_expanded_changed)
        self.windowGroup.addSettingCard(self.navExpandedCard)
        self.vBoxLayout.addWidget(self.windowGroup)

    def _create_data_group(self) -> None:
        """创建数据管理设置组"""
        self.dataGroup = SettingCardGroup("数据管理", self.view)
        
        self.backupCard = PushSettingCard(
            "备份数据",
            FIF.ZIP_FOLDER,
            "数据备份",
            "将 data 文件夹打包为 zip 文件",
            parent=self.view
        )
        self.backupCard.clicked.connect(self._backup_data)
        self.dataGroup.addSettingCard(self.backupCard)
        
        self.loadCard = PushSettingCard(
            "加载数据",
            FIF.FOLDER,
            "数据恢复",
            "从 zip 备份文件恢复数据（将覆盖现有数据）",
            parent=self.view
        )
        self.loadCard.clicked.connect(self._load_data)
        self.dataGroup.addSettingCard(self.loadCard)
        
        self.vBoxLayout.addWidget(self.dataGroup)

    def _get_main_window(self):
        """获取主窗口"""
        widget = self
        while widget.parent():
            widget = widget.parent()
        return widget

    def _on_auto_save_changed(self, checked: bool) -> None:
        """自动保存配置改变"""
        self.core.logger.info(f"Auto save changed to: {checked}")

    def _on_window_size_changed(self) -> None:
        """窗口大小配置改变"""
        main_window = self._get_main_window()
        if main_window:
            main_window.resize(
                self.core.config.window_width.value,
                self.core.config.window_height.value
            )
            self.core.logger.info(
                f"Window size changed to: "
                f"{self.core.config.window_width.value}x{self.core.config.window_height.value}"
            )

    def _on_nav_expanded_changed(self, checked: bool):
        """导航栏展开配置改变"""
        main_window = self._get_main_window()
        if hasattr(main_window, 'navigationInterface'):
            try:
                if checked:
                    main_window.navigationInterface.expand()
                else:
                    main_window.navigationInterface.collapse()
                self.core.logger.info(f"Navigation expanded changed to: {checked}")
            except Exception as e:
                self.core.logger.error(f"Failed to change navigation expanded: {e}")

    def _backup_data(self) -> None:
        """备份数据到 zip 文件"""
        main_window = self._get_main_window()
        
        default_name = "flutool_data_backup.zip"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存备份文件",
            default_name,
            "ZIP 文件 (*.zip)"
        )
        
        if not file_path:
            return
        
        if not file_path.endswith('.zip'):
            file_path += '.zip'
        
        try:
            with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                if self.data_dir.exists():
                    for root, dirs, files in os.walk(self.data_dir):
                        for file in files:
                            file_path_full = Path(root) / file
                            arcname = file_path_full.relative_to(self.project_root)
                            zipf.write(file_path_full, arcname)
            
            InfoBar.success(
                title="备份成功",
                content=f"数据已备份到 {Path(file_path).name}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            MessageBox("备份失败", f"无法创建备份文件：{str(e)}", main_window).exec()

    def _load_data(self) -> None:
        """从 zip 文件恢复数据"""
        main_window = self._get_main_window()
        
        confirm = MessageBox(
            "确认恢复",
            "恢复数据将覆盖现有的 data 文件夹内容，此操作不可撤销。\n是否继续？",
            main_window
        )
        confirm.yesButton.setText("确认恢复")
        confirm.cancelButton.setText("取消")
        
        if not confirm.exec():
            return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择备份文件",
            "",
            "ZIP 文件 (*.zip)"
        )
        
        if not file_path:
            return
        
        try:
            if self.data_dir.exists():
                shutil.rmtree(self.data_dir)
            
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(file_path, 'r') as zipf:
                for member in zipf.namelist():
                    if member.startswith('data/'):
                        zipf.extract(member, self.project_root)
            
            InfoBar.success(
                title="恢复成功",
                content="数据已恢复，部分功能可能需要重启应用生效",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        except Exception as e:
            MessageBox("恢复失败", f"无法恢复数据：{str(e)}", main_window).exec()
