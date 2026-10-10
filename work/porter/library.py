"""Local CoD4 / MW2 actor / BO2 single-player and Zombies library indexing for Yoroji Tool."""
from pathlib import Path
import hashlib,json,subprocess
from runtime import decode,body_clip
from mw2_assets import extract_fastfile

def bo2_single_player(ff):
    """Campaign and Strike Force zones in BO2's zone/all; skips MP, Zombies and shared code zones."""
    name=ff.stem
    if name.endswith(('_mp','_zm')) or name.startswith(('mp_','zm_','code_','dlc','faction_','patch')):return False
    return not (name.startswith(('so_z','su_z')) and '_zm_' in name)

def bo2_zombies(ff):
    """Zombies maps, modes and shared zones in BO2's zone/all; skips shared code zones."""
    name=ff.stem
    if name.startswith('code_'):return False
    return name.endswith('_zm') or name.startswith('zm_') or (name.startswith(('so_z','su_z')) and '_zm_' in name)

# kind: (catalog game, zone filter, zone credited first for clips shared between zones)
BO2_LIBRARIES={'sp':('BO2 SP',bo2_single_player,'common'),'zombies':('BO2 Zombies',bo2_zombies,'common_zm')}

def index_libraries(cod4,mw2,root,unlinker,log,stopped=lambda:False,bo2=None):
    root=Path(root);catalog=[];seen=set()
    for game,folder in [('CoD4',cod4),('MW2 Actors',mw2),*([(g,bo2) for g,_,_ in BO2_LIBRARIES.values()] if bo2 else [])]:
        bo2_filter=next((f for g,f,_ in BO2_LIBRARIES.values() if g==game),None)
        base=Path(folder)/('zone/all' if bo2_filter else 'zone/english')
        if not base.exists():raise FileNotFoundError(f'Cannot find {game} {base.relative_to(folder).as_posix()} folder')
        if bo2_filter:files=[p for p in base.glob('*.ff') if bo2_filter(p)]
        else:files=[p for p in base.glob('*.ff') if not p.name.startswith(('mp_','localized_','code_','ui','xcommon_','dlc','patch')) and (game=='CoD4' or p.stat().st_size>20_000_000)]
        if game=='MW2 Actors':files=[p for p in files if p.name not in ('common_mp.ff','iw4_credits.ff')]
        elif game=='CoD4' and (base/'common_mp.ff') not in files:files.append(base/'common_mp.ff')
        files.sort(key=lambda p:(p.name not in ('common_mp.ff','common.ff','common_zm.ff'),p.name))
        for i,ff in enumerate(files):
            if stopped():return None
            key=hashlib.sha256(str(ff.resolve()).lower().encode()).hexdigest()[:16]
            cache=root/'cache'/key;cache.mkdir(parents=True,exist_ok=True)
            stamp={'size':ff.stat().st_size,'modified':ff.stat().st_mtime_ns};meta=cache/'zone.json'
            if meta.exists() and json.loads(meta.read_text())['stamp']==stamp:items=json.loads(meta.read_text())['clips']
            elif game=='CoD4' or bo2_filter:
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
