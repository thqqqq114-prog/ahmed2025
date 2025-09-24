from __future__ import annotations
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from app.data.database import init_db
from app.security import AuthService
from app.ui.login_dialog import LoginDialog
from app.ui.main_window import MainWindow
from app.ui.license_dialog import LicenseDialog
from app.licensing import LicenseClient

def main() -> None:
    """الدالة الرئيسية لتشغيل التطبيق"""
    init_db()
    AuthService.ensure_admin_exists()

    # إنشاء تطبيق Qt
    qt_app = QApplication(sys.argv)
    
    # تطبيق ملف التصميم (يدعم سمات متعددة)
    from app.data.database import get_setting
    theme = (get_setting('theme') or 'default').strip().lower()
    base_dir = Path(__file__).resolve().parent / 'ui'
    # دعم عدة سمات
    file_map = {
        'default': 'style.qss',
        'pro': 'style_pro.qss',
        'modern': 'style_pro.qss',
        'dark': 'style_dark.qss',
        'minimal': 'style_minimal.qss',
        'green': 'style_green.qss',
    }
    style_file = file_map.get(theme, 'style.qss')
    style_path = base_dir / style_file
    if style_path.exists():
        with open(style_path, 'r', encoding='utf-8') as f:
            qt_app.setStyleSheet(f.read())

    # التحقق من الترخيص قبل تسجيل الدخول
    from PySide6.QtWidgets import QMessageBox
    client = LicenseClient()
    token = client.get_saved_token()
    if not client.verify_token(token):
        dlg = LicenseDialog()
        if dlg.exec() != LicenseDialog.Accepted or not dlg.ok:
            QMessageBox.warning(None, "ترخيص غير موجود", "لا يمكن المتابعة بدون ترخيص صالح.")
            sys.exit(0)
        # تم الحفظ داخل activate، تحقق مرة أخرى للاطمئنان
        if not client.is_valid():
            QMessageBox.critical(None, "فشل التحقق", "الترخيص غير صالح أو فشل الاتصال بالخادم.")
            sys.exit(0)

    # عرض نافذة تسجيل الدخول
    login_dialog = LoginDialog()
    if login_dialog.exec() != LoginDialog.Accepted or not login_dialog.ok:
        sys.exit(0)

    # فتح النافذة الرئيسية
    username: str = login_dialog.username_edit.text().strip()
    auth = AuthService.authenticate(username, login_dialog.password_edit.text())

    # تم إزالة أي رسائل تخص الترخيص

    window = MainWindow(username=username, is_admin=auth.is_admin, role=auth.role)
    window.show()
    
    # بدء تشغيل التطبيق
    sys.exit(qt_app.exec())

if __name__ == "__main__":
    main()