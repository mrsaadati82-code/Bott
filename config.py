# ============================================================
# Bot Builder SaaS - Bale Messenger
# config.py - Central Configuration
# ============================================================
# All settings of the system live here. Read by every module.
# Do NOT scatter constants in other files.
# ============================================================

import os

# ------------------------------------------------------------
# Base paths
# ------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# ------------------------------------------------------------
# Bale API
# ------------------------------------------------------------
# Per official docs: https://docs.bale.ai
BALE_API_BASE = "https://tapi.bale.ai"


def bale_api_url(token: str, method: str) -> str:
    """Build a fully-qualified Bale API endpoint."""
    return "{}/bot{}/{}".format(BALE_API_BASE, token, method)


# ------------------------------------------------------------
# Mother Bot (the SaaS panel bot)
# ------------------------------------------------------------
# Token of the central "mother" bot through which users manage
# their child bots, buy subscriptions, etc.
# IMPORTANT: replace with your real token before running.
MOTHER_BOT_TOKEN = os.environ.get(
    "MOTHER_BOT_TOKEN",
    "PUT_YOUR_MOTHER_BOT_TOKEN_HERE",
)

# Numeric Bale user id(s) of super-admin(s).
# Get yours by sending /start to your bot, then read message.from.id
SUPER_ADMIN_IDS = [
    int(x) for x in os.environ.get("SUPER_ADMIN_IDS", "0").split(",") if x.strip().isdigit()
]

# ------------------------------------------------------------
# Polling settings (getUpdates - long polling)
# ------------------------------------------------------------
POLL_TIMEOUT = 30        # seconds; Bale long-poll timeout
POLL_LIMIT = 100         # max updates per request (1..100)
POLL_ERROR_SLEEP = 3     # seconds to wait after a network error

# ------------------------------------------------------------
# Database
# ------------------------------------------------------------
# SQLite by default. Switching to PostgreSQL only requires
# changing DB_BACKEND and providing DB_DSN.
DB_BACKEND = os.environ.get("DB_BACKEND", "sqlite")   # 'sqlite' | 'postgres'
DB_PATH = os.path.join(DATA_DIR, "botbuilder.sqlite3")
DB_DSN = os.environ.get("DB_DSN", "")  # used only if DB_BACKEND='postgres'

# ------------------------------------------------------------
# Subscription defaults (days)
# ------------------------------------------------------------
SUBSCRIPTION_DURATIONS = {
    "monthly": 30,
    "quarterly": 90,
    "biannual": 180,
    "yearly": 365,
}

# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------
LOG_DIR = os.path.join(DATA_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "botbuilder.log")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# ------------------------------------------------------------
# Misc
# ------------------------------------------------------------
DEFAULT_LANGUAGE = "fa"
APP_NAME = "BaleBotBuilder"
APP_VERSION = "0.1.0"
