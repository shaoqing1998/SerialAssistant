"""
title_bar.py - 标题栏设置按钮组件
v0.43 — Lucide 标准 SVG 齿轮图标 + 动态匹配原生按钮尺寸
★ 齿轮采用 Lucide settings 图标（QSvgRenderer 渲染）
★ 运行时 match_native_size() 匹配原生 min/max/close 按钮
"""
from __future__ import annotations

from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPixmap
from PySide6.QtSvg import QSvgRenderer


# ★ Lucide 标准 settings 齿轮 SVG
_GEAR_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>'


def _render_gear(color: str, size: int = 16) -> QPixmap:
    """将 SVG 齿轮渲染为 QPixmap（支持 HiDPI 清晰渲染）"""
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QRectF
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
    # ★ 显式指定逻辑目标矩形，防止 HiDPI 下内容被裁剪
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return pixmap


class SettingsButton(QPushButton):
    """设置齿轮按钮 — 与原生标题栏按钮风格统一"""

    def __init__(self, parent=None):
        super().__init__(parent)
        # 默认尺寸，showEvent 时会被 match_native_size 覆盖
        self.setFixedSize(46, 32)
        self.setFlat(True)
        self.setToolTip("设置")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hovered = False
        self._pressed = False

    def match_native_size(self, ref_btn):
        """读取原生按钮的实际尺寸并匹配"""
        if ref_btn:
            w = ref_btn.width() or 46
            h = ref_btn.height() or 32
            if w > 0 and h > 0:
                self.setFixedSize(w, h)

    # ── 鼠标状态 ──
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

    # ── 绘制 ──
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # ★ 方形背景，无倒角（与原生按钮一致）
        if self._pressed:
            p.fillRect(self.rect(), QColor("#c8c8c8"))
        elif self._hovered:
            p.fillRect(self.rect(), QColor("#dcdcdc"))

        # ★ SVG 齿轮图标（用逻辑尺寸居中）
        gear = _render_gear("#5f6368", 16)
        dpr = gear.devicePixelRatio()
        lw = int(gear.width() / dpr)
        lh = int(gear.height() / dpr)
        x = (self.width() - lw) // 2
        y = (self.height() - lh) // 2
        p.drawPixmap(x, y, gear)
        p.end()