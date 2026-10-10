import importlib.util,json,sys
from pathlib import Path
s=importlib.util.spec_from_file_location('runtime','work/porter/runtime.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
pid=int(sys.argv[1]);session=m.Session(pid)
names=json.loads(Path('work/project/names.json').read_text())
mapping={name:str(Path('work/cod4/common_mp/xanim',name).resolve()) for name in names}
report=session.apply(mapping)
journal={'pid':pid,'originals':{name:[addr,data.hex()] for name,(addr,data) in session.originals.items()},'imported':{name:data.hex() for name,data in session.imported.items()},'report':report}
Path('work/runtime_journal.json').write_text(json.dumps(journal,indent=2))
print('applied',len(report),'death animations',sum('death' in x['target'] for x in report),'omitted bones',sum(len(x['omitted_bones']) for x in report))
print('sample',report[:2]);session.close()
