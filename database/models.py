# ============================================================
# database/models.py - Schema definitions (DDL)
# ============================================================
# All tables defined in the project spec live here as plain
# SQL strings. migrations.py applies them and bumps schema_version.
#
# Tables (locked list - do not remove):
#   users, admins, bots, bot_templates, modules,
#   plans, subscriptions, wallets, wallet_transactions,
#   payments, payment_methods, gift_codes, products,
#   categories, orders, channel_locks, broadcasts,
#   system_settings, schema_version
# ============================================================

# Current schema version. Increase whenever you add a migration.
SCHEMA_VERSION = 1


# Ordered list of (name, DDL) - executed during init.
TABLES = [
    # --------------------------------------------------------
    ("schema_version", """
        CREATE TABLE IF NOT EXISTS schema_version (
            id            INTEGER PRIMARY KEY,
            version       INTEGER NOT NULL,
            applied_at    TEXT    NOT NULL DEFAULT (datetime('now'))
        );
    """),

    # --------------------------------------------------------
    ("users", """
        CREATE TABLE IF NOT EXISTS users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            bale_user_id    INTEGER NOT NULL UNIQUE,
            username        TEXT,
            first_name      TEXT,
            last_name       TEXT,
            phone           TEXT,
            language        TEXT DEFAULT 'fa',
            is_blocked      INTEGER NOT NULL DEFAULT 0,
            referrer_id     INTEGER,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """),

    # --------------------------------------------------------
    ("admins", """
        CREATE TABLE IF NOT EXISTS admins (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL UNIQUE,
            role            TEXT NOT NULL DEFAULT 'admin',  -- 'super_admin' | 'admin' | 'reseller'
            permissions     TEXT,                            -- JSON array of permission keys
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """),

    # --------------------------------------------------------
    ("bots", """
        CREATE TABLE IF NOT EXISTS bots (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id        INTEGER NOT NULL,                -- users.id of bot owner
            token           TEXT NOT NULL UNIQUE,
            bot_username    TEXT,
            display_name    TEXT,
            template_id     INTEGER,                          -- nullable: built from template?
            status          TEXT NOT NULL DEFAULT 'active',  -- 'active'|'paused'|'banned'
            settings_json   TEXT NOT NULL DEFAULT '{}',
            last_update_id  INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (owner_id)   REFERENCES users(id)         ON DELETE CASCADE,
            FOREIGN KEY (template_id) REFERENCES bot_templates(id) ON DELETE SET NULL
        );
    """),

    # --------------------------------------------------------
    ("bot_templates", """
        CREATE TABLE IF NOT EXISTS bot_templates (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            key             TEXT NOT NULL UNIQUE,            -- e.g. 'shop_basic'
            name            TEXT NOT NULL,
            description     TEXT,
            price           INTEGER NOT NULL DEFAULT 0,
            content_json    TEXT NOT NULL DEFAULT '{}',      -- pages, flows, modules
            is_published    INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """),

    # --------------------------------------------------------
    ("modules", """
        CREATE TABLE IF NOT EXISTS modules (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            key             TEXT NOT NULL UNIQUE,            -- e.g. 'shop', 'survey'
            name            TEXT NOT NULL,
            description     TEXT,
            version         TEXT NOT NULL DEFAULT '1.0.0',
            price           INTEGER NOT NULL DEFAULT 0,
            is_core         INTEGER NOT NULL DEFAULT 0,
            is_enabled      INTEGER NOT NULL DEFAULT 1,
            config_json     TEXT NOT NULL DEFAULT '{}',
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """),

    # --------------------------------------------------------
    ("plans", """
        CREATE TABLE IF NOT EXISTS plans (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            key                   TEXT NOT NULL UNIQUE,
            name                  TEXT NOT NULL,
            description           TEXT,
            duration_days         INTEGER NOT NULL,
            price                 INTEGER NOT NULL DEFAULT 0,
            max_bots              INTEGER NOT NULL DEFAULT 1,
            max_users_per_bot     INTEGER NOT NULL DEFAULT 1000,
            max_monthly_messages  INTEGER NOT NULL DEFAULT 10000,
            allowed_modules       TEXT NOT NULL DEFAULT '[]',  -- JSON array of module keys
            allowed_templates     TEXT NOT NULL DEFAULT '[]',  -- JSON array of template keys
            is_active             INTEGER NOT NULL DEFAULT 1,
            created_at            TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """),

    # --------------------------------------------------------
    ("subscriptions", """
        CREATE TABLE IF NOT EXISTS subscriptions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            bot_id          INTEGER,                          -- nullable: account-wide vs per-bot
            plan_id         INTEGER NOT NULL,
            starts_at       TEXT NOT NULL DEFAULT (datetime('now')),
            ends_at         TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'active',  -- 'active'|'expired'|'cancelled'
            usage_json      TEXT NOT NULL DEFAULT '{}',      -- counters: messages, bots, etc.
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (bot_id)  REFERENCES bots(id)  ON DELETE CASCADE,
            FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE RESTRICT
        );
    """),

    # --------------------------------------------------------
    ("wallets", """
        CREATE TABLE IF NOT EXISTS wallets (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL UNIQUE,
            balance         INTEGER NOT NULL DEFAULT 0,       -- stored in rials (integer)
            currency        TEXT NOT NULL DEFAULT 'IRR',
            updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """),

    # --------------------------------------------------------
    ("wallet_transactions", """
        CREATE TABLE IF NOT EXISTS wallet_transactions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            wallet_id       INTEGER NOT NULL,
            amount          INTEGER NOT NULL,                 -- positive=credit, negative=debit
            type            TEXT NOT NULL,                    -- 'topup'|'purchase'|'gift'|'refund'|'manual'
            ref_type        TEXT,                             -- 'payment'|'subscription'|'order' ...
            ref_id          INTEGER,
            description     TEXT,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (wallet_id) REFERENCES wallets(id) ON DELETE CASCADE
        );
    """),

    # --------------------------------------------------------
    ("payment_methods", """
        CREATE TABLE IF NOT EXISTS payment_methods (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            key             TEXT NOT NULL UNIQUE,            -- 'bale'|'online'|'card_to_card'
            name            TEXT NOT NULL,
            is_enabled      INTEGER NOT NULL DEFAULT 1,
            config_json     TEXT NOT NULL DEFAULT '{}',
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """),

    # --------------------------------------------------------
    ("payments", """
        CREATE TABLE IF NOT EXISTS payments (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            method_key      TEXT NOT NULL,                    -- references payment_methods.key
            amount          INTEGER NOT NULL,
            currency        TEXT NOT NULL DEFAULT 'IRR',
            status          TEXT NOT NULL DEFAULT 'pending', -- pending|approved|rejected|failed
            ref_type        TEXT,                             -- 'subscription'|'wallet_topup'|'order'
            ref_id          INTEGER,
            gateway_ref     TEXT,                             -- external gateway reference / receipt
            meta_json       TEXT NOT NULL DEFAULT '{}',
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """),

    # --------------------------------------------------------
    ("gift_codes", """
        CREATE TABLE IF NOT EXISTS gift_codes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            code            TEXT NOT NULL UNIQUE,
            amount          INTEGER NOT NULL DEFAULT 0,       -- wallet credit on redeem
            plan_id         INTEGER,                          -- optional: grants a plan instead
            max_uses        INTEGER NOT NULL DEFAULT 1,
            used_count      INTEGER NOT NULL DEFAULT 0,
            expires_at      TEXT,
            is_active       INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE SET NULL
        );
    """),

    # --------------------------------------------------------
    ("categories", """
        CREATE TABLE IF NOT EXISTS categories (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id          INTEGER NOT NULL,
            parent_id       INTEGER,
            name            TEXT NOT NULL,
            sort_order      INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (bot_id)    REFERENCES bots(id)       ON DELETE CASCADE,
            FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL
        );
    """),

    # --------------------------------------------------------
    ("products", """
        CREATE TABLE IF NOT EXISTS products (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id          INTEGER NOT NULL,
            category_id     INTEGER,
            name            TEXT NOT NULL,
            description     TEXT,
            price           INTEGER NOT NULL DEFAULT 0,
            stock           INTEGER NOT NULL DEFAULT -1,      -- -1 = unlimited
            meta_json       TEXT NOT NULL DEFAULT '{}',
            is_active       INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (bot_id)      REFERENCES bots(id)       ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
        );
    """),

    # --------------------------------------------------------
    ("orders", """
        CREATE TABLE IF NOT EXISTS orders (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id          INTEGER NOT NULL,
            user_id         INTEGER NOT NULL,
            items_json      TEXT NOT NULL DEFAULT '[]',
            total           INTEGER NOT NULL DEFAULT 0,
            status          TEXT NOT NULL DEFAULT 'pending',
            payment_id      INTEGER,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (bot_id)     REFERENCES bots(id)     ON DELETE CASCADE,
            FOREIGN KEY (user_id)    REFERENCES users(id)    ON DELETE CASCADE,
            FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE SET NULL
        );
    """),

    # --------------------------------------------------------
    ("channel_locks", """
        CREATE TABLE IF NOT EXISTS channel_locks (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id          INTEGER NOT NULL,                 -- which child bot enforces it
            channel_id      TEXT NOT NULL,                    -- @username or numeric id
            title           TEXT,
            is_required     INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE
        );
    """),

    # --------------------------------------------------------
    ("broadcasts", """
        CREATE TABLE IF NOT EXISTS broadcasts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_user_id  INTEGER NOT NULL,
            bot_id          INTEGER,                          -- null = all bots / mother bot
            target          TEXT NOT NULL DEFAULT 'all',      -- 'all'|'active'|'bot_users'
            content_json    TEXT NOT NULL DEFAULT '{}',       -- {type, text, media_url, buttons}
            status          TEXT NOT NULL DEFAULT 'queued',   -- queued|running|finished|failed
            total_targets   INTEGER NOT NULL DEFAULT 0,
            sent_count      INTEGER NOT NULL DEFAULT 0,
            failed_count    INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            finished_at     TEXT,
            FOREIGN KEY (sender_user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (bot_id)         REFERENCES bots(id)  ON DELETE CASCADE
        );
    """),

    # --------------------------------------------------------
    ("system_settings", """
        CREATE TABLE IF NOT EXISTS system_settings (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            key             TEXT NOT NULL UNIQUE,
            value           TEXT,
            updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """),
]


# Useful indexes
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_users_bale_user_id     ON users(bale_user_id);",
    "CREATE INDEX IF NOT EXISTS idx_bots_owner_id          ON bots(owner_id);",
    "CREATE INDEX IF NOT EXISTS idx_bots_status            ON bots(status);",
    "CREATE INDEX IF NOT EXISTS idx_subs_user_id           ON subscriptions(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_subs_status            ON subscriptions(status);",
    "CREATE INDEX IF NOT EXISTS idx_payments_user_id       ON payments(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_payments_status        ON payments(status);",
    "CREATE INDEX IF NOT EXISTS idx_wallet_tx_wallet_id    ON wallet_transactions(wallet_id);",
    "CREATE INDEX IF NOT EXISTS idx_products_bot           ON products(bot_id);",
    "CREATE INDEX IF NOT EXISTS idx_orders_bot             ON orders(bot_id);",
    "CREATE INDEX IF NOT EXISTS idx_orders_user            ON orders(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_channel_locks_bot      ON channel_locks(bot_id);",
]
