# ============================================================
# admin_panel/user_panel.py
# ============================================================
# User-facing handlers — simplified for template-only bot creation.
# No manual page/flow/button building.
# ============================================================

import json

from core.router import mother_router
from core.keyboards import reply_keyboard, inline, remove_keyboard
from core.state_manager import state_manager, text_input_bus
from core.bot_manager import bot_manager
from core.updater import BaleAPI

from database.db import db

from subscriptions.subscription_manager import (
    check_can_create_bot, list_user_subscriptions,
    get_feature_tier,
)
from subscriptions.plan_manager import list_plans, get_plan
from wallet.wallet_manager import (
    get_balance, list_transactions, redeem_gift_code,
)
from payments.payment_manager import (
    start_subscription_purchase, start_wallet_topup,
    list_enabled_methods, notify_receipt_submitted,
)
from payments import wallet_gateway
from templates import template_registry


# ============================================================
# Labels
# ============================================================
BTN_NEW_BOT          = "🤖 ساخت ربات"
BTN_MY_BOTS          = "🗂 ربات‌های من"
BTN_WALLET           = "💰 کیف پول"
BTN_MY_SUBS          = "🎟 اشتراک‌های من"
BTN_INVITE           = "🎯 دعوت دوستان"
BTN_GIFT             = "🎁 ثبت کد هدیه"
BTN_SUPPORT          = "📞 پشتیبانی"
BTN_HELP             = "❓ راهنما"

USER_MAIN_KB = reply_keyboard([
    [BTN_NEW_BOT],
    [BTN_MY_BOTS],
    [BTN_WALLET, BTN_MY_SUBS],
    [BTN_INVITE, BTN_GIFT],
    [BTN_SUPPORT, BTN_HELP],
])


def _is_referral_enabled() -> bool:
    row = db.fetchone("SELECT value FROM system_settings WHERE key='referral_enabled'")
    return not (row and row["value"] == "0")


def get_user_main_kb():
    if _is_referral_enabled():
        return USER_MAIN_KB
    return reply_keyboard([
        [BTN_NEW_BOT],
        [BTN_MY_BOTS],
        [BTN_WALLET, BTN_MY_SUBS],
        [BTN_GIFT],
        [BTN_SUPPORT, BTN_HELP],
    ])


# ============================================================
# Helpers
# ============================================================
def _owner_id(ctx) -> int:
    return int(ctx.db_user_id)


def _money(n: int) -> str:
    return "{:,} ریال".format(int(n))


def _user_bots(owner_id: int):
    return db.fetchall(
        "SELECT * FROM bots WHERE owner_id=? ORDER BY id DESC", (int(owner_id),)
    )


def _get_bot_for_owner(bot_id: int, owner_id: int):
    return db.fetchone(
        "SELECT * FROM bots WHERE id=? AND owner_id=?",
        (int(bot_id), int(owner_id)),
    )


def _payment_methods_kb(prefix: str, amount: int, extra_args: str = "",
                        user_id: int = None) -> dict:
    methods = list_enabled_methods()
    wallet_bal = get_balance(user_id) if user_id else 0
    rows = []
    for m in methods:
        if m["key"] == "wallet":
            if wallet_bal >= amount:
                label = "💰 کیف پول ({})".format(_money(wallet_bal))
                rows.append([(label, "{}:{}:wallet:{}".format(prefix, extra_args, amount))
                             if extra_args
                             else (label, "{}:wallet:{}".format(prefix, amount))])
            break
    for m in methods:
        if m["key"] == "wallet":
            continue
        cb = ("{}:{}:{}:{}".format(prefix, extra_args, m["key"], amount)
              if extra_args else "{}:{}:{}".format(prefix, m["key"], amount))
        rows.append([(m["name"], cb)])
    if user_id is not None and wallet_bal < amount:
        shortage = amount - wallet_bal
        rows.append([(
            "💼 شارژ سریع {} (موجودی: {})".format(_money(shortage), _money(wallet_bal)),
            "wt:quick:{}".format(shortage),
        )])
    rows.append([("🔙 لغو", "cancel:main")])
    return inline(rows)


# ============================================================
# Setup
# ============================================================
def setup():

    # --------------------------------------------------------
    # HOME / CANCEL
    # --------------------------------------------------------
    @mother_router.text("🏠 صفحه اصلی")
    def _home(ctx):
        ctx.reply("منوی اصلی:", reply_markup=get_user_main_kb())

    @mother_router.command("cancel")
    def _cancel(ctx):
        state_manager.clear(ctx.bot_id, ctx.user_id)
        ctx.reply("لغو شد.", reply_markup=get_user_main_kb())

    @mother_router.callback("cancel:")
    def _cancel_cb(ctx):
        state_manager.clear(ctx.bot_id, ctx.user_id)
        ctx.answer_callback("لغو شد")
        ctx.reply("منوی اصلی:", reply_markup=get_user_main_kb())

    # ========================================================
    # WALLET
    # ========================================================
    @mother_router.text(BTN_WALLET)
    def _wallet_btn(ctx):
        bal = get_balance(_owner_id(ctx))
        txs = list_transactions(_owner_id(ctx), limit=5)
        text = "👛 موجودی: <b>{}</b>\n\n".format(_money(bal))
        if txs:
            text += "📑 آخرین تراکنش‌ها:\n"
            for t in txs:
                sign = "➕" if t["amount"] > 0 else "➖"
                text += "{} {:,} | {}\n".format(sign, abs(t["amount"]), t["type"])
        else:
            text += "تراکنشی نیست."
        kb = inline([
            [("💳 شارژ", "wt:start:0")],
            [("🎁 کد هدیه", "wt:gift:0")],
            [("🔄 رفرش", "wt:refresh:0")],
        ])
        ctx.reply(text, reply_markup=kb, parse_mode="HTML")

    @mother_router.callback("wt:")
    def _wt_cb(ctx):
        parts = ctx.data.split(":")
        action = parts[1]
        ctx.answer_callback()
        if action == "refresh":
            _wallet_btn(ctx)
        elif action == "start":
            ctx.reply("💳 مبلغ شارژ:", reply_markup=inline([
                [("50,000", "wt:amt:50000")],
                [("100,000", "wt:amt:100000")],
                [("200,000", "wt:amt:200000")],
                [("500,000", "wt:amt:500000")],
                [("✏️ دلخواه", "wt:custom:0")],
                [("🔙", "wt:refresh:0")],
            ]))
        elif action == "custom":
            state_manager.set(ctx.bot_id, ctx.user_id, "user:wallet:topup", {})
            ctx.reply("✏️ مبلغ (ریال):\n/cancel")
        elif action in ("amt", "quick"):
            _show_topup(ctx, int(parts[2]))
        elif action == "gift":
            state_manager.set(ctx.bot_id, ctx.user_id, "user:gift:code", {})
            ctx.reply("🎁 کد هدیه:\n/cancel")
        elif action == "pay":
            _do_topup(ctx, parts[2], int(parts[3]))

    def _show_topup(ctx, amount):
        methods = [m for m in list_enabled_methods() if m["key"] != "wallet"]
        if not methods:
            ctx.reply("❌ روش پرداختی فعال نیست."); return
        rows = [[(m["name"], "wt:pay:{}:{}".format(m["key"], amount))] for m in methods]
        rows.append([("🔙", "wt:refresh:0")])
        ctx.reply("💳 {} — روش پرداخت:".format(_money(amount)), reply_markup=inline(rows))

    def _do_topup(ctx, method, amount):
        p = start_wallet_topup(_owner_id(ctx), amount, method)
        if method == "card_to_card":
            from payments.card_to_card import get_card_text
            state_manager.set(ctx.bot_id, ctx.user_id, "user:c2c:photo",
                              {"payment_id": p["id"]})
            ctx.reply("🧾 #{}\n\n{}".format(p["id"], get_card_text()), parse_mode="HTML")
        elif method == "online":
            from payments.online_gateway import request_payment
            r = request_payment(amount, "شارژ کیف پول")
            ctx.reply("🔗 {}\n\n#{}".format(r["redirect_url"], p["id"]))
        elif method == "bale":
            ctx.reply("💳 بله #{} ثبت شد.".format(p["id"]))

    @text_input_bus.on("user:wallet:topup")
    def _on_custom_amt(ctx):
        s = (ctx.text or "").strip()
        if not s.isdigit() or int(s) < 1000:
            ctx.reply("❌ حداقل ۱,۰۰۰"); return
        state_manager.clear(ctx.bot_id, ctx.user_id)
        _show_topup(ctx, int(s))

    @text_input_bus.on("user:gift:code")
    def _on_gift(ctx):
        code = (ctx.text or "").strip().upper()
        state_manager.clear(ctx.bot_id, ctx.user_id)
        r = redeem_gift_code(_owner_id(ctx), code)
        ctx.reply(r["message"], reply_markup=get_user_main_kb())

    @text_input_bus.on("user:c2c:photo")
    def _on_c2c(ctx):
        data = state_manager.get_data(ctx.bot_id, ctx.user_id)
        pid = int(data.get("payment_id") or 0)
        if ctx.photo_file_id:
            from payments.card_to_card import attach_receipt_photo
            attach_receipt_photo(pid, ctx.photo_file_id,
                                 tracking_code=(ctx.caption or "").strip() or None)
            state_manager.clear(ctx.bot_id, ctx.user_id)
            notify_receipt_submitted(pid)
            ctx.reply("✅ رسید دریافت شد.\n⏳ منتظر تأیید مدیر.",
                      reply_markup=get_user_main_kb())
        elif ctx.text:
            from payments.card_to_card import attach_receipt_text
            attach_receipt_text(pid, ctx.text.strip())
            ctx.reply("📝 ثبت شد. <b>عکس رسید</b> هم بفرستید.", parse_mode="HTML")

    # ========================================================
    # MY SUBSCRIPTIONS — active only
    # ========================================================
    @mother_router.text(BTN_MY_SUBS)
    def _my_subs(ctx):
        subs = list_user_subscriptions(_owner_id(ctx))
        active = [s for s in subs if s["status"] == "active"]
        tier = get_feature_tier(_owner_id(ctx))
        tier_label = "⭐ VIP" if tier == "vip" else "🆓 رایگان"

        if not active:
            ctx.reply(
                "🎟 <b>اشتراک‌های من</b>\n\n"
                "🔘 طرح: <b>{}</b>\n\n"
                "شما اشتراک فعالی ندارید.".format(tier_label),
                parse_mode="HTML")
            return

        text = "🎟 <b>اشتراک‌های من</b>\n\n🔑 طرح: <b>{}</b>\n\n".format(tier_label)
        for s in active:
            plan = get_plan(s["plan_id"])
            pn = plan["name"] if plan else "?"
            try:
                from datetime import datetime
                ends = datetime.strptime(s["ends_at"], "%Y-%m-%d %H:%M:%S")
                rem = (ends - datetime.utcnow()).days
                rem_text = "{} روز مانده".format(rem) if rem > 0 else "در حال اتمام"
            except Exception:
                rem_text = "-"
            text += "✅ <b>{}</b>\n   📅 {}\n\n".format(pn, rem_text)

        ctx.reply(text, parse_mode="HTML")

    # ========================================================
    # CREATE BOT — template only
    # ========================================================
    @mother_router.text(BTN_NEW_BOT)
    def _new_bot(ctx):
        tpls = template_registry.list_published_templates()
        if not tpls:
            ctx.reply("⚠️ فعلاً قالبی در دسترس نیست.")
            return

        text = (
            "🤖 <b>ساخت ربات</b>\n\n"
            "یک نوع ربات انتخاب کنید:\n\n"
        )
        kb = []
        for t in tpls:
            meta = template_registry.get(t["key"])
            if not meta:
                continue
            plans = template_registry.list_plans_for_template(t["key"])
            cheapest = min((p["price"] for p in plans), default=0)
            label = "{} {} — از {}".format(meta.icon, meta.name, _money(cheapest))
            kb.append([(label, "tpl:open:{}".format(t["key"]))])

        ctx.reply(text, reply_markup=inline(kb), parse_mode="HTML")

    @mother_router.callback("tpl:")
    def _tpl_cb(ctx):
        parts = ctx.data.split(":", 3)
        action = parts[1]
        ctx.answer_callback()

        if action == "open" and len(parts) >= 3:
            key = parts[2]
            meta = template_registry.get(key)
            if not meta:
                ctx.reply("یافت نشد."); return
            plans = template_registry.list_plans_for_template(key)

            text = (
                "{} <b>{}</b>\n"
                "{}\n\n"
                "📦 پلن‌ها:\n"
            ).format(meta.icon, meta.name, meta.description)

            kb = []
            for p in plans:
                tag = "⭐" if int(p["price"]) > 0 else "🆓"
                text += "{} {} — {} روز — <b>{}</b>\n".format(
                    tag, p["name"], p["duration_days"], _money(p["price"]))
                kb.append([(p["name"], "tpl:plan:{}:{}".format(key, p["id"]))])
            kb.append([("🔙 بازگشت", "tpl:list:0")])
            ctx.reply(text, reply_markup=inline(kb), parse_mode="HTML")
            return

        if action == "list":
            _new_bot(ctx); return

        if action == "plan" and len(parts) >= 4:
            tpl_key, plan_id = parts[2], int(parts[3])
            p = get_plan(plan_id)
            meta = template_registry.get(tpl_key)
            if not p or not meta:
                ctx.reply("پلن یافت نشد."); return

            # Check subscription
            chk = check_can_create_bot(_owner_id(ctx))
            if not chk["ok"]:
                ctx.reply(chk["message"])
                return

            state_manager.set(ctx.bot_id, ctx.user_id, "user:tpl:choice",
                              {"tpl_key": tpl_key, "plan_id": plan_id})

            text = (
                "{} <b>{}</b> — {}\n\n"
                "⏱ {} روز\n"
                "💰 <b>{}</b>\n\n"
                "👇 روش پرداخت:"
            ).format(meta.icon, meta.name, p["name"],
                     p["duration_days"], _money(p["price"]))

            kb = _payment_methods_kb("tpl:pay", int(p["price"]),
                                     extra_args="{}_{}".format(tpl_key, plan_id),
                                     user_id=_owner_id(ctx))
            ctx.reply(text, reply_markup=inline(kb), parse_mode="HTML")
            return

        if action == "pay" and len(parts) >= 4:
            tpl_plan, method = parts[2], parts[3].split(":")[0]
            try:
                tpl_key, plan_id = tpl_plan.rsplit("_", 1)
                plan_id = int(plan_id)
            except Exception:
                ctx.reply("خطا."); return
            p = get_plan(plan_id)
            if not p:
                return

            try:
                payment = start_subscription_purchase(
                    _owner_id(ctx), plan_id, int(p["price"]), method,
                    meta={"tpl_key": tpl_key})
            except ValueError as e:
                if "insufficient" in str(e):
                    shortage = wallet_gateway.shortage(_owner_id(ctx), int(p["price"]))
                    ctx.reply("❌ موجودی کافی نیست.\n💸 کسری: {}".format(_money(shortage)),
                              reply_markup=inline([
                                  [("💼 شارژ سریع", "wt:quick:{}".format(shortage))],
                                  [("🔙", "tpl:plan:{}:{}".format(tpl_key, plan_id))]]))
                else:
                    ctx.reply("❌ {}".format(e))
                return

            if method == "wallet":
                ctx.reply("✅ پرداخت انجام شد.\n🎟 فعال شد.\n\n🔑 توکن ربات را آماده کنید 👇")
                _ask_token(ctx, tpl_key)
                return

            if method == "card_to_card":
                from payments.card_to_card import get_card_text
                state_manager.set(ctx.bot_id, ctx.user_id, "user:c2c:photo",
                                  {"payment_id": payment["id"]})
                ctx.reply(
                    "🧾 #{}\n\n{}\n\n"
                    "💡 پس از تأیید، دکمه «ساخت ربات» در پیام تأیید نمایش داده می‌شود."
                    .format(payment["id"], get_card_text()), parse_mode="HTML")
                state_manager.update_data(ctx.bot_id, ctx.user_id, pending_template=tpl_key)
                return

            if method == "online":
                from payments.online_gateway import request_payment
                r = request_payment(int(p["price"]), meta.name)
                ctx.reply("🔗 {}\n\n💡 پس از تأیید، ربات ساخته می‌شود.".format(r["redirect_url"]))
                state_manager.update_data(ctx.bot_id, ctx.user_id, pending_template=tpl_key)
                return

            if method == "bale":
                ctx.reply("💳 بله #{} ثبت شد.\n💡 پس از تأیید، ربات ساخته می‌شود.".format(payment["id"]))
                state_manager.update_data(ctx.bot_id, ctx.user_id, pending_template=tpl_key)
                return

    def _ask_token(ctx, tpl_key):
        """Ask user for bot token."""
        state_manager.set(ctx.bot_id, ctx.user_id, "user:newbot:token",
                          {"template": tpl_key})
        ctx.reply(
            "🔑 <b>توکن ربات خود را بفرستید</b>\n\n"
            "ابتدا در @botfather ربات بسازید.\n"
            "سپس توکن را اینجا بفرستید.\n\n"
            "💡 توکن شبیه:\n"
            "<code>123456789:AbCdEf...</code>\n\n"
            "/cancel",
            parse_mode="HTML", reply_markup=remove_keyboard())

    # --------------------------------------------------------
    # GIFT / RECEIPT
    # --------------------------------------------------------
    @mother_router.text(BTN_GIFT)
    def _gift_btn(ctx):
        state_manager.set(ctx.bot_id, ctx.user_id, "user:gift:code", {})
        ctx.reply("🎁 کد هدیه:\n/cancel")

    @mother_router.command("gift")
    def _gift_cmd(ctx):
        parts = (ctx.text or "").split()
        if len(parts) == 2:
            ctx.reply(redeem_gift_code(_owner_id(ctx), parts[1])["message"])
        else:
            state_manager.set(ctx.bot_id, ctx.user_id, "user:gift:code", {})
            ctx.reply("🎁 کد هدیه:")

    @mother_router.command("receipt")
    def _receipt(ctx):
        parts = (ctx.text or "").split(maxsplit=2)
        if len(parts) >= 3 and parts[1].isdigit():
            from payments.card_to_card import attach_receipt_text
            try:
                attach_receipt_text(int(parts[1]), parts[2])
                notify_receipt_submitted(int(parts[1]))
                ctx.reply("✅ ثبت شد.")
            except Exception as e:
                ctx.reply("❌ {}".format(e))
        else:
            ctx.reply("💡 عکس رسید را بفرستید.")

    # ========================================================
    # MY BOTS
    # ========================================================
    @mother_router.text(BTN_MY_BOTS)
    def _my_bots(ctx):
        rows = _user_bots(_owner_id(ctx))
        if not rows:
            ctx.reply("هنوز رباتی نساخته‌اید 🤖\n\nاز «🤖 ساخت ربات» شروع کنید.",
                      reply_markup=get_user_main_kb())
            return
        kb = [[("🤖 @{} — {}".format(b.get("bot_username") or "?", b["status"]),
                "mb:open:{}".format(b["id"]))] for b in rows]
        ctx.reply("🤖 <b>ربات‌های شما</b> ({}):".format(len(rows)),
                  reply_markup=inline(kb), parse_mode="HTML")

    @mother_router.callback("mb:")
    def _my_bots_cb(ctx):
        parts = ctx.data.split(":", 3)
        action, bot_id = parts[1], (int(parts[2]) if len(parts) > 2 else None)
        b = _get_bot_for_owner(bot_id, _owner_id(ctx)) if bot_id else None
        if not b:
            ctx.answer_callback("⛔", show_alert=True); return

        if action == "open":
            ctx.answer_callback()
            tpl_name = "-"
            if b.get("template_id"):
                tr = db.fetchone("SELECT name FROM bot_templates WHERE id=?",
                                 (int(b["template_id"]),))
                if tr:
                    tpl_name = tr["name"]
            si = "✅" if b["status"] == "active" else "⏸"
            text = (
                "🤖 <b>@{u}</b>\n\n"
                "📡 وضعیت: {si} {st}\n"
                "🧩 نوع: {tpl}\n\n"
                "👇 انتخاب کنید:"
            ).format(u=b.get("bot_username") or "?", si=si, st=b["status"], tpl=tpl_name)
            kb = inline([
                [("⏸ توقف" if b["status"] == "active" else "▶️ فعال", "mb:pause:{}".format(bot_id))],
                [("🗑 حذف", "mb:delete:{}".format(bot_id))],
                [("🔙 بازگشت", "mb:list:0")],
            ])
            ctx.reply(text, reply_markup=kb, parse_mode="HTML")

        elif action == "list":
            ctx.answer_callback()
            _my_bots(ctx)

        elif action == "delete":
            ctx.answer_callback("حذف")
            bot_manager.stop_bot(b["id"])
            db.execute("DELETE FROM bots WHERE id=?", (b["id"],))
            ctx.reply("🗑 ربات حذف شد.", reply_markup=get_user_main_kb())

        elif action == "pause":
            new = "paused" if b["status"] == "active" else "active"
            db.execute("UPDATE bots SET status=? WHERE id=?", (new, b["id"]))
            if new == "paused":
                bot_manager.stop_bot(b["id"])
            else:
                bot_manager.start_child(_get_bot_for_owner(b["id"], _owner_id(ctx)))
            ctx.answer_callback("OK")
            _my_bots(ctx)

    # ========================================================
    # TOKEN HANDLER
    # ========================================================
    @text_input_bus.on("user:newbot:token")
    def _on_token(ctx):
        data = state_manager.get_data(ctx.bot_id, ctx.user_id)
        token = (ctx.text or "").strip()
        if ":" not in token or len(token) < 20:
            ctx.reply("❌ توکن نامعتبر.\n🔑 شبیه:\n<code>123456789:AbCd...</code>\n/cancel",
                      parse_mode="HTML")
            return
        try:
            api = BaleAPI(token)
            me = api.get_me()
        except Exception as e:
            ctx.reply("❌ توکن اشتباه: {}\n/cancel".format(str(e)[:150]))
            return
        if db.fetchone("SELECT id FROM bots WHERE token=?", (token,)):
            ctx.reply("⚠️ قبلاً ثبت شده. از «🗂 ربات‌های من» ببینید.",
                      reply_markup=get_user_main_kb())
            state_manager.clear(ctx.bot_id, ctx.user_id)
            return

        tpl_key = data.get("template")
        tpl_row = template_registry.db_row(tpl_key) if tpl_key else None
        tpl_id = tpl_row["id"] if tpl_row else None

        bot_id = db.insert(
            """INSERT INTO bots
                  (owner_id, token, bot_username, display_name, template_id, status, settings_json)
               VALUES (?, ?, ?, ?, ?, 'active', '{}')""",
            (_owner_id(ctx), token, me.get("username"),
             me.get("first_name") or me.get("username"), tpl_id))

        if tpl_key:
            tpl = template_registry.get(tpl_key)
            if tpl:
                try:
                    tpl.apply(bot_id)
                except Exception:
                    pass

        bot_manager.start_child(db.fetchone("SELECT * FROM bots WHERE id=?", (bot_id,)))
        state_manager.clear(ctx.bot_id, ctx.user_id)

        tpl_label = ""
        if tpl_key and template_registry.get(tpl_key):
            tpl_label = "🧩 نوع: {}\n".format(template_registry.get(tpl_key).name)

        ctx.reply(
            "🎉 <b>ربات شما آماده است!</b>\n\n"
            "🤖 @{u}\n"
            "{tpl}"
            "🆔 #{id}\n\n"
            "✅ ربات ساخته شد و در حال کار است.\n"
            "از «🗂 ربات‌های من» می‌توانید مدیریتش کنید.".format(
                u=me.get("username"), tpl=tpl_label, id=bot_id),
            reply_markup=get_user_main_kb(), parse_mode="HTML")

        # Notify super-admins
        try:
            from core.notifications import notify_super_admins
            notify_super_admins(
                "🆕 <b>ربات جدید</b>\n\n🤖 @{u}\n🆔 #{id}\n👤 {n}".format(
                    u=me.get("username", "?"), id=bot_id,
                    n=(ctx.from_user or {}).get("first_name", "-")),
                parse_mode="HTML")
        except Exception:
            pass

    # ========================================================
    # INVITE / REFERRAL
    # ========================================================
    @mother_router.text(BTN_INVITE)
    def _invite(ctx):
        from reseller.affiliate_manager import make_ref_code, count_referrals
        if not _is_referral_enabled():
            ctx.reply("🎯 دعوت غیرفعال است."); return
        code = make_ref_code(_owner_id(ctx))
        link = code
        mother_api = bot_manager.get_mother_api()
        if mother_api:
            try:
                me = mother_api.get_me()
                link = "https://ble.ir/{}?start={}".format(me.get("username", ""), code)
            except Exception:
                pass
        ctx.reply(
            "🎯 <b>دعوت دوستان</b>\n\n🔗 <b>لینک شما:</b>\n<code>{}</code>\n\n"
            "👥 دعوت‌شدگان: <b>{}</b>".format(link, count_referrals(_owner_id(ctx))),
            reply_markup=inline([[("🖼 بنر", "ref:banner:0")]]),
            parse_mode="HTML")

    @mother_router.callback("ref:")
    def _ref_cb(ctx):
        ctx.answer_callback()
        if ctx.data.split(":")[1] == "banner":
            _send_banner(ctx)

    def _send_banner(ctx):
        from reseller.affiliate_manager import make_ref_code
        bt = db.fetchone("SELECT value FROM system_settings WHERE key='referral_banner_text'")
        bp = db.fetchone("SELECT value FROM system_settings WHERE key='referral_banner_photo'")
        btext = (bt["value"] or "") if bt else ""
        bphoto = (bp["value"] or "") if bp else ""
        if not btext and not bphoto:
            ctx.reply("⚠️ بنر تنظیم نشده."); return
        code = make_ref_code(_owner_id(ctx))
        link = code
        mother_api = bot_manager.get_mother_api()
        if mother_api:
            try:
                me = mother_api.get_me()
                link = "https://ble.ir/{}?start={}".format(me.get("username", ""), code)
            except Exception:
                pass
        final = btext.replace("{link}", link) if btext else link
        if bphoto:
            try:
                ctx.api.call("sendPhoto", {"chat_id": ctx.chat_id, "photo": bphoto, "caption": final})
            except Exception:
                ctx.reply(final)
        else:
            ctx.reply(final)

    # PAYBUILD — after payment approval
    @mother_router.callback("paybuild:")
    def _paybuild_cb(ctx):
        pid = int(ctx.data.split(":")[1])
        from payments.payment_manager import get_payment
        p = get_payment(pid)
        if not p or p["user_id"] != _owner_id(ctx):
            ctx.answer_callback("⛔", show_alert=True); return
        ctx.answer_callback()
        try:
            meta = json.loads(p.get("meta_json") or "{}")
        except Exception:
            meta = {}
        _ask_token(ctx, meta.get("tpl_key"))

    # SUPPORT / HELP
    @mother_router.text(BTN_SUPPORT)
    def _support(ctx):
        row = db.fetchone("SELECT value FROM system_settings WHERE key='support_contact'")
        ctx.reply("📞 پشتیبانی: {}".format((row["value"] if row else "@support")))

    @mother_router.text(BTN_HELP)
    def _help(ctx):
        ctx.reply(
            "❓ <b>راهنما</b>\n\n"
            "🤖 «ساخت ربات» — انتخاب نوع ربات آماده\n"
            "🗂 «ربات‌های من» — مشاهده و مدیریت ربات‌ها\n"
            "💰 «کیف پول» — شارژ و تراکنش‌ها\n"
            "🎟 «اشتراک‌ها» — مشاهده اشتراک‌های فعال\n"
            "🎯 «دعوت» — کسب درآمد از معرفی\n\n"
            "💡 سوال داشتید؟ «📞 پشتیبانی» تماس بگیرید.",
            parse_mode="HTML")
