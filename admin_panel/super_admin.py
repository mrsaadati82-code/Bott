# ============================================================
# admin_panel/super_admin.py
# ============================================================
# Super-admin-only commands that are kept separate so a
# regular admin role cannot accidentally trigger them.
# Most of these were inlined under admin_commands.py already
# (addplan, setprice, commission, set, makereseller, ...).
# This module is the canonical home for FUTURE super-admin
# tools (gateway management, total revenue dashboards, ...).
# ============================================================

from core.router import mother_router
from core.permission_manager import is_super_admin, grant_admin, ROLE_ADMIN
from database.db import db

from monitoring.analytics import total_revenue, total_users, total_bots


def setup():

    @mother_router.command("makeadmin")
    def _make_admin(ctx):
        if not is_super_admin(ctx.user_id):
            return
        parts = (ctx.text or "").split()
        if len(parts) != 2 or not parts[1].isdigit():
            ctx.reply("استفاده: /makeadmin <bale_user_id>")
            return
        u = db.fetchone("SELECT * FROM users WHERE bale_user_id=?", (int(parts[1]),))
        if not u:
            ctx.reply("کاربر یافت نشد.")
            return
        grant_admin(u["id"], role=ROLE_ADMIN)
        ctx.reply("✅ کاربر به ادمین ارتقا یافت.")

    @mother_router.command("revenue")
    def _revenue(ctx):
        if not is_super_admin(ctx.user_id):
            return
        ctx.reply(
            "💰 درآمد کل: {:,} ریال\n"
            "👥 کاربران: {}\n"
            "🤖 ربات‌ها: {}".format(
                total_revenue(), total_users(), total_bots()
            )
        )

    @mother_router.command("gateways")
    def _gateways(ctx):
        if not is_super_admin(ctx.user_id):
            return
        rows = db.fetchall("SELECT key, name, is_enabled FROM payment_methods ORDER BY id")
        text = "💳 درگاه‌های پرداخت:\n\n" + "\n".join(
            "- {} ({}) {}".format(r["name"], r["key"], "✅" if r["is_enabled"] else "⛔")
            for r in rows
        )
        text += "\n\nفعال/غیرفعال: /gateway <key> <on|off>"
        ctx.reply(text)

    @mother_router.command("gateway")
    def _gateway_toggle(ctx):
        if not is_super_admin(ctx.user_id):
            return
        parts = (ctx.text or "").split()
        if len(parts) != 3 or parts[2] not in ("on", "off"):
            ctx.reply("استفاده: /gateway <key> <on|off>")
            return
        db.execute("UPDATE payment_methods SET is_enabled=? WHERE key=?",
                   (1 if parts[2] == "on" else 0, parts[1]))
        ctx.reply("✅ وضعیت درگاه به‌روزرسانی شد.")
