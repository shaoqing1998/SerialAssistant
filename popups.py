"""
popups.py - 自定义弹窗组件
v0.7 — 从 settings_dialog.py Part 1 提取

InfoPopup / ConfirmPopup / InputIntPopup / InputTextPopup
所有弹窗统一风格：无标题栏、遮罩模式、圆角面板。
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QPushButton, QWidget, QLineEdit,
    QSpinBox,
)
from PySide6.QtCore import Qt, QPoint, QRectF, Signal
from PySide6.QtGui import (
    QPainter, QPainterPath, QColor, QPen,
)

from theme import (
    PRIMARY, PRIMARY_HOVER, PRIMARY_PRESSED,
    BG_PANEL, BG_HOVER, BG_PRESSED,
    TEXT_PRIMARY, TEXT_MUTED, TEXT_SECONDARY,
    BORDER_DEFAULT, BORDER_FOCUS, BORDER_PANEL,
    OVERLAY_COLOR, POPUP_RADIUS, POPUP_FONT_SIZE,
    LABEL_FONT_SIZE,
    checkbox_ss, primary_btn_ss, cancel_btn_ss,
)
from widgets import CloseBtn


# ════════════════════════════════════════════
# 信息提示弹窗
# ════════════════════════════════════════════
class InfoPopup(QDialog):
    """无标题栏、无图标的信息提示弹窗 — 确定按钮底部居中"""

    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, True,
        )
        self._pw = 280
        self._panel = QWidget(self)
        v = QVBoxLayout(self._panel)
        v.setContentsMargins(20, 20, 20, 16)
        v.setSpacing(16)
        lbl = QLabel(message)
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(
            f"font-size:{POPUP_FONT_SIZE}px;"
            f"color:{TEXT_PRIMARY};background:transparent;"
        )
        v.addWidget(lbl)
        btn_ok = QPushButton("确定")
        btn_ok.setFixedSize(72, 30)
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setStyleSheet(primary_btn_ss())
        btn_ok.clicked.connect(self.accept)
        btn_h = QHBoxLayout()
        btn_h.addStretch(1)
        btn_h.addWidget(btn_ok)
        btn_h.addStretch(1)
        v.addLayout(btn_h)
        self._panel.setFixedWidth(self._pw)
        self._panel.adjustSize()
        self._ph = self._panel.sizeHint().height()
        self._panel.setFixedHeight(self._ph)

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            pw = self.parent()
            self.resize(pw.size())
            self.move(pw.mapToGlobal(QPoint(0, 0)))
        self._panel.move(
            (self.width() - self._pw) // 2,
            (self.height() - self._ph) // 2,
        )

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), QColor(*OVERLAY_COLOR))
        pr = QRectF(
            self._panel.geometry()
        ).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(pr, POPUP_RADIUS, POPUP_RADIUS)
        p.fillPath(path, QColor(BG_PANEL))
        p.setPen(QPen(QColor(BORDER_DEFAULT), 1.0))
        p.drawPath(path)
        p.end()

    def mousePressEvent(self, event):
        if not self._panel.geometry().contains(event.pos()):
            self.accept()
            return
        super().mousePressEvent(event)


# ════════════════════════════════════════════
# 确认弹窗
# ════════════════════════════════════════════
class ConfirmPopup(QDialog):
    """确认弹窗 — 可选“以后都不提示”复选框"""

    def __init__(self, message, show_dont_ask=False,
                 parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, True,
        )
        self._dont_ask = False
        self._pw = 300
        self._panel = QWidget(self)
        v = QVBoxLayout(self._panel)
        v.setContentsMargins(20, 20, 20, 16)
        v.setSpacing(12)
        lbl = QLabel(message)
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(
            f"font-size:{POPUP_FONT_SIZE}px;"
            f"color:{TEXT_PRIMARY};background:transparent;"
        )
        v.addWidget(lbl)
        self._chk_dont_ask = None
        if show_dont_ask:
            self._chk_dont_ask = QCheckBox("以后都不提示")
            self._chk_dont_ask.setStyleSheet(checkbox_ss())
            chk_h = QHBoxLayout()
            chk_h.addStretch(1)
            chk_h.addWidget(self._chk_dont_ask)
            chk_h.addStretch(1)
            v.addLayout(chk_h)
        btn_h = QHBoxLayout()
        btn_h.setSpacing(12)
        btn_h.addStretch(1)
        btn_cancel = QPushButton("取消")
        btn_cancel.setFixedSize(72, 30)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(cancel_btn_ss())
        btn_cancel.clicked.connect(self.reject)
        btn_h.addWidget(btn_cancel)
        btn_ok = QPushButton("确认")
        btn_ok.setFixedSize(72, 30)
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setStyleSheet(primary_btn_ss())
        btn_ok.clicked.connect(self._on_accept)
        btn_h.addWidget(btn_ok)
        btn_h.addStretch(1)
        v.addLayout(btn_h)
        self._panel.setFixedWidth(self._pw)
        self._panel.adjustSize()
        self._ph = self._panel.sizeHint().height()
        self._panel.setFixedHeight(self._ph)

    def _on_accept(self):
        if self._chk_dont_ask and self._chk_dont_ask.isChecked():
            self._dont_ask = True
        self.accept()

    def dont_ask_again(self):
        return self._dont_ask

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            pw = self.parent()
            self.resize(pw.size())
            self.move(pw.mapToGlobal(QPoint(0, 0)))
        self._panel.move(
            (self.width() - self._pw) // 2,
            (self.height() - self._ph) // 2,
        )

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), QColor(*OVERLAY_COLOR))
        pr = QRectF(
            self._panel.geometry()
        ).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(pr, POPUP_RADIUS, POPUP_RADIUS)
        p.fillPath(path, QColor(BG_PANEL))
        p.setPen(QPen(QColor(BORDER_DEFAULT), 1.0))
        p.drawPath(path)
        p.end()

    def mousePressEvent(self, event):
        if not self._panel.geometry().contains(event.pos()):
            self.reject()
            return
        super().mousePressEvent(event)


# ════════════════════════════════════════════
# 非模态整数输入弹窗
# ════════════════════════════════════════════
class InputIntPopup(QDialog):
    """非模态整数输入弹窗 — 有边框阴影、可拖动、置顶不阻塞"""
    value_accepted = Signal(int)

    def __init__(self, message, value=1, min_val=1,
                 max_val=99999, btn_text="确定",
                 parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, True,
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_DeleteOnClose, True,
        )
        self._drag_pos = None
        self._sd = 8
        self._pw = 260
        self._panel = QWidget(self)
        v = QVBoxLayout(self._panel)
        v.setContentsMargins(16, 10, 10, 12)
        v.setSpacing(10)
        # ── title row ──
        title_h = QHBoxLayout()
        title_h.setSpacing(4)
        lbl = QLabel(message)
        lbl.setStyleSheet(
            f"font-size:{LABEL_FONT_SIZE}px;"
            f"color:{TEXT_PRIMARY};background:transparent;"
            "font-weight:600;"
        )
        title_h.addWidget(lbl, stretch=1)
        cb = CloseBtn(size=24, parent=self._panel)
        cb.clicked.connect(self.close)
        title_h.addWidget(cb)
        v.addLayout(title_h)
        # ── spinbox ──
        self._spin = QSpinBox()
        self._spin.setRange(min_val, max_val)
        self._spin.setValue(value)
        self._spin.setFixedHeight(30)
        self._spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._spin.setStyleSheet(
            f"QSpinBox{{font-size:14px;color:{TEXT_PRIMARY};"
            f"background:{BG_PANEL};"
            f"border:1.5px solid {BORDER_DEFAULT};"
            "border-radius:6px;padding:0 8px}}"
            f"QSpinBox:focus{{border-color:{BORDER_FOCUS}}}"
            "QSpinBox::up-button,QSpinBox::down-button{"
            "width:16px;border:none;background:transparent}"
        )
        v.addWidget(self._spin)
        # ── buttons ──
        btn_h = QHBoxLayout()
        btn_h.setSpacing(8)
        btn_h.addStretch(1)
        btn_cancel = QPushButton("取消")
        btn_cancel.setFixedSize(60, 28)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(cancel_btn_ss())
        btn_cancel.clicked.connect(self.close)
        btn_h.addWidget(btn_cancel)
        btn_ok = QPushButton(btn_text)
        btn_ok.setFixedSize(60, 28)
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setStyleSheet(primary_btn_ss())
        btn_ok.clicked.connect(self._on_accept)
        btn_h.addWidget(btn_ok)
        v.addLayout(btn_h)
        # ── size ──
        self._panel.setFixedWidth(self._pw)
        self._panel.adjustSize()
        self._ph = self._panel.sizeHint().height()
        self._panel.setFixedHeight(self._ph)
        self._panel.move(self._sd, self._sd)
        self.setFixedSize(
            self._pw + 2 * self._sd,
            self._ph + 2 * self._sd,
        )

    def _on_accept(self):
        self.value_accepted.emit(self._spin.value())
        self.close()

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            pg = self.parent().geometry()
            x = pg.x() + (pg.width() - self.width()) // 2
            y = pg.y() + (pg.height() - self.height()) // 2
            self.move(x, y)
        self.activateWindow()
        self._spin.setFocus()
        self._spin.selectAll()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        S = self._sd
        pr = QRectF(S, S, self._pw, self._ph)
        for i in range(S, 0, -1):
            a = int(12 * (S - i + 1) / S)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, a))
            r = pr.adjusted(-i, -i, i, i)
            p.drawRoundedRect(r, 8 + i * 0.5, 8 + i * 0.5)
        panel_r = pr.adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(panel_r, POPUP_RADIUS, POPUP_RADIUS)
        p.fillPath(path, QColor(BG_PANEL))
        p.setPen(QPen(QColor(BORDER_DEFAULT), 1.0))
        p.drawPath(path)
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.pos())
            if (child is None or child is self._panel
                    or isinstance(child, QLabel)):
                self._drag_pos = (
                    event.globalPosition().toPoint() - self.pos()
                )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            self.move(
                event.globalPosition().toPoint() - self._drag_pos
            )
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() in (
            Qt.Key.Key_Return, Qt.Key.Key_Enter
        ):
            self._on_accept()
        else:
            super().keyPressEvent(event)


# ════════════════════════════════════════════
# 模态文本输入弹窗
# ════════════════════════════════════════════
class InputTextPopup(QDialog):
    """模态文本输入弹窗 — 延续 ConfirmPopup 遮罩风格"""

    def __init__(self, message, text="", parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, True,
        )
        self._result_text = None
        self._pw = 300
        self._panel = QWidget(self)
        v = QVBoxLayout(self._panel)
        v.setContentsMargins(20, 20, 20, 16)
        v.setSpacing(12)
        lbl = QLabel(message)
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(
            f"font-size:{POPUP_FONT_SIZE}px;"
            f"color:{TEXT_PRIMARY};background:transparent;"
        )
        v.addWidget(lbl)
        edit_h = QHBoxLayout()
        edit_h.addStretch(1)
        self._edit = QLineEdit()
        self._edit.setText(text)
        self._edit.setFixedSize(160, 32)
        self._edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._edit.setStyleSheet(
            f"QLineEdit{{font-size:14px;color:{TEXT_PRIMARY};"
            f"background:{BG_PANEL};"
            f"border:1.5px solid {BORDER_DEFAULT};"
            "border-radius:6px;padding:0 8px}}"
            f"QLineEdit:focus{{border-color:{BORDER_FOCUS}}}"
        )
        edit_h.addWidget(self._edit)
        edit_h.addStretch(1)
        v.addLayout(edit_h)
        btn_h = QHBoxLayout()
        btn_h.setSpacing(12)
        btn_h.addStretch(1)
        btn_cancel = QPushButton("取消")
        btn_cancel.setFixedSize(72, 30)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(cancel_btn_ss())
        btn_cancel.clicked.connect(self.reject)
        btn_h.addWidget(btn_cancel)
        btn_ok = QPushButton("确定")
        btn_ok.setFixedSize(72, 30)
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setStyleSheet(primary_btn_ss())
        btn_ok.clicked.connect(self._on_accept)
        btn_h.addWidget(btn_ok)
        btn_h.addStretch(1)
        v.addLayout(btn_h)
        self._panel.setFixedWidth(self._pw)
        self._panel.adjustSize()
        self._ph = self._panel.sizeHint().height()
        self._panel.setFixedHeight(self._ph)

    def _on_accept(self):
        self._result_text = self._edit.text()
        self.accept()

    def get_text(self):
        return self._result_text

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            pw = self.parent()
            self.resize(pw.size())
            self.move(pw.mapToGlobal(QPoint(0, 0)))
        self._panel.move(
            (self.width() - self._pw) // 2,
            (self.height() - self._ph) // 2,
        )
        self._edit.setFocus()
        self._edit.selectAll()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), QColor(*OVERLAY_COLOR))
        pr = QRectF(
            self._panel.geometry()
        ).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(pr, POPUP_RADIUS, POPUP_RADIUS)
        p.fillPath(path, QColor(BG_PANEL))
        p.setPen(QPen(QColor(BORDER_DEFAULT), 1.0))
        p.drawPath(path)
        p.end()

    def mousePressEvent(self, event):
        if not self._panel.geometry().contains(event.pos()):
            self.reject()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (
            Qt.Key.Key_Return, Qt.Key.Key_Enter
        ):
            self._on_accept()
        else:
            super().keyPressEvent(event)