"""Any-key binding and right-click button hotkeys. No game writes.

Runs hidden GUI apps against an isolated copy of the release profile/catalog
(work/hotkeys_test) and drives the hook's event logic directly, so no physical
keys are needed. Writes work/hotkeys_validation.json.
"""
from pathlib import Path
import sys,json
sys.path.insert(0,'work/porter')
import runtime_app as gui
from replay_hotkey import HotkeyListener,key_name
final=Path('outputs/Yoroji Tool').resolve();root=Path('work/hotkeys_test').resolve();root.mkdir(exist_ok=True);(root/'state').mkdir(exist_ok=True);(root/'library').mkdir(exist_ok=True)
profile=json.loads((final/'profile.json').read_text());profile['mapping']={n:str(final/p) for n,p in profile['mapping'].items()}
profile['replay']={'key':'F6','enabled':True,'target':'','source':''};profile.pop('hotkeys',None) # Legacy profile: name only, no vk.
(root/'profile.json').write_text(json.dumps(profile));catalog=json.loads((final/'library/catalog.json').read_text())
for item in catalog:item['path']=str(final/item['path'])
(root/'library/catalog.json').write_text(json.dumps(catalog));gui.ROOT=root;gui.STATE=root/'state'
result={};failures=[]
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

for stage in (0,1):
    app=gui.App();app.withdraw();app.start=lambda:None # Never start the importer from this test.
    def verify():
        try:
            if stage==0:
                assert app.apply_vk==0x75 and app.replay_key.get()=='F6';result['legacy_f6_profile_loads']=True
                app.capture_action='apply_anim';app.assign_hotkey(0x77,'F8')
                saved=json.loads((root/'profile.json').read_text());assert saved['replay']['vk']==0x77 and saved['replay']['key']=='F8'
                result['apply_anim_any_key_saved']=True
                hits=[];button=app.actions['lock_target'][0];button.configure(command=lambda:hits.append(1))
                app.capture_action='lock_target';app.assign_hotkey(0x4B,'K')
                assert 'K' in str(button.cget('text')) and app.bindings(active=True)[0x4B]=='lock_target';result['button_hotkey_label']=str(button.cget('text'))
                app.run_action('lock_target');assert hits==[1];result['hotkey_presses_button']=True
                app.capture_action='clear_selection';app.assign_hotkey(0x77,'F8')
                assert app.apply_vk==0 and app.replay_key.get()=='None' and 'moved from Apply anim' in app.status.get();result['conflict_moves_key']=app.status.get()
                app.capture_action='use_highlighted';app.assign_hotkey(0x57,'W')
                assert 'BO2 still receives' in app.status.get();result['game_key_warning']=True
                app.replay_enabled.set(False);requests=[];app.request_replay=lambda:requests.append(1)
                app.run_action('apply_anim');assert not requests;result['disabled_apply_anim_ignored']=True
                app.clear_hotkey('use_highlighted');assert 'use_highlighted' not in app.hotkeys
                app.capture_action='apply_anim';app.assign_hotkey(0x75,'F6');app.replay_enabled.set(True);app.save()
            else:
                assert app.apply_vk==0x75 and app.replay_key.get()=='F6'
                assert app.hotkeys=={'lock_target':{'vk':0x4B,'name':'K'},'clear_selection':{'vk':0x77,'name':'F8'}},app.hotkeys
                assert '[K]' in str(app.actions['lock_target'][0].cget('text'));result['hotkeys_reload']=True
                assert app.bindings(active=True)=={0x4B:'lock_target',0x77:'clear_selection',0x75:'apply_anim'};result['active_bindings']=True
        except Exception as e:failures.append(f'stage {stage}: {type(e).__name__}: {e}')
        finally:app.close_app()
    app.after(250,verify);app.mainloop();assert not app.hotkey.is_alive()
assert not failures,failures
Path('work/hotkeys_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=1))
