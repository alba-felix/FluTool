import os
import sys
import threading
from pathlib import Path
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFileDialog, QApplication
from PyQt5.QtCore import Qt, pyqtSignal
from qfluentwidgets import (
    ScrollArea, SettingCardGroup, SwitchSettingCard,
    RangeSettingCard, FluentIcon as FIF,
    setCustomStyleSheet, PushSettingCard, MessageBox,
    InfoBar, InfoBarPosition, FolderListSettingCard,
    MessageBoxBase, SubtitleLabel, LineEdit, ComboBox,
    ConfigItem, CaptionLabel
)
from core import get_app_data_path
from core.efficiency_mode import set_process_efficiency_mode, is_efficiency_mode_supported
from core.settings import AISettingsManager
from core.utils import set_auto_start


class SettingsInterface(ScrollArea):
    """
    应用设置界面

    集成 qfluentwidgets 设置卡片组件，提供可视化配置管理。
    """

    # 云同步连接测试结果（从工作线程发回主线程，避免跨线程操作 UI）
    _syncTestDone = pyqtSignal(bool, str)

    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.ai_settings = AISettingsManager()
        self._selected_ai_provider = self.ai_settings.get_default_provider()
        self.setObjectName("settings")
        self._init_paths()
        self._setup_ui()
        self._connect_backup_signals()
        self._connect_sync_signals()

    def _connect_backup_signals(self) -> None:
        """连接备份管理器的恢复结果信号"""
        manager = getattr(self.core, "backup_manager", None)
        if manager is None:
            return

        manager.restore_completed.connect(self._on_restore_finished)
        manager.restore_failed.connect(self._on_restore_error)

    def _connect_sync_signals(self) -> None:
        """连接云同步信号（notes 插件的 SyncService 单例；连接测试信号跨线程安全）"""
        self._syncTestDone.connect(self._on_sync_test_done)
        try:
            from plugins.notes.services.sync_service import SyncService
            self._sync_service = SyncService.get_instance()
            self._sync_service.syncFinished.connect(self._on_sync_finished)
        except Exception as e:
            self.core.logger.warning(f"云同步服务不可用：{e}")
            self._sync_service = None

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
        self._create_sync_group()
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
        self.autoSaveCard.switchButton.onText = "开"
        self.autoSaveCard.switchButton.offText = "关"
        self.autoSaveCard.checkedChanged.connect(self._on_auto_save_changed)
        self.generalGroup.addSettingCard(self.autoSaveCard)
        
        if is_efficiency_mode_supported():
            self.efficiencyModeCard = SwitchSettingCard(
                FIF.SPEED_OFF,
                "效能模式",
                "降低 CPU 占用，延长电池续航（需重启生效）",
                configItem=self.core.config.efficiency_mode
            )
            self.efficiencyModeCard.switchButton.onText = "开"
            self.efficiencyModeCard.switchButton.offText = "关"
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
        self.navExpandedCard.switchButton.onText = "开"
        self.navExpandedCard.switchButton.offText = "关"
        self.navExpandedCard.checkedChanged.connect(self._on_nav_expanded_changed)
        self.windowGroup.addSettingCard(self.navExpandedCard)
        self.autoStartCard = SwitchSettingCard(
            FIF.POWER_BUTTON,
            "开机自启",
            "系统启动时自动运行 FluTool",
            configItem=self.core.config.auto_start
        )
        self.autoStartCard.switchButton.onText = "开"
        self.autoStartCard.switchButton.offText = "关"
        self.autoStartCard.checkedChanged.connect(self._on_auto_start_changed)
        self.windowGroup.addSettingCard(self.autoStartCard)
        self.minimizeToTrayCard = SwitchSettingCard(
            FIF.MINIMIZE,
            "最小化到系统托盘",
            "关闭窗口时最小化到系统托盘而非退出程序",
            configItem=self.core.config.minimize_to_tray
        )
        self.minimizeToTrayCard.switchButton.onText = "开"
        self.minimizeToTrayCard.switchButton.offText = "关"
        self.windowGroup.addSettingCard(self.minimizeToTrayCard)
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
        self.autoBackupCard.switchButton.onText = "开"
        self.autoBackupCard.switchButton.offText = "关"
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

    def _create_sync_group(self) -> None:
        """创建云同步设置组（坚果云 WebDAV，笔记插件提供同步服务）"""
        self.syncGroup = SettingCardGroup("云同步（坚果云）", self.view)

        self.cloudSyncEnabledCard = SwitchSettingCard(
            FIF.CLOUD,
            "启用云同步",
            "与其他设备自动合并同步笔记（绝不覆盖删除）",
            configItem=ConfigItem('notes_sync', 'webdav_enabled', False)
        )
        self.cloudSyncEnabledCard.checkedChanged.connect(self._on_cloud_sync_enabled)
        self.syncGroup.addSettingCard(self.cloudSyncEnabledCard)

        self.cloudSyncAccountCard = PushSettingCard(
            "编辑",
            FIF.PEOPLE,
            "坚果云账号",
            "",
            parent=self.view
        )
        self.cloudSyncAccountCard.clicked.connect(self._edit_sync_account)
        self.syncGroup.addSettingCard(self.cloudSyncAccountCard)

        self.cloudSyncPasswordCard = PushSettingCard(
            "编辑",
            FIF.CERTIFICATE,
            "应用密码",
            "",
            parent=self.view
        )
        self.cloudSyncPasswordCard.clicked.connect(self._edit_sync_password)
        self.syncGroup.addSettingCard(self.cloudSyncPasswordCard)

        self.cloudSyncDirCard = PushSettingCard(
            "编辑",
            FIF.FOLDER,
            "远端目录",
            "坚果云网盘里的同步目录名",
            parent=self.view
        )
        self.cloudSyncDirCard.clicked.connect(self._edit_sync_dir)
        self.syncGroup.addSettingCard(self.cloudSyncDirCard)

        self.cloudSyncIntervalCard = PushSettingCard(
            "选择",
            FIF.DATE_TIME,
            "同步间隔",
            "",
            parent=self.view
        )
        self.cloudSyncIntervalCard.clicked.connect(self._edit_sync_interval)
        self.syncGroup.addSettingCard(self.cloudSyncIntervalCard)

        self.cloudSyncTestCard = PushSettingCard(
            "测试",
            FIF.SYNC,
            "连接测试",
            "验证账号与应用密码是否可用",
            parent=self.view
        )
        self.cloudSyncTestCard.clicked.connect(self._test_cloud_sync)
        self.syncGroup.addSettingCard(self.cloudSyncTestCard)

        self.cloudSyncNowCard = PushSettingCard(
            "立即同步",
            FIF.UPDATE,
            "手动同步",
            "从云端拉取合并 + 推送本地改动",
            parent=self.view
        )
        self.cloudSyncNowCard.clicked.connect(self._sync_cloud_now)
        self.syncGroup.addSettingCard(self.cloudSyncNowCard)

        self.cloudSyncStatusCard = PushSettingCard(
            "刷新",
            FIF.INFO,
            "上次同步",
            "",
            parent=self.view
        )
        self.cloudSyncStatusCard.clicked.connect(self._refresh_sync_cards)
        self.syncGroup.addSettingCard(self.cloudSyncStatusCard)

        self.vBoxLayout.addWidget(self.syncGroup)
        self._refresh_sync_cards()

    # ── 云同步：配置读写与卡片刷新 ──

    @staticmethod
    def _get_sync_config() -> dict:
        """读取云同步配置（notes 插件的 config.json；纯文件操作，不依赖插件已加载）"""
        from plugins.notes.services.config_service import ConfigService
        cs = ConfigService()
        return {
            'webdav_enabled': bool(cs.get('webdav_enabled', False)),
            'webdav_account': cs.get('webdav_account', ''),
            'webdav_password': cs.get('webdav_password', ''),
            'webdav_dir': cs.get('webdav_dir', 'JotMe'),
            'sync_interval': int(cs.get('sync_interval', 30) or 30),
            'sync_last_time': cs.get('sync_last_time', ''),
            'sync_last_result': cs.get('sync_last_result', ''),
        }

    @staticmethod
    def _set_sync_config(**kv) -> None:
        from plugins.notes.services.config_service import ConfigService
        cs = ConfigService()
        for key, value in kv.items():
            cs.set(key, value)
        cs.save()

    def _refresh_sync_cards(self) -> None:
        """按当前配置刷新云同步各卡片显示（blockSignals 防止程序化 setCheck 触发开关逻辑）"""
        cfg = self._get_sync_config()
        self.cloudSyncEnabledCard.blockSignals(True)
        self.cloudSyncEnabledCard.setChecked(cfg['webdav_enabled'])
        self.cloudSyncEnabledCard.blockSignals(False)
        self.cloudSyncAccountCard.setContent(cfg['webdav_account'] or "未设置")
        self.cloudSyncPasswordCard.setContent("已设置" if cfg['webdav_password'] else "未设置")
        self.cloudSyncDirCard.setContent(cfg['webdav_dir'] or "JotMe")
        minutes = cfg['sync_interval']
        if minutes < 60:
            label = f"每 {minutes} 分钟"
        elif minutes < 1440:
            label = f"每 {minutes // 60} 小时"
        else:
            label = f"每 {minutes // 1440} 天"
        self.cloudSyncIntervalCard.setContent(label)
        if cfg['sync_last_time']:
            self.cloudSyncStatusCard.setContent(
                f"{cfg['sync_last_time']} · {cfg['sync_last_result']}")
        else:
            self.cloudSyncStatusCard.setContent("尚未同步过")

    # ── 云同步：事件处理 ──

    def _on_cloud_sync_enabled(self, checked: bool) -> None:
        """启用/关闭云同步"""
        cfg = self._get_sync_config()
        if checked and (not cfg['webdav_account'] or not cfg['webdav_password']):
            self.cloudSyncEnabledCard.blockSignals(True)
            self.cloudSyncEnabledCard.setChecked(False)
            self.cloudSyncEnabledCard.blockSignals(False)
            InfoBar.warning(
                title="云同步",
                content="请先设置坚果云账号与应用密码，再开启云同步",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=3000, parent=self
            )
            return
        self._set_sync_config(webdav_enabled=checked)
        if self._sync_service is not None:
            self._sync_service.start_auto_sync()  # 未启用时内部会停掉定时器
            if checked:
                self._sync_service.sync_now()
        status = "开启" if checked else "关闭"
        self.core.logger.info(f"云同步已{status}")

    def _edit_sync_account(self) -> None:
        """编辑坚果云账号"""
        cfg = self._get_sync_config()
        dialog = MessageBoxBase(self)
        title = SubtitleLabel("坚果云账号", dialog)
        dialog.viewLayout.addWidget(title)
        input_edit = LineEdit(dialog)
        input_edit.setPlaceholderText("坚果云账号（邮箱）")
        input_edit.setText(cfg['webdav_account'])
        dialog.viewLayout.addWidget(input_edit)
        dialog.yesButton.setText("保存")
        dialog.cancelButton.setText("取消")
        if not dialog.exec():
            return
        self._set_sync_config(webdav_account=input_edit.text().strip())
        self._refresh_sync_cards()

    def _edit_sync_password(self) -> None:
        """编辑应用密码"""
        cfg = self._get_sync_config()
        dialog = MessageBoxBase(self)
        title = SubtitleLabel("应用密码", dialog)
        dialog.viewLayout.addWidget(title)
        input_edit = LineEdit(dialog)
        input_edit.setEchoMode(LineEdit.Password)
        input_edit.setPlaceholderText("应用密码（非登录密码）")
        input_edit.setText(cfg['webdav_password'])
        dialog.viewLayout.addWidget(input_edit)
        hint = CaptionLabel(
            "获取方式：坚果云网页端 → 账户信息 → 安全选项 → 添加应用密码", dialog)
        dialog.viewLayout.addWidget(hint)
        dialog.yesButton.setText("保存")
        dialog.cancelButton.setText("取消")
        if not dialog.exec():
            return
        self._set_sync_config(webdav_password=input_edit.text().strip())
        self._refresh_sync_cards()

    def _edit_sync_dir(self) -> None:
        """编辑远端目录"""
        cfg = self._get_sync_config()
        dialog = MessageBoxBase(self)
        title = SubtitleLabel("远端目录", dialog)
        dialog.viewLayout.addWidget(title)
        input_edit = LineEdit(dialog)
        input_edit.setPlaceholderText("JotMe")
        input_edit.setText(cfg['webdav_dir'])
        dialog.viewLayout.addWidget(input_edit)
        dialog.yesButton.setText("保存")
        dialog.cancelButton.setText("取消")
        if not dialog.exec():
            return
        self._set_sync_config(webdav_dir=input_edit.text().strip() or "JotMe")
        self._refresh_sync_cards()

    def _edit_sync_interval(self) -> None:
        """选择同步间隔"""
        cfg = self._get_sync_config()
        dialog = MessageBoxBase(self)
        title = SubtitleLabel("同步间隔", dialog)
        dialog.viewLayout.addWidget(title)
        combo = ComboBox(dialog)
        options = [
            (10, "每 10 分钟"), (30, "每 30 分钟"), (60, "每 1 小时"), (180, "每 3 小时"),
            (720, "每 12 小时"), (1440, "每 24 小时"), (4320, "每 3 天"), (10080, "每 7 天"),
        ]
        for _, label in options:
            combo.addItem(label)
        index = next((i for i, (m, _) in enumerate(options) if m == cfg['sync_interval']), 1)
        combo.setCurrentIndex(index)
        dialog.viewLayout.addWidget(combo)
        dialog.yesButton.setText("保存")
        dialog.cancelButton.setText("取消")
        if not dialog.exec():
            return
        if combo.currentIndex() < 0:
            return
        minutes = options[combo.currentIndex()][0]
        self._set_sync_config(sync_interval=minutes)
        if self._sync_service is not None:
            self._sync_service.start_auto_sync()  # 用新间隔重启定时器
        self._refresh_sync_cards()

    def _test_cloud_sync(self) -> None:
        """连接测试（后台线程，结果经信号回主线程）"""
        cfg = self._get_sync_config()
        if not cfg['webdav_account'] or not cfg['webdav_password']:
            InfoBar.warning(
                title="连接测试",
                content="请先设置坚果云账号与应用密码",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2500, parent=self
            )
            return
        self.cloudSyncTestCard.button.setEnabled(False)
        self.cloudSyncTestCard.button.setText("测试中…")

        def run():
            from plugins.notes.services.webdav_client import WebDavClient
            client = WebDavClient('https://dav.jianguoyun.com/dav/',
                                  cfg['webdav_account'], cfg['webdav_password'])
            ok, msg = client.test_connection()
            self._syncTestDone.emit(ok, msg)

        threading.Thread(target=run, daemon=True).start()

    def _on_sync_test_done(self, ok: bool, msg: str) -> None:
        """连接测试结果（主线程）"""
        self.cloudSyncTestCard.button.setEnabled(True)
        self.cloudSyncTestCard.button.setText("测试")
        if ok:
            InfoBar.success(title="连接测试", content=msg, orient=Qt.Horizontal,
                            isClosable=True, position=InfoBarPosition.TOP,
                            duration=2500, parent=self)
        else:
            InfoBar.error(title="连接测试", content=msg, orient=Qt.Horizontal,
                          isClosable=True, position=InfoBarPosition.TOP,
                          duration=4000, parent=self)

    def _sync_cloud_now(self) -> None:
        """立即同步"""
        if self._sync_service is None:
            InfoBar.error(title="云同步", content="同步服务不可用（笔记插件未加载）",
                          orient=Qt.Horizontal, isClosable=True,
                          position=InfoBarPosition.TOP, duration=3000, parent=self)
            return
        cfg = self._get_sync_config()
        if not cfg['webdav_enabled']:
            self._set_sync_config(webdav_enabled=True)
            self.cloudSyncEnabledCard.blockSignals(True)
            self.cloudSyncEnabledCard.setChecked(True)
            self.cloudSyncEnabledCard.blockSignals(False)
            self._sync_service.start_auto_sync()
        self.cloudSyncNowCard.button.setEnabled(False)
        self.cloudSyncNowCard.button.setText("同步中…")
        self._sync_service.sync_now()

    def _on_sync_finished(self, success: bool, message: str) -> None:
        """同步结束（主线程；信号来自 SyncService 单例，含自动定时同步）"""
        self.cloudSyncNowCard.button.setEnabled(True)
        self.cloudSyncNowCard.button.setText("立即同步")
        cfg = self._get_sync_config()
        if cfg['sync_last_time']:
            self.cloudSyncStatusCard.setContent(
                f"{cfg['sync_last_time']} · {cfg['sync_last_result']}")
        if success:
            InfoBar.success(title="云同步", content=message, orient=Qt.Horizontal,
                            isClosable=True, position=InfoBarPosition.TOP,
                            duration=3000, parent=self)
        else:
            InfoBar.error(title="云同步", content=message, orient=Qt.Horizontal,
                          isClosable=True, position=InfoBarPosition.TOP,
                          duration=5000, parent=self)

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
            "API 密钥",
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
        self.aiEnabledCard.setContent("启用" if enabled else "禁用")

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
        title = SubtitleLabel(f"编辑 API 密钥 ({provider})", dialog)
        dialog.viewLayout.addWidget(title)
        input_edit = LineEdit(dialog)
        input_edit.setPlaceholderText("输入 API 密钥")
        # 设置密码模式，显示掩码
        input_edit.setEchoMode(LineEdit.Password)
        input_edit.setText(str(provider_config.get("api_key", "")))
        dialog.viewLayout.addWidget(input_edit)
        dialog.yesButton.setText("保存")
        dialog.cancelButton.setText("取消")
        if not dialog.exec():
            return

        self.ai_settings.save_provider_config(provider, {"api_key": input_edit.text().strip()})
        if self.core.ai_settings:
            self.core.ai_settings.set_api_key(provider, input_edit.text().strip())
        self._refresh_ai_cards()

    def _edit_ai_base_url(self) -> None:
        """编辑 API 地址"""
        provider = self._selected_ai_provider
        provider_config = self.ai_settings.get_provider_config(provider)
        dialog = MessageBoxBase(self)
        title = SubtitleLabel(f"编辑 API 地址 ({provider})", dialog)
        dialog.viewLayout.addWidget(title)
        input_edit = LineEdit(dialog)
        input_edit.setPlaceholderText("输入 API 地址")
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
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            w = min(self.core.config.window_width.value, geo.width())
            h = min(self.core.config.window_height.value, geo.height())
        else:
            w = self.core.config.window_width.value
            h = self.core.config.window_height.value

        main_window = self._get_main_window()
        if main_window:
            main_window.resize(w, h)
            self.core.logger.info(
                f"Window size changed to: {w}x{h}"
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

    def _on_auto_start_changed(self, checked: bool):
        """开机自启配置改变"""
        set_auto_start(checked)
        self.core.logger.info(f"Auto-start changed to: {checked}")

    def _backup_data(self) -> None:
        """通过 BackupManager 备份数据到 zip 文件"""
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
            ok = self.core.backup_manager.manual_backup(file_path)
            if not ok:
                raise RuntimeError("BackupManager returned False")
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
        """通过 BackupManager 从 zip 文件恢复数据"""
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
            ok, message = self.core.backup_manager.restore_backup_async(file_path)
            if not ok:
                raise RuntimeError(message)
            InfoBar.info(
                title="正在恢复",
                content="正在后台恢复数据，请勿关闭应用...",
                orient=Qt.Horizontal,
                isClosable=False,
                position=InfoBarPosition.TOP,
                duration=-1,
                parent=self
            )
        except Exception as e:
            MessageBox("恢复失败", f"无法恢复数据：{str(e)}", main_window).exec()

    def _on_restore_finished(self, backup_path: str) -> None:
        """后台恢复完成：弹出成功提示"""
        self._close_restoring_bars()
        InfoBar.success(
            title="恢复成功",
            content="数据已恢复，插件数据已刷新",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )

    def _on_restore_error(self, message: str) -> None:
        """后台恢复失败：弹窗提示（需手动关闭）"""
        self._close_restoring_bars()
        MessageBox("恢复失败", f"无法恢复数据：{message}", self._get_main_window()).exec()

    def _close_restoring_bars(self) -> None:
        """关闭所有"正在恢复"提示条"""
        for bar in self.findChildren(InfoBar):
            if bar.title == "正在恢复":
                bar.close()
