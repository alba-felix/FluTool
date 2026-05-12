# FluTool Agent Guide

> 面向开发者和 AI 编码助手。这里保留必须先知道的项目规则；详细架构、插件、打包和测试说明见 `docs/development_guide.md` 与 `.trae/skills/`。

## 项目概览

- FluTool 是 Windows 优先的 PyQt5 + QFluentWidgets 多功能工具箱。
- 架构是微内核 + 插件化：核心服务在 `core/`，插件在 `plugins/`，UI 在 `ui/`，数据访问在 `storage/`。
- 插件扫描必须轻量：开发环境读 `plugin.json`，打包环境读 `plugins/plugin_index.py`，不要在扫描阶段导入插件主体。
- 插件 UI 生命周期由 `ui/plugin_host.py` 管理，`ui/main_window.py` 只负责导航和显示。
- `storage/database.py` 是兼容门面；连接、schema、迁移、仓库注册和导入服务已拆到 `storage/connection.py`、`schema.py`、`migration.py`、`repository_registry.py`、`import_service.py`。

## 必守规则

1. `core/` 不得依赖 `ui/`。
2. `plugins/__init__.py` 必须保持轻量，禁止导入子插件。
3. 新增或改名插件时同步 `plugins/<plugin>/plugin.json` 和 `plugins/plugin_index.py`。
4. 打包不要恢复 `--add-data "plugins;plugins/"`；插件通过 `hooks/hook-plugins.py` / `--collect-submodules plugins` 收集。
5. 复杂插件按 `Widget -> Service -> Repository/DatabaseManager` 拆分，Widget 不直接承载事务、校验和数据库异常处理。
6. 路径使用 `core.utils.get_resource_path()` / `get_app_data_path()`，不要硬编码本机路径。
7. 数据库连接必须启用外键约束，相关逻辑集中在连接层。
8. 关键流程使用 `LogManager` 记录日志，异常日志要保留上下文。

## 按需阅读

| 场景 | 文档 |
| :--- | :--- |
| 当前架构、目录、打包、测试细则 | `docs/development_guide.md` |
| 插件开发 | `.trae/skills/plugin-dev/SKILL.md` |
| 全局搜索接入 | `.trae/skills/global-search/SKILL.md` |
| 架构关系图和调用链 | `.trae/skills/codemap/SKILL.md` |
| AI 助手架构 | `docs/ai_architecture_v0_1.md` |

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
.venv\Scripts\python.exe main.py

# 运行测试，避免 Windows 默认 Temp 权限问题
pytest -q --basetemp=.pytest_tmp

# 打包
build.bat
```

## 修改前检查

- 改插件：先看 `.trae/skills/plugin-dev/SKILL.md`。
- 改全局搜索：先看 `.trae/skills/global-search/SKILL.md`。
- 改插件发现、打包、数据库拆分或主窗口生命周期：先看 `docs/development_guide.md`。
- 提交前至少运行相关测试；如果无法运行，要在回复中说明原因。
