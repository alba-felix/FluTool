"""文件夹备注服务 - JSON 存储"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from core import get_app_data_path


class CommentService:
    """文件夹备注 CRUD"""

    def __init__(self, data_path: Optional[str] = None):
        self._path = Path(data_path) if data_path else get_app_data_path("data/filecomment.json")
        self._store: Dict[str, Dict] = {}
        self._load()

    def get(self, folder_path: str) -> Optional[Dict]:
        return self._store.get(folder_path)

    def put(self, folder_path: str, text: str) -> Dict:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        existing = self._store.get(folder_path)
        if existing:
            existing["text"] = text
            existing["updated_at"] = now
        else:
            self._store[folder_path] = {
                "text": text,
                "created_at": now,
                "updated_at": now,
            }
        self._save()
        return self._store[folder_path]

    def delete(self, folder_path: str) -> bool:
        if folder_path in self._store:
            del self._store[folder_path]
            self._save()
            return True
        return False

    def clear(self) -> None:
        self._store.clear()
        self._save()

    def search(self, keyword: str) -> List[Dict]:
        keyword_lower = keyword.lower()
        return [
            {"path": p, **d}
            for p, d in self._store.items()
            if keyword_lower in p.lower() or keyword_lower in d.get("text", "").lower()
        ]

    def all(self) -> List[Dict]:
        return [{"path": p, **d} for p, d in self._store.items()]

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._store = json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                self._store = {}
        else:
            self._store = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._store, ensure_ascii=False, indent=2), encoding="utf-8")
