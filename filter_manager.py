"""
filter_manager.py - 多 Tab 关键词过滤管理模块
v0.67 — ★ 行号区域（_LineNumberArea）左侧显示
        ★ set_line_numbers_visible 开关
        ★ scrollContentsBy 同步行号滚动
v0.6 — ★ 日志区默认字号 12pt + Ctrl+滚轮/箭头调字号
       ★ 右下角字号提示浮层（2秒后淡出）
       ★ FilteredLogView 绑定 LogHighlighter 高亮引擎
       ★ FilterManager.refresh_highlighter 刷新所有 Tab 高亮
v0.62 — ★ "历史"按钮改名"打开文件"
        ★ hover 悬浮按钮（清空+关闭，右上角淡入淡出）
        ★ Del 关闭 Tab + Ctrl+W 支持（信号路由确认）
        ★ tab_close_requested / hover_clear_requested 信号
        ★ Ctrl+G 跳转行号（goto_line / goto_line_current）
"""
from __future__ import annotations
from typing import Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabBar,
    QTabWidget, QPushButton,
    QCheckBox, QInputDialog,
    QLabel, QGraphicsOpacityEffect,
)
from PySide6.QtCore import (
    Qt, Signal, QRect, QPoint, QPointF, QRectF, QSize,
    QTimer, QPropertyAnimation, QEasingCurve,
)
from PySide6.QtGui import (
    QFont, QColor, QTextCharFormat, QTextCursor,
    QPainter, QPen, QPainterPath,
)
from rounded_menu import (
    RoundedMenu, RoundedContextTextEdit,
    RoundedContextLineEdit,
)
from highlight_engine import LogHighlighter


# ════════════════════════════════════════════
# 悬浮图标按钮（清空 / 关闭）
# ════════════════════════════════════════════
class _HoverIconBtn(QWidget):
    """24×24 圆形图标按钮（paintEvent 绘制 trash / close）"""
    clicked = Signal()

    def __init__(self, icon_type="close", parent=None):
        super().__init__(parent)
        self._icon_type = icon_type  # "trash" or "close"
        self._hovered = False
        self._pressed = False
        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)

    def enterEvent(self, e):
        self._hovered = True; self.update()

    def leaveEvent(self, e):
        self._hovered = False; self._pressed = False; self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._pressed = True; self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if self._pressed and self.rect().contains(
                e.position().toPoint()
            ):
                self.clicked.emit()
            self._pressed = False; self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(0, 0, 24, 24)
        # 背景圆
        if self._pressed:
            bg = QColor("#dbeafe")
        elif self._hovered:
            bg = QColor("#f3f4f6")
        else:
            bg = QColor(255, 255, 255, 0)
        path = QPainterPath()
        path.addEllipse(r)
        p.fillPath(path, bg)
        # 图标线条
        if self._pressed:
            pen_c = QColor("#2563eb")
        elif self._hovered:
            pen_c = QColor("#374151")
        else:
            pen_c = QColor("#9ca3af")
        p.setPen(QPen(pen_c, 1.6, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap))
        cx, cy = 12.0, 12.0
        if self._icon_type == "close":
            d = 4.0
            p.drawLine(QPointF(cx - d, cy - d),
                       QPointF(cx + d, cy + d))
            p.drawLine(QPointF(cx + d, cy - d),
                       QPointF(cx - d, cy + d))
        else:  # trash
            # 桶盖
            p.drawLine(QPointF(8, 8.5), QPointF(16, 8.5))
            p.drawLine(QPointF(10.5, 8.5), QPointF(10.5, 7))
            p.drawLine(QPointF(10.5, 7), QPointF(13.5, 7))
            p.drawLine(QPointF(13.5, 7), QPointF(13.5, 8.5))
            # 桶身
            p.drawLine(QPointF(9, 9.5), QPointF(9.5, 16.5))
            p.drawLine(QPointF(9.5, 16.5), QPointF(14.5, 16.5))
            p.drawLine(QPointF(14.5, 16.5), QPointF(15, 9.5))
            # 竖线
            p.drawLine(QPointF(12, 11), QPointF(12, 15))
        p.end()


# ════════════════════════════════════════════
# 行号区域
# ════════════════════════════════════════════
class _LineNumberArea(QWidget):
    """行号区域 — 绘制在 FilteredLogView 左侧，点击选中对应行"""
    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def sizeHint(self):
        return QSize(self._editor._line_number_width(), 0)

    def paintEvent(self, event):
        self._editor._paint_line_numbers(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._editor._select_line_at(
                int(event.position().y())
            )


# ════════════════════════════════════════════
# 单个过滤 Tab 的日志视图
# ════════════════════════════════════════════
class FilteredLogView(RoundedContextTextEdit):
    font_size_changed = Signal(int)  # ★ v0.6 fix: 通知字号变化
    clear_requested = Signal()   # ★ v0.62: hover 清空
    close_requested = Signal()   # ★ v0.62: hover 关闭

    def __init__(self, keywords=None, case_sensitive=False,
                 invert=False, parent=None):
        super().__init__(parent)
        self.keywords = keywords or []
        self.case_sensitive = case_sensitive
        self.invert = invert
        self._auto_scroll = True
        self._line_count = 0
        self._max_lines = 5000
        # ★ v0.6: resize 防抖
        self._wrap_mode = (
            RoundedContextTextEdit.LineWrapMode.NoWrap
        )
        self._resize_debounce = QTimer(self)
        self._resize_debounce.setSingleShot(True)
        self._resize_debounce.setInterval(300)
        self._resize_debounce.timeout.connect(
            self._restore_wrap
        )
        self.setReadOnly(True)
        self.setLineWrapMode(
            RoundedContextTextEdit.LineWrapMode.NoWrap
        )
        font = QFont("Consolas", 12)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self._highlighter = None  # ★ v0.5

        # ★ v0.6: 字号调节 + 右下角提示浮层
        self._font_size = 12
        self._update_stylesheet()  # ★ 必须在 _font_size 赋值之后
        self._size_tip = QLabel(self)
        self._size_tip.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self._size_tip.setStyleSheet(
            "QLabel{background:rgba(0,0,0,0.55);color:#fff;"
            "font-size:13px;font-family:Consolas,monospace;"
            "border-radius:6px;padding:3px 10px}"
        )
        self._size_tip.setFixedHeight(26)
        self._size_tip.hide()
        self._tip_opacity = QGraphicsOpacityEffect(
            self._size_tip
        )
        self._size_tip.setGraphicsEffect(self._tip_opacity)
        self._tip_opacity.setOpacity(1.0)
        self._tip_fade = QPropertyAnimation(
            self._tip_opacity, b"opacity"
        )
        self._tip_fade.setDuration(400)
        self._tip_fade.setStartValue(1.0)
        self._tip_fade.setEndValue(0.0)
        self._tip_fade.setEasingCurve(
            QEasingCurve.Type.OutCubic
        )
        self._tip_fade.finished.connect(
            self._size_tip.hide
        )
        self._tip_timer = QTimer(self)
        self._tip_timer.setSingleShot(True)
        self._tip_timer.timeout.connect(
            self._tip_fade.start
        )
        # ★ NoWrap 模式：文档宽度跟随内容，消除右侧空白
        self._adjusting_width = False
        self.document().documentLayout().documentSizeChanged.connect(
            self._on_doc_size_changed
        )
        # ★ auto-scroll 智能管理 + 底部回滚按钮
        self._programmatic_scroll = False
        self._scroll_bottom_btn = QPushButton("▼", self)
        self._scroll_bottom_btn.setFixedSize(36, 36)
        self._scroll_bottom_btn.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self._scroll_bottom_btn.setStyleSheet(
            "QPushButton{background:rgba(30,30,30,0.7);"
            "color:#fff;font-size:16px;border:none;"
            "border-radius:18px}"
            "QPushButton:hover{background:rgba(30,30,30,0.85)}"
            "QPushButton:pressed{background:rgba(30,30,30,0.95)}"
        )
        self._scroll_bottom_btn.clicked.connect(
            self._scroll_to_bottom
        )
        self._scroll_bottom_btn.hide()
        self.verticalScrollBar().valueChanged.connect(
            self._on_vscroll_changed
        )

        # ★ v0.62: hover 悬浮按钮栏（清空 + 关闭）
        self._hover_bar = QWidget(self)
        self._hover_bar.setStyleSheet(
            "background:transparent;"
        )
        hover_lay = QHBoxLayout(self._hover_bar)
        hover_lay.setContentsMargins(4, 4, 4, 4)
        hover_lay.setSpacing(2)
        self._hover_clear_btn = _HoverIconBtn(
            "trash", self._hover_bar
        )
        self._hover_close_btn = _HoverIconBtn(
            "close", self._hover_bar
        )
        self._hover_clear_btn.clicked.connect(
            self.clear_requested.emit
        )
        self._hover_close_btn.clicked.connect(
            self.close_requested.emit
        )
        hover_lay.addWidget(self._hover_clear_btn)
        hover_lay.addWidget(self._hover_close_btn)
        self._hover_bar.setFixedSize(60, 32)
        self._hover_bar.hide()
        # opacity + fade 动画
        self._hover_opacity = QGraphicsOpacityEffect(
            self._hover_bar
        )
        self._hover_bar.setGraphicsEffect(self._hover_opacity)
        self._hover_opacity.setOpacity(0.0)
        self._hover_fade_in = QPropertyAnimation(
            self._hover_opacity, b"opacity"
        )
        self._hover_fade_in.setDuration(200)
        self._hover_fade_in.setStartValue(0.0)
        self._hover_fade_in.setEndValue(0.9)
        self._hover_fade_in.setEasingCurve(
            QEasingCurve.Type.OutCubic
        )
        self._hover_fade_out = QPropertyAnimation(
            self._hover_opacity, b"opacity"
        )
        self._hover_fade_out.setDuration(400)
        self._hover_fade_out.setStartValue(0.9)
        self._hover_fade_out.setEndValue(0.0)
        self._hover_fade_out.setEasingCurve(
            QEasingCurve.Type.OutCubic
        )
        self._hover_fade_out.finished.connect(
            self._hover_bar.hide
        )

        # ★ v0.67: 行号区域
        self._line_num_visible = True
        self._line_num_area = _LineNumberArea(self)
        self.document().blockCountChanged.connect(
            self._update_line_number_width
        )
        self._update_line_number_width()


    def set_auto_scroll(self, v):
        self._auto_scroll = v
        if v:
            self._scroll_to_bottom()

    def matches(self, line):
        if not self.keywords:
            return True
        check = line if self.case_sensitive else line.lower()
        hit = any(
            (kw if self.case_sensitive else kw.lower()) in check
            for kw in self.keywords
        )
        return (not hit) if self.invert else hit

    def append_line(self, line, color="#1e293b"):
        # ★ 保存滚动位置（insertText + setTextWidth 都可能重置）
        hbar = self.horizontalScrollBar()
        vbar = self.verticalScrollBar()
        h_val = hbar.value()
        v_val = vbar.value()
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.setCharFormat(fmt)
        cursor.insertText(line)
        self._line_count += line.count('\n')
        if self._max_lines > 0 and self._line_count > self._max_lines:
            self._trim()
        # ★ 恢复滚动位置
        self._programmatic_scroll = True
        if self._auto_scroll:
            vbar.setValue(vbar.maximum())
        else:
            vbar.setValue(v_val)
        hbar.setValue(h_val)
        self._programmatic_scroll = False

    def _trim(self):
        n = self._max_lines // 4
        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        for _ in range(n):
            cursor.movePosition(
                QTextCursor.MoveOperation.Down,
                QTextCursor.MoveMode.KeepAnchor,
            )
        cursor.removeSelectedText()
        self._line_count -= n

    @staticmethod
    def to_text(data):
        return data.decode("utf-8", errors="replace")

    @staticmethod
    def to_hex(data):
        lines = []
        for i in range(0, len(data), 16):
            chunk = data[i:i + 16]
            lines.append(" ".join(f"{b:02X}" for b in chunk))
        return "\n".join(lines) + "\n"


    # ★ v0.6 fix: instance stylesheet 覆盖全局 STYLE 的 font-size
    def _update_stylesheet(self):
        self.setStyleSheet(
            "QTextEdit { border: 1px solid #e5e7eb; "
            "border-radius: 6px; background: #ffffff; "
            "color: #1e293b; padding: 2px; "
            f"font-size: {self._font_size}pt; "
            "}"
            "QTextEdit:focus { border: 1px solid #3b82f6; }"
        )

    def _apply_font_size(self, size):
        """统一字号入口 — QFont + stylesheet 双写"""
        self._font_size = size
        font = self.font()
        font.setPointSize(size)
        self.setFont(font)
        self._update_stylesheet()
        self._update_line_number_width()
        # ★ Fix: 延迟到下一帧重排，等字号变化的布局完成后再修正
        QTimer.singleShot(0, self._relayout_after_font)

    def _relayout_after_font(self):
        """字号变化后延迟触发的完整重排"""
        doc = self.document()
        doc.setTextWidth(-1)
        if self._wrap_mode == self.LineWrapMode.NoWrap:
            self._adjust_doc_width()
        # ★ 修正滚动位置：跟踪底部时重新沿底
        vbar = self.verticalScrollBar()
        if self._auto_scroll:
            self._programmatic_scroll = True
            vbar.setValue(vbar.maximum())
            self._programmatic_scroll = False

    # ★ v0.6: 字号调节
    def _change_font_size(self, delta):
        new = max(8, min(30, self._font_size + delta))
        if new == self._font_size:
            return
        self._apply_font_size(new)
        self._show_size_tip()
        self.font_size_changed.emit(new)

    def _show_size_tip(self):
        self._tip_fade.stop()
        self._tip_opacity.setOpacity(1.0)
        self._size_tip.setText(f"{self._font_size}pt")
        self._size_tip.adjustSize()
        x = self.width() - self._size_tip.width() - 8
        y = self.height() - self._size_tip.height() - 8
        self._size_tip.move(x, y)
        self._size_tip.show()
        self._tip_timer.start(2000)

    # ★ auto-scroll 智能管理
    def _on_vscroll_changed(self, value):
        if self._programmatic_scroll:
            return
        vbar = self.verticalScrollBar()
        at_bottom = value >= vbar.maximum() - 5
        if at_bottom and not self._auto_scroll:
            self._auto_scroll = True
            self._scroll_bottom_btn.hide()
        elif not at_bottom and self._auto_scroll:
            self._auto_scroll = False
            self._scroll_bottom_btn.show()
            self._update_scroll_btn_pos()

    def _scroll_to_bottom(self):
        self._auto_scroll = True
        self._scroll_bottom_btn.hide()
        self._programmatic_scroll = True
        vbar = self.verticalScrollBar()
        vbar.setValue(vbar.maximum())
        self._programmatic_scroll = False

    def _update_scroll_btn_pos(self):
        vp = self.viewport()
        x = vp.x() + (vp.width() - self._scroll_bottom_btn.width()) // 2
        y = vp.y() + vp.height() - self._scroll_bottom_btn.height() - 12
        self._scroll_bottom_btn.move(x, y)
        self._scroll_bottom_btn.raise_()

    # ★ NoWrap 文档宽度自适应 — 消除多余空白
    def _on_doc_size_changed(self, size):
        if self._adjusting_width:
            return
        if self._resize_frozen:
            return
        if self._wrap_mode != self.LineWrapMode.NoWrap:
            return
        self._adjust_doc_width()

    def _adjust_doc_width(self):
        """NoWrap: 文档宽度 = max(内容宽度, 视口宽度)"""
        doc = self.document()
        self._adjusting_width = True
        ideal = doc.idealWidth()
        vp_w = self.viewport().width()
        new_w = max(ideal, vp_w)
        if abs(doc.textWidth() - new_w) > 1:
            # ★ setTextWidth 触发文档重排，会重置滚动条
            hbar = self.horizontalScrollBar()
            vbar = self.verticalScrollBar()
            h_val = hbar.value()
            v_val = vbar.value()
            doc.setTextWidth(new_w)
            hbar.setValue(h_val)
            vbar.setValue(v_val)
        self._adjusting_width = False

    # ★ v0.62: hover 悬浮按钮 — 淡入 / 淡出
    def enterEvent(self, event):
        super().enterEvent(event)
        self._hover_fade_out.stop()
        cur = self._hover_opacity.opacity()
        self._hover_fade_in.setStartValue(cur)
        self._update_hover_pos()
        self._hover_bar.show()
        self._hover_bar.raise_()
        self._hover_fade_in.start()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._hover_fade_in.stop()
        cur = self._hover_opacity.opacity()
        self._hover_fade_out.setStartValue(cur)
        self._hover_fade_out.start()

    def set_closable(self, closable):
        """main tab 隐藏关闭按钮"""
        self._hover_close_btn.setVisible(closable)
        self._hover_bar.setFixedSize(
            60 if closable else 36, 32
        )

    def _update_hover_pos(self):
        vp = self.viewport()
        x = vp.x() + vp.width() - self._hover_bar.width() - 6
        y = vp.y() + 6
        self._hover_bar.move(x, y)

    # ★ v0.67: 行号显示
    def _line_number_width(self):
        if not self._line_num_visible:
            return 0
        digits = len(str(max(1, self.document().blockCount())))
        digits = max(digits, 3)  # 最少 3 位宽度
        fw = self.fontMetrics().horizontalAdvance('9')
        return fw * digits + 16

    def _update_line_number_width(self, _count=0):
        w = self._line_number_width()
        self.setViewportMargins(w, 0, 0, 0)
        self._update_line_number_geometry()

    def _update_line_number_geometry(self):
        cr = self.contentsRect()
        w = self._line_number_width()
        self._line_num_area.setGeometry(
            cr.left(), cr.top(), w, cr.height()
        )

    def _paint_line_numbers(self, event):
        if not self._line_num_visible:
            return
        painter = QPainter(self._line_num_area)
        painter.setRenderHint(
            QPainter.RenderHint.TextAntialiasing, True
        )
        area_w = self._line_num_area.width()
        # 背景
        painter.fillRect(event.rect(), QColor("#f8f9fa"))
        # 右边框线
        painter.setPen(QPen(QColor("#e5e7eb"), 1))
        painter.drawLine(
            area_w - 1, event.rect().top(),
            area_w - 1, event.rect().bottom(),
        )
        # 行号文字
        font = QFont(self.font())
        painter.setFont(font)
        painter.setPen(QColor("#9ca3af"))
        # 找到第一个可见块
        first_cursor = self.cursorForPosition(
            QPoint(0, 0)
        )
        block = first_cursor.block()
        for _ in range(3):
            prev = block.previous()
            if prev.isValid():
                block = prev
        vp_bottom = self.viewport().rect().bottom()
        while block.isValid():
            tc = QTextCursor(block)
            cr = self.cursorRect(tc)
            top = cr.top()
            if top > vp_bottom:
                break
            if top + cr.height() >= 0:
                painter.drawText(
                    0, top, area_w - 8, cr.height(),
                    (Qt.AlignmentFlag.AlignRight
                     | Qt.AlignmentFlag.AlignVCenter),
                    str(block.blockNumber() + 1),
                )
            block = block.next()
        painter.end()

    def set_line_numbers_visible(self, visible):
        self._line_num_visible = visible
        self._line_num_area.setVisible(visible)
        self._update_line_number_width()

    def _select_line_at(self, y):
        """选中行号区域点击位置对应的整行"""
        cursor = self.cursorForPosition(QPoint(0, y))
        block = cursor.block()
        if block.isValid():
            tc = QTextCursor(block)
            tc.movePosition(
                QTextCursor.MoveOperation.StartOfBlock
            )
            tc.movePosition(
                QTextCursor.MoveOperation.EndOfBlock,
                QTextCursor.MoveMode.KeepAnchor,
            )
            self.setTextCursor(tc)

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        if (hasattr(self, '_line_num_area')
                and self._line_num_area.isVisible()):
            self._line_num_area.update()

    def wheelEvent(self, event):
        if (event.modifiers()
                & Qt.KeyboardModifier.ControlModifier):
            delta = 1 if event.angleDelta().y() > 0 else -1
            self._change_font_size(delta)
            event.accept()
            return
        # ★ Shift+滚轮 → 水平滚动
        if (event.modifiers()
                & Qt.KeyboardModifier.ShiftModifier):
            bar = self.horizontalScrollBar()
            dy = event.angleDelta().y()
            if dy:
                bar.setValue(
                    bar.value() - dy
                )
            event.accept()
            return
        super().wheelEvent(event)

    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
        shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)
        # Ctrl+Up/Down: 字号调节
        if ctrl and key == Qt.Key.Key_Up:
            self._change_font_size(1)
            event.accept()
            return
        if ctrl and key == Qt.Key.Key_Down:
            self._change_font_size(-1)
            event.accept()
            return
        # PgUp / PgDn: 翔页（Shift → 水平翔页）
        if key == Qt.Key.Key_PageUp:
            if shift:
                hbar = self.horizontalScrollBar()
                hbar.setValue(
                    hbar.value() - self.viewport().width()
                )
            else:
                vbar = self.verticalScrollBar()
                vbar.setValue(
                    vbar.value() - self.viewport().height()
                )
            event.accept()
            return
        if key == Qt.Key.Key_PageDown:
            if shift:
                hbar = self.horizontalScrollBar()
                hbar.setValue(
                    hbar.value() + self.viewport().width()
                )
            else:
                vbar = self.verticalScrollBar()
                vbar.setValue(
                    vbar.value() + self.viewport().height()
                )
            event.accept()
            return
        # End / Ctrl+End: 跳到最后一行有内容的位置
        if key == Qt.Key.Key_End:
            doc = self.document()
            block = doc.lastBlock()
            while (block.isValid()
                    and block.text().strip() == ''
                    and block.previous().isValid()):
                block = block.previous()
            if block.isValid():
                tc = QTextCursor(block)
                tc.movePosition(
                    QTextCursor.MoveOperation.EndOfBlock
                )
                self.setTextCursor(tc)
                self.ensureCursorVisible()
            event.accept()
            return
        # Home / Ctrl+Home: 跳到文档开头
        if key == Qt.Key.Key_Home:
            tc = QTextCursor(self.document().begin())
            self.setTextCursor(tc)
            vbar = self.verticalScrollBar()
            vbar.setValue(0)
            event.accept()
            return
        super().keyPressEvent(event)

    # ★ v0.6: resize 冻结 — 拖动窗口期间跳过布局重排
    _resize_frozen = False

    def set_resize_frozen(self, frozen):
        self._resize_frozen = frozen
        vp = self.viewport()
        if frozen:
            # ★ 锁定 viewport 尺寸 → QTextDocument 不重排
            vp.setFixedSize(vp.size())
        else:
            # ★ 解锁 viewport
            vp.setMinimumSize(0, 0)
            vp.setMaximumSize(16777215, 16777215)

    def resizeEvent(self, event):
        if self._resize_frozen:
            QWidget.resizeEvent(self, event)
            self._update_line_number_geometry()
            return
        super().resizeEvent(event)
        self._update_line_number_geometry()
        # ★ NoWrap: viewport 变化时同步文档宽度
        if self._wrap_mode == self.LineWrapMode.NoWrap:
            self._adjust_doc_width()
        if self._size_tip.isVisible():
            x = self.width() - self._size_tip.width() - 8
            y = self.height() - self._size_tip.height() - 8
            self._size_tip.move(x, y)
        if self._scroll_bottom_btn.isVisible():
            self._update_scroll_btn_pos()
        if self._hover_bar.isVisible():
            self._update_hover_pos()

    def _restore_wrap(self):
        """resize 结束后恢复自动换行"""
        if self._wrap_mode == (
            RoundedContextTextEdit.LineWrapMode.WidgetWidth
        ):
            self.setLineWrapMode(self._wrap_mode)

    # ★ v0.5 新增：高亮器绑定
    def set_highlighter(self, config: dict | None):
        """绑定/更新 LogHighlighter 到本视图的 document"""
        if not hasattr(self, '_highlighter') or self._highlighter is None:
            self._highlighter = LogHighlighter(self.document())
        if config:
            self._highlighter.load_config(config)
            # ★ v0.6: 同步设置页字号
            fs = config.get("highlight", {}).get(
                "font_size", 12
            )
            if fs != self._font_size:
                self._apply_font_size(fs)
            # ★ v0.6: 同步自动换行设置
            wrap = config.get("highlight", {}).get(
                "word_wrap", False
            )
            wrap_mode = (
                RoundedContextTextEdit.LineWrapMode.WidgetWidth
                if wrap
                else RoundedContextTextEdit.LineWrapMode.NoWrap
            )
            self._wrap_mode = wrap_mode
            self.setLineWrapMode(wrap_mode)
            # ★ v0.6: 同步最大行数
            self._max_lines = config.get(
                "highlight", {}
            ).get("max_lines", 5000)
            # ★ v0.67: 同步行号显示
            show_ln = config.get("highlight", {}).get(
                "show_line_numbers", True
            )
            self.set_line_numbers_visible(show_ln)
        else:
            self._highlighter.set_enabled(False)

    def update_highlighter_only(self, config: dict | None):
        """更新高亮配置但不 rehighlight 已有文本"""
        if not hasattr(self, '_highlighter') or self._highlighter is None:
            self._highlighter = LogHighlighter(self.document())
        if config:
            self._highlighter.load_config(config, rehighlight=False)
            fs = config.get("highlight", {}).get(
                "font_size", 12
            )
            if fs != self._font_size:
                self._apply_font_size(fs)
            wrap = config.get("highlight", {}).get(
                "word_wrap", False
            )
            wrap_mode = (
                RoundedContextTextEdit.LineWrapMode.WidgetWidth
                if wrap
                else RoundedContextTextEdit.LineWrapMode.NoWrap
            )
            self._wrap_mode = wrap_mode
            self.setLineWrapMode(wrap_mode)
            # ★ v0.6: 同步最大行数
            self._max_lines = config.get(
                "highlight", {}
            ).get("max_lines", 5000)
            # ★ v0.67: 同步行号显示
            show_ln = config.get("highlight", {}).get(
                "show_line_numbers", True
            )
            self.set_line_numbers_visible(show_ln)
        else:
            self._highlighter.set_enabled(False)

    # ★ v0.62: Ctrl+G 跳转行号
    def goto_line(self, line_num):
        """跳转到指定行号（1-based），并选中整行"""
        doc = self.document()
        block = doc.findBlockByLineNumber(
            max(0, line_num - 1)
        )
        if not block.isValid():
            block = doc.lastBlock()
        cursor = QTextCursor(block)
        cursor.movePosition(
            QTextCursor.MoveOperation.StartOfBlock
        )
        cursor.movePosition(
            QTextCursor.MoveOperation.EndOfBlock,
            QTextCursor.MoveMode.KeepAnchor,
        )
        self.setTextCursor(cursor)
        # QTextEdit 没有 centerCursor，手动滚动居中
        self.ensureCursorVisible()
        cursor_rect = self.cursorRect()
        vp_h = self.viewport().height()
        vbar = self.verticalScrollBar()
        offset = cursor_rect.top() - vp_h // 2
        if offset > 0:
            vbar.setValue(vbar.value() + offset)


# ════════════════════════════════════════════
# 自定义 TabBar
# ════════════════════════════════════════════
_BLUE_LINE_W = 20
_BLUE_LINE_H = 2
_BLUE_COLOR = QColor("#2563eb")
_PLUS_DATA = "__plus__"

# ★ v0.42: 右键菜单字号已移至 rounded_menu.py 全局控制，不再需要局部覆盖


class RenamableTabBar(QTabBar):
    tab_rename_requested = Signal(int)
    add_tab_requested = Signal()
    save_tab_requested = Signal(int)

    def mousePressEvent(self, event):
        idx = self.tabAt(event.position().toPoint())
        if (idx == self.count() - 1
                and self.tabData(idx) == _PLUS_DATA):
            if event.button() == Qt.MouseButton.LeftButton:
                self.add_tab_requested.emit()
                return
        super().mousePressEvent(event)

    # ★ 重写：main tab 也有右键菜单（仅另存为）
    def contextMenuEvent(self, event):
        idx = self.tabAt(event.pos())
        if idx < 0:
            return
        if self.tabData(idx) == _PLUS_DATA:
            return
        is_main = self.tabText(idx).strip() == "main"
        menu = RoundedMenu(self.window())

        act_rename = None
        act_close = None
        if not is_main:
            act_rename = menu.addAction("重命名")
        act_save = menu.addAction("另存为…")
        if not is_main:
            menu.addSeparator()
            act_close = menu.addAction("关闭")
        chosen = menu.exec(event.globalPos())
        if chosen is None:
            return
        if chosen == act_rename:
            self.tab_rename_requested.emit(idx)
        elif chosen == act_save:
            self.save_tab_requested.emit(idx)
        elif chosen == act_close:
            self.tabCloseRequested.emit(idx)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            idx = self.currentIndex()
            if (idx >= 0
                    and self.tabData(idx) != _PLUS_DATA
                    and self.tabText(idx).strip() != "main"):
                self.tabCloseRequested.emit(idx)
                return
        super().keyPressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        cur = self.currentIndex()
        if cur < 0:
            return
        rect = self.tabRect(cur)
        from PySide6.QtWidgets import QStyleOptionTab
        opt = QStyleOptionTab()
        self.initStyleOption(opt, cur)
        text_rect = self.style().subElementRect(
            self.style().SubElement.SE_TabBarTabText,
            opt, self,
        )
        if text_rect.isValid():
            cx = text_rect.x() + text_rect.width() / 2.0
        else:
            cx = rect.x() + rect.width() / 2.0
        x = round(cx - _BLUE_LINE_W / 2.0)
        y = rect.bottom() - _BLUE_LINE_H + 1
        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing, False
        )
        pen = QPen(_BLUE_COLOR, _BLUE_LINE_H)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen)
        painter.drawLine(x, y, x + _BLUE_LINE_W - 1, y)
        painter.end()


# ════════════════════════════════════════════
# 过滤器管理器（多 Tab）
# ════════════════════════════════════════════
class FilterManager(QWidget):
    filter_changed = Signal()
    tab_close_requested = Signal(int)   # ★ v0.62
    hover_clear_requested = Signal()    # ★ v0.62

    def __init__(self, config, h_margin=10, right_width=272,
                 toggle_send_callback=None, parent=None):
        super().__init__(parent)
        self._config = config
        self._h_margin = h_margin
        self._right_width = right_width
        self._toggle_send_cb = toggle_send_callback
        self._show_hex = False
        self._auto_scroll = True
        self._line_buffer = ""
        self._history = []
        self._log_write_cb = None
        self._log_close_cb = None
        self._save_as_cb = None
        # ★ v0.6: 写入暂停机制 — 换行切换/resize 期间攒数据
        self._write_paused = False
        self._pending_lines = []
        self._init_ui()

    # ── 回调设置 ─────────────────────────

    def set_log_callbacks(self, write_cb, close_tab_cb):
        self._log_write_cb = write_cb
        self._log_close_cb = close_tab_cb

    def set_save_as_callback(self, cb):
        self._save_as_cb = cb

    def get_tab_names(self):
        names = []
        for i in range(self._tabs.count()):
            if self._tab_bar.tabData(i) != _PLUS_DATA:
                names.append(self._tabs.tabText(i).strip())
        return names

    def get_tab_content(self, tab_name):
        for i in range(self._tabs.count()):
            if self._tabs.tabText(i).strip() == tab_name:
                v = self._tabs.widget(i)
                if isinstance(v, FilteredLogView):
                    return v.toPlainText()
        return ""

    # ── UI 构建 ───────────────────────────

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
        self._tab_bar.tabCloseRequested.connect(
            self._request_close_tab
        )
        self._tab_bar.save_tab_requested.connect(self._on_save_tab_request)
        self._tabs.setTabsClosable(False)
        self._tabs.setMovable(False)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self._tabs, stretch=1)
        layout.addWidget(self._build_filter_bar())
        main_view = FilteredLogView()
        main_view.set_auto_scroll(self._auto_scroll)
        main_view.font_size_changed.connect(
            self._on_font_size_changed
        )
        main_view.clear_requested.connect(
            self.hover_clear_requested.emit
        )
        main_view.set_closable(False)
        self._tabs.addTab(main_view, "main")
        for i in range(1, 2):
            self._add_tab(f"filter-{i:02d}", closable=True)
        plus_widget = QWidget()
        self._tabs.addTab(plus_widget, "+")
        plus_idx = self._tabs.count() - 1
        self._tab_bar.setTabData(plus_idx, _PLUS_DATA)
        self._tabs.setCurrentIndex(0)
        self._on_tab_changed(0)

    def _build_filter_bar(self):
        bar = QWidget()
        bar.setObjectName("FilterBar")
        bar.setFixedHeight(38)
        h = QHBoxLayout(bar)
        h.setContentsMargins(0, 4, 0, 4)
        h.setSpacing(8)
        self._kw_edit = RoundedContextLineEdit()
        self._kw_edit.setObjectName("KwEdit")
        self._kw_edit.setPlaceholderText(
            "关键词过滤（多个关键词用 | 分隔，"
            "如: error|warn|fail）— 实时生效"
        )
        self._kw_edit.textChanged.connect(self._apply_kw)
        h.addWidget(self._kw_edit, stretch=1)
        right_box = QWidget()
        right_box.setFixedWidth(self._right_width)
        right_h = QHBoxLayout(right_box)
        right_h.setContentsMargins(0, 0, 0, 0)
        right_h.setSpacing(8)
        self._chk_case = QCheckBox("区分大小写")
        self._chk_invert = QCheckBox("反选")
        self._chk_invert.setToolTip("显示不包含关键词的行")
        self._chk_case.toggled.connect(self._apply_kw)
        self._chk_invert.toggled.connect(self._apply_kw)
        self._btn_refilter = QPushButton("打开文件")
        self._btn_refilter.setObjectName("BtnRefilter")
        self._btn_refilter.setToolTip("用当前关键词重新过滤已有历史数据")
        self._btn_refilter.clicked.connect(self._refilter)
        self._btn_toggle = QPushButton("▼")
        self._btn_toggle.setObjectName("BtnToggleSend")
        self._btn_toggle.setFlat(True)
        self._btn_toggle.setFixedSize(30, 30)
        self._btn_toggle.setToolTip("隐藏/显示发送区")
        if self._toggle_send_cb:
            self._btn_toggle.clicked.connect(self._toggle_send_cb)
        right_h.addWidget(self._chk_case)
        right_h.addWidget(self._chk_invert)
        right_h.addStretch(1)
        right_h.addWidget(self._btn_refilter)
        right_h.addWidget(self._btn_toggle)
        h.addWidget(right_box)
        return bar

    # ── Tab 管理 ──────────────────────────

    def _find_plus_idx(self):
        for i in range(self._tabs.count()):
            if self._tab_bar.tabData(i) == _PLUS_DATA:
                return i
        return -1

    def _add_tab(self, name, closable=True):
        view = FilteredLogView()
        view.set_auto_scroll(self._auto_scroll)
        view.font_size_changed.connect(
            self._on_font_size_changed
        )
        view.clear_requested.connect(
            self.hover_clear_requested.emit
        )
        view.close_requested.connect(
            lambda _v=view: self._request_close_tab(
                self._tabs.indexOf(_v)
            )
        )
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
                try:
                    existing.append(int(t.split("-")[1]))
                except Exception:
                    pass
        n = max(existing) + 1 if existing else 1
        new_idx = self._add_tab(f"filter-{n:02d}", closable=True)
        self._tabs.setCurrentIndex(new_idx)

    def _request_close_tab(self, idx):
        """路由到 tab_close_requested 信号（需确认）"""
        name = self._tabs.tabText(idx).strip()
        if name in ("main", "+"):
            return
        if self._tab_bar.tabData(idx) == _PLUS_DATA:
            return
        self.tab_close_requested.emit(idx)

    def request_close_current_tab(self):
        """请求关闭当前 Tab（Ctrl+W / hover ×）"""
        idx = self._tabs.currentIndex()
        self._request_close_tab(idx)

    def force_close_tab(self, idx):
        """确认后实际关闭 Tab"""
        name = self._tabs.tabText(idx).strip()
        if name in ("main", "+"):
            return
        if self._tab_bar.tabData(idx) == _PLUS_DATA:
            return
        if self._log_close_cb:
            self._log_close_cb(name)
        self._tabs.removeTab(idx)

    def _rename_tab(self, idx):
        name = self._tabs.tabText(idx).strip()
        if name == "main":
            return
        if self._tab_bar.tabData(idx) == _PLUS_DATA:
            return
        new_name, ok = QInputDialog.getText(
            self, "重命名 Tab", "请输入新名称：", text=name,
        )
        if ok and new_name.strip():
            self._tabs.setTabText(idx, new_name.strip())

    def _on_save_tab_request(self, idx):
        if self._save_as_cb is None:
            return
        name = self._tabs.tabText(idx).strip()
        self._save_as_cb(name)

    def _on_tab_changed(self, idx):
        if self._tab_bar.tabData(idx) == _PLUS_DATA:
            prev = max(0, idx - 1)
            self._tabs.setCurrentIndex(prev)
            return
        view = self._tabs.widget(idx)
        if view is None:
            return
        is_main = self._tabs.tabText(idx).strip() == "main"
        self._kw_edit.setEnabled(not is_main)
        self._chk_case.setEnabled(not is_main)
        self._chk_invert.setEnabled(not is_main)
        self._btn_refilter.setEnabled(not is_main)
        self._kw_edit.blockSignals(True)
        self._chk_case.blockSignals(True)
        self._chk_invert.blockSignals(True)
        if is_main:
            self._kw_edit.setPlaceholderText(
                "main 窗口显示所有数据（不过滤）"
            )
            self._kw_edit.clear()
        elif isinstance(view, FilteredLogView):
            self._kw_edit.setPlaceholderText(
                "关键词过滤（多个关键词用 | 分隔）"
                "— 实时生效"
            )
            self._kw_edit.setText("|".join(view.keywords))
            self._chk_case.setChecked(view.case_sensitive)
            self._chk_invert.setChecked(view.invert)
        self._kw_edit.blockSignals(False)
        self._chk_case.blockSignals(False)
        self._chk_invert.blockSignals(False)

    # ── 关键词 / 过滤 ──────────────────────

    def _apply_kw(self):
        idx = self._tabs.currentIndex()
        view = self._tabs.widget(idx)
        if not isinstance(view, FilteredLogView):
            return
        name = self._tabs.tabText(idx).strip()
        if name == "main":
            return
        if self._tab_bar.tabData(idx) == _PLUS_DATA:
            return
        raw = self._kw_edit.text().strip()
        view.keywords = [
            k.strip() for k in raw.split("|") if k.strip()
        ]
        view.case_sensitive = self._chk_case.isChecked()
        view.invert = self._chk_invert.isChecked()
        if not view.keywords:
            view.clear()
            view._line_count = 0
        self.filter_changed.emit()

    def _refilter(self):
        self._apply_kw()
        idx = self._tabs.currentIndex()
        view = self._tabs.widget(idx)
        if not isinstance(view, FilteredLogView):
            return
        tab_name = self._tabs.tabText(idx).strip()
        if tab_name != "main" and not view.keywords:
            return
        view.clear()
        view._line_count = 0
        for line, color in self._history:
            if view.matches(line):
                view.append_line(line, color)

    # ── 公开接口 ──────────────────────────

    def update_toggle_btn(self, send_visible):
        self._btn_toggle.setText("▼" if send_visible else "▲")

    def append_data(self, data):
        text = (
            FilteredLogView.to_hex(data)
            if self._show_hex
            else FilteredLogView.to_text(data)
        )
        self._dispatch(text, "#1a6b3a")

    def append_sent(self, data):
        text = (
            FilteredLogView.to_hex(data)
            if self._show_hex
            else FilteredLogView.to_text(data)
        )
        self._dispatch("[TX] " + text, "#92400e")

    def append_info(self, msg):
        self._dispatch(f"[INFO] {msg}\n", "#6b7280")

    def append_error(self, msg):
        self._dispatch(f"[ERROR] {msg}\n", "#dc2626")

    def clear_current(self):
        v = self._tabs.currentWidget()
        if isinstance(v, FilteredLogView):
            v.clear()
            v._line_count = 0

    def clear_all(self):
        self._history.clear()
        self._line_buffer = ""
        for i in range(self._tabs.count()):
            v = self._tabs.widget(i)
            if isinstance(v, FilteredLogView):
                v.clear()
                v._line_count = 0

    def clear_main_and_current(self):
        for i in range(self._tabs.count()):
            if self._tabs.tabText(i).strip() == "main":
                v = self._tabs.widget(i)
                if isinstance(v, FilteredLogView):
                    v.clear()
                    v._line_count = 0
                break
        current_idx = self._tabs.currentIndex()
        v = self._tabs.widget(current_idx)
        if isinstance(v, FilteredLogView):
            v.clear()
            v._line_count = 0

    # ★ v0.62: Ctrl+G 跳转行号
    def goto_line_current(self, line_num):
        """跳转当前 Tab 到指定行号"""
        v = self._tabs.currentWidget()
        if isinstance(v, FilteredLogView):
            v.goto_line(line_num)

    def set_auto_scroll(self, v):
        self._auto_scroll = v
        for i in range(self._tabs.count()):
            w = self._tabs.widget(i)
            if isinstance(w, FilteredLogView):
                w.set_auto_scroll(v)

    def set_show_hex(self, show):
        self._show_hex = show

    # ★ v0.5 新增：刷新所有 Tab 的高亮器
    def refresh_highlighter(self, config: dict):
        """将高亮配置应用到所有 FilteredLogView Tab"""
        for i in range(self._tabs.count()):
            v = self._tabs.widget(i)
            if isinstance(v, FilteredLogView):
                v.set_highlighter(config)

    # ★ v0.6: 更新高亮配置但不 rehighlight — 仅新日志生效
    def update_highlighter_config(self, config: dict):
        """将高亮配置应用到所有 Tab 但不 rehighlight"""
        for i in range(self._tabs.count()):
            v = self._tabs.widget(i)
            if isinstance(v, FilteredLogView):
                v.update_highlighter_only(config)

    # ★ v0.6 fix: 字号专用通路 — 不触发 rehighlight
    def update_font_size(self, size):
        """设置页/外部调用 — 只改字号，不 rehighlight"""
        hl = self._config.setdefault("highlight", {})
        hl["font_size"] = size
        from config import save_config
        save_config(self._config)
        for i in range(self._tabs.count()):
            v = self._tabs.widget(i)
            if (
                isinstance(v, FilteredLogView)
                and v._font_size != size
            ):
                v._apply_font_size(size)

    # ★ v0.6: 自动换行开关（暂停写入 → 切换 → 恢复 flush）
    def update_word_wrap(self, enabled):
        """设置页调用 — 切换所有 Tab 换行模式"""
        hl = self._config.setdefault("highlight", {})
        hl["word_wrap"] = enabled
        from config import save_config
        save_config(self._config)
        self._write_paused = True
        mode = (
            FilteredLogView.LineWrapMode.WidgetWidth
            if enabled
            else FilteredLogView.LineWrapMode.NoWrap
        )
        for i in range(self._tabs.count()):
            v = self._tabs.widget(i)
            if isinstance(v, FilteredLogView):
                v._wrap_mode = mode
                v.setLineWrapMode(mode)
        self._write_paused = False
        self._flush_pending()

    # ★ v0.67: 行号显示开关
    def set_line_numbers_visible(self, visible):
        """设置所有 Tab 行号可见性"""
        for i in range(self._tabs.count()):
            v = self._tabs.widget(i)
            if isinstance(v, FilteredLogView):
                v.set_line_numbers_visible(visible)

    # ★ v0.6: 最大行数更新
    def update_max_lines(self, n):
        """设置页调用 — 更新所有 Tab 最大行数"""
        hl = self._config.setdefault("highlight", {})
        hl["max_lines"] = n
        from config import save_config
        save_config(self._config)
        for i in range(self._tabs.count()):
            v = self._tabs.widget(i)
            if isinstance(v, FilteredLogView):
                v._max_lines = n

    def _on_font_size_changed(self, size):
        self.update_font_size(size)

    # ── 核心分发 ──────────────────────────

    # ★ v0.6: 写入暂停 — resize/换行切换期间缓冲数据
    def set_write_paused(self, paused):
        self._write_paused = paused
        if not paused:
            self._flush_pending()

    def _flush_pending(self):
        if not self._pending_lines:
            return
        pending = self._pending_lines
        self._pending_lines = []
        # ★ 批量编辑块 — 合并所有插入为一次布局更新
        edit_cursors = []
        for i in range(self._tabs.count()):
            v = self._tabs.widget(i)
            if isinstance(v, FilteredLogView):
                c = v.textCursor()
                c.beginEditBlock()
                edit_cursors.append((v, c))
        for text, color in pending:
            self._dispatch(text, color)
        for v, c in edit_cursors:
            c.endEditBlock()

    def _dispatch(self, text, color):
        if self._write_paused:
            self._pending_lines.append((text, color))
            return
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
                if not isinstance(v, FilteredLogView):
                    continue
                tab_name = self._tabs.tabText(i).strip()
                is_main = tab_name == "main"
                if not is_main and not v.keywords:
                    continue
                if v.matches(full):
                    v.append_line(full, color)
                    if self._log_write_cb:
                        self._log_write_cb(tab_name, full)