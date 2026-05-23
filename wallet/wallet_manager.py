# ============================================================
# wallet/wallet_manager.py
# ============================================================

import secrets
import string
from datetime import datetime
from typing import List, Optional

from database.db import db
from monitoring.logs import get_logger

log = get_logger(__name__)


# ------------------------------------------------------------
# Wallet retrieval / creation
# ------------------------------------------------------------
def get_or_create_wallet(user_id: int) -> dict:
    row = db.fetchone("SELECT * FROM wallets WHERE user_id=?", (int(user_id),))
    if row:
        return row
    db.insert(
        "INSERT INTO wallets (user_id, balance, currency) VALUES (?, 0, 'IRR')",
        (int(user_id),),
    )
    return db.fetchone("SELECT * FROM wallets WHERE user_id=?", (int(user_id),))


def get_balance(user_id: int) -> int:
    return int(get_or_create_wallet(user_id)["balance"])


# ------------------------------------------------------------
# Core mutations
# ------------------------------------------------------------
def _record_tx(wallet_id: int, amount: int, tx_type: str,
               description: str = "", ref_type: Optional[str] = None,
               ref_id: Optional[int] = None) -> int:
    return db.insert(
        """INSERT INTO wallet_transactions
              (wallet_id, amount, type, ref_type, ref_id, description)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (int(wallet_id), int(amount), tx_type, ref_type,
         int(ref_id) if ref_id else None, description),
    )


def credit(user_id: int, amount: int, tx_type: str = "topup",
           description: str = "", ref_type: Optional[str] = None,
           ref_id: Optional[int] = None, notify: bool = True) -> dict:
    if int(amount) <= 0:
        raise ValueError("amount must be positive")
    w = get_or_create_wallet(user_id)
    with db.transaction():
        db.execute("UPDATE wallets SET balance=balance+?, updated_at=datetime('now') WHERE id=?",
                   (int(amount), w["id"]))
        tx_id = _record_tx(w["id"], int(amount), tx_type, description, ref_type, ref_id)
    new_balance = get_balance(user_id)
    log.info("Wallet credit: user=%s amount=%s type=%s", user_id, amount, tx_type)

    if notify:
        _notify_balance_change(user_id, int(amount), new_balance, tx_type, description)

    return {"tx_id": tx_id, "balance": new_balance}


def debit(user_id: int, amount: int, tx_type: str = "purchase",
          description: str = "", ref_type: Optional[str] = None,
          ref_id: Optional[int] = None, allow_negative: bool = False,
          notify: bool = True) -> dict:
    if int(amount) <= 0:
        raise ValueError("amount must be positive")
    w = get_or_create_wallet(user_id)
    if not allow_negative and int(w["balance"]) < int(amount):
        raise ValueError("insufficient_funds")
    with db.transaction():
        db.execute("UPDATE wallets SET balance=balance-?, updated_at=datetime('now') WHERE id=?",
                   (int(amount), w["id"]))
        tx_id = _record_tx(w["id"], -int(amount), tx_type, description, ref_type, ref_id)
    new_balance = get_balance(user_id)
    log.info("Wallet debit: user=%s amount=%s type=%s", user_id, amount, tx_type)

    if notify:
        _notify_balance_change(user_id, -int(amount), new_balance, tx_type, description)

    return {"tx_id": tx_id, "balance": new_balance}


# ------------------------------------------------------------
# Notify on balance change
# ------------------------------------------------------------
def _notify_balance_change(user_id: int, delta: int, new_balance: int,
                           tx_type: str, description: str = ""):
    """Send a DM to user explaining wallet change."""
    try:
        from core.notifications import notify_user, fmt_money
    except Exception:
        return
    if delta > 0:
        icon = "💰"
        title = "کیف پول شما شارژ شد"
        sign = "+"
    else:
        icon = "💸"
        title = "از کیف پول شما کسر شد"
        sign = "-"
    # Friendlier reason labels
    reason_map = {
        "topup":    "شارژ",
        "manual":   "اقدام مدیر",
        "gift":     "کد هدیه",
        "commission": "پورسانت نمایندگی",
        "purchase": "خرید",
        "refund":   "بازگشت وجه",
    }
    reason = reason_map.get(tx_type, tx_type)
    extra = "\n📝 " + description if description else ""
    text = (
        "{i} {t}\n\n"
        "{sign}{amt}\n"
        "💼 موجودی جدید: {nb}\n"
        "🏷 علت: {r}{x}"
    ).format(
        i=icon, t=title, sign=sign, amt=fmt_money(abs(delta)),
        nb=fmt_money(new_balance), r=reason, x=extra,
    )
    notify_user(user_id, text)


# ------------------------------------------------------------
# Transactions list
# ------------------------------------------------------------
def list_transactions(user_id: int, limit: int = 20) -> List[dict]:
    w = get_or_create_wallet(user_id)
    return db.fetchall(
        "SELECT * FROM wallet_transactions WHERE wallet_id=? ORDER BY id DESC LIMIT ?",
        (w["id"], int(limit)),
    )


# ============================================================
# Gift codes
# ============================================================
def _gen_code(length: int = 10) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create_gift_code(amount: int = 0, plan_id: Optional[int] = None,
                     max_uses: int = 1, expires_at: Optional[str] = None,
                     custom_code: Optional[str] = None) -> dict:
    code = custom_code or _gen_code()
    db.insert(
        """INSERT INTO gift_codes
              (code, amount, plan_id, max_uses, used_count, expires_at, is_active)
           VALUES (?, ?, ?, ?, 0, ?, 1)""",
        (code, int(amount), int(plan_id) if plan_id else None,
         int(max_uses), expires_at),
    )
    return db.fetchone("SELECT * FROM gift_codes WHERE code=?", (code,))


def redeem_gift_code(user_id: int, code: str) -> dict:
    code = (code or "").strip().upper()
    if not code:
        return {"ok": False, "message": "کد نامعتبر است."}
    g = db.fetchone("SELECT * FROM gift_codes WHERE code=?", (code,))
    if not g:
        return {"ok": False, "message": "کد هدیه یافت نشد."}
    if not int(g["is_active"]):
        return {"ok": False, "message": "این کد غیرفعال شده است."}
    if int(g["used_count"]) >= int(g["max_uses"]):
        return {"ok": False, "message": "ظرفیت استفاده از این کد پر شده است."}
    if g["expires_at"]:
        try:
            exp = datetime.strptime(g["expires_at"], "%Y-%m-%d %H:%M:%S")
            if exp < datetime.utcnow():
                return {"ok": False, "message": "این کد منقضی شده است."}
        except Exception:
            pass

    result = {"ok": True, "message": "✅ کد با موفقیت اعمال شد"}

    if int(g["amount"]) > 0:
        r = credit(user_id, int(g["amount"]),
                   tx_type="gift",
                   description="کد هدیه " + code,
                   ref_type="gift_code", ref_id=int(g["id"]),
                   notify=False)
        result["balance"] = r["balance"]
        result["message"] += "\n💰 مبلغ {:,} ریال به کیف پول شما اضافه شد.".format(int(g["amount"]))

    if g["plan_id"]:
        from subscriptions.subscription_manager import activate
        sub = activate(user_id, int(g["plan_id"]))
        result["plan_activated"] = True
        result["subscription_id"] = sub["id"]
        result["message"] += "\n🎟 اشتراک شما فعال شد."

    db.execute("UPDATE gift_codes SET used_count=used_count+1 WHERE id=?", (int(g["id"]),))
    return result


def list_gift_codes(active_only: bool = False, limit: int = 50) -> List[dict]:
    sql = "SELECT * FROM gift_codes"
    if active_only:
        sql += " WHERE is_active=1"
    sql += " ORDER BY id DESC LIMIT ?"
    return db.fetchall(sql, (int(limit),))


def deactivate_gift_code(code: str):
    db.execute("UPDATE gift_codes SET is_active=0 WHERE code=?", (code,))
