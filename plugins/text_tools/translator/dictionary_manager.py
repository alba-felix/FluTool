"""
词典管理器

支持从多个文件加载词典数据并合并。
"""

import os
from typing import Dict, Optional


class DictionaryManager:
    """词典管理器 - 支持多文件词典"""

    def __init__(self):
        self._dictionaries: Dict[str, str] = {}
        self._loaded_files: set[str] = set()

    def load_from_dict(self, data: Dict[str, str], source_name: str = "default") -> None:
        """
        从字典加载数据

        Args:
            data: 词典数据字典
            source_name: 数据源名称(用于调试)
        """
        for key, value in data.items():
            key_lower = key.lower().strip()
            if key_lower not in self._dictionaries:
                self._dictionaries[key_lower] = value
        print(f"[DictionaryManager] 从 {source_name} 加载了 {len(data)} 个词条")

    def load_from_file(self, file_path: str) -> bool:
        """
        从Python文件加载词典

        Args:
            file_path: 词典文件路径

        Returns:
            是否成功加载
        """
        if not os.path.exists(file_path):
            print(f"[DictionaryManager] 文件不存在: {file_path}")
            return False

        if file_path in self._loaded_files:
            print(f"[DictionaryManager] 文件已加载: {file_path}")
            return True

        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("dict_module", file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 查找字典变量 (常见的命名: EN_TO_ZH, DICT, DICTIONARY 等)
            dict_data = None
            for attr_name in ['EN_TO_ZH', 'DICT', 'DICTIONARY', 'DATA', 'WORDS']:
                if hasattr(module, attr_name):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, dict):
                        dict_data = attr
                        break

            if dict_data:
                self.load_from_dict(dict_data, os.path.basename(file_path))
                self._loaded_files.add(file_path)
                return True
            else:
                print(f"[DictionaryManager] 未找到词典数据: {file_path}")
                return False

        except Exception as e:
            print(f"[DictionaryManager] 加载失败 {file_path}: {e}")
            return False

    def load_from_directory(self, directory: str, pattern: str = "*_dict.py") -> int:
        """
        从目录加载所有词典文件

        Args:
            directory: 词典目录
            pattern: 文件匹配模式

        Returns:
            成功加载的文件数
        """
        import glob

        if not os.path.exists(directory):
            print(f"[DictionaryManager] 目录不存在: {directory}")
            return 0

        count = 0
        for file_path in glob.glob(os.path.join(directory, pattern)):
            if self.load_from_file(file_path):
                count += 1

        print(f"[DictionaryManager] 从目录加载了 {count} 个文件")
        return count

    def get(self, key: str) -> Optional[str]:
        """获取翻译"""
        return self._dictionaries.get(key.lower().strip())

    def __contains__(self, key: str) -> bool:
        """检查是否包含某个词"""
        return key.lower().strip() in self._dictionaries

    def __len__(self) -> int:
        """获取词条总数"""
        return len(self._dictionaries)

    def keys(self):
        """获取所有键"""
        return self._dictionaries.keys()

    def values(self):
        """获取所有值"""
        return self._dictionaries.values()

    def items(self):
        """获取所有键值对"""
        return self._dictionaries.items()


# 全局词典管理器实例
_dict_manager: Optional[DictionaryManager] = None


def get_dictionary_manager() -> DictionaryManager:
    """获取词典管理器单例"""
    global _dict_manager
    if _dict_manager is None:
        _dict_manager = DictionaryManager()
    return _dict_manager


def reset_dictionary_manager() -> DictionaryManager:
    """重置词典管理器"""
    global _dict_manager
    _dict_manager = DictionaryManager()
    return _dict_manager
