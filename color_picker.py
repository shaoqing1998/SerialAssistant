"""
color_picker.py  -  色板弹窗
v0.5 — 12 最近预制柔色 + HSV 色盘 + Hue 条 + HEX 输入
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QApplication,
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
            clip.addRoundedRect(QRectF(self.rect()), 7, 7)
            p.setClipPath(clip)
            p.drawImage(0, 0, self._img)
            p.setClipping(False)
        cx = self._sat * (self.width() - 1)
        cy = (1.0 - self._val) * (self.height() - 1)
        # ★ clamp 圆圈到控件内部，避免被相邻控件裁掉
        r_outer = 8.0
        cx = max(r_outer, min(self.width() - r_outer, cx))
        cy = max(r_outer, min(self.height() - r_outer, cy))
        p.setPen(QPen(QColor("#ffffff"), 2.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), 5, 5)
        p.setPen(QPen(QColor("#000000"), 1.0))
        p.drawEllipse(QPointF(cx, cy), 6, 6)
        br = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(QColor("#d1d5db"), 1.5))
        p.drawRoundedRect(br, 7, 7)
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

    _PAD = 4  # 上下留白，给滑块完整显示空间

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pad = self._PAD
        r = QRectF(2, pad, self.width() - 4, self.height() - 2 * pad)
        clip = QPainterPath()
        clip.addRoundedRect(r, 4, 4)
        p.setClipPath(clip)
        grad = QLinearGradient(0, pad, 0, self.height() - pad)
        for i in range(7):
            grad.setColorAt(i / 6.0, QColor.fromHsvF(i / 6.0, 1.0, 1.0))
        p.fillRect(r, grad)
        p.setClipping(False)
        p.setPen(QPen(QColor("#d1d5db"), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), 4, 4)
        # ★ 滑块：填充当前色相，外圈灰+内圈白
        y = pad + self._hue * (self.height() - 2 * pad - 1)
        ind = QRectF(0, y - 3, self.width(), 6)
        cur_color = QColor.fromHsvF(self._hue, 1.0, 1.0)
        p.setBrush(cur_color)
        p.setPen(QPen(QColor("#b0b8c4"), 1.0))
        p.drawRoundedRect(ind, 2, 2)
        p.setPen(QPen(QColor("#ffffff"), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(ind.adjusted(1, 1, -1, -1), 1.5, 1.5)
        p.end()

    def _pick(self, pos):
        pad = self._PAD
        usable = self.height() - 2 * pad
        h = max(0.0, min(1.0, (pos.y() - pad) / max(usable - 1, 1)))
        self._hue = h; self.update(); self.changed.emit(h)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton: self._pick(e.position())

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton: self._pick(e.position())


class _FullPaletteDialog(QDialog):
    """200 色完整调色板 — 按与当前色的相近度排序"""
    color_chosen = Signal(str)
    _COLS = 10

    def __init__(self, current_hex="#ffffff", parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, True
        )
        self._chosen = None
        from highlight_engine import SOFT_PALETTE, color_dist
        sorted_colors = sorted(
            SOFT_PALETTE,
            key=lambda c: color_dist(c, current_hex),
        )
        cols = self._COLS
        sw, sh, sp = 30, 24, 3
        grid_w = cols * (sw + sp) - sp
        margin = 12
        self.setFixedSize(grid_w + 2 * margin + 10, 500)
        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(sp)
        for i, c in enumerate(sorted_colors):
            btn = _SwatchBtn(c)
            btn.setFixedSize(sw, sh)
            btn.clicked.connect(self._pick)
            grid.addWidget(btn, i // cols, i % cols)
        scroll = QScrollArea()
        scroll.setWidget(container)
        scroll.setWidgetResizable(False)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none}"
            "QScrollBar:vertical{width:6px;background:transparent}"
            "QScrollBar::handle:vertical{"
            "background:#d1d5db;border-radius:3px;min-height:30px}"
            "QScrollBar::add-line:vertical,"
            "QScrollBar::sub-line:vertical{height:0}"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(margin, margin, margin, margin)
        root.addWidget(scroll)
        # 居中于屏幕
        screen = QApplication.primaryScreen()
        if screen:
            sg = screen.availableGeometry()
            self.move(
                sg.x() + (sg.width() - self.width()) // 2,
                sg.y() + (sg.height() - self.height()) // 2,
            )

    def _pick(self, hex_str):
        self._chosen = hex_str
        self.color_chosen.emit(hex_str)
        self.accept()

    def get_color(self):
        return self._chosen

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


class ColorPickerPopup(QDialog):
    color_chosen = Signal(str)

    def __init__(self, initial="#5b8cc2", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(380, 230)
        self._color = QColor(initial)
        self._swatches: list[_SwatchBtn] = []
        self._build_ui()
        self._sync_from_color(initial)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)
        body = QHBoxLayout()
        body.setSpacing(10)
        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(4)
        for i in range(16):
            sw = _SwatchBtn()
            sw.clicked.connect(self._on_swatch)
            grid.addWidget(sw, i // 4, i % 4)
            self._swatches.append(sw)
        body.addWidget(grid_w)
        right = QHBoxLayout()
        right.setSpacing(12)
        self._sv = _SVField()
        self._sv.changed.connect(self._on_sv)
        right.addWidget(self._sv)
        self._hue_bar = _HueBar()
        self._hue_bar.changed.connect(self._on_hue)
        right.addWidget(self._hue_bar)
        body.addLayout(right)
        root.addLayout(body)
        # ── 更多按钮（独立行，不挤占 4×4 色板空间）──
        btn_more = QPushButton("更多")
        btn_more.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_more.setStyleSheet(
            "QPushButton{background:transparent;border:none;"
            "color:#9ca3af;font-size:12px;"
            "min-height:0;min-width:0;padding:2px 6px}"
            "QPushButton:hover{background:#f3f4f6;color:#374151;"
            "border-radius:4px}"
            "QPushButton:pressed{background:#e5e7eb;color:#1d4ed8;"
            "border-radius:4px}"
        )
        btn_more.clicked.connect(self._on_more)
        root.addWidget(btn_more, 0, Qt.AlignmentFlag.AlignLeft)
        _input_ss = (
            "QLineEdit{font-size:13px;font-family:Consolas,monospace;"
            "background:#fff;border:1px solid #d1d5db;border-radius:4px;"
            "padding:0 4px;color:#374151}"
            "QLineEdit:focus{border-color:#3b82f6}"
        )
        # ── RGB + HEX + 预览 + 确定（合并为一行）──
        input_row = QHBoxLayout()
        input_row.setSpacing(5)
        self._rgb_edits = []
        for ch in ("R", "G", "B"):
            lb = QLabel(ch)
            lb.setStyleSheet("font-size:12px;color:#6b7280;background:transparent;")
            lb.setFixedWidth(10)
            input_row.addWidget(lb)
            ed = QLineEdit()
            ed.setMaxLength(3)
            ed.setFixedHeight(24)
            ed.setFixedWidth(36)
            ed.setStyleSheet(_input_ss)
            ed.editingFinished.connect(self._on_rgb_input)
            input_row.addWidget(ed)
            self._rgb_edits.append(ed)
        lbl = QLabel("#")
        lbl.setStyleSheet("font-size:12px;color:#6b7280;background:transparent;")
        lbl.setFixedWidth(10)
        input_row.addWidget(lbl)
        self._hex_edit = QLineEdit()
        self._hex_edit.setMaxLength(6)
        self._hex_edit.setFixedHeight(24)
        self._hex_edit.setFixedWidth(62)
        self._hex_edit.setStyleSheet(_input_ss)
        self._hex_edit.editingFinished.connect(self._on_hex_input)
        input_row.addWidget(self._hex_edit)
        self._preview = QWidget()
        self._preview.setFixedSize(24, 24)
        input_row.addSpacing(6)
        input_row.addWidget(self._preview)
        input_row.addSpacing(4)
        btn_ok = QPushButton("确定")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setStyleSheet(
            "QPushButton{background:transparent;border:none;"
            "color:#9ca3af;font-size:13px;"
            "min-height:0;min-width:0;padding:2px 4px}"
            "QPushButton:hover{background:#f3f4f6;color:#374151;"
            "border-radius:4px}"
            "QPushButton:pressed{background:#e5e7eb;color:#1d4ed8;"
            "border-radius:4px}"
        )
        btn_ok.setFixedWidth(36)
        btn_ok.clicked.connect(self._confirm)
        input_row.addWidget(btn_ok)
        root.addLayout(input_row)

    def _sync_from_color(self, hex_str):
        c = QColor(hex_str)
        self._color = c
        h, s, v, _ = c.getHsvF()
        if h < 0: h = 0.0
        self._hue_bar.set_hue(h)
        self._sv.set_hue(h)
        self._sv.set_sv(s, v)
        self._hex_edit.setText(hex_str.lstrip("#"))
        self._sync_rgb_display()
        self._update_preview()
        self._update_swatches(hex_str)

    def _sync_rgb_display(self):
        c = self._color
        for ed, val in zip(self._rgb_edits, (c.red(), c.green(), c.blue())):
            ed.blockSignals(True)
            ed.setText(str(val))
            ed.blockSignals(False)

    def _update_swatches(self, hex_str):
        from highlight_engine import DEFAULT_12
        # 前 12 格：固定初始色；后 4 格：基于当前色的推荐色
        recs = nearest_n(hex_str, 4)
        colors = DEFAULT_12 + recs
        for i, sw in enumerate(self._swatches):
            sw.set_color(colors[i])
            sw.set_selected(colors[i].lower() == hex_str.lower())

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
        self._sync_rgb_display()
        self._update_preview()
        self._update_swatches(c.name())

    def _on_sv(self, s, v):
        c = QColor.fromHsvF(self._hue_bar._hue, s, v)
        self._color = c
        self._hex_edit.setText(c.name().lstrip("#"))
        self._sync_rgb_display()
        self._update_preview()
        self._update_swatches(c.name())

    def _on_rgb_input(self):
        try:
            r = max(0, min(255, int(self._rgb_edits[0].text())))
            g = max(0, min(255, int(self._rgb_edits[1].text())))
            b = max(0, min(255, int(self._rgb_edits[2].text())))
        except ValueError:
            return
        self._sync_from_color(f"#{r:02x}{g:02x}{b:02x}")

    def _on_more(self):
        cur = self._color.name()
        self.hide()
        dlg = _FullPaletteDialog(cur, self.parent())
        if (dlg.exec() == QDialog.DialogCode.Accepted
                and dlg.get_color()):
            self.color_chosen.emit(dlg.get_color())
        self.close()

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