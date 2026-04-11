"""
settings_dialog.py - 通用设置弹窗（全屏遮罩 + 居中面板）
v0.7 — ★ 重构：提取公共组件到 theme.py / widgets.py / popups.py
       ★ 本文件保留：高亮规则组件 + 快捷键组件 + SettingsDialog 主类

最近更改 (v0.7):
  [1] 删除已迁移类：_CloseBtn, _NavBtn, _ResetBtn, _GearIconLabel,
      _CircleBtn, _BorderOverlay, _RoundedScrollContainer, _TagChip,
      InfoPopup, ConfirmPopup, InputIntPopup, InputTextPopup
  [2] 删除已迁移常量：PANEL_W/H, RADIUS, BORDER_COLOR, BG_COLOR,
      OVERLAY_COLOR, _POPUP_FONT_SIZE, _CHK_SS, _RADIO_SS, _GEAR_SVG
  [3] 新增 import: theme, widgets, popups
  [4] 所有裸写颜色/字号改为引用 theme 常量
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QPushButton, QFileDialog, QWidget,
    QRadioButton, QScrollArea, QFrame, QStackedWidget,
    QButtonGroup, QLineEdit, QTextEdit, QMenu,
    QApplication, QScrollBar, QSpinBox,
)
from PySide6.QtCore import (
    Qt, QPoint, QPointF, QRectF, Signal, QEvent,
    QTimer,
)
from PySide6.QtGui import (
    QPainter, QPainterPath, QColor, QPen,
    QRegion, QPixmap, QCursor, QKeySequence,
)
from PySide6.QtSvg import QSvgRenderer
from config import save_config
from highlight_engine import (
    BUILTIN_RULES, PREVIEW_TEXT, LogHighlighter,
    auto_fg, lum,
)
from color_picker import ColorPickerPopup

# ★ v0.7: 从公共模块导入
from theme import (
    PANEL_W, PANEL_H, PANEL_RADIUS,
    OVERLAY_COLOR as _OVERLAY_RGBA,
    BG_PANEL, BG_HOVER, BG_PRESSED,
    BG_SUBTLE, BG_SELECTED_ROW,
    TEXT_PRIMARY, TEXT_DARK, TEXT_LOG,
    TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
    BORDER_DEFAULT, BORDER_FOCUS, BORDER_LIGHT,
    BORDER_PANEL,
    PRIMARY, PRIMARY_HOVER, PRIMARY_PRESSED,
    PRIMARY_LIGHT, PRIMARY_BG, PRIMARY_NAV,
    ERROR, ERROR_BORDER, ERROR_BG,
    ERROR_HOVER_BG, ERROR_PRESSED_BG, ERROR_DARK,
    POPUP_FONT_SIZE, LABEL_FONT_SIZE,
    SMALL_FONT_SIZE, TINY_FONT_SIZE,
    HEADER_FONT_SIZE, SEPARATOR_SPACING,
    checkbox_ss, radio_ss, mini_checkbox_ss,
    line_edit_ss, separator_ss,
    header_label_ss, section_label_ss,
    borderless_btn_ss, primary_btn_ss, cancel_btn_ss,
)
from widgets import (
    CloseBtn as _CloseBtn,
    CircleBtn as _CircleBtn,
    NavBtn as _NavBtn,
    ResetBtn as _ResetBtn,
    TagChip as _TagChip,
    GearIconLabel as _GearIconLabel,
    RoundedScrollContainer as _RoundedScrollContainer,
    ArrowScrollBar as _ArrowScrollBar,
    make_separator,
)
from popups import (
    InfoPopup, ConfirmPopup,
    InputIntPopup, InputTextPopup,
)

# ★ v0.7: 常量别名（兼容 Part 2 引用）
RADIUS = PANEL_RADIUS
BORDER_COLOR = QColor(BORDER_PANEL)
BG_COLOR = QColor(BG_PANEL)
OVERLAY_COLOR = QColor(*_OVERLAY_RGBA)
_CHK_SS = checkbox_ss()
_RADIO_SS = radio_ss()
_POPUP_FONT_SIZE = POPUP_FONT_SIZE


# ═══════════════════════════════════════════
# ★ v0.5: 色块按钮（用于规则行的颜色选择）
# ═══════════════════════════════════════════
class _ColorBtn(QWidget):
    color_changed = Signal(str)

    def __init__(self, color="#cccccc", letter=False, parent=None):
        super().__init__(parent)
        self._color = color
        self._letter = letter
        self._hovered = False
        self.setFixedSize(22, 16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)

    def color(self): return self._color

    def set_color(self, c):
        self._color = c; self.update()

    def enterEvent(self, e):
        self._hovered = True; self.update()

    def leaveEvent(self, e):
        self._hovered = False; self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            dlg = ColorPickerPopup(self._color, self.window())
            dlg.color_chosen.connect(self._on_pick)
            pos = self.mapToGlobal(QPoint(0, self.height() + 2))
            dlg.move(pos)
            dlg.exec()

    def _on_pick(self, c):
        self._color = c; self.update()
        self.color_changed.emit(c)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        path = QPainterPath()
        path.addRoundedRect(r, 3, 3)
        if self._letter:
            font = p.font()
            font.setPixelSize(11)
            font.setBold(True)
            p.setFont(font)
            p.setPen(QColor(self._color))
            p.drawText(
                QRectF(0, 0, self.width(), self.height()),
                Qt.AlignmentFlag.AlignCenter, "A",
            )
        else:
            p.fillPath(path, QColor(self._color))
            pen_c = TEXT_MUTED if self._hovered else BORDER_DEFAULT
            p.setPen(QPen(QColor(pen_c), 1.0))
            p.drawRoundedRect(r, 3, 3)
        p.end()


# ═══════════════════════════════════════════
# ★ v0.5: 内置规则行
# ═══════════════════════════════════════════
class _BuiltinRuleRow(QWidget):
    changed = Signal()

    def __init__(self, rule, override=None, parent=None):
        super().__init__(parent)
        self._id = rule["id"]
        self._default_fg = rule["fg"]
        self._default_bg = rule.get("bg")
        self._pattern = rule["pattern"]
        self._showing_pattern = False
        self.setFixedHeight(28)
        h = QHBoxLayout(self)
        h.setContentsMargins(6, 0, 6, 0)
        h.setSpacing(6)
        self._chk = QCheckBox()
        self._chk.setStyleSheet(_CHK_SS)
        self._chk.setChecked(True)
        self._chk.toggled.connect(lambda _: self.changed.emit())
        h.addWidget(self._chk)
        self._lbl = QLabel(rule["name"])
        h.addWidget(self._lbl, stretch=1)
        self._cs = QCheckBox("Aa")
        self._cs.setStyleSheet(mini_checkbox_ss())
        self._cs.setFixedWidth(38)
        self._cs.toggled.connect(lambda _: self.changed.emit())
        h.addWidget(self._cs)
        self._fg_btn = _ColorBtn(rule["fg"], letter=True)
        self._fg_btn.color_changed.connect(self._on_color)
        h.addWidget(self._fg_btn)
        self._bg_btn = _ColorBtn(rule.get("bg") or "#ffffff")
        self._bg_btn.color_changed.connect(self._on_color)
        h.addWidget(self._bg_btn)
        if override:
            self._chk.setChecked(override.get("enabled", True))
            self._cs.setChecked(override.get("case_sensitive", False))
            if "fg" in override:
                self._fg_btn.set_color(override["fg"])
            if "bg" in override:
                self._bg_btn.set_color(override["bg"] or "#ffffff")
        self._style_lbl()

    def _on_color(self, _=""):
        self._style_lbl(); self.changed.emit()

    def _style_lbl(self):
        fg = self._fg_btn.color()
        bg = self._bg_btn.color()
        has_bg = bg and bg.lower() != "#ffffff"
        if has_bg:
            self._lbl.setStyleSheet(
                f"font-size:{SMALL_FONT_SIZE}px;color:{TEXT_DARK};"
                f"background:{bg};border-radius:3px;padding:1px 4px;"
            )
        else:
            self._lbl.setStyleSheet(
                f"font-size:{SMALL_FONT_SIZE}px;color:{fg};"
                "background:transparent;"
            )

    def rule_id(self): return self._id

    def get_config(self):
        bg = self._bg_btn.color() or "#ffffff"
        return {
            "enabled": self._chk.isChecked(),
            "case_sensitive": self._cs.isChecked(),
            "fg": self._fg_btn.color(),
            "bg": bg if bg.lower() != "#ffffff" else None,
        }

    def reset(self):
        self._chk.setChecked(True)
        self._cs.setChecked(False)
        self._fg_btn.set_color(self._default_fg)
        self._bg_btn.set_color(self._default_bg or "#ffffff")
        self._style_lbl()

    def mouseDoubleClickEvent(self, event):
        if self._showing_pattern: return
        self._showing_pattern = True
        self._lbl.setWordWrap(True)
        self.setMinimumHeight(28)
        self.setMaximumHeight(16777215)
        self._lbl.setText(self._pattern)
        self._lbl.setStyleSheet(
            "font-family:Consolas,monospace;"
            f"font-size:{TINY_FONT_SIZE}px;color:{TEXT_SECONDARY};"
            f"background:{BG_HOVER};border-radius:3px;padding:1px 4px;"
        )
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        if (self._showing_pattern
                and event.type() == QEvent.Type.MouseButtonPress):
            self._showing_pattern = False
            self._lbl.setWordWrap(False)
            self.setFixedHeight(28)
            QApplication.instance().removeEventFilter(self)
            self._lbl.setText(
                next(r["name"] for r in BUILTIN_RULES
                     if r["id"] == self._id)
            )
            self._style_lbl()
        return super().eventFilter(obj, event)


# ═══════════════════════════════════════════
# ★ v0.5: 自定义规则行
# ═══════════════════════════════════════════
class _CustomRuleRow(QWidget):
    changed = Signal()
    delete_me = Signal(object)
    grip_pressed = Signal(object)

    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self._selected = False
        self.setFixedHeight(28)
        h = QHBoxLayout(self)
        h.setContentsMargins(6, 0, 6, 0)
        h.setSpacing(6)
        self._chk = QCheckBox()
        self._chk.setStyleSheet(_CHK_SS)
        self._chk.setChecked(True)
        self._chk.toggled.connect(lambda _: self.changed.emit())
        h.addWidget(self._chk)
        self._kw = QLineEdit()
        self._kw.setPlaceholderText("关键词 / 正则")
        self._kw.setFixedHeight(23)
        self._kw.setStyleSheet(line_edit_ss())
        self._kw.textChanged.connect(lambda _: self.changed.emit())
        h.addWidget(self._kw, stretch=1)
        self._rx = QCheckBox(".*")
        self._rx.setStyleSheet(mini_checkbox_ss())
        self._rx.setFixedWidth(32)
        self._rx.toggled.connect(lambda _: self.changed.emit())
        h.addWidget(self._rx)
        self._cs = QCheckBox("Aa")
        self._cs.setStyleSheet(mini_checkbox_ss())
        self._cs.setFixedWidth(38)
        self._cs.toggled.connect(lambda _: self.changed.emit())
        h.addWidget(self._cs)
        fg = (data or {}).get("fg", TEXT_PRIMARY)
        self._fg = _ColorBtn(fg, letter=True)
        self._fg.color_changed.connect(self.changed.emit)
        h.addWidget(self._fg)
        bg = (data or {}).get("bg") or "#ffffff"
        self._bg = _ColorBtn(bg)
        self._bg.color_changed.connect(self.changed.emit)
        h.addWidget(self._bg)
        d = _CircleBtn("\u00d7", size=20)
        d._fg = BORDER_DEFAULT
        d._fg_hover = ERROR
        d._fg_pressed = ERROR_DARK
        d._bg_hover = ERROR_HOVER_BG
        d._bg_pressed = ERROR_PRESSED_BG
        d._font_size = 14
        d.clicked.connect(lambda: self.delete_me.emit(self))
        h.addWidget(d)
        if data:
            self._chk.setChecked(data.get("enabled", True))
            self._kw.setText(data.get("keyword", ""))
            self._rx.setChecked(data.get("is_regex", False))
            self._cs.setChecked(data.get("case_sensitive", False))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.position().toPoint())
            if child is None:
                mods = QApplication.keyboardModifiers()
                if mods & Qt.KeyboardModifier.ControlModifier:
                    self.set_selected(not self._selected)
                else:
                    self.grip_pressed.emit(self)
                return
        super().mousePressEvent(event)

    def set_selected(self, s): self._selected = s; self.update()
    def is_selected(self): return self._selected

    def get_data(self):
        bg = self._bg.color()
        return {
            "enabled": self._chk.isChecked(),
            "keyword": self._kw.text(),
            "is_regex": self._rx.isChecked(),
            "case_sensitive": self._cs.isChecked(),
            "fg": self._fg.color(),
            "bg": bg if bg.lower() != "#ffffff" else None,
        }

    def set_fg(self, c): self._fg.set_color(c)
    def set_bg(self, c): self._bg.set_color(c)

    def paintEvent(self, event):
        if self._selected:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            path = QPainterPath()
            path.addRoundedRect(QRectF(self.rect()), 4, 4)
            p.fillPath(path, QColor(BG_SELECTED_ROW))
            p.end()
        super().paintEvent(event)


# ═══════════════════════════════════════════
# ★ v0.5: 自定义规则列表（拖动排序 + 多选 + 右键批量）
# ═══════════════════════════════════════════
class _CustomRuleList(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[_CustomRuleRow] = []
        self._drag_row = None
        self._v = QVBoxLayout(self)
        self._v.setContentsMargins(0, 0, 0, 0)
        self._v.setSpacing(2)
        self.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.customContextMenuRequested.connect(self._ctx)

    def _update_height(self):
        n = len(self._rows)
        self.setMinimumHeight(max(0, n * 30))
        self.updateGeometry()

    def add_rule(self, data=None):
        if len(self._rows) >= 200: return
        row = _CustomRuleRow(data)
        row.changed.connect(self.changed.emit)
        row.delete_me.connect(self._del)
        row.grip_pressed.connect(self._start_drag)
        self._v.insertWidget(self._v.count(), row)
        self._rows.append(row)
        self._update_height()
        self.changed.emit()

    def _del(self, row):
        if row in self._rows:
            self._rows.remove(row)
            self._v.removeWidget(row)
            row.deleteLater()
            self._update_height()
            self.changed.emit()

    def _start_drag(self, row):
        self._drag_row = row
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        if self._drag_row is None: return False
        if event.type() == QEvent.Type.MouseMove:
            local = self.mapFromGlobal(QCursor.pos())
            self._move(local.y()); return True
        if event.type() == QEvent.Type.MouseButtonRelease:
            self._end_drag(); return True
        return False

    def _move(self, y):
        di = self._rows.index(self._drag_row)
        for i, r in enumerate(self._rows):
            if r is self._drag_row: continue
            mid = r.geometry().y() + r.height() // 2
            if (i < di and y < mid) or (i > di and y > mid):
                self._rows.pop(di)
                self._rows.insert(i, self._drag_row)
                for rr in self._rows:
                    self._v.removeWidget(rr)
                for idx, rr in enumerate(self._rows):
                    self._v.insertWidget(idx, rr)
                return

    def _end_drag(self):
        self._drag_row = None
        QApplication.instance().removeEventFilter(self)
        self.changed.emit()

    def _ctx(self, pos):
        sel = [r for r in self._rows if r.is_selected()]
        if not sel: return
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:#fff;border:1px solid {BORDER_DEFAULT};"
            "border-radius:6px;padding:4px}"
            f"QMenu::item{{padding:4px 16px;font-size:{SMALL_FONT_SIZE}px;"
            "border-radius:4px}"
            f"QMenu::item:selected{{background:{BG_SELECTED_ROW};"
            f"color:{PRIMARY}}}"
        )
        a_fg = menu.addAction(f"修改字体颜色（{len(sel)}条）")
        a_bg = menu.addAction(f"修改背景颜色（{len(sel)}条）")
        act = menu.exec(self.mapToGlobal(pos))
        if act == a_fg:
            dlg = ColorPickerPopup(
                sel[0].get_data()["fg"], self.window()
            )
            if dlg.exec():
                for r in sel: r.set_fg(dlg.get_color())
                self.changed.emit()
        elif act == a_bg:
            bg0 = sel[0].get_data().get("bg") or "#ffffff"
            dlg = ColorPickerPopup(bg0, self.window())
            if dlg.exec():
                for r in sel: r.set_bg(dlg.get_color())
                self.changed.emit()

    def get_all(self):
        return [r.get_data() for r in self._rows]

    def clear_all(self):
        for r in list(self._rows): self._del(r)

    def clear_selection(self):
        for r in self._rows: r.set_selected(False)


# ═══════════════════════════════════════════
# ★ v0.69: 快捷键捕获控件
# ═══════════════════════════════════════════
class _ShortcutEdit(QWidget):
    """点击进入捕获模式，按下按键组合后记录并显示
    ★ v0.69: 内置圆润重置按钮 + Backspace/Delete 清空"""
    shortcut_changed = Signal(str)

    def __init__(self, default="", parent=None):
        super().__init__(parent)
        self._value = ""
        self._default = default
        self._capturing = False
        self._hovered = False
        self._reset_hovered = False
        self._clear_hovered = False
        self._conflict = False
        self.setFixedHeight(28)
        self.setMinimumWidth(100)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

    def value(self): return self._value

    def set_value(self, v):
        self._value = v; self._capturing = False; self.update()

    def _icon_size(self): return 18

    def _reset_rect(self):
        s = self._icon_size()
        if self._show_clear():
            x = self.width() - s * 2 - 8
        else:
            x = self.width() - s - 4
        return QRectF(x, (self.height() - s) / 2, s, s)

    def _clear_rect(self):
        s = self._icon_size()
        return QRectF(
            self.width() - s - 4,
            (self.height() - s) / 2, s, s,
        )

    def _show_clear(self):
        return bool(self._value) and not self._capturing

    def _show_reset(self):
        return self._value != self._default and not self._capturing

    def enterEvent(self, e):
        self._hovered = True; self.update()

    def leaveEvent(self, e):
        self._hovered = False; self._reset_hovered = False
        self.update()

    def mouseMoveEvent(self, e):
        pos = e.position()
        changed = False
        if self._show_reset():
            rr = self._reset_rect()
            was = self._reset_hovered
            self._reset_hovered = rr.contains(pos)
            if was != self._reset_hovered: changed = True
        else:
            if self._reset_hovered:
                self._reset_hovered = False; changed = True
        if self._show_clear():
            cr = self._clear_rect()
            was_c = self._clear_hovered
            self._clear_hovered = cr.contains(pos)
            if was_c != self._clear_hovered: changed = True
        else:
            if self._clear_hovered:
                self._clear_hovered = False; changed = True
        if changed: self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            pos = e.position()
            if (self._show_clear()
                    and self._clear_rect().contains(pos)):
                self._value = ""
                self._clear_hovered = False
                self._reset_hovered = False
                self.update()
                self.shortcut_changed.emit("")
                return
            if (self._show_reset()
                    and self._reset_rect().contains(pos)):
                self._value = self._default
                self._clear_hovered = False
                self._reset_hovered = False
                self.update()
                self.shortcut_changed.emit(self._default)
                return
            self._capturing = True
            self.setFocus(); self.update()

    def focusOutEvent(self, e):
        if self._capturing:
            self._capturing = False; self.update()
        super().focusOutEvent(e)

    def keyPressEvent(self, event):
        if not self._capturing:
            super().keyPressEvent(event); return
        key = event.key()
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift,
                   Qt.Key.Key_Alt, Qt.Key.Key_Meta,
                   Qt.Key.Key_unknown):
            return
        if key == Qt.Key.Key_Escape:
            self._capturing = False; self.update(); return
        if key in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            self._value = ""
            self._capturing = False; self.update()
            self.shortcut_changed.emit("")
            event.accept(); return
        mods = event.modifiers()
        seq = QKeySequence(
            int(mods.value) | key
        ).toString(QKeySequence.SequenceFormat.NativeText)
        if seq:
            self._value = seq
            self._capturing = False; self.update()
            self.shortcut_changed.emit(seq)
        event.accept()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        if self._capturing:
            border = QColor(BORDER_FOCUS)
            bg = QColor(PRIMARY_BG)
            text = "按键设置… (Esc取消/Del清空)"
            text_color = QColor(PRIMARY)
        elif self._conflict:
            border = QColor(ERROR_BORDER)
            bg = QColor(ERROR_BG)
            text = self._value or "（未设置）"
            text_color = QColor(ERROR)
        elif self._hovered:
            border = QColor(TEXT_MUTED)
            bg = QColor(BG_SUBTLE)
            text = self._value or "（未设置）"
            text_color = QColor(TEXT_PRIMARY)
        else:
            border = QColor(BORDER_DEFAULT)
            bg = QColor(BG_PANEL)
            text = self._value or "（未设置）"
            text_color = (
                QColor(TEXT_PRIMARY) if self._value
                else QColor(TEXT_MUTED)
            )
        path = QPainterPath()
        path.addRoundedRect(r, 6, 6)
        p.fillPath(path, bg)
        p.setPen(QPen(border, 1.5))
        p.drawPath(path)
        font = p.font()
        font.setPixelSize(SMALL_FONT_SIZE)
        font.setFamily("Consolas")
        p.setFont(font)
        p.setPen(text_color)
        n_icons = ((1 if self._show_clear() else 0)
                   + (1 if self._show_reset() else 0))
        text_r = self.width() - 8 - n_icons * (self._icon_size() + 2)
        p.drawText(
            QRectF(8, 0, text_r - 8, self.height()),
            Qt.AlignmentFlag.AlignVCenter
            | Qt.AlignmentFlag.AlignLeft, text,
        )
        icon_font = p.font()
        icon_font.setPixelSize(LABEL_FONT_SIZE)
        p.setFont(icon_font)
        if self._show_clear():
            cr = self._clear_rect()
            if self._clear_hovered:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(ERROR_HOVER_BG))
                p.drawEllipse(cr)
                p.setPen(QColor(ERROR))
            else:
                p.setPen(QColor(TEXT_DISABLED))
            cr_adj = QRectF(cr.x(), cr.y() - 1,
                            cr.width(), cr.height())
            p.drawText(cr_adj,
                       Qt.AlignmentFlag.AlignCenter, "×")
        if self._show_reset():
            rr = self._reset_rect()
            if self._reset_hovered:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(PRIMARY_LIGHT))
                p.drawEllipse(rr)
                p.setPen(QColor(PRIMARY))
            else:
                p.setPen(QColor(TEXT_DISABLED))
            p.drawText(rr,
                       Qt.AlignmentFlag.AlignCenter, "↺")
        p.end()


class _ShortcutRow(QWidget):
    """单行快捷键设置：标签 + 捕获框（内置重置）
    冲突提示显示在行下方（红色小字，左侧对齐捕获框）"""
    changed = Signal()

    def __init__(self, label, default_key, parent=None):
        super().__init__(parent)
        self._default = default_key
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        row = QWidget()
        row.setFixedHeight(34)
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 3, 0, 3)
        h.setSpacing(8)
        lbl = QLabel(label)
        lbl.setFixedWidth(90)
        lbl.setStyleSheet(
            f"font-size:{LABEL_FONT_SIZE}px;color:{TEXT_PRIMARY};"
            "background:transparent;"
        )
        h.addWidget(lbl)
        self._edit = _ShortcutEdit(default=default_key)
        self._edit.set_value(default_key)
        self._edit.shortcut_changed.connect(
            lambda _: self.changed.emit()
        )
        h.addWidget(self._edit, stretch=1)
        outer.addWidget(row)
        self._lbl_conflict = QLabel()
        self._lbl_conflict.setStyleSheet(
            f"font-size:{TINY_FONT_SIZE}px;color:{ERROR};"
            "background:transparent;padding:0 0 2px 98px;"
        )
        self._lbl_conflict.hide()
        outer.addWidget(self._lbl_conflict)

    def value(self): return self._edit.value()

    def set_value(self, v): self._edit.set_value(v)

    def set_conflict(self, msg=""):
        has = bool(msg)
        self._lbl_conflict.setVisible(has)
        if has: self._lbl_conflict.setText(msg)
        self._edit._conflict = has
        self._edit.update()
# ═══════════════════════════════════════════
# ★ 带三角箭头的自定义滚动条
# ═══════════════════════════════════════════
# ★ v0.7: _ArrowScrollBar 已迁移到 widgets.py，通过 Part 1 的 import 导入


# ═══════════════════════════════════════════
# ★ 帮助弹窗（就近弹出，点击外部自动关闭）
# ═══════════════════════════════════════════
_KW_HELP = """\
关键词匹配规则
━━━━━━━━━━━━━━━━━━━━
填写要高亮的文本，精确匹配。

单个词：
  error → 匹配日志中所有 error

多个词（空格分隔）：
  error fail timeout
  → 同时匹配这三个词

• 默认不区分大小写
• 勾选 Aa 后精确匹配大小写"""

_RX_HELP = r"""\
正则表达式规则
━━━━━━━━━━━━━━━━━━━━
勾选 .* 后，输入内容作为正则表达式。

常用语法：
  |      或        error|fail
  .      任意字符   a.c → abc, a1c
  *      零或多次   ab* → a, ab, abb
  +      一或多次   ab+ → ab, abb
  ?      零或一次   colou?r
  \\d     数字      \\d+ → 123
  \\b     词边界    \\berror\\b
  \[...\]  字符集    \[aeiou\] 任意元音
  (...)  分组      (err|fail)
  \\.     转义点号   192\\.168

场景举例：
  匹配 IP 地址
    \\d+\\.\\d+\\.\\d+\\.\\d+
    → 192.168.1.1

  匹配 HEX 地址
    0x\[0-9a-fA-F\]+
    → 0x1A2B, 0xFF00

  匹配方括号标签
    \\\[.*?\\\]
    → \[RX\], \[WARN\], \[ERR\]

  匹配多个错误关键词
    error|fail|fatal
    → error, fail, fatal

  匹配时间戳格式
    \\d{2}:\\d{2}:\\d{2}
    → 14:30:02

• 默认不区分大小写
• 勾选 Aa 后精确匹配大小写"""


class _HelpPopup(QDialog):
    """帮助弹窗 — 居中显示，外围半透明遮罩"""

    def __init__(self, content, parent=None, width=280):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, True
        )
        self._pw = width
        self._panel = QWidget(self)
        v = QVBoxLayout(self._panel)
        v.setContentsMargins(2, 2, 2, 2)
        v.setSpacing(0)
        self._body = QTextEdit()
        self._body.setReadOnly(True)
        self._body.setPlainText(content)
        self._body.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._body.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._body.setStyleSheet(
            "QTextEdit{background:transparent;border:none;"
            "font-size:12px;color:#374151;padding:8px 10px;"
            "font-family:Consolas,'Courier New',monospace}"
            "QScrollBar:vertical{width:4px;background:transparent}"
            "QScrollBar::handle:vertical{background:#d1d5db;"
            "border-radius:2px}"
            "QScrollBar::add-line,QScrollBar::sub-line{"
            "width:0;height:0}"
        )
        v.addWidget(self._body)
        self._panel.setFixedWidth(width)
        doc = self._body.document()
        doc.setTextWidth(width - 28)
        h = int(doc.size().height()) + 20
        self._ph = min(h, 420)
        self._panel.setFixedHeight(self._ph)

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            pw = self.parent()
            self.resize(pw.size())
            self.move(pw.mapToGlobal(QPoint(0, 0)))
        self._panel.move(
            (self.width() - self._pw) // 2,
            (self.height() - self._ph) // 2,
        )

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), QColor(0, 0, 0, 80))
        pr = QRectF(self._panel.geometry()).adjusted(
            0.5, 0.5, -0.5, -0.5
        )
        path = QPainterPath()
        path.addRoundedRect(pr, 8, 8)
        p.fillPath(path, QColor("#ffffff"))
        p.setPen(QPen(QColor("#d1d5db"), 1.0))
        p.drawPath(path)
        p.end()

    def mousePressEvent(self, event):
        if not self._panel.geometry().contains(event.pos()):
            self.close()
            return
        super().mousePressEvent(event)


# ═══════════════════════════════════════════
# 主设置弹窗（全屏遮罩模式）
# ═══════════════════════════════════════════
class SettingsDialog(QDialog):
    highlight_changed = Signal()
    font_size_changed = Signal(int)  # ★ v0.6 fix: 字号专用信号，不触发 rehighlight
    word_wrap_changed = Signal(bool)   # ★ v0.6: 自动换行开关
    max_lines_changed = Signal(int)    # ★ v0.6: 行数上限变更
    show_line_numbers_changed = Signal(bool)  # ★ v0.69: 行号显示开关

    def __init__(self, config, tab_names, parent=None):
        super().__init__(parent)
        self._config = config
        self._tab_names = tab_names
        self._tab_checks = []
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, True
        )
        self._panel = QWidget(self)
        self._panel.setFixedSize(PANEL_W, PANEL_H)
        # ★ [8] 已移除所有 QToolTip（规避 WA_TranslucentBackground 黑色 tooltip）
        self._record_all = True  # ★ v0.45: 全选状态（新增tab是否自动勾选）
        self._init_panel()
        self._load()
        self._connect_auto_save()
        self._on_enabled_toggled(self._chk_enabled.isChecked())
        self._on_hl_enabled(self._chk_hl_enabled.isChecked())
        self._refresh_preview()

    def _init_panel(self):
        root = QVBoxLayout(self._panel)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ★ 顶部标题栏：齿轮图标 + "设置" 文字 + 关闭按钮
        top_bar = QWidget()
        top_bar.setFixedHeight(32)
        top_h = QHBoxLayout(top_bar)
        top_h.setContentsMargins(0, 0, 0, 0)
        top_h.setSpacing(0)

        # ★ 左侧：齿轮图标 + "设置"
        self._gear_icon = _GearIconLabel()
        top_h.addWidget(self._gear_icon)
        lbl_title = QLabel("设置")
        lbl_title.setStyleSheet(
            "font-size: 13px; font-weight: 600;"
            " color: #374151; background: transparent;"
        )
        lbl_title.setAlignment(
            Qt.AlignmentFlag.AlignVCenter
            | Qt.AlignmentFlag.AlignLeft
        )
        top_h.addWidget(lbl_title)

        top_h.addStretch(1)
        self._btn_close = _CloseBtn()  # v0.7: 新 CloseBtn 统一 drawLine 圆形 hover
        self._btn_close.clicked.connect(self.close)
        top_h.addWidget(
            self._btn_close,
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )
        top_h.addSpacing(6)  # 右侧留白
        root.addSpacing(4)  # 顶部留白
        root.addWidget(top_bar)

        # ── 内容区 ──
        content = QWidget()
        content_v = QVBoxLayout(content)
        content_v.setContentsMargins(16, 4, 14, 14)
        content_v.setSpacing(0)

        body_h = QHBoxLayout()
        body_h.setSpacing(12)

        nav_w = QWidget()
        nav_w.setFixedWidth(80)
        nav_v = QVBoxLayout(nav_w)
        nav_v.setContentsMargins(0, 0, 0, 0)
        nav_v.setSpacing(4)
        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        btn_log = _NavBtn("日志")
        btn_log.setChecked(True)
        self._nav_group.addButton(btn_log, 0)
        nav_v.addWidget(btn_log)
        btn_hl = _NavBtn("字体")
        self._nav_group.addButton(btn_hl, 1)
        nav_v.addWidget(btn_hl)
        btn_other = _NavBtn("其他")
        self._nav_group.addButton(btn_other, 2)
        nav_v.addWidget(btn_other)
        btn_sc = _NavBtn("快捷键")
        self._nav_group.addButton(btn_sc, 3)
        nav_v.addWidget(btn_sc)
        nav_v.addStretch(1)
        body_h.addWidget(nav_w)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_log_page())
        self._stack.addWidget(self._build_highlight_page())
        self._stack.addWidget(self._build_other_page())
        self._stack.addWidget(self._build_shortcut_page())
        body_h.addWidget(self._stack, stretch=1)
        self._nav_group.idClicked.connect(self._on_nav)
        content_v.addLayout(body_h, stretch=1)

        content_v.addSpacing(12)
        bottom_h = QHBoxLayout()
        bottom_h.addStretch(1)
        self._btn_reset = _ResetBtn()
        self._btn_reset.clicked.connect(self._reset)
        bottom_h.addWidget(self._btn_reset)
        content_v.addLayout(bottom_h)

        root.addWidget(content, stretch=1)

    def _build_log_page(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        log_content = QWidget()
        _lc_v = QVBoxLayout(log_content)
        _lc_v.setContentsMargins(0, 0, 0, 0)
        _lc_v.setSpacing(10)

        self._chk_enabled = QCheckBox(
            "启用实时日志记录（连接串口时自动开始）"
        )
        self._chk_enabled.setStyleSheet(_CHK_SS)
        self._chk_enabled.toggled.connect(self._on_enabled_toggled)
        _lc_v.addWidget(self._chk_enabled)

        self._options_widget = QWidget()
        opts_v = QVBoxLayout(self._options_widget)
        opts_v.setContentsMargins(0, 0, 0, 0)
        opts_v.setSpacing(10)

        dir_h = QHBoxLayout()
        dir_h.setSpacing(6)
        lbl = QLabel("保存位置：")
        lbl.setStyleSheet(
            "font-size: 13px; color: #374151;"
            " background: transparent;"
        )
        lbl.setFixedHeight(28)
        lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        dir_h.addWidget(lbl)
        self._lbl_dir = QLineEdit()
        self._lbl_dir.setPlaceholderText("默认：应用所在目录/logs")
        self._lbl_dir.setStyleSheet(
            "QLineEdit { font-size: 12px; color: #374151;"
            "  background: #ffffff;"
            "  border: 1.5px solid #d1d5db;"
            "  border-radius: 6px; padding: 0px 4px 2px 4px;"
            "  min-height: 24px; max-height: 28px;"
            "  selection-background-color: #2563eb;"
            "  selection-color: #ffffff; }"
            "QLineEdit:focus { border-color: #3b82f6; }"
            "QLineEdit:disabled { background: #f3f4f6;"
            "  color: #c0c0c0; border-color: #e5e7eb; }"
        )
        self._lbl_dir.setFixedHeight(28)
        dir_h.addWidget(self._lbl_dir, stretch=1)
        btn_browse = QPushButton("浏览")
        btn_browse.setFixedSize(52, 28)
        btn_browse.setStyleSheet(
            "QPushButton { background: transparent;"
            "  border: none;"
            "  border-radius: 6px;"
            "  padding: 0; font-size: 13px;"
            "  color: #6b7280;"
            "  min-height: 28px; min-width: 52px; }"
            "QPushButton:hover { background: #f3f4f6;"
            "  color: #374151; }"
            "QPushButton:pressed { background: #e5e7eb; }"
            "QPushButton:disabled { background: transparent;"
            "  color: #c0c0c0; }"
        )
        btn_browse.clicked.connect(self._browse)
        dir_h.addWidget(
            btn_browse,
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )
        opts_v.addLayout(dir_h)

        fmt_h = QHBoxLayout()
        fmt_h.setSpacing(8)
        fmt_lbl = QLabel("文件格式：")
        fmt_lbl.setStyleSheet(
            "font-size: 13px; color: #374151;"
            " background: transparent;"
        )
        fmt_h.addWidget(fmt_lbl)
        self._radio_log = QRadioButton(".log")
        self._radio_txt = QRadioButton(".txt")
        for r in (self._radio_log, self._radio_txt):
            r.setStyleSheet(_RADIO_SS)
        self._radio_log.setChecked(True)
        fmt_h.addWidget(self._radio_log)
        fmt_h.addWidget(self._radio_txt)
        fmt_h.addStretch(1)
        opts_v.addLayout(fmt_h)


        tab_inner = QWidget()
        tab_v = QVBoxLayout(tab_inner)
        tab_v.setContentsMargins(4, 6, 4, 6)
        tab_v.setSpacing(2)

        # ★ v0.45: 全选项（独立控制，不自动联动）
        self._chk_select_all = _TagChip(
            "全选（新增 Tab 自动勾选）"
        )
        self._chk_select_all.toggled.connect(
            self._toggle_select_all
        )
        tab_v.addWidget(self._chk_select_all)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #e5e7eb;")
        tab_v.addWidget(sep)

        # ★ v0.45: 各 Tab 列表项
        for name in self._tab_names:
            item = _TagChip(name)
            item.toggled.connect(
                self._on_tab_check_changed
            )
            self._tab_checks.append(item)
            tab_v.addWidget(item)
        tab_v.addStretch(1)

        self._tab_scroll = QScrollArea()
        self._tab_scroll.setWidget(tab_inner)
        self._tab_scroll.setWidgetResizable(True)
        self._tab_scroll.setFrameShape(QFrame.Shape.NoFrame)
        tab_inner.setStyleSheet("background: transparent;")
        # ★ QPainter 抗锯齿圆角容器
        self._scroll_container = _RoundedScrollContainer(
            self._tab_scroll
        )
        self._scroll_container.setMaximumHeight(120)
        opts_v.addWidget(self._scroll_container)
        opts_v.addStretch(1)
        _lc_v.addWidget(self._options_widget)

        self._log_scroll = QScrollArea()
        self._log_scroll.setWidget(log_content)
        self._log_scroll.setWidgetResizable(True)
        self._log_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._log_scroll.setVerticalScrollBar(_ArrowScrollBar())
        self._log_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self._log_scroll.setViewportMargins(0, 0, 12, 0)
        self._log_scroll.setStyleSheet(
            "QScrollArea{border:none;background:transparent}"
        )
        self._log_scroll.viewport().setStyleSheet(
            "background:transparent;"
        )
        v.addWidget(self._log_scroll)

        # ★ sticky 置顶覆盖层
        self._sticky_log = QWidget(page)
        _sl = QHBoxLayout(self._sticky_log)
        _sl.setContentsMargins(0, 0, 12, 0)
        _sl.setSpacing(0)
        self._sticky_log_chk = QCheckBox(
            "启用实时日志记录（连接串口时自动开始）"
        )
        self._sticky_log_chk.setStyleSheet(_CHK_SS)
        self._sticky_log_chk.setChecked(
            self._chk_enabled.isChecked()
        )
        _sl.addWidget(self._sticky_log_chk)
        self._sticky_log.setStyleSheet(
            "background:#ffffff;"
            "border-bottom:1px solid #e5e7eb;"
        )
        self._sticky_log.hide()
        self._sticky_log_chk.toggled.connect(
            self._chk_enabled.setChecked
        )
        self._chk_enabled.toggled.connect(
            self._sticky_log_chk.setChecked
        )
        self._log_scroll.verticalScrollBar().valueChanged.connect(
            self._on_log_sticky
        )
        return page

    def _on_enabled_toggled(self, checked):
        self._options_widget.setEnabled(checked)

    def _toggle_select_all(self, checked):
        """★ v0.45: 用户点击全选 → record_all 跟随"""
        self._record_all = checked
        for chk in self._tab_checks:
            chk.blockSignals(True)
            chk.setChecked(checked)
            chk.blockSignals(False)
        self._auto_save()

    def _on_tab_check_changed(self):
        """★ v0.45: 单独改 tab 不影响全选状态"""
        self._auto_save()

    def _connect_auto_save(self):
        self._chk_enabled.toggled.connect(self._auto_save)
        self._radio_log.toggled.connect(self._auto_save)
        self._radio_txt.toggled.connect(self._auto_save)
        self._lbl_dir.textChanged.connect(self._auto_save)

    def _auto_save(self):
        self._write_to_config()
        save_config(self._config)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), OVERLAY_COLOR)
        pr = QRectF(self._panel.geometry()).adjusted(
            0.5, 0.5, -0.5, -0.5
        )
        path = QPainterPath()
        path.addRoundedRect(pr, RADIUS, RADIUS)
        p.fillPath(path, BG_COLOR)
        p.setPen(QPen(BORDER_COLOR, 1.5))
        p.drawPath(path)
        p.end()

    def mousePressEvent(self, event):
        if not self._panel.geometry().contains(event.pos()):
            self.close()
            return
        super().mousePressEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            pw = self.parent()
            self.resize(pw.size())
            self.move(pw.mapToGlobal(QPoint(0, 0)))
        self._center_panel()
        self._clip_panel()
        self._update_hl_body_size()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._center_panel()
        self._clip_panel()

    def _center_panel(self):
        self._panel.move(
            (self.width() - PANEL_W) // 2,
            (self.height() - PANEL_H) // 2,
        )

    def _clip_panel(self):
        path = QPainterPath()
        path.addRoundedRect(
            QRectF(self._panel.rect()), RADIUS, RADIUS
        )
        self._panel.setMask(
            QRegion(path.toFillPolygon().toPolygon())
        )

    def _browse(self):
        d = QFileDialog.getExistingDirectory(
            self, "选择日志保存目录"
        )
        if d:
            self._lbl_dir.setText(d)
            self._lbl_dir.setCursorPosition(0)
            self._auto_save()

    def _build_highlight_page(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # ★ 内容包装器（checkbox + body 都在滚动区内）
        self._hl_content = QWidget()
        _hlc_v = QVBoxLayout(self._hl_content)
        _hlc_v.setContentsMargins(0, 0, 0, 0)
        _hlc_v.setSpacing(8)

        # ★ 默认字体颜色（独立于高亮开关）
        dfg_h = QHBoxLayout()
        dfg_h.setSpacing(6)
        lbl_dfg = QLabel("默认字体颜色")
        lbl_dfg.setStyleSheet(
            "font-size:12px;color:#6b7280;"
            "background:transparent;"
        )
        dfg_h.addWidget(lbl_dfg)
        _hl_cfg = self._config.get("highlight", {})
        _dfg_c = _hl_cfg.get("default_fg", "#1e293b")
        self._default_fg_btn = _ColorBtn(_dfg_c, letter=True)
        self._default_fg_btn.color_changed.connect(
            self._on_hl_changed
        )
        dfg_h.addWidget(self._default_fg_btn)
        dfg_h.addStretch(1)
        _hlc_v.addLayout(dfg_h)

        # ★ 日志字号设置
        fs_h = QHBoxLayout()
        fs_h.setSpacing(6)
        lbl_fs = QLabel("日志字号")
        lbl_fs.setStyleSheet(
            "font-size:12px;color:#6b7280;"
            "background:transparent;"
        )
        fs_h.addWidget(lbl_fs)
        # ★ ◀ [字号] ▶ 自定义字号控件
        fs_ctrl = QWidget()
        fs_ctrl_h = QHBoxLayout(fs_ctrl)
        fs_ctrl_h.setContentsMargins(0, 0, 0, 0)
        fs_ctrl_h.setSpacing(1)
        self._fs_dec_btn = _CircleBtn("◀", size=28)
        self._fs_dec_btn._font_size = 22
        self._fs_dec_btn._fg = "#9ca3af"
        self._fs_dec_btn._fg_hover = "#374151"
        self._fs_dec_btn.clicked.connect(
            self._fs_dec
        )
        fs_ctrl_h.addWidget(self._fs_dec_btn)
        self._fs_edit = QLineEdit()
        self._fs_edit.setFixedWidth(28)
        self._fs_edit.setFixedHeight(18)
        self._fs_edit.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self._fs_edit.setMaxLength(2)
        self._fs_edit.setText(
            str(_hl_cfg.get("font_size", 12))
        )
        self._fs_edit.setStyleSheet(
            "QLineEdit{font-size:11px;"
            "color:#374151;background:#fff;"
            "border:1.5px solid #d1d5db;"
            "border-radius:3px;padding:0;"
            "selection-background-color:#2563eb;"
            "selection-color:#fff}"
            "QLineEdit:focus{border-color:#3b82f6}"
        )
        self._fs_edit.editingFinished.connect(
            self._fs_edited
        )
        fs_ctrl_h.addWidget(self._fs_edit)
        self._fs_inc_btn = _CircleBtn("▶", size=28)
        self._fs_inc_btn._font_size = 22
        self._fs_inc_btn._fg = "#9ca3af"
        self._fs_inc_btn._fg_hover = "#374151"
        self._fs_inc_btn.clicked.connect(
            self._fs_inc
        )
        fs_ctrl_h.addWidget(self._fs_inc_btn)
        fs_h.addWidget(
            fs_ctrl, 0,
            Qt.AlignmentFlag.AlignVCenter,
        )
        lbl_pt = QLabel("pt")
        lbl_pt.setStyleSheet(
            "font-size:12px;color:#9ca3af;"
            "background:transparent;"
        )
        fs_h.addWidget(lbl_pt)
        fs_h.addStretch(1)
        _hlc_v.addLayout(fs_h)

        _hlc_v.addSpacing(12)
        sep_hl1 = QFrame()
        sep_hl1.setFixedHeight(2)
        sep_hl1.setStyleSheet("background: #e5e7eb;")
        _hlc_v.addWidget(sep_hl1)
        _hlc_v.addSpacing(12)

        # ★ 自动换行
        self._chk_wrap = QCheckBox("自动换行")
        self._chk_wrap.setStyleSheet(_CHK_SS)
        self._chk_wrap.setChecked(
            _hl_cfg.get("word_wrap", False)
        )
        self._chk_wrap.toggled.connect(
            self._on_wrap_changed
        )
        _hlc_v.addWidget(self._chk_wrap)

        # ★ v0.69: 显示行号
        self._chk_line_numbers = QCheckBox("显示行号")
        self._chk_line_numbers.setStyleSheet(_CHK_SS)
        self._chk_line_numbers.setChecked(
            _hl_cfg.get("show_line_numbers", True)
        )
        self._chk_line_numbers.toggled.connect(
            self._on_line_numbers_changed
        )
        _hlc_v.addWidget(self._chk_line_numbers)

        # ★ 行数上限
        ml_h = QHBoxLayout()
        ml_h.setSpacing(6)
        lbl_ml = QLabel("行数上限")
        lbl_ml.setStyleSheet(
            "font-size:12px;color:#6b7280;"
            "background:transparent;"
        )
        ml_h.addWidget(lbl_ml)
        self._max_lines_spin = QSpinBox()
        self._max_lines_spin.setObjectName("max_lines_spin")
        self._max_lines_spin.setRange(500, 100000)
        self._max_lines_spin.setSingleStep(500)
        self._max_lines_spin.setValue(
            _hl_cfg.get("max_lines", 5000)
        )
        self._max_lines_spin.setFixedWidth(80)
        self._max_lines_spin.setStyleSheet(
            "QSpinBox#max_lines_spin{"
            "font-size:11px;color:#374151;"
            "background:#fff;border:1.5px solid #d1d5db;"
            "border-radius:3px;padding:0 2px;"
            "min-height:18px;max-height:18px}"
            "QSpinBox#max_lines_spin:focus{"
            "border-color:#3b82f6}"
            "QSpinBox#max_lines_spin:disabled{"
            "background:#f3f4f6;color:#c0c0c0;"
            "border-color:#e5e7eb}"
        )
        self._max_lines_spin.valueChanged.connect(
            self._on_max_lines_changed
        )
        ml_h.addWidget(self._max_lines_spin)
        self._chk_unlimited = QCheckBox("无限制")
        self._chk_unlimited.setStyleSheet(_CHK_SS)
        self._chk_unlimited.toggled.connect(
            self._on_unlimited_toggled
        )
        ml_h.addWidget(self._chk_unlimited)
        lbl_ml_warn = QLabel("（不建议超过 10000）")
        lbl_ml_warn.setStyleSheet(
            "font-size:11px;color:#e67700;"
            "background:transparent;"
        )
        ml_h.addWidget(lbl_ml_warn)
        ml_h.addStretch(1)
        _hlc_v.addLayout(ml_h)

        _hlc_v.addSpacing(12)
        sep_hl2 = QFrame()
        sep_hl2.setFixedHeight(2)
        sep_hl2.setStyleSheet("background: #e5e7eb;")
        _hlc_v.addWidget(sep_hl2)
        _hlc_v.addSpacing(12)

        # ★ 启用高亮
        self._chk_hl_enabled = QCheckBox("启用关键词高亮")
        self._chk_hl_enabled.setStyleSheet(_CHK_SS)
        self._chk_hl_enabled.setChecked(True)
        self._chk_hl_enabled.toggled.connect(
            self._on_hl_enabled
        )
        _hlc_v.addWidget(self._chk_hl_enabled)

        self._hl_body = QWidget()
        body_v = QVBoxLayout(self._hl_body)
        body_v.setContentsMargins(10, 0, 10, 0)
        body_v.setSpacing(6)

        # ★ 预览区（可编辑，样式与日志窗一致）
        self._hl_preview = QTextEdit()
        self._hl_preview.setFixedHeight(80)
        self._hl_preview.setPlainText(PREVIEW_TEXT)
        self._hl_preview.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._hl_preview.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._hl_preview.setStyleSheet(
            "QTextEdit{background:#ffffff;color:#1e293b;"
            "border:1px solid #e5e7eb;border-radius:4px;"
            "font-family:Consolas,monospace;font-size:12px;"
            "padding:2px 4px;"
            "selection-background-color:#2563eb;"
            "selection-color:#ffffff}"
            "QScrollBar:vertical{width:4px;background:transparent}"
            "QScrollBar::handle:vertical{background:#d1d5db;"
            "border-radius:2px}"
            "QScrollBar::add-line,QScrollBar::sub-line{"
            "width:0;height:0}"
        )
        self._preview_hl = LogHighlighter(
            self._hl_preview.document()
        )
        body_v.addWidget(self._hl_preview)

        # ★ 内置规则
        lbl_b = QLabel("内置规则")
        lbl_b.setStyleSheet(
            "font-size:12px;color:#6b7280;"
            "background:transparent;"
        )
        body_v.addWidget(lbl_b)

        builtin_inner = QWidget()
        bi_v = QVBoxLayout(builtin_inner)
        bi_v.setContentsMargins(4, 4, 4, 4)
        bi_v.setSpacing(2)

        # ★ 表头（含全选框）[16]
        hdr = QWidget()
        hdr.setFixedHeight(18)
        hdr_h = QHBoxLayout(hdr)
        hdr_h.setContentsMargins(6, 0, 6, 0)
        hdr_h.setSpacing(6)
        _hdr_ss = "font-size:10px;color:#9ca3af;background:transparent;"
        self._bi_chk_all = QCheckBox()
        self._bi_chk_all.setStyleSheet(
            "QCheckBox{spacing:0;background:transparent}"
            "QCheckBox::indicator{width:12px;height:12px;margin:2px}"
            "QCheckBox::indicator:unchecked{"
            "border:1px solid #9ca3af;border-radius:3px;background:#fff}"
            "QCheckBox::indicator:checked{"
            "border:1px solid #2563eb;border-radius:3px;background:#2563eb}"
            "QCheckBox::indicator:hover{border-color:#3b82f6}"
        )
        self._bi_chk_all.setChecked(True)
        self._bi_chk_all.toggled.connect(self._toggle_bi_all)
        hdr_h.addWidget(self._bi_chk_all)
        hdr_name = QLabel("名称")
        hdr_name.setStyleSheet(_hdr_ss)
        hdr_name.setIndent(4)
        hdr_h.addWidget(hdr_name, stretch=1)
        hdr_cs = QLabel("大小写")
        hdr_cs.setStyleSheet(_hdr_ss)
        hdr_cs.setFixedWidth(38)
        hdr_h.addWidget(hdr_cs)
        hdr_fg = QLabel("字色")
        hdr_fg.setStyleSheet(_hdr_ss)
        hdr_fg.setFixedWidth(22)
        hdr_h.addWidget(hdr_fg)
        hdr_bg = QLabel("背景")
        hdr_bg.setStyleSheet(_hdr_ss)
        hdr_bg.setFixedWidth(22)
        hdr_h.addWidget(hdr_bg)
        bi_v.addWidget(hdr)

        hl_cfg = self._config.get("highlight", {})
        bc = hl_cfg.get("builtin_rules", {})
        self._builtin_rows = []
        for rule in BUILTIN_RULES:
            ov = bc.get(rule["id"])
            row = _BuiltinRuleRow(rule, override=ov)
            row.changed.connect(self._on_hl_changed)
            bi_v.addWidget(row)
            self._builtin_rows.append(row)
        bi_v.addStretch(1)

        bi_scroll = QScrollArea()
        bi_scroll.setWidget(builtin_inner)
        bi_scroll.setWidgetResizable(True)
        bi_scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )
        builtin_inner.setStyleSheet(
            "background:transparent;"
        )
        bi_container = _RoundedScrollContainer(
            bi_scroll
        )
        bi_container.setMinimumHeight(130)
        bi_container.setMaximumHeight(130)
        body_v.addWidget(bi_container)

        # ★ 自定义规则 + 添加按钮（同一行）
        cu_title_h = QHBoxLayout()
        cu_title_h.setSpacing(6)
        lbl_c = QLabel("自定义规则")
        lbl_c.setStyleSheet(
            "font-size:12px;color:#6b7280;"
            "background:transparent;"
        )
        cu_title_h.addWidget(lbl_c)
        btn_add = _CircleBtn("+", size=22)
        btn_add.clicked.connect(self._add_user_rule)
        cu_title_h.addWidget(btn_add)
        cu_title_h.addStretch(1)
        lbl_kw_q = QLabel("关键词")
        lbl_kw_q.setStyleSheet(
            "font-size:10px;color:#b0b8c4;"
            "background:transparent;"
        )
        cu_title_h.addWidget(lbl_kw_q)
        btn_kw_help = _CircleBtn("?", size=14)
        btn_kw_help._font_size = 9
        btn_kw_help._font_weight = 600
        btn_kw_help._fg = "#b0b8c4"
        btn_kw_help._fg_hover = "#2563eb"
        btn_kw_help.clicked.connect(
            lambda: self._show_help(btn_kw_help, _KW_HELP, 260)
        )
        cu_title_h.addWidget(btn_kw_help)
        cu_title_h.addSpacing(4)
        lbl_rx_q = QLabel("正则")
        lbl_rx_q.setStyleSheet(
            "font-size:10px;color:#b0b8c4;"
            "background:transparent;"
        )
        cu_title_h.addWidget(lbl_rx_q)
        btn_rx_help = _CircleBtn("?", size=14)
        btn_rx_help._font_size = 9
        btn_rx_help._font_weight = 600
        btn_rx_help._fg = "#b0b8c4"
        btn_rx_help._fg_hover = "#2563eb"
        btn_rx_help.clicked.connect(
            lambda: self._show_help(btn_rx_help, _RX_HELP, 300)
        )
        cu_title_h.addWidget(btn_rx_help)
        body_v.addLayout(cu_title_h)

        # ★ 圆角边框容器 + 表头 + 规则列表（带滚动条）
        cu_frame = QWidget()
        cu_frame.setObjectName("CuFrame")
        cu_frame.setStyleSheet(
            "QWidget#CuFrame{"
            "background:#ffffff;"
            "border:1.5px solid #d1d5db;"
            "border-radius:6px}"
        )
        cu_frame_v = QVBoxLayout(cu_frame)
        cu_frame_v.setContentsMargins(4, 4, 4, 4)
        cu_frame_v.setSpacing(2)
        cu_hdr = QWidget()
        cu_hdr.setFixedHeight(18)
        cu_hdr_h = QHBoxLayout(cu_hdr)
        cu_hdr_h.setContentsMargins(6, 0, 6, 0)
        cu_hdr_h.setSpacing(6)
        self._cu_chk_all = QCheckBox()
        self._cu_chk_all.setStyleSheet(
            "QCheckBox{spacing:0;background:transparent}"
            "QCheckBox::indicator{width:12px;height:12px;margin:2px}"
            "QCheckBox::indicator:unchecked{"
            "border:1px solid #9ca3af;border-radius:3px;background:#fff}"
            "QCheckBox::indicator:checked{"
            "border:1px solid #2563eb;border-radius:3px;background:#2563eb}"
            "QCheckBox::indicator:hover{border-color:#3b82f6}"
        )
        self._cu_chk_all.setChecked(True)
        self._cu_chk_all.toggled.connect(self._toggle_cu_all)
        cu_hdr_h.addWidget(self._cu_chk_all)
        cu_hdr_kw = QLabel("关键词")
        cu_hdr_kw.setStyleSheet(_hdr_ss)
        cu_hdr_kw.setIndent(4)
        cu_hdr_h.addWidget(cu_hdr_kw, stretch=1)
        cu_hdr_rx = QLabel("正则")
        cu_hdr_rx.setStyleSheet(_hdr_ss)
        cu_hdr_rx.setFixedWidth(32)
        cu_hdr_h.addWidget(cu_hdr_rx)
        cu_hdr_cs = QLabel("大小写")
        cu_hdr_cs.setStyleSheet(_hdr_ss)
        cu_hdr_cs.setFixedWidth(38)
        cu_hdr_h.addWidget(cu_hdr_cs)
        cu_hdr_fg = QLabel("字色")
        cu_hdr_fg.setStyleSheet(_hdr_ss)
        cu_hdr_fg.setFixedWidth(22)
        cu_hdr_h.addWidget(cu_hdr_fg)
        cu_hdr_bg = QLabel("背景")
        cu_hdr_bg.setStyleSheet(_hdr_ss)
        cu_hdr_bg.setFixedWidth(22)
        cu_hdr_h.addWidget(cu_hdr_bg)
        cu_hdr_del = QLabel("")
        cu_hdr_del.setFixedWidth(20)
        cu_hdr_h.addWidget(cu_hdr_del)
        cu_frame_v.addWidget(cu_hdr)
        self._custom_list = _CustomRuleList()
        self._custom_list.changed.connect(
            self._on_hl_changed
        )
        self._custom_list.setStyleSheet(
            "background:transparent;"
        )
        cu_frame_v.addWidget(self._custom_list)
        cu_frame_v.addStretch(1)
        cu_frame.setMinimumHeight(60)
        body_v.addWidget(cu_frame)
        body_v.addStretch(1)

        _hlc_v.addWidget(self._hl_body)

        self._hl_scroll = QScrollArea()
        self._hl_scroll.setWidget(self._hl_content)
        self._hl_scroll.setWidgetResizable(True)
        self._hl_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._hl_scroll.setStyleSheet(
            "QScrollArea{border:none;background:transparent}"
        )
        self._hl_scroll.setVerticalScrollBar(_ArrowScrollBar())
        self._hl_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self._hl_scroll.setViewportMargins(0, 0, 12, 0)
        self._hl_scroll.viewport().setStyleSheet("background:transparent;")
        v.addWidget(self._hl_scroll)

        # ★ sticky 置顶覆盖层（滚过 checkbox 时固定在顶部）
        self._sticky_hl = QWidget(page)
        _sh = QHBoxLayout(self._sticky_hl)
        _sh.setContentsMargins(0, 0, 12, 0)
        _sh.setSpacing(0)
        self._sticky_hl_chk = QCheckBox("启用关键词高亮")
        self._sticky_hl_chk.setStyleSheet(_CHK_SS)
        self._sticky_hl_chk.setChecked(
            self._chk_hl_enabled.isChecked()
        )
        _sh.addWidget(self._sticky_hl_chk)
        self._sticky_hl.setStyleSheet(
            "background:#ffffff;"
            "border-bottom:1px solid #e5e7eb;"
        )
        self._sticky_hl.hide()
        self._sticky_hl_chk.toggled.connect(
            self._chk_hl_enabled.setChecked
        )
        self._chk_hl_enabled.toggled.connect(
            self._sticky_hl_chk.setChecked
        )
        self._hl_scroll.verticalScrollBar().valueChanged.connect(
            self._on_hl_sticky
        )
        return page

    def _build_shortcut_page(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 20, 0)
        v.setSpacing(4)
        lbl_hint = QLabel(
            "点击捕获框按新组合 · Del清空 · 右侧↺重置"
        )
        lbl_hint.setStyleSheet(
            "font-size:11px;color:#9ca3af;"
            "background:transparent;"
        )
        v.addWidget(lbl_hint)
        self._sc_close_tab = _ShortcutRow(
            "关闭 Tab", "Ctrl+W"
        )
        self._sc_goto_line = _ShortcutRow(
            "跳转行号", "Ctrl+G"
        )
        self._sc_send = _ShortcutRow(
            "发送", "Ctrl+Return"
        )
        for row in (
            self._sc_close_tab,
            self._sc_goto_line,
            self._sc_send,
        ):
            row.changed.connect(
                self._on_shortcut_changed
            )
            v.addWidget(row)
        # ★ v0.69: 内置快捷键参考（不可修改）
        v.addSpacing(12)
        sep_sc = QFrame()
        sep_sc.setFixedHeight(2)
        sep_sc.setStyleSheet("background: #e5e7eb;")
        v.addWidget(sep_sc)
        v.addSpacing(8)
        lbl_ref = QLabel("内置快捷键（不可修改）")
        lbl_ref.setStyleSheet(
            "font-size:12px;color:#6b7280;"
            "background:transparent;"
            "font-weight:600;"
        )
        v.addWidget(lbl_ref)
        _ref_ss = (
            "font-size:11px;color:#6b7280;"
            "background:transparent;"
            "font-family:Consolas,monospace;"
        )
        _refs = [
            ("Home", "跳到文档开头"),
            ("End", "跳到最后一行（跳过空行）"),
            ("PgUp / PgDn", "垂直翻页"),
            ("Shift+PgUp/PgDn", "水平翻页"),
            ("Ctrl+↑ / Ctrl+↓", "调整日志区字号"),
            ("Ctrl+滚轮", "调整日志区字号"),
            ("Shift+滚轮", "水平滚动"),
        ]
        for key, desc in _refs:
            ref_h = QHBoxLayout()
            ref_h.setContentsMargins(4, 1, 0, 1)
            ref_h.setSpacing(8)
            lbl_k = QLabel(key)
            lbl_k.setFixedWidth(130)
            lbl_k.setStyleSheet(_ref_ss)
            ref_h.addWidget(lbl_k)
            lbl_d = QLabel(desc)
            lbl_d.setStyleSheet(
                "font-size:11px;color:#9ca3af;"
                "background:transparent;"
            )
            ref_h.addWidget(lbl_d, stretch=1)
            v.addLayout(ref_h)
        v.addStretch(1)
        return page

    # ★ v0.69: 内置快捷键表（keyPressEvent 实现，不可修改）
    _BUILTIN_SHORTCUTS = {
        "Home": "跳到文档开头",
        "End": "跳到最后一行",
        "PgUp": "垂直翻页",
        "PgDown": "垂直翻页",
        "Shift+PgUp": "水平翻页",
        "Shift+PgDown": "水平翻页",
        "Ctrl+Up": "调整字号",
        "Ctrl+Down": "调整字号",
    }

    def _on_shortcut_changed(self):
        """冲突检测：自定义行互相重复 + 内置快捷键冲突"""
        rows = [
            self._sc_close_tab,
            self._sc_goto_line,
            self._sc_send,
        ]
        vals = [r.value() for r in rows]
        builtin = self._BUILTIN_SHORTCUTS
        for i, row in enumerate(rows):
            v = vals[i]
            if not v:
                row.set_conflict("")
                continue
            # 1) 检查与其他自定义行重复
            dup = any(
                vals[j] == v and j != i
                for j in range(len(rows))
                if vals[j]
            )
            if dup:
                row.set_conflict("与其他快捷键重复")
                continue
            # 2) 检查内置快捷键
            if v in builtin:
                row.set_conflict(
                    f"内置: {builtin[v]}"
                )
                continue
            row.set_conflict("")
        self._auto_save()

    def _build_other_page(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 20, 0)
        v.setSpacing(10)
        self._chk_confirm_clear = QCheckBox(
            "清空日志时显示确认提示"
        )
        self._chk_confirm_clear.setStyleSheet(_CHK_SS)
        self._chk_confirm_clear.setChecked(
            self._config.get("ui", {}).get(
                "confirm_clear", True
            )
        )
        self._chk_confirm_clear.toggled.connect(
            self._auto_save
        )
        v.addWidget(self._chk_confirm_clear)
        self._chk_confirm_close_tab = QCheckBox(
            "关闭 Tab 时显示确认提示"
        )
        self._chk_confirm_close_tab.setStyleSheet(
            _CHK_SS
        )
        self._chk_confirm_close_tab.setChecked(
            self._config.get("ui", {}).get(
                "confirm_close_tab", True
            )
        )
        self._chk_confirm_close_tab.toggled.connect(
            self._auto_save
        )
        v.addWidget(self._chk_confirm_close_tab)
        v.addStretch(1)
        return page

    def _on_nav(self, idx):
        self._stack.setCurrentIndex(idx)
        if idx == 1:
            self._update_hl_body_size()

    def _on_hl_enabled(self, checked):
        self._hl_body.setEnabled(checked)
        self._on_hl_changed()

    def _toggle_bi_all(self, checked):
        """★ [16] 全选/全不选内置规则"""
        for row in self._builtin_rows:
            row._chk.blockSignals(True)
            row._chk.setChecked(checked)
            row._chk.blockSignals(False)
        self._on_hl_changed()

    def _toggle_cu_all(self, checked):
        """★ 全选/全不选自定义规则"""
        for row in self._custom_list._rows:
            row._chk.blockSignals(True)
            row._chk.setChecked(checked)
            row._chk.blockSignals(False)
        self._on_hl_changed()

    def _add_user_rule(self):
        self._custom_list.add_rule()
        self._update_hl_body_size()

    def _show_help(self, btn, text, width=280):
        """显示帮助弹窗 — 居中，外围置灰"""
        popup = _HelpPopup(text, self, width=width)
        popup.exec()

    def _fs_value(self):
        try:
            v = int(self._fs_edit.text())
            return max(8, min(30, v))
        except ValueError:
            return 12

    def _fs_set_value(self, v):
        self._fs_edit.setText(
            str(max(8, min(30, v)))
        )

    def _fs_dec(self):
        self._fs_set_value(self._fs_value() - 1)
        self._on_fs_changed()

    def _fs_inc(self):
        self._fs_set_value(self._fs_value() + 1)
        self._on_fs_changed()

    def _fs_edited(self):
        self._fs_set_value(self._fs_value())
        self._on_fs_changed()

    def _on_fs_changed(self):
        """★ v0.6 fix: 字号变化专用通路 — 不触发 highlight_changed"""
        self._refresh_preview()
        self._auto_save()
        self.font_size_changed.emit(self._fs_value())

    def _on_wrap_changed(self, checked):
        """★ v0.6: 自动换行开关 — 不触发 rehighlight"""
        self._auto_save()
        self.word_wrap_changed.emit(checked)

    def _on_line_numbers_changed(self, checked):
        """★ v0.69: 行号显示开关"""
        self._auto_save()
        self.show_line_numbers_changed.emit(checked)

    def _on_unlimited_toggled(self, checked):
        """★ v0.61: 无限制勾选 — 禁用 spinbox 并 emit 0"""
        self._max_lines_spin.setEnabled(not checked)
        self._auto_save()
        self.max_lines_changed.emit(
            0 if checked
            else self._max_lines_spin.value()
        )

    def _on_max_lines_changed(self, value):
        """★ v0.6: 行数上限变更 — 不触发 rehighlight"""
        self._auto_save()
        self.max_lines_changed.emit(value)

    def _on_hl_changed(self, _=""):
        """★ 接受可选 str 参数（color_changed Signal(str) 会传值）"""
        self._build_hl_config()
        self._refresh_preview()
        self._auto_save()
        # ★ v0.6 fix: 不再实时 emit highlight_changed
        #   设置弹窗是全屏遮罩，用户看不到背后日志区，
        #   实时 rehighlight 全部 Tab 毫无意义且造成卡顿。
        #   关闭设置时 _open_settings 已有 refresh_highlighter 兜底。

    def _update_hl_body_size(self):
        """强制内容最小高度跟随内容，让 hl_scroll 出现滚动条"""
        self._custom_list.layout().activate()
        self._hl_body.layout().activate()
        self._hl_content.layout().activate()
        h = self._hl_content.layout().sizeHint().height()
        min_h = self._hl_content.layout().minimumSize().height()
        self._hl_content.setMinimumHeight(max(h, min_h))

    def _on_hl_sticky(self, value):
        """高亮页：checkbox 滚出视口时显示 sticky 覆盖"""
        chk_y = self._chk_hl_enabled.geometry().y()
        chk_h = self._chk_hl_enabled.height()
        sticky_h = chk_h + 8
        if value > chk_y + chk_h + 4:
            vp_w = self._hl_scroll.viewport().width()
            self._sticky_hl.setGeometry(0, 0, vp_w, sticky_h)
            self._sticky_hl.raise_()
            self._sticky_hl.show()
        else:
            self._sticky_hl.hide()

    def _on_log_sticky(self, value):
        """日志页：checkbox 滚出视口时显示 sticky 覆盖"""
        chk_h = self._chk_enabled.height() + 8
        if value > chk_h:
            vp_w = self._log_scroll.viewport().width()
            self._sticky_log.setGeometry(0, 0, vp_w, chk_h)
            self._sticky_log.raise_()
            self._sticky_log.show()
        else:
            self._sticky_log.hide()

    def _refresh_preview(self):
        cfg = self._build_hl_config()
        self._preview_hl.load_config(
            {"highlight": cfg}
        )

    def _build_hl_config(self):
        cfg = {
            "enabled": self._chk_hl_enabled.isChecked(),
            "default_fg": self._default_fg_btn.color(),
            "font_size": self._fs_value(),
            "word_wrap": self._chk_wrap.isChecked(),
            "max_lines": (
                0 if self._chk_unlimited.isChecked()
                else self._max_lines_spin.value()
            ),
            "show_line_numbers": self._chk_line_numbers.isChecked(),
            "builtin_rules": {},
            "user_rules": [],
        }
        for row in self._builtin_rows:
            cfg["builtin_rules"][row.rule_id()] = (
                row.get_config()
            )
        cfg["user_rules"] = (
            self._custom_list.get_all()
        )
        return cfg

    def _load(self):
        log_cfg = self._config.get("logging", {})
        self._chk_enabled.setChecked(
            log_cfg.get("enabled", False)
        )
        root = log_cfg.get("root_dir", "")
        self._lbl_dir.setText(root)
        self._lbl_dir.setCursorPosition(0)
        if log_cfg.get("file_format", ".log") == ".txt":
            self._radio_txt.setChecked(True)
        else:
            self._radio_log.setChecked(True)
        # ★ v0.45: 全选独立控制
        self._record_all = log_cfg.get("record_all_tabs", True)
        self._chk_select_all.blockSignals(True)
        self._chk_select_all.setChecked(self._record_all)
        self._chk_select_all.blockSignals(False)
        if self._record_all:
            for chk in self._tab_checks:
                chk.blockSignals(True)
                chk.setChecked(True)
                chk.blockSignals(False)
        else:
            selected = log_cfg.get("selected_tabs", [])
            for chk in self._tab_checks:
                chk.blockSignals(True)
                chk.setChecked(chk.text() in selected)
                chk.blockSignals(False)
        # ★ v0.5: 加载高亮配置
        hl_cfg = self._config.get("highlight", {})
        self._chk_hl_enabled.setChecked(
            hl_cfg.get("enabled", True)
        )
        self._fs_set_value(
            hl_cfg.get("font_size", 12)
        )
        for ur in hl_cfg.get("user_rules", []):
            self._custom_list.add_rule(ur)
        _ml = hl_cfg.get("max_lines", 5000)
        self._chk_unlimited.blockSignals(True)
        self._max_lines_spin.blockSignals(True)
        if _ml == 0:
            self._chk_unlimited.setChecked(True)
            self._max_lines_spin.setEnabled(False)
        else:
            self._chk_unlimited.setChecked(False)
            self._max_lines_spin.setEnabled(True)
            self._max_lines_spin.setValue(_ml)
        self._chk_unlimited.blockSignals(False)
        self._max_lines_spin.blockSignals(False)
        # ★ 其他设置
        self._chk_confirm_clear.blockSignals(True)
        self._chk_confirm_clear.setChecked(
            self._config.get("ui", {}).get(
                "confirm_clear", True
            )
        )
        self._chk_confirm_clear.blockSignals(False)
        self._chk_confirm_close_tab.blockSignals(True)
        self._chk_confirm_close_tab.setChecked(
            self._config.get("ui", {}).get(
                "confirm_close_tab", True
            )
        )
        self._chk_confirm_close_tab.blockSignals(False)
        # ★ v0.63: 快捷键设置
        sc_cfg = self._config.get("shortcuts", {})
        self._sc_close_tab.set_value(
            sc_cfg.get("close_tab", "Ctrl+W")
        )
        self._sc_goto_line.set_value(
            sc_cfg.get("goto_line", "Ctrl+G")
        )
        self._sc_send.set_value(
            sc_cfg.get("send", "Ctrl+Return")
        )

    def _write_to_config(self):
        if "logging" not in self._config:
            self._config["logging"] = {}
        c = self._config["logging"]
        c["enabled"] = self._chk_enabled.isChecked()
        txt = self._lbl_dir.text()
        c["root_dir"] = txt.strip()
        c["file_format"] = (
            ".txt"
            if self._radio_txt.isChecked()
            else ".log"
        )
        c["record_all_tabs"] = self._record_all
        c["selected_tabs"] = [
            chk.text()
            for chk in self._tab_checks
            if chk.isChecked()
        ]
        self._config.setdefault("ui", {})[
            "confirm_clear"
        ] = self._chk_confirm_clear.isChecked()
        self._config.setdefault("ui", {})[
            "confirm_close_tab"
        ] = self._chk_confirm_close_tab.isChecked()
        self._config["highlight"] = (
            self._build_hl_config()
        )
        # ★ v0.63: 快捷键配置
        self._config.setdefault("shortcuts", {}).update({
            "close_tab": self._sc_close_tab.value(),
            "goto_line": self._sc_goto_line.value(),
            "send": self._sc_send.value(),
        })

    def closeEvent(self, event):
        """★ v0.6: Windows 任务栏右键关闭 → reject 退出对话框"""
        self.reject()
        event.accept()

    def _reset(self):
        idx = self._stack.currentIndex()
        if idx == 0:
            # ★ 日志页重置
            self._config["logging"] = {
                "enabled": False,
                "root_dir": "",
                "file_format": ".log",
                "record_all_tabs": True,
                "selected_tabs": [],
            }
            save_config(self._config)
            self._record_all = True
            self._chk_enabled.setChecked(False)
            self._lbl_dir.setText("")
            self._radio_log.setChecked(True)
            self._chk_select_all.setChecked(True)
        elif idx == 1:
            # ★ 字体页重置
            self._chk_hl_enabled.setChecked(True)
            self._fs_set_value(12)
            self._default_fg_btn.set_color("#1e293b")
            self._bi_chk_all.blockSignals(True)
            self._bi_chk_all.setChecked(True)
            self._bi_chk_all.blockSignals(False)
            for row in self._builtin_rows:
                row.reset()
            self._custom_list.clear_all()
            self._chk_unlimited.blockSignals(True)
            self._chk_unlimited.setChecked(False)
            self._chk_unlimited.blockSignals(False)
            self._max_lines_spin.setEnabled(True)
            self._max_lines_spin.blockSignals(True)
            self._max_lines_spin.setValue(5000)
            self._max_lines_spin.blockSignals(False)
            self._chk_line_numbers.blockSignals(True)
            self._chk_line_numbers.setChecked(True)
            self._chk_line_numbers.blockSignals(False)
            self._on_hl_changed()
        elif idx == 2:
            self._chk_confirm_clear.setChecked(True)
            self._chk_confirm_close_tab.setChecked(True)
            self._auto_save()
        elif idx == 3:
            self._sc_close_tab.set_value("Ctrl+W")
            self._sc_goto_line.set_value("Ctrl+G")
            self._sc_send.set_value("Ctrl+Return")
            self._on_shortcut_changed()