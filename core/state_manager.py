# ============================================================
# core/state_manager.py - Per-user FSM state
# ============================================================

import threading
import time
from typing import Any, Dict, Optional


class StateManager:
    def __init__(self):
        self._lock = threading.RLock()
        self._states: Dict[tuple, Dict[str, Any]] = {}

    def _k(self, bot_id: int, user_id: int) -> tuple:
        return (int(bot_id), int(user_id))

    def set(self, bot_id: int, user_id: int, state: str, data: Optional[dict] = None):
        with self._lock:
            self._states[self._k(bot_id, user_id)] = {
                "state": state,
                "data": data or {},
                "ts": time.time(),
            }

    def update_data(self, bot_id: int, user_id: int, **kwargs):
        with self._lock:
            entry = self._states.get(self._k(bot_id, user_id))
            if not entry:
                entry = {"state": None, "data": {}, "ts": time.time()}
                self._states[self._k(bot_id, user_id)] = entry
            entry["data"].update(kwargs)
            entry["ts"] = time.time()

    def get(self, bot_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._states.get(self._k(bot_id, user_id))

    def get_state(self, bot_id: int, user_id: int) -> Optional[str]:
        entry = self.get(bot_id, user_id)
        return entry["state"] if entry else None

    def get_data(self, bot_id: int, user_id: int) -> dict:
        entry = self.get(bot_id, user_id)
        return entry["data"] if entry else {}

    def starts_with(self, bot_id: int, user_id: int, prefix: str) -> bool:
        """True if current state starts with given prefix (e.g. 'admin:' or 'user:')."""
        st = self.get_state(bot_id, user_id)
        return bool(st and st.startswith(prefix))

    def clear(self, bot_id: int, user_id: int):
        with self._lock:
            self._states.pop(self._k(bot_id, user_id), None)

    def cleanup(self, max_age_seconds: int = 3 * 3600):
        with self._lock:
            cutoff = time.time() - max_age_seconds
            stale = [k for k, v in self._states.items() if v["ts"] < cutoff]
            for k in stale:
                self._states.pop(k, None)


# ============================================================
# Text Input Bus - solves regex collision between admin & user
# ============================================================
# Many handlers want to receive a user's free-text reply while
# the user is in a specific FSM state. Instead of competing
# regex handlers in router.py, all of them register a callback
# with this bus, keyed by their state PREFIX (e.g. "admin:wallet").
#
# The dispatcher consults this bus AFTER trying exact-text /
# command matches and BEFORE the regex fallback.
# ============================================================

class TextInputBus:
    def __init__(self):
        self._handlers: Dict[str, Any] = {}  # prefix -> callable(ctx)

    def on(self, prefix: str):
        """Decorator: register a handler for any state matching `prefix*`."""
        def deco(fn):
            self._handlers[prefix] = fn
            return fn
        return deco

    def dispatch(self, ctx) -> bool:
        """If user is in a state matching any registered prefix, call it.
        Returns True if a handler was invoked."""
        if not ctx.user_id:
            return False
        st = state_manager.get_state(ctx.bot_id, ctx.user_id)
        if not st:
            return False
        # Try longest-match first so 'admin:wallet:add' wins over 'admin:'
        for prefix in sorted(self._handlers.keys(), key=len, reverse=True):
            if st.startswith(prefix):
                self._handlers[prefix](ctx)
                return True
        return False


# Singletons
state_manager = StateManager()
text_input_bus = TextInputBus()
