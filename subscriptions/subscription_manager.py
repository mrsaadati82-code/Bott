# ============================================================
# subscriptions/subscription_manager.py
# ============================================================
# Lifecycle of `subscriptions` rows:
#   - activate / extend
#   - check status (active/expired)
#   - enforce limits (max_bots, max_monthly_messages, ...)
#   - usage counters
#
# A subscription can be:
#   * account-wide (bot_id IS NULL) -> applies to all of user's bots
#   * per-bot      (bot_id NOT NULL) -> applies only to that bot
# ============================================================

import json
from datetime import datetime, timedelta
from typing import Optional, Dict

from database.db import db
from subscriptions.plan_manager import get_plan
from monitoring.logs import get_logger

log = get_logger(__name__)


STATUS_ACTIVE    = "active"
STATUS_EXPIRED   = "expired"
STATUS_CANCELLED = "cancelled"


# ============================================================
# Feature Tier System — Free vs VIP
# ============================================================
FEATURE_LIMITS = {
    "free": {
        "max_pages": 3,
        "max_buttons_per_page": 5,
        "max_conversations": 1,
        "button_types": ["open_page", "send_message", "url"],
        "welcome_message": True,
        "auto_reply": False,
        "analytics": False,
        "broadcast": False,
        "user_management": False,
        "send_photo": False,
        "forward_admin": False,
        "custom_conversation": False,
        "form_templates": False,
    },
    "vip": {
        "max_pages": -1,           # unlimited
        "max_buttons_per_page": -1,
        "max_conversations": -1,
        "button_types": "all",
        "welcome_message": True,
        "auto_reply": True,
        "analytics": True,
        "broadcast": True,
        "user_management": True,
        "send_photo": True,
        "forward_admin": True,
        "custom_conversation": True,
        "form_templates": True,
    },
}


def get_feature_tier(user_id: int) -> str:
    """Return 'vip' if user has a paid plan, 'free' otherwise."""
    plan = get_effective_plan(user_id, None)
    if not plan:
        return "free"
    # Any plan with price > 0 is VIP
    if int(plan.get("price", 0)) > 0:
        return "vip"
    return "free"


def check_bot_feature(user_id: int, feature_key: str) -> dict:
    """
    Check if a user can access a specific bot-building feature.
    Returns {"ok": bool, "tier": str, "reason": str}
    """
    tier = get_feature_tier(user_id)
    limits = FEATURE_LIMITS.get(tier, FEATURE_LIMITS["free"])

    if feature_key not in limits:
        return {"ok": False, "tier": tier, "reason": "unknown_feature"}

    val = limits[feature_key]
    if val == "all":
        return {"ok": True, "tier": tier, "reason": ""}
    if val is True:
        return {"ok": True, "tier": tier, "reason": ""}
    if val is False:
        return {"ok": False, "tier": tier, "reason": "vip_required"}
    # Numeric limits checked elsewhere
    return {"ok": True, "tier": tier, "reason": ""}


def check_bot_limit(user_id: int, limit_key: str, current_count: int) -> dict:
    """Check numeric limits (max_pages, max_conversations, etc.)."""
    tier = get_feature_tier(user_id)
    limits = FEATURE_LIMITS.get(tier, FEATURE_LIMITS["free"])
    max_val = limits.get(limit_key, 0)
    if max_val == -1:  # unlimited
        return {"ok": True, "tier": tier, "max": -1}
    if current_count < max_val:
        return {"ok": True, "tier": tier, "max": max_val}
    return {"ok": False, "tier": tier, "max": max_val,
            "reason": "limit_reached"}


def get_allowed_button_types(user_id: int) -> list:
    """Get list of button types this user can use."""
    tier = get_feature_tier(user_id)
    limits = FEATURE_LIMITS.get(tier, FEATURE_LIMITS["free"])
    bt = limits.get("button_types", [])
    if bt == "all":
        from page_builder.button_manager import ACTIONS
        return list(ACTIONS)
    return bt


def is_vip(user_id: int) -> bool:
    return get_feature_tier(user_id) == "vip"


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def _now() -> datetime:
    return datetime.utcnow()


def _to_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _parse(dt_str: str) -> datetime:
    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")


# ------------------------------------------------------------
# Activation
# ------------------------------------------------------------
def activate(user_id: int, plan_id: int, bot_id: Optional[int] = None,
             extend_if_active: bool = True) -> dict:
    """
    Activate a plan for a user (optionally tied to a specific bot).
    If user already has an active subscription on the same scope
    and extend_if_active=True, we extend ends_at instead of inserting
    a new row.
    """
    plan = get_plan(plan_id)
    if not plan:
        raise ValueError("Plan {} not found".format(plan_id))

    existing = get_active(user_id, bot_id)
    if existing and extend_if_active:
        # extend
        old_end = _parse(existing["ends_at"])
        base = old_end if old_end > _now() else _now()
        new_end = base + timedelta(days=int(plan["duration_days"]))
        db.execute(
            "UPDATE subscriptions SET ends_at=?, plan_id=?, status=? WHERE id=?",
            (_to_str(new_end), int(plan_id), STATUS_ACTIVE, int(existing["id"])),
        )
        return get_by_id(existing["id"])

    starts = _now()
    ends   = starts + timedelta(days=int(plan["duration_days"]))
    new_id = db.insert(
        """INSERT INTO subscriptions
              (user_id, bot_id, plan_id, starts_at, ends_at, status, usage_json)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            int(user_id),
            int(bot_id) if bot_id else None,
            int(plan_id),
            _to_str(starts),
            _to_str(ends),
            STATUS_ACTIVE,
            "{}",
        ),
    )
    return get_by_id(new_id)


def cancel(subscription_id: int):
    db.execute("UPDATE subscriptions SET status=? WHERE id=?",
               (STATUS_CANCELLED, int(subscription_id)))


# ------------------------------------------------------------
# Queries
# ------------------------------------------------------------
def get_by_id(sub_id: int) -> Optional[dict]:
    return db.fetchone("SELECT * FROM subscriptions WHERE id=?", (int(sub_id),))


def get_active(user_id: int, bot_id: Optional[int] = None) -> Optional[dict]:
    """Latest active subscription on the given scope."""
    if bot_id is None:
        row = db.fetchone(
            """SELECT * FROM subscriptions
                 WHERE user_id=? AND bot_id IS NULL AND status=?
                 ORDER BY ends_at DESC LIMIT 1""",
            (int(user_id), STATUS_ACTIVE),
        )
    else:
        row = db.fetchone(
            """SELECT * FROM subscriptions
                 WHERE user_id=? AND bot_id=? AND status=?
                 ORDER BY ends_at DESC LIMIT 1""",
            (int(user_id), int(bot_id), STATUS_ACTIVE),
        )
    if not row:
        return None
    # Auto-expire if past ends_at
    if _parse(row["ends_at"]) < _now():
        db.execute("UPDATE subscriptions SET status=? WHERE id=?",
                   (STATUS_EXPIRED, int(row["id"])))
        return None
    return row


def get_effective_plan(user_id: int, bot_id: Optional[int] = None) -> Optional[dict]:
    """Return the plan currently in force for (user_id, bot_id)."""
    sub = get_active(user_id, bot_id) or get_active(user_id, None)
    if not sub:
        return None
    return get_plan(sub["plan_id"])


def list_user_subscriptions(user_id: int) -> list:
    return db.fetchall(
        "SELECT * FROM subscriptions WHERE user_id=? ORDER BY id DESC",
        (int(user_id),),
    )


# ------------------------------------------------------------
# Usage counters & limit enforcement
# ------------------------------------------------------------
def _get_usage(sub: dict) -> dict:
    try:
        return json.loads(sub.get("usage_json") or "{}")
    except Exception:
        return {}


def _save_usage(sub_id: int, usage: dict):
    db.execute("UPDATE subscriptions SET usage_json=? WHERE id=?",
               (json.dumps(usage), int(sub_id)))


def incr_usage(user_id: int, key: str, amount: int = 1,
               bot_id: Optional[int] = None):
    """Increment a counter (e.g. 'monthly_messages') on the active sub."""
    sub = get_active(user_id, bot_id) or get_active(user_id, None)
    if not sub:
        return
    usage = _get_usage(sub)
    usage[key] = int(usage.get(key, 0)) + int(amount)
    _save_usage(sub["id"], usage)


def get_usage(user_id: int, key: str, bot_id: Optional[int] = None) -> int:
    sub = get_active(user_id, bot_id) or get_active(user_id, None)
    if not sub:
        return 0
    return int(_get_usage(sub).get(key, 0))


# ------------------------------------------------------------
# Limit checks (returns dict: ok, reason, suggest)
# ------------------------------------------------------------
def check_can_create_bot(user_id: int) -> Dict:
    plan = get_effective_plan(user_id, None)
    if not plan:
        return {"ok": False, "reason": "no_subscription",
                "message": "اشتراکی فعال نیست. ابتدا یک پلن خریداری کنید."}
    current = db.fetchone(
        "SELECT COUNT(*) AS c FROM bots WHERE owner_id=? AND status!='banned'",
        (int(user_id),),
    )["c"]
    if current >= int(plan["max_bots"]):
        return {
            "ok": False, "reason": "max_bots",
            "message": "به سقف تعداد ربات‌های پلن «{}» رسیدید ({}).\n"
                       "برای ساخت ربات بیشتر، پلن خود را ارتقا دهید."
                       .format(plan["name"], plan["max_bots"]),
        }
    return {"ok": True}


def check_message_quota(user_id: int, bot_id: Optional[int] = None) -> Dict:
    plan = get_effective_plan(user_id, bot_id)
    if not plan:
        return {"ok": False, "reason": "no_subscription",
                "message": "اشتراکی فعال نیست."}
    used = get_usage(user_id, "monthly_messages", bot_id)
    if used >= int(plan["max_monthly_messages"]):
        return {
            "ok": False, "reason": "max_messages",
            "message": "سقف پیام ماهانه پلن «{}» پر شد ({}).\n"
                       "برای ارسال بیشتر، پلن خود را ارتقا دهید."
                       .format(plan["name"], plan["max_monthly_messages"]),
        }
    return {"ok": True}


# ------------------------------------------------------------
# Maintenance
# ------------------------------------------------------------
def expire_overdue():
    """Background task: flip active->expired for past-due subs."""
    n = db.execute(
        "UPDATE subscriptions SET status=? WHERE status=? AND ends_at < ?",
        (STATUS_EXPIRED, STATUS_ACTIVE, _to_str(_now())),
    ).rowcount
    if n:
        log.info("Expired %s subscriptions.", n)
    return n
