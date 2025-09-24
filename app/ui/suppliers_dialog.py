from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QMessageBox
from sqlalchemy.exc import IntegrityError
from app.data.database import SessionLocal, log_action
from app.data.models import Supplier
from app.ui.toast import show_toast

class SuppliersDialog(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.name_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        self.address_edit = QLineEdit()
        add_btn = QPushButton("إضافة"); add_btn.setProperty("role", "bottom")
        update_btn = QPushButton("تعديل"); update_btn.setProperty("role", "bottom")
        del_btn = QPushButton("حذف"); del_btn.setProperty("role", "bottom")
        self.list_widget = QListWidget()

        layout = QVBoxLayout(self)
        form1 = QHBoxLayout(); form1.addWidget(QLabel("الاسم:")); form1.addWidget(self.name_edit)
        form2 = QHBoxLayout(); form2.addWidget(QLabel("تليفون:")); form2.addWidget(self.phone_edit)
        form3 = QHBoxLayout(); form3.addWidget(QLabel("العنوان:")); form3.addWidget(self.address_edit)
        layout.addLayout(form1); layout.addLayout(form2); layout.addLayout(form3)
        btns = QHBoxLayout(); btns.addWidget(add_btn); btns.addWidget(update_btn); btns.addWidget(del_btn)
        layout.addLayout(btns)
        layout.addWidget(self.list_widget)

        add_btn.clicked.connect(self.add_supplier)
        update_btn.clicked.connect(self.update_supplier)
        del_btn.clicked.connect(self.delete_supplier)
        self.list_widget.itemClicked.connect(self.fill_from_selected)

        self.refresh_list()
        # تعطيل الإدخال للمشاهِد
        try:
            mw = self.window()
            is_viewer = getattr(mw, 'role', '') == 'viewer'
            if is_viewer:
                for w in [self.name_edit, self.phone_edit, self.address_edit]:
                    w.setReadOnly(True)
                add_btn.setEnabled(False)
                update_btn.setEnabled(False)
                del_btn.setEnabled(False)
        except Exception:
            pass

    def refresh_list(self):
        self.list_widget.clear()
        with SessionLocal() as s:
            suppliers = s.query(Supplier).order_by(Supplier.name).all()
            for sup in suppliers:
                self.list_widget.addItem(f"{sup.id} | {sup.name} | {sup.phone or ''} | {sup.address or ''}")

    def fill_from_selected(self):
        if not self.list_widget.currentItem():
            return
        parts = [p.strip() for p in self.list_widget.currentItem().text().split('|')]
        # parts: [id, name, phone, address]
        self.name_edit.setText(parts[1])
        self.phone_edit.setText(parts[2])
        self.address_edit.setText(parts[3])

    def add_supplier(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "تنبيه", "الاسم مطلوب")
            return
        with SessionLocal() as s:
            try:
                s.add(Supplier(name=name, phone=self.phone_edit.text().strip() or None,
                               address=self.address_edit.text().strip() or None))
                s.commit()
                try:
                    mw = self.window(); username = getattr(mw, 'username', None)
                    last = s.query(Supplier).order_by(Supplier.id.desc()).first()
                    if last:
                        log_action(username, 'create', 'supplier', last.id, f'name={name}')
                except Exception:
                    pass
                self.name_edit.clear(); self.phone_edit.clear(); self.address_edit.clear()
                self.refresh_list()
                try:
                    show_toast(self, "تمت الإضافة")
                except Exception:
                    pass
            except IntegrityError:
                s.rollback()
                QMessageBox.warning(self, "خطأ", "الاسم موجود بالفعل")

    def update_supplier(self):
        if not self.list_widget.currentItem():
            return
        parts = [p.strip() for p in self.list_widget.currentItem().text().split('|')]
        sup_id = int(parts[0])
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "تنبيه", "الاسم مطلوب")
            return
        with SessionLocal() as s:
            obj = s.get(Supplier, sup_id)
            if not obj:
                return
            obj.name = name
            obj.phone = self.phone_edit.text().strip() or None
            obj.address = self.address_edit.text().strip() or None
            try:
                s.commit()
                try:
                    mw = self.window(); username = getattr(mw, 'username', None)
                    log_action(username, 'update', 'supplier', obj.id, f'name={name}')
                except Exception:
                    pass
                self.refresh_list()
                try:
                    show_toast(self, "تم التعديل")
                except Exception:
                    pass
            except IntegrityError:
                s.rollback(); QMessageBox.warning(self, "خطأ", "الاسم موجود بالفعل")

    def delete_supplier(self):
        if not self.list_widget.currentItem():
            return
        sup_id = int(self.list_widget.currentItem().text().split('|')[0].strip())
        with SessionLocal() as s:
            obj = s.get(Supplier, sup_id)
            if obj:
                sid = obj.id
                s.delete(obj)
                s.commit()
                try:
                    mw = self.window(); username = getattr(mw, 'username', None)
                    log_action(username, 'delete', 'supplier', sid, None)
                except Exception:
                    pass
                self.refresh_list()
                try:
                    show_toast(self, "تم الحذف")
                except Exception:
                    pass