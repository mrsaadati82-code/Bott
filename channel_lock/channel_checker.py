# ============================================================
# channel_lock/channel_checker.py
# ============================================================
# Force-join: a child bot's owner can attach one or more
# required channels. Before serving any update we check if
# the user is a member; if not we send a "join then verify"
# message.
#
# Bale's getChatMember works like Telegram's:
#   GET /bot<token>/getChatMember?chat_id=<@channel>&user_id=<int>
#   -> {ok: true, result: {status: 'member'|'administrator'|...}}
# ============================================================

from typing import List, Tuple

from database.db import db
from core.bot_manager import bot_manager
from core.keyboards import inline
from monitoring.logs import get_logger

log = get_logger(__name__)


MEMBER_STATUSES = {"member", "administrator", "creator", "owner"}


# ------------------------------------------------------------
# CRUD
# ------------------------------------------------------------
def add_channel(bot_id: int, channel_id: str, title: str = "", required: bool = True) -> int:
    return db.insert(
        """INSERT INTO channel_locks
              (bot_id, channel_id, title, is_required)
           VALUES (?, ?, ?, ?)""",
        (int(bot_id), channel_id.strip(), title or channel_id, 1 if required else 0),
    )


def remove_channel(lock_id: int):
    db.execute("DELETE FROM channel_locks WHERE id=?", (int(lock_id),))


def list_channels(bot_id: int) -> List[dict]:
    return db.fetchall(
        "SELECT * FROM channel_locks WHERE bot_id=? ORDER BY id ASC",
        (int(bot_id),),
    )


# ------------------------------------------------------------
# Check
# ------------------------------------------------------------
def _is_member(api, channel_id: str, user_id: int) -> bool:
    try:
        res = api.call("getChatMember", {"chat_id": channel_id, "user_id": int(user_id)})
        return (res or {}).get("status") in MEMBER_STATUSES
    except Exception as e:
        # If bot isn't admin in the channel, the API errors out -
        # treat as "cannot verify -> not a member" so user is prompted.
        log.debug("getChatMember failed for %s/%s: %s", channel_id, user_id, e)
        return False


def check_user(bot_id: int, user_id: int) -> Tuple[bool, List[dict]]:
    """
    Returns (ok, missing_channels) where ok=True means user is
    member of every required channel.
    """
    locks = [l for l in list_channels(bot_id) if int(l["is_required"])]
    if not locks:
        return True, []
    api = bot_manager.get_api(bot_id)
    if not api:
        return True, []
    missing = []
    for lock in locks:
        if not _is_member(api, lock["channel_id"], user_id):
            missing.append(lock)
    return (len(missing) == 0), missing


def prompt_join(ctx, missing: List[dict]):
    """Send a join-required message with inline join buttons + verify."""
    if not missing:
        return
    rows = []
    for m in missing:
        ch = m["channel_id"]
        title = m.get("title") or ch
        link = "https://ble.ir/{}".format(ch.lstrip("@")) if ch.startswith("@") else ch
        rows.append([(title, {"url": link})])
    rows.append([("✅ بررسی عضویت", "cl:verify")])
    ctx.reply(
        "برای استفاده از این ربات، ابتدا در کانال(های) زیر عضو شوید:",
        reply_markup=inline(rows),
    )
