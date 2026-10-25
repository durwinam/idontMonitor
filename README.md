<div align="center">

<img src="static/idontmonitor-logo.png" alt="لوگوی آیدونت مانیتور" width="90">

# `idontMonitor`

### پایش سرور، با دیدی روشن‌تر

`while (server.is_alive()) { monitor(); }`
![Version](https://img.shields.io/badge/Version-1.8.1-7C3AED?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Linux](https://img.shields.io/badge/Operating%20System-Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)
![License](https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge)
**پایش · تحلیل · مدیریت**

[معرفی](#معرفی) · [قابلیت‌ها](#قابلیتهای-پروژه) · [نصب](#نصب-سریع) · [مدیریت](#مدیریت-با-خط-فرمان) · [به‌روزرسانی](#بهروزرسانی)

</div>

---

## معرفی

**idontMonitor** پروژه‌ای برای مانیتورینگ و مدیریت وضعیت سرورهای لینوکسی و VPS است. سورس پروژه بخش برنامه، رابط کاربری، ترجمه‌ها، اسکریپت‌های مدیریتی، سرویس سیستم و آزمون‌ها را در ساختاری جداگانه نگهداری می‌کند.

## قابلیت‌های پروژه

- رابط وب و فایل‌های مستقل رابط کاربری
- فایل‌های ترجمه فارسی و انگلیسی
- ساختار جداگانه برای برنامه، اسکریپت‌ها، مستندات و آزمون‌ها
- مدیریت سرویس با `systemd`
- ابزار خط فرمان برای وضعیت، گزارش‌ها، راه‌اندازی مجدد و به‌روزرسانی
- محیط مجازی پایتون برای وابستگی‌های برنامه

## پیش‌نیازها

- سرور مبتنی بر Debian یا Ubuntu
- دسترسی `root` یا `sudo`
- دسترسی اینترنت برای دریافت سورس و وابستگی‌ها

## نصب سریع

برای نصب، دستور زیر را روی سرور اجرا کنید:

```bash
sudo bash -c "$(curl -sL https://raw.githubusercontent.com/durwinam/idontMonitor/main/install.sh)"
```

این دستور نصب‌کننده را از شاخه `main` دریافت و اجرا می‌کند. اسکریپت وابستگی‌های پایه را نصب می‌کند، سورس را دریافت می‌کند، محیط مجازی پایتون می‌سازد و سرویس `idontmonitor` را ثبت می‌کند.

**توصیه امنیتی:** پیش از اجرای نصب‌کننده با دسترسی مدیریتی، کد آن را بررسی کنید:

```bash
curl -fsSL https://raw.githubusercontent.com/durwinam/idontMonitor/main/install.sh -o install.sh
less install.sh
sudo bash install.sh
```

## مدیریت با خط فرمان

پس از نصب، از دستور `idontMonitor` استفاده کنید.

### وضعیت سرویس

```bash
sudo idontMonitor status
```

### نسخه نصب‌شده

```bash
idontMonitor version
```

### گزارش زنده

```bash
sudo idontMonitor logs
```

برای خروج از گزارش زنده، `Ctrl+C` را فشار دهید.

### راه‌اندازی مجدد، اجرا و توقف

```bash
sudo idontMonitor restart
sudo idontMonitor start
sudo idontMonitor stop
```

### راهنما

```bash
idontMonitor help
```

## به‌روزرسانی

برای دریافت آخرین سورس از شاخه `main` و اجرای به‌روزرسانی:

```bash
sudo idontMonitor update
```

این فرایند نسخه را از فایل `VERSION` می‌خواند، وابستگی‌های نسخه جدید را نصب می‌کند و نسخه فعال را جابه‌جا می‌کند. در حالت به‌روزرسانی، پیش از تغییر نسخه از مسیرهای تنظیمات و داده‌های پایدار نسخه پشتیبان در `/var/backups/idontmonitor` ساخته می‌شود.

پس از به‌روزرسانی، وضعیت سرویس را بررسی کنید:

```bash
sudo idontMonitor status
sudo journalctl -u idontmonitor -n 100 --no-pager
```

نسخه‌های برنامه در `/opt/idontmonitor/releases` نگهداری می‌شوند. در صورت شکست راه‌اندازی نسخه جدید، نصب‌کننده تلاش می‌کند پیوند نسخه قبلی را بازگرداند؛ با این حال، پس از هر به‌روزرسانی وضعیت سرویس را بررسی کنید.

## مسیرهای مهم

| مسیر | کاربرد |
|---|---|
| `/opt/idontmonitor/current` | نسخه فعال |
| `/opt/idontmonitor/releases` | نسخه‌های نصب‌شده |
| `/etc/idontmonitor` | تنظیمات |
| `/var/lib/idontmonitor` | داده‌های پایدار |
| `/var/log/idontmonitor` | مسیر اختصاصی گزارش‌ها |
| `/usr/local/bin/idontMonitor` | ابزار خط فرمان |
| `/etc/systemd/system/idontmonitor.service` | سرویس سیستم |

## عیب‌یابی

اگر سرویس اجرا نشد، وضعیت و گزارش‌ها را بررسی کنید:

```bash
sudo systemctl status idontmonitor --no-pager
sudo journalctl -u idontmonitor -n 100 --no-pager
```

برای اجرای آزمون‌های موجود در مخزن، پس از آماده‌سازی محیط توسعه:

```bash
python3 -m unittest discover -s tests -v
```

## امنیت

- پیش از اجرای اسکریپت نصب یا به‌روزرسانی، محتوای آن را بررسی کنید.
- رمزها، توکن‌ها و اطلاعات حساس را در مخزن عمومی قرار ندهید.
- پس از به‌روزرسانی، فعال‌بودن سرویس را بررسی کنید.
- برای گزارش آسیب‌پذیری، دستورالعمل‌های `SECURITY.md` را دنبال کنید.

## ساختار پروژه

```text
idontMonitor/
├── app/                 # بخش برنامه
├── docs/                # مستندات
├── locales/             # ترجمه‌ها
├── scripts/             # ابزارهای مدیریتی
├── static/              # رابط کاربری
├── systemd/             # فایل‌های سرویس
├── tests/               # آزمون‌ها
├── install.sh           # نصب و به‌روزرسانی
├── requirements.txt     # وابستگی‌ها
├── VERSION              # نسخه
├── CHANGELOG.md         # تاریخچه تغییرات
├── SECURITY.md          # راهنمای امنیت
└── README.md            # راهنمای پروژه
```

## تاریخچه نسخه‌ها و مجوز

نسخه درج‌شده در این README برابر با `1.8.1` است. جزئیات تغییرات در [`CHANGELOG.md`](CHANGELOG.md) و شرایط مجوز در [`LICENSE`](LICENSE) قرار دارد.

---

<div align="center">

<img src="static/idontmonitor-logo.png" alt="آیدونت مانیتور" width="68">

### `monitor(); analyze(); protect();`

**پایش هوشمند · مدیریت ساده‌تر**

[مخزن گیت‌هاب](https://github.com/durwinam/idontMonitor) · [گزارش خطا](https://github.com/durwinam/idontMonitor/issues)

</div>
