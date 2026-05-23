# 📚 راهنمای کامل راه‌اندازی و آموزش
## Bot Builder SaaS برای پیام‌رسان بله

این راهنما شما را از صفر تا یک ربات‌ساز کامل در حال اجرا می‌برد.

---

## 📌 فهرست
1. [پیش‌نیازها](#1-پیش‌نیازها)
2. [ساخت ربات مادر در بله](#2-ساخت-ربات-مادر-در-بله)
3. [گرفتن شناسه عددی خودتان](#3-گرفتن-شناسه-عددی-خودتان)
4. [نصب روی Pydroid 3 (اندروید)](#4-نصب-روی-pydroid-3-اندروید)
5. [نصب روی Termux (اندروید پیشرفته)](#5-نصب-روی-termux-اندروید-پیشرفته)
6. [نصب روی Linux/VPS](#6-نصب-روی-linuxvps)
7. [اولین اجرا و بررسی سلامت](#7-اولین-اجرا-و-بررسی-سلامت)
8. [تست گام‌به‌گام همه قابلیت‌ها](#8-تست-گام‌به‌گام-همه-قابلیت‌ها)
9. [همه دستورات و دکمه‌ها](#9-همه-دستورات-و-دکمه‌ها)
10. [رفع اشکال متداول](#10-رفع-اشکال-متداول)
11. [اضافه کردن Template جدید](#11-اضافه-کردن-template-جدید)
12. [پشتیبان‌گیری از داده‌ها](#12-پشتیبان‌گیری-از-داده‌ها)

---

## 1. پیش‌نیازها

| مورد | نسخه/مشخصات |
|---|---|
| Python | ≥ 3.7 (پیشنهاد 3.9 یا بالاتر) |
| اینترنت | دائمی برای polling به سرور بله |
| فضای ذخیره | حداقل 50MB برای کد + دیتابیس |
| کتابخانه | فقط `requests` |

---

## 2. ساخت ربات مادر در بله

«ربات مادر» همان رباتی است که کاربران از طریق آن وارد پنل می‌شوند و ربات‌های خودشان را می‌سازند.

### مراحل:
1. در بله به این آدرس بروید: **https://ble.ir/botfather**
2. روی **/start** بزنید
3. دستور `/newbot` را بفرستید
4. اسم ربات را وارد کنید (مثلاً: "ربات‌ساز من")
5. یوزرنیم ربات را وارد کنید (مثلاً: `mybotbuilder_bot` — باید به `_bot` ختم شود)
6. BotFather یک **توکن** به شما می‌دهد، شبیه:
   ```
   123456789:abcdIuZmK5qNEm2A1BhUaAg7MPJv1O9KCcBQB2ro
   ```
7. ✏️ **این توکن را یک جای امن کپی کنید** — در مرحله 7 لازم می‌شود.

> 💡 برای ربات‌های فرزند (که کاربران شما می‌سازند) هم همین مراحل تکرار می‌شود.

---

## 3. گرفتن شناسه عددی خودتان

برای سوپرادمین شدن، نیاز به **`user_id` عددی** خود در بله دارید.

### راه آسان (با خود ربات‌تان):
1. ربات مادر را اجرا کنید (مرحله 7).
2. در بله به ربات مادر `/whoami` بفرستید.
3. پاسخ شامل عدد `user_id` شماست — کپی کنید.
4. آن را در `config.py` در لیست `SUPER_ADMIN_IDS` بگذارید و ربات را ری‌استارت کنید.

### راه جایگزین:
- در بله ربات `@userinfobot` را پیدا کنید (اگر وجود داشت).
- یا با هر روش دیگری شناسه عددی خود را پیدا کنید.

---

## 4. نصب روی Pydroid 3 (اندروید)

ساده‌ترین روش برای راه‌اندازی روی گوشی بدون دسکتاپ.

### مرحله ۱: نصب اپ
1. **Pydroid 3** را از Google Play / Aurora Store / Bazaar نصب کنید.
2. اپ را باز کنید.

### مرحله ۲: نصب کتابخانه `requests`
1. در Pydroid 3 منوی ⋮ بالا سمت چپ ← **Pip**
2. در فیلد جستجو بنویسید: `requests` و **Install** بزنید.
3. صبر کنید تا نصب کامل شود (پایین صفحه «Success» می‌نویسد).

### مرحله ۳: انتقال پوشه پروژه
1. کل پوشه `botbuilder/` را با کابل USB یا فضای ابری به گوشی منتقل کنید.
2. مسیر پیشنهادی: `Internal Storage/botbuilder/`

### مرحله ۴: تنظیم توکن و ادمین
1. در Pydroid 3 ← منوی ⋮ ← **Open** ← به مسیر `botbuilder/config.py` بروید.
2. این دو خط را پیدا و ویرایش کنید:
   ```python
   MOTHER_BOT_TOKEN = os.environ.get(
       "MOTHER_BOT_TOKEN",
       "123456789:abcdIuZmK5qNEm2A1BhUaAg7MPJv1O9KCcBQB2ro",  # ← توکن واقعی
   )

   SUPER_ADMIN_IDS = [
       int(x) for x in os.environ.get("SUPER_ADMIN_IDS", "12345678").split(",")
       if x.strip().isdigit()
   ]
   ```
3. ذخیره کنید (Ctrl+S یا منو ← Save).

### مرحله ۵: اجرای health_check
1. در Pydroid 3 فایل `health_check.py` را باز کنید.
2. روی دکمه ▶️ بزنید.
3. باید همه موارد ✅ سبز باشند.

### مرحله ۶: اجرای اصلی
1. فایل `main.py` را باز کنید.
2. روی ▶️ بزنید.
3. در ترمینال پایین باید ببینید:
   ```
   Booting BaleBotBuilder v0.1.0 ...
   Database initialized.
   Templates: ['shop_basic', 'survey_basic', ...]
   Mother bot poller running.
   Engine ready. Press Ctrl+C to stop.
   ```
4. ✅ ربات شما زنده است! بروید به مرحله 7.

### نکات مهم برای Pydroid 3:
- 🔋 **همیشه شارژر وصل باشد** هنگام اجرا — اپ در پس‌زمینه می‌رود.
- 📱 در تنظیمات اندروید، Pydroid 3 را از «Battery Optimization» معاف کنید.
- 🔇 «Don't keep activities» در Developer Options را خاموش کنید.

---

## 5. نصب روی Termux (اندروید پیشرفته)

اگر می‌خواهید ربات در پس‌زمینه بدون اپ باز اجرا شود.

### مرحله ۱: نصب Termux
- از F-Droid یا GitHub (نه از Play Store، آن نسخه قدیمی است).

### مرحله ۲: نصب پایتون
```bash
pkg update -y && pkg upgrade -y
pkg install python git -y
pip install requests
```

### مرحله ۳: انتقال پروژه
```bash
# اگر کد روی GitHub خصوصی است:
git clone https://github.com/...

# یا اگر در حافظه گوشی است:
termux-setup-storage    # فقط یک بار
cp -r /sdcard/botbuilder ~/
cd ~/botbuilder
```

### مرحله ۴: تنظیم متغیرها (به جای ویرایش config.py)
```bash
export MOTHER_BOT_TOKEN="123456789:abcdIuZmK5qNEm2A..."
export SUPER_ADMIN_IDS="12345678"
```
برای دائمی شدن، در `~/.bashrc` بگذارید.

### مرحله ۵: تست و اجرا
```bash
python health_check.py
python main.py
```

### مرحله ۶: اجرا در پس‌زمینه (نگه‌دارنده)
```bash
# با nohup
nohup python main.py > bot.log 2>&1 &

# یا با screen (پیشنهادی)
pkg install tmux -y
tmux new -s bot
python main.py
# Ctrl+B سپس D برای detach
# بازگشت: tmux attach -t bot
```

---

## 6. نصب روی Linux/VPS

### مرحله ۱
```bash
sudo apt update && sudo apt install python3 python3-pip git -y
git clone <your-repo>    # یا rsync پوشه
cd botbuilder
pip3 install -r requirements.txt
```

### مرحله ۲: تنظیمات
```bash
cp config.py config.py.bak
# سپس config.py را ویرایش کنید یا متغیرها را export کنید
```

### مرحله ۳: اجرا با systemd (پیشنهادی)
فایل `/etc/systemd/system/botbuilder.service`:
```ini
[Unit]
Description=Bale Bot Builder SaaS
After=network.target

[Service]
Type=simple
WorkingDirectory=/root/botbuilder
Environment="MOTHER_BOT_TOKEN=123456789:abc..."
Environment="SUPER_ADMIN_IDS=12345678"
ExecStart=/usr/bin/python3 /root/botbuilder/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable botbuilder
sudo systemctl start botbuilder
sudo systemctl status botbuilder
sudo journalctl -u botbuilder -f
```

---

## 7. اولین اجرا و بررسی سلامت

### چک‌لیست:

#### ✅ مرحله A: تست خودکار
```bash
python health_check.py
```
انتظار: تمام موارد ✅ سبز. اگر چیزی قرمز است:
- 📦 وابستگی‌ها → `pip install requests`
- ⚙️ توکن/ادمین → `config.py` را ویرایش کنید
- 💾 دیتابیس → پوشه `data/` نوشتنی است؟

#### ✅ مرحله B: اجرای ربات
```bash
python main.py
```
لاگ موفقیت:
```
[INFO] Booting BaleBotBuilder v0.1.0 ...
[INFO] Database initialized.
[INFO] Templates: ['business_card', 'shop_basic', 'support_ticket', 'survey_basic']
[INFO] Admin + user panel handlers registered.
[INFO] Broadcast worker started.
[INFO] Mother bot authenticated as @yourbot (id=12345)
[INFO] Mother bot poller running.
[INFO] Engine ready. Press Ctrl+C to stop.
```

#### ✅ مرحله C: تست ربات در بله
1. به ربات مادر `/start` بفرستید → باید پاسخ خوش‌آمد + کیبورد ببینید.
2. `/ping` بفرستید → باید `pong ✅` بگیرید.
3. `/whoami` بفرستید → آی‌دی + نقش شما را نشان می‌دهد.

اگر این سه کار کرد، ✅ ربات سالم است.

---

## 8. تست گام‌به‌گام همه قابلیت‌ها

این بخش مهم است — هر قابلیت را دقیقاً تست کنید.

### 🧪 تست ۱: نقش سوپرادمین
**هدف:** اطمینان از اینکه شما به پنل ادمین دسترسی دارید.

1. `/whoami` بفرستید.
2. باید بنویسد: `🎭 role: super_admin`
3. `/admin` بفرستید.
4. باید کیبورد پنل ادمین با ۱۴ دکمه نمایش داده شود.

❌ اگر `role: user` بود → `SUPER_ADMIN_IDS` در `config.py` صحیح نیست. آی‌دی خود را با `/whoami` ببینید و در config بگذارید، سپس ربات را ری‌استارت کنید.

---

### 🧪 تست ۲: کیف پول و کد هدیه
**هدف:** تست کامل سیستم مالی.

1. در پنل ادمین «🎁 مدیریت کد هدیه» را بزنید.
2. دستور بدهید: `/newgift 50000 1`
3. کدی مثل `ABCD1234XY` دریافت می‌کنید.
4. حالا روی منوی اصلی «💰 کیف پول» را بزنید → موجودی شما `0` است.
5. دستور بدهید: `/gift ABCD1234XY`
6. باید بنویسد «کد با موفقیت اعمال شد ✅».
7. دوباره «💰 کیف پول» بزنید → موجودی `50,000 ریال` شد.

✅ اگر کار کرد، تراکنش‌ها هم در همان صفحه قابل دیدن است.

---

### 🧪 تست ۳: ساخت پلن و خرید اشتراک (با کارت‌به‌کارت)
**هدف:** تست کامل چرخه پرداخت کارت‌به‌کارت.

1. در پنل ادمین «📦 مدیریت پلن‌ها» را بزنید.
2. می‌بینید پلن‌های Templateها قبلاً ساخته شده‌اند (17 پلن).
3. دستور بدهید: `/setprice 2 50000` (شناسه پلن را از لیست بگیرید).
4. حالا کارت‌به‌کارت را تنظیم کنید:
   ```
   /set support_contact @your_username
   ```
5. اطلاعات کارت را در system_settings بگذارید (در فاز بعدی ابزارش اضافه می‌شود؛ فعلاً مستقیماً در DB):
   - فعلاً پیش‌فرض کار می‌کند.
6. به منوی اصلی برگردید (دکمه «🔙 بازگشت»).
7. «📦 پلن‌ها» را بزنید → لیست پلن‌های قابل خرید.
8. دستور بدهید: `/buy 2 card_to_card`
9. پیام «🧾 پرداخت #N ثبت شد» می‌بینید.
10. حالا فرض کنید واریز کردید: `/receipt N 123456` (N شناسه پرداخت، 123456 شماره پیگیری).
11. به پنل ادمین برگردید → «💳 مدیریت پرداخت‌ها» را بزنید.
12. دکمه‌های ✅ تایید / ❌ رد را می‌بینید.
13. روی ✅ بزنید.
14. اشتراک خودکار فعال می‌شود. در «🎟 مدیریت اشتراک‌ها» تأیید کنید.

---

### 🧪 تست ۴: ساخت ربات فرزند از Template (مهم‌ترین تست!)
**هدف:** تست سناریوی اصلی پلتفرم.

#### پیش‌نیاز:
- یک ربات دیگر در @botfather بسازید (مثلاً `my_shop_bot`) و توکنش را کپی کنید.

#### مراحل:
1. در ربات مادر «🎁 ساخت ربات از Template» را بزنید.
2. لیست ۴ Template را می‌بینید با قیمت‌ها.
3. روی «🛍 ربات فروشگاه ساده» بزنید.
4. ۴ پلن قیمت را می‌بینید (40k، 110k، 200k، 360k).
5. روی «خرید: ماهانه» بزنید.
6. روش پرداخت انتخاب کنید (مثلاً کارت‌به‌کارت).
7. پیام شامل شماره کارت + شناسه پرداخت می‌آید.
8. `/receipt <ID> <tracking>` بفرستید.
9. به پنل ادمین برگردید → پرداخت را تایید کنید.
10. حالا توکن ربات `my_shop_bot` را کپی کنید و در همان چت پیست کنید.
11. سیستم باید:
    - ربات را در دیتابیس ثبت کند
    - ۴ صفحه (home, products, contact, about) را روی آن بسازد
    - ۱ Flow «order» را بسازد
    - poller ربات فرزند را شروع کند
12. پیام «✅ ربات @my_shop_bot با موفقیت اضافه شد. 🎁 Template «🛍 ربات فروشگاه ساده» روی آن اعمال شد.» می‌بینید.

#### تست ربات فرزند:
13. به ربات `my_shop_bot` در بله بروید (یعنی به ربات فرزند).
14. `/start` بفرستید.
15. باید صفحه «home» با ۴ دکمه ببینید:
    - 📦 محصولات
    - 🛒 سفارش جدید
    - 📞 تماس
    - ℹ️ درباره ما
16. روی «📦 محصولات» بزنید → صفحه محصولات با دکمه «🔙 بازگشت».
17. روی «🛒 سفارش جدید» بزنید → Flow شروع می‌شود:
    - نام محصول؟ → پاسخ بدهید
    - تعداد؟ → عدد بدهید
    - آدرس؟ → آدرس بدهید
    - تلفن؟ → شماره بدهید
    - پیام تایید با خلاصه سفارش می‌آید

🎉 ✅ یک ربات فروشگاه کامل بدون یک خط کد!

---

### 🧪 تست ۵: ساخت ربات خالی + طراحی دستی
**هدف:** تست Page Builder و Flow Builder دستی.

1. ربات سوم را در @botfather بسازید.
2. در ربات مادر «🤖 ساخت ربات» را بزنید.
3. توکن بفرستید → ربات اضافه می‌شود (بدون template، خالی).
4. «🗂 ربات‌های من» را بزنید → روی ربات جدید کلیک کنید.
5. داشبورد را می‌بینید.
6. «📄 مدیریت صفحات» → «➕ صفحه جدید» → اسم بگذارید: `home`
7. «🌊 مدیریت Flow» → «📥 وارد کردن JSON» → این JSON را بفرستید:
   ```json
   {"name":"hi","trigger":"/hi","steps":[
     {"type":"send_message","text":"سلام {first_name}!"},
     {"type":"ask_text","var":"hobby","prompt":"سرگرمی موردعلاقه‌ات؟"},
     {"type":"send_message","text":"چقدر جالب! {hobby} هم خوبه."},
     {"type":"finish"}
   ]}
   ```
8. به ربات فرزند بروید و `/hi` بفرستید → Flow شروع می‌شود.

---

### 🧪 تست ۶: کانال اجباری
**هدف:** اطمینان از قفل کانال.

#### پیش‌نیاز:
- یک کانال در بله بسازید (مثلاً `@mytest_ch`) و ربات فرزند را در آن کانال **ادمین** کنید.

#### مراحل:
1. در داشبورد ربات فرزند «🔒 کانال اجباری» → «➕ افزودن کانال» → بفرستید: `@mytest_ch`
2. حالا با حساب دیگری (یا با یک دوست) به ربات فرزند `/start` بفرستید.
3. اگر کاربر عضو کانال نباشد، پیام «برای استفاده، در کانال زیر عضو شوید» می‌بیند.
4. کاربر عضو می‌شود، دکمه «✅ بررسی عضویت» را می‌زند.
5. اگر تایید شد، می‌تواند ادامه دهد.

---

### 🧪 تست ۷: Broadcast
**هدف:** تست ارسال انبوه.

1. در پنل ادمین «📢 مدیریت Broadcast» را بزنید.
2. دستور بدهید: `/broadcast all | سلام! این یک پیام آزمایشی است.`
3. پیام «✅ Broadcast #N در صف قرار گرفت» می‌آید.
4. در پشت صحنه، worker شروع به ارسال به همه کاربران می‌کند.
5. در لاگ ربات می‌بینید: `broadcast 1 done: sent=X failed=0`

---

### 🧪 تست ۸: نمایندگی و کد دعوت
**هدف:** تست سیستم Referral.

1. در پنل سوپرادمین: `/makereseller 12345678` (آی‌دی یک کاربر دیگر).
2. آن کاربر به ربات می‌آید و `/reseller` می‌زند.
3. کد دعوتش را می‌بیند: `R<آی‌دی_خودش>`
4. نفر سوم با لینک `/start R<id>` وارد می‌شود.
5. وقتی نفر سوم خرید کند، 10% به کیف پول نماینده اضافه می‌شود.
6. تغییر درصد: `/commission 15`

---

### 🧪 تست ۹: آمار سیستم
1. در پنل ادمین «📊 مشاهده آمار» را بزنید.
2. می‌بینید:
   - 👥 تعداد کاربران
   - 🤖 ربات‌های فعال
   - 💳 تعداد تراکنش‌ها
   - 💰 درآمد کل

---

### 🧪 تست ۱۰: مدیریت Templateها (ویرایش قیمت)
1. `/templates` بفرستید (یا «🧩 مدیریت Template» در پنل).
2. لیست ۴ Template را می‌بینید.
3. روی یکی کلیک کنید (مثلاً 🛍 شاپ).
4. ۴ پلن را می‌بینید با دکمه «✏️ قیمت».
5. روی «✏️ ماهانه - قیمت» بزنید → عدد جدید بفرستید مثلاً `150000`.
6. ✅ قیمت ذخیره شد و در همه جا اعمال می‌شود.
7. حالا حتی اگر ربات را ری‌استارت کنید، قیمت دستی شما حفظ می‌شود.

---

## 9. همه دستورات و دکمه‌ها

### 👤 کاربر عادی
| دستور / دکمه | عملکرد |
|---|---|
| `/start` | شروع + ثبت معرف اگر `/start Rxxx` |
| `🤖 ساخت ربات` | ربات خالی با توکن جدید |
| `🎁 ساخت ربات از Template` | انتخاب Template آماخرید |
| `🗂 ربات‌های من` | لیست + مدیریت ربات‌های فرزند |
| `💰 کیف پول` | موجودی + ۵ تراکنش اخیر |
| `📦 پلن‌ها` | لیست پلن‌های فعال |
| `🎁 ثبت کد هدیه` | راهنمای ریدیم |
| `/gift <code>` | ریدیم کد هدیه |
| `/buy <plan_id> <method>` | شروع خرید (method: bale | online | card_to_card) |
| `/receipt <pid> <track>` | ارسال رسید کارت‌به‌کارت |
| `🎯 دعوت دوستان` | کد دعوت برای referral |
| `📞 پشتیبانی` | اطلاعات تماس |
| `❓ راهنما` | راهنمای کوتاه |
| `/whoami` | اطلاعات و نقش |
| `/cancel` | لغو هر عملیات FSM در جریان |
| `/ping` | تست زنده بودن |

### 🛠 ادمین (پس از `/admin`)
| دکمه / دستور | عملکرد |
|---|---|
| `👥 مدیریت کاربران` | لیست ۱۵ کاربر اخیر |
| `/user <bale_id>` | جزییات یک کاربر + شارژ/کسر/بلاک |
| `🤖 مدیریت ربات‌ها` | لیست ربات‌های فرزند |
| `📦 مدیریت پلن‌ها` | لیست پلن‌ها |
| `/setprice <plan_id> <price>` | تغییر قیمت |
| `/addplan` | ساخت پلن جدید (FSM) |
| `🎟 مدیریت اشتراک‌ها` | اشتراک‌های اخیر |
| `💳 مدیریت پرداخت‌ها` | پرداخت‌های pending + تایید/رد |
| `👛 مدیریت کیف پول` | برترین کیف پول‌ها |
| `🎁 مدیریت کد هدیه` | لیست + `/newgift <amount> [max_uses]` |
| `🧩 مدیریت Template` (یا `/templates`) | پنل کامل templates + قیمت |
| `⚙️ مدیریت Module` | لیست ماژول‌های نصب‌شده |
| `📣 مدیریت کانال اجباری` | لیست همه قفل‌ها در سیستم |
| `📢 مدیریت Broadcast` | راهنما + `/broadcast` |
| `/broadcast <all\|active> \| <متن>` | ارسال انبوه |
| `📊 مشاهده آمار` | آمار کلی |
| `🧑‍💼 مدیریت نمایندگان` | لیست + `/makereseller` + `/commission` |
| `🔧 تنظیمات سیستم` | لیست + `/set <key> <value>` |

### 👑 سوپرادمین (اضافه بر ادمین)
| دستور | عملکرد |
|---|---|
| `/makeadmin <bale_id>` | ارتقا به ادمین |
| `/makereseller <bale_id>` | ارتقا به نماینده |
| `/unreseller <bale_id>` | حذف نقش نمایندگی |
| `/commission <percent>` | تنظیم درصد پورسانت |
| `/gateways` | لیست درگاه‌ها |
| `/gateway <key> <on\|off>` | فعال/غیرفعال درگاه |
| `/revenue` | درآمد کل + آمار |
| `/set <key> <value>` | تنظیم system_settings |
| `/templates` | پنل Template ها |

### 🧑‍💼 نماینده
| دستور | عملکرد |
|---|---|
| `/reseller` | پنل نمایندگی + کد دعوت |
| `/referrals` | لیست دعوت‌شدگان |

---

## 10. رفع اشکال متداول

### ❌ خطا: `MOTHER_BOT_TOKEN is not configured`
**علت:** توکن در `config.py` تنظیم نشده.
**حل:** `config.py` را باز کنید و توکن واقعی @botfather را در `MOTHER_BOT_TOKEN` بگذارید.

### ❌ خطا: `Bale API error 401: Unauthorized`
**علت:** توکن اشتباه است یا ربات حذف شده.
**حل:** توکن را در @botfather دوباره بگیرید (Revoke + New).

### ❌ خطا: `requests` نصب نیست
**حل:** 
- Pydroid 3 → منو ⋮ → Pip → install `requests`
- Termux → `pip install requests`

### ❌ ربات `/start` می‌فرستم ولی جواب نمی‌دهد
**علت:** poller شروع نشده.
**حل:** 
- لاگ ربات را چک کنید — باید «Mother bot poller running» نوشته باشد.
- اگر «Mother bot token check failed» می‌بینید، توکن اشتباه است.
- اگر هیچ لاگی نمی‌بینید، ربات اصلاً اجرا نشده.

### ❌ `/admin` به من می‌گوید «دسترسی ندارید»
**علت:** آی‌دی شما در `SUPER_ADMIN_IDS` نیست.
**حل:**
1. `/whoami` بفرستید → عدد `user_id` را ببینید.
2. در `config.py` بگذارید:
   ```python
   SUPER_ADMIN_IDS = [int(x) for x in os.environ.get("SUPER_ADMIN_IDS", "YOUR_ID").split(",") if x.strip().isdigit()]
   ```
   یا متغیر محیطی: `export SUPER_ADMIN_IDS="12345678"`
3. ربات را ری‌استارت کنید.

### ❌ ربات فرزند جواب نمی‌دهد
**علت:** poller ربات فرزند اجرا نشده.
**حل:**
- در لاگ ببینید: `Child bot started: id=N @username`
- اگر `Child bot N token check failed` می‌بینید → توکن ربات فرزند نامعتبر است.
- ربات را در «🗂 ربات‌های من» → دکمه «⏸ توقف/شروع» reset کنید.

### ❌ کانال اجباری همیشه می‌گوید «عضو نیستید»
**علت:** ربات فرزند در آن کانال **ادمین** نیست.
**حل:** ربات را به کانال اضافه کنید و دسترسی «ادمین» (با حق خواندن اعضا) بدهید.

### ❌ پرداخت داخلی بله کار نمی‌کند
**علت:** provider_token کیف‌پول تنظیم نشده.
**حل:** 
- در @botfather به ربات بروید → Payments → یک provider اضافه کنید.
- برای تست، از توکن سندباکس استفاده کنید: `WALLET-TEST-1111111111111111`

### ❌ بعد از ری‌استارت، آپدیت‌های قبلی همه دوباره اجرا می‌شوند
**علت:** `last_update_id` ذخیره نشده.
**حل:** این نباید رخ دهد — هر poller `last_update_id` را در DB ذخیره می‌کند. اگر می‌بینید، شاید پوشه `data/` پاک شده.

### ❌ Pydroid 3 ربات را پس از چند دقیقه می‌بندد
**علت:** اندروید فرآیند را kill می‌کند.
**حل:**
- شارژر وصل باشد.
- Battery Optimization برای Pydroid 3 خاموش.
- در تنظیمات Pydroid 3 ← «Keep scre
en on» را فعال کنید.

### ❌ خطای `OperationalError: database is locked`
**علت:** دو instance همزمان از ربات اجرا می‌شوند.
**حل:** فقط یک نسخه را اجرا کنید. process های قدیمی را ببندید.

---

## 11. اضافه کردن Template جدید (آموزش گام به گام)

این یکی از قدرتمندترین قابلیت‌های سیستم است. **هرگز هسته یا ربات مادر را لمس نمی‌کنید.**

### مرحله ۱: فایل جدید بسازید
مسیر: `botbuilder/templates/builtin/my_template.py`

### مرحله ۲: محتوا بنویسید
```python
from templates.template_base import BotTemplate


class MyAwesomeTemplate(BotTemplate):
    # متادیتای پایه
    key         = "awesome_bot"          # کلید یکتا (انگلیسی، بدون فاصله)
    name        = "ربات شگفت‌انگیز"
    description = "این ربات کارهای شگفت‌انگیز انجام می‌دهد"
    icon        = "✨"
    version     = "1.0.0"

    # پلن‌های اشتراک اختصاصی این Template
    plan_specs = [
        {
            "duration": "monthly",
            "name": "ماهانه",
            "price": 100_000,              # ریال
            "max_bots": 1,
            "max_users_per_bot": 2_000,
            "max_monthly_messages": 15_000,
        },
        {
            "duration": "quarterly",
            "name": "سه ماهه",
            "price": 270_000,
            "max_bots": 1,
            "max_users_per_bot": 5_000,
            "max_monthly_messages": 50_000,
        },
        {
            "duration": "yearly",
            "name": "سالانه",
            "price": 900_000,
            "max_bots": 3,
            "max_users_per_bot": 20_000,
            "max_monthly_messages": 200_000,
        },
    ]

    # صفحات پیش‌فرض ربات
    def get_pages(self):
        return {
            "home": {
                "text": "✨ به ربات شگفت‌انگیز خوش آمدید!",
                "buttons": [
                    {"text": "🚀 شروع",       "type": "text_button",
                     "action": "run_flow",    "target": "start_flow"},
                    {"text": "ℹ️ درباره",    "type": "text_button",
                     "action": "open_page",   "target": "about", "row": 1},
                ],
            },
            "about": {
                "text": "این ربات با ربات‌ساز بله ساخته شده.",
                "buttons": [
                    {"text": "🔙 بازگشت", "type": "text_button",
                     "action": "open_page", "target": "home"},
                ],
            },
        }

    # Flow های پیش‌فرض
    def get_flows(self):
        return {
            "start_flow": {
                "trigger": "🚀 شروع",
                "steps": [
                    {"type": "send_message", "text": "بریم شروع کنیم!"},
                    {"type": "ask_text",   "var": "name",   "prompt": "اسمت چیه؟"},
                    {"type": "ask_number", "var": "lucky",  "prompt": "عدد شانس از 1 تا 100؟"},
                    {"type": "send_message",
                     "text": "خوش اومدی {name}! عدد شانست {lucky} هست. 🍀"},
                    {"type": "finish"},
                ],
            }
        }


# این متغیر اجباری است - registry آن را پیدا می‌کند
TEMPLATE = MyAwesomeTemplate()
```

### مرحله ۳: ربات را ری‌استارت کنید
```bash
# Ctrl+C برای توقف، سپس:
python main.py
```

### مرحله ۴: تایید
- در لاگ ببینید: `Templates: ['awesome_bot', 'business_card', ...]`
- در ربات مادر «🎁 ساخت ربات از Template» را بزنید.
- باید Template جدید شما در لیست باشد.
- پلن‌هایش هم خودکار ساخته شده‌اند.
- می‌توانید از پنل ادمین قیمت‌ها را تغییر دهید.

### نکات مهم Template:
1. ✅ `key` باید **یکتا** باشد و در آینده تغییر نکند.
2. ✅ `plan_specs` می‌تواند ۱ تا ۴ پلن داشته باشد (هر duration یک بار).
3. ✅ هر Template می‌تواند **محدودیت‌های متفاوت** داشته باشد.
4. ✅ کلیدهای ثابت `duration`: `monthly`, `quarterly`, `biannual`, `yearly`
5. ✅ `target` در دکمه‌های `open_page` باید نام یکی از صفحات `get_pages()` باشد.
6. ✅ `target` در دکمه‌های `run_flow` باید نام یکی از Flow های `get_flows()` باشد.
7. ✅ نام Flow ها در `get_flows()` آزاد است، اما `trigger` آن چیزی است که کاربر می‌فرستد.

---

## 12. پشتیبان‌گیری از داده‌ها

تمام داده‌ها در یک فایل SQLite هستند: `botbuilder/data/botbuilder.sqlite3`

### پشتیبان دستی:
```bash
# قبل از ری‌استارت بزرگ یا تغییرات مهم
cp data/botbuilder.sqlite3 data/backup_$(date +%Y%m%d_%H%M%S).sqlite3
```

### پشتیبان خودکار روزانه (cron در لینوکس):
```bash
# crontab -e
0 3 * * * cp /root/botbuilder/data/botbuilder.sqlite3 /root/backups/bb_$(date +\%Y\%m\%d).sqlite3
```

### Restore:
```bash
# ربات را متوقف کنید
cp data/backup_20260101.sqlite3 data/botbuilder.sqlite3
# ربات را دوباره اجرا کنید
```

### Export به CSV (برای آنالیز):
```python
# در پایتون
import sqlite3, csv
conn = sqlite3.connect("data/botbuilder.sqlite3")
for table in ["users", "bots", "subscriptions", "payments"]:
    rows = conn.execute(f"SELECT * FROM {table}").fetchall()
    cols = [d[0] for d in conn.execute(f"SELECT * FROM {table} LIMIT 0").description]
    with open(f"{table}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(cols); w.writerows(rows)
```

---

## 🎉 تبریک!

شما اکنون یک **پلتفرم کامل ربات‌ساز SaaS** در دست دارید.

### امکانات کلی سیستم:
- ✅ مدیریت چند ربات با توکن جدا
- ✅ سیستم اشتراک با محدودیت‌های دقیق
- ✅ کیف پول داخلی + کد هدیه
- ✅ ۳ روش پرداخت (داخلی بله + درگاه آنلاین + کارت‌به‌کارت)
- ✅ Page Builder بدون کدنویسی
- ✅ Flow Engine با ۱۰ نوع step
- ✅ کانال اجباری
- ✅ Broadcast انبوه با rate limiting
- ✅ سیستم نمایندگی + پورسانت
- ✅ Template Marketplace (۴ نمونه آماده)
- ✅ Module Marketplace (معماری آماده)
- ✅ پنل ادمین کامل با ۱۴ بخش
- ✅ آمار و تحلیل
- ✅ Auto-discovery برای افزودن Template/Module بدون لمس هسته

### مسیر فایل‌های مهم:
- 🔑 توکن: `botbuilder/config.py`
- 💾 دیتابیس: `botbuilder/data/botbuilder.sqlite3`
- 📝 لاگ: `botbuilder/data/logs/botbuilder.log`
- 🧩 Templateها: `botbuilder/templates/builtin/`
- ⚙️ Moduleها: `botbuilder/modules/builtin/`

### پشتیبانی:
اگر سوال یا مشکلی داشتید، با ارائه:
- 📝 پیام خطا (از لاگ)
- 🔢 شماره فاز/بخش
- 🧪 نتیجه `python health_check.py`

می‌توانم بهتر کمک کنم.

**موفق باشید! 🚀**
