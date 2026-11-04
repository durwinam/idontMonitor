#!/usr/bin/env python3
"""Root watchdog: sustained CPU OR memory pressure triggers a guarded reboot."""
import json, time, subprocess, urllib.request, urllib.parse
from pathlib import Path
STATE_DIR=Path(__import__('os').environ.get('IDM_STATE_DIR','/var/lib/idontmonitor')); STATE=STATE_DIR/'auto-reboot-state.json'; TELEGRAM=STATE_DIR/'telegram-bot.json'
THRESHOLD=90.0; HOLD=120; COOLDOWN=1800; ALERT_DELAY=15

def read_cpu():
    a=list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:])); return sum(a),a[3]+(a[4] if len(a)>4 else 0)
def read_ram():
    m={}
    for line in Path('/proc/meminfo').read_text().splitlines():
        k,v=line.split(':',1); m[k]=int(v.strip().split()[0])*1024
    total=m.get('MemTotal',0); avail=m.get('MemAvailable',0)
    return max(0,(total-avail)/total*100) if total else 0

def notify(message):
    try:
        cfg=json.loads(TELEGRAM.read_text()); token=str(cfg.get('token','')).strip(); admins=cfg.get('admin_ids',[])
        if not token:return
        for admin in admins:
            data=urllib.parse.urlencode({'chat_id':str(admin),'text':message}).encode()
            req=urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage',data=data)
            urllib.request.urlopen(req,timeout=5).read(4096)
    except Exception: pass

def save(s):
    STATE.parent.mkdir(parents=True,exist_ok=True); tmp=STATE.with_suffix('.tmp'); tmp.write_text(json.dumps(s)); tmp.chmod(0o600); tmp.replace(STATE)

def main():
    now=time.time(); s={}
    try:s=json.loads(STATE.read_text())
    except Exception:pass
    total,idle=read_cpu(); prev=s.get('cpu_prev') or {}; dt=total-int(prev.get('total',total)); di=idle-int(prev.get('idle',idle))
    cpu=max(0,min(100,(1-di/dt)*100)) if dt>0 else 0; ram=read_ram()
    s['cpu_prev']={'total':total,'idle':idle}; over=(cpu>THRESHOLD or ram>THRESHOLD)
    if over:
        if not s.get('above_since'): s['above_since']=now
    else: s['above_since']=None
    s['last_sample']={'timestamp':now,'cpu_percent':round(cpu,1),'ram_percent':round(ram,1)}
    if over and now-float(s.get('above_since') or now)>=HOLD and now-float(s.get('last_reboot') or 0)>=COOLDOWN and not s.get('reboot_pending'):
        s['reboot_pending']=True; s['reboot_reason']=f'CPU={cpu:.1f}% RAM={ram:.1f}%'; save(s)
        notify(f'🚨 idontMonitor: CPU/RAM بالای ۹۰٪ برای ۱۲۰ ثانیه باقی ماند. سرور تا ۱۵ ثانیه دیگر ریبوت می‌شود.\nCPU: {cpu:.1f}% · RAM: {ram:.1f}%')
        time.sleep(ALERT_DELAY)
        # Re-check before acting; if pressure cleared, cancel.
        cpu2=0
        try:
            t2,i2=read_cpu(); d2=t2-total; idle2=i2-idle; cpu2=max(0,min(100,(1-idle2/d2)*100)) if d2>0 else 0
        except Exception: pass
        ram2=read_ram()
        if cpu2<=THRESHOLD and ram2<=THRESHOLD:
            s['reboot_pending']=False; s['above_since']=None; s['last_cancelled']=time.time(); save(s); notify('✅ ریبوت خودکار لغو شد؛ فشار منابع پیش از اجرا برطرف شد.'); return
        s['last_reboot']=time.time(); s['reboot_pending']=False; s['last_reboot_reason']=s.get('reboot_reason'); save(s)
        subprocess.run(['/usr/bin/logger','-t','idontmonitor-auto-reboot',f"Automatic reboot: {s['last_reboot_reason']}"],check=False)
        subprocess.run(['/usr/bin/systemctl','reboot'],check=False)
    else: save(s)
if __name__=='__main__': main()
