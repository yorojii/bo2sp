"""Favorites and saved replacement sets. No game writes.

Drives core.Core on an isolated copy of the release profile/catalog (work/favorites_test),
with dialogs answered by FakeUI and the importer never started.
Writes work/favorites_validation.json.
"""
from pathlib import Path
import json
from test_support import isolated_root,new_core,close,FINAL
def fresh(profile):profile['mapping']={};profile.pop('favorites',None);profile.pop('saved_sets',None)
root=isolated_root('favorites_test',fresh)
imported=root/'state/imported_clip.xanim';imported.write_bytes((FINAL/'library/clips/00000.xanim').read_bytes()) # A non-library file in a set.
result={}
app,ui=new_core()
try:
    assert app.clips('Favorites')==[];result['favorites_start_empty']=True
    first=app.clips('CoD4')[0];app.toggle_favorite(first);key=app.clip_key(app.catalog[first])
    assert key in app.favorites and app.clips('Favorites')==[first];result['star_from_library_tab']=key
    app.toggle_favorite(first);assert not app.favorites and app.clips('Favorites')==[];result['unstar']=True
    a=app.clips('MW2 Actors')[0];b=app.clips('BO2 Zombies')[0];app.toggle_favorite(a);app.toggle_favorite(b)
    assert app.clips('Favorites',zone='BO2 Zombies')==[b] and sorted(app.clips('Favorites'))==sorted([a,b]) and 'BO2 Zombies' in app.zones('Favorites');result['favorites_game_filter']=True
    assert app.clips('Favorites',query=app.catalog[a]['name'])==[a];result['favorites_search']=True
    app.choose_clip(a);assert app.replay_path==app.catalog[a]['path'];result['favorite_selects_clip']=True
    app.mapping={'pb_stand_alert':app.catalog[a]['path'],'pb_crouch_alert':app.catalog[b]['path'],'pb_prone_aim':str(imported)}
    ui.text_answer='Scene one';assert app.save_set()=='Scene one';saved=app.saved_sets['Scene one']
    assert saved['pb_stand_alert']=={'clip':app.clip_key(app.catalog[a])} and saved['pb_prone_aim']=={'path':'state\\imported_clip.xanim'},saved
    result['set_saved_by_clip_key']=saved
    expected=dict(app.mapping);app.clear();assert not app.mapping
    app.load_set('Scene one');assert app.mapping==expected,app.mapping;result['set_loads_back']=True
    ui.confirm_answer=False;app.mapping={};app.load_set('Scene one');app.mapping={'x':'y'};app.load_set('Scene one');assert app.mapping=={'x':'y'};result['load_asks_before_replacing']=True
    ui.confirm_answer=True;app.mapping=dict(expected)
finally:close(app,ui)
app,ui=new_core()
try:
    assert len(app.favorites)==2 and len(app.clips('Favorites'))==2;result['favorites_reload']=True
    assert 'Scene one' in app.saved_sets;result['sets_reload']=True
    app.saved_sets['Scene one']['pb_walk']={'clip':'CoD4/nowhere/missing_clip'};app.load_set('Scene one')
    assert len(app.mapping)==3 and 'missing clips skipped' in app.status;result['missing_clip_reported']=app.status
    app.delete_set('Scene one');assert 'Scene one' not in app.saved_sets and app.mapping;result['delete_keeps_current']=True
finally:close(app,ui)
Path('work/favorites_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=1))
