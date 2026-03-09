from abc import ABCMeta, abstractmethod
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal, QObject


class PluginMeta(ABCMeta, type(QObject)):
    """统一的元类，解决 ABC 和 QObject 的元类冲突"""
    pass


class PluginInterface(QObject, metaclass=PluginMeta):
    """
    插件接口基类
    
    所有插件必须继承此类并实现抽象方法。支持懒加载机制：
    1. initialize() - 插件加载时调用（轻量初始化）
    2. get_widget() - 首次切换到插件页面时调用（创建界面）
    3. load_data() - 界面显示后异步调用（加载数据）
    """
    
    widget_created = pyqtSignal()
    data_loaded = pyqtSignal()
    PLUGIN_ID = ""
    PLUGIN_NAME = ""
    PLUGIN_ICON = None

    def __init__(self):
        QObject.__init__(self)
        self._widget = None
        self._data_loaded = False
        self.core = None

    def get_id(self) -> str:
        """获取插件ID"""
        plugin_id = getattr(self, "PLUGIN_ID", "")
        if plugin_id:
            return plugin_id
        return getattr(self, "_id", "")

    def get_name(self) -> str:
        """获取插件名称"""
        plugin_name = getattr(self, "PLUGIN_NAME", "")
        if plugin_name:
            return plugin_name
        return getattr(self, "_name", "")

    def get_icon(self):
        """获取插件图标"""
        plugin_icon = getattr(self, "PLUGIN_ICON", None)
        if plugin_icon is not None:
            return plugin_icon
        return getattr(self, "_icon", None)

    @property
    def is_widget_created(self) -> bool:
        """检查界面是否已创建"""
        return self._widget is not None

    @abstractmethod
    def initialize(self, core) -> None:
        """
        初始化插件（轻量操作）
        
        Args:
            core: AppCore 实例
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """关闭插件，释放资源"""
        pass

    @abstractmethod
    def _create_widget(self, parent=None) -> QWidget:
        """
        创建插件界面（子类实现）
        
        Args:
            parent: 父组件
            
        Returns:
            插件的 QWidget 界面
        """
        pass

    def get_widget(self, parent=None) -> QWidget:
        """
        获取插件界面（懒加载）
        
        Args:
            parent: 父组件
            
        Returns:
            插件的 QWidget 界面
        """
        if self._widget is None:
            self._widget = self._create_widget(parent)
            self.widget_created.emit()
        return self._widget

    def load_data(self) -> None:
        """
        加载数据（异步调用）
        
        子类可重写此方法实现数据加载逻辑。
        """
        if self._data_loaded:
            return
        self._data_loaded = True
        self._do_load_data()
        self.data_loaded.emit()

    def _do_load_data(self) -> None:
        """
        实际数据加载逻辑（子类可重写）
        """
        pass
