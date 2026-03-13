"""
filter_manager.py - 多 Tab 关键词过滤管理模块
v1.7:
- Tab 右键菜单（重命名/关闭），去掉 × 按钮
- 蓝线固定宽度 20px，底部居中（重写 paintEvent）
- 过滤栏左右边距与主布局对齐
"""

from __future__ import annotations
from typing import Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabBar,
    QTabWidget, QLineEdit, QPushButton,
    QCheckBox, QInputDialog
)
from PySide6.QtCore import Qt, Signal, QRect, QPoint
from PySide6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor, QPainter, QPen
from rounded_menu import RoundedMenu, RoundedContextTextEdit


# ══════════════════════════════════════════════
# 单个过滤 Tab 的日志视图
# ══════════════════════════════════════════════
class FilteredLogView(RoundedContextTextEdit):
    def __init__(self, keywords: list[str] = None,
                 case_sensitive: bool = False,
                 invert: bool = False,
                 parent=None):
        super().__init__(parent)
        self.keywords: list[str] = keywords or []
        self.case_sensitive: bool = case_sensitive
        self.invert: bool = invert
        self._auto_scroll = True
        self._line_count = 0
        self._max_lines = 5000

        self.setReadOnly(True)
        self.setLineWrapMode(RoundedContextTextEdit.LineWrapMode.NoWrap)
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setStyleSheet(
            "QTextEdit { border: 1px solid #e5e7eb; border-radius: 6px; "
            "background: #ffffff; color: #1e293b; padding: 2px; }"
        )

    def set_auto_scroll(self, v: bool): self._auto_scroll = v

    def matches(self, line: str) -> bool:
        if not self.keywords:
            return True
        check = line if self.case_sensitive else line.lower()
        hit = any(
            (kw if self.case_sensitive else kw.lower()) in check
            for kw in self.keywords
        )
        return (not hit) if self.invert else hit

    def append_line(self, line: str, color: str = "#1e293b"):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.setCharFormat(fmt)
        cursor.insertText(line)
        self._line_count += line.count('\n')
        if self._line_count > self._max_lines:
            self._trim()
        if self._auto_scroll:
            self.setTextCursor(cursor)
            self.ensureCursorVisible()

    def _trim(self):
        n = self._max_lines // 4
        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        for _ in range(n):
            cursor.movePosition(QTextCursor.MoveOperation.Down,
                                QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        self._line_count -= n

    @staticmethod
    def to_text(data: bytes) -> str:
        return data.decode("utf-8", errors="replace")

    @staticmethod
    def to_hex(data: bytes) -> str:
        lines = []
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            lines.append(" ".join(f"{b:02X}" for b in chunk))
        return "\n".join(lines) + "\n"


# ══════════════════════════════════════════════
# 自定义 TabBar：
#   - 右键菜单（重命名/关闭）
#   - 蓝线固定宽度 20px，底部居中
#   - 点击 + Tab 发出信号
# ══════════════════════════════════════════════
_BLUE_LINE_W = 20   # 蓝线固定宽度 px
_BLUE_LINE_H = 2    # 蓝线高度 px
_BLUE_COLOR  = QColor("#2563eb")
_PLUS_DATA   = "__plus__"


class RenamableTabBar(QTabBar):
    tab_rename_requested = Signal(int)
    add_tab_requested    = Signal()

    def mousePressEvent(self, event):
        idx = self.tabAt(event.position().toPoint())
        if idx == self.count() - 1 and self.tabData(idx) == _PLUS_DATA:
            if event.button() == Qt.MouseButton.LeftButton:
                self.add_tab_requested.emit()
                return
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        idx = self.tabAt(event.pos())
        if idx < 0:
            return
        # + Tab 不显示菜单
        if self.tabData(idx) == _PLUS_DATA:
            return

        # main Tab 不显示菜单
        if self.tabText(idx).strip() == "main":
            return

        menu = RoundedMenu(self.window())
        act_rename = menu.addAction("重命名")
        menu.addSeparator()
        act_close = menu.addAction("关闭")

        chosen = menu.exec(event.globalPos())
        if chosen is None:
            return
        if chosen == act_rename:
            self.tab_rename_requested.emit(idx)
        elif chosen == act_close:
            # 发出关闭信号（通过 FilterManager 处理）
            self._close_idx = idx
            self.tabCloseRequested.emit(idx)

    def paintEvent(self, event):
        """先画默认 Tab，再在选中 Tab 底部居中画固定宽度蓝线"""
        super().paintEvent(event)
        cur = self.currentIndex()
        if cur < 0:
            return
        rect: QRect = self.tabRect(cur)
        # 用 QStyleOptionTab 获取文字绘制区域，取其中心
        from PySide6.QtWidgets import QStyleOptionTab
        opt = QStyleOptionTab()
        self.initStyleOption(opt, cur)
        text_rect = self.style().subElementRect(
            self.style().SubElement.SE_TabBarTabText, opt, self)
        if text_rect.isValid():
            cx = text_rect.x() + text_rect.width() / 2.0
        else:
            cx = rect.x() + rect.width() / 2.0
        x = round(cx - _BLUE_LINE_W / 2.0)
        y = rect.bottom() - _BLUE_LINE_H + 1
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        pen = QPen(_BLUE_COLOR, _BLUE_LINE_H)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen)
        painter.drawLine(x, y, x + _BLUE_LINE_W - 1, y)
        painter.end()


# ══════════════════════════════════════════════
# 过滤器管理器（多 Tab）
# ══════════════════════════════════════════════
class FilterManager(QWidget):
    filter_changed = Signal()

    def __init__(self, config: dict,
                 h_margin: int = 10,
                 toggle_send_callback: Callable | None = None,
                 parent=None):
        super().__init__(parent)
        self._config = config
        self._h_margin = h_margin
        self._toggle_send_cb = toggle_send_callback
        self._show_hex = False
        self._auto_scroll = True
        self._line_buffer = ""
        self._history: list[tuple[str, str]] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._tab_bar = RenamableTabBar()
        self._tabs.setTabBar(self._tab_bar)
        self._tab_bar.tab_rename_requested.connect(self._rename_tab)
        self._tab_bar.add_tab_requested.connect(self._add_new_tab)
        self._tab_bar.tabCloseRequested.connect(self._close_tab_by_idx)
        self._tabs.setTabsClosable(False)
        self._tabs.setMovable(False)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self._tabs, stretch=1)

        layout.addWidget(self._build_filter_bar())

        # main Tab
        main_view = FilteredLogView()
        main_view.set_auto_scroll(self._auto_scroll)
        self._tabs.addTab(main_view, "main")

        # filter Tabs
        for i in range(1, 2):
            self._add_tab(f"filter-{i:02d}", closable=True)

        # + Tab
        plus_widget = QWidget()
        self._tabs.addTab(plus_widget, "+")
        plus_idx = self._tabs.count() - 1
        self._tab_bar.setTabData(plus_idx, _PLUS_DATA)

        self._tabs.setCurrentIndex(0)
        self._on_tab_changed(0)

    def _build_filter_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("FilterBar")
        bar.setFixedHeight(36)

        h = QHBoxLayout(bar)
        h.setContentsMargins(0, 4, 0, 4)
        h.setSpacing(8)

        self._kw_edit = QLineEdit()
        self._kw_edit.setObjectName("KwEdit")
        self._kw_edit.setPlaceholderText(
            "关键词过滤（多个关键词用 | 分隔，如: error|warn|fail）— 按 Enter 应用"
        )
        self._kw_edit.returnPressed.connect(self._apply_kw)
        h.addWidget(self._kw_edit, stretch=1)

        self._chk_case = QCheckBox("区分大小写")
        self._chk_invert = QCheckBox("反选")
        self._chk_invert.setToolTip("显示不包含关键词的行")
        h.addWidget(self._chk_case)
        h.addWidget(self._chk_invert)

        self._btn_refilter = QPushButton("历史")
        self._btn_refilter.setObjectName("BtnRefilter")
        self._btn_refilter.setToolTip("用当前关键词重新过滤已有历史数据")
        self._btn_refilter.clicked.connect(self._refilter)
        h.addWidget(self._btn_refilter)

        self._btn_toggle = QPushButton("▼")
        self._btn_toggle.setObjectName("BtnToggleSend")
        self._btn_toggle.setFlat(True)
        self._btn_toggle.setFixedSize(28, 28)
        self._btn_toggle.setToolTip("隐藏/显示发送区")
        if self._toggle_send_cb:
            self._btn_toggle.clicked.connect(self._toggle_send_cb)
        h.addWidget(self._btn_toggle)
        return bar

    # ── Tab 管理 ──────────────────────────────

    def _find_plus_idx(self) -> int:
        for i in range(self._tabs.count()):
            if self._tab_bar.tabData(i) == _PLUS_DATA:
                return i
        return -1

    def _add_tab(self, name: str, closable: bool = True) -> int:
        view = FilteredLogView()
        view.set_auto_scroll(self._auto_scroll)
        plus_idx = self._find_plus_idx()
        if plus_idx >= 0:
            self._tabs.insertTab(plus_idx, view, name)
            idx = plus_idx
        else:
            idx = self._tabs.addTab(view, name)
        return idx

    def _add_new_tab(self):
        existing = []
        for i in range(self._tabs.count()):
            t = self._tabs.tabText(i).strip()
            if t.startswith("filter-"):
                try: existing.append(int(t.split("-")[1]))
                except: pass
        n = max(existing) + 1 if existing else 1
        new_idx = self._add_tab(f"filter-{n:02d}", closable=True)
        self._tabs.setCurrentIndex(new_idx)

    def _close_tab_by_idx(self, idx: int):
        name = self._tabs.tabText(idx).strip()
        if name in ("main", "+"):
            return
        if self._tab_bar.tabData(idx) == _PLUS_DATA:
            return
        self._tabs.removeTab(idx)

    def _rename_tab(self, idx: int):
        name = self._tabs.tabText(idx).strip()
        if name == "main":
            return
        if self._tab_bar.tabData(idx) == _PLUS_DATA:
            return
        new_name, ok = QInputDialog.getText(
            self, "重命名 Tab", "请输入新名称：", text=name
        )
        if ok and new_name.strip():
            self._tabs.setTabText(idx, new_name.strip())

    def _on_tab_changed(self, idx: int):
        if self._tab_bar.tabData(idx) == _PLUS_DATA:
            prev = max(0, idx - 1)
            self._tabs.setCurrentIndex(prev)
            return

        view = self._tabs.widget(idx)
        if view is None: return
        is_main = (self._tabs.tabText(idx).strip() == "main")

        self._kw_edit.setEnabled(not is_main)
        self._chk_case.setEnabled(not is_main)
        self._chk_invert.setEnabled(not is_main)
        self._btn_refilter.setEnabled(not is_main)

        if is_main:
            self._kw_edit.setPlaceholderText("main 窗口显示所有数据（不过滤）")
            self._kw_edit.clear()
        elif isinstance(view, FilteredLogView):
            self._kw_edit.setPlaceholderText(
                "关键词过滤（多个关键词用 | 分隔，如: error|warn|fail）— 按 Enter 应用"
            )
            self._kw_edit.setText("|".join(view.keywords))
            self._chk_case.setChecked(view.case_sensitive)
            self._chk_invert.setChecked(view.invert)

    def _apply_kw(self):
        idx = self._tabs.currentIndex()
        view = self._tabs.widget(idx)
        if not isinstance(view, FilteredLogView): return
        name = self._tabs.tabText(idx).strip()
        if name == "main": return
        if self._tab_bar.tabData(idx) == _PLUS_DATA: return
        raw = self._kw_edit.text().strip()
        view.keywords = [k.strip() for k in raw.split("|") if k.strip()]
        view.case_sensitive = self._chk_case.isChecked()
        view.invert = self._chk_invert.isChecked()
        self.filter_changed.emit()

    def _refilter(self):
        self._apply_kw()
        idx = self._tabs.currentIndex()
        view = self._tabs.widget(idx)
        if not isinstance(view, FilteredLogView): return
        view.clear(); view._line_count = 0
        for line, color in self._history:
            if view.matches(line):
                view.append_line(line, color)

    # ── 公开接口 ──────────────────────────────

    def update_toggle_btn(self, send_visible: bool):
        self._btn_toggle.setText("▼" if send_visible else "▲")

    def append_data(self, data: bytes):
        text = FilteredLogView.to_hex(data) if self._show_hex else FilteredLogView.to_text(data)
        self._dispatch(text, "#1a6b3a")

    def append_sent(self, data: bytes):
        text = FilteredLogView.to_hex(data) if self._show_hex else FilteredLogView.to_text(data)
        self._dispatch("[TX] " + text, "#92400e")

    def append_info(self, msg: str):
        self._dispatch(f"[INFO] {msg}\n", "#6b7280")

    def append_error(self, msg: str):
        self._dispatch(f"[ERROR] {msg}\n", "#dc2626")

    def clear_current(self):
        v = self._tabs.currentWidget()
        if isinstance(v, FilteredLogView):
            v.clear(); v._line_count = 0

    def clear_all(self):
        self._history.clear(); self._line_buffer = ""
        for i in range(self._tabs.count()):
            v = self._tabs.widget(i)
            if isinstance(v, FilteredLogView):
                v.clear(); v._line_count = 0

    def clear_main_and_current(self):
        """清空 main 和当前显示的 filter 内容"""
        # 清空 main tab
        for i in range(self._tabs.count()):
            tab_name = self._tabs.tabText(i).strip()
            if tab_name == "main":
                v = self._tabs.widget(i)
                if isinstance(v, FilteredLogView):
                    v.clear(); v._line_count = 0
                break
        
        # 清空当前显示的 tab（包括 main 本身）
        current_idx = self._tabs.currentIndex()
        v = self._tabs.widget(current_idx)
        if isinstance(v, FilteredLogView):
            v.clear(); v._line_count = 0

    def set_auto_scroll(self, v: bool):
        self._auto_scroll = v
        for i in range(self._tabs.count()):
            w = self._tabs.widget(i)
            if isinstance(w, FilteredLogView):
                w.set_auto_scroll(v)

    def set_show_hex(self, v: bool):
        self._show_hex = v

    # ── 内部分发 ──────────────────────────────

    def _dispatch(self, text: str, color: str):
        combined = self._line_buffer + text
        lines = combined.split('\n')
        self._line_buffer = lines[-1]
        for line in lines[:-1]:
            full = line + '\n'
            self._history.append((full, color))
            if len(self._history) > 20000:
                self._history = self._history[-10000:]
            for i in range(self._tabs.count()):
                v = self._tabs.widget(i)
                if isinstance(v, FilteredLogView) and v.matches(full):
                    v.append_line(full, color)
