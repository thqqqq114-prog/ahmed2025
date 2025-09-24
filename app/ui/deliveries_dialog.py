from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QMessageBox, QListWidget, QDateEdit
from app.data.database import SessionLocal
from app.data.models import Supplier, Delivery, Item, Factory, AuditLog
from app.ui.toast import show_toast

class DeliveriesDialog(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.supplier_combo = QComboBox()
        self.item_combo = QComboBox()
        self.factory_combo = QComboBox()

        self.qty_edit = QLineEdit(); self.qty_edit.setPlaceholderText("الكمية")
        self.unit_edit = QLineEdit(); self.unit_edit.setPlaceholderText("الوحدة (kg/ton/bag)")
        self.unit_weight_edit = QLineEdit(); self.unit_weight_edit.setPlaceholderText("وزن الوحدة (اختياري)")
        self.price_edit = QLineEdit(); self.price_edit.setPlaceholderText("سعر الوحدة")
        self.date_edit = QDateEdit(); self.date_edit.setCalendarPopup(True); self.date_edit.setDisplayFormat("yyyy-MM-dd")
        from PySide6.QtCore import QDate
        self.date_edit.setDate(QDate.currentDate())

        add_btn = QPushButton("تسجيل التوريد"); add_btn.setProperty("role", "bottom")
        update_btn = QPushButton("تعديل"); update_btn.setProperty("role", "bottom")
        del_btn = QPushButton("حذف"); del_btn.setProperty("role", "bottom")
        self.list_widget = QListWidget()

        layout = QVBoxLayout(self)
        layout.addLayout(self.row("المورد:", self.supplier_combo))
        layout.addLayout(self.row("الصنف:", self.item_combo))
        layout.addLayout(self.row("المصنع (اختياري):", self.factory_combo))
        layout.addLayout(self.row("الكمية:", self.qty_edit))
        layout.addLayout(self.row("الوحدة:", self.unit_edit))
        layout.addLayout(self.row("وزن الوحدة:", self.unit_weight_edit))
        layout.addLayout(self.row("سعر الوحدة:", self.price_edit))
        layout.addLayout(self.row("التاريخ:", self.date_edit))
        btns = QHBoxLayout(); btns.addWidget(add_btn); btns.addWidget(update_btn); btns.addWidget(del_btn)
        layout.addLayout(btns)
        layout.addWidget(self.list_widget)

        add_btn.clicked.connect(self.add_delivery)
        update_btn.clicked.connect(self.update_delivery)
        del_btn.clicked.connect(self.delete_delivery)
        self.list_widget.itemClicked.connect(self.fill_from_selected)

        self.load_refs(); self.refresh_list()

    def row(self, label, widget):
        from PySide6.QtWidgets import QHBoxLayout, QLabel
        h = QHBoxLayout(); h.addWidget(QLabel(label)); h.addWidget(widget); return h

    def load_refs(self):
        self.supplier_combo.clear(); self.item_combo.clear(); self.factory_combo.clear()
        with SessionLocal() as s:
            for sup in s.query(Supplier).order_by(Supplier.name).all():
                self.supplier_combo.addItem(sup.name, sup.id)
            for it in s.query(Item).order_by(Item.name).all():
                self.item_combo.addItem(it.name, it.id)
            self.factory_combo.addItem("—", None)
            for f in s.query(Factory).order_by(Factory.name).all():
                self.factory_combo.addItem(f.name, f.id)

    def refresh_list(self):
        self.list_widget.clear()
        with SessionLocal() as s:
            for d in s.query(Delivery).order_by(Delivery.delivered_at.desc()).limit(100):
                sup = s.get(Supplier, d.supplier_id)
                it = s.get(Item, d.item_id)
                fac = s.get(Factory, d.factory_id) if d.factory_id else None
                self.list_widget.addItem(f"{d.id} | {sup.name} | {it.name} | {fac.name if fac else '-'} | {d.quantity} {d.unit} | {d.price_per_unit} | {d.total_price}")

    def fill_from_selected(self):
        if not self.list_widget.currentItem():
            return
        parts = [p.strip() for p in self.list_widget.currentItem().text().split('|')]
        # [id, sup, item, factory, qty unit, price, total]
        with SessionLocal() as s:
            d = s.get(Delivery, int(parts[0]))
            if not d:
                return
            # set combos
            self._set_combo_by_data(self.supplier_combo, d.supplier_id)
            self._set_combo_by_data(self.item_combo, d.item_id)
            self._set_combo_by_data(self.factory_combo, d.factory_id)
            # fields
            self.qty_edit.setText(str(d.quantity))
            self.unit_edit.setText(d.unit or '')
            self.unit_weight_edit.setText('' if d.unit_weight is None else str(d.unit_weight))
            self.price_edit.setText(str(d.price_per_unit))

    def _set_combo_by_data(self, combo, value):
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i); return

    def add_delivery(self):
        if self.supplier_combo.count() == 0:
            QMessageBox.warning(self, "تنبيه", "من فضلك أنشئ مورد أولاً")
            return
        if self.item_combo.count() == 0:
            QMessageBox.warning(self, "تنبيه", "من فضلك أنشئ صنف أولاً")
            return
        try:
            qty = float(self.qty_edit.text()); price = float(self.price_edit.text())
        except ValueError:
            QMessageBox.warning(self, "خطأ", "الكمية والسعر يجب أن يكونا أرقامًا")
            return
        unit = self.unit_edit.text().strip() or 'kg'
        unit_weight = None
        try:
            if self.unit_weight_edit.text().strip():
                unit_weight = float(self.unit_weight_edit.text().strip())
        except ValueError:
            QMessageBox.warning(self, "خطأ", "وزن الوحدة يجب أن يكون رقمًا")
            return
        total = qty * price
        with SessionLocal() as s:
            # تحويل QDate إلى datetime
            qd = self.date_edit.date()
            from datetime import datetime
            delivered_at = datetime(qd.year(), qd.month(), qd.day(), 0, 0, 0)
            d = Delivery(
                supplier_id=self.supplier_combo.currentData(),
                item_id=self.item_combo.currentData(),
                factory_id=self.factory_combo.currentData(),
                quantity=qty,
                unit=unit,
                unit_weight=unit_weight,
                price_per_unit=price,
                total_price=total,
                delivered_at=delivered_at,
            )
            s.add(d); s.commit()
            try:
                s.add(AuditLog(username=None, action='create', entity='delivery', entity_id=d.id, details=f'total={total}'))
                s.commit()
            except Exception:
                s.rollback()
        self.qty_edit.clear(); self.unit_edit.clear(); self.unit_weight_edit.clear(); self.price_edit.clear()
        self.refresh_list()
        try:
            show_toast(self, "تم تسجيل التوريد")
        except Exception:
            QMessageBox.information(self, "تم", f"تم تسجيل التوريد. الإجمالي: {total}")

    def update_delivery(self):
        if not self.list_widget.currentItem():
            return
        try:
            qty = float(self.qty_edit.text()); price = float(self.price_edit.text())
        except ValueError:
            QMessageBox.warning(self, "خطأ", "الكمية والسعر يجب أن يكونا أرقامًا")
            return
        unit = self.unit_edit.text().strip() or 'kg'
        unit_weight = None
        try:
            if self.unit_weight_edit.text().strip():
                unit_weight = float(self.unit_weight_edit.text().strip())
        except ValueError:
            QMessageBox.warning(self, "خطأ", "وزن الوحدة يجب أن يكون رقمًا")
            return
        d_id = int(self.list_widget.currentItem().text().split('|')[0].strip())
        with SessionLocal() as s:
            d = s.get(Delivery, d_id)
            if not d:
                return
            d.supplier_id = self.supplier_combo.currentData()
            d.item_id = self.item_combo.currentData()
            d.factory_id = self.factory_combo.currentData()
            d.quantity = qty
            d.unit = unit
            d.unit_weight = unit_weight
            d.price_per_unit = price
            d.total_price = qty * price
            # تحديث التاريخ اليدوي
            qd = self.date_edit.date()
            from datetime import datetime
            d.delivered_at = datetime(qd.year(), qd.month(), qd.day(), 0, 0, 0)
            s.commit()
        self.refresh_list()
        try:
            show_toast(self, "تم تحديث التوريد")
        except Exception:
            pass

    def delete_delivery(self):
        if not self.list_widget.currentItem():
            return
        d_id = int(self.list_widget.currentItem().text().split('|')[0].strip())
        with SessionLocal() as s:
            d = s.get(Delivery, d_id)
            if d:
                s.delete(d); s.commit()
                try:
                    s.add(AuditLog(username=None, action='delete', entity='delivery', entity_id=d_id, details=None))
                    s.commit()
                except Exception:
                    s.rollback()
        self.refresh_list()
        try:
            show_toast(self, "تم حذف التوريد")
        except Exception:
            pass