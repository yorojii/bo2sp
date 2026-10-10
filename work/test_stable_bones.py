import sys,json
from pathlib import Path
sys.path.insert(0,'work/porter')
from runtime import Session,load_clip
s=Session(int(sys.argv[1]));catalog=json.loads(Path('work/cod4_catalog.json').read_text());source=next(x for x in catalog if x['name']=='run_pain_stumble')
targets=['pb_stand_alert','pb_stumble_pistol_walk_forward','pb_death_run_stumble']
result=[]
for target in targets:
    addr,old=s.assets[target];p=int.from_bytes(old[64:68],'little');names=s.read(p,old[33]*2)
    report=s.apply({target:source['path']});new=s.read(addr,104)
    assert new[33]==old[33] and new[64:68]==old[64:68] and s.read(p,old[33]*2)==names
    assert new[26]==old[33] and sum(new[24:29])==old[33]
    assert s.restore()==1 and s.read(addr,104)==old
    result.append({'target':target,'stable_bone_count':old[33],'name_pointer_preserved':True,'restore_verified':True})
Path('work/stable_bone_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True);s.close()
