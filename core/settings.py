from PyQt5.QtCore import QSettings


class SettingsManager:
    def __init__(self, organization: str = "FluTool", application: str = "App"):
        self._settings = QSettings(organization, application)

    def get(self, key: str, default=None):
        return self._settings.value(key, default)

    def set(self, key: str, value) -> None:
        self._settings.setValue(key, value)

    def sync(self) -> None:
        self._settings.sync()

    def remove(self, key: str) -> None:
        self._settings.remove(key)

    def contains(self, key: str) -> bool:
        return self._settings.contains(key)
