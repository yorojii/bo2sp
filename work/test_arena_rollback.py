import sys,json
from pathlib import Path
sys.path.insert(0,'work/porter')
from runtime import Session
s=Session(int(sys.argv[1]));target='pb_stand_alert';old=s.assets[target];result={}
catalog=json.loads(Path('work/cod4_catalog.json').read_text());clip=next(x for x in catalog if x['name']=='run_pain_stumble')['path']
normal=s.alloc;calls=0;checkpoint=(len(s.allocations),s.arena_cursor,s.arena_remaining)
def failing(data):
    global calls
    calls+=1
    if calls==4:raise OSError('Injected preparation failure')
    return normal(data)
s.alloc=failing
try:
    try:s.apply({target:clip})
    except OSError:pass
    else:raise AssertionError('Injected error not propagated')
    assert (len(s.allocations),s.arena_cursor,s.arena_remaining)==checkpoint
    assert s.read(old[0],104)==old[1] and not s.imported
    result['unpublished_blocks_reclaimed']=True
    s.alloc=normal;assert len(s.apply({target:clip}))==1
    imported=s.imported[target];checkpoint=(len(s.allocations),s.arena_cursor,s.arena_remaining);calls=0;s.alloc=failing
    other='pb_crouch_alert';other_old=s.assets[other]
    try:s.apply({other:clip})
    except OSError:pass
    else:raise AssertionError('Injected error not propagated')
    assert (len(s.allocations),s.arena_cursor,s.arena_remaining)==checkpoint
    assert s.read(old[0],104)==imported and s.read(other_old[0],104)==other_old[1]
    result['prior_import_preserved_on_preparation_failure']=True
finally:
    s.restore();assert s.read(old[0],104)==old[1];s.close()
result['exact_restore']=True;Path('work/arena_rollback_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
