# ============================================================
# core/engine.py - The system boot orchestrator
# ============================================================

import signal
import time

from config import MOTHER_BOT_TOKEN, APP_NAME, APP_VERSION
from database.migrations import init_database
from monitoring.logs import get_logger
from core.bot_manager import bot_manager
from core.dispatcher import dispatch
from core.router import mother_router, child_router
from core.permission_manager import is_super_admin, get_role
from core.keyboards import reply_keyboard

log = get_logger(__name__)


class Engine:
    def __init__(self):
        self._running = False

    def start(self):
        log.info("Booting %s v%s ...", APP_NAME, APP_VERSION)

        # 1) DB
        init_database()
        log.info("Database initialized.")

        # 1.b) Auto-discover Templates + Modules from /builtin/
        from templates import template_registry
        template_registry.discover()
        template_registry.sync_to_db()
        log.info("Templates: %s", [t.key for t in template_registry.all_templates()])

        from modules.module_loader import discover_and_register
        discover_and_register()

        # 2) Dispatcher wiring
        bot_manager.bind_dispatcher(dispatch)

        # 3) Handlers
        self._register_baseline_handlers()

        # 3.b) Admin/User panel
        from admin_panel import setup_all as setup_admin
        setup_admin()
        log.info("Admin + user panel handlers registered.")

        # 3.c) Broadcast worker
        from broadcast.broadcast_manager import start_worker as start_bcast
        start_bcast()
        log.info("Broadcast worker started.")

        # 4) Mother bot
        if not MOTHER_BOT_TOKEN or MOTHER_BOT_TOKEN.startswith("PUT_YOUR"):
            log.error("MOTHER_BOT_TOKEN is not configured. Edit botbuilder/config.py first.")
            return
        bot_manager.start_mother(MOTHER_BOT_TOKEN)
        log.info("Mother bot poller running.")

        # 5) Resume child bots
        bot_manager.start_all_child_bots()

        # 6) Stay alive
        self._running = True
        signal.signal(signal.SIGINT, self._on_signal)
        signal.signal(signal.SIGTERM, self._on_signal)

        log.info("Engine ready. Press Ctrl+C to stop.")
        try:
            while self._running:
                time.sleep(1)
        finally:
            self.stop()

    def stop(self):
        if not self._running:
            return
        self._running = False
        log.info("Shutting down ...")
        try:
            from broadcast.broadcast_manager import stop_worker
            stop_worker()
        except Exception:
            pass
        bot_manager.stop_all()
        log.info("Bye.")

    def _on_signal(self, signum, frame):
        log.info("Signal %s received.", signum)
        self._running = False

    def _register_baseline_handlers(self):

        @mother_router.command("start")
        def _start(ctx):
            parts = (ctx.text or "").split(maxsplit=1)
            if len(parts) > 1:
                from reseller.affiliate_manager import parse_ref_code, set_referrer
                ref = parse_ref_code(parts[1])
                if ref and ctx.db_user_id:
                    set_referrer(ctx.db_user_id, ref)

            role_msg = ""
            if ctx.user_id and is_super_admin(ctx.user_id):
                role_msg = "🛡 سوپرادمین. /admin"
            elif ctx.user_id and get_role(ctx.user_id) == "admin":
                role_msg = "🛠 ادمین. /admin"
            elif ctx.user_id and get_role(ctx.user_id) == "reseller":
                role_msg = "🧑‍💼 نماینده. /reseller"

            from admin_panel.user_panel import get_user_main_kb
            ctx.reply(
                "سلام {} 👋\n\n"
                "به ربات‌ساز بله خوش آمدید.\n{}".format(
                    (ctx.from_user or {}).get("first_name", "دوست عزیز"),
                    role_msg,
                ).strip(),
                reply_markup=get_user_main_kb(),
            )

        @mother_router.command("ping")
        def _ping(ctx):
            ctx.reply("pong ✅")

        @mother_router.command("whoami")
        def _whoami(ctx):
            ctx.reply(
                "🆔 user_id: {}\n👤 username: @{}\n🎭 role: {}".format(
                    ctx.user_id,
                    (ctx.from_user or {}).get("username", "-"),
                    get_role(ctx.user_id) if ctx.user_id else "-",
                )
            )

        @mother_router.default
        def _fallback(ctx):
            if ctx.text and ctx.text.startswith("/"):
                ctx.reply("دستور نامشخص. /start را ارسال کنید.")


engine = Engine()
