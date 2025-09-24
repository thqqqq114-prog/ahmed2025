from __future__ import annotations
import os
import bcrypt
import time
from dataclasses import dataclass
from typing import List, Tuple
from datetime import datetime
from app.data.database import SessionLocal
from app.data.models import User, AuditLog

# Improved password hashing using bcrypt

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def _check_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        # تنسيقات قديمة/غير صالحة
        return False

@dataclass
class AuthResult:
    ok: bool
    message: str
    username: str | None = None
    is_admin: bool = False
    role: str | None = None

class AuthService:
    @staticmethod
    def ensure_admin_exists():
        """Create default admin/admin if no users exist."""
        with SessionLocal() as s:
            existing = s.query(User).count()
            if existing == 0:
                admin = User(
                    username='admin',
                    password_hash=_hash_password('admin'),
                    is_admin=True,
                    role='admin',
                )
                s.add(admin)
                s.commit()

    @staticmethod
    def authenticate(username: str, password: str) -> AuthResult:
        with SessionLocal() as s:
            user = s.query(User).filter(User.username == username).one_or_none()
            if not user:
                return AuthResult(False, "مستخدم غير موجود")
            # التحقق من عدد المحاولات الفاشلة (5 دقائق قفل بعد 3 محاولات)
            from datetime import datetime, timedelta
            if (user.login_attempts or 0) >= 3 and user.last_attempt and (datetime.now() - user.last_attempt) < timedelta(minutes=5):
                return AuthResult(False, "تم تجاوز عدد المحاولات. انتظر 5 دقائق")
            if not _check_password(password, user.password_hash):
                user.login_attempts = (user.login_attempts or 0) + 1
                user.last_attempt = datetime.now()
                s.commit()
                return AuthResult(False, "كلمة المرور غير صحيحة")
            # إعادة تعيين العداد وتسجيل دخول ناجح
            user.login_attempts = 0
            user.last_attempt = datetime.now()
            s.commit()
            try:
                s.add(AuditLog(username=username, action='login', entity='user', entity_id=user.id, details='login ok'))
                s.commit()
            except Exception:
                s.rollback()
            return AuthResult(True, "تم", username=user.username, is_admin=user.is_admin, role=user.role)

    # === User management ===
    @staticmethod
    def list_users() -> list[tuple[str, bool]]:
        with SessionLocal() as s:
            return [(u.username, u.is_admin) for u in s.query(User).order_by(User.username).all()]

    @staticmethod
    def create_user(username: str, password: str, is_admin: bool) -> None:
        with SessionLocal() as s:
            if s.query(User).filter(User.username == username).first():
                raise ValueError("اسم المستخدم موجود بالفعل")
            user = User(
                username=username,
                password_hash=_hash_password(password),
                is_admin=is_admin,
                login_attempts=0,
                last_attempt=datetime.now()
            )
            s.add(user)
            s.commit()

    @staticmethod
    def delete_user(username: str) -> None:
        with SessionLocal() as s:
            user = s.query(User).filter(User.username == username).one_or_none()
            if not user:
                return
            s.delete(user)
            s.commit()

    @staticmethod
    def change_password(username: str, new_password: str) -> None:
        with SessionLocal() as s:
            user = s.query(User).filter(User.username == username).one_or_none()
            if not user:
                raise ValueError("مستخدم غير موجود")
            user.password_hash = _hash_password(new_password)
            user.login_attempts = 0  # إعادة تعيين المحاولات بعد تغيير كلمة المرور
            s.commit()

    @staticmethod
    def set_admin(username: str, is_admin: bool) -> None:
        with SessionLocal() as s:
            user = s.query(User).filter(User.username == username).one_or_none()
            if not user:
                raise ValueError("مستخدم غير موجود")
            user.is_admin = is_admin
            s.commit()