from __future__ import annotations
from datetime import datetime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QDateEdit, QTabWidget, QFileDialog, QAbstractItemView, QLineEdit
from PySide6.QtGui import QPainter, QTextDocument, QPageSize, QPageLayout
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtCore import QDate, Qt, QMarginsF
from app.data.database import SessionLocal
from app.data.models import Supplier, Delivery, Payment, Item, Factory, FactoryCard, Invoice, InvoiceLine, AuditLog

class ReportsDialog(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # كـ QWidget لأن MainWindow يضيفه كصفحة
        self.setWindowTitle("التقارير")
        self.resize(900, 700)

        self.setLayoutDirection(Qt.RightToLeft)
        tabs = QTabWidget(self)
        # تبويب 1: كشف حساب فلاح
        farmer_tab = QWidget(); fl = QVBoxLayout(farmer_tab)
        # تبويب إضافي: حركة الأصناف
        items_tab = QWidget(); il = QVBoxLayout(items_tab)
        self.items_from = QDateEdit(); self.items_from.setCalendarPopup(True); self.items_from.setDisplayFormat("yyyy-MM-dd"); self.items_from.setDate(QDate.currentDate().addMonths(-1))
        self.items_to = QDateEdit(); self.items_to.setCalendarPopup(True); self.items_to.setDisplayFormat("yyyy-MM-dd"); self.items_to.setDate(QDate.currentDate())
        self.items_search = QLineEdit(); self.items_search.setPlaceholderText("بحث بالاسم/المورد/التفاصيل")
        from PySide6.QtWidgets import QComboBox, QTableWidget, QTableWidgetItem
        self.items_combo = QComboBox(); self._load_items_combo()
        load_items_btn = QPushButton("عرض الحركة"); load_items_btn.setProperty("role", "bottom")
        self.items_table = QTableWidget(0, 7)
        self.items_table.setHorizontalHeaderLabels(["التاريخ", "الحدث", "الصنف", "وارد كمية", "سحب كمية", "سعر/وحدة", "المبلغ"])
        self.items_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        top_items = QHBoxLayout(); top_items.addWidget(QLabel("الصنف:")); top_items.addWidget(self.items_combo)
        top_items.addWidget(QLabel("من:")); top_items.addWidget(self.items_from)
        top_items.addWidget(QLabel("إلى:")); top_items.addWidget(self.items_to)
        top_items.addWidget(self.items_search)
        top_items.addWidget(load_items_btn)
        # طباعة فاتورة برقمها
        self.inv_id_edit = QLineEdit(); self.inv_id_edit.setPlaceholderText("رقم فاتورة")
        inv_print_btn = QPushButton("طباعة فاتورة"); inv_print_btn.setProperty("role", "bottom")
        top_items.addWidget(self.inv_id_edit)
        top_items.addWidget(inv_print_btn)
        il.addLayout(top_items); il.addWidget(self.items_table)
        self.supplier_combo = QComboBox(); self._load_suppliers_deferred = False
        self.date_from = QDateEdit(); self.date_from.setCalendarPopup(True); self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_to = QDateEdit(); self.date_to.setCalendarPopup(True); self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_to.setDate(QDate.currentDate())
        self.search_edit = QLineEdit(); self.search_edit.setPlaceholderText("ابحث بالاسم/النوع")
        self.load_btn = QPushButton("عرض"); self.load_btn.setProperty("role", "bottom")
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["التاريخ", "النوع", "الصنف", "الكمية", "مدين", "دائن"])  # مدين=عليه، دائن=له
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        print_btn = QPushButton("طباعة"); print_btn.setProperty("role", "bottom")
        export_csv_btn = QPushButton("تصدير CSV"); export_csv_btn.setProperty("role", "bottom")
        top = QHBoxLayout();
        top.addWidget(QLabel("الفلاح:")); top.addWidget(self.supplier_combo)
        top.addWidget(QLabel("من:")); top.addWidget(self.date_from)
        top.addWidget(QLabel("إلى:")); top.addWidget(self.date_to)
        top.addWidget(self.search_edit)
        # فلاتر سريعة
        quick_month_btn = QPushButton("هذا الشهر"); quick_month_btn.setProperty("role", "bottom")
        quick_year_btn = QPushButton("العام الحالي"); quick_year_btn.setProperty("role", "bottom")
        quick_month_btn.clicked.connect(self._set_quick_month)
        quick_year_btn.clicked.connect(self._set_quick_year)
        top.addWidget(quick_month_btn); top.addWidget(quick_year_btn)
        top.addWidget(self.load_btn); top.addWidget(print_btn); top.addWidget(export_csv_btn)
        fl.addLayout(top); fl.addWidget(self.table)

        # تبويب 2: كشف حساب مصنع
        factory_tab = QWidget(); fa = QVBoxLayout(factory_tab)
        self.factory_combo = QComboBox(); self._load_factories_deferred = False
        self.load_factories()
        self.f_date_from = QDateEdit(); self.f_date_from.setCalendarPopup(True); self.f_date_from.setDisplayFormat("yyyy-MM-dd")
        self.f_date_to = QDateEdit(); self.f_date_to.setCalendarPopup(True); self.f_date_to.setDisplayFormat("yyyy-MM-dd")
        self.f_date_from.setDate(QDate.currentDate().addMonths(-1))
        self.f_date_to.setDate(QDate.currentDate())
        self.f_search_edit = QLineEdit(); self.f_search_edit.setPlaceholderText("ابحث بالدرجة/النوع")
        self.f_load_btn = QPushButton("عرض")
        self.f_table = QTableWidget(0, 7)
        self.f_table.setHorizontalHeaderLabels(["التاريخ", "النوع", "الدرجة", "الوزن الصافي", "نسبة الخصم %", "سعر اليوم", "الإجمالي"]) 
        # عرض دفعات المصنع ضمن هذا التبويب (ملخص)
        self.f_pay_table = QTableWidget(0, 3)
        self.f_pay_table.setHorizontalHeaderLabels(["التاريخ", "المبلغ", "الطريقة"]) 
        self.f_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.f_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        f_print_btn = QPushButton("طباعة"); f_print_btn.setProperty("role", "bottom")
        f_export_csv_btn = QPushButton("تصدير CSV"); f_export_csv_btn.setProperty("role", "bottom")
        f_top = QHBoxLayout();
        f_top.addWidget(QLabel("المصنع:")); f_top.addWidget(self.factory_combo)
        f_top.addWidget(QLabel("من:")); f_top.addWidget(self.f_date_from)
        f_top.addWidget(QLabel("إلى:")); f_top.addWidget(self.f_date_to)
        f_top.addWidget(self.f_search_edit)
        # فلاتر سريعة
        f_quick_month_btn = QPushButton("هذا الشهر")
        f_quick_year_btn = QPushButton("العام الحالي")
        f_quick_month_btn.clicked.connect(self._set_f_quick_month)
        f_quick_year_btn.clicked.connect(self._set_f_quick_year)
        f_top.addWidget(f_quick_month_btn); f_top.addWidget(f_quick_year_btn)
        f_top.addWidget(self.f_load_btn); f_top.addWidget(f_print_btn); f_top.addWidget(f_export_csv_btn)
        fa.addLayout(f_top); fa.addWidget(self.f_table)
        # قسم دفعات المصنع كملخص
        fa.addWidget(QLabel("دفعات المصنع (ملخص):"))
        fa.addWidget(self.f_pay_table)

        tabs.addTab(farmer_tab, "كشف حساب فلاح")
        tabs.addTab(factory_tab, "كشف حساب مصنع")
        tabs.addTab(items_tab, "حركة الأصناف")
        # تبويب الملخصات
        summary_tab = QWidget(); sl = QVBoxLayout(summary_tab)
        self.sum_from = QDateEdit(); self.sum_from.setCalendarPopup(True); self.sum_from.setDisplayFormat("yyyy-MM-dd"); self.sum_from.setDate(QDate.currentDate().addMonths(-1))
        self.sum_to = QDateEdit(); self.sum_to.setCalendarPopup(True); self.sum_to.setDisplayFormat("yyyy-MM-dd"); self.sum_to.setDate(QDate.currentDate())
        sum_quick_m = QPushButton("هذا الشهر"); sum_quick_y = QPushButton("العام الحالي")
        sum_quick_m.clicked.connect(lambda: self._set_quick_range(self.sum_from, self.sum_to, 'month'))
        sum_quick_y.clicked.connect(lambda: self._set_quick_range(self.sum_from, self.sum_to, 'year'))
        self.sum_btn = QPushButton("عرض الملخص")
        self.sum_table = QTableWidget(0, 4)
        self.sum_table.setHorizontalHeaderLabels(["التاريخ", "إجمالي التوريد", "إجمالي المدفوع", "الصافي"]) 
        self.sum_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        st = QHBoxLayout(); st.addWidget(QLabel("من:")); st.addWidget(self.sum_from); st.addWidget(QLabel("إلى:")); st.addWidget(self.sum_to); st.addWidget(sum_quick_m); st.addWidget(sum_quick_y); st.addWidget(self.sum_btn)
        sl.addLayout(st); sl.addWidget(self.sum_table)
        tabs.addTab(summary_tab, "ملخصات")
        # تبويب سجل العمليات
        audit_tab = QWidget(); al = QVBoxLayout(audit_tab)
        self.audit_from = QDateEdit(); self.audit_from.setCalendarPopup(True); self.audit_from.setDisplayFormat("yyyy-MM-dd"); self.audit_from.setDate(QDate.currentDate().addMonths(-1))
        self.audit_to = QDateEdit(); self.audit_to.setCalendarPopup(True); self.audit_to.setDisplayFormat("yyyy-MM-dd"); self.audit_to.setDate(QDate.currentDate())
        self.audit_user = QLineEdit(); self.audit_user.setPlaceholderText("مستخدم")
        self.audit_entity = QLineEdit(); self.audit_entity.setPlaceholderText("كيان (supplier/payment/...)")
        self.audit_btn = QPushButton("عرض السجل")
        self.audit_table = QTableWidget(0, 6)
        self.audit_table.setHorizontalHeaderLabels(["التاريخ", "المستخدم", "العملية", "الكيان", "رقم", "تفاصيل"]) 
        self.audit_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        at = QHBoxLayout(); at.addWidget(QLabel("من:")); at.addWidget(self.audit_from); at.addWidget(QLabel("إلى:")); at.addWidget(self.audit_to); at.addWidget(self.audit_user); at.addWidget(self.audit_entity); at.addWidget(self.audit_btn)
        al.addLayout(at); al.addWidget(self.audit_table)
        tabs.addTab(audit_tab, "سجل العمليات")

        root = QVBoxLayout(self); root.addWidget(tabs)

        self.load_btn.clicked.connect(self.load_farmer_report)
        self.f_load_btn.clicked.connect(self.load_factory_report)
        print_btn.clicked.connect(lambda: self.print_table(self.table))
        f_print_btn.clicked.connect(lambda: self.print_table(self.f_table))
        export_csv_btn.clicked.connect(lambda: self.export_table_csv(self.table))
        f_export_csv_btn.clicked.connect(lambda: self.export_table_csv(self.f_table))
        # تصدير Excel
        try:
            from openpyxl import Workbook  # تحقق أن الحزمة مثبتة
            self._excel_ok = True
        except Exception:
            self._excel_ok = False
        export_xlsx_btn = QPushButton("تصدير Excel")
        f_export_xlsx_btn = QPushButton("تصدير Excel")
        export_xlsx_btn.clicked.connect(lambda: self.export_table_xlsx(self.table))
        f_export_xlsx_btn.clicked.connect(lambda: self.export_table_xlsx(self.f_table))
        top.addWidget(export_xlsx_btn)
        f_top.addWidget(f_export_xlsx_btn)
        # حركة الأصناف
        load_items_btn.clicked.connect(self.load_items_flow)
        inv_print_btn.clicked.connect(self.print_invoice_by_id)
        # ملخصات
        self.sum_btn.clicked.connect(self.load_summary_tab)
        # سجل العمليات
        self.audit_btn.clicked.connect(self.load_audit_tab)
        self.load_suppliers(); self.load_factories(); self._load_items_combo()

    # مساعد لاختيار المصنع تلقائياً بالاسم من صفحات أخرى
    def set_factory_filter_by_name(self, name: str):
        if not name:
            return
        self.load_factories()
        for i in range(self.factory_combo.count()):
            if self.factory_combo.itemText(i) == name:
                self.factory_combo.setCurrentIndex(i)
                break

    def load_suppliers(self):
        self.supplier_combo.clear()
        with SessionLocal() as s:
            for sup in s.query(Supplier).order_by(Supplier.name).all():
                self.supplier_combo.addItem(sup.name, sup.id)

    def load_factories(self):
        self.factory_combo.clear()
        with SessionLocal() as s:
            for f in s.query(Factory).order_by(Factory.name).all():
                self.factory_combo.addItem(f.name, f.id)

    def _qdate_to_range(self, q_from: QDate, q_to: QDate):
        start = datetime(q_from.year(), q_from.month(), q_from.day(), 0, 0, 0)
        end = datetime(q_to.year(), q_to.month(), q_to.day(), 23, 59, 59)
        return start, end

    def _set_quick_month(self):
        today = QDate.currentDate(); start = QDate(today.year(), today.month(), 1)
        self.date_from.setDate(start); self.date_to.setDate(today)

    def _set_quick_year(self):
        today = QDate.currentDate(); start = QDate(today.year(), 1, 1)
        self.date_from.setDate(start); self.date_to.setDate(today)

    def _set_f_quick_month(self):
        today = QDate.currentDate(); start = QDate(today.year(), today.month(), 1)
        self.f_date_from.setDate(start); self.f_date_to.setDate(today)

    def _set_f_quick_year(self):
        today = QDate.currentDate(); start = QDate(today.year(), 1, 1)
        self.f_date_from.setDate(start); self.f_date_to.setDate(today)

    def _set_quick_range(self, w_from: QDateEdit, w_to: QDateEdit, typ: str):
        today = QDate.currentDate()
        if typ == 'month':
            start = QDate(today.year(), today.month(), 1)
        else:
            start = QDate(today.year(), 1, 1)
        w_from.setDate(start); w_to.setDate(today)

    def load_farmer_report(self):
        self.table.setRowCount(0)
        supplier_id = self.supplier_combo.currentData()
        start, end = self._qdate_to_range(self.date_from.date(), self.date_to.date())
        q = (self.search_edit.text() or '').strip().lower()
        rows = []
        opening_debit = 0.0
        opening_credit = 0.0
        with SessionLocal() as s:
            # رصيد افتتاحي قبل الفترة
            od = s.query(Delivery).filter(Delivery.supplier_id == supplier_id, Delivery.delivered_at < start).all()
            op = s.query(Payment).filter(Payment.supplier_id == supplier_id, Payment.paid_at < start).all()
            opening_debit = sum(d.total_price for d in od)
            opening_credit = sum(p.amount for p in op)
            # حركات الفترة
            deliveries = (
                s.query(Delivery)
                 .filter(Delivery.supplier_id == supplier_id)
                 .filter(Delivery.delivered_at >= start, Delivery.delivered_at <= end)
                 .all()
            )
            for d in deliveries:
                item = s.get(Item, d.item_id) if d.item_id else None
                item_name = item.name if item else "-"
                if q and (q not in item_name.lower() and q not in 'توريد'):
                    pass
                else:
                    rows.append((d.delivered_at, "توريد", item_name, f"{d.quantity} {d.unit}", d.total_price, 0.0))
            payments = (
                s.query(Payment)
                 .filter(Payment.supplier_id == supplier_id)
                 .filter(Payment.paid_at >= start, Payment.paid_at <= end)
                 .all()
            )
            for p in payments:
                if q and (q not in 'دفع'):
                    continue
                rows.append((p.paid_at, "دفع", "-", "-", 0.0, p.amount))
        rows.sort(key=lambda x: x[0])
        # صف رصيد افتتاحي
        opening_balance = opening_debit - opening_credit
        if opening_balance != 0:
            if opening_balance > 0:
                self._append_row(self.table, [str(start.date()), "رصيد افتتاحي", "", "", f"{opening_balance:.2f}", "0.00"])
            else:
                self._append_row(self.table, [str(start.date()), "رصيد افتتاحي", "", "", "0.00", f"{abs(opening_balance):.2f}"])
        # حركات
        total_debit = 0.0
        total_credit = 0.0
        for r in rows:
            dt, typ, item_name, qty, debit, credit = r
            total_debit += float(debit)
            total_credit += float(credit)
            self._append_row(self.table, [str(dt.date()), typ, item_name, qty, f"{debit:.2f}", f"{credit:.2f}"])
        # ملخص أسفل الجدول
        period_balance = total_debit - total_credit
        closing_balance = opening_balance + period_balance
        self._append_row(self.table, ["", "إجمالي الفترة", "", "", f"{total_debit:.2f}", f"{total_credit:.2f}"])
        if closing_balance >= 0:
            self._append_row(self.table, ["", "رصيد ختامي", "", "", f"{closing_balance:.2f}", "0.00"])
        else:
            self._append_row(self.table, ["", "رصيد ختامي", "", "", "0.00", f"{abs(closing_balance):.2f}"])

    def load_factory_report(self):
        self.f_table.setRowCount(0)
        self.f_pay_table.setRowCount(0)
        fid = self.factory_combo.currentData()
        start, end = self._qdate_to_range(self.f_date_from.date(), self.f_date_to.date())
        q = (self.f_search_edit.text() or '').strip().lower()
        rows = []
        from app.data.models import FactoryPayment
        with SessionLocal() as s:
            cards = (
                s.query(FactoryCard)
                 .filter(FactoryCard.factory_id == fid)
                 .filter(FactoryCard.created_at >= start, FactoryCard.created_at <= end)
                 .all()
            )
            for c in cards:
                typ = "كارتة"
                grade = (c.grade or '-').lower()
                if q and (q not in typ and q not in grade):
                    continue
                rows.append((c.created_at, "كارتة", c.grade or '-', f"{c.net_weight:.2f}", f"{c.discount_percent:.2f}", f"{c.price_today:.2f}", f"{c.total_amount:.2f}"))
            pays = (
                s.query(FactoryPayment)
                 .filter(FactoryPayment.factory_id == fid)
                 .filter(FactoryPayment.paid_at >= start, FactoryPayment.paid_at <= end)
                 .all()
            )
        rows.sort(key=lambda x: x[0])
        total = sum(float(r[6]) for r in rows) if rows else 0.0
        # عرض الكروت
        for r in rows:
            self._append_row(self.f_table, [str(r[0].date()), r[1], r[2], r[3], r[4], r[5], r[6]])
        # ملخص أسفل الجدول
        self._append_row(self.f_table, ["", "الإجمالي", "", "", "", "", f"{total:.2f}"])
        # عرض الدفعات
        pay_total = 0.0
        for p in pays:
            pay_total += float(p.amount)
            self._append_row(self.f_pay_table, [p.paid_at.strftime('%Y-%m-%d'), f"{p.amount:.2f}", p.method or '-'])
        # صف إجمالي الدفعات
        self._append_row(self.f_pay_table, ["الإجمالي", f"{pay_total:.2f}", ""])

    def _append_row(self, table: QTableWidget, values):
        row = table.rowCount(); table.insertRow(row)
        for col, val in enumerate(values):
            table.setItem(row, col, QTableWidgetItem(val))

    def load_summary_tab(self):
        from collections import defaultdict
        self.sum_table.setRowCount(0)
        start, end = self._qdate_to_range(self.sum_from.date(), self.sum_to.date())
        daily_in = defaultdict(float)
        daily_pay = defaultdict(float)
        with SessionLocal() as s:
            for d in s.query(Delivery).filter(Delivery.delivered_at>=start, Delivery.delivered_at<=end).all():
                k = d.delivered_at.date().isoformat()
                daily_in[k] += float(d.total_price)
            for p in s.query(Payment).filter(Payment.paid_at>=start, Payment.paid_at<=end).all():
                k = p.paid_at.date().isoformat()
                daily_pay[k] += float(p.amount)
        days = sorted(set(list(daily_in.keys()) + list(daily_pay.keys())))
        for day in days:
            tin = daily_in.get(day, 0.0)
            tpay = daily_pay.get(day, 0.0)
            net = tin - tpay
            self._append_row(self.sum_table, [day, f"{tin:.2f}", f"{tpay:.2f}", f"{net:.2f}"])

    def _load_items_combo(self):
        self.items_combo.clear()
        with SessionLocal() as s:
            for it in s.query(Item).order_by(Item.name).all():
                self.items_combo.addItem(it.name, it.id)

    def load_items_flow(self):
        from datetime import datetime
        self.items_table.setRowCount(0)
        item_id = self.items_combo.currentData()
        q = (self.items_search.text() or '').strip().lower()
        start = datetime(self.items_from.date().year(), self.items_from.date().month(), self.items_from.date().day(), 0, 0, 0)
        end = datetime(self.items_to.date().year(), self.items_to.date().month(), self.items_to.date().day(), 23, 59, 59)
        rows = []
        with SessionLocal() as s:
            # وارد (توريدات)
            for d in s.query(Delivery).filter(Delivery.item_id==item_id).filter(Delivery.delivered_at>=start, Delivery.delivered_at<=end).all():
                it = s.get(Item, d.item_id); name = it.name if it else '-'
                if q and (q not in name.lower()):
                    continue
                rows.append((d.delivered_at, 'وارد', name, f"{d.quantity}", "", f"{d.price_per_unit:.2f}", f"{d.total_price:.2f}"))
            # سحب (فواتير)
            for l in s.query(InvoiceLine).filter(InvoiceLine.item_id==item_id).all():
                inv = s.get(Invoice, l.invoice_id)
                if not inv or not (start <= inv.created_at <= end):
                    continue
                it = s.get(Item, l.item_id); name = it.name if it else '-'
                if q and (q not in name.lower()):
                    continue
                rows.append((inv.created_at, 'سحب', name, "", f"{l.quantity}", f"{l.unit_price:.2f}", f"{l.line_total:.2f}"))
        rows.sort(key=lambda x: x[0])
        total_in = 0.0; total_out = 0.0; total_amount = 0.0
        for r in rows:
            dt, typ, name, qin, qout, unit_price, amount = r
            if qin:
                total_in += float(qin)
            if qout:
                total_out += float(qout)
            total_amount += float(amount)
            self._append_row(self.items_table, [str(dt.date()), typ, name, qin, qout, unit_price, amount])
        # ملخص
        self._append_row(self.items_table, ["", "إجمالي", "", f"{total_in:.2f}", f"{total_out:.2f}", "", f"{total_amount:.2f}"])

    def load_audit_tab(self):
        from datetime import datetime
        self.audit_table.setRowCount(0)
        start = datetime(self.audit_from.date().year(), self.audit_from.date().month(), self.audit_from.date().day(), 0,0,0)
        end = datetime(self.audit_to.date().year(), self.audit_to.date().month(), self.audit_to.date().day(), 23,59,59)
        u = (self.audit_user.text() or '').strip().lower()
        e = (self.audit_entity.text() or '').strip().lower()
        with SessionLocal() as s:
            logs = s.query(AuditLog).filter(AuditLog.created_at>=start, AuditLog.created_at<=end).order_by(AuditLog.created_at.asc()).all()
            for lg in logs:
                if u and (u not in (lg.username or '').lower()):
                    continue
                if e and (e not in (lg.entity or '').lower()):
                    continue
                self._append_row(self.audit_table, [str(lg.created_at.date()), lg.username or '-', lg.action, lg.entity, str(lg.entity_id or ''), lg.details or '-'])

    # طباعة حقيقية عبر QPrinter
    def print_table(self, table: QTableWidget):
        # طباعة فعلية عبر نافذة الطباعة الافتراضية
        printer = QPrinter(QPrinter.HighResolution)
        dlg = QPrintDialog(printer, self)
        if dlg.exec() != QPrintDialog.Accepted:
            return
        # إعدادات الطباعة والشركة
        company = self._get_company_name(); address = self._get_company_address(); logo = self._get_logo_path()
        paper, margins_mm, font_pt = self._get_print_settings()
        # تطبيق إعداد حجم الصفحة
        from PySide6.QtGui import QPageSize, QPageLayout
        if paper == 'A5':
            printer.setPageSize(QPageSize(QPageSize.A5))
        else:
            printer.setPageSize(QPageSize(QPageSize.A4))
        # تطبيق الهوامش
        try:
            top, right, bottom, left = margins_mm
            printer.setPageMargins(QMarginsF(left, top, right, bottom), QPageLayout.Millimeter)
        except Exception:
            pass
        # توليد HTML للطباعة
        headers = [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())]
        html = [f"<html><head><meta charset='utf-8'><style>body{{font-family:Arial; font-size:{font_pt}px;}} h2{{margin:0 0 8px 0;}} .head{{margin-bottom:10px; color:#111}} table{{font-size:{max(10, font_pt-2)}px;}} th{{background:#f3f4f6}}</style></head><body>"]
        # ترويسة
        head_parts = []
        if logo:
            head_parts.append(f"<img src='{logo}' height='48' style='vertical-align:middle;margin-left:12px' />")
        if company:
            head_parts.append(f"<span style='font-weight:700;font-size:{font_pt+2}px'>{company}</span>")
        if address:
            head_parts.append(f"<div style='color:#555'>{address}</div>")
        if head_parts:
            html.append(f"<div class='head'>{''.join(head_parts)}</div>")
        html.append("<table border='1' cellspacing='0' cellpadding='4' style='border-collapse:collapse;width:100%;'>")
        ths = ''.join([f"<th>{h}</th>" for h in headers])
        html.append(f"<tr>{ths}</tr>")
        for r in range(table.rowCount()):
            tds = []
            for c in range(table.columnCount()):
                it = table.item(r, c)
                tds.append(f"<td>{(it.text() if it else '')}</td>")
            html.append(f"<tr>{''.join(tds)}</tr>")
        html.append("</table></body></html>")
        doc = QTextDocument("".join(html))
        doc.print_(printer)

    def print_invoice_by_id(self):
        from PySide6.QtWidgets import QMessageBox
        try:
            inv_id = int(self.inv_id_edit.text().strip())
        except Exception:
            QMessageBox.warning(self, "تنبيه", "أدخل رقم فاتورة صحيح"); return
        with SessionLocal() as s:
            inv = s.get(Invoice, inv_id)
            if not inv:
                QMessageBox.warning(self, "غير موجود", "رقم الفاتورة غير موجود"); return
            lines = s.query(InvoiceLine).filter(InvoiceLine.invoice_id == inv_id).all()
        # بناء مستند بسيط للطباعة
        html = [
            f"<h2 style='text-align:center'>فاتورة #{inv_id}</h2>",
            f"<p>التاريخ: {inv.created_at.date()}</p>",
            f"<p>الفلاح: {self._supplier_name(inv.supplier_id)}</p>",
            "<table border='1' cellspacing='0' cellpadding='4' width='100%'>",
            "<tr><th>الصنف</th><th>الوصف</th><th>الكمية</th><th>السعر</th><th>خصم%</th><th>إجمالي</th></tr>",
        ]
        total = 0.0
        with SessionLocal() as s:
            for ln in lines:
                item_name = s.get(Item, ln.item_id).name if ln.item_id else '-'
                html.append(f"<tr><td>{item_name}</td><td>{ln.description or ''}</td><td>{ln.quantity}</td><td>{ln.unit_price:.2f}</td><td>{ln.discount or 0:.2f}</td><td>{ln.line_total:.2f}</td></tr>")
                total += float(ln.line_total or 0)
        html.append(f"</table><h3 style='text-align:right'>الإجمالي: {total:.2f}</h3>")
        doc = QTextDocument(); doc.setHtml("".join(html))
        # طباعة فعلية عبر نافذة الطباعة
        printer = QPrinter(QPrinter.HighResolution)
        dlg = QPrintDialog(printer, self)
        if dlg.exec() != QPrintDialog.Accepted:
            return
        doc.print_(printer)

    def _supplier_name(self, sup_id: int) -> str:
        with SessionLocal() as s:
            sup = s.get(Supplier, sup_id)
            return sup.name if sup else "-"

        # توليد HTML بسيط من جدول مع شعار/عنوان الشركة لو متاح من الإعدادات
        company = self._get_company_name()
        headers = [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())]
        html = ["<html><head><meta charset='utf-8'><style>body{font-family:Arial;} h2{margin:0 0 8px 0;} .head{margin-bottom:10px; color:#111} table{font-size:12px;} th{background:#f3f4f6}</style></head><body>"]
        if company:
            html.append(f"<div class='head'><h2>{company}</h2></div>")
        html.append("<table border='1' cellspacing='0' cellpadding='4' style='border-collapse:collapse;width:100%;'>")
        ths = ''.join([f"<th>{h}</th>" for h in headers])
        html.append(f"<tr>{ths}</tr>")
        for r in range(table.rowCount()):
            tds = []
            for c in range(table.columnCount()):
                it = table.item(r, c)
                tds.append(f"<td>{(it.text() if it else '')}</td>")
            html.append(f"<tr>{''.join(tds)}</tr>")
        html.append("</table></body></html>")
        doc = QTextDocument("".join(html))
        doc.print_(printer)

    def export_table_csv(self, table: QTableWidget):
        path, _ = QFileDialog.getSaveFileName(self, "حفظ CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        import csv
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            headers = [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())]
            writer.writerow(headers)
            for r in range(table.rowCount()):
                row = []
                for c in range(table.columnCount()):
                    it = table.item(r, c)
                    row.append(it.text() if it else '')
                writer.writerow(row)

    def export_table_xlsx(self, table: QTableWidget):
        if not getattr(self, '_excel_ok', False):
            QFileDialog.getSaveFileName(self, "تأكد من تنصيب openpyxl أولاً", "", "")
            return
        path, _ = QFileDialog.getSaveFileName(self, "حفظ Excel", "", "Excel Files (*.xlsx)")
        if not path:
            return
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active
        # headers
        headers = [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())]
        ws.append(headers)
        # rows
        for r in range(table.rowCount()):
            row = []
            for c in range(table.columnCount()):
                it = table.item(r, c)
                row.append(it.text() if it else '')
            ws.append(row)
        wb.save(path)

    def _get_company_name(self) -> str | None:
        try:
            from app.data.database import get_setting
            return get_setting('company_name') or None
        except Exception:
            return None

    def _get_company_address(self) -> str | None:
        try:
            from app.data.database import get_setting
            return get_setting('company_address') or None
        except Exception:
            return None

    def _get_logo_path(self) -> str | None:
        try:
            from app.data.database import get_setting
            return get_setting('company_logo') or None
        except Exception:
            return None

    def _get_print_settings(self):
        try:
            from app.data.database import get_setting
            paper = get_setting('print_paper') or 'A4'
            mm = (get_setting('print_margins_mm') or '15,10,10,10').split(',')
            margins = tuple(float(x) for x in mm[:4]) if len(mm) >= 4 else (15.0,10.0,10.0,10.0)
            font_pt = int(get_setting('print_font_pt') or '12')
            return paper, margins, font_pt
        except Exception:
            return 'A4', (15.0,10.0,10.0,10.0), 12