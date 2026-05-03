import os
import sys
import zipfile
import shutil
from pathlib import Path
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFileDialog
from PyQt5.QtCore import Qt
from qfluentwidgets import (
    ScrollArea, SettingCardGroup, SwitchSettingCard,
    RangeSettingCard, FluentIcon as FIF,
    setCustomStyleSheet, PushSettingCard, MessageBox,
    InfoBar, InfoBarPosition, FolderListSettingCard,
    MessageBoxBase, SubtitleLabel, LineEdit, ComboBox
)
from core import get_app_data_path
from core.efficiency_mode import set_process_efficiency_mode, is_efficiency_mode_supported
from core.settings import AISettingsManager


class SettingsInterface(ScrollArea):
    """
    应用设置界面
    
    集成 qfluentwidgets 设置卡片组件，提供可视化配置管理。
    """
    
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.ai_settings = AISettingsManager()
        self._selected_ai_provider = self.ai_settings.get_default_provider()
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
        self._create_ai_group()
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
        
        if is_efficiency_mode_supported():
            self.efficiencyModeCard = SwitchSettingCard(
                FIF.SPEED_OFF,
                "效能模式",
                "降低 CPU 占用，延长电池续航（需重启生效）",
                configItem=self.core.config.efficiency_mode
            )
            self.efficiencyModeCard.checkedChanged.connect(self._on_efficiency_mode_changed)
            self.generalGroup.addSettingCard(self.efficiencyModeCard)
        
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
        
        self.autoBackupCard = SwitchSettingCard(
            FIF.SYNC,
            "启动备份",
            "每次启动应用时自动备份数据到指定目录（每天一次）",
            configItem=self.core.config.auto_backup_enabled
        )
        self.autoBackupCard.checkedChanged.connect(self._on_auto_backup_changed)
        self.dataGroup.addSettingCard(self.autoBackupCard)
        
        self.backupPathCard = PushSettingCard(
            "选择目录",
            FIF.FOLDER,
            "备份路径",
            self._get_backup_path_display(),
            parent=self.view
        )
        self.backupPathCard.clicked.connect(self._select_backup_path)
        self.dataGroup.addSettingCard(self.backupPathCard)
        
        self.backupCard = PushSettingCard(
            "备份数据",
            FIF.ZIP_FOLDER,
            "手动备份",
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

    def _create_ai_group(self) -> None:
        """创建 AI 设置组"""
        self.aiGroup = SettingCardGroup("AI 设置", self.view)

        self.aiProviderCard = PushSettingCard(
            "切换",
            FIF.SETTING,
            "当前服务商",
            "",
            parent=self.view
        )
        self.aiProviderCard.clicked.connect(self._select_ai_provider)
        self.aiGroup.addSettingCard(self.aiProviderCard)

        self.aiApiKeyCard = PushSettingCard(
            "编辑",
            FIF.SAVE,
            "API Key",
            "",
            parent=self.view
        )
        self.aiApiKeyCard.clicked.connect(self._edit_ai_api_key)
        self.aiGroup.addSettingCard(self.aiApiKeyCard)

        self.aiApiUrlCard = PushSettingCard(
            "编辑",
            FIF.SETTING,
            "API 地址",
            "",
            parent=self.view
        )
        self.aiApiUrlCard.clicked.connect(self._edit_ai_base_url)
        self.aiGroup.addSettingCard(self.aiApiUrlCard)

        self.aiDefaultModelCard = PushSettingCard(
            "编辑",
            FIF.SETTING,
            "默认模型",
            "",
            parent=self.view
        )
        self.aiDefaultModelCard.clicked.connect(self._edit_ai_default_model)
        self.aiGroup.addSettingCard(self.aiDefaultModelCard)

        self.aiEnabledCard = PushSettingCard(
            "切换",
            FIF.POWER_BUTTON,
            "服务商启用状态",
            "",
            parent=self.view
        )
        self.aiEnabledCard.clicked.connect(self._toggle_ai_provider_enabled)
        self.aiGroup.addSettingCard(self.aiEnabledCard)

        self.aiTestCard = PushSettingCard(
            "测试",
            FIF.SYNC,
            "连接测试",
            "发送测试请求验证配置是否可用",
            parent=self.view
        )
        self.aiTestCard.clicked.connect(self._test_ai_connection)
        self.aiGroup.addSettingCard(self.aiTestCard)

        self.vBoxLayout.addWidget(self.aiGroup)
        self._refresh_ai_cards()

    def _refresh_ai_cards(self) -> None:
        """刷新 AI 设置卡片显示"""
        provider = self._selected_ai_provider
        provider_config = self.ai_settings.get_provider_config(provider)
        provider_name = provider_config.get("name", provider)
        base_url = provider_config.get("base_url", "")
        api_key = provider_config.get("api_key", "")
        default_model = provider_config.get("default_model", "")
        enabled = bool(provider_config.get("enabled", True))

        masked_key = "未设置"
        if api_key:
            masked_key = f"{api_key[:6]}...{api_key[-4:]}" if len(api_key) > 10 else "已设置"

        self.aiProviderCard.setContent(f"{provider_name} ({provider})")
        self.aiApiKeyCard.setContent(masked_key)
        self.aiApiUrlCard.setContent(base_url or "未设置")
        self.aiDefaultModelCard.setContent(default_model or "未设置")
        self.aiEnabledCard.setContent("ON" if enabled else "OFF")

    def _select_ai_provider(self) -> None:
        """选择 AI 服务商"""
        dialog = MessageBoxBase(self)
        title = SubtitleLabel("选择服务商", dialog)
        dialog.viewLayout.addWidget(title)
        combo = ComboBox(dialog)
        providers = self.ai_settings.list_providers()
        provider_ids = []
        for provider in providers:
            provider_id = str(provider.get("provider_id", ""))
            provider_name = str(provider.get("name", provider_id))
            combo.addItem(f"{provider_name} ({provider_id})")
            provider_ids.append(provider_id)

        if self._selected_ai_provider in provider_ids:
            combo.setCurrentIndex(provider_ids.index(self._selected_ai_provider))
        dialog.viewLayout.addWidget(combo)
        dialog.yesButton.setText("确定")
        dialog.cancelButton.setText("取消")

        if not dialog.exec():
            return

        if combo.currentIndex() < 0 or combo.currentIndex() >= len(provider_ids):
            return

        self._selected_ai_provider = provider_ids[combo.currentIndex()]
        self.ai_settings.set_default_provider(self._selected_ai_provider)
        self._refresh_ai_cards()

    def _edit_ai_api_key(self) -> None:
        """编辑 API Key"""
        provider = self._selected_ai_provider
        provider_config = self.ai_settings.get_provider_config(provider)
        dialog = MessageBoxBase(self)
        title = SubtitleLabel(f"编辑 API Key ({provider})", dialog)
        dialog.viewLayout.addWidget(title)
        input_edit = LineEdit(dialog)
        input_edit.setPlaceholderText("输入 API Key")
        # 设置密码模式，显示掩码
        input_edit.setEchoMode(LineEdit.Password)
        input_edit.setText(str(provider_config.get("api_key", "")))
        dialog.viewLayout.addWidget(input_edit)
        dialog.yesButton.setText("保存")
        dialog.cancelButton.setText("取消")
        if not dialog.exec():
            return

        self.ai_settings.save_provider_config(provider, {"api_key": input_edit.text().strip()})
        self._refresh_ai_cards()

    def _edit_ai_base_url(self) -> None:
        """编辑 API 地址"""
        provider = self._selected_ai_provider
        provider_config = self.ai_settings.get_provider_config(provider)
        dialog = MessageBoxBase(self)
        title = SubtitleLabel(f"编辑 API 地址 ({provider})", dialog)
        dialog.viewLayout.addWidget(title)
        input_edit = LineEdit(dialog)
        input_edit.setPlaceholderText("输入 Base URL")
        input_edit.setText(str(provider_config.get("base_url", "")))
        dialog.viewLayout.addWidget(input_edit)
        dialog.yesButton.setText("保存")
        dialog.cancelButton.setText("取消")
        if not dialog.exec():
            return

        self.ai_settings.save_provider_config(provider, {"base_url": input_edit.text().strip()})
        self._refresh_ai_cards()

    def _edit_ai_default_model(self) -> None:
        """编辑默认模型"""
        provider = self._selected_ai_provider
        provider_config = self.ai_settings.get_provider_config(provider)
        dialog = MessageBoxBase(self)
        title = SubtitleLabel(f"编辑默认模型 ({provider})", dialog)
        dialog.viewLayout.addWidget(title)
        input_edit = LineEdit(dialog)
        input_edit.setPlaceholderText("例如: deepseek-chat")
        input_edit.setText(str(provider_config.get("default_model", "")))
        dialog.viewLayout.addWidget(input_edit)
        dialog.yesButton.setText("保存")
        dialog.cancelButton.setText("取消")
        if not dialog.exec():
            return

        model_id = input_edit.text().strip()
        if not model_id:
            return
        self.ai_settings.save_provider_config(provider, {"default_model": model_id})
        self.ai_settings.set_default_model(model_id)
        self._refresh_ai_cards()

    def _toggle_ai_provider_enabled(self) -> None:
        """切换服务商启用状态"""
        provider = self._selected_ai_provider
        provider_config = self.ai_settings.get_provider_config(provider)
        current_enabled = bool(provider_config.get("enabled", True))
        self.ai_settings.save_provider_config(provider, {"enabled": not current_enabled})
        self._refresh_ai_cards()

    def _test_ai_connection(self) -> None:
        """测试当前 AI 服务商连接"""
        provider = self._selected_ai_provider
        provider_config = self.ai_settings.get_provider_config(provider)
        model_id = str(provider_config.get("default_model", "")).strip() or self.ai_settings.get_default_model()
        response = self.core.ai_chat_service.send_message(
            user_text="你好，请回复“连接成功”",
            provider=provider,
            model_id=model_id
        )

        if response.error:
            InfoBar.error(
                title="连接失败",
                content=response.error,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self
            )
            return

        InfoBar.success(
            title="连接成功",
            content=f"{provider} 已可用",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2500,
            parent=self
        )
    
    def _get_backup_path_display(self) -> str:
        """获取备份路径显示文本"""
        path = self.core.config.auto_backup_path.value
        if path:
            return path
        return "未设置备份路径"

    def _get_main_window(self):
        """获取主窗口"""
        widget = self
        while widget.parent():
            widget = widget.parent()
        return widget

    def _on_auto_save_changed(self, checked: bool) -> None:
        """自动保存配置改变"""
        self.core.logger.info(f"Auto save changed to: {checked}")
    
    def _on_efficiency_mode_changed(self, checked: bool) -> None:
        """效能模式配置改变"""
        if checked:
            if set_process_efficiency_mode(True, self.core.logger):
                self.core.logger.info("Efficiency mode enabled")
                InfoBar.success(
                    title="效能模式已启用",
                    content="降低 CPU 占用，延长电池续航",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
            else:
                self.efficiencyModeCard.setChecked(False)
                InfoBar.error(
                    title="启用失败",
                    content="无法启用效能模式",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
        else:
            set_process_efficiency_mode(False, self.core.logger)
            self.core.logger.info("Efficiency mode disabled")
    
    def _on_auto_backup_changed(self, checked: bool) -> None:
        """启动备份配置改变"""
        if checked:
            backup_path = self.core.config.auto_backup_path.value
            if not backup_path:
                InfoBar.warning(
                    title="请设置备份路径",
                    content="启用启动备份前，请先选择备份目录",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                self.autoBackupCard.setChecked(False)
                return
            self.core.logger.info("Startup backup enabled")
        else:
            self.core.logger.info("Startup backup disabled")
    
    def _select_backup_path(self) -> None:
        """选择备份路径"""
        current_path = self.core.config.auto_backup_path.value or ""
        
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "选择备份目录",
            current_path,
            QFileDialog.ShowDirsOnly
        )
        
        if folder_path:
            self.core.config.auto_backup_path.value = folder_path
            self.backupPathCard.setContent(folder_path)
            self.core.logger.info(f"Backup path set to: {folder_path}")

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
            
            # 发布数据恢复事件，通知各插件热刷新
            try:
                self.core.event_bus.emit("data_restored")
            except Exception:
                pass
            
            # 记录操作日志
            try:
                self.core.logger.log_operation("RESTORE", f"从备份文件恢复数据: {os.path.basename(file_path)}")
            except Exception:
                pass
            
            InfoBar.success(
                title="恢复成功",
                content="数据已恢复，各插件已自动刷新",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        except Exception as e:
            MessageBox("恢复失败", f"无法恢复数据：{str(e)}", main_window).exec()
