"""
highlight_engine.py  -  日志高亮引擎
v0.5 — QSyntaxHighlighter + 200 预制柔色 + 自动对比度
"""
from __future__ import annotations

import re
import colorsys

from PySide6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor,
)


# ══════════════════════════════════════════
# 200 种预制柔色（HSL 色环 20 色相 × 10 变体）
# ══════════════════════════════════════════
def _gen_palette(n=200):
    out = []
    hues = 20
    per = n // hues
    for hi in range(hues):
        h = hi / hues
        for vi in range(per):
            s = 0.30 + (vi % 5) * 0.10
            l = 0.35 + (vi // 5) * 0.15
            r, g, b = colorsys.hls_to_rgb(h, l, s)
            out.append(
                f"#{int(r*255):02x}{int(g*255):02x}"
                f"{int(b*255):02x}"
            )
    return out


SOFT_PALETTE = _gen_palette()

DEFAULT_12 = [
    "#c0392b", "#e67e22", "#b8860b", "#27864e",
    "#2a9d8f", "#5b8cc2", "#7c5cbf", "#c2577a",
    "#8c8c8c", "#3a7ca5", "#6b8e4e", "#9b6b4a",
]


def color_dist(a: str, b: str) -> float:
    ra, ga, ba = (
        int(a[1:3], 16), int(a[3:5], 16), int(a[5:7], 16)
    )
    rb, gb, bb = (
        int(b[1:3], 16), int(b[3:5], 16), int(b[5:7], 16)
    )
    return (
        (ra - rb) ** 2 + (ga - gb) ** 2 + (ba - bb) ** 2
    ) ** 0.5


def nearest_n(target: str, n: int = 12) -> list[str]:
    return sorted(
        SOFT_PALETTE, key=lambda c: color_dist(c, target)
    )[:n]


def lum(c: str) -> float:
    return (
        0.299 * int(c[1:3], 16)
        + 0.587 * int(c[3:5], 16)
        + 0.114 * int(c[5:7], 16)
    )


def auto_fg(fg: str, bg: str | None) -> str:
    """前景色与背景色冲突时自动调整"""
    if not bg:
        return fg
    if abs(lum(fg) - lum(bg)) < 60:
        if lum(bg) <= 128:
            return "#ffffff"
        r = max(0, int(fg[1:3], 16) - 80)
        g = max(0, int(fg[3:5], 16) - 80)
        b = max(0, int(fg[5:7], 16) - 80)
        return f"#{r:02x}{g:02x}{b:02x}"
    return fg


# ══════════════════════════════════════════
# 内置规则（8 条，不可改正则，可改颜色和开关）
# ══════════════════════════════════════════
BUILTIN_RULES = [
    {
        "id": "timestamp",
        "name": "时间戳",
        "pattern": r"^\[?\d[\d:.]+\]?\s?",
        "fg": "#8c8c8c",
        "bg": None,
    },
    {
        "id": "bracket",
        "name": "方括号标签",
        "pattern": r"\[[A-Za-z_][\w.:/-]*\]",
        "fg": "#5b8cc2",
        "bg": None,
    },
    {
        "id": "hex_addr",
        "name": "HEX 地址",
        "pattern": r"0x[0-9a-fA-F]+",
        "fg": "#c47e2a",
        "bg": None,
    },
    {
        "id": "number",
        "name": "纯数字",
        "pattern": r"(?<![\.\w])\d+(?![\.\w])",
        "fg": "#2a9d8f",
        "bg": None,
    },
    {
        "id": "error",
        "name": "ERROR / FAIL",
        "pattern": r"\b(?:error|fail|fatal)\b",
        "fg": "#c0392b",
        "bg": "#fdecea",
    },
    {
        "id": "warn",
        "name": "WARN",
        "pattern": r"\b(?:warn|warning)\b",
        "fg": "#b8860b",
        "bg": "#fef9e7",
    },
    {
        "id": "success",
        "name": "OK / SUCCESS",
        "pattern": r"\b(?:ok|success|done|enable)\b",
        "fg": "#27864e",
        "bg": None,
    },
    {
        "id": "disable",
        "name": "DISABLE / STOP",
        "pattern": r"\b(?:disable|off|stop)\b",
        "fg": "#b05a30",
        "bg": None,
    },
]

PREVIEW_TEXT = (
    "[14:30:02.123] [ISP] ISP_ioctl: "
    "disable CG/MTCMOS 0x18000 ok count=42"
)


# ══════════════════════════════════════════
# LogHighlighter — QSyntaxHighlighter
# ══════════════════════════════════════════
class LogHighlighter(QSyntaxHighlighter):
    """日志高亮器：先内置规则，再用户规则（用户优先覆盖）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._enabled = True
        self._builtin: list[tuple] = []
        self._user: list[tuple] = []
        self._load_defaults()

    @staticmethod
    def _make_fmt(fg, bg=None):
        fmt = QTextCharFormat()
        if bg:
            fg = auto_fg(fg, bg)
            fmt.setBackground(QColor(bg))
        fmt.setForeground(QColor(fg))
        return fmt

    def _load_defaults(self):
        self._builtin.clear()
        for r in BUILTIN_RULES:
            try:
                rx = re.compile(
                    r["pattern"], re.IGNORECASE
                )
                self._builtin.append(
                    (rx, self._make_fmt(
                        r["fg"], r.get("bg")
                    ))
                )
            except re.error:
                pass

    def set_enabled(self, v: bool):
        self._enabled = v
        self.rehighlight()

    def load_config(self, config: dict):
        hl = config.get("highlight", {})
        self._enabled = hl.get("enabled", True)
        bc = hl.get("builtin_rules", {})
        self._builtin.clear()
        for r in BUILTIN_RULES:
            rc = bc.get(r["id"], {})
            if not rc.get("enabled", True):
                continue
            fg = rc.get("fg", r["fg"])
            bg = rc.get("bg", r.get("bg"))
            try:
                rx = re.compile(
                    r["pattern"], re.IGNORECASE
                )
                self._builtin.append(
                    (rx, self._make_fmt(fg, bg))
                )
            except re.error:
                pass
        self._user.clear()
        for ur in hl.get("user_rules", []):
            if not ur.get("enabled", True):
                continue
            kw = ur.get("keyword", "")
            if not kw:
                continue
            fg = ur.get("fg", "#374151")
            bg = ur.get("bg")
            pat = (
                kw if ur.get("is_regex")
                else re.escape(kw)
            )
            try:
                rx = re.compile(pat, re.IGNORECASE)
                self._user.append(
                    (rx, self._make_fmt(fg, bg))
                )
            except re.error:
                pass
        self.rehighlight()

    def highlightBlock(self, text: str):
        if not self._enabled:
            return
        # ★ 先把整块重置为默认文字色，
        #   覆盖 insertHtml 带进来的 #4ec9b0
        base = QTextCharFormat()
        base.setForeground(QColor("#1e293b"))
        self.setFormat(0, len(text), base)
        for rx, fmt in self._builtin:
            for m in rx.finditer(text):
                self.setFormat(
                    m.start(),
                    m.end() - m.start(),
                    fmt,
                )
        for rx, fmt in self._user:
            for m in rx.finditer(text):
                self.setFormat(
                    m.start(),
                    m.end() - m.start(),
                    fmt,
                )