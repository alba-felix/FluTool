# FluTool 开发细则

本文承接根目录 `AGENTS.md`，记录较详细的架构、目录、插件、打包和测试约定。日常任务先读 `AGENTS.md`，涉及具体模块时再读本文。

## 1. 架构摘要

FluTool 采用微内核 + 插件化架构：

```text
main.py
  -> AppCore
      -> PluginManager
      -> EventBus
      -> Config
      -> LogManager
      -> SearchManager

MainWindow
  -> PluginHost
      -> PluginInterface.get_widget()
      -> PluginInterface.load_data()

DatabaseManager
  -> DatabaseConnection
  -> SchemaManager
  -> MigrationManager
  -> RepositoryRegistry
  -> ImportService
```

核心边界：

- `core/` 不依赖 `ui/`。
- `ui/main_window.py` 处理主界面、导航、主题切换和基础页面显示。
- `ui/plugin_host.py` 处理插件容器、首次创建 widget、触发数据加载。
- 复杂插件优先拆成 `service.py`，调用链为 `Widget -> Service -> Repository/DatabaseManager`。
- `storage/database.py` 保留旧 API 兼容，具体职责转发到拆分模块。

## 2. 关键目录

```text
FluTool/
├── main.py
├── build.bat
├── config/
├── core/
│   ├── app_core.py
│   ├── plugin_manager.py
│   ├── plugin_interface.py
│   ├── event_bus.py
│   ├── log.py
│   ├── search.py
│   └── utils.py
├── storage/
│   ├── connection.py
│   ├── schema.py
│   ├── migration.py
│   ├── repository_registry.py
│   ├── import_service.py
│   ├── database.py
│   └── repositories/
├── ui/
│   ├── main_window.py
│   ├── plugin_host.py
│   └── settings_interface.py
├── hooks/
│   └── hook-plugins.py
├── plugins/
│   ├── __init__.py
│   ├── plugin_index.py
│   └── <plugin>/
│       ├── __init__.py
│       ├── plugin.json
│       └── service.py
├── tests/
└── .trae/skills/
```

## 3. 插件发现与懒加载

插件加载分为四段：

1. 扫描阶段：读取 `plugin.json` 或 `plugins/plugin_index.py`，不导入插件主体。
2. 加载阶段：`PluginManager.load_plugin()` 按需导入插件模块并调用 `initialize()`。
3. 界面阶段：首次切换页面时由 `PluginHost` 调用 `get_widget()` 创建界面。
4. 数据阶段：界面显示后由 `PluginHost` 调用 `load_data()`。

新增插件必须同步：

- `plugins/<plugin_id>/plugin.json`
- `plugins/plugin_index.py`
- 如新增动态导入或资源，检查 `hooks/hook-plugins.py` 和 `build.bat`

`plugins/__init__.py` 只能放包级轻量信息，禁止 `from . import xxx` 批量导入插件。

## 4. 插件接口最小结构

```python
class Plugin(PluginInterface):
    PLUGIN_ID = "plugin_id"
    PLUGIN_NAME = "插件名称"
    PLUGIN_ICON = FIF.DOCUMENT
    PLUGIN_PRIORITY = 999

    def initialize(self, core) -> None:
        self.core = core
        core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")

    def shutdown(self) -> None:
        self.core.logger.info(f"Plugin '{self.PLUGIN_NAME}' shutdown")

    def _create_widget(self, parent=None):
        return PluginWidget(self.core, parent)

    def _do_load_data(self) -> None:
        if self._widget is not None:
            self._widget.load_data()
```

开发细节以 `.trae/skills/plugin-dev/SKILL.md` 为准。

## 5. 数据层

`data/data.db` 是主 SQLite 数据库。常见数据包括：

- `notebook`
- `categories`
- `todo`
- `bookmark`
- `clipboard`
- `color`
- `command`
- `password`
- `app_launcher`
- `quick_copy` / `quick_copy_items`

模块职责：

| 模块 | 职责 |
| :--- | :--- |
| `storage/connection.py` | SQLite 连接管理，启用 `PRAGMA foreign_keys = ON` |
| `storage/schema.py` | 建表、索引和 schema 定义 |
| `storage/migration.py` | 迁移和兼容字段补齐 |
| `storage/repository_registry.py` | Repository 初始化和集中访问 |
| `storage/import_service.py` | JSON 导入 |
| `storage/database.py` | 兼容门面，保留旧调用入口 |

## 6. 打包规则

`build.bat` 使用 PyInstaller。插件模块应进入 PYZ；运行时 `data/`、`config/` 由 `core/runtime_layout.py` 在 exe 同级或开发环境项目根目录创建，不作为打包资源复制：

```batch
pyinstaller --noconfirm --onedir --windowed ^
  --icon "logo.ico" ^
  --name "FluTool" ^
  --additional-hooks-dir "hooks" ^
  --collect-all qfluentwidgets ^
  --collect-submodules plugins ^
  --add-data "logo.ico;." ^
  --add-data "ui/resources;ui/resources/" ^
  "main.py"
```

打包检查：

- 不使用 `--add-data "plugins;plugins/"`。
- 不使用 `--add-data "data;data/"` 和 `--add-data "config;config/"`。
- `hooks/hook-plugins.py` 收集插件子模块。
- `plugins/plugin_index.py` 提供打包环境插件发现元信息。
- `dist/FluTool/_internal/plugins` 不应作为源码目录存在，`dist/FluTool/data` 和 `dist/FluTool/config` 应由首次启动创建。
- 启动日志应显示正确插件数量，例如 `Application started ..., 21 plugins loaded`。

## 7. 测试

推荐命令：

```bash
pytest -q --basetemp=.pytest_tmp
```

说明：

- Windows 下使用 `--basetemp=.pytest_tmp` 可避开默认 Temp 权限问题。
- 测试放在 `tests/`。
- 优先覆盖核心模块、仓库、service、插件扫描、打包元信息。
- 测试后可清理 `.pytest_tmp*`、`tests/__pycache__`、`tests/*.log`。

## 8. 开发约定

- 优先使用卫语句处理边界情况。
- 关键类、方法和复杂逻辑写中文注释，避免解释无意义赋值。
- QFluentWidgets 组件 API 和 PyQt 原生组件不同，使用前参考现有插件或 `.trae/skills/plugin-dev/SKILL.md`。
- 主题切换相关逻辑避免一次性重刷大量组件；必要时显示提示并延迟刷新。
- 路径使用 `core.utils.get_resource_path()` / `get_app_data_path()`。
