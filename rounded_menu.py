from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QPoint, QEvent, QTimer, QObject
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QGuiApplication, QFontMetrics
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
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
    min-height: 30px;
    text-align: left;
    color: #1f2937;
    font-size: 12px;
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


class _MenuAction(QObject):
    """模拟 QAction 的自定义 Action 对象"""
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
    """自定义圆角弹出菜单，彻底绕过 QMenu 的渲染链"""
    RADIUS = 8
    BG_COLOR = QColor("#ffffff")
    BORDER_COLOR = QColor("#e5e7eb")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._actions = []  # 保存 _MenuAction 对象
        self._selected_action = None
        self._max_text_width = 0  # 记录最长文本宽度
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
        # 主容器
        self._panel = QFrame(self)
        self._panel.setObjectName("MenuPanel")

        # 主布局添加 panel
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self._panel)

        # 垂直布局直接作为 panel 的布局
        self._vbox = QVBoxLayout(self._panel)
        self._vbox.setContentsMargins(6, 6, 6, 6)
        self._vbox.setSpacing(2)

    def addAction(self, text: str, enabled: bool = True) -> _MenuAction:
        """添加菜单项，返回一个 _MenuAction 对象"""
        btn = QPushButton(text, self._panel)
        btn.setObjectName("MenuItem")
        btn.setEnabled(enabled)
        btn.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
        btn.setFlat(True)
        btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        # 计算文本宽度
        font_metrics = QFontMetrics(btn.font())
        text_width = font_metrics.horizontalAdvance(text)
        self._max_text_width = max(self._max_text_width, text_width)

        action = _MenuAction(text, enabled, self)
        self._actions.append(action)

        def on_clicked():
            self._selected_action = action
            self.accept()

        btn.clicked.connect(on_clicked)
        self._vbox.addWidget(btn)
        return action

    def addSeparator(self):
        """添加分隔线"""
        sep = QFrame(self._panel)
        sep.setObjectName("MenuSeparator")
        sep.setFixedHeight(1)
        self._vbox.addWidget(sep)

    def exec(self, global_pos: QPoint = None):
        """弹出菜单，返回被点击的 action（模拟 QMenu.exec）"""
        # 根据最长文本设置固定宽度
        if self._max_text_width > 0:
            # 总宽度 = 文本宽度 + 左右padding(14*2) + 左右margins(6*2)
            total_width = self._max_text_width + 14 * 2 + 6 * 2
            # 加上一些额外空间，确保文本不会贴边
            total_width += 10
            # 设置固定宽度
            self.setFixedWidth(int(total_width))
        
        self.adjustSize()

        if global_pos is None:
            # 默认在鼠标位置
            global_pos = QGuiApplication.primaryScreen().cursor().pos()
        else:
            # 确保 global_pos 是 QPoint
            if not isinstance(global_pos, QPoint):
                global_pos = QPoint(global_pos)

        # 安全定位：确保菜单不会跑出屏幕
        screen = QGuiApplication.screenAt(global_pos)
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        screen_geo = screen.availableGeometry()
        menu_width = self.width()
        menu_height = self.height()

        # 尝试在鼠标右下角显示
        x = global_pos.x()
        y = global_pos.y()

        # 如果右侧空间不够，向左移
        if x + menu_width > screen_geo.right():
            x = screen_geo.right() - menu_width
        if x < screen_geo.left():
            x = screen_geo.left()

        # 如果底部空间不够，向上移
        if y + menu_height > screen_geo.bottom():
            y = screen_geo.bottom() - menu_height
        if y < screen_geo.top():
            y = screen_geo.top()

        self.move(int(x), int(y))
        self._selected_action = None
        super().exec()
        return self._selected_action

    def paintEvent(self, event):
        """绘制圆角白底和边框"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        rect = self.rect().adjusted(0, 0, -1, -1)  # 留出1px边框空间
        path = QPainterPath()
        path.addRoundedRect(rect, self.RADIUS, self.RADIUS)

        # 填充白色背景
        painter.fillPath(path, self.BG_COLOR)

        # 绘制边框
        pen = QPen(self.BORDER_COLOR)
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        painter.end()

    def event(self, event):
        """处理点击外部关闭"""
        if event.type() == QEvent.Type.MouseButtonPress:
            # 点击在窗口外，关闭
            if not self.rect().contains(event.pos()):
                self.reject()
                return True
        return super().event(event)


class RoundedContextTextEdit(QTextEdit):
    """自定义文本编辑框，提供圆角右键菜单"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_rounded_context_menu)

    def _show_rounded_context_menu(self, pos):
        """显示自定义右键菜单"""
        src_menu = self.createStandardContextMenu()
        menu = RoundedMenu(self.window())

        for act in src_menu.actions():
            if act.isSeparator():
                menu.addSeparator()
                continue

            text = act.text().split('\t')[0].replace('&', '').strip()
            if not text:
                continue

            custom_act = menu.addAction(text, act.isEnabled())
            if act.isEnabled():
                custom_act.triggered.connect(act.trigger)

        src_menu.deleteLater()
        menu.exec(self.mapToGlobal(pos))
