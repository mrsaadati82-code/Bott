# ============================================================
# admin_panel/reseller.py
# ============================================================
# Reseller-specific commands.
# Resellers are admins with a limited scope: they can see their
# referrals, commissions, and a copy of their referral link.
# ============================================================

from core.router import mother_router
from core.keyboards import reply_keyboard, inline
from core.permission_manager import (
    get_role, ROLE_RESELLER, ROLE_SUPER_ADMIN, is_super_admin,
)
from core.state_manager import state_manager, text_input_bus
from reseller.affiliate_manager import (
    make_ref_code, count_referrals, list_referrals, get_commission_summary,
    get_reseller_stats,
)
from wallet.wallet_manager import get_balance, list_transactions
from database.db import db


def _money(n: int) -> str:
    return "{:,} ریال".format(int(n))


def setup():

    @mother_router.command("reseller")
    def _reseller_panel(ctx):
        role = get_role(ctx.user_id)
        if role == ROLE_RESELLER:
            _show_reseller_panel(ctx)
        elif role == ROLE_SUPER_ADMIN:
            _show_admin_reseller_panel(ctx)
        else:
            ctx.reply("⛔ این بخش فقط برای نمایندگان است.")

    @mother_router.command("referrals")
    def _referrals(ctx):
        if get_role(ctx.user_id) != ROLE_RESELLER:
            return
        _show_referrals(ctx)

    # ========================================================
    # Reseller Panel
    # ========================================================
    def _show_reseller_panel(ctx):
        ref_code = make_ref_code(ctx.db_user_id)
        bal = get_balance(ctx.db_user_id)
        refs = count_referrals(ctx.db_user_id)
        stats = get_reseller_stats(ctx.db_user_id)
        recent_refs = list_referrals(ctx.db_user_id, limit=3)

        text = (
            "🧑‍💼 <b>پنل نمایندگی شما</b>\n\n"
            "🔗 کد دعوت: <code>{code}</code>\n"
            "👥 تعداد دعوت‌شدگان: <b>{n}</b>\n"
            "💰 موجودی: <b>{bal}</b>\n\n"
            "📊 <b>آمار عملکرد:</b>\n"
            "• فروش مستقیم: {s} مورد\n"
            "• کمیسیون دریافتی: {c}\n"
            "• دعوت‌های امروز: {td}\n"
            "• دعوت‌های این هفته: {tw}\n"
        ).format(
            code=ref_code, n=refs, bal=_money(bal),
            s=stats.get("direct_sales", 0),
            c=_money(stats.get("total_commission", 0)),
            td=stats.get("today_refs", 0),
            tw=stats.get("week_refs", 0),
        )

        if recent_refs:
            text += "\n📋 آخرین دعوت‌شدگان:\n"
            for r in recent_refs:
                text += "  • {} ({})\n".format(
                    r.get("first_name") or "-", r["created_at"][:10])

        kb = inline([
            [("🔄 رفرش", "res_pnl:refresh:0")],
            [("👥 لیست دعوت‌شدگان", "res_pnl:reflist:0")],
            [("📊 آمار فروش", "res_pnl:sales:0")],
            [("🔗 لینک دعوت", "res_pnl:link:0")],
            [("💳 برداشت کمیسیون", "res_pnl:withdraw:0")],
        ])
        ctx.reply(text, reply_markup=kb, parse_mode="HTML")

    def _show_referrals(ctx):
        rows = list_referrals(ctx.db_user_id, limit=30)
        if not rows:
            ctx.reply("👥 هنوز کسی با کد شما عضو نشده.")
            return
        text = "👥 <b>لیست دعوت‌شدگان ({})</b>\n\n".format(len(rows))
        for i, r in enumerate(rows, 1):
            text += "{}. {} (id:{}) — {}\n".format(
                i, r.get("first_name") or "-", r["bale_user_id"],
                r["created_at"][:10])
        ctx.reply(text, parse_mode="HTML")

    # ========================================================
    # Reseller callback handlers
    # ========================================================
    @mother_router.callback("res_pnl:")
    def _res_pnl_cb(ctx):
        action = ctx.data.split(":")[1]
        ctx.answer_callback()

        if action == "refresh":
            _show_reseller_panel(ctx)

        elif action == "reflist":
            rows = list_referrals(ctx.db_user_id, limit=30)
            if not rows:
                ctx.edit("👥 هنوز کسی با کد شما عضو نشده.")
                return
            text = "👥 <b>لیست دعوت‌شدگان</b>\n\n"
            for r in rows:
                text += "  • {} — {}\n".format(
                    r.get("first_name") or "-", r["created_at"][:10])
            ctx.edit(text, reply_markup=inline([
                [("🔙 بازگشت", "res_pnl:refresh:0")]
            ]), parse_mode="HTML")

        elif action == "sales":
            txs = list_transactions(ctx.db_user_id, limit=15)
            bal = get_balance(ctx.db_user_id)
            commission_txs = [t for t in txs if t["type"] == "commission"]

            text = "📊 <b>آمار فروش و درآمد</b>\n\n"
            text += "💰 موجودی قابل برداشت: {}\n\n".format(_money(bal))
            if commission_txs:
                total_comm = sum(abs(t["amount"]) for t in commission_txs)
                text += "💵 مجموع کمیسیون: {}\n".format(_money(total_comm))
                text += "📑 آخرین پورسانت‌ها:\n"
                for t in commission_txs[:5]:
                    text += "  ➕ {:,} | {}\n".format(
                        abs(t["amount"]), t["created_at"][:10])
            else:
                text += "هنوز پورسانتی ثبت نشده است.\n"
                text += "💡 دوستان خود را دعوت کنید و از فروش کمیسیون بگیرید!"
            ctx.edit(text, reply_markup=inline([
                [("🔙 بازگشت", "res_pnl:refresh:0")]
            ]), parse_mode="HTML")

        elif action == "link":
            code = make_ref_code(ctx.db_user_id)
            link = code
            try:
                from core.bot_manager import bot_manager as bm
                api = bm.get_mother_api()
                if api:
                    me = api.get_me()
                    link = "https://ble.ir/{}?start={}".format(
                        me.get("username", ""), code)
            except Exception:
                pass
            ctx.edit(
                "🔗 <b>لینک دعوت اختصاصی شما</b>\n\n"
                "<code>{}</code>\n\n"
                "📱 این لینک را برای دوستانتان بفرستید.\n"
                "💰 با هر خرید آنها، کمیسیون دریافت می‌کنید.".format(link),
                reply_markup=inline([
                    [("🔄 رفرش", "res_pnl:refresh:0")]
                ]), parse_mode="HTML")

        elif action == "withdraw":
            bal = get_balance(ctx.db_user_id)
            if bal <= 0:
                ctx.edit("❌ موجودی قابل برداشتی ندارید.")
                return
            from core.notifications import notify_super_admins
            notify_super_admins(
                "💰 <b>درخواست برداشت کمیسیون</b>\n\n"
                "👤 نماینده #{id}\n"
                "💰 مبلغ: {bal}\n\n"
                "برای پرداخت با نماینده هماهنگ کنید.".format(
                    id=ctx.db_user_id, bal=_money(bal)),
                parse_mode="HTML")
            ctx.edit(
                "✅ <b>درخواست برداشت ثبت شد</b>\n\n"
                "اطلاعات به مدیر ارسال شد.\n"
                "به زودی برای برداشت با شما تماس گرفته می‌شود.",
                reply_markup=inline([
                    [("🔙 بازگشت", "res_pnl:refresh:0")]
                ]))

    # ========================================================
    # Admin panel: Reseller management
    # ========================================================
    @mother_router.command("resellers")
    def _admin_resellers(ctx):
        if not is_super_admin(ctx.user_id):
            return
        _show_admin_reseller_panel(ctx)

    def _show_admin_reseller_panel(ctx):
        resellers = db.fetchall(
            """SELECT u.*, a.role, a.created_at as admin_since
               FROM admins a JOIN users u ON u.id = a.user_id
               WHERE a.role='reseller'
               ORDER BY a.id DESC"""
        )

        text = "🧑‍💼 <b>مدیریت نمایندگان</b>\n\n"
        kb = []

        if resellers:
            text += "تعداد: {} نماینده\n\n".format(len(resellers))
            for r in resellers:
                name = r.get("first_name") or "-"
                refs = count_referrals(r["id"])
                bal = get_balance(r["id"])
                text += "• {} — دعوت: {} | کیف پول: {}\n".format(
                    name, refs, _money(bal))
                kb.append([(
                    "{} (id:{})".format(name, r["bale_user_id"]),
                    "adm_res:detail:{}".format(r["id"])
                )])
        else:
            text += "هیچ نماینده‌ای ثبت نشده است.\n\n"

        kb.append([("➕ افزودن نماینده", "adm_res:add:0")])
        kb.append([("⚙️ تنظیمات کمیسیون", "adm_res:settings:0")])
        ctx.reply(text, reply_markup=inline(kb), parse_mode="HTML")

    @mother_router.callback("adm_res:")
    def _adm_res_cb(ctx):
        if not is_super_admin(ctx.user_id):
            ctx.answer_callback("⛔", show_alert=True)
            return
        parts = ctx.data.split(":")
        action = parts[1]
        ctx.answer_callback()

        if action == "detail" and len(parts) >= 3:
            _show_reseller_detail(ctx, int(parts[2]))

        elif action == "add":
            state_manager.set(ctx.bot_id, ctx.user_id, "admin:reseller:add", {})
            ctx.edit(
                "➕ <b>افزودن نماینده جدید</b>\n\n"
                "آی‌دی عددی بله کاربر مورد نظر را ارسال کنید:\n"
                "/cancel برای انصراف",
                parse_mode="HTML")

        elif action == "remove" and len(parts) >= 3:
            from core.permission_manager import revoke_admin
            revoke_admin(int(parts[2]))
            ctx.edit("✅ نماینده حذف شد.")
            _show_admin_reseller_panel(ctx)

        elif action == "settings":
            from reseller.affiliate_manager import _get_percent
            pct = _get_percent()
            state_manager.set(ctx.bot_id, ctx.user_id, "admin:reseller:percent", {})
            ctx.edit(
                "⚙️ <b>تنظیمات کمیسیون</b>\n\n"
                "درصد فعلی: <b>{}%</b>\n\n"
                "درصد جدید (۰-۱۰۰) را ارسال کنید:".format(pct),
                parse_mode="HTML")

        elif action == "list":
            _show_admin_reseller_panel(ctx)

    def _show_reseller_detail(ctx, user_id):
        u = db.fetchone("SELECT * FROM users WHERE id=?", (int(user_id),))
        if not u:
            ctx.edit("کاربر یافت نشد.")
            return
        bal = get_balance(u["id"])
        refs = count_referrals(u["id"])
        stats = get_reseller_stats(u["id"])
        referrals = list_referrals(u["id"], limit=5)

        text = (
            "🧑‍💼 <b>جزییات نماینده</b>\n\n"
            "👤 {nm} (@{un})\n"
            "🆔 {bid}\n\n"
            "📊 <b>آمار:</b>\n"
            "👥 دعوت‌شدگان: {n}\n"
            "💰 موجودی: {bal}\n"
            "💵 مجموع کمیسیون: {comm}\n"
            "📈 فروش مستقیم: {s}\n"
        ).format(
            nm=u.get("first_name") or "-",
            un=u.get("username") or "-",
            bid=u["bale_user_id"],
            n=refs, bal=_money(bal),
            comm=_money(stats.get("total_commission", 0)),
            s=stats.get("direct_sales", 0),
        )

        if referrals:
            text += "\n📋 آخرین دعوت‌شدگان:\n"
            for r in referrals:
                text += "  • {} ({})\n".format(
                    r.get("first_name") or "-", r["created_at"][:10])

        kb = inline([
            [("❌ حذف نمایندگی", "adm_res:remove:{}".format(u["id"]))],
            [("🔙 بازگشت", "adm_res:list:0")],
        ])
        ctx.edit(text, reply_markup=kb, parse_mode="HTML")

    # FSM handlers
    @text_input_bus.on("admin:reseller:add")
    def _on_reseller_add(ctx):
        s = (ctx.text or "").strip()
        if not s.isdigit():
            ctx.reply("❌ آی‌دی باید عدد باشد. /cancel"); return
        u = db.fetchone("SELECT * FROM users WHERE bale_user_id=?", (int(s),))
        state_manager.clear(ctx.bot_id, ctx.user_id)
        if not u:
            ctx.reply(
                "⚠️ کاربری با این آی‌دی هنوز در ربات /start نزده است.\n"
                "ابتدا از او بخواهید /start بفرستد، سپس مجدد امتحان کنید."
            )
            return
        from core.permission_manager import grant_admin, ROLE_RESELLER
        grant_admin(u["id"], role=ROLE_RESELLER)
        ctx.reply("✅ کاربر به نماینده ارتقا یافت.")
        _show_reseller_detail(ctx, u["id"])

    @text_input_bus.on("admin:reseller:percent")
    def _on_reseller_percent(ctx):
        s = (ctx.text or "").strip()
        if not s.isdigit() or int(s) < 0 or int(s) > 100:
            ctx.reply("❌ عدد بین ۰ تا ۱۰۰ وارد کنید. /cancel")
            return
        from reseller.affiliate_manager import set_percent
        set_percent(int(s))
        state_manager.clear(ctx.bot_id, ctx.user_id)
        ctx.reply("✅ درصد پورسانت روی {}% تنظیم شد.".format(s))
