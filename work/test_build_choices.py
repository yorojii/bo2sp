"""Build libraries: per-game choices. No game writes; extraction is stubbed.

Defaults tick only games whose folder is found and that have no clips yet; with everything
built, Build does nothing and says so; a ticked game is rebuilt alone while every other game
keeps its clips; choices reset after a build. Writes work/build_choices_validation.json.
"""
import json,collections
from pathlib import Path
from test_support import isolated_root,new_core,close
import library
result={}
isolated_root('build_choices_test')
app,ui=new_core()
try:
    rows={game:(found,count,ticked) for game,found,count,ticked in app.build_choices()};result['defaults']={g:{'found':f,'clips':c,'ticked':t} for g,(f,c,t) in rows.items()}
    assert all(not t for f,c,t in rows.values() if c) and all(not t for f,c,t in rows.values() if not f)
    assert rows['MW3 Actors'][0] and rows['MW3 Actors'][1]>0,'Expected MW3 installed and built here'
    app.reindex();assert 'Nothing to build' in app.status and not app.building;result['all_built_skips']=app.status
    calls=[];before=collections.Counter(x['game'] for x in app.catalog)
    def fake(folders,root,unlinker,log,stopped,progress,games=None):
        calls.append(games);clip=next(x for x in app.catalog if x['game']=='MW3 Actors')
        return [dict(clip)],[g for g in games],[]
    library.index_libraries=fake
    app.pick_build('MW3 Actors',True);assert dict((g,t) for g,f,c,t in app.build_choices())['MW3 Actors']
    app.reindex();ui.pump(3)
    while app.building:ui.pump(0.2)
    assert calls==[['MW3 Actors']],calls;after=collections.Counter(x['game'] for x in app.catalog)
    assert after['MW3 Actors']==1 and all(after[g]==n for g,n in before.items() if g!='MW3 Actors'),after
    result['only_ticked_game_rebuilt']=dict(after);result['status']=app.status
    assert not dict((g,t) for g,f,c,t in app.build_choices())['MW3 Actors'];result['choices_reset_after_build']=True
finally:close(app,ui)
Path('work/build_choices_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=1))
