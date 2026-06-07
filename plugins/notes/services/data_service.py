"""
数据服务模块
提供笔记数据的备份和导入功能，不依赖 Qt UI 组件。
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from typing import Optional

from ..core.path_util import PathUtil


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
        从 ZIP 备份文件导入笔记数据

        Args:
            file_path: 备份 ZIP 文件路径

        Returns:
            (success, message) 二元组
        """
        try:
            data_path = Path(PathUtil.get_data_path())
            images_path = Path(PathUtil.get_image_path())

            with ZipFile(file_path, 'r') as zipf:
                for member in zipf.namelist():
                    if member.endswith('/'):
                        continue

                    if member.startswith('data/images/'):
                        target_path = images_path / member.replace('data/images/', '')
                    elif member.startswith('data/'):
                        target_path = data_path / member.replace('data/', '')
                    else:
                        continue

                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    with zipf.open(member) as source, open(target_path, 'wb') as target:
                        target.write(source.read())

            return True, '数据已导入，请重启应用以生效'
        except Exception as e:
            return False, f'导入失败：{str(e)}'