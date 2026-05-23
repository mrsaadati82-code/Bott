# ============================================================
# page_builder/button_manager.py
# ============================================================
# A Button is the smallest unit a user can place on a page.
#
# Button schema (stored as JSON inside page.content_json):
#   {
#     "text":   str,                 # what the user sees
#     "type":   str,                 # one of BUTTON_TYPES (locked list)
#     "action": str,                 # one of ACTIONS (locked list)
#     "target": str | int | None,    # action-specific target
#     "row":    int (optional)       # which row to place on
#   }
#
# Locked Button Types (from spec):
#   text_button, callback_button, url_button, flow_button, page_button
#
# Locked Action Types (from spec):
#   open_page, run_flow, send_message, url, call_module
# ============================================================

from typing import Dict, List, Any

# Locked lists (additions allowed, removals not)
BUTTON_TYPES = [
    "text_button",      # reply-keyboard text button
    "callback_button",  # inline button with callback_data
    "url_button",       # inline url button
    "flow_button",      # callback button that triggers a flow
    "page_button",      # callback/text button that opens another page
    "photo_button",     # sends a photo when pressed
    "admin_button",     # forwards message to bot admin
]

ACTIONS = [
    "open_page",
    "run_flow",
    "send_message",
    "url",
    "call_module",
    "send_photo",
    "forward_admin",
    "auto_reply",
]


# ------------------------------------------------------------
# Validation
# ------------------------------------------------------------
class ButtonValidationError(ValueError):
    pass


def validate(btn: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate + normalize a button dict. Raises ButtonValidationError
    on bad input; returns the normalized copy on success.
    """
    if not isinstance(btn, dict):
        raise ButtonValidationError("button must be a dict")

    text = (btn.get("text") or "").strip()
    if not text:
        raise ButtonValidationError("button.text is required")
    if len(text) > 64:
        raise ButtonValidationError("button.text too long (max 64)")

    btype = btn.get("type") or "text_button"
    if btype not in BUTTON_TYPES:
        raise ButtonValidationError("unknown button type: {}".format(btype))

    action = btn.get("action") or _default_action_for(btype)
    if action not in ACTIONS:
        raise ButtonValidationError("unknown action: {}".format(action))

    target = btn.get("target")
    _validate_target(action, target)

    return {
        "text":   text,
        "type":   btype,
        "action": action,
        "target": target,
        "row":    int(btn.get("row", 0)),
    }


def _default_action_for(btype: str) -> str:
    return {
        "text_button":     "send_message",
        "callback_button": "send_message",
        "url_button":      "url",
        "flow_button":     "run_flow",
        "page_button":     "open_page",
    }.get(btype, "send_message")


def _validate_target(action: str, target):
    if action == "url":
        if not isinstance(target, str) or not target.startswith(("http://", "https://")):
            raise ButtonValidationError("url action requires http(s) target")
    elif action in ("open_page", "run_flow", "call_module"):
        if target is None or str(target).strip() == "":
            raise ButtonValidationError("{} requires a target".format(action))
    elif action == "send_photo":
        # target should be a file_id or URL
        if target is None or str(target).strip() == "":
            raise ButtonValidationError("send_photo requires a photo file_id or URL")
    elif action in ("forward_admin", "auto_reply"):
        # target is optional
        return
    elif action == "send_message":
        # target is optional message text; default = button text
        return


# ------------------------------------------------------------
# Rendering: convert a list of buttons -> Bale keyboards
# ------------------------------------------------------------
def render_keyboards(buttons: List[Dict[str, Any]]):
    """
    Splits buttons into:
      * reply keyboard (text_button) → {"keyboard": [...]}
      * inline keyboard (everything else) → {"inline_keyboard": [...]}
    Returns (reply_markup, inline_markup) where each may be None.
    """
    if not buttons:
        return None, None

    # Group by row id then by insertion order
    reply_rows: Dict[int, List[dict]]  = {}
    inline_rows: Dict[int, List[dict]] = {}

    for i, raw in enumerate(buttons):
        try:
            b = validate(raw)
        except ButtonValidationError:
            continue
        row = b.get("row", 0)
        if b["type"] == "text_button":
            reply_rows.setdefault(row, []).append(b)
        else:
            inline_rows.setdefault(row, []).append(b)

    reply_markup = None
    if reply_rows:
        kb = []
        for row_id in sorted(reply_rows.keys()):
            kb.append([{"text": b["text"]} for b in reply_rows[row_id]])
        reply_markup = {
            "keyboard": kb,
            "resize_keyboard": True,
            "one_time_keyboard": False,
        }

    inline_markup = None
    if inline_rows:
        kb = []
        for row_id in sorted(inline_rows.keys()):
            row = []
            for b in inline_rows[row_id]:
                if b["action"] == "url":
                    row.append({"text": b["text"], "url": b["target"]})
                else:
                    # encode action+target into callback_data
                    row.append({"text": b["text"],
                                "callback_data": _encode_cb(b)})
            kb.append(row)
        inline_markup = {"inline_keyboard": kb}

    return reply_markup, inline_markup


# ------------------------------------------------------------
# Callback data encoding
# Format: pb:<action>:<target>
# (kept short to respect Bale's callback_data byte limit)
# ------------------------------------------------------------
def _encode_cb(btn: dict) -> str:
    return "pb:{}:{}".format(btn["action"], btn.get("target") or "")


def decode_cb(data: str):
    """Decode pb:<action>:<target> -> (action, target). Returns None if not ours."""
    if not data or not data.startswith("pb:"):
        return None
    parts = data.split(":", 2)
    if len(parts) < 3:
        return None
    return parts[1], parts[2] or None
