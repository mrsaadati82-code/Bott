# ============================================================
# admin_panel/template_admin.py
# ============================================================

import json

from core.router import mother_router
from core.keyboards import inline
from core.permission_manager import is_super_admin, get_role
from core.state_manager import state_manager, text_input_bus
from database.db import db

from templates import template_registry
from subscriptions.plan_manager import update_plan, get_plan


def _money(n: int) -> str:
    return "{:,} ریال".format(int(n))


def _is_admin(ctx) -> bool:
    return get_role(ctx.user_id) in ("admin", "super_admin", "reseller")


def _plan_template_key(plan: dict) -> str:
    try:
        arr = json.loads(plan.get("allowed_templates") or "[]")
        return arr[0] if arr else ""
    except Exception:
        return ""


def _send_templates_list(ctx):
    tpls = template_registry.list_published_templates()
    if not tpls:
        ctx.reply("هیچ Template ای ثبت نشده است.")
        return
    text = "🧩 لیست Templateها ({}):\n\n".format(len(tpls))
    rows = []
    for t in tpls:
        meta = template_registry.get(t["key"])
        icon = meta.icon if meta else "🤖"
        plans = template_registry.list_plans_for_template(t["key"])
        cheapest = min((p["price"] for p in plans), default=0)
        text += "{} {} - از {}\n".format(icon, t["name"], _money(cheapest))
        rows.append([("{} {}".format(icon, t["name"]),
                      "tpl:open:{}".format(t["key"]))])
    ctx.reply(text, reply_markup=inline(rows))


def _send_template_detail(ctx, key: str):
    meta = template_registry.get(key)
    row = template_registry.db_row(key)
    if not meta or not row:
        ctx.reply("Template یافت نشد.")
        return
    plans = template_registry.list_plans_for_template(key)

    text = (
        "{icon} {name} v{ver}\n"
        "{desc}\n\n"
        "وضعیت انتشار: {pub}\n\n"
        "📦 پلن‌های این Template:\n"
    ).format(
        icon=meta.icon, name=meta.name, ver=meta.version,
        desc=meta.description,
        pub="✅ منتشر شده" if int(row["is_published"]) else "⛔ پنهان",
    )
    rows = []
    for p in plans:
        text += "\n• {} | {} روز | {} | bots:{} msg:{}".format(
            p["name"], p["duration_days"], _money(p["price"]),
            p["max_bots"], p["max_monthly_messages"],
        )
        rows.append([
            ("✏️ {} - قیمت".format(p["name"]), "tpl:editprice:{}".format(p["id"])),
            ("📏 محدودیت‌ها",                 "tpl:editlimit:{}".format(p["id"])),
        ])

    rows.append([
        ("{} انتشار".format("⛔" if int(row["is_published"]) else "✅"),
         "tpl:toggle:{}".format(key)),
        ("🔙 بازگشت", "tpl:list:0"),
    ])
    ctx.reply(text, reply_markup=inline(rows))


def setup():

    @mother_router.command("templates")
    def _list_cmd(ctx):
        if not _is_admin(ctx):
            return
        _send_templates_list(ctx)

    @mother_router.callback("tpl:")
    def _tpl_cb(ctx):
        if not _is_admin(ctx):
            ctx.answer_callback("⛔", show_alert=True); return
        parts = ctx.data.split(":", 3)
        action = parts[1]
        ctx.answer_callback()

        if action == "list":
            _send_templates_list(ctx); return

        if action == "open" and len(parts) >= 3:
            _send_template_detail(ctx, parts[2]); return

        if action == "toggle" and len(parts) >= 3:
            key = parts[2]
            row = template_registry.db_row(key)
            if not row:
                ctx.edit("یافت نشد."); return
            new_val = 0 if int(row["is_published"]) else 1
            db.execute("UPDATE bot_templates SET is_published=? WHERE id=?",
                       (new_val, row["id"]))
            _send_template_detail(ctx, key); return

        if action == "editprice" and len(parts) >= 3:
            if not is_super_admin(ctx.user_id):
                ctx.edit("⛔ فقط سوپرادمین قیمت‌ها را تغییر می‌دهد.")
                return
            plan_id = int(parts[2])
            plan = get_plan(plan_id)
            if not plan:
                ctx.edit("پلن یافت نشد."); return
            state_manager.set(
                ctx.bot_id, ctx.user_id,
                "admin:tpl:setprice",
                {"plan_id": plan_id, "tpl_key": _plan_template_key(plan)},
            )
            ctx.edit(
                "🏷 پلن «{}» — قیمت فعلی: {}\n\n"
                "قیمت جدید (به ریال) را ارسال کنید:\n/cancel برای انصراف"
                .format(plan["name"], _money(plan["price"]))
            )
            return

        if action == "editlimit" and len(parts) >= 3:
            if not is_super_admin(ctx.user_id):
                ctx.edit("⛔ فقط سوپرادمین."); return
            plan_id = int(parts[2])
            plan = get_plan(plan_id)
            if not plan:
                ctx.edit("پلن یافت نشد."); return
            kb = inline([
                [("max_bots ({})".format(plan["max_bots"]),
                  "tplL:max_bots:{}".format(plan_id))],
                [("max_users_per_bot ({})".format(plan["max_users_per_bot"]),
                  "tplL:max_users_per_bot:{}".format(plan_id))],
                [("max_monthly_messages ({})".format(plan["max_monthly_messages"]),
                  "tplL:max_monthly_messages:{}".format(plan_id))],
            ])
            ctx.edit("کدام محدودیت را تغییر می‌دهید؟", reply_markup=kb)
            return

    @mother_router.callback("tplL:")
    def _tpl_limit_cb(ctx):
        if not is_super_admin(ctx.user_id):
            ctx.answer_callback("⛔", show_alert=True); return
        _, field, plan_id = ctx.data.split(":", 2)
        plan_id = int(plan_id)
        state_manager.set(
            ctx.bot_id, ctx.user_id,
            "admin:tpl:setlimit",
            {"plan_id": plan_id, "field": field},
        )
        ctx.answer_callback()
        ctx.edit("مقدار جدید برای «{}» را ارسال کنید:".format(field))

    # FSM via TextInputBus
    @text_input_bus.on("admin:tpl:setprice")
    def _on_tpl_setprice(ctx):
        data = state_manager.get_data(ctx.bot_id, ctx.user_id)
        s = (ctx.text or "").strip()
        if not s.isdigit():
            ctx.reply("❌ قیمت باید عدد باشد. دوباره بفرستید یا /cancel"); return
        update_plan(int(data["plan_id"]), price=int(s))
        tpl_key = data.get("tpl_key")
        state_manager.clear(ctx.bot_id, ctx.user_id)
        ctx.reply("✅ قیمت به‌روزرسانی شد.")
        if tpl_key:
            _send_template_detail(ctx, tpl_key)

    @text_input_bus.on("admin:tpl:setlimit")
    def _on_tpl_setlimit(ctx):
        data = state_manager.get_data(ctx.bot_id, ctx.user_id)
        s = (ctx.text or "").strip()
        if not s.isdigit():
            ctx.reply("❌ مقدار باید عدد باشد. دوباره بفرستید یا /cancel"); return
        update_plan(int(data["plan_id"]), **{data["field"]: int(s)})
        state_manager.clear(ctx.bot_id, ctx.user_id)
        ctx.reply("✅ {} به‌روزرسانی شد.".format(data["field"]))
