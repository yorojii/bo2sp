import subprocess,json,sys,time
from pathlib import Path
sys.path.insert(0,'work/porter')
from runtime import decode
root=Path(r'D:\Call of Duty 4\zone\english')
core={'j_mainroot','j_spinelower','j_spineupper','j_head','j_hip_le','j_hip_ri'}
catalog=[];seen=set()
files=[p for p in sorted(root.glob('*.ff')) if not p.name.startswith(('mp_','localized_','code_','ui','xcommon_')) and p.name!='common_mp.ff']
files=[root/'common_mp.ff',*files]
for i,ff in enumerate(files):
    folder=Path('work/catalog/cod4')/ff.stem
    if not (folder/'xanim').exists():
        folder.mkdir(parents=True,exist_ok=True)
        r=subprocess.run(['work/oat/Unlinker.exe','--include-assets','xanim','-o',str(folder),str(ff)],capture_output=True)
        if r.returncode:print('Skipped zone',ff.name,r.returncode,flush=True);continue
    for p in sorted((folder/'xanim').glob('*')):
        try:
            raw=p.read_bytes();anim=decode(raw)
            if len(core.intersection(t['name'] for t in anim['tracks']))<3:continue
            key=(p.name,raw)
            if key in seen:continue
            seen.add(key)
            catalog.append({'game':'CoD4','zone':ff.stem,'name':p.name,'path':str(p.resolve()),'frames':anim['frames'],'fps':anim['fps'],'loop':anim['loop'],'bones':len(anim['tracks'])})
        except (ValueError,UnicodeError):pass
    print(f'{i+1}/{len(files)} {ff.stem}: {len(catalog)} unique body clips',flush=True)
    Path('work/cod4_catalog.json').write_text(json.dumps(catalog,indent=2))
