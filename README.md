 
<div align="center">

<img src="static/idontmonitor-logo.png" width="110" alt="idontMonitor Logo">

# `idontMonitor`

**`// Observe. Analyze. Protect.`**

[![Version](https://img.shields.io/badge/version-1.8.1-00D4FF?style=for-the-badge&logo=semver&logoColor=white)](VERSION)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-111827?style=for-the-badge&logo=linux&logoColor=white)](https://www.kernel.org/)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge&logo=opensourceinitiative&logoColor=white)](LICENSE)

**A modern server monitoring experience, built for clarity, control, and performance.**

[English](#english) · [فارسی](#فارسی) · [Features](#features) · [Installation](#installation)

</div>

---

<a id="english"></a>

## `01` / About

**idontMonitor** is a server monitoring project designed to bring system visibility, operational awareness, and convenient management into one modern interface.

Built for VPS and Linux server environments, it focuses on presenting useful system information through a clean dashboard and maintaining a structured foundation for future improvements.

```python
from idontmonitor import Monitor

monitor = Monitor()
monitor.observe()
monitor.report()
```

> *Monitor the system. Understand the signals. Stay in control.*

## `02` / Features

- **System Monitoring** — Keep an eye on important server metrics.
- **Modern Web Interface** — A clean, responsive dashboard.
- **Multilingual UI** — English and Persian interface support.
- **Theme Support** — Designed for a customizable visual experience.
- **Update Management** — A dedicated foundation for update workflows.
- **Linux & VPS Focused** — Built with server administration in mind.
- **Structured Architecture** — Organized application, static assets, localization, scripts, and tests.

## `03` / Tech Stack

| Component | Technology |
|---|---|
| Runtime | Python 3.10+ |
| Interface | HTML, CSS, JavaScript |
| Localization | JSON-based language files |
| Deployment | Linux / systemd |
| Testing | Python unittest |

## `04` / Installation

Clone the repository:

```bash
git clone https://github.com/durwinam/idontMonitor.git
cd idontMonitor
```

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

For the supported installation workflow, review:

[`docs/INSTALL.md`](docs/INSTALL.md)

## `05` / Project Structure

```text
idontMonitor/
├── app/                 # Application backend
├── docs/                # Documentation
├── locales/
│   ├── en/              # English translations
│   └── fa/              # Persian translations
├── scripts/             # Management utilities
├── static/              # Frontend assets
├── systemd/             # Service configuration
├── tests/               # Automated tests
├── install.sh
├── requirements.txt
├── VERSION
└── README.md
```

## `06` / Version

Current project version: **1.8.1**

See [`CHANGELOG.md`](CHANGELOG.md) for release notes.

## `07` / Security

Please do not publish credentials, API tokens, private server addresses, or sensitive configuration data in public issues.

For security-related concerns, see [`SECURITY.md`](SECURITY.md).

## `08` / Contributing

Contributions, bug reports, and suggestions are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Make your changes and test them.
4. Submit a pull request with a clear description.

## `09` / License

This project is distributed under the [MIT License](LICENSE).

---

<a id="فارسی"></a>

## `فارسی` / درباره پروژه

**idontMonitor** یک ابزار مانیتورینگ سرور است که با هدف نمایش بهتر وضعیت سیستم، دسترسی سریع به اطلاعات مهم و مدیریت آسان‌تر سرورهای لینوکسی و VPS طراحی شده است.

تمرکز پروژه بر رابط کاربری مدرن، پشتیبانی از زبان فارسی و انگلیسی، ساختار منظم کد و فراهم‌کردن بستری مناسب برای توسعه قابلیت‌های آینده است.

### قابلیت‌ها

- مانیتورینگ اطلاعات مهم سرور
- رابط وب مدرن و واکنش‌گرا
- پشتیبانی از فارسی و انگلیسی
- زیرساخت پشتیبانی از پوسته‌های مختلف
- ساختار مدیریت به‌روزرسانی
- سازگاری با محیط‌های لینوکسی و VPS
- ساختار تفکیک‌شده برای بک‌اند، رابط کاربری، ترجمه‌ها و تست‌ها

### نصب

```bash
git clone https://github.com/durwinam/idontMonitor.git
cd idontMonitor

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

برای مشاهده مراحل نصب و راه‌اندازی، فایل [`docs/INSTALL.md`](docs/INSTALL.md) را مطالعه کنید.

### نسخه فعلی

`1.8.1`

برای مشاهده تغییرات نسخه‌ها، به فایل [`CHANGELOG.md`](CHANGELOG.md) مراجعه کنید.

### مشارکت و امنیت

برای گزارش باگ یا پیشنهاد قابلیت جدید، از بخش Issues مخزن GitHub استفاده کنید. اطلاعات محرمانه، رمزهای عبور و توکن‌ها را در گزارش‌های عمومی قرار ندهید.

---

<div align="center">

**`idontMonitor`**

`while (server.is_alive()) { monitor(); }`

*Observe · Analyze · Protect*

[Repository](https://github.com/durwinam/idontMonitor) · [Issues](https://github.com/durwinam/idontMonitor/issues)

</div>
