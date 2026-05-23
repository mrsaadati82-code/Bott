# ============================================================
# payments/payment_manager.py
# ============================================================

import json
from typing import Optional, List, Dict, Any

from database.db import db
from monitoring.logs import get_logger

log = get_logger(__name__)


STATUS_PENDING  = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_FAILED   = "failed"


# ------------------------------------------------------------
# Methods registry
# ------------------------------------------------------------
def list_enabled_methods() -> List[dict]:
    return db.fetchall(
        "SELECT * FROM payment_methods WHERE is_enabled=1 ORDER BY id ASC"
    )


def is_method_enabled(key: str) -> bool:
    row = db.fetchone("SELECT is_enabled FROM payment_methods WHERE key=?", (key,))
    return bool(row and int(row["is_enabled"]))


def get_method(key: str) -> Optional[dict]:
    return db.fetchone("SELECT * FROM payment_methods WHERE key=?", (key,))


# ------------------------------------------------------------
# Create payment
# ------------------------------------------------------------
def create_payment(
    user_id: int,
    amount: int,
    method_key: str,
    ref_type: Optional[str] = None,
    ref_id: Optional[int] = None,
    meta: Optional[Dict[str, Any]] = None,
    status: str = STATUS_PENDING,
) -> dict:
    if not is_method_enabled(method_key):
        raise ValueError("Payment method '{}' is disabled".format(method_key))
    if int(amount) <= 0:
        raise ValueError("amount must be positive")

    new_id = db.insert(
        """INSERT INTO payments
              (user_id, method_key, amount, currency,
               status, ref_type, ref_id, gateway_ref, meta_json)
           VALUES (?, ?, ?, 'IRR', ?, ?, ?, NULL, ?)""",
        (
            int(user_id), method_key, int(amount), status,
            ref_type, int(ref_id) if ref_id else None,
            json.dumps(meta or {}),
        ),
    )
    log.info("Payment created id=%s user=%s method=%s amount=%s ref=%s/%s",
             new_id, user_id, method_key, amount, ref_type, ref_id)
    return get_payment(new_id)


# ------------------------------------------------------------
# Queries
# ------------------------------------------------------------
def get_payment(payment_id: int) -> Optional[dict]:
    return db.fetchone("SELECT * FROM payments WHERE id=?", (int(payment_id),))


def list_pending(limit: int = 50) -> List[dict]:
    return db.fetchall(
        "SELECT * FROM payments WHERE status=? ORDER BY id DESC LIMIT ?",
        (STATUS_PENDING, int(limit)),
    )


def list_user_payments(user_id: int, limit: int = 20) -> List[dict]:
    return db.fetchall(
        "SELECT * FROM payments WHERE user_id=? ORDER BY id DESC LIMIT ?",
        (int(user_id), int(limit)),
    )


# ------------------------------------------------------------
# Approve / reject
# ------------------------------------------------------------
def approve(payment_id: int, gateway_ref: Optional[str] = None) -> dict:
    p = get_payment(payment_id)
    if not p:
        raise ValueError("payment not found")
    if p["status"] == STATUS_APPROVED:
        return p
    db.execute(
        """UPDATE payments
              SET status=?, gateway_ref=COALESCE(?, gateway_ref),
                  updated_at=datetime('now')
            WHERE id=?""",
        (STATUS_APPROVED, gateway_ref, int(payment_id)),
    )
    fulfill(payment_id)
    # Notify user that their payment was approved
    _notify_user_payment_approved(payment_id)
    return get_payment(payment_id)


def reject(payment_id: int, reason: str = "") -> dict:
    p = get_payment(payment_id)
    if not p:
        raise ValueError("payment not found")
    try:
        meta = json.loads(p.get("meta_json") or "{}")
    except Exception:
        meta = {}
    meta["reject_reason"] = reason
    db.execute(
        "UPDATE payments SET status=?, meta_json=?, updated_at=datetime('now') WHERE id=?",
        (STATUS_REJECTED, json.dumps(meta), int(payment_id)),
    )
    _notify_user_payment_rejected(payment_id, reason)
    return get_payment(payment_id)


# ------------------------------------------------------------
# Fulfill
# ------------------------------------------------------------
def fulfill(payment_id: int):
    p = get_payment(payment_id)
    if not p or p["status"] != STATUS_APPROVED:
        return
    try:
        meta = json.loads(p.get("meta_json") or "{}")
    except Exception:
        meta = {}
    if meta.get("fulfilled"):
        return

    ref_type = p["ref_type"]
    user_id  = p["user_id"]
    amount   = int(p["amount"])

    if ref_type == "wallet_topup":
        from wallet.wallet_manager import credit
        credit(user_id, amount,
               tx_type="topup",
               description="شارژ کیف پول از پرداخت #{}".format(p["id"]),
               ref_type="payment", ref_id=int(p["id"]),
               notify=True)

    elif ref_type == "subscription":
        from subscriptions.subscription_manager import activate as activate_sub
        plan_id = int(p["ref_id"]) if p["ref_id"] else int(meta.get("plan_id", 0))
        bot_id  = meta.get("bot_id")
        if plan_id:
            sub = activate_sub(user_id, plan_id, bot_id=bot_id)
            meta["subscription_id"] = sub["id"]

    elif ref_type == "order":
        pass

    meta["fulfilled"] = True
    db.execute("UPDATE payments SET meta_json=? WHERE id=?",
               (json.dumps(meta), int(p["id"])))
    log.info("Payment %s fulfilled (ref_type=%s)", p["id"], ref_type)


# ------------------------------------------------------------
# High-level starters (used by user-facing handlers)
# ------------------------------------------------------------
def start_wallet_topup(user_id: int, amount: int, method_key: str,
                       meta: Optional[Dict[str, Any]] = None) -> dict:
    p = create_payment(user_id, amount, method_key,
                       ref_type="wallet_topup", meta=meta)
    _notify_admins_new_payment(p["id"])
    return p


def start_subscription_purchase(user_id: int, plan_id: int, amount: int,
                                method_key: str, bot_id: Optional[int] = None,
                                meta: Optional[Dict[str, Any]] = None) -> dict:
    """Subscription purchase. Method `wallet` is processed instantly."""
    meta = dict(meta or {})
    if bot_id is not None:
        meta["bot_id"] = int(bot_id)
    meta["plan_id"] = int(plan_id)

    # Instant path for wallet
    if method_key == "wallet":
        from payments.wallet_gateway import has_enough, charge
        if not has_enough(user_id, amount):
            raise ValueError("insufficient_funds")
        p = create_payment(user_id, amount, method_key,
                           ref_type="subscription", ref_id=plan_id,
                           meta=meta, status=STATUS_PENDING)
        ok, msg = charge(user_id, amount,
                         description="خرید اشتراک #{}".format(p["id"]),
                         ref_type="payment", ref_id=p["id"])
        if ok:
            approve(p["id"], gateway_ref="WALLET")
        else:
            reject(p["id"], reason=msg)
        return get_payment(p["id"])

    # Other methods: create pending and notify admins
    p = create_payment(user_id, amount, method_key,
                       ref_type="subscription", ref_id=plan_id, meta=meta)
    _notify_admins_new_payment(p["id"])
    return p


# ============================================================
# Notification helpers
# ============================================================
def _notify_admins_new_payment(payment_id: int):
    from core.notifications import notify_super_admins, fmt_money
    from core.keyboards import inline
    p = get_payment(payment_id)
    if not p:
        return
    u = db.fetchone("SELECT * FROM users WHERE id=?", (p["user_id"],))
    method_row = get_method(p["method_key"])
    method_name = method_row["name"] if method_row else p["method_key"]

    ref_label = ""
    if p["ref_type"] == "subscription" and p["ref_id"]:
        plan = db.fetchone("SELECT name FROM plans WHERE id=?", (p["ref_id"],))
        if plan:
            ref_label = "\n🎟 پلن: {}".format(plan["name"])
    elif p["ref_type"] == "wallet_topup":
        ref_label = "\n💼 شارژ کیف پول"

    text = (
        "🔔 <b>پرداخت جدید</b>\n\n"
        "🆔 شناسه: #{id}\n"
        "👤 کاربر: {nm} (id={bid})\n"
        "💰 مبلغ: {amt}\n"
        "🔧 روش: {m}{rl}\n\n"
        "وضعیت: <b>در انتظار تایید</b>"
    ).format(
        id=p["id"],
        nm=(u.get("first_name") or "-") if u else "-",
        bid=(u.get("bale_user_id") or "-") if u else "-",
        amt=fmt_money(p["amount"]),
        m=method_name, rl=ref_label,
    )
    kb = inline([
        [("✅ تایید", "pay:ok:{}".format(p["id"])),
         ("❌ رد",    "pay:no:{}".format(p["id"]))],
        [("🔍 جزییات کامل", "pay:view:{}".format(p["id"]))],
    ])
    notify_super_admins(text, reply_markup=kb, parse_mode="HTML")


def _notify_user_payment_approved(payment_id: int):
    from core.notifications import notify_user, fmt_money
    from core.keyboards import inline
    p = get_payment(payment_id)
    if not p:
        return
    ref_text = ""
    kb = None
    if p["ref_type"] == "wallet_topup":
        ref_text = "\nکیف پول شما به مبلغ {} شارژ شد. 💰".format(fmt_money(p["amount"]))
    elif p["ref_type"] == "subscription":
        ref_text = "\nاشتراک شما فعال شد. 🎟"
        # Show inline button to start bot creation wizard
        try:
            meta = json.loads(p.get("meta_json") or "{}")
            tpl_key = meta.get("tpl_key")
            if tpl_key:
                kb = inline([
                    [("🤖 ساخت ربات", "paybuild:{}".format(p["id"]))],
                ])
        except Exception:
            pass
    notify_user(
        p["user_id"],
        "✅ پرداخت #{} با موفقیت تایید شد.{}\n\nبا تشکر 🙏".format(p["id"], ref_text),
        reply_markup=kb,
    )


def _notify_user_payment_rejected(payment_id: int, reason: str = ""):
    from core.notifications import notify_user
    p = get_payment(payment_id)
    if not p:
        return
    extra = "\nدلیل: {}".format(reason) if reason else ""
    notify_user(
        p["user_id"],
        "❌ پرداخت #{} رد شد.{}\n\n"
        "اگر سوالی داشتید با پشتیبانی تماس بگیرید.".format(p["id"], extra),
    )


# ------------------------------------------------------------
# Called by users after they submit a card-to-card receipt
# ------------------------------------------------------------
def notify_receipt_submitted(payment_id: int):
    """Re-ping super-admins that a card-to-card receipt is ready."""
    from core.notifications import notify_super_admins, notify_super_admins_photo, fmt_money
    from core.keyboards import inline
    from payments.card_to_card import get_receipt
    p = get_payment(payment_id)
    if not p:
        return
    u = db.fetchone("SELECT * FROM users WHERE id=?", (p["user_id"],))
    receipt = get_receipt(payment_id)

    caption = (
        "🧾 <b>رسید کارت‌به‌کارت</b>\n\n"
        "💳 پرداخت #{id}\n"
        "👤 {nm} (id={bid})\n"
        "💰 مبلغ: {amt}\n"
        "🔢 شماره پیگیری: {tr}"
    ).format(
        id=p["id"],
        nm=(u.get("first_name") or "-") if u else "-",
        bid=(u.get("bale_user_id") or "-") if u else "-",
        amt=fmt_money(p["amount"]),
        tr=receipt.get("tracking_code") or "-",
    )
    kb = inline([
        [("✅ تایید", "pay:ok:{}".format(p["id"])),
         ("❌ رد",    "pay:no:{}".format(p["id"]))],
    ])

    photo_id = receipt.get("photo_file_id")
    if photo_id:
        notify_super_admins_photo(photo_id, caption=caption, reply_markup=kb)
    else:
        notify_super_admins(caption, reply_markup=kb, parse_mode="HTML")
