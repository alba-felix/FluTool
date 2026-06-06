"""
笔记卡片样式定义
"""

DARK_STYLE = """
NoteCard {
    background-color: #2d2d2d;
    border: 1px solid #3d3d3d;
    border-radius: 12px;
}

NoteCard:hover {
    border: 1px solid #0078d4;
    background-color: #323232;
}

#card_title {
    color: #ffffff;
    padding: 0px;
    font-weight: bold;
}

#card_category {
    color: #aaaaaa;
    background-color: rgba(0, 120, 212, 0.2);
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 11px;
}

#card_create_time {
    color: #666666;
    padding: 0px;
    font-size: 11px;
}

#card_preview {
    color: #cccccc;
    background-color: transparent;
    padding: 0px;
    border: none;
}

#card_content {
    color: #ffffff;
    background-color: #1e1e1e;
    padding: 8px;
    border-radius: 6px;
    border: 1px solid #333333;
}

#card_tag {
    color: #aaaaaa;
    background-color: rgba(100, 100, 100, 0.2);
    padding: 2px 8px;
    border-radius: 10px;
    border: 1px solid #555555;
    font-size: 11px;
}

#card_expand_button,
#card_save_button,
#card_edit_button,
#card_favorite_button,
#card_archive_button,
#card_code_button,
#card_images_button,
#card_delete_button {
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 2px;
}

#card_expand_button:hover,
#card_save_button:hover,
#card_edit_button:hover,
#card_favorite_button:hover,
#card_archive_button:hover,
#card_code_button:hover,
#card_images_button:hover,
#card_delete_button:hover {
    background-color: rgba(255, 255, 255, 0.1);
    border: none;
}

#card_save_button {
    background-color: transparent;
    border: none;
}

#card_save_button:hover {
    background-color: rgba(0, 120, 212, 0.2);
    border: none;
}

#card_delete_button {
    background-color: transparent;
    border: none;
}

#card_delete_button:hover {
    background-color: rgba(255, 107, 107, 0.2);
    border: none;
}

#card_delete_button:hover {
    background-color: rgba(255, 107, 107, 0.15);
    border-color: #ff6b6b;
}

#card_favorite_button {
    color: #ffd700;
    border-color: #4a4530;
}

#card_favorite_button:hover {
    background-color: rgba(255, 215, 0, 0.15);
}

#card_archive_button {
    color: #87ceeb;
    border-color: #3a4a55;
}

#card_archive_button:hover {
    background-color: rgba(135, 206, 235, 0.15);
}
"""

LIGHT_STYLE = """
NoteCard {
    background-color: #ffffff;
    border: 1px solid #e8e8e8;
    border-radius: 12px;
}

NoteCard:hover {
    border: 1px solid #0078d4;
    background-color: #fafafa;
}

#card_title {
    color: #1a1a1a;
    padding: 0px;
    font-weight: bold;
}

#card_category {
    color: #0078d4;
    background-color: rgba(0, 120, 212, 0.1);
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 11px;
}

#card_create_time {
    color: #999999;
    padding: 0px;
    font-size: 11px;
}

#card_preview {
    color: #333333;
    background-color: transparent;
    padding: 0px;
    border: none;
}

#card_content {
    color: #1a1a1a;
    background-color: #f8f8f8;
    padding: 8px;
    border-radius: 6px;
    border: 1px solid #e0e0e0;
}

#card_tag {
    color: #555555;
    background-color: rgba(0, 0, 0, 0.05);
    padding: 2px 8px;
    border-radius: 10px;
    border: 1px solid #cccccc;
    font-size: 11px;
}

#card_expand_button,
#card_save_button,
#card_edit_button,
#card_favorite_button,
#card_archive_button,
#card_code_button,
#card_images_button,
#card_delete_button {
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 2px;
}

#card_expand_button:hover,
#card_save_button:hover,
#card_edit_button:hover,
#card_favorite_button:hover,
#card_archive_button:hover,
#card_code_button:hover,
#card_images_button:hover,
#card_delete_button:hover {
    background-color: rgba(0, 0, 0, 0.05);
    border: none;
}

#card_save_button {
    background-color: transparent;
    border: none;
}

#card_save_button:hover {
    background-color: rgba(0, 120, 212, 0.1);
    border: none;
}

#card_delete_button {
    background-color: transparent;
    border: none;
}

#card_delete_button:hover {
    background-color: rgba(211, 47, 47, 0.1);
    border: none;
}

#card_delete_button:hover {
    background-color: rgba(211, 47, 47, 0.08);
    border-color: #d32f2f;
}

#card_favorite_button {
    color: #f9a825;
    border-color: #fff8e1;
}

#card_favorite_button:hover {
    background-color: rgba(249, 168, 37, 0.1);
}

#card_archive_button {
    color: #0288d1;
    border-color: #e1f5fe;
}

#card_archive_button:hover {
    background-color: rgba(2, 136, 209, 0.1);
}
"""


SCROLL_BAR_STYLE_DARK = """
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 0.15);
    min-height: 30px;
    border-radius: 4px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(255, 255, 255, 0.25);
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
    background: transparent;
}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
}

QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background: rgba(255, 255, 255, 0.15);
    min-width: 30px;
    border-radius: 4px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover {
    background: rgba(255, 255, 255, 0.25);
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
    background: transparent;
}

QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: transparent;
}
"""

SCROLL_BAR_STYLE_LIGHT = """
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: rgba(0, 0, 0, 0.15);
    min-height: 30px;
    border-radius: 4px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(0, 0, 0, 0.25);
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
    background: transparent;
}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
}

QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background: rgba(0, 0, 0, 0.15);
    min-width: 30px;
    border-radius: 4px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover {
    background: rgba(0, 0, 0, 0.25);
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
    background: transparent;
}

QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: transparent;
}
"""