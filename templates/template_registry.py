# ============================================================
# templates/template_registry.py
# ============================================================
# Auto-discovers BotTemplate subclasses living in
#   templates/builtin/*.py
#
# Each .py file there MUST expose a module-level variable
# named  TEMPLATE  that is an instance of a BotTemplate subclass.
#
# On startup:
#   1) discover()          -> imports every builtin file
#   2) sync_to_db()        -> creates rows in `bot_templates`
#                              and per-template `plans` rows
#                              (idempotent; admins can change
#                              prices later and we will NOT
#                              overwrite them on next boot).
# ============================================================

import importlib
import json
import os
import pkgutil
from typing import Dict, List, Optional

from database.db import db
from monitoring.logs import get_logger
from config import SUBSCRIPTION_DURATIONS
from templates.template_base import BotTemplate

log = get_logger(__name__)


# In-memory registry: key -> BotTemplate instance
_REGISTRY: Dict[str, BotTemplate] = {}


# ------------------------------------------------------------
# Public API
# ------------------------------------------------------------
def register(template: BotTemplate):
    if not isinstance(template, BotTemplate):
        raise TypeError("register() expects a BotTemplate instance")
    if not template.key:
        raise ValueError("template.key is required")
    if template.key in _REGISTRY:
        log.warning("Template '%s' already registered, overwriting.", template.key)
    _REGISTRY[template.key] = template
    log.info("Registered template: %s (%s)", template.key, template.name)


def get(key: str) -> Optional[BotTemplate]:
    return _REGISTRY.get(key)


def all_templates() -> List[BotTemplate]:
    return list(_REGISTRY.values())


def db_row(key: str) -> Optional[dict]:
    return db.fetchone("SELECT * FROM bot_templates WHERE key=?", (key,))


# ------------------------------------------------------------
# Auto-discovery
# ------------------------------------------------------------
def discover():
    """Import every file under templates/builtin/ so its TEMPLATE
    instance gets registered via templates.template_registry.register()."""
    try:
        from templates import builtin as builtin_pkg
    except Exception as e:
        log.warning("templates/builtin not importable: %s", e)
        return

    pkg_path = os.path.dirname(builtin_pkg.__file__)
    for _, name, ispkg in pkgutil.iter_modules([pkg_path]):
        if ispkg or name.startswith("_"):
            continue
        full_name = "templates.builtin." + name
        try:
            mod = importlib.import_module(full_name)
            tpl = getattr(mod, "TEMPLATE", None)
            if isinstance(tpl, BotTemplate):
                register(tpl)
            else:
                log.warning("%s has no TEMPLATE attribute - skipped", full_name)
        except Exception as e:
            log.exception("Failed to load template module %s: %s", full_name, e)


# ------------------------------------------------------------
# Sync to DB
# ------------------------------------------------------------
def sync_to_db():
    """
    Make sure every registered template has a row in `bot_templates`
    and a matching set of `plans` rows (one per duration).

    PRICE PROTECTION: if an admin has manually changed a plan price
    via the admin panel, we do NOT overwrite it. We only create
    missing rows; existing rows are left intact (except is_active=1
    is enforced so deactivated plans stay deactivated by admin).
    """
    for tpl in _REGISTRY.values():
        _sync_template_row(tpl)
        _sync_template_plans(tpl)


def _sync_template_row(tpl: BotTemplate):
    existing = db_row(tpl.key)
    content_blob = json.dumps({
        "version": tpl.version,
        "icon": tpl.icon,
        "required_modules": tpl.required_modules,
    }, ensure_ascii=False)

    if existing:
        # Refresh metadata, but NOT price/is_published (admin-controlled).
        db.execute(
            """UPDATE bot_templates
                  SET name=?, description=?, content_json=?
                WHERE id=?""",
            (tpl.name, tpl.description, content_blob, existing["id"]),
        )
    else:
        db.execute(
            """INSERT INTO bot_templates
                  (key, name, description, price, content_json, is_published)
               VALUES (?, ?, ?, 0, ?, 1)""",
            (tpl.key, tpl.name, tpl.description, content_blob),
        )


def _sync_template_plans(tpl: BotTemplate):
    """
    Each plan_specs entry becomes a row in `plans` with
    key = "<tpl_key>_<duration_key>" and allowed_templates=[tpl_key].
    Admin can later edit price/limits via /setprice or the panel.
    """
    if not tpl.plan_specs:
        return
    for spec in tpl.plan_specs:
        dur = spec.get("duration")
        if dur not in SUBSCRIPTION_DURATIONS:
            log.warning("Template %s: unknown duration '%s' - skipped", tpl.key, dur)
            continue
        plan_key = "{}_{}".format(tpl.key, dur)
        existing = db.fetchone("SELECT id FROM plans WHERE key=?", (plan_key,))
        if existing:
            continue  # do NOT overwrite admin-set prices

        days = SUBSCRIPTION_DURATIONS[dur]
        allowed_templates = spec.get("allowed_templates") or [tpl.key]
        if tpl.key not in allowed_templates:
            allowed_templates.append(tpl.key)

        db.execute(
            """INSERT INTO plans
                  (key, name, description, duration_days, price,
                   max_bots, max_users_per_bot, max_monthly_messages,
                   allowed_modules, allowed_templates, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (
                plan_key,
                "{} - {}".format(tpl.name, spec.get("name") or dur),
                spec.get("description") or "",
                days,
                int(spec.get("price", 0)),
                int(spec.get("max_bots", 1)),
                int(spec.get("max_users_per_bot", 1000)),
                int(spec.get("max_monthly_messages", 10_000)),
                json.dumps(spec.get("allowed_modules") or []),
                json.dumps(allowed_templates),
            ),
        )
        log.info("Plan created: %s (template=%s)", plan_key, tpl.key)


# ------------------------------------------------------------
# Queries used by panels
# ------------------------------------------------------------
def list_plans_for_template(template_key: str) -> List[dict]:
    """Returns plans rows whose allowed_templates contains template_key."""
    rows = db.fetchall("SELECT * FROM plans WHERE is_active=1 ORDER BY price ASC")
    out = []
    for r in rows:
        try:
            allowed = json.loads(r.get("allowed_templates") or "[]")
        except Exception:
            allowed = []
        if template_key in allowed:
            out.append(r)
    return out


def list_published_templates() -> List[dict]:
    rows = db.fetchall(
        "SELECT * FROM bot_templates WHERE is_published=1 ORDER BY id ASC"
    )
    # only return ones still registered in memory
    return [r for r in rows if r["key"] in _REGISTRY]
