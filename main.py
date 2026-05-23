# ============================================================
# main.py - Entry point
# ============================================================
# Run with:
#     python main.py
#
# On Pydroid 3 (Android):
#     open this file and tap the "Play" button.
#
# Before first run, edit `config.py`:
#     MOTHER_BOT_TOKEN = "...your bot token..."
#     SUPER_ADMIN_IDS  = "...,..."   (env var) OR edit list directly
# ============================================================

import os
import sys


def _ensure_path():
    """Make sure imports like `from core.engine import engine` work
    regardless of where the script is launched from."""
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)


def main():
    _ensure_path()
    # Import AFTER path fix so relative-style imports resolve.
    from core.engine import engine
    engine.start()


if __name__ == "__main__":
    main()
