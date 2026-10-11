"""Fresh-install one-click library build. Reads game files only; no game memory writes.

Phase A: an empty folder (tools only, no profile, no library) detects the game folders and
builds the libraries once; BO2 SP, BO2 Zombies and MW3 Actors must match the release library clip for
clip (same game/zone/name keys and identical bytes).
Phase B: the same folder is given the full release catalog and a mapping, then built again
(per-zone cache, so fast): games that aren't installed keep their clips, and the mapping is
re-pointed at the rebuilt files by game/zone/name.
Writes work/fresh_install_validation.json. Slow: the first build extracts every BO2 zone.
"""
import hashlib,json,shutil,sys,time
from pathlib import Path
sys.path.insert(0,'work/porter')
import core
from test_support import FakeUI,close
release=Path('outputs/BO2SPAnims').resolve();root=Path('work/fresh_install_test').resolve()
phase_b_only='phase-b' in sys.argv # Reuse the folder and cache from a previous full run.
if root.exists() and not phase_b_only:shutil.rmtree(root)
if not phase_b_only:(root/'tools').mkdir(parents=True);shutil.copy2(release/'tools/Unlinker.exe',root/'tools/Unlinker.exe')
core.ROOT=root;core.TOOLS=root/'tools';core.STATE=root/'state';core.STATE.mkdir(exist_ok=True);result={}
def build(app,ui,limit=3600):
    app.reindex();start=time.monotonic();end=start+limit
    while (app.building or ui.queue) and time.monotonic()<end:ui.pump(0.5)
    assert not app.building,'build did not finish';return round(time.monotonic()-start,1)
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

ui=FakeUI();app=core.Core(ui) if not phase_b_only else None
try:
    if phase_b_only:raise SystemExit
    app.start=lambda:None
    ui.pump(0.2);assert app.bo2 and core.valid_folder('bo2',app.bo2) and not app.catalog;result['fresh_detects_bo2']=app.bo2
    assert core.valid_folder('mw3',app.mw3),app.mw3;result['fresh_detects_mw3']=app.mw3
    result['fresh_build_seconds']=build(app,ui);result['fresh_status']=app.status
    released={app.clip_key(x):x for x in json.loads((release/'library/catalog.json').read_text()) if x['game'] in ('BO2 SP','BO2 Zombies','MW3 Actors')}
    built={app.clip_key(x):x for x in app.catalog if x['game'] in ('BO2 SP','BO2 Zombies','MW3 Actors')}
    assert set(built)==set(released),(len(built),len(released),sorted(set(built)^set(released))[:5])
    mismatched=[key for key in built if digest(built[key]['path'])!=digest(release/released[key]['path'])]
    assert not mismatched,mismatched[:5]
    result['fresh_matches_release']={**{g:sum(x['game']==g for x in built.values()) for g in ('BO2 SP','BO2 Zombies','MW3 Actors')},'byte_identical':True}
    result['skipped_games_reported']=[line for line in ui.logs if 'skipped' in line]
    result['library_size_mb']=round(sum(f.stat().st_size for f in (root/'library').rglob('*') if f.is_file())/2**20,1)
except SystemExit:pass
finally:
    if app:close(app,ui)

# Phase B: an existing install (release catalog + mapping) rebuilt from the cache.
catalog=json.loads((release/'library/catalog.json').read_text())
for item in catalog:item['path']=str(release/item['path']) # Absolute, so the release clips stay readable.
(root/'library/catalog.json').write_text(json.dumps(catalog))
sp=next(x for x in catalog if x['game']=='BO2 SP');cod4=next(x for x in catalog if x['game']=='CoD4')
(root/'profile.json').write_text(json.dumps({'cod4':'','mw2':'','bo2':'','mapping':{'pb_stand_alert':sp['path'],'pb_crouch_alert':cod4['path']},'targets':[],'replay':{'key':'F6','vk':0x75,'enabled':True,'target':'pb_stand_alert','source':sp['path']}}))
ui=FakeUI();app=core.Core(ui);app.start=lambda:None
try:
    ui.pump(0.2);result['rebuild_seconds']=build(app,ui)
    counts={game:sum(x['game']==game for x in app.catalog) for game in core.GAMES};result['rebuild_counts']=counts
    assert counts['CoD4']==2171 and counts['MW2 Actors']==3047,counts;result['missing_games_keep_clips']=True
    key=lambda path:next(app.clip_key(x) for x in app.catalog if x['path']==path)
    assert key(app.mapping['pb_stand_alert'])==f"BO2 SP/{sp['zone']}/{sp['name']}" and str(root) in app.mapping['pb_stand_alert'];result['mapping_repointed_to_rebuilt_clip']=True
    assert app.mapping['pb_crouch_alert']==cod4['path'];result['kept_game_mapping_unchanged']=True
    assert app.replay_path==app.mapping['pb_stand_alert'];result['apply_anim_source_repointed']=True
finally:close(app,ui)
out=Path('work/fresh_install_validation.json');previous=json.loads(out.read_text()) if phase_b_only and out.exists() else {}
out.write_text(json.dumps({**previous,**result},indent=2));print(json.dumps(result,indent=1))
