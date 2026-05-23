# ============================================================
# templates/builtin/support_pro.py
# ============================================================
# 🎫 ربات تیکت پشتیبانی حرفه‌ای
# ارسال تیکت، پیگیری، سوالات متداول
# ============================================================

from templates.template_base import BotTemplate


class SupportProTemplate(BotTemplate):
    key = "support_pro"
    name = "ربات تیکت پشتیبانی"
    description = "ثبت تیکت پشتیبانی، پیگیری وضعیت و سوالات متداول"
    icon = "🎫"
    version = "2.0.0"

    plan_specs = [
        {"duration": "monthly",   "name": "ماهانه",   "price": 150_000,
         "max_bots": 1, "max_users_per_bot": 5_000,  "max_monthly_messages": 20_000},
        {"duration": "quarterly", "name": "سه ماهه",  "price": 400_000,
         "max_bots": 1, "max_users_per_bot": 10_000, "max_monthly_messages": 60_000},
        {"duration": "biannual",  "name": "شش ماهه",  "price": 750_000,
         "max_bots": 2, "max_users_per_bot": 20_000, "max_monthly_messages": 150_000},
        {"duration": "yearly",    "name": "سالانه",   "price": 1_400_000,
         "max_bots": 5, "max_users_per_bot": 50_000, "max_monthly_messages": 300_000},
    ]

    def get_pages(self):
        return {
            "home": {
                "text": (
                    "🎫 <b>پشتیبانی</b>\n\n"
                    "سلام! چطور می‌تونم کمکتون کنم؟"
                ),
                "buttons": [
                    {"text": "📩 ثبت تیکت جدید", "type": "text_button",
                     "action": "run_flow", "target": "new_ticket", "row": 0},
                    {"text": "🔍 پیگیری تیکت", "type": "text_button",
                     "action": "run_flow", "target": "track_ticket", "row": 0},
                    {"text": "❓ سوالات متداول", "type": "text_button",
                     "action": "open_page", "target": "faq", "row": 1},
                    {"text": "📞 تماس مستقیم", "type": "text_button",
                     "action": "open_page", "target": "contact", "row": 1},
                ],
            },
            "faq": {
                "text": (
                    "❓ <b>سوالات متداول</b>\n\n"
                    "🔹 <b>چطور سفارشم رو پیگیری کنم؟</b>\n"
                    "از «🔍 پیگیری تیکت» استفاده کنید.\n\n"
                    "🔹 <b>ساعات پاسخگویی چه زمانی است؟</b>\n"
                    "شنبه تا پنجشنبه ۹ تا ۱۸\n\n"
                    "🔹 <b>چطور سفارشم رو کنسل کنم؟</b>\n"
                    "یک تیکت با عنوان «کنسلی» ثبت کنید.\n\n"
                    "🔹 <b>آیا مرجوعی امکان‌پذیر است؟</b>\n"
                    "بله، تا ۷ روز پس از دریافت."
                ),
                "buttons": [
                    {"text": "📩 ثبت تیکت", "type": "text_button",
                     "action": "run_flow", "target": "new_ticket"},
                    {"text": "🔙 بازگشت", "type": "text_button",
                     "action": "open_page", "target": "home"},
                ],
            },
            "contact": {
                "text": (
                    "📞 <b>تماس مستقیم</b>\n\n"
                    "📱 تلفن: 021-99998888\n"
                    "💬 تلگرام: @support_team\n"
                    "📧 ایمیل: support@example.com\n\n"
                    "⏰ شنبه تا پنجشنبه: ۹ تا ۱۸"
                ),
                "buttons": [
                    {"text": "🔙 بازگشت", "type": "text_button",
                     "action": "open_page", "target": "home"},
                ],
            },
        }

    def get_flows(self):
        return {
            "new_ticket": {
                "trigger": "📩 ثبت تیکت جدید",
                "steps": [
                    {"type": "send_message",
                     "text": "📩 <b>ثبت تیکت جدید</b>\n\nلطفاً مشکل خود را شرح دهید:"},
                    {"type": "ask_text", "var": "subject",
                     "prompt": "📌 عنوان مشکل (مثلاً: مشکل در ارسال):"},
                    {"type": "ask_text", "var": "description",
                     "prompt": "📝 توضیحات کامل مشکل:"},
                    {"type": "ask_text", "var": "order_code",
                     "prompt": "🔢 کد سفارش یا شناسه (اگر ندارید — بفرستید):"},
                    {"type": "save_variable", "var": "ticket_time", "value": "now"},
                    {"type": "send_message",
                     "text": (
                         "✅ <b>تیکت شما ثبت شد!</b>\n\n"
                         "📌 عنوان: {subject}\n\n"
                         "💬 تیم پشتیبانی به‌زودی پاسخ می‌دهد.\n"
                         "⏱ زمان متوسط پاسخ: ۲-۴ ساعت\n\n"
                         "💡 برای پیگیری از «🔍 پیگیری تیکت» استفاده کنید."
                     )},
                    {"type": "finish"},
                ],
            },
            "track_ticket": {
                "trigger": "🔍 پیگیری تیکت",
                "steps": [
                    {"type": "send_message",
                     "text": "🔍 <b>پیگیری تیکت</b>\n\nکد تیکت خود را وارد کنید:"},
                    {"type": "ask_text", "var": "ticket_code",
                     "prompt": "🔢 کد تیکت (مثلاً: TKT-456):"},
                    {"type": "send_message",
                     "text": (
                         "📋 <b>وضعیت تیکت</b>\n\n"
                         "🔢 کد: {ticket_code}\n"
                         "📌 وضعیت: در حال بررسی\n"
                         "👨‍💼 کارشناس: اختصاص داده شده\n\n"
                         "💡 به‌محض پاسخ، اطلاع‌رسانی می‌شوید."
                     )},
                    {"type": "finish"},
                ],
            },
        }


TEMPLATE = SupportProTemplate()
