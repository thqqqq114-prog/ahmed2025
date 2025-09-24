from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QMessageBox, QCheckBox
from app.data.database import SessionLocal
from app.data.models import Item
from app.ui.toast import show_toast

class ItemsDialog(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.name_edit = QLineEdit(); self.name_edit.setPlaceholderText("اسم الصنف")
        self.unit_edit = QLineEdit(); self.unit_edit.setPlaceholderText("الوحدة الافتراضية (kg/bag/ton)")
        self.unit_weight_edit = QLineEdit(); self.unit_weight_edit.setPlaceholderText("وزن الوحدة (اختياري)")
        self.price_edit = QLineEdit(); self.price_edit.setPlaceholderText("سعر افتراضي (اختياري)")
        self.min_stock_edit = QLineEdit(); self.min_stock_edit.setPlaceholderText("حد أدنى للمخزون (اختياري)")
        self.allow_override_cb = QCheckBox("سماح تعديل السعر عند الفاتورة")
        self.allow_override_cb.setChecked(True)

        add_btn = QPushButton("إضافة/تعديل"); add_btn.setProperty("role", "bottom")
        del_btn = QPushButton("حذف"); del_btn.setProperty("role", "bottom")
        self.list_widget = QListWidget()

        layout = QVBoxLayout(self)
        layout.addLayout(self.row("الصنف:", self.name_edit))
        layout.addLayout(self.row("الوحدة:", self.unit_edit))
        layout.addLayout(self.row("وزن الوحدة:", self.unit_weight_edit))
        layout.addLayout(self.row("سعر افتراضي:", self.price_edit))
        layout.addLayout(self.row("حد أدنى للمخزون:", self.min_stock_edit))
        layout.addWidget(self.allow_override_cb)
        layout.addWidget(add_btn)
        layout.addWidget(del_btn)
        layout.addWidget(self.list_widget)

        add_btn.clicked.connect(self.add_or_update)
        del_btn.clicked.connect(self.delete_item)
        self.list_widget.itemClicked.connect(self.fill_from_selected)

        self.refresh_list()
        # تعطيل الإدخال للمشاهِد
        try:
            mw = self.window()
            is_viewer = getattr(mw, 'role', '') == 'viewer'
            if is_viewer:
                for w in [self.name_edit, self.unit_edit, self.unit_weight_edit, self.price_edit, self.min_stock_edit]:
                    w.setReadOnly(True)
                self.allow_override_cb.setEnabled(False)
                add_btn.setEnabled(False)
                del_btn.setEnabled(False)
        except Exception:
            pass

    def row(self, label, widget):
        h = QHBoxLayout(); h.addWidget(QLabel(label)); h.addWidget(widget); return h

    def refresh_list(self):
        self.list_widget.clear()
        with SessionLocal() as s:
            for it in s.query(Item).order_by(Item.name).all():
                self.list_widget.addItem(f"{it.id} | {it.name} | {it.default_unit} | {it.default_unit_weight or '-'} | {it.default_price_per_unit or '-'} | min={it.min_stock or '-'} | override={'Y' if it.allow_price_override else 'N'}")

    def fill_from_selected(self):
        t = self.list_widget.currentItem().text()
        parts = [p.strip() for p in t.split('|')]
        # parts: [id, name, unit, unit_weight, price, min, override]
        self.name_edit.setText(parts[1])
        self.unit_edit.setText(parts[2])
        self.unit_weight_edit.setText('' if parts[3] == '-' else parts[3])
        self.price_edit.setText('' if parts[4] == '-' else parts[4])
        # extract min=...
        try:
            min_val = parts[5].split('=')[1].strip()
            self.min_stock_edit.setText('' if min_val == '-' else min_val)
        except Exception:
            self.min_stock_edit.setText('')
        self.allow_override_cb.setChecked('Y' in parts[6])

    def add_or_update(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "تنبيه", "اسم الصنف مطلوب")
            return
        default_unit = self.unit_edit.text().strip() or 'kg'
        default_unit_weight = None
        default_price = None
        min_stock = None
        try:
            if self.unit_weight_edit.text().strip():
                default_unit_weight = float(self.unit_weight_edit.text().strip())
            if self.price_edit.text().strip():
                default_price = float(self.price_edit.text().strip())
            if self.min_stock_edit.text().strip():
                min_stock = float(self.min_stock_edit.text().strip())
        except ValueError:
            QMessageBox.warning(self, "خطأ", "الوزن والسعر والحد الأدنى يجب أن تكون أرقامًا")
            return
        with SessionLocal() as s:
            existing = s.query(Item).filter(Item.name == name).one_or_none()
            if existing:
                existing.default_unit = default_unit
                existing.default_unit_weight = default_unit_weight
                existing.default_price_per_unit = default_price
                existing.min_stock = min_stock
                existing.allow_price_override = self.allow_override_cb.isChecked()
            else:
                s.add(Item(name=name, default_unit=default_unit,
                           default_unit_weight=default_unit_weight,
                           default_price_per_unit=default_price,
                           min_stock=min_stock,
                           allow_price_override=self.allow_override_cb.isChecked()))
            s.commit()
            self.refresh_list()
            self.name_edit.clear(); self.unit_edit.clear(); self.unit_weight_edit.clear(); self.price_edit.clear(); self.min_stock_edit.clear(); self.allow_override_cb.setChecked(True)
            try:
                show_toast(self, "تم الحفظ")
            except Exception:
                pass

    def delete_item(self):
        if not self.list_widget.currentItem():
            return
        t = self.list_widget.currentItem().text()
        item_id = int(t.split('|')[0].strip())
        with SessionLocal() as s:
            obj = s.get(Item, item_id)
            if obj is None:
                return
            s.delete(obj)
            s.commit()
            self.refresh_list()
            try:
                show_toast(self, "تم الحذف")
            except Exception:
                pass