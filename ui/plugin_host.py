"""插件界面宿主管理。"""

from typing import Dict

from PyQt5.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import setCustomStyleSheet


class PluginHost:
	"""管理插件容器、界面创建和数据加载。"""

	def __init__(self, core):
		if core is None:
			raise ValueError("Core instance cannot be None")
		self.core = core
		self.plugin_containers: Dict[str, QWidget] = {}
		self.plugin_widgets: Dict[str, QWidget] = {}
		self.plugin_initialized: Dict[str, bool] = {}

	def create_container(self, plugin_id: str) -> QWidget:
		"""创建并注册插件容器。"""
		container = QWidget()
		container.setObjectName(f"container_{plugin_id}")
		container.setLayout(QVBoxLayout())
		container.layout().setContentsMargins(0, 0, 0, 0)

		qss = f"QWidget#{container.objectName()} {{ background-color: transparent; }}"
		setCustomStyleSheet(container, qss, qss)

		self.plugin_containers[plugin_id] = container
		self.plugin_initialized[plugin_id] = False
		return container

	def init_plugin_widget(self, plugin_id: str) -> bool:
		"""按需创建插件界面。"""
		if not plugin_id:
			return False

		if self.plugin_initialized.get(plugin_id, False):
			return True

		plugin = self.core.plugin_manager.get_plugin(plugin_id)
		if not plugin:
			self.core.logger.error(f"Plugin not found: {plugin_id}")
			return False

		container = self.plugin_containers.get(plugin_id)
		if container is None:
			self.core.logger.error(f"Container not found for plugin: {plugin_id}")
			return False

		try:
			widget = plugin.get_widget(container)
			if widget is None:
				self.core.logger.warning(f"Plugin widget is None: {plugin_id}")
				return False

			widget.setObjectName(plugin_id)
			container.layout().addWidget(widget)

			self.plugin_widgets[plugin_id] = widget
			self.plugin_initialized[plugin_id] = True

			self.core.logger.info(f"Plugin widget created: {plugin.get_name()}")
			return True
		except Exception as e:
			self.core.logger.error(f"Failed to create plugin widget {plugin_id}: {e}")
			return False

	def load_plugin_data(self, plugin_id: str) -> None:
		"""触发插件数据加载。"""
		if not plugin_id:
			return

		plugin = self.core.plugin_manager.get_plugin(plugin_id)
		if plugin is None:
			return

		try:
			plugin.load_data()
		except Exception as e:
			self.core.logger.error(f"Failed to load plugin data {plugin_id}: {e}")

	def attach_loaded_plugin(self, plugin) -> QWidget:
		"""注册已经加载完成的插件并立即创建界面。"""
		plugin_id = plugin.get_id()
		container = self.create_container(plugin_id)

		try:
			widget = plugin.get_widget(container)
			if widget is None:
				self.core.logger.warning(f"Plugin widget is None: {plugin_id}")
				return container

			widget.setObjectName(plugin_id)
			container.layout().addWidget(widget)
			self.plugin_widgets[plugin_id] = widget
			self.plugin_initialized[plugin_id] = True
			self.core.logger.info(f"Plugin widget created: {plugin.get_name()}")
		except Exception as e:
			self.core.logger.error(f"Failed to create plugin widget {plugin_id}: {e}")
		return container

	def shutdown_plugin(self, plugin_id: str) -> None:
		"""关闭插件并清理宿主状态。"""
		if not plugin_id:
			return

		plugin = self.core.plugin_manager.get_plugin(plugin_id)
		if plugin:
			try:
				plugin.shutdown()
			except Exception as e:
				self.core.logger.error(f"Plugin shutdown error: {e}")

		self.plugin_containers.pop(plugin_id, None)
		self.plugin_widgets.pop(plugin_id, None)
		self.plugin_initialized.pop(plugin_id, None)
