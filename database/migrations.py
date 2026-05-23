# ============================================================
# database/migrations.py
# ============================================================

from database.db import db
from database.models import TABLES, INDEXES, SCHEMA_VERSION


MIGRATIONS = {}


def _current_version() -> int:
    try:
        row = db.fetchone("SELECT version FROM schema_version ORDER BY id DESC LIMIT 1")
        if row:
            return int(row["version"])
    except Exception:
        pass
    return 0


def _set_version(v: int):
    db.execute("INSERT INTO schema_version (version) VALUES (?)", (v,))


def init_database():
    for name, ddl in TABLES:
        db.execute(ddl)
    for ix in INDEXES:
        db.execute(ix)
    current = _current_version()
    if current == 0:
        _set_version(SCHEMA_VERSION)
        current = SCHEMA_VERSION
    for target in sorted(MIGRATIONS.keys()):
        if target > current:
            for stmt in MIGRATIONS[target]:
                db.execute(stmt)
            _set_version(target)
            current = target
    _seed_defaults()


def _seed_defaults():
    # Payment methods (order matters - shown to users in this order)
    defaults = [
        ("wallet",       "💰 پرداخت از کیف پول"),
        ("bale",         "💳 پرداخت داخلی بله"),
        ("online",       "🌐 درگاه آنلاین"),
        ("card_to_card", "🧾 کارت به کارت"),
    ]
    for key, name in defaults:
        exists = db.fetchone("SELECT id FROM payment_methods WHERE key=?", (key,))
        if not exists:
            db.execute(
                "INSERT INTO payment_methods (key, name, is_enabled) VALUES (?, ?, ?)",
                (key, name, 1),
            )

    # Default free plan
    free = db.fetchone("SELECT id FROM plans WHERE key=?", ("free",))
    if not free:
        db.execute(
            """INSERT INTO plans
                (key, name, description, duration_days, price,
                 max_bots, max_users_per_bot, max_monthly_messages,
                 allowed_modules, allowed_templates, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "free", "رایگان", "پلن رایگان آزمایشی",
                30, 0,
                1, 100, 1000,
                "[]", "[]", 1,
            ),
        )

    # Default settings
    settings_defaults = {
        "support_contact": "@support",
        "welcome_message": "به ربات‌ساز بله خوش آمدید 🎉",
        "card_number": "0000-0000-0000-0000",
        "card_holder": "نام صاحب کارت",
        "card_bank": "نام بانک",
        "referral_enabled": "1",
        "referral_banner_text": "🎯 با کلیک روی لینک زیر، عضو ربات‌ساز بله شوید و خودتان هم یک ربات بسازید!\n\n🔗 {link}",
        "referral_banner_photo": "",
    }
    for k, v in settings_defaults.items():
        exists = db.fetchone("SELECT id FROM system_settings WHERE key=?", (k,))
        if not exists:
            db.execute(
                "INSERT INTO system_settings (key, value) VALUES (?, ?)", (k, v)
            )
