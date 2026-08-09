from qfluentwidgets import QConfig, ConfigItem, RangeConfigItem, BoolValidator, RangeValidator


class AppConfig(QConfig):
    """应用配置类"""
    
    auto_save = ConfigItem("General", "AutoSave", True, BoolValidator())
    efficiency_mode = ConfigItem("General", "EfficiencyMode", False, BoolValidator())
    auto_start = ConfigItem("General", "AutoStart", False, BoolValidator())
    minimize_to_tray = ConfigItem("General", "MinimizeToTray", True, BoolValidator())
    
    window_width = RangeConfigItem("Window", "Width", 1000, RangeValidator(600, 2000))
    window_height = RangeConfigItem("Window", "Height", 700, RangeValidator(400, 1500))
    nav_expanded = ConfigItem("Navigation", "Expanded", False, BoolValidator())
    
    auto_backup_enabled = ConfigItem("Backup", "AutoBackupEnabled", False, BoolValidator())
    auto_backup_path = ConfigItem("Backup", "AutoBackupPath", "", None)

    filecomment_hotkey = ConfigItem("FileComment", "Hotkey", "alt+space", None)
    filecomment_data_path = ConfigItem("FileComment", "DataPath", "", None)
    filecomment_autostart = ConfigItem("FileComment", "AutoStart", False, BoolValidator())
    filecomment_context_menu = ConfigItem("FileComment", "ContextMenu", False, BoolValidator())
