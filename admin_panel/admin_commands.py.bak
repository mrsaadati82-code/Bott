# ============================================================
# admin_panel/admin_commands.py
# ============================================================
# Full inline-button driven admin panel.
# All FSM free-text inputs go through state_manager.text_input_bus
# (no more colliding regex handlers).
# ============================================================

import json

from core.router import mother_router
from core.keyboards import reply_keyboard, inline, remove_keyboard
from core.permission_manager import (
    get_role, is_super_admin,
    ROLE_ADMIN, ROLE_SUPER_ADMIN, ROLE_RESELLER,
    grant_admin, revoke_admin,
)
from core.state_manager import state_manager, text_input_bus
from database.db import db

from monitoring.analytics import (
    total_users, total_bots, total_revenue, total_transactions,
    total_subscriptions, daily_user_growth,
)
from subscriptions.plan_manager import list_plans, get_plan, update_plan
from subscriptions.subscription_manager import list_user_subscriptions
from wallet.wallet_manager import (
    get_balance, credit, debit,
    create_gift_code, list_gift_codes,
)
from payments.payment_manager import (
    list_pending as list_pending_payments, approve, reject,
)
from reseller.affiliate_manager import (
    pay_commission_for, set_percent, _get_percent,
    count_referrals,
)

from admin_panel.admin_router import (
    ADMIN_KEYBOARD,
    BTN_USERS, BTN_BOTS, BTN_PLANS, BTN_SUBS, BTN_PAYMENTS, BTN_WALLETS,
    BTN_GIFTS, BTN_TEMPLATES, BTN_MODULES, BTN_CHANNEL_LOCK,
    BTN_BROADCAST, BTN_STATS, BTN_RESELLERS, BTN_SETTINGS, BTN_BACK,
)


# ============================================================
# Helpers
# ============================================================
def _is_admin(ctx) -> bool:
    if not ctx.user_id:
        return False
    return get_role(ctx.user_id) in (ROLE_ADMIN, ROLE_SUPER_ADMIN, ROLE_RESELLER)


def _is_super(ctx) -> bool:
    return ctx.user_id and is_super_admin(ctx.user_id)


def _money(n: int) -> str:
    return "{:,} ریال".format(int(n))


def _user_label(u: dict) -> str:
    name = (u.get("first_name") or "") + (" " + u.get("last_name") if u.get("last_name") else "")
    name = name.strip() or "-"
    uname = "@" + u["username"] if u.get("username") else ""
    return "{} {} (id={})".format(name, uname, u["bale_user_id"])


# ============================================================
# Public entrypoint
# ============================================================
def setup():

    # --------------------------------------------------------
    # /admin command
    # --------------------------------------------------------
    @mother_router.command("admin")
    def _open_admin(ctx):
        if not _is_admin(ctx):
            ctx.reply("⛔ شما به پنل ادمین دسترسی ندارید.")
            return
        role = get_role(ctx.user_id)
        ctx.reply(
            "🛠 پنل ادمین\n"
            "نقش شما: {}\n\n"
            "یکی از گزینه‌های زیر را انتخاب کنید:".format(role),
            reply_markup=ADMIN_KEYBOARD,
        )

    # ========================================================
    # STATS
    # ========================================================
    @mother_router.text(BTN_STATS)
    def _stats(ctx):
        if not _is_admin(ctx):
            return
        growth = daily_user_growth(7)
        growth_line = " | ".join("{}:{}".format(d[-5:], c) for d, c in growth) or "(خالی)"
        msg = (
            "📊 آمار سیستم\n\n"
            "👥 کاربران: {u}\n"
            "🤖 ربات‌های فعال: {b}\n"
            "🎟 اشتراک‌های فعال: {s}\n"
            "💳 تعداد تراکنش‌ها: {t}\n"
            "💰 درآمد کل: {r}\n\n"
            "📈 رشد کاربران ۷ روز اخیر:\n{g}"
        ).format(
            u=total_users(), b=total_bots(), s=total_subscriptions(),
            t=total_transactions(), r=_money(total_revenue()), g=growth_line,
        )
        ctx.reply(msg, reply_markup=ADMIN_KEYBOARD)

    # ========================================================
    # USERS
    # ========================================================
    @mother_router.text(BTN_USERS)
    def _users(ctx):
        if not _is_admin(ctx):
            return
        _show_users_page(ctx, page=0)

    def _show_users_page(ctx, page: int = 0, per_page: int = 8):
        offset = page * per_page
        rows = db.fetchall(
            "SELECT * FROM users ORDER BY id DESC LIMIT ? OFFSET ?",
            (per_page, offset),
        )
        total = db.fetchone("SELECT COUNT(*) AS c FROM users")["c"]
        if not rows:
            ctx.reply("کاربری یافت نشد.", reply_markup=ADMIN_KEYBOARD)
            return
        text = "👥 کاربران (صفحه {} / مجموع {}):".format(page + 1, total)
        kb = []
        for u in rows:
            label = "{} | id={}".format(u.get("first_name") or "-", u["bale_user_id"])
            kb.append([(label, "uadm:open:{}".format(u["id"]))])
        nav = []
        if page > 0:
            nav.append(("◀️ قبلی", "uadm:page:{}".format(page - 1)))
        if (page + 1) * per_page < total:
            nav.append(("بعدی ▶️", "uadm:page:{}".format(page + 1)))
        if nav:
            kb.append(nav)
        kb.append([("🔍 جستجو با آی‌دی", "uadm:search:0")])
        ctx.reply(text, reply_markup=inline(kb))

    @mother_router.callback("uadm:")
    def _uadm(ctx):
        if not _is_admin(ctx):
            ctx.answer_callback("⛔", show_alert=True); return
        parts = ctx.data.split(":", 3)
        action = parts[1]
        ctx.answer_callback()
        if action == "page":
            _show_users_page(ctx, int(parts[2]))
        elif action == "search":
            state_manager.set(ctx.bot_id, ctx.user_id, "admin:user:search")
            ctx.reply("آی‌دی عددی بله را ارسال کنید:")
        elif action == "open":
            _show_user_detail(ctx, int(parts[2]))
        elif action == "block":
            db.execute("UPDATE users SET is_blocked=1 WHERE id=?", (int(parts[2]),))
            ctx.reply("🚫 کاربر بلاک شد.")
            _show_user_detail(ctx, int(parts[2]))
        elif action == "unblock":
            db.execute("UPDATE users SET is_blocked=0 WHERE id=?", (int(parts[2]),))
            ctx.reply("✅ کاربر آنبلاک شد.")
            _show_user_detail(ctx, int(parts[2]))
        elif action == "credit":
            state_manager.set(ctx.bot_id, ctx.user_id, "admin:wallet:credit",
                              {"user_id": int(parts[2])})
            ctx.reply("💰 مبلغ شارژ (ریال) را ارسال کنید:\n/cancel برای انصراف")
        elif action == "debit":
            state_manager.set(ctx.bot_id, ctx.user_id, "admin:wallet:debit",
                              {"user_id": int(parts[2])})
            ctx.reply("💸 مبلغ کسر (ریال) را ارسال کنید:\n/cancel برای انصراف")
        elif action == "makeadmin":
            if not _is_super(ctx):
                ctx.reply("⛔ فقط سوپرادمین.")
                return
            grant_admin(int(parts[2]), role=ROLE_ADMIN)
            ctx.reply("✅ به ادمین ارتقا یافت.")
            _show_user_detail(ctx, int(parts[2]))
        elif action == "makereseller":
            if not _is_super(ctx):
                ctx.reply("⛔ فقط سوپرادمین.")
                return
            grant_admin(int(parts[2]), role=ROLE_RESELLER)
            ctx.reply("✅ به نماینده ارتقا یافت.")
            _show_user_detail(ctx, int(parts[2]))
        elif action == "revoke":
            if not _is_super(ctx):
                ctx.reply("⛔ فقط سوپرادمین.")
                return
            revoke_admin(int(parts[2]))
            ctx.reply("✅ نقش حذف شد.")
            _show_user_detail(ctx, int(parts[2]))

    def _show_user_detail(ctx, user_id: int):
        u = db.fetchone("SELECT * FROM users WHERE id=?", (int(user_id),))
        if not u:
            ctx.reply("کاربر یافت نشد.")
            return
        bal = get_balance(u["id"])
        bots_count = db.fetchone(
            "SELECT COUNT(*) AS c FROM bots WHERE owner_id=?", (u["id"],)
        )["c"]
        subs = list_user_subscriptions(u["id"])
        active_sub = next((s for s in subs if s["status"] == "active"), None)
        role = get_role(int(u["bale_user_id"]))
        refs = count_referrals(u["id"])

        text = (
            "👤 کاربر #{id}\n"
            "{lbl}\n\n"
            "🎭 نقش: {r}\n"
            "💰 موجودی: {bal}\n"
            "🤖 تعداد ربات: {bc}\n"
            "🎟 اشتراک فعال: {sub}\n"
            "🎯 دعوت‌شدگان: {rf}\n"
            "🚫 بلاک: {bl}"
        ).format(
            id=u["id"], lbl=_user_label(u), r=role, bal=_money(bal),
            bc=bots_count, sub=("بله #" + str(active_sub["id"]) if active_sub else "خیر"),
            rf=refs, bl=("بله" if int(u.get("is_blocked") or 0) else "خیر"),
        )

        kb = [
            [("➕ شارژ کیف پول", "uadm:credit:{}".format(u["id"])),
             ("➖ کسر کیف پول",  "uadm:debit:{}".format(u["id"]))],
            [
                ("✅ آنبلاک" if int(u.get("is_blocked") or 0) else "🚫 بلاک",
                 "uadm:{}:{}".format("unblock" if int(u.get("is_blocked") or 0) else "block", u["id"])),
            ],
        ]
        if _is_super(ctx):
            if role == "user":
                kb.append([("⬆️ ارتقا به ادمین",   "uadm:makeadmin:{}".format(u["id"]))])
                kb.append([("⬆️ ارتقا به نماینده", "uadm:makereseller:{}".format(u["id"]))])
            else:
                kb.append([("❌ حذف نقش", "uadm:revoke:{}".format(u["id"]))])
        kb.append([("🔙 لیست کاربران", "uadm:page:0")])

        ctx.reply(text, reply_markup=inline(kb))

    # FSM: search user
    @text_input_bus.on("admin:user:search")
    def _on_user_search(ctx):
        s = (ctx.text or "").strip()
        state_manager.clear(ctx.bot_id, ctx.user_id)
        if not s.isdigit():
            ctx.reply("❌ آی‌دی باید عدد باشد.")
            return
        u = db.fetchone("SELECT * FROM users WHERE bale_user_id=?", (int(s),))
        if not u:
            ctx.reply("کاربری با این آی‌دی یافت نشد.")
            return
        _show_user_detail(ctx, u["id"])

    # FSM: wallet credit/debit
    @text_input_bus.on("admin:wallet:credit")
    def _on_wallet_credit(ctx):
        _wallet_op(ctx, kind="credit")

    @text_input_bus.on("admin:wallet:debit")
    def _on_wallet_debit(ctx):
        _wallet_op(ctx, kind="debit")

    def _wallet_op(ctx, kind: str):
        data = state_manager.get_data(ctx.bot_id, ctx.user_id)
        target = int(data.get("user_id") or 0)
        s = (ctx.text or "").strip()
        if not s.isdigit() or int(s) <= 0:
            ctx.reply("❌ مبلغ باید عدد مثبت باشد. دوباره بفرستید یا /cancel")
            return
        amount = int(s)
        state_manager.clear(ctx.bot_id, ctx.user_id)
        try:
            if kind == "credit":
                r = credit(target, amount, tx_type="manual",
                           description="شارژ دستی توسط ادمین")
            else:
                r = debit(target, amount, tx_type="manual",
                          description="کسر دستی توسط ادمین")
            ctx.reply("✅ انجام شد.\nموجودی جدید: {}".format(_money(r["balance"])))
        except Exception as e:
            ctx.reply("❌ خطا: {}".format(e))
        _show_user_detail(ctx, target)

    # ========================================================
    # BOTS
    # ========================================================
    @mother_router.text(BTN_BOTS)
    def _bots(ctx):
        if not _is_admin(ctx):
            return
        rows = db.fetchall(
            """SELECT b.*, u.bale_user_id AS owner_bale FROM bots b
                 JOIN users u ON u.id=b.owner_id
                 ORDER BY b.id DESC LIMIT 15"""
        )
        if not rows:
            ctx.reply("هنوز ربات فرزندی ساخته نشده.", reply_markup=ADMIN_KEYBOARD)
            return
        text = "🤖 ربات‌های فرزند ({}):".format(len(rows))
        kb = []
        for r in rows:
            label = "@{} | owner={} | {}".format(
                r.get("bot_username") or "?", r["owner_bale"], r["status"]
            )
            kb.append([(label, "badm:open:{}".format(r["id"]))])
        ctx.reply(text, reply_markup=inline(kb))

    @mother_router.callback("badm:")
    def _badm(ctx):
        if not _is_admin(ctx):
            ctx.answer_callback("⛔", show_alert=True); return
        parts = ctx.data.split(":", 3)
        action = parts[1]
        bot_id = int(parts[2])
        b = db.fetchone("SELECT * FROM bots WHERE id=?", (bot_id,))
        if not b:
            ctx.answer_callback("یافت نشد", show_alert=True); return
        ctx.answer_callback()

        if action == "open":
            text = (
                "🤖 ربات #{id}\n"
                "@{u}\n"
                "👤 owner_id: {ow}\n"
                "📡 وضعیت: {st}\n"
                "📅 ساخت: {ca}"
            ).format(id=b["id"], u=b.get("bot_username") or "?",
                     ow=b["owner_id"], st=b["status"], ca=b["created_at"])
            kb = inline([
                [("⏸ توقف" if b["status"] == "active" else "▶️ راه‌اندازی",
                  "badm:toggle:{}".format(b["id"]))],
                [("🚫 بن کردن", "badm:ban:{}".format(b["id"])),
                 ("✅ رفع بن",  "badm:unban:{}".format(b["id"]))],
                [("🗑 حذف ربات", "badm:delete:{}".format(b["id"]))],
            ])
            ctx.reply(text, reply_markup=kb)
        elif action == "toggle":
            new = "paused" if b["status"] == "active" else "active"
            db.execute("UPDATE bots SET status=? WHERE id=?", (new, b["id"]))
            from core.bot_manager import bot_manager
            if new == "paused":
                bot_manager.stop_bot(b["id"])
            else:
                bot_manager.start_child(db.fetchone("SELECT * FROM bots WHERE id=?", (b["id"],)))
            ctx.reply("✅ وضعیت ربات به {} تغییر کرد.".format(new))
        elif action == "ban":
            db.execute("UPDATE bots SET status='banned' WHERE id=?", (b["id"],))
            from core.bot_manager import bot_manager
            bot_manager.stop_bot(b["id"])
            ctx.reply("🚫 ربات بن شد.")
        elif action == "unban":
            db.execute("UPDATE bots SET status='active' WHERE id=?", (b["id"],))
            from core.bot_manager import bot_manager
            bot_manager.start_child(db.fetchone("SELECT * FROM bots WHERE id=?", (b["id"],)))
            ctx.reply("✅ ربات از بن خارج شد.")
        elif action == "delete":
            from core.bot_manager import bot_manager
            bot_manager.stop_bot(b["id"])
            db.execute("DELETE FROM bots WHERE id=?", (b["id"],))
            ctx.reply("🗑 ربات حذف شد.")

    # ========================================================
    # PLANS
    # ========================================================
    @mother_router.text(BTN_PLANS)
    def _plans(ctx):
        if not _is_admin(ctx):
            return
        _show_plans_list(ctx)

    def _show_plans_list(ctx):
        rows = list_plans(only_active=False)
        if not rows:
            ctx.reply("پلنی تعریف نشده.", reply_markup=ADMIN_KEYBOARD); return
        text = "📦 پلن‌ها ({}):".format(len(rows))
        kb = []
        for p in rows:
            mark = "✅" if p["is_active"] else "⛔"
            label = "{} #{} {} | {}".format(mark, p["id"], p["name"], _money(p["price"]))
            kb.append([(label, "padm:open:{}".format(p["id"]))])
        ctx.reply(text, reply_markup=inline(kb))

    @mother_router.callback("padm:")
    def _padm(ctx):
        if not _is_admin(ctx):
            ctx.answer_callback("⛔", show_alert=True); return
        parts = ctx.data.split(":", 4)
        action = parts[1]
        ctx.answer_callback()

        if action == "list":
            _show_plans_list(ctx); return
        if action == "open":
            _show_plan_detail(ctx, int(parts[2])); return
        if action == "toggle":
            p = get_plan(int(parts[2]))
            update_plan(p["id"], is_active=0 if p["is_active"] else 1)
            _show_plan_detail(ctx, int(parts[2])); return
        if action == "setprice":
            if not _is_super(ctx):
                ctx.reply("⛔ فقط سوپرادمین."); return
            state_manager.set(ctx.bot_id, ctx.user_id, "admin:plan:setprice",
                              {"plan_id": int(parts[2])})
            ctx.reply("💰 قیمت جدید (ریال) را ارسال کنید:\n/cancel برای انصراف")
            return
        if action == "setlimit":
            if not _is_super(ctx):
                ctx.reply("⛔ فقط سوپرادمین."); return
            plan_id = int(parts[2])
            p = get_plan(plan_id)
            kb = inline([
                [("max_bots ({})".format(p["max_bots"]),
                  "padm:setfield:max_bots:{}".format(plan_id))],
                [("max_users_per_bot ({})".format(p["max_users_per_bot"]),
                  "padm:setfield:max_users_per_bot:{}".format(plan_id))],
                [("max_monthly_messages ({})".format(p["max_monthly_messages"]),
                  "padm:setfield:max_monthly_messages:{}".format(plan_id))],
                [("🔙 بازگشت", "padm:open:{}".format(plan_id))],
            ])
            ctx.reply("کدام محدودیت را تغییر می‌دهید؟", reply_markup=kb); return
        if action == "setfield" and len(parts) >= 4:
            field = parts[2]
            plan_id = int(parts[3])
            state_manager.set(ctx.bot_id, ctx.user_id, "admin:plan:setfield",
                              {"plan_id": plan_id, "field": field})
            ctx.reply("مقدار جدید برای «{}» را ارسال کنید:".format(field))

    def _show_plan_detail(ctx, plan_id: int):
        p = get_plan(plan_id)
        if not p:
            ctx.reply("پلن یافت نشد."); return
        text = (
            "📦 پلن #{id} - {nm}\n"
            "{desc}\n\n"
            "⏱ مدت: {d} روز\n"
            "💰 قیمت: {pr}\n"
            "🤖 max_bots: {mb}\n"
            "👥 max_users_per_bot: {mu}\n"
            "💬 max_monthly_messages: {mm}\n"
            "وضعیت: {st}"
        ).format(
            id=p["id"], nm=p["name"], desc=p.get("description") or "-",
            d=p["duration_days"], pr=_money(p["price"]),
            mb=p["max_bots"], mu=p["max_users_per_bot"], mm=p["max_monthly_messages"],
            st="✅ فعال" if p["is_active"] else "⛔ غیرفعال",
        )
        kb = []
        if _is_super(ctx):
            kb.append([
                ("✏️ تغییر قیمت", "padm:setprice:{}".format(p["id"])),
                ("📏 محدودیت‌ها",  "padm:setlimit:{}".format(p["id"])),
            ])
            kb.append([
                ("⛔ غیرفعال" if p["is_active"] else "✅ فعال",
                 "padm:toggle:{}".format(p["id"])),
            ])
        kb.append([("🔙 بازگشت", "padm:list:")])
        ctx.reply(text, reply_markup=inline(kb))

    @text_input_bus.on("admin:plan:setprice")
    def _on_plan_setprice(ctx):
        data = state_manager.get_data(ctx.bot_id, ctx.user_id)
        s = (ctx.text or "").strip()
        if not s.isdigit():
            ctx.reply("❌ قیمت باید عدد باشد. دوباره بفرستید یا /cancel"); return
        update_plan(int(data["plan_id"]), price=int(s))
        state_manager.clear(ctx.bot_id, ctx.user_id)
        ctx.reply("✅ قیمت به‌روزرسانی شد.")
        _show_plan_detail(ctx, int(data["plan_id"]))

    @text_input_bus.on("admin:plan:setfield")
    def _on_plan_setfield(ctx):
        data = state_manager.get_data(ctx.bot_id, ctx.user_id)
        s = (ctx.text or "").strip()
        if not s.isdigit():
            ctx.reply("❌ مقدار باید عدد باشد. دوباره بفرستید یا /cancel"); return
        update_plan(int(data["plan_id"]), **{data["field"]: int(s)})
        state_manager.clear(ctx.bot_id, ctx.user_id)
        ctx.reply("✅ {} به‌روزرسانی شد.".format(data["field"]))
        _show_plan_detail(ctx, int(data["plan_id"]))

    # ========================================================
    # SUBSCRIPTIONS
    # ========================================================
    @mother_router.text(BTN_SUBS)
    def _subs(ctx):
        if not _is_admin(ctx):
            return
        rows = db.fetchall(
            """SELECT s.*, u.bale_user_id, p.name AS plan_name
                 FROM subscriptions s
                 JOIN users u ON u.id=s.user_id
                 JOIN plans p ON p.id=s.plan_id
                 ORDER BY s.id DESC LIMIT 15"""
        )
        if not rows:
            ctx.reply("اشتراکی ثبت نشده.", reply_markup=ADMIN_KEYBOARD); return
        text = "🎟 اشتراک‌های اخیر:\n\n"
        for s in rows:
            text += "#{} | user={} | {} | تا {} | {}\n".format(
                s["id"], s["bale_user_id"], s["plan_name"],
                s["ends_at"][:10], s["status"],
            )
        ctx.reply(text, reply_markup=ADMIN_KEYBOARD)

    # ========================================================
    # PAYMENTS
    # ========================================================
    @mother_router.text(BTN_PAYMENTS)
    def _payments(ctx):
        if not _is_admin(ctx):
            return
        pendings = list_pending_payments(limit=10)
        if not pendings:
            ctx.reply("✅ هیچ پرداختی در انتظار تایید نیست.", reply_markup=ADMIN_KEYBOARD)
            return
        ctx.reply("💳 پرداخت‌های در انتظار ({}):".format(len(pendings)),
                  reply_markup=ADMIN_KEYBOARD)
        for p in pendings:
            u = db.fetchone("SELECT * FROM users WHERE id=?", (p["user_id"],))
            ctx.reply(
                "💳 پرداخت #{id}\n"
                "👤 {ul}\n"
                "💰 {amt}\n"
                "🔧 روش: {m}\n"
                "📎 ref: {ref}".format(
                    id=p["id"], ul=_user_label(u) if u else "-",
                    amt=_money(p["amount"]), m=p["method_key"],
                    ref=p.get("gateway_ref") or "-",
                ),
                reply_markup=inline([
                    [("✅ تایید", "pay:ok:{}".format(p["id"])),
                     ("❌ رد",   "pay:no:{}".format(p["id"]))],
                ]),
            )

    @mother_router.callback("pay:")
    def _pay_decision(ctx):
        if not _is_admin(ctx):
            ctx.answer_callback("⛔", show_alert=True); return
        parts = ctx.data.split(":")
        action = parts[1]
        pid = int(parts[2])
        if action == "ok":
            approve(pid)
            pay_commission_for(pid)
            ctx.answer_callback("تایید شد ✅")
            ctx.reply("✅ پرداخت #{} تایید و تخصیص داده شد.".format(pid))
        elif action == "no":
            reject(pid, reason="رد توسط مدیر")
            ctx.answer_callback("رد شد ❌")
            ctx.reply("❌ پرداخت #{} رد شد.".format(pid))
        elif action == "view":
            _show_payment_detail(ctx, pid)

    def _show_payment_detail(ctx, pid: int):
        from payments.payment_manager import get_payment, get_method
        from payments.card_to_card import get_receipt
        p = get_payment(pid)
        if not p:
            ctx.reply("پرداخت یافت نشد."); return
        u = db.fetchone("SELECT * FROM users WHERE id=?", (p["user_id"],))
        method = get_method(p["method_key"])
        text = (
            "💳 <b>جزییات پرداخت #{id}</b>\n\n"
            "👤 کاربر: {nm} (id={bid})\n"
            "💰 مبلغ: {amt}\n"
            "🔧 روش: {m}\n"
            "📅 ایجاد: {ca}\n"
            "📡 وضعیت: {st}"
        ).format(
            id=p["id"],
            nm=(u.get("first_name") or "-") if u else "-",
            bid=(u.get("bale_user_id") or "-") if u else "-",
            amt=_money(p["amount"]),
            m=method["name"] if method else p["method_key"],
            ca=p["created_at"][:16], st=p["status"],
        )
        receipt = get_receipt(pid) if p["method_key"] == "card_to_card" else None
        if receipt:
            text += "\n\n🧾 رسید:\n🔢 شماره پیگیری: {}".format(receipt.get("tracking_code") or "-")
        kb = []
        if p["status"] == "pending":
            kb.append([
                ("✅ تایید", "pay:ok:{}".format(p["id"])),
                ("❌ رد",    "pay:no:{}".format(p["id"])),
            ])
        if receipt and receipt.get("photo_file_id"):
            try:
                ctx.api.call("sendPhoto", {
                    "chat_id": ctx.chat_id,
                    "photo": receipt["photo_file_id"],
                    "caption": text,
                    "parse_mode": "HTML",
                    "reply_markup": inline(kb) if kb else None,
                })
                return
            except Exception:
                pass
        ctx.reply(text, reply_markup=inline(kb) if kb else None, parse_mode="HTML")

    # ========================================================
    # WALLETS
    # ========================================================
    @mother_router.text(BTN_WALLETS)
    def _wallets(ctx):
        if not _is_admin(ctx):
            return
        rows = db.fetchall(
            """SELECT w.*, u.bale_user_id, u.first_name
                 FROM wallets w JOIN users u ON u.id=w.user_id
                 ORDER BY w.balance DESC LIMIT 15"""
        )
        if not rows:
            ctx.reply("کیف پولی یافت نشد.", reply_markup=ADMIN_KEYBOARD); return
        text = "👛 برترین کیف‌پول‌ها (روی هر کدام بزنید):"
        kb = []
        for r in rows:
            label = "{} | {}".format(r.get("first_name") or "-", _money(r["balance"]))
            kb.append([(label, "uadm:open:{}".format(r["user_id"]))])
        ctx.reply(text, reply_markup=inline(kb))

    # ========================================================
    # GIFT CODES
    # ========================================================
    @mother_router.text(BTN_GIFTS)
    def _gifts(ctx):
        if not _is_admin(ctx):
            return
        _show_gifts(ctx)

    def _show_gifts(ctx):
        rows = list_gift_codes(limit=10)
        text = "🎁 آخرین کدهای هدیه ({}):\n\n".format(len(rows))
        if rows:
            for g in rows:
                text += "{ico} {code} | {amt} | {used}/{max}\n".format(
                    ico="✅" if g["is_active"] else "⛔",
                    code=g["code"], amt=_money(g["amount"]),
                    used=g["used_count"], max=g["max_uses"],
                )
        else:
            text += "(خالی)"
        kb = inline([
            [("➕ ساخت کد هدیه جدید", "gift:new")],
            [("🔄 رفرش", "gift:list")],
        ])
        ctx.reply(text, reply_markup=kb)

    @mother_router.callback("gift:")
    def _gift_cb(ctx):
        if not _is_admin(ctx):
            ctx.answer_callback("⛔", show_alert=True); return
        action = ctx.data.split(":", 2)[1]
        ctx.answer_callback()
        if action == "list":
            _show_gifts(ctx)
        elif action == "new":
            state_manager.set(ctx.bot_id, ctx.user_id, "admin:gift:amount", {})
            ctx.reply("💰 مبلغ کد هدیه (ریال) را ارسال کنید:\n/cancel برای انصراف")

    @text_input_bus.on("admin:gift:amount")
    def _gift_amount(ctx):
        s = (ctx.text or "").strip()
        if not s.isdigit() or int(s) <= 0:
            ctx.reply("❌ مبلغ باید عدد مثبت باشد."); return
        state_manager.set(ctx.bot_id, ctx.user_id, "admin:gift:maxuses",
                          {"amount": int(s)})
        ctx.reply("🔢 سقف استفاده (تعداد دفعاتی که می‌تواند ریدیم شود)؟\n"
                  "برای یکبار مصرف عدد 1 بفرستید.")

    @text_input_bus.on("admin:gift:maxuses")
    def _gift_maxuses(ctx):
        data = state_manager.get_data(ctx.bot_id, ctx.user_id)
        s = (ctx.text or "").strip()
        if not s.isdigit() or int(s) <= 0:
            ctx.reply("❌ سقف باید عدد مثبت باشد."); return
        amount = int(data["amount"])
        max_uses = int(s)
        state_manager.clear(ctx.bot_id, ctx.user_id)
        g = create_gift_code(amount=amount, max_uses=max_uses)
        ctx.reply(
            "✅ کد هدیه ساخته شد:\n\n"
            "🎁 کد: <code>{c}</code>\n"
            "💰 مبلغ: {a}\n"
            "🔢 سقف: {m}\n\n"
            "کاربر می‌تواند با /gift {c} ریدیم کند.".format(
                c=g["code"], a=_money(amount), m=max_uses,
            ),
            parse_mode="HTML",
        )

    # ========================================================
    # TEMPLATES (delegated)
    # ========================================================
    @mother_router.text(BTN_TEMPLATES)
    def _templates_btn(ctx):
        if not _is_admin(ctx):
            return
        from admin_panel import template_admin
        template_admin._send_templates_list(ctx)

    # ========================================================
    # MODULES
    # ========================================================
    @mother_router.text(BTN_MODULES)
    def _modules(ctx):
        if not _is_admin(ctx):
            return
        from modules.module_registry import module_registry
        mods = module_registry.all()
        if not mods:
            ctx.reply(
                "⚙️ هیچ ماژولی نصب نشده است.\n\n"
                "برای افزودن ماژول جدید، یک فایل .py در پوشه\n"
                "<code>modules/builtin/</code> قرار دهید.\n"
                "(راهنما در README_SETUP.md)",
                parse_mode="HTML",
                reply_markup=ADMIN_KEYBOARD,
            )
            return
        text = "⚙️ ماژول‌های نصب‌شده ({}):\n\n".format(len(mods))
        for m in mods:
            text += "• {} v{} - {}\n".format(m.key, m.version, m.name)
        ctx.reply(text, reply_markup=ADMIN_KEYBOARD)

    # ========================================================
    # CHANNEL LOCKS
    # ========================================================
    @mother_router.text(BTN_CHANNEL_LOCK)
    def _channel_lock(ctx):
        if not _is_admin(ctx):
            return
        rows = db.fetchall(
            """SELECT c.*, b.bot_username FROM channel_locks c
                 LEFT JOIN bots b ON b.id=c.bot_id
                 ORDER BY c.id DESC LIMIT 20"""
        )
        if not rows:
            ctx.reply(
                "📣 هیچ قفل کانالی در سیستم وجود ندارد.\n\n"
                "کاربران از داشبورد ربات‌های خود این را تنظیم می‌کنند.",
                reply_markup=ADMIN_KEYBOARD,
            )
            return
        text = "📣 قفل‌های کانال ({}):\n\n".format(len(rows))
        for r in rows:
            text += "• @{} → {} (required={})\n".format(
                r.get("bot_username") or "?",
                r["channel_id"], r["is_required"],
            )
        ctx.reply(text, reply_markup=ADMIN_KEYBOARD)

    # ========================================================
    # BROADCAST
    # ========================================================
    @mother_router.text(BTN_BROADCAST)
    def _broadcast_menu(ctx):
        if not _is_admin(ctx):
            return
        kb = inline([
            [("📤 ارسال به همه کاربران",  "bc:target:all")],
            [("⚡ ارسال به کاربران فعال", "bc:target:active")],
            [("🔙 بازگشت",                "bc:cancel:0")],
        ])
        ctx.reply("📢 Broadcast\n\nهدف ارسال را انتخاب کنید:", reply_markup=kb)

    @mother_router.callback("bc:")
    def _bc_cb(ctx):
        if not _is_admin(ctx):
            ctx.answer_callback("⛔", show_alert=True); return
        parts = ctx.data.split(":", 3)
        action = parts[1]
        ctx.answer_callback()
        if action == "target":
            target = parts[2]
            state_manager.set(ctx.bot_id, ctx.user_id, "admin:bc:text",
                              {"target": target})
            ctx.reply(
                "✏️ متن پیام Broadcast را ارسال کنید.\n"
                "هدف: {}\n\n/cancel برای انصراف".format(target)
            )
        elif action == "cancel":
            state_manager.clear(ctx.bot_id, ctx.user_id)
            ctx.reply("لغو شد.", reply_markup=ADMIN_KEYBOARD)

    @text_input_bus.on("admin:bc:text")
    def _bc_text(ctx):
        data = state_manager.get_data(ctx.bot_id, ctx.user_id)
        target = data.get("target", "all")
        msg = ctx.text or ""
        state_manager.clear(ctx.bot_id, ctx.user_id)
        bid = db.insert(
            """INSERT INTO broadcasts (sender_user_id, target, content_json, status)
               VALUES (?, ?, ?, ?)""",
            (int(ctx.db_user_id), target,
             json.dumps({"type": "text", "text": msg}, ensure_ascii=False),
             "queued"),
        )
        ctx.reply(
            "✅ Broadcast #{} در صف قرار گرفت.\n"
            "ارسال در پس‌زمینه آغاز می‌شود.".format(bid),
            reply_markup=ADMIN_KEYBOARD,
        )

    # ========================================================
    # RESELLERS
    # ========================================================
    @mother_router.text(BTN_RESELLERS)
    def _resellers(ctx):
        if not _is_admin(ctx):
            return
        _show_resellers(ctx)

    def _show_resellers(ctx):
        rows = db.fetchall(
            """SELECT u.id, u.bale_user_id, u.first_name
                 FROM admins a JOIN users u ON u.id=a.user_id
                 WHERE a.role=? ORDER BY u.id DESC LIMIT 15""",
            (ROLE_RESELLER,),
        )
        text = "🧑‍💼 نمایندگان فعلی ({}):\n".format(len(rows))
        text += "💱 درصد پورسانت: {}%\n\n".format(_get_percent())
        kb = []
        for r in rows:
            label = "{} | id={}".format(r.get("first_name") or "-", r["bale_user_id"])
            kb.append([(label, "uadm:open:{}".format(r["id"]))])
        kb.append([("➕ افزودن نماینده جدید", "res:add:0")])
        if _is_super(ctx):
            kb.append([("💱 تغییر درصد پورسانت", "res:percent:0")])
        ctx.reply(text, reply_markup=inline(kb))

    @mother_router.callback("res:")
    def _res_cb(ctx):
        if not _is_admin(ctx):
            ctx.answer_callback("⛔", show_alert=True); return
        action = ctx.data.split(":", 2)[1]
        ctx.answer_callback()
        if action == "add":
            if not _is_super(ctx):
                ctx.reply("⛔ فقط سوپرادمین.")
                return
            state_manager.set(ctx.bot_id, ctx.user_id, "admin:res:add", {})
            ctx.reply("آی‌دی عددی بله کاربر را ارسال کنید:")
        elif action == "percent":
            if not _is_super(ctx):
                ctx.reply("⛔ فقط سوپرادمین.")
                return
            state_manager.set(ctx.bot_id, ctx.user_id, "admin:res:percent", {})
            ctx.reply("درصد جدید (0 تا 100) را ارسال کنید:")

    @text_input_bus.on("admin:res:add")
    def _res_add(ctx):
        s = (ctx.text or "").strip()
        if not s.isdigit():
            ctx.reply("❌ آی‌دی باید عدد باشد."); return
        u = db.fetchone("SELECT * FROM users WHERE bale_user_id=?", (int(s),))
        state_manager.clear(ctx.bot_id, ctx.user_id)
        if not u:
            ctx.reply(
                "⚠️ کاربری با این آی‌دی هنوز در ربات /start نزده است.\n"
                "ابتدا از او بخواهید /start بفرستد، سپس مجدد امتحان کنید."
            )
            return
        grant_admin(u["id"], role=ROLE_RESELLER)
        ctx.reply("✅ کاربر به نماینده ارتقا یافت.")
        _show_user_detail(ctx, u["id"])

    @text_input_bus.on("admin:res:percent")
    def _res_percent(ctx):
        s = (ctx.text or "").strip()
        if not s.isdigit():
            ctx.reply("❌ مقدار باید عدد باشد."); return
        set_percent(int(s))
        state_manager.clear(ctx.bot_id, ctx.user_id)
        ctx.reply("✅ درصد پورسانت روی {}% تنظیم شد.".format(s))
        _show_resellers(ctx)

    # ========================================================
    # SYSTEM SETTINGS
    # ========================================================
    @mother_router.text(BTN_SETTINGS)
    def _settings(ctx):
        if not _is_admin(ctx):
            return
        _show_settings(ctx)

    def _show_settings(ctx):
        rows = db.fetchall("SELECT * FROM system_settings ORDER BY key ASC")
        text = "🔧 تنظیمات سیستم:\n\n"
        kb = []
        for r in rows:
            val = (r["value"] or "")[:30]
            text += "• {} = {}\n".format(r["key"], val)
            if _is_super(ctx):
                kb.append([("✏️ " + r["key"], "set:edit:{}".format(r["id"]))])
        if _is_super(ctx):
            kb.append([("➕ افزودن تنظیم جدید", "set:new:0")])
            kb.append([("🎯 مدیریت زیرمجموعه‌گیری", "refcfg:menu:0")])
        ctx.reply(text, reply_markup=inline(kb) if kb else None)

    @mother_router.callback("set:")
    def _set_cb(ctx):
        if not _is_super(ctx):
            ctx.answer_callback("⛔ فقط سوپرادمین", show_alert=True); return
        parts = ctx.data.split(":", 3)
        action = parts[1]
        ctx.answer_callback()
        if action == "edit":
            row = db.fetchone("SELECT * FROM system_settings WHERE id=?", (int(parts[2]),))
            if not row:
                ctx.reply("یافت نشد."); return
            state_manager.set(ctx.bot_id, ctx.user_id, "admin:set:edit",
                              {"id": row["id"], "key": row["key"]})
            ctx.reply("مقدار جدید برای «{}» را ارسال کنید:\n(فعلی: {})".format(
                row["key"], row["value"] or "-"
            ))
        elif action == "new":
            state_manager.set(ctx.bot_id, ctx.user_id, "admin:set:newkey", {})
            ctx.reply("نام کلید تنظیم جدید را ارسال کنید:")

    @text_input_bus.on("admin:set:edit")
    def _set_edit(ctx):
        data = state_manager.get_data(ctx.bot_id, ctx.user_id)
        db.execute(
            "UPDATE system_settings SET value=?, updated_at=datetime('now') WHERE id=?",
            (ctx.text or "", int(data["id"])),
        )
        state_manager.clear(ctx.bot_id, ctx.user_id)
        ctx.reply("✅ تنظیم «{}» به‌روزرسانی شد.".format(data["key"]))
        _show_settings(ctx)

    @text_input_bus.on("admin:set:newkey")
    def _set_newkey(ctx):
        key = (ctx.text or "").strip()
        if not key:
            ctx.reply("کلید نمی‌تواند خالی باشد."); return
        state_manager.set(ctx.bot_id, ctx.user_id, "admin:set:newval", {"key": key})
        ctx.reply("مقدار آن را ارسال کنید:")

    @text_input_bus.on("admin:set:newval")
    def _set_newval(ctx):
        data = state_manager.get_data(ctx.bot_id, ctx.user_id)
        db.execute("INSERT INTO system_settings (key, value) VALUES (?, ?)",
                   (data["key"], ctx.text or ""))
        state_manager.clear(ctx.bot_id, ctx.user_id)
        ctx.reply("✅ تنظیم جدید ذخیره شد.")
        _show_settings(ctx)

    # ========================================================
    # REFERRAL CONFIG  —  banner + toggle
    # ========================================================
    @mother_router.callback("refcfg:")
    def _refcfg_cb(ctx):
        if not _is_super(ctx):
            ctx.answer_callback("⛔ فقط سوپرادمین", show_alert=True); return
        parts = ctx.data.split(":")
        action = parts[1]
        ctx.answer_callback()
        if action == "menu":
            _show_referral_config(ctx)
        elif action == "toggle":
            row = db.fetchone("SELECT value FROM system_settings WHERE key='referral_enabled'")
            current = row["value"] if row else "1"
            new_val = "0" if current == "1" else "1"
            if row:
                db.execute("UPDATE system_settings SET value=? WHERE key=?", (new_val, "referral_enabled"))
            else:
                db.execute("INSERT INTO system_settings (key, value) VALUES (?, ?)",
                           ("referral_enabled", new_val))
            _show_referral_config(ctx)
        elif action == "settext":
            state_manager.set(ctx.bot_id, ctx.user_id, "admin:refcfg:text", {})
            ctx.reply("✏️ متن بنر دعوت را ارسال کنید.\n"
                      "از {link} برای جایگذاری لینک دعوت استفاده کنید.\n/cancel برای انصراف")
        elif action == "setphoto":
            state_manager.set(ctx.bot_id, ctx.user_id, "admin:refcfg:photo", {})
            ctx.reply("🖼 عکس بنر دعوت را ارسال کنید:\n/cancel برای انصراف")
        elif action == "clearphoto":
            db.execute("UPDATE system_settings SET value='' WHERE key='referral_banner_photo'")
            ctx.reply("🗑 عکس بنر حذف شد.")
            _show_referral_config(ctx)

    def _show_referral_config(ctx):
        ref_row = db.fetchone("SELECT value FROM system_settings WHERE key='referral_enabled'")
        enabled = ref_row["value"] != "0" if ref_row else True

        text_row = db.fetchone("SELECT value FROM system_settings WHERE key='referral_banner_text'")
        photo_row = db.fetchone("SELECT value FROM system_settings WHERE key='referral_banner_photo'")
        banner_text = (text_row["value"] or "") if text_row else ""
        banner_photo = (photo_row["value"] or "") if photo_row else ""

        status = "✅ فعال" if enabled else "⛔ غیرفعال"
        photo_status = "✅ تنظیم شده" if banner_photo else "❌ تنظیم نشده"
        preview = (banner_text[:80] + "...") if len(banner_text) > 80 else banner_text

        text = (
            "🎯 <b>مدیریت زیرمجموعه‌گیری</b>\n\n"
            "📡 وضعیت دکمه دعوت: {status}\n"
            "🖼 عکس بنر: {photo}\n"
            "📝 متن بنر:\n<pre>{preview}</pre>"
        ).format(status=status, photo=photo_status, preview=preview or "(خالی)")

        kb = inline([
            [("⛔ غیرفعال‌سازی" if enabled else "✅ فعال‌سازی", "refcfg:toggle:0")],
            [("📝 تنظیم متن بنر", "refcfg:settext:0")],
            [("🖼 تنظیم عکس بنر", "refcfg:setphoto:0")],
            [("🗑 حذف عکس بنر", "refcfg:clearphoto:0")],
            [("🔙 بازگشت به تنظیمات", "set:view:0")],
        ])
        ctx.reply(text, reply_markup=kb, parse_mode="HTML")

    @text_input_bus.on("admin:refcfg:text")
    def _on_refcfg_text(ctx):
        text = (ctx.text or "").strip()
        state_manager.clear(ctx.bot_id, ctx.user_id)
        row = db.fetchone("SELECT id FROM system_settings WHERE key='referral_banner_text'")
        if row:
            db.execute("UPDATE system_settings SET value=? WHERE key=?", (text, "referral_banner_text"))
        else:
            db.execute("INSERT INTO system_settings (key, value) VALUES (?, ?)",
                       ("referral_banner_text", text))
        ctx.reply("✅ متن بنر ذخیره شد.")
        _show_referral_config(ctx)

    @text_input_bus.on("admin:refcfg:photo")
    def _on_refcfg_photo(ctx):
        # Accept photo
        file_id = ctx.photo_file_id
        if not file_id:
            ctx.reply("❌ لطفاً یک عکس ارسال کنید یا /cancel")
            return
        state_manager.clear(ctx.bot_id, ctx.user_id)
        row = db.fetchone("SELECT id FROM system_settings WHERE key='referral_banner_photo'")
        if row:
            db.execute("UPDATE system_settings SET value=? WHERE key=?", (file_id, "referral_banner_photo"))
        else:
            db.execute("INSERT INTO system_settings (key, value) VALUES (?, ?)",
                       ("referral_banner_photo", file_id))
        ctx.reply("✅ عکس بنر ذخیره شد.")
        _show_referral_config(ctx)

    # Also handle photo for referral banner via text_input_bus (photo dispatch)
    # This is needed because the default text_input_bus only catches text,
    # but photos are handled separately in dispatcher.
    # We will add the photo state prefix to text_input_bus as well.

    # ========================================================
    # BACK
    # ========================================================
    @mother_router.text(BTN_BACK)
    def _back(ctx):
        from admin_panel.user_panel import get_user_main_kb
        ctx.reply("🏠 خارج از پنل ادمین.", reply_markup=get_user_main_kb())
