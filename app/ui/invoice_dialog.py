from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QMessageBox, QCheckBox, QDateEdit
)
from PySide6.QtCore import Qt, QDate
from app.data.database import SessionLocal, is_date_locked, get_setting, set_setting, log_action
from sqlalchemy import text
from app.data.models import Supplier, Item, Invoice, InvoiceLine, Payment

class InvoiceDialog(QDialog):
    """واجهة فاتورة متقدمة مع بنود متعددة وخصم/ضريبة، ووضع بسيط/متقدم."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("فاتورة متقدمة")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(800, 600)

        # رأس الفاتورة
        self.sup_combo = QComboBox(); self._load_suppliers()
        self.date_edit = QDateEdit(); self.date_edit.setCalendarPopup(True); self.date_edit.setDisplayFormat("yyyy-MM-dd"); self.date_edit.setDate(QDate.currentDate())
        self.simple_mode_cb = QCheckBox("الوضع البسيط")
        # تحميل الوضع الافتراضي من الإعدادات
        try:
            self.simple_mode_cb.setChecked((get_setting('invoice_default_mode') or 'simple') == 'simple')
        except Exception:
            self.simple_mode_cb.setChecked(True)

        # جدول البنود: الصنف، الوصف، الكمية، السعر، الخصم%، الضريبة%، الإجمالي
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["الصنف", "الوصف", "الكمية", "السعر", "خصم %", "ضريبة %", "الإجمالي"])
        self.table.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)

        add_row_btn = QPushButton("سطر جديد"); add_row_btn.setProperty("role", "bottom")
        del_row_btn = QPushButton("حذف سطر"); del_row_btn.setProperty("role", "bottom")
        calc_btn = QPushButton("حساب"); calc_btn.setProperty("role", "bottom")
        save_btn = QPushButton("حفظ"); save_btn.setProperty("role", "bottom")

        # إجماليات
        self.total_edit = QLineEdit(); self.total_edit.setPlaceholderText("إجمالي"); self.total_edit.setReadOnly(True)
        self.discount_abs_edit = QLineEdit(); self.discount_abs_edit.setPlaceholderText("خصم إضافي (مبلغ)")
        self.tax_abs_edit = QLineEdit(); self.tax_abs_edit.setPlaceholderText("ضريبة إضافية (مبلغ)")
        self.net_edit = QLineEdit(); self.net_edit.setPlaceholderText("الصافي"); self.net_edit.setReadOnly(True)

        layout = QVBoxLayout(self)
        top = QHBoxLayout(); top.addWidget(QLabel("الفلاح:")); top.addWidget(self.sup_combo)
        top.addWidget(QLabel("التاريخ:")); top.addWidget(self.date_edit)
        top.addWidget(self.simple_mode_cb)
        layout.addLayout(top)
        layout.addWidget(self.table)
        row_btns = QHBoxLayout(); row_btns.addWidget(add_row_btn); row_btns.addWidget(del_row_btn); row_btns.addStretch(1); row_btns.addWidget(calc_btn); row_btns.addWidget(save_btn)
        layout.addLayout(row_btns)
        sums = QHBoxLayout(); sums.addWidget(QLabel("الإجمالي:")); sums.addWidget(self.total_edit)
        sums.addWidget(QLabel("خصم+ (مبلغ):")); sums.addWidget(self.discount_abs_edit)
        sums.addWidget(QLabel("ضريبة+ (مبلغ):")); sums.addWidget(self.tax_abs_edit)
        sums.addWidget(QLabel("الصافي:")); sums.addWidget(self.net_edit)
        layout.addLayout(sums)

        add_row_btn.clicked.connect(self.add_row)
        del_row_btn.clicked.connect(self.del_row)
        calc_btn.clicked.connect(self.recalculate)
        save_btn.clicked.connect(self.save_invoice)
        # حفظ تفضيل الوضع عند التغيير
        self.simple_mode_cb.stateChanged.connect(self._persist_default_mode)

        # ابدأ بسطر فارغ
        self.add_row()

    def _load_suppliers(self):
        with SessionLocal() as s:
            for sup in s.query(Supplier).order_by(Supplier.name).all():
                self.sup_combo.addItem(sup.name, sup.id)

    def _load_items_combo(self, combo: QComboBox):
        combo.clear()
        with SessionLocal() as s:
            for it in s.query(Item).order_by(Item.name).all():
                combo.addItem(it.name, it.id)

    def add_row(self):
        r = self.table.rowCount()
        self.table.insertRow(r)
        # صنف (كومبوبوكس داخل الجدول)
        from PySide6.QtWidgets import QWidget, QHBoxLayout
        w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0,0,0,0)
        combo = QComboBox(); self._load_items_combo(combo)
        h.addWidget(combo); w.setLayout(h)
        self.table.setCellWidget(r, 0, w)
        for c in range(1, 7):
            self.table.setItem(r, c, QTableWidgetItem(""))

    def del_row(self):
        r = self.table.currentRow()
        if r >= 0:
            self.table.removeRow(r)

    def _persist_default_mode(self):
        try:
            set_setting('invoice_default_mode', 'simple' if self.simple_mode_cb.isChecked() else 'advanced')
        except Exception:
            pass

    def recalculate(self):
        total = 0.0
        for r in range(self.table.rowCount()):
            # استرجاع الصنف
            cw = self.table.cellWidget(r, 0)
            combo = cw.findChild(QComboBox)
            # القيم
            desc = self.table.item(r, 1).text() if self.table.item(r,1) else ""
            qty = float(self.table.item(r, 2).text() or 0)
            price = float(self.table.item(r, 3).text() or 0)
            disc_pct = float(self.table.item(r, 4).text() or 0)
            tax_pct = float(self.table.item(r, 5).text() or 0)
            line_total = qty * price
            if not self.simple_mode_cb.isChecked():
                line_total -= (line_total * disc_pct / 100.0)
                line_total += (line_total * tax_pct / 100.0)
            # اكتب الإجمالي في الخانة
            self.table.setItem(r, 6, QTableWidgetItem(f"{line_total:.2f}"))
            total += line_total
        # إجماليات إضافية
        try:
            total += float(self.tax_abs_edit.text() or 0)
            total -= float(self.discount_abs_edit.text() or 0)
        except ValueError:
            pass
        self.total_edit.setText(f"{total:.2f}")
        self.net_edit.setText(f"{total:.2f}")

    def save_invoice(self):
        if self.sup_combo.currentIndex() < 0:
            QMessageBox.warning(self, "تنبيه", "اختر الفلاح"); return
        sup_id = self.sup_combo.currentData()
        dt = self.date_edit.text()
        from datetime import datetime
        created_at = datetime.strptime(dt, "%Y-%m-%d")
        if is_date_locked(created_at):
            QMessageBox.warning(self, "مغلق", "الفترة مقفلة — لا يمكن الحفظ ضمن نطاق القفل"); return
        # احسب لتحديث الإجماليات
        self.recalculate()
        total = float(self.net_edit.text() or 0)
        username = None
        try:
            mw = self.window(); username = getattr(mw, 'username', None)
        except Exception:
            pass
        with SessionLocal() as s:
            # توليد رقم فاتورة وفق الصيغة
            from app.data.database import get_setting
            fmt = get_setting('invoice_format') or '{YYYY}{MM}-{SEQ:04}'
            # احسب التسلسل الحالي حسب السنة/الشهر
            year = created_at.year; month = created_at.month
            last_no = s.execute(text("SELECT invoice_no FROM invoices WHERE invoice_no LIKE :pfx ORDER BY id DESC LIMIT 1"), {"pfx": f"{year}{month:02}%"}).fetchone() if '{SEQ' in fmt else None
            seq = 1
            if last_no and last_no[0]:
                import re
                m = re.search(r"(\d+)$", last_no[0])
                if m:
                    seq = int(m.group(1)) + 1
            inv_no = fmt.replace('{YYYY}', f'{year}').replace('{MM}', f'{month:02}')
            if '{SEQ' in fmt:
                # صيغة {SEQ:04}
                import re
                m = re.search(r"\{SEQ:(\d+)\}", fmt)
                width = int(m.group(1)) if m else 4
                inv_no = inv_no.replace(m.group(0) if m else '{SEQ:04}', f"{seq:0{width}d}")
            inv = Invoice(invoice_no=inv_no, supplier_id=sup_id, customer_name=None,
                          total_amount=total, discount_amount=0.0, tax_amount=0.0,
                          net_amount=total, status='posted', created_at=created_at)
            s.add(inv); s.flush()
            for r in range(self.table.rowCount()):
                cw = self.table.cellWidget(r, 0); combo = cw.findChild(QComboBox)
                item_id = combo.currentData()
                desc = self.table.item(r, 1).text() if self.table.item(r,1) else None
                qty = float(self.table.item(r, 2).text() or 0)
                price = float(self.table.item(r, 3).text() or 0)
                disc_pct = float(self.table.item(r, 4).text() or 0)
                tax_pct = float(self.table.item(r, 5).text() or 0)
                # فحص المخزون قبل اعتماد السطر
                from app.data.database import get_item_stock
                current_stock = get_item_stock(item_id)
                if qty > current_stock:
                    s.rollback()
                    QMessageBox.warning(self, "المخزون", f"الكمية المطلوبة ({qty}) للصنف ID={item_id} تتجاوز المخزون المتاح ({current_stock:.2f})")
                    return
                # تحذير إذا سينخفض الرصيد عن الحد الأدنى
                it = s.get(Item, item_id)
                try:
                    min_stock = float(it.min_stock or 0)
                except Exception:
                    min_stock = 0.0
                new_stock = current_stock - qty
                if min_stock and new_stock < min_stock:
                    from PySide6.QtWidgets import QMessageBox as _QB
                    ans = _QB.question(self, "تحذير المخزون", f"سيصبح رصيد الصنف '{it.name}' {new_stock:.2f} أقل من الحد الأدنى ({min_stock}). هل تريد المتابعة؟", _QB.Yes | _QB.No)
                    if ans != _QB.Yes:
                        s.rollback(); return
                line_total = float(self.table.item(r, 6).text() or 0)
                line = InvoiceLine(invoice_id=inv.id, item_id=item_id, description=desc,
                                   quantity=qty, unit='unit', unit_price=price,
                                   discount=disc_pct, line_total=line_total)
                s.add(line); s.flush()
                try:
                    log_action(username, 'create', 'invoice_line', line.id, f'item={item_id}, qty={qty}')
                except Exception:
                    pass
            pay = Payment(supplier_id=sup_id, amount=total, method="فاتورة (متقدمة)", note=f"فاتورة {inv.invoice_no or inv.id}", paid_at=created_at)
            s.add(pay); s.flush()
            try:
                log_action(username, 'create', 'invoice', inv.id, f'no={inv.invoice_no}, net={total}')
                log_action(username, 'create', 'payment', pay.id, f'amount={total}, via=invoice')
            except Exception:
                pass
            s.commit()
        QMessageBox.information(self, "تم", "تم حفظ الفاتورة")
        self.accept()