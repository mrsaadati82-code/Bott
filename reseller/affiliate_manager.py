# ============================================================
# reseller/affiliate_manager.py
# ============================================================
# Affiliate / referral tracking + reseller commission.
#
# Concepts:
#   - referrer_id (users.referrer_id) -> who invited this user
#   - commission_percent (system setting) -> reseller share
#   - on every approved payment whose user has a referrer that
#     is also a 'reseller', we credit the reseller's wallet.
# ============================================================

import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from database.db import db
from wallet.wallet_manager import credit
from core.permission_manager import get_role, ROLE_RESELLER
from monitoring.logs import get_logger

log = get_logger(__name__)


SETTING_KEY = "reseller_commission_percent"
DEFAULT_PERCENT = 10  # 10%


# ------------------------------------------------------------
# Referral link / code
# ------------------------------------------------------------
def make_ref_code(user_id: int) -> str:
    """Stable, opaque-ish ref code for a user."""
    return "R{}".format(int(user_id))


def parse_ref_code(payload: str) -> Optional[int]:
    """Extract referrer user_id from '/start RXXX' style payload."""
    if not payload:
        return None
    p = payload.strip().upper()
    if p.startswith("R") and p[1:].isdigit():
        return int(p[1:])
    return None


def set_referrer(user_id: int, referrer_user_id: int):
    if int(user_id) == int(referrer_user_id):
        return  # cannot refer self
    row = db.fetchone("SELECT referrer_id FROM users WHERE id=?", (int(user_id),))
    if not row:
        return
    if row["referrer_id"]:
        return  # already set, immutable
    db.execute("UPDATE users SET referrer_id=? WHERE id=?",
               (int(referrer_user_id), int(user_id)))
    log.info("Set referrer: user=%s referrer=%s", user_id, referrer_user_id)


def list_referrals(user_id: int, limit: int = 100) -> List[dict]:
    return db.fetchall(
        "SELECT id, bale_user_id, first_name, created_at FROM users "
        "WHERE referrer_id=? ORDER BY id DESC LIMIT ?",
        (int(user_id), int(limit)),
    )


def count_referrals(user_id: int) -> int:
    r = db.fetchone("SELECT COUNT(*) AS c FROM users WHERE referrer_id=?", (int(user_id),))
    return int(r["c"]) if r else 0


# ------------------------------------------------------------
# Reseller stats & analytics
# ------------------------------------------------------------
def get_reseller_stats(user_id: int) -> Dict[str, Any]:
    """
    Return comprehensive stats for a reseller (users.id).
    """
    result = {
        "total_referrals": 0,
        "today_refs": 0,
        "week_refs": 0,
        "month_refs": 0,
        "total_commission": 0,
        "direct_sales": 0,
        "pending_commission": 0,
    }

    result["total_referrals"] = count_referrals(user_id)

    # Today
    today = datetime.utcnow().strftime("%Y-%m-%d")
    r = db.fetchone(
        "SELECT COUNT(*) AS c FROM users WHERE referrer_id=? AND DATE(created_at)=?",
        (int(user_id), today),
    )
    result["today_refs"] = int(r["c"]) if r else 0

    # This week
    week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    r = db.fetchone(
        "SELECT COUNT(*) AS c FROM users WHERE referrer_id=? AND created_at>=?",
        (int(user_id), week_ago),
    )
    result["week_refs"] = int(r["c"]) if r else 0

    # This month
    month_ago = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    r = db.fetchone(
        "SELECT COUNT(*) AS c FROM users WHERE referrer_id=? AND created_at>=?",
        (int(user_id), month_ago),
    )
    result["month_refs"] = int(r["c"]) if r else 0

    # Total commission
    w = db.fetchone("SELECT id FROM wallets WHERE user_id=?", (int(user_id),))
    if w:
        r = db.fetchone(
            "SELECT COALESCE(SUM(ABS(amount)), 0) AS s FROM wallet_transactions "
            "WHERE wallet_id=? AND type='commission'",
            (w["id"],),
        )
        result["total_commission"] = int(r["s"]) if r else 0

    # Direct sales (payments from referred users that generated commission)
    r = db.fetchone(
        "SELECT COUNT(*) AS c FROM payments p "
        "JOIN users u ON u.id = p.user_id "
        "WHERE u.referrer_id=? AND p.status='approved'",
        (int(user_id),),
    )
    result["direct_sales"] = int(r["c"]) if r else 0

    return result


def get_commission_summary(user_id: int) -> Dict[str, Any]:
    """
    Get a summary of commissions for a reseller.
    """
    result = {
        "total_commission": 0,
        "paid_commission": 0,
        "pending_commission": 0,
        "commission_count": 0,
    }

    w = db.fetchone("SELECT id FROM wallets WHERE user_id=?", (int(user_id),))
    if w:
        rows = db.fetchall(
            "SELECT * FROM wallet_transactions "
            "WHERE wallet_id=? AND type='commission' ORDER BY id DESC",
            (w["id"],),
        )
        result["commission_count"] = len(rows)
        for t in rows:
            amt = abs(t["amount"])
            result["total_commission"] += amt
            # All commissions are considered "paid" into wallet
            result["paid_commission"] += amt

    # Current wallet balance as "pending" (available for withdrawal)
    from wallet.wallet_manager import get_balance
    result["pending_commission"] = get_balance(user_id)

    return result


# ------------------------------------------------------------
# Commission
# ------------------------------------------------------------
def _get_percent() -> int:
    row = db.fetchone("SELECT value FROM system_settings WHERE key=?", (SETTING_KEY,))
    try:
        return int(row["value"]) if row and row["value"] else DEFAULT_PERCENT
    except Exception:
        return DEFAULT_PERCENT


def set_percent(p: int):
    p = max(0, min(100, int(p)))
    row = db.fetchone("SELECT id FROM system_settings WHERE key=?", (SETTING_KEY,))
    if row:
        db.execute("UPDATE system_settings SET value=?, updated_at=datetime('now') WHERE id=?",
                   (str(p), row["id"]))
    else:
        db.execute("INSERT INTO system_settings (key, value) VALUES (?, ?)",
                   (SETTING_KEY, str(p)))


def pay_commission_for(payment_id: int):
    """
    Called by admin_panel after approving a payment.
    If the paying user has a referrer who is a reseller, credit
    them with commission_percent of the payment amount.
    """
    p = db.fetchone("SELECT * FROM payments WHERE id=?", (int(payment_id),))
    if not p or p["status"] != "approved":
        return
    user = db.fetchone("SELECT * FROM users WHERE id=?", (int(p["user_id"]),))
    if not user or not user.get("referrer_id"):
        return

    referrer = db.fetchone("SELECT * FROM users WHERE id=?", (int(user["referrer_id"]),))
    if not referrer:
        return
    if get_role(int(referrer["bale_user_id"])) != ROLE_RESELLER:
        return

    pct = _get_percent()
    commission = int(int(p["amount"]) * pct / 100)
    if commission <= 0:
        return

    credit(
        int(referrer["id"]),
        commission,
        tx_type="commission",
        description="پورسانت پرداخت #{} ({}%)".format(p["id"], pct),
        ref_type="payment", ref_id=int(p["id"]),
    )
    log.info("Paid commission %s to reseller user=%s for payment=%s",
             commission, referrer["id"], p["id"])


# ------------------------------------------------------------
# Reseller request management
# ------------------------------------------------------------
def save_reseller_request(user_id: int, description: str):
    """Save a reseller request from a user."""
    existing = db.fetchone(
        "SELECT id FROM system_settings WHERE key=?",
        ("reseller_request_{}".format(user_id),),
    )
    if existing:
        db.execute(
            "UPDATE system_settings SET value=?, updated_at=datetime('now') WHERE id=?",
            (description, existing["id"]),
        )
    else:
        db.execute(
            "INSERT INTO system_settings (key, value) VALUES (?, ?)",
            ("reseller_request_{}".format(user_id), description),
        )


def get_pending_reseller_requests() -> List[Dict[str, Any]]:
    """Get all pending reseller requests from system_settings."""
    rows = db.fetchall(
        "SELECT * FROM system_settings WHERE key LIKE 'reseller_request_%' ORDER BY id DESC"
    )
    result = []
    for r in rows:
        try:
            user_id = int(r["key"].replace("reseller_request_", ""))
            u = db.fetchone("SELECT * FROM users WHERE id=?", (user_id,))
            result.append({
                "user_id": user_id,
                "description": r["value"],
                "user": u,
                "created_at": r.get("updated_at", ""),
            })
        except Exception:
            continue
    return result


def clear_reseller_request(user_id: int):
    db.execute(
        "DELETE FROM system_settings WHERE key=?",
        ("reseller_request_{}".format(user_id),),
    )
