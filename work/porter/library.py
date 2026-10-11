"""Local CoD4 / MW2 actor / BO2 single-player and Zombies library indexing for BO2SPAnims.

index_libraries() builds the clip catalog from whichever game folders exist. A game whose
folder is missing or unset is skipped (and reported) rather than failing the whole build.
Each zone's extracted clips are cached under library/cache/<zone key>/ with a size+mtime
stamp, so a cancelled or interrupted build resumes where it stopped.
"""
from pathlib import Path
import hashlib,json,os,subprocess
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
GAMES=('CoD4','MW2 Actors','BO2 SP','BO2 Zombies')
FOLDER_KEY={'CoD4':'cod4','MW2 Actors':'mw2','BO2 SP':'bo2','BO2 Zombies':'bo2'}

def language_zone(folder):
    """CoD4/MW2 keep their zones in zone/<language>; prefer english, else the only one with common_mp.ff."""
    zone=Path(folder)/'zone'
    if (zone/'english').is_dir():return zone/'english'
    found=[p.parent for p in zone.glob('*/common_mp.ff')]
    return found[0] if len(found)==1 else None

def game_zones(game,folder):
    """Fastfiles to index for one game, in a stable order (shared zones first), or None if the game isn't there."""
    if not folder or not Path(folder).is_dir():return None
    bo2_filter=next((f for g,f,_ in BO2_LIBRARIES.values() if g==game),None)
    if bo2_filter:
        base=Path(folder)/'zone/all'
        if not (base/'common_mp.ff').exists():return None
        files=[p for p in base.glob('*.ff') if bo2_filter(p)]
    else:
        base=language_zone(folder)
        if base is None or not (base/'common_mp.ff').exists():return None
        files=[p for p in base.glob('*.ff') if not p.name.startswith(('mp_','localized_','code_','ui','xcommon_','dlc','patch')) and (game=='CoD4' or p.stat().st_size>20_000_000)]
        if game=='MW2 Actors':files=[p for p in files if p.name not in ('common_mp.ff','iw4_credits.ff')]
        elif (base/'common_mp.ff') not in files:files.append(base/'common_mp.ff')
    return sorted(files,key=lambda p:(p.name not in ('common_mp.ff','common.ff','common_zm.ff'),p.name))

def index_libraries(folders,root,unlinker,log,stopped=lambda:False,progress=lambda done,total,text:None):
    """folders: {'cod4','mw2','bo2'} paths. Returns (catalog, built games, skipped games), or None if stopped."""
    root=Path(root);unlinker=Path(unlinker)
    if not unlinker.exists():raise FileNotFoundError('tools/Unlinker.exe is missing. Keep the whole BO2SPAnims folder together.')
    plan=[];skipped=[]
    for game in GAMES:
        files=game_zones(game,folders.get(FOLDER_KEY[game]))
        if files is None:skipped.append(game);log(f'{game}: game folder not found; skipped.')
        else:plan.append((game,files))
    total=sum(len(files) for game,files in plan);done=0;catalog=[]
    for game,files in plan:
        seen=set();bo2_game=any(g==game for g,_,_ in BO2_LIBRARIES.values())
        for ff in files:
            if stopped():return None
            progress(done,total,f'{game} · {ff.stem}')
            key=hashlib.sha256(str(ff.resolve()).lower().encode()).hexdigest()[:16]
            cache=root/'cache'/key;cache.mkdir(parents=True,exist_ok=True)
            stamp={'size':ff.stat().st_size,'modified':ff.stat().st_mtime_ns};meta=cache/'zone.json'
            if meta.exists() and json.loads(meta.read_text())['stamp']==stamp:items=json.loads(meta.read_text())['clips']
            elif game=='CoD4' or bo2_game:
                result=subprocess.run([str(unlinker),'--include-assets','xanim','-o',str(cache),str(ff)],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
                if result.returncode:log(f'Skipped unsupported zone {ff.stem}');done+=1;continue
                items=[]
                for path in sorted((cache/'xanim').glob('*')):
                    try:
                        anim=decode(path.read_bytes())
                        if not body_clip(anim):path.unlink();continue # Keep only body clips on disk.
                        items.append({'game':game,'zone':ff.stem,'name':path.name,'path':str(path.resolve()),'frames':anim['frames'],'fps':anim['fps'],'loop':anim['loop'],'bones':len(anim['tracks'])})
                    except (ValueError,UnicodeError):path.unlink()
                write_json(meta,{'stamp':stamp,'clips':items})
            else:
                try:items,skips=extract_fastfile(ff,cache/'xanim',log)
                except ValueError:log(f'Skipped unsupported zone {ff.stem}');done+=1;continue
                write_json(meta,{'stamp':stamp,'clips':items})
            for item in items:
                identity=(item['name'],hashlib.sha256(Path(item['path']).read_bytes()).digest())
                if identity in seen:continue # The same clip in several zones is credited to the first zone.
                seen.add(identity);catalog.append(item)
            done+=1
        log(f'{game}: {sum(x["game"]==game for x in catalog):,} clips from {len(files)} zones.')
    progress(total,total,'done')
    return catalog,[game for game,files in plan],skipped

def write_json(path,data):
    temp=Path(str(path)+'.tmp');temp.write_text(json.dumps(data));os.replace(temp,path) # A half-written stamp would look complete.
