"""Read-only session watcher for live acceptance tests.

Usage: python work/watch_session.py [seconds] [profile.json]

Finds the single BO2 process in the profile's BO2 folder and samples the local
character every 25 ms through a read-only handle. Records primary-slot changes,
playback phase resets on every body layer, death/spawn and readiness changes,
replay-key presses (polled with GetAsyncKeyState; no hook, nothing consumed),
and mapping changes saved by the importer. Never writes game memory.

Output: work/watch_logs/session-<time>.jsonl, one JSON event per line, and a
summary line at the end. Stop early with Ctrl+C; the summary is still written.
"""
import ctypes,json,sys,time
from datetime import datetime
from pathlib import Path
WORK=Path(__file__).resolve().parent
sys.path.insert(0,str(WORK/'porter'))
from runtime import Session
from live_target import LiveTargetReader,AnimationChanging
from replay_hotkey import KEYS,foreground_pid
from core import game_pids

seconds=float(sys.argv[1]) if len(sys.argv)>1 else 1800
profile_path=Path(sys.argv[2]) if len(sys.argv)>2 else WORK.parent/'outputs/Yoroji Tool/profile.json'
release=profile_path.parent
user32=ctypes.WinDLL('user32');user32.GetAsyncKeyState.restype=ctypes.c_short

def load_profile():
    try:return json.loads(profile_path.read_text())
    except (OSError,ValueError):return {}
catalog={}
try:catalog={x['path'].replace('/','\\').lower():x for x in json.loads((release/'library/catalog.json').read_text())}
except (OSError,ValueError):pass
def describe(path):
    if not path:return None
    item=catalog.get(str(path).replace('/','\\').lower())
    if item:return f"{item['game']}: {item['name']} ({'loop' if item['loop'] else 'one-shot'})"
    return ('CoD4 basic: ' if 'state\\sources' in str(path).replace('/','\\') else '')+Path(path).stem

profile=load_profile();profile_mtime=profile_path.stat().st_mtime_ns if profile_path.exists() else 0
folder=profile.get('bo2','');key_name=profile.get('replay',{}).get('key','F6');vk=KEYS.get(key_name,KEYS['F6'])
pids=game_pids(folder)
if len(pids)!=1:sys.exit(f'Expected exactly one BO2 process in {folder!r}, found {len(pids)}.')
pid=pids[0]

logdir=WORK/'watch_logs';logdir.mkdir(exist_ok=True)
logpath=logdir/f"session-{datetime.now():%Y%m%d-%H%M%S}.jsonl"
out=logpath.open('w',encoding='utf-8');start=time.monotonic()
counts={}
def event(kind,**data):
    row={'t':round(time.monotonic()-start,3),'event':kind,**data}
    out.write(json.dumps(row)+'\n');out.flush();counts[kind]=counts.get(kind,0)+1
    print(json.dumps(row),flush=True)

event('start',pid=pid,bo2=folder,replay_key=key_name,replay_enabled=profile.get('replay',{}).get('enabled'),
      mappings=len(profile.get('mapping',{})),profile=str(profile_path),log=str(logpath))
session=Session(pid,read_only=True);reader=LiveTargetReader(session)
last_primary=None;last_state=None;last_dead=None;phases={};key_down=False;samples=0;transitions=0
try:
    while time.monotonic()-start<seconds:
        now_down=bool(user32.GetAsyncKeyState(vk)&0x8000)
        if now_down!=key_down:
            key_down=now_down
            event('key_down' if now_down else 'key_up',key=key_name,bo2_focused=foreground_pid()==pid)
        if profile_path.exists() and profile_path.stat().st_mtime_ns!=profile_mtime:
            profile_mtime=profile_path.stat().st_mtime_ns;new=load_profile()
            old_map=profile.get('mapping',{});new_map=new.get('mapping',{})
            changed={t:describe(p) for t,p in new_map.items() if old_map.get(t)!=p}
            removed=[t for t in old_map if t not in new_map]
            event('profile_saved',changed=changed,removed=removed,mappings=len(new_map),replay=new.get('replay'))
            profile=new
        try:
            snap=reader.snapshot();samples+=1
        except AnimationChanging:
            transitions+=1;time.sleep(0.025);continue
        state=(snap.get('ready'),None if snap.get('ready') else snap.get('message'))
        if state!=last_state:event('state',ready=state[0],message=snap.get('message'));last_state=state
        if 'dead' in snap and snap['dead']!=last_dead:
            if last_dead is not None:event('died' if snap['dead'] else 'alive',client=snap.get('client'),entity=snap.get('entity'))
            last_dead=snap['dead']
        primary=snap.get('primary');key=primary['target'] if primary else None
        if key!=last_primary:
            mapped=profile.get('mapping',{}).get(key) if key else None
            event('primary',target=key,action=primary['action'] if primary else None,weight=primary['weight'] if primary else None,
                  replacement=describe(mapped) if mapped else 'Original BO2')
            last_primary=key
        seen=set()
        for item in snap.get('animations',[]):
            if not item['selectable']:continue
            name=item['target'];phase=item['phase'];seen.add(name);before=phases.get(name)
            if before is not None and before>0.5 and phase<0.15:
                mapped=profile.get('mapping',{}).get(name)
                event('phase_reset',target=name,before=round(before,4),after=round(phase,4),weight=item['weight'],
                      replacement=describe(mapped) if mapped else 'Original BO2')
            phases[name]=phase
        for name in list(phases):
            if name not in seen:del phases[name]
        time.sleep(0.025)
except KeyboardInterrupt:pass
finally:
    session.close()
    event('summary',seconds=round(time.monotonic()-start,1),samples=samples,transitions_skipped=transitions,counts=dict(counts))
    out.close()
