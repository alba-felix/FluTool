"""配置服务模块"""
import json
from pathlib import Path
from typing import Optional, Any


class ConfigService:
    """
    配置服务类（简化版，去除 WebDAV）
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            from ..core.path_util import PathUtil
            config_path = Path(PathUtil.get_config_path('config.json'))
        self._config_path = Path(config_path)
        self._config: dict = {}
        self._load()
    
    def _load(self) -> None:
        if self._config_path.exists():
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._config = {}
        else:
            self._config = {}
    
    def save(self) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        self._config[key] = value