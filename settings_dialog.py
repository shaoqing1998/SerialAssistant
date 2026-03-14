"""
settings_dialog.py - 通用设置弹窗（全屏遮罩 + 居中面板）
v0.43 — 第二轮 UI 全面修复
★ 移除顶部"设置"标题和分隔线
★ 关闭按钮 46x32 + 右上角圆角路径（红色不溢出面板圆角）
★ 重置按钮 hover 修复（自定义 enterEvent/leaveEvent）
★ 路径框/浏览按钮统一 28px 高度 + 垂直居中
★ Tab 列表改用标准 QCheckBox（正确响应 setEnabled 视觉置灰）
★ 全选 checkbox 在 tab 列表最顶上
★ 全部 Tab 勾选 -> 置灰 tab 选择列表
★ 不勾选启用日志 -> 所有选项视觉置灰
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QPushButton, QFileDialog, QWidget,
    QRadioButton, QScrollArea, QFrame, QStackedWidget,
    QButtonGroup,
)
from PySide6.QtCore import Qt, QPoint, QRectF
from PySide6.QtGui import (
    QPainter, QPainterPath, QColor, QPen, QMouseEvent, QRegion,
)
from config import save_config

# ═══════════════════════════════════════════
# 常量
# ═══════════════════════════════════════════
PANEL_W = 520
PANEL_H = 480
RADIUS = 10
BORDER_COLOR = QColor("#b0b8c4")
BG_COLOR = QColor("#ffffff")
OVERLAY_COLOR = QColor(0, 0, 0, 80)

# ★ 统一 QCheckBox 样式（含 disabled 置灰态）
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


# ═══════════════════════════════════════════
# ★ 关闭按钮（46x32 贴边，右上角圆角匹配面板）
# ═══════════════════════════════════════════
class _CloseBtn(QPushButton):
    """贴边关闭按钮，右上角圆角防止红色溢出面板"""

    def __init__(self, corner_radius=0, parent=None):
        super().__init__(parent)
        self.setFixedSize(46, 32)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hovered = False
        self._pressed = False
        self._cr = corner_radius

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

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        color = None
        if self._pressed:
            color = QColor("#c42b1c")
        elif self._hovered:
            color = QColor("#e81123")
        if color:
            # ★ 右上角圆角路径 -> 红色不会溢出面板圆角
            r = self._cr
            rect = QRectF(self.rect())
            path = QPainterPath()
            path.moveTo(0, rect.height())          # 左下
            path.lineTo(0, 0)                      # 左上
            path.lineTo(rect.width() - r, 0)       # 向右
            if r > 0:
                path.arcTo(
                    rect.width() - 2 * r, 0,
                    2 * r, 2 * r, 90, -90,
                )                                  # 右上圆角
            else:
                path.lineTo(rect.width(), 0)
            path.lineTo(rect.width(), rect.height())  # 右下
            path.closeSubpath()
            p.fillPath(path, color)
        # x 号
        fg = (
            QColor("#ffffff")
            if (self._hovered or self._pressed)
            else QColor("#9ca3af")
        )
        pen = QPen(fg, 1.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        cx, cy = self.width() / 2, self.height() / 2
        d = 5
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
# ★ 重置按钮（自定义 enterEvent 修复从上方进入不高亮）
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
        # ★ 初始化启用/禁用状态
        self._on_enabled_toggled(self._chk_enabled.isChecked())

    # ── 面板 UI ────────────────────────────
    def _init_panel(self):
        root = QVBoxLayout(self._panel)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ★ 顶部：仅关闭按钮（无"设置"标题、无分隔线）
        top_bar = QWidget()
        top_bar.setFixedHeight(32)
        top_h = QHBoxLayout(top_bar)
        top_h.setContentsMargins(0, 0, 0, 0)
        top_h.setSpacing(0)
        top_h.addStretch(1)
        self._btn_close = _CloseBtn(corner_radius=RADIUS)
        self._btn_close.clicked.connect(self.close)
        top_h.addWidget(self._btn_close)
        root.addWidget(top_bar)

        # ── 内容区 ──
        content = QWidget()
        content_v = QVBoxLayout(content)
        content_v.setContentsMargins(16, 4, 16, 14)
        content_v.setSpacing(0)

        body_h = QHBoxLayout()
        body_h.setSpacing(12)

        # 左侧导航
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

        # ★ 底部重置（自定义 _ResetBtn 修复 hover）
        content_v.addSpacing(12)
        bottom_h = QHBoxLayout()
        bottom_h.addStretch(1)
        self._btn_reset = _ResetBtn()
        self._btn_reset.clicked.connect(self._reset)
        bottom_h.addWidget(self._btn_reset)
        content_v.addLayout(bottom_h)

        root.addWidget(content, stretch=1)

    # ── 日志设置页 ────────────────────────
    def _build_log_page(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)

        # 启用开关
        self._chk_enabled = QCheckBox(
            "启用实时日志记录（连接串口时自动开始）"
        )
        self._chk_enabled.setStyleSheet(_CHK_SS)
        self._chk_enabled.toggled.connect(self._on_enabled_toggled)
        v.addWidget(self._chk_enabled)

        # ★ 可置灰区域（setEnabled 视觉生效）
        self._options_widget = QWidget()
        opts_v = QVBoxLayout(self._options_widget)
        opts_v.setContentsMargins(0, 0, 0, 0)
        opts_v.setSpacing(10)

        # ★ 保存路径（统一 28px + 垂直居中）
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

        # 文件格式
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

        # "全部 Tab" 独立选项
        self._chk_all = QCheckBox("全部 Tab（包括后续新建的）")
        self._chk_all.setStyleSheet(_CHK_SS)
        self._chk_all.toggled.connect(self._on_all_toggled)
        opts_v.addWidget(self._chk_all)

        # ★ Tab 选择列表（标准 QCheckBox 支持 setEnabled 置灰）
        tab_inner = QWidget()
        tab_v = QVBoxLayout(tab_inner)
        tab_v.setContentsMargins(4, 4, 4, 4)
        tab_v.setSpacing(4)

        # ★ 全选 checkbox 在最顶上左边
        self._chk_select_all = QCheckBox("全选")
        self._chk_select_all.setStyleSheet(_CHK_SS)
        self._chk_select_all.toggled.connect(self._toggle_select_all)
        tab_v.addWidget(self._chk_select_all)

        # 分隔线
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #e5e7eb;")
        tab_v.addWidget(sep)

        # 个别 Tab checkbox
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

    # ── ★ 启用/禁用日志选项 ──────────────
    def _on_enabled_toggled(self, checked):
        self._options_widget.setEnabled(checked)
        if checked:
            # 重新应用 "全部 Tab" 的置灰逻辑
            self._on_all_toggled(self._chk_all.isChecked())

    # ── Tab 列表逻辑 ─────────────────────
    def _toggle_select_all(self, checked):
        """全选 checkbox -> 勾上/取消所有 tab"""
        for chk in self._tab_checks:
            chk.blockSignals(True)
            chk.setChecked(checked)
            chk.blockSignals(False)
        self._auto_save()

    def _on_tab_check_changed(self):
        """某个 tab checkbox 变化 -> 同步全选状态"""
        total = len(self._tab_checks)
        selected = sum(1 for c in self._tab_checks if c.isChecked())
        self._chk_select_all.blockSignals(True)
        self._chk_select_all.setChecked(selected == total and total > 0)
        self._chk_select_all.blockSignals(False)
        self._auto_save()

    def _on_all_toggled(self, checked):
        """全部 Tab -> 置灰 tab 选择列表（不改变选中状态）"""
        self._tab_scroll.setEnabled(not checked)

    # ── 实时保存 ──────────────────────────
    def _connect_auto_save(self):
        self._chk_enabled.toggled.connect(self._auto_save)
        self._radio_log.toggled.connect(self._auto_save)
        self._radio_txt.toggled.connect(self._auto_save)
        self._chk_all.toggled.connect(self._auto_save)

    def _auto_save(self):
        self._write_to_config()
        save_config(self._config)

    # ── 绘制：遮罩 + 面板 ────────────────
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

    # ── 点击遮罩区域关闭 ───────────────
    def mousePressEvent(self, event):
        if not self._panel.geometry().contains(event.pos()):
            self.close()
            return
        super().mousePressEvent(event)

    # ── 显示时覆盖父窗口 ───────────────
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
        """面板圆角裁剪"""
        path = QPainterPath()
        path.addRoundedRect(
            QRectF(self._panel.rect()), RADIUS, RADIUS
        )
        self._panel.setMask(
            QRegion(path.toFillPolygon().toPolygon())
        )

    # ── 内部逻辑 ─────────────────────────
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