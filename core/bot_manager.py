# ============================================================
# core/bot_manager.py - Multi-bot orchestration
# ============================================================
# Owns the lifecycle of every bot in the system:
#   - the central MOTHER bot (the SaaS panel)
#   - all CHILD bots created by users (each has its own token)
#
# For each bot we keep:
#   * a BaleAPI client (HTTP)
#   * a Poller thread (getUpdates loop)
#
# All updates funnel into core.dispatcher.dispatch().
# ============================================================

import threading
from typing import Dict, Optional

from database.db import db
from monitoring.logs import get_logger
from core.updater import BaleAPI, Poller

log = get_logger(__name__)


# Sentinel bot_id used for the mother bot.
MOTHER_BOT_ID = 0


class _BotRuntime:
    def __init__(self, bot_id: int, api: BaleAPI, poller: Poller, thread: threading.Thread,
                 is_mother: bool = False):
        self.bot_id = bot_id
        self.api = api
        self.poller = poller
        self.thread = thread
        self.is_mother = is_mother


class BotManager:
    def __init__(self):
        self._bots: Dict[int, _BotRuntime] = {}
        self._lock = threading.RLock()
        self._on_update = None  # set by engine

    # --------------------------------------------------------
    # Wiring
    # --------------------------------------------------------
    def bind_dispatcher(self, on_update):
        """Engine calls this once with the dispatch callback."""
        self._on_update = on_update

    # --------------------------------------------------------
    # Queries
    # --------------------------------------------------------
    def get_api(self, bot_id: int) -> Optional[BaleAPI]:
        rt = self._bots.get(int(bot_id))
        return rt.api if rt else None

    def get_mother_api(self) -> Optional[BaleAPI]:
        return self.get_api(MOTHER_BOT_ID)

    def list_running(self):
        return list(self._bots.keys())

    # --------------------------------------------------------
    # Start / stop
    # --------------------------------------------------------
    def start_mother(self, token: str):
        """Start the mother bot under the fixed id MOTHER_BOT_ID."""
        with self._lock:
            if MOTHER_BOT_ID in self._bots:
                return
            api = BaleAPI(token)
            # Verify token early - surfaces bad config immediately.
            try:
                me = api.get_me()
                log.info("Mother bot authenticated as @%s (id=%s)",
                         me.get("username"), me.get("id"))
            except Exception as e:
                log.error("Mother bot token check failed: %s", e)
                raise

            poller = Poller(api, MOTHER_BOT_ID, initial_offset=0,
                            on_update=self._handle_update)
            t = threading.Thread(target=poller.run, name="poller-mother", daemon=True)
            t.start()
            self._bots[MOTHER_BOT_ID] = _BotRuntime(
                MOTHER_BOT_ID, api, poller, t, is_mother=True
            )

    def start_child(self, bot_row: dict):
        """Start a child bot from a bots-table row."""
        bot_id = int(bot_row["id"])
        with self._lock:
            if bot_id in self._bots:
                return
            api = BaleAPI(bot_row["token"])
            try:
                me = api.get_me()
            except Exception as e:
                log.error("Child bot %s token check failed: %s", bot_id, e)
                return
            offset = int(bot_row.get("last_update_id") or 0)
            poller = Poller(api, bot_id, initial_offset=offset,
                            on_update=self._handle_update)
            t = threading.Thread(target=poller.run, name="poller-bot{}".format(bot_id), daemon=True)
            t.start()
            self._bots[bot_id] = _BotRuntime(bot_id, api, poller, t)
            log.info("Child bot started: id=%s @%s", bot_id, me.get("username"))

    def stop_bot(self, bot_id: int):
        with self._lock:
            rt = self._bots.pop(int(bot_id), None)
            if rt:
                rt.poller.stop()

    def stop_all(self):
        with self._lock:
            for rt in list(self._bots.values()):
                rt.poller.stop()
            self._bots.clear()

    def start_all_child_bots(self):
        """On engine startup, resume polling for every active child bot."""
        rows = db.fetchall("SELECT * FROM bots WHERE status='active'")
        for r in rows:
            self.start_child(r)

    # --------------------------------------------------------
    # Internal: per-update fanout to dispatcher
    # --------------------------------------------------------
    def _handle_update(self, bot_id: int, update: dict):
        if self._on_update is None:
            log.warning("Update arrived but dispatcher not bound yet")
            return
        self._on_update(bot_id, update)


# Singleton
bot_manager = BotManager()
