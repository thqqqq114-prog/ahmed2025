from __future__ import annotations
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap
from app.security import AuthService

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تسجيل الدخول")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(520, 420)

        # تحميل بيانات الدخول المحفوظة إن وُجدت
        try:
            import json, os
            cfg_path = os.path.join(os.path.expanduser('~'), '.farm_app_login.json')
            if os.path.exists(cfg_path):
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._prefill_username = data.get('username', '')
                    self._prefill_password = data.get('password', '')
            else:
                self._prefill_username = ''
                self._prefill_password = ''
        except Exception:
            self._prefill_username = ''
            self._prefill_password = ''

        # عنوان وصورة تعبّر عن طبيعة البرنامج
        title = QLabel("نظام إدارة توريدات الفراولة")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #111827;")
        subtitle = QLabel("مرحباً بك! الرجاء تسجيل الدخول")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color:#6b7280; font-size: 14px;")

        # صورة فاكهة (يمكن لاحقاً استبدالها بصورة من ملف الموارد)
        img = QLabel("🍓👨‍🌾")
        img.setAlignment(Qt.AlignCenter)
        img.setStyleSheet("font-size: 48px;")
        img.setFixedHeight(100)

        self.username_edit = QLineEdit(); self.username_edit.setPlaceholderText("اسم المستخدم")
        self.password_edit = QLineEdit(); self.password_edit.setPlaceholderText("كلمة المرور"); self.password_edit.setEchoMode(QLineEdit.Password)
        # تعبئة تلقائية إن كانت البيانات محفوظة
        if getattr(self, '_prefill_username', ''):
            self.username_edit.setText(self._prefill_username)
        if getattr(self, '_prefill_password', ''):
            self.password_edit.setText(self._prefill_password)
        login_btn = QPushButton("دخول")
        login_btn.setMinimumHeight(40)

        # حفظ بيانات الدخول
        from PySide6.QtWidgets import QCheckBox
        self.remember_cb = QCheckBox("تذكرني")

        layout = QVBoxLayout(self); layout.setSpacing(10)
        layout.addWidget(title); layout.addWidget(subtitle); layout.addWidget(img)
        layout.addLayout(self.row("اسم المستخدم:", self.username_edit))
        layout.addLayout(self.row("كلمة المرور:", self.password_edit))
        layout.addWidget(self.remember_cb)
        layout.addWidget(login_btn)
        # زر إعادة تعيين كلمة مرور الأدمن
        reset_btn = QPushButton("إعادة تعيين كلمة مرور الأدمن")
        reset_btn.setStyleSheet("QPushButton{background:#2563eb;} QPushButton:hover{background:#1d4ed8;}")
        layout.addWidget(reset_btn)

        # Footer: بيانات المبرمج
        footer = QLabel("© جميع الحقوق محفوظة — أحمد حسين\nواتساب/موبايل: 01555560207 — 01096169187")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color:#6b7280; font-size: 12px; margin-top:8px;")
        layout.addWidget(footer)

        # نمط عصري
        self.setStyleSheet(
            """
            * { font-size: 16px; }
            QDialog { background: #f7f8fb; }
            QLineEdit { border:1px solid #e5e7eb; border-radius:8px; padding:10px; background:#fff; }
            QPushButton { background:#ef4444; color:#fff; border:none; border-radius:8px; padding:10px 16px; font-weight:700; }
            QPushButton:hover { background:#dc2626; }
            QPushButton:pressed { background:#b91c1c; }
            QLabel { color:#111827; }
            """
        )

        login_btn.clicked.connect(self.try_login)
        reset_btn.clicked.connect(self.reset_admin_password)
        self.ok = False

    def row(self, label, widget):
        h = QHBoxLayout(); h.addWidget(QLabel(label)); h.addWidget(widget); return h

    def try_login(self):
        res = AuthService.authenticate(self.username_edit.text().strip(), self.password_edit.text())
        if not res.ok:
            QMessageBox.warning(self, "خطأ", res.message)
            return
        # حفظ بيانات الدخول في ملف بسيط إذا اختار المستخدم التذكر
        try:
            if getattr(self, 'remember_cb', None) and self.remember_cb.isChecked():
                import json, os
                cfg_path = os.path.join(os.path.expanduser('~'), '.farm_app_login.json')
                with open(cfg_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        'username': self.username_edit.text().strip(),
                        'password': self.password_edit.text(),
                    }, f, ensure_ascii=False)
        except Exception:
            pass
        self.ok = True
        self.accept()

    def reset_admin_password(self):
        # إعادة تعيين كلمة مرور الأدمن إلى 'admin' وإنشاءه إن لم يوجد
        try:
            AuthService.ensure_admin_exists()
            AuthService.change_password('admin', 'admin')
            QMessageBox.information(self, 'تم', "تمت إعادة تعيين كلمة مرور الأدمن إلى 'admin'")
            # تعبئة الحقول لتسهيل الدخول
            self.username_edit.setText('admin')
            self.password_edit.setText('admin')
        except Exception as e:
            QMessageBox.warning(self, 'خطأ', str(e))