"""Any-key binding and per-action hotkeys. No game writes.

Drives the hook's event logic directly (no physical keys) and the core's binding logic
against an isolated copy of the release profile (work/hotkeys_test).
Writes work/hotkeys_validation.json.
"""
from pathlib import Path
import sys,json
from test_support import isolated_root,new_core,close
from replay_hotkey import HotkeyListener,key_name
result={}
def drain(listener):
    events=[]
    while not listener.events.empty():events.append(listener.events.get_nowait())
    return events

# Hook event logic, without a real keypress.
listener=HotkeyListener();listener.ready.wait(5)
try:
    listener.configure({0x76:'lock_target'},1234)
    listener._key_event(0x76,0,0,0x100,1234);listener._key_event(0x76,0,0,0x100,1234) # held key auto-repeats
    assert drain(listener)==[('press','lock_target',1234)];result['press_fires_once_while_held']=True
    listener._key_event(0x76,0,0,0x101,1234);listener._key_event(0x76,0,0,0x100,1234);listener._key_event(0x76,0,0,0x101,1234)
    assert drain(listener)==[('press','lock_target',1234)];result['press_fires_again_after_release']=True
    listener._key_event(0x76,0,0,0x100,999);listener._key_event(0x76,0,0,0x101,999)
    assert drain(listener)==[];result['ignored_unless_game_focused']=True
    listener.capture();listener._key_event(0x41,0x1E,0,0x100,0);listener._key_event(0x41,0x1E,0,0x101,0)
    assert drain(listener)==[('capture',0x41,'A')] and not listener.capturing;result['capture_reports_any_key']=True
    listener.capture();listener._key_event(0x1B,0x01,0,0x100,0)
    assert drain(listener)==[('cancel',)];result['escape_cancels_capture']=True
    assert key_name(0x75)=='F6' and key_name(0xA5)=='Right Alt';result['key_names']=[key_name(0x75),key_name(0xA5),key_name(0x41)]
finally:listener.stop();listener.thread.join(5)

def legacy(profile):profile['replay']={'key':'F6','enabled':True,'target':'','source':''};profile.pop('hotkeys',None);profile.pop('freelook',None) # Name only, no vk.
root=isolated_root('hotkeys_test',legacy)
app,ui=new_core()
try:
    assert app.apply_vk==0x75 and app.apply_name=='F6';result['legacy_f6_profile_loads']=True
    app.capture_action='apply_anim';app.assign_hotkey(0x77,'F8')
    saved=json.loads((root/'profile.json').read_text());assert saved['replay']['vk']==0x77 and saved['replay']['key']=='F8';result['apply_anim_any_key_saved']=True
    hits=[];app.register_action('stop_restore','Stop & restore',lambda:hits.append(1))
    app.capture_action='stop_restore';app.assign_hotkey(0x4B,'K')
    assert app.key_for('stop_restore')=='K' and app.bindings(active=True)[0x4B]=='stop_restore';result['action_hotkey_bound']=True
    app.run_action('stop_restore');assert hits==[1];result['hotkey_runs_action']=True
    app.register_action('disabled','Disabled',lambda:hits.append(2),enabled=lambda:False);app.run_action('disabled');assert hits==[1];result['disabled_action_ignored']=True
    app.capture_action='clear_selection';app.assign_hotkey(0x77,'F8')
    assert app.apply_vk==0 and app.apply_name=='None' and 'moved from Apply anim' in app.status;result['conflict_moves_key']=app.status
    app.capture_action='use_highlighted';app.assign_hotkey(0x57,'W')
    assert 'BO2 still receives' in app.status;result['game_key_warning']=True
    app.set_hotkey_options(replay_enabled=False);requests=[];app.request_replay=lambda:requests.append(1)
    app.run_action('apply_anim');assert not requests;result['disabled_apply_anim_ignored']=True
    app.clear_hotkey('use_highlighted');assert 'use_highlighted' not in app.hotkeys
    app.capture_action='apply_anim';app.assign_hotkey(0x75,'F6');app.set_hotkey_options(replay_enabled=True)
finally:close(app,ui)
app,ui=new_core()
try:
    assert app.apply_vk==0x75 and app.apply_name=='F6' and app.replay_enabled
    assert app.hotkeys=={'stop_restore':{'vk':0x4B,'name':'K'},'clear_selection':{'vk':0x77,'name':'F8'}},app.hotkeys;result['hotkeys_reload']=True
    assert app.bindings(active=True)=={0x4B:'stop_restore',0x77:'clear_selection',0x75:'apply_anim'};result['active_bindings']=True
finally:close(app,ui)
Path('work/hotkeys_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=1))
