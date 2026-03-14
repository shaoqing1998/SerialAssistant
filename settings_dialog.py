"""
settings_dialog.py - 通用设置弹窗（全屏遮罩 + 居中面板）
v0.38 — 打开时主窗口置灰，点击面板外区域关闭（实时保存）
左侧 Tab 导航 + 右侧内容面板
★ 修改即实时保存，仅保留重置按钮
★ 加深边框、修复 RadioButton 选中涂白、QPainter 绘制关闭按钮
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
    QPainter, QPainterPath, QColor, QPen, QMouseEvent,
)
from config import save_config
# ═══════════════════════════════════════════
# QPainter 关闭按钮（与标题栌同款）
# ═══════════════════════════════════════════
class _CloseBtn(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(28, 28)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
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
        if self._pressed:
            p.setBrush(QColor("#c42b1c"))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(self.rect(), 4, 4)
        elif self._hovered:
            p.setBrush(QColor("#e81123"))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(self.rect(), 4, 4)
        fg = (
            QColor("#ffffff")
            if (self._hovered or self._pressed)
            else QColor("#9ca3af")
        )
        pen = QPen(fg, 1.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        cx, cy = self.width() / 2, self.height() / 2
        d = 4.5
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
    def __init__(self, text: str, parent=None):
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
# 常量
# ═══════════════════════════════════════════
PANEL_W = 520
PANEL_H = 480
RADIUS = 10
BORDER_COLOR = QColor("#b0b8c4")
BG_COLOR = QColor("#ffffff")
OVERLAY_COLOR = QColor(0, 0, 0, 80)
# ═══════════════════════════════════════════
# 主设置弹窗（全屏遮罩模式）
# ═══════════════════════════════════════════
class SettingsDialog(QDialog):
    def __init__(self, config: dict, tab_names: list[str], parent=None):
        super().__init__(parent)
        self._config = config
        self._tab_names = tab_names
        self._tab_checks: dict[str, QCheckBox] = {}
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, True
        )
        # ── 面板容器 ──
        self._panel = QWidget(self)
        self._panel.setFixedSize(PANEL_W, PANEL_H)
        self._init_panel()
        self._load()
        self._connect_auto_save()
    # ── 面板 UI ────────────────────────────
    def _init_panel(self):
        root = QVBoxLayout(self._panel)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(0)
        # 标题栏
        title_h = QHBoxLayout()
        title_h.setContentsMargins(6, 0, 0, 0)
        title_lbl = QLabel("设置")
        title_lbl.setStyleSheet(
            "font-size: 15px; font-weight: 600; color: #1f2937;"
            " background: transparent;"
        )
        title_h.addWidget(title_lbl, stretch=1)
        self._btn_close = _CloseBtn()
        self._btn_close.clicked.connect(self.close)
        title_h.addWidget(self._btn_close)
        root.addLayout(title_h)
        # 分隔线
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #c5cbd3;")
        root.addSpacing(10)
        root.addWidget(sep)
        root.addSpacing(10)
        # 左侧导航 + 右侧内容
        body_h = QHBoxLayout()
        body_h.setSpacing(12)
        nav_w = QWidget()
        nav_w.setFixedWidth(100)
        nav_v = QVBoxLayout(nav_w)
        nav_v.setContentsMargins(0, 0, 0, 0)
        nav_v.setSpacing(4)
        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        btn_log = _NavBtn("📋 日志")
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
        root.addLayout(body_h, stretch=1)
        # 底部：重置按钮
        root.addSpacing(8)
        bottom_h = QHBoxLayout()
        bottom_h.addStretch(1)
        btn_reset = QPushButton("重置")
        btn_reset.setFixedSize(72, 30)
        btn_reset.setStyleSheet(
            "QPushButton { background: #f3f4f6;"
            "  border: 1px solid #c5cbd3; border-radius: 6px;"
            "  font-size: 13px; color: #374151; }"
            "QPushButton:hover { background: #fee2e2;"
            "  border-color: #f87171; color: #dc2626; }"
        )
        btn_reset.setToolTip("将日志设置恢复为默认值")
        btn_reset.clicked.connect(self._reset)
        bottom_h.addWidget(btn_reset)
        root.addLayout(bottom_h)
    # ── 日志设置页 ────────────────────────
    def _build_log_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        # 启用开关
        self._chk_enabled = QCheckBox(
            "启用实时日志记录（连接串口时自动开始）"
        )
        self._chk_enabled.setStyleSheet(
            "font-size: 13px; background: transparent;"
        )
        v.addWidget(self._chk_enabled)
        # 保存路径
        dir_h = QHBoxLayout()
        dir_h.setSpacing(6)
        lbl = QLabel("保存位置：")
        lbl.setStyleSheet(
            "font-size: 13px; color: #374151;"
            " background: transparent;"
        )
        dir_h.addWidget(lbl)
        self._lbl_dir = QLabel("（默认：程序目录/logs）")
        self._lbl_dir.setStyleSheet(
            "font-size: 12px; color: #6b7280;"
            " background: #f9fafb;"
            " border: 1px solid #b0b8c4;"
            " border-radius: 4px; padding: 4px 8px;"
        )
        self._lbl_dir.setWordWrap(True)
        dir_h.addWidget(self._lbl_dir, stretch=1)
        btn_browse = QPushButton("浏览")
        btn_browse.setFixedHeight(28)
        btn_browse.setStyleSheet(
            "QPushButton { background: #f3f4f6;"
            "  border: 1px solid #b0b8c4;"
            "  border-radius: 6px;"
            "  padding: 0 12px; font-size: 13px;"
            "  color: #374151; }"
            "QPushButton:hover { background: #e5e7eb;"
            "  border-color: #9ca3af; }"
        )
        btn_browse.clicked.connect(self._browse)
        dir_h.addWidget(btn_browse)
        v.addLayout(dir_h)
        # ★ 文件格式（修复 RadioButton 选中后图标涂白）
        fmt_h = QHBoxLayout()
        fmt_h.setSpacing(8)
        fmt_lbl = QLabel("文件格式：")
        fmt_lbl.setStyleSheet(
            "font-size: 13px; color: #374151;"
            " background: transparent;"
        )
        fmt_h.addWidget(fmt_lbl)
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
        )
        self._radio_log = QRadioButton(".log")
        self._radio_txt = QRadioButton(".txt")
        for r in (self._radio_log, self._radio_txt):
            r.setStyleSheet(_RADIO_SS)
        self._radio_log.setChecked(True)
        fmt_h.addWidget(self._radio_log)
        fmt_h.addWidget(self._radio_txt)
        fmt_h.addStretch(1)
        v.addLayout(fmt_h)
        # Tab 选择
        tab_lbl = QLabel("记录的 Tab：")
        tab_lbl.setStyleSheet(
            "font-size: 13px; font-weight: 600;"
            " color: #374151; background: transparent;"
        )
        v.addWidget(tab_lbl)
        self._chk_all = QCheckBox(
            "全部 Tab（包括后续新建的）"
        )
        self._chk_all.setStyleSheet(
            "font-size: 13px; background: transparent;"
        )
        self._chk_all.toggled.connect(self._on_all_toggled)
        v.addWidget(self._chk_all)
        # 可滚动的 tab 列表
        tab_w = QWidget()
        tab_v = QVBoxLayout(tab_w)
        tab_v.setContentsMargins(20, 4, 0, 4)
        tab_v.setSpacing(4)
        for name in self._tab_names:
            chk = QCheckBox(name)
            chk.setStyleSheet(
                "font-size: 13px; background: transparent;"
            )
            self._tab_checks[name] = chk
            tab_v.addWidget(chk)
        tab_v.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidget(tab_w)
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(120)
        scroll.setStyleSheet(
            "QScrollArea { border: 1px solid #b0b8c4;"
            "  border-radius: 6px;"
            "  background: #f9fafb; }"
            "QScrollBar:vertical {"
            "  width: 4px; background: transparent; }"
            "QScrollBar::handle:vertical {"
            "  background: #d1d5db;"
            "  border-radius: 2px; }"
        )
        v.addWidget(scroll)
        v.addStretch(1)
        return page
    # ── 实时保存 ──────────────────────────
    def _connect_auto_save(self):
        self._chk_enabled.toggled.connect(self._auto_save)
        self._radio_log.toggled.connect(self._auto_save)
        self._radio_txt.toggled.connect(self._auto_save)
        self._chk_all.toggled.connect(self._auto_save)
        for chk in self._tab_checks.values():
            chk.toggled.connect(self._auto_save)
    def _auto_save(self):
        self._write_to_config()
        save_config(self._config)
    # ── 绘制：遮罩 + 面板 ────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(
            QPainter.RenderHint.Antialiasing, True
        )
        # 半透明遮罩
        p.fillRect(self.rect(), OVERLAY_COLOR)
        # 面板背景（白色圆角卡片 + 描边）
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
    def mousePressEvent(self, event: QMouseEvent):
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
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._center_panel()
    def _center_panel(self):
        self._panel.move(
            (self.width() - PANEL_W) // 2,
            (self.height() - PANEL_H) // 2,
        )
    # ── 内部逻辑 ─────────────────────────
    def _on_all_toggled(self, checked: bool):
        for chk in self._tab_checks.values():
            chk.setEnabled(not checked)
            if checked:
                chk.setChecked(True)
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
            for name, chk in self._tab_checks.items():
                chk.setChecked(name in selected)
    def _write_to_config(self):
        if "logging" not in self._config:
            self._config["logging"] = {}
        c = self._config["logging"]
        c["enabled"] = self._chk_enabled.isChecked()
        txt = self._lbl_dir.text()
        c["root_dir"] = "" if txt.startswith("（") else txt
        c["file_format"] = (
            ".txt" if self._radio_txt.isChecked() else ".log"
        )
        c["record_all_tabs"] = self._chk_all.isChecked()
        if not self._chk_all.isChecked():
            c["selected_tabs"] = [
                n
                for n, ch in self._tab_checks.items()
                if ch.isChecked()
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