import sys,json,time
from pathlib import Path
sys.path.insert(0,'work/porter')
import runtime_app as gui
final=Path('outputs/Yoroji Tool').resolve();root=Path('work/follow_replay_test').resolve();root.mkdir(exist_ok=True);(root/'state').mkdir(exist_ok=True);(root/'library').mkdir(exist_ok=True)
profile=json.loads((final/'profile.json').read_text());profile['mapping']={n:str(final/p) for n,p in profile['mapping'].items()}
(root/'profile.json').write_text(json.dumps(profile));catalog=json.loads((final/'library/catalog.json').read_text())
for item in catalog:item['path']=str(final/item['path'])
(root/'library/catalog.json').write_text(json.dumps(catalog));gui.ROOT=root;gui.STATE=root/'state';app=gui.App();app.withdraw();result={};errors=[];starts=[]
app.start=lambda:starts.append(True) # Test target selection without mutating BO2.
def check():
    try:
        index=next(i for i,x in enumerate(app.catalog) if x['game']=='MW2 Actors' and x['name']=='run_pain_stumble')
        app.panels['MW2 Actors'][0].set('run_pain_stumble');app.panels['MW2 Actors'][4].selection_set(str(index));app.choose_target('MW2 Actors')
        source=app.catalog[index]['path'];assert app.replay_path==source
        result['selection_without_use_button']=True
        app.follow_live.set(True)
        targets={'Idle':'pb_stand_alert','Running':'pb_pistol_run_fast','Crouched':'pb_crouch_alert','Prone':'pb_prone_aim'}
        for label,target in targets.items():
            assert target in app.targets
            app.target.set('pb_stand_alert');app.last_snapshot={'ready':True,'primary':{'target':target}};app.detected_at=time.monotonic()
            assert app.request_replay() and app.mapping[target]==source
            requests=[]
            while not app.restart_requests.empty():requests.append(app.restart_requests.get_nowait())
            assert requests[-1][0]==target and requests[-1][1]==source and requests[-1][2]
            result[label]=target
        app.follow_live.set(False);app.target.set('pb_stand_alert');app.last_snapshot={'ready':True,'primary':{'target':'pb_pistol_run_fast'}};app.detected_at=time.monotonic()
        assert app.request_replay() and app.restart_requests.get_nowait()[0]=='pb_stand_alert';result['locked_mode_uses_locked_target']=True
        saved=json.loads((root/'profile.json').read_text());assert saved['replay']['source']==source
        result['selected_source_persisted']=True;result['starts_importer_for_key_action']=len(starts)==5
        app.last_snapshot={'ready':False};assert not app.request_replay();result['no_match_does_not_apply']=True
    except Exception as e:errors.append(str(e))
    finally:app.close_app()
app.after(250,check);app.mainloop();assert not errors,errors
Path('work/follow_replay_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
