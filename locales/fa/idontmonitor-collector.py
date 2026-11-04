#!/usr/bin/env python3
"""Minute telemetry collector for six-hour resource and tunnel reports."""
import json, os, time, subprocess, shutil, tempfile, grp
from pathlib import Path
STATE=Path(os.environ.get('IDM_STATE_DIR','/var/lib/idontmonitor'))
HISTORY=STATE/'metrics-history.json'; PREV=STATE/'collector-prev.json'; EVENTS=STATE/'tunnel-events.json'
PATTERNS=('ctunnel@','ctunnel-engine@','backpack-','paqet','paqet-')
EXCLUDED={'backpack-monitor.service','backpack-webui.service','backpack-proxy.service','paqet-relay.service','paqet-auto-reset.service','paqet-tunnel.service'}
def atomic(path,data):
    path.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(prefix='.idm-',dir=str(path.parent))
    with os.fdopen(fd,'w') as f: json.dump(data,f,separators=(',',':'))
    os.chmod(tmp,0o640)
    try: os.chown(tmp,0,grp.getgrnam('idontmonitor').gr_gid)
    except KeyError: pass
    os.replace(tmp,path)
def cpu_ticks():
    a=list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:])); return sum(a),a[3]+(a[4] if len(a)>4 else 0)
def main():
    now=int(time.time()); total,idle=cpu_ticks(); prev={}
    try: prev=json.loads(PREV.read_text())
    except Exception: pass
    dt=total-int(prev.get('total',total)); di=idle-int(prev.get('idle',idle)); cpu=round(max(0,min(100,(1-di/dt)*100)),1) if dt>0 else None
    mem={}
    for line in Path('/proc/meminfo').read_text().splitlines():
        k,v=line.split(':',1); mem[k]=int(v.strip().split()[0])*1024
    mt=mem.get('MemTotal',0); ma=mem.get('MemAvailable',0); used=max(0,mt-ma)
    disk=shutil.disk_usage('/'); row={'timestamp':now,'cpu_percent':cpu,'memory_percent':round(used/mt*100,1) if mt else 0,'memory_used_bytes':used,'memory_total_bytes':mt,'disk_percent':round(disk.used/disk.total*100,1) if disk.total else 0,'disk_used_bytes':disk.used,'disk_total_bytes':disk.total}
    try: rows=json.loads(HISTORY.read_text())
    except Exception: rows=[]
    if not isinstance(rows,list): rows=[]
    rows=[r for r in rows if now-int(r.get('timestamp',0))<=86400]
    if not rows or now-int(rows[-1].get('timestamp',0))>=50: rows.append(row)
    else: rows[-1]=row
    atomic(HISTORY,rows[-1440:]); atomic(PREV,{'total':total,'idle':idle,'timestamp':now})
    p=subprocess.run(['/usr/bin/systemctl','list-units','--all','--type=service','--no-legend','--no-pager'],capture_output=True,text=True,timeout=8)
    current={}
    if p.returncode==0:
        for line in p.stdout.splitlines():
            cols=line.split(None,4)
            if len(cols)>=4 and cols[0].endswith('.service') and cols[0] not in EXCLUDED and cols[0].startswith(PATTERNS): current[cols[0]]=cols[2]=='active'
    try: old=json.loads((STATE/'collector-tunnels.json').read_text())
    except Exception: old={}
    events=[]
    for unit,active in current.items():
        if unit in old and bool(old[unit])!=active:
            events.append({'timestamp':now,'unit':unit,'event':'recovered' if active else 'disconnected','status':'active' if active else 'inactive'})
    try: ev=json.loads(EVENTS.read_text())
    except Exception: ev=[]
    ev=[x for x in ev if now-float(x.get('timestamp',0))<=86400]+events
    atomic(EVENTS,ev[-1000:]); atomic(STATE/'collector-tunnels.json',current)
if __name__=='__main__': main()
