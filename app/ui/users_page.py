from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QCheckBox, QMessageBox
from app.security import AuthService
from app.ui.toast import show_toast

class UsersPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("UsersPage")

        self.users_list = QListWidget()
        self.username_edit = QLineEdit(); self.username_edit.setPlaceholderText("اسم المستخدم")
        self.password_edit = QLineEdit(); self.password_edit.setPlaceholderText("كلمة المرور"); self.password_edit.setEchoMode(QLineEdit.Password)
        self.is_admin_cb = QCheckBox("أدمن")

        add_btn = QPushButton("إضافة مستخدم")
        del_btn = QPushButton("حذف المستخدم")
        reset_btn = QPushButton("تغيير كلمة المرور")
        toggle_admin_btn = QPushButton("تبديل أدمن")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("المستخدمون"))
        layout.addWidget(self.users_list)
        layout.addLayout(self.row("اسم المستخدم:", self.username_edit))
        layout.addLayout(self.row("كلمة المرور:", self.password_edit))
        layout.addWidget(self.is_admin_cb)
        btns = QHBoxLayout(); btns.addWidget(add_btn); btns.addWidget(del_btn); btns.addWidget(reset_btn); btns.addWidget(toggle_admin_btn)
        layout.addLayout(btns)

        # تعطيل الإدخال للمشاهِد
        try:
            mw = self.window()
            is_viewer = getattr(mw, 'role', '') == 'viewer'
            if is_viewer:
                for w in [self.username_edit, self.password_edit, self.is_admin_cb]:
                    if hasattr(w, 'setReadOnly'):
                        w.setReadOnly(True)
                    else:
                        w.setEnabled(False)
                for b in [add_btn, del_btn, reset_btn, toggle_admin_btn]:
                    b.setEnabled(False)
        except Exception:
            pass

        add_btn.clicked.connect(self.add_user)
        del_btn.clicked.connect(self.delete_user)
        reset_btn.clicked.connect(self.reset_password)
        toggle_admin_btn.clicked.connect(self.toggle_admin)

        self.refresh()

    def row(self, label, widget):
        h = QHBoxLayout(); h.addWidget(QLabel(label)); h.addWidget(widget); return h

    def refresh(self):
        self.users_list.clear()
        for username, is_admin in AuthService.list_users():
            self.users_list.addItem(f"{username} | {'أدمن' if is_admin else 'عادي'}")

    def _current_username(self):
        if not self.users_list.currentItem():
            return None
        return self.users_list.currentItem().text().split('|')[0].strip()

    def add_user(self):
        u = self.username_edit.text().strip(); p = self.password_edit.text(); a = self.is_admin_cb.isChecked()
        if not u or not p:
            QMessageBox.warning(self, "تنبيه", "أدخل اسم المستخدم وكلمة المرور")
            return
        try:
            AuthService.create_user(u, p, a)
            self.username_edit.clear(); self.password_edit.clear(); self.is_admin_cb.setChecked(False)
            self.refresh()
            try:
                show_toast(self, "تمت الإضافة")
            except Exception:
                pass
        except Exception as e:
            QMessageBox.warning(self, "خطأ", str(e))

    def delete_user(self):
        u = self._current_username()
        if not u:
            return
        AuthService.delete_user(u)
        self.refresh()
        try:
            show_toast(self, "تم الحذف")
        except Exception:
            pass

    def reset_password(self):
        u = self._current_username()
        if not u:
            return
        p = self.password_edit.text()
        if not p:
            QMessageBox.warning(self, "تنبيه", "أدخل كلمة مرور جديدة في الحقل")
            return
        try:
            AuthService.change_password(u, p)
            self.password_edit.clear()
            try:
                show_toast(self, "تم تغيير كلمة المرور")
            except Exception:
                QMessageBox.information(self, "تم", "تم تغيير كلمة المرور")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", str(e))

    def toggle_admin(self):
        u = self._current_username()
        if not u:
            return
        # Quick get current role from list
        is_admin = 'أدمن' in self.users_list.currentItem().text()
        try:
            AuthService.set_admin(u, not is_admin)
            self.refresh()
            try:
                show_toast(self, "تم تغيير الصلاحيات")
            except Exception:
                pass
        except Exception as e:
            QMessageBox.warning(self, "خطأ", str(e))