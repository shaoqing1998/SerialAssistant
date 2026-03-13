"""
main.py - 串口调试助手 v1.6
"""

import sys
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QGridLayout,
    QComboBox, QPushButton, QLabel,
    QCheckBox, QSizePolicy,
    QMessageBox, QSpinBox, QStyledItemDelegate,
    QInputDialog,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QMouseEvent

from config import load_config, save_config
from serial_manager import SerialManager
from filter_manager import FilterManager
from rounded_menu import RoundedMenu, RoundedContextTextEdit


# ── 全局对齐边距
_M = 10   # px

# 选项区宽度：列0(72)+sp(6)+列1(64)+sp(6)+ms(20) = 168px，留余量到 176px
_OPTS_W = 176
# 按钮宽度
_BTN_W = 72
# 筛选栏右侧容器宽度 = opts + spacing + btns
_RIGHT_W = _OPTS_W + 8 + _BTN_W   # = 250px


class _CenterDelegate(QStyledItemDelegate):
    """让 QComboBox 下拉列表项居中"""
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignmentFlag.AlignCenter


class _BaudComboBox(QComboBox):
    """
    波特率下拉框：
    - 不使用 setEditable，避免 lineEdit 拦截鼠标事件
    - 重写 paintEvent 绘制居中文字
    - 重写 mousePressEvent 点击任何位置都弹出下拉
    """
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.showPopup()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event):
        from PySide6.QtWidgets import QStylePainter, QStyleOptionComboBox, QStyle
        painter = QStylePainter(self)
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        # 清空默认文字，避免重复绘制
        opt.currentText = ""
        # 画框体（含下拉箭头），不画文字
        painter.drawComplexControl(QStyle.ComplexControl.CC_ComboBox, opt)
        # 在整个控件矩形内居中绘制文字（下拉箭头独立绘制，不影响视觉居中）
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.currentText())


STYLE = """
* { outline: none; }

QMainWindow, QWidget#AppRoot {
    background-color: #eef0f3;
    color: #1f2937;
    font-family: "Microsoft YaHei UI", "PingFang SC", "Segoe UI", sans-serif;
    font-size: 13px;
}

QWidget {
    color: #1f2937;
    font-family: "Microsoft YaHei UI", "PingFang SC", "Segoe UI", sans-serif;
    font-size: 13px;
}

/* ── 下拉框 ── */
QComboBox {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 0 8px 0 8px;
    min-height: 28px;
    color: #1f2937;
    font-size: 13px;
    selection-background-color: #dbeafe;
}
QComboBox:hover  { background: #f3f4f6; border-color: #9ca3af; }
QComboBox:focus  { border-color: #3b82f6; }
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 18px;
    border: none;
}
QComboBox::down-arrow {
    width: 8px; height: 5px;
    image: url("data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' width='8' height='5'><polygon points='0,0 8,0 4,5' fill='%236b7280'/></svg>");
}
QComboBox QAbstractItemView {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    selection-background-color: #dbeafe;
    selection-color: #1d4ed8;
    padding: 2px;
    outline: none;
}

/* ── 按钮基础 ── */
QPushButton {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    color: #374151;
    font-size: 13px;
    padding: 0 12px;
    min-height: 28px;
    min-width: 52px;
}
QPushButton:hover   { background: #f0f4ff; border-color: #93c5fd; color: #1d4ed8; }
QPushButton:pressed { background: #dbeafe; }
QPushButton:disabled { background: #f3f4f6; border-color: #e5e7eb; color: #d1d5db; }

QPushButton#BtnConnect {
    background: #2563eb; border: none; border-radius: 6px;
    color: #fff; font-weight: 600; min-height: 28px; min-width: 80px; padding: 0 14px;
}
QPushButton#BtnConnect:hover   { background: #3b82f6; }
QPushButton#BtnConnect:pressed { background: #1d4ed8; }

QPushButton#BtnDisconnect {
    background: #6b7280; border: none; border-radius: 6px;
    color: #fff; font-weight: 600; min-height: 28px; min-width: 80px; padding: 0 14px;
}
QPushButton#BtnDisconnect:hover   { background: #9ca3af; }
QPushButton#BtnDisconnect:pressed { background: #4b5563; }

/* 发送/清空按钮：min-height/min-width 清零，由 setFixedHeight 控制 */
QPushButton#BtnSend {
    background: #16a34a; border: none; border-radius: 6px;
    color: #fff; font-weight: 600; padding: 0;
    min-height: 0; min-width: 0;
}
QPushButton#BtnSend:hover   { background: #22c55e; }
QPushButton#BtnSend:pressed { background: #15803d; }
QPushButton#BtnSend:disabled { background: #d1fae5; color: #6ee7b7; border: none; }

QPushButton#BtnClear {
    background: #ffffff; border: 1px solid #d1d5db; border-radius: 6px;
    color: #6b7280; padding: 0;
    min-height: 0; min-width: 0;
}
QPushButton#BtnClear:hover { background: #fef3c7; border-color: #fbbf24; color: #b45309; }

QPushButton#BtnRefilter {
    background: #ffffff; border: 1px solid #d1d5db; border-radius: 6px;
    color: #374151; min-height: 26px; padding: 0 10px; font-size: 12px;
}
QPushButton#BtnRefilter:hover { background: #faf5ff; border-color: #c084fc; color: #7c3aed; }
QPushButton#BtnRefilter:disabled { background: #f3f4f6; border-color: #e5e7eb; color: #d1d5db; }

/* 隐藏/显示发送区（正方形 28×28） */
QPushButton#BtnToggleSend {
    background: transparent; border: none; border-radius: 4px;
    color: #9ca3af; font-size: 14px;
    min-width: 28px; max-width: 28px;
    min-height: 28px; max-height: 28px;
    padding: 0;
}
QPushButton#BtnToggleSend:hover { background: #e5e7eb; color: #2563eb; }

QPushButton#BtnTabClose {
    background: transparent; border: none; border-radius: 3px;
    color: #d1d5db; font-size: 11px; font-weight: 700;
    min-width: 14px; max-width: 14px; min-height: 14px; max-height: 14px; padding: 0;
}
QPushButton#BtnTabClose:hover { background: #fee2e2; color: #dc2626; }

/* ── TabWidget：无边框无灰线 ── */
QTabWidget { background: transparent; border: none; }
QTabWidget::pane { border: none; background: transparent; margin: 0; padding: 0; }
QTabBar { background: transparent; border: none; qproperty-drawBase: 0; }
QTabBar::tab {
    background: transparent;
    color: #6b7280;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 5px 0px 5px 0px;
    margin: 0 8px 0 0;
    min-width: 0px;
    font-size: 12px;
}
QTabBar::tab:selected {
    color: #2563eb;
    border-bottom: 2px solid transparent;
    font-weight: 600;
}
QTabBar::tab:hover:!selected { color: #3b82f6; }

/* ── 文本框 ── */
QTextEdit {
    background: #ffffff;
    color: #1e293b;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    selection-background-color: #bfdbfe;
    selection-color: #1e3a8a;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
}

QWidget#FilterBar { background: transparent; }

/* ── 关键词输入框 ── */
QLineEdit#KwEdit {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 0 9px;
    min-height: 26px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    color: #1f2937;
}
QLineEdit#KwEdit:focus    { border-color: #3b82f6; }
QLineEdit#KwEdit:disabled { background: #f3f4f6; color: #d1d5db; border-color: #e5e7eb; }

QTextEdit#SendEdit {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    color: #1f2937;
    padding: 4px 6px;
}
QTextEdit#SendEdit:focus { border-color: #3b82f6; }

QCheckBox {
    color: #374151; spacing: 5px; font-size: 12px; background: transparent;
}
QCheckBox::indicator {
    width: 14px; height: 14px;
    border: 1.5px solid #9ca3af; border-radius: 3px; background: #ffffff;
}
QCheckBox::indicator:checked  { background: #2563eb; border-color: #2563eb; }
QCheckBox::indicator:hover    { border-color: #3b82f6; }
QCheckBox:disabled            { color: #d1d5db; }
QCheckBox::indicator:disabled { background: #f3f4f6; border-color: #e5e7eb; }

QLabel { color: #374151; background: transparent; }
QLabel#DotOn  { color: #16a34a; font-size: 13px; }
QLabel#DotOff { color: #d1d5db; font-size: 13px; }

/* ── 状态栏 ── */
QStatusBar {
    background: #eef0f3; color: #6b7280;
    font-size: 12px; border: none; min-height: 22px;
}
QStatusBar::item { border: none; }
QStatusBar QLabel { color: #6b7280; padding: 0 6px; font-size: 12px; background: transparent; border: none; }

QSpinBox {
    background: #ffffff; border: 1px solid #d1d5db; border-radius: 6px;
    padding: 0 4px; min-height: 24px; color: #1f2937; font-size: 12px;
}
QSpinBox:focus    { border-color: #3b82f6; }
QSpinBox:disabled { background: #f3f4f6; color: #d1d5db; border-color: #e5e7eb; }
QSpinBox::up-button, QSpinBox::down-button { width: 14px; border: none; background: transparent; }

QScrollBar:vertical   { background: transparent; width: 6px; }
QScrollBar:horizontal { background: transparent; height: 6px; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #d1d5db; border-radius: 3px; min-height: 20px;
}
QScrollBar::handle:vertical:hover,
QScrollBar::handle:horizontal:hover { background: #3b82f6; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }

"""


class MainWindow(QMainWindow):

    BAUDRATES = ["1200","2400","4800","9600","14400",
                 "19200","38400","57600","115200",
                 "230400","460800","921600"]

    def __init__(self):
        super().__init__()
        self._cfg = load_config()
        self._serial = SerialManager()
        self._connected = False
        self._start_time: datetime | None = None
        self._last_rx = self._last_tx = 0
        self._known_ports: list[str] = []
        self._send_visible = True

        self._build_ui()

        self._port_timer = QTimer(self)
        self._port_timer.timeout.connect(self._scan_ports)
        self._port_timer.start(800)

        self._stat_timer = QTimer(self)
        self._stat_timer.timeout.connect(self._refresh_stat)
        self._stat_timer.start(1000)

        self._scan_ports()
        self._wire()

    # ══ 构建 UI ════════════════════════════════

    def _build_ui(self):
        self.setWindowTitle("串口调试助手  v1.6")
        self.resize(self._cfg["ui"]["window_width"],
                    self._cfg["ui"]["window_height"])
        self.setMinimumSize(900, 520)

        root = QWidget()
        root.setObjectName("AppRoot")
        self.setCentralWidget(root)
        vbox = QVBoxLayout(root)
        vbox.setContentsMargins(_M, 8, _M, 4)
        vbox.setSpacing(4)

        vbox.addWidget(self._make_toolbar())
        self._filter_mgr = FilterManager(
            self._cfg,
            h_margin=0,
            toggle_send_callback=self._toggle_send_area
        )
        vbox.addWidget(self._filter_mgr, stretch=1)
        self._send_area = self._make_send_area()
        vbox.addWidget(self._send_area)
        self._make_statusbar()

    # ── 顶部工具栏 ────────────────────────────
    def _make_toolbar(self) -> QWidget:
        bar = QWidget()
        h = QHBoxLayout(bar)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)

        self._cb_port = QComboBox()
        self._cb_port.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._cb_port.setMinimumWidth(200)
        self._cb_port.setToolTip("串口端口（自动实时扫描）")
        h.addWidget(self._cb_port, stretch=1)

        # 波特率：自定义 ComboBox，点击任何位置都弹出下拉，重写 paintEvent 居中显示
        self._cb_baud = _BaudComboBox()
        # 加载自定义波特率（从 config 中读取）
        custom_bauds = self._cfg.get("serial", {}).get("custom_baudrates", [])
        all_bauds = sorted(set(int(b) for b in self.BAUDRATES) | set(custom_bauds))
        for b in all_bauds:
            self._cb_baud.addItem(str(b))
        self._cb_baud.addItem("自定义...")
        # 恢复上次选择
        saved = str(self._cfg["serial"]["baudrate"])
        idx = self._cb_baud.findText(saved)
        if idx >= 0:
            self._cb_baud.setCurrentIndex(idx)
        self._cb_baud.setFixedWidth(80)
        self._cb_baud.setToolTip("波特率（点击选择，可自定义）")
        self._cb_baud.setItemDelegate(_CenterDelegate(self._cb_baud))
        self._cb_baud.currentIndexChanged.connect(self._on_baud_changed)
        h.addWidget(self._cb_baud)

        self._dot = QLabel("●")
        self._dot.setObjectName("DotOff")
        self._dot.setFixedWidth(14)
        self._dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.addWidget(self._dot)

        self._btn_conn = QPushButton("连  接")
        self._btn_conn.setObjectName("BtnConnect")
        h.addWidget(self._btn_conn)

        return bar

    # ── 发送区 ────────────────────────────────
    def _make_send_area(self) -> QWidget:
        """
        发送区高度 120px，布局：
        [发送框 stretch=1] | [选项区 固定宽度 _OPTS_W] | [发送/清空按钮 固定高度，宽度撑满]

        选项区 4 行，用 addStretch(1) 均匀分布，整体垂直居中
        发送/清空按钮：固定高度 BTN_H，宽度由 SizePolicy.Expanding 撑满剩余空间
        """
        AREA_H = 120
        area = QWidget()
        area.setFixedHeight(AREA_H)

        h = QHBoxLayout(area)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)

        # 左：发送输入框（stretch=1）
        self._send_edit = RoundedContextTextEdit()
        self._send_edit.setObjectName("SendEdit")
        self._send_edit.setPlaceholderText("输入发送内容…（Ctrl+Enter 发送）")
        mono = QFont("Consolas", 11)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self._send_edit.setFont(mono)
        self._send_edit.installEventFilter(self)
        h.addWidget(self._send_edit, stretch=1)

        # 中：选项区（QGridLayout，第二列左对齐）
        # 行0: □时间戳    [SpinBox] ms
        # 行1: □循环发送  [SpinBox] ms
        # 行2: □HEX显示   □HEX发送
        # 行3: □回车发送  □追加换行
        SPIN_W = 64   # SpinBox 宽度（足够显示4位数+上下箭头，修复截断）

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
        grid.setColumnMinimumWidth(0, 72)
        grid.setColumnStretch(2, 1)
        ROW_H = 24
        for r in range(4):
            grid.setRowMinimumHeight(r, ROW_H)

        # 行0：□时间戳  [SpinBox] ms
        self._chk_ts = QCheckBox("时间戳")
        self._spin_ts = QSpinBox()
        self._spin_ts.setRange(10, 9999); self._spin_ts.setValue(100)
        self._spin_ts.setFixedWidth(SPIN_W)
        self._spin_ts.setEnabled(False)
        self._spin_ts.setToolTip("超时时间：超过此时间无数据则换行")
        lbl_ts = QLabel("ms"); lbl_ts.setStyleSheet("color:#9ca3af;font-size:12px;")
        grid.addWidget(self._chk_ts,  0, 0, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        grid.addWidget(self._spin_ts, 0, 1, Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(lbl_ts,        0, 2, Qt.AlignmentFlag.AlignVCenter)

        # 行1：□循环发送 [SpinBox] ms
        self._chk_loop = QCheckBox("循环发送")
        self._spin_ms = QSpinBox()
        self._spin_ms.setRange(50, 99999); self._spin_ms.setValue(200)
        self._spin_ms.setFixedWidth(SPIN_W)
        self._spin_ms.setEnabled(False)
        lbl_ms = QLabel("ms"); lbl_ms.setStyleSheet("color:#9ca3af;font-size:12px;")
        grid.addWidget(self._chk_loop, 1, 0, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        grid.addWidget(self._spin_ms,  1, 1, Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(lbl_ms,         1, 2, Qt.AlignmentFlag.AlignVCenter)

        # 行2：□HEX显示  □HEX发送（第1列对齐SpinBox左边缘）
        self._chk_hex_rx = QCheckBox("HEX 显示")
        self._chk_hex_tx = QCheckBox("HEX 发送")
        grid.addWidget(self._chk_hex_rx, 2, 0, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        grid.addWidget(self._chk_hex_tx, 2, 1, 1, 2, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        # 行3：□回车发送  □追加换行
        self._chk_enter = QCheckBox("回车发送")
        self._chk_nl = QCheckBox("追加换行")
        self._chk_nl.setChecked(self._cfg["send"].get("add_newline", True))
        grid.addWidget(self._chk_enter, 3, 0, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        grid.addWidget(self._chk_nl,    3, 1, 1, 2, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        opts_v.addLayout(grid)
        opts_v.addStretch(1)
        h.addWidget(opts_container)

        # 右：发送/清空按钮（固定尺寸，与原版一致）
        BTN_H = (AREA_H - 4) // 2   # 4 = spacing between buttons

        self._btn_send = QPushButton("发送")
        self._btn_send.setObjectName("BtnSend")
        self._btn_send.setEnabled(False)
        self._btn_send.setFixedSize(_BTN_W, BTN_H)

        self._btn_clear = QPushButton("清空")
        self._btn_clear.setObjectName("BtnClear")
        self._btn_clear.setFixedSize(_BTN_W, BTN_H)
        self._btn_clear.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

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

    # ── 状态栏 ────────────────────────────────
    def _make_statusbar(self):
        sb = self.statusBar()
        sb.setSizeGripEnabled(False)
        self._lbl_status  = QLabel("就绪")
        self._lbl_timer   = QLabel("00:00:00")
        self._lbl_tx      = QLabel("TX: 0 B")
        self._lbl_rx      = QLabel("RX: 0 B")
        self._lbl_tx_rate = QLabel("↑ 0 B/s")
        self._lbl_rx_rate = QLabel("↓ 0 B/s")
        sb.addWidget(self._lbl_status, 1)
        for w in (self._lbl_timer, self._lbl_tx, self._lbl_rx,
                  self._lbl_tx_rate, self._lbl_rx_rate):
            sb.addPermanentWidget(w)

    def _toggle_send_area(self):
        self._send_visible = not self._send_visible
        self._send_area.setVisible(self._send_visible)
        self._filter_mgr.update_toggle_btn(self._send_visible)

    # ══ 信号连接 ═══════════════════════════════

    def _wire(self):
        self._serial.data_received.connect(self._on_rx)
        self._serial.error_occurred.connect(self._on_err)
        self._serial.connection_changed.connect(self._on_conn_changed)
        self._btn_conn.clicked.connect(self._toggle_conn)
        self._btn_send.clicked.connect(self._do_send)
        self._btn_clear.clicked.connect(self._filter_mgr.clear_main_and_current)
        self._chk_hex_rx.toggled.connect(self._filter_mgr.set_show_hex)
        self._chk_ts.toggled.connect(self._spin_ts.setEnabled)
        self._chk_loop.toggled.connect(self._spin_ms.setEnabled)
        self._chk_loop.toggled.connect(self._on_loop_toggled)
        self._btn_clear.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._btn_clear.customContextMenuRequested.connect(self._on_clear_context_menu)

    def _on_clear_context_menu(self, pos):
        """清空按钮右键菜单（Win11 风格）"""
        menu = RoundedMenu(self.window())
        act_clear_all = menu.addAction("清空所有")
        act_clear_all.triggered.connect(self._filter_mgr.clear_all)
        menu.exec(self._btn_clear.mapToGlobal(pos))

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is self._send_edit and event.type() == QEvent.Type.KeyPress:
            k, m = event.key(), event.modifiers()
            if k == Qt.Key.Key_Return and m & Qt.KeyboardModifier.ControlModifier:
                self._do_send(); return True
            if self._chk_enter.isChecked():
                if k in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not m:
                    self._do_send(); return True
        return super().eventFilter(obj, event)

    # ══ 串口扫描 ════════════════════════════════

    def _scan_ports(self):
        if self._connected: return
        ports = SerialManager.list_ports()
        if ports == self._known_ports: return
        self._known_ports = ports
        prev = self._cb_port.currentData() or ""
        self._cb_port.blockSignals(True)
        self._cb_port.clear()
        if ports:
            for info in SerialManager.get_port_info():
                desc = info["description"]
                label = f"{info['device']}  {desc}" if desc else info["device"]
                self._cb_port.addItem(label, userData=info["device"])
            for i in range(self._cb_port.count()):
                if self._cb_port.itemData(i) == prev:
                    self._cb_port.setCurrentIndex(i); break
        else:
            self._cb_port.addItem("（无可用端口）", userData="")
        self._cb_port.blockSignals(False)

    def _get_port(self) -> str:
        d = self._cb_port.currentData()
        return d if d else ""

    # ══ 连接操作 ════════════════════════════════

    def _toggle_conn(self):
        if self._connected: self._do_disconnect()
        else:               self._do_connect()

    def _do_connect(self):
        port = self._get_port()
        if not port:
            QMessageBox.warning(self, "提示", "请先选择有效的串口端口！"); return
        ok, msg = self._serial.connect(port, int(self._cb_baud.currentText()))
        if ok:   self._filter_mgr.append_info(msg)
        else:
            self._filter_mgr.append_error(msg)
            QMessageBox.critical(self, "连接失败", msg)

    def _do_disconnect(self):
        if self._loop_timer.isActive():
            self._loop_timer.stop(); self._chk_loop.setChecked(False)
        _, msg = self._serial.disconnect()
        self._filter_mgr.append_info(msg)

    # ══ 发送 ════════════════════════════════════

    def _do_send(self):
        if not self._connected: return
        text = self._send_edit.toPlainText()
        if not text: return
        try:
            if self._chk_hex_tx.isChecked():
                hs = text.replace(" ","").replace("\n","").replace("\r","")
                if len(hs) % 2:
                    self._filter_mgr.append_error("HEX 格式错误：字节数不完整"); return
                data = bytes.fromhex(hs)
            else:
                if self._chk_nl.isChecked():
                    text = text.rstrip("\r\n") + "\r\n"
                data = text.encode("utf-8")
            ok, msg = self._serial.send(data)
            if ok:   self._filter_mgr.append_sent(data)
            else:    self._filter_mgr.append_error(msg)
        except ValueError as e:
            self._filter_mgr.append_error(f"HEX 解析错误: {e}")

    # ══ 信号槽 ══════════════════════════════════

    def _on_rx(self, data: bytes):
        if self._chk_ts.isChecked():
            try:
                ts = datetime.now().strftime("[%H:%M:%S.%f")[:-3] + "] "
                txt = data.decode("utf-8", errors="replace")
                data = "\n".join((ts+l) if l else l for l in txt.split("\n")).encode()
            except Exception: pass
        self._filter_mgr.append_data(data)

    def _on_err(self, msg: str):
        self._filter_mgr.append_error(msg)

    def _on_conn_changed(self, connected: bool):
        self._connected = connected
        if connected:
            self._set_dot(True)
            self._btn_conn.setText("断  开")
            self._btn_conn.setObjectName("BtnDisconnect")
            self._btn_conn.style().unpolish(self._btn_conn)
            self._btn_conn.style().polish(self._btn_conn)
            self._cb_port.setEnabled(False)
            self._cb_baud.setEnabled(False)
            self._btn_send.setEnabled(True)
            self._start_time = datetime.now()
            self._serial.reset_counters()
            self._last_rx = self._last_tx = 0
            p, b = self._get_port(), self._cb_baud.currentText()
            self._lbl_status.setText(f"已连接  {p}  @  {b} bps")
        else:
            self._set_dot(False)
            self._btn_conn.setText("连  接")
            self._btn_conn.setObjectName("BtnConnect")
            self._btn_conn.style().unpolish(self._btn_conn)
            self._btn_conn.style().polish(self._btn_conn)
            self._cb_port.setEnabled(True)
            self._cb_baud.setEnabled(True)
            self._btn_send.setEnabled(False)
            self._start_time = None
            self._lbl_status.setText("已断开")

    def _set_dot(self, on: bool):
        n = "DotOn" if on else "DotOff"
        self._dot.setObjectName(n)
        self._dot.style().unpolish(self._dot)
        self._dot.style().polish(self._dot)

    def _on_baud_changed(self, idx: int):
        """选择波特率下拉项时处理：若选了"自定义..."则弹出输入框"""
        text = self._cb_baud.itemText(idx)
        if text != "自定义...":
            return
        # 弹出输入框
        val, ok = QInputDialog.getText(
            self, "自定义波特率", "请输入波特率（整数）：",
            text=""
        )
        if not ok or not val.strip():
            # 取消：恢复到上一个有效选项
            self._cb_baud.blockSignals(True)
            self._cb_baud.setCurrentIndex(max(0, idx - 1))
            self._cb_baud.blockSignals(False)
            return
        try:
            baud = int(val.strip())
            if baud <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "输入错误", "波特率必须是正整数！")
            self._cb_baud.blockSignals(True)
            self._cb_baud.setCurrentIndex(max(0, idx - 1))
            self._cb_baud.blockSignals(False)
            return
        # 检查是否已存在
        existing = self._cb_baud.findText(str(baud))
        if existing >= 0:
            self._cb_baud.blockSignals(True)
            self._cb_baud.setCurrentIndex(existing)
            self._cb_baud.blockSignals(False)
            return
        # 插入到"自定义..."之前，按数值排序
        insert_pos = 0
        for i in range(self._cb_baud.count() - 1):  # 不含最后的"自定义..."
            try:
                if int(self._cb_baud.itemText(i)) < baud:
                    insert_pos = i + 1
            except ValueError:
                pass
        self._cb_baud.blockSignals(True)
        self._cb_baud.insertItem(insert_pos, str(baud))
        self._cb_baud.setCurrentIndex(insert_pos)
        self._cb_baud.blockSignals(False)
        # 保存到 config
        if "custom_baudrates" not in self._cfg["serial"]:
            self._cfg["serial"]["custom_baudrates"] = []
        if baud not in self._cfg["serial"]["custom_baudrates"]:
            self._cfg["serial"]["custom_baudrates"].append(baud)
            self._cfg["serial"]["custom_baudrates"].sort()
        save_config(self._cfg)

    def _on_loop_toggled(self, checked: bool):
        if checked and self._connected:
            self._loop_timer.start(self._spin_ms.value())
        else:
            self._loop_timer.stop()

    def _refresh_stat(self):
        rx, tx = self._serial.rx_bytes, self._serial.tx_bytes
        rr, tr = rx - self._last_rx, tx - self._last_tx
        self._last_rx, self._last_tx = rx, tx
        self._lbl_rx.setText(f"RX: {self._fmt(rx)}")
        self._lbl_tx.setText(f"TX: {self._fmt(tx)}")
        self._lbl_rx_rate.setText(f"↓ {self._fmt(rr)}/s")
        self._lbl_tx_rate.setText(f"↑ {self._fmt(tr)}/s")
        if self._start_time:
            s = int((datetime.now()-self._start_time).total_seconds())
            h,r = divmod(s,3600); m,s = divmod(r,60)
            self._lbl_timer.setText(f"{h:02d}:{m:02d}:{s:02d}")
        else:
            self._lbl_timer.setText("00:00:00")

    @staticmethod
    def _fmt(n: int) -> str:
        if n < 1024:    return f"{n} B"
        if n < 1048576: return f"{n/1024:.1f} KB"
        return f"{n/1048576:.2f} MB"

    def closeEvent(self, event):
        self._port_timer.stop(); self._stat_timer.stop()
        if self._loop_timer.isActive(): self._loop_timer.stop()
        if self._connected: self._serial.disconnect()
        cur_text = self._cb_baud.currentText()
        if cur_text != "自定义...":
            try:
                self._cfg["serial"]["baudrate"] = int(cur_text)
            except ValueError:
                pass
        self._cfg["serial"]["port"] = self._get_port()
        self._cfg["send"]["add_newline"] = self._chk_nl.isChecked()
        save_config(self._cfg)
        event.accept()


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(
        Qt.ApplicationAttribute.AA_DontUseNativeMenuWindows, True
    )
    app = QApplication(sys.argv)
    app.setApplicationName("SerialAssistant")
    app.setStyleSheet(STYLE)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
