import sys,json,time,traceback
from pathlib import Path
sys.path.insert(0,'work/porter')
from runtime_app import App
from runtime import Session
app=App();result={};started=time.monotonic();original_mapping=dict(app.mapping)
try:
    assert [app.notebook.tab(t,'text') for t in app.notebook.tabs()]==['CoD4','MW2 Actors','Selected replacements']
    assert len(app.catalog)==5218
    tree=app.panels['MW2 Actors'][4];app.panels['MW2 Actors'][0].set('heat_run_loop')
    index=next(i for i,x in enumerate(app.catalog) if x['game']=='MW2 Actors' and x['name']=='heat_run_loop')
    assert str(index) in tree.get_children()
    tree.selection_set(str(index));app.target.set('pb_stand_alert');app.use_clip('MW2 Actors')
    assert app.mapping['pb_stand_alert']==app.catalog[index]['path']
    app.save();result['tabs_and_search']=True;result['source_selection']=True
    app.start()
except Exception:
    traceback.print_exc();app.destroy();raise
def poll():
    try:
        if time.monotonic()-started>180:raise RuntimeError('App integration test timed out: '+app.status.get())
        if 'baseline' not in result:
            if app.session and len(app.session.imported)==142:
                result['baseline']={n:(a,b.hex()) for n,(a,b) in app.session.originals.items()};result['pid']=app.session.pid
                result['mixed_import_count']=142;app.stop();app.after(250,poll);return
            if app.worker and not app.worker.is_alive():raise RuntimeError(app.status.get())
        elif app.idle():
            s=Session(result['pid'])
            assert all(s.read(a,104)==bytes.fromhex(b) for a,b in result['baseline'].values())
            s.close();result['restore_verified']=142;result.pop('baseline')
            app.mapping=original_mapping;app.save();app.close_app()
            Path('work/gui_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True);return
        app.after(250,poll)
    except Exception:
        traceback.print_exc();app.stop();app.close_app();raise
app.after(250,poll);app.mainloop()
