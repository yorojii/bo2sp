"""Crash-safe profile saving and backup recovery. No game writes.

Uses an isolated profile copy (work/profile_safety_test). Simulates a crash during a
save (the final rename fails) and a corrupted profile.json on startup.
Writes work/profile_safety_validation.json.
"""
import json,os
from pathlib import Path
from test_support import isolated_root,new_core,close
import core
root=isolated_root('profile_safety_test');profile=root/'profile.json';backup=root/'profile.json.bak';result={}
for leftover in (backup,root/'profile.json.tmp'):leftover.unlink(missing_ok=True)
app,ui=new_core()
try:
    app.favorites.add('CoD4/test/first');app.save()
    first=json.loads(profile.read_text());assert 'CoD4/test/first' in first['favorites'] and backup.exists() and not (root/'profile.json.tmp').exists()
    result['save_keeps_backup_and_no_temp_file']=True
    good=profile.read_bytes();real=os.replace
    def crash(src,dst):
        if str(src).endswith('profile.json.tmp'):raise OSError('simulated crash before the rename')
        return real(src,dst)
    core.os.replace=crash
    try:
        app.favorites.add('CoD4/test/second')
        try:app.save();raise AssertionError('save should have failed')
        except OSError:pass
    finally:core.os.replace=real
    assert json.loads(profile.read_text())['favorites']==first['favorites'];result['crash_leaves_last_complete_profile']=True
    app.save()
finally:close(app,ui)
saved=json.loads(profile.read_text());assert 'CoD4/test/second' in saved['favorites']
profile.write_text(profile.read_text()[:40]) # Corrupt: truncated mid-file, like a partial write.
app,ui=new_core()
try:
    ui.pump(0.2)
    assert 'CoD4/test/first' in app.favorites and app.bo2==saved['bo2'];result['corrupt_profile_loads_backup']=sorted(app.favorites)[:3]
    assert any('backup' in line for line in ui.logs),ui.logs;result['user_told_about_backup']=[l for l in ui.logs if 'backup' in l][:2]
    app.save();assert json.loads(profile.read_text())['bo2']==saved['bo2'];result['next_save_repairs_profile']=True
finally:close(app,ui)
Path('work/profile_safety_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=1))
