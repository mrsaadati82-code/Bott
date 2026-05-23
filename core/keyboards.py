# ============================================================
# core/keyboards.py - Reply & Inline keyboard builders
# ============================================================
# A tiny DSL to avoid repeating the same dict structures in
# every handler. All keyboards in the project go through here.
#
# Reply keyboard (visible at the bottom of chat):
#     reply_keyboard([["A", "B"], ["C"]])
#
# Inline keyboard (buttons attached to a message):
#     inline([
#         [("📊 آمار", "stats")],
#         [("✅ تایید", "ok"), ("❌ رد", "no")],
#     ])
#     # or with URL buttons:
#     inline([[("سایت ما", {"url": "https://example.com"})]])
# ============================================================

from typing import List, Tuple, Union, Dict


def reply_keyboard(rows: List[List[str]],
                   resize: bool = True,
                   one_time: bool = False) -> Dict:
    """Build a ReplyKeyboardMarkup."""
    keyboard = [[{"text": str(label)} for label in row] for row in rows]
    return {
        "keyboard": keyboard,
        "resize_keyboard": resize,
        "one_time_keyboard": one_time,
    }


def remove_keyboard() -> Dict:
    return {"remove_keyboard": True}


def inline(rows: List[List[Tuple[str, Union[str, Dict]]]]) -> Dict:
    """
    Build an InlineKeyboardMarkup.

    Each cell is (text, data) where data is either:
      - str       -> becomes callback_data
      - {"url": ...}             -> becomes url button
      - {"callback_data": ...}   -> explicit
    """
    keyboard = []
    for row in rows:
        new_row = []
        for text, data in row:
            btn = {"text": str(text)}
            if isinstance(data, dict):
                btn.update(data)
            else:
                btn["callback_data"] = str(data)
            new_row.append(btn)
        keyboard.append(new_row)
    return {"inline_keyboard": keyboard}
