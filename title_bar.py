"""
title_bar.py - 标题栏组件
v0.44 — ★ 覆盖 qframelesswindow 库 min/max/close 按钮 paintEvent
        ★ 圆润 Notion 风格图标（细线条 + round cap + round join）
        ★ SettingsButton（SVG 齿轮 + HiDPI）
"""
from __future__ import annotations

from PySide6.QtWidgets import QPushButton, QApplication
from PySide6.QtCore import Qt, QPoint, QRectF
from PySide6.QtGui import QPainter, QColor, QPixmap, QPen, QPainterPath
from PySide6.QtSvg import QSvgRenderer


# ══════════════════════════════════════════
# ★ Lucide 标准 settings 齿轮 SVG
# ══════════════════════════════════════════
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


def _render_gear(color: str, size: int = 16) -> QPixmap:
    """将 SVG 齿轮渲染为 QPixmap（支持 HiDPI）"""
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


# ══════════════════════════════════════════
# ★ 覆盖库按钮 paintEvent — 圆润 Notion 风格
# ══════════════════════════════════════════
_HOVER_BG = QColor("#e8e8e8")
_PRESSED_BG = QColor("#d2d2d2")
_CLOSE_HOVER_BG = QColor("#e81123")
_CLOSE_PRESSED_BG = QColor("#c42b1c")
_ICON_COLOR = QColor("#868686")
_ICON_CLOSE_COLOR = QColor("#868686")
_ICON_CLOSE_HOVER = QColor("#ffffff")


def _btn_state(btn):
    """读取按钮 hover / pressed 状态"""
    hovered = btn.property("_custom_hover") or False
    pressed = btn.property("_custom_press") or False
    return hovered, pressed


def _install_hover_tracking(btn):
    """为按钮安装 hover 追踪（不替换原有逻辑）"""
    btn.setProperty("_custom_hover", False)
    btn.setProperty("_custom_press", False)
    btn.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
    btn.setMouseTracking(True)

    orig_enter = btn.enterEvent
    orig_leave = btn.leaveEvent
    orig_press = btn.mousePressEvent
    orig_release = btn.mouseReleaseEvent

    def enter(e):
        btn.setProperty("_custom_hover", True)
        btn.update()
        orig_enter(e)

    def leave(e):
        btn.setProperty("_custom_hover", False)
        btn.setProperty("_custom_press", False)
        btn.update()
        orig_leave(e)

    def press(e):
        btn.setProperty("_custom_press", True)
        btn.update()
        orig_press(e)

    def release(e):
        btn.setProperty("_custom_press", False)
        btn.update()
        orig_release(e)

    btn.enterEvent = enter
    btn.leaveEvent = leave
    btn.mousePressEvent = press
    btn.mouseReleaseEvent = release


def _paint_minimize(btn, event):
    """最小化：细横线，圆角端点"""
    p = QPainter(btn)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    hovered, pressed = _btn_state(btn)
    if pressed:
        p.fillRect(btn.rect(), _PRESSED_BG)
    elif hovered:
        p.fillRect(btn.rect(), _HOVER_BG)
    pen = QPen(_ICON_COLOR, 1.0)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    cx, cy = btn.width() / 2, btn.height() / 2
    p.drawLine(
        QPoint(int(cx - 5), int(cy)),
        QPoint(int(cx + 5), int(cy)),
    )
    p.end()


def _paint_maximize(btn, event):
    """放大：圆角矩形（Notion 风格）"""
    p = QPainter(btn)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    hovered, pressed = _btn_state(btn)
    if pressed:
        p.fillRect(btn.rect(), _PRESSED_BG)
    elif hovered:
        p.fillRect(btn.rect(), _HOVER_BG)
    pen = QPen(_ICON_COLOR, 1.0)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    cx, cy = btn.width() / 2, btn.height() / 2
    # ★ 8x8 圆角矩形，radius=1.5（柔和的 Notion 风格）
    rect = QRectF(cx - 4.5, cy - 4, 9, 8)
    p.drawRoundedRect(rect, 1.5, 1.5)
    p.end()


def _paint_maximize_restore(btn, event):
    """还原（双矩形叠加，圆角风格）"""
    p = QPainter(btn)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    hovered, pressed = _btn_state(btn)
    if pressed:
        p.fillRect(btn.rect(), _PRESSED_BG)
    elif hovered:
        p.fillRect(btn.rect(), _HOVER_BG)
    pen = QPen(_ICON_COLOR, 1.0)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    cx, cy = btn.width() / 2, btn.height() / 2
    # 后层矩形（右上偏移）
    back = QRectF(cx - 2.5, cy - 5, 8, 7)
    p.drawRoundedRect(back, 1.5, 1.5)
    # 前层矩形（左下，白底遮挡）
    front = QRectF(cx - 5.5, cy - 2.5, 8, 7)
    p.save()
    p.setBrush(QColor("#eef0f3"))  # 标题栏背景色
    p.setPen(pen)
    p.drawRoundedRect(front, 1.5, 1.5)
    p.restore()
    p.end()


def _paint_close(btn, event):
    """关闭：细 X 线条，圆角端点"""
    p = QPainter(btn)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    hovered, pressed = _btn_state(btn)
    if pressed:
        # ★ 右上角圆角路径，防止红色溢出窗口边角
        path = QPainterPath()
        r = QRectF(btn.rect())
        path.addRect(r)
        p.fillPath(path, _CLOSE_PRESSED_BG)
    elif hovered:
        path = QPainterPath()
        r = QRectF(btn.rect())
        path.addRect(r)
        p.fillPath(path, _CLOSE_HOVER_BG)
    # X 号颜色
    fg = (
        _ICON_CLOSE_HOVER
        if (hovered or pressed)
        else _ICON_CLOSE_COLOR
    )
    pen = QPen(fg, 1.0)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    cx, cy = btn.width() / 2, btn.height() / 2
    d = 4.5
    p.drawLine(
        QPoint(int(cx - d), int(cy - d)),
        QPoint(int(cx + d), int(cy + d)),
    )
    p.drawLine(
        QPoint(int(cx + d), int(cy - d)),
        QPoint(int(cx - d), int(cy + d)),
    )
    p.end()


def customize_titlebar_buttons(titlebar):
    """
    覆盖 qframelesswindow 库 min/max/close 按钮的 paintEvent
    ★ 圆润 Notion 风格图标 + hover/pressed 状态
    """
    min_btn = titlebar.minBtn
    max_btn = titlebar.maxBtn
    close_btn = titlebar.closeBtn

    for btn in (min_btn, max_btn, close_btn):
        _install_hover_tracking(btn)

    # ★ 覆盖 paintEvent
    min_btn.paintEvent = lambda e: _paint_minimize(min_btn, e)

    # max 按钮需要根据窗口状态切换 maximize / restore
    def _max_paint(e):
        win = titlebar.window()
        if win and win.isMaximized():
            _paint_maximize_restore(max_btn, e)
        else:
            _paint_maximize(max_btn, e)

    max_btn.paintEvent = _max_paint
    close_btn.paintEvent = lambda e: _paint_close(close_btn, e)


# ══════════════════════════════════════════
# ★ 设置齿轮按钮
# ══════════════════════════════════════════
class SettingsButton(QPushButton):
    """设置齿轮按钮 — 与原生标题栏按钮风格统一"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(46, 32)
        self.setFlat(True)
        self.setToolTip("设置")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hovered = False
        self._pressed = False

    def match_native_size(self, ref_btn):
        if ref_btn:
            w = ref_btn.width() or 46
            h = ref_btn.height() or 32
            if w > 0 and h > 0:
                self.setFixedSize(w, h)

    def enterEvent(self, e):
        self._hovered = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self._pressed = False
        self.update()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        self._pressed = True
        self.update()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(e)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._pressed:
            p.fillRect(self.rect(), QColor("#c8c8c8"))
        elif self._hovered:
            p.fillRect(self.rect(), QColor("#dcdcdc"))
        gear = _render_gear("#5f6368", 16)
        dpr = gear.devicePixelRatio()
        lw = int(gear.width() / dpr)
        lh = int(gear.height() / dpr)
        x = (self.width() - lw) // 2
        y = (self.height() - lh) // 2
        p.drawPixmap(x, y, gear)
        p.end()