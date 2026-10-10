import sys,time,json
from pathlib import Path
sys.path.insert(0,'work/porter')
from runtime import Session
from live_target import LiveTargetReader,AnimationChanging
s=Session(int(sys.argv[1]),read_only=True);reader=LiveTargetReader(s);target='pb_stand_alert';start=time.monotonic();previous=None;resets=[];samples=0
print('Watching the live idle clip for F6 replays.',flush=True)
try:
    while time.monotonic()-start<float(sys.argv[2]):
        try:
            item=next((x for x in reader.snapshot().get('animations',[]) if x['target']==target),None)
            if item:
                phase=item['phase'];samples+=1
                if previous is not None and previous>0.5 and phase<0.15:
                    entry={'seconds':round(time.monotonic()-start,3),'before':previous,'after':phase};resets.append(entry);print('Replay reset:',json.dumps(entry),flush=True)
                previous=phase
            else:previous=None
        except AnimationChanging:pass
        time.sleep(0.025)
finally:s.close()
result={'pid':int(sys.argv[1]),'target':target,'phase_resets':resets,'samples':samples}
Path('work/replay_hotkey_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
