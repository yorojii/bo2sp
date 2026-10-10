import sys,json,time
from pathlib import Path
sys.path.insert(0,'work/porter')
from runtime import Session
names=json.loads(Path('work/project/names.json').read_text())
s=Session(29252)
try:
    path=str(Path('work/cod4/common_mp/xanim',sys.argv[1] if len(sys.argv)>1 else 'pb_stand_death_nervedeath').resolve())
    mapping={name:path for name in names if 'alert' in name or 'ads' in name or 'hold_idle' in name}
    report=s.apply(mapping)
    print('Temporary clip-pose validation',Path(path).name,len(report),flush=True)
    time.sleep(25)
finally:
    print('Restored',s.restore(),flush=True);s.close()
