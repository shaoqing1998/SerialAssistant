"""
main.py - 串口调试助手主入口 & 主窗口 UI
技术栈：Python + PySide6 + pyserial
"""

import sys
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QSplitter,
    QComboBox, QPushButton, QLabel,
    QTextEdit, QStatusBar, QGroupBox,
    QCheckBox, QToolBar, QSizePolicy,
    QMessageBox, QFrame
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QIcon, QAction

from config import load_config, save_config
from serial_manager import SerialManager
from log_viewer import LogViewer
from filter_manager import FilterManager


# ══════════════════════════════════════════════
# 全局样式表
# ══════════════════════════════════════════════
GLOBAL_STYLE = """
QMainWindow, QWidget {
    background-color: #2d2d2d;
    color: #d4d4d4;
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}

/* ── 下拉框 ── */
QComboBox {
    background-color: #3c3c3c;
    color: #d4d4d4;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 4px 8px;
    min-width: 100px;
}
QComboBox:hover {
    border-color: #4ec9b0;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #3c3c3c;
    color: #d4d4d4;
    selection-background-color: #094771;
    border: 1px solid #555555;
}

/* ── 按钮基础 ── */
QPushButton {
    background-color: #3c3c3c;
    color: #d4d4d4;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 5px 14px;
    min-width: 72px;
}
QPushButton:hover {
    background-color: #4a4a4a;
    border-color: #888888;
}
QPushButton:pressed {
    background-color: #2a2a2a;
}
QPushButton:disabled {
    color: #666666;
    border-color: #444444;
    background-color: #333333;
}

/* ── 绿色连接按钮 ── */
QPushButton#btn_connect {
    background-color: #2d6a2d;
    color: #ffffff;
    border: 1px solid #3a8a3a;
    font-weight: bold;
}
QPushButton#btn_connect:hover {
    background-color: #3a8a3a;
    border-color: #4ec94e;
}
QPushButton#btn_connect:pressed {
    background-color: #1e4d1e;
}

/* ── 红色断开按钮 ── */
QPushButton#btn_disconnect {
    background-color: #6a2d2d;
    color: #ffffff;
    border: 1px solid #8a3a3a;
    font-weight: bold;
}
QPushButton#btn_disconnect:hover {
    background-color: #8a3a3a;
    border-color: #c94e4e;
}
QPushButton#btn_disconnect:pressed {
    background-color: #4d1e1e;
}

/* ── 发送按钮（绿色） ── */
QPushButton#btn_send {
    background-color: #2d6a2d;
    color: #ffffff;
    border: 1px solid #3a8a3a;
    font-weight: bold;
    min-width: 80px;
    padding: 6px 16px;
}
QPushButton#btn_send:hover {
    background-color: #3a8a3a;
    border-color: #4ec94e;
}
QPushButton#btn_send:pressed {
    background-color: #1e4d1e;
}
QPushButton#btn_send:disabled {
    background-color: #333333;
    color: #666666;
    border-color: #444444;
}

/* ── 清空按钮 ── */
QPushButton#btn_clear {
    background-color: #3c3c3c;
    color: #aaaaaa;
    border: 1px solid #555555;
    min-width: 60px;
}
QPushButton#btn_clear:hover {
    background-color: #4a4a4a;
    color: #d4d4d4;
}

/* ── 刷新端口按钮 ── */
QPushButton#btn_refresh {
    background-color: #3c3c3c;
    color: #4ec9b0;
    border: 1px solid #555555;
    min-width: 60px;
}
QPushButton#btn_refresh:hover {
    background-color: #4a4a4a;
    border-color: #4ec9b0;
}

/* ── 发送输入框 ── */
QTextEdit#send_edit {
    background-color: #1e1e1e;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 11px;
}
QTextEdit#send_edit:focus {
    border-color: #4ec9b0;
}

/* ── GroupBox ── */
QGroupBox {
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 4px;
    color: #aaaaaa;
    font-size: 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    left: 8px;
}

/* ── 标签 ── */
QLabel {
    color: #aaaaaa;
}
QLabel#lbl_status_connected {
    color: #4ec94e;
    font-weight: bold;
}
QLabel#lbl_status_disconnected {
    color: #f44747;
    font-weight: bold;
}

/* ── 状态栏 ── */
QStatusBar {
    background-color: #007acc;
    color: #ffffff;
    font-size: 12px;
}
QStatusBar QLabel {
    color: #ffffff;
    padding: 0 8px;
}

/* ── 复选框 ── */
QCheckBox {
    color: #aaaaaa;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #555555;
    border-radius: 2px;
    background-color: #3c3c3c;
}
QCheckBox::indicator:checked {
    background-color: #4ec9b0;
    border-color: #4ec9b0;
}

/* ── 分割线 ── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {
    color: #3c3c3c;
}

/* ── Splitter ── */
QSplitter::handle {
    background-color: #3c3c3c;
    width: 3px;
    height: 3px;
}
QSplitter::handle:hover {
    background-color: #4ec9b0;
}
"""


# ══════════════════════════════════════════════
# 主窗口
# ══════════════════════════════════════════════
class MainWindow(QMainWindow):

    BAUDRATES = [
        "1200", "2400", "4800", "9600", "14400",
        "19200", "38400", "57600", "115200",
        "230400", "460800", "921600"
    ]

    def __init__(self):
        super().__init__()
        self._config = load_config()
        self._serial = SerialManager()
        self._is_connected = False

        self._init_ui()
        self._connect_signals()
        self._refresh_ports()

        # 定时刷新状态栏计数（每秒）
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._update_counters)
        self._status_timer.start(1000)

    # ── 初始化 UI ─────────────────────────────

    def _init_ui(self):
        self.setWindowTitle("串口调试助手 - SerialAssistant v1.0")
        w = self._config["ui"]["window_width"]
        h = self._config["ui"]["window_height"]
        self.resize(w, h)
        self.setMinimumSize(900, 500)

        # 中央容器
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 4)
        main_layout.setSpacing(6)

        # 1. 顶部串口设置栏
        main_layout.addWidget(self._build_toolbar())

        # 2. 分割线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line)

        # 3. 主体区域（左：日志 60%，右：发送 40%）
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # 左侧日志区
        self._log_viewer = LogViewer(self._config)
        log_group = QGroupBox("接收日志")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(4, 8, 4, 4)
        log_layout.addWidget(self._log_viewer)
        splitter.addWidget(log_group)

        # 右侧发送区
        splitter.addWidget(self._build_send_panel())

        # 设置比例 60:40
        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)
        main_layout.addWidget(splitter, stretch=1)

        # 4. 状态栏
        self._build_statusbar()

    def _build_toolbar(self) -> QWidget:
        """构建顶部串口设置栏"""
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 端口标签 + 下拉框
        layout.addWidget(QLabel("端口:"))
        self._combo_port = QComboBox()
        self._combo_port.setMinimumWidth(110)
        self._combo_port.setToolTip("选择串口端口")
        layout.addWidget(self._combo_port)

        # 刷新端口按钮
        self._btn_refresh = QPushButton("⟳ 刷新")
        self._btn_refresh.setObjectName("btn_refresh")
        self._btn_refresh.setToolTip("重新扫描可用串口")
        self._btn_refresh.setFixedWidth(70)
        layout.addWidget(self._btn_refresh)

        # 分隔
        layout.addWidget(self._make_vsep())

        # 波特率
        layout.addWidget(QLabel("波特率:"))
        self._combo_baud = QComboBox()
        self._combo_baud.addItems(self.BAUDRATES)
        self._combo_baud.setCurrentText(
            str(self._config["serial"]["baudrate"])
        )
        self._combo_baud.setToolTip("选择波特率")
        layout.addWidget(self._combo_baud)

        # 分隔
        layout.addWidget(self._make_vsep())

        # 连接 / 断开按钮
        self._btn_connect = QPushButton("▶ 连接")
        self._btn_connect.setObjectName("btn_connect")
        self._btn_connect.setFixedWidth(90)

        self._btn_disconnect = QPushButton("■ 断开")
        self._btn_disconnect.setObjectName("btn_disconnect")
        self._btn_disconnect.setFixedWidth(90)
        self._btn_disconnect.setEnabled(False)

        layout.addWidget(self._btn_connect)
        layout.addWidget(self._btn_disconnect)

        # 分隔
        layout.addWidget(self._make_vsep())

        # HEX 显示模式
        self._chk_hex = QCheckBox("HEX 显示")
        self._chk_hex.setToolTip("以十六进制格式显示接收数据")
        layout.addWidget(self._chk_hex)

        # 自动滚动
        self._chk_autoscroll = QCheckBox("自动滚动")
        self._chk_autoscroll.setChecked(True)
        self._chk_autoscroll.setToolTip("接收数据时自动滚动到底部")
        layout.addWidget(self._chk_autoscroll)

        layout.addStretch()

        # 连接状态指示
        self._lbl_conn_state = QLabel("● 未连接")
        self._lbl_conn_state.setObjectName("lbl_status_disconnected")
        layout.addWidget(self._lbl_conn_state)

        return bar

    def _build_send_panel(self) -> QGroupBox:
        """构建右侧发送面板"""
        group = QGroupBox("发送")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 10, 6, 6)
        layout.setSpacing(6)

        # 发送选项行
        opt_layout = QHBoxLayout()
        self._chk_hex_send = QCheckBox("HEX 发送")
        self._chk_hex_send.setToolTip("以十六进制格式解析发送内容（如: 01 02 03）")
        self._chk_newline = QCheckBox("追加换行 \\r\\n")
        self._chk_newline.setChecked(
            self._config["send"].get("add_newline", True)
        )
        self._chk_newline.setToolTip("发送时在末尾追加 \\r\\n")
        opt_layout.addWidget(self._chk_hex_send)
        opt_layout.addWidget(self._chk_newline)
        opt_layout.addStretch()
        layout.addLayout(opt_layout)

        # 发送输入框
        self._send_edit = QTextEdit()
        self._send_edit.setObjectName("send_edit")
        self._send_edit.setPlaceholderText(
            "在此输入要发送的内容...\n"
            "（Ctrl+Enter 快速发送）"
        )
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._send_edit.setFont(font)
        layout.addWidget(self._send_edit, stretch=1)

        # 按钮行
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        self._btn_clear_send = QPushButton("清空输入")
        self._btn_clear_send.setObjectName("btn_clear")
        self._btn_clear_send.setFixedWidth(80)

        self._btn_clear_log = QPushButton("清空日志")
        self._btn_clear_log.setObjectName("btn_clear")
        self._btn_clear_log.setFixedWidth(80)

        self._btn_send = QPushButton("▶ 发送")
        self._btn_send.setObjectName("btn_send")
        self._btn_send.setEnabled(False)
        self._btn_send.setToolTip("发送数据（Ctrl+Enter）")

        btn_layout.addWidget(self._btn_clear_send)
        btn_layout.addWidget(self._btn_clear_log)
        btn_layout.addStretch()
        btn_layout.addWidget(self._btn_send)
        layout.addLayout(btn_layout)

        return group

    def _build_statusbar(self):
        """构建底部状态栏"""
        sb = self.statusBar()

        self._lbl_status = QLabel("就绪")
        self._lbl_rx = QLabel("RX: 0 B")
        self._lbl_tx = QLabel("TX: 0 B")
        self._lbl_time = QLabel("")

        # 添加分隔符
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.VLine)

        sb.addWidget(self._lbl_status, 1)
        sb.addPermanentWidget(sep1)
        sb.addPermanentWidget(self._lbl_rx)
        sb.addPermanentWidget(sep2)
        sb.addPermanentWidget(self._lbl_tx)
        sb.addPermanentWidget(sep3)
        sb.addPermanentWidget(self._lbl_time)

    # ── 信号连接 ──────────────────────────────

    def _connect_signals(self):
        # 串口管理器信号
        self._serial.data_received.connect(self._on_data_received)
        self._serial.error_occurred.connect(self._on_serial_error)
        self._serial.connection_changed.connect(self._on_connection_changed)

        # 按钮
        self._btn_connect.clicked.connect(self._do_connect)
        self._btn_disconnect.clicked.connect(self._do_disconnect)
        self._btn_refresh.clicked.connect(self._refresh_ports)
        self._btn_send.clicked.connect(self._do_send)
        self._btn_clear_send.clicked.connect(self._send_edit.clear)
        self._btn_clear_log.clicked.connect(self._log_viewer.clear)

        # 复选框
        self._chk_hex.toggled.connect(self._log_viewer.set_show_hex)
        self._chk_autoscroll.toggled.connect(self._log_viewer.set_auto_scroll)

        # Ctrl+Enter 快速发送
        self._send_edit.installEventFilter(self)

    # ── 事件过滤（Ctrl+Enter 发送）────────────

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QKeyEvent
        if obj is self._send_edit and event.type() == QEvent.Type.KeyPress:
            key_event: QKeyEvent = event
            if (key_event.key() == Qt.Key.Key_Return and
                    key_event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                self._do_send()
                return True
        return super().eventFilter(obj, event)

    # ── 串口操作 ──────────────────────────────

    def _refresh_ports(self):
        """刷新可用串口列表"""
        current = self._combo_port.currentText()
        self._combo_port.clear()
        ports = SerialManager.list_ports()
        if ports:
            self._combo_port.addItems(ports)
            # 尝试恢复之前选中的端口
            idx = self._combo_port.findText(current)
            if idx >= 0:
                self._combo_port.setCurrentIndex(idx)
            self._log_viewer.append_info(
                f"扫描到 {len(ports)} 个串口: {', '.join(ports)}"
            )
        else:
            self._combo_port.addItem("（无可用端口）")
            self._log_viewer.append_info("未扫描到可用串口")

    def _do_connect(self):
        """连接串口"""
        port = self._combo_port.currentText()
        if not port or port.startswith("（"):
            QMessageBox.warning(self, "提示", "请先选择有效的串口端口！")
            return

        baudrate = int(self._combo_baud.currentText())
        ok, msg = self._serial.connect(port, baudrate)
        if ok:
            self._log_viewer.append_info(msg)
        else:
            self._log_viewer.append_error(msg)
            QMessageBox.critical(self, "连接失败", msg)

    def _do_disconnect(self):
        """断开串口"""
        ok, msg = self._serial.disconnect()
        self._log_viewer.append_info(msg)

    def _do_send(self):
        """发送数据"""
        if not self._is_connected:
            return

        text = self._send_edit.toPlainText()
        if not text:
            return

        try:
            if self._chk_hex_send.isChecked():
                # HEX 模式：解析十六进制字符串
                hex_str = text.replace(" ", "").replace("\n", "").replace("\r", "")
                if len(hex_str) % 2 != 0:
                    self._log_viewer.append_error("HEX 格式错误：字节数不完整")
                    return
                data = bytes.fromhex(hex_str)
            else:
                # 文本模式
                if self._chk_newline.isChecked():
                    text = text.rstrip("\r\n") + "\r\n"
                data = text.encode("utf-8")

            ok, msg = self._serial.send(data)
            if ok:
                self._log_viewer.append_sent(data)
            else:
                self._log_viewer.append_error(msg)

        except ValueError as e:
            self._log_viewer.append_error(f"HEX 解析错误: {e}")

    # ── 信号槽 ────────────────────────────────

    def _on_data_received(self, data: bytes):
        """接收到串口数据"""
        self._log_viewer.append_data(data)

    def _on_serial_error(self, msg: str):
        """串口发生错误"""
        self._log_viewer.append_error(msg)

    def _on_connection_changed(self, connected: bool):
        """连接状态变化"""
        self._is_connected = connected
        if connected:
            port = self._combo_port.currentText()
            baud = self._combo_baud.currentText()
            self._lbl_conn_state.setText(f"● {port} @ {baud}")
            self._lbl_conn_state.setObjectName("lbl_status_connected")
            self._lbl_status.setText(f"已连接: {port} @ {baud} bps")
            self._btn_connect.setEnabled(False)
            self._btn_disconnect.setEnabled(True)
            self._btn_send.setEnabled(True)
            self._combo_port.setEnabled(False)
            self._combo_baud.setEnabled(False)
            self._btn_refresh.setEnabled(False)
        else:
            self._lbl_conn_state.setText("● 未连接")
            self._lbl_conn_state.setObjectName("lbl_status_disconnected")
            self._lbl_status.setText("已断开连接")
            self._btn_connect.setEnabled(True)
            self._btn_disconnect.setEnabled(False)
            self._btn_send.setEnabled(False)
            self._combo_port.setEnabled(True)
            self._combo_baud.setEnabled(True)
            self._btn_refresh.setEnabled(True)

        # 强制刷新样式（objectName 变化后需要重新 polish）
        self._lbl_conn_state.style().unpolish(self._lbl_conn_state)
        self._lbl_conn_state.style().polish(self._lbl_conn_state)

    def _update_counters(self):
        """定时更新收发字节计数"""
        self._lbl_rx.setText(f"RX: {self._format_bytes(self._serial.rx_bytes)}")
        self._lbl_tx.setText(f"TX: {self._format_bytes(self._serial.tx_bytes)}")
        self._lbl_time.setText(datetime.now().strftime("%H:%M:%S"))

    # ── 工具方法 ──────────────────────────────

    @staticmethod
    def _make_vsep() -> QFrame:
        """创建垂直分隔线"""
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        return sep

    @staticmethod
    def _format_bytes(n: int) -> str:
        """格式化字节数为可读字符串"""
        if n < 1024:
            return f"{n} B"
        elif n < 1024 * 1024:
            return f"{n / 1024:.1f} KB"
        else:
            return f"{n / 1024 / 1024:.2f} MB"

    # ── 窗口关闭 ──────────────────────────────

    def closeEvent(self, event):
        """关闭窗口时断开串口并保存配置"""
        if self._is_connected:
            self._serial.disconnect()

        # 保存当前配置
        self._config["serial"]["baudrate"] = int(self._combo_baud.currentText())
        self._config["serial"]["port"] = self._combo_port.currentText()
        self._config["send"]["add_newline"] = self._chk_newline.isChecked()
        save_config(self._config)

        event.accept()


# ══════════════════════════════════════════════
# 程序入口
# ══════════════════════════════════════════════
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SerialAssistant")
    app.setApplicationVersion("1.0.0")
    app.setStyleSheet(GLOBAL_STYLE)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
