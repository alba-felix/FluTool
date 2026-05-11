# SKILL.md - FluTool 插件开发指南

## 1. 插件开发流程

### 1.1 创建插件目录

```
plugins/
└── my_plugin/
    ├── __init__.py    # 插件入口文件，定义 Plugin 和 Widget
    ├── plugin.json    # 插件扫描元信息
    └── service.py     # 业务逻辑层，复杂插件必须拆出
```

新增插件后必须同步：
- `plugins/my_plugin/plugin.json`
- `plugins/plugin_index.py`
- 如新增动态依赖，补 `build.bat` hidden import 或 `hooks/hook-plugins.py`

不要在 `plugins/__init__.py` 中导入新插件。该文件必须保持轻量，否则会破坏懒加载。

### 1.2 插件基本结构

```python
# plugins/my_plugin/__init__.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import StrongBodyLabel, FluentIcon as FIF
from core.plugin_interface import PluginInterface
from .service import MyPluginService


class MyPluginWidget(QWidget):
    """插件界面"""
    
    PLUGIN_ID = "my_plugin"  # 业务类也可访问
    
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.service = MyPluginService(core)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """构建界面"""
        layout = QVBoxLayout(self)
        layout.addWidget(StrongBodyLabel("我的插件"))
    
    def load_data(self) -> None:
        """加载数据"""
        pass


class Plugin(PluginInterface):
    """插件类"""
    
    PLUGIN_ID = "my_plugin"
    PLUGIN_NAME = "我的插件"
    PLUGIN_ICON = FIF.APPLICATION
    PLUGIN_PRIORITY = 50
    
    def initialize(self, core) -> None:
        self.core = core
        core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")
    
    def shutdown(self) -> None:
        self.core.logger.info(f"Plugin '{self.PLUGIN_NAME}' shutdown")
    
    def _create_widget(self, parent=None) -> QWidget:
        return MyPluginWidget(self.core, parent)
    
    def _do_load_data(self) -> None:
        if self._widget is not None:
            self._widget.load_data()
```

## 2. 插件元信息

### 2.1 Python 类元信息

```python
class Plugin(PluginInterface):
    PLUGIN_ID = "unique_id"      # 唯一标识，用于数据库关联
    PLUGIN_NAME = "显示名称"      # 导航栏显示
    PLUGIN_ICON = FIF.APPLICATION  # 导航图标
    PLUGIN_PRIORITY = 50         # 侧边栏排序，数字越小越靠前
```

### 2.2 plugin.json

`plugin.json` 是扫描阶段的主要元信息来源。扫描插件时不能导入插件主体模块。

```json
{
  "id": "my_plugin",
  "name": "我的插件",
  "priority": 50,
  "module": "plugins.my_plugin"
}
```

### 2.3 plugins/plugin_index.py

打包环境不依赖外置 `plugin.json` 或源码目录。新增内置插件时必须把轻量元信息加入 `BUILTIN_PLUGIN_MANIFESTS`：

```python
{"package": "my_plugin", "id": "my_plugin", "priority": 50, "module": "plugins.my_plugin"}
```

`plugin_index.py` 只能放元信息，禁止导入插件模块或 UI 模块。

### 2.4 打包约束

- `build.bat` 使用 `--additional-hooks-dir "hooks"` 和 `hooks/hook-plugins.py` 收集插件模块。
- 不要使用 `--add-data "plugins;plugins/"` 复制插件源码目录。
- 打包后验证 `dist/FluTool/_internal/plugins` 不应存在。
- 打包后日志应出现 `Application started ..., 21 plugins loaded` 或新插件加入后的正确数量。

## 3. 数据库使用

复杂插件不要让 Widget 直接持有 `DatabaseManager()`。推荐依赖链：

```
Widget -> Service -> Repository/DatabaseManager
```

Widget 只负责 UI 状态和交互；Service 负责校验、事务、日志、异常转换；Repository/DatabaseManager 负责数据访问。

### 3.1 分类管理

```python
# 添加分类
category_id = self.db.add_category(self.PLUGIN_ID, "分类名称")

# 获取分类列表
categories = self.db.get_categories(self.PLUGIN_ID)
# 返回: [{'id': 1, 'name': '分类名称', ...}, ...]

# 删除分类
self.db.delete_category(self.PLUGIN_ID, category_id)
```

### 3.2 书签管理

```python
# 添加书签
bookmark_id = self.db.add_bookmark(
    plugin_id=self.PLUGIN_ID,
    name="网站名称",
    url="https://example.com",
    icon="data/icons/example.ico",
    category_name="分类名称",
    notes="备注"
)

# 获取书签列表
bookmarks = self.db.get_bookmarks(self.PLUGIN_ID, category_id=None)

# 更新书签
self.db.update_bookmark(self.PLUGIN_ID, bookmark_id, name="新名称")

# 删除书签
self.db.delete_bookmark(self.PLUGIN_ID, bookmark_id)
```

### 3.3 命令管理

```python
# 添加命令
command_id = self.db.add_command(
    plugin_id=self.PLUGIN_ID,
    name="命令名称",
    content="命令内容",
    category_name="分类名称",
    sub_title="副标题"
)

# 获取命令列表
commands = self.db.get_commands(self.PLUGIN_ID, category_id=None)

# 更新命令
self.db.update_command(self.PLUGIN_ID, command_id, name="新名称")

# 删除命令
self.db.delete_command(self.PLUGIN_ID, command_id)
```

## 4. UI 组件使用

### 4.1 布局

```python
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QFormLayout
from PyQt5.QtCore import Qt

# 垂直布局
layout = QVBoxLayout(self)
layout.setContentsMargins(20, 20, 20, 20)
layout.setSpacing(12)

# 水平布局
h_layout = QHBoxLayout()
h_layout.setSpacing(8)

# 表单布局
form = QFormLayout()
form.addRow("标签:", widget)
```

### 4.2 常用组件

```python
from qfluentwidgets import (
    StrongBodyLabel,    # 加粗标签
    BodyLabel,          # 普通标签
    CaptionLabel,       # 小号标签
    LineEdit,           # 单行输入框
    TextEdit,           # 多行输入框
    PushButton,         # 按钮
    ComboBox,           # 下拉框
    TreeWidget,         # 树形列表
    InfoBar,            # 提示条
    InfoBarPosition,
    FluentIcon as FIF,
    MessageBoxBase,     # 对话框基类
    SubtitleLabel,
)

# 标签
title = StrongBodyLabel("标题")

# 输入框（注意：不接受初始文本参数）
edit = LineEdit(self)
edit.setPlaceholderText("提示文本")
edit.setClearButtonEnabled(True)
edit.setText("初始文本")  # 用 setText 设置初始值

# 按钮
btn = PushButton("按钮文字", self)
btn.setIcon(FIF.ADD)
btn.clicked.connect(self._on_click)

# 提示条
InfoBar.success(
    title="成功",
    content="操作成功",
    orient=Qt.Horizontal,
    isClosable=True,
    position=InfoBarPosition.TOP,
    duration=2000,
    parent=self
)
```

### 4.3 对话框

```python
from qfluentwidgets import MessageBoxBase, SubtitleLabel, LineEdit
from PyQt5.QtWidgets import QFormLayout

class MyDialog(MessageBoxBase):
    def __init__(self, parent=None, default_value=""):
        super().__init__(parent)
        
        self.titleLabel = SubtitleLabel('对话框标题', self)
        self.viewLayout.addWidget(self.titleLabel)
        
        form = QFormLayout()
        
        self.name_input = LineEdit(self)
        self.name_input.setText(default_value)
        form.addRow("名称:", self.name_input)
        
        self.viewLayout.addLayout(form)
        
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(400)
    
    def validate(self) -> bool:
        """验证表单，返回 False 阻止关闭"""
        return bool(self.name_input.text().strip())
    
    def get_value(self) -> str:
        return self.name_input.text().strip()

# 使用
dialog = MyDialog(self, "默认值")
if dialog.exec():
    value = dialog.get_value()
```

## 5. 路径处理

```python
import sys
from pathlib import Path

def get_app_data_path(relative_path: str) -> Path:
    """获取可读写数据路径"""
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).parent.parent.parent
    return base_path / relative_path

# 使用
icons_dir = get_app_data_path("data/icons")
icons_dir.mkdir(parents=True, exist_ok=True)
```

## 6. 事件总线

```python
# 订阅事件
handler_id = self.core.event_bus.listen("event_name", self._on_event)

def _on_event(self, data):
    print(f"收到事件: {data}")

# 发布事件
self.core.event_bus.emit("event_name", {"key": "value"})

# 解绑事件
self.core.event_bus.disconnect("event_name", handler_id)
```

## 7. 日志

```python
# 使用核心日志
self.core.logger.info("信息日志")
self.core.logger.warning("警告日志")
self.core.logger.error("错误日志")
```

## 8. 样式定制

```python
from qfluentwidgets import setCustomStyleSheet, isDarkTheme

# 设置透明背景
self.setObjectName("myWidget")
setCustomStyleSheet(
    self,
    "QWidget#myWidget { background-color: transparent; }",
    "QWidget#myWidget { background-color: transparent; }"
)

# 根据主题切换样式
if isDarkTheme():
    qss = "QLabel { color: white; }"
else:
    qss = "QLabel { color: black; }"
```

## 9. 完整示例

参考现有插件：
- `plugins/bookmark/__init__.py` - 书签管理插件
- `plugins/command/__init__.py` - 命令管理插件

## 10. 注意事项

1. **插件ID唯一**：`PLUGIN_ID` 必须全局唯一
2. **元信息同步**：新增插件必须同步 `plugin.json` 和 `plugins/plugin_index.py`
3. **禁止包级导入插件**：不要在 `plugins/__init__.py` 中导入插件
4. **资源释放**：`shutdown()` 中释放所有资源
5. **懒加载**：实现 `_create_widget()`，不要在 `initialize()` 创建 UI
6. **数据加载**：实现 `_do_load_data()`，只在 widget 已创建时刷新界面
7. **路径问题**：使用 `get_app_data_path()` 获取可写路径
8. **业务解耦**：复杂插件使用 service/repository，Widget 不直接承载数据库事务
9. **组件API**：qfluentwidgets 组件参数与 PyQt5 原生组件有差异
