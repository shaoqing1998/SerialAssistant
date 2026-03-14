"""
title_bar.py - 标题栏设置按钮组件
v0.38 — 配合 pyqt-frameless-window 库使用
仅保留平面设计齿轮图标按钮（窗口控制按钮由库原生提供）
"""
from __future__ import annotations

import math

from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QPen, QColor


class SettingsButton(QPushButton):
    """平面设计齿轮图标（QPainter 绘制）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(38, 30)
        self.setFlat(True)
        self.setToolTip("设置")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hovered = False
        self._pressed = False

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
        # 背景
        if self._pressed:
            p.setBrush(QColor("#d1d5db"))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(self.rect(), 4, 4)
        elif self._hovered:
            p.setBrush(QColor("#e5e7eb"))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(self.rect(), 4, 4)
        # 齿轮
        fg = QColor("#5f6368")
        pen = QPen(fg, 1.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        cx, cy = self.width() / 2, self.height() / 2
        # 内圆
        p.drawEllipse(QPointF(cx, cy), 3.2, 3.2)
        # 外层齿牙（6 个）
        r_out, r_tooth, half = 7.0, 8.8, 0.32
        for i in range(6):
            angle = math.pi / 3 * i - math.pi / 2
            a1, a2 = angle - half, angle + half
            pts = [
                QPointF(cx + r_out * math.cos(a1), cy + r_out * math.sin(a1)),
                QPointF(cx + r_tooth * math.cos(a1), cy + r_tooth * math.sin(a1)),
                QPointF(cx + r_tooth * math.cos(a2), cy + r_tooth * math.sin(a2)),
                QPointF(cx + r_out * math.cos(a2), cy + r_out * math.sin(a2)),
            ]
            p.drawLine(pts[0], pts[1])
            p.drawLine(pts[1], pts[2])
            p.drawLine(pts[2], pts[3])
        p.end()