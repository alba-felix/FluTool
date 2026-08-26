"""
数据服务模块
提供笔记数据的备份和导入功能，不依赖 Qt UI 组件。

导入采用内容指纹合并（与 Android 端 JotMe 相同策略），绝不覆盖删除现有数据：
- 分类按名称匹配（同名复用，新名新建）
- 笔记按内容指纹（标题/正文/标签/代码块/备注/图片）去重：
  内容相同只保留一份（收藏/归档标志 OR 合并），内容不同各保留一份
- 导入的笔记一律分配新 id，绝不沿用导入数据的自增 id
  （两端各自新增笔记会撞号，沿用会导致互相覆盖）
- 不依赖时间戳判断新旧（PC 端 CURRENT_TIMESTAMP 为 UTC，
  Android 端写入本地时间，相差 8 小时不可比）
- 删除不会传播（无墓碑机制，宁多勿丢）
- 同时支持两种备份布局：PC 导出（data/notes.db）与 Android 导出（notes.db）
"""
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from typing import Optional

from ..core.path_util import PathUtil
from ..dao.database import Database


class DataService:
    """笔记数据备份与导入服务"""

    @staticmethod
    def backup_data(save_path: str) -> tuple[bool, str]:
        """
        备份笔记数据到 ZIP 文件

        Args:
            save_path: 目标 ZIP 文件路径

        Returns:
            (success, message) 二元组
        """
        try:
            with ZipFile(save_path, 'w', ZIP_DEFLATED) as zipf:
                db_path = Path(PathUtil.get_db_path())
                if db_path.exists():
                    zipf.write(db_path, 'data/notes.db')

                images_path = Path(PathUtil.get_image_path())
                if images_path.exists():
                    for image_file in images_path.iterdir():
                        if image_file.is_file():
                            zipf.write(image_file, f'data/images/{image_file.name}')

            return True, f'数据已备份到：{save_path}'
        except Exception as e:
            return False, f'备份失败：{str(e)}'

    @staticmethod
    def import_data(file_path: str) -> tuple[bool, str]:
        """
        从 ZIP 备份合并导入笔记数据（保留双方数据，绝不覆盖删除）

        Args:
            file_path: 备份 ZIP 文件路径

        Returns:
            (success, message) 二元组
        """
        temp_dir: Optional[Path] = None
        imported_conn: Optional[sqlite3.Connection] = None
        try:
            data_path = Path(PathUtil.get_data_path())
            images_path = Path(PathUtil.get_image_path())
            images_path.mkdir(parents=True, exist_ok=True)

            temp_dir = Path(tempfile.mkdtemp(prefix='notes_import_'))
            db_file: Optional[Path] = None

            with ZipFile(file_path, 'r') as zipf:
                for member in zipf.namelist():
                    if member.endswith('/'):
                        continue

                    # PC 布局：data/notes.db、data/images/*；Android 布局：notes.db、images/*
                    if member in ('data/notes.db', 'notes.db'):
                        db_file = temp_dir / 'imported.db'
                        with zipf.open(member) as source, open(db_file, 'wb') as target:
                            shutil.copyfileobj(source, target)
                    elif member.startswith('data/images/'):
                        DataService._extract_image(zipf, member, temp_dir, 'data/images/')
                    elif member.startswith('images/'):
                        DataService._extract_image(zipf, member, temp_dir, 'images/')

            if db_file is None:
                return False, 'ZIP 中未找到笔记数据库（notes.db）'

            # 图片先合并（若此处失败，数据库未做任何改动）
            imported_images = temp_dir / 'images'
            if imported_images.exists():
                for image_file in imported_images.iterdir():
                    if image_file.is_file():
                        target = images_path / image_file.name
                        if not target.exists():
                            shutil.copy2(image_file, target)

            imported_conn = sqlite3.connect(f'{db_file.as_uri()}?mode=ro', uri=True)
            imported_conn.row_factory = sqlite3.Row

            categories = DataService._read_rows(imported_conn, 'categories')
            notes = DataService._read_rows(imported_conn, 'notes')

            added_notes, added_categories, skipped = DataService._merge_into_live_db(categories, notes)

            return True, (
                f'合并完成：新增 {added_notes} 条笔记、'
                f'{added_categories} 个分类，跳过相同 {skipped} 条'
            )
        except Exception as e:
            DataService._rollback()
            return False, f'导入失败：{str(e)}'
        finally:
            if imported_conn is not None:
                imported_conn.close()
            if temp_dir is not None:
                shutil.rmtree(temp_dir, ignore_errors=True)

    @staticmethod
    def _extract_image(zipf: ZipFile, member: str, temp_dir: Path, prefix: str) -> None:
        """解压 zip 内的图片到临时目录 images/ 下（统一去掉前缀）"""
        rel = member[len(prefix):]
        if not rel:
            return
        target = temp_dir / 'images' / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with zipf.open(member) as source, open(target, 'wb') as out:
            shutil.copyfileobj(source, out)

    @staticmethod
    def _read_rows(conn: sqlite3.Connection, table: str) -> list:
        """读取导入数据库中的表（表不存在时返回空列表）"""
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        )
        if cursor.fetchone() is None:
            return []
        return conn.execute(f'SELECT * FROM {table}').fetchall()

    @staticmethod
    def _get(row, key: str, default=None):
        """容错取列值：列缺失或 NULL 时返回默认值（适配两端 schema 差异）"""
        try:
            value = row[key]
        except (IndexError, KeyError):
            return default
        return default if value is None else value

    @staticmethod
    def _merge_into_live_db(categories: list, notes: list) -> tuple[int, int, int]:
        """将导入数据按内容指纹合并进本地数据库，返回 (新增笔记, 新增分类, 跳过)"""
        db = Database.get_instance()

        # 分类：按名称匹配，建立 导入id → 本地id 映射
        category_map: dict[int, int] = {}
        added_categories = 0
        for row in categories:
            name = DataService._get(row, 'name')
            if not name:
                continue
            existing = db.execute(
                'SELECT id, sort_order FROM categories WHERE name = ?', (name,)
            ).fetchone()
            if existing is not None:
                category_map[row['id']] = existing['id']
                # 传播排序（与 Android 端 BackupService 对称：同步指纹含 sort_order，
                # 不传播会导致一端的拖拽排序每轮都被另一端的旧排序打回）
                imported_order = DataService._get(row, 'sort_order', 0) or 0
                if existing['sort_order'] != imported_order:
                    db.execute(
                        'UPDATE categories SET sort_order = ? WHERE id = ?',
                        (imported_order, existing['id'])
                    )
            else:
                cursor = db.execute(
                    'INSERT INTO categories (name, sort_order, created_at) VALUES (?, ?, ?)',
                    (name, DataService._get(row, 'sort_order', 0) or 0,
                     DataService._get(row, 'created_at'))
                )
                category_map[row['id']] = cursor.lastrowid
                added_categories += 1

        # 笔记：内容指纹去重后插入（一律分配新 id）
        existing_by_fingerprint: dict[str, int] = {}
        for row in db.execute('SELECT * FROM notes').fetchall():
            existing_by_fingerprint[DataService._fingerprint(row)] = row['id']

        added_notes = 0
        skipped = 0
        seen: set[str] = set()
        for row in notes:
            fingerprint = DataService._fingerprint(row)
            if fingerprint in seen:
                skipped += 1  # 导入数据内部重复
                continue
            seen.add(fingerprint)

            local_id = existing_by_fingerprint.get(fingerprint)
            if local_id is not None:
                # 内容相同：合并收藏/归档标志（任一端开启即开启）
                db.execute(
                    'UPDATE notes SET is_favorite = MAX(is_favorite, ?), '
                    'is_archived = MAX(is_archived, ?) WHERE id = ?',
                    (DataService._get(row, 'is_favorite', 0) or 0,
                     DataService._get(row, 'is_archived', 0) or 0,
                     local_id)
                )
                skipped += 1
                continue

            category_id = DataService._get(row, 'category_id')
            category_id = category_map.get(category_id) if category_id is not None else None
            db.execute(
                '''INSERT INTO notes
                   (title, content, category_id, tags, code_blocks, remarks, images,
                    is_archived, is_favorite, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (DataService._get(row, 'title', '无标题'),
                 DataService._get(row, 'content', ''),
                 category_id,
                 DataService._get(row, 'tags'),
                 DataService._get(row, 'code_blocks'),
                 DataService._get(row, 'remarks'),
                 DataService._get(row, 'images'),
                 DataService._get(row, 'is_archived', 0) or 0,
                 DataService._get(row, 'is_favorite', 0) or 0,
                 DataService._get(row, 'created_at'),
                 DataService._get(row, 'updated_at'))
            )
            added_notes += 1

        db.commit()
        return added_notes, added_categories, skipped

    @staticmethod
    def _rollback() -> None:
        """合并中途失败时回滚未提交的改动"""
        try:
            Database.get_instance().execute('ROLLBACK')
        except Exception:
            pass  # 无活动事务时忽略

    @staticmethod
    def _normalize(value):
        """数值规范化：整数值浮点转 int，保证两端指纹一致（Python 1.0 → 1，与 org.json 一致）"""
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, list):
            return [DataService._normalize(item) for item in value]
        if isinstance(value, dict):
            return {key: DataService._normalize(item) for key, item in value.items()}
        return value

    @staticmethod
    def _canonical_json(value: Optional[str]) -> str:
        """JSON 规范化：解析后紧凑序列化+键排序，消除两端序列化差异；空值统一为 '[]'"""
        if not value:
            return '[]'
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError):
            return value
        return json.dumps(
            DataService._normalize(parsed),
            ensure_ascii=False, separators=(',', ':'), sort_keys=True
        )

    @staticmethod
    def _fingerprint(row) -> str:
        """内容指纹：不含 id/时间戳/收藏归档标志（理由见模块注释）"""
        return '\x00'.join([
            DataService._get(row, 'title', '') or '',
            DataService._get(row, 'content', '') or '',
            DataService._canonical_json(DataService._get(row, 'tags')),
            DataService._canonical_json(DataService._get(row, 'code_blocks')),
            DataService._get(row, 'remarks', '') or '',
            DataService._canonical_json(DataService._get(row, 'images')),
        ])
