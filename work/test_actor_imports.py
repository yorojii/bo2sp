import sys,json
from pathlib import Path
sys.path.insert(0,'work/porter')
from runtime import Session,load_clip,flatten
pid=int(sys.argv[1]);s=Session(pid)
cod4=json.loads(Path('work/cod4_catalog.json').read_text());mw2=json.loads(Path('work/mw2_catalog.json').read_text())
chosen=[next(x for x in cod4 if x['zone']=='coup'),next(x for x in mw2 if x['name']=='heat_run_loop'),next(x for x in mw2 if x['name']=='death_run_forward_crumple'),next(x for x in mw2 if load_clip(x['path']).get('delta') and load_clip(x['path'])['delta'].get('three_d'))]
results=[]
for clip in chosen:
    addr,old=s.assets['pb_stand_alert']
    try:
        report=s.apply({'pb_stand_alert':clip['path']})
        assert len(report)==1 and s.read(addr,104)==s.imported['pb_stand_alert']
        assert s.restore()==1 and s.read(addr,104)==old
        results.append({'game':clip['game'],'name':clip['name'],'zone':clip['zone'],'delta_3d':bool(load_clip(clip['path']).get('delta') and load_clip(clip['path'])['delta'].get('three_d')),'omitted_optional_bones':report[0]['omitted_bones'],'verified':True})
    except Exception as e:results.append({'game':clip['game'],'name':clip['name'],'error':str(e)})
    s.refresh()
print(json.dumps(results,indent=2));Path('work/actor_import_validation.json').write_text(json.dumps(results,indent=2));s.close()
assert all(x.get('verified') for x in results)
