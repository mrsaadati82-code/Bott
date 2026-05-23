# ============================================================
# templates/builtin/restaurant.py
# ============================================================
# 🍽 ربات رستوران و سفارش آنلاین
# منو غذا، سفارش میز/آنلاین، رزرو میز
# ============================================================

from templates.template_base import BotTemplate


class RestaurantTemplate(BotTemplate):
    key = "restaurant"
    name = "ربات رستوران و سفارش آنلاین"
    description = "منو غذا، ثبت سفارش، رزرو میز و اطلاعات رستوران"
    icon = "🍽"
    version = "2.0.0"

    plan_specs = [
        {"duration": "monthly",   "name": "ماهانه",   "price": 250_000,
         "max_bots": 1, "max_users_per_bot": 5_000,  "max_monthly_messages": 40_000},
        {"duration": "quarterly", "name": "سه ماهه",  "price": 650_000,
         "max_bots": 1, "max_users_per_bot": 12_000, "max_monthly_messages": 120_000},
        {"duration": "biannual",  "name": "شش ماهه",  "price": 1_200_000,
         "max_bots": 2, "max_users_per_bot": 25_000, "max_monthly_messages": 250_000},
        {"duration": "yearly",    "name": "سالانه",   "price": 2_200_000,
         "max_bots": 3, "max_users_per_bot": 50_000, "max_monthly_messages": 500_000},
    ]

    def get_pages(self):
        return {
            "home": {
                "text": (
                    "🍽 <b>رستوران ما</b>\n\n"
                    "به رستوران ما خوش آمدید! 👋\n\n"
                    "از منو انتخاب کنید:"
                ),
                "buttons": [
                    {"text": "📋 منو غذاها", "type": "text_button",
                     "action": "open_page", "target": "menu", "row": 0},
                    {"text": "🛒 سفارش آنلاین", "type": "text_button",
                     "action": "run_flow", "target": "order_food", "row": 0},
                    {"text": "🪑 رزرو میز", "type": "text_button",
                     "action": "run_flow", "target": "reserve_table", "row": 1},
                    {"text": "📍 آدرس و ساعات", "type": "text_button",
                     "action": "open_page", "target": "info", "row": 1},
                    {"text": "📞 تماس", "type": "text_button",
                     "action": "open_page", "target": "contact", "row": 2},
                ],
            },
            "menu": {
                "text": (
                    "📋 <b>منو غذاها</b>\n\n"
                    "🥗 <b>پیش‌غذا:</b>\n"
                    "  سالاد سزار — ۸۵,۰۰۰\n"
                    "  سوپ جو — ۶۵,۰۰۰\n\n"
                    "🥩 <b>غذای اصلی:</b>\n"
                    "  چلوکباب کوبیده — ۲۲۰,۰۰۰\n"
                    "  جوجه کباب — ۲۵۰,۰۰۰\n"
                    "  قرمه‌سبزی — ۱۸۰,۰۰۰\n"
                    "  باقالی‌پلو با ماهیچه — ۲۸۰,۰۰۰\n\n"
                    "🍰 <b>دسر:</b>\n"
                    "  بستنی خانگی — ۵۵,۰۰۰\n"
                    "  نوشابه — ۳۰,۰۰۰\n\n"
                    "💰 قیمت‌ها به تومان\n\n"
                    "💡 برای سفارش «🛒 سفارش آنلاین» بزنید"
                ),
                "buttons": [
                    {"text": "🛒 سفارش آنلاین", "type": "text_button",
                     "action": "run_flow", "target": "order_food"},
                    {"text": "🔙 بازگشت", "type": "text_button",
                     "action": "open_page", "target": "home"},
                ],
            },
            "info": {
                "text": (
                    "📍 <b>آدرس و ساعات کاری</b>\n\n"
                    "📍 آدرس: تهران، خیابان ولیعصر، پلاک ۱۲۳\n"
                    "🕐 ساعات کاری:\n"
                    "  شنبه تا پنجشنبه: ۱۱:۰۰ تا ۲۳:۰۰\n"
                    "  جمعه: ۱۲:۰۰ تا ۲۳:۰۰\n\n"
                    "🚗 پارکینگ رایگان\n"
                    "🏦 امکان پرداخت کارتی"
                ),
                "buttons": [
                    {"text": "🔙 بازگشت", "type": "text_button",
                     "action": "open_page", "target": "home"},
                ],
            },
            "contact": {
                "text": (
                    "📞 <b>تماس با ما</b>\n\n"
                    "📱 تلفن: 021-55551234\n"
                    "💬 تلگرام: @restaurant_support\n"
                    "📧 ایمیل: info@myrestaurant.com\n\n"
                    "⏰ پاسخگویی: ۱۱ تا ۲۳"
                ),
                "buttons": [
                    {"text": "🔙 بازگشت", "type": "text_button",
                     "action": "open_page", "target": "home"},
                ],
            },
        }

    def get_flows(self):
        return {
            "order_food": {
                "trigger": "🛒 سفارش آنلاین",
                "steps": [
                    {"type": "send_message",
                     "text": "🛒 <b>سفارش آنلاین</b>\n\nلطفاً اطلاعات سفارش را وارد کنید:"},
                    {"type": "ask_text", "var": "items",
                     "prompt": "🍽 لیست غذاها:\n\nمثال: ۲ کوبیده + ۱ جوجه + ۲ نوشابه"},
                    {"type": "ask_text", "var": "address",
                     "prompt": "🏠 آدرس دقیق ارسال:"},
                    {"type": "ask_phone", "var": "phone",
                     "prompt": "📱 شماره تماس:"},
                    {"type": "ask_text", "var": "note",
                     "prompt": "📝 توضیحات اضافی (سس اضافه، بدون پیاز و...):\nاگر ندارد — بفرستید"},
                    {"type": "save_variable", "var": "order_time", "value": "now"},
                    {"type": "send_message",
                     "text": (
                         "✅ <b>سفارش شما ثبت شد!</b>\n\n"
                         "🍽 {items}\n"
                         "🏠 {address}\n"
                         "📱 {phone}\n\n"
                         "⏱ حدود ۴۵-۶۰ دقیقه تحویل\n"
                         "💳 پرداخت در محل\n\n"
                         "با تشکر از انتخاب شما 🙏"
                     )},
                    {"type": "finish"},
                ],
            },
            "reserve_table": {
                "trigger": "🪑 رزرو میز",
                "steps": [
                    {"type": "send_message",
                     "text": "🪑 <b>رزرو میز</b>\n\nاطلاعات رزرو را وارد کنید:"},
                    {"type": "ask_text", "var": "name",
                     "prompt": "👤 نام شما:"},
                    {"type": "ask_number", "var": "guests",
                     "prompt": "👥 تعداد نفرات:"},
                    {"type": "ask_text", "var": "date",
                     "prompt": "📅 تاریخ:\nمثال: ۱۴۰۵/۰۳/۱۵"},
                    {"type": "ask_text", "var": "time",
                     "prompt": "🕐 ساعت:\nمثال: ۸ شب"},
                    {"type": "ask_phone", "var": "phone",
                     "prompt": "📱 شماره تماس:"},
                    {"type": "send_message",
                     "text": (
                         "✅ <b>رزرو ثبت شد!</b>\n\n"
                         "👤 {name}\n"
                         "👥 {guests} نفر\n"
                         "📅 {date} — {time}\n"
                         "📱 {phone}\n\n"
                         "💡 تأیید نهایی به موبایل ارسال می‌شود.\n"
                         "🍽 رستوران ما"
                     )},
                    {"type": "finish"},
                ],
            },
        }


TEMPLATE = RestaurantTemplate()
