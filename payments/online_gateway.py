# ============================================================
# payments/online_gateway.py
# ============================================================
# Provider-agnostic skeleton for an online payment gateway
# (e.g. ZarinPal, IDPay, NextPay).
#
# We don't bind to any specific provider here; instead each
# super-admin can configure their own via payment_methods
# table (key='online', config_json={"provider": "...", ...}).
#
# Two phases:
#   request(amount, callback_url) -> {redirect_url, gateway_ref}
#   verify(gateway_ref, params)   -> {ok, ref_id}
#
# In phase 2 we ship a STUB that always succeeds when
# config.provider == 'stub'. Real providers are plugged in
# later via subclasses without touching core.
# ============================================================

import json
from typing import Dict, Any

from database.db import db
from monitoring.logs import get_logger

log = get_logger(__name__)


METHOD_KEY = "online"


# ------------------------------------------------------------
# Config loader
# ------------------------------------------------------------
def get_config() -> Dict[str, Any]:
    row = db.fetchone("SELECT config_json FROM payment_methods WHERE key=?", (METHOD_KEY,))
    if not row:
        return {}
    try:
        return json.loads(row["config_json"] or "{}")
    except Exception:
        return {}


def save_config(cfg: Dict[str, Any]):
    db.execute("UPDATE payment_methods SET config_json=? WHERE key=?",
               (json.dumps(cfg or {}), METHOD_KEY))


# ------------------------------------------------------------
# Provider dispatch
# ------------------------------------------------------------
class _StubProvider:
    """Always-approve provider for development."""
    name = "stub"

    def request(self, amount: int, callback_url: str, description: str = "") -> Dict[str, Any]:
        return {
            "ok": True,
            "redirect_url": "https://example.com/pay?stub=1&amount={}".format(amount),
            "gateway_ref": "STUB-{}".format(amount),
        }

    def verify(self, gateway_ref: str, params: dict) -> Dict[str, Any]:
        return {"ok": True, "ref_id": gateway_ref}


_PROVIDERS = {
    "stub": _StubProvider(),
    # 'zarinpal': ZarinPalProvider(),     # add later
    # 'idpay':    IdPayProvider(),
}


def _provider():
    cfg = get_config()
    name = (cfg.get("provider") or "stub").lower()
    p = _PROVIDERS.get(name)
    if not p:
        log.warning("Unknown online provider '%s', falling back to stub.", name)
        return _PROVIDERS["stub"]
    return p


def request_payment(amount: int, callback_url: str = "", description: str = "") -> Dict[str, Any]:
    return _provider().request(int(amount), callback_url, description)


def verify_payment(gateway_ref: str, params: dict = None) -> Dict[str, Any]:
    return _provider().verify(gateway_ref, params or {})
