"""
settings_dialog.py - 通用设置弹窗（全屏遮罩 + 居中面板）
v0.45 — ★ 重置按钮无边框设计（hover/pressed 仅背景色）
        ★ 关闭按钮垂直居中修复
        ★ 关闭按钮与主窗口一致 + 标题栏左侧齿轮图标
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QPushButton, QFileDialog, QWidget,
    QRadioButton, QScrollArea, QFrame, QStackedWidget,
    QButtonGroup, QLineEdit,
)
from PySide6.QtCore import Qt, QPoint, QPointF, QRectF, Signal
from PySide6.QtGui import (
    QPainter, QPainterPath, QColor, QPen, QMouseEvent, QRegion,
    QPixmap,
)
from PySide6.QtSvg import QSvgRenderer
from config import save_config

PANEL_W = 520
PANEL_H = 480
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
        self.setToolTip("将日志设置恢复为默认值")
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
# 主设置弹窗（全屏遮罩模式）
# ═══════════════════════════════════════════
class SettingsDialog(QDialog):
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
        self._record_all = True  # ★ v0.45: 全选状态（新增tab是否自动勾选）
        self._init_panel()
        self._load()
        self._connect_auto_save()
        self._on_enabled_toggled(self._chk_enabled.isChecked())

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
        content_v.setContentsMargins(16, 4, 16, 14)
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
        nav_v.addStretch(1)
        body_h.addWidget(nav_w)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_log_page())
        body_h.addWidget(self._stack, stretch=1)
        self._nav_group.idClicked.connect(
            self._stack.setCurrentIndex
        )
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
        v.setSpacing(10)

        self._chk_enabled = QCheckBox(
            "启用实时日志记录（连接串口时自动开始）"
        )
        self._chk_enabled.setStyleSheet(_CHK_SS)
        self._chk_enabled.toggled.connect(self._on_enabled_toggled)
        v.addWidget(self._chk_enabled)

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
        self._lbl_dir.setPlaceholderText("默认：程序目录/logs")
        self._lbl_dir.setStyleSheet(
            "QLineEdit { font-size: 12px; color: #374151;"
            "  background: #ffffff;"
            "  border: 1.5px solid #d1d5db;"
            "  border-radius: 6px; padding: 0px 4px 2px 4px;"
            "  min-height: 24px; max-height: 28px; }"
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
        v.addWidget(self._options_widget)
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

    def _reset(self):
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
        self._chk_select_all.setChecked(True)  # 触发 _toggle_select_all → 全部勾选