"""
settings_dialog.py - 通用设置弹窗（全屏遮罩 + 居中面板）
v0.44 — ★ 关闭按钮与主窗口一致（细 X + 圆角端点 + 红色 hover）
        ★ 标题栏左侧齿轮图标 + "设置" 文字
        ★ 其余逻辑不变
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QPushButton, QFileDialog, QWidget,
    QRadioButton, QScrollArea, QFrame, QStackedWidget,
    QButtonGroup,
)
from PySide6.QtCore import Qt, QPoint, QRectF, Signal
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
    "  width: 14px; height: 14px; }"
    "QCheckBox::indicator:unchecked {"
    "  border: 1.5px solid #9ca3af;"
    "  border-radius: 3px; background: #ffffff; }"
    "QCheckBox::indicator:checked {"
    "  border: 1.5px solid #2563eb;"
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
    "  background: transparent; spacing: 5px; }"
    "QRadioButton::indicator {"
    "  width: 14px; height: 14px; }"
    "QRadioButton::indicator:unchecked {"
    "  border: 1.5px solid #9ca3af;"
    "  border-radius: 7px;"
    "  background: #ffffff; }"
    "QRadioButton::indicator:checked {"
    "  border: 1.5px solid #2563eb;"
    "  border-radius: 7px;"
    "  background: #2563eb; }"
    "QRadioButton::indicator:hover {"
    "  border-color: #3b82f6; }"
    "QRadioButton:disabled { color: #c0c0c0; }"
    "QRadioButton::indicator:disabled {"
    "  border-color: #d1d5db;"
    "  background: #f0f0f0; }"
)

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
        cx, cy = self.width() / 2, self.height() / 2
        d = 3.5
        p.drawLine(
            QPoint(int(cx - d), int(cy - d)),
            QPoint(int(cx + d), int(cy + d)),
        )
        p.drawLine(
            QPoint(int(cx + d), int(cy - d)),
            QPoint(int(cx - d), int(cy + d)),
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
    def __init__(self, parent=None):
        super().__init__("重置", parent)
        self.setFixedSize(72, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("将日志设置恢复为默认值")
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
        self._hovered = False
        self._apply_style()

    def enterEvent(self, e):
        self._hovered = True
        self._apply_style()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self._apply_style()
        super().leaveEvent(e)

    def _apply_style(self):
        if self._hovered:
            self.setStyleSheet(
                "QPushButton { background: #fee2e2;"
                "  border: 1px solid #f87171;"
                "  border-radius: 6px;"
                "  font-size: 13px; color: #dc2626; }"
            )
        else:
            self.setStyleSheet(
                "QPushButton { background: #f3f4f6;"
                "  border: 1px solid #c5cbd3;"
                "  border-radius: 6px;"
                "  font-size: 13px; color: #374151; }"
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
        top_h.addWidget(self._btn_close)
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
        nav_w.setFixedWidth(100)
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
        self._lbl_dir = QLabel("（默认：程序目录/logs）")
        self._lbl_dir.setStyleSheet(
            "font-size: 12px; color: #6b7280;"
            " background: #f9fafb;"
            " border: 1px solid #b0b8c4;"
            " border-radius: 4px; padding: 2px 8px;"
        )
        self._lbl_dir.setFixedHeight(28)
        self._lbl_dir.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self._lbl_dir.setWordWrap(True)
        dir_h.addWidget(self._lbl_dir, stretch=1)
        btn_browse = QPushButton("浏览")
        btn_browse.setFixedSize(52, 28)
        btn_browse.setStyleSheet(
            "QPushButton { background: #f3f4f6;"
            "  border: 1px solid #b0b8c4;"
            "  border-radius: 6px;"
            "  padding: 0 12px; font-size: 13px;"
            "  color: #374151; }"
            "QPushButton:hover { background: #e5e7eb;"
            "  border-color: #9ca3af; }"
            "QPushButton:disabled { background: #f3f4f6;"
            "  border-color: #e5e7eb; color: #c0c0c0; }"
        )
        btn_browse.clicked.connect(self._browse)
        dir_h.addWidget(btn_browse)
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

        self._chk_all = QCheckBox("全部 Tab（包括后续新建的）")
        self._chk_all.setStyleSheet(_CHK_SS)
        self._chk_all.toggled.connect(self._on_all_toggled)
        opts_v.addWidget(self._chk_all)

        tab_inner = QWidget()
        tab_v = QVBoxLayout(tab_inner)
        tab_v.setContentsMargins(4, 4, 4, 4)
        tab_v.setSpacing(4)

        self._chk_select_all = QCheckBox("全选")
        self._chk_select_all.setStyleSheet(_CHK_SS)
        self._chk_select_all.toggled.connect(self._toggle_select_all)
        tab_v.addWidget(self._chk_select_all)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #e5e7eb;")
        tab_v.addWidget(sep)

        for name in self._tab_names:
            chk = QCheckBox(name)
            chk.setStyleSheet(_CHK_SS)
            chk.toggled.connect(self._on_tab_check_changed)
            self._tab_checks.append(chk)
            tab_v.addWidget(chk)
        tab_v.addStretch(1)

        self._tab_scroll = QScrollArea()
        self._tab_scroll.setWidget(tab_inner)
        self._tab_scroll.setWidgetResizable(True)
        self._tab_scroll.setMaximumHeight(120)
        self._tab_scroll.setStyleSheet(
            "QScrollArea { border: 1px solid #d1d5db;"
            "  border-radius: 6px;"
            "  background: #ffffff; }"
            "QScrollBar:vertical {"
            "  width: 4px; background: transparent; }"
            "QScrollBar::handle:vertical {"
            "  background: #d1d5db;"
            "  border-radius: 2px; }"
            "QScrollBar::add-line, QScrollBar::sub-line {"
            "  width: 0; height: 0; }"
        )
        opts_v.addWidget(self._tab_scroll)
        opts_v.addStretch(1)
        v.addWidget(self._options_widget)
        return page

    def _on_enabled_toggled(self, checked):
        self._options_widget.setEnabled(checked)
        if checked:
            self._on_all_toggled(self._chk_all.isChecked())

    def _toggle_select_all(self, checked):
        for chk in self._tab_checks:
            chk.blockSignals(True)
            chk.setChecked(checked)
            chk.blockSignals(False)
        self._auto_save()

    def _on_tab_check_changed(self):
        total = len(self._tab_checks)
        selected = sum(1 for c in self._tab_checks if c.isChecked())
        self._chk_select_all.blockSignals(True)
        self._chk_select_all.setChecked(selected == total and total > 0)
        self._chk_select_all.blockSignals(False)
        self._auto_save()

    def _on_all_toggled(self, checked):
        self._tab_scroll.setEnabled(not checked)

    def _connect_auto_save(self):
        self._chk_enabled.toggled.connect(self._auto_save)
        self._radio_log.toggled.connect(self._auto_save)
        self._radio_txt.toggled.connect(self._auto_save)
        self._chk_all.toggled.connect(self._auto_save)

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
            self._auto_save()

    def _load(self):
        log_cfg = self._config.get("logging", {})
        self._chk_enabled.setChecked(
            log_cfg.get("enabled", False)
        )
        root = log_cfg.get("root_dir", "")
        if root:
            self._lbl_dir.setText(root)
        if log_cfg.get("file_format", ".log") == ".txt":
            self._radio_txt.setChecked(True)
        else:
            self._radio_log.setChecked(True)
        if log_cfg.get("record_all_tabs", True):
            self._chk_all.setChecked(True)
        else:
            selected = log_cfg.get("selected_tabs", [])
            for chk in self._tab_checks:
                chk.setChecked(chk.text() in selected)

    def _write_to_config(self):
        if "logging" not in self._config:
            self._config["logging"] = {}
        c = self._config["logging"]
        c["enabled"] = self._chk_enabled.isChecked()
        txt = self._lbl_dir.text()
        c["root_dir"] = (
            "" if txt.startswith("（") else txt
        )
        c["file_format"] = (
            ".txt"
            if self._radio_txt.isChecked()
            else ".log"
        )
        c["record_all_tabs"] = self._chk_all.isChecked()
        if not self._chk_all.isChecked():
            c["selected_tabs"] = [
                chk.text()
                for chk in self._tab_checks
                if chk.isChecked()
            ]
        else:
            c["selected_tabs"] = []

    def _reset(self):
        self._config["logging"] = {
            "enabled": False,
            "root_dir": "",
            "file_format": ".log",
            "record_all_tabs": True,
            "selected_tabs": [],
        }
        save_config(self._config)
        self._chk_enabled.setChecked(False)
        self._lbl_dir.setText("（默认：程序目录/logs）")
        self._radio_log.setChecked(True)
        self._chk_all.setChecked(True)
        self._chk_select_all.blockSignals(True)
        self._chk_select_all.setChecked(True)
        self._chk_select_all.blockSignals(False)
        for chk in self._tab_checks:
            chk.blockSignals(True)
            chk.setChecked(True)
            chk.blockSignals(False)