# ============================================================
# flow_engine/variable_manager.py
# ============================================================
# Per-(bot, user, flow) variable storage used during a flow run.
# Backed by state_manager.data so it's process-local in phase 3.
# Phase 4 can swap to DB-backed without touching callers.
# ============================================================

from typing import Any, Dict, Optional

from core.state_manager import state_manager


VARS_KEY = "_flow_vars"


def _entry(bot_id: int, user_id: int) -> Dict[str, Any]:
    data = state_manager.get_data(bot_id, user_id)
    if VARS_KEY not in data:
        data[VARS_KEY] = {}
        state_manager.update_data(bot_id, user_id, **{VARS_KEY: data[VARS_KEY]})
    return data[VARS_KEY]


def set_var(bot_id: int, user_id: int, name: str, value: Any):
    vars_ = _entry(bot_id, user_id)
    vars_[name] = value
    state_manager.update_data(bot_id, user_id, **{VARS_KEY: vars_})


def get_var(bot_id: int, user_id: int, name: str, default: Any = None) -> Any:
    return _entry(bot_id, user_id).get(name, default)


def get_all(bot_id: int, user_id: int) -> Dict[str, Any]:
    return dict(_entry(bot_id, user_id))


def clear(bot_id: int, user_id: int):
    state_manager.update_data(bot_id, user_id, **{VARS_KEY: {}})


# ------------------------------------------------------------
# Template substitution: "سلام {name}، شماره {phone}"
# ------------------------------------------------------------
def render_template(text: str, bot_id: int, user_id: int,
                    extra: Optional[Dict[str, Any]] = None) -> str:
    if not text or "{" not in text:
        return text or ""
    merged = dict(_entry(bot_id, user_id))
    if extra:
        merged.update(extra)
    # str.format_map with a safe fallback so missing keys don't crash
    class _SafeDict(dict):
        def __missing__(self, key):
            return "{" + key + "}"
    try:
        return text.format_map(_SafeDict(merged))
    except Exception:
        return text
