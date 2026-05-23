# ============================================================
# flow_engine/flow_manager.py
# ============================================================
# A Flow is a JSON-defined conversation. Flows live inside
# bots.settings_json under the key 'flows':
#
#   {
#     "flows": {
#       "register": {
#         "trigger": "/register",         # optional command/text
#         "steps": [
#             {"type": "send_message", "text": "خوش آمدید"},
#             {"type": "ask_text",     "var":  "name", "prompt": "نامتان؟"},
#             {"type": "ask_phone",    "var":  "phone"},
#             {"type": "save_variable","var":  "registered_at", "value": "now"},
#             {"type": "send_message", "text": "ثبت‌نام انجام شد {name}"},
#             {"type": "finish"}
#         ]
#       }
#     }
#   }
#
# Locked step types (from spec):
#   send_message, ask_text, ask_number, ask_phone, ask_location,
#   send_media, condition, save_variable, call_module, finish
# ============================================================

import json
from typing import Dict, List, Optional, Any

from database.db import db


STEP_TYPES = [
    "send_message",
    "ask_text",
    "ask_number",
    "ask_phone",
    "ask_location",
    "send_media",
    "condition",
    "save_variable",
    "call_module",
    "finish",
]


# ------------------------------------------------------------
# Settings I/O (kept independent from page_manager to avoid
# import cycles)
# ------------------------------------------------------------
def _load(bot_id: int) -> dict:
    row = db.fetchone("SELECT settings_json FROM bots WHERE id=?", (int(bot_id),))
    if not row:
        raise ValueError("bot not found")
    try:
        return json.loads(row.get("settings_json") or "{}")
    except Exception:
        return {}


def _save(bot_id: int, settings: dict):
    db.execute(
        "UPDATE bots SET settings_json=?, updated_at=datetime('now') WHERE id=?",
        (json.dumps(settings, ensure_ascii=False), int(bot_id)),
    )


def _flows_block(settings: dict) -> dict:
    if "flows" not in settings or not isinstance(settings["flows"], dict):
        settings["flows"] = {}
    return settings["flows"]


# ------------------------------------------------------------
# Validation
# ------------------------------------------------------------
class FlowValidationError(ValueError):
    pass


def validate_step(step: dict) -> dict:
    if not isinstance(step, dict):
        raise FlowValidationError("step must be a dict")
    t = step.get("type")
    if t not in STEP_TYPES:
        raise FlowValidationError("unknown step type: {}".format(t))
    # Per-type required fields
    if t == "send_message":
        if not step.get("text"):
            raise FlowValidationError("send_message requires 'text'")
    elif t in ("ask_text", "ask_number", "ask_phone", "ask_location"):
        if not step.get("var"):
            raise FlowValidationError("{} requires 'var'".format(t))
    elif t == "save_variable":
        if not step.get("var"):
            raise FlowValidationError("save_variable requires 'var'")
    elif t == "condition":
        if "if" not in step or "then" not in step:
            raise FlowValidationError("condition requires 'if' and 'then'")
    elif t == "call_module":
        if not step.get("module"):
            raise FlowValidationError("call_module requires 'module'")
    return step


def validate_flow(flow: dict) -> dict:
    if not isinstance(flow, dict):
        raise FlowValidationError("flow must be a dict")
    steps = flow.get("steps") or []
    if not isinstance(steps, list) or not steps:
        raise FlowValidationError("flow.steps must be a non-empty list")
    flow["steps"] = [validate_step(s) for s in steps]
    return flow


# ------------------------------------------------------------
# Public CRUD
# ------------------------------------------------------------
def list_flows(bot_id: int) -> List[str]:
    return list(_flows_block(_load(bot_id)).keys())


def get_flow(bot_id: int, flow_name: str) -> Optional[dict]:
    return _flows_block(_load(bot_id)).get(flow_name)


def create_flow(bot_id: int, flow_name: str, steps: List[dict],
                trigger: Optional[str] = None) -> dict:
    flow_name = flow_name.strip()
    if not flow_name:
        raise FlowValidationError("flow_name is required")
    s = _load(bot_id)
    flows = _flows_block(s)
    if flow_name in flows:
        raise FlowValidationError("flow '{}' already exists".format(flow_name))
    flow = validate_flow({"trigger": trigger or "", "steps": steps})
    flows[flow_name] = flow
    _save(bot_id, s)
    return flow


def update_flow(bot_id: int, flow_name: str, steps: Optional[List[dict]] = None,
                trigger: Optional[str] = None) -> dict:
    s = _load(bot_id)
    flows = _flows_block(s)
    if flow_name not in flows:
        raise FlowValidationError("flow not found")
    if steps is not None:
        flows[flow_name]["steps"] = [validate_step(x) for x in steps]
    if trigger is not None:
        flows[flow_name]["trigger"] = trigger
    _save(bot_id, s)
    return flows[flow_name]


def delete_flow(bot_id: int, flow_name: str):
    s = _load(bot_id)
    flows = _flows_block(s)
    if flow_name in flows:
        del flows[flow_name]
        _save(bot_id, s)


def find_flow_by_trigger(bot_id: int, text: str) -> Optional[str]:
    """If a flow has trigger == text, return its name."""
    if not text:
        return None
    flows = _flows_block(_load(bot_id))
    for name, f in flows.items():
        trig = (f.get("trigger") or "").strip()
        if trig and trig == text:
            return name
    return None
