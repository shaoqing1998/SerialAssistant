"""
title_bar.py - 标题栏设置按钮组件
v0.43 — 标准填充齿轮图标 + 动态匹配原生按钮尺寸
★ 齿轮采用主流软件标准样式（6齿填充 + 中心圆孔）
★ 运行时 match_native_size() 匹配原生 min/max/close 按钮
★ 去除所有图标相关代码
"""
from __future__ import annotations

import math

from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPainter, QColor, QPainterPath


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
            p.fillRect(self.rect(), QColor("#d1d5db"))
        elif self._hovered:
            p.fillRect(self.rect(), QColor("#e5e7eb"))

        # ★ 标准齿轮图标（主流设置按钮样式）
        # 6 齿填充齿轮 + 中心圆孔
        fg = QColor("#5f6368")
        cx, cy = self.width() / 2, self.height() / 2

        teeth = 6
        r_tip = 7.0       # 齿尖半径
        r_root = 5.0      # 齿根半径
        r_hole = 2.6      # 中心孔半径

        tooth_arc = 2 * math.pi / teeth
        tooth_half = tooth_arc * 0.28   # 齿顶半角宽

        gear = QPainterPath()
        for i in range(teeth):
            a = tooth_arc * i - math.pi / 2
            # 齿顶（flat top）
            t1 = a - tooth_half
            t2 = a + tooth_half
            # 齿谷（flat bottom）
            valley = a + tooth_arc / 2
            v1 = valley - tooth_half
            v2 = valley + tooth_half

            p0 = QPointF(cx + r_tip * math.cos(t1),
                         cy + r_tip * math.sin(t1))
            p1 = QPointF(cx + r_tip * math.cos(t2),
                         cy + r_tip * math.sin(t2))
            p2 = QPointF(cx + r_root * math.cos(v1),
                         cy + r_root * math.sin(v1))
            p3 = QPointF(cx + r_root * math.cos(v2),
                         cy + r_root * math.sin(v2))

            if i == 0:
                gear.moveTo(p0)
            else:
                gear.lineTo(p0)
            gear.lineTo(p1)
            gear.lineTo(p2)
            gear.lineTo(p3)
        gear.closeSubpath()

        # 中心圆孔
        hole = QPainterPath()
        hole.addEllipse(QPointF(cx, cy), r_hole, r_hole)
        gear = gear.subtracted(hole)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(fg)
        p.drawPath(gear)
        p.end()