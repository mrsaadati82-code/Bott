# ============================================================
# payments/wallet_gateway.py - "Pay from wallet" gateway
# ============================================================
# Instant gateway: if user has enough balance, debit immediately
# and auto-approve the payment.
# ============================================================

from typing import Tuple

from wallet.wallet_manager import get_balance, debit
from monitoring.logs import get_logger

log = get_logger(__name__)


METHOD_KEY = "wallet"


def has_enough(user_id: int, amount: int) -> bool:
    return int(get_balance(user_id)) >= int(amount)


def shortage(user_id: int, amount: int) -> int:
    """How much more the user needs to top up to afford `amount`."""
    return max(0, int(amount) - int(get_balance(user_id)))


def charge(user_id: int, amount: int, description: str = "",
           ref_type: str = "", ref_id: int = None) -> Tuple[bool, str]:
    """
    Debit the wallet for `amount`. Returns (ok, message).
    Raises nothing - returns (False, reason) on failure.
    """
    try:
        r = debit(
            user_id, int(amount),
            tx_type="purchase",
            description=description or "خرید از کیف پول",
            ref_type=ref_type or None,
            ref_id=ref_id,
        )
        return True, "ok (new_balance={})".format(r["balance"])
    except ValueError as e:
        return False, str(e)
    except Exception as e:
        log.exception("wallet charge failed: %s", e)
        return False, str(e)
