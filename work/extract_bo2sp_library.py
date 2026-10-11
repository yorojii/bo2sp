"""Extract BO2 single-player or Zombies body animations into work/catalog.

Usage: python work/extract_bo2sp_library.py [sp|zombies] [BO2 folder]

The library defaults to 'sp' (game 'BO2 SP': campaign and Strike Force zones);
'zombies' gives game 'BO2 Zombies'. The BO2 folder defaults to the release
profile's 'bo2'. Reads zone/all with OpenAssetTools (read-only on game files),
keeps clips that decode and use the human body rig, removes exact duplicates
shared between zones, and writes work/<library>_catalog.json. Already-extracted
zones are reused, so the script can be rerun after an interruption.
"""
import subprocess,json,sys
from pathlib import Path
WORK=Path(__file__).resolve().parent
sys.path.insert(0,str(WORK/'porter'))
from runtime import decode,body_clip
from library import BO2_LIBRARIES

kind=sys.argv[1] if len(sys.argv)>1 else 'sp'
game,zone_filter,common=BO2_LIBRARIES[kind]
bo2=Path(sys.argv[2]) if len(sys.argv)>2 else Path(json.loads((WORK.parent/'outputs/BO2SPAnims/profile.json').read_text())['bo2'])
files=[ff for ff in sorted((bo2/'zone/all').glob('*.ff')) if zone_filter(ff)]
files.sort(key=lambda ff:ff.stem!=common) # Shared clips are credited to the common zone first.
library=f'bo2{kind}';catalog=[];seen=set();skipped=[]
for i,ff in enumerate(files):
    folder=WORK/'catalog'/library/ff.stem
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
            catalog.append({'game':game,'zone':ff.stem,'name':path.name,'path':str(path.resolve()),'frames':anim['frames'],'fps':anim['fps'],'loop':anim['loop'],'bones':len(anim['tracks'])})
        except (ValueError,UnicodeError):pass
    print(f'{i+1}/{len(files)} {ff.stem}: {len(catalog)} unique body clips',flush=True)
    (WORK/f'{library}_catalog.json').write_text(json.dumps(catalog,indent=2))
print(json.dumps({'game':game,'zones':len(files),'skipped':skipped,'clips':len(catalog)}),flush=True)
