"""
widgets.py - 可复用公共组件
v0.7 — 从 settings_dialog.py / filter_manager.py 提取

统一关闭按钮、圆形按钮、无界按钮、分隔线、圆角滚动容器等。
所有组件依赖 theme.py 常量，不裸写颜色/字号。
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QScrollBar,
)
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import (
    QPainter, QPainterPath, QColor, QPen, QRegion,
    QPixmap,
)
from PySide6.QtSvg import QSvgRenderer

from theme import (
    PRIMARY, PRIMARY_HOVER, PRIMARY_NAV,
    BG_PANEL, BG_HOVER, BG_PRESSED, BG_SUBTLE,
    BG_SELECTED_ROW,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    TEXT_DISABLED, TEXT_ARROW,
    BORDER_DEFAULT, BORDER_FOCUS, BORDER_LIGHT,
    BORDER_PANEL,
    TITLEBAR_HOVER, TITLEBAR_PRESSED,
    CLOSE_FG, CLOSE_FG_HOVER, CLOSE_FG_PRESSED,
    ERROR, ERROR_DARK, ERROR_HOVER_BG,
    ERROR_PRESSED_BG,
    CLOSE_BTN_SIZE, CLOSE_BTN_HOVER_RADIUS,
    LABEL_FONT_SIZE, SMALL_FONT_SIZE,
    SEPARATOR_HEIGHT,
    checkbox_ss, nav_btn_ss, separator_ss,
)


# ════════════════════════════════════════════
# ★ 统一关闭按钮（drawLine × 号，视觉居中精确）
# ════════════════════════════════════════════
class CloseBtn(QWidget):
    """Notion 风格关闭按钮 — 灰色×号 + hover 浅灰圆圈背景
    统一使用 drawLine 绘制，不用 drawText，解决字形偏移问题"""
    clicked = Signal()

    def __init__(self, size=CLOSE_BTN_SIZE, parent=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
        self._hovered = False
        self._pressed = False

    def enterEvent(self, e):
        self._hovered = True; self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False; self._pressed = False
        self.update(); super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._pressed = True; self.update()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        was = self._pressed
        self._pressed = False; self.update()
        if was and e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(e)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        cx, cy = self.width() / 2.0, self.height() / 2.0
        # hover/pressed 圆圈背景
        if self._pressed or self._hovered:
            bg = QColor(TITLEBAR_PRESSED if self._pressed
                        else TITLEBAR_HOVER)
            radius = CLOSE_BTN_HOVER_RADIUS
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(bg)
            p.drawEllipse(QRectF(
                cx - radius, cy - radius,
                radius * 2, radius * 2,
            ))
        # × 号（drawLine，RoundCap）
        if self._pressed:
            fg = QColor(CLOSE_FG_PRESSED)
        elif self._hovered:
            fg = QColor(CLOSE_FG_HOVER)
        else:
            fg = QColor(CLOSE_FG)
        pen = QPen(fg, 1.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        d = 3.5
        p.drawLine(QPointF(cx - d, cy - d),
                   QPointF(cx + d, cy + d))
        p.drawLine(QPointF(cx + d, cy - d),
                   QPointF(cx - d, cy + d))
        p.end()


# ════════════════════════════════════════════
# ★ 圆形 hover 按钮（paintEvent 绘制）
# ════════════════════════════════════════════
class CircleBtn(QWidget):
    """paintEvent + drawEllipse 圆形背景 + 居中文字"""
    clicked = Signal()

    def __init__(self, text, size=22, parent=None):
        super().__init__(parent)
        self._text = text
        self._hovered = False
        self._pressed = False
        self._fg = TEXT_MUTED
        self._fg_hover = TEXT_PRIMARY
        self._fg_pressed = "#1f2937"
        self._bg_hover = BG_HOVER
        self._bg_pressed = BG_PRESSED
        self._font_size = 16
        self._font_weight = 700
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)

    def enterEvent(self, e):
        self._hovered = True; self.update()

    def leaveEvent(self, e):
        self._hovered = False; self._pressed = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._pressed = True; self.update()

    def mouseReleaseEvent(self, e):
        was = self._pressed
        self._pressed = False; self.update()
        if was and e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        cx, cy = self.width() / 2.0, self.height() / 2.0
        r = min(cx, cy)
        if self._pressed:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(self._bg_pressed))
            p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
            fg = self._fg_pressed
        elif self._hovered:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(self._bg_hover))
            p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
            fg = self._fg_hover
        else:
            fg = self._fg
        p.setBrush(Qt.BrushStyle.NoBrush)
        font = p.font()
        font.setPixelSize(self._font_size)
        font.setBold(self._font_weight >= 600)
        p.setFont(font)
        p.setPen(QColor(fg))
        p.drawText(
            QRectF(0, 0, self.width(), self.height()),
            Qt.AlignmentFlag.AlignCenter, self._text,
        )
        p.end()


# ════════════════════════════════════════════
# ★ 左侧导航按钮
# ════════════════════════════════════════════
class NavBtn(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setFixedHeight(34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(nav_btn_ss())


# ════════════════════════════════════════════
# ★ 重置按钮（无界设计，hover/pressed 才显示背景色）
# ════════════════════════════════════════════
class ResetBtn(QPushButton):
    def __init__(self, parent=None):
        super().__init__("重置", parent)
        self.setFixedSize(52, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
        self._hovered = False
        self._pressed = False
        self._apply_style()

    def enterEvent(self, e):
        self._hovered = True; self._apply_style()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False; self._pressed = False
        self._apply_style(); super().leaveEvent(e)

    def mousePressEvent(self, e):
        self._pressed = True; self._apply_style()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._pressed = False; self._apply_style()
        super().mouseReleaseEvent(e)

    def _apply_style(self):
        if self._pressed:
            self.setStyleSheet(
                f"QPushButton{{background:{ERROR_PRESSED_BG};"
                f"border:none;border-radius:6px;"
                f"font-size:{LABEL_FONT_SIZE}px;"
                f"color:{ERROR_DARK};}}"
            )
        elif self._hovered:
            self.setStyleSheet(
                f"QPushButton{{background:{ERROR_HOVER_BG};"
                f"border:none;border-radius:6px;"
                f"font-size:{LABEL_FONT_SIZE}px;"
                f"color:{ERROR};}}"
            )
        else:
            self.setStyleSheet(
                f"QPushButton{{background:transparent;"
                f"border:none;border-radius:6px;"
                f"font-size:{LABEL_FONT_SIZE}px;"
                f"color:{TEXT_SECONDARY};}}"
            )


# ════════════════════════════════════════════
# ★ 分隔线工厂函数
# ════════════════════════════════════════════
def make_separator() -> QFrame:
    """创建统一风格分隔线（2px #e5e7eb）"""
    sep = QFrame()
    sep.setFixedHeight(SEPARATOR_HEIGHT)
    sep.setStyleSheet(separator_ss())
    return sep


# ════════════════════════════════════════════
# ★ 圆角滚动容器（叠加层边框 + 圆角背景）
# ════════════════════════════════════════════
class _BorderOverlay(QWidget):
    """透明叠加层 — 在所有子控件之上绘制边框"""
    def __init__(self, parent, radius=6):
        super().__init__(parent)
        self._radius = radius
        self._border_color = QColor(BORDER_DEFAULT)
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, True
        )

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(0.75, 0.75, -0.75, -0.75)
        p.setPen(QPen(self._border_color, 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r, self._radius, self._radius)
        p.end()


class RoundedScrollContainer(QWidget):
    """圆角滚动容器 — 背景在底层，边框在叠加层"""
    def __init__(self, scroll_area: QScrollArea, parent=None):
        super().__init__(parent)
        self._scroll = scroll_area
        self._radius = 6
        self._bg_color = QColor(BG_PANEL)
        self._scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            "QScrollBar:vertical {"
            "  width: 4px; background: transparent; }"
            "QScrollBar::handle:vertical {"
            f"  background: {BORDER_DEFAULT};"
            "  border-radius: 2px; }"
            "QScrollBar::add-line, QScrollBar::sub-line {"
            "  width: 0; height: 0; }"
        )
        self._scroll.viewport().setAutoFillBackground(False)
        self._scroll.viewport().setStyleSheet(
            "background: transparent;"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(0)
        lay.addWidget(self._scroll)
        self._overlay = _BorderOverlay(self, self._radius)
        self._overlay.setGeometry(self.rect())
        self._overlay.raise_()

    def setMaximumHeight(self, h):
        super().setMaximumHeight(h)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._overlay.setGeometry(self.rect())
        self._overlay.raise_()

    def showEvent(self, event):
        super().showEvent(event)
        self._overlay.setGeometry(self.rect())
        self._overlay.raise_()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        bg_path = QPainterPath()
        bg_path.addRoundedRect(r, self._radius, self._radius)
        p.fillPath(bg_path, self._bg_color)
        p.end()


# ════════════════════════════════════════════
# ★ 列表选择项（圆形指示器替代 QCheckBox）
# ════════════════════════════════════════════
class TagChip(QWidget):
    """列表选择项 — 圆形指示器 + 文字，无多选框"""
    toggled = Signal(bool)

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self._text = text
        self._checked = False
        self._hovered = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
        self.setFixedHeight(26)

    def text(self): return self._text
    def isChecked(self): return self._checked

    def setChecked(self, checked):
        if self._checked == checked: return
        self._checked = checked
        self.update()
        self.toggled.emit(checked)

    def enterEvent(self, e):
        self._hovered = True; self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False; self.update()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if not self.isEnabled(): return
        if e.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        h = self.height()
        w = self.width()
        if not self.isEnabled():
            font = p.font(); font.setPixelSize(12)
            p.setFont(font)
            p.setPen(QColor(TEXT_DISABLED))
            p.drawText(
                QRectF(16.0, 0, w - 16.0, h),
                Qt.AlignmentFlag.AlignVCenter
                | Qt.AlignmentFlag.AlignLeft,
                self._text,
            )
            p.end(); return
        if self._checked:
            bg_path = QPainterPath()
            bg_path.addRoundedRect(QRectF(0, 0, w, h), 4, 4)
            p.fillPath(bg_path, QColor(BG_PANEL))
            bar_h = 14.0
            bar_y = (h - bar_h) / 2.0
            bar_path = QPainterPath()
            bar_path.addRoundedRect(
                QRectF(4, bar_y, 2.5, bar_h), 1.2, 1.2
            )
            p.fillPath(bar_path, QColor(PRIMARY))
            fg = QColor(PRIMARY)
        else:
            if self._hovered:
                hover_path = QPainterPath()
                hover_path.addRoundedRect(
                    QRectF(0, 0, w, h), 4, 4
                )
                p.fillPath(hover_path, QColor(BG_SUBTLE))
            fg = QColor(TEXT_SECONDARY)
        font = p.font(); font.setPixelSize(12)
        p.setFont(font)
        p.setPen(fg)
        p.drawText(
            QRectF(16.0, 0, w - 16.0, h),
            Qt.AlignmentFlag.AlignVCenter
            | Qt.AlignmentFlag.AlignLeft,
            self._text,
        )
        p.end()


# ════════════════════════════════════════════
# ★ 齿轮图标 Label（设置标题栏左侧）
# ════════════════════════════════════════════
_GEAR_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" '
    'width="16" height="16" viewBox="0 0 24 24" '
    'fill="none" stroke="{color}" stroke-width="1.8" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 '
    '1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73'
    'l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51'
    'a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 '
    '2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 '
    '1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 '
    '0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 '
    '2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 '
    '1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 '
    '.73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 '
    '1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>'
    '<circle cx="12" cy="12" r="3"/></svg>'
)


def _render_mini_gear(color: str, size: int = 14) -> QPixmap:
    from PySide6.QtWidgets import QApplication
    screen = QApplication.primaryScreen()
    dpr = screen.devicePixelRatio() if screen else 1.0
    real = int(size * dpr)
    svg_data = _GEAR_SVG.format(color=color).encode("utf-8")
    pixmap = QPixmap(real, real)
    pixmap.fill(Qt.GlobalColor.transparent)
    pixmap.setDevicePixelRatio(dpr)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer = QSvgRenderer(svg_data)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return pixmap


class GearIconLabel(QLabel):
    """在标题栏左侧显示齿轮图标"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        gear = _render_mini_gear(TEXT_SECONDARY, 14)
        dpr = gear.devicePixelRatio()
        lw = int(gear.width() / dpr)
        lh = int(gear.height() / dpr)
        x = (self.width() - lw) // 2
        y = (self.height() - lh) // 2
        p.drawPixmap(x, y, gear)
        p.end()


# ════════════════════════════════════════════
# ★ 带三角箭头的自定义滚动条
# ════════════════════════════════════════════
class ArrowScrollBar(QScrollBar):
    """竖向滚动条 — 顶/底绘制三角箭头指示器"""
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Vertical, parent)
        self.setStyleSheet(
            "QScrollBar:vertical{"
            "  width:8px;background:transparent;"
            "  margin:12px 0 12px 0}"
            "QScrollBar::handle:vertical{"
            f"  background:{BORDER_DEFAULT};border-radius:3px;"
            "  min-height:20px}"
            f"QScrollBar::handle:vertical:hover{{background:{BORDER_FOCUS}}}"
            "QScrollBar::sub-line:vertical{height:10px;background:transparent}"
            "QScrollBar::add-line:vertical{height:10px;background:transparent}"
            "QScrollBar::add-page,QScrollBar::sub-page{background:transparent}"
        )

    def paintEvent(self, event):
        if self.maximum() <= 0:
            return
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(TEXT_ARROW))
        w = self.width()
        cx = w / 2.0
        # ▲ 上三角
        up = QPainterPath()
        up.moveTo(cx, 2)
        up.lineTo(cx + 3, 8)
        up.lineTo(cx - 3, 8)
        up.closeSubpath()
        p.drawPath(up)
        # ▼ 下三角
        h = self.height()
        dn = QPainterPath()
        dn.moveTo(cx, h - 2)
        dn.lineTo(cx + 3, h - 8)
        dn.lineTo(cx - 3, h - 8)
        dn.closeSubpath()
        p.drawPath(dn)
        p.end()