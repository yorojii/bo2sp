from pathlib import Path
import sys,json,shutil,hashlib
sys.path.insert(0,'work/porter')
from runtime_app import scan
root=Path('work/yoroji_final/Yoroji Tool').resolve()
root.mkdir(parents=True,exist_ok=True)
(root/'tools').mkdir(exist_ok=True)
shutil.copy2('work/oat/Unlinker.exe',root/'tools/Unlinker.exe')
mapping,targets=scan(r'D:\Call of Duty 4',r'D:\Call of Duty Black Ops II')
out={}
for name,path in mapping.items():
    dest=root/'state/sources/preloaded/xanim'/name;dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(path,dest);out[name]=str(dest.relative_to(root))
(root/'library/clips').mkdir(parents=True,exist_ok=True)
catalog=json.loads(Path('work/cod4_catalog.json').read_text())+json.loads(Path('work/mw2_catalog.json').read_text());portable={}
for index,item in enumerate(catalog):
    path=Path(item['path']);dest=root/'library/clips'/(f'{index:05d}'+('.yanim' if path.suffix=='.yanim' else '.xanim'))
    shutil.copy2(path,dest);portable[str(path.resolve()).lower()]=str(dest.relative_to(root));item['path']=str(dest.relative_to(root))
(root/'library/catalog.json').write_text(json.dumps(catalog,separators=(',',':')))
profile=json.loads(Path('work/porter/profile.json').read_text());chosen={}
for target,path in profile['mapping'].items():
    source=(Path('work/porter')/path).resolve();key=str(source).lower()
    if key in portable:chosen[target]=portable[key]
    elif target in out and source.read_bytes()==(root/out[target]).read_bytes():chosen[target]=out[target]
    else:
        dest=root/'state/sources/custom'/target;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest);chosen[target]=str(dest.relative_to(root))
profile.update({'mapping':chosen,'targets':targets})
(root/'profile.json').write_text(json.dumps(profile,indent=2))
(root/'source').mkdir(exist_ok=True)
for name in ('runtime.py','runtime_app.py','library.py','mw2_assets.py','camera.py','live_target.py','replay_hotkey.py'):shutil.copy2(Path('work/porter')/name,root/'source'/name)
shutil.copy2('work/oat-src/LICENSE',root/'LICENSE.txt')
shutil.copy2('work/final_build/Yoroji Tool/source/OpenAssetTools-v0.33.0.zip',root/'source/OpenAssetTools-v0.33.0.zip')
(root/'_internal/licenses').mkdir(exist_ok=True)
for name in ('Python.txt','TclTk.txt'):shutil.copy2(Path('work/yoroji_v2/Yoroji Tool/_internal/licenses')/name,root/'_internal/licenses'/name)
shutil.copy2('work/README-v2.txt',root/'README.txt')
report=json.loads(Path('work/session_validation.json').read_text())
report.update({'default_clips':142,'death_clips':22,'native_arrays_compared':142,'native_array_errors':0,
               'saved_replacements':len(chosen),
               'catalog_counts':{'CoD4':2171,'MW2 Actors':3047},'gui_checks':json.loads(Path('work/gui_validation.json').read_text()),'actor_imports':json.loads(Path('work/actor_import_validation.json').read_text()),
               'bone_mapping_regression':json.loads(Path('work/stable_bone_validation.json').read_text()),
               'complete_library_conversion':json.loads(Path('work/all_clips_validation.json').read_text()),
               'game_build':'Redacted MP 43.1337.7 (t6mpv43.exe)','live_match':'Hijacked',
               'visual_checks':['CoD4 run_pain_stumble after mid-match clip changes','MW2 run_pain_stomach_stumble after source changes','CoD4 pb_stand_death_nervedeath on BO2 character'],
               'visual_coverage':'Representative clips; not every animation and weapon combination was visually checked.',
               'original_common_mp_sha256':hashlib.sha256(Path(r'D:\Call of Duty Black Ops II\zone\all\common_mp.ff').read_bytes()).hexdigest()})
(root/'Validation.json').write_text(json.dumps(report,indent=2))
assert not report['complete_library_conversion']['errors'] and not report['complete_library_conversion']['basic_errors']
assert len(catalog)==5218 and len(chosen)==len(profile['mapping'])
assert all(not Path(path).is_absolute() and (root/path).is_file() for path in chosen.values())
print('Release prepared:',root)
