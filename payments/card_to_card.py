# ============================================================
# payments/card_to_card.py
# ============================================================

import json
from typing import Optional, Dict, Any

from database.db import db
from monitoring.logs import get_logger

log = get_logger(__name__)


METHOD_KEY = "card_to_card"


# ------------------------------------------------------------
# Config: card number, holder, bank (live in system_settings)
# ------------------------------------------------------------
def _get_setting(key: str, default: str = "") -> str:
    row = db.fetchone("SELECT value FROM system_settings WHERE key=?", (key,))
    return row["value"] if row and row["value"] else default


def get_config() -> Dict[str, Any]:
    row = db.fetchone("SELECT config_json FROM payment_methods WHERE key=?", (METHOD_KEY,))
    if not row:
        cfg = {}
    else:
        try:
            cfg = json.loads(row["config_json"] or "{}")
        except Exception:
            cfg = {}
    # Pull from system_settings as fallback
    cfg.setdefault("card_number", _get_setting("card_number", "0000-0000-0000-0000"))
    cfg.setdefault("holder",      _get_setting("card_holder", "-"))
    cfg.setdefault("bank",        _get_setting("card_bank", "-"))
    return cfg


def save_config(cfg: Dict[str, Any]):
    db.execute("UPDATE payment_methods SET config_json=? WHERE key=?",
               (json.dumps(cfg or {}), METHOD_KEY))


def get_card_text() -> str:
    cfg = get_config()
    return (
        "💳 <b>اطلاعات کارت برای واریز:</b>\n\n"
        "🔢 شماره کارت: <code>{c}</code>\n"
        "👤 صاحب کارت: {h}\n"
        "🏦 بانک: {b}\n\n"
        "👈 پس از واریز، عکس رسید را همینجا ارسال کنید."
    ).format(c=cfg["card_number"], h=cfg["holder"], b=cfg["bank"])


# ------------------------------------------------------------
# Submit receipt (photo or tracking code)
# ------------------------------------------------------------
def attach_receipt_photo(payment_id: int, photo_file_id: str,
                         tracking_code: Optional[str] = None,
                         note: Optional[str] = None):
    p = db.fetchone("SELECT * FROM payments WHERE id=?", (int(payment_id),))
    if not p:
        raise ValueError("payment not found")
    try:
        meta = json.loads(p.get("meta_json") or "{}")
    except Exception:
        meta = {}
    meta["receipt"] = {
        "tracking_code": (tracking_code or "").strip(),
        "note": note or "",
        "photo_file_id": photo_file_id,
    }
    db.execute(
        """UPDATE payments
              SET meta_json=?, gateway_ref=?, updated_at=datetime('now')
            WHERE id=?""",
        (json.dumps(meta), tracking_code or photo_file_id[:32], int(payment_id)),
    )


def attach_receipt_text(payment_id: int, tracking_code: str,
                        note: Optional[str] = None):
    p = db.fetchone("SELECT * FROM payments WHERE id=?", (int(payment_id),))
    if not p:
        raise ValueError("payment not found")
    try:
        meta = json.loads(p.get("meta_json") or "{}")
    except Exception:
        meta = {}
    receipt = meta.get("receipt") or {}
    receipt["tracking_code"] = str(tracking_code).strip()
    if note:
        receipt["note"] = note
    meta["receipt"] = receipt
    db.execute(
        """UPDATE payments
              SET meta_json=?, gateway_ref=?, updated_at=datetime('now')
            WHERE id=?""",
        (json.dumps(meta), str(tracking_code).strip(), int(payment_id)),
    )


def get_receipt(payment_id: int) -> Dict[str, Any]:
    p = db.fetchone("SELECT meta_json FROM payments WHERE id=?", (int(payment_id),))
    if not p:
        return {}
    try:
        meta = json.loads(p.get("meta_json") or "{}")
    except Exception:
        return {}
    return meta.get("receipt") or {}


# Back-compat alias
def submit_receipt(payment_id: int, tracking_code: str,
                   note: Optional[str] = None, photo_file_id: Optional[str] = None):
    if photo_file_id:
        attach_receipt_photo(payment_id, photo_file_id, tracking_code, note)
    else:
        attach_receipt_text(payment_id, tracking_code, note)
