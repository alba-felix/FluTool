# FluTool 项目指南

> **面向对象**：开发者 / AI 编码助手（Cursor/Codex/Trae）
> **目标**：构建一款基于 PyQt5 和 QFluentWidgets 的多功能工具箱应用，遵循模块化、可测试、可扩展的开发原则。

***

## 1. 项目简介

### 1.1 应用定位

- **核心理念**：一站式工具箱应用，集成多种实用工具
- **技术栈**：PyQt5 + QFluentWidgets，现代 Fluent Design 风格
- **架构特点**：插件化架构，高内聚低耦合，易于扩展
- **运行环境**：Windows, Python 3.8+

### 1.2 核心系统

- **插件系统**：模块化插件架构，支持懒加载和热插拔
- **数据存储**：SQLite 数据库统一管理，支持数据备份恢复
- **全局搜索**：跨插件内容搜索，快速定位信息
- **AI 助手**：集成 AI 聊天功能，支持多种 AI 提供商
- **效率模式**：支持进程效率优化，降低资源占用

### 1.3 技术栈

| 组件 | 选型 |
| :--- | :--- |
| 语言 | Python 3.8+ |
| GUI 框架 | PyQt5 + QFluentWidgets |
| 数据库 | SQLite (通过 sqlite3) |
| 日志 | 自定义 LogManager |
| 测试 | Pytest (待实现) |

***

## 2. 文件与模块导航

### 2.1 项目目录结构

```
FluTool/
├── README.md
├── requirements.txt
├── AGENTS.md                 # 本指南（项目概述 + 模块导航）
├── build.bat                 # 打包脚本
├── main.py                   # 程序入口
├── logo.ico                  # 应用图标
├── config/
│   ├── config.json           # 全局配置文件
│   ├── ai_settings.json      # AI 设置配置
│   └── ai_providers.json     # AI 提供商配置
├── core/
│   ├── __init__.py
│   ├── app_core.py           # 应用核心单例类
│   ├── config.py             # 配置管理
│   ├── settings.py           # AI 设置管理器
│   ├── plugin_manager.py     # 插件管理器
│   ├── plugin_interface.py   # 插件接口基类
│   ├── event_bus.py          # 全局事件总线
│   ├── log.py                # 日志管理器
│   ├── search.py             # 全局搜索管理器
│   ├── backup_manager.py     # 备份管理器
│   ├── efficiency_mode.py    # 效率模式设置
│   ├── utils.py              # 工具函数
│   └── ai/
│       ├── __init__.py
│       ├── chat_service.py   # AI 聊天服务
│       ├── provider_base.py  # AI 提供商基类
│       ├── settings_bridge.py # AI 设置桥接
│       ├── search_bridge.py  # AI 搜索桥接
│       ├── types.py          # AI 类型定义
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── ollama.py     # Ollama 提供商
│       │   └── openai_compatible.py # OpenAI 兼容提供商
├── storage/
│   ├── __init__.py
│   ├── database.py           # 数据库管理器
│   ├── password_manager.py   # 密码管理器
│   ├── app_launcher_manager.py # 应用启动器管理
│   ├── models/
│   │   └── __init__.py       # 数据模型
│   └── repositories/
│       ├── __init__.py
│       ├── base.py           # 仓库基类
│       ├── ai_repository.py
│       ├── app_repository.py
│       ├── bookmark_repository.py
│       ├── category_repository.py
│       ├── clipboard_repository.py
│       ├── color_repository.py
│       ├── command_repository.py
│       ├── folder_tree_repository.py
│       ├── notebook_repository.py
│       ├── password_repository.py
│       ├── quick_copy_repository.py
│       ├── script_repository.py
│       └── todo_repository.py
├── ui/
│   ├── __init__.py
│   ├── main_window.py        # 主窗口
│   ├── global_search_dialog.py # 全局搜索对话框
│   ├── settings_interface.py # 设置界面
│   ├── translator_window.py  # 翻译窗口
│   ├── more_menu.py          # 更多菜单
│   ├── custom_icon.py        # 自定义图标
│   ├── common/
│   │   └── __init__.py       # 通用对话框
│   └── resources/            # UI 资源文件（SVG 图标等）
├── plugins/                  # 插件目录
│   ├── __init__.py
│   ├── ai_assistant/         # AI 助手插件
│   ├── app_launcher/         # 应用启动器
│   ├── bookmark/             # 书签管理
│   ├── clipboard/            # 剪贴板管理
│   ├── color_palette/        # 取色器
│   ├── command/              # 命令工具
│   ├── dev_tools/            # 开发工具
│   ├── environment/          # 环境变量
│   ├── folder_tree/          # 文件夹树
│   ├── image_assistant/      # 图片助手
│   ├── network/              # 网络工具
│   ├── notebook/             # 随手记
│   ├── password/             # 密码管理
│   ├── quick_copy/           # 快速复制
│   ├── script_manager/       # 脚本管理
│   ├── system_tools/         # 系统工具
│   ├── text_compare/         # 文本对比
│   ├── text_tools/           # 文本工具
│   ├── time_converter/       # 时间转换
│   └── todo/                 # 待办事项
├── utils/
│   ├── __init__.py
│   └── crypto_utils.py       # 加密工具
└── tests/                    # 测试目录（待实现）
    └── __init__.py
```

### 2.2 核心模块职责

| 模块 | 路径 | 核心职责 |
| :--- | :--- | :--- |
| **应用核心** | `core/app_core.py` | 单例类，管理插件、事件、配置、日志等 |
| **插件管理** | `core/plugin_manager.py` | 插件扫描、加载、卸载、生命周期管理 |
| **插件接口** | `core/plugin_interface.py` | 插件基类，定义插件规范 |
| **事件总线** | `core/event_bus.py` | 全局事件发布订阅 |
| **日志管理** | `core/log.py` | 应用日志和操作日志记录 |
| **配置管理** | `core/config.py` | 应用配置加载保存 |
| **全局搜索** | `core/search.py` | 跨插件内容搜索 |
| **备份管理** | `core/backup_manager.py` | 数据备份与恢复 |
| **效率模式** | `core/efficiency_mode.py` | 进程效率优化 |
| **数据库** | `storage/database.py` | SQLite 数据库连接管理 |
| **密码管理** | `storage/password_manager.py` | 密码加密存储 |
| **数据仓库** | `storage/repositories/` | 各模块数据访问层 |
| **主窗口** | `ui/main_window.py` | 应用主界面 |
| **全局搜索** | `ui/global_search_dialog.py` | 全局搜索 UI |
| **设置界面** | `ui/settings_interface.py` | 应用设置 UI |

### 2.3 插件接口设计

所有插件必须继承 `PluginInterface` 基类，实现以下核心方法：

```python
class Plugin(PluginInterface):
    """插件示例"""
    
    PLUGIN_ID = "plugin_id"        # 插件唯一标识
    PLUGIN_NAME = "插件名称"        # 插件显示名称
    PLUGIN_ICON = FIF.DOCUMENT     # 插件图标
    PLUGIN_PRIORITY = 999          # 插件优先级（数值越小优先级越高）
    
    def initialize(self, core) -> None:
        """初始化插件（轻量操作）"""
        self.core = core
        core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")
    
    def shutdown(self) -> None:
        """关闭插件，释放资源"""
        self.core.logger.info(f"Plugin '{self.PLUGIN_NAME}' shutdown")
    
    def _create_widget(self, parent=None) -> QWidget:
        """创建插件界面（懒加载）"""
        self._widget = PluginWidget(self.core, parent)
        return self._widget
    
    def _do_load_data(self) -> None:
        """加载数据（异步调用）"""
        if self._widget is None:
            return
        self._widget.load_data()
    
    def supports_search(self) -> bool:
        """是否支持全局搜索"""
        return True
    
    def search(self, query: str):
        """搜索接口"""
        # 实现搜索逻辑
        return []
```

### 2.4 懒加载机制

插件系统采用三级懒加载：

1. **initialize()** - 插件加载时调用（轻量初始化）
2. **get_widget()** - 首次切换到插件页面时调用（创建界面）
3. **load_data()** - 界面显示后异步调用（加载数据）

### 2.5 模块依赖关系

```
AppCore → PluginManager, EventBus, LogManager, Config, SearchManager
PluginManager → PluginInterface
GlobalSearchManager → PluginInterface (supports_search)
EventBus → 全局事件发布订阅
DatabaseManager → Repositories → Models
```

> **重要**：核心模块（`core/`）不依赖 UI 模块（`ui/`），保证可测试性。

***

## 3. 数据配置

### 3.1 配置文件

所有静态配置位于 [`config/`](config/) 目录下：

| 文件 | 内容 |
| :--- | :--- |
| `config.json` | 全局应用配置（主题、效率模式、备份设置等） |
| `ai_settings.json` | AI 聊天设置（提供商、API Key、模型等） |
| `ai_providers.json` | AI 提供商配置列表 |

### 3.2 数据库结构

应用使用 SQLite 数据库 (`data/data.db`) 存储动态数据：

- **notebook** - 随手记笔记
- **categories** - 分类管理
- **todo** - 待办事项
- **bookmark** - 书签
- **clipboard** - 剪贴板历史
- **color** - 颜色收藏
- **command** - 命令历史
- **password** - 密码记录（加密）
- **app_launcher** - 应用启动记录
- 等等...

详细数据库结构请参阅 [`storage/database.py`](storage/database.py)。

***

## 4. 开发原则（优先级从高到低）

1. **模块化优先**：核心逻辑与 UI 解耦，便于单独测试
2. **高内聚低耦合**：各模块职责单一，依赖关系清晰
3. **清晰优先于兼容**：开发阶段不保证向前兼容，新代码以清晰、合理为首要目标
4. **日志与调试优先**：关键路径必须包含结构化日志
5. **卫语句优先**：使用卫语句处理边界情况，避免嵌套条件
6. **函数式编程**：避免复杂循环和递归，优先使用函数式编程风格

***

## 5. 编码规范

### 5.1 代码风格

- 基于 **PyQt5** 框架开发，使用 **QFluentWidgets** 组件库
- 优先使用 **卫语句（Guard Clauses）** 处理边界情况
- 避免复杂的循环和递归，优先使用 Python 的函数式编程风格
- 变量全局唯一，避免命名冲突

### 5.2 注释规范

- 关键性注释、函数和方法的注释、类的注释要简洁明了
- 包括类的属性和方法都需要注释
- 注释使用中文，清晰表达意图

### 5.3 插件开发

- 输入词中有"插件"时，参考 `.trae\skills\plugin-dev\SKILL.md`
- 所有插件必须继承 `PluginInterface` 基类
- 插件必须实现 `initialize()`, `shutdown()`, `_create_widget()` 方法
- 可选实现 `supports_search()`, `search()`, `_do_load_data()` 方法

### 5.4 全局搜索

- 输入词中有"全局搜索"时，参考 `.trae\skills\global-search\SKILL.md`
- 实现 `supports_search()` 返回 `True`
- 实现 `search(query)` 方法返回 `SearchResult` 列表

***

## 6. 常用命令

| 操作 | 命令 |
| :--- | :--- |
| 运行应用 | `python main.py` |
| 安装依赖 | `pip install -r requirements.txt` |
| 打包应用 | `build.bat` |
| 运行测试 | `pytest` (待实现) |

***

## 7. 维护约定

### 硬约束

1. **新增可注册模块**（如动作、事件）必须在对应 `__init__.py` 中导入
2. **核心模块不得依赖 UI 模块**（`core/` 不 `import ui/`）
3. **日志使用 LogManager**，关键流程必须打点
4. **开发阶段不要求向前兼容**，清晰代码优先
5. **测试要求**：核心模块覆盖率 ≥ 80%，路径禁止硬编码
6. **测试在 tests 目录下**编写

### 插件优先级

插件优先级数值越小，在侧边栏中显示越靠前：

- 优先级 1-10：核心功能插件（如随手记、待办、书签等）
- 优先级 11-500：常用工具插件
- 优先级 501-999：辅助功能插件
- 默认优先级：999

***

## 8. 文档导航

| 文档 | 内容 |
| :--- | :--- |
| [docs/ai_architecture_v0_1.md](docs/ai_architecture_v0_1.md) | AI 助手架构设计 |
| [README.md](README.md) | 项目概述与使用说明 |
| [requirements.txt](requirements.txt) | 项目依赖列表 |

***

## 9. 快速开始

### 9.1 环境搭建

```bash
# 创建虚拟环境（推荐）
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 9.2 运行应用

```bash
.venv\Scripts\python.exe main.py
```

### 9.3 开发新插件

1. 在 `plugins/` 目录创建新插件文件夹
2. 创建 `__init__.py`，定义继承 `PluginInterface` 的 `Plugin` 类
3. 实现 `initialize()`, `shutdown()`, `_create_widget()` 方法
4. 可选实现 `_do_load_data()`, `supports_search()`, `search()` 方法
5. 设置 `PLUGIN_ID`, `PLUGIN_NAME`, `PLUGIN_ICON`, `PLUGIN_PRIORITY` 常量

***

## 10. 参考资料

- [QFluentWidgets 官方文档](https://pyqt-fluent-widgets.readthedocs.io/zh-cn/latest/autoapi/index.html)
- 本地文档：`.venv\Lib\site-packages\qfluentwidgets\`
- 插件开发指南：`.trae\skills\plugin-dev\SKILL.md`
- 全局搜索指南：`.trae\skills\global-search\SKILL.md`
