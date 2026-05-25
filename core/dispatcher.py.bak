# ============================================================
# core/dispatcher.py - Update -> handler dispatcher
# ============================================================

from typing import Any, Dict, Optional

from database.db import db
from monitoring.logs import get_logger
from core.bot_manager import bot_manager, MOTHER_BOT_ID
from core.router import mother_router, child_router
from core.state_manager import state_manager, text_input_bus
from modules.module_registry import module_registry

log = get_logger(__name__)


class Context:
    def __init__(self, bot_id: int, update: Dict[str, Any]):
        self.bot_id = bot_id
        self.update = update
        self.api = bot_manager.get_api(bot_id)

        self.message: Optional[dict]  = update.get("message") or update.get("edited_message")
        self.callback: Optional[dict] = update.get("callback_query")
        self.pre_checkout: Optional[dict] = update.get("pre_checkout_query")

        src = self.callback.get("message") if self.callback else self.message
        self.chat:    Optional[dict] = src.get("chat") if src else None
        self.from_user: Optional[dict] = (
            (self.callback or self.message or {}).get("from")
        )

        self.chat_id: Optional[int] = self.chat["id"] if self.chat else None
        self.user_id: Optional[int] = self.from_user["id"] if self.from_user else None
        self.text:    Optional[str] = (self.message or {}).get("text")
        self.data:    Optional[str] = (self.callback or {}).get("data")

        # Photo support
        self.photo: Optional[list] = (self.message or {}).get("photo")
        self.caption: Optional[str] = (self.message or {}).get("caption")

        self.db_user_id: Optional[int] = None

    def reply(self, text: str, reply_markup: Optional[dict] = None,
              parse_mode: Optional[str] = None):
        if not self.api or self.chat_id is None:
            return
        return self.api.send_message(
            self.chat_id, text,
            reply_markup=reply_markup, parse_mode=parse_mode,
        )

    def answer_callback(self, text: Optional[str] = None, show_alert: bool = False):
        if self.callback and self.api:
            self.api.answer_callback_query(self.callback["id"], text=text, show_alert=show_alert)

    @property
    def is_mother(self) -> bool:
        return self.bot_id == MOTHER_BOT_ID

    @property
    def photo_file_id(self) -> Optional[str]:
        """Highest-resolution photo file_id from the message (if any)."""
        if not self.photo:
            return None
        return self.photo[-1].get("file_id")


def ensure_user(ctx: Context):
    if not ctx.from_user:
        return
    bale_id = int(ctx.from_user["id"])
    row = db.fetchone("SELECT id FROM users WHERE bale_user_id=?", (bale_id,))
    if row:
        ctx.db_user_id = row["id"]
        db.execute(
            """UPDATE users
                  SET username=?, first_name=?, last_name=?,
                      updated_at=datetime('now')
                WHERE bale_user_id=?""",
            (
                ctx.from_user.get("username"),
                ctx.from_user.get("first_name"),
                ctx.from_user.get("last_name"),
                bale_id,
            ),
        )
    else:
        new_id = db.insert(
            """INSERT INTO users
                  (bale_user_id, username, first_name, last_name, language)
               VALUES (?, ?, ?, ?, ?)""",
            (
                bale_id,
                ctx.from_user.get("username"),
                ctx.from_user.get("first_name"),
                ctx.from_user.get("last_name"),
                ctx.from_user.get("language_code") or "fa",
            ),
        )
        ctx.db_user_id = new_id
        db.execute(
            "INSERT INTO wallets (user_id, balance, currency) VALUES (?, 0, 'IRR')",
            (new_id,),
        )


def dispatch(bot_id: int, update: Dict[str, Any]):
    ctx = Context(bot_id, update)
    try:
        ensure_user(ctx)
    except Exception as e:
        log.exception("ensure_user failed: %s", e)

    router = mother_router if ctx.is_mother else child_router

    try:
        # Channel-lock guard (child bots only, on /start)
        if not ctx.is_mother and ctx.user_id and ctx.text and ctx.text == "/start":
            from channel_lock.channel_checker import check_user, prompt_join
            ok, missing = check_user(bot_id, ctx.user_id)
            if not ok:
                prompt_join(ctx, missing)
                return

        # Callback query
        if ctx.callback and ctx.data:
            if ctx.data.startswith("pb:"):
                _handle_page_button(ctx)
                ctx.answer_callback()
                return
            handler = router.resolve_callback(ctx.data)
            if handler:
                handler(ctx)
                return
            module_registry.dispatch_callback(ctx)
            return

        # ----------------------------------------------------
        # PHOTO message (new in this phase)
        # If user is in a FSM state that expects a photo, route
        # to text_input_bus which dispatches by state prefix.
        # ----------------------------------------------------
        if ctx.message and ctx.photo:
            if ctx.user_id and text_input_bus.dispatch(ctx):
                return
            # If no handler wants the photo, fall through to modules
            module_registry.dispatch_message(ctx)
            return

        # Text message
        if ctx.message and ctx.text:

            # Mid-flow: child-bot flow engine
            from flow_engine.step_executor import is_in_flow, resume_flow
            if ctx.user_id and is_in_flow(bot_id, ctx.user_id):
                resume_flow(ctx)
                return

            # Flow trigger detection
            from flow_engine.flow_manager import find_flow_by_trigger
            trig_name = find_flow_by_trigger(bot_id, ctx.text)
            if trig_name:
                from flow_engine.step_executor import start_flow
                start_flow(ctx, trig_name)
                return

            # /command
            if ctx.text.startswith("/"):
                cmd = ctx.text.split()[0][1:].split("@")[0].lower()
                handler = router.resolve_command(cmd)
                if handler:
                    handler(ctx)
                    return
                if cmd == "start" and not ctx.is_mother:
                    _render_start_page(ctx)
                    return

            # Exact text label
            if ctx.text in router._texts:
                router._texts[ctx.text](ctx)
                return

            # FSM bus (text inputs while in admin/user state)
            if text_input_bus.dispatch(ctx):
                return

            # Child bots: open a page whose name matches the text
            if not ctx.is_mother:
                from page_builder import page_manager
                pages = page_manager.list_pages(bot_id)
                if ctx.text in pages:
                    page_manager.send_page(ctx.api, ctx.chat_id, bot_id, ctx.text)
                    return

            # Modules
            module_registry.dispatch_message(ctx)

            # Regex fallback (rarely used now)
            handler = router.resolve_text(ctx.text)
            if handler and ctx.text not in router._texts:
                handler(ctx)
                return

            # Default
            if router.default_handler:
                router.default_handler(ctx)
            return

        # Pre-checkout query
        if ctx.pre_checkout:
            try:
                from payments.bale_gateway import answer_pre_checkout
                answer_pre_checkout(bot_id, ctx.pre_checkout["id"], ok=True)
            except Exception as e:
                log.warning("answer_pre_checkout failed: %s", e)
            return

        if ctx.message and (ctx.message.get("successful_payment")):
            _handle_successful_payment(ctx)
            return

        module_registry.dispatch_message(ctx)

    except Exception as e:
        log.exception("dispatch error on bot %s: %s", bot_id, e)


def _render_start_page(ctx: Context):
    from page_builder import page_manager
    sp = page_manager.get_start_page(ctx.bot_id)
    if sp and page_manager.send_page(ctx.api, ctx.chat_id, ctx.bot_id, sp):
        return
    ctx.reply("سلام 👋\nاین ربات با ربات‌ساز بله ساخته شده است.")


def _handle_page_button(ctx: Context):
    from page_builder.button_manager import decode_cb
    from page_builder import page_manager
    decoded = decode_cb(ctx.data)
    if not decoded:
        return
    action, target = decoded
    if action == "open_page" and target:
        page_manager.send_page(ctx.api, ctx.chat_id, ctx.bot_id, target)
    elif action == "send_message" and target:
        ctx.reply(target)
    elif action == "run_flow" and target:
        from flow_engine.step_executor import start_flow
        start_flow(ctx, target)
    elif action == "call_module" and target:
        mod = module_registry.get(target)
        if mod and mod.on_callback:
            mod.on_callback(ctx)


def _handle_successful_payment(ctx: Context):
    from payments.bale_gateway import parse_payload
    from payments.payment_manager import approve
    sp = ctx.message.get("successful_payment") or {}
    payload = parse_payload(sp.get("invoice_payload", ""))
    pid = payload.get("id")
    if pid:
        try:
            approve(int(pid), gateway_ref=str(sp.get("provider_payment_charge_id", "")))
            ctx.reply("✅ پرداخت با موفقیت انجام شد.")
        except Exception as e:
            log.warning("approve from successful_payment failed: %s", e)
