"""
log_manager.py - 日志文件记录引擎
自动按目录结构保存串口日志，支持 50 MB 自动分片
目录格式：<root>/YYYY-MM/dayDD/PORT-DESC-connectN-HHMMSS/TAB.log
"""

from __future__ import annotations

import os
import re
from datetime import datetime

from PySide6.QtCore import QObject, Signal

_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def _safe_name(s: str) -> str:
    """将文件名中的特殊字符替换为下划线"""
    return re.sub(r'[<>:"/\\|?*\s]+', '_', s).strip('_') or 'unknown'


class LogManager(QObject):
    """日志记录管理器"""

    write_error = Signal(str)

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self._config = config
        self._session_dir: str = ""
        self._files: dict[str, _LogFile] = {}
        self._recording = False
        self._connect_count = 0

    @property
    def is_recording(self) -> bool:
        return self._recording

    # ── 会话管理 ──────────────────────────────

    def start_session(self, port: str, description: str):
        """开始新的录制会话（串口连接时调用）"""
        log_cfg = self._config.get("logging", {})
        if not log_cfg.get("enabled", False):
            return

        root = log_cfg.get("root_dir", "").strip()
        if not root:
            root = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "logs"
            )

        self._connect_count += 1
        now = datetime.now()

        year_month = now.strftime("%Y-%m")
        day_dir = f"day{now.day:02d}"
        port_safe = _safe_name(port)
        desc_safe = _safe_name(description)
        time_str = now.strftime("%H%M%S")
        session = (
            f"{port_safe}-{desc_safe}"
            f"-connect{self._connect_count}-{time_str}"
        )

        self._session_dir = os.path.join(
            root, year_month, day_dir, session
        )
        try:
            os.makedirs(self._session_dir, exist_ok=True)
            self._recording = True
        except Exception as e:
            self.write_error.emit(f"创建日志目录失败: {e}")
            self._recording = False

    def stop_session(self):
        """停止录制，关闭所有文件"""
        self._recording = False
        for lf in self._files.values():
            lf.close()
        self._files.clear()

    # ── 写入 ─────────────────────────────────

    def write_line(self, tab_name: str, text: str):
        """写一行到指定 tab 的日志文件"""
        if not self._recording:
            return
        if not self._should_record_tab(tab_name):
            return

        ext = self._config.get("logging", {}).get(
            "file_format", ".log"
        )

        if tab_name not in self._files:
            safe = _safe_name(tab_name)
            path = os.path.join(
                self._session_dir, f"{safe}{ext}"
            )
            lf = _LogFile(path, self.write_error)
            if lf.is_open:
                self._files[tab_name] = lf
            else:
                return

        self._files[tab_name].write(text)

    def close_tab(self, tab_name: str):
        """关闭某个 tab 对应的日志文件"""
        if tab_name in self._files:
            self._files[tab_name].close()
            del self._files[tab_name]

    def _should_record_tab(self, tab_name: str) -> bool:
        log_cfg = self._config.get("logging", {})
        if log_cfg.get("record_all_tabs", True):
            return True
        selected = log_cfg.get("selected_tabs", [])
        return tab_name in selected


class _LogFile:
    """单个日志文件，支持 50 MB 自动分片"""

    def __init__(self, base_path: str, error_signal: Signal):
        self._base_path = base_path
        self._error_signal = error_signal
        self._file = None
        self._part = 1
        self._current_path = base_path
        self._written = 0
        self._open()

    @property
    def is_open(self) -> bool:
        return self._file is not None

    def _open(self):
        try:
            self._file = open(
                self._current_path, "a", encoding="utf-8", buffering=1
            )
        except Exception:
            self._error_signal.emit("自动保存写入失败！")
            self._file = None

    def write(self, text: str):
        if self._file is None:
            return
        try:
            self._file.write(text)
            self._written += len(text.encode("utf-8"))
            if self._written >= _MAX_FILE_SIZE:
                self._split()
        except Exception:
            self._error_signal.emit("自动保存写入失败！")
            try:
                self._file.close()
            except Exception:
                pass
            self._file = None

    def _split(self):
        """切换到新的分片文件"""
        self.close()
        self._part += 1
        base, ext = os.path.splitext(self._base_path)
        self._current_path = f"{base}-part{self._part}{ext}"
        self._written = 0
        self._open()

    def close(self):
        if self._file:
            try:
                self._file.close()
            except Exception:
                pass
            self._file = None