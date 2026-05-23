# ============================================================
# templates/builtin/medical_appointment.py
# ============================================================
# 🏥 ربات نوبت‌دهی پزشکی
# شامل: انتخاب پزشک، زمان نوبت، ثبت و پیگیری
# ============================================================

from templates.template_base import BotTemplate


class MedicalAppointmentTemplate(BotTemplate):
    key = "medical_appointment"
    name = "ربات نوبت‌دهی پزشکی"
    description = "انتخاب پزشک و تخصص، دریافت نوبت، پیگیری و اطلاع‌رسانی"
    icon = "🏥"
    version = "2.0.0"

    plan_specs = [
        {"duration": "monthly",   "name": "ماهانه",   "price": 350_000,
         "max_bots": 1, "max_users_per_bot": 3_000,  "max_monthly_messages": 30_000},
        {"duration": "quarterly", "name": "سه ماهه",  "price": 900_000,
         "max_bots": 1, "max_users_per_bot": 8_000,  "max_monthly_messages": 80_000},
        {"duration": "biannual",  "name": "شش ماهه",  "price": 1_700_000,
         "max_bots": 2, "max_users_per_bot": 15_000, "max_monthly_messages": 200_000},
        {"duration": "yearly",    "name": "سالانه",   "price": 3_200_000,
         "max_bots": 3, "max_users_per_bot": 30_000, "max_monthly_messages": 400_000},
    ]

    def get_pages(self):
        return {
            "home": {
                "text": (
                    "🏥 <b>مرکز درمانی ما</b>\n\n"
                    "به سامانه نوبت‌دهی خوش آمدید.\n"
                    "از منو انتخاب کنید:"
                ),
                "buttons": [
                    {"text": "📋 دریافت نوبت", "type": "text_button",
                     "action": "run_flow", "target": "book_appointment", "row": 0},
                    {"text": "👨‍⚕️ پزشکان و تخصص‌ها", "type": "text_button",
                     "action": "open_page", "target": "doctors", "row": 0},
                    {"text": "🔍 پیگیری نوبت", "type": "text_button",
                     "action": "run_flow", "target": "track_appointment", "row": 1},
                    {"text": "🕐 ساعات کاری", "type": "text_button",
                     "action": "open_page", "target": "hours", "row": 1},
                    {"text": "📞 تماس و آدرس", "type": "text_button",
                     "action": "open_page", "target": "contact", "row": 2},
                ],
            },
            "doctors": {
                "text": (
                    "👨‍⚕️ <b>پزشکان و تخصص‌ها</b>\n\n"
                    "🔹 دکتر محمدی — متخصص قلب\n"
                    "🔹 دکتر احمدی — پزشک عمومی\n"
                    "🔹 دکتر رضایی — متخصص پوست\n"
                    "🔹 دکتر حسینی — دندانپزشک\n"
                    "🔹 دکتر کریمی — متخصص اطفال\n"
                    "🔹 دکتر صادقی — چشم‌پزشک\n\n"
                    "💡 برای نوبت «📋 دریافت نوبت» بزنید"
                ),
                "buttons": [
                    {"text": "📋 دریافت نوبت", "type": "text_button",
                     "action": "run_flow", "target": "book_appointment"},
                    {"text": "🔙 بازگشت", "type": "text_button",
                     "action": "open_page", "target": "home"},
                ],
            },
            "hours": {
                "text": (
                    "🕐 <b>ساعات کاری</b>\n\n"
                    "📅 شنبه تا چهارشنبه: ۸:۰۰ تا ۲۰:۰۰\n"
                    "📅 پنجشنبه: ۸:۰۰ تا ۱۴:۰۰\n"
                    "📅 جمعه: تعطیل\n\n"
                    "📞 اورژانس: ۲۴ ساعته\n"
                    "📱 شماره: 021-87654321"
                ),
                "buttons": [
                    {"text": "🔙 بازگشت", "type": "text_button",
                     "action": "open_page", "target": "home"},
                ],
            },
            "contact": {
                "text": (
                    "📞 <b>اطلاعات تماس</b>\n\n"
                    "🏥 مرکز درمانی ما\n"
                    "📍 آدرس: تهران، خیابان آزادی\n"
                    "📱 تلفن: 021-87654321\n"
                    "🚑 اورژانس: 115\n"
                    "💬 تلگرام: @clinic_support\n\n"
                    "⏰ پاسخگویی: ۸ تا ۲۰"
                ),
                "buttons": [
                    {"text": "🔙 بازگشت", "type": "text_button",
                     "action": "open_page", "target": "home"},
                ],
            },
        }

    def get_flows(self):
        return {
            "book_appointment": {
                "trigger": "📋 دریافت نوبت",
                "steps": [
                    {"type": "send_message",
                     "text": "📋 <b>دریافت نوبت</b>\n\nاطلاعات خود را وارد کنید:"},
                    {"type": "ask_text", "var": "fullname",
                     "prompt": "👤 نام و نام خانوادگی:"},
                    {"type": "ask_phone", "var": "phone",
                     "prompt": "📱 شماره موبایل:"},
                    {"type": "ask_text", "var": "doctor",
                     "prompt": "👨‍⚕️ نام پزشک مورد نظر:\n\nمثال: دکتر محمدی"},
                    {"type": "ask_text", "var": "date",
                     "prompt": "📅 تاریخ دلخواه:\n\nمثال: ۱۴۰۵/۰۳/۱۵"},
                    {"type": "ask_text", "var": "time_pref",
                     "prompt": "🕐 ساعت ترجیحی:\n\nمثال: ۱۰ صبح، ۴ بعدازظهر"},
                    {"type": "save_variable", "var": "booked_at", "value": "now"},
                    {"type": "send_message",
                     "text": (
                         "✅ <b>درخواست نوبت ثبت شد!</b>\n\n"
                         "👤 {fullname}\n"
                         "📱 {phone}\n"
                         "👨‍⚕️ {doctor}\n"
                         "📅 {date} — {time_pref}\n\n"
                         "📱 نتیجه تأیید به شماره موبایل شما ارسال می‌شود.\n\n"
                         "🏥 مرکز درمانی ما"
                     )},
                    {"type": "finish"},
                ],
            },
            "track_appointment": {
                "trigger": "🔍 پیگیری نوبت",
                "steps": [
                    {"type": "send_message",
                     "text": "🔍 <b>پیگیری نوبت</b>\n\nکد پیگیری خود را وارد کنید:"},
                    {"type": "ask_text", "var": "code",
                     "prompt": "🔢 کد پیگیری (مثلاً: APT-123):"},
                    {"type": "send_message",
                     "text": (
                         "📋 <b>وضعیت نوبت</b>\n\n"
                         "🔢 کد: {code}\n"
                         "📌 وضعیت: در حال بررسی\n\n"
                         "💡 نتیجه نهایی به موبایل شما پیامک می‌شود.\n"
                         "📞 تماس: 021-87654321"
                     )},
                    {"type": "finish"},
                ],
            },
        }


TEMPLATE = MedicalAppointmentTemplate()
