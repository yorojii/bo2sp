import importlib.util, json, shutil
from pathlib import Path
s=importlib.util.spec_from_file_location('porter','work/porter/porter.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
fake=Path('work/test_game').resolve(); (fake/'zone/all').mkdir(parents=True,exist_ok=True)
shutil.copy2('work/recovery/common_mp.ff',fake/'zone/all/common_mp.ff')
logs=[]
engine=m.Engine(r'D:\Call of Duty 4',fake,logs.append)
try:
    mapping=engine.scan()
    assert len(mapping)==142
    output,report=engine.build(mapping,install=False)
    print(json.dumps(report|{'mapping':'omitted'},indent=2))
except Exception:
    Path('work/engine_test.log').write_text('\n'.join(logs),encoding='utf-8')
    raise
Path('work/engine_test.log').write_text('\n'.join(logs),encoding='utf-8')
