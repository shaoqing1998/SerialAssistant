"""
settings_dialog.py - 通用设置弹窗（全屏遮罩 + 居中面板）
v0.5 — ★ 新增「高亮」设置页（预览行 + 内置规则 + 自定义规则）
       ★ 拖动排序 + Ctrl 多选 + 右键批量修改颜色
       ★ ColorPickerPopup 色板弹窗集成

最近更改 (2026-03-21):
  [1] _BuiltinRuleRow: 新增 self._cs = QCheckBox("Aa") 区分大小写选项
      → get_config() 输出 case_sensitive, reset() 重置为 False
      → override 加载 case_sensitive
  [2] _CustomRuleRow: 新增 self._cs = QCheckBox("Aa") 区分大小写选项
      → get_data() 输出 case_sensitive, 构造函数加载 case_sensitive
  [3] changed Signal 连接统一用 lambda _: self.changed.emit()
  [4] 默认字体颜色 default_fg 色块按钮 + _build_hl_config 输出 default_fg
  [5] 双击内置规则名称 → 就地显示正则, 点击任意位置还原
  [6] _BuiltinRuleRow: 所有规则统一添加背景色按钮（无默认bg用#ffffff）
  [7] _build_highlight_page: 内置规则上方添加表头行（启用/名称/Aa/字色/背景）
  [8] 删除设置窗内所有 QToolTip（规避 WA_TranslucentBackground 导致黑色 tooltip 问题）
  [9] 双击显示正则时 setWordWrap(True) + 解除固定高度，还原时恢复 fixedHeight(28)
  [10] _CustomRuleRow 重写：统一风格（QWidget/28px/6px 边距），隐藏拖动图标保留功能，
      所有 QLineEdit/QTextEdit 选中文字改为蓝底(#2563eb)白字(#fff)
  [11] 自定义规则视觉修复：添加表头行，容器随行数撑大（无滚动条），
      移除 grip 让复选框顶头对齐
  [12] 撤回 _BuiltinRuleRow 误加的 _rx_sp/_del_sp 占位符和表头多余列
  [13] 修复内置规则容器高度被挤压：bi_container 加 minHeight=130，PANEL_H 480→560
  [14] 对齐内置/自定义规则列：Aa 列统一 fixedWidth=38
  [15] (撤回) 恢复 _rx(".*") 正则切换 + 表头"正则"列(fixedWidth=32)
  [17] 撤回内置规则行末 _end_sp(16px) 及表头 hdr_end — 不改内置规则布局
  [16] 内置规则表头加全选框（默认勾选），批量启用/禁用全部内置规则
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QPushButton, QFileDialog, QWidget,
    QRadioButton, QScrollArea, QFrame, QStackedWidget,
    QButtonGroup, QLineEdit, QTextEdit, QMenu,
    QApplication, QScrollBar,
)
from PySide6.QtCore import (
    Qt, QPoint, QPointF, QRectF, Signal, QEvent,
)
from PySide6.QtGui import (
    QPainter, QPainterPath, QColor, QPen,
    QRegion, QPixmap, QCursor,
)
from PySide6.QtSvg import QSvgRenderer
from config import save_config
from highlight_engine import (
    BUILTIN_RULES, PREVIEW_TEXT, LogHighlighter,
    auto_fg, lum,
)
from color_picker import ColorPickerPopup

PANEL_W = 520
PANEL_H = 560
RADIUS = 10
BORDER_COLOR = QColor("#b0b8c4")
BG_COLOR = QColor("#ffffff")
OVERLAY_COLOR = QColor(0, 0, 0, 80)

_CHK_SS = (
    "QCheckBox { font-size: 13px; background: transparent;"
    "  spacing: 5px; }"
    "QCheckBox::indicator {"
    "  width: 12px; height: 12px;"
    "  margin: 2px; }"
    "QCheckBox::indicator:unchecked {"
    "  border: 1px solid #9ca3af;"
    "  border-radius: 3px; background: #ffffff; }"
    "QCheckBox::indicator:checked {"
    "  border: 1px solid #2563eb;"
    "  border-radius: 3px; background: #2563eb; }"
    "QCheckBox::indicator:hover {"
    "  border-color: #3b82f6; }"
    "QCheckBox:disabled { color: #c0c0c0; }"
    "QCheckBox::indicator:disabled {"
    "  border-color: #d1d5db;"
    "  background: #f0f0f0; }"
    "QCheckBox::indicator:checked:disabled {"
    "  border-color: #93b4f0;"
    "  background: #93b4f0; }"
)

_RADIO_SS = (
    "QRadioButton { font-size: 13px;"
    "  background: transparent; spacing: 4px; }"
    "QRadioButton::indicator {"
    "  width: 10px; height: 10px;"
    "  margin: 2px; }"
    "QRadioButton::indicator:unchecked {"
    "  border: 1px solid #9ca3af;"
    "  border-radius: 5px;"
    "  background: #ffffff; }"
    "QRadioButton::indicator:checked {"
    "  border: 1px solid #2563eb;"
    "  border-radius: 5px;"
    "  background: #2563eb; }"
    "QRadioButton::indicator:hover {"
    "  border-color: #3b82f6; }"
    "QRadioButton:disabled { color: #c0c0c0; }"
    "QRadioButton::indicator:disabled {"
    "  border-color: #d1d5db;"
    "  background: #f0f0f0; }"
)

# ★ v0.45: 圆角滚动容器（叠加层边框，保证四边统一）
class _BorderOverlay(QWidget):
    """透明叠加层 — 在所有子控件之上绘制边框"""

    def __init__(self, parent, radius=6):
        super().__init__(parent)
        self._radius = radius
        self._border_color = QColor("#d1d5db")
        # ★ 不拦截鼠标事件，保证下层可点击
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, True
        )

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # ★ 1.5px pen — 更粗更均匀
        r = QRectF(self.rect()).adjusted(0.75, 0.75, -0.75, -0.75)
        p.setPen(QPen(self._border_color, 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r, self._radius, self._radius)
        p.end()


class _RoundedScrollContainer(QWidget):
    """圆角滚动容器 — 背景在底层，边框在叠加层（保证四边统一）"""

    def __init__(self, scroll_area: QScrollArea, parent=None):
        super().__init__(parent)
        self._scroll = scroll_area
        self._radius = 6
        self._bg_color = QColor("#ffffff")
        # 内嵌 QScrollArea，去掉自身边框
        self._scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            "QScrollBar:vertical {"
            "  width: 4px; background: transparent; }"
            "QScrollBar::handle:vertical {"
            "  background: #d1d5db;"
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
        # ★ 叠加层：在所有子控件之上绘制边框
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
        # ★ 只画背景，边框由 overlay 负责
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        bg_path = QPainterPath()
        bg_path.addRoundedRect(r, self._radius, self._radius)
        p.fillPath(bg_path, self._bg_color)
        p.end()


# ★ v0.45: 可切换列表项（圆形指示器替代 QCheckBox）
class _TagChip(QWidget):
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

    def text(self):
        return self._text

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        if self._checked == checked:
            return
        self._checked = checked
        self.update()
        self.toggled.emit(checked)

    def enterEvent(self, e):
        self._hovered = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self.update()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if not self.isEnabled():
            return
        if e.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        h = self.height()
        w = self.width()
        # ★ disabled 状态：灰色文字，不画指示器
        if not self.isEnabled():
            font = p.font()
            font.setPixelSize(12)
            p.setFont(font)
            p.setPen(QColor("#c0c0c0"))
            p.drawText(
                QRectF(16.0, 0, w - 16.0, h),
                Qt.AlignmentFlag.AlignVCenter
                | Qt.AlignmentFlag.AlignLeft,
                self._text,
            )
            p.end()
            return
        if self._checked:
            # ★ 选中：浅蓝底 + 左侧蓝色竖线
            bg_path = QPainterPath()
            bg_path.addRoundedRect(QRectF(0, 0, w, h), 4, 4)
            p.fillPath(bg_path, QColor("#ffffff"))
            bar_h = 14.0
            bar_y = (h - bar_h) / 2.0
            bar_path = QPainterPath()
            bar_path.addRoundedRect(
                QRectF(4, bar_y, 2.5, bar_h), 1.2, 1.2
            )
            p.fillPath(bar_path, QColor("#2563eb"))
            fg = QColor("#2563eb")
        else:
            # ★ 未选中：hover 时浅灰底，否则透明
            if self._hovered:
                hover_path = QPainterPath()
                hover_path.addRoundedRect(
                    QRectF(0, 0, w, h), 4, 4
                )
                p.fillPath(hover_path, QColor("#f9fafb"))
            fg = QColor("#6b7280")
        # ★ 文字
        font = p.font()
        font.setPixelSize(12)
        p.setFont(font)
        p.setPen(fg)
        text_x = 16.0
        p.drawText(
            QRectF(text_x, 0, w - text_x, h),
            Qt.AlignmentFlag.AlignVCenter
            | Qt.AlignmentFlag.AlignLeft,
            self._text,
        )
        p.end()


# ★ 齿轮 SVG（与 title_bar.py 一致）
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
    """渲染小齿轮图标用于设置标题栏"""
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


# ═══════════════════════════════════════════
# ★ 关闭按钮（与主窗口 close 按钮完全一致的绘制风格）
# ═══════════════════════════════════════════
class _CloseBtn(QWidget):
    """Notion 风格关闭按钮 — 灰色×号 + hover浅灰背景，无红色"""
    clicked = Signal()

    def __init__(self, corner_radius=0, parent=None):
        super().__init__(parent)
        self.setFixedSize(28, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
        self._hovered = False
        self._pressed = False

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
        if e.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self.update()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        was_pressed = self._pressed
        self._pressed = False
        self.update()
        if was_pressed and e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(e)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # ★ Notion 风格：hover 小圆圈背景
        if self._pressed or self._hovered:
            bg = QColor("#d2d2d2") if self._pressed else QColor("#e8e8e8")
            cx, cy = self.width() / 2, self.height() / 2
            radius = 11  # 小圆圈半径
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(bg)
            p.drawEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))
        # ★ × 号
        if self._pressed:
            fg = QColor("#3c4043")
        elif self._hovered:
            fg = QColor("#5f6368")
        else:
            fg = QColor("#868686")
        pen = QPen(fg, 1.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        cx, cy = self.width() / 2.0, self.height() / 2.0
        d = 3.5
        p.drawLine(
            QPointF(cx - d, cy - d),
            QPointF(cx + d, cy + d),
        )
        p.drawLine(
            QPointF(cx + d, cy - d),
            QPointF(cx - d, cy + d),
        )
        p.end()


# ═══════════════════════════════════════════
# 左侧导航按钮
# ═══════════════════════════════════════════
class _NavBtn(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setFixedHeight(34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            "QPushButton { background: transparent; border: none;"
            "  border-radius: 6px; text-align: left;"
            "  padding: 0 12px; font-size: 13px; color: #374151; }"
            "QPushButton:checked { background: #e0e7ff; color: #2563eb;"
            "  font-weight: 600; }"
            "QPushButton:hover:!checked { background: #f3f4f6; }"
        )


# ═══════════════════════════════════════════
# 重置按钮
# ═══════════════════════════════════════════
class _ResetBtn(QPushButton):
    """v0.45 — 无边框设计，hover/pressed 时才显示边框"""

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
        self._hovered = True
        self._apply_style()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self._pressed = False
        self._apply_style()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        self._pressed = True
        self._apply_style()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._pressed = False
        self._apply_style()
        super().mouseReleaseEvent(e)

    def _apply_style(self):
        if self._pressed:
            self.setStyleSheet(
                "QPushButton { background: #fecaca;"
                "  border: none;"
                "  border-radius: 6px;"
                "  font-size: 13px; color: #b91c1c; }"
            )
        elif self._hovered:
            self.setStyleSheet(
                "QPushButton { background: #fee2e2;"
                "  border: none;"
                "  border-radius: 6px;"
                "  font-size: 13px; color: #dc2626; }"
            )
        else:
            self.setStyleSheet(
                "QPushButton { background: transparent;"
                "  border: none;"
                "  border-radius: 6px;"
                "  font-size: 13px; color: #6b7280; }"
            )


# ═══════════════════════════════════════════
# ★ 齿轮图标 Label（用于设置标题栏左侧）
# ═══════════════════════════════════════════
class _GearIconLabel(QLabel):
    """在标题栏左侧显示齿轮图标"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        gear = _render_mini_gear("#6b7280", 14)
        dpr = gear.devicePixelRatio()
        lw = int(gear.width() / dpr)
        lh = int(gear.height() / dpr)
        x = (self.width() - lw) // 2
        y = (self.height() - lh) // 2
        p.drawPixmap(x, y, gear)
        p.end()


# ═══════════════════════════════════════════
# ★ v0.5 新增：色块按钮（用于规则行的颜色选择）
# ═══════════════════════════════════════════
class _ColorBtn(QWidget):
    color_changed = Signal(str)

    def __init__(self, color="#cccccc", parent=None):
        super().__init__(parent)
        self._color = color
        self._hovered = False
        self.setFixedSize(22, 16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)

    def color(self):
        return self._color

    def set_color(self, c):
        self._color = c
        self.update()

    def enterEvent(self, e):
        self._hovered = True
        self.update()

    def leaveEvent(self, e):
        self._hovered = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            dlg = ColorPickerPopup(self._color, self.window())
            dlg.color_chosen.connect(self._on_pick)
            pos = self.mapToGlobal(QPoint(0, self.height() + 2))
            dlg.move(pos)
            dlg.exec()

    def _on_pick(self, c):
        self._color = c
        self.update()
        self.color_changed.emit(c)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        path = QPainterPath()
        path.addRoundedRect(r, 3, 3)
        p.fillPath(path, QColor(self._color))
        pen_c = "#9ca3af" if self._hovered else "#d1d5db"
        p.setPen(QPen(QColor(pen_c), 1.0))
        p.drawRoundedRect(r, 3, 3)
        p.end()


# ═══════════════════════════════════════════
# ★ v0.5 新增：内置规则行
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
        self._cs.setStyleSheet(
            "QCheckBox{font-size:11px;"
            "font-family:Consolas,monospace;"
            "background:transparent;spacing:3px}"
            "QCheckBox::indicator{width:12px;height:12px;margin:2px}"
            "QCheckBox::indicator:unchecked{"
            "border:1px solid #9ca3af;border-radius:3px;background:#fff}"
            "QCheckBox::indicator:checked{"
            "border:1px solid #2563eb;border-radius:3px;background:#2563eb}"
            "QCheckBox::indicator:hover{border-color:#3b82f6}"
        )
        self._cs.setFixedWidth(38)
        self._cs.toggled.connect(lambda _: self.changed.emit())
        h.addWidget(self._cs)
        self._fg_btn = _ColorBtn(rule["fg"])
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
        self._style_lbl()
        self.changed.emit()

    def _style_lbl(self):
        fg = self._fg_btn.color()
        bg = self._bg_btn.color()
        has_bg = bg and bg.lower() != "#ffffff"
        if has_bg:
            self._lbl.setStyleSheet(
                f"font-size:12px;color:#1f2937;"
                f"background:{bg};border-radius:3px;padding:1px 4px;"
            )
        else:
            self._lbl.setStyleSheet(
                f"font-size:12px;color:{fg};background:transparent;"
            )

    def rule_id(self):
        return self._id

    def get_config(self):
        bg = self._bg_btn.color() or "#ffffff"
        d = {
            "enabled": self._chk.isChecked(),
            "case_sensitive": self._cs.isChecked(),
            "fg": self._fg_btn.color(),
            "bg": bg if bg.lower() != "#ffffff" else None,
        }
        return d

    def reset(self):
        # ★ bracket 规则默认不勾选，其余默认勾选
        default_on = (self._id != "bracket")
        self._chk.setChecked(default_on)
        self._cs.setChecked(False)
        self._fg_btn.set_color(self._default_fg)
        self._bg_btn.set_color(self._default_bg or "#ffffff")
        self._style_lbl()

    def mouseDoubleClickEvent(self, event):
        """双击：名称 ↔ 正则 就地切换，点击任意位置还原"""
        if self._showing_pattern:
            return
        self._showing_pattern = True
        self._lbl.setWordWrap(True)
        self.setMinimumHeight(28)
        self.setMaximumHeight(16777215)
        self._lbl.setText(self._pattern)
        self._lbl.setStyleSheet(
            "font-family:Consolas,monospace;"
            "font-size:11px;color:#6b7280;"
            "background:#f3f4f6;border-radius:3px;"
            "padding:1px 4px;"
        )
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        """监听全局点击，还原名称显示"""
        if (
            self._showing_pattern
            and event.type() == QEvent.Type.MouseButtonPress
        ):
            self._showing_pattern = False
            self._lbl.setWordWrap(False)
            self.setFixedHeight(28)
            QApplication.instance().removeEventFilter(self)
            self._lbl.setText(
                next(
                    r["name"]
                    for r in BUILTIN_RULES
                    if r["id"] == self._id
                )
            )
            self._style_lbl()
        return super().eventFilter(obj, event)


# ═══════════════════════════════════════════
# ★ 圆形 hover 按钮（paintEvent 绘制，不依赖 stylesheet）
# ═══════════════════════════════════════════
class _CircleBtn(QWidget):
    """用 paintEvent + drawEllipse 绘制圆形 hover 背景，彻底解决 stylesheet 圆角失效"""
    clicked = Signal()

    def __init__(self, text, size=22, parent=None):
        super().__init__(parent)
        self._text = text
        self._hovered = False
        self._pressed = False
        self._fg = "#9ca3af"
        self._fg_hover = "#374151"
        self._fg_pressed = "#1f2937"
        self._bg_hover = "#f3f4f6"
        self._bg_pressed = "#e5e7eb"
        self._font_size = 16
        self._font_weight = 700
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)

    def enterEvent(self, e):
        self._hovered = True
        self.update()

    def leaveEvent(self, e):
        self._hovered = False
        self._pressed = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self.update()

    def mouseReleaseEvent(self, e):
        was = self._pressed
        self._pressed = False
        self.update()
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
            Qt.AlignmentFlag.AlignCenter,
            self._text,
        )
        p.end()


# ═══════════════════════════════════════════
# ★ v0.5 新增：自定义规则行
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
        self._kw.setFixedHeight(20)
        self._kw.setStyleSheet(
            "QLineEdit{font-size:12px;color:#374151;"
            "background:#fff;border:1px solid #d1d5db;"
            "border-radius:4px;padding:0 4px;"
            "selection-background-color:#2563eb;"
            "selection-color:#ffffff}"
            "QLineEdit:focus{border-color:#3b82f6}"
        )
        self._kw.textChanged.connect(lambda _: self.changed.emit())
        h.addWidget(self._kw, stretch=1)
        self._rx = QCheckBox(".*")
        self._rx.setStyleSheet(
            "QCheckBox{font-size:11px;"
            "font-family:Consolas,monospace;"
            "background:transparent;spacing:3px}"
            "QCheckBox::indicator{width:12px;height:12px;margin:2px}"
            "QCheckBox::indicator:unchecked{"
            "border:1px solid #9ca3af;border-radius:3px;background:#fff}"
            "QCheckBox::indicator:checked{"
            "border:1px solid #2563eb;border-radius:3px;background:#2563eb}"
            "QCheckBox::indicator:hover{border-color:#3b82f6}"
        )
        self._rx.setFixedWidth(32)
        self._rx.toggled.connect(lambda _: self.changed.emit())
        h.addWidget(self._rx)
        self._cs = QCheckBox("Aa")
        self._cs.setStyleSheet(
            "QCheckBox{font-size:11px;"
            "font-family:Consolas,monospace;"
            "background:transparent;spacing:3px}"
            "QCheckBox::indicator{width:12px;height:12px;margin:2px}"
            "QCheckBox::indicator:unchecked{"
            "border:1px solid #9ca3af;border-radius:3px;background:#fff}"
            "QCheckBox::indicator:checked{"
            "border:1px solid #2563eb;border-radius:3px;background:#2563eb}"
            "QCheckBox::indicator:hover{border-color:#3b82f6}"
        )
        self._cs.setFixedWidth(38)
        self._cs.toggled.connect(lambda _: self.changed.emit())
        h.addWidget(self._cs)
        fg = (data or {}).get("fg", "#374151")
        self._fg = _ColorBtn(fg)
        self._fg.color_changed.connect(self.changed.emit)
        h.addWidget(self._fg)
        bg = (data or {}).get("bg") or "#ffffff"
        self._bg = _ColorBtn(bg)
        self._bg.color_changed.connect(self.changed.emit)
        h.addWidget(self._bg)
        d = _CircleBtn("\u00d7", size=20)
        d._fg = "#d1d5db"
        d._fg_hover = "#dc2626"
        d._fg_pressed = "#b91c1c"
        d._bg_hover = "#fee2e2"
        d._bg_pressed = "#fca5a5"
        d._font_size = 14
        d.clicked.connect(lambda: self.delete_me.emit(self))
        h.addWidget(d)
        if data:
            self._chk.setChecked(data.get("enabled", True))
            self._kw.setText(data.get("keyword", ""))
            self._rx.setChecked(data.get("is_regex", False))
            self._cs.setChecked(data.get("case_sensitive", False))

    def mousePressEvent(self, event):
        """★ [11] 点击行空白区域发起拖动（Ctrl+点击多选）"""
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

    def set_selected(self, s):
        self._selected = s
        self.update()

    def is_selected(self):
        return self._selected

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

    def set_fg(self, c):
        self._fg.set_color(c)

    def set_bg(self, c):
        self._bg.set_color(c)

    def paintEvent(self, event):
        if self._selected:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            path = QPainterPath()
            path.addRoundedRect(QRectF(self.rect()), 4, 4)
            p.fillPath(path, QColor("#eff6ff"))
            p.end()
        super().paintEvent(event)


# ═══════════════════════════════════════════
# ★ v0.5 新增：自定义规则列表（拖动排序 + 多选 + 右键批量）
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
        """根据行数动态调整自身最小高度，让父容器跟着撑大"""
        n = len(self._rows)
        self.setMinimumHeight(max(0, n * 30))  # 28px row + 2px spacing
        self.updateGeometry()  # 通知父布局重新计算

    def add_rule(self, data=None):
        if len(self._rows) >= 200:
            return
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
        if self._drag_row is None:
            return False
        if event.type() == QEvent.Type.MouseMove:
            local = self.mapFromGlobal(QCursor.pos())
            self._move(local.y())
            return True
        if event.type() == QEvent.Type.MouseButtonRelease:
            self._end_drag()
            return True
        return False

    def _move(self, y):
        di = self._rows.index(self._drag_row)
        for i, r in enumerate(self._rows):
            if r is self._drag_row:
                continue
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
        if not sel:
            return
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu{background:#fff;border:1px solid #d1d5db;"
            "border-radius:6px;padding:4px}"
            "QMenu::item{padding:4px 16px;font-size:12px;"
            "border-radius:4px}"
            "QMenu::item:selected{background:#eff6ff;color:#2563eb}"
        )
        a_fg = menu.addAction(f"修改字体颜色（{len(sel)}条）")
        a_bg = menu.addAction(f"修改背景颜色（{len(sel)}条）")
        act = menu.exec(self.mapToGlobal(pos))
        if act == a_fg:
            dlg = ColorPickerPopup(
                sel[0].get_data()["fg"], self.window()
            )
            if dlg.exec():
                for r in sel:
                    r.set_fg(dlg.get_color())
                self.changed.emit()
        elif act == a_bg:
            bg0 = sel[0].get_data().get("bg") or "#ffffff"
            dlg = ColorPickerPopup(bg0, self.window())
            if dlg.exec():
                for r in sel:
                    r.set_bg(dlg.get_color())
                self.changed.emit()

    def get_all(self):
        return [r.get_data() for r in self._rows]

    def clear_all(self):
        for r in list(self._rows):
            self._del(r)

    def clear_selection(self):
        for r in self._rows:
            r.set_selected(False)


# ═══════════════════════════════════════════
# ★ 带三角箭头的自定义滚动条
# ═══════════════════════════════════════════
class _ArrowScrollBar(QScrollBar):
    """竖向滚动条 — 顶/底绘制三角箭头指示器"""

    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Vertical, parent)
        self.setStyleSheet(
            "QScrollBar:vertical{"
            "  width:8px;background:transparent;"
            "  margin:12px 0 12px 0}"
            "QScrollBar::handle:vertical{"
            "  background:#d1d5db;border-radius:3px;min-height:20px}"
            "QScrollBar::handle:vertical:hover{background:#3b82f6}"
            "QScrollBar::sub-line:vertical{height:10px;background:transparent}"
            "QScrollBar::add-line:vertical{height:10px;background:transparent}"
            "QScrollBar::add-page,QScrollBar::sub-page{background:transparent}"
        )

    def paintEvent(self, event):
        if self.maximum() <= 0:
            return  # 无需滚动时完全隐藏整个滚动条（保留占位）
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#b0b8c4"))
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


# ═══════════════════════════════════════════
# 主设置弹窗（全屏遮罩模式）
# ═══════════════════════════════════════════
class SettingsDialog(QDialog):
    highlight_changed = Signal()

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
        self._btn_close = _CloseBtn(corner_radius=RADIUS)
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
        content_v.setContentsMargins(16, 4, 8, 14)
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
        btn_hl = _NavBtn("高亮")
        self._nav_group.addButton(btn_hl, 1)
        nav_v.addWidget(btn_hl)
        nav_v.addStretch(1)
        body_h.addWidget(nav_w)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_log_page())
        self._stack.addWidget(self._build_highlight_page())
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
        body_v.setContentsMargins(0, 0, 0, 0)
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

        # ★ 默认字体颜色
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
        self._default_fg_btn = _ColorBtn(_dfg_c)
        self._default_fg_btn.color_changed.connect(
            self._on_hl_changed
        )
        dfg_h.addWidget(self._default_fg_btn)
        dfg_h.addStretch(1)
        body_v.addLayout(dfg_h)

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

    def _on_hl_changed(self):
        self._refresh_preview()
        self._auto_save()
        self.highlight_changed.emit()
        self._update_hl_body_size()

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
        chk_h = self._chk_hl_enabled.height() + 8
        if value > chk_h:
            vp_w = self._hl_scroll.viewport().width()
            self._sticky_hl.setGeometry(0, 0, vp_w, chk_h)
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
        for ur in hl_cfg.get("user_rules", []):
            self._custom_list.add_rule(ur)

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
        self._config["highlight"] = (
            self._build_hl_config()
        )

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
            # ★ 高亮页重置
            self._chk_hl_enabled.setChecked(True)
            self._default_fg_btn.set_color("#1e293b")
            self._bi_chk_all.blockSignals(True)
            self._bi_chk_all.setChecked(True)
            self._bi_chk_all.blockSignals(False)
            for row in self._builtin_rows:
                row.reset()
            self._custom_list.clear_all()
            self._on_hl_changed()