from pathlib import Path
import sys,json
sys.path.insert(0,'work/porter')
from runtime import Session
pid=int(sys.argv[1]);mode=sys.argv[2];s=Session(pid,read_only=True)
root=Path('outputs/BO2SP');baseline=Path('work/packaged_live_baseline.json')
try:
    if mode=='capture':
        mapping=json.loads((root/'profile.json').read_text())['mapping']
        rows={name:{'addr':s.assets[name][0],'header':s.assets[name][1].hex()} for name in mapping}
        baseline.write_text(json.dumps({'pid':pid,'rows':rows},indent=2));print('Captured',len(rows),'original slots')
    else:
        saved=json.loads(baseline.read_text());assert saved['pid']==pid
        count=0
        for name,item in saved['rows'].items():
            old=bytes.fromhex(item['header']);current=s.read(item['addr'],104)
            if mode=='import':
                assert current!=old,name+' was not imported'
                assert current[64:68]==old[64:68] and current[33]==old[33],name+' bone mapping changed'
                assert current[:4]==old[:4],name+' asset name changed'
            else:assert current==old,name+' did not restore exactly'
            count+=1
        result={'pid':pid,'verified_slots':count,'mode':mode}
        Path('work/packaged_'+mode+'_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
finally:s.close()
