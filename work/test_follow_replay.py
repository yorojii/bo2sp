"""Follow-mode target selection for the apply anim key. No game writes.

Uses synthetic live snapshots and a stubbed importer start. Writes work/follow_replay_validation.json.
"""
import json,time
from pathlib import Path
from test_support import isolated_root,new_core,close
root=isolated_root('follow_replay_test');result={};starts=[]
app,ui=new_core(start=lambda:starts.append(True))
try:
    index=next(i for i,x in enumerate(app.catalog) if x['game']=='MW2 Actors' and x['name']=='run_pain_stumble')
    app.choose_clip(index);source=app.catalog[index]['path'];assert app.replay_path==source;result['selection_without_use_button']=True
    app.set_follow(True)
    targets={'Idle':'pb_stand_alert','Running':'pb_pistol_run_fast','Crouched':'pb_crouch_alert','Prone':'pb_prone_aim'}
    for name,target in targets.items():
        if target not in app.targets:app.targets.append(target)
        app.target='pb_stand_alert';app.last_snapshot={'ready':True,'primary':{'target':target}};app.detected_at=time.monotonic()
        assert app.request_replay() and app.mapping[target]==source
        requests=[]
        while not app.restart_requests.empty():requests.append(app.restart_requests.get_nowait())
        assert requests[-1][0]==target and requests[-1][1]==source and requests[-1][2]
        result[name]=target
    app.set_follow(False);app.target='pb_stand_alert';app.last_snapshot={'ready':True,'primary':{'target':'pb_pistol_run_fast'}};app.detected_at=time.monotonic()
    assert app.request_replay() and app.restart_requests.get_nowait()[0]=='pb_stand_alert';result['locked_mode_uses_locked_target']=True
    app.last_snapshot={'ready':True,'primary':{'target':'pb_crouch_alert'}};app.detected_at=time.monotonic();app.set_locked(True)
    assert not app.follow_live and app.target=='pb_crouch_alert';app.set_locked(False);assert app.follow_live;result['lock_checkbox_locks_current_slot']=True
    saved=json.loads((root/'profile.json').read_text());assert saved['replay']['source'].endswith('.xanim') or saved['replay']['source'].endswith('.yanim')
    result['selected_source_persisted']=True;result['starts_importer_for_key_action']=len(starts)==5
    app.last_snapshot={'ready':False};assert not app.request_replay();result['no_match_does_not_apply']=True
finally:close(app,ui)
Path('work/follow_replay_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
