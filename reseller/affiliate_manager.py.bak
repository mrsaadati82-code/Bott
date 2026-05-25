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
from typing import Optional, List

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
