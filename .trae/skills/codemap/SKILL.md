# SKILL.md - 基于 PyQt5 和 PyQt-Fluent-Widgets 的插件化桌面应用架构

## 1. 项目概述

本项目旨在构建一个基于 PyQt5 的桌面应用程序，核心设计理念是 **微内核 + 插件化**。应用核心仅提供基础服务，具体功能由独立插件实现。利用 **PyQt-Fluent-Widgets (qfluentwidgets)** 库快速构建现代化 Fluent Design 风格的用户界面。

## 2. 总体架构

```
┌─────────────────────────────────────────────────────────┐
│                      main.py (入口)                      │
│              创建应用 → 初始化核心 → 加载插件              │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    AppCore (核心服务)                     │
│     LogManager │ EventBus │ PluginManager │ Config      │
└─────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │PluginManager│ │ PluginHost  │ │ Repository  │
    │发现/加载插件 │ │UI生命周期管理│ │ 数据访问注册 │
    └─────────────┘ └─────────────┘ └─────────────┘
```

## 3. 核心模块

### 3.1 AppCore (单例)

```python
# core/app_core.py
class AppCore:
    _instance: Optional['AppCore'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self) -> None:
        """初始化核心服务"""
        
    def shutdown(self) -> None:
        """关闭核心服务，释放资源"""
    
    @property
    def plugin_manager(self) -> PluginManager: ...
    @property
    def event_bus(self) -> EventBus: ...
    @property
    def config(self) -> AppConfig: ...
    @property
    def logger(self) -> LogManager: ...
```

### 3.2 PluginManager

```python
# core/plugin_manager.py
class PluginManager:
    def scan_plugins(self, plugin_path: str) -> List[str]:
        """开发环境扫描插件目录，优先读取 plugin.json，不导入插件主体"""

    def scan_builtin_plugins(self) -> List[str]:
        """打包环境扫描内置插件，优先使用 plugins/plugin_index.py"""
        
    def load_plugin(self, plugin_id: str) -> Optional[PluginInterface]:
        """加载指定插件"""
        
    def unload_plugin(self, plugin_id: str) -> bool:
        """卸载插件"""
        
    def get_plugins(self) -> List[PluginInterface]:
        """获取所有已加载的插件"""
        
    def clear(self) -> None:
        """清理所有已加载的插件"""
        
    def close_all(self) -> None:
        """关闭所有插件并清理资源"""
```

扫描阶段必须保持轻量：
- 优先读取 `plugin.json`
- 打包后优先读取 `plugins/plugin_index.py`
- 只有兼容回退时才允许导入插件主体
- `plugins/__init__.py` 不导入子插件

### 3.3 EventBus

```python
# core/event_bus.py
class EventBus(QObject):
    def emit(self, event_name: str, data: Any = None) -> None:
        """发布事件"""
        
    def listen(self, event_name: str, callback: Callable) -> int:
        """订阅事件，返回handler_id用于解绑"""
        
    def disconnect(self, event_name: str, handler_id: int = None) -> None:
        """解绑事件"""
        
    def disconnect_all(self) -> None:
        """解绑所有事件"""
```

### 3.4 路径工具

```python
# core/utils.py
def get_resource_path(relative_path: str) -> Path:
    """获取只读资源路径（打包后从 sys._MEIPASS）"""

def get_app_data_path(relative_path: str) -> Path:
    """获取可读写数据路径（打包后从 exe 所在目录）"""
```

## 4. 插件开发

### 4.1 插件接口

```python
# core/plugin_interface.py
class PluginInterface:
    PLUGIN_ID: str = ""
    PLUGIN_NAME: str = ""
    PLUGIN_ICON: FIF = FIF.DOCUMENT
    
    def get_id(self) -> str:
        return self.PLUGIN_ID
    
    def get_name(self) -> str:
        return self.PLUGIN_NAME
    
    def get_icon(self):
        return self.PLUGIN_ICON
    
    def initialize(self, core) -> None:
        """初始化插件"""
        
    def shutdown(self) -> None:
        """关闭插件，释放资源"""
        
    def get_widget(self, parent=None) -> QWidget:
        """获取插件界面（懒加载）"""
        
    def load_data(self) -> None:
        """加载数据（懒加载）"""
```

### 4.2 插件示例

```python
# plugins/example/__init__.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import StrongBodyLabel, FluentIcon as FIF
from core.plugin_interface import PluginInterface

class ExampleWidget(QWidget):
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(StrongBodyLabel("示例插件"))

class Plugin(PluginInterface):
    PLUGIN_ID = "example"
    PLUGIN_NAME = "示例插件"
    PLUGIN_ICON = FIF.APPLICATION
    
    def initialize(self, core) -> None:
        self.core = core
        core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")
    
    def shutdown(self) -> None:
        self.core.logger.info(f"Plugin '{self.PLUGIN_NAME}' shutdown")
    
    def get_widget(self, parent=None) -> QWidget:
        return ExampleWidget(self.core, parent)
    
    def load_data(self) -> None:
        pass
```

## 5. UI 层

### 5.1 主窗口

```python
# ui/main_window.py
class MainWindow(FluentWindow):
    def __init__(self, core):
        super().__init__()
        self._setup_home_page()      # 首页（关于页面）
        self._setup_settings_interface()  # 设置界面
        
    def register_plugin(self, plugin_id: str, icon, name: str) -> None:
        """注册插件导航项（延迟加载）"""
        
    def _on_page_changed(self, index: int) -> None:
        """页面切换事件 - 委托 PluginHost 懒加载"""
```

### 5.2 PluginHost

```python
# ui/plugin_host.py
class PluginHost:
    def create_container(self, plugin_id: str) -> QWidget:
        """创建插件容器"""

    def init_plugin_widget(self, plugin_id: str) -> bool:
        """首次进入插件页时创建 widget"""

    def load_plugin_data(self, plugin_id: str) -> None:
        """触发插件 load_data"""
```

主窗口只负责导航和显示容器；插件 widget 创建、容器注册、首次加载数据由 `PluginHost` 处理。

### 5.3 设置界面

```python
# ui/settings_interface.py
class SettingsInterface(ScrollArea):
    def __init__(self, core, parent=None):
        # 通用设置组
        # 窗口设置组
        # 数据管理组（备份/恢复）
```

## 6. 数据层

### 6.1 数据库

```python
# storage/database.py
class DatabaseManager:
    def initialize(self, db_path: str) -> None:
        """初始化数据库"""
        
    def add_category(self, plugin_id: str, name: str) -> int:
    def get_categories(self, plugin_id: str) -> List[dict]:
    def add_bookmark(self, plugin_id: str, name: str, url: str, ...) -> int:
    # ... 更多方法
```

`DatabaseManager` 仍保留旧 API，内部职责已拆分：

| 模块 | 职责 |
|------|------|
| `storage/connection.py` | SQLite 连接和 `PRAGMA foreign_keys = ON` |
| `storage/schema.py` | 建表、索引和 schema 定义 |
| `storage/migration.py` | 迁移和兼容字段补齐 |
| `storage/repository_registry.py` | Repository 初始化和集中访问 |
| `storage/import_service.py` | JSON 导入 |

复杂插件推荐 `Widget -> Service -> Repository/DatabaseManager`。Widget 不直接处理事务、缓存、校验和数据库异常。

## 7. 打包配置

```batch
# build.bat
pyinstaller --noconfirm --onedir --windowed ^
      --icon "logo.ico" ^
      --name "FluTool" ^
      --additional-hooks-dir "hooks" ^
      --collect-all qfluentwidgets ^
      --collect-submodules plugins ^
      --add-data "data;data/" ^
      --add-data "config;config/" ^
      "main.py"
```

插件打包规则：
- 不使用 `--add-data "plugins;plugins/"`，避免复制插件源码目录。
- `hooks/hook-plugins.py` 通过 `collect_submodules("plugins")` 把插件模块打入 PYZ。
- `plugins/plugin_index.py` 提供打包环境插件发现元信息。
- 打包验证时检查 `dist/FluTool/_internal/plugins` 不存在，且启动日志显示正确插件数量。

## 8. 目录结构

```
FluTool/
├── main.py                 # 应用入口
├── requirements.txt        # 依赖
├── logo.ico               # 应用图标
├── build.bat              # 打包脚本
├── config/                # 配置文件
│   └── config.json
├── data/                  # 运行时数据
│   ├── data.db           # SQLite 数据库
│   └── icons/            # 书签图标
├── core/                  # 核心服务
│   ├── app_core.py
│   ├── plugin_manager.py
│   ├── plugin_interface.py
│   ├── event_bus.py
│   ├── config.py
│   ├── utils.py
│   └── log.py
├── storage/               # 数据访问
│   ├── connection.py
│   ├── database.py
│   ├── migration.py
│   ├── repository_registry.py
│   └── schema.py
├── ui/                    # UI 层
│   ├── main_window.py
│   ├── plugin_host.py
│   └── settings_interface.py
├── hooks/                 # PyInstaller hook
│   └── hook-plugins.py
└── plugins/               # 插件
    ├── plugin_index.py
    ├── bookmark/
    ├── command/
    └── password/
```

## 9. 开发规范

### 9.1 路径获取

```python
# 正确：使用 core.utils
from core.utils import get_app_data_path, get_resource_path

# 错误：直接使用 Path(__file__)
# path = Path(__file__).parent / "data"  # 打包后路径错误
```

### 9.2 qfluentwidgets 组件

```python
# LineEdit 不接受初始文本参数
edit = LineEdit(self)
edit.setText("初始文本")  # 正确

# edit = LineEdit("初始文本", self)  # 错误

# 对话框使用 MessageBoxBase
class MyDialog(MessageBoxBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
```

### 9.3 事件总线

```python
# 订阅事件，保存 handler_id
handler_id = core.event_bus.listen("event_name", callback)

# 解绑事件
core.event_bus.disconnect("event_name", handler_id)
```

## 10. 注意事项

1. **路径问题**：打包后使用 `get_app_data_path()` 获取可写路径
2. **插件懒加载**：插件界面在首次切换时由 `PluginHost` 创建
3. **扫描轻量化**：扫描阶段读 manifest/index，不导入插件主体
4. **插件元信息**：新增插件必须维护 `plugin.json` 和 `plugins/plugin_index.py`
5. **打包约束**：插件模块进 PYZ，不复制 `plugins` 源码目录
6. **资源释放**：`shutdown()` 必须正确释放资源
7. **qfluentwidgets API**：注意组件构造函数参数差异
