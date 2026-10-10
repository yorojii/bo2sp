import sys,json,time
from pathlib import Path
sys.path.insert(0,'work/porter')
from runtime import Session
pid=int(sys.argv[1]);game=sys.argv[2];name=sys.argv[3]
catalog=json.loads(Path('work/'+('mw2_catalog.json' if game=='mw2' else 'cod4_catalog.json')).read_text())
clip=next(x for x in catalog if x['name']==name)
s=Session(pid);names=json.loads(Path('work/project/names.json').read_text())
try:
    report=s.apply({target:clip['path'] for target in names if game=='cod4' or 'alert' in target or 'ads' in target or 'hold_idle' in target})
    print('Visual test active:',game,name,len(report),flush=True);time.sleep(18)
finally:print('Restored',s.restore(),flush=True);s.close()
