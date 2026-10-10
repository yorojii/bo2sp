"""Extract BO2 single-player body animations into work/catalog/bo2sp.

Usage: python work/extract_bo2sp_library.py [BO2 folder]

The BO2 folder defaults to the release profile's 'bo2'. Reads the campaign and
Strike Force zones in zone/all with OpenAssetTools (read-only on game files),
keeps clips that decode and use the human body rig, removes exact duplicates
shared between zones, and writes work/bo2sp_catalog.json. Already-extracted
zones are reused, so the script can be rerun after an interruption.
"""
import subprocess,json,sys
from pathlib import Path
WORK=Path(__file__).resolve().parent
sys.path.insert(0,str(WORK/'porter'))
from runtime import decode,body_clip

bo2=Path(sys.argv[1]) if len(sys.argv)>1 else Path(json.loads((WORK.parent/'outputs/Yoroji Tool/profile.json').read_text())['bo2'])
zones=bo2/'zone/all'
def single_player(ff):
    name=ff.stem
    if name.endswith(('_mp','_zm')) or name.startswith(('mp_','zm_','code_','dlc','faction_','patch')):return False
    return not (name.startswith(('so_z','su_z')) and '_zm_' in name) # Zombies modes packaged as so_* zones.
files=[ff for ff in sorted(zones.glob('*.ff')) if single_player(ff)]
files.sort(key=lambda ff:ff.stem!='common') # Shared clips are credited to common first.
catalog=[];seen=set();skipped=[]
for i,ff in enumerate(files):
    folder=WORK/'catalog/bo2sp'/ff.stem
    if not (folder/'xanim').exists():
        folder.mkdir(parents=True,exist_ok=True)
        result=subprocess.run([str(WORK/'oat/Unlinker.exe'),'--include-assets','xanim','-o',str(folder),str(ff)],capture_output=True)
        if result.returncode:skipped.append(ff.stem);print('Skipped zone',ff.name,result.returncode,flush=True);continue
        (folder/'xanim').mkdir(exist_ok=True) # Zones without animations still count as extracted.
    for path in sorted((folder/'xanim').glob('*')):
        try:
            raw=path.read_bytes();anim=decode(raw)
            if not body_clip(anim):continue
            key=(path.name,raw)
            if key in seen:continue
            seen.add(key)
            catalog.append({'game':'BO2 SP','zone':ff.stem,'name':path.name,'path':str(path.resolve()),'frames':anim['frames'],'fps':anim['fps'],'loop':anim['loop'],'bones':len(anim['tracks'])})
        except (ValueError,UnicodeError):pass
    print(f'{i+1}/{len(files)} {ff.stem}: {len(catalog)} unique body clips',flush=True)
    (WORK/'bo2sp_catalog.json').write_text(json.dumps(catalog,indent=2))
print(json.dumps({'zones':len(files),'skipped':skipped,'clips':len(catalog)}),flush=True)
