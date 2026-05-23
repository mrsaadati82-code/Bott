# ============================================================
# monitoring/logs.py - Unified logger
# ============================================================

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from config import LOG_FILE, LOG_LEVEL, APP_NAME


_logger = None


def get_logger(name: str = APP_NAME) -> logging.Logger:
    global _logger
    if _logger is not None:
        return logging.getLogger(name)

    logger = logging.getLogger(APP_NAME)
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    logger.propagate = False

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File (rotating to avoid filling phone storage)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        fh = RotatingFileHandler(LOG_FILE, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception:
        # On Pydroid sometimes the path is restricted - ignore.
        pass

    _logger = logger
    return logging.getLogger(name)
