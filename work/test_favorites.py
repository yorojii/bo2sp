"""Favorites tab and saved replacement sets. No game writes.

Runs hidden GUI apps on an isolated copy of the release profile/catalog
(work/favorites_test), with dialogs stubbed and the importer never started.
Writes work/favorites_validation.json.
"""
from pathlib import Path
import sys,json
sys.path.insert(0,'work/porter')
import runtime_app as gui
final=Path('outputs/Yoroji Tool').resolve();root=Path('work/favorites_test').resolve();root.mkdir(exist_ok=True);(root/'state').mkdir(exist_ok=True);(root/'library').mkdir(exist_ok=True)
profile=json.loads((final/'profile.json').read_text());profile['mapping']={};profile.pop('favorites',None);profile.pop('saved_sets',None)
(root/'profile.json').write_text(json.dumps(profile));catalog=json.loads((final/'library/catalog.json').read_text())
for item in catalog:item['path']=str(final/item['path'])
(root/'library/catalog.json').write_text(json.dumps(catalog));gui.ROOT=root;gui.STATE=root/'state'
imported=root/'state/imported_clip.xanim';imported.write_bytes((final/'library/clips/00000.xanim').read_bytes()) # A non-library file in a set.
gui.simpledialog.askstring=lambda *a,**k:'Scene one';gui.messagebox.askyesno=lambda *a,**k:True
result={};failures=[]
def first_row(app,game):
    tree=app.panels[game][4];iid=tree.get_children()[0];tree.selection_set(iid);app.update();return iid
for stage in (0,1):
    app=gui.App();app.withdraw();app.start=lambda:None
    def verify():
        try:
            if stage==0:
                assert app.notebook.tab(app.notebook.tabs()[0],'text')=='Favorites' and not app.panels['Favorites'][4].get_children();result['favorites_tab_first_and_empty']=True
                iid=first_row(app,'CoD4');item=app.catalog[int(iid)];app.toggle_favorite('CoD4')
                assert app.clip_key(item) in app.favorites and app.panels['CoD4'][4].set(iid,'fav')=='★' and app.panels['Favorites'][4].get_children()==(iid,)
                result['star_from_library_tab']=app.clip_key(item)
                app.panels['Favorites'][4].selection_set(iid);app.toggle_favorite('Favorites')
                assert not app.favorites and app.panels['CoD4'][4].set(iid,'fav')=='' and not app.panels['Favorites'][4].get_children();result['remove_from_favorites_tab']=True
                a=first_row(app,'MW2 Actors');app.toggle_favorite('MW2 Actors');b=first_row(app,'BO2 Zombies');app.toggle_favorite('BO2 Zombies')
                app.panels['Favorites'][2].set('BO2 Zombies');assert app.panels['Favorites'][4].get_children()==(b,);app.panels['Favorites'][2].set('All')
                assert len(app.panels['Favorites'][4].get_children())==2;result['favorites_game_filter']=True
                app.panels['Favorites'][4].selection_set(a);app.choose_target('Favorites');assert app.replay_path==app.catalog[int(a)]['path'];result['favorite_selects_clip']=True
                app.mapping={'pb_stand_alert':app.catalog[int(a)]['path'],'pb_crouch_alert':app.catalog[int(b)]['path'],'pb_prone_aim':str(imported)}
                app.save_set();saved=app.saved_sets['Scene one']
                assert saved['pb_stand_alert']=={'clip':app.clip_key(app.catalog[int(a)])} and saved['pb_prone_aim']=={'path':'state\\imported_clip.xanim'},saved
                result['set_saved_by_clip_key']=saved
                expected=dict(app.mapping);app.clear();assert not app.mapping
                app.set_name.set('Scene one');app.load_set();assert app.mapping==expected,app.mapping;result['set_loads_back']=True
            else:
                assert len(app.favorites)==2 and len(app.panels['Favorites'][4].get_children())==2;result['favorites_reload']=True
                assert 'Scene one' in app.setbox.cget('values');result['sets_reload']=True
                app.saved_sets['Scene one']['pb_walk']={'clip':'CoD4/nowhere/missing_clip'};app.set_name.set('Scene one');app.load_set()
                assert len(app.mapping)==3 and 'missing clips skipped' in app.status.get();result['missing_clip_reported']=app.status.get()
                app.delete_set();assert 'Scene one' not in app.saved_sets and app.mapping;result['delete_keeps_current']=True
        except Exception as e:
            import traceback;failures.append(f'stage {stage}: '+traceback.format_exc(limit=-1))
        finally:app.close_app()
    app.after(300,verify);app.mainloop()
assert not failures,failures
Path('work/favorites_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=1))
