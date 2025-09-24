from __future__ import annotations
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from .models import Base

DB_PATH = Path(__file__).resolve().parent / 'farm.db'
ENGINE = create_engine(f'sqlite:///{DB_PATH}', echo=False, future=True)
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, future=True)


def _ensure_sqlite_columns() -> None:
    """تأكد من وجود الأعمدة والجداول الضرورية في قاعدة البيانات (هجرات بسيطة)"""
    with ENGINE.connect() as conn:
        # users: phone, company
        info = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        cols = {row[1] for row in info}  # row[1] = name
        if 'phone' not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(50) NULL"))
        if 'company' not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN company VARCHAR(500) NULL"))
        if 'salt' not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN salt VARCHAR(64) NULL"))
        # create app_settings if not exist (تم إزالة جدول التراخيص نهائيًا)
        conn.execute(text("CREATE TABLE IF NOT EXISTS app_settings (key VARCHAR(200) PRIMARY KEY, value VARCHAR(5000))"))
        # add role/login_attempts/last_attempt columns if missing
        info_users = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        cols_users = {row[1] for row in info_users}
        if 'role' not in cols_users:
            conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(50) NULL"))
        if 'login_attempts' not in cols_users:
            conn.execute(text("ALTER TABLE users ADD COLUMN login_attempts INTEGER NOT NULL DEFAULT 0"))
        if 'last_attempt' not in cols_users:
            conn.execute(text("ALTER TABLE users ADD COLUMN last_attempt DATETIME NULL"))
        # factory payments table
        conn.execute(text("CREATE TABLE IF NOT EXISTS factory_payments (id INTEGER PRIMARY KEY, factory_id INTEGER NOT NULL, amount FLOAT NOT NULL, method VARCHAR(100), note VARCHAR(1000), paid_at DATETIME, FOREIGN KEY(factory_id) REFERENCES factories(id))"))
        # performance indexes (safe if missing)
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_deliveries_supplier ON deliveries(supplier_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_deliveries_delivered_at ON deliveries(delivered_at)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_payments_supplier ON payments(supplier_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_payments_paid_at ON payments(paid_at)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_cards_factory ON factory_cards(factory_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_cards_created_at ON factory_cards(created_at)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_factory_payments_factory ON factory_payments(factory_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_factory_payments_paid_at ON factory_payments(paid_at)"))
        # audit logs table
        conn.execute(text("CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY, username VARCHAR(255), action VARCHAR(100) NOT NULL, entity VARCHAR(100) NOT NULL, entity_id INTEGER, details VARCHAR(5000), created_at DATETIME)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_created_at ON audit_logs(created_at)"))
        # invoices tables (idempotent create)
        conn.execute(text("CREATE TABLE IF NOT EXISTS invoices (id INTEGER PRIMARY KEY, invoice_no VARCHAR(100) UNIQUE, supplier_id INTEGER, customer_name VARCHAR(500), total_amount FLOAT NOT NULL DEFAULT 0, discount_amount FLOAT NOT NULL DEFAULT 0, tax_amount FLOAT NOT NULL DEFAULT 0, net_amount FLOAT NOT NULL DEFAULT 0, status VARCHAR(50) NOT NULL DEFAULT 'draft', created_at DATETIME, FOREIGN KEY(supplier_id) REFERENCES suppliers(id))"))
        # add invoice_no if missing
        info_inv = conn.execute(text("PRAGMA table_info(invoices)")).fetchall()
        cols_inv = {row[1] for row in info_inv}
        if 'invoice_no' not in cols_inv:
            conn.execute(text("ALTER TABLE invoices ADD COLUMN invoice_no VARCHAR(50) NULL"))
        conn.execute(text("CREATE TABLE IF NOT EXISTS invoice_lines (id INTEGER PRIMARY KEY, invoice_id INTEGER NOT NULL, item_id INTEGER NOT NULL, description VARCHAR(1000), quantity FLOAT NOT NULL, unit VARCHAR(50) NOT NULL DEFAULT 'kg', unit_price FLOAT NOT NULL, discount FLOAT NOT NULL DEFAULT 0, line_total FLOAT NOT NULL, FOREIGN KEY(invoice_id) REFERENCES invoices(id), FOREIGN KEY(item_id) REFERENCES items(id))"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_invoice_created_at ON invoices(created_at)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_invoice_supplier ON invoices(supplier_id)"))
        # extra helpful indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_inv_lines_invoice ON invoice_lines(invoice_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_inv_lines_item ON invoice_lines(item_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_deliveries_item ON deliveries(item_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_items_name ON items(name)"))
        # add min_stock to items if missing
        info_items = conn.execute(text("PRAGMA table_info(items)")).fetchall()
        cols_items = {row[1] for row in info_items}
        if 'min_stock' not in cols_items:
            conn.execute(text("ALTER TABLE items ADD COLUMN min_stock FLOAT NULL"))
        conn.commit()


def init_db() -> None:
    """تهيئة قاعدة البيانات وإنشاء الجداول إذا لم تكن موجودة"""
    Base.metadata.create_all(bind=ENGINE)
    # Ensure new columns exist if DB was created previously
    _ensure_sqlite_columns()


def reset_database() -> None:
    """إعادة تعيين قاعدة البيانات (حذف جميع الجداول وإعادة إنشائها) - عملية لا يمكن الرجوع فيها"""
    # Ensure all sessions are closed by using new connection scope
    Base.metadata.drop_all(bind=ENGINE)
    Base.metadata.create_all(bind=ENGINE)
    _ensure_sqlite_columns()

# ========= App settings helpers =========
from typing import Optional
from datetime import timedelta

def get_setting(key: str) -> Optional[str]:
    from sqlalchemy import text as sqltext
    with ENGINE.connect() as conn:
        row = conn.execute(sqltext("SELECT value FROM app_settings WHERE key=:k"), {"k": key}).fetchone()
        return row[0] if row else None

def set_setting(key: str, value: Optional[str]) -> None:
    from sqlalchemy import text as sqltext
    with ENGINE.connect() as conn:
        if value is None:
            conn.execute(sqltext("DELETE FROM app_settings WHERE key=:k"), {"k": key})
        else:
            conn.execute(sqltext("INSERT INTO app_settings(key,value) VALUES(:k,:v) ON CONFLICT(key) DO UPDATE SET value=excluded.value"), {"k": key, "v": value})
        conn.commit()

# ========= Helpers: stock & posting =========
def get_item_stock(item_id: int, conn=None) -> float:
    """رصيد الصنف = مجموع كميات التوريد - مجموع كميات السحب من الفواتير"""
    # إذا لم يتم تمرير conn استخدم الافتراضي
    if conn is None:
        from app.data.database import ENGINE
        conn = ENGINE.connect()
        close_conn = True
    else:
        close_conn = False
    try:
        delivered = conn.execute(
            text("SELECT COALESCE(SUM(quantity), 0) FROM deliveries WHERE item_id = :item_id"),
            {"item_id": item_id}
        ).scalar() or 0.0
        withdrawn = conn.execute(
            text("SELECT COALESCE(SUM(quantity), 0) FROM invoice_lines WHERE item_id = :item_id"),
            {"item_id": item_id}
        ).scalar() or 0.0
        return float(delivered) - float(withdrawn)
    finally:
        if close_conn:
            conn.close()

# تخزين مؤقت لإعدادات القفل
_lock_settings_cache = None
_cache_expiry = None
CACHE_DURATION = 300  # 5 دقائق بالثواني

def is_date_locked(dt: datetime, conn=None) -> bool:
    """يتحقق من قفل الفترة بناءً على إعدادات القفل في قاعدة البيانات مع استخدام تخزين مؤقت"""
    global _lock_settings_cache, _cache_expiry
    now = datetime.now()
    if _cache_expiry is None or now > _cache_expiry:
        try:
            from sqlalchemy import text as sqltext
            if conn is None:
                from app.data.database import ENGINE
                conn2 = ENGINE.connect()
                close_conn = True
            else:
                conn2 = conn
                close_conn = False
            try:
                row_from = conn2.execute(sqltext("SELECT value FROM app_settings WHERE key='lock_from'"), {}).fetchone()
                row_to = conn2.execute(sqltext("SELECT value FROM app_settings WHERE key='lock_to'"), {}).fetchone()
                s = row_from[0] if row_from else None
                e = row_to[0] if row_to else None
                _lock_settings_cache = (s, e)
                _cache_expiry = datetime.now() + timedelta(seconds=CACHE_DURATION)
            finally:
                if close_conn:
                    conn2.close()
        except Exception:
            return False
    s, e = _lock_settings_cache
    if not s and not e:
        return False
    if s:
        sdt = datetime.strptime(s, "%Y-%m-%d")
        if dt < sdt:
            return True
    if e:
        edt = datetime.strptime(e, "%Y-%m-%d")
        if dt > edt:
            return True
    return False

def log_action(username: str | None, action: str, entity: str, entity_id: int | None, details: str | None = None, conn=None) -> None:
    """تسجيل حركة مراجعة في سجل العمليات (AuditLog)"""
    try:
        from sqlalchemy import text as sqltext
        if conn is None:
            from app.data.database import ENGINE
            conn2 = ENGINE.connect()
            close_conn = True
        else:
            conn2 = conn
            close_conn = False
        try:
            conn2.execute(sqltext("INSERT INTO audit_logs(username, action, entity, entity_id, details, created_at) VALUES(:u,:a,:e,:id,:d, CURRENT_TIMESTAMP)"),
                         {"u": username, "a": action, "e": entity, "id": entity_id, "d": details})
            conn2.commit()
        finally:
            if close_conn:
                conn2.close()
    except Exception:
        pass