from pathlib import Path
import hashlib,json,shutil

workspace=Path(__file__).resolve().parent.parent
root=workspace/'outputs/BO2SPAnims'
build=workspace/'work/yoroji_live_build/BO2SPAnims'
assert root.is_dir() and build.is_dir()
profile=(root/'profile.json').read_bytes()
recovery=workspace/'work/recovery/BO2SPAnims-before-live-target.exe'
if not recovery.exists() and (root/'BO2SPAnims.exe').exists():shutil.copy2(root/'BO2SPAnims.exe',recovery)
shutil.copy2(build/'BO2SPAnims.exe',root/'BO2SPAnims.exe')
for source in (build/'_internal').rglob('*'):
    if not source.is_file():continue
    target=root/'_internal'/source.relative_to(build/'_internal')
    if not target.is_file() or source.read_bytes()!=target.read_bytes():
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
for name in ('runtime.py','core.py','bo2spanims.py','library.py','mw2_assets.py','camera.py','live_target.py','replay_hotkey.py','freelook.py','movement.py','logfile.py'):
    shutil.copy2(workspace/'work/porter'/name,root/'source'/name)
shutil.copytree(workspace/'work/porter/assets',root/'source/assets',dirs_exist_ok=True)
shutil.copy2(workspace/'work/README-v2.txt',root/'README.txt')
report=json.loads((root/'Validation.json').read_text())
report.update({
    'saved_replacements':len(json.loads(profile)['mapping']),
    'live_target_detection':json.loads((workspace/'work/live_target_validation.json').read_text()),
    'live_target_gui':json.loads((workspace/'work/live_gui_validation.json').read_text()),
    'live_target_observed_states':json.loads((workspace/'work/live_state_validation.json').read_text()),
    'live_target_notes':'Live runtime detection, hot clip changes, playback restart and exact original restoration were checked. Death/corpse target detection has not had a dedicated live test.'
})
for key,name in (
    ('memory_arena_import','allocation_probe.json'),
    ('memory_arena_failure_recovery','arena_rollback_validation.json'),
    ('packaged_live_import','packaged_import_validation.json'),
    ('packaged_live_restore','packaged_restore_validation.json'),
    ('replay_playback','replay_phase_validation.json'),
    ('replay_hotkey','replay_hotkey_validation.json'),
    ('follow_replay','follow_replay_validation.json'),
    ('replay_settings','replay_settings_validation.json'),
    ('spine_alignment','spine_alignment_validation.json'),
    ('complete_library_conversion','all_clips_validation.json'),
    ('bo2sp_library','bo2sp_library_validation.json'),
    ('bo2zombies_library','bo2zombies_library_validation.json'),
    ('hotkeys','hotkeys_validation.json'),
    ('f6_live','f6_live_validation.json'),
):
    testfile=workspace/'work'/name
    if testfile.is_file():report[key]=json.loads(testfile.read_text())
report['executable_sha256']=hashlib.sha256((root/'BO2SPAnims.exe').read_bytes()).hexdigest()
(root/'Validation.json').write_text(json.dumps(report,indent=2))
assert (root/'profile.json').read_bytes()==profile
assert (root/'BO2SPAnims.exe').read_bytes()==(build/'BO2SPAnims.exe').read_bytes()
catalog=json.loads((root/'library/catalog.json').read_text())
counts={game:sum(x['game']==game for x in catalog) for game in ('CoD4','MW2 Actors','BO2 SP','BO2 Zombies')}
assert counts['CoD4']==2171 and counts['MW2 Actors']==3047 and len(catalog)==sum(counts.values())
assert all(not Path(x['path']).is_absolute() and (root/x['path']).is_file() for x in catalog)
for path in json.loads(profile)['mapping'].values():assert (root/path).is_file()
ff=Path(r'F:\Games\Call of Duty Black Ops IIOLD\zone\all\common_mp.ff')
assert hashlib.sha256(ff.read_bytes()).hexdigest()==report['original_common_mp_sha256']
print(json.dumps({'deployed':str(root/'BO2SPAnims.exe'),'library_clips':len(catalog),'saved_replacements':report['saved_replacements'],'profile_preserved':True,'original_fastfile_unchanged':True,'sha256':report['executable_sha256']}))
