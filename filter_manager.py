"""
filter_manager.py - 过滤器管理模块（占位版本）
第一步暂不实现过滤功能，预留接口供后续扩展。

后续计划：
  - 多 Tab 过滤：每个 Tab 对应一组关键词过滤规则
  - 关键词高亮：不同关键词用不同颜色高亮
  - 正则表达式支持
  - 过滤规则的保存/加载
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class FilterManager(QWidget):
    """
    过滤器管理组件（占位）。
    当前版本仅显示占位提示，后续版本将实现完整的多 Tab 过滤功能。
    """

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self._config = config
        self._filters: list[dict] = []   # 过滤规则列表（预留）
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        placeholder = QLabel("过滤器功能\n（即将在下一版本实现）")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("""
            QLabel {
                color: #808080;
                font-size: 13px;
                border: 1px dashed #3c3c3c;
                border-radius: 4px;
                padding: 20px;
            }
        """)
        layout.addWidget(placeholder)
        layout.addStretch()

    # ── 预留接口 ──────────────────────────────

    def add_filter(self, keyword: str, color: str = "#ffff00",
                   is_regex: bool = False) -> int:
        """
        添加一条过滤/高亮规则。
        返回规则 ID（索引）。
        （占位，暂未实现）
        """
        rule = {
            "id": len(self._filters),
            "keyword": keyword,
            "color": color,
            "is_regex": is_regex,
            "enabled": True
        }
        self._filters.append(rule)
        return rule["id"]

    def remove_filter(self, rule_id: int):
        """删除指定 ID 的过滤规则（占位）"""
        self._filters = [f for f in self._filters if f["id"] != rule_id]

    def get_filters(self) -> list[dict]:
        """返回当前所有过滤规则（占位）"""
        return list(self._filters)

    def apply_filters(self, text: str) -> list[tuple[int, int, str]]:
        """
        对文本应用过滤规则，返回高亮区间列表。
        每个元素为 (start, end, color)。
        （占位，暂返回空列表）
        """
        return []
