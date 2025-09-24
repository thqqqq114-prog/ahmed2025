from __future__ import annotations
import shutil
from datetime import datetime
from pathlib import Path
import os

# قاعدة البيانات داخل مجلد data
DB_FILE = Path(__file__).resolve().parent / 'data' / 'farm.db'
BACKUP_DIR = Path(__file__).resolve().parent / 'backups'

BACKUP_DIR.mkdir(exist_ok=True)

def backup_now() -> str:
    ts = datetime.now().strftime('%Y%m%d-%H%M%S')
    dest = BACKUP_DIR / f'farm-{ts}.db'
    shutil.copy2(DB_FILE, dest)
    return str(dest)

def backup_all_app() -> str:
    """نسخة احتياطية كاملة للمجلد app في ملف zip"""
    ts = datetime.now().strftime('%Y%m%d-%H%M%S')
    base_dir = Path(__file__).resolve().parent
    zip_base = BACKUP_DIR / f'app-full-{ts}'
    archive_path = shutil.make_archive(str(zip_base), 'zip', root_dir=base_dir)
    return archive_path

def restore_db_from(src: str) -> None:
    """استرجاع ملف قاعدة البيانات"""
    shutil.copy2(src, DB_FILE)

def backup_on_close_rotate(max_keep: int = 5) -> str:
    """ينشئ نسخة احتياطية لقاعدة البيانات ويحذف الأقدم مع الإبقاء على آخر max_keep نسخ"""
    path = backup_now()
    # ترتيب الملفات حسب التاريخ بالاسم farm-YYYYMMDD-HHMMSS.db
    files = sorted(BACKUP_DIR.glob('farm-*.db'))
    if len(files) > max_keep:
        to_delete = files[:-max_keep]
        for f in to_delete:
            try:
                os.remove(f)
            except Exception:
                pass
    return path