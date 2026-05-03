import sys
from pathlib import Path
from datetime import datetime
from loguru import logger


class LogManager:
    """
    日志管理器（基于 loguru）

    支持：
    1. 主日志文件（logs/flutool.log）- 系统日志、错误信息
    2. 操作日志文件（logs/operations.log）- 增删改等关键操作
    3. 控制台输出
    4. 日志轮转（按天）
    5. 日志级别过滤
    6. 保留最近7天日志，不保留压缩包
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, log_dir: str = None, log_level: str = "INFO"):
        # 检查是否已经初始化过
        if hasattr(self, '_initialized') and self._initialized:
            return

        # 打包后使用正确的路径
        if log_dir is None:
            if getattr(sys, 'frozen', False):
                # 打包后使用 exe 所在目录的 logs 文件夹
                exe_path = Path(sys.executable)
                log_dir = exe_path.parent / "logs"
            else:
                # 开发环境使用相对路径
                log_dir = Path("logs")

        self._log_dir = Path(log_dir)
        self._log_level = log_level
        self._handler_ids = []

        # 移除 loguru 默认处理器
        logger.remove()

        # 添加控制台处理器
        try:
            handler_id = logger.add(
                sys.stdout,
                level=log_level,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
                colorize=True,
                backtrace=True,
                diagnose=True,
            )
            self._handler_ids.append(handler_id)
        except Exception as e:
            print(f"Failed to add console handler: {e}")

        # 标记为已初始化
        self._initialized = True

    def _ensure_log_dir(self):
        """确保日志目录存在"""
        self._log_dir.mkdir(parents=True, exist_ok=True)

    def _get_main_log_path(self) -> Path:
        """获取主日志文件路径"""
        self._ensure_log_dir()
        return self._log_dir / "flutool.log"

    def _get_operation_log_path(self) -> Path:
        """获取操作日志文件路径"""
        self._ensure_log_dir()
        return self._log_dir / "operations.log"

    def setup_main_logger(self):
        """设置主日志文件处理器（系统日志、错误信息）"""
        if not hasattr(self, '_initialized') or not self._initialized:
            raise RuntimeError("LogManager not initialized")

        log_path = self._get_main_log_path()

        handler_id = logger.add(
            log_path,
            level=self._log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="00:00",
            retention="7 days",
            encoding="utf-8",
            backtrace=True,
            diagnose=True,
        )
        self._handler_ids.append(handler_id)

    def setup_operation_logger(self):
        """设置操作日志文件处理器（增删改等关键操作）"""
        if not hasattr(self, '_initialized') or not self._initialized:
            raise RuntimeError("LogManager not initialized")

        log_path = self._get_operation_log_path()

        handler_id = logger.add(
            log_path,
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {extra[operation_type]: <10} | {message}",
            rotation="00:00",
            retention="7 days",
            encoding="utf-8",
            filter=lambda record: "operation_type" in record["extra"],
        )
        self._handler_ids.append(handler_id)

    def get_logger(self, name: str = None):
        """
        获取日志记录器

        Args:
            name: 日志名称，如果为 None 则返回主日志

        Returns:
            配置好的 logger 实例
        """
        if name is None:
            return logger

        return logger.bind(name=name)

    def log_operation(self, operation_type: str, message: str) -> None:
        """
        记录操作日志

        Args:
            operation_type: 操作类型（如 CREATE, UPDATE, DELETE, READ 等）
            message: 操作描述
        """
        logger.bind(operation_type=operation_type).info(message)

    def debug(self, msg: str) -> None:
        logger.debug(msg)

    def info(self, msg: str) -> None:
        logger.info(msg)

    def warning(self, msg: str) -> None:
        logger.warning(msg)

    def error(self, msg: str) -> None:
        logger.error(msg)

    def critical(self, msg: str) -> None:
        logger.critical(msg)

    def success(self, msg: str) -> None:
        logger.success(msg)
