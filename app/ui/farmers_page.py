from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QTabWidget, QMessageBox
from app.ui.toast import show_toast
from PySide6.QtCore import Qt
from sqlalchemy.exc import IntegrityError
from app.data.database import SessionLocal
from app.data.models import Supplier, Delivery, Payment

class FarmersPage(QWidget):
    """إدارة الفلاحين: (إضافة/حذف/تعديل) + قائمة + إحصائيات عامة"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("FarmersPage")
        self.setLayoutDirection(Qt.RightToLeft)

        tabs = QTabWidget(self)

        # تبويب 1: إضافة/تعديل/حذف
        crud_w = QWidget(); crud_l = QVBoxLayout(crud_w)
        self.name_edit = QLineEdit(); self.name_edit.setPlaceholderText("اسم الفلاح")
        self.phone_edit = QLineEdit(); self.phone_edit.setPlaceholderText("رقم الهاتف")
        self.address_edit = QLineEdit(); self.address_edit.setPlaceholderText("العنوان")
        self.btn_add = QPushButton("إضافة"); self.btn_add.setProperty("role", "bottom")
        self.btn_upd = QPushButton("تعديل"); self.btn_upd.setProperty("role", "bottom")
        self.btn_del = QPushButton("حذف"); self.btn_del.setProperty("role", "bottom")
        crud_l.addLayout(self.row("الاسم:", self.name_edit))
        crud_l.addLayout(self.row("التليفون:", self.phone_edit))
        crud_l.addLayout(self.row("العنوان:", self.address_edit))
        btns = QHBoxLayout(); btns.addWidget(self.btn_add); btns.addWidget(self.btn_upd); btns.addWidget(self.btn_del)
        crud_l.addLayout(btns)
        self.list_crud = QListWidget(); crud_l.addWidget(self.list_crud)

        self.btn_add.clicked.connect(self.add_farmer)
        self.btn_upd.clicked.connect(self.update_farmer)
        self.btn_del.clicked.connect(self.delete_farmer)
        self.list_crud.itemClicked.connect(self._fill_from_selected)

        # تبويب 2: قائمة الفلاحين + الدخول لحساب كل فلاح (توريد/سحب)
        accounts_w = QWidget(); accounts_l = QVBoxLayout(accounts_w)
        self.acc_search = QLineEdit(); self.acc_search.setPlaceholderText("ابحث بالاسم/الهاتف/العنوان")
        self.list_acc = QListWidget();
        # ترقيم صفحات بسيط
        self.acc_page = 1; self.acc_page_size = 20
        nav_l = QHBoxLayout();
        self.acc_prev = QPushButton("السابق"); self.acc_next = QPushButton("التالي")
        nav_l.addWidget(self.acc_prev); nav_l.addWidget(self.acc_next)
        accounts_l.addWidget(self.acc_search); accounts_l.addWidget(self.list_acc); accounts_l.addLayout(nav_l)
        open_acc_btn = QPushButton("فتح حساب الفلاح")
        accounts_l.addWidget(open_acc_btn)
        open_acc_btn.clicked.connect(self.open_farmer_account)
        self.open_acc_btn = open_acc_btn
        self.acc_search.textChanged.connect(lambda *_: self._acc_reload(reset_page=True))
        self.acc_prev.clicked.connect(lambda *_: self._acc_change_page(-1))
        self.acc_next.clicked.connect(lambda *_: self._acc_change_page(1))

        # تبويب 3: إحصائية عامة للفلاحين
        stats_w = QWidget(); stats_l = QVBoxLayout(stats_w)
        self.stats_label = QLabel("—")
        stats_l.addWidget(self.stats_label)
        refresh_stats_btn = QPushButton("تحديث الإحصائية")
        stats_l.addWidget(refresh_stats_btn)
        refresh_stats_btn.clicked.connect(self.refresh_stats)

        tabs.addTab(crud_w, "إضافة/تعديل/حذف")
        tabs.addTab(accounts_w, "قائمة الفلاحين")
        tabs.addTab(stats_w, "إحصائية عامة")

        root = QVBoxLayout(self); root.addWidget(tabs)
        self.refresh_lists(); self.refresh_stats()

    def row(self, label, widget):
        h = QHBoxLayout(); h.addWidget(QLabel(label)); h.addWidget(widget); return h

    def refresh_lists(self):
        self.list_crud.clear(); self.list_acc.clear()
        with SessionLocal() as s:
            farmers = s.query(Supplier).order_by(Supplier.name).all()
            for f in farmers:
                text = f"{f.id} | {f.name} | {f.phone or ''} | {f.address or ''}"
                self.list_crud.addItem(text)
        # إعادة تحميل القائمة مع البحث والترقيم
        self._acc_reload(reset_page=False)

    def _acc_reload(self, reset_page: bool = False):
        if reset_page:
            self.acc_page = 1
        q = (self.acc_search.text() or '').strip().lower()
        with SessionLocal() as s:
            items = []
            for f in s.query(Supplier).order_by(Supplier.name).all():
                text = f"{f.id} | {f.name} | {f.phone or ''} | {f.address or ''}"
                if q and (q not in (f.name or '').lower()) and (q not in (f.phone or '').lower()) and (q not in (f.address or '').lower()):
                    continue
                items.append(text)
        total = len(items)
        start = (self.acc_page - 1) * self.acc_page_size
        end = start + self.acc_page_size
        page_items = items[start:end]
        self.list_acc.clear()
        for t in page_items:
            self.list_acc.addItem(t)
        # تفعيل/تعطيل أزرار التصفح
        self.acc_prev.setEnabled(self.acc_page > 1)
        self.acc_next.setEnabled(end < total)

    def _acc_change_page(self, delta: int):
        new_page = max(1, self.acc_page + delta)
        # تحقق من عدم تجاوز الصفحات
        q = (self.acc_search.text() or '').strip().lower()
        with SessionLocal() as s:
            total = 0
            for f in s.query(Supplier).all():
                if q and (q not in (f.name or '').lower()) and (q not in (f.phone or '').lower()) and (q not in (f.address or '').lower()):
                    continue
                total += 1
        max_page = max(1, (total + self.acc_page_size - 1) // self.acc_page_size)
        self.acc_page = min(new_page, max_page)
        self._acc_reload(reset_page=False)

    def _fill_from_selected(self):
        if not self.list_crud.currentItem():
            return
        parts = [p.strip() for p in self.list_crud.currentItem().text().split('|')]
        self.name_edit.setText(parts[1]); self.phone_edit.setText(parts[2]); self.address_edit.setText(parts[3])

    def add_farmer(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "تنبيه", "اسم الفلاح مطلوب"); return
        with SessionLocal() as s:
            try:
                s.add(Supplier(name=name, phone=self.phone_edit.text().strip() or None, address=self.address_edit.text().strip() or None))
                s.commit(); self.name_edit.clear(); self.phone_edit.clear(); self.address_edit.clear(); self.refresh_lists()
                try:
                    show_toast(self, "تمت الإضافة")
                except Exception:
                    pass
            except IntegrityError:
                s.rollback(); QMessageBox.warning(self, "خطأ", "الاسم موجود بالفعل")

    def update_farmer(self):
        if not self.list_crud.currentItem(): return
        parts = [p.strip() for p in self.list_crud.currentItem().text().split('|')]
        sup_id = int(parts[0]); name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "تنبيه", "اسم الفلاح مطلوب"); return
        with SessionLocal() as s:
            obj = s.get(Supplier, sup_id)
            if not obj: return
            obj.name = name; obj.phone = self.phone_edit.text().strip() or None; obj.address = self.address_edit.text().strip() or None
            try:
                s.commit(); self.refresh_lists()
                try:
                    show_toast(self, "تم التعديل")
                except Exception:
                    pass
            except IntegrityError:
                s.rollback(); QMessageBox.warning(self, "خطأ", "الاسم موجود بالفعل")

    def delete_farmer(self):
        if not self.list_crud.currentItem(): return
        sup_id = int(self.list_crud.currentItem().text().split('|')[0].strip())
        with SessionLocal() as s:
            obj = s.get(Supplier, sup_id)
            if obj:
                s.delete(obj); s.commit(); self.refresh_lists()

    def open_farmer_account(self):
        if not self.list_acc.currentItem():
            QMessageBox.warning(self, "تنبيه", "اختر فلاح أولاً من القائمة"); return
        # استخراج المعرّف بأمان
        text = self.list_acc.currentItem().text()
        try:
            sup_id = int(text.split('|')[0].strip())
        except Exception:
            QMessageBox.warning(self, "تنبيه", "تعذّر قراءة رقم الفلاح من السطر"); return
        # بدلاً من فتح نافذة مستقلة، انتقل لصفحة التقارير المدمجة وحدّد الفلاح
        mw = self.window()
        try:
            pr = getattr(mw, 'page_reports', None)
            if pr is None:
                return
            pr.load_suppliers()
            for i in range(pr.supplier_combo.count()):
                if pr.supplier_combo.itemData(i) == sup_id:
                    pr.supplier_combo.setCurrentIndex(i)
                    break
            pr.load_farmer_report()
            # بدّل الصفحة الحالية إلى التقارير
            if hasattr(mw, '_switch_to'):
                mw._switch_to(pr)
        except Exception:
            pass

    def refresh_stats(self):
        with SessionLocal() as s:
            # إجمالي التوريد وإجمالي السحب لكل الفلاحين
            total_deliveries = sum(d.total_price for d in s.query(Delivery).all())
            total_payments = sum(p.amount for p in s.query(Payment).all())
            self.stats_label.setText(f"إجمالي التوريد: {total_deliveries:.2f} — إجمالي السحب: {total_payments:.2f}")