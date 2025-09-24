from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTabWidget, QMessageBox, QDateEdit
from PySide6.QtCore import Qt, QDate
from datetime import datetime
from app.data.database import SessionLocal, is_date_locked, log_action
from app.data.models import Supplier, Delivery, Payment, Item, Invoice, InvoiceLine
from app.ui.toast import show_toast

class JournalPage(QWidget):
    """تسجيل اليومية: تبويتين (مسحوبات) و(توريد)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("JournalPage")
        self.setLayoutDirection(Qt.RightToLeft)
        tabs = QTabWidget(self)

        # تبويب المسحوبات
        w_withdraw = QWidget(); l_w = QVBoxLayout(w_withdraw)
        from PySide6.QtWidgets import QComboBox
        self.w_supplier = QComboBox()
        self._load_suppliers(self.w_supplier)
        self.w_amount = QLineEdit(); self.w_amount.setPlaceholderText("المبلغ")
        self.w_method = QLineEdit(); self.w_method.setPlaceholderText("طريقة الدفع")
        self.w_note = QLineEdit(); self.w_note.setPlaceholderText("ملاحظة")
        # تاريخ يدوي للمسحوبات
        self.w_date = QDateEdit(); self.w_date.setCalendarPopup(True); self.w_date.setDisplayFormat("yyyy-MM-dd"); self.w_date.setDate(self._today())
        save_w_btn = QPushButton("حفظ المسحوب"); save_w_btn.setProperty("role", "bottom")
        # خيار سحب صنف: اختيار صنف + كمية + سعر متغير
        from PySide6.QtWidgets import QComboBox
        self.w_item_combo = QComboBox(); self._load_items(self.w_item_combo)
        self.w_item_qty = QLineEdit(); self.w_item_qty.setPlaceholderText("كمية الصنف")
        self.w_item_price = QLineEdit(); self.w_item_price.setPlaceholderText("سعر الصنف")
        save_w_item_btn = QPushButton("حفظ كمبلغ/سحب صنف"); save_w_item_btn.setProperty("role", "bottom")
        # زر فتح الفاتورة المتقدمة
        open_adv_invoice_btn = QPushButton("فتح فاتورة متقدمة"); open_adv_invoice_btn.setProperty("role", "bottom")

        l_w.addLayout(self.row("الفلاح:", self.w_supplier))
        l_w.addLayout(self.row("المبلغ:", self.w_amount))
        l_w.addLayout(self.row("الطريقة:", self.w_method))
        l_w.addLayout(self.row("ملاحظة:", self.w_note))
        l_w.addLayout(self.row("التاريخ:", self.w_date))
        l_w.addWidget(save_w_btn)
        l_w.addWidget(QLabel("أو سحب صنف بسعر وكمية:"))
        l_w.addLayout(self.row("الصنف:", self.w_item_combo))
        l_w.addLayout(self.row("الكمية:", self.w_item_qty))
        l_w.addLayout(self.row("السعر:", self.w_item_price))
        l_w.addWidget(save_w_item_btn)
        l_w.addWidget(open_adv_invoice_btn)
        save_w_btn.clicked.connect(self.save_withdraw)
        save_w_item_btn.clicked.connect(self.save_withdraw_item)
        open_adv_invoice_btn.clicked.connect(self._open_advanced_invoice)

        # تبويب التوريد
        w_deliv = QWidget(); l_d = QVBoxLayout(w_deliv)
        self.d_supplier = QComboBox(); self._load_suppliers(self.d_supplier)
        self.d_item = QComboBox(); self._load_items(self.d_item)
        self.d_qty = QLineEdit(); self.d_qty.setPlaceholderText("الكمية")
        self.d_unit = QLineEdit(); self.d_unit.setPlaceholderText("الوحدة")
        self.d_price = QLineEdit(); self.d_price.setPlaceholderText("سعر الوحدة")
        # تاريخ يدوي للتوريد
        self.d_date = QDateEdit(); self.d_date.setCalendarPopup(True); self.d_date.setDisplayFormat("yyyy-MM-dd"); self.d_date.setDate(self._today())
        save_d_btn = QPushButton("حفظ التوريد"); save_d_btn.setProperty("role", "bottom")
        l_d.addLayout(self.row("الفلاح:", self.d_supplier))
        l_d.addLayout(self.row("الصنف:", self.d_item))
        l_d.addLayout(self.row("الكمية:", self.d_qty))
        l_d.addLayout(self.row("الوحدة:", self.d_unit))
        l_d.addLayout(self.row("سعر الوحدة:", self.d_price))
        l_d.addLayout(self.row("التاريخ:", self.d_date))
        l_d.addWidget(save_d_btn)
        save_d_btn.clicked.connect(self.save_delivery)

        tabs.addTab(w_withdraw, "مسحوبات")
        tabs.addTab(w_deliv, "توريد")

        root = QVBoxLayout(self); root.addWidget(tabs)
        # تعطيل الإدخال للمشاهِد
        try:
            mw = self.window(); is_viewer = getattr(mw, 'role', '') == 'viewer'
            if is_viewer:
                # تبويب المسحوبات
                for w in [self.w_supplier, self.w_amount, self.w_method, self.w_note, self.w_item_combo, self.w_item_qty, self.w_item_price, self.w_date]:
                    if hasattr(w, 'setReadOnly'):
                        w.setReadOnly(True)
                    else:
                        w.setEnabled(False)
                # أزرار المسحوبات
                for b in self.findChildren(QPushButton):
                    # لا نعطّل التنقل العام هنا، لكن نعطل أزرار الحفظ داخل هذه الصفحة
                    if b.text() in ["حفظ المسحوب", "حفظ كمبلغ/سحب صنف", "حفظ التوريد"]:
                        b.setEnabled(False)
                # تبويب التوريد
                for w in [self.d_supplier, self.d_item, self.d_qty, self.d_unit, self.d_price, self.d_date]:
                    if hasattr(w, 'setReadOnly'):
                        w.setReadOnly(True)
                    else:
                        w.setEnabled(False)
        except Exception:
            pass

    def row(self, label, widget):
        h = QHBoxLayout(); h.addWidget(QLabel(label)); h.addWidget(widget); return h

    def _load_suppliers(self, combo):
        combo.clear()
        with SessionLocal() as s:
            for sup in s.query(Supplier).order_by(Supplier.name).all():
                combo.addItem(sup.name, sup.id)

    def _load_items(self, combo):
        combo.clear()
        with SessionLocal() as s:
            for it in s.query(Item).order_by(Item.name).all():
                combo.addItem(it.name, it.id)

    def _today(self):
        return QDate.currentDate()

    def _open_advanced_invoice(self):
        # يتحكم به إعداد من صفحة الإعدادات
        try:
            from app.data.database import get_setting
            enabled = (get_setting('advanced_invoice_ui') or '0') == '1'
        except Exception:
            enabled = False
        if not enabled:
            QMessageBox.information(self, "غير مفعّل", "واجهة الفاتورة المتقدمة غير مفعّلة. فعّلها من الإعدادات.")
            return
        try:
            from app.ui.invoice_dialog import InvoiceDialog
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"تعذّر فتح شاشة الفاتورة المتقدمة: {e}")
            return
        dlg = InvoiceDialog(self)
        dlg.exec()
    def save_withdraw(self):
        if self.w_supplier.currentIndex() < 0:
            QMessageBox.warning(self, "تنبيه", "اختر الفلاح"); return
        sup_id = self.w_supplier.currentData()
        try:
            amount = float(self.w_amount.text())
        except ValueError:
            QMessageBox.warning(self, "تنبيه", "أدخل مبلغ صحيح"); return
        paid_at = datetime.strptime(self.w_date.text(), "%Y-%m-%d")
        if is_date_locked(paid_at):
            QMessageBox.warning(self, "مغلق", "الفترة مقفلة — لا يمكن الحفظ ضمن نطاق القفل"); return
        with SessionLocal() as s:
            obj = Payment(supplier_id=sup_id, amount=amount, method=self.w_method.text().strip() or None, note=self.w_note.text().strip() or None, paid_at=paid_at)
            s.add(obj); s.commit()
            try:
                mw = self.window(); username = getattr(mw, 'username', None)
                log_action(username, 'create', 'payment', obj.id, f'amount={amount}')
            except Exception:
                pass
            try:
                show_toast(self, "تم حفظ المسحوب")
            except Exception:
                QMessageBox.information(self, "تم", "تم حفظ المسحوب")
            self.w_amount.clear(); self.w_method.clear(); self.w_note.clear()

    def save_withdraw_item(self):
        if self.w_supplier.currentIndex() < 0 or self.w_item_combo.currentIndex() < 0:
            QMessageBox.warning(self, "تنبيه", "اختر الفلاح والصنف"); return
        sup_id = self.w_supplier.currentData(); item_id = self.w_item_combo.currentData()
        try:
            qty = float(self.w_item_qty.text()); price = float(self.w_item_price.text())
        except ValueError:
            QMessageBox.warning(self, "تنبيه", "تحقق من القيم"); return
        total = qty * price
        paid_at = datetime.strptime(self.w_date.text(), "%Y-%m-%d")
        if is_date_locked(paid_at):
            QMessageBox.warning(self, "مغلق", "الفترة مقفلة — لا يمكن الحفظ ضمن نطاق القفل"); return
        # تحذير حدّ أدنى للمخزون
        try:
            from app.data.database import get_item_stock
            from app.data.database import ENGINE
            from sqlalchemy import text as sqltext
            with ENGINE.connect() as conn:
                row = conn.execute(sqltext("SELECT min_stock FROM items WHERE id=:i"), {"i": item_id}).fetchone()
                min_stock = float(row[0]) if row and row[0] is not None else None
            if min_stock is not None:
                current_stock = get_item_stock(item_id)
                if (current_stock - qty) < min_stock:
                    QMessageBox.warning(self, "تنبيه مخزون", "سيهبط رصيد الصنف تحت الحد الأدنى")
        except Exception:
            pass
        # إنشاء فاتورة وخط فاتورة بدل تسجيله كمبلغ فقط
        from sqlalchemy import select
        with SessionLocal() as s:
            inv = Invoice(supplier_id=sup_id, customer_name=None, total_amount=total, discount_amount=0.0, tax_amount=0.0, net_amount=total, status='posted', created_at=paid_at)
            s.add(inv); s.flush()  # للحصول على id
            line = InvoiceLine(invoice_id=inv.id, item_id=item_id, description=None, quantity=qty, unit='unit', unit_price=price, discount=0.0, line_total=total)
            s.add(line)
            # تسجيل دفعة مساوية لتأثير الفاتورة على حساب الفلاح (يمكن جعلها اختيارية لاحقاً)
            pay = Payment(supplier_id=sup_id, amount=total, method="فاتورة صنف", note=f"فاتورة #{inv.id}", paid_at=paid_at)
            s.add(pay)
            s.commit()
            try:
                mw = self.window(); username = getattr(mw, 'username', None)
                log_action(username, 'create', 'invoice', inv.id, f'amount={total}')
                log_action(username, 'create', 'invoice_line', line.id, f'item={item_id}, qty={qty}')
                log_action(username, 'create', 'payment', pay.id, f'amount={total}, via=invoice')
            except Exception:
                pass
            try:
                show_toast(self, "تم حفظ الفاتورة وسحب الصنف")
            except Exception:
                QMessageBox.information(self, "تم", "تم حفظ الفاتورة وخط الصنف")
            self.w_item_qty.clear(); self.w_item_price.clear()

    def save_delivery(self):
        if self.d_supplier.currentIndex() < 0 or self.d_item.currentIndex() < 0:
            QMessageBox.warning(self, "تنبيه", "اختر الفلاح والصنف"); return
        try:
            qty = float(self.d_qty.text()); price = float(self.d_price.text()); unit = self.d_unit.text().strip() or 'kg'
        except ValueError:
            QMessageBox.warning(self, "تنبيه", "تحقق من القيم"); return
        sup_id = self.d_supplier.currentData(); item_id = self.d_item.currentData()
        delivered_at = datetime.strptime(self.d_date.text(), "%Y-%m-%d")
        if is_date_locked(delivered_at):
            QMessageBox.warning(self, "مغلق", "الفترة مقفلة — لا يمكن الحفظ ضمن نطاق القفل"); return
        with SessionLocal() as s:
            total = qty * price
            obj = Delivery(supplier_id=sup_id, item_id=item_id, quantity=qty, unit=unit, price_per_unit=price, total_price=total, delivered_at=delivered_at)
            s.add(obj); s.commit()
            try:
                mw = self.window(); username = getattr(mw, 'username', None)
                log_action(username, 'create', 'delivery', obj.id, f'item={item_id}, qty={qty}')
            except Exception:
                pass
            try:
                show_toast(self, "تم حفظ التوريد")
            except Exception:
                QMessageBox.information(self, "تم", "تم حفظ التوريد")
            self.d_qty.clear(); self.d_price.clear()