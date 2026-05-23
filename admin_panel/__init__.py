# package: admin_panel
# ============================================================
# Single entrypoint for the engine: setup_all()
# Registers every admin/super-admin/reseller/template handler
# AND the end-user panel on the mother bot's router.
# ============================================================

from admin_panel import (
    admin_commands,
    super_admin,
    reseller as reseller_panel,
    user_panel,
    template_admin,
)


def setup_all():
    # User-facing handlers FIRST so its regex catcher runs only
    # when an explicit user FSM state is active.
    user_panel.setup()
    admin_commands.setup()
    super_admin.setup()
    reseller_panel.setup()
    template_admin.setup()
