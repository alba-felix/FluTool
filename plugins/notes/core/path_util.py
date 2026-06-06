"""路径工具类 - 使用 FluTool 的运行时路径"""
from core.utils import get_app_data_path


class PathUtil:
    """路径工具类，将数据路径映射到 FluTool 的运行时目录"""

    @classmethod
    def get_data_path(cls, filename: str = '') -> str:
        """获取笔记数据目录 data/notes/"""
        base = get_app_data_path("data/notes")
        base.mkdir(parents=True, exist_ok=True)
        return str(base / filename) if filename else str(base)

    @classmethod
    def get_image_path(cls, filename: str = '') -> str:
        """获取图片目录 data/notes/images/"""
        base = get_app_data_path("data/notes/images")
        base.mkdir(parents=True, exist_ok=True)
        return str(base / filename) if filename else str(base)

    @classmethod
    def get_db_path(cls) -> str:
        """获取数据库文件路径"""
        return str(get_app_data_path("data/notes/notes.db"))

    @classmethod
    def get_config_path(cls, filename: str = '') -> str:
        """获取配置目录 data/notes/config/"""
        base = get_app_data_path("data/notes/config")
        base.mkdir(parents=True, exist_ok=True)
        return str(base / filename) if filename else str(base)

    @classmethod
    def get_resource_path(cls, filename: str = '') -> str:
        """获取资源目录 - 使用插件内资源"""
        import sys
        from pathlib import Path
        base = Path(__file__).parent.parent / "resources"
        return str(base / filename) if filename else str(base)

    @classmethod
    def get_icon_path(cls, filename: str = '') -> str:
        """获取图标目录"""
        base = Path(__file__).parent.parent / "resources" / "icons"
        return str(base / filename) if filename else str(base)