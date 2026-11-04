# معماری idontMonitor

## وضعیت فعلی

- `app/main.py`: برنامهٔ FastAPI، نشست، احراز هویت، APIها و جمع‌آوری داده‌های سیستم در نسخهٔ فعلی.
- `static/index.html`: پوستهٔ داشبورد و صفحات پنل.
- `static/login.html`: صفحهٔ ورود.
- `static/app.js`: تعاملات مرورگر، دریافت داده و نمودارها.
- `static/i18n.js` و `locales/`: انتخاب زبان و واژه‌نامه‌ها.
- `static/style.css`: طراحی، واکنش‌گرایی و حالت RTL/LTR.
- `install.sh` و `systemd/`: نصب و اجرای سرویس.

## جهت معماری پیشنهادی

در بازآرایی‌های بعدی، کد سمت سرور به ماژول‌های `api`, `services`, `domain`, `infrastructure` و `repositories` تفکیک شود. هر مرحله باید رفتار فعلی را حفظ کند و قبل از ادغام، تست‌های رگرسیون و آزمون نصب/به‌روزرسانی را بگذراند.

## محدودیت مهم

نسخهٔ 1.8.1 قابلیت Update Center و مرز امنیتی updater را اضافه می‌کند. تفکیک کامل بک‌اند به لایه‌های مستقل به‌صورت مرحله‌ای و با تست‌های رگرسیون انجام می‌شود تا رفتار پایش سیستم تغییر ناخواسته نکند.

## v1.8.1 Update Center boundary

- `app/main.py` exposes authenticated update metadata/status/apply endpoints. It does not accept arbitrary shell commands or user-supplied URLs.
- `scripts/idontmonitor-update` is installed as a root-owned fixed helper at `/usr/local/sbin/idontmonitor-update`. The `idontmonitor` service account receives a narrowly scoped sudoers rule for the `apply` action only.
- Release installation uses `/opt/idontmonitor/releases/<version>` and switches `/opt/idontmonitor/current` atomically after asset digest, archive-path, version and syntax validation. The helper runs a health check and restores the previous symlink if the new service fails health checks.
- Configuration in `/etc/idontmonitor`, and persistent state in `/var/lib/idontmonitor`, are not extracted from the release ZIP or replaced by the updater.
- GitHub API results are cached briefly in-process to avoid repeated unauthenticated requests; frontend polling is bounded to status checks rather than continuous downloads.


## v1.9.9 operations boundary

`app/ops.py` provides authenticated, bounded operations endpoints. Read-only probes use fixed argument arrays and timeouts. Privileged actions use `/usr/local/sbin/idontmonitor-ops`, a root-owned helper that validates action and service identifiers before invoking systemd. The sudoers entry permits only this helper; the helper does not expose a shell. `static/operations.js` is the UI client. See `docs/PLUGIN_API.md` for module safety requirements.

The application log rotates at 100 MiB and retains three previous files. Tunnel service state is derived from systemd. Per-tunnel traffic is intentionally marked unavailable unless a unique, verified interface mapping exists. The provided Paqet archive is installer-only, so this project detects resulting service names but does not install or change Paqet itself.
