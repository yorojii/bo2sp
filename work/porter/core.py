"""BO2SP application core: state, profile, importer, observer and hotkeys (GPL-3.0-or-later).

No GUI toolkit here. A front end passes a `ui` object providing:
  post(fn)                      run fn on the UI thread (callable from any thread)
  changed(*fields)              core fields changed; refresh the matching widgets
  append_log(text)              add a line to the log
  confirm(title,text) -> bool   yes/no question
  ask_text(title,prompt,initial) -> str|None
  message(kind,title,text)      kind is 'info' or 'error'
  ask_file(title) -> str|None
  focus_neutral()               move keyboard focus off buttons (before key capture)
Core methods are called on the UI thread; worker threads only reach the UI through post().
"""
from pathlib import Path
import base64,csv,ctypes,hashlib,json,os,queue,re,subprocess,sys,threading,time,zlib
from ctypes import wintypes
from runtime import Session,decode,load_clip,body_clip,k
from camera import install_camera
from live_target import LiveTargetReader,AnimationChanging
from replay_hotkey import HotkeyListener,KEYS,GAME_KEYS,key_name
from freelook import Freelook
from movement import Movement,LIMITS as MOVEMENT_LIMITS,clamp_percent
from logfile import LogFile,setup_info

ROOT=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
TOOLS=ROOT/'tools';STATE=ROOT/'state';STATE.mkdir(exist_ok=True)
GAMES=('CoD4','MW2 Actors','MW3 Actors','BO2 SP','BO2 Zombies')
from library import SHORT,short # Display names: COD4 / MW2 / MW3 / BO2 SP / BO2 ZM.
DEFAULT_THEME={'h':32,'s':100,'l':52,'glow':True,'style':'terminal','glass':10} # glass: iOS darkening tint 0-60% over the see-through backdrop. # style: 'terminal', 'glass' (shown as iOS) or 'android' (a deliberately low-quality joke); glass: tint 0-100.
THEME_PRESETS={'Amber':(32,100,52),'Phosphor':(130,90,50),'Cyan':(190,95,55),'Magenta':(320,85,62),'Mono':(0,0,85)}

class ProcessEntry(ctypes.Structure):
    _fields_=[('size',wintypes.DWORD),('usage',wintypes.DWORD),('pid',wintypes.DWORD),('heap',ctypes.c_size_t),
              ('module',wintypes.DWORD),('threads',wintypes.DWORD),('parent',wintypes.DWORD),
              ('priority',wintypes.LONG),('flags',wintypes.DWORD),('exe',wintypes.WCHAR*260)]
k.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD];k.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
k.Process32FirstW.argtypes=[wintypes.HANDLE,ctypes.POINTER(ProcessEntry)];k.Process32FirstW.restype=wintypes.BOOL
k.Process32NextW.argtypes=k.Process32FirstW.argtypes;k.Process32NextW.restype=wintypes.BOOL
k.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)];k.QueryFullProcessImageNameW.restype=wintypes.BOOL

def running_games():
    """(pid, executable path) of every running BO2 MP process."""
    snapshot=k.CreateToolhelp32Snapshot(2,0)
    if snapshot in (None,ctypes.c_void_p(-1).value):raise OSError('Cannot inspect running games')
    row=ProcessEntry();row.size=ctypes.sizeof(row);result=[]
    try:
        ok=k.Process32FirstW(snapshot,ctypes.byref(row))
        while ok:
            if row.exe.lower() in ('t6mp.exe','t6mpv43.exe'):
                handle=k.OpenProcess(0x1000,False,row.pid)
                if handle:
                    try:
                        buf=ctypes.create_unicode_buffer(4096);length=wintypes.DWORD(len(buf))
                        if k.QueryFullProcessImageNameW(handle,0,buf,ctypes.byref(length)):result.append((row.pid,Path(buf.value)))
                    finally:k.CloseHandle(handle)
            ok=k.Process32NextW(snapshot,ctypes.byref(row))
    finally:k.CloseHandle(snapshot)
    return result

def game_pids(folder):
    if not folder:return []
    folder=Path(folder).resolve();return [pid for pid,exe in running_games() if exe.parent.resolve()==folder]

# Game folder detection for fresh installs: a running BO2, Steam libraries, then common install folders.
GAME_NAMES={'bo2':('Call of Duty Black Ops II','Call of Duty - Black Ops II','Black Ops II','BO2'),
            'cod4':('Call of Duty 4','Call of Duty 4 - Modern Warfare'),'mw2':('Call of Duty Modern Warfare 2','Call of Duty - Modern Warfare 2'),
            'mw3':('Call of Duty Modern Warfare 3','Call of Duty - Modern Warfare 3')}
def valid_folder(key,folder):
    if not folder or not Path(folder).is_dir():return False
    folder=Path(folder)
    if key=='bo2':return (folder/'zone/all/common_mp.ff').exists() and any((folder/exe).exists() for exe in ('t6mpv43.exe','t6mp.exe'))
    from library import language_zone
    base=language_zone(folder);return base is not None and (base/'common_mp.ff').exists()
def steam_libraries():
    roots=[]
    try:
        import winreg
        for hive,key,value in ((winreg.HKEY_CURRENT_USER,r'Software\Valve\Steam','SteamPath'),(winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\WOW6432Node\Valve\Steam','InstallPath')):
            try:
                with winreg.OpenKey(hive,key) as handle:roots.append(Path(winreg.QueryValueEx(handle,value)[0]))
            except OSError:pass
    except ImportError:pass
    libraries=[]
    for root in roots:
        libraries.append(root/'steamapps')
        try:libraries+=[Path(path.replace('\\\\','\\'))/'steamapps' for path in re.findall(r'"path"\s+"([^"]+)"',(root/'steamapps/libraryfolders.vdf').read_text(errors='replace'))]
        except OSError:pass
    return list(dict.fromkeys(libraries))
def candidate_folders(key):
    found=[]
    if key=='bo2':
        try:found+=[exe.parent for pid,exe in running_games()]
        except OSError:pass
    for library in steam_libraries():found+=[library/'common'/name for name in GAME_NAMES[key]]
    for drive in (f'{letter}:\\' for letter in 'CDEFGHIJ'):
        for parent in (Path(drive),Path(drive)/'Games',Path(drive)/'Program Files (x86)',Path(drive)/'Program Files (x86)/Activision'):
            try:found+=[child for child in parent.iterdir() if child.is_dir() and any(child.name.lower().startswith(name.lower()) for name in GAME_NAMES[key])]
            except OSError:pass
    return found
def detect_folders(current):
    """Keep each valid configured folder; otherwise return the best detected one (Redacted BO2 preferred)."""
    result={}
    for key in ('bo2','cod4','mw2','mw3'):
        if valid_folder(key,current.get(key)):result[key]=current[key];continue
        options=[str(folder) for folder in dict.fromkeys(candidate_folders(key)) if valid_folder(key,folder)]
        if key=='bo2':options.sort(key=lambda folder:not (Path(folder)/'t6mpv43.exe').exists())
        result[key]=options[0] if options else (current.get(key) or '')
    return result

def write_atomic(path,text,backup=False):
    """Write a file so a crash or power loss leaves either the old or the new version, never a partial one."""
    path=Path(path);temp=path.with_name(path.name+'.tmp')
    with open(temp,'w',encoding='utf-8',newline='\n') as handle:handle.write(text);handle.flush();os.fsync(handle.fileno())
    if backup and path.exists():
        try: # Copy (not move) the last good version, so the main file exists at every moment.
            current=path.read_text(encoding='utf-8');json.loads(current);spare=path.with_name(path.name+'.bak.tmp')
            with open(spare,'w',encoding='utf-8',newline='\n') as handle:handle.write(current);handle.flush();os.fsync(handle.fileno())
            os.replace(spare,path.with_name(path.name+'.bak'))
        except (OSError,ValueError):pass
    os.replace(temp,path)

def read_profile(log):
    """profile.json, or its .bak copy if the main file is missing or unreadable."""
    path=ROOT/'profile.json';backup=path.with_name('profile.json.bak')
    for candidate in (path,backup):
        try:
            profile=json.loads(candidate.read_text(encoding='utf-8'))
            if candidate==backup:log('profile.json was unreadable; loaded the backup copy profile.json.bak.')
            return profile
        except FileNotFoundError:continue
        except (OSError,ValueError):
            if candidate==path:log('profile.json is unreadable; trying the backup copy.')
    return {}

def unlink(args,log):
    exe=TOOLS/'Unlinker.exe'
    if not exe.exists():raise FileNotFoundError('tools/Unlinker.exe is missing. Keep the whole importer folder together.')
    result=subprocess.run([str(exe),*map(str,args)],capture_output=True,text=True,encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
    text=result.stdout+'\n'+result.stderr
    if result.returncode or 'ERROR:' in text:raise RuntimeError(text[-1800:] or f'Unlinker exited with {result.returncode}')
    log('Asset scan completed.')
    return text

def scan(cod4,bo2,log=print):
    cod4=Path(cod4);bo2=Path(bo2)
    if not (bo2/'Redacted.ini').exists():raise ValueError('Choose your BO2 Redacted folder, containing Redacted.ini.')
    ff=bo2/'zone/all/common_mp.ff'
    if not ff.exists():raise FileNotFoundError(f'Missing BO2 common_mp.ff: {ff}')
    text=unlink(['--list',ff],log);targets=[];active=False
    for line in text.splitlines():
        if line=='Content:':active=True;continue
        if active and line.startswith('Unloaded'):break
        if active and line.startswith('xanim,'):
            row=[v.strip() for v in next(csv.reader([line]))]
            if len(row)==2 and row[1].startswith('pb_'):targets.append(row[1])
    sourceff=cod4/'zone/english/common_mp.ff'
    if not sourceff.exists():
        found=list((cod4/'zone').glob('*/common_mp.ff'))
        if len(found)!=1:raise FileNotFoundError('Cannot find COD4 zone/<language>/common_mp.ff.')
        sourceff=found[0]
    key=hashlib.sha256(str(sourceff.resolve()).lower().encode()).hexdigest()[:16]
    folder=STATE/'sources'/key
    stamp={'size':sourceff.stat().st_size,'modified':sourceff.stat().st_mtime_ns}
    cached=folder/'source.json'
    if not cached.exists() or json.loads(cached.read_text())!=stamp:
        unlink(['--include-assets','xanim','-o',folder,sourceff],log)
        cached.write_text(json.dumps(stamp))
    sources=folder/'xanim';keywords=('death','run','walk','sprint','jump','crawl','alert','ads','hold','prone2','crouch2')
    mapping={name:str(sources/name) for name in sorted(set(targets)) if (sources/name).exists() and any(word in name for word in keywords)}
    if not mapping:raise ValueError('No compatible basic COD4 body animations were found.')
    for path in mapping.values():decode(Path(path).read_bytes())
    log(f'Ready: {len(mapping)} basic animations, including {sum("death" in n for n in mapping)} deaths.')
    return mapping,sorted(set(targets))

SHARE_PREFIX='BO2SP1-'
def encode_share(data):
    """Compact copy-paste text for a preset: prefix + URL-safe base64 of zlib-compressed JSON."""
    raw=zlib.compress(json.dumps(data,separators=(',',':')).encode(),9)
    return SHARE_PREFIX+base64.urlsafe_b64encode(raw).decode().rstrip('=')
def decode_share(text):
    """The preset dict from a share code (surrounding text and line breaks are ignored), or ValueError."""
    match=re.search(re.escape(SHARE_PREFIX)+r'([A-Za-z0-9_\-\s]+)',text or '')
    if not match:raise ValueError("That isn't a BO2SP share code.")
    body=re.sub(r'\s','',match.group(1))
    try:data=json.loads(zlib.decompress(base64.urlsafe_b64decode(body+'='*(-len(body)%4))))
    except Exception:raise ValueError('That share code is incomplete or damaged. Copy the whole code and try again.')
    if not isinstance(data,dict) or data.get('kind') not in ('set','theme'):raise ValueError('That share code is from an unsupported version.')
    return data

class Core:
    def __init__(self,ui):
        self.ui=ui;self.logfile=LogFile(ROOT);self.status='';self.mapping={};self.targets=[];self.catalog=[];self.session=None;self.stop_event=threading.Event();self.worker=None;self.indexthread=None;self.lock=threading.Lock();self.closing=False
        self.cod4='';self.bo2='';self.mw2='';self.mw3='';self.build_picks={};self.building=False;self.build_cancel=threading.Event()
        profile=read_profile(self.log)
        try:
            self.cod4=profile['cod4'];self.bo2=profile['bo2'];self.mw2=profile.get('mw2',self.mw2);self.mw3=profile.get('mw3',self.mw3)
            self.mapping={name:str((ROOT/path).resolve()) for name,path in profile.get('mapping',{}).items() if (ROOT/path).is_file()};self.targets=profile.get('targets',[])
        except (OSError,ValueError,KeyError):pass
        self.detect_folders(save=False);folders_found=self.folders_changed and bool(profile) # Saved once every setting is loaded.
        self.status='Choose a source clip and a BO2 replacement slot.';self.live='Imports inactive. Live target detection is running.';self.target='pb_stand_alert'
        self.follow_live=True;self.live_lock=False;self.last_snapshot={};self.detected_at=0
        self.detected='Looking for your character…';self.target_note='Automatic target: waiting for a match.'
        self.observe_stop=threading.Event();self.restart_requests=queue.SimpleQueue()
        self.worker_wake=threading.Event();self.replay_target=profile.get('replay',{}).get('target','')
        replay_source=profile.get('replay',{}).get('source','')
        self.replay_path=str((ROOT/replay_source).resolve()) if replay_source and (ROOT/replay_source).is_file() else self.mapping.get(self.replay_target,'')
        # Apply anim key: any keyboard key saved as vk + name; older profiles only saved an F-key/numpad name.
        replay=profile.get('replay',{});vk=replay.get('vk',KEYS.get(replay.get('key'),KEYS['F6']))
        self.apply_vk=int(vk or 0);self.apply_name=(replay.get('key') if 'vk' in replay else key_name(self.apply_vk)) if self.apply_vk else 'None'
        self.replay_enabled=bool(replay.get('enabled',True))
        self.hotkeys={action:{'vk':int(v['vk']),'name':str(v.get('name') or key_name(v['vk']))} for action,v in profile.get('hotkeys',{}).items() if isinstance(v,dict) and v.get('vk')}
        self.actions={};self.capture_action=None
        # Favorites and saved sets refer to clips by game/zone/name, so they survive library renumbering.
        self.favorites=set(profile.get('favorites',[]));self.saved_sets=dict(profile.get('saved_sets',{}))
        look=profile.get('freelook',{});self.freelook_vk=int(look.get('vk',0x12) or 0) # Default: either Alt key.
        self.freelook_name=(look.get('key') if 'vk' in look else key_name(self.freelook_vk)) if self.freelook_vk else 'None'
        self.freelook_enabled=bool(look.get('enabled',True));self.freelook_speed=self.clamp_speed(look.get('speed',0.15))
        self.setup_done=bool(profile.get('setup_done',False)) # First launch shows the Setup tab until it's finished.
        moves=profile.get('movement',{});self.movement={key:clamp_percent(key,moves.get(key,100)) for key in MOVEMENT_LIMITS} # Percent of BO2's defaults.
        theme=profile.get('theme',{});self.theme={**DEFAULT_THEME,**{key:theme[key] for key in DEFAULT_THEME if key in theme}}
        self.replay_note='';self.replay_error_shown=False
        self.read_library();self.update_target_note()
        self.logfile.header(setup_info(ROOT,self.bo2,len(self.catalog),len(self.mapping)))
        self.observer=threading.Thread(target=self.observe_game,name='Live target observer');self.observer.start()
        self.hotkey=HotkeyListener();self.freelook=Freelook();self.mover=Movement()
        if folders_found:self.save()

    # Plumbing
    def post(self,fn):
        if not self.closing:self.ui.post(fn)
    def log(self,text):self.logfile.write(text);self.post(lambda:self.ui.append_log(str(text))) # From any thread.
    def write_log(self,text):self.logfile.write(text);self.ui.append_log(text) # UI thread only.
    def set_status(self,text):
        if text!=self.status:self.logfile.write(text,'status')
        self.status=text;self.ui.changed('status')
    def support_text(self):return self.logfile.support_text()
    def set_live(self,text):self.live=text;self.ui.changed('live')
    def idle(self):return not ((self.worker and self.worker.is_alive()) or (self.indexthread and self.indexthread.is_alive()))
    def editable(self):return not self.closing and not (self.indexthread and self.indexthread.is_alive())
    def busy_changed(self):self.ui.changed('busy')
    def clip_key(self,item):return f"{item['game']}/{item['zone']}/{item['name']}"
    @staticmethod
    def shown_key(key):game,_,rest=key.partition('/');return f'{short(game)}/{rest}' # A clip key as the UI names games.
    def clip_for_path(self,path):return next((x for x in self.catalog if x['path']==path),None)
    def describe(self,path):
        item=self.clip_for_path(path)
        return f"{short(item['game'])}: {item['name']} ({item['zone']})" if item else (Path(path).stem if path else 'Original BO2')

    # Profile
    def save(self):
        mapping={}
        for name,path in self.mapping.items():
            try:mapping[name]=str(Path(path).resolve().relative_to(ROOT))
            except ValueError:mapping[name]=str(Path(path).resolve())
        replay_source=self.replay_path
        if replay_source:
            try:replay_source=str(Path(replay_source).resolve().relative_to(ROOT))
            except ValueError:pass
        write_atomic(ROOT/'profile.json',json.dumps({'cod4':self.cod4,'bo2':self.bo2,'mw2':self.mw2,'mw3':self.mw3,'mapping':mapping,'targets':self.targets,
            'replay':{'key':self.apply_name,'vk':self.apply_vk,'enabled':self.replay_enabled,'target':self.replay_target,'source':replay_source},
            'hotkeys':self.hotkeys,'favorites':sorted(self.favorites),'saved_sets':self.saved_sets,
            'freelook':{'key':self.freelook_name,'vk':self.freelook_vk,'enabled':self.freelook_enabled,'speed':self.freelook_speed},'movement':self.movement,'theme':self.theme,'setup_done':self.setup_done},indent=2),backup=True)
    def set_setup_done(self,done):self.setup_done=bool(done);self.save();self.ui.changed('setup')
    def set_folder(self,key,path):
        """Set one game folder (the Setup tab's Browse buttons)."""
        setattr(self,key,path);self.save();self.ui.changed('folders')
    def set_folders(self,cod4,mw2,bo2,mw3=None):
        self.cod4,self.mw2,self.bo2=cod4,mw2,bo2
        if mw3 is not None:self.mw3=mw3
        self.save();self.ui.changed('folders')
    def set_theme(self,save=True,**values):
        self.theme={**self.theme,**values};self.ui.changed('theme')
        if save:self.save()

    # Library and favorites
    def read_library(self):
        try:
            self.catalog=json.loads((ROOT/'library/catalog.json').read_text())
            for item in self.catalog:item['path']=str((ROOT/item['path']).resolve())
        except (OSError,ValueError):self.catalog=[]
        self.ui.changed('catalog')
    def zones(self,game):
        return sorted({x['game'] for x in self.catalog}) if game=='Favorites' else sorted({x['zone'] for x in self.catalog if x['game']==game})
    def clips(self,game,query='',zone='All'):
        """Catalog indexes shown in a library tab ('Favorites' lists starred clips; zone then filters by game)."""
        q=query.casefold();out=[]
        for index,item in enumerate(self.catalog):
            if game=='Favorites':
                if self.clip_key(item) not in self.favorites or (zone!='All' and item['game']!=zone):continue
            elif item['game']!=game or (zone!='All' and item['zone']!=zone):continue
            if q in (item['name']+' '+item['zone']).casefold():out.append(index)
        return out
    def toggle_favorite(self,index):
        if index is None:self.set_status('Select a clip first, then use ★ Favorite.');return
        item=self.catalog[index];key=self.clip_key(item);added=key not in self.favorites
        if added:self.favorites.add(key)
        else:self.favorites.discard(key)
        self.save();self.ui.changed('favorites')
        self.set_status(('Added to' if added else 'Removed from')+f" favorites: {item['name']}")
    def choose_clip(self,index):
        """A clip was highlighted in a library tab: it becomes the apply-anim source."""
        if index is None:return
        item=self.catalog[index];self.replay_path=item['path'];self.update_replay_note()
        if self.follow_live or self.live_lock:return
        if item['name'] in self.targets:self.set_target(item['name'])

    # Saved replacement sets
    def set_entries(self):
        """Current mapping as saveable entries: catalog clips by key, other files by path."""
        lookup={x['path']:x for x in self.catalog};entries={}
        for target,path in self.mapping.items():
            item=lookup.get(path)
            if item:entries[target]={'clip':self.clip_key(item)}
            else:
                try:entries[target]={'path':str(Path(path).resolve().relative_to(ROOT))}
                except ValueError:entries[target]={'path':str(Path(path).resolve())}
        return entries
    def save_set(self,current=''):
        if not self.mapping:self.set_status('Choose some replacements before saving a set.');return None
        name=(self.ui.ask_text('Save replacements','Name for this set of replacements:',current) or '').strip()
        if not name:return None
        if name in self.saved_sets and not self.ui.confirm('Replace set',f'Replace the saved set "{name}"?'):return None
        self.saved_sets[name]=self.set_entries();self.save();self.ui.changed('sets')
        self.set_status(f'Saved {len(self.saved_sets[name])} replacements as "{name}".');return name
    def resolve_set(self,name):
        paths={self.clip_key(x):x['path'] for x in self.catalog};mapping={};missing=[]
        for target,entry in self.saved_sets[name].items():
            path=paths.get(entry.get('clip')) if 'clip' in entry else str((ROOT/entry.get('path','')).resolve())
            if path and Path(path).is_file():mapping[target]=path
            else:missing.append(entry.get('clip') or entry.get('path') or target)
        return mapping,missing
    def load_set(self,name):
        if not self.editable():return
        if name not in self.saved_sets:self.set_status('Choose a saved set to load.');return
        mapping,missing=self.resolve_set(name)
        if self.mapping and self.mapping!=mapping and not self.ui.confirm('Load set',f'Replace your {len(self.mapping)} current replacements with "{name}"?'):return
        self.mapping=mapping;self.worker_wake.set();self.refresh();self.save()
        self.set_status(f'Loaded "{name}": {len(mapping)} replacements'+(f', {len(missing)} missing clips skipped ({", ".join(map(self.shown_key,missing[:3]))})' if missing else '')+'.')
        if mapping and self.last_snapshot.get('ready') and self.idle():self.start()
    # Share codes: presets as copy-paste text.
    def share_set_code(self,name=''):
        """Code for a saved set (or the current replacements when name is empty). Only library clips are portable."""
        entries=self.saved_sets[name] if name in self.saved_sets else self.set_entries()
        clips={target:entry['clip'] for target,entry in entries.items() if 'clip' in entry};local=len(entries)-len(clips)
        if not clips:self.set_status("Nothing to share: choose library clips first (imported files can't be shared).");return None
        code=encode_share({'kind':'set','name':name or 'Shared replacements','clips':clips})
        self.set_status(f'Share code copied: {len(clips)} replacements'+(f' ({local} imported files left out; only library clips can be shared)' if local else '')+'.');return code
    def share_theme_code(self):
        code=encode_share({'kind':'theme','theme':{key:self.theme[key] for key in DEFAULT_THEME}});self.set_status('Appearance code copied.');return code
    def import_share_code(self,text):
        """Apply a pasted code: a set is saved under a name you choose; an appearance is applied. Returns (kind, name) or None."""
        try:data=decode_share(text)
        except ValueError as e:self.set_status(str(e));return None
        if data['kind']=='theme':
            theme={key:value for key,value in data.get('theme',{}).items() if key in DEFAULT_THEME}
            if not theme:self.set_status('That appearance code is empty.');return None
            self.set_theme(**theme);self.set_status('Appearance applied from share code.');return ('theme','')
        clips={target:key for target,key in data.get('clips',{}).items() if isinstance(target,str) and isinstance(key,str)}
        name=(self.ui.ask_text('Save shared set','Name for this set of replacements:',data.get('name','Shared replacements')) or '').strip()
        if not name:return None
        if name in self.saved_sets and not self.ui.confirm('Replace set',f'Replace the saved set "{name}"?'):return None
        known={self.clip_key(x) for x in self.catalog};missing=[key for key in clips.values() if key not in known]
        self.saved_sets[name]={target:{'clip':key} for target,key in clips.items()};self.save();self.ui.changed('sets')
        self.set_status(f'Saved "{name}": {len(clips)} replacements'+(f', {len(missing)} not in your library ({", ".join(map(self.shown_key,missing[:3]))})' if missing else '')+'. Pick it and Load set to use it.')
        return ('set',name)
    def delete_set(self,name):
        if name not in self.saved_sets:self.set_status('Choose a saved set to delete.');return
        if not self.ui.confirm('Delete set',f'Delete the saved set "{name}"? Your current replacements are not changed.'):return
        del self.saved_sets[name];self.save();self.ui.changed('sets');self.set_status(f'Deleted saved set "{name}".')

    # Targets, follow/lock and apply anim
    def set_target(self,name):self.target=name;self.update_target_note()
    def update_target_note(self):
        self.target_note=('Automatic target' if self.follow_live else 'Locked target')+': '+self.target
        self.update_replay_note();self.ui.changed('target')
    def update_replay_note(self):
        name=next((x['name'] for x in self.catalog if x['path']==self.replay_path),Path(self.replay_path).stem if self.replay_path else '')
        mode='current live slot' if self.follow_live else self.target
        self.replay_note='Apply anim: '+name+' → '+mode if name else 'Select a clip, then press the apply anim key.';self.ui.changed('replay_note')
    def set_follow(self,follow):
        self.follow_live=follow;self.live_lock=not follow
        if follow and self.last_snapshot.get('ready'):self.target=self.last_snapshot['primary']['target']
        self.update_target_note()
    def set_locked(self,locked):
        """Lock target checkbox: lock the current live slot, or go back to following."""
        if locked:
            if self.last_snapshot.get('ready') and time.monotonic()-self.detected_at<=2:self.target=self.last_snapshot['primary']['target']
            self.set_follow(False);self.set_status('Target locked: '+self.target+'. Choose a source clip, then Use selected clip.')
        else:self.set_follow(True);self.set_status('Following your current animation.')
    def manual_target(self,name):self.target=name;self.set_follow(False)
    def lock_highlighted(self,name):
        if not any(x['target']==name and x['selectable'] for x in self.last_snapshot.get('animations',[])):
            self.set_status('Choose a Body layer to replace with a full-character clip.');return False
        self.manual_target(name);return True
    def queue_restart(self,target,path,notify=False):
        self.restart_requests.put((target,path,notify,time.monotonic()+1.0));self.worker_wake.set()
    def request_replay(self):
        if not self.editable():return False
        if not self.replay_path:
            self.set_status('Select a source clip first, then press your apply anim key.');return False
        if not self.last_snapshot.get('ready') or time.monotonic()-self.detected_at>2:
            self.set_status('Wait for a live character animation before pressing the apply anim key.');return False
        if self.worker and self.worker.is_alive() and self.stop_event.is_set():
            self.set_status('Wait for restoration to finish before applying an anim.');return False
        target=self.last_snapshot['primary']['target'] if self.follow_live else self.target
        if target not in self.targets:
            self.set_status('Choose a valid BO2 slot or enable Follow current animation.');return False
        path=self.replay_path;changed=self.mapping.get(target)!=path or self.replay_target!=target
        self.replay_target=target
        if changed:
            self.mapping={**self.mapping,target:path};self.refresh();self.save()
        self.update_replay_note()
        self.queue_restart(target,path,True);self.set_status('Apply anim queued: '+target)
        if self.idle():self.start()
        return True
    def use_clip(self,index):
        if not self.editable():return
        if index is None:self.ui.message('info','Select a clip','Choose an animation from this tab first.');return
        if self.follow_live and not self.last_snapshot.get('ready'):
            self.set_status('Wait for a live body animation, or lock a target and choose a slot manually.');return
        if self.target not in self.targets:self.ui.message('error','Select a BO2 slot','Choose an existing BO2 animation slot.');return
        item=self.catalog[index];target=self.target;self.mapping={**self.mapping,target:item['path']}
        self.replay_target=target;self.replay_path=item['path'];self.queue_restart(target,item['path']);self.save();self.refresh();self.log(f"{short(item['game'])}: {item['name']} → {target}")
        if self.last_snapshot.get('ready') and self.idle():self.start()
    def import_clip(self):
        if not self.editable():return
        if not self.targets:self.ui.message('info','Load basics first','Load COD4 basics to find BO2 target names.');return
        path=self.ui.ask_file('Select a compiled COD4 / MW2 / MW3 / BO2 character animation')
        if not path:return
        try:
            anim=load_clip(path)
            if not body_clip(anim):raise ValueError('Choose a character animation. Weapon, hand and vehicle rigs are not supported.')
        except Exception as e:self.ui.message('error','Unsupported animation',str(e));return
        if self.target not in self.targets:self.ui.message('error','Select a slot','Choose the BO2 animation slot first.');return
        if self.follow_live and not self.last_snapshot.get('ready'):
            self.set_status('Wait for a live target, or lock a target and choose a slot.');return
        target=self.target;self.mapping={**self.mapping,target:path};self.replay_target=target;self.replay_path=path;self.queue_restart(target,path);self.save();self.refresh()
        if self.last_snapshot.get('ready') and self.idle():self.start()
    def remove(self,targets):
        if not self.editable():return
        removed=set(targets);self.mapping={name:path for name,path in self.mapping.items() if name not in removed}
        self.worker_wake.set();self.refresh();self.save()
    def clear(self):
        if not self.editable():return
        self.mapping={};self.worker_wake.set();self.refresh();self.save()
    def refresh(self):
        if self.replay_target not in self.mapping:self.replay_target=''
        self.update_replay_note();self.ui.changed('mapping')
        self.set_status(f'{len(self.mapping)} selected replacements. Use selected clip updates the current match.' if self.worker and self.worker.is_alive() else f'{len(self.mapping)} selected replacements. Lock a target or choose a BO2 slot, then select a clip.')

    # Hotkeys: Apply anim and Freelook have their own keys; any other registered action gets one by right-click.
    def register_action(self,action,label,callback,enabled=lambda:True):self.actions[action]=(label,callback,enabled)
    def action_label(self,action):return {'apply_anim':'Apply anim','freelook':'Freelook'}.get(action) or self.actions.get(action,(action,))[0]
    def key_for(self,action):
        if action=='apply_anim':return self.apply_name if self.apply_vk else None
        if action=='freelook':return self.freelook_name if self.freelook_vk else None
        return self.hotkeys.get(action,{}).get('name')
    @staticmethod
    def clamp_speed(value):
        try:return min(max(float(value),0.01),2.0)
        except (TypeError,ValueError):return 0.15
    def bindings(self,active=False):
        keys={v['vk']:action for action,v in self.hotkeys.items()}
        if self.freelook_vk and not active: # Held by freelook, not dispatched as a press; 'Alt' covers both Alt keys.
            for vk in ((0x12,0xA4,0xA5) if self.freelook_vk==0x12 else (self.freelook_vk,)):keys[vk]='freelook'
        if self.apply_vk and (self.replay_enabled or not active):keys[self.apply_vk]='apply_anim'
        return keys
    def begin_capture(self,action):
        if self.hotkey.error:self.set_status('Hotkeys unavailable: '+self.hotkey.error);return
        self.capture_action=action;self.ui.focus_neutral();self.hotkey.capture() # Keep the key from re-pressing a button.
        self.set_status(f'Press any key for {self.action_label(action)}. Esc cancels.')
    def unbind_action(self,action):
        if action=='apply_anim':self.apply_vk=0;self.apply_name='None'
        elif action=='freelook':self.freelook_vk=0;self.freelook_name='None'
        else:self.hotkeys.pop(action,None)
    def assign_hotkey(self,vk,name):
        action=self.capture_action;self.capture_action=None
        if not action:return
        moved=[other for key,other in self.bindings().items() if key==vk and other!=action]
        for other in moved:self.unbind_action(other)
        if action=='apply_anim':self.apply_vk=vk;self.apply_name=name
        elif action=='freelook':self.freelook_vk=vk;self.freelook_name=name
        else:self.hotkeys[action]={'vk':vk,'name':name}
        notes=['moved from '+self.action_label(other) for other in moved]
        if vk in GAME_KEYS:notes.append("BO2 won't receive this key while freelook is on" if action=='freelook' else 'BO2 still receives this key, so it also does its game action')
        self.save();self.ui.changed('hotkeys')
        self.set_status(f'{name} → {self.action_label(action)}'+(' ('+'; '.join(notes)+')' if notes else '')+'. Works while BO2 is focused.')
    def clear_hotkey(self,action):
        self.unbind_action(action);self.save();self.ui.changed('hotkeys');self.set_status('Hotkey cleared: '+self.action_label(action))
    def set_hotkey_options(self,**values):
        if 'replay_enabled' in values:self.replay_enabled=bool(values['replay_enabled'])
        if 'freelook_enabled' in values:self.freelook_enabled=bool(values['freelook_enabled'])
        if 'freelook_speed' in values:self.freelook_speed=self.clamp_speed(values['freelook_speed'])
        self.save();self.ui.changed('hotkeys')
    def set_movement(self,save=True,**values):
        """Movement sliders, as percent of BO2's defaults (speed, sprint, jump). Applied by tick() to the attached game."""
        for key,value in values.items():
            if key in MOVEMENT_LIMITS:self.movement[key]=clamp_percent(key,value)
        self.mover.checked=0.0
        if save:self.save()
        self.ui.changed('movement')
    def reset_movement(self):self.set_movement(**{key:100 for key in MOVEMENT_LIMITS})
    def run_action(self,action):
        if action=='apply_anim':
            if self.replay_enabled:self.request_replay()
        elif action in self.actions:
            label,callback,enabled=self.actions[action]
            if enabled():callback()
    def tick(self):
        """Called by the UI every ~20 ms: configure listeners and dispatch hotkey events."""
        if self.closing:return
        pid=self.session.pid if self.session else self.last_snapshot.get('pid',0)
        self.hotkey.configure(self.bindings(active=True),pid)
        self.freelook.degrees_per_pixel=self.freelook_speed;self.freelook.configure(self.freelook_vk,pid,self.freelook_enabled and bool(self.freelook_vk))
        if self.freelook.error:self.write_log('Freelook: '+self.freelook.error);self.freelook.error=None
        self.mover.update(pid,self.movement)
        if self.mover.error:self.write_log('Movement: '+self.mover.error);self.mover.error=None
        if self.hotkey.error and not self.replay_error_shown:
            self.write_log('Hotkeys unavailable: '+self.hotkey.error+'. The buttons still work.');self.replay_error_shown=True
        while True:
            try:event=self.hotkey.events.get_nowait()
            except queue.Empty:break
            if event[0]=='capture':self.assign_hotkey(event[1],event[2])
            elif event[0]=='cancel':self.capture_action=None;self.set_status('Hotkey unchanged.')
            elif event[2]==pid:self.run_action(event[1])

    # Live target observer (read-only)
    def show_snapshot(self,snapshot):
        self.last_snapshot=snapshot;self.detected_at=time.monotonic()
        primary=snapshot.get('primary')
        if primary:
            self.detected='Now: '+primary['action']+' • '+primary['target']
            if self.follow_live and self.target!=primary['target']:self.set_target(primary['target'])
        else:
            self.detected=snapshot.get('message','Waiting for the game.')
            if self.follow_live:self.target_note='Automatic target: waiting for a match.';self.ui.changed('target')
        for item in snapshot.get('animations',[]):
            if item['selectable'] and item['target'] not in self.targets:self.targets=sorted([*self.targets,item['target']]);self.ui.changed('targets')
        self.ui.changed('snapshot')
    def observe_game(self):
        session=None;reader=None;folder=None;last_message=None
        try:
            while not self.observe_stop.is_set():
                try:
                    current_folder=self.bo2;pids=game_pids(current_folder)
                    if len(pids)!=1:
                        if session:session.close();session=None;reader=None
                        snapshot={'ready':False,'message':'Open one BO2 multiplayer instance to detect your animation.'}
                    else:
                        if session and (session.pid!=pids[0] or folder!=current_folder):session.close();session=None;reader=None
                        if not session:
                            session=Session(pids[0],read_only=True);reader=LiveTargetReader(session);folder=current_folder
                        snapshot=reader.snapshot()
                        snapshot['pid']=session.pid
                    self.post(lambda value=snapshot:self.show_snapshot(value));last_message=None
                except AnimationChanging:
                    self.post(lambda:self.show_snapshot({'ready':False,'message':'Animation is transitioning…'}))
                except (OSError,ValueError,RuntimeError) as e:
                    if session:session.close();session=None;reader=None
                    message=str(e)
                    if message!=last_message:
                        self.post(lambda:self.show_snapshot({'ready':False,'message':'Waiting for BO2’s live character data…'}));last_message=message
                    self.observe_stop.wait(1)
                self.observe_stop.wait(0.25)
        finally:
            if session:session.close()

    # Libraries
    def load_basics(self):
        if not self.idle():return
        cod4=self.cod4;bo2=self.bo2
        def work():
            try:
                mapping,targets=scan(cod4,bo2,self.log)
                def done():self.mapping=mapping;self.targets=targets;self.ui.changed('targets');self.refresh();self.save()
                self.post(done)
            except Exception as e:self.log(str(e))
            finally:self.post(self.busy_changed)
        self.indexthread=threading.Thread(target=work);self.indexthread.start();self.busy_changed()
    def detect_folders(self,save=True):
        found=detect_folders({'bo2':self.bo2,'cod4':self.cod4,'mw2':self.mw2,'mw3':self.mw3});changes=[]
        for key,label in (('bo2','BO2 Redacted'),('cod4','COD4'),('mw2','MW2'),('mw3','MW3')):
            if found[key]!=getattr(self,key):setattr(self,key,found[key]);changes.append(f'{label}: {found[key]}')
        self.folders_changed=bool(changes)
        if changes:self.log('Found game folders — '+'; '.join(changes))
        if changes and save:self.save()
        self.ui.changed('folders');return found
    def build_choices(self):
        """(game, folder found, clips in the library, ticked) for the Build libraries row. A game is ticked by default
        when its folder is found and it has no clips yet, so games already built are skipped; the user can tick them to rebuild."""
        from library import game_zones,FOLDER_KEY
        rows=[]
        for game in GAMES:
            found=game_zones(game,getattr(self,FOLDER_KEY[game]))is not None;count=sum(x['game']==game for x in self.catalog)
            rows.append((game,found,count,found and self.build_picks.get(game,count==0)))
        return rows
    def pick_build(self,game,on):self.build_picks[game]=bool(on);self.ui.changed('build')
    def reindex(self):
        """Build the ticked games' libraries (one click). Pressing it again while building cancels."""
        if self.building:self.build_cancel.set();self.set_status('Cancelling the library build…');return
        if not self.idle():return
        games=[game for game,found,count,ticked in self.build_choices() if ticked]
        if not games:self.set_status('Nothing to build: every game found is already in the library. Tick a game to rebuild it.');return
        folders={'cod4':self.cod4,'mw2':self.mw2,'mw3':self.mw3,'bo2':self.bo2};old=[dict(x) for x in self.catalog]
        self.building=True;self.build_cancel.clear();self.set_status('Building libraries…')
        def progress(done,total,text):self.post(lambda:self.set_status(f'Building libraries: {done}/{total} zones • {text}' if done<total else 'Building libraries: finishing…'))
        def work():
            try:
                from library import index_libraries
                result=index_libraries(folders,ROOT/'library',TOOLS/'Unlinker.exe',self.log,lambda:self.closing or self.build_cancel.is_set(),progress,games)
                if result is None:self.post(lambda:self.set_status('Library build cancelled. Build again to continue where it stopped.'));return
                catalog,built,skipped=result
                kept=[x for x in old if x['game'] not in built] # Games not built (unticked or not installed) keep their clips.
                for item in catalog+kept:
                    try:item['path']=str(Path(item['path']).resolve().relative_to(ROOT))
                    except ValueError:item['path']=str(Path(item['path']).resolve()) # Clips outside the tool folder stay absolute.
                write_atomic(ROOT/'library/catalog.json',json.dumps(catalog+kept))
                self.post(lambda:self.after_build(old,built,skipped))
            except Exception as e:
                message=str(e);self.log(message);self.post(lambda:self.set_status('Library build stopped: '+message))
            finally:self.post(self.build_finished)
        self.indexthread=threading.Thread(target=work);self.indexthread.start();self.busy_changed()
    def build_finished(self):self.building=False;self.busy_changed()
    def after_build(self,old,built,skipped):
        """Re-point replacements at the rebuilt clip files, matched by game/zone/name."""
        old_keys={x['path']:self.clip_key(x) for x in old};self.read_library();paths={self.clip_key(x):x['path'] for x in self.catalog}
        moved=lambda path:paths.get(old_keys.get(path),path)
        self.mapping={target:moved(path) for target,path in self.mapping.items()};self.replay_path=moved(self.replay_path) if self.replay_path else ''
        self.save();self.refresh()
        counts=', '.join(f"{short(game)} {sum(x['game']==game for x in self.catalog):,}" for game in GAMES if any(x['game']==game for x in self.catalog))
        rest=[game for game in GAMES if game not in built]
        self.build_picks={};self.ui.changed('build') # Back to the defaults: what was just built is now skipped.
        names=lambda games:', '.join(map(short,games))
        self.set_status(f"Built {names(built) or 'nothing'}. Library: {counts}."+(f" Kept as they were: {names(rest)}." if rest else '')+(f" Folder not found: {names(skipped)}." if skipped else ''))
    def enable_camera(self):
        try:
            path=install_camera(self.bo2)
            self.log('Installed the Third Person Camera: '+str(path))
            self.log('Start a new custom match you host. Third person turns on after you spawn; hold Use and press action slot 1 (F + 1 with your bindings) to switch views.')
            self.set_status('Third Person Camera installed. Start a new custom match you host, then hold F and press 1 to switch views.')
        except (OSError,ValueError) as e:self.log(str(e));self.set_status('Third Person Camera setup stopped: '+str(e))

    # Importer
    def start(self):
        if not self.idle():return
        bo2=self.bo2;self.save()
        self.stop_event.clear();self.set_live('Preparing animation imports…')
        def worker():
            failure=None
            try:
                pids=game_pids(bo2)
                if len(pids)>1:raise RuntimeError('More than one BO2 process is running. Close the extra game instance.')
                if not pids:
                    exe=Path(bo2)/'t6mpv43.exe'
                    if not exe.exists():exe=Path(bo2)/'t6mp.exe'
                    if not exe.exists():raise FileNotFoundError('Cannot find Redacted multiplayer in that folder.')
                    subprocess.Popen([str(exe)],cwd=bo2)
                    self.log(f'Started {exe.name}. The importer will apply when the animation bank is ready.')
                else:self.log('Using your running BO2 session.')
                applied=0;last_pid=None;attempt=0;pending_restarts={}
                while not self.stop_event.is_set():
                    self.worker_wake.clear();replay_messages=[]
                    pids=game_pids(bo2)
                    if len(pids)>1:raise RuntimeError('Multiple BO2 instances found. Import stopped to avoid choosing the wrong one.')
                    if not pids:
                        if last_pid:self.log('BO2 closed. Its original animations will load next time.');break
                        attempt+=1
                        if attempt>60:raise RuntimeError('BO2 did not start. Check the game window for a launch error.')
                        self.stop_event.wait(2);continue
                    pid=pids[0]
                    with self.lock:
                        if self.session is None:
                            try:self.session=Session(pid);last_pid=pid
                            except (OSError,RuntimeError):
                                self.post(lambda:self.set_live('Waiting for BO2’s multiplayer animation bank…'))
                                attempt+=1
                                if attempt>90:raise RuntimeError('BO2 animation-bank discovery timed out. This executable may be unsupported.')
                                self.stop_event.wait(2);continue
                        if self.session.pid!=pid:raise RuntimeError('BO2 restarted during import. Stop, then launch and apply again.')
                        mapping=dict(self.mapping)
                        restored=self.session.restore_targets(set(self.session.imported)-set(mapping))
                        report=self.session.apply(mapping)
                        applied=len(self.session.imported)
                        while True:
                            try:
                                target,path,notify,deadline=self.restart_requests.get_nowait();pending_restarts[target]=(path,notify,deadline)
                            except queue.Empty:break
                        for target,(path,notify,deadline) in list(pending_restarts.items()):
                            if target not in mapping:pending_restarts.pop(target,None);continue
                            if mapping.get(target)!=path:continue
                            try:
                                if not hasattr(self.session,'live_reader'):self.session.live_reader=LiveTargetReader(self.session)
                                count=self.session.live_reader.restart({target})
                                if notify:replay_messages.append('Applied anim to '+target+' and restarted it.' if count else 'Apply anim target is not active: '+target+'. Use its matching pose, or assign your clip to an idle slot.')
                            except AnimationChanging:
                                if time.monotonic()<deadline:continue
                                if notify:replay_messages.append('Animation is transitioning. Press the apply anim key again.')
                            except (OSError,RuntimeError,ValueError) as e:
                                if notify:replay_messages.append('Apply anim unavailable: '+str(e))
                            pending_restarts.pop(target,None)
                    if restored:self.log(f'Restored {restored} removed replacements.')
                    if report:
                        applied=len(self.session.imported)
                        self.log(f'Applied and verified {len(report)} animation updates ({applied} active).')
                        omitted=sorted({bone for item in report for bone in item['omitted_bones']})
                        if omitted:self.log('Optional bones absent from this rig: '+', '.join(omitted))
                        (STATE/'last_import.json').write_text(json.dumps({'pid':pid,'active_count':applied,'updates':report},indent=2))
                    self.post(lambda count=applied,pid=pid:self.set_live(f'{count} imported animations active • BO2 process {pid}'))
                    for message in replay_messages:self.log(message);self.post(lambda value=message:self.set_status(value))
                    if (report or restored) and not replay_messages:self.post(lambda:self.set_status('Active. Map and demo reloads are checked automatically.'))
                    self.worker_wake.wait(0.5)
            except Exception as e:
                failure=str(e);self.log(failure);self.post(lambda:self.set_status('Import stopped: '+failure))
            finally:
                with self.lock:
                    if self.session:
                        try:
                            restored=self.session.restore();self.log(f'Restored {restored} original animation entries.')
                        except (OSError,RuntimeError):pass
                        self.session.close();self.session=None
                def finish():
                    self.set_live('Importer stopped. BO2 animation files were never changed.')
                    self.set_status('Import stopped: '+failure if failure else 'Original animation entries restored. Live target detection continues.');self.busy_changed()
                self.post(finish)
        self.worker=threading.Thread(target=worker);self.worker.start();self.busy_changed()
    def stop(self):self.stop_event.set();self.worker_wake.set();self.set_status('Stopping and restoring the current session…')

    # Shutdown: stop every thread; the UI closes once finished() is True.
    def close(self):self.logfile.write('closing: restoring the game and stopping');self.stop_event.set();self.worker_wake.set();self.observe_stop.set();self.hotkey.stop();self.freelook.stop();self.mover.restore(quiet=True);self.closing=True
    def finished(self):
        done=self.idle() and not self.observer.is_alive() and not self.hotkey.is_alive() and not self.freelook.is_alive()
        if done and self.closing and self.logfile.file:self.logfile.write('closed');self.logfile.close() # Lets the next session rotate it.
        return done
