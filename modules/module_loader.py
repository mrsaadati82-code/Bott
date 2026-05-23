# ============================================================
# modules/module_loader.py
# ============================================================
# Auto-discovers and registers modules from modules/builtin/.
#
# Each builtin module file MUST expose a module-level variable
# named  MODULE  that is a ModuleMeta instance:
#
#   from modules.module_registry import ModuleMeta, FEATURE_MODULES
#   MODULE = ModuleMeta(
#       key="shop",
#       name="فروشگاه",
#       version="1.0.0",
#       feature=FEATURE_MODULES,
#       on_message=my_handler,
#       on_callback=my_cb_handler,
#       on_command={"order": my_order_cmd},
#   )
#
# To add a NEW module: drop a .py file here. No core changes.
# ============================================================

import importlib
import os
import pkgutil

from monitoring.logs import get_logger
from modules.module_registry import module_registry, ModuleMeta

log = get_logger(__name__)


def discover_and_register():
    try:
        from modules import builtin as builtin_pkg
    except Exception as e:
        log.info("modules/builtin not found (ok if empty): %s", e)
        return

    pkg_path = os.path.dirname(builtin_pkg.__file__)
    count = 0
    for _, name, ispkg in pkgutil.iter_modules([pkg_path]):
        if ispkg or name.startswith("_"):
            continue
        full = "modules.builtin." + name
        try:
            mod = importlib.import_module(full)
            meta = getattr(mod, "MODULE", None)
            if isinstance(meta, ModuleMeta):
                module_registry.register(meta)
                count += 1
            else:
                log.warning("%s has no MODULE attribute - skipped", full)
        except Exception as e:
            log.exception("Failed to load module %s: %s", full, e)
    log.info("Auto-registered %s modules from modules/builtin/", count)
