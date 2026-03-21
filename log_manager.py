"""
log_manager.py - 日志文件记录引擎
v0.5 — ★ _default_log_root() 兼容 PyInstaller
       ★ exe 旁边优先，无写权限时自动回退到 Documents
目录格式：<root>/YYYY-MM/dayDD/PORT-DESC-connectN-HHMMSS/TAB.log
"""

from __future__ import annotations

import os
import sys
import re
from datetime import datetime

from PySide6.QtCore import QObject, Signal

_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def _app_dir() -> str:
    """返回 exe / 脚本 所在目录（兼容 PyInstaller / Nuitka --onefile）"""
    # PyInstaller 设 sys.frozen
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    # Nuitka --onefile: 不设 sys.frozen，但 __file__ 指向临时解压目录
    # 用 sys.argv[0] 检测：如果是 .exe 就取它的目录
    main_script = os.path.abspath(sys.argv[0])
    if main_script.lower().endswith('.exe'):
        return os.path.dirname(main_script)
    # 开发环境：直接用 __file__
    return os.path.dirname(os.path.abspath(__file__))


def _resolve_log_root(log_cfg: dict) -> str:
    """解析日志根目录：有自定义就用自定义，否则用 exe旁/logs 并写回 config"""
    root = log_cfg.get("root_dir", "").strip()
    if root:
        return root
    # ★ 默认路径：exe 旁边的 logs 文件夹
    root = os.path.join(_app_dir(), "logs")
    # ★ 写回 config，让用户在设置页看到实际路径
    log_cfg["root_dir"] = root
    return root


def _safe_name(s: str) -> str:
    return re.sub(r'[<>:"/\\|?*\s]+', '_', s).strip('_') or 'unknown'


class LogManager(QObject):
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

    # ★ 新增：供另存为使用 ──────────────────

    @property
    def session_dir(self) -> str:
        """当前会话目录路径"""
        return self._session_dir

    def get_default_save_dir(self) -> str:
        """返回另存为的默认目录（当前会话目录，若无则返回 logs 根目录）"""
        if self._session_dir and os.path.isdir(self._session_dir):
            return self._session_dir
        log_cfg = self._config.get("logging", {})
        root = log_cfg.get("root_dir", "").strip()
        if not root:
            root = os.path.join(_app_dir(), "logs")
        return root

    # ── 会话管理 ─────────────────────────

    def start_session(self, port: str, description: str):
        log_cfg = self._config.get("logging", {})
        if not log_cfg.get("enabled", False):
            return
        root = _resolve_log_root(log_cfg)
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
        self._recording = False
        for lf in self._files.values():
            lf.close()
        self._files.clear()

    # ── 写入 ─────────────────────────────

    def write_line(self, tab_name: str, text: str):
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
        if tab_name in self._files:
            self._files[tab_name].close()
            del self._files[tab_name]

    def _should_record_tab(self, tab_name: str) -> bool:
        log_cfg = self._config.get("logging", {})
        if log_cfg.get("record_all_tabs", True):
            return True
        return tab_name in log_cfg.get("selected_tabs", [])


class _LogFile:
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
                self._current_path, "a",
                encoding="utf-8", buffering=1,
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