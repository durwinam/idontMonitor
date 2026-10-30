<div align="center">

![لوگوی idontMonitor](static/idontmonitor-logo-full.png)

# idontMonitor
### پنل پایش سرور، منابع سیستم و وضعیت شبکه

**نسخهٔ ۲.۲.۹** · توسعه‌دهنده: **durwinam**

[مخزن گیت‌هاب](https://github.com/durwinam/idontMonitor) · [کانال تلگرام](https://t.me/idontproject)

</div>

---

## v2.3.4 security and UI notes

- Root VPS password changes now require an authenticated, single-use server-side arithmetic CAPTCHA. The challenge expires after three minutes and is bound to the request IP and login session.
- CAPTCHA issuance and password-change attempts are rate-limited. The ordinary dashboard login CAPTCHA and rate limits remain enabled.
- API/login responses receive no-store cache headers and the application adds baseline browser security headers.
- Persian/English strings cover the VPS password/reboot modal and CAPTCHA errors; the selected language is applied to dynamic UI text.
- Telegram messages try mapped Premium custom emoji entities for CPU/RAM/Disk and other configured glyphs. If Telegram rejects the entities, the same message is retried with the exact original Unicode emoji. An explicit Premium eligibility rejection switches the worker to Unicode fallback; an individual invalid ID triggers only a per-message fallback. IDs can be overridden with `IDM_TELEGRAM_CUSTOM_EMOJI_IDS`.
- Existing monitoring counters, traffic persistence, tunnel operations, updater behavior, and all eight themes are retained.

**Deployment note:** CAPTCHA state is in process memory; the default installer runs one application worker. If you deliberately configure multiple workers, use a shared challenge store before enabling this flow across workers.


## معرفی

`idontMonitor` یک پنل تحت وب برای مشاهدهٔ وضعیت منابع سرور، مصرف شبکه، تاریخچهٔ ترافیک، آزمون سرعت اتصال و بررسی‌های امنیتی است. این برنامه برای نصب روی سرور شخصی طراحی شده و رابط وب آن از بک‌اند برنامه داده دریافت می‌کند.

## قابلیت‌ها

- پایش مصرف پردازنده، حافظه و فضای دیسک
- نمایش وضعیت میزبان، زمان روشن‌بودن و میانگین بار سیستم
- مشاهدهٔ نرخ دریافت و ارسال و تاریخچهٔ ترافیک شبکه
- آزمون سرعت خروجی سرور با انتقال واقعی و محدودشده
- نمایش اطلاعات تأخیر، نوسان تأخیر و از دست رفتن بسته‌ها در صورت قابل‌اندازه‌گیری بودن
- احراز هویت پنل، محدودسازی تلاش‌های ورود و ثبت رویدادهای ورود
- تنظیمات حساب و پشتیبانی از HTTP یا HTTPS مطابق تنظیمات نصب
- رابط واکنش‌گرا برای نمایشگرهای دسکتاپ و موبایل
- انتخاب زبان انگلیسی یا فارسی؛ فارسی با چیدمان راست‌چین و فونت وزیرمتن
- لینک‌های رسمی گیت‌هاب و تلگرام در پایین پنل




## C-Tunnel 0.2.5 compatibility (v2.3.4)

The tunnel manager now understands C-Tunnel's exact `ct-<name>` device and ECMP lane devices `ct-<name>.1` through `.7`; traffic totals include only interfaces matching the exact instance-derived names. C-Tunnel instances are managed through the shared `ctunnel@.service` / `ctunnel-engine@.service` templates, so removing an instance stops and disables that instance without deleting the shared template or tunnel config. If teardown fails, idontMonitor leaves the instance enabled and preserves its state/configuration record rather than hiding the failure.

## Operations & Tunnel Manager (v2.3.4)

در نسخهٔ 2.3.4 قابلیت‌های مدیریت عملیات حفظ شده‌اند: شناسایی سرویس‌های تانل از systemd، ریستارت گروهی با تأیید، عیب‌یابی فقط‌خواندنی از فهرست مجاز، هشدارهای محلی، حالت تعمیر زمان‌دار، ثبت رویدادهای مدیریتی و پشتیبان‌گیری محدود از تنظیمات هشدار. اجرای شل دلخواه از پنل پشتیبانی نمی‌شود.

**محدودیت داده:** آمار ترافیک هر تانل فقط وقتی نمایش داده می‌شود که رابط شبکه با اطمینان به همان سرویس نگاشت شود. در غیر این صورت وضعیت «در دسترس نیست» نشان داده می‌شود. فایل Paqet ارائه‌شده در ورودی این نسخه اسکریپت نصب است؛ idontMonitor موتور Paqet را نصب یا پیکربندی نمی‌کند.

**چرخش لاگ:** فایل فعال `idontmonitor.log` حداکثر 100 MiB است و سه فایل چرخیده نگه داشته می‌شوند. گزارش‌های systemd journal جداگانه تابع تنظیمات journald هستند.

## مرکز به‌روزرسانی (v2.3.4)

نسخهٔ 2.3.4 از Asset دقیق `idontMonitor-vX.Y.Z.tar.gz` را از Release رسمی دریافت می‌کند؛ فقط اگر Asset موجود نباشد از آرشیو خودکار تگ استفاده می‌کند. این مسیر به ZIP وابسته نیست.

- `sudo idontMonitor update` آخرین GitHub Release پایدار را از آرشیو سورس `tar.gz` مربوط به Tag دریافت می‌کند.
- `sudo idontMonitor update-main` سورس شاخهٔ `main` را بررسی می‌کند؛ این مسیر نسخهٔ داخل سورس را بررسی می‌کند و برای هر commit جدید، حتی با شماره نسخهٔ ثابت، پوشهٔ مستقل می‌سازد؛ برای محیط عملیاتی همچنان Release پایدار توصیه می‌شود.
- نسخهٔ تگ، فایل `VERSION` و ساختار سورس قبل از فعال‌سازی اعتبارسنجی می‌شوند.
- پیش از فعال‌سازی، فایل‌های Python بررسی نحوی می‌شوند؛ سپس نسخهٔ جدید در مسیر staging ساخته می‌شود، helper و unit به‌روزرسانی می‌شوند، symlink جابه‌جا و سلامت سرویس بررسی می‌شود. در صورت شکست، نسخه و فایل‌های کمکی قبلی بازگردانده می‌شوند. در صورت شکست راه‌اندازی/سلامت، بازگشت به نسخهٔ قبلی تلاش می‌شود.
- پیکربندی `/etc/idontmonitor` و داده‌های پایدار `/var/lib/idontmonitor` خارج از دایرکتوری نسخه‌ها باقی می‌مانند.
- به‌روزرسانی عادی از Release Tag توصیه می‌شود؛ شاخهٔ `main` برای دریافت تغییرات توسعه است و ممکن است ناپایدار باشد.

## دستاوردهای نصب و راه‌اندازی

- انتخاب خودکار یک پورت آزاد در نصب تازه، با آزمون واقعی bind؛ هیچ سرویس دیگری متوقف نمی‌شود.
- هنگام ارتقا، پورت و تنظیمات اتصال موجود حفظ می‌شوند؛ نصب‌کننده به‌جای حدس زدن، در صورت ناقص بودن متادیتا متوقف می‌شود.
- سرویس با کاربر سیستمی کم‌دسترسی اجرا می‌شود و تنظیمات/داده‌ها خارج از پوشهٔ نسخه نگهداری می‌شوند.
- نصب‌کننده برای Debian/Ubuntu طراحی شده و پیش‌نیازهای سیستمی را بررسی یا نصب می‌کند.

## پیش‌نیازها

- سیستم‌عامل لینوکس؛ نصب‌کننده برای محیط‌های Debian/Ubuntu تهیه شده است.
- Python و ابزارهای لازم که نصب‌کنندهٔ پروژه بررسی یا نصب می‌کند.
- دسترسی مدیریتی برای نصب سرویس و تنظیم وابستگی‌های سیستم.
- دسترسی شبکه برای دریافت وابستگی‌ها و اجرای آزمون سرعت.

> نسخه‌های دقیق وابستگی‌ها در `requirements.txt` ثبت شده‌اند. پیش از نصب روی سرور عملیاتی، نصب‌کننده و تنظیمات محیط مقصد را بررسی کنید.

## نصب

روش نصب توصیه‌شده، استفاده از نصب‌کنندهٔ موجود در مخزن رسمی است. ابتدا مخزن را دریافت و محتوای `install.sh` را بررسی کنید؛ سپس آن را با دسترسی مدیریتی اجرا کنید.

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/durwinam/idontMonitor/main/install.sh)"
```

رفتار نصب، پورت، مسیر پنل، دامنه و روش فعال‌سازی HTTPS می‌تواند به نسخهٔ نصب‌کننده وابسته باشد. هنگام نصب، مقادیر پیشنهادی را با تنظیمات محیط خود تطبیق دهید.

## ساختار سورس

```text
idontMonitor/
├── app/
│   └── main.py              # برنامهٔ FastAPI، API و منطق فعلی سمت سرور
├── static/
│   ├── index.html           # پنل اصلی
│   ├── login.html           # صفحهٔ ورود
│   ├── app.js               # رفتار تعاملی رابط
│   ├── i18n.js              # مدیریت زبان رابط
│   ├── style.css            # استایل و واکنش‌گرایی
│   └── ...                  # لوگوها و منابع ثابت
├── locales/
│   ├── en/messages.json     # واژه‌نامهٔ انگلیسی
│   └── fa/messages.json     # واژه‌نامهٔ فارسی
├── docs/                    # مستندات نصب و معماری
├── systemd/                 # فایل سرویس systemd
├── tests/                   # تست‌های ساختار و واحد
├── install.sh               # نصب‌کننده
├── requirements.txt         # وابستگی‌های پایتون
├── VERSION                  # نسخهٔ سورس
├── CHANGELOG.md             # تاریخچهٔ تغییرات
└── README.md                # همین راهنما
```

> این ساختار مستندکنندهٔ سورس فعلی است؛ انتقال ماژول‌های بک‌اند به لایه‌های مستقل باید مرحله‌ای و همراه با تست رگرسیون انجام شود تا منطق عملیاتی تغییر نکند.

## معماری و قواعد توسعه

- هر فایل باید مسئولیت مشخص و قابل توضیحی داشته باشد.
- منطق رابط کاربری، واژه‌نامه‌ها، استایل‌ها و منطق سمت سرور از یکدیگر تفکیک شوند.
- از فرمت‌بندی استاندارد، نام‌گذاری معنادار و توابع کوتاه و قابل‌آزمون استفاده شود.
- تنظیمات محیطی و اسرار در سورس یا مستندات عمومی قرار نگیرند.
- تغییرات معماری باید با تست واحد، تست یکپارچگی و تست رگرسیون همراه باشند.
- قابلیت‌های موجود، تاریخچهٔ ترافیک و تنظیمات اتصال هنگام به‌روزرسانی باید حفظ شوند.

## زبان فارسی و فونت وزیرمتن

زبان از انتخاب‌گر بالای پنل تغییر می‌کند. انتخاب کاربر در مرورگر نگهداری می‌شود. در حالت فارسی، جهت صفحه `RTL` و فونت `Vazirmatn` فعال می‌شود؛ در حالت انگلیسی، رابط به `LTR` برمی‌گردد. نصب‌کننده تلاش می‌کند بستهٔ فونت وزیرمتن را از مخازن توزیع نصب کرده و فایل آن را در منابع محلی پنل قرار دهد؛ در نتیجه رابط برای نمایش فارسی به Google Fonts وابسته نیست.

## اجرای تست‌ها

در پوشهٔ ریشهٔ پروژه اجرا کنید:

```bash
python -m compileall -q app
node --check static/app.js
node --check static/i18n.js
python tests/test_syntax.py
python tests/test_units.py
```

## عیب‌یابی سرویس

نام سرویس و مسیر نصب ممکن است در محیط‌های مختلف تفاوت داشته باشد. از نام سرویس نمایش‌داده‌شده در نصب‌کننده استفاده کنید. برای سرویس systemd با نام `idontmonitor`، دستورهای معمول عبارت‌اند از:

```bash
sudo systemctl status idontmonitor
sudo systemctl restart idontmonitor
sudo journalctl -u idontmonitor -n 100 --no-pager
```

## امنیت و نگهداری

- گذرواژه، کلید نشست، فایل پیکربندی و داده‌های تاریخچه را منتشر نکنید.
- پیش از ارتقا، از پیکربندی و داده‌های پایدار نسخهٔ پشتیبان تهیه کنید.
- اسکریپت نصب و به‌روزرسانی را پیش از اجرا بررسی کنید.
- آزمون سرعت، ترافیک واقعی مصرف می‌کند و نتایج آن به مسیر شبکه و نقطهٔ پایانی وابسته است.
- نتیجهٔ تست در محیط توسعه به‌تنهایی اثبات‌کنندهٔ عملکرد روی VPS مقصد نیست.

## مشارکت در توسعه

۱. مخزن را Fork کنید.
۲. برای تغییر خود یک شاخهٔ مستقل بسازید.
۳. قالب‌بندی و تست‌های مرتبط را اجرا کنید.
۴. در توضیح درخواست ادغام، رفتار تغییرکرده و نتیجهٔ تست‌ها را بنویسید.

## لینک‌ها و مالکیت

- GitHub: https://github.com/durwinam/idontMonitor
- Telegram: https://t.me/idontproject

---

<div align="center">

**© 2026 durwinam — تمامی حقوق محفوظ است.**

</div>

### VPS control center (v2.3.4)
The VPS Management page displays live host facts and includes protected root-password change and reboot operations. Password changes use the fixed root-owned `idontmonitor-ops` helper; arbitrary commands are not accepted. Telegram password changes are admin-only, use a confirmation callback, and delete the incoming password message where Telegram permits. Use this feature only in a private bot chat, never in groups.

## Safe extraction path

The release archive is packaged inside a single `idontMonitor-v2.3.4/` directory. Extract it to a dedicated directory instead of the VPS filesystem root:

```bash
sudo install -d -m 0755 /opt/idontmonitor-source
sudo unzip idontMonitor-v2.3.4.zip -d /opt/idontmonitor-source
cd /opt/idontmonitor-source/idontMonitor-v2.3.4
sudo bash ./install.sh
```

Extraction only unpacks the source. The installer installs the application to `/opt/idontmonitor`; do not unzip the archive directly into `/`.
