"""
serial_manager.py - 串口连接管理模块
封装 pyserial，提供 connect/disconnect/send/receive 方法
使用 QThread 在后台线程持续读取串口数据
"""

import serial
import serial.tools.list_ports
from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker


# ──────────────────────────────────────────────
# 后台读取线程
# ──────────────────────────────────────────────
class SerialReaderThread(QThread):
    """在后台线程中持续读取串口数据，通过 Signal 发送到主线程"""

    data_received = Signal(bytes)   # 收到原始字节数据
    error_occurred = Signal(str)    # 发生错误

    def __init__(self, ser: serial.Serial, parent=None):
        super().__init__(parent)
        self._ser = ser
        self._running = False

    def run(self):
        self._running = True
        while self._running:
            try:
                if self._ser and self._ser.is_open:
                    waiting = self._ser.in_waiting
                    if waiting > 0:
                        data = self._ser.read(waiting)
                        if data:
                            self.data_received.emit(data)
                    else:
                        # 没有数据时短暂休眠，避免 CPU 空转
                        self.msleep(10)
                else:
                    self.msleep(20)
            except serial.SerialException as e:
                self.error_occurred.emit(f"串口读取错误: {e}")
                self._running = False
            except Exception as e:
                self.error_occurred.emit(f"未知错误: {e}")
                self._running = False

    def stop(self):
        """请求停止线程"""
        self._running = False


# ──────────────────────────────────────────────
# 串口管理器
# ──────────────────────────────────────────────
class SerialManager:
    """
    串口管理器，封装 pyserial 的连接/断开/发送/接收操作。

    使用方式：
        mgr = SerialManager()
        mgr.data_received.connect(my_slot)   # 连接数据信号
        mgr.connect("COM3", 115200)
        mgr.send(b"hello\\r\\n")
        mgr.disconnect()
    """

    # 把信号代理出去，方便外部直接连接
    # （SerialManager 不继承 QObject，所以用一个内部 QObject 持有信号）
    class _Signals:
        pass

    def __init__(self):
        self._ser: serial.Serial | None = None
        self._reader: SerialReaderThread | None = None
        self._mutex = QMutex()

        # 统计
        self.rx_bytes: int = 0
        self.tx_bytes: int = 0

        # 信号（通过内部 _SignalHolder 暴露）
        self._holder = _SignalHolder()
        self.data_received: Signal = self._holder.data_received
        self.error_occurred: Signal = self._holder.error_occurred
        self.connection_changed: Signal = self._holder.connection_changed

    # ── 公开接口 ──────────────────────────────

    def connect(self, port: str, baudrate: int = 115200,
                bytesize: int = 8, parity: str = "N",
                stopbits: int = 1, timeout: float = 0.1) -> tuple[bool, str]:
        """
        打开串口并启动后台读取线程。
        返回 (success: bool, message: str)
        """
        if self.is_connected():
            return False, "串口已连接，请先断开"

        try:
            self._ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=bytesize,
                parity=parity,
                stopbits=stopbits,
                timeout=timeout
            )
            # 清空缓冲区
            self._ser.reset_input_buffer()
            self._ser.reset_output_buffer()

            # 启动读取线程
            self._reader = SerialReaderThread(self._ser)
            self._reader.data_received.connect(self._on_data_received)
            self._reader.error_occurred.connect(self._on_error)
            self._reader.start()

            self._holder.connection_changed.emit(True)
            return True, f"已连接到 {port} @ {baudrate} bps"

        except serial.SerialException as e:
            self._ser = None
            return False, f"连接失败: {e}"
        except Exception as e:
            self._ser = None
            return False, f"连接失败（未知错误）: {e}"

    def disconnect(self) -> tuple[bool, str]:
        """断开串口连接"""
        if not self.is_connected():
            return False, "串口未连接"

        # 停止读取线程
        if self._reader is not None:
            self._reader.stop()
            self._reader.wait(2000)   # 最多等 2 秒
            self._reader = None

        # 关闭串口
        try:
            if self._ser and self._ser.is_open:
                self._ser.close()
        except Exception:
            pass
        self._ser = None

        self._holder.connection_changed.emit(False)
        return True, "已断开连接"

    def send(self, data: bytes) -> tuple[bool, str]:
        """
        发送字节数据。
        返回 (success: bool, message: str)
        """
        if not self.is_connected():
            return False, "串口未连接"

        with QMutexLocker(self._mutex):
            try:
                written = self._ser.write(data)
                self.tx_bytes += written
                return True, f"已发送 {written} 字节"
            except serial.SerialException as e:
                return False, f"发送失败: {e}"
            except Exception as e:
                return False, f"发送失败（未知错误）: {e}"

    def is_connected(self) -> bool:
        """返回当前是否已连接"""
        return self._ser is not None and self._ser.is_open

    def reset_counters(self):
        """重置收发计数"""
        self.rx_bytes = 0
        self.tx_bytes = 0

    # ── 静态工具 ──────────────────────────────

    @staticmethod
    def list_ports() -> list[str]:
        """扫描并返回当前可用的串口列表"""
        ports = serial.tools.list_ports.comports()
        # 按端口名排序
        return sorted([p.device for p in ports])

    @staticmethod
    def get_port_info() -> list[dict]:
        """返回详细的串口信息列表"""
        ports = serial.tools.list_ports.comports()
        result = []
        for p in sorted(ports, key=lambda x: x.device):
            result.append({
                "device": p.device,
                "description": p.description or "",
                "hwid": p.hwid or ""
            })
        return result

    # ── 内部槽 ────────────────────────────────

    def _on_data_received(self, data: bytes):
        self.rx_bytes += len(data)
        self._holder.data_received.emit(data)

    def _on_error(self, msg: str):
        # 读取线程报错，说明串口可能已断开
        self._ser = None
        self._reader = None
        self._holder.connection_changed.emit(False)
        self._holder.error_occurred.emit(msg)


# ──────────────────────────────────────────────
# 内部信号持有者（QObject 子类才能定义 Signal）
# ──────────────────────────────────────────────
from PySide6.QtCore import QObject

class _SignalHolder(QObject):
    data_received = Signal(bytes)
    error_occurred = Signal(str)
    connection_changed = Signal(bool)   # True=已连接, False=已断开
