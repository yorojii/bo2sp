import importlib.util,json,time,sys
from pathlib import Path
s=importlib.util.spec_from_file_location('runtime','work/porter/runtime.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
pid=int(sys.argv[1]);names=json.loads(Path('work/project/names.json').read_text())
mapping={name:str(Path('work/cod4/common_mp/xanim',name).resolve()) for name in names}
session=None
for i in range(120):
    try:
        if session is None:session=m.Session(pid)
        report=session.apply(mapping)
        if report:
            print('imported',len(report),flush=True)
            journal={'pid':pid,'originals':{name:[addr,data.hex()] for name,(addr,data) in session.originals.items()},'imported':{name:data.hex() for name,data in session.imported.items()},'report':report}
            Path('work/runtime_journal.json').write_text(json.dumps(journal,indent=2))
    except Exception as e:
        if i%10==0:print('waiting',str(e),flush=True)
    time.sleep(2)
if session:session.close()
