"""
toolbar.py - 工具栏
v0.71 — 连接栏下方工具栏，paintEvent 线条图标按钮

所有图标用 QPainter 手绘线条（Lucide 风格），
不依赖外部图片资源。Toggle 选中态：蓝底 + 蓝图标 + ✓ 角标。
"""
from __future__ import annotations

from PySide6.QtWidgets import QWidget, QHBoxLayout
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath

from theme import (
    PRIMARY, PRIMARY_BG,
    BG_MAIN, BG_HOVER, BG_PRESSED,
    TEXT_SECONDARY, TEXT_MUTED,
    BORDER_LIGHT,
    TOOLBAR_BTN_SIZE, TOOLBAR_ICON_SIZE,
)

_BTN = TOOLBAR_BTN_SIZE
_ICO = TOOLBAR_ICON_SIZE
_PW = 1.2  # 默认线宽


# ════════════════════════════════════════════
# ★ 工具栏按钮基类
# ════════════════════════════════════════════
class _TBtn(QWidget):
    """paintEvent 图标按钮，支持 checkable toggle"""
    clicked = Signal()

    def __init__(self, tip="", checkable=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(_BTN, _BTN)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tip)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
        self._hov = self._prs = False
        self._ckable = checkable
        self._ckd = False

    def isChecked(self):
        return self._ckd

    def setChecked(self, v):
        if self._ckd == v:
            return
        self._ckd = v
        self.update()

    def enterEvent(self, e):
        self._hov = True
        self.update()

    def leaveEvent(self, e):
        self._hov = self._prs = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._prs = True
            self.update()

    def mouseReleaseEvent(self, e):
        was = self._prs
        self._prs = False
        self.update()
        if was and e.button() == Qt.MouseButton.LeftButton:
            if self._ckable:
                self._ckd = not self._ckd
            self.clicked.emit()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(
            QPainter.RenderHint.Antialiasing, True
        )
        w, h = self.width(), self.height()
        bg_r = QRectF(1, 1, w - 2, h - 2)

        # ── 背景 ──
        on = self._ckd and self._ckable
        if on:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(PRIMARY_BG))
            p.drawRoundedRect(bg_r, 4, 4)
        elif self._prs:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(BG_PRESSED))
            p.drawRoundedRect(bg_r, 4, 4)
        elif self._hov:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(BG_HOVER))
            p.drawRoundedRect(bg_r, 4, 4)

        # ── 图标颜色 ──
        color = QColor(PRIMARY) if on else QColor(
            TEXT_SECONDARY
        )

        # ── 图标 ──
        ix = (w - _ICO) / 2
        iy = (h - _ICO) / 2
        self._draw_icon(
            p, QRectF(ix, iy, _ICO, _ICO), color
        )

        # ── Toggle ✓ 角标（左上） ──
        if on:
            ck = QPen(QColor(PRIMARY), 1.5)
            ck.setCapStyle(Qt.PenCapStyle.RoundCap)
            ck.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(ck)
            p.drawLine(
                QPointF(3.0, 6.5),
                QPointF(5.0, 8.5),
            )
            p.drawLine(
                QPointF(5.0, 8.5),
                QPointF(8.5, 4.5),
            )

        p.end()

    def _draw_icon(self, p, r, c):
        """子类覆盖"""
        pass

    def _pen(self, color, width=_PW):
        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        return pen


# ════════════════════════════════════════════
# ★ 竖分隔线
# ════════════════════════════════════════════
class _TSep(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(9, _BTN)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setPen(QPen(QColor(BORDER_LIGHT), 1))
        x = self.width() / 2
        p.drawLine(
            QPointF(x, 5),
            QPointF(x, self.height() - 5),
        )
        p.end()


# ════════════════════════════════════════════
# ★ 各图标按钮
# ════════════════════════════════════════════

class _BtnOpen(_TBtn):
    """📂 打开文件"""
    def __init__(self, p=None):
        super().__init__("打开文件 (Ctrl+O)", parent=p)

    def _draw_icon(self, p, r, c):
        p.setPen(self._pen(c))
        p.setBrush(Qt.BrushStyle.NoBrush)
        x, y = r.x(), r.y()
        w, h = r.width(), r.height()
        path = QPainterPath()
        path.moveTo(x + 1, y + 3)
        path.lineTo(x + 1, y + h - 1)
        path.lineTo(x + w - 1, y + h - 1)
        path.lineTo(x + w - 1, y + 5)
        path.lineTo(x + w * 0.55, y + 5)
        path.lineTo(x + w * 0.45, y + 3)
        path.closeSubpath()
        p.drawPath(path)


class _BtnSave(_TBtn):
    """💾 另存为"""
    def __init__(self, p=None):
        super().__init__("另存为", parent=p)

    def _draw_icon(self, p, r, c):
        p.setPen(self._pen(c))
        p.setBrush(Qt.BrushStyle.NoBrush)
        x, y = r.x(), r.y()
        w, h = r.width(), r.height()
        p.drawRoundedRect(
            QRectF(x + 1, y + 1, w - 2, h - 2),
            1.5, 1.5,
        )
        # 上部切口
        p.drawLine(
            QPointF(x + 4, y + 1),
            QPointF(x + 4, y + 5),
        )
        p.drawLine(
            QPointF(x + w - 4, y + 1),
            QPointF(x + w - 4, y + 5),
        )
        p.drawLine(
            QPointF(x + 4, y + 5),
            QPointF(x + w - 4, y + 5),
        )
        # 下部标签
        p.drawRect(
            QRectF(x + 3, y + h - 6, w - 6, 4.5)
        )


class _BtnElapsed(_TBtn):
    """⏳ 连接计时（沙漏 A — 沙在底部，时间已流逝）"""
    def __init__(self, p=None):
        super().__init__(
            "连接计时", checkable=True, parent=p
        )

    def _draw_icon(self, p, r, c):
        p.setPen(self._pen(c, 1.1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        x, y = r.x(), r.y()
        w, h = r.width(), r.height()
        cx = x + w / 2
        top = y + 1.5
        bot = y + h - 1.5
        mid = y + h / 2
        hw = w / 2 - 1.5   # 上下边缘半宽
        nk = 1.2            # 细腰半宽
        # 上下横线
        p.drawLine(
            QPointF(cx - hw, top),
            QPointF(cx + hw, top),
        )
        p.drawLine(
            QPointF(cx - hw, bot),
            QPointF(cx + hw, bot),
        )
        # 左侧曲线（上→中→下）
        left = QPainterPath()
        left.moveTo(cx - hw, top)
        left.quadTo(
            cx - hw, mid - 1,
            cx - nk, mid,
        )
        left.quadTo(
            cx - hw, mid + 1,
            cx - hw, bot,
        )
        p.drawPath(left)
        # 右侧曲线
        right = QPainterPath()
        right.moveTo(cx + hw, top)
        right.quadTo(
            cx + hw, mid - 1,
            cx + nk, mid,
        )
        right.quadTo(
            cx + hw, mid + 1,
            cx + hw, bot,
        )
        p.drawPath(right)
        # 沙粒：底部填充（时间已过）
        sand = QPainterPath()
        sand.moveTo(cx - hw + 1.5, bot)
        sand.quadTo(
            cx - hw + 1.5, mid + 3,
            cx, mid + 2,
        )
        sand.quadTo(
            cx + hw - 1.5, mid + 3,
            cx + hw - 1.5, bot,
        )
        sand.closeSubpath()
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.setOpacity(0.3)
        p.drawPath(sand)
        p.restore()


class _BtnClock(_TBtn):
    """📅⏳ 当前时钟（日历页 + 右下角迷你沙漏）"""
    def __init__(self, p=None):
        super().__init__(
            "当前时钟", checkable=True, parent=p
        )

    def _draw_icon(self, p, r, c):
        p.setPen(self._pen(c))
        p.setBrush(Qt.BrushStyle.NoBrush)
        x, y = r.x(), r.y()
        w, h = r.width(), r.height()
        # ── 日历主体（左上 72%）──
        pw = w * 0.72
        ph = h * 0.72
        p.drawRoundedRect(
            QRectF(x, y + 2, pw, ph), 1.5, 1.5
        )
        # 日历顶部横线
        p.drawLine(
            QPointF(x, y + 2 + ph * 0.28),
            QPointF(x + pw, y + 2 + ph * 0.28),
        )
        # 两个吊环
        hk_y = y + 1
        p.drawLine(
            QPointF(x + pw * 0.3, hk_y),
            QPointF(x + pw * 0.3, y + 3),
        )
        p.drawLine(
            QPointF(x + pw * 0.7, hk_y),
            QPointF(x + pw * 0.7, y + 3),
        )
        # ── 右下迷你沙漏 ──
        sw = 5.5
        sh = 7.5
        sx = x + w - sw - 0.5
        sy = y + h - sh - 0.5
        scx = sx + sw / 2
        s_top = sy
        s_bot = sy + sh
        s_mid = sy + sh / 2
        s_hw = sw / 2 - 0.5
        s_nk = 0.8
        # ★ 先用背景色填充沙漏区域，遮挡日历重叠线条
        on = self._ckd and self._ckable
        if on:
            bg = QColor(PRIMARY_BG)
        elif self._prs:
            bg = QColor(BG_PRESSED)
        elif self._hov:
            bg = QColor(BG_HOVER)
        else:
            # 默认态用工具栏实际背景色（不能透明）
            bg = QColor(BG_MAIN)
        # 遮罩矩形（比沙漏稍大 1px 的确保完全覆盖）
        mask = QRectF(
            sx - 1.5, s_top - 1,
            sw + 3, sh + 2,
        )
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRect(mask)
        p.restore()
        # 绘制沙漏
        pen_s = self._pen(c, 0.9)
        p.setPen(pen_s)
        # 上下横线
        p.drawLine(
            QPointF(scx - s_hw, s_top),
            QPointF(scx + s_hw, s_top),
        )
        p.drawLine(
            QPointF(scx - s_hw, s_bot),
            QPointF(scx + s_hw, s_bot),
        )
        # 左侧曲线
        sl = QPainterPath()
        sl.moveTo(scx - s_hw, s_top)
        sl.quadTo(
            scx - s_hw, s_mid - 0.5,
            scx - s_nk, s_mid,
        )
        sl.quadTo(
            scx - s_hw, s_mid + 0.5,
            scx - s_hw, s_bot,
        )
        p.drawPath(sl)
        # 右侧曲线
        sr = QPainterPath()
        sr.moveTo(scx + s_hw, s_top)
        sr.quadTo(
            scx + s_hw, s_mid - 0.5,
            scx + s_nk, s_mid,
        )
        sr.quadTo(
            scx + s_hw, s_mid + 0.5,
            scx + s_hw, s_bot,
        )
        p.drawPath(sr)
        # 沙粒：顶部填充
        sand = QPainterPath()
        sand.moveTo(scx - s_hw + 1, s_top)
        sand.quadTo(
            scx - s_hw + 1, s_mid - 1.5,
            scx, s_mid - 1,
        )
        sand.quadTo(
            scx + s_hw - 1, s_mid - 1.5,
            scx + s_hw - 1, s_top,
        )
        sand.closeSubpath()
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.setOpacity(0.3)
        p.drawPath(sand)
        p.restore()


class _BtnSearch(_TBtn):
    """🔍 搜索"""
    def __init__(self, p=None):
        super().__init__("搜索 (Ctrl+F)", parent=p)

    def _draw_icon(self, p, r, c):
        p.setPen(self._pen(c, 1.3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        cx = r.x() + r.width() * 0.4
        cy = r.y() + r.height() * 0.4
        rd = r.width() * 0.28
        p.drawEllipse(QPointF(cx, cy), rd, rd)
        dx = rd * 0.71
        p.drawLine(
            QPointF(cx + dx, cy + dx),
            QPointF(r.right() - 1, r.bottom() - 1),
        )


class _BtnGoto(_TBtn):
    """⤵ 跳转行号"""
    def __init__(self, p=None):
        super().__init__(
            "跳转行号 (Ctrl+G)", parent=p
        )

    def _draw_icon(self, p, r, c):
        p.setPen(self._pen(c))
        x, y = r.x(), r.y()
        w, h = r.width(), r.height()
        ax = x + w * 0.28
        # 竖向箭头
        p.drawLine(
            QPointF(ax, y + 2),
            QPointF(ax, y + h - 2),
        )
        p.drawLine(
            QPointF(ax, y + h - 2),
            QPointF(ax - 2.5, y + h - 5),
        )
        p.drawLine(
            QPointF(ax, y + h - 2),
            QPointF(ax + 2.5, y + h - 5),
        )
        # 右侧横线
        for i in range(3):
            ly = y + 3.5 + i * 3.5
            p.drawLine(
                QPointF(x + w * 0.5, ly),
                QPointF(x + w - 1, ly),
            )


class _BtnWrap(_TBtn):
    """↩ 自动换行"""
    def __init__(self, p=None):
        super().__init__(
            "自动换行", checkable=True, parent=p
        )

    def _draw_icon(self, p, r, c):
        p.setPen(self._pen(c))
        x, y = r.x(), r.y()
        w, h = r.width(), r.height()
        # 三条横线
        p.drawLine(
            QPointF(x + 1, y + 3),
            QPointF(x + w - 1, y + 3),
        )
        p.drawLine(
            QPointF(x + 1, y + h / 2),
            QPointF(x + w - 2, y + h / 2),
        )
        p.drawLine(
            QPointF(x + 1, y + h - 3),
            QPointF(x + w * 0.55, y + h - 3),
        )
        # 折回箭头
        ex = x + w - 2
        p.drawLine(
            QPointF(ex, y + h / 2),
            QPointF(ex, y + h - 3),
        )
        p.drawLine(
            QPointF(ex, y + h - 3),
            QPointF(ex - 3, y + h - 5.5),
        )


class _BtnLineNum(_TBtn):
    """# 显示行号"""
    def __init__(self, p=None):
        super().__init__(
            "显示行号", checkable=True, parent=p
        )

    def _draw_icon(self, p, r, c):
        x, y = r.x(), r.y()
        w, h = r.width(), r.height()
        sp = (h - 2) / 3
        # 数字
        font = p.font()
        font.setPixelSize(8)
        font.setFamily("Consolas")
        p.setFont(font)
        p.setPen(c)
        for i, n in enumerate("123"):
            ny = y + 1 + i * sp
            p.drawText(
                QRectF(x, ny, w * 0.32, sp),
                Qt.AlignmentFlag.AlignCenter, n,
            )
        # 竖线
        sx = x + w * 0.38
        p.setPen(self._pen(c, 0.8))
        p.drawLine(
            QPointF(sx, y + 1),
            QPointF(sx, y + h - 1),
        )
        # 横线
        for i in range(3):
            ly = y + 3.5 + i * sp
            p.drawLine(
                QPointF(x + w * 0.48, ly),
                QPointF(x + w - 1, ly),
            )


class _BtnHex(_TBtn):
    """H — HEX 显示（低调样式）"""
    def __init__(self, p=None):
        super().__init__(
            "HEX 显示", checkable=True, parent=p
        )

    def _draw_icon(self, p, r, c):
        on = self._ckd and self._ckable
        if not on:
            c = QColor(TEXT_MUTED)
        font = p.font()
        font.setPixelSize(11)
        font.setFamily("Consolas")
        font.setBold(True)
        p.setFont(font)
        p.setPen(c)
        p.drawText(
            r, Qt.AlignmentFlag.AlignCenter, "H"
        )


# ════════════════════════════════════════════
# ★ 工具栏组装
# ════════════════════════════════════════════
class Toolbar(QWidget):
    """主工具栏 — 连接栏下方、Tab 栏上方"""

    open_file_clicked = Signal()
    save_as_clicked = Signal()
    elapsed_ts_toggled = Signal(bool)
    clock_ts_toggled = Signal(bool)
    search_clicked = Signal()
    goto_line_clicked = Signal()
    word_wrap_toggled = Signal(bool)
    line_numbers_toggled = Signal(bool)
    hex_display_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(_BTN + 4)

        h = QHBoxLayout(self)
        h.setContentsMargins(0, 2, 0, 2)
        h.setSpacing(2)

        # ── 文件 ──
        self.btn_open = _BtnOpen()
        self.btn_save = _BtnSave()
        h.addWidget(self.btn_open)
        h.addWidget(self.btn_save)
        h.addWidget(_TSep())

        # ── 时间戳 ──
        self.btn_elapsed = _BtnElapsed()
        self.btn_clock = _BtnClock()
        h.addWidget(self.btn_elapsed)
        h.addWidget(self.btn_clock)
        h.addWidget(_TSep())

        # ── 导航 ──
        self.btn_search = _BtnSearch()
        self.btn_goto = _BtnGoto()
        h.addWidget(self.btn_search)
        h.addWidget(self.btn_goto)
        h.addWidget(_TSep())

        # ── 显示选项 ──
        self.btn_wrap = _BtnWrap()
        self.btn_lnum = _BtnLineNum()
        self.btn_hex = _BtnHex()
        h.addWidget(self.btn_wrap)
        h.addWidget(self.btn_lnum)
        h.addWidget(self.btn_hex)

        h.addStretch(1)

        # ── 信号转发 ──
        self.btn_open.clicked.connect(
            self.open_file_clicked
        )
        self.btn_save.clicked.connect(
            self.save_as_clicked
        )
        self.btn_elapsed.clicked.connect(
            lambda: self.elapsed_ts_toggled.emit(
                self.btn_elapsed.isChecked()
            )
        )
        self.btn_clock.clicked.connect(
            lambda: self.clock_ts_toggled.emit(
                self.btn_clock.isChecked()
            )
        )
        self.btn_search.clicked.connect(
            self.search_clicked
        )
        self.btn_goto.clicked.connect(
            self.goto_line_clicked
        )
        self.btn_wrap.clicked.connect(
            lambda: self.word_wrap_toggled.emit(
                self.btn_wrap.isChecked()
            )
        )
        self.btn_lnum.clicked.connect(
            lambda: self.line_numbers_toggled.emit(
                self.btn_lnum.isChecked()
            )
        )
        self.btn_hex.clicked.connect(
            lambda: self.hex_display_toggled.emit(
                self.btn_hex.isChecked()
            )
        )

    # ── 外部同步（设置页 → 工具栏）──
    def set_word_wrap(self, on):
        self.btn_wrap.setChecked(on)

    def set_line_numbers(self, on):
        self.btn_lnum.setChecked(on)

    def set_hex_display(self, on):
        self.btn_hex.setChecked(on)

    def set_elapsed_ts(self, on):
        self.btn_elapsed.setChecked(on)

    def set_clock_ts(self, on):
        self.btn_clock.setChecked(on)