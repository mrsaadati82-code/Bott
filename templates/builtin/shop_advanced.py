# ============================================================
# templates/builtin/shop_advanced.py
# ============================================================
# 🏪 ربات فروشگاهی پیشرفته
# شامل: دسته‌بندی محصولات، سبد خرید، ثبت سفارش،
# پیگیری، اطلاعات فروشگاه
# ============================================================

from templates.template_base import BotTemplate


class ShopAdvancedTemplate(BotTemplate):
    key = "shop_advanced"
    name = "ربات فروشگاهی پیشرفته"
    description = "دسته‌بندی محصولات، سبد خرید، ثبت سفارش، پیگیری مرسوله و اطلاعات فروشگاه"
    icon = "🏪"
    version = "2.0.0"

    plan_specs = [
        {"duration": "monthly",   "name": "ماهانه",   "price": 300_000,
         "max_bots": 1, "max_users_per_bot": 5_000,  "max_monthly_messages": 50_000},
        {"duration": "quarterly", "name": "سه ماهه",  "price": 800_000,
         "max_bots": 1, "max_users_per_bot": 15_000, "max_monthly_messages": 150_000},
        {"duration": "biannual",  "name": "شش ماهه",  "price": 1_500_000,
         "max_bots": 2, "max_users_per_bot": 30_000, "max_monthly_messages": 300_000},
        {"duration": "yearly",    "name": "سالانه",   "price": 2_800_000,
         "max_bots": 3, "max_users_per_bot": 50_000, "max_monthly_messages": 500_000},
    ]

    def get_pages(self):
        return {
            "home": {
                "text": (
                    "🏪 <b>به فروشگاه ما خوش آمدید!</b>\n\n"
                    "از منوی زیر انتخاب کنید:"
                ),
                "buttons": [
                    {"text": "📦 دسته‌بندی محصولات", "type": "text_button",
                     "action": "open_page", "target": "categories", "row": 0},
                    {"text": "🛒 ثبت سفارش", "type": "text_button",
                     "action": "run_flow", "target": "order", "row": 0},
                    {"text": "🔍 پیگیری سفارش", "type": "text_button",
                     "action": "run_flow", "target": "track_order", "row": 1},
                    {"text": "ℹ️ درباره فروشگاه", "type": "text_button",
                     "action": "open_page", "target": "about", "row": 1},
                    {"text": "📞 تماس با ما", "type": "text_button",
                     "action": "open_page", "target": "contact", "row": 2},
                ],
            },
            "categories": {
                "text": (
                    "📦 <b>دسته‌بندی محصولات</b>\n\n"
                    "یک دسته را انتخاب کنید:"
                ),
                "buttons": [
                    {"text": "👕 پوشاک", "type": "text_button",
                     "action": "open_page", "target": "cat_clothing", "row": 0},
                    {"text": "📱 لوازم الکترونیکی", "type": "text_button",
                     "action": "open_page", "target": "cat_electronics", "row": 0},
                    {"text": "🏠 لوازم خانگی", "type": "text_button",
                     "action": "open_page", "target": "cat_home", "row": 1},
                    {"text": "🍕 مواد غذایی", "type": "text_button",
                     "action": "open_page", "target": "cat_food", "row": 1},
                    {"text": "🔙 بازگشت", "type": "text_button",
                     "action": "open_page", "target": "home", "row": 2},
                ],
            },
            "cat_clothing": {
                "text": (
                    "👕 <b>پوشاک</b>\n\n"
                    "🔹 تیشرت مردانه — ۲۵۰,۰۰۰ تومان\n"
                    "🔹 شلوار جین — ۴۵۰,۰۰۰ تومان\n"
                    "🔹 مانتو زنانه — ۶۸۰,۰۰۰ تومان\n"
                    "🔹 کاپشن زمستانی — ۹۵۰,۰۰۰ تومان\n\n"
                    "💡 برای خرید «🛒 ثبت سفارش» بزنید"
                ),
                "buttons": [
                    {"text": "🛒 ثبت سفارش", "type": "text_button",
                     "action": "run_flow", "target": "order"},
                    {"text": "🔙 دسته‌بندی", "type": "text_button",
                     "action": "open_page", "target": "categories"},
                ],
            },
            "cat_electronics": {
                "text": (
                    "📱 <b>لوازم الکترونیکی</b>\n\n"
                    "🔹 هندزفری بلوتوثی — ۳۵۰,۰۰۰ تومان\n"
                    "🔹 پاوربانک ۲۰۰۰۰ — ۴۸۰,۰۰۰ تومان\n"
                    "🔹 قاب گوشت سفارشی — ۱۲۰,۰۰۰ تومان\n"
                    "🔹 کابل شارژ تایپ سی — ۸۵,۰۰۰ تومان\n\n"
                    "💡 برای خرید «🛒 ثبت سفارش» بزنید"
                ),
                "buttons": [
                    {"text": "🛒 ثبت سفارش", "type": "text_button",
                     "action": "run_flow", "target": "order"},
                    {"text": "🔙 دسته‌بندی", "type": "text_button",
                     "action": "open_page", "target": "categories"},
                ],
            },
            "cat_home": {
                "text": (
                    "🏠 <b>لوازم خانگی</b>\n\n"
                    "🔹 ست قاشق و چنگال — ۳۲۰,۰۰۰ تومان\n"
                    "🔹 لیوان سرامیکی (۶عددی) — ۲۸۰,۰۰۰ تومان\n"
                    "🔹 ماگ حرارتی — ۱۵۰,۰۰۰ تومان\n\n"
                    "💡 برای خرید «🛒 ثبت سفارش» بزنید"
                ),
                "buttons": [
                    {"text": "🛒 ثبت سفارش", "type": "text_button",
                     "action": "run_flow", "target": "order"},
                    {"text": "🔙 دسته‌بندی", "type": "text_button",
                     "action": "open_page", "target": "categories"},
                ],
            },
            "cat_food": {
                "text": (
                    "🍕 <b>مواد غذایی</b>\n\n"
                    "🔹 زعفران (۱ گرمی) — ۱۸۰,۰۰۰ تومان\n"
                    "🔹 گردو (۵۰۰ گرمی) — ۲۵۰,۰۰۰ تومان\n"
                    "🔹 پسته (۵۰۰ گرمی) — ۴۵۰,۰۰۰ تومان\n\n"
                    "💡 برای خرید «🛒 ثبت سفارش» بزنید"
                ),
                "buttons": [
                    {"text": "🛒 ثبت سفارش", "type": "text_button",
                     "action": "run_flow", "target": "order"},
                    {"text": "🔙 دسته‌بندی", "type": "text_button",
                     "action": "open_page", "target": "categories"},
                ],
            },
            "about": {
                "text": (
                    "ℹ️ <b>درباره فروشگاه</b>\n\n"
                    "🏪 فروشگاه ما از سال ۱۴۰۰ در خدمت شماست\n"
                    "📦 ارسال به سراسر کشور\n"
                    "🔄 امکان مرجوعی تا ۷ روز\n"
                    "✅ تضمین اصالت کالا\n\n"
                    "📍 آدرس: تهران، خیابان ولیعصر"
                ),
                "buttons": [
                    {"text": "🔙 بازگشت", "type": "text_button",
                     "action": "open_page", "target": "home"},
                ],
            },
            "contact": {
                "text": (
                    "📞 <b>تماس با ما</b>\n\n"
                    "📱 تلفن: 021-12345678\n"
                    "📱 موبایل: 0912-3456789\n"
                    "📧 ایمیل: info@myshop.com\n"
                    "💬 تلگرام: @myshop_support\n\n"
                    "⏰ ساعات پاسخگویی: ۹ تا ۲۱"
                ),
                "buttons": [
                    {"text": "🔙 بازگشت", "type": "text_button",
                     "action": "open_page", "target": "home"},
                ],
            },
        }

    def get_flows(self):
        return {
            "order": {
                "trigger": "🛒 ثبت سفارش",
                "steps": [
                    {"type": "send_message",
                     "text": "🛒 <b>ثبت سفارش جدید</b>\n\nلطفاً اطلاعات زیر را وارد کنید:"},
                    {"type": "ask_text", "var": "product",
                     "prompt": "📦 نام یا کد محصول مورد نظر را بنویسید:"},
                    {"type": "ask_number", "var": "quantity",
                     "prompt": "🔢 چند عدد می‌خواهید؟ (عدد وارد کنید)"},
                    {"type": "ask_text", "var": "address",
                     "prompt": "🏠 آدرس کامل ارسال:"},
                    {"type": "ask_phone", "var": "phone",
                     "prompt": "📱 شماره موبایل:"},
                    {"type": "ask_text", "var": "note",
                     "prompt": "📝 توضیحات اضافی (اگر ندارید — بفرستید):"},
                    {"type": "save_variable", "var": "order_time", "value": "now"},
                    {"type": "send_message",
                     "text": (
                         "✅ <b>سفارش شما ثبت شد!</b>\n\n"
                         "📦 محصول: {product}\n"
                         "🔢 تعداد: {quantity}\n"
                         "🏠 آدرس: {address}\n"
                         "📱 تلفن: {phone}\n\n"
                         "همکاران ما به‌زودی برای تأیید تماس خواهند گرفت 🙏"
                     )},
                    {"type": "finish"},
                ],
            },
            "track_order": {
                "trigger": "🔍 پیگیری سفارش",
                "steps": [
                    {"type": "send_message",
                     "text": "🔍 <b>پیگیری سفارش</b>\n\nکد پیگیری سفارش خود را وارد کنید:"},
                    {"type": "ask_text", "var": "tracking_code",
                     "prompt": "🔢 کد پیگیری (مثلاً: ORD-12345):"},
                    {"type": "send_message",
                     "text": (
                         "📦 <b>وضعیت سفارش</b>\n\n"
                         "کد: {tracking_code}\n"
                         "وضعیت: در حال پردازش\n\n"
                         "💡 برای اطلاعات بیشتر با پشتیبانی تماس بگیرید.\n"
                         "📞 شماره: 021-12345678"
                     )},
                    {"type": "finish"},
                ],
            },
        }


TEMPLATE = ShopAdvancedTemplate()
