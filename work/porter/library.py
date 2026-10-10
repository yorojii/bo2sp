"""Local CoD4 / MW2 actor library indexing for Yoroji Tool."""
from pathlib import Path
import hashlib,json,subprocess
from runtime import decode,body_clip
from mw2_assets import extract_fastfile

def index_libraries(cod4,mw2,root,unlinker,log,stopped=lambda:False):
    root=Path(root);catalog=[];seen=set()
    for game,folder in [('CoD4',cod4),('MW2 Actors',mw2)]:
        base=Path(folder)/'zone/english'
        if not base.exists():raise FileNotFoundError(f'Cannot find {game} zone/english folder')
        files=[p for p in base.glob('*.ff') if not p.name.startswith(('mp_','localized_','code_','ui','xcommon_','dlc','patch')) and (game=='CoD4' or p.stat().st_size>20_000_000)]
        if game=='MW2 Actors':files=[p for p in files if p.name not in ('common_mp.ff','iw4_credits.ff')]
        elif (base/'common_mp.ff') not in files:files.append(base/'common_mp.ff')
        files.sort(key=lambda p:(p.name not in ('common_mp.ff','common.ff'),p.name))
        for i,ff in enumerate(files):
            if stopped():return None
            key=hashlib.sha256(str(ff.resolve()).lower().encode()).hexdigest()[:16]
            cache=root/'cache'/key;cache.mkdir(parents=True,exist_ok=True)
            stamp={'size':ff.stat().st_size,'modified':ff.stat().st_mtime_ns};meta=cache/'zone.json'
            if meta.exists() and json.loads(meta.read_text())['stamp']==stamp:items=json.loads(meta.read_text())['clips']
            elif game=='CoD4':
                result=subprocess.run([str(unlinker),'--include-assets','xanim','-o',str(cache),str(ff)],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
                if result.returncode:log(f'Skipped unsupported zone {ff.stem}');continue
                items=[]
                for path in (cache/'xanim').glob('*'):
                    try:
                        anim=decode(path.read_bytes())
                        if not body_clip(anim):continue
                        items.append({'game':game,'zone':ff.stem,'name':path.name,'path':str(path.resolve()),'frames':anim['frames'],'fps':anim['fps'],'loop':anim['loop'],'bones':len(anim['tracks'])})
                    except (ValueError,UnicodeError):continue
                meta.write_text(json.dumps({'stamp':stamp,'clips':items}))
            else:
                try:items,skips=extract_fastfile(ff,cache/'xanim',log)
                except ValueError:log(f'Skipped unsupported zone {ff.stem}');continue
                meta.write_text(json.dumps({'stamp':stamp,'clips':items}))
            for item in items:
                key=(game,item['name'],hashlib.sha256(Path(item['path']).read_bytes()).digest())
                if key in seen:continue
                seen.add(key);catalog.append(item)
            log(f'{game}: {i+1}/{len(files)} zones indexed')
    return catalog
