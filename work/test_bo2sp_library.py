"""Offline conversion audit for a packaged BO2 library. No game access.

Usage: python work/test_bo2sp_library.py [sp|zombies|mw3]

Converts every 'BO2 SP' (or 'BO2 Zombies', or 'MW3 Actors') clip in the release catalog onto two BO2 MP body rigs
(bone names from the original dumped pb_ animations in work/bo2/common_mp),
then checks the encoded streams decode back to the same motion on exactly the
destination bones. Also counts where the direct-pelvis spine correction
applied. Writes work/bo2<kind>_library_validation.json (mw3_library_validation.json for mw3).
"""
import json,sys,time,collections
from pathlib import Path
WORK=Path(__file__).resolve().parent
sys.path.insert(0,str(WORK/'porter'))
from runtime import decode,load_clip,body_clip,adapt_tracks,adapt_spine_translation,flatten
from mw2_assets import unflatten

def normalized(value):
    if isinstance(value,dict):return {k:normalized(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [normalized(v) for v in value]
    return value
kind=sys.argv[1] if len(sys.argv)>1 else 'sp';game={'sp':'BO2 SP','zombies':'BO2 Zombies','mw3':'MW3 Actors'}[kind]
started=time.monotonic();release=WORK.parent/'outputs/BO2SPAnims'
rigs={name:[t['name'] for t in decode((WORK/'bo2/common_mp/xanim'/name).read_bytes())['tracks']] for name in ('pb_stand_alert','pb_death_run_stumble')}
clips=[x for x in json.loads((release/'library/catalog.json').read_text()) if x['game']==game]
assert clips,f'No {game} clips in the release catalog'
errors=[];corrected=0;static=0;missing=collections.Counter();zones=collections.Counter()
for item in clips:
    try:
        anim=load_clip(release/item['path']);assert body_clip(anim);zones[item['zone']]+=1;static+=not anim['frames']
        spine=next((t for t in anim['tracks'] if t['name']=='j_spinelower'),None)
        for names in rigs.values():
            adapted,skipped=adapt_tracks(anim,names);flat=flatten(adapted)
            rebuilt=unflatten({'frames':adapted['frames'],'fps':adapted['fps'],'loop':adapted['loop'],'kind':adapted['kind'],'counts':flat['counts']},names,{k:v for k,v in flat.items() if k!='counts'},adapted['notes'],adapted['delta'])
            assert [t['name'] for t in rebuilt['tracks']]==names,'Destination bone order changed'
            assert normalized(rebuilt['tracks'])==normalized(adapted['tracks']),'Decoded bone motion differs'
            missing.update(skipped)
        if spine and normalized(adapt_spine_translation(anim,spine,rigs['pb_stand_alert']))!=normalized(spine['trans']):corrected+=1
    except Exception as e:errors.append({'clip':item['path'],'name':item['name'],'error':f'{type(e).__name__}: {e}'})
result={'clips':len(clips),'zones':len(zones),'rigs':{k:len(v) for k,v in rigs.items()},'errors':errors[:50],'error_count':len(errors),
        'spine_corrected':corrected,'static_poses':static,'destination_bones_without_source_top':missing.most_common(10),'seconds':round(time.monotonic()-started,1)}
(WORK/('mw3_library_validation.json' if kind=='mw3' else f'bo2{kind}_library_validation.json')).write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='errors'}))
assert not errors,f'{len(errors)} clips failed'
