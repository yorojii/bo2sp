import sys,json,struct,time,traceback,shutil
from pathlib import Path
sys.path.insert(0,'work/porter')
from runtime import Session
from live_target import LiveTargetReader,read_tree_nodes,AnimationChanging

pid=int(sys.argv[1]);report={}
# A fading child must inherit its parent weight; cached inactive leaves must
# never be offered as the current target, and corrupt links must be rejected.
nodes=bytearray(64*5);entries=bytearray(16*4)
def node(i,parent,child,next_index,anim,part,weight):
    struct.pack_into('<5H',nodes,i*64+8,0,next_index,child,parent,anim)
    struct.pack_into('<I',nodes,i*64+20,part);struct.pack_into('<f',nodes,i*64+44,weight)
node(1,0,2,0,0,0,0.5);node(2,1,0,3,1,100,0.25);node(3,1,0,4,2,200,0.75);node(4,1,0,0,3,300,0)
for i,p in [(1,100),(2,200),(3,300)]:struct.pack_into('<I',entries,i*16,p)
out=read_tree_nodes(nodes,entries,1,{100:'pb_stand_alert',200:'pb_pistol_run_fast',300:'pb_crouch_alert'})
assert [(x['target'],x['weight']) for x in out]==[('pb_pistol_run_fast',0.375),('pb_stand_alert',0.125)]
struct.pack_into('<H',nodes,3*64+10,2)
try:read_tree_nodes(nodes,entries,1,{100:'pb_stand_alert',200:'pb_pistol_run_fast'})
except AnimationChanging:report['cycles_rejected']=True
else:raise AssertionError('A cyclic animation tree was accepted')
report['inherited_blends_verified']=True;report['inactive_slots_excluded']=True

observer=Session(pid,read_only=True);reader=LiveTargetReader(observer);snap=reader.snapshot();assert snap['ready'];report['detected_before']=snap['primary']['target']
for method in (lambda:observer.write(1,b''),lambda:observer.apply({}),lambda:reader.restart({snap['primary']['target']})):
    try:method()
    except RuntimeError:pass
    else:raise AssertionError('Observer accepted a mutation')
report['observer_read_only']=True;observer.close()

s=Session(pid);target=snap['primary']['target'];other='pb_stand_alert' if target!='pb_stand_alert' else 'pb_crouch_alert'
baseline={name:s.assets[name] for name in (target,other)}
cod4=json.loads(Path('work/cod4_catalog.json').read_text());mw2=json.loads(Path('work/mw2_catalog.json').read_text())
clip1=next(x for x in cod4 if x['name']=='run_pain_stumble')['path'];clip2=next(x for x in mw2 if x['name']=='heat_run_loop')['path']
try:
    assert len(s.apply({target:clip1,other:clip2}))==2
    first=s.imported[target];assert s.originals[target][1]==baseline[target][1]
    assert len(s.apply({target:clip2,other:clip2}))==1
    assert s.imported[target]!=first and s.originals[target][1]==baseline[target][1]
    assert s.apply({target:clip2,other:clip2})==[]
    report['same_session_clip_change']=True;report['original_baseline_retained']=True
    live=LiveTargetReader(s);report['restarted_local_nodes']=live.restart({target})
    assert s.restore_targets({target})==1
    assert s.read(baseline[target][0],104)==baseline[target][1]
    assert s.read(baseline[other][0],104)==s.imported[other]
    report['selective_restore_verified']=True
finally:
    s.restore()
    assert all(s.read(addr,104)==old for addr,old in baseline.values())
    s.close()
report['exact_final_restore']=2
Path('work/live_target_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
