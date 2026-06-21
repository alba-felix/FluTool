"""
应用启动插件
提供应用程序快捷启动功能，支持分类、拖拽、图标提取
支持多种文件类型：exe、py、bat、cmd、ps1、vbs、文件夹等
"""
import html
import difflib
from typing import List, Dict, Any, Tuple

from PyQt5.QtCore import QRect
from PyQt5.QtGui import QPixmap, QImage
from qfluentwidgets import FluentIcon as FIF, isDarkTheme

from core import get_app_data_path
from ui.custom_icon import CustomFluentIcon as CFIF

from .utils import get_python_executable, get_plugins_sourcecode_dir


CARD_WIDTH = 120
CARD_HEIGHT = 35
ICON_SIZE = 24
LIST_CARD_HEIGHT = 64
GRID_VIEW = "grid"
LIST_VIEW = "list"
DEFAULT_ICON_SIZE = 24
CATEGORY_PRESET_COLORS = [
    ("默认", ""),
    ("青色", "#009faa"),
    ("蓝色", "#0078d4"),
    ("绿色", "#16a34a"),
    ("橙色", "#ea580c"),
    ("红色", "#dc2626"),
    ("紫色", "#9333ea"),
]
CATEGORY_ICON_MAP = {
    "": None,
    "FOLDER": FIF.FOLDER,
    "APPLICATION": FIF.APPLICATION,
    "DOCUMENT": FIF.DOCUMENT,
    "CODE": FIF.CODE,
    "SETTING": FIF.SETTING,
    "HOME": FIF.HOME,
    "FAVORITE": CFIF.BOOKMARK_TAG,
    "TAG": FIF.TAG,
}


def get_non_transparent_rect(pixmap: QPixmap) -> QRect:
    """计算图像中非透明像素的最小包围矩形"""
    if pixmap.isNull():
        return QRect()

    image = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
    width = image.width()
    height = image.height()
    if width <= 0 or height <= 0:
        return QRect()

    min_x, min_y = width, height
    max_x, max_y = -1, -1

    for y in range(height):
        for x in range(width):
            if image.pixelColor(x, y).alpha() == 0:
                continue
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)

    if max_x < min_x or max_y < min_y:
        return QRect()
    return QRect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)


def get_category_icon(icon_name: str):
    """根据名称获取分类图标"""
    return CATEGORY_ICON_MAP.get(icon_name or "", None)


def get_category_icon_options() -> List[Tuple[str, str]]:
    """获取分类图标选项"""
    return [
        ("默认", ""),
        ("文件夹", "FOLDER"),
        ("应用", "APPLICATION"),
        ("文档", "DOCUMENT"),
        ("代码", "CODE"),
        ("设置", "SETTING"),
        ("首页", "HOME"),
        ("收藏", "FAVORITE"),
        ("标签", "TAG"),
    ]


def normalize_search_text(text: str) -> str:
    """标准化搜索文本"""
    return ''.join(str(text or '').lower().split())


def to_pinyin_text(text: str) -> str:
    """将文本转换为拼音串，依赖缺失时自动降级"""
    normalized_text = normalize_search_text(text)
    if not normalized_text:
        return ""

    try:
        from pypinyin import lazy_pinyin
        return ''.join(lazy_pinyin(text)).lower()
    except Exception:
        return normalized_text


def highlight_text(text: str, keyword: str) -> str:
    """高亮文本中的匹配内容"""
    safe_text = html.escape(text or "")
    normalized_keyword = normalize_search_text(keyword)
    if not normalized_keyword:
        return safe_text

    source_text = text or ""
    lowered_source = source_text.lower()
    lowered_keyword = keyword.lower()
    start_index = lowered_source.find(lowered_keyword)
    if start_index < 0:
        return f"<span style='font-weight: 600; color: #009faa;'>{safe_text}</span>"

    end_index = start_index + len(keyword)
    before_text = html.escape(source_text[:start_index])
    middle_text = html.escape(source_text[start_index:end_index])
    after_text = html.escape(source_text[end_index:])
    return (
        f"{before_text}"
        f"<span style='background-color: rgba(0, 159, 170, 0.22); color: #009faa; font-weight: 700;'>{middle_text}</span>"
        f"{after_text}"
    )


def score_search_match(query: str, app_data: Dict[str, Any]) -> Tuple[float, str]:
    """计算应用搜索匹配分数"""
    normalized_query = normalize_search_text(query)
    if not normalized_query:
        return 0.0, "none"

    fields = [
        ("name", app_data.get("name", "")),
        ("target_path", app_data.get("target_path", "")),
        ("notes", app_data.get("notes", "")),
    ]
    best_score = 0.0
    best_mode = "none"

    for field_name, value in fields:
        normalized_value = normalize_search_text(value)
        if not normalized_value:
            continue

        if normalized_query in normalized_value:
            base_score = 120.0 if field_name == "name" else 100.0
            compact_penalty = len(normalized_value) * 0.01
            score_value = base_score - compact_penalty
            if score_value > best_score:
                best_score = score_value
                best_mode = "direct"

        pinyin_value = to_pinyin_text(value)
        if pinyin_value and normalized_query in pinyin_value:
            score_value = 92.0 if field_name == "name" else 80.0
            if score_value > best_score:
                best_score = score_value
                best_mode = "pinyin"

        similarity = difflib.SequenceMatcher(None, normalized_query, normalized_value).ratio()
        if similarity >= 0.45:
            score_value = similarity * (78.0 if field_name == "name" else 66.0)
            if score_value > best_score:
                best_score = score_value
                best_mode = "fuzzy"

    return best_score, best_mode


def get_menu_style() -> str:
    """获取菜单样式"""
    if isDarkTheme():
        return """
            QMenu {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                background-color: transparent;
                color: #ffffff;
                padding: 6px 30px 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3d3d3d;
            }
            QMenu::item:pressed {
                background-color: #009faa;
            }
        """
    else:
        return """
            QMenu {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                background-color: transparent;
                color: #333333;
                padding: 6px 30px 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #f0f0f0;
            }
            QMenu::item:pressed {
                background-color: #009faa;
                color: #ffffff;
            }
        """


def __getattr__(name):
    """延迟导入 Plugin 类，避免循环引用"""
    if name == "Plugin":
        from .plugin import Plugin
        return Plugin
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
