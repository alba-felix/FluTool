"""
表格笔记服务（布局2 - 极简 Excel）
将「迷你 Excel 表格」作为 notebook 表中 note_type="table" 的一类笔记存储，
复用 NotebookService / notebook 表的增删改查逻辑。
content 字段存放稀疏 JSON：{"A1": "值", ...}，坐标键用列字母+行号。
"""
import json
from typing import Any, Dict, List, Optional

from plugins.notebook.service import NotebookService

TABLE_TYPE = "table"
COLUMN_NAMES = [chr(ord("A") + i) for i in range(26)]  # A..Z
MAX_COLUMNS = len(COLUMN_NAMES)
MAX_ROWS = 999


def coord_to_key(col: int, row: int) -> str:
    """0-based 行列转 Excel 坐标键，如 (0,0) -> 'A1'"""
    if not (0 <= col < MAX_COLUMNS) or not (0 <= row < MAX_ROWS):
        raise IndexError(f"table coordinate out of range: col={col}, row={row}")
    return f"{COLUMN_NAMES[col]}{row + 1}"


def key_to_coord(key: str) -> Optional[tuple]:
    """Excel 坐标键转 0-based (col, row)，非法坐标返回 None"""
    if not key or len(key) < 2:
        return None
    col_letter = key[0].upper()
    if col_letter not in COLUMN_NAMES:
        return None
    try:
        row = int(key[1:]) - 1
    except ValueError:
        return None
    if not (0 <= row < MAX_ROWS):
        return None
    return COLUMN_NAMES.index(col_letter), row


class TableService:
    """表格笔记服务：数据以 notebook 记录形式复用，note_type='table' 区分。"""

    def __init__(self, plugin_id: str, db=None):
        self._service = NotebookService(plugin_id, db)

    @staticmethod
    def is_table(note: Any) -> bool:
        """判断记录是否为表格笔记"""
        return bool(note) and note.get("note_type") == TABLE_TYPE

    def list_tables(self) -> List[Dict[str, Any]]:
        """列出全部表格笔记"""
        return [
            n for n in self._service.list_notes()
            if self.is_table(n)
        ]

    def create_table(self, name: str = "表格") -> Optional[int]:
        """新建表格笔记，返回 note_id"""
        title = (name or "表格").strip() or "表格"
        return self._service.add_note(
            title=title,
            content="{}",
            note_type=TABLE_TYPE,
        )

    def get_table(self, table_id: int) -> Optional[Dict[str, Any]]:
        """按 ID 取表格笔记"""
        note = self._service.get_note(table_id)
        if note is None or not self.is_table(note):
            return None
        return note

    def delete_table(self, table_id: int) -> bool:
        """删除表格笔记"""
        return self._service.delete_note(table_id)

    def rename_table(self, table_id: int, new_name: str) -> bool:
        """重命名表格"""
        note = self.get_table(table_id)
        if note is None:
            return False
        title = (new_name or "表格").strip() or "表格"
        return self._service.update_note(table_id, title=title)

    def load_cells(self, note: Dict[str, Any]) -> Dict[str, str]:
        """读取单元格内容（稀疏字典）"""
        if not self.is_table(note):
            return {}
        try:
            data = json.loads(note.get("content") or "{}")
        except (ValueError, TypeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {str(k): str(v) for k, v in data.items() if str(v) != ""}

    def save_cells(self, table_id: int, cells: Dict[str, str]) -> bool:
        """将单元格字典写回表格笔记"""
        note = self.get_table(table_id)
        if note is None:
            return False
        clean = {str(k): str(v) for k, v in (cells or {}).items() if str(v) != ""}
        return self._service.update_note(
            table_id, content=json.dumps(clean, ensure_ascii=False)
        )

    def to_markdown(self, cells: Dict[str, str]) -> str:
        """将单元格字典序列化为 Markdown 表格

        表头为列字母 A..X，第一列为行号，仅覆盖实际有内容的范围。
        """
        used_rows = set()
        used_cols = set()
        for key, value in (cells or {}).items():
            coord = key_to_coord(key)
            if coord is None:
                continue
            col, row = coord
            if value != "":
                used_cols.add(col)
                used_rows.add(row)
        if not used_cols:
            return "| | A |\n| :--- | :--- |\n| 1 |  |"
        row_numbers = sorted(used_rows)
        col_numbers = sorted(used_cols)

        header = ["", *[COLUMN_NAMES[c] for c in col_numbers]]
        separator = [":---"] * len(header)
        lines = ["| " + " | ".join(header) + " |"]
        lines.append("| " + " | ".join(separator) + " |")
        for row in row_numbers:
            row_vals = [
                cells.get(coord_to_key(col, row), "").replace("\n", " ")
                for col in col_numbers
            ]
            lines.append(
                "| " + str(row + 1) + " | " + " | ".join(row_vals) + " |"
            )
        return "\n".join(lines) + "\n"
