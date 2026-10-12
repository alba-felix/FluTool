"""JSON 工具业务逻辑：格式化、压缩、校验、排序、路径提取"""

import json
from typing import Any, List, Optional, Tuple

# JSONDecodeError 常见消息中文化
_MSG_MAP = {
    "Expecting value": "期望一个值",
    "Expecting ',' delimiter": "期望逗号分隔符",
    "Expecting ':' delimiter": "期望冒号分隔符",
    "Expecting property name enclosed in double quotes": "期望双引号包裹的键名",
    "Expecting ',' or ']'": "期望逗号或右方括号",
    "Expecting ',' or '}'": "期望逗号或右花括号",
    "Extra data": "存在多余数据",
    "Unterminated string starting at": "字符串未闭合",
    "Invalid control character at": "包含非法控制字符",
    "Invalid \\escape": "包含非法转义",
}


class JsonService:
    """JSON 处理服务，提供纯计算能力，不依赖 UI"""

    def __init__(self, indent: int = 2):
        self._indent = indent

    def set_indent(self, indent: int) -> None:
        """设置格式化缩进空格数"""
        self._indent = indent

    def format_json(self, text: str) -> Tuple[bool, str]:
        """格式化 JSON 文本，返回 (是否成功, 结果文本或错误信息)"""
        obj, err = self._parse(text)
        if err:
            return False, err
        return True, json.dumps(obj, ensure_ascii=False, indent=self._indent)

    def minify_json(self, text: str) -> Tuple[bool, str]:
        """压缩 JSON 文本"""
        obj, err = self._parse(text)
        if err:
            return False, err
        return True, json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

    def validate_json(self, text: str) -> Tuple[bool, str]:
        """校验 JSON 文本，合法返回 True 和成功信息"""
        _, err = self._parse(text)
        if err:
            return False, err
        return True, "JSON 格式合法"

    def sort_keys(self, text: str) -> Tuple[bool, str]:
        """递归按键名排序后重新格式化"""
        obj, err = self._parse(text)
        if err:
            return False, err
        return True, json.dumps(self._sorted(obj), ensure_ascii=False, indent=self._indent)

    def extract_paths(self, text: str) -> Tuple[bool, str]:
        """提取所有键路径（含数组下标），每行一个"""
        obj, err = self._parse(text)
        if err:
            return False, err
        paths: List[str] = []
        self._walk(obj, "", paths)
        return True, "\n".join(paths) if paths else "（无键路径）"

    def escape_string(self, text: str) -> Tuple[bool, str]:
        """把普通文本转义为 JSON 字符串字面量"""
        return True, json.dumps(text, ensure_ascii=False)

    def unescape_string(self, text: str) -> Tuple[bool, str]:
        """把 JSON 字符串字面量反转义为普通文本"""
        try:
            return True, json.loads(text)
        except (json.JSONDecodeError, ValueError) as e:
            return False, f"反转义失败: {e}"

    def _parse(self, text: str) -> Tuple[Optional[Any], Optional[str]]:
        """解析 JSON，返回 (对象, 错误信息)，成功时错误信息为 None"""
        if not text.strip():
            return None, "输入为空"
        try:
            return json.loads(text), None
        except json.JSONDecodeError as e:
            msg = _MSG_MAP.get(e.msg, e.msg)
            # 片段取错误所在行，避免跨行截取
            line_start = e.doc.rfind("\n", 0, e.pos) + 1
            line_end = e.doc.find("\n", e.pos)
            if line_end == -1:
                line_end = len(e.doc)
            fragment = e.doc[line_start:line_end].strip()
            return None, (
                f"JSON 解析失败: 第 {e.lineno} 行 第 {e.colno} 列\n"
                f"{msg}\n片段: {fragment}"
            )

    def _sorted(self, obj: Any) -> Any:
        """递归按键名排序 dict，list 逐项递归"""
        if isinstance(obj, dict):
            return {k: self._sorted(obj[k]) for k in sorted(obj.keys())}
        if isinstance(obj, list):
            return [self._sorted(v) for v in obj]
        return obj

    def _walk(self, obj: Any, prefix: str, paths: List[str]) -> None:
        """递归收集所有键路径"""
        if isinstance(obj, dict):
            for k, v in obj.items():
                path = f"{prefix}.{k}" if prefix else str(k)
                paths.append(path)
                self._walk(v, path, paths)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                path = f"{prefix}[{i}]"
                if isinstance(v, (dict, list)):
                    self._walk(v, path, paths)
                else:
                    paths.append(path)
