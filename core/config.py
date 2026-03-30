from qfluentwidgets import QConfig, ConfigItem, RangeConfigItem, BoolValidator, RangeValidator


class AppConfig(QConfig):
    """
    应用配置类
    
    定义应用全局配置项，支持类型验证和自动保存。
    """
    
    auto_save = ConfigItem(
        "General", "AutoSave", True, BoolValidator()
    )
    efficiency_mode = ConfigItem(
        "General", "EfficiencyMode", False, BoolValidator()
    )
    window_width = RangeConfigItem(
        "Window", "Width", 1000, RangeValidator(600, 2000)
    )
    window_height = RangeConfigItem(
        "Window", "Height", 700, RangeValidator(400, 1500)
    )
    nav_expanded = ConfigItem(
        "Navigation", "Expanded", False, BoolValidator()
    )
    auto_backup_enabled = ConfigItem(
        "Backup", "AutoBackupEnabled", False, BoolValidator()
    )
    auto_backup_path = ConfigItem(
        "Backup", "AutoBackupPath", "", None
    )
