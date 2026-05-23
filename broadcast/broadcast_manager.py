# ============================================================
# broadcast/broadcast_manager.py
# ============================================================
# Background broadcaster: reads `broadcasts` table rows whose
# status='queued' and sends to all targeted users with a
# small rate-limit to respect Bale's flood control.
#
# Targets:
#   'all'         -> every user in users table
#   'active'      -> every user with messages in last 30 days
#                    (placeholder: same as 'all' until analytics tracks it)
#   'bot_users'   -> users that have interacted with `bot_id`
#                    (placeholder: same as 'all' until per-bot users table exists)
# ============================================================

import json
import threading
import time
from typing import List

from database.db import db
from core.bot_manager import bot_manager, MOTHER_BOT_ID
from monitoring.logs import get_logger

log = get_logger(__name__)


# Rate limiting
SEND_INTERVAL_SEC = 0.05    # 20 msg/sec ceiling
RETRY_SLEEP_SEC   = 1.0


# ============================================================
# Target resolution
# ============================================================
def _resolve_targets(b: dict) -> List[int]:
    target = b.get("target") or "all"
    rows = db.fetchall("SELECT bale_user_id FROM users WHERE is_blocked=0")
    return [int(r["bale_user_id"]) for r in rows]


# ============================================================
# Sender
# ============================================================
def _send_one(api, chat_id: int, content: dict) -> bool:
    try:
        if content.get("type") == "text":
            api.send_message(chat_id, content.get("text") or "")
        elif content.get("type") == "photo" and content.get("file_id"):
            api.call("sendPhoto", {
                "chat_id": chat_id,
                "photo": content["file_id"],
                "caption": content.get("caption") or "",
            })
        else:
            return False
        return True
    except Exception as e:
        log.debug("broadcast send failed to %s: %s", chat_id, e)
        return False


def _run_broadcast(b: dict):
    try:
        content = json.loads(b.get("content_json") or "{}")
    except Exception:
        content = {}

    bot_id = b.get("bot_id") or MOTHER_BOT_ID
    api = bot_manager.get_api(bot_id) or bot_manager.get_mother_api()
    if not api:
        log.warning("broadcast %s: no API available", b["id"])
        db.execute("UPDATE broadcasts SET status=? WHERE id=?", ("failed", b["id"]))
        return

    targets = _resolve_targets(b)
    db.execute(
        "UPDATE broadcasts SET status=?, total_targets=? WHERE id=?",
        ("running", len(targets), b["id"]),
    )

    sent, failed = 0, 0
    for chat_id in targets:
        if _send_one(api, chat_id, content):
            sent += 1
        else:
            failed += 1
        if (sent + failed) % 20 == 0:
            db.execute(
                "UPDATE broadcasts SET sent_count=?, failed_count=? WHERE id=?",
                (sent, failed, b["id"]),
            )
        time.sleep(SEND_INTERVAL_SEC)

    db.execute(
        """UPDATE broadcasts
              SET status=?, sent_count=?, failed_count=?, finished_at=datetime('now')
            WHERE id=?""",
        ("finished", sent, failed, b["id"]),
    )
    log.info("broadcast %s done: sent=%s failed=%s", b["id"], sent, failed)


# ============================================================
# Worker loop (one daemon thread)
# ============================================================
_worker_thread = None
_running = False


def _worker_loop():
    global _running
    log.info("Broadcast worker started.")
    while _running:
        try:
            row = db.fetchone(
                "SELECT * FROM broadcasts WHERE status='queued' ORDER BY id ASC LIMIT 1"
            )
            if row:
                _run_broadcast(row)
            else:
                time.sleep(2)
        except Exception as e:
            log.exception("Broadcast worker error: %s", e)
            time.sleep(RETRY_SLEEP_SEC)
    log.info("Broadcast worker stopped.")


def start_worker():
    global _worker_thread, _running
    if _running:
        return
    _running = True
    _worker_thread = threading.Thread(target=_worker_loop, name="broadcast-worker", daemon=True)
    _worker_thread.start()


def stop_worker():
    global _running
    _running = False


# ============================================================
# Public helper (used by admin /broadcast handler)
# ============================================================
def enqueue_text(sender_user_id: int, text: str, target: str = "all",
                 bot_id: int = None) -> int:
    return db.insert(
        """INSERT INTO broadcasts
              (sender_user_id, bot_id, target, content_json, status)
           VALUES (?, ?, ?, ?, ?)""",
        (
            int(sender_user_id),
            int(bot_id) if bot_id else None,
            target,
            json.dumps({"type": "text", "text": text}, ensure_ascii=False),
            "queued",
        ),
    )
