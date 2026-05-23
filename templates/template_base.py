# ============================================================
# templates/template_base.py
# ============================================================
# Base class every BotTemplate inherits from.
#
# A BotTemplate is a PLUG-AND-PLAY package that contains:
#   - metadata (key, name, description, icon)
#   - default subscription plans (plan_specs) tied to the template
#   - default pages (declarative dicts -> page_manager)
#   - default flows (declarative dicts -> flow_manager)
#   - optional required modules (by key)
#
# To add a new template, drop a *.py file inside
#   templates/builtin/   with a subclass of BotTemplate and a
#   module-level   TEMPLATE = MyTemplate()
# Nothing else needs to change. The registry auto-discovers it.
# ============================================================

from typing import Dict, List, Optional, Any


class BotTemplate:
    # --------------------------------------------------------
    # Required class attributes (override in subclasses)
    # --------------------------------------------------------
    key: str = ""           # unique key, e.g. "shop_basic"
    name: str = ""          # display name in Persian
    description: str = ""
    icon: str = "🤖"
    version: str = "1.0.0"

    # Per-template subscription plans (locked durations only).
    # Each entry generates a `plans` row with key = "<tpl_key>_<duration_key>".
    # Limits + price are template-specific so each template can have
    # its own monetization strategy.
    #
    # plan_specs = [
    #     {
    #         "duration": "monthly",   # monthly|quarterly|biannual|yearly
    #         "name": "ماهانه",
    #         "price": 200_000,
    #         "max_bots": 1,
    #         "max_users_per_bot": 5_000,
    #         "max_monthly_messages": 30_000,
    #         "allowed_modules": [],
    #         "allowed_templates": [],   # auto-filled with [key]
    #     },
    #     ...
    # ]
    plan_specs: List[Dict[str, Any]] = []

    # Required modules (by module key). Will be auto-enabled.
    required_modules: List[str] = []

    # --------------------------------------------------------
    # Content (override these to return declarative content)
    # --------------------------------------------------------
    def get_pages(self) -> Dict[str, Dict[str, Any]]:
        """
        Return a dict of pages, e.g.:
            {
                "home": {"text": "...", "buttons": [...]},
                "about": {"text": "...", "buttons": [...]},
            }
        """
        return {}

    def get_start_page(self) -> Optional[str]:
        """Which page should be the start_page. Defaults to first page."""
        pages = self.get_pages()
        return next(iter(pages.keys()), None)

    def get_flows(self) -> Dict[str, Dict[str, Any]]:
        """
        Return a dict of flows, e.g.:
            {
                "feedback": {
                    "trigger": "/feedback",
                    "steps": [...]
                }
            }
        """
        return {}

    def get_channel_locks(self) -> List[Dict[str, Any]]:
        """Optional: [{'channel_id': '@x', 'title': 'X', 'required': True}, ...]"""
        return []

    # --------------------------------------------------------
    # Apply template content onto a freshly-created child bot
    # --------------------------------------------------------
    def apply(self, bot_id: int):
        """
        Materialize the template onto bot_id by creating its
        pages / flows / locks via the public managers.
        Idempotent: re-applying merges (doesn't duplicate).
        """
        from page_builder import page_manager
        from flow_engine import flow_manager
        from channel_lock import channel_checker

        # Pages
        pages = self.get_pages()
        existing_pages = set(page_manager.list_pages(bot_id))
        for name, page in pages.items():
            if name in existing_pages:
                page_manager.update_page(bot_id, name,
                                         text=page.get("text"),
                                         buttons=page.get("buttons") or [])
            else:
                page_manager.create_page(bot_id, name,
                                         text=page.get("text") or name,
                                         buttons=page.get("buttons") or [])
        sp = self.get_start_page()
        if sp and sp in page_manager.list_pages(bot_id):
            page_manager.set_start_page(bot_id, sp)

        # Flows
        flows = self.get_flows()
        existing_flows = set(flow_manager.list_flows(bot_id))
        for name, f in flows.items():
            if name in existing_flows:
                flow_manager.update_flow(bot_id, name,
                                         steps=f.get("steps") or [],
                                         trigger=f.get("trigger"))
            else:
                flow_manager.create_flow(bot_id, name,
                                         steps=f.get("steps") or [],
                                         trigger=f.get("trigger"))

        # Channel locks
        for lock in self.get_channel_locks():
            channel_checker.add_channel(
                bot_id,
                lock["channel_id"],
                title=lock.get("title") or lock["channel_id"],
                required=lock.get("required", True),
            )

    # --------------------------------------------------------
    # Repr
    # --------------------------------------------------------
    def __repr__(self):
        return "<Template {} v{}>".format(self.key, self.version)
