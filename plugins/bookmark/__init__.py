"""书签插件"""

import webbrowser
from typing import Optional

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import QUrl

from core import PluginInterface, SearchResult
from ui.custom_icon import CustomFluentIcon
from .service import BookmarkService
from .widget import BookmarkWidget


class Plugin(PluginInterface):
    """书签插件"""
    PLUGIN_ID = "bookmark"
    PLUGIN_NAME = "网站书签"
    PLUGIN_ICON = CustomFluentIcon.BOOKMARK_TAG
    PLUGIN_PRIORITY = 1

    def initialize(self, core) -> None:
        self.core = core
        core.logger.info(f"Plugin '{self.get_name()}' initialized")

    def shutdown(self) -> None:
        self.core.logger.info(f"Plugin '{self.get_name()}' shutdown")

    def _create_widget(self, parent=None) -> QWidget:
        return BookmarkWidget(self.core, parent)

    def _do_load_data(self) -> None:
        """加载数据：直接从数据库读取"""
        if self._widget is None:
            return
        self._widget.load_data()
    
    def supports_search(self) -> bool:
        return True
    
    def search(self, query: str):
        results = []
        bookmarks = BookmarkService(self.PLUGIN_ID).search(query)
        for bm in bookmarks[:20]:
            result = SearchResult(
                plugin_id=self.PLUGIN_ID,
                plugin_name=self.get_name(),
                title=bm['name'],
                description=f"{bm['url']} - {bm.get('notes', '')}",
                icon=self.PLUGIN_ICON,
                relevance=1.0 if query in bm['name'].lower() else 0.5,
                action=lambda url=bm['url']: webbrowser.open(url),
                metadata={'bookmark_id': bm['id'], 'url': bm['url']}
            )
            results.append(result)
        return results
