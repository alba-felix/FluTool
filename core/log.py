import logging
import sys
from pathlib import Path


class LogManager:
    """
    日志管理器
    
    单例模式，支持控制台和文件输出，延迟初始化文件处理器。
    """
    
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, log_dir: str = "logs", log_level: int = logging.INFO):
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = True
        self._logger = logging.getLogger("FluTool")
        self._logger.setLevel(log_level)
        self._logger.handlers.clear()
        self._file_handler = None
        self._setup_console_handler()
        self._log_dir = log_dir

    def _setup_console_handler(self) -> None:
        """设置控制台处理器"""
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)

    def _ensure_file_handler(self) -> None:
        """延迟初始化文件处理器"""
        if self._file_handler is not None:
            return
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        log_path = Path(self._log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        self._file_handler = logging.FileHandler(
            log_path / "flutool.log", encoding='utf-8'
        )
        self._file_handler.setFormatter(formatter)
        self._logger.addHandler(self._file_handler)

    def debug(self, msg: str) -> None:
        self._ensure_file_handler()
        self._logger.debug(msg)

    def info(self, msg: str) -> None:
        self._ensure_file_handler()
        self._logger.info(msg)

    def warning(self, msg: str) -> None:
        self._ensure_file_handler()
        self._logger.warning(msg)

    def error(self, msg: str) -> None:
        self._ensure_file_handler()
        self._logger.error(msg)
