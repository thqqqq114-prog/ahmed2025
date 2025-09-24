from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QListWidget,
    QStackedWidget, QSplitter, QLabel, QMessageBox
)
from pathlib import Path
from app.ui.suppliers_dialog import SuppliersDialog
from app.ui.deliveries_dialog import DeliveriesDialog
from app.ui.items_dialog import ItemsDialog
from app.ui.factories_dialog import FactoriesDialog
from app.ui.requirements_dialog import RequirementsDialog
from app.ui.payments_dialog import PaymentsDialog
from app.ui.reports_dialog import ReportsDialog
from app.ui.users_page import UsersPage
from app.ui.farmers_page import FarmersPage
from app.ui.factories_page import FactoriesPage
from app.ui.journal_page import JournalPage
from app.ui.settings_page import SettingsPage
from app.ui.about_dev_page import AboutDeveloperPage

class MainWindow(QMainWindow):
    def __init__(self, username: str | None = None, is_admin: bool = False, role: str | None = None):
        super().__init__()
        self.setWindowTitle("حسابات فلاحين/موردين")
        self._backup_on_close_enabled = False
        self.resize(1200, 800)
        self.setLayoutDirection(Qt.RightToLeft)  # RTL
        self.is_admin = is_admin  # set from login
        self.username = username or ""
        self.role = (role or ("admin" if is_admin else "editor")).lower()

        # Root layout with a splitter: sidebar on the right, content on the left
        splitter = QSplitter(self)
        splitter.setLayoutDirection(Qt.LeftToRight)  # keep visual order predictable
        splitter.setOrientation(Qt.Horizontal)

        # Left: side navigation
        nav = QWidget(); nav_layout = QVBoxLayout(nav)
        title = QLabel("القوائم"); title.setStyleSheet("font-size:20px; font-weight:bold; padding:8px 0;")
        nav_layout.addWidget(title)

        self.btn_dashboard = QPushButton("الرئيسية")
        self.btn_farmers = QPushButton("فلاحين")
        self.btn_factories2 = QPushButton("مصانع")
        self.btn_journal = QPushButton("اليومية")
        self.btn_reports = QPushButton("التقارير")
        self.btn_settings = QPushButton("الإعدادات")
        self.btn_about = QPushButton("عن المبرمج")
        self.btn_users = QPushButton("المستخدمون")
        self.btn_print = QPushButton("طباعة الصفحة (A4)")

        for b in (
            self.btn_dashboard,
            self.btn_farmers, self.btn_factories2, self.btn_journal,
            self.btn_reports, self.btn_settings, self.btn_about, self.btn_users
        ):
            b.setCursor(Qt.PointingHandCursor)
            b.setMinimumHeight(40)
            nav_layout.addWidget(b)
        nav_layout.addWidget(self.btn_print)
        nav_layout.addStretch(1)

        # Right: pages area
        self.pages = QStackedWidget()

        # Each page is a QWidget now
        from app.ui.dashboard_page import DashboardPage
        self.page_dashboard = DashboardPage(self)
        self.page_farmers = FarmersPage(self)
        self.page_factories2 = FactoriesPage(self)
        self.page_journal = JournalPage(self)
        self.page_reports = ReportsDialog(self)
        self.page_settings = SettingsPage(username=self.username, parent=self)
        self.page_about = AboutDeveloperPage(self)
        self.page_users = UsersPage(self)

        for w in (
            self.page_dashboard,
            self.page_farmers, self.page_factories2, self.page_journal,
            self.page_reports, self.page_settings, self.page_about, self.page_users
        ):
            self.pages.addWidget(w)

        # Add widgets in order: content (left) then sidebar (right)
        splitter.addWidget(self.pages)  # index 0 -> left pane
        splitter.addWidget(nav)         # index 1 -> right pane (sidebar)
        splitter.setStretchFactor(0, 1) # content expands
        splitter.setStretchFactor(1, 0) # sidebar fixed
        self.setCentralWidget(splitter)

        # Connections
        self.btn_dashboard.clicked.connect(lambda: self._switch_to(self.page_dashboard))
        self.btn_farmers.clicked.connect(lambda: self._switch_to(self.page_farmers))
        self.btn_factories2.clicked.connect(lambda: self._switch_to(self.page_factories2))
        self.btn_journal.clicked.connect(lambda: self._switch_to(self.page_journal))
        self.btn_reports.clicked.connect(lambda: self._switch_to(self.page_reports))
        self.btn_settings.clicked.connect(lambda: self._switch_to(self.page_settings))
        self.btn_about.clicked.connect(lambda: self._switch_to(self.page_about))
        self.btn_users.clicked.connect(lambda: self._switch_to(self.page_users))

        # Dashboard quick shortcuts
        try:
            self.page_dashboard.btn_go_journal.clicked.connect(lambda: self._switch_to(self.page_journal))
            self.page_dashboard.btn_go_factory_card.clicked.connect(self._open_factory_card_tab)
            self.page_dashboard.btn_go_reports.clicked.connect(lambda: self._switch_to(self.page_reports))
        except Exception:
            pass

        # Universal print current page
        self.btn_print.clicked.connect(self._print_current_page)

        # Modern styling & bigger font + quick backup button
        self._apply_modern_style()
        # Optionally load icons stylesheet (placeholder emoji)
        # with open(Path(__file__).resolve().parent / 'icons.qss', 'r', encoding='utf-8') as f:
        #     self.setStyleSheet(self.styleSheet() + '\n' + f.read())
        self._add_quick_backup(nav_layout)

        # Admin-only pages/buttons
        self._apply_access_control()
        # قراءة إعداد النسخ الاحتياطي عند الإغلاق ويوميًا
        try:
            from app.data.database import get_setting
            self._backup_on_close_enabled = (get_setting('backup_on_close') or '0') == '1'
            self._setup_daily_backup((get_setting('backup_daily') or '0') == '1')
        except Exception:
            self._backup_on_close_enabled = False



        self._switch_to(self.page_dashboard)

    def _setup_daily_backup(self, enabled: bool):
        from PySide6.QtCore import QTimer
        if not enabled or not self.is_admin:
            return
        # مؤقت بسيط يجري نسخًا احتياطيًا كل 6 ساعات أثناء التشغيل
        self._daily_timer = QTimer(self)
        self._daily_timer.setInterval(6*60*60*1000)
        self._daily_timer.timeout.connect(self._daily_backup_tick)
        self._daily_timer.start()
        # تنفيذ نسخة أولية عند بدء التشغيل
        try:
            from app.backup import backup_on_close_rotate
            backup_on_close_rotate(max_keep=5)
        except Exception:
            pass

    def _daily_backup_tick(self):
        try:
            if self.is_admin:
                from app.backup import backup_on_close_rotate
                backup_on_close_rotate(max_keep=5)
        except Exception:
            pass

    def _switch_to(self, widget):
        self.pages.setCurrentWidget(widget)

    def _open_factory_card_tab(self):
        # انتقل لصفحة المصانع وافتح تبويب الكارتة إن أمكن
        self._switch_to(self.page_factories2)
        try:
            # ابحث عن QTabWidget داخل الصفحة وحدد التبويب الثاني (الكارتة)
            from PySide6.QtWidgets import QTabWidget
            tabs = self.page_factories2.findChild(QTabWidget)
            if tabs:
                tabs.setCurrentIndex(1)
        except Exception:
            pass

    def _print_current_page(self):
        from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog
        # معاينة قبل الطباعة للصفحة الحالية
        w = self.pages.currentWidget()
        if w is None:
            return
        printer = QPrinter(QPrinter.HighResolution)
        preview = QPrintPreviewDialog(printer, self)
        def render(p):
            pm = w.grab()
            from PySide6.QtGui import QPainter
            painter = QPainter(p)
            try:
                rect = painter.viewport()
                scaled = pm.scaled(rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                painter.setViewport(rect.x(), rect.y(), scaled.width(), scaled.height())
                painter.setWindow(pm.rect())
                painter.drawPixmap(0, 0, pm)
            finally:
                painter.end()
        preview.paintRequested.connect(render)
        preview.exec()



    def _apply_modern_style(self):
        self.setStyleSheet(
            """
            * { font-size: 16px; } /* تكبير الخط */
            QMainWindow { background: #f7f8fb; }
            QWidget { background: #ffffff; }
            QPushButton {
                background: #3b82f6; color: white; border: none; padding: 10px 14px;
                border-radius: 8px; font-weight: 600;
            }
            QPushButton:hover { background: #2563eb; }
            QPushButton:pressed { background: #1d4ed8; }
            /* Sidebar buttons look as tabs */
            QWidget > QPushButton {
                text-align: center;
                margin-bottom: 6px;
            }
            /* Green for backup, gray for print */
            QPushButton[text="نسخة احتياطية فورية"] { background:#10b981; }
            QPushButton[text="طباعة الصفحة (A4)"] { background:#6b7280; }
            QPushButton[text="طباعة الصفحة (A4)"]:hover { background:#4b5563; }

            QLineEdit, QComboBox, QListWidget, QTableWidget {
                border: 1px solid #e5e7eb; border-radius: 8px; padding: 8px; background: white;
            }
            QLabel { color: #111827; }
            QSplitter::handle { background: #e5e7eb; width: 6px; }
            """
        )

    def _add_quick_backup(self, nav_layout):
        from PySide6.QtWidgets import QMessageBox
        from app.backup import backup_now
        btn = QPushButton("نسخة احتياطية فورية")
        btn.setStyleSheet("background:#10b981;")
        btn.clicked.connect(lambda: self._run_backup(backup_now))
        nav_layout.addWidget(btn)

    def _run_backup(self, fn):
        from PySide6.QtWidgets import QMessageBox
        if not self.is_admin:
            QMessageBox.warning(self, "تنبيه", "هذه العملية تتطلب صلاحية الأدمن")
            return
        try:
            path = fn()
            QMessageBox.information(self, "تم", f"تم إنشاء نسخة: {path}")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", str(e))

    def closeEvent(self, event):
        # نسخ احتياطي تلقائي إن كان مفعلاً
        try:
            if self._backup_on_close_enabled and self.is_admin:
                from app.backup import backup_on_close_rotate
                backup_on_close_rotate(max_keep=5)
        except Exception:
            pass
        super().closeEvent(event)

    def _apply_access_control(self):
        # Admin-only access: users page visible only to admin
        self.btn_users.setVisible(self.role == 'admin')
        # Editor can تعديل/إضافة، Viewer قراءة فقط: نعطّل الأزرار الحساسة إذا viewer
        is_viewer = (self.role == 'viewer')
        try:
            # تعطيل أزرار CRUD داخل الصفحات إذا viewer
            # FarmersPage
            for btn_name in ['btn_add', 'btn_upd', 'btn_del', 'open_acc_btn']:
                b = getattr(self.page_farmers, btn_name, None)
                if b:
                    b.setEnabled(not is_viewer)
            # تعطيل الحقول النصية أيضاً
            for w_name in ['name_edit', 'phone_edit', 'address_edit', 'acc_search']:
                w = getattr(self.page_farmers, w_name, None)
                if w:
                    w.setReadOnly(is_viewer) if hasattr(w, 'setReadOnly') else w.setEnabled(not is_viewer)

            # FactoriesPage: إدارة المصانع + الكارتة + الدفعات
            for btn_name in ['btn_factory_add', 'btn_factory_del', 'btn_calc_card', 'btn_save_card', 'pay_factory_combo']:
                w = getattr(self.page_factories2, btn_name, None)
                if w:
                    # السماح باختيار المصنع لكن منع الحفظ عند viewer
                    if btn_name == 'pay_factory_combo':
                        w.setEnabled(True)
                    else:
                        w.setEnabled(not is_viewer)
            for w_name in ['name_edit', 'notes_edit', 'fac_search', 'card_grade', 'card_gross', 'card_disc', 'card_net', 'card_price', 'card_total']:
                w = getattr(self.page_factories2, w_name, None)
                if w:
                    w.setReadOnly(is_viewer) if hasattr(w, 'setReadOnly') else w.setEnabled(not is_viewer)
        except Exception:
            pass
        # منع فتح صفحة المستخدمين لغير الأدمن
        if self.role != 'admin' and self.pages.currentWidget() == getattr(self, 'page_users', None):
            self._switch_to(self.page_farmers)