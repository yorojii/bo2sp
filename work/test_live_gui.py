import sys,json,time,traceback
from pathlib import Path
sys.path.insert(0,'work/porter')
import runtime_app as gui
from runtime import Session

final=Path('outputs/Yoroji Tool').resolve();root=Path('work/live_gui_test').resolve();root.mkdir(exist_ok=True);(root/'state').mkdir(exist_ok=True);(root/'library').mkdir(exist_ok=True)
profile=json.loads((final/'profile.json').read_text());profile['mapping']={k:str((final/v).resolve()) for k,v in profile['mapping'].items()}
(root/'profile.json').write_text(json.dumps(profile));catalog=json.loads((final/'library/catalog.json').read_text())
for item in catalog:item['path']=str((final/item['path']).resolve())
(root/'library/catalog.json').write_text(json.dumps(catalog));gui.ROOT=root;gui.STATE=root/'state'
app=gui.App();app.withdraw();result={};stage=0;started=time.monotonic();baseline={};target=None;failure=None
def poll():
    global stage,baseline,target,failure
    try:
        if time.monotonic()-started>60:raise RuntimeError('GUI live test timed out: '+app.status.get())
        if stage==0 and app.last_snapshot.get('ready'):
            assert [app.notebook.tab(t,'text') for t in app.notebook.tabs()]==['CoD4','MW2 Actors','Selected replacements','Live target']
            app.lock_current();target=app.target.get();assert not app.follow_live.get() and app.live_lock
            assert target==app.last_snapshot['primary']['target'];result['detected_and_locked']=target
            s=Session(gui.game_pids(app.bo2.get())[0]);baseline={n:s.assets[n] for n in set(app.mapping)|{target}};s.close()
            index=next(i for i,x in enumerate(app.catalog) if x['game']=='CoD4' and x['name']=='run_pain_stumble')
            app.panels['CoD4'][0].set('run_pain_stumble');app.panels['CoD4'][4].selection_set(str(index));app.use_clip('CoD4');stage=1
        elif stage==1 and app.session and app.session.imported_paths.get(target):
            assert app.session.originals[target][1]==baseline[target][1]
            index=next(i for i,x in enumerate(app.catalog) if x['game']=='MW2 Actors' and x['name']=='heat_run_loop')
            app.panels['MW2 Actors'][0].set('heat_run_loop');app.panels['MW2 Actors'][4].selection_set(str(index))
            assert app.target.get()==target
            app.use_clip('MW2 Actors');result['first_import_count']=len(app.session.imported);stage=2
        elif stage==2 and app.session and app.session.imported_paths.get(target,(None,))[0]==str(Path(app.mapping[target]).resolve()):
            assert app.worker.is_alive();assert app.session.originals[target][1]==baseline[target][1]
            result['updated_while_active']=True;app.tree.selection_set(target);app.remove();stage=3
        elif stage==3 and app.session and target not in app.session.imported:
            assert app.session.read(baseline[target][0],104)==baseline[target][1]
            result['removed_target_restored']=True;app.clear();stage=4
        elif stage==4 and app.session and not app.session.imported:
            assert all(app.session.read(a,104)==h for a,h in baseline.values())
            result['cleared_without_default_reimport']=True;result['exact_restore_count']=len(baseline)
            app.stop();stage=5
        elif stage==5 and app.idle():
            result['observer_still_detects_after_stop']=app.last_snapshot.get('ready',False)
            assert app.status.get()=='Original animation entries restored. Live target detection continues.'
            result['stop_completion_message']=True
            app.close_app();Path('work/live_gui_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True);return
        app.after(100,poll)
    except Exception:
        failure=traceback.format_exc();print(failure,flush=True);app.close_app()
app.after(100,poll);app.mainloop()
if failure:sys.exit(1)
