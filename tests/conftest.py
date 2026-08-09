"""pytest 全局夹具。

解决两类环境性失败：
1. 各测试文件各自创建 QApplication，fixture 结束后对象被 GC 回收，
   连带 qfluentwidgets 全局 qconfig 等 QObject 被销毁，后续模块级单例
   再使用时抛 "wrapped C/C++ object has been deleted"。
   这里在会话级创建唯一 QApplication 并持有强引用。
2. 开发环境下 get_app_data_path() 直指项目根 data/ 目录，测试一旦触达
   会读写真实数据，并可能与正在运行的应用程序产生 PermissionError。
   这里把各模块已绑定的路径函数重定向到每个测试独立的临时目录。
"""

import importlib
import sys

import pytest

# 全局 QApplication 强引用，防止 GC 提前回收 Qt 单例。
_BOOTSTRAP_APP = None


@pytest.fixture(scope="session", autouse=True)
def qapp_session():
    """会话级唯一 QApplication，跨测试文件复用，避免对象销毁串扰。"""
    global _BOOTSTRAP_APP
    from PyQt5.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    _BOOTSTRAP_APP = app
    yield app


# 可能以 from ... import get_app_data_path 绑定形式持有路径函数的核心模块。
_APP_PATH_BINDERS = (
    "core",
    "core.utils",
    "core.app_core",
    "core.api_key_manager",
    "core.backup_manager",
    "core.runtime_layout",
    "core.settings",
    "core.ai.providers.deepseek",
)


@pytest.fixture(autouse=True)
def _isolate_app_data_dirs(tmp_path, monkeypatch):
    """把应用数据/资源路径重定向到本用例独立的临时目录，隔离真实 data/。"""
    data_dir = tmp_path / "app_data"
    resource_dir = tmp_path / "resources"

    for module_name in _APP_PATH_BINDERS:
        try:
            module = importlib.import_module(module_name)
        except Exception:
            # 该模块可能依赖高成本环境（如 PyInstaller 冻结），跳过。
            continue
        if hasattr(module, "get_app_data_path"):
            monkeypatch.setattr(module, "get_app_data_path",
                                lambda rel, _data=data_dir: _data / rel)
        if hasattr(module, "get_resource_path"):
            monkeypatch.setattr(module, "get_resource_path",
                                lambda rel, _res=resource_dir: _res / rel)
        if hasattr(module, "get_local_app_data_dir"):
            monkeypatch.setattr(module, "get_local_app_data_dir",
                                lambda _data=data_dir: _data)

    yield data_dir