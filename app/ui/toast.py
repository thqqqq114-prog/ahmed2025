from __future__ import annotations
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget, QLabel

class Toast(QWidget):
    def __init__(self, parent: QWidget | None, message: str, timeout_ms: int = 2000):
        super().__init__(parent)
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        label = QLabel(message, self)
        label.setStyleSheet(
            "background: rgba(0,0,0,0.8); color: white; padding: 10px 14px; border-radius: 8px;"
        )
        label.adjustSize()
        self.resize(label.size())
        # Position bottom-right over parent (if any)
        if parent:
            pw = parent.width(); ph = parent.height()
            tw = self.width(); th = self.height()
            self.move(max(0, pw - tw - 24), max(0, ph - th - 24))
        QTimer.singleShot(timeout_ms, self.close)


def show_toast(parent: QWidget | None, message: str, timeout_ms: int = 2000):
    t = Toast(parent, message, timeout_ms)
    t.show()
    return t