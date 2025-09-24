from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QMessageBox
from app.data.database import SessionLocal
from app.data.models import Factory

class FactoriesDialog(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.name_edit = QLineEdit(); self.name_edit.setPlaceholderText("اسم المصنع")
        self.notes_edit = QLineEdit(); self.notes_edit.setPlaceholderText("ملاحظات")
        add_btn = QPushButton("إضافة/تعديل")
        del_btn = QPushButton("حذف")
        self.list_widget = QListWidget()

        layout = QVBoxLayout(self)
        layout.addLayout(self.row("الاسم:", self.name_edit))
        layout.addLayout(self.row("ملاحظات:", self.notes_edit))
        layout.addWidget(add_btn)
        layout.addWidget(del_btn)
        layout.addWidget(self.list_widget)

        add_btn.clicked.connect(self.add_or_update)
        del_btn.clicked.connect(self.delete_factory)
        self.list_widget.itemClicked.connect(self.fill_from_selected)

        self.refresh_list()

    def row(self, label, widget):
        h = QHBoxLayout(); h.addWidget(QLabel(label)); h.addWidget(widget); return h

    def refresh_list(self):
        self.list_widget.clear()
        with SessionLocal() as s:
            for f in s.query(Factory).order_by(Factory.name).all():
                self.list_widget.addItem(f"{f.id} | {f.name} | {f.notes or ''}")

    def fill_from_selected(self):
        t = self.list_widget.currentItem().text()
        parts = [p.strip() for p in t.split('|')]
        self.name_edit.setText(parts[1])
        self.notes_edit.setText(parts[2])

    def add_or_update(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "تنبيه", "اسم المصنع مطلوب")
            return
        with SessionLocal() as s:
            existing = s.query(Factory).filter(Factory.name == name).one_or_none()
            if existing:
                existing.notes = self.notes_edit.text().strip() or None
            else:
                s.add(Factory(name=name, notes=self.notes_edit.text().strip() or None))
            s.commit()
            self.refresh_list()
            self.name_edit.clear(); self.notes_edit.clear()

    def delete_factory(self):
        if not self.list_widget.currentItem():
            return
        t = self.list_widget.currentItem().text()
        factory_id = int(t.split('|')[0].strip())
        with SessionLocal() as s:
            obj = s.get(Factory, factory_id)
            if obj is None:
                return
            s.delete(obj)
            s.commit()
            self.refresh_list()