# ============================================================
# core/router.py - Lightweight command/text/callback router
# ============================================================
# Modules and admin/user panels register handlers here.
# The dispatcher consults the router first; if nothing matches,
# control falls back to the module registry / flow engine.
#
# This is the *only* place where commands/text-buttons get
# resolved to callables. Keep it simple and predictable.
# ============================================================

from typing import Callable, Dict, List, Optional, Tuple, Pattern
import re


class Router:
    def __init__(self):
        # /command  ->  handler(ctx)
        self._commands: Dict[str, Callable] = {}
        # exact-match Persian text buttons  ->  handler(ctx)
        self._texts: Dict[str, Callable] = {}
        # regex patterns  ->  handler(ctx, match)
        self._regex: List[Tuple[Pattern, Callable]] = []
        # callback data prefix  ->  handler(ctx)
        self._callbacks: List[Tuple[str, Callable]] = []
        # fallback when nothing matched
        self._default_handler: Optional[Callable] = None

    # --------------------------------------------------------
    # Registration
    # --------------------------------------------------------
    def command(self, name: str):
        """Decorator: @router.command('start')"""
        name = name.lstrip("/").lower()
        def deco(fn):
            self._commands[name] = fn
            return fn
        return deco

    def text(self, label: str):
        """Decorator: @router.text('کیف پول')"""
        def deco(fn):
            self._texts[label] = fn
            return fn
        return deco

    def regex(self, pattern: str, flags: int = 0):
        def deco(fn):
            self._regex.append((re.compile(pattern, flags), fn))
            return fn
        return deco

    def callback(self, prefix: str):
        """Decorator: @router.callback('plan:')"""
        def deco(fn):
            self._callbacks.append((prefix, fn))
            return fn
        return deco

    def default(self, fn: Callable):
        """Register the fallback handler."""
        self._default_handler = fn
        return fn

    # --------------------------------------------------------
    # Resolution
    # --------------------------------------------------------
    def resolve_command(self, cmd: str) -> Optional[Callable]:
        return self._commands.get(cmd.lstrip("/").lower())

    def resolve_text(self, text: str) -> Optional[Callable]:
        # exact match first
        if text in self._texts:
            return self._texts[text]
        # regex fallback
        for pat, fn in self._regex:
            m = pat.match(text)
            if m:
                return lambda ctx, _m=m, _fn=fn: _fn(ctx, _m)
        return None

    def resolve_callback(self, data: str) -> Optional[Callable]:
        for prefix, fn in self._callbacks:
            if data.startswith(prefix):
                return fn
        return None

    @property
    def default_handler(self) -> Optional[Callable]:
        return self._default_handler


# Two separate routers: one for the MOTHER bot (SaaS panel),
# one shared by CHILD bots (user-built bots). This keeps
# the panel commands from leaking into user bots.
mother_router = Router()
child_router  = Router()
