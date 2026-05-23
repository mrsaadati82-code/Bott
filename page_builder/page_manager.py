# ============================================================
# page_builder/page_manager.py
# ============================================================
# A "page" is a screen the bot owner designs visually:
#   - page_name (unique per bot)
#   - text (main body shown to user)
#   - buttons[] (list of button dicts; see button_manager.py)
#
# Pages live inside bots.settings_json under the key 'pages':
#   {
#     "pages": {
#       "home":   {"text": "...", "buttons": [...]},
#       "about":  {...},
#       ...
#     },
#     "start_page": "home"
#   }
#
# This file is the ONLY place that mutates that structure.
# ============================================================

import json
from typing import Dict, List, Optional, Any

from database.db import db
from page_builder.button_manager import validate as validate_button, render_keyboards

START_PAGE_DEFAULT = "home"


# ------------------------------------------------------------
# Settings I/O
# ------------------------------------------------------------
def _load_settings(bot_id: int) -> dict:
    row = db.fetchone("SELECT settings_json FROM bots WHERE id=?", (int(bot_id),))
    if not row:
        raise ValueError("bot not found")
    try:
        return json.loads(row.get("settings_json") or "{}")
    except Exception:
        return {}


def _save_settings(bot_id: int, settings: dict):
    db.execute(
        "UPDATE bots SET settings_json=?, updated_at=datetime('now') WHERE id=?",
        (json.dumps(settings, ensure_ascii=False), int(bot_id)),
    )


def _pages_block(settings: dict) -> dict:
    if "pages" not in settings or not isinstance(settings["pages"], dict):
        settings["pages"] = {}
    return settings["pages"]


# ------------------------------------------------------------
# Public CRUD
# ------------------------------------------------------------
def list_pages(bot_id: int) -> List[str]:
    s = _load_settings(bot_id)
    return list(_pages_block(s).keys())


def get_page(bot_id: int, page_name: str) -> Optional[Dict[str, Any]]:
    s = _load_settings(bot_id)
    return _pages_block(s).get(page_name)


def create_page(bot_id: int, page_name: str, text: str = "",
                buttons: Optional[List[dict]] = None) -> dict:
    page_name = page_name.strip()
    if not page_name:
        raise ValueError("page_name is required")
    s = _load_settings(bot_id)
    pages = _pages_block(s)
    if page_name in pages:
        raise ValueError("page '{}' already exists".format(page_name))
    page = {
        "text": text or page_name,
        "buttons": [validate_button(b) for b in (buttons or [])],
    }
    pages[page_name] = page
    if not s.get("start_page"):
        s["start_page"] = page_name
    _save_settings(bot_id, s)
    return page


def update_page(bot_id: int, page_name: str,
                text: Optional[str] = None,
                buttons: Optional[List[dict]] = None) -> dict:
    s = _load_settings(bot_id)
    pages = _pages_block(s)
    page = pages.get(page_name)
    if not page:
        raise ValueError("page '{}' not found".format(page_name))
    if text is not None:
        page["text"] = text
    if buttons is not None:
        page["buttons"] = [validate_button(b) for b in buttons]
    _save_settings(bot_id, s)
    return page


def delete_page(bot_id: int, page_name: str):
    s = _load_settings(bot_id)
    pages = _pages_block(s)
    if page_name in pages:
        del pages[page_name]
        if s.get("start_page") == page_name:
            s["start_page"] = next(iter(pages.keys()), None)
        _save_settings(bot_id, s)


def add_button(bot_id: int, page_name: str, button: dict):
    btn = validate_button(button)
    s = _load_settings(bot_id)
    page = _pages_block(s).get(page_name)
    if not page:
        raise ValueError("page not found")
    page.setdefault("buttons", []).append(btn)
    _save_settings(bot_id, s)


def remove_button(bot_id: int, page_name: str, index: int):
    s = _load_settings(bot_id)
    page = _pages_block(s).get(page_name)
    if not page:
        return
    btns = page.get("buttons") or []
    if 0 <= index < len(btns):
        btns.pop(index)
        page["buttons"] = btns
        _save_settings(bot_id, s)


def set_start_page(bot_id: int, page_name: str):
    s = _load_settings(bot_id)
    if page_name not in _pages_block(s):
        raise ValueError("page not found")
    s["start_page"] = page_name
    _save_settings(bot_id, s)


def get_start_page(bot_id: int) -> Optional[str]:
    s = _load_settings(bot_id)
    return s.get("start_page")


# ------------------------------------------------------------
# Rendering
# ------------------------------------------------------------
def render_page(bot_id: int, page_name: str):
    """
    Returns (text, reply_markup, inline_markup) for a page, or
    (None, None, None) if the page doesn't exist.
    """
    page = get_page(bot_id, page_name)
    if not page:
        return None, None, None
    reply_kb, inline_kb = render_keyboards(page.get("buttons") or [])
    return page.get("text") or page_name, reply_kb, inline_kb


def send_page(api, chat_id: int, bot_id: int, page_name: str) -> bool:
    """Convenience: send a page to a chat using the given BaleAPI."""
    text, reply_kb, inline_kb = render_page(bot_id, page_name)
    if text is None:
        return False
    # Bale doesn't accept both reply + inline in the same message,
    # so when both exist we send the page text with reply_kb and
    # then attach the inline buttons in a follow-up message.
    if reply_kb and inline_kb:
        api.send_message(chat_id, text, reply_markup=reply_kb)
        api.send_message(chat_id, "👇", reply_markup=inline_kb)
    elif inline_kb:
        api.send_message(chat_id, text, reply_markup=inline_kb)
    else:
        api.send_message(chat_id, text, reply_markup=reply_kb)
    return True
