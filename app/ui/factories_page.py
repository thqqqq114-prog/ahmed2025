from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QTabWidget, QMessageBox
from app.ui.toast import show_toast
from PySide6.QtCore import Qt
from app.data.database import SessionLocal
from app.data.models import Factory, FactoryCard

class FactoriesPage(QWidget):
    """إدارة المصانع + تبويب تسجيل كارتة + تقارير"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("FactoriesPage")

        self.setLayoutDirection(Qt.RightToLeft)
        tabs = QTabWidget(self)

        # تبويب 1: إدارة المصانع (إضافة/حذف/تعديل مبسط)
        crud_w = QWidget(); crud_l = QVBoxLayout(crud_w)
        self.name_edit = QLineEdit(); self.name_edit.setPlaceholderText("اسم المصنع")
        self.notes_edit = QLineEdit(); self.notes_edit.setPlaceholderText("ملاحظات")
        self.btn_factory_add = QPushButton("إضافة/تعديل"); self.btn_factory_add.setProperty("role", "bottom"); self.btn_factory_del = QPushButton("حذف"); self.btn_factory_del.setProperty("role", "bottom")
        crud_l.addLayout(self.row("الاسم:", self.name_edit))
        crud_l.addLayout(self.row("ملاحظات:", self.notes_edit))
        btns = QHBoxLayout(); btns.addWidget(self.btn_factory_add); btns.addWidget(self.btn_factory_del); crud_l.addLayout(btns)
        # بحث وترقيم
        self.fac_search = QLineEdit(); self.fac_search.setPlaceholderText("ابحث بالاسم")
        nav_l = QHBoxLayout(); self.fac_prev = QPushButton("السابق"); self.fac_next = QPushButton("التالي")
        nav_l.addWidget(self.fac_prev); nav_l.addWidget(self.fac_next)
        self.list_factories = QListWidget();
        crud_l.addWidget(self.fac_search); crud_l.addWidget(self.list_factories); crud_l.addLayout(nav_l)

        self.btn_factory_add.clicked.connect(self.add_or_update)
        self.btn_factory_del.clicked.connect(self.delete_factory)
        self.list_factories.itemClicked.connect(self._fill_from_selected)
        self.fac_page = 1; self.fac_page_size = 20
        self.fac_search.textChanged.connect(lambda *_: self._fac_reload(reset_page=True))
        self.fac_prev.clicked.connect(lambda *_: self._fac_change_page(-1))
        self.fac_next.clicked.connect(lambda *_: self._fac_change_page(1))

        # تبويب 2: تسجيل كارتة
        card_w = QWidget(); card_l = QVBoxLayout(card_w)
        # قائمة منسدلة للمصانع بدل الإدخال النصي
        from PySide6.QtWidgets import QComboBox
        self.card_factory_combo = QComboBox()
        self._load_factories_into_combo(self.card_factory_combo)
        self.card_grade = QLineEdit(); self.card_grade.setPlaceholderText("درجة")
        self.card_gross = QLineEdit(); self.card_gross.setPlaceholderText("الوزن")
        self.card_disc = QLineEdit(); self.card_disc.setPlaceholderText("نسبة الخصم %")
        self.card_net = QLineEdit(); self.card_net.setPlaceholderText("الوزن الصافي")
        self.card_price = QLineEdit(); self.card_price.setPlaceholderText("سعر اليوم")
        self.card_total = QLineEdit(); self.card_total.setPlaceholderText("الإجمالي")
        from PySide6.QtWidgets import QDateEdit
        self.card_date = QDateEdit(); self.card_date.setCalendarPopup(True); self.card_date.setDisplayFormat("yyyy-MM-dd")
        self.card_date.setDate(self._today())
        # حساب تلقائي بسيط: net = gross - (gross*disc/100), total = net * price
        self.btn_calc_card = QPushButton("حساب تلقائي"); self.btn_calc_card.setProperty("role", "bottom")
        self.btn_save_card = QPushButton("حفظ الكارتة"); self.btn_save_card.setProperty("role", "bottom")
        card_l.addLayout(self.row("المصنع:", self.card_factory_combo))
        card_l.addLayout(self.row("درجة:", self.card_grade))
        card_l.addLayout(self.row("الوزن:", self.card_gross))
        card_l.addLayout(self.row("نسبة الخصم %:", self.card_disc))
        card_l.addLayout(self.row("الوزن الصافي:", self.card_net))
        card_l.addLayout(self.row("سعر اليوم:", self.card_price))
        card_l.addLayout(self.row("الإجمالي:", self.card_total))
        card_l.addLayout(self.row("التاريخ:", self.card_date))
        btn2 = QHBoxLayout(); btn2.addWidget(self.btn_calc_card); btn2.addWidget(self.btn_save_card); card_l.addLayout(btn2)
        self.btn_calc_card.clicked.connect(self._calc_card)
        self.btn_save_card.clicked.connect(self._save_card)

        # تبويب 3: دفعات الرصيد للمصنع
        payments_w = QWidget(); payments_l = QVBoxLayout(payments_w)
        from PySide6.QtWidgets import QComboBox, QDateEdit
        self.pay_factory_combo = QComboBox(); self._load_factories_into_combo(self.pay_factory_combo)
        self.pay_amount = QLineEdit(); self.pay_amount.setPlaceholderText("المبلغ")
        self.pay_method = QLineEdit(); self.pay_method.setPlaceholderText("طريقة الاستلام (نقدي/تحويل/شيك)")
        self.pay_note = QLineEdit(); self.pay_note.setPlaceholderText("ملاحظة")
        self.pay_date = QDateEdit(); self.pay_date.setCalendarPopup(True)
        self.pay_date.setDisplayFormat("yyyy-MM-dd"); self.pay_date.setDate(self._today())
        add_payment_btn = QPushButton("إضافة الدفعة"); add_payment_btn.setProperty("role", "bottom")
        del_payment_btn = QPushButton("حذف الدفعة المحددة"); del_payment_btn.setProperty("role", "bottom")
        payments_l.addLayout(self.row("المصنع:", self.pay_factory_combo))
        payments_l.addLayout(self.row("المبلغ:", self.pay_amount))
        payments_l.addLayout(self.row("الطريقة:", self.pay_method))
        payments_l.addLayout(self.row("ملاحظة:", self.pay_note))
        payments_l.addLayout(self.row("التاريخ:", self.pay_date))
        btnp = QHBoxLayout(); btnp.addWidget(add_payment_btn); btnp.addWidget(del_payment_btn); payments_l.addLayout(btnp)
        # جدول الدفعات
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
        self.pay_table = QTableWidget(0, 5)
        self.pay_table.setHorizontalHeaderLabels(["#", "التاريخ", "المبلغ", "الطريقة", "ملاحظة"])
        payments_l.addWidget(self.pay_table)
        add_payment_btn.clicked.connect(self._add_factory_payment)
        del_payment_btn.clicked.connect(self._delete_factory_payment)
        try:
            self.pay_factory_combo.currentIndexChanged.connect(lambda *_: self._load_payments())
        except Exception:
            pass

        # تبويب 4: تقارير (كشف حساب المصنع)
        reports_w = QWidget(); reports_l = QVBoxLayout(reports_w)
        from PySide6.QtWidgets import QComboBox
        self.report_factory_combo = QComboBox(); self._load_factories_into_combo(self.report_factory_combo)
        show_report_btn = QPushButton("عرض كشف الحساب"); show_report_btn.setProperty("role", "bottom")
        reports_l.addLayout(self.row("المصنع:", self.report_factory_combo))
        reports_l.addWidget(show_report_btn)
        show_report_btn.clicked.connect(self._open_factory_report)

        tabs.addTab(crud_w, "إدارة المصانع")
        tabs.addTab(card_w, "تسجيل كارتة")
        tabs.addTab(payments_w, "دفعات المصنع")
        tabs.addTab(reports_w, "كشف حساب مصنع")

        root = QVBoxLayout(self); root.addWidget(tabs)
        self.refresh_list()

    def row(self, label, widget):
        h = QHBoxLayout(); h.addWidget(QLabel(label)); h.addWidget(widget); return h

    def _today(self):
        from PySide6.QtCore import QDate
        return QDate.currentDate()

    def _load_payments(self):
        self.pay_table.setRowCount(0)
        from app.data.database import SessionLocal
        from app.data.models import FactoryPayment
        fid = self.pay_factory_combo.currentData()
        if fid is None:
            return
        with SessionLocal() as s:
            pays = s.query(FactoryPayment).filter(FactoryPayment.factory_id == fid).order_by(FactoryPayment.paid_at.desc()).all()
            for p in pays:
                row = self.pay_table.rowCount(); self.pay_table.insertRow(row)
                from PySide6.QtWidgets import QTableWidgetItem
                self.pay_table.setItem(row, 0, QTableWidgetItem(str(p.id)))
                self.pay_table.setItem(row, 1, QTableWidgetItem(p.paid_at.strftime('%Y-%m-%d')))
                self.pay_table.setItem(row, 2, QTableWidgetItem(f"{p.amount:.2f}"))
                self.pay_table.setItem(row, 3, QTableWidgetItem(p.method or '-'))
                self.pay_table.setItem(row, 4, QTableWidgetItem(p.note or '-'))

    def _add_factory_payment(self):
        from app.data.database import SessionLocal
        from app.data.models import FactoryPayment
        try:
            fid = self.pay_factory_combo.currentData()
            amt = float(self.pay_amount.text())
            method = self.pay_method.text().strip() or None
            note = self.pay_note.text().strip() or None
            dt = self.pay_date.date()
            from datetime import datetime
            paid_at = datetime(dt.year(), dt.month(), dt.day(), 0, 0, 0)
        except Exception:
            QMessageBox.warning(self, "تنبيه", "تأكد من إدخال القيم بشكل صحيح"); return
        with SessionLocal() as s:
            s.add(FactoryPayment(factory_id=fid, amount=amt, method=method, note=note, paid_at=paid_at))
            s.commit()
        self.pay_amount.clear(); self.pay_method.clear(); self.pay_note.clear(); self._load_payments()
        QMessageBox.information(self, "تم", "تمت إضافة الدفعة")

    def _delete_factory_payment(self):
        row = self.pay_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "تنبيه", "اختر دفعة من الجدول"); return
        pid = self.pay_table.item(row, 0).text()
        from app.data.database import SessionLocal
        from app.data.models import FactoryPayment
        with SessionLocal() as s:
            obj = s.get(FactoryPayment, int(pid))
            if obj:
                s.delete(obj); s.commit(); self._load_payments(); QMessageBox.information(self, "تم", "تم حذف الدفعة")

    def refresh_list(self):
        # إعادة تحميل مع البحث والترقيم
        self._fac_reload(reset_page=False)
        # حدّث القائمة المنسدلة للكارتة
        self._load_factories_into_combo(self.card_factory_combo)

    def _fac_reload(self, reset_page: bool = False):
        if reset_page:
            self.fac_page = 1
        q = (self.fac_search.text() or '').strip().lower()
        with SessionLocal() as s:
            items = []
            for f in s.query(Factory).order_by(Factory.name).all():
                text = f"{f.id} | {f.name} | {f.notes or ''}"
                if q and (q not in (f.name or '').lower()) and (q not in (f.notes or '').lower()):
                    continue
                items.append(text)
        total = len(items)
        start = (self.fac_page - 1) * self.fac_page_size
        end = start + self.fac_page_size
        page_items = items[start:end]
        self.list_factories.clear()
        for t in page_items:
            self.list_factories.addItem(t)
        self.fac_prev.setEnabled(self.fac_page > 1)
        self.fac_next.setEnabled(end < total)

    def _fac_change_page(self, delta: int):
        new_page = max(1, self.fac_page + delta)
        q = (self.fac_search.text() or '').strip().lower()
        with SessionLocal() as s:
            total = 0
            for f in s.query(Factory).all():
                if q and (q not in (f.name or '').lower()) and (q not in (f.notes or '').lower()):
                    continue
                total += 1
        max_page = max(1, (total + self.fac_page_size - 1) // self.fac_page_size)
        self.fac_page = min(new_page, max_page)
        self._fac_reload(reset_page=False)

    def _fill_from_selected(self):
        t = self.list_factories.currentItem().text()
        parts = [p.strip() for p in t.split('|')]
        self.name_edit.setText(parts[1]); self.notes_edit.setText(parts[2])

    def _load_factories_into_combo(self, combo):
        combo.clear()
        with SessionLocal() as s:
            for f in s.query(Factory).order_by(Factory.name).all():
                combo.addItem(f.name, f.id)

    def add_or_update(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "تنبيه", "اسم المصنع مطلوب"); return
        with SessionLocal() as s:
            existing = s.query(Factory).filter(Factory.name == name).one_or_none()
            if existing:
                existing.notes = self.notes_edit.text().strip() or None
            else:
                s.add(Factory(name=name, notes=self.notes_edit.text().strip() or None))
            s.commit(); self.refresh_list(); self.name_edit.clear(); self.notes_edit.clear()
            try:
                show_toast(self, "تم الحفظ")
            except Exception:
                pass

    def delete_factory(self):
        if not self.list_factories.currentItem(): return
        factory_id = int(self.list_factories.currentItem().text().split('|')[0].strip())
        with SessionLocal() as s:
            obj = s.get(Factory, factory_id)
            if obj: s.delete(obj); s.commit(); self.refresh_list()
            try:
                show_toast(self, "تم الحذف")
            except Exception:
                pass

    def _calc_card(self):
        try:
            gross = float(self.card_gross.text() or 0)
            disc = float(self.card_disc.text() or 0)
            price = float(self.card_price.text() or 0)
            net = gross - (gross * disc / 100.0)
            total = net * price
            self.card_net.setText(f"{net:.2f}")
            self.card_total.setText(f"{total:.2f}")
        except ValueError:
            QMessageBox.warning(self, "تنبيه", "تحقق من القيم الرقمية")

    def _save_card(self):
        if self.card_factory_combo.currentIndex() < 0:
            QMessageBox.warning(self, "تنبيه", "اختر المصنع"); return
        fid = self.card_factory_combo.currentData()
        try:
            gross = float(self.card_gross.text()); disc = float(self.card_disc.text() or 0); net = float(self.card_net.text()); price = float(self.card_price.text()); total = float(self.card_total.text())
        except ValueError:
            QMessageBox.warning(self, "تنبيه", "تحقق من القيم الرقمية"); return
        with SessionLocal() as s:
            # تحديد تاريخ الكارتة اليدوي
            dt = self.card_date.date(); from datetime import datetime
            created_at = datetime(dt.year(), dt.month(), dt.day(), 0, 0, 0)
            s.add(FactoryCard(factory_id=fid, grade=self.card_grade.text().strip() or None, gross_weight=gross, discount_percent=disc, net_weight=net, price_today=price, total_amount=total, created_at=created_at))
            s.commit()
            QMessageBox.information(self, "تم", "تم حفظ الكارتة")
            self.card_grade.clear(); self.card_gross.clear(); self.card_disc.clear(); self.card_net.clear(); self.card_price.clear(); self.card_total.clear()

    def _open_factory_report(self):
        # بدلاً من فتح نافذة مستقلة، انتقل لصفحة التقارير المدمجة وحدّد المصنع
        mw = self.window()
        try:
            pr = getattr(mw, 'page_reports', None)
            if pr is None:
                return
            pr.load_factories()
            if self.report_factory_combo.currentIndex() >= 0:
                name = self.report_factory_combo.currentText()
                pr.set_factory_filter_by_name(name)
            pr.load_factory_report()
            if hasattr(mw, '_switch_to'):
                mw._switch_to(pr)
        except Exception:
            pass