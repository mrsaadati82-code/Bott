# ============================================================
# health_check.py - Pre-flight diagnostics
# ============================================================
# Run this BEFORE starting the bot to ensure everything is
# wired up correctly. No network calls, no need for a token.
#
#     python health_check.py
#
# Exit code 0 = all good, 1 = some checks failed.
# ============================================================

import os
import sys
import traceback


def _print(ok, msg, detail=""):
    icon = "✅" if ok else "❌"
    print(" {} {}".format(icon, msg))
    if detail:
        print("    └─ {}".format(detail))


def _bullet(msg):
    print(" • {}".format(msg))


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)

    failed = 0
    print("\n" + "=" * 56)
    print(" Bot Builder SaaS - Pre-flight Health Check")
    print("=" * 56 + "\n")

    # ---------- 1. Python version ----------
    print("🐍 Python")
    py_ok = sys.version_info >= (3, 7)
    _print(py_ok, "Python {}.{}.{} ".format(*sys.version_info[:3]),
           "نیاز: ≥3.7" if not py_ok else "")
    if not py_ok:
        failed += 1

    # ---------- 2. Required packages ----------
    print("\n📦 وابستگی‌ها")
    try:
        import requests          # noqa
        _print(True, "requests نصب است")
    except ImportError:
        _print(False, "requests نصب نیست",
               "اجرا کنید: pip install requests")
        failed += 1

    try:
        import sqlite3           # noqa
        _print(True, "sqlite3 (stdlib) موجود است")
    except ImportError:
        _print(False, "sqlite3 موجود نیست",
               "نسخه Python شما sqlite3 ندارد")
        failed += 1

    # ---------- 3. Directory structure ----------
    print("\n📁 ساختار پوشه‌ها")
    required_dirs = [
        "core", "database", "modules", "modules/builtin",
        "templates", "templates/builtin",
        "flow_engine", "page_builder", "payments", "wallet",
        "subscriptions", "channel_lock", "admin_panel",
        "reseller", "broadcast", "monitoring", "data",
    ]
    for d in required_dirs:
        full = os.path.join(here, d)
        _print(os.path.isdir(full), d)
        if not os.path.isdir(full):
            failed += 1

    # ---------- 4. Imports ----------
    print("\n🔌 لود ماژول‌ها")
    modules = [
        "config",
        "core.engine", "core.dispatcher", "core.router",
        "core.bot_manager", "core.updater", "core.state_manager",
        "core.permission_manager", "core.keyboards",
        "database.db", "database.models", "database.migrations",
        "modules.module_registry", "modules.module_loader",
        "page_builder.page_manager", "page_builder.button_manager",
        "flow_engine.flow_manager", "flow_engine.step_executor",
        "flow_engine.variable_manager",
        "channel_lock.channel_checker",
        "broadcast.broadcast_manager",
        "payments.payment_manager", "payments.bale_gateway",
        "payments.online_gateway", "payments.card_to_card",
        "wallet.wallet_manager",
        "subscriptions.plan_manager", "subscriptions.subscription_manager",
        "reseller.affiliate_manager",
        "admin_panel.admin_router", "admin_panel.admin_commands",
        "admin_panel.super_admin", "admin_panel.reseller",
        "admin_panel.user_panel", "admin_panel.template_admin",
        "monitoring.logs", "monitoring.analytics",
        "templates.template_base", "templates.template_registry",
    ]
    for m in modules:
        try:
            # ensure env vars exist so config doesn't blow up
            os.environ.setdefault("MOTHER_BOT_TOKEN", "PUT_YOUR_TOKEN")
            __import__(m)
            _print(True, m)
        except Exception as e:
            _print(False, m, str(e))
            failed += 1

    # ---------- 5. Configuration sanity ----------
    print("\n⚙️ تنظیمات")
    try:
        from config import MOTHER_BOT_TOKEN, SUPER_ADMIN_IDS, DB_PATH, DATA_DIR
        token_ok = MOTHER_BOT_TOKEN and not MOTHER_BOT_TOKEN.startswith("PUT_YOUR")
        _print(token_ok, "MOTHER_BOT_TOKEN تنظیم شده",
               "config.py را ویرایش کنید و توکن @botfather را بگذارید"
               if not token_ok else "")
        if not token_ok:
            failed += 1

        admins_ok = bool(SUPER_ADMIN_IDS) and SUPER_ADMIN_IDS != [0]
        _print(admins_ok, "SUPER_ADMIN_IDS تنظیم شده",
               "حداقل یک ID عددی در config.py یا متغیر محیطی بگذارید"
               if not admins_ok else "  ".join(str(x) for x in SUPER_ADMIN_IDS))
        if not admins_ok:
            failed += 1

        _print(os.path.isdir(DATA_DIR), "پوشه data وجود دارد", DATA_DIR)
    except Exception as e:
        _print(False, "خواندن config.py", str(e))
        failed += 1

    # ---------- 6. Database init ----------
    print("\n💾 دیتابیس")
    try:
        from database.migrations import init_database
        init_database()
        from database.db import db
        n = db.fetchone(
            "SELECT COUNT(*) AS c FROM sqlite_master WHERE type='table'"
        )["c"]
        _print(True, "ساخت/باز کردن دیتابیس", "تعداد جداول: {}".format(n))

        plans = db.fetchone(
            "SELECT COUNT(*) AS c FROM plans"
        )["c"]
        methods = db.fetchone(
            "SELECT COUNT(*) AS c FROM payment_methods"
        )["c"]
        _print(True, "Seed پلن‌ها", "{} پلن".format(plans))
        _print(True, "Seed روش‌های پرداخت", "{} روش".format(methods))
    except Exception as e:
        _print(False, "init_database", str(e))
        traceback.print_exc()
        failed += 1

    # ---------- 7. Templates discovery ----------
    print("\n🧩 Templateها")
    try:
        from templates import template_registry
        template_registry.discover()
        template_registry.sync_to_db()
        tpls = template_registry.all_templates()
        _print(len(tpls) > 0, "Auto-discovery",
               "{} Template".format(len(tpls)))
        for t in tpls:
            plans = template_registry.list_plans_for_template(t.key)
            _bullet("{} {} - {} پلن".format(t.icon, t.name, len(plans)))
    except Exception as e:
        _print(False, "Template discovery", str(e))
        failed += 1

    # ---------- 8. Feature Registry ----------
    print("\n🎯 Feature Registry")
    try:
        from modules.module_registry import FEATURES
        _print(len(FEATURES) == 12,
               "تعداد قابلیت‌های قفل‌شده: {}".format(len(FEATURES)),
               "انتظار: 12")
        if len(FEATURES) != 12:
            failed += 1
    except Exception as e:
        _print(False, "Feature Registry", str(e))
        failed += 1

    # ---------- Verdict ----------
    print("\n" + "=" * 56)
    if failed == 0:
        print("🎉 همه چیز آماده است! می‌توانید با python main.py اجرا کنید.")
        print("=" * 56 + "\n")
        return 0
    else:
        print("⚠️  {} مورد نیاز به رفع دارد. لطفاً موارد قرمز را اصلاح کنید.".format(failed))
        print("=" * 56 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
