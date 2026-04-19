from typing import Optional, Callable
from PyQt5.QtWidgets import QWidget
from qfluentwidgets import (
    MessageBoxBase, SubtitleLabel, LineEdit, PlainTextEdit
)


class InputDialog(MessageBoxBase):
    """Fluent 风格输入对话框 - 共享组件
    
    支持多种微调方式：
    1. 自定义窗口最小宽度
    2. 自定义按钮文本
    3. 自定义验证逻辑
    4. 支持单行/多行输入模式
    5. 支持占位符和提示文本
    6. 支持密码模式
    """
    
    def __init__(
        self, 
        title: str, 
        label: str, 
        default_text: str = "", 
        parent: Optional[QWidget] = None,
        min_width: int = 350,
        placeholder: str = "",
        yes_text: str = "确定",
        cancel_text: str = "取消",
        validator: Optional[Callable[[str], bool]] = None,
        multi_line: bool = False,
        is_password: bool = False,
    ):
        super().__init__(parent)
        
        # 标题
        self.titleLabel = SubtitleLabel(title, self)
        self.viewLayout.addWidget(self.titleLabel)
        
        # 输入控件（支持单行/多行）
        if multi_line:
            self.input_edit = PlainTextEdit(self)
            self.input_edit.setPlainText(default_text)
            self.input_edit.setPlaceholderText(placeholder or label)
            self.input_edit.setFixedHeight(100)
        else:
            self.input_edit = LineEdit(self)
            self.input_edit.setText(default_text)
            self.input_edit.setPlaceholderText(placeholder or label)
            self.input_edit.setClearButtonEnabled(True)
            if is_password:
                self.input_edit.setEchoMode(LineEdit.Password)
            self.input_edit.returnPressed.connect(lambda: self.yesButton.click())
        
        self.viewLayout.addWidget(self.input_edit)
        
        # 自定义按钮文本
        self.yesButton.setText(yes_text)
        self.cancelButton.setText(cancel_text)
        
        # 自定义最小宽度
        self.widget.setMinimumWidth(min_width)
        
        # 设置焦点
        if not multi_line:
            self.input_edit.setFocus()
        
        # 自定义验证器
        self._validator = validator
    
    def get_text(self) -> str:
        """获取输入文本"""
        if hasattr(self.input_edit, 'toPlainText'):
            return self.input_edit.toPlainText().strip()
        return self.input_edit.text().strip()
    
    def validate(self) -> bool:
        """验证输入"""
        text = self.get_text()
        
        # 使用自定义验证器
        if self._validator is not None:
            return self._validator(text)
        
        # 默认验证：非空
        return bool(text)
