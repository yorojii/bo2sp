"""Standalone freelook trial: hold Alt in BO2 to orbit the third-person camera.

Usage: python work/freelook_probe.py [seconds] [degrees_per_pixel]

Writes only cg_thirdPersonAngle / cg_thirdPersonRange and restores them when
Alt is released and on exit. Prints on/off events and errors.
"""
import json,sys,time
from pathlib import Path
WORK=Path(__file__).resolve().parent
sys.path.insert(0,str(WORK/'porter'))
from freelook import Freelook,CameraDvars
from runtime_app import game_pids

seconds=float(sys.argv[1]) if len(sys.argv)>1 else 600
sensitivity=float(sys.argv[2]) if len(sys.argv)>2 else 0.15
folder=json.loads((WORK.parent/'outputs/Yoroji Tool/profile.json').read_text())['bo2']
pids=game_pids(folder)
if len(pids)!=1:sys.exit(f'Expected one BO2 process in {folder!r}, found {len(pids)}.')
pid=pids[0];camera=CameraDvars(pid)
before=(camera.get(camera.angle),camera.get(camera.range));camera.close()
print(json.dumps({'pid':pid,'angle':before[0],'range':before[1],'seconds':seconds,'degrees_per_pixel':sensitivity}),flush=True)
look=Freelook(degrees_per_pixel=sensitivity);look.ready.wait(5);look.configure(0x12,pid,True);shown=0
try:
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        time.sleep(0.05)
        for stamp,text in look.events[shown:]:print(text,flush=True)
        shown=len(look.events)
        if look.error:print('error:',look.error,flush=True);look.error=None
except KeyboardInterrupt:pass
finally:
    look.stop();camera=CameraDvars(pid)
    after=(camera.get(camera.angle),camera.get(camera.range));camera.close()
    print(json.dumps({'stopped':True,'hook_closed':not look.is_alive(),'angle_after':after[0],'range_after':after[1],'restored':after==before}),flush=True)
