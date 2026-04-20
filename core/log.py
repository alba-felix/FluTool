import sys
from pathlib import Path
from datetime import datetime
from loguru import logger


class LogManager:
    """
    日志管理器（基于 loguru）
    
    支持：
    1. 主日志文件（logs/flutool.log）
    2. 插件独立日志文件（logs/plugins/{plugin_id}.log）
    3. 控制台输出
    4. 日志轮转（按天）
    5. 日志级别过滤
    """
    
    _initialized = False
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, log_dir: str = None, log_level: str = "INFO"):
        if self._initialized:
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
        self._plugin_handlers = {}
        self._handler_ids = []
        
        # 移除 loguru 默认处理器
        logger.remove()
        
        # 添加控制台处理器
        handler_id = logger.add(
            sys.stdout,
            level=log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            colorize=True,
            backtrace=True,
            diagnose=True,
        )
        self._handler_ids.append(handler_id)
        
        self._initialized = True
        
    def _ensure_log_dir(self):
        """确保日志目录存在"""
        self._log_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_main_log_path(self) -> Path:
        """获取主日志文件路径"""
        self._ensure_log_dir()
        return self._log_dir / "flutool.log"
    
    def _get_plugin_log_path(self, plugin_id: str) -> Path:
        """获取插件日志文件路径"""
        plugins_dir = self._log_dir / "plugins"
        plugins_dir.mkdir(parents=True, exist_ok=True)
        return plugins_dir / f"{plugin_id}.log"
    
    def setup_main_logger(self):
        """设置主日志文件处理器"""
        if not self._initialized:
            raise RuntimeError("LogManager not initialized")
        
        log_path = self._get_main_log_path()
        
        handler_id = logger.add(
            log_path,
            level=self._log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="00:00",
            retention="7 days",
            compression="zip",
            encoding="utf-8",
            backtrace=True,
            diagnose=True,
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
    
    def get_plugin_logger(self, plugin_id: str):
        """
        获取插件专用日志记录器
        
        Args:
            plugin_id: 插件 ID
            
        Returns:
            配置好的插件 logger 实例
        """
        if not self._initialized:
            raise RuntimeError("LogManager not initialized")
        
        # 如果已有该插件的处理器，直接返回
        if plugin_id in self._plugin_handlers:
            return logger.bind(plugin_id=plugin_id)
        
        # 添加插件专用的文件处理器
        plugin_log_path = self._get_plugin_log_path(plugin_id)
        
        handler_id = logger.add(
            plugin_log_path,
            level=self._log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {extra[plugin_id]} - {message}",
            rotation="00:00",
            retention="7 days",
            compression="zip",
            encoding="utf-8",
            backtrace=True,
            diagnose=True,
            filter=lambda record: record["extra"].get("plugin_id") == plugin_id,
        )
        
        self._plugin_handlers[plugin_id] = handler_id
        
        return logger.bind(plugin_id=plugin_id)
    
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
