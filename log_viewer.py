"""
log_viewer.py - 日志显示组件
支持等宽字体显示、自动滚动、最大行数限制
后续可扩展关键词高亮和过滤功能
"""

from PySide6.QtWidgets import QTextEdit, QWidget, QVBoxLayout
from PySide6.QtGui import QFont, QTextCursor, QColor, QTextCharFormat
from PySide6.QtCore import Qt


class LogViewer(QWidget):
    """
    日志显示组件，基于 QTextEdit（只读）。
    提供 append_data() 方法接收字节数据并显示。
    """

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self._config = config
        self._max_lines: int = config.get("ui", {}).get("max_log_lines", 5000)
        self._auto_scroll: bool = True
        self._show_hex: bool = False        # 是否以 HEX 格式显示
        self._line_count: int = 0

        self._init_ui()

    # ── 初始化 UI ─────────────────────────────

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        # 等宽字体
        font_family = self._config.get("ui", {}).get("font_family", "Consolas")
        font_size = self._config.get("ui", {}).get("font_size", 10)
        font = QFont(font_family, font_size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._text_edit.setFont(font)

        # 深色背景风格
        self._text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                selection-background-color: #264f78;
            }
        """)

        layout.addWidget(self._text_edit)

    # ── 公开接口 ──────────────────────────────

    def append_data(self, data: bytes):
        """
        追加接收到的字节数据到日志区。
        根据 _show_hex 决定显示格式。
        """
        if self._show_hex:
            text = self._bytes_to_hex(data)
        else:
            text = self._bytes_to_text(data)

        self._append_text(text, color="#4ec9b0")   # 接收数据用青绿色

    def append_sent(self, data: bytes):
        """追加已发送的数据到日志区（用不同颜色区分）"""
        if self._show_hex:
            text = "[TX] " + self._bytes_to_hex(data)
        else:
            text = "[TX] " + self._bytes_to_text(data)

        self._append_text(text, color="#ce9178")   # 发送数据用橙色

    def append_info(self, msg: str):
        """追加系统信息（灰色）"""
        self._append_text(f"[INFO] {msg}", color="#808080")

    def append_error(self, msg: str):
        """追加错误信息（红色）"""
        self._append_text(f"[ERROR] {msg}", color="#f44747")

    def clear(self):
        """清空日志"""
        self._text_edit.clear()
        self._line_count = 0

    def set_auto_scroll(self, enabled: bool):
        """设置是否自动滚动到底部"""
        self._auto_scroll = enabled

    def set_show_hex(self, enabled: bool):
        """切换 HEX / 文本显示模式"""
        self._show_hex = enabled

    def set_max_lines(self, n: int):
        """设置最大保留行数"""
        self._max_lines = max(100, n)

    # ── 内部方法 ──────────────────────────────

    def _append_text(self, text: str, color: str = "#d4d4d4"):
        """向 QTextEdit 追加带颜色的文本"""
        cursor = self._text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.setCharFormat(fmt)
        cursor.insertText(text)

        # 统计行数并裁剪超出部分
        new_lines = text.count('\n')
        self._line_count += new_lines
        if self._line_count > self._max_lines:
            self._trim_old_lines()

        # 自动滚动
        if self._auto_scroll:
            self._text_edit.setTextCursor(cursor)
            self._text_edit.ensureCursorVisible()

    def _trim_old_lines(self):
        """删除最旧的若干行，保持在 max_lines 以内"""
        doc = self._text_edit.document()
        # 每次删除 max_lines // 4 行，减少频繁操作
        lines_to_remove = self._max_lines // 4
        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        for _ in range(lines_to_remove):
            cursor.movePosition(
                QTextCursor.MoveOperation.Down,
                QTextCursor.MoveMode.KeepAnchor
            )
        cursor.removeSelectedText()
        self._line_count -= lines_to_remove

    @staticmethod
    def _bytes_to_text(data: bytes) -> str:
        """将字节数据解码为可显示文本（无法解码的字节用 ? 替代）"""
        try:
            return data.decode("utf-8", errors="replace")
        except Exception:
            return data.decode("latin-1", errors="replace")

    @staticmethod
    def _bytes_to_hex(data: bytes) -> str:
        """将字节数据转换为 HEX 字符串，每行 16 字节"""
        lines = []
        for i in range(0, len(data), 16):
            chunk = data[i:i + 16]
            hex_part = " ".join(f"{b:02X}" for b in chunk)
            lines.append(hex_part)
        return "\n".join(lines) + "\n"
