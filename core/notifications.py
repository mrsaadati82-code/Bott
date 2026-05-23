# ============================================================
# core/notifications.py - Central notification dispatcher
# ============================================================
# Sends DM notifications via the mother bot to:
#   - the affected user (e.g. wallet credited)
#   - all super-admins (e.g. new payment to approve)
# Failures are logged and swallowed - never break a flow.
# ============================================================

from typing import Optional, List

from database.db import db
from config import SUPER_ADMIN_IDS
from core.bot_manager import bot_manager
from monitoring.logs import get_logger

log = get_logger(__name__)


def _api():
    return bot_manager.get_mother_api()


def _safe_send(chat_id: int, text: str, reply_markup: Optional[dict] = None,
               parse_mode: Optional[str] = None):
    api = _api()
    if not api:
        return False
    try:
        api.send_message(chat_id, text,
                         reply_markup=reply_markup, parse_mode=parse_mode)
        return True
    except Exception as e:
        log.debug("notify failed to %s: %s", chat_id, e)
        return False


def _safe_send_photo(chat_id: int, file_id: str, caption: str = "",
                     reply_markup: Optional[dict] = None):
    api = _api()
    if not api:
        return False
    try:
        payload = {"chat_id": chat_id, "photo": file_id, "caption": caption}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        api.call("sendPhoto", payload)
        return True
    except Exception as e:
        log.debug("photo notify failed to %s: %s", chat_id, e)
        return False


# ------------------------------------------------------------
# Target resolution
# ------------------------------------------------------------
def _super_admin_chat_ids() -> List[int]:
    """All chat_ids that should receive admin notifications.
    Source 1: SUPER_ADMIN_IDS from config (raw Bale user ids).
    Source 2: admins table with role='super_admin' (joined to users).
    """
    out = set()
    for x in SUPER_ADMIN_IDS:
        try:
            out.add(int(x))
        except (TypeError, ValueError):
            continue
    rows = db.fetchall(
        """SELECT u.bale_user_id FROM admins a
             JOIN users u ON u.id = a.user_id
             WHERE a.role='super_admin'"""
    )
    for r in rows:
        out.add(int(r["bale_user_id"]))
    return list(out)


def _bale_id_of_user(user_id: int) -> Optional[int]:
    row = db.fetchone("SELECT bale_user_id FROM users WHERE id=?", (int(user_id),))
    return int(row["bale_user_id"]) if row else None


# ============================================================
# Public notifiers
# ============================================================
def notify_user(user_id: int, text: str, reply_markup: Optional[dict] = None,
                parse_mode: Optional[str] = None) -> bool:
    """Send a DM to a user via the mother bot. user_id is users.id."""
    bale_id = _bale_id_of_user(user_id)
    if not bale_id:
        return False
    return _safe_send(bale_id, text, reply_markup, parse_mode)


def notify_super_admins(text: str, reply_markup: Optional[dict] = None,
                        parse_mode: Optional[str] = None) -> int:
    """Send to every super-admin. Returns count of successful sends."""
    n = 0
    for cid in _super_admin_chat_ids():
        if _safe_send(cid, text, reply_markup, parse_mode):
            n += 1
    return n


def notify_super_admins_photo(file_id: str, caption: str = "",
                              reply_markup: Optional[dict] = None) -> int:
    n = 0
    for cid in _super_admin_chat_ids():
        if _safe_send_photo(cid, file_id, caption, reply_markup):
            n += 1
    return n


# ------------------------------------------------------------
# Convenience: build a money string
# ------------------------------------------------------------
def fmt_money(n: int) -> str:
    return "{:,} ریال".format(int(n))
