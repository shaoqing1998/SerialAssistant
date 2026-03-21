"""
color_picker.py  -  色板弹窗
v0.5 — 12 最近预制柔色 + HSV 色盘 + Hue 条 + HEX 输入
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QPushButton,
)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QColor, QPen, QLinearGradient,
    QImage, QPainterPath,
)
from highlight_engine import nearest_n


class _SwatchBtn(QWidget):
    clicked = Signal(str)

    def __init__(self, color="#cccccc", parent=None):
        super().__init__(parent)
        self._color = color
        self._hovered = self._selected = False
        self.setFixedSize(36, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)

    def set_color(self, c): self._color = c; self.update()
    def set_selected(self, s): self._selected = s; self.update()
    def color(self): return self._color
    def enterEvent(self, e): self._hovered = True; self.update()
    def leaveEvent(self, e): self._hovered = False; self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._color)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(1, 1, self.width() - 2, self.height() - 2)
        path = QPainterPath()
        path.addRoundedRect(r, 4, 4)
        p.fillPath(path, QColor(self._color))
        if self._selected:
            p.setPen(QPen(QColor("#2563eb"), 2.0))
        elif self._hovered:
            p.setPen(QPen(QColor("#9ca3af"), 1.5))
        else:
            p.setPen(QPen(QColor("#d1d5db"), 1.0))
        p.drawRoundedRect(r, 4, 4)
        p.end()


class _SVField(QWidget):
    changed = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 140)
        self._hue = 0.0
        self._sat = 1.0
        self._val = 1.0
        self._img = None
        self._rebuild()

    def set_hue(self, h):
        self._hue = h; self._rebuild(); self.update()

    def set_sv(self, s, v):
        self._sat = s; self._val = v; self.update()

    def _rebuild(self):
        w, h = self.width(), self.height()
        img = QImage(w, h, QImage.Format.Format_RGB32)
        for y in range(h):
            v = 1.0 - y / max(h - 1, 1)
            for x in range(w):
                s = x / max(w - 1, 1)
                img.setPixelColor(x, y, QColor.fromHsvF(self._hue, s, v))
        self._img = img

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._img:
            clip = QPainterPath()
            clip.addRoundedRect(QRectF(self.rect()), 4, 4)
            p.setClipPath(clip)
            p.drawImage(0, 0, self._img)
            p.setClipping(False)
        cx = self._sat * (self.width() - 1)
        cy = (1.0 - self._val) * (self.height() - 1)
        p.setPen(QPen(QColor("#ffffff"), 2.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), 5, 5)
        p.setPen(QPen(QColor("#000000"), 1.0))
        p.drawEllipse(QPointF(cx, cy), 6, 6)
        br = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(QColor("#d1d5db"), 1.0))
        p.drawRoundedRect(br, 4, 4)
        p.end()

    def _pick(self, pos):
        w, h = self.width(), self.height()
        s = max(0.0, min(1.0, pos.x() / max(w - 1, 1)))
        v = max(0.0, min(1.0, 1.0 - pos.y() / max(h - 1, 1)))
        self._sat, self._val = s, v
        self.update()
        self.changed.emit(s, v)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton: self._pick(e.position())

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton: self._pick(e.position())


class _HueBar(QWidget):
    changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 140)
        self._hue = 0.0

    def set_hue(self, h): self._hue = h; self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(2, 0, self.width() - 4, self.height())
        clip = QPainterPath()
        clip.addRoundedRect(r, 4, 4)
        p.setClipPath(clip)
        grad = QLinearGradient(0, 0, 0, self.height())
        for i in range(7):
            grad.setColorAt(i / 6.0, QColor.fromHsvF(i / 6.0, 1.0, 1.0))
        p.fillRect(r, grad)
        p.setClipping(False)
        p.setPen(QPen(QColor("#d1d5db"), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), 4, 4)
        y = self._hue * (self.height() - 1)
        p.setPen(QPen(QColor("#ffffff"), 2.0))
        p.drawRoundedRect(QRectF(0, y - 3, self.width(), 6), 2, 2)
        p.end()

    def _pick(self, pos):
        h = max(0.0, min(1.0, pos.y() / max(self.height() - 1, 1)))
        self._hue = h; self.update(); self.changed.emit(h)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton: self._pick(e.position())

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton: self._pick(e.position())


class ColorPickerPopup(QDialog):
    color_chosen = Signal(str)

    def __init__(self, initial="#5b8cc2", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(320, 260)
        self._color = QColor(initial)
        self._swatches: list[_SwatchBtn] = []
        self._build_ui()
        self._sync_from_color(initial)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)
        body = QHBoxLayout()
        body.setSpacing(10)
        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(4)
        for i in range(12):
            sw = _SwatchBtn()
            sw.clicked.connect(self._on_swatch)
            grid.addWidget(sw, i // 4, i % 4)
            self._swatches.append(sw)
        body.addWidget(grid_w)
        right = QHBoxLayout()
        right.setSpacing(6)
        self._sv = _SVField()
        self._sv.changed.connect(self._on_sv)
        right.addWidget(self._sv)
        self._hue_bar = _HueBar()
        self._hue_bar.changed.connect(self._on_hue)
        right.addWidget(self._hue_bar)
        body.addLayout(right)
        root.addLayout(body)
        bot = QHBoxLayout()
        bot.setSpacing(8)
        lbl = QLabel("#")
        lbl.setStyleSheet("font-size:13px;color:#6b7280;background:transparent;")
        lbl.setFixedWidth(10)
        bot.addWidget(lbl)
        self._hex_edit = QLineEdit()
        self._hex_edit.setMaxLength(6)
        self._hex_edit.setFixedHeight(26)
        self._hex_edit.setStyleSheet(
            "QLineEdit{font-size:13px;font-family:Consolas,monospace;"
            "background:#fff;border:1px solid #d1d5db;border-radius:4px;"
            "padding:0 6px;color:#374151}"
            "QLineEdit:focus{border-color:#3b82f6}"
        )
        self._hex_edit.editingFinished.connect(self._on_hex_input)
        bot.addWidget(self._hex_edit, stretch=1)
        self._preview = QWidget()
        self._preview.setFixedSize(26, 26)
        bot.addWidget(self._preview)
        btn_ok = QPushButton("确定")
        btn_ok.setFixedSize(48, 26)
        btn_ok.setStyleSheet(
            "QPushButton{background:#2563eb;border:none;border-radius:4px;"
            "color:#fff;font-size:13px;min-height:0;min-width:0}"
            "QPushButton:hover{background:#3b82f6}"
            "QPushButton:pressed{background:#1d4ed8}"
        )
        btn_ok.clicked.connect(self._confirm)
        bot.addWidget(btn_ok)
        root.addLayout(bot)

    def _sync_from_color(self, hex_str):
        c = QColor(hex_str)
        self._color = c
        h, s, v, _ = c.getHsvF()
        if h < 0: h = 0.0
        self._hue_bar.set_hue(h)
        self._sv.set_hue(h)
        self._sv.set_sv(s, v)
        self._hex_edit.setText(hex_str.lstrip("#"))
        self._update_preview()
        self._update_swatches(hex_str)

    def _update_swatches(self, hex_str):
        nearest = nearest_n(hex_str, 12)
        for i, sw in enumerate(self._swatches):
            sw.set_color(nearest[i])
            sw.set_selected(nearest[i].lower() == hex_str.lower())

    def _update_preview(self):
        self._preview.setStyleSheet(
            f"background:{self._color.name()};"
            "border:1px solid #d1d5db;border-radius:4px;"
        )

    def _on_swatch(self, hex_str): self._sync_from_color(hex_str)

    def _on_hue(self, h):
        self._sv.set_hue(h)
        c = QColor.fromHsvF(h, self._sv._sat, self._sv._val)
        self._color = c
        self._hex_edit.setText(c.name().lstrip("#"))
        self._update_preview()
        self._update_swatches(c.name())

    def _on_sv(self, s, v):
        c = QColor.fromHsvF(self._hue_bar._hue, s, v)
        self._color = c
        self._hex_edit.setText(c.name().lstrip("#"))
        self._update_preview()
        self._update_swatches(c.name())

    def _on_hex_input(self):
        txt = self._hex_edit.text().strip().lstrip("#")
        if len(txt) == 6:
            try:
                int(txt, 16)
                self._sync_from_color(f"#{txt}")
            except ValueError:
                pass

    def _confirm(self):
        self.color_chosen.emit(self._color.name())
        self.accept()

    def get_color(self): return self._color.name()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(r, 8, 8)
        p.fillPath(path, QColor("#ffffff"))
        p.setPen(QPen(QColor("#b0b8c4"), 1.0))
        p.drawPath(path)
        p.end()