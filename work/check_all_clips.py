import sys,json,time,struct,collections
from pathlib import Path
sys.path.insert(0,'work/porter')
from runtime import Session,load_clip,adapt_tracks,flatten,adapt_spine_translation
from mw2_assets import unflatten

s=Session(int(sys.argv[1]));started=time.monotonic()
def names_for(target):
    old=s.assets[target][1];ids=struct.unpack('<'+'H'*old[33],s.read(int.from_bytes(old[64:68],'little'),old[33]*2))
    return [s.text(s.strings+i*24+4) for i in ids]
rigs={target:names_for(target) for target in ('pb_stand_alert','pb_stumble_pistol_walk_forward','pb_death_run_stumble')}
catalog=json.loads(Path('work/cod4_catalog.json').read_text())+json.loads(Path('work/mw2_catalog.json').read_text())
errors=[];checked=collections.Counter();static=0;three_d=0
def normalized(value):
    if isinstance(value,dict):return {k:normalized(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [normalized(v) for v in value]
    return value
def check(anim,names):
    adapted,missing=adapt_tracks(anim,names);flat=flatten(adapted)
    reconstructed=unflatten({'frames':adapted['frames'],'fps':adapted['fps'],'loop':adapted['loop'],'kind':adapted['kind'],'counts':flat['counts']},names,{k:v for k,v in flat.items() if k!='counts'},adapted['notes'],adapted['delta'])
    assert [t['name'] for t in reconstructed['tracks']]==names
    assert normalized(reconstructed['tracks'])==normalized(adapted['tracks']), 'Decoded bone motion differs'
    source={t['name']:t for t in anim['tracks']}
    for t in reconstructed['tracks']:
        if t['name'] not in source:continue
        old=source[t['name']];q=old['quat'];new=t['quat']
        assert normalized(t['trans'])==normalized(adapt_spine_translation(anim,old,names)), 'Translation motion differs'
        if q['type'] in (1,2):
            expected=q['values'] if q['type']==2 else [[0,0,*v] for v in q['values']]
            assert new['values']==expected or (len(expected)==1 and new['values']==expected*2)
            if len(q['indices'])>1:assert new['indices']==q['indices']
        elif q['type'] in (3,4):
            expected=q['values'][0] if q['type']==4 else [0,0,*q['values'][0]]
            assert all(v==expected for v in new['values'])
        else:assert all(v==[0,0,0,32767] for v in new['values'])
    return missing
for i,item in enumerate(catalog):
    try:
        anim=load_clip(item['path']);static+=not anim['frames'];three_d+=bool(anim['delta'] and anim['delta'].get('three_d'))
        for target,names in rigs.items():check(anim,names)
        checked[item['game']]+=1
    except Exception as e:errors.append({'game':item['game'],'name':item['name'],'zone':item['zone'],'error':str(e)})
    if (i+1)%500==0:print('Checked',i+1,'errors',len(errors),flush=True)
basics=json.loads(Path('work/project/names.json').read_text());basic_errors=[]
for target in basics:
    try:check(load_clip(Path('work/cod4/common_mp/xanim')/target),names_for(target))
    except Exception as e:basic_errors.append({'target':target,'error':str(e)})
report={'catalog_checked':dict(checked),'rigs_checked':{k:len(v) for k,v in rigs.items()},'errors':errors,'basic_checked':len(basics),'basic_errors':basic_errors,'static_poses':static,'three_d_root_clips':three_d,'seconds':round(time.monotonic()-started,2),'checks':['stable destination bone order','quaternion values preserved by bone name','translation motion preserved with actor spine basis correction','complete T6 stream inverse roundtrip']}
Path('work/all_clips_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps({**report,'errors':errors[:8]}),flush=True);s.close()
if errors or basic_errors:sys.exit(1)
