"""
插件元信息读取抽象层

提供统一的插件元信息数据抽象和策略模式的读取器框架，
支持多种 manifest 格式（plugin.py、plugin.json），
并可通过注册新的读取器来扩展。
"""

import ast
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional


@dataclass
class PluginManifest:
    """插件元信息数据类，替代原始的元组返回值"""

    plugin_id: str
    priority: float = 999.0
    module_name: Optional[str] = None
    source: str = ""

    @property
    def is_valid(self) -> bool:
        return bool(self.plugin_id)


# ─── 规范化工具函数 ──────────────────────────────────────────


def normalize_string(value: Any) -> Optional[str]:
    """规范化字符串字段"""
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def normalize_priority(value: Any) -> float:
    """规范化优先级字段"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 999.0


def normalize_manifest_from_dict(
    manifest: dict,
    source: str,
) -> Optional[PluginManifest]:
    """从字典中提取并规范化 manifest 字段"""
    plugin_id = normalize_string(manifest.get("id"))
    if not plugin_id:
        return None

    priority = normalize_priority(manifest.get("priority", 999))
    module_name = normalize_string(manifest.get("module"))
    return PluginManifest(
        plugin_id=plugin_id,
        priority=priority,
        module_name=module_name,
        source=source,
    )


# ─── 读取器接口 ──────────────────────────────────────────────


class ManifestReader(ABC):
    """插件元信息读取器接口"""

    @abstractmethod
    def can_read(self, location: Path) -> bool:
        """检查是否可以读取该位置的 manifest"""
        ...

    @abstractmethod
    def read(self, location: Path, logger) -> Optional[PluginManifest]:
        """读取并解析 manifest，失败返回 None"""
        ...


# ─── 具体读取器 ──────────────────────────────────────────────


class PyManifestReader(ManifestReader):
    """plugin.py 格式的 manifest 读取器"""

    MANIFEST_FILENAME = "plugin.py"

    def can_read(self, location: Path) -> bool:
        return (location / self.MANIFEST_FILENAME).is_file()

    def read(self, location: Path, logger) -> Optional[PluginManifest]:
        manifest_file = location / self.MANIFEST_FILENAME
        source = str(manifest_file)

        try:
            content = manifest_file.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read {source}: {e}")
            return None

        return self._parse_py_manifest(content, source, logger)

    def _parse_py_manifest(
        self,
        content: str,
        source: str,
        logger,
    ) -> Optional[PluginManifest]:
        """解析 plugin.py 中的 PLUGIN_MANIFEST 字典"""
        try:
            tree = ast.parse(content, filename=source)
        except SyntaxError as e:
            logger.error(f"Failed to parse {source}: {e}")
            return None

        manifest = None
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "PLUGIN_MANIFEST":
                        try:
                            manifest = ast.literal_eval(node.value)
                        except (ValueError, SyntaxError) as e:
                            logger.error(
                                f"Failed to evaluate PLUGIN_MANIFEST in {source}: {e}"
                            )
                            return None
                        break
                if manifest is not None:
                    break

        if not isinstance(manifest, dict):
            logger.warning(f"PLUGIN_MANIFEST must be a dict in {source}")
            return None

        result = normalize_manifest_from_dict(manifest, source)
        if result is None:
            logger.warning(f"Plugin manifest missing id: {source}")
        return result


class JsonManifestReader(ManifestReader):
    """plugin.json 格式的 manifest 读取器"""

    MANIFEST_FILENAME = "plugin.json"

    def can_read(self, location: Path) -> bool:
        return (location / self.MANIFEST_FILENAME).is_file()

    def read(self, location: Path, logger) -> Optional[PluginManifest]:
        manifest_file = location / self.MANIFEST_FILENAME
        source = str(manifest_file)

        try:
            content = manifest_file.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read {source}: {e}")
            return None

        return self._parse_json_manifest(content, source, logger)

    def _parse_json_manifest(
        self,
        content: str,
        source: str,
        logger,
    ) -> Optional[PluginManifest]:
        """解析 plugin.json 内容"""
        try:
            manifest = json.loads(content)
        except Exception as e:
            logger.error(f"Failed to parse {source}: {e}")
            return None

        if not isinstance(manifest, dict):
            logger.warning(f"Plugin manifest must be an object: {source}")
            return None

        result = normalize_manifest_from_dict(manifest, source)
        if result is None:
            logger.warning(f"Plugin manifest missing id: {source}")
        return result


# ─── 读取器工厂 ──────────────────────────────────────────────

MANIFEST_FILENAMES = ("plugin.py", "plugin.json")


class ManifestReaderFactory:
    """插件元信息读取器工厂，管理多个策略读取器"""

    def __init__(self):
        self._readers: List[ManifestReader] = []
        self._register_default_readers()

    def _register_default_readers(self):
        """注册默认的读取器"""
        self.register_reader(PyManifestReader())
        self.register_reader(JsonManifestReader())

    def register_reader(self, reader: ManifestReader):
        """注册新的读取器"""
        self._readers.append(reader)

    def get_reader(self, location: Path) -> Optional[ManifestReader]:
        """获取适合该位置的首个读取器"""
        for reader in self._readers:
            if reader.can_read(location):
                return reader
        return None

    def read_manifest(self, location: Path, logger) -> Optional[PluginManifest]:
        """便捷方法：直接读取指定位置的 manifest"""
        reader = self.get_reader(location)
        if reader:
            return reader.read(location, logger)
        return None