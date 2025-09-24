from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFileDialog, QCheckBox
from app.backup import backup_now, backup_all_app, restore_db_from
from app.data.database import SessionLocal, get_setting, set_setting
from app.data.models import User
from app.licensing import LicenseClient, LicenseError
from app.ui.license_dialog import LicenseDialog

class SettingsPage(QWidget):
    """إعدادات المستخدم: رقم الموبايل واسم الشركة + إعدادات عامة"""
    def __init__(self, username: str, parent=None):
        super().__init__(parent)
        self.username = username
        self.setObjectName("SettingsPage")

        self.phone_edit = QLineEdit(); self.phone_edit.setPlaceholderText("رقم الموبايل")
        self.company_edit = QLineEdit(); self.company_edit.setPlaceholderText("اسم الشركة")
        self.address_edit = QLineEdit(); self.address_edit.setPlaceholderText("عنوان الشركة")
        # إعدادات عامة
        self.default_unit_edit = QLineEdit(); self.default_unit_edit.setPlaceholderText("الوحدة الافتراضية للأصناف (kg/bag/ton)")
        from PySide6.QtWidgets import QComboBox
        self.theme_combo = QComboBox(); self.theme_combo.addItem("افتراضي", "default"); self.theme_combo.addItem("احترافي", "pro"); self.theme_combo.addItem("داكن", "dark"); self.theme_combo.addItem("حد أدنى", "minimal"); self.theme_combo.addItem("أخضر", "green")
        self.lock_from_edit = QLineEdit(); self.lock_from_edit.setPlaceholderText("إقفال من تاريخ (YYYY-MM-DD)")
        self.lock_to_edit = QLineEdit(); self.lock_to_edit.setPlaceholderText("إقفال إلى تاريخ (YYYY-MM-DD)")
        self.backup_on_close_cb = QCheckBox("نسخ احتياطي تلقائي عند الإغلاق")
        self.backup_daily_cb = QCheckBox("نسخ احتياطي يومي تلقائي أثناء التشغيل")
        self.advanced_invoice_cb = QCheckBox("تفعيل واجهة الفاتورة المتقدمة")

        # الوضع الافتراضي للفواتير (بسيط/متقدم)
        from PySide6.QtWidgets import QComboBox
        self.invoice_mode_combo = QComboBox(); self.invoice_mode_combo.addItem("بسيط", "simple"); self.invoice_mode_combo.addItem("متقدم", "advanced")
        # ترقيم الفواتير
        self.invoice_format_edit = QLineEdit(); self.invoice_format_edit.setPlaceholderText("صيغة رقم الفاتورة {YYYY}{MM}-{SEQ:04}")
        # إعدادات الطباعة
        self.print_paper_combo = QComboBox(); self.print_paper_combo.addItems(["A4", "A5"]) 
        self.print_margins_edit = QLineEdit(); self.print_margins_edit.setPlaceholderText("هوامش مم: أعلى,يمين,أسفل,يسار — مثال: 15,10,10,10")
        self.print_font_size_edit = QLineEdit(); self.print_font_size_edit.setPlaceholderText("حجم الخط للطباعة (نقطة) مثال: 12")
        # شعار
        self.logo_path_edit = QLineEdit(); self.logo_path_edit.setPlaceholderText("مسار شعار الشركة (اختياري)")
        choose_logo_btn = QPushButton("اختيار شعار")

        save_btn = QPushButton("حفظ"); save_btn.setProperty("role", "bottom")
        backup_btn = QPushButton("تصدير نسخة قاعدة البيانات"); backup_btn.setProperty("role", "bottom")
        backup_all_btn = QPushButton("تصدير نسخة كاملة للبرنامج"); backup_all_btn.setProperty("role", "bottom")
        restore_btn = QPushButton("استرجاع نسخة قاعدة البيانات"); restore_btn.setProperty("role", "bottom")
        import_sup_btn = QPushButton("استيراد الموردين من CSV"); import_sup_btn.setProperty("role", "bottom")
        import_items_btn = QPushButton("استيراد الأصناف من CSV"); import_items_btn.setProperty("role", "bottom")
        # تم إزالة زر التحديث
        self.wipe_btn = QPushButton("تصفير البرنامج — حذف كل البيانات"); self.wipe_btn.setProperty("role", "bottom")
        self.wipe_btn.setStyleSheet("background:#ef4444; color:white; font-weight:bold;")

        layout = QVBoxLayout(self)
        layout.addLayout(self.row("رقم الموبايل:", self.phone_edit))
        layout.addLayout(self.row("اسم الشركة:", self.company_edit))
        layout.addLayout(self.row("عنوان الشركة:", self.address_edit))
        # إعدادات عامة
        layout.addLayout(self.row("الوحدة الافتراضية:", self.default_unit_edit))
        # اختيار الثيم + زر تطبيق الآن
        self.theme_apply_btn = QPushButton("تطبيق الآن")
        theme_container = QWidget()
        h = QHBoxLayout(theme_container)
        h.addWidget(self.theme_combo)
        h.addWidget(self.theme_apply_btn)
        layout.addLayout(self.row("الثيم:", theme_container))
        # ربط التطبيق الفوري
        self.theme_apply_btn.clicked.connect(self.apply_theme_now)
        try:
            self.theme_combo.currentIndexChanged.connect(self.apply_theme_now)
        except Exception:
            pass
        layout.addLayout(self.row("إقفال من:", self.lock_from_edit))
        layout.addLayout(self.row("إقفال إلى:", self.lock_to_edit))
        layout.addWidget(self.backup_on_close_cb)
        layout.addWidget(self.backup_daily_cb)
        layout.addWidget(self.advanced_invoice_cb)

        layout.addLayout(self.row("وضع الفاتورة الافتراضي:", self.invoice_mode_combo))
        layout.addLayout(self.row("صيغة رقم الفاتورة:", self.invoice_format_edit))
        # إعدادات الطباعة
        layout.addLayout(self.row("حجم الورق للطباعة:", self.print_paper_combo))
        layout.addLayout(self.row("هوامش الطباعة (مم):", self.print_margins_edit))
        layout.addLayout(self.row("حجم خط الطباعة:", self.print_font_size_edit))
        # شعار
        logo_row = QHBoxLayout(); logo_row.addWidget(self.logo_path_edit); logo_row.addWidget(choose_logo_btn)
        layout.addLayout(self.row("شعار الشركة:", QWidget()))
        layout.addLayout(logo_row)

        # ===== قسم إدارة الترخيص =====
        self.api_base_edit = QLineEdit(); self.api_base_edit.setPlaceholderText("https://ahmedhussein.online")
        self.license_status_label = QLabel("—")
        self.license_verify_btn = QPushButton("تحقق من الترخيص")
        self.license_activate_btn = QPushButton("تفعيل/تغيير الترخيص")
        self.license_deactivate_btn = QPushButton("إلغاء الترخيص")

        layout.addLayout(self.row("License API Base:", self.api_base_edit))
        layout.addLayout(self.row("الحالة:", self.license_status_label))
        lic_btns = QHBoxLayout(); lic_btns.addWidget(self.license_verify_btn); lic_btns.addWidget(self.license_activate_btn); lic_btns.addWidget(self.license_deactivate_btn)
        layout.addLayout(lic_btns)

        # شريط أزرار سفلي مُنظّم وصغير الحجم
        btn_bar = QHBoxLayout()
        for b in (save_btn, backup_btn, backup_all_btn, restore_btn, import_sup_btn, import_items_btn, self.wipe_btn):
            b.setMinimumHeight(34)
            b.setStyleSheet("padding:6px 10px; border-radius:6px;")
            btn_bar.addWidget(b)
        layout.addLayout(btn_bar)

        save_btn.clicked.connect(self.save)
        backup_btn.clicked.connect(self.export_backup)
        backup_all_btn.clicked.connect(self.export_backup_all)
        restore_btn.clicked.connect(self.import_backup)
        import_sup_btn.clicked.connect(self.import_suppliers_csv)
        import_items_btn.clicked.connect(self.import_items_csv)
        choose_logo_btn.clicked.connect(self.choose_logo)
        self.wipe_btn.clicked.connect(self.wipe_all_data)

        # ترخيص: ربط الأزرار
        self.license_verify_btn.clicked.connect(self.license_verify)
        self.license_activate_btn.clicked.connect(self.license_activate)
        self.license_deactivate_btn.clicked.connect(self.license_deactivate)

        # إظهار زر التصفير للأدمن فقط
        try:
            mw = self.window()
            is_admin = getattr(mw, 'role', 'admin') == 'admin'
            self.wipe_btn.setVisible(is_admin)
        except Exception:
            self.wipe_btn.setVisible(False)

        self.load()

    def wipe_all_data(self):
        from PySide6.QtWidgets import QMessageBox
        from app.data.database import reset_database
        # تحقق من صلاحيات الأدمن
        try:
            mw = self.window()
            if getattr(mw, 'role', '') != 'admin':
                QMessageBox.warning(self, "تنبيه", "هذه العملية تتطلب صلاحية الأدمن")
                return
        except Exception:
            QMessageBox.warning(self, "تنبيه", "تعذر التحقق من الصلاحيات")
            return
        # تحذير مزدوج
        r1 = QMessageBox.warning(self, "تحذير شديد", "سيتم حذف جميع البيانات نهائياً ولا يمكن استرجاعها إلا من نسخة احتياطية. هل تريد المتابعة؟", QMessageBox.Yes | QMessageBox.No)
        if r1 != QMessageBox.Yes:
            return
        r2 = QMessageBox.warning(self, "تأكيد نهائي", "هذه العملية خطيرة جداً. تأكيد أخير للتصفير؟", QMessageBox.Yes | QMessageBox.No)
        if r2 != QMessageBox.Yes:
            return
        # محاولة أخذ نسخة احتياطية قبل التصفير
        try:
            path = backup_now()
            QMessageBox.information(self, "نسخة احتياطية", f"تم إنشاء نسخة قبل التصفير: {path}")
        except Exception:
            pass
        try:
            reset_database()
            QMessageBox.information(self, "تم", "تم تصفير البرنامج بنجاح. يُفضل إعادة التشغيل.")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", str(e))

    def row(self, label, widget):
        h = QHBoxLayout(); h.addWidget(QLabel(label)); h.addWidget(widget); return h

    def load(self):
        with SessionLocal() as s:
            u = s.query(User).filter(User.username == self.username).one_or_none()
            if u:
                if u.phone: self.phone_edit.setText(u.phone)
                if u.company: self.company_edit.setText(u.company)
                # قد نخزن العنوان مستقبلًا في جدول المستخدم
        # تحميل الإعدادات العامة
        try:
            self.default_unit_edit.setText(get_setting('default_unit') or '')
            theme = (get_setting('theme') or 'default')
            idx = max(0, self.theme_combo.findData(theme))
            self.theme_combo.setCurrentIndex(idx)
            self.lock_from_edit.setText(get_setting('lock_from') or '')
            self.lock_to_edit.setText(get_setting('lock_to') or '')
            self.backup_on_close_cb.setChecked((get_setting('backup_on_close') or '0') == '1')
            self.backup_daily_cb.setChecked((get_setting('backup_daily') or '0') == '1')
            self.advanced_invoice_cb.setChecked((get_setting('advanced_invoice_ui') or '0') == '1')

            mode = (get_setting('invoice_default_mode') or 'simple')
            idx = 0 if mode == 'simple' else 1
            self.invoice_mode_combo.setCurrentIndex(idx)
            self.invoice_format_edit.setText(get_setting('invoice_format') or '{YYYY}{MM}-{SEQ:04}')
            # إعدادات الطباعة
            paper = get_setting('print_paper') or 'A4'
            self.print_paper_combo.setCurrentIndex(0 if paper=='A4' else 1)
            self.print_margins_edit.setText(get_setting('print_margins_mm') or '15,10,10,10')
            self.print_font_size_edit.setText(get_setting('print_font_pt') or '12')
            self.logo_path_edit.setText(get_setting('company_logo') or '')
            self.address_edit.setText(get_setting('company_address') or '')

            # ترخيص: تحميل api_base وحالة التوكن
            api_base = get_setting('api_base') or ''
            self.api_base_edit.setText(api_base)
            token = get_setting('license_token')
            status = "صالح" if LicenseClient(api_base or None).verify_token(token) else "غير صالح"
            self.license_status_label.setText(status)
        except Exception:
            pass

    def save(self):
        with SessionLocal() as s:
            u = s.query(User).filter(User.username == self.username).one_or_none()
            if not u:
                QMessageBox.warning(self, "خطأ", "المستخدم غير موجود"); return
            u.phone = self.phone_edit.text().strip() or None
            u.company = self.company_edit.text().strip() or None
            s.commit()
        # حفظ الإعدادات العامة
        try:
            set_setting('company_name', self.company_edit.text().strip() or None)
            set_setting('default_unit', self.default_unit_edit.text().strip() or None)
            set_setting('theme', self.theme_combo.currentData())
            set_setting('lock_from', self.lock_from_edit.text().strip() or None)
            set_setting('lock_to', self.lock_to_edit.text().strip() or None)
            set_setting('backup_on_close', '1' if self.backup_on_close_cb.isChecked() else '0')
            set_setting('backup_daily', '1' if self.backup_daily_cb.isChecked() else '0')
            set_setting('advanced_invoice_ui', '1' if self.advanced_invoice_cb.isChecked() else '0')

            # حفظ وضع الفاتورة الافتراضي
            mode = self.invoice_mode_combo.currentData()
            set_setting('invoice_default_mode', mode)
            # ترقيم الفواتير
            set_setting('invoice_format', self.invoice_format_edit.text().strip() or '{YYYY}{MM}-{SEQ:04}')
            # إعدادات الطباعة
            set_setting('print_paper', self.print_paper_combo.currentText())
            set_setting('print_margins_mm', self.print_margins_edit.text().strip() or '15,10,10,10')
            set_setting('print_font_pt', self.print_font_size_edit.text().strip() or '12')
            set_setting('company_logo', self.logo_path_edit.text().strip() or None)
            set_setting('company_address', self.address_edit.text().strip() or None)

            # حفظ إعدادات الترخيص
            api_base = self.api_base_edit.text().strip() or None
            set_setting('api_base', api_base)

            QMessageBox.information(self, "تم", "تم الحفظ")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", str(e))

    def export_backup(self):
        try:
            path = backup_now()
            QMessageBox.information(self, "تم", f"تم إنشاء النسخة: {path}")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", str(e))

    def export_backup_all(self):
        try:
            path = backup_all_app()
            QMessageBox.information(self, "تم", f"تم إنشاء الملف المضغوط: {path}")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", str(e))

    def import_backup(self):
        from pathlib import Path
        src, _ = QFileDialog.getOpenFileName(self, "اختر ملف النسخة", "", "Database (*.db)")
        if not src:
            return
        try:
            # استبدال قاعدة البيانات الحالية بالنسخة المحددة
            from shutil import copy2
            db_path = Path(__file__).resolve().parent.parent / 'data' / 'farm.db'
            copy2(src, db_path)
            QMessageBox.information(self, "تم", "تم الاسترجاع، أعد تشغيل البرنامج")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", str(e))

    # تم إزالة دالة تحديث البرنامج

    def choose_logo(self):
        path, _ = QFileDialog.getOpenFileName(self, "اختر شعار", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.logo_path_edit.setText(path)

    # تم إزالة دالة شراء الترخيص

    def license_verify(self):
        try:
            api_base = self.api_base_edit.text().strip() or None
            token = get_setting('license_token')
            ok = LicenseClient(api_base).verify_token(token)
            self.license_status_label.setText("صالح" if ok else "غير صالح")
            if ok:
                QMessageBox.information(self, "تم", "الترخيص صالح")
            else:
                QMessageBox.warning(self, "تنبيه", "الترخيص غير صالح أو فشل الاتصال")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", str(e))

    def license_activate(self):
        dlg = LicenseDialog(self)
        if dlg.exec() == dlg.Accepted and dlg.ok:
            self.license_status_label.setText("صالح")

    def license_deactivate(self):
        try:
            token = get_setting('license_token')
            ok = LicenseClient().deactivate(token)
            self.license_status_label.setText("غير صالح")
            if ok:
                QMessageBox.information(self, "تم", "تم إلغاء الترخيص")
            else:
                QMessageBox.warning(self, "تنبيه", "تعذر إلغاء الترخيص على الخادم، تم مسحه محلياً")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", str(e))

    def import_suppliers_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "استيراد موردين من CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        import csv
        from app.data.models import Supplier
        cnt = 0
        with SessionLocal() as s:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = (row.get('name') or row.get('اسم') or '').strip()
                    if not name:
                        continue
                    phone = (row.get('phone') or row.get('تليفون') or '').strip() or None
                    addr = (row.get('address') or row.get('عنوان') or '').strip() or None
                    if s.query(Supplier).filter(Supplier.name == name).first():
                        continue
                    s.add(Supplier(name=name, phone=phone, address=addr)); cnt += 1
                s.commit()

    def apply_theme_now(self):
        """تطبيق الثيم المختار فوراً بدون إعادة تشغيل"""
        try:
            # احصل على المفتاح الحالي من القائمة
            key = self.theme_combo.currentData() or 'default'
            # خريطة الملفات كما في main.py
            file_map = {
                'default': 'style.qss',
                'pro': 'style_pro.qss',
                'modern': 'style_pro.qss',
                'dark': 'style_dark.qss',
                'minimal': 'style_minimal.qss',
                'green': 'style_green.qss',
            }
            from pathlib import Path
            style_file = file_map.get(key, 'style.qss')
            base_dir = Path(__file__).resolve().parent
            style_path = base_dir / style_file
            # حفظ الاختيار فوراً حتى يبقى بعد إعادة التشغيل
            try:
                from app.data.database import set_setting
                set_setting('theme', key)
            except Exception:
                pass
            if style_path.exists():
                from PySide6.QtWidgets import QApplication
                app = QApplication.instance()
                if app is not None:
                    with open(style_path, 'r', encoding='utf-8') as f:
                        app.setStyleSheet(f.read())
            else:
                QMessageBox.warning(self, "تنبيه", f"تعذر العثور على ملف الثيم: {style_file}")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", str(e))

    def import_items_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "استيراد أصناف من CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        import csv
        from app.data.models import Item
        cnt = 0
        with SessionLocal() as s:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = (row.get('name') or row.get('الصنف') or '').strip()
                    if not name:
                        continue
                    if s.query(Item).filter(Item.name == name).first():
                        continue
                    unit = (row.get('unit') or row.get('وحدة') or get_setting('default_unit') or 'kg').strip()
                    price = float(row.get('price') or row.get('السعر') or 0)
                    s.add(Item(name=name, default_unit=unit, default_price_per_unit=price)); cnt += 1
                s.commit()
        QMessageBox.information(self, "تم", f"تم استيراد {cnt} صنف")