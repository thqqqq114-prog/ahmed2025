from __future__ import annotations
"""
عميل ترخيص بسيط للتعامل مع API الخارجي.
- تفعيل: POST /api/v1/activate -> token
- تحقق: GET /api/v1/verify (Authorization: Bearer <token>)
- إلغاء: POST /api/v1/deactivate

يتم حفظ الـ token في جدول app_settings بالمفتاح 'license_token'.
قاعدة الـ API يمكن تخصيصها عبر الإعداد 'api_base' وإلا الافتراضي هو الدومين الرئيسي.
"""

import hashlib
import platform
import uuid
from typing import Optional

import requests

from app.data.database import get_setting, set_setting


DEFAULT_API_BASE = "https://ahmedhussein.online"
TIMEOUT = 10  # seconds


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_hwid() -> str:
    """توليد HWID بسيط (MAC + اسم الجهاز) ثم SHA256.
    ملاحظة: ليس ضد العبث بشكل كامل لكنه كافٍ للاستخدام الحالي.
    """
    try:
        mac = uuid.getnode()  # قد يرجع قيمة عشوائية في بعض البيئات
        host = platform.node() or "unknown-host"
        base = f"{mac}-{host}".strip()
        return _sha256_hex(base)
    except Exception:
        return _sha256_hex("fallback-hwid")


class LicenseError(Exception):
    pass


class LicenseClient:
    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = (base_url or get_setting("api_base") or DEFAULT_API_BASE).rstrip("/")

    # ===== Public API =====
    def activate(self, license_key: str, device_limit: int = 1) -> str:
        """يرسل مفتاح الترخيص والـ HWID للحصول على token. يرجع الـ token أو يرمي استثناء عند الفشل."""
        url = f"{self.base_url}/api/v1/activate"
        payload = {
            "license_key": (license_key or "").strip(),
            "hwid": get_hwid(),
            "device_limit": int(device_limit or 1),
        }
        try:
            r = requests.post(url, json=payload, timeout=TIMEOUT)
        except Exception as e:
            raise LicenseError(f"تعذر الاتصال بخادم الترخيص: {e}")
        if r.status_code != 200:
            # حاول استخراج رسالة مفيدة
            try:
                msg = r.json().get("detail") or r.text
            except Exception:
                msg = r.text
            raise LicenseError(f"فشل التفعيل: {msg}")
        data = r.json() or {}
        token = data.get("token")
        if not token:
            raise LicenseError("استجابة غير متوقعة من خادم الترخيص")
        # حفظ الـ token
        set_setting("license_token", token)
        return token

    def verify_token(self, token: Optional[str]) -> bool:
        token = (token or "").strip()
        if not token:
            return False
        url = f"{self.base_url}/api/v1/verify"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            r = requests.get(url, headers=headers, timeout=TIMEOUT)
        except Exception:
            return False
        if r.status_code != 200:
            return False
        try:
            data = r.json() or {}
            return bool(data.get("ok"))
        except Exception:
            return False

    def deactivate(self, token: Optional[str]) -> bool:
        token = (token or "").strip()
        if not token:
            return True
        url = f"{self.base_url}/api/v1/deactivate"
        try:
            r = requests.post(url, json={"token": token}, timeout=TIMEOUT)
            ok = r.status_code == 200
        except Exception:
            ok = False
        # امسح المخزن محليًا بغض النظر عن نتيجة النداء
        set_setting("license_token", None)
        return ok

    # ===== Convenience =====
    def get_saved_token(self) -> Optional[str]:
        return get_setting("license_token")

    def is_valid(self) -> bool:
        return self.verify_token(self.get_saved_token())