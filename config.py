"""
config.py - 配置文件加载/保存模块
"""

import json
import os

# 配置文件路径（与脚本同目录）
_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# 默认配置（兜底）
_DEFAULT_CONFIG = {
    "serial": {
        "port": "",
        "baudrate": 115200,
        "bytesize": 8,
        "parity": "N",
        "stopbits": 1,
        "timeout": 0.1
    },
    "ui": {
        "window_width": 1100,
        "window_height": 650,
        "font_family": "Consolas",
        "font_size": 10,
        "max_log_lines": 5000
    },
    "send": {
        "hex_mode": False,
        "add_newline": True,
        "newline_type": "\r\n"
    }
}


def load_config() -> dict:
    """加载配置文件，若不存在则返回默认配置"""
    if not os.path.exists(_CONFIG_PATH):
        return _deep_copy(_DEFAULT_CONFIG)

    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 用默认值填充缺失的键
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
    """深拷贝字典"""
    return json.loads(json.dumps(d))


def _deep_merge(base: dict, override: dict):
    """将 override 的值合并到 base（递归）"""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
