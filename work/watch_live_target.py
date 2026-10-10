import sys,json,time
from pathlib import Path
sys.path.insert(0,'work/porter')
from runtime import Session
from live_target import LiveTargetReader,AnimationChanging
s=Session(int(sys.argv[1]),read_only=True);reader=LiveTargetReader(s);end=time.monotonic()+float(sys.argv[2]);last=None;changes=[]
try:
    while time.monotonic()<end:
        try:
            snapshot=reader.snapshot();primary=snapshot.get('primary');key=(primary['action'],primary['target']) if primary else None
            if key and key!=last:
                row={'action':key[0],'target':key[1],'weight':primary['weight']};changes.append(row);print(json.dumps(row),flush=True);last=key
        except AnimationChanging:pass
        time.sleep(0.1)
finally:s.close()
Path('work/live_state_validation.json').write_text(json.dumps(changes,indent=2))
