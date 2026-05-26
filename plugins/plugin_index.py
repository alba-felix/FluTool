"""内置插件索引。

这里只记录插件元信息，不导入插件模块，供打包环境稳定发现插件。
"""

BUILTIN_PLUGIN_MANIFESTS = [
    {"package": "quick_copy", "id": "quick_copy", "priority": 0, "module": "plugins.quick_copy"},
    {"package": "bookmark", "id": "bookmark", "priority": 1, "module": "plugins.bookmark"},
    {"package": "command", "id": "command", "priority": 2, "module": "plugins.command"},
    {"package": "password", "id": "password", "priority": 3, "module": "plugins.password"},
    {"package": "time_converter", "id": "time_converter", "priority": 4, "module": "plugins.time_converter"},
    {"package": "system_tools", "id": "system_tools", "priority": 5, "module": "plugins.system_tools"},
    {"package": "notebook", "id": "notebook", "priority": 6, "module": "plugins.notebook"},
    {"package": "ai_assistant", "id": "ai_assistant", "priority": 8, "module": "plugins.ai_assistant"},
    {"package": "text_tools", "id": "text_tools", "priority": 8.2, "module": "plugins.text_tools"},
    {"package": "dev_tools", "id": "dev_tools", "priority": 8.3, "module": "plugins.dev_tools"},
    {"package": "clipboard", "id": "clipboard", "priority": 10, "module": "plugins.clipboard"},
    {"package": "todo", "id": "todo", "priority": 11, "module": "plugins.todo"},
    {"package": "image_assistant", "id": "image_assistant", "priority": 15, "module": "plugins.image_assistant"},
    {"package": "color_palette", "id": "color_palette", "priority": 13, "module": "plugins.color_palette"},
    {"package": "script_manager", "id": "script_manager", "priority": 14, "module": "plugins.script_manager"},
    {"package": "app_launcher", "id": "app_launcher", "priority": 12, "module": "plugins.app_launcher"},
    {"package": "folder_tree", "id": "folder_tree", "priority": 16, "module": "plugins.folder_tree"},
    {"package": "text_compare", "id": "text_compare", "priority": 17, "module": "plugins.text_compare"},
    {"package": "environment", "id": "environment", "priority": 18, "module": "plugins.environment"},
    {"package": "network", "id": "network", "priority": 19, "module": "plugins.network"},
    {"package": "toolkit", "id": "toolkit", "priority": 999, "module": "plugins.toolkit"},
]

BUILTIN_PLUGIN_PACKAGES = [manifest["package"] for manifest in BUILTIN_PLUGIN_MANIFESTS]
