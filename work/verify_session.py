import sys,json
from pathlib import Path
sys.path.insert(0,'work/porter')
from runtime import Session
j=json.loads(Path('work/runtime_journal.json').read_text())
s=Session(j['pid'])
s.originals={name:(addr,bytes.fromhex(data)) for name,(addr,data) in j['originals'].items()}
s.imported={name:bytes.fromhex(data) for name,data in j['imported'].items()}
baseline=dict(s.originals)
active=sum(s.read(addr,104)==s.imported[name] for name,(addr,data) in baseline.items())
assert active==142,(active,'changed by another tool')
restored=s.restore()
assert restored==142
assert all(s.read(addr,104)==data for addr,data in baseline.values())
mapping={name:str(Path('work/cod4/common_mp/xanim',name).resolve()) for name in baseline}
report=s.apply(mapping)
assert len(report)==142 and not any(r['omitted_bones'] for r in report)
assert not s.apply(mapping),'Repeated import should not allocate or rewrite'
# Exercise the same restore/reapply path used after an asset bank reload.
name=next(iter(baseline));addr,old=baseline[name]
s.write(addr,old)
assert len(s.apply(mapping))==1
assert s.restore()==142
assert all(s.read(addr,104)==data for addr,data in baseline.values())
result={'active_before_restore':active,'restored':restored,'reapplied':len(report),'missing_bones':0,'reload_reapply':1,'final_restored':142}
Path('work/session_validation.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result));s.close()
