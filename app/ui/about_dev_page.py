from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

# الإصدار الحالي للتطبيق
from app.version import __version__ as APP_VERSION


class AboutDeveloperPage(QWidget):
    """قسم المبرمج: معلومات عامة فقط (بدون روابط أو تحديثات)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AboutDeveloperPage")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        # معلومات ثابتة
        title = QLabel("عن المبرمج")
        title.setStyleSheet("font-size:20px; font-weight:bold;")
        layout.addWidget(title)
        layout.addWidget(QLabel("مبرمج البرنامج: أحمد حسين"))
        layout.addWidget(QLabel(f"الإصدار الحالي: {APP_VERSION}"))
        layout.addWidget(QLabel("حقوق النشر محفوظة والملكية الفكرية"))
        layout.addWidget(QLabel("بواسطة: أحمد حسين"))
        layout.addWidget(QLabel("جوال/واتساب: 01555560207 - 01096169187"))

        # تم حذف قسم الترخيص وإعدادات الروابط والتحديثات بالكامل
        layout.addStretch(1)