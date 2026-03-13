from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QPoint, QTimer, QObject
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QGuiApplication, QFontMetrics
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QPushButton,
    QTextEdit,
    QLineEdit,
    QVBoxLayout,
    QSizePolicy,
)


_MENU_STYLE = """
QFrame#MenuPanel {
    background: transparent;
    border: none;
}

QPushButton#MenuItem {
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 0 14px;
    margin: 0;
    min-width: 0;
    min-height: 34px;
    text-align: left;
    color: #1f2937;
    font-size: 13px;
    font-family: "Microsoft YaHei UI", "PingFang SC", "Segoe UI", sans-serif;
}

QPushButton#MenuItem:hover {
    background: #eef2ff;
    border: none;
}

QPushButton#MenuItem:pressed {
    background: #e0e7ff;
    border: none;
}

QPushButton#MenuItem:disabled {
    color: #9ca3af;
    background: transparent;
    border: none;
}

QFrame#MenuSeparator {
    background: #e5e7eb;
    min-height: 1px;
    max-height: 1px;
    margin: 3px 10px;
}
"""


def _normalize_action_text(text: str) -> str:
    clean = text.split("\t")[0].replace("&", "").strip()
    mapping = {
        "undo": "撤销",
        "redo": "重做",
        "cut": "剪切",
        "copy": "复制",
        "paste": "粘贴",
        "delete": "删除",
        "select all": "全选",
        "paste and match style": "粘贴并匹配样式",
    }
    return mapping.get(clean.lower(), clean)


class _MenuAction(QObject):
    """模拟 QAction 的轻量 action 对象"""
    triggered = Signal()

    def __init__(self, text: str, enabled: bool = True, parent=None):
        super().__init__(parent)
        self._text = text
        self._enabled = enabled

    @property
    def text(self) -> str:
        return self._text

    @property
    def enabled(self) -> bool:
        return self._enabled

    def setEnabled(self, enabled: bool):
        self._enabled = enabled

    def trigger(self):
        if self._enabled:
            self.triggered.emit()


class RoundedMenu(QDialog):
    """自定义圆角弹出菜单"""
    RADIUS = 8
    BG_COLOR = QColor("#ffffff")
    BORDER_COLOR = QColor("#e5e7eb")
    H_PADDING = 14
    ITEM_HEIGHT = 34
    PANEL_MARGIN = 6
    MIN_MENU_WIDTH = 0
    EXTRA_WIDTH = 6

    def __init__(self, parent=None):
        super().__init__(parent)
        self._actions = []
        self._selected_action = None
        self._last_added_separator = False
        self._max_text_width = 0

        self._init_window()
        self._init_layout()

    def _init_window(self):
        self.setWindowFlags(
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setStyleSheet(_MENU_STYLE)

    def _init_layout(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._panel = QFrame(self)
        self._panel.setObjectName("MenuPanel")
        main_layout.addWidget(self._panel)

        self._vbox = QVBoxLayout(self._panel)
        self._vbox.setContentsMargins(self.PANEL_MARGIN, self.PANEL_MARGIN, self.PANEL_MARGIN, self.PANEL_MARGIN)
        self._vbox.setSpacing(2)

    def addAction(self, text: str, enabled: bool = True) -> _MenuAction:
        btn = QPushButton(text, self._panel)
        btn.setObjectName("MenuItem")
        btn.setEnabled(enabled)
        btn.setCursor(
            Qt.CursorShape.PointingHandCursor
            if enabled else Qt.CursorShape.ArrowCursor
        )
        btn.setFlat(True)
        btn.setAutoDefault(False)
        btn.setDefault(False)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setFixedHeight(self.ITEM_HEIGHT)
        btn.setMinimumWidth(0)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        btn.ensurePolished()
        text_width = QFontMetrics(btn.font()).horizontalAdvance(text)
        self._max_text_width = max(self._max_text_width, text_width)

        action = _MenuAction(text, enabled, self)
        self._actions.append(action)

        def on_clicked():
            if not action.enabled:
                return
            self._selected_action = action
            self.accept()
            QTimer.singleShot(0, action.trigger)

        btn.clicked.connect(on_clicked)
        self._vbox.addWidget(btn)
        self._last_added_separator = False
        return action

    def addSeparator(self):
        if self._vbox.count() == 0 or self._last_added_separator:
            return

        sep = QFrame(self._panel)
        sep.setObjectName("MenuSeparator")
        sep.setFixedHeight(1)
        self._vbox.addWidget(sep)
        self._last_added_separator = True

    def _apply_dynamic_width(self):
        content_width = max(
            self.MIN_MENU_WIDTH,
            self._max_text_width + self.H_PADDING * 2 + self.EXTRA_WIDTH,
        )
        total_width = content_width + self.PANEL_MARGIN * 2
        self.setFixedWidth(int(total_width))

    def exec(self, global_pos: QPoint = None):
        self._apply_dynamic_width()
        self.adjustSize()

        if global_pos is None:
            screen = QGuiApplication.primaryScreen()
            if screen is not None:
                global_pos = QGuiApplication.primaryScreen().cursor().pos()
            else:
                global_pos = QPoint(0, 0)

        if not isinstance(global_pos, QPoint):
            global_pos = QPoint(global_pos)

        screen = QGuiApplication.screenAt(global_pos)
        if screen is None:
            screen = QGuiApplication.primaryScreen()

        if screen is not None:
            screen_geo = screen.availableGeometry()
            menu_width = self.width()
            menu_height = self.height()

            x = global_pos.x()
            y = global_pos.y()

            if x + menu_width > screen_geo.right():
                x = screen_geo.right() - menu_width
            if x < screen_geo.left():
                x = screen_geo.left()

            if y + menu_height > screen_geo.bottom():
                y = screen_geo.bottom() - menu_height
            if y < screen_geo.top():
                y = screen_geo.top()

            self.move(int(x), int(y))
        else:
            self.move(global_pos)

        self._selected_action = None
        super().exec()
        return self._selected_action

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        rect = self.rect().adjusted(0, 0, -1, -1)

        path = QPainterPath()
        path.addRoundedRect(rect, self.RADIUS, self.RADIUS)

        painter.fillPath(path, self.BG_COLOR)

        pen = QPen(self.BORDER_COLOR)
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        painter.end()


class RoundedContextTextEdit(QTextEdit):
    """自定义文本编辑框，提供圆角右键菜单"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_rounded_context_menu)

    def _show_rounded_context_menu(self, pos):
        src_menu = self.createStandardContextMenu()
        menu = RoundedMenu(self.window())

        last_was_separator = True
        for act in src_menu.actions():
            if act.isSeparator():
                if not last_was_separator:
                    menu.addSeparator()
                    last_was_separator = True
                continue

            text = _normalize_action_text(act.text())
            if not text:
                continue

            custom_act = menu.addAction(text, act.isEnabled())
            if act.isEnabled():
                custom_act.triggered.connect(act.trigger)

            last_was_separator = False

        menu.exec(self.mapToGlobal(pos))
        src_menu.deleteLater()


class RoundedContextLineEdit(QLineEdit):
    """自定义单行输入框，提供圆角右键菜单"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_rounded_context_menu)

    def _show_rounded_context_menu(self, pos):
        src_menu = self.createStandardContextMenu()
        menu = RoundedMenu(self.window())

        last_was_separator = True
        for act in src_menu.actions():
            if act.isSeparator():
                if not last_was_separator:
                    menu.addSeparator()
                    last_was_separator = True
                continue

            text = _normalize_action_text(act.text())
            if not text:
                continue

            custom_act = menu.addAction(text, act.isEnabled())
            if act.isEnabled():
                custom_act.triggered.connect(act.trigger)

            last_was_separator = False

        menu.exec(self.mapToGlobal(pos))
        src_menu.deleteLater()