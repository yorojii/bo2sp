from pathlib import Path
import sys,json
sys.path.insert(0,'work/porter')
import runtime_app as gui
final=Path('outputs/Yoroji Tool').resolve();root=Path('work/replay_settings_test').resolve();root.mkdir(exist_ok=True);(root/'state').mkdir(exist_ok=True);(root/'library').mkdir(exist_ok=True)
profile=json.loads((final/'profile.json').read_text());profile['mapping']={n:str(final/p) for n,p in profile['mapping'].items()};profile['mapping'].setdefault('pb_stand_alert',str(final/'library/clips/00000.xanim')) # Target must be mapped to stay selected.
(root/'profile.json').write_text(json.dumps(profile));catalog=json.loads((final/'library/catalog.json').read_text())
for item in catalog:item['path']=str(final/item['path'])
(root/'library/catalog.json').write_text(json.dumps(catalog));gui.ROOT=root;gui.STATE=root/'state';failures=[]
for stage in (0,1):
    app=gui.App();app.withdraw()
    def verify():
        try:
            if stage==0:
                app.capture_action='apply_anim';app.assign_hotkey(0x76,'F7');app.replay_enabled.set(False);app.replay_target='pb_stand_alert';app.replay_settings_changed()
                saved=json.loads((root/'profile.json').read_text());assert saved['replay']['key']=='F7' and saved['replay']['vk']==0x76 and saved['replay']['enabled'] is False and saved['replay']['target']=='pb_stand_alert'
            else:
                assert app.replay_key.get()=='F7' and app.apply_vk==0x76 and not app.replay_enabled.get() and app.replay_target=='pb_stand_alert'
                app.replay_path='';assert not app.request_replay() and app.session is None
        except Exception as e:failures.append(str(e))
        finally:app.close_app()
    app.after(250,verify);app.mainloop();assert not app.hotkey.is_alive()
assert not failures,failures
result={'binding_saved_and_reloaded':True,'replay_target_saved':True,'disabled_setting_saved':True,'no_clip_does_not_start_imports':True,'key_listener_closed':True}
Path('work/replay_settings_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
