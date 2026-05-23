# ============================================================
# admin_panel/admin_router.py
# ============================================================
# Defines the admin reply-keyboard exactly as listed in the
# project spec and provides helpers to detect "the user is
# currently in the admin panel".
# ============================================================

from core.keyboards import reply_keyboard


# Labels MUST exactly match the spec - they are used as routing keys.
BTN_USERS         = "👥 مدیریت کاربران"
BTN_BOTS          = "🤖 مدیریت ربات‌ها"
BTN_PLANS         = "📦 مدیریت پلن‌ها"
BTN_SUBS          = "🎟 مدیریت اشتراک‌ها"
BTN_PAYMENTS      = "💳 مدیریت پرداخت‌ها"
BTN_WALLETS       = "👛 مدیریت کیف پول"
BTN_GIFTS         = "🎁 مدیریت کد هدیه"
BTN_TEMPLATES     = "🧩 مدیریت Template"
BTN_MODULES       = "⚙️ مدیریت Module"
BTN_CHANNEL_LOCK  = "📣 مدیریت کانال اجباری"
BTN_BROADCAST     = "📢 مدیریت Broadcast"
BTN_STATS         = "📊 مشاهده آمار"
BTN_RESELLERS     = "🧑‍💼 مدیریت نمایندگان"
BTN_SETTINGS      = "🔧 تنظیمات سیستم"
BTN_BACK          = "🔙 بازگشت"


ADMIN_KEYBOARD = reply_keyboard([
    [BTN_USERS,         BTN_BOTS],
    [BTN_PLANS,         BTN_SUBS],
    [BTN_PAYMENTS,      BTN_WALLETS],
    [BTN_GIFTS,         BTN_TEMPLATES],
    [BTN_MODULES,       BTN_CHANNEL_LOCK],
    [BTN_BROADCAST,     BTN_STATS],
    [BTN_RESELLERS,     BTN_SETTINGS],
    [BTN_BACK],
])

ADMIN_LABELS = {
    BTN_USERS, BTN_BOTS, BTN_PLANS, BTN_SUBS, BTN_PAYMENTS, BTN_WALLETS,
    BTN_GIFTS, BTN_TEMPLATES, BTN_MODULES, BTN_CHANNEL_LOCK,
    BTN_BROADCAST, BTN_STATS, BTN_RESELLERS, BTN_SETTINGS, BTN_BACK,
}
