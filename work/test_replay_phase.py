import sys,time,json,struct
from pathlib import Path
sys.path.insert(0,'work/porter')
from runtime import Session,load_clip
from live_target import LiveTargetReader
s=Session(int(sys.argv[1]));reader=LiveTargetReader(s);target='pb_stand_alert';old=s.assets[target]
catalog=json.loads(Path('work/mw2_catalog.json').read_text());clip=next(x for x in catalog if x['name']=='run_pain_stumble')['path']
anim=load_clip(clip);duration=anim['frames']/anim['fps'];result={'clip':'MW2 run_pain_stumble','target':target,'duration':duration}
def phase():
    snap=reader.snapshot();item=next((x for x in snap.get('animations',[]) if x['target']==target),None)
    assert item is not None,'Stand still with the primary weapon for this replay test'
    return item['phase']
try:
    assert len(s.apply({target:clip}))==1
    reader.restart({target});time.sleep(duration+0.3);result['finished_phase']=phase()
    result['reset_nodes']=reader.restart({target});result['immediate_phase']=phase()
    time.sleep(0.15);result['phase_after_150ms']=phase()
    time.sleep(0.3);result['phase_after_450ms']=phase()
    assert result['finished_phase']>0.95 and result['immediate_phase']<0.15
    assert 0<result['phase_after_150ms']<0.5
    assert result['phase_after_450ms']>result['phase_after_150ms']
    result['playback_progress_verified']=True
finally:
    s.restore();assert s.read(old[0],104)==old[1];s.close()
Path('work/replay_phase_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
