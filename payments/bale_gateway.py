# ============================================================
# payments/bale_gateway.py - Bale internal wallet gateway
# ============================================================
# Implements the official Bale "sendInvoice" flow.
# Reference: https://docs.bale.ai (search 'sendInvoice')
#
# How it works:
#   1) bot calls sendInvoice() with title/description/payload/prices
#   2) user clicks "pay" inside Bale, money is transferred to the
#      bot owner's Bale wallet immediately
#   3) Bale sends two updates back to the bot:
#        - pre_checkout_query   (we must approve via answerPreCheckoutQuery)
#        - message.successful_payment   (we credit the user / activate plan)
#
# Provider tokens are issued by @botfather. Use
#   WALLET-TEST-1111111111111111  for sandbox testing.
# ============================================================

import json
from typing import List, Optional, Dict, Any

from core.bot_manager import bot_manager
from monitoring.logs import get_logger

log = get_logger(__name__)


# Public alias used by payment_manager.py
METHOD_KEY = "bale"


def send_invoice(
    bot_id: int,
    chat_id: int,
    title: str,
    description: str,
    payload: str,
    provider_token: str,
    prices: List[Dict[str, Any]],
    photo_url: Optional[str] = None,
    reply_to_message_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Send a Bale wallet invoice from the given bot to a chat.

    `prices`: list of {"label": "...", "amount": <int rials>}
    """
    api = bot_manager.get_api(bot_id)
    if api is None:
        raise RuntimeError("Bot {} is not running".format(bot_id))

    payload_dict = {
        "chat_id": chat_id,
        "title": title[:32],
        "description": description[:255],
        "payload": payload[:128],
        "provider_token": provider_token,
        "prices": prices,
    }
    if photo_url:
        payload_dict["photo_url"] = photo_url
    if reply_to_message_id:
        payload_dict["reply_to_message_id"] = reply_to_message_id

    log.info("sendInvoice bot=%s chat=%s payload=%s amount=%s",
             bot_id, chat_id, payload, sum(p["amount"] for p in prices))
    return api.call("sendInvoice", payload_dict)


def answer_pre_checkout(bot_id: int, pre_checkout_query_id: str,
                        ok: bool = True, error_message: Optional[str] = None) -> Dict[str, Any]:
    api = bot_manager.get_api(bot_id)
    if api is None:
        raise RuntimeError("Bot {} is not running".format(bot_id))
    payload = {"pre_checkout_query_id": pre_checkout_query_id, "ok": ok}
    if not ok and error_message:
        payload["error_message"] = error_message
    return api.call("answerPreCheckoutQuery", payload)


# ------------------------------------------------------------
# Helpers for building the `payload` field
# ------------------------------------------------------------
def build_payload(payment_id: int, kind: str = "payment", **extra) -> str:
    """
    Build a JSON payload to put into sendInvoice.payload.
    Keep it short - Bale limits this field to 128 bytes.
    """
    d = {"id": int(payment_id), "k": kind}
    d.update(extra)
    return json.dumps(d, separators=(",", ":"))


def parse_payload(payload_str: str) -> dict:
    try:
        return json.loads(payload_str)
    except Exception:
        return {}
