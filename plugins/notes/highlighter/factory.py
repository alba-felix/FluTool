from typing import Optional, Dict, Type
from PyQt5.QtGui import QSyntaxHighlighter

from ..highlighter.base_highlighter import BaseHighlighter
from ..highlighter.python_highlighter import PythonHighlighter
from ..highlighter.java_highlighter import JavaHighlighter
from ..highlighter.javascript_highlighter import JavaScriptHighlighter
from ..highlighter.other_highlighter import OtherHighlighter


class HighlighterFactory:
    _highlighters: Dict[str, Type[BaseHighlighter]] = {
        'python': PythonHighlighter,
        'py': PythonHighlighter,
        'java': JavaHighlighter,
        'javascript': JavaScriptHighlighter,
        'js': JavaScriptHighlighter,
        'typescript': JavaScriptHighlighter,
        'ts': JavaScriptHighlighter,
        'other': OtherHighlighter,
    }

    @classmethod
    def create(cls, language: str, document) -> Optional[QSyntaxHighlighter]:
        language_lower = language.lower().strip()
        highlighter_class = cls._highlighters.get(language_lower)
        if highlighter_class is None:
            return None
        return highlighter_class(document)

    @classmethod
    def get_supported_languages(cls) -> list:
        return list(set(cls._highlighters.keys()))

    @classmethod
    def register(cls, language: str, highlighter_class: Type[BaseHighlighter]):
        cls._highlighters[language.lower()] = highlighter_class

    @classmethod
    def is_supported(cls, language: str) -> bool:
        return language.lower().strip() in cls._highlighters