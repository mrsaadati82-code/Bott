# ============================================================
# flow_engine/step_executor.py
# ============================================================
# Drives a flow forward step by step.
#
# Flow state stored via state_manager:
#   state = "flow:<flow_name>"
#   data  = {"_flow_idx": int, "_flow_vars": {...}, ...}
#
# Public entry points:
#   start_flow(ctx, flow_name)        -> begins a flow
#   resume_flow(ctx)                  -> called by dispatcher when
#                                        an ask_* step is awaiting input
# ============================================================

from datetime import datetime
from typing import Optional

from core.state_manager import state_manager
from flow_engine import flow_manager
from flow_engine.variable_manager import (
    set_var, get_all, render_template, clear as clear_vars, VARS_KEY,
)
from modules.module_registry import module_registry
from monitoring.logs import get_logger

log = get_logger(__name__)


FLOW_STATE_PREFIX = "flow:"
IDX_KEY = "_flow_idx"


# ============================================================
# Entry / detection
# ============================================================
def is_in_flow(bot_id: int, user_id: int) -> Optional[str]:
    st = state_manager.get_state(bot_id, user_id)
    if st and st.startswith(FLOW_STATE_PREFIX):
        return st[len(FLOW_STATE_PREFIX):]
    return None


def start_flow(ctx, flow_name: str):
    flow = flow_manager.get_flow(ctx.bot_id, flow_name)
    if not flow:
        ctx.reply("⚠️ Flow '{}' یافت نشد.".format(flow_name))
        return
    # Reset state + variables
    state_manager.set(
        ctx.bot_id, ctx.user_id,
        FLOW_STATE_PREFIX + flow_name,
        {IDX_KEY: 0, VARS_KEY: {}},
    )
    _run_until_input(ctx, flow_name)


def resume_flow(ctx):
    """Called by dispatcher when user sends a message while in a flow."""
    flow_name = is_in_flow(ctx.bot_id, ctx.user_id)
    if not flow_name:
        return False
    flow = flow_manager.get_flow(ctx.bot_id, flow_name)
    if not flow:
        state_manager.clear(ctx.bot_id, ctx.user_id)
        return False

    data = state_manager.get_data(ctx.bot_id, ctx.user_id)
    idx = int(data.get(IDX_KEY, 0))
    steps = flow.get("steps") or []
    if idx >= len(steps):
        _finish(ctx)
        return True

    current = steps[idx]
    t = current.get("type")

    # Only ask_* steps consume input
    if t in ("ask_text", "ask_number", "ask_phone", "ask_location"):
        if not _capture_input(ctx, current):
            return True  # asked again, still waiting
        # advance
        data[IDX_KEY] = idx + 1
        state_manager.update_data(ctx.bot_id, ctx.user_id, **{IDX_KEY: idx + 1})
        _run_until_input(ctx, flow_name)
        return True

    # If we're here, the current step isn't waiting - just advance.
    data[IDX_KEY] = idx + 1
    state_manager.update_data(ctx.bot_id, ctx.user_id, **{IDX_KEY: idx + 1})
    _run_until_input(ctx, flow_name)
    return True


# ============================================================
# Engine loop
# ============================================================
def _run_until_input(ctx, flow_name: str):
    """Execute steps sequentially until one needs user input or flow ends."""
    flow = flow_manager.get_flow(ctx.bot_id, flow_name)
    steps = (flow or {}).get("steps") or []

    while True:
        data = state_manager.get_data(ctx.bot_id, ctx.user_id)
        idx = int(data.get(IDX_KEY, 0))
        if idx >= len(steps):
            _finish(ctx)
            return

        step = steps[idx]
        t = step.get("type")

        if t == "send_message":
            _do_send_message(ctx, step)
            _advance(ctx)
            continue

        if t == "send_media":
            _do_send_media(ctx, step)
            _advance(ctx)
            continue

        if t == "save_variable":
            _do_save_variable(ctx, step)
            _advance(ctx)
            continue

        if t == "condition":
            _do_condition(ctx, step)
            # condition mutates idx itself
            continue

        if t == "call_module":
            _do_call_module(ctx, step)
            _advance(ctx)
            continue

        if t == "finish":
            _finish(ctx)
            return

        # ask_* steps: prompt and wait for next message
        if t in ("ask_text", "ask_number", "ask_phone", "ask_location"):
            prompt = step.get("prompt") or "لطفاً پاسخ دهید:"
            prompt = render_template(prompt, ctx.bot_id, ctx.user_id)
            ctx.reply(prompt)
            return  # wait

        # unknown -> skip
        log.warning("Unknown step type encountered: %s", t)
        _advance(ctx)


# ============================================================
# Step implementations
# ============================================================
def _do_send_message(ctx, step: dict):
    text = render_template(step.get("text") or "", ctx.bot_id, ctx.user_id)
    if text:
        ctx.reply(text)


def _do_send_media(ctx, step: dict):
    """Minimal media: by file_id."""
    kind = step.get("media_type", "photo")
    file_id = step.get("file_id")
    caption = render_template(step.get("caption", ""), ctx.bot_id, ctx.user_id)
    if not file_id or not ctx.api:
        return
    method = {"photo": "sendPhoto", "video": "sendVideo",
              "document": "sendDocument", "audio": "sendAudio"}.get(kind, "sendPhoto")
    payload = {"chat_id": ctx.chat_id, kind: file_id}
    if caption:
        payload["caption"] = caption
    try:
        ctx.api.call(method, payload)
    except Exception as e:
        log.warning("send_media failed: %s", e)


def _do_save_variable(ctx, step: dict):
    name  = step["var"]
    value = step.get("value")
    if value == "now":
        value = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(value, str):
        value = render_template(value, ctx.bot_id, ctx.user_id)
    set_var(ctx.bot_id, ctx.user_id, name, value)


def _do_condition(ctx, step: dict):
    """
    Very small condition language:
        {"if": {"var": "age", "op": ">=", "value": 18},
         "then": <step_index_or_label>,
         "else": <step_index_or_label>}
    Currently 'then'/'else' must be integer indices (0-based).
    """
    cond = step.get("if") or {}
    var_name = cond.get("var")
    op = cond.get("op", "==")
    rhs = cond.get("value")
    lhs = get_all(ctx.bot_id, ctx.user_id).get(var_name)

    try:
        if op == "==":   ok = lhs == rhs
        elif op == "!=": ok = lhs != rhs
        elif op == ">":  ok = float(lhs) > float(rhs)
        elif op == ">=": ok = float(lhs) >= float(rhs)
        elif op == "<":  ok = float(lhs) < float(rhs)
        elif op == "<=": ok = float(lhs) <= float(rhs)
        elif op == "in": ok = lhs in (rhs or [])
        else:            ok = False
    except Exception:
        ok = False

    target = step.get("then") if ok else step.get("else")
    if isinstance(target, int):
        state_manager.update_data(ctx.bot_id, ctx.user_id, **{IDX_KEY: int(target)})
    else:
        _advance(ctx)


def _do_call_module(ctx, step: dict):
    mod_key = step.get("module")
    mod = module_registry.get(mod_key) if mod_key else None
    if not mod or not mod.on_message:
        return
    try:
        # Pass flow vars to module via ctx (lightweight injection)
        setattr(ctx, "flow_vars", get_all(ctx.bot_id, ctx.user_id))
        mod.on_message(ctx)
    except Exception as e:
        log.warning("call_module %s failed: %s", mod_key, e)


# ============================================================
# Input capture for ask_*
# ============================================================
def _capture_input(ctx, step: dict) -> bool:
    """
    Read user reply matching the current ask step.
    Returns True on accept, False on retry (already asked again).
    """
    t = step["type"]
    var = step["var"]

    if t == "ask_text":
        if not ctx.text:
            ctx.reply("لطفاً متن ارسال کنید.")
            return False
        set_var(ctx.bot_id, ctx.user_id, var, ctx.text)
        return True

    if t == "ask_number":
        if not ctx.text or not ctx.text.strip().lstrip("-").isdigit():
            ctx.reply("لطفاً یک عدد معتبر ارسال کنید.")
            return False
        set_var(ctx.bot_id, ctx.user_id, var, int(ctx.text.strip()))
        return True

    if t == "ask_phone":
        # Accept either text (phone number) OR a contact attachment.
        contact = (ctx.message or {}).get("contact")
        if contact and contact.get("phone_number"):
            set_var(ctx.bot_id, ctx.user_id, var, contact["phone_number"])
            return True
        if ctx.text and any(c.isdigit() for c in ctx.text):
            set_var(ctx.bot_id, ctx.user_id, var, ctx.text.strip())
            return True
        ctx.reply("لطفاً شماره تلفن خود را ارسال کنید.")
        return False

    if t == "ask_location":
        loc = (ctx.message or {}).get("location")
        if loc:
            set_var(ctx.bot_id, ctx.user_id, var,
                    {"lat": loc.get("latitude"), "lon": loc.get("longitude")})
            return True
        ctx.reply("لطفاً موقعیت مکانی خود را ارسال کنید.")
        return False

    return False


# ============================================================
# Helpers
# ============================================================
def _advance(ctx):
    data = state_manager.get_data(ctx.bot_id, ctx.user_id)
    idx = int(data.get(IDX_KEY, 0)) + 1
    state_manager.update_data(ctx.bot_id, ctx.user_id, **{IDX_KEY: idx})


def _finish(ctx):
    state_manager.clear(ctx.bot_id, ctx.user_id)
