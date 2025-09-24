from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QMessageBox, QListWidget, QDateEdit
from app.data.database import SessionLocal
from app.data.models import Supplier, Payment, AuditLog
from app.ui.toast import show_toast

class PaymentsDialog(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.supplier_combo = QComboBox()
        self.amount_edit = QLineEdit(); self.amount_edit.setPlaceholderText("المبلغ")
        self.method_edit = QLineEdit(); self.method_edit.setPlaceholderText("طريقة الدفع")
        self.note_edit = QLineEdit(); self.note_edit.setPlaceholderText("ملاحظة")
        self.date_edit = QDateEdit(); self.date_edit.setCalendarPopup(True); self.date_edit.setDisplayFormat("yyyy-MM-dd")
        from PySide6.QtCore import QDate
        self.date_edit.setDate(QDate.currentDate())

        add_btn = QPushButton("تسجيل"); add_btn.setProperty("role", "bottom")
        update_btn = QPushButton("تعديل"); update_btn.setProperty("role", "bottom")
        del_btn = QPushButton("حذف"); del_btn.setProperty("role", "bottom")
        self.list_widget = QListWidget()

        layout = QVBoxLayout(self)
        layout.addLayout(self.row("المورد:", self.supplier_combo))
        layout.addLayout(self.row("المبلغ:", self.amount_edit))
        layout.addLayout(self.row("الطريقة:", self.method_edit))
        layout.addLayout(self.row("ملاحظة:", self.note_edit))
        layout.addLayout(self.row("التاريخ:", self.date_edit))
        btns = QHBoxLayout(); btns.addWidget(add_btn); btns.addWidget(update_btn); btns.addWidget(del_btn)
        layout.addLayout(btns)
        layout.addWidget(self.list_widget)

        add_btn.clicked.connect(self.add_payment)
        update_btn.clicked.connect(self.update_payment)
        del_btn.clicked.connect(self.delete_payment)
        self.list_widget.itemClicked.connect(self.fill_from_selected)

        self.load_suppliers(); self.refresh_list()

    def row(self, label, widget):
        h = QHBoxLayout(); h.addWidget(QLabel(label)); h.addWidget(widget); return h

    def load_suppliers(self):
        self.supplier_combo.clear()
        with SessionLocal() as s:
            for sup in s.query(Supplier).order_by(Supplier.name).all():
                self.supplier_combo.addItem(sup.name, sup.id)

    def refresh_list(self):
        self.list_widget.clear()
        with SessionLocal() as s:
            for p in s.query(Payment).order_by(Payment.paid_at.desc()).limit(100):
                sup = s.get(Supplier, p.supplier_id)
                self.list_widget.addItem(f"{p.id} | {sup.name} | {p.amount} | {p.method or ''} | {p.note or ''}")

    def fill_from_selected(self):
        if not self.list_widget.currentItem():
            return
        parts = [p.strip() for p in self.list_widget.currentItem().text().split('|')]
        pay_id = int(parts[0])
        with SessionLocal() as s:
            p = s.get(Payment, pay_id)
            if not p:
                return
            self._set_combo_by_data(self.supplier_combo, p.supplier_id)
            self.amount_edit.setText(str(p.amount))
            self.method_edit.setText(p.method or '')
            self.note_edit.setText(p.note or '')

    def _set_combo_by_data(self, combo, value):
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i); return

    def add_payment(self):
        if self.supplier_combo.count() == 0:
            QMessageBox.warning(self, "تنبيه", "من فضلك أنشئ مورد أولاً")
            return
        try:
            amount = float(self.amount_edit.text())
        except ValueError:
            QMessageBox.warning(self, "خطأ", "المبلغ يجب أن يكون رقمًا")
            return
        with SessionLocal() as s:
            # تحويل QDate إلى datetime
            qd = self.date_edit.date()
            from datetime import datetime
            paid_at = datetime(qd.year(), qd.month(), qd.day(), 0, 0, 0)
            p = Payment(supplier_id=self.supplier_combo.currentData(), amount=amount,
                        method=self.method_edit.text().strip() or None,
                        note=self.note_edit.text().strip() or None,
                        paid_at=paid_at)
            s.add(p); s.commit()
            try:
                s.add(AuditLog(username=None, action='create', entity='payment', entity_id=p.id, details=f'amount={amount}'))
                s.commit()
            except Exception:
                s.rollback()
        self.amount_edit.clear(); self.method_edit.clear(); self.note_edit.clear()
        self.refresh_list()
        try:
            show_toast(self, "تم تسجيل السحب")
        except Exception:
            pass

    def update_payment(self):
        if not self.list_widget.currentItem():
            return
        try:
            amount = float(self.amount_edit.text())
        except ValueError:
            QMessageBox.warning(self, "خطأ", "المبلغ يجب أن يكون رقمًا")
            return
        pay_id = int(self.list_widget.currentItem().text().split('|')[0].strip())
        with SessionLocal() as s:
            p = s.get(Payment, pay_id)
            if not p:
                return
            p.supplier_id = self.supplier_combo.currentData()
            p.amount = amount
            p.method = self.method_edit.text().strip() or None
            p.note = self.note_edit.text().strip() or None
            # تحديث التاريخ اليدوي
            qd = self.date_edit.date()
            from datetime import datetime
            p.paid_at = datetime(qd.year(), qd.month(), qd.day(), 0, 0, 0)
            s.commit()
            try:
                s.add(AuditLog(username=None, action='update', entity='payment', entity_id=pay_id, details=f'amount={amount}'))
                s.commit()
            except Exception:
                s.rollback()
        self.refresh_list()
        try:
            show_toast(self, "تم تحديث السحب")
        except Exception:
            pass

    def delete_payment(self):
        if not self.list_widget.currentItem():
            return
        pay_id = int(self.list_widget.currentItem().text().split('|')[0].strip())
        with SessionLocal() as s:
            p = s.get(Payment, pay_id)
            if p:
                s.delete(p); s.commit()
                try:
                    s.add(AuditLog(username=None, action='delete', entity='payment', entity_id=pay_id, details=None))
                    s.commit()
                except Exception:
                    s.rollback()
        self.refresh_list()
        try:
            show_toast(self, "تم حذف السحب")
        except Exception:
            pass