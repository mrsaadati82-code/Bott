# ⚡ راهنمای سریع راه‌اندازی (5 دقیقه)

برای راهنمای کامل: `README_SETUP.md`

---

## 1️⃣ ساخت ربات مادر در بله
1. به https://ble.ir/botfather بروید
2. `/newbot` بفرستید
3. اسم و یوزرنیم بدهید
4. **توکن** را کپی کنید

## 2️⃣ تنظیم config.py
فایل `botbuilder/config.py` را باز کنید و این دو خط را پیدا و تغییر دهید:

```python
MOTHER_BOT_TOKEN = os.environ.get(
    "MOTHER_BOT_TOKEN",
    "123456789:abcdIuZmK5qNEm2A1BhUaAg7MPJv1O9KCcBQB2ro",  # ← توکن واقعی
)

SUPER_ADMIN_IDS = [
    int(x) for x in os.environ.get("SUPER_ADMIN_IDS", "12345678").split(",")
    if x.strip().isdigit()                                       # ← آی‌دی شما
]
```

> اگر آی‌دی خود را نمی‌دانید: ابتدا با `"0"` اجرا کنید، در ربات `/whoami` بزنید، عدد را کپی کنید و دوباره تنظیم کنید.

## 3️⃣ نصب وابستگی
**Pydroid 3:** منو ⋮ ← Pip ← `requests` ← Install  
**Termux / Linux:** `pip install requests`

## 4️⃣ تست سلامت
```bash
python health_check.py
```
باید همه ✅ سبز باشد.

## 5️⃣ اجرا
```bash
python main.py
```
لاگ موفقیت:
```
[INFO] Mother bot poller running.
[INFO] Engine ready. Press Ctrl+C to stop.
```

## 6️⃣ تست در بله
به ربات مادر این پیام‌ها را بفرستید:
1. `/start` → پیام خوش‌آمد + کیبورد
2. `/whoami` → آی‌دی و نقش شما
3. `/admin` → پنل ادمین با ۱۴ دکمه (اگر سوپرادمین هستید)
4. `🎁 ساخت ربات از Template` → ۴ Template آماده

✅ **اگر همه کار کرد، تبریک — سیستم آماده است!**

---

## 📚 منابع
- 📘 راهنمای کامل: `README_SETUP.md`
- 🐛 رفع اشکال: بخش 10 از README_SETUP.md
- 🎁 ساخت Template جدید: بخش 11 از README_SETUP.md
