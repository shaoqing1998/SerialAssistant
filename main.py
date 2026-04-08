"""
main.py - 串口调试助手 v0.63
★ pyqt-frameless-window 库（Win11 原生按钮 + 窗口阴影）
★ 覆盖库 min/max/close 按钮 paintEvent（圆润 Notion 风格）
★ Snap Layout 通过 nativeEvent 覆写实现（库官方方案）
★ v0.5: 设置变更 → 刷新高亮
★ v0.6: closeEvent 先关闭所有打开的 QDialog
"""
import sys
import os
import ctypes
import ctypes.wintypes

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QWidget,
    QHBoxLayout, QVBoxLayout, QGridLayout,
    QComboBox, QPushButton, QLabel,
    QCheckBox, QSizePolicy,
    QSpinBox, QStyledItemDelegate,
    QFileDialog,
    QDialog,
)
from PySide6.QtCore import (
    Qt, QTimer, QEvent, QPoint,
    QAbstractNativeEventFilter,
)
from PySide6.QtGui import (
    QFont, QMouseEvent, QColor, QCursor,
    QAction, QKeySequence,
)

from qframelesswindow import FramelessMainWindow
from config import load_config, save_config
from serial_manager import SerialManager
from filter_manager import FilterManager, FilteredLogView
from rounded_menu import RoundedMenu, RoundedContextTextEdit
from title_bar import (
    SettingsButton,
    customize_titlebar_buttons,
)
from log_manager import LogManager
from settings_dialog import (
    SettingsDialog, InfoPopup, ConfirmPopup,
    InputIntPopup, InputTextPopup,
)


_M = 10
_OPTS_W = 192
_BTN_W = 72
_RIGHT_W = _OPTS_W + 8 + _BTN_W


class _CenterDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = (
            Qt.AlignmentFlag.AlignCenter
        )


class _BaudComboBox(QComboBox):
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.showPopup()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event):
        from PySide6.QtWidgets import (
            QStylePainter, QStyleOptionComboBox, QStyle,
        )
        painter = QStylePainter(self)
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        opt.currentText = ""
        painter.drawComplexControl(
            QStyle.ComplexControl.CC_ComboBox, opt
        )
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignCenter,
            self.currentText(),
        )


STYLE = """
* { outline: none; }
QMainWindow, QWidget#AppRoot {
    background-color: #eef0f3;
    color: #1f2937;
    font-family: "Microsoft YaHei UI", "PingFang SC",
                 "Segoe UI", sans-serif;
    font-size: 14px;
}
QWidget {
    color: #1f2937;
    font-family: "Microsoft YaHei UI", "PingFang SC",
                 "Segoe UI", sans-serif;
    font-size: 14px;
}
QComboBox {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 0 8px 0 8px;
    min-height: 30px;
    color: #1f2937;
    font-size: 14px;
    selection-background-color: #dbeafe;
}
QComboBox:hover  { background: #f3f4f6;
                   border-color: #9ca3af; }
QComboBox:focus  { border-color: #3b82f6; }
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 18px; border: none;
}
QComboBox::down-arrow {
    width: 8px; height: 5px;
    image: url("data:image/svg+xml,<svg xmlns="
        "'http://www.w3.org/2000/svg'"
        " width='8' height='5'>"
        "<polygon points='0,0 8,0 4,5'"
        " fill='%236b7280'/></svg>");
}
QComboBox QAbstractItemView {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    selection-background-color: #dbeafe;
    selection-color: #1d4ed8;
    padding: 2px; outline: none;
}
QPushButton {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    color: #374151; font-size: 14px;
    padding: 0 12px;
    min-height: 30px; min-width: 52px;
}
QPushButton:hover {
    background: #f0f4ff;
    border-color: #93c5fd; color: #1d4ed8;
}
QPushButton:pressed { background: #dbeafe; }
QPushButton:disabled {
    background: #f3f4f6;
    border-color: #e5e7eb; color: #d1d5db;
}
QPushButton#BtnConnect {
    background: #2563eb; border: none;
    border-radius: 6px; color: #fff;
    font-weight: 600; min-height: 30px;
    min-width: 82px; padding: 0 14px;
}
QPushButton#BtnConnect:hover { background: #3b82f6; }
QPushButton#BtnConnect:pressed { background: #1d4ed8; }
QPushButton#BtnDisconnect {
    background: #6b7280; border: none;
    border-radius: 6px; color: #fff;
    font-weight: 600; min-height: 30px;
    min-width: 82px; padding: 0 14px;
}
QPushButton#BtnDisconnect:hover { background: #9ca3af; }
QPushButton#BtnDisconnect:pressed { background: #4b5563; }
QPushButton#BtnSend {
    background: #16a34a; border: none;
    border-radius: 6px; color: #fff;
    font-weight: 600; padding: 0;
    min-height: 0; min-width: 0;
}
QPushButton#BtnSend:hover { background: #22c55e; }
QPushButton#BtnSend:pressed { background: #15803d; }
QPushButton#BtnSend:disabled {
    background: #d1fae5; color: #6ee7b7; border: none;
}
QPushButton#BtnClear {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 6px; color: #6b7280;
    padding: 0; min-height: 0; min-width: 0;
}
QPushButton#BtnClear:hover {
    background: #fef3c7;
    border-color: #fbbf24; color: #b45309;
}
QPushButton#BtnRefilter {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 6px; color: #374151;
    min-height: 28px; padding: 0 10px;
    font-size: 13px;
}
QPushButton#BtnRefilter:hover {
    background: #faf5ff;
    border-color: #c084fc; color: #7c3aed;
}
QPushButton#BtnRefilter:disabled {
    background: #f3f4f6;
    border-color: #e5e7eb; color: #d1d5db;
}
QPushButton#BtnToggleSend {
    background: transparent; border: none;
    border-radius: 4px; color: #9ca3af;
    font-size: 15px;
    min-width: 30px; max-width: 30px;
    min-height: 30px; max-height: 30px;
    padding: 0;
}
QPushButton#BtnToggleSend:hover {
    background: #e5e7eb; color: #2563eb;
}
QPushButton#BtnTabClose {
    background: transparent; border: none;
    border-radius: 3px; color: #d1d5db;
    font-size: 12px; font-weight: 700;
    min-width: 14px; max-width: 14px;
    min-height: 14px; max-height: 14px;
    padding: 0;
}
QPushButton#BtnTabClose:hover {
    background: #fee2e2; color: #dc2626;
}
QTabWidget { background: transparent; border: none; }
QTabWidget::pane {
    border: none; background: transparent;
    margin: 0; padding: 0;
}
QTabBar {
    background: transparent; border: none;
    qproperty-drawBase: 0;
}
QTabBar::tab {
    background: transparent; color: #6b7280;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 6px 0px 6px 0px;
    margin: 0 8px 0 0;
    min-width: 0px; font-size: 13px;
}
QTabBar::tab:selected {
    color: #2563eb;
    border-bottom: 2px solid transparent;
    font-weight: 600;
}
QTabBar::tab:hover:!selected { color: #3b82f6; }
QTextEdit {
    background: #ffffff; color: #1e293b;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    selection-background-color: #bfdbfe;
    selection-color: #1e3a8a;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 13px;
}
QWidget#FilterBar { background: transparent; }
QLineEdit#KwEdit {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 6px; padding: 0 9px;
    min-height: 28px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 13px; color: #1f2937;
}
QLineEdit#KwEdit:focus { border-color: #3b82f6; }
QLineEdit#KwEdit:disabled {
    background: #f3f4f6; color: #d1d5db;
    border-color: #e5e7eb;
}
QTextEdit#SendEdit {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 13px; color: #1f2937;
    padding: 4px 6px;
}
QTextEdit#SendEdit:focus { border-color: #3b82f6; }
QCheckBox {
    color: #374151; spacing: 5px;
    font-size: 13px; background: transparent;
}
QCheckBox::indicator {
    width: 14px; height: 14px;
    border: 1.5px solid #9ca3af;
    border-radius: 3px; background: #ffffff;
}
QCheckBox::indicator:checked {
    background: #2563eb; border-color: #2563eb;
}
QCheckBox::indicator:hover { border-color: #3b82f6; }
QCheckBox:disabled { color: #d1d5db; }
QCheckBox::indicator:disabled {
    background: #f3f4f6; border-color: #e5e7eb;
}
QLabel { color: #374151; background: transparent; }
QLabel#DotOn  { color: #16a34a; font-size: 14px; }
QLabel#DotOff { color: #d1d5db; font-size: 14px; }
QStatusBar {
    background: #eef0f3; color: #6b7280;
    font-size: 13px; border: none;
    min-height: 24px;
}
QStatusBar::item { border: none; }
QStatusBar QLabel {
    color: #6b7280; padding: 0 6px;
    font-size: 13px; background: transparent;
    border: none;
}
QSpinBox {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 6px; padding: 0 4px;
    min-height: 26px; color: #1f2937;
    font-size: 13px;
}
QSpinBox:focus { border-color: #3b82f6; }
QSpinBox:disabled {
    background: #f3f4f6; color: #d1d5db;
    border-color: #e5e7eb;
}
QSpinBox::up-button, QSpinBox::down-button {
    width: 14px; border: none;
    background: transparent;
}
QScrollBar:vertical {
    background: transparent; width: 6px;
}
QScrollBar:horizontal {
    background: transparent; height: 6px;
}
QScrollBar::handle:vertical,
QScrollBar::handle:horizontal {
    background: #d1d5db; border-radius: 3px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover,
QScrollBar::handle:horizontal:hover {
    background: #3b82f6;
}
QScrollBar::add-line, QScrollBar::sub-line {
    width: 0; height: 0;
}
"""


class _WinCloseFilter(QAbstractNativeEventFilter):
    """应用级 WM_CLOSE 拦截 — 模态对话框 exec 中也生效"""

    def __init__(self, window):
        super().__init__()
        self._window = window
        self._closing = False

    def _do_close(self):
        """关闭所有可见 Dialog + 主窗口"""
        app = QApplication.instance()
        for w in app.topLevelWidgets():
            if (
                isinstance(w, QDialog)
                and w.isVisible()
            ):
                w.done(0)
        self._window.close()

    def nativeEventFilter(self, eventType, message):
        if self._closing:
            return True, 0          # 阻断后续 WM_CLOSE
        if eventType == b"windows_generic_MSG":
            try:
                msg = ctypes.wintypes.MSG.from_address(
                    int(message)
                )
                if msg.message == 0x0010:   # WM_CLOSE
                    # ★ 不检查 HWND — qframelesswindow
                    #   的 winId() 可能与 Windows 实际
                    #   发送目标不一致，全部拦截最可靠
                    self._closing = True
                    QTimer.singleShot(
                        0,
                        self._do_close,
                    )
                    return True, 0
                # ★ v0.6: resize 预冻结
                elif msg.message == 0x0231:
                    # WM_ENTERSIZEMOVE
                    self._window._freeze_for_resize()
                elif msg.message == 0x0232:
                    # WM_EXITSIZEMOVE — 松手瞬间解冻
                    self._window._unfreeze_after_resize()
            except Exception:
                pass
        return False, 0


class MainWindow(FramelessMainWindow):
    BAUDRATES = [
        "1200", "2400", "4800", "9600", "14400",
        "19200", "38400", "57600", "115200",
        "230400", "460800", "921600",
    ]

    def __init__(self):
        super().__init__()
        self._cfg = load_config()
        self._serial = SerialManager()
        self._connected = False
        self._start_time = None
        self._last_rx = self._last_tx = 0
        self._known_ports = []
        self._send_visible = True
        self._log_mgr = LogManager(self._cfg, parent=self)
        self._log_mgr.write_error.connect(self._on_log_error)
        self._setup_title_bar()
        self._build_ui()
        self.titleBar.raise_()
        self._port_timer = QTimer(self)
        self._port_timer.timeout.connect(self._scan_ports)
        self._port_timer.start(800)
        self._stat_timer = QTimer(self)
        self._stat_timer.timeout.connect(self._refresh_stat)
        self._stat_timer.start(1000)

        self._scan_ports()
        self._wire()
        # ★ v0.5: 初始加载高亮配置
        self._filter_mgr.refresh_highlighter(self._cfg)
        self._center_on_screen()
        # ★ v0.6: 应用级 WM_CLOSE 拦截（模态对话框中也生效）
        self._close_filter = _WinCloseFilter(self)
        QApplication.instance().installNativeEventFilter(
            self._close_filter
        )
        # ★ v0.63: 动态快捷键（从配置读取）
        self._act_close_tab = QAction(self)
        self._act_close_tab.triggered.connect(
            lambda: self._filter_mgr
                .request_close_current_tab()
        )
        self.addAction(self._act_close_tab)
        self._act_goto_line = QAction(self)
        self._act_goto_line.triggered.connect(
            self._on_goto_line
        )
        self.addAction(self._act_goto_line)
        self._act_send = QAction(self)
        self._act_send.triggered.connect(
            self._do_send
        )
        self.addAction(self._act_send)
        self._rebind_shortcuts()

    # ── ★ 标题栏配置 ─────────────────────
    def _setup_title_bar(self):
        self.setWindowTitle("串口调试助手  v0.63")
        tb = self.titleBar
        tb.setFixedHeight(32)
        tb.setAutoFillBackground(True)
        palette = tb.palette()
        palette.setColor(
            palette.ColorRole.Window, QColor("#eef0f3")
        )
        tb.setPalette(palette)
        if hasattr(tb, 'titleLabel'):
            tb.titleLabel.setStyleSheet(
                "color: #374151; font-size: 13px;"
                " font-weight: 600;"
                " background: transparent;"
            )
        if hasattr(tb, 'iconLabel'):
            tb.iconLabel.hide()
        # ★ v0.44: 覆盖 min/max/close 按钮绘制
        customize_titlebar_buttons(tb)
        self._btn_settings = SettingsButton()
        self._btn_settings.clicked.connect(
            self._open_settings
        )
        try:
            layout = tb.hBoxLayout
            idx = layout.indexOf(tb.minBtn)
            if idx >= 0:
                layout.insertWidget(
                    idx, self._btn_settings
                )
        except AttributeError:
            tb.layout().addWidget(self._btn_settings)

    def _build_ui(self):
        w = self._cfg["ui"]["window_width"]
        h = self._cfg["ui"]["window_height"]
        if w <= 0 or h <= 0:
            # ★ v0.6: 首次启动自适应屏幕 — 85% 可用区域
            from PySide6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                w = int(geo.width() * 0.85)
                h = int(geo.height() * 0.85)
            else:
                w, h = 1100, 650
        self.resize(max(w, 900), max(h, 520))
        self.setMinimumSize(900, 520)
        root = QWidget()
        root.setObjectName("AppRoot")
        self.setCentralWidget(root)
        root_v = QVBoxLayout(root)
        root_v.setContentsMargins(0, 0, 0, 0)
        root_v.setSpacing(0)
        content = QWidget()
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(_M, 36, _M, 4)
        vbox.setSpacing(4)
        vbox.addWidget(self._make_toolbar())
        self._filter_mgr = FilterManager(
            self._cfg,
            h_margin=0,
            right_width=_RIGHT_W,
            toggle_send_callback=self._toggle_send_area,
        )
        vbox.addWidget(self._filter_mgr, stretch=1)
        self._send_area = self._make_send_area()
        vbox.addWidget(self._send_area)
        self._make_statusbar()
        root_v.addWidget(content, stretch=1)

    def _center_on_screen(self):
        from PySide6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (
                geo.height() - self.height()
            ) // 2
            self.move(x, y)

    def _make_toolbar(self):
        bar = QWidget()
        h = QHBoxLayout(bar)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        self._cb_port = QComboBox()
        self._cb_port.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self._cb_port.setMinimumWidth(200)
        self._cb_port.setToolTip(
            "串口端口（自动实时扫描）"
        )
        h.addWidget(self._cb_port, stretch=1)
        self._cb_baud = _BaudComboBox()
        custom_bauds = self._cfg.get("serial", {}).get(
            "custom_baudrates", []
        )
        all_bauds = sorted(
            set(int(b) for b in self.BAUDRATES)
            | set(custom_bauds)
        )
        for b in all_bauds:
            self._cb_baud.addItem(str(b))
        self._cb_baud.addItem("自定义...")
        saved = str(self._cfg["serial"]["baudrate"])
        idx = self._cb_baud.findText(saved)
        if idx >= 0:
            self._cb_baud.setCurrentIndex(idx)
        self._cb_baud.setFixedWidth(84)
        self._cb_baud.setToolTip(
            "波特率（点击选择，可自定义）"
        )
        self._cb_baud.setItemDelegate(
            _CenterDelegate(self._cb_baud)
        )
        self._cb_baud.currentIndexChanged.connect(
            self._on_baud_changed
        )
        h.addWidget(self._cb_baud)
        self._dot = QLabel("●")
        self._dot.setObjectName("DotOff")
        self._dot.setFixedWidth(16)
        self._dot.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        h.addWidget(self._dot)
        self._btn_conn = QPushButton("连  接")
        self._btn_conn.setObjectName("BtnConnect")
        h.addWidget(self._btn_conn)
        return bar

    def _make_send_area(self):
        AREA_H = 128
        area = QWidget()
        area.setFixedHeight(AREA_H)
        h = QHBoxLayout(area)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        self._send_edit = RoundedContextTextEdit()
        self._send_edit.setObjectName("SendEdit")
        self._send_edit.setPlaceholderText(
            "输入发送内容…（Ctrl+Enter 发送）"
        )
        mono = QFont("Consolas", 12)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self._send_edit.setFont(mono)
        self._send_edit.installEventFilter(self)
        h.addWidget(self._send_edit, stretch=1)
        SPIN_W = 72
        opts_container = QWidget()
        opts_container.setFixedWidth(_OPTS_W)
        opts_container.setFixedHeight(AREA_H)
        opts_v = QVBoxLayout(opts_container)
        opts_v.setContentsMargins(0, 0, 0, 0)
        opts_v.setSpacing(0)
        opts_v.addStretch(1)
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)
        grid.setColumnMinimumWidth(0, 84)
        grid.setColumnStretch(2, 1)
        ROW_H = 28
        for r in range(4):
            grid.setRowMinimumHeight(r, ROW_H)
        self._chk_ts = QCheckBox("时间戳")
        self._spin_ts = QSpinBox()
        self._spin_ts.setRange(10, 9999)
        self._spin_ts.setValue(100)
        self._spin_ts.setFixedWidth(SPIN_W)
        self._spin_ts.setEnabled(False)
        self._spin_ts.setToolTip(
            "超时时间：超过此时间无数据则换行"
        )
        lbl_ts = QLabel("ms")
        lbl_ts.setStyleSheet(
            "color:#9ca3af;font-size:14px;"
        )
        grid.addWidget(
            self._chk_ts, 0, 0,
            Qt.AlignmentFlag.AlignVCenter
            | Qt.AlignmentFlag.AlignLeft,
        )
        grid.addWidget(
            self._spin_ts, 0, 1,
            Qt.AlignmentFlag.AlignVCenter,
        )
        grid.addWidget(
            lbl_ts, 0, 2,
            Qt.AlignmentFlag.AlignVCenter,
        )
        self._chk_loop = QCheckBox("循环发送")
        self._spin_ms = QSpinBox()
        self._spin_ms.setRange(50, 99999)
        self._spin_ms.setValue(200)
        self._spin_ms.setFixedWidth(SPIN_W)
        self._spin_ms.setEnabled(False)
        lbl_ms = QLabel("ms")
        lbl_ms.setStyleSheet(
            "color:#9ca3af;font-size:14px;"
        )
        grid.addWidget(
            self._chk_loop, 1, 0,
            Qt.AlignmentFlag.AlignVCenter
            | Qt.AlignmentFlag.AlignLeft,
        )
        grid.addWidget(
            self._spin_ms, 1, 1,
            Qt.AlignmentFlag.AlignVCenter,
        )
        grid.addWidget(
            lbl_ms, 1, 2,
            Qt.AlignmentFlag.AlignVCenter,
        )
        self._chk_hex_rx = QCheckBox("HEX 显示")
        self._chk_hex_tx = QCheckBox("HEX 发送")
        grid.addWidget(
            self._chk_hex_rx, 2, 0,
            Qt.AlignmentFlag.AlignVCenter
            | Qt.AlignmentFlag.AlignLeft,
        )
        grid.addWidget(
            self._chk_hex_tx, 2, 1, 1, 2,
            Qt.AlignmentFlag.AlignVCenter
            | Qt.AlignmentFlag.AlignLeft,
        )
        self._chk_enter = QCheckBox("回车发送")
        self._chk_nl = QCheckBox("追加换行")
        self._chk_nl.setChecked(
            self._cfg["send"].get("add_newline", True)
        )
        grid.addWidget(
            self._chk_enter, 3, 0,
            Qt.AlignmentFlag.AlignVCenter
            | Qt.AlignmentFlag.AlignLeft,
        )
        grid.addWidget(
            self._chk_nl, 3, 1, 1, 2,
            Qt.AlignmentFlag.AlignVCenter
            | Qt.AlignmentFlag.AlignLeft,
        )
        opts_v.addLayout(grid)
        opts_v.addStretch(1)
        h.addWidget(opts_container)
        BTN_H = (AREA_H - 4) // 2
        self._btn_send = QPushButton("发送")
        self._btn_send.setObjectName("BtnSend")
        self._btn_send.setEnabled(False)
        self._btn_send.setFixedSize(_BTN_W, BTN_H)
        self._btn_clear = QPushButton("清空")
        self._btn_clear.setObjectName("BtnClear")
        self._btn_clear.setFixedSize(_BTN_W, BTN_H)
        self._btn_clear.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        btns_col = QWidget()
        btns_col.setFixedSize(_BTN_W, AREA_H)
        btns_v = QVBoxLayout(btns_col)
        btns_v.setContentsMargins(0, 0, 0, 0)
        btns_v.setSpacing(4)
        btns_v.addWidget(self._btn_send)
        btns_v.addWidget(self._btn_clear)
        h.addWidget(btns_col)
        self._loop_timer = QTimer(self)
        self._loop_timer.timeout.connect(self._do_send)
        return area

    def _make_statusbar(self):
        sb = self.statusBar()
        sb.setSizeGripEnabled(False)
        self._lbl_log_err = QLabel("")
        self._lbl_log_err.setStyleSheet(
            "color: #dc2626; font-weight: 600;"
            " font-size: 13px;"
            " background: transparent; padding: 0 6px;"
        )
        self._lbl_log_err.hide()
        sb.addWidget(self._lbl_log_err)
        self._lbl_status = QLabel("就绪")
        self._lbl_timer = QLabel("00:00:00")
        self._lbl_tx = QLabel("TX: 0 B")
        self._lbl_rx = QLabel("RX: 0 B")
        self._lbl_tx_rate = QLabel("↑ 0 B/s")
        self._lbl_rx_rate = QLabel("↓ 0 B/s")
        sb.addWidget(self._lbl_status, 1)
        for w in (
            self._lbl_timer, self._lbl_tx,
            self._lbl_rx, self._lbl_tx_rate,
            self._lbl_rx_rate,
        ):
            sb.addPermanentWidget(w)

    # ── ★ v0.6: 窗口拖动期间冻结日志视图布局 ──
    def _freeze_for_resize(self):
        """WM_ENTERSIZEMOVE 预冻结 — 仅换行模式锁 viewport"""
        # 不开换行时无需冻结（NoWrap 布局开销极低）
        has_wrap = any(
            isinstance(self._filter_mgr._tabs.widget(i), FilteredLogView)
            and self._filter_mgr._tabs.widget(i)._wrap_mode
                == FilteredLogView.LineWrapMode.WidgetWidth
            for i in range(self._filter_mgr._tabs.count())
        )
        if not has_wrap:
            return
        self._filter_mgr.set_write_paused(True)
        for i in range(self._filter_mgr._tabs.count()):
            v = self._filter_mgr._tabs.widget(i)
            if isinstance(v, FilteredLogView):
                v.set_resize_frozen(True)

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def _unfreeze_after_resize(self):
        """WM_EXITSIZEMOVE — 松手瞬间立即解冻"""
        self._do_unfreeze()

    def _do_unfreeze(self):
        """flush 缓冲 + 解冻被锁视图（幂等安全）"""
        if not self._filter_mgr._write_paused:
            return   # 已解冻过，跳过
        # Phase 1: flush 缓冲（viewport 锁着零重排开销）
        self._filter_mgr.set_write_paused(False)
        # Phase 2: 只解冻实际被锁的视图
        for i in range(self._filter_mgr._tabs.count()):
            v = self._filter_mgr._tabs.widget(i)
            if isinstance(v, FilteredLogView):
                if v._resize_frozen:
                    v.set_resize_frozen(False)
                    from PySide6.QtCore import QSize
                    from PySide6.QtGui import QResizeEvent
                    v.resizeEvent(
                        QResizeEvent(v.size(), QSize())
                    )


    def _rebind_shortcuts(self):
        """从配置读取快捷键并绑定到 QAction"""
        sc = self._cfg.get("shortcuts", {})
        self._act_close_tab.setShortcut(
            QKeySequence(
                sc.get("close_tab", "Ctrl+W")
            )
        )
        self._act_goto_line.setShortcut(
            QKeySequence(
                sc.get("goto_line", "Ctrl+G")
            )
        )
        self._act_send.setShortcut(
            QKeySequence(
                sc.get("send", "Ctrl+Return")
            )
        )

    # ── ★ v0.44: 首次显示匹配设置按钮尺寸 ──
    def showEvent(self, event):
        super().showEvent(event)
        self._btn_settings.match_native_size(
            self.titleBar.maxBtn
        )

    # ── ★ v0.44: Snap Layout（nativeEvent 覆写）──
    def nativeEvent(self, eventType, message):
        """拦截 WM_NCHITTEST → maxBtn 返回 HTMAXBUTTON"""
        if eventType == b"windows_generic_MSG":
            try:
                msg = ctypes.wintypes.MSG.from_address(
                    int(message)
                )
                if not msg.hWnd:
                    return super().nativeEvent(
                        eventType, message
                    )
                # WM_NCHITTEST
                if msg.message == 0x0084:
                    if self._isHoverMaxBtn():
                        self.titleBar.maxBtn.setProperty(
                            "_custom_hover", True
                        )
                        self.titleBar.maxBtn.update()
                        return True, 9  # HTMAXBUTTON
                # WM_NCMOUSELEAVE / WM_MOUSELEAVE
                elif msg.message in (0x02A2, 0x02A3):
                    self.titleBar.maxBtn.setProperty(
                        "_custom_hover", False
                    )
                    self.titleBar.maxBtn.setProperty(
                        "_custom_press", False
                    )
                    self.titleBar.maxBtn.update()
                # WM_NCLBUTTONDOWN / WM_NCLBUTTONDBLCLK
                elif msg.message in (0x00A1, 0x00A3):
                    if self._isHoverMaxBtn():
                        QApplication.sendEvent(
                            self.titleBar.maxBtn,
                            QMouseEvent(
                                QEvent.Type.MouseButtonPress,
                                QPoint(),
                                Qt.MouseButton.LeftButton,
                                Qt.MouseButton.LeftButton,
                                Qt.KeyboardModifier.NoModifier,
                            ),
                        )
                        return True, 0
                # WM_NCLBUTTONUP / WM_NCRBUTTONUP
                elif msg.message in (0x00A2, 0x00A5):
                    if self._isHoverMaxBtn():
                        QApplication.sendEvent(
                            self.titleBar.maxBtn,
                            QMouseEvent(
                                QEvent.Type.MouseButtonRelease,
                                QPoint(),
                                Qt.MouseButton.LeftButton,
                                Qt.MouseButton.LeftButton,
                                Qt.KeyboardModifier.NoModifier,
                            ),
                        )
            except Exception:
                pass
        return super().nativeEvent(eventType, message)

    def _isHoverMaxBtn(self):
        pos = (
            QCursor.pos()
            - self.geometry().topLeft()
            - self.titleBar.pos()
        )
        return (
            self.titleBar.childAt(pos)
            is self.titleBar.maxBtn
        )

    def _open_settings(self):
        tab_names = self._filter_mgr.get_tab_names()
        dlg = SettingsDialog(
            self._cfg, tab_names, parent=self
        )
        # ★ v0.5: 实时刷新外部日志区高亮（修改即更新）
        dlg.highlight_changed.connect(
            lambda: self._filter_mgr.refresh_highlighter(
                self._cfg
            )
        )
        # ★ v0.6 fix: 字号变化走专用通路，不触发 rehighlight
        dlg.font_size_changed.connect(
            lambda sz: self._filter_mgr.update_font_size(sz)
        )
        # ★ v0.6: 自动换行走专用通路
        dlg.word_wrap_changed.connect(
            lambda on: self._filter_mgr.update_word_wrap(on)
        )
        # ★ v0.6: 最大行数走专用通路
        dlg.max_lines_changed.connect(
            lambda n: self._filter_mgr.update_max_lines(n)
        )
        # ★ v0.69: 行号显示开关
        dlg.show_line_numbers_changed.connect(
            lambda v: self._filter_mgr.set_line_numbers_visible(v)
        )
        dlg.exec()
        # ★ v0.6: 设置关闭后只更新配置，不 rehighlight 已有日志
        self._filter_mgr.update_highlighter_config(self._cfg)
        # ★ v0.63: 重新绑定快捷键
        self._rebind_shortcuts()
        # ★ fix: 设置关闭后同步日志录制状态
        log_on = self._cfg.get("logging", {}).get(
            "enabled", False
        )
        if (
            self._connected
            and log_on
            and not self._log_mgr.is_recording
        ):
            p = self._get_port()
            desc = self._get_port_description()
            self._log_mgr.start_session(p, desc)
            if self._log_mgr.is_recording:
                self._filter_mgr.append_info(
                    f"日志录制已开始: "
                    f"{self._log_mgr.session_dir}"
                )
        elif (
            self._connected
            and not log_on
            and self._log_mgr.is_recording
        ):
            self._log_mgr.stop_session()
            self._filter_mgr.append_info(
                "日志录制已停止"
            )

    def _on_log_error(self, msg):
        self._lbl_log_err.setText(
            "自动保存写入失败！"
        )
        self._lbl_log_err.show()
        QTimer.singleShot(5000, self._lbl_log_err.hide)

    def _save_as_tab(self, tab_name):
        content = self._filter_mgr.get_tab_content(
            tab_name
        )
        if not content:
            InfoPopup(
                "当前 Tab 没有内容", self
            ).exec()
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            f"另存为 — {tab_name}",
            f"{tab_name}.log",
            "Log Files (*.log);;"
            "Text Files (*.txt);;"
            "All Files (*)",
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as e:
                InfoPopup(
                    f"保存失败：{e}", self
                ).exec()

    def _toggle_send_area(self):
        self._send_visible = not self._send_visible
        self._send_area.setVisible(self._send_visible)
        self._filter_mgr.update_toggle_btn(
            self._send_visible
        )

    def _wire(self):
        self._serial.data_received.connect(self._on_rx)
        self._serial.error_occurred.connect(self._on_err)
        self._serial.connection_changed.connect(
            self._on_conn_changed
        )
        self._btn_conn.clicked.connect(self._toggle_conn)
        self._btn_send.clicked.connect(self._do_send)
        self._btn_clear.clicked.connect(self._on_clear)
        self._chk_hex_rx.toggled.connect(
            self._filter_mgr.set_show_hex
        )
        self._chk_ts.toggled.connect(
            self._spin_ts.setEnabled
        )
        self._chk_loop.toggled.connect(
            self._spin_ms.setEnabled
        )
        self._chk_loop.toggled.connect(
            self._on_loop_toggled
        )
        self._btn_clear.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._btn_clear.customContextMenuRequested.connect(
            self._on_clear_context_menu
        )
        self._filter_mgr.set_log_callbacks(
            self._log_mgr.write_line,
            self._log_mgr.close_tab,
        )
        self._filter_mgr.set_save_as_callback(
            self._save_as_tab
        )
        # ★ v0.62: hover 按钮 + 关闭 Tab 信号
        self._filter_mgr.tab_close_requested.connect(
            self._on_close_tab
        )
        self._filter_mgr.hover_clear_requested.connect(
            self._on_hover_clear
        )

    def _on_clear_context_menu(self, pos):
        menu = RoundedMenu(self.window())
        act = menu.addAction("清空所有")
        act.triggered.connect(self._on_clear_all)
        menu.exec(
            self._btn_clear.mapToGlobal(pos)
        )

    def _on_clear(self):
        if self._cfg.get("ui", {}).get(
            "confirm_clear", True
        ):
            dlg = ConfirmPopup(
                "确定要清空当前日志吗？",
                show_dont_ask=True,
                parent=self,
            )
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            if dlg.dont_ask_again():
                self._cfg.setdefault("ui", {})[
                    "confirm_clear"
                ] = False
                save_config(self._cfg)
        self._filter_mgr.clear_main_and_current()

    def _on_clear_all(self):
        if self._cfg.get("ui", {}).get(
            "confirm_clear", True
        ):
            dlg = ConfirmPopup(
                "确定要清空所有日志吗？",
                show_dont_ask=True,
                parent=self,
            )
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            if dlg.dont_ask_again():
                self._cfg.setdefault("ui", {})[
                    "confirm_clear"
                ] = False
                save_config(self._cfg)
        self._filter_mgr.clear_all()

    def _on_close_tab(self, idx):
        """★ v0.62: 关闭 Tab 确认"""
        name = self._filter_mgr._tabs.tabText(
            idx
        ).strip()
        if name in ("main", "+"):
            return
        if self._cfg.get("ui", {}).get(
            "confirm_close_tab", True
        ):
            dlg = ConfirmPopup(
                f"确定要关闭「{name}」吗？",
                show_dont_ask=True,
                parent=self,
            )
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            if dlg.dont_ask_again():
                self._cfg.setdefault("ui", {})[
                    "confirm_close_tab"
                ] = False
                save_config(self._cfg)
        self._filter_mgr.force_close_tab(idx)

    def _on_hover_clear(self):
        """★ v0.62: hover 清空按钮 → 只清空当前 Tab"""
        if self._cfg.get("ui", {}).get(
            "confirm_clear", True
        ):
            dlg = ConfirmPopup(
                "确定要清空当前日志吗？",
                show_dont_ask=True,
                parent=self,
            )
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            if dlg.dont_ask_again():
                self._cfg.setdefault("ui", {})[
                    "confirm_clear"
                ] = False
                save_config(self._cfg)
        self._filter_mgr.clear_current()

    def _on_goto_line(self):
        """★ v0.62: Ctrl+G 跳转行号（非模态）"""
        v = self._filter_mgr._tabs.currentWidget()
        if not isinstance(v, FilteredLogView):
            return
        total = v.document().blockCount()
        # 已打开则关闭重建（行数可能变了）
        old = getattr(self, '_goto_dlg', None)
        try:
            if old is not None and old.isVisible():
                old.close()
        except RuntimeError:
            pass
        self._goto_dlg = None
        dlg = InputIntPopup(
            f"跳转行号（共 {total} 行）",
            value=1, min_val=1, max_val=999999,
            btn_text="跳转",
            parent=self,
        )
        def _do_goto(line):
            cur = self._filter_mgr._tabs.currentWidget()
            if isinstance(cur, FilteredLogView):
                t = cur.document().blockCount()
                self._filter_mgr.goto_line_current(
                    min(line, t)
                )
        dlg.value_accepted.connect(_do_goto)
        dlg.destroyed.connect(
            lambda: setattr(self, '_goto_dlg', None)
        )
        self._goto_dlg = dlg
        dlg.show()

    def eventFilter(self, obj, event):
        if (
            obj is self._send_edit
            and event.type() == QEvent.Type.KeyPress
        ):
            k, m = event.key(), event.modifiers()
            if (
                k == Qt.Key.Key_Return
                and m & Qt.KeyboardModifier.ControlModifier
            ):
                self._do_send()
                return True
            if self._chk_enter.isChecked():
                if (
                    k in (Qt.Key.Key_Return,
                          Qt.Key.Key_Enter)
                    and not m
                ):
                    self._do_send()
                    return True
        return super().eventFilter(obj, event)

    def _scan_ports(self):
        if self._connected:
            return
        ports = SerialManager.list_ports()
        if ports == self._known_ports:
            return
        self._known_ports = ports
        prev = self._cb_port.currentData() or ""
        self._cb_port.blockSignals(True)
        self._cb_port.clear()
        if ports:
            for info in SerialManager.get_port_info():
                desc = info["description"]
                label = (
                    f"{info['device']}  {desc}"
                    if desc else info["device"]
                )
                self._cb_port.addItem(
                    label, userData=info["device"]
                )
            for i in range(self._cb_port.count()):
                if self._cb_port.itemData(i) == prev:
                    self._cb_port.setCurrentIndex(i)
                    break
        else:
            self._cb_port.addItem(
                "（无可用端口）", userData=""
            )
        self._cb_port.blockSignals(False)

    def _get_port(self):
        d = self._cb_port.currentData()
        return d if d else ""

    def _get_port_description(self):
        text = self._cb_port.currentText()
        parts = text.split("  ", 1)
        return (
            parts[1].strip() if len(parts) > 1 else ""
        )

    def _toggle_conn(self):
        if self._connected:
            self._do_disconnect()
        else:
            self._do_connect()

    def _do_connect(self):
        port = self._get_port()
        if not port:
            InfoPopup(
                "请先选择有效的串口端口",
                self,
            ).exec()
            return
        ok, msg = self._serial.connect(
            port, int(self._cb_baud.currentText())
        )
        if ok:
            self._filter_mgr.append_info(msg)
        else:
            self._filter_mgr.append_error(msg)
            InfoPopup(
                f"连接失败：{msg}", self
            ).exec()

    def _do_disconnect(self):
        if self._loop_timer.isActive():
            self._loop_timer.stop()
            self._chk_loop.setChecked(False)
        _, msg = self._serial.disconnect()
        self._filter_mgr.append_info(msg)

    def _do_send(self):
        if not self._connected:
            return
        text = self._send_edit.toPlainText()
        if not text:
            return
        try:
            if self._chk_hex_tx.isChecked():
                hs = (
                    text.replace(" ", "")
                    .replace("\n", "")
                    .replace("\r", "")
                )
                if len(hs) % 2:
                    self._filter_mgr.append_error(
                        "HEX 格式错误：字节数不完整"
                    )
                    return
                data = bytes.fromhex(hs)
            else:
                if self._chk_nl.isChecked():
                    text = (
                        text.rstrip("\r\n") + "\r\n"
                    )
                data = text.encode("utf-8")
            ok, msg = self._serial.send(data)
            if ok:
                self._filter_mgr.append_sent(data)
            else:
                self._filter_mgr.append_error(msg)
        except ValueError as e:
            self._filter_mgr.append_error(
                f"HEX 解析错误: {e}"
            )

    def _on_rx(self, data):
        if self._chk_ts.isChecked():
            try:
                ts = datetime.now().strftime(
                    "[%H:%M:%S.%f"
                )[:-3] + "] "
                txt = data.decode(
                    "utf-8", errors="replace"
                )
                data = "\n".join(
                    (ts + l) if l else l
                    for l in txt.split("\n")
                ).encode()
            except Exception:
                pass
        self._filter_mgr.append_data(data)

    def _on_err(self, msg):
        self._filter_mgr.append_error(msg)

    def _on_conn_changed(self, connected):
        self._connected = connected
        if connected:
            self._set_dot(True)
            self._btn_conn.setText("断  开")
            self._btn_conn.setObjectName(
                "BtnDisconnect"
            )
            self._btn_conn.style().unpolish(
                self._btn_conn
            )
            self._btn_conn.style().polish(
                self._btn_conn
            )
            self._cb_port.setEnabled(False)
            self._cb_baud.setEnabled(False)
            self._btn_send.setEnabled(True)
            self._start_time = datetime.now()
            self._serial.reset_counters()
            self._last_rx = self._last_tx = 0
            p = self._get_port()
            b = self._cb_baud.currentText()
            self._lbl_status.setText(
                f"已连接  {p}  @  {b} bps"
            )
            desc = self._get_port_description()
            self._log_mgr.start_session(p, desc)
            if self._log_mgr.is_recording:
                self._filter_mgr.append_info(
                    f"日志录制中: "
                    f"{self._log_mgr.session_dir}"
                )
        else:
            self._set_dot(False)
            self._btn_conn.setText("连  接")
            self._btn_conn.setObjectName("BtnConnect")
            self._btn_conn.style().unpolish(
                self._btn_conn
            )
            self._btn_conn.style().polish(
                self._btn_conn
            )
            self._cb_port.setEnabled(True)
            self._cb_baud.setEnabled(True)
            self._btn_send.setEnabled(False)
            self._start_time = None
            self._lbl_status.setText("已断开")
            self._log_mgr.stop_session()

    def _set_dot(self, on):
        n = "DotOn" if on else "DotOff"
        self._dot.setObjectName(n)
        self._dot.style().unpolish(self._dot)
        self._dot.style().polish(self._dot)

    def _on_baud_changed(self, idx):
        text = self._cb_baud.itemText(idx)
        if text != "自定义...":
            return
        dlg = InputTextPopup(
            "请输入波特率（整数）",
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            self._cb_baud.blockSignals(True)
            self._cb_baud.setCurrentIndex(
                max(0, idx - 1)
            )
            self._cb_baud.blockSignals(False)
            return
        val = dlg.get_text()
        if not val or not val.strip():
            self._cb_baud.blockSignals(True)
            self._cb_baud.setCurrentIndex(
                max(0, idx - 1)
            )
            self._cb_baud.blockSignals(False)
            return
        try:
            baud = int(val.strip())
            if baud <= 0:
                raise ValueError
        except ValueError:
            InfoPopup(
                "波特率必须是正整数", self
            ).exec()
            self._cb_baud.blockSignals(True)
            self._cb_baud.setCurrentIndex(
                max(0, idx - 1)
            )
            self._cb_baud.blockSignals(False)
            return
        existing = self._cb_baud.findText(str(baud))
        if existing >= 0:
            self._cb_baud.blockSignals(True)
            self._cb_baud.setCurrentIndex(existing)
            self._cb_baud.blockSignals(False)
            return
        insert_pos = 0
        for i in range(
            self._cb_baud.count() - 1
        ):
            try:
                if (
                    int(self._cb_baud.itemText(i))
                    < baud
                ):
                    insert_pos = i + 1
            except ValueError:
                pass
        self._cb_baud.blockSignals(True)
        self._cb_baud.insertItem(
            insert_pos, str(baud)
        )
        self._cb_baud.setCurrentIndex(insert_pos)
        self._cb_baud.blockSignals(False)
        if (
            "custom_baudrates"
            not in self._cfg["serial"]
        ):
            self._cfg["serial"][
                "custom_baudrates"
            ] = []
        if (
            baud
            not in self._cfg["serial"][
                "custom_baudrates"
            ]
        ):
            self._cfg["serial"][
                "custom_baudrates"
            ].append(baud)
            self._cfg["serial"][
                "custom_baudrates"
            ].sort()
            save_config(self._cfg)

    def _on_loop_toggled(self, checked):
        if checked and self._connected:
            self._loop_timer.start(
                self._spin_ms.value()
            )
        else:
            self._loop_timer.stop()

    def _refresh_stat(self):
        rx = self._serial.rx_bytes
        tx = self._serial.tx_bytes
        rr, tr = rx - self._last_rx, tx - self._last_tx
        self._last_rx, self._last_tx = rx, tx
        self._lbl_rx.setText(f"RX: {self._fmt(rx)}")
        self._lbl_tx.setText(f"TX: {self._fmt(tx)}")
        self._lbl_rx_rate.setText(
            f"↓ {self._fmt(rr)}/s"
        )
        self._lbl_tx_rate.setText(
            f"↑ {self._fmt(tr)}/s"
        )
        if self._start_time:
            s = int(
                (datetime.now() - self._start_time)
                .total_seconds()
            )
            h, r = divmod(s, 3600)
            m, s = divmod(r, 60)
            self._lbl_timer.setText(
                f"{h:02d}:{m:02d}:{s:02d}"
            )
        else:
            self._lbl_timer.setText("00:00:00")

    @staticmethod
    def _fmt(n):
        if n < 1024:
            return f"{n} B"
        if n < 1048576:
            return f"{n/1024:.1f} KB"
        return f"{n/1048576:.2f} MB"

    def closeEvent(self, event):
        # ★ v0.6: 先关闭所有打开的模态对话框
        for child in self.findChildren(QDialog):
            if child.isVisible():
                child.close()
        self._port_timer.stop()
        self._stat_timer.stop()
        if self._loop_timer.isActive():
            self._loop_timer.stop()
        self._log_mgr.stop_session()
        if self._connected:
            self._serial.disconnect()
        cur_text = self._cb_baud.currentText()
        if cur_text != "自定义...":
            try:
                self._cfg["serial"]["baudrate"] = (
                    int(cur_text)
                )
            except ValueError:
                pass
        self._cfg["serial"]["port"] = self._get_port()
        self._cfg["send"]["add_newline"] = (
            self._chk_nl.isChecked()
        )
        self._cfg["ui"]["window_width"] = self.width()
        self._cfg["ui"]["window_height"] = self.height()
        save_config(self._cfg)
        event.accept()


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("SerialAssistant")
    app.setStyleSheet(STYLE)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()