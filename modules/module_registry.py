# ============================================================
# modules/module_registry.py
# ============================================================
# Two responsibilities:
#
# 1) FEATURE REGISTRY (Memory Protection System)
#    A *locked* list of high-level features supported by the
#    platform. Features are NEVER removed - only added.
#    Any new capability MUST register a FEATURE_* constant here.
#
# 2) MODULE REGISTRY
#    Runtime registry where individual modules (shop, survey,
#    etc.) register themselves so the core engine can dispatch
#    messages/callbacks/commands to them without the core ever
#    importing them directly.
# ============================================================

from typing import Callable, Dict, List, Optional


# ============================================================
# 1) FEATURE REGISTRY  (locked - additions only)
# ============================================================

FEATURE_PAGE_BUILDER   = "FEATURE_PAGE_BUILDER"
FEATURE_FLOW_BUILDER   = "FEATURE_FLOW_BUILDER"
FEATURE_MULTI_BOT      = "FEATURE_MULTI_BOT"
FEATURE_SUBSCRIPTIONS  = "FEATURE_SUBSCRIPTIONS"
FEATURE_WALLET         = "FEATURE_WALLET"
FEATURE_PAYMENT        = "FEATURE_PAYMENT"
FEATURE_CHANNEL_LOCK   = "FEATURE_CHANNEL_LOCK"
FEATURE_BROADCAST      = "FEATURE_BROADCAST"
FEATURE_ANALYTICS      = "FEATURE_ANALYTICS"
FEATURE_TEMPLATES      = "FEATURE_TEMPLATES"
FEATURE_MODULES        = "FEATURE_MODULES"
FEATURE_RESELLER       = "FEATURE_RESELLER"


FEATURES: List[str] = [
    FEATURE_PAGE_BUILDER,
    FEATURE_FLOW_BUILDER,
    FEATURE_MULTI_BOT,
    FEATURE_SUBSCRIPTIONS,
    FEATURE_WALLET,
    FEATURE_PAYMENT,
    FEATURE_CHANNEL_LOCK,
    FEATURE_BROADCAST,
    FEATURE_ANALYTICS,
    FEATURE_TEMPLATES,
    FEATURE_MODULES,
    FEATURE_RESELLER,
]


def assert_feature(name: str):
    """Raise if a feature key isn't registered (developer-time guard)."""
    if name not in FEATURES:
        raise RuntimeError(
            "Unknown feature '{}'. Register it in modules/module_registry.py first.".format(name)
        )


# ============================================================
# 2) MODULE REGISTRY  (runtime)
# ============================================================

class ModuleMeta:
    """Lightweight metadata + entrypoints for a module."""
    def __init__(
        self,
        key: str,
        name: str,
        version: str = "1.0.0",
        feature: Optional[str] = None,
        on_load: Optional[Callable] = None,
        on_message: Optional[Callable] = None,
        on_callback: Optional[Callable] = None,
        on_command: Optional[Dict[str, Callable]] = None,
    ):
        self.key = key
        self.name = name
        self.version = version
        self.feature = feature
        self.on_load = on_load
        self.on_message = on_message
        self.on_callback = on_callback
        self.on_command = on_command or {}

    def __repr__(self):
        return "<Module {} v{}>".format(self.key, self.version)


class ModuleRegistry:
    def __init__(self):
        self._modules: Dict[str, ModuleMeta] = {}

    # ----------------------------------------
    # Registration
    # ----------------------------------------
    def register(self, module: ModuleMeta):
        if module.feature is not None:
            assert_feature(module.feature)
        if module.key in self._modules:
            raise RuntimeError("Module '{}' already registered.".format(module.key))
        self._modules[module.key] = module
        if callable(module.on_load):
            module.on_load()

    def get(self, key: str) -> Optional[ModuleMeta]:
        return self._modules.get(key)

    def all(self) -> List[ModuleMeta]:
        return list(self._modules.values())

    # ----------------------------------------
    # Dispatch helpers (used by core/dispatcher.py)
    # ----------------------------------------
    def dispatch_command(self, command: str, ctx) -> bool:
        """Returns True if at least one module handled the command."""
        handled = False
        for m in self._modules.values():
            fn = m.on_command.get(command)
            if fn:
                try:
                    fn(ctx)
                    handled = True
                except Exception as e:
                    # logging is done by caller
                    raise
        return handled

    def dispatch_message(self, ctx):
        for m in self._modules.values():
            if m.on_message:
                m.on_message(ctx)

    def dispatch_callback(self, ctx):
        for m in self._modules.values():
            if m.on_callback:
                m.on_callback(ctx)


# Singleton
module_registry = ModuleRegistry()
