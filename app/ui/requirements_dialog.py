from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QListWidget, QMessageBox
from app.data.database import SessionLocal
from app.data.models import Factory, Item, FactoryRequirement
from app.ui.toast import show_toast

class RequirementsDialog(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.factory_combo = QComboBox()
        self.item_combo = QComboBox()
        self.unit_combo = QComboBox(); self.unit_combo.setEditable(True)
        self.unit_combo.addItems(["", "kg", "bag", "ton"])
        add_btn = QPushButton("إضافة")
        del_btn = QPushButton("حذف")
        self.list_widget = QListWidget()

        layout = QVBoxLayout(self)
        layout.addLayout(self.row("المصنع:", self.factory_combo))
        layout.addLayout(self.row("الصنف:", self.item_combo))
        layout.addLayout(self.row("الوحدة المطلوبة:", self.unit_combo))
        layout.addWidget(add_btn)
        layout.addWidget(del_btn)
        layout.addWidget(self.list_widget)

        add_btn.clicked.connect(self.add_req)
        del_btn.clicked.connect(self.del_req)

        self.load_refs(); self.refresh_list()
        # تعطيل الإدخال للمشاهِد
        try:
            mw = self.window()
            is_viewer = getattr(mw, 'role', '') == 'viewer'
            if is_viewer:
                for w in [self.factory_combo, self.item_combo, self.unit_combo]:
                    w.setEnabled(False)
                add_btn.setEnabled(False)
                del_btn.setEnabled(False)
        except Exception:
            pass

    def row(self, label, widget):
        h = QHBoxLayout(); h.addWidget(QLabel(label)); h.addWidget(widget); return h

    def load_refs(self):
        self.factory_combo.clear(); self.item_combo.clear()
        with SessionLocal() as s:
            for f in s.query(Factory).order_by(Factory.name).all():
                self.factory_combo.addItem(f.name, f.id)
            for it in s.query(Item).order_by(Item.name).all():
                self.item_combo.addItem(it.name, it.id)

    def refresh_list(self):
        self.list_widget.clear()
        with SessionLocal() as s:
            for req in s.query(FactoryRequirement).all():
                f = s.get(Factory, req.factory_id); i = s.get(Item, req.item_id)
                self.list_widget.addItem(f"{req.id} | {f.name} | {i.name} | {req.required_unit or '-'}")

    def add_req(self):
        if self.factory_combo.count() == 0 or self.item_combo.count() == 0:
            QMessageBox.warning(self, "تنبيه", "من فضلك أنشئ مصنع وصنف أولاً")
            return
        with SessionLocal() as s:
            req = FactoryRequirement(factory_id=self.factory_combo.currentData(),
                                     item_id=self.item_combo.currentData(),
                                     required_unit=(self.unit_combo.currentText().strip() or None))
            s.add(req)
            try:
                s.commit()
                try:
                    show_toast(self, "تمت الإضافة")
                except Exception:
                    pass
            except Exception as e:
                s.rollback(); QMessageBox.warning(self, "خطأ", "هذا الربط موجود بالفعل")
            self.refresh_list()

    def del_req(self):
        if not self.list_widget.currentItem():
            return
        req_id = int(self.list_widget.currentItem().text().split('|')[0].strip())
        with SessionLocal() as s:
            obj = s.get(FactoryRequirement, req_id)
            if obj:
                s.delete(obj); s.commit()
                self.refresh_list()
                try:
                    show_toast(self, "تم الحذف")
                except Exception:
                    pass