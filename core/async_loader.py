"""
异步加载器基类模块

提供统一的异步加载框架，封装 QThread 的公共逻辑，
通过模板方法模式让子类实现具体的加载逻辑。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from PyQt5.QtCore import QThread, pyqtSignal
from storage import DatabaseManager


class BaseAsyncLoader(QThread, ABC):
    """异步加载器基类
    
    提供统一的异步加载框架，子类只需实现 load_data() 方法。
    支持进度报告和错误处理。
    
    使用场景：数据库数据加载、文件读取等简单异步任务
    
    示例:
        class ScriptLoader(BaseAsyncLoader):
            def load_data(self) -> List[Dict[str, Any]]:
                return self.db.get_scripts(self.plugin_id)
            
            def get_data_name(self) -> str:
                return "脚本"
    """
    
    load_finished = pyqtSignal(list)
    load_progress = pyqtSignal(int)
    load_error = pyqtSignal(str)
    
    def __init__(self, db: Optional[DatabaseManager] = None, plugin_id: str = ""):
        super().__init__()
        self.db = db
        self.plugin_id = plugin_id
    
    def run(self):
        """执行异步加载"""
        try:
            self.load_progress.emit(10)
            self.load_progress.emit(30)
            
            data = self.load_data()
            self.load_progress.emit(60)
            
            self.load_progress.emit(100)
            
            self.load_finished.emit(data)
        except Exception as e:
            self.load_error.emit(f"加载{self.get_data_name()}数据时出错：{e}")
    
    @abstractmethod
    def load_data(self) -> List[Dict[str, Any]]:
        """加载数据（子类实现）
        
        Returns:
            加载的数据列表
        """
        pass
    
    def get_data_name(self) -> str:
        """获取数据名称（用于错误消息）
        
        子类可以重写此方法以提供更友好的错误消息。
        
        Returns:
            数据名称字符串
        """
        return ""


class NetworkAsyncLoader(QThread, ABC):
    """网络异步加载器基类
    
    在 QThread 基础上增加可停止机制，适用于网络请求等耗时操作。
    子类需要实现 do_request() 方法。
    
    使用场景：API 调用、HTTP 请求、文件下载等网络操作
    
    示例:
        class AIChatWorker(NetworkAsyncLoader):
            stream_update = pyqtSignal(str)
            
            def __init__(self, chat_service, user_text: str, ...):
                super().__init__()
                self.chat_service = chat_service
                self.user_text = user_text
            
            def do_request(self):
                def stream_callback(text: str):
                    if self._is_running:
                        self.stream_update.emit(text)
                
                return self.chat_service.send_message(
                    user_text=self.user_text,
                    ...
                )
    """
    
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self._is_running = True
    
    def run(self):
        """执行网络请求"""
        try:
            if not self._is_running:
                return
            
            result = self.do_request()
            
            if self._is_running:
                self.finished.emit(result)
        except Exception as e:
            if self._is_running:
                self.error.emit(str(e))
    
    @abstractmethod
    def do_request(self):
        """执行请求（子类实现）
        
        Returns:
            请求结果
        """
        pass
    
    def stop(self):
        """停止加载"""
        self._is_running = False
        self.wait(1000)  # 等待 1 秒让线程结束
