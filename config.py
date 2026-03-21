"""
config.py - 配置文件加载/保存模块
v0.5 — ★ _app_dir() 兼容 PyInstaller --onefile/--onedir
       ★ 新增 highlight 配置节
"""
import json
import os
import sys


def _app_dir() -> str:
    """exe 所在目录（兼容 PyInstaller --onefile / --onedir）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


_CONFIG_PATH = os.path.join(_app_dir(), "config.json")
_DEFAULT_CONFIG = {
    "serial": {
        "port": "",
        "baudrate": 115200,
        "bytesize": 8,
        "parity": "N",
        "stopbits": 1,
        "timeout": 0.1,
    },
    "ui": {
        "window_width": 1100,
        "window_height": 650,
        "font_family": "Consolas",
        "font_size": 10,
        "max_log_lines": 5000,
    },
    "send": {
        "hex_mode": False,
        "add_newline": True,
        "newline_type": "\r\n",
    },
    # ★ 新增：日志记录配置
    "logging": {
        "enabled": False,
        "root_dir": "",
        "file_format": ".log",
        "record_all_tabs": True,
        "selected_tabs": [],
    },
    # ★ v0.5: 高亮配置
    "highlight": {
        "enabled": True,
        "builtin_rules": {},
        "user_rules": [],
    },
}
def load_config() -> dict:
    """加载配置文件，若不存在则返回默认配置"""
    if not os.path.exists(_CONFIG_PATH):
        return _deep_copy(_DEFAULT_CONFIG)
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = _deep_copy(_DEFAULT_CONFIG)
        _deep_merge(merged, data)
        return merged
    except Exception as e:
        print(f"[Config] 加载配置失败: {e}，使用默认配置")
        return _deep_copy(_DEFAULT_CONFIG)
def save_config(config: dict) -> bool:
    """保存配置到文件"""
    try:
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"[Config] 保存配置失败: {e}")
        return False
def _deep_copy(d: dict) -> dict:
    return json.loads(json.dumps(d))
def _deep_merge(base: dict, override: dict):
    for key, value in override.items():
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(value, dict)
        ):
            _deep_merge(base[key], value)
        else:
            base[key] = value