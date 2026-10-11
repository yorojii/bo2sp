"""Movement speed slider against a fake game. No game writes.

Checks: nothing is touched at 100%; percentages scale the game's own values; values the game
resets are rewritten; returning to 100% restores the originals exactly; switching game
restores quietly; errors are reported once per game; profile round trip and clamping.
Writes work/movement_validation.json.
"""
import json
from pathlib import Path
from test_support import isolated_root,new_core,close
import movement
from movement import Movement,clamp_percent
result={}

class FakeDvars:
    games={}
    def __init__(self,pid):
        if pid==999:raise RuntimeError('g_speed not found in this BO2 build')
        self.pid=pid;self.values=FakeDvars.games.setdefault(pid,{'speed':190});self.writes=0
    def get(self,key):return self.values[key]
    def set(self,key,value):self.values[key]=int(round(value)) if key=='speed' else float(value);self.writes+=1
    def close(self):pass
movement.MovementDvars=FakeDvars
import importlib;real=importlib.reload(movement) # Undo test_support's no-op for this test only.
real.MovementDvars=FakeDvars

def run(m,pid,percent):m.checked=0.0;m.update(pid,percent)
m=real.Movement();same={'speed':100}
run(m,1,same);assert m.dvars is None and 1 not in FakeDvars.games;result['untouched_at_100']=True
run(m,1,{'speed':150});g=FakeDvars.games[1]
assert g=={'speed':285},g;result['scaled']=dict(g)
g['speed']=190;run(m,1,{'speed':150});assert g['speed']==285;result['reapplied_after_game_reset']=True
run(m,1,same);assert g=={'speed':190} and m.dvars is None;result['restored_exactly']=True
run(m,1,{'speed':120});run(m,2,{'speed':120})
assert FakeDvars.games[1]['speed']==190 and FakeDvars.games[2]['speed']==228;result['switch_game_restores_old']=True
m.restore();assert FakeDvars.games[2]['speed']==190;result['close_restores']=True
run(m,999,{'speed':150});first=m.error;m.error=None;run(m,999,{'speed':150})
assert first and m.error is None;result['error_reported_once']=first
assert clamp_percent('speed',5)==10 and clamp_percent('speed',900)==300 and clamp_percent('speed','x')==100;result['clamped']=True

isolated_root('movement_test');app,ui=new_core()
try:
    app.set_movement(speed=175,jump=250);assert app.movement=={'speed':175} # Old keys are ignored.
    app.reset_movement();app.set_movement(speed=130)
finally:close(app,ui)
app,ui=new_core()
try:assert app.movement=={'speed':130},app.movement;result['profile_round_trip']=app.movement
finally:close(app,ui)
Path('work/movement_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=1))
