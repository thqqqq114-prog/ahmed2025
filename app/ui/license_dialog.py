from __future__ import annotations
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PySide6.QtCore import Qt

from app.licensing import LicenseClient, LicenseError


class LicenseDialog(QDialog):
    """حوارات بسيطة لإدخال مفتاح الترخيص وتفعيله."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تفعيل الترخيص")
        self.setModal(True)
        self.ok = False
        self.token: str | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("من فضلك أدخل مفتاح الترخيص:", self))

        self.key_edit = QLineEdit(self)
        self.key_edit.setPlaceholderText("مثال: FA-XXXX-XXXX-XXXX")
        layout.addWidget(self.key_edit)

        self.error_label = QLabel("", self)
        self.error_label.setStyleSheet("color: red;")
        layout.addWidget(self.error_label)

        btns = QHBoxLayout()
        self.activate_btn = QPushButton("تفعيل", self)
        self.cancel_btn = QPushButton("إلغاء", self)
        btns.addWidget(self.activate_btn)
        btns.addWidget(self.cancel_btn)
        layout.addLayout(btns)

        self.activate_btn.clicked.connect(self._on_activate)
        self.cancel_btn.clicked.connect(self.reject)

        self.resize(420, 160)

    def _set_busy(self, busy: bool):
        self.activate_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(not busy)
        self.key_edit.setEnabled(not busy)

    def _on_activate(self):
        key = self.key_edit.text().strip()
        if not key:
            self.error_label.setText("أدخل مفتاح الترخيص")
            return
        self.error_label.setText("")
        client = LicenseClient()
        try:
            token = client.activate(key)
            self.ok = True
            self.token = token
            self.accept()
        except LicenseError as e:
            self.error_label.setText(str(e))
        except Exception as e:  # حراسة عامة لعدم كسر الواجهة
            self.error_label.setText(f"خطأ غير متوقع: {e}")