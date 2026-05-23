# ============================================================
# subscriptions/plan_manager.py
# ============================================================
# CRUD + queries on the `plans` table.
# A plan defines: duration_days, price, max_bots,
# max_users_per_bot, max_monthly_messages,
# allowed_modules[], allowed_templates[].
# ============================================================

import json
from typing import List, Optional, Dict

from database.db import db
from config import SUBSCRIPTION_DURATIONS


# Duration keys exposed to UI -> days
DURATION_KEYS = list(SUBSCRIPTION_DURATIONS.keys())  # monthly|quarterly|biannual|yearly


def _row_to_plan(row: dict) -> dict:
    if not row:
        return None
    row = dict(row)
    try:
        row["allowed_modules"]   = json.loads(row.get("allowed_modules")   or "[]")
        row["allowed_templates"] = json.loads(row.get("allowed_templates") or "[]")
    except Exception:
        row["allowed_modules"]   = []
        row["allowed_templates"] = []
    return row


# ------------------------------------------------------------
# Queries
# ------------------------------------------------------------
def list_plans(only_active: bool = True) -> List[dict]:
    sql = "SELECT * FROM plans"
    if only_active:
        sql += " WHERE is_active=1"
    sql += " ORDER BY price ASC, id ASC"
    return [_row_to_plan(r) for r in db.fetchall(sql)]


def get_plan(plan_id: int) -> Optional[dict]:
    return _row_to_plan(db.fetchone("SELECT * FROM plans WHERE id=?", (int(plan_id),)))


def get_plan_by_key(key: str) -> Optional[dict]:
    return _row_to_plan(db.fetchone("SELECT * FROM plans WHERE key=?", (key,)))


# ------------------------------------------------------------
# Mutations
# ------------------------------------------------------------
def create_plan(
    key: str,
    name: str,
    duration_days: int,
    price: int,
    max_bots: int = 1,
    max_users_per_bot: int = 1000,
    max_monthly_messages: int = 10000,
    allowed_modules: Optional[List[str]] = None,
    allowed_templates: Optional[List[str]] = None,
    description: str = "",
    is_active: bool = True,
) -> int:
    return db.insert(
        """INSERT INTO plans
              (key, name, description, duration_days, price,
               max_bots, max_users_per_bot, max_monthly_messages,
               allowed_modules, allowed_templates, is_active)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            key, name, description, int(duration_days), int(price),
            int(max_bots), int(max_users_per_bot), int(max_monthly_messages),
            json.dumps(allowed_modules or []),
            json.dumps(allowed_templates or []),
            1 if is_active else 0,
        ),
    )


def update_plan(plan_id: int, **fields):
    if not fields:
        return
    cols, vals = [], []
    for k, v in fields.items():
        if k in ("allowed_modules", "allowed_templates"):
            v = json.dumps(v or [])
        cols.append("{}=?".format(k))
        vals.append(v)
    vals.append(int(plan_id))
    db.execute("UPDATE plans SET {} WHERE id=?".format(", ".join(cols)), tuple(vals))


def set_active(plan_id: int, active: bool):
    db.execute("UPDATE plans SET is_active=? WHERE id=?", (1 if active else 0, int(plan_id)))


def delete_plan(plan_id: int):
    # Soft-delete: deactivate. Real deletion would break FKs on subscriptions.
    set_active(plan_id, False)


# ------------------------------------------------------------
# Convenience: create the four standard durations of a plan
# ------------------------------------------------------------
def ensure_standard_durations(base_key: str, base_name: str, monthly_price: int,
                              **limits) -> Dict[str, int]:
    """
    Create (if missing) the 4 standard plan variants:
        <base_key>_monthly, _quarterly, _biannual, _yearly
    Quarterly = 3x price, biannual = 6x, yearly = 12x. Override any
    limit via **limits (max_bots, max_users_per_bot, ...).
    """
    multipliers = {"monthly": 1, "quarterly": 3, "biannual": 6, "yearly": 12}
    result = {}
    for k, days in SUBSCRIPTION_DURATIONS.items():
        full_key = "{}_{}".format(base_key, k)
        existing = get_plan_by_key(full_key)
        if existing:
            result[k] = existing["id"]
            continue
        result[k] = create_plan(
            key=full_key,
            name="{} ({})".format(base_name, k),
            duration_days=days,
            price=int(monthly_price) * multipliers[k],
            **limits,
        )
    return result
