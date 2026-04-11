"""
theme.py - 设计 token 统一管理
v0.7 — 颜色、字号、间距、stylesheet 生成函数

所有 UI 文件引用此模块的常量，不再裸写魔法字符串。
修改一处 → 全局生效。
"""
from __future__ import annotations


# ════════════════════════════════════════════
# 颜色常量
# ════════════════════════════════════════════

# ── 主色 ──
PRIMARY = "#2563eb"          # 蓝色，选中态/强调
PRIMARY_HOVER = "#3b82f6"    # hover 蓝
PRIMARY_PRESSED = "#1d4ed8"  # pressed 深蓝
PRIMARY_LIGHT = "#dbeafe"    # 浅蓝选中背景
PRIMARY_BG = "#eff6ff"       # 极浅蓝背景
PRIMARY_NAV = "#e0e7ff"      # 导航选中背景

# ── 背景 ──
BG_MAIN = "#eef0f3"          # 主窗口背景
BG_PANEL = "#ffffff"         # 面板/输入框背景
BG_HOVER = "#f3f4f6"         # 普通按钮 hover
BG_PRESSED = "#e5e7eb"       # 普通按钮 pressed
BG_SUBTLE = "#f9fafb"        # 微弱 hover（列表项）
BG_LINE_NUM = "#f8f9fa"      # 行号区域背景
BG_SELECTED_ROW = "#eff6ff"  # 选中行背景

# ── 文字 ──
TEXT_PRIMARY = "#374151"     # 主文字
TEXT_DARK = "#1f2937"        # 深色文字
TEXT_LOG = "#1e293b"         # 日志区文字
TEXT_SECONDARY = "#6b7280"   # 次要文字
TEXT_MUTED = "#9ca3af"       # 占位符/标注
TEXT_DISABLED = "#c0c0c0"    # 禁用态文字
TEXT_ARROW = "#b0b8c4"       # 滚动条箭头

# ── 边框 ──
BORDER_DEFAULT = "#d1d5db"   # 默认边框
BORDER_FOCUS = "#3b82f6"     # 聚焦边框
BORDER_LIGHT = "#e5e7eb"     # 浅色边框/分隔线
BORDER_PANEL = "#b0b8c4"     # 面板外框

# ── 标题栏按钮 ──
TITLEBAR_HOVER = "#e8e8e8"
TITLEBAR_PRESSED = "#d2d2d2"
CLOSE_FG = "#868686"         # 关闭按钮默认
CLOSE_FG_HOVER = "#5f6368"
CLOSE_FG_PRESSED = "#3c4043"

# ── 状态色 ──
ERROR = "#dc2626"            # 错误红
ERROR_BORDER = "#ef4444"     # 冲突边框红
ERROR_BG = "#fef2f2"         # 冲突背景浅红
ERROR_HOVER_BG = "#fee2e2"   # 红色 hover 背景
ERROR_PRESSED_BG = "#fecaca" # 红色 pressed 背景
ERROR_DARK = "#b91c1c"       # 深红
SUCCESS = "#16a34a"          # 成功绿
WARN_TEXT = "#e67700"         # 警告文字
SEND_BTN = "#16a34a"         # 发送按钮绿
SEND_BTN_HOVER = "#22c55e"
SEND_BTN_PRESSED = "#15803d"
TX_COLOR = "#92400e"         # TX 发送文字
RX_COLOR = "#1a6b3a"         # RX 接收文字

# ── 遮罩 ──
OVERLAY_COLOR = (0, 0, 0, 80)  # rgba 遮罩


# ════════════════════════════════════════════
# 字号常量
# ════════════════════════════════════════════
POPUP_FONT_SIZE = 16         # 弹窗消息统一字号
LABEL_FONT_SIZE = 13         # 标签字号
SMALL_FONT_SIZE = 12         # 小字号（规则行等）
TINY_FONT_SIZE = 11          # 极小字号（提示/表头）
HEADER_FONT_SIZE = 10        # 表头字号
DEFAULT_LOG_FONT_SIZE = 12   # 日志区默认字号
MIN_LOG_FONT_SIZE = 8
MAX_LOG_FONT_SIZE = 30


# ════════════════════════════════════════════
# 间距/尺寸常量
# ════════════════════════════════════════════
PANEL_W = 550                # 设置弹窗面板宽度
PANEL_H = 560                # 设置弹窗面板高度
PANEL_RADIUS = 10            # 设置弹窗圆角
POPUP_RADIUS = 8             # 弹窗圆角
SEPARATOR_HEIGHT = 2         # 分隔线高度
SEPARATOR_SPACING = 12       # 分隔线上下间距
CLOSE_BTN_SIZE = 28          # 关闭按钮尺寸
CLOSE_BTN_HOVER_RADIUS = 11  # 关闭按钮 hover 圆圈半径
TOOLBAR_BTN_SIZE = 26        # 工具栏按钮边长
TOOLBAR_ICON_SIZE = 14       # 工具栏图标绘制区域


# ════════════════════════════════════════════
# 通用 Stylesheet 生成函数
# ════════════════════════════════════════════

def checkbox_ss() -> str:
    """统一 QCheckBox 样式 — 12px indicator + 蓝色选中"""
    return (
        f"QCheckBox {{ font-size: {LABEL_FONT_SIZE}px;"
        f" background: transparent; spacing: 5px; }}"
        "QCheckBox::indicator {"
        "  width: 12px; height: 12px; margin: 2px; }"
        "QCheckBox::indicator:unchecked {"
        f"  border: 1px solid {TEXT_MUTED};"
        f"  border-radius: 3px; background: {BG_PANEL}; }}"
        "QCheckBox::indicator:checked {"
        f"  border: 1px solid {PRIMARY};"
        f"  border-radius: 3px; background: {PRIMARY}; }}"
        "QCheckBox::indicator:hover {"
        f"  border-color: {PRIMARY_HOVER}; }}"
        f"QCheckBox:disabled {{ color: {TEXT_DISABLED}; }}"
        "QCheckBox::indicator:disabled {"
        f"  border-color: {BORDER_DEFAULT};"
        f"  background: #f0f0f0; }}"
        "QCheckBox::indicator:checked:disabled {"
        "  border-color: #93b4f0;"
        "  background: #93b4f0; }"
    )


def radio_ss() -> str:
    """统一 QRadioButton 样式 — 10px indicator + 蓝色选中"""
    return (
        f"QRadioButton {{ font-size: {LABEL_FONT_SIZE}px;"
        "  background: transparent; spacing: 4px; }"
        "QRadioButton::indicator {"
        "  width: 10px; height: 10px; margin: 2px; }"
        "QRadioButton::indicator:unchecked {"
        f"  border: 1px solid {TEXT_MUTED};"
        f"  border-radius: 5px; background: {BG_PANEL}; }}"
        "QRadioButton::indicator:checked {"
        f"  border: 1px solid {PRIMARY};"
        f"  border-radius: 5px; background: {PRIMARY}; }}"
        "QRadioButton::indicator:hover {"
        f"  border-color: {PRIMARY_HOVER}; }}"
        f"QRadioButton:disabled {{ color: {TEXT_DISABLED}; }}"
        "QRadioButton::indicator:disabled {"
        f"  border-color: {BORDER_DEFAULT};"
        f"  background: #f0f0f0; }}"
    )


def mini_checkbox_ss() -> str:
    """紧凑 checkbox（Aa / .* 等小开关）"""
    return (
        f"QCheckBox{{font-size:{TINY_FONT_SIZE}px;"
        "font-family:Consolas,monospace;"
        "background:transparent;spacing:3px}"
        "QCheckBox::indicator{width:12px;height:12px;margin:2px}"
        "QCheckBox::indicator:unchecked{"
        f"border:1px solid {TEXT_MUTED};border-radius:3px;"
        f"background:{BG_PANEL}}}"
        "QCheckBox::indicator:checked{"
        f"border:1px solid {PRIMARY};border-radius:3px;"
        f"background:{PRIMARY}}}"
        f"QCheckBox::indicator:hover{{border-color:{PRIMARY_HOVER}}}"
    )


def line_edit_ss(*, font_size=SMALL_FONT_SIZE) -> str:
    """统一 QLineEdit 样式"""
    return (
        f"QLineEdit{{font-size:{font_size}px;color:{TEXT_PRIMARY};"
        f"background:{BG_PANEL};border:1.5px solid {BORDER_DEFAULT};"
        "border-radius:6px;padding:0px 4px;"
        f"selection-background-color:{PRIMARY};"
        "selection-color:#ffffff}}"
        f"QLineEdit:focus{{border-color:{BORDER_FOCUS}}}"
    )


def nav_btn_ss() -> str:
    """设置页左侧导航按钮样式"""
    return (
        "QPushButton { background: transparent; border: none;"
        "  border-radius: 6px; text-align: left;"
        f"  padding: 0 12px; font-size: {LABEL_FONT_SIZE}px;"
        f"  color: {TEXT_PRIMARY}; }}"
        f"QPushButton:checked {{ background: {PRIMARY_NAV};"
        f"  color: {PRIMARY}; font-weight: 600; }}"
        f"QPushButton:hover:!checked {{ background: {BG_HOVER}; }}"
    )


def borderless_btn_ss(
    *,
    font_size=LABEL_FONT_SIZE,
    fg=TEXT_SECONDARY,
    fg_hover=TEXT_PRIMARY,
) -> str:
    """无界按钮样式（浏览、重置等辅助按钮）"""
    return (
        f"QPushButton{{background:transparent;border:none;"
        f"border-radius:6px;font-size:{font_size}px;"
        f"color:{fg};min-height:0;min-width:0;padding:2px 6px}}"
        f"QPushButton:hover{{background:{BG_HOVER};color:{fg_hover};"
        "border-radius:6px}}"
        f"QPushButton:pressed{{background:{BG_PRESSED}}}"
    )


def primary_btn_ss() -> str:
    """主操作蓝色按钮（弹窗确定等）"""
    return (
        f"QPushButton{{background:{PRIMARY};"
        "border:none;border-radius:6px;"
        f"color:#fff;font-size:{LABEL_FONT_SIZE}px;"
        "font-weight:600}}"
        f"QPushButton:hover{{background:{PRIMARY_HOVER}}}"
        f"QPushButton:pressed{{background:{PRIMARY_PRESSED}}}"
    )


def cancel_btn_ss() -> str:
    """取消按钮（白色底 + 灰色边框）"""
    return (
        f"QPushButton{{background:{BG_PANEL};"
        f"border:1px solid {BORDER_DEFAULT};"
        f"border-radius:6px;color:{TEXT_PRIMARY};"
        f"font-size:{LABEL_FONT_SIZE}px}}"
        f"QPushButton:hover{{background:{BG_HOVER};"
        f"border-color:{TEXT_MUTED}}}"
        f"QPushButton:pressed{{background:{BG_PRESSED}}}"
    )


def separator_ss() -> str:
    """设置页分隔线样式"""
    return f"background: {BORDER_LIGHT};"


def header_label_ss() -> str:
    """表头标签样式"""
    return (
        f"font-size:{HEADER_FONT_SIZE}px;"
        f"color:{TEXT_MUTED};background:transparent;"
    )


def section_label_ss() -> str:
    """小节标题样式（如 '内置规则'、'自定义规则'）"""
    return (
        f"font-size:{SMALL_FONT_SIZE}px;"
        f"color:{TEXT_SECONDARY};background:transparent;"
    )