"""Apply anim hotkey settings persist and reload. No game writes.

Writes work/replay_settings_validation.json.
"""
from pathlib import Path
import json
from test_support import isolated_root,new_core,close
def seed(profile):profile['mapping'].setdefault('pb_stand_alert',str(Path('outputs/BO2SP/library/clips/00000.xanim').resolve())) # Target must be mapped to stay selected.
root=isolated_root('replay_settings_test',seed)
app,ui=new_core()
try:
    app.capture_action='apply_anim';app.assign_hotkey(0x76,'F7');app.set_hotkey_options(replay_enabled=False);app.replay_target='pb_stand_alert';app.save()
    saved=json.loads((root/'profile.json').read_text());assert saved['replay']['key']=='F7' and saved['replay']['vk']==0x76 and saved['replay']['enabled'] is False and saved['replay']['target']=='pb_stand_alert'
finally:close(app,ui)
starts=[];app,ui=new_core(start=lambda:starts.append(1))
try:
    assert app.apply_name=='F7' and app.apply_vk==0x76 and not app.replay_enabled and app.replay_target=='pb_stand_alert'
    app.replay_path='';assert not app.request_replay() and app.session is None and not starts
finally:close(app,ui)
result={'binding_saved_and_reloaded':True,'replay_target_saved':True,'disabled_setting_saved':True,'no_clip_does_not_start_imports':True,'key_listener_closed':True}
Path('work/replay_settings_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
