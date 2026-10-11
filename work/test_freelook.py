"""Freelook key handling and settings. No game writes.

Drives the keyboard logic directly (no physical keys; SendInput is stubbed so the Alt
hand-back is never really injected), reads the camera dvars from a running BO2 if one is
open (read only), and checks the core saves, reloads and de-conflicts the freelook key
using an isolated profile (work/freelook_test). Writes work/freelook_validation.json.
"""
from pathlib import Path
import json
from test_support import isolated_root,new_core,close
import core,freelook
result={};injected=[]
class StubUser32:
    def __getattr__(self,name):return getattr(real,name)
    def SendInput(self,count,inputs,size):injected.append(inputs._obj.ki.vk);return 1
real=freelook.u;freelook.u=StubUser32()
look=freelook.Freelook();look.ready.wait(5)
try:
    k=look._key_event;look.configure(0x12,111,True)
    assert k(0xA4,0x104,False,111) is True and look.held;assert k(0xA4,0x104,False,111) is True # held auto-repeat
    assert k(0xA4,0x105,False,111) is True and not look.held;result['alt_hidden_from_bo2']=True
    assert k(0xA4,0x104,False,999) is False and not look.held and k(0xA4,0x105,False,999) is False;result['alt_untouched_outside_bo2']=True
    assert k(0xA4,0x104,False,111) is True and k(0x09,0x100,False,111) is False and injected==[0x12] and look.handed_back and not look.held
    assert k(0xA4,0x105,False,111) is False and not look.handed_back;result['alt_tab_hands_alt_back']=True
    assert k(0xA4,0x104,True,111) is False;result['injected_keys_pass']=True
    look.configure(0x12,111,False);assert k(0xA4,0x104,False,111) is False and k(0xA4,0x105,False,111) is False;result['disabled_passes_alt']=True
    look.configure(0x14,111,True);assert k(0xA4,0x104,False,111) is False and k(0xA4,0x105,False,111) is False
    assert k(0x14,0x100,False,111) is True and k(0x14,0x101,False,111) is True;result['rebound_key_only']=True
finally:look.stop();freelook.u=real
assert not look.is_alive();result['hooks_closed']=True

pids=core.game_pids(json.loads(Path('outputs/Yoroji Tool/profile.json').read_text())['bo2'])
if len(pids)==1:
    camera=freelook.CameraDvars(pids[0])
    try:result['live_camera_read']={'angle':camera.get(camera.angle),'range':camera.get(camera.range),'limits':[list(v) for v in camera.limits.values()]}
    finally:camera.close()
else:result['live_camera_read']='skipped: BO2 not running'

isolated_root('freelook_test',lambda profile:profile.pop('freelook',None))
app,ui=new_core()
try:
    assert app.freelook_vk==0x12 and app.freelook_name=='Alt' and app.freelook_enabled;result['default_alt']=True
    assert all(app.bindings().get(vk)=='freelook' for vk in (0x12,0xA4,0xA5)) and 0x12 not in app.bindings(active=True);result['alt_reserved_not_dispatched']=True
    app.capture_action='apply_anim';app.assign_hotkey(0xA4,'Alt')
    assert app.freelook_vk==0 and app.freelook_name=='None' and 'moved from Freelook' in app.status;result['conflict_moves_alt']=app.status
    app.capture_action='freelook';app.assign_hotkey(0x43,'C')
    assert app.freelook_vk==0x43 and "won't receive" in app.status;result['freelook_game_key_note']=app.status
    app.set_hotkey_options(freelook_speed='0.3',freelook_enabled=False)
    app.capture_action='apply_anim';app.assign_hotkey(0x75,'F6')
finally:close(app,ui)
app,ui=new_core()
try:
    assert app.freelook_vk==0x43 and app.freelook_name=='C' and not app.freelook_enabled and app.freelook_speed==0.3;result['settings_reload']=True
    assert app.clamp_speed('fast')==0.15 and app.clamp_speed(9)==2.0;result['bad_speed_falls_back']=True
finally:close(app,ui)
Path('work/freelook_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=1))
