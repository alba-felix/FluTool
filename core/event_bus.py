from PyQt5.QtCore import QObject, pyqtSignal
from typing import Callable, Dict, List, Any


class EventBus(QObject):
    """
    全局事件总线
    
    支持事件的发布/订阅，实现模块间解耦通信。
    使用 handler 注册表管理回调，支持彻底解绑。
    """
    
    event_signal = pyqtSignal(str, object)

    def __init__(self):
        super().__init__()
        self._handlers: Dict[str, Dict[int, Callable]] = {}
        self._next_handler_id = 0

    def emit(self, event_name: str, data: Any = None) -> None:
        """
        发布事件
        
        Args:
            event_name: 事件名称
            data: 事件数据
        """
        self.event_signal.emit(event_name, data)

    def listen(self, event_name: str, callback: Callable) -> int:
        """
        订阅事件
        
        Args:
            event_name: 事件名称
            callback: 回调函数
            
        Returns:
            handler_id: 用于解绑的处理器ID
        """
        if event_name not in self._handlers:
            self._handlers[event_name] = {}
            self.event_signal.connect(self._create_handler(event_name))
        
        handler_id = self._next_handler_id
        self._handlers[event_name][handler_id] = callback
        self._next_handler_id += 1
        return handler_id

    def _create_handler(self, event_name: str) -> Callable:
        """创建事件处理器"""
        def handler(name: str, data: Any) -> None:
            if name == event_name:
                for callback in list(self._handlers.get(event_name, {}).values()):
                    callback(data)
        return handler

    def disconnect(self, event_name: str, handler_id: int = None) -> None:
        """
        解绑事件
        
        Args:
            event_name: 事件名称
            handler_id: 处理器ID，如果为None则解绑该事件所有处理器
        """
        if event_name not in self._handlers:
            return
        
        if handler_id is None:
            self._handlers[event_name].clear()
        elif handler_id in self._handlers[event_name]:
            del self._handlers[event_name][handler_id]

    def disconnect_all(self) -> None:
        """解绑所有事件"""
        self._handlers.clear()

    def get_handlers_count(self, event_name: str = None) -> int:
        """
        获取处理器数量
        
        Args:
            event_name: 事件名称，如果为None则返回总数
            
        Returns:
            处理器数量
        """
        if event_name:
            return len(self._handlers.get(event_name, {}))
        return sum(len(handlers) for handlers in self._handlers.values())
