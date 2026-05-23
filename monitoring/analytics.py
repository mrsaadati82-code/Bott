# ============================================================
# monitoring/analytics.py
# ============================================================
# Aggregations used by the admin panel "📊 آمار" screen and
# by super-admin /revenue.
# All queries are SQLite-safe and use simple WHERE clauses.
# ============================================================

from database.db import db


# ------------------------------------------------------------
# Totals
# ------------------------------------------------------------
def total_users() -> int:
    r = db.fetchone("SELECT COUNT(*) AS c FROM users")
    return int(r["c"]) if r else 0


def total_bots() -> int:
    r = db.fetchone("SELECT COUNT(*) AS c FROM bots WHERE status='active'")
    return int(r["c"]) if r else 0


def total_revenue() -> int:
    r = db.fetchone(
        "SELECT COALESCE(SUM(amount), 0) AS s FROM payments WHERE status='approved'"
    )
    return int(r["s"]) if r else 0


def total_transactions() -> int:
    r = db.fetchone("SELECT COUNT(*) AS c FROM payments")
    return int(r["c"]) if r else 0


def total_subscriptions() -> int:
    r = db.fetchone("SELECT COUNT(*) AS c FROM subscriptions WHERE status='active'")
    return int(r["c"]) if r else 0


# ------------------------------------------------------------
# Daily growth (last N days)
# ------------------------------------------------------------
def _daily_count(table: str, date_col: str = "created_at", days: int = 7):
    """
    Return list of (date, count) for the last `days` days, oldest first.
    Uses SQLite's DATE() so it works without extra deps.
    """
    rows = db.fetchall(
        """SELECT DATE({dc}) AS day, COUNT(*) AS c
             FROM {t}
             WHERE {dc} >= datetime('now', ?)
             GROUP BY DATE({dc})
             ORDER BY day ASC""".format(t=table, dc=date_col),
        ("-{} days".format(int(days)),),
    )
    return [(r["day"], int(r["c"])) for r in rows]


def daily_user_growth(days: int = 7):
    return _daily_count("users", "created_at", days)


def daily_payment_volume(days: int = 7):
    rows = db.fetchall(
        """SELECT DATE(created_at) AS day,
                  COALESCE(SUM(amount),0) AS s, COUNT(*) AS c
             FROM payments
             WHERE status='approved' AND created_at >= datetime('now', ?)
             GROUP BY DATE(created_at)
             ORDER BY day ASC""",
        ("-{} days".format(int(days)),),
    )
    return [(r["day"], int(r["s"]), int(r["c"])) for r in rows]


# ------------------------------------------------------------
# Per-bot stats
# ------------------------------------------------------------
def per_bot_stats(bot_id: int) -> dict:
    """
    Aggregate stats for one child bot.
    Note: we don't track per-bot message counts yet; this returns
    structural info (#subscriptions, owner balance, etc.).
    """
    b = db.fetchone("SELECT * FROM bots WHERE id=?", (int(bot_id),))
    if not b:
        return {}
    subs = db.fetchone(
        "SELECT COUNT(*) AS c FROM subscriptions WHERE bot_id=? AND status='active'",
        (int(bot_id),),
    )
    return {
        "id": b["id"],
        "username": b.get("bot_username"),
        "status": b["status"],
        "active_subscriptions": int(subs["c"]) if subs else 0,
    }


# ------------------------------------------------------------
# Top resellers
# ------------------------------------------------------------
def top_referrers(limit: int = 5):
    rows = db.fetchall(
        """SELECT u.id, u.bale_user_id, u.first_name, COUNT(r.id) AS n
             FROM users u
             LEFT JOIN users r ON r.referrer_id = u.id
             GROUP BY u.id
             HAVING n > 0
             ORDER BY n DESC LIMIT ?""",
        (int(limit),),
    )
    return rows
