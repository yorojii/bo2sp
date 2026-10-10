"""CoD4 body-animation importer for BO2 Redacted MP (GPL-3.0-or-later)."""
from pathlib import Path
import csv,ctypes,hashlib,json,os,queue,subprocess,sys,threading,time,tkinter as tk
from tkinter import ttk,filedialog,messagebox
from ctypes import wintypes
from runtime import Session,decode,load_clip,body_clip,k
from camera import install_camera
from live_target import LiveTargetReader,AnimationChanging
from replay_hotkey import ReplayHotkey,KEYS

ROOT=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
TOOLS=ROOT/'tools';STATE=ROOT/'state';STATE.mkdir(exist_ok=True)

class ProcessEntry(ctypes.Structure):
    _fields_=[('size',wintypes.DWORD),('usage',wintypes.DWORD),('pid',wintypes.DWORD),('heap',ctypes.c_size_t),
              ('module',wintypes.DWORD),('threads',wintypes.DWORD),('parent',wintypes.DWORD),
              ('priority',wintypes.LONG),('flags',wintypes.DWORD),('exe',wintypes.WCHAR*260)]
k.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD];k.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
k.Process32FirstW.argtypes=[wintypes.HANDLE,ctypes.POINTER(ProcessEntry)];k.Process32FirstW.restype=wintypes.BOOL
k.Process32NextW.argtypes=k.Process32FirstW.argtypes;k.Process32NextW.restype=wintypes.BOOL
k.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)];k.QueryFullProcessImageNameW.restype=wintypes.BOOL

def game_pids(folder):
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
                        if k.QueryFullProcessImageNameW(handle,0,buf,ctypes.byref(length)):
                            if Path(buf.value).parent.resolve()==Path(folder).resolve():result.append(row.pid)
                    finally:k.CloseHandle(handle)
            ok=k.Process32NextW(snapshot,ctypes.byref(row))
    finally:k.CloseHandle(snapshot)
    return result

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
        if len(found)!=1:raise FileNotFoundError('Cannot find CoD4 zone/<language>/common_mp.ff.')
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
    if not mapping:raise ValueError('No compatible basic CoD4 body animations were found.')
    for path in mapping.values():decode(Path(path).read_bytes())
    log(f'Ready: {len(mapping)} basic animations, including {sum("death" in n for n in mapping)} deaths.')
    return mapping,sorted(set(targets))

class App(tk.Tk):
    def __init__(self):
        super().__init__();self.title('Yoroji Tool');self.geometry('1080x940');self.minsize(940,860)
        self.mapping={};self.targets=[];self.catalog=[];self.session=None;self.stop_event=threading.Event();self.worker=None;self.indexthread=None;self.lock=threading.Lock();self.closing=False
        self.cod4=tk.StringVar(value=r'D:\Call of Duty 4');self.bo2=tk.StringVar(value=r'F:\Games\Call of Duty Black Ops IIOLD');self.mw2=tk.StringVar(value=r'D:\SteamLibrary\steamapps\common\Call of Duty Modern Warfare 2')
        profile={}
        try:
            profile=json.loads((ROOT/'profile.json').read_text());self.cod4.set(profile['cod4']);self.bo2.set(profile['bo2']);self.mw2.set(profile.get('mw2',self.mw2.get()))
            self.mapping={name:str((ROOT/path).resolve()) for name,path in profile.get('mapping',{}).items() if (ROOT/path).is_file()};self.targets=profile.get('targets',[])
        except (OSError,ValueError,KeyError):pass
        self.status=tk.StringVar(value='Choose a source clip and a BO2 replacement slot.');self.live=tk.StringVar(value='Imports inactive. Live target detection is running.');self.target=tk.StringVar(value='pb_stand_alert')
        self.follow_live=tk.BooleanVar(value=True);self.live_lock=False;self.last_snapshot={};self.detected_at=0
        self.detected=tk.StringVar(value='Looking for your character…');self.target_note=tk.StringVar(value='Automatic target: waiting for a match.')
        self.observe_stop=threading.Event();self.observer_folder=self.bo2.get();self.restart_requests=queue.SimpleQueue()
        self.worker_wake=threading.Event();self.replay_target=profile.get('replay',{}).get('target','')
        replay_source=profile.get('replay',{}).get('source','')
        self.replay_path=str((ROOT/replay_source).resolve()) if replay_source and (ROOT/replay_source).is_file() else self.mapping.get(self.replay_target,'')
        replay_key=profile.get('replay',{}).get('key','F6')
        self.replay_key=tk.StringVar(value=replay_key if replay_key in KEYS else 'F6')
        self.replay_enabled=tk.BooleanVar(value=profile.get('replay',{}).get('enabled',True))
        self.replay_note=tk.StringVar();self.replay_error_shown=False
        self.bo2.trace_add('write',lambda *args:setattr(self,'observer_folder',self.bo2.get()))
        self.target.trace_add('write',lambda *args:self.update_target_note())
        style=ttk.Style(self);style.theme_use('clam');style.configure('Title.TLabel',font=('Segoe UI',20,'bold'));style.configure('TButton',padding=(9,6))
        body=ttk.Frame(self,padding=18);body.pack(fill='both',expand=True);body.columnconfigure(0,weight=1);body.rowconfigure(5,weight=1)
        ttk.Label(body,text='Yoroji Tool',style='Title.TLabel').grid(row=0,column=0,sticky='w')
        ttk.Label(body,text='CoD4 single-player & multiplayer / MW2 actor animations → BO2 Redacted MP').grid(row=1,column=0,sticky='w',pady=(3,10))
        row=ttk.Frame(body);row.grid(row=2,column=0,sticky='ew',pady=4)
        ttk.Label(row,text='BO2 folder').pack(side='left',padx=(0,12));ttk.Entry(row,textvariable=self.bo2).pack(side='left',fill='x',expand=True);ttk.Button(row,text='Game folders…',command=self.settings).pack(side='left',padx=(8,0))
        row=ttk.Frame(body);row.grid(row=3,column=0,sticky='ew',pady=8)
        self.scanbutton=ttk.Button(row,text='Load CoD4 basics',command=self.load);self.scanbutton.pack(side='left')
        ttk.Button(row,text='Import animation file…',command=self.import_clip).pack(side='left',padx=6)
        self.indexbutton=ttk.Button(row,text='Refresh source libraries',command=self.reindex);self.indexbutton.pack(side='left')
        live_panel=ttk.LabelFrame(body,text='Live character target',padding=8);live_panel.grid(row=4,column=0,sticky='ew',pady=4)
        ttk.Label(live_panel,textvariable=self.detected,font=('Segoe UI',11,'bold')).pack(anchor='w')
        live_controls=ttk.Frame(live_panel);live_controls.pack(fill='x',pady=(5,0))
        ttk.Checkbutton(live_controls,text='Follow current animation',variable=self.follow_live,command=self.follow_changed).pack(side='left')
        ttk.Button(live_controls,text='Lock current target',command=self.lock_current).pack(side='left',padx=10)
        ttk.Label(live_controls,textvariable=self.target_note).pack(side='left',padx=6)
        replay_controls=ttk.Frame(live_panel);replay_controls.pack(fill='x',pady=(6,0))
        ttk.Checkbutton(replay_controls,text='Replay hotkey',variable=self.replay_enabled,command=self.replay_settings_changed).pack(side='left')
        self.replay_keybox=ttk.Combobox(replay_controls,textvariable=self.replay_key,values=list(KEYS),state='readonly',width=7);self.replay_keybox.pack(side='left',padx=8)
        self.replay_keybox.bind('<<ComboboxSelected>>',lambda event:self.replay_settings_changed())
        ttk.Button(replay_controls,text='Replay now',command=self.request_replay).pack(side='left')
        ttk.Label(replay_controls,textvariable=self.replay_note,wraplength=590).pack(side='left',padx=12)
        self.notebook=ttk.Notebook(body);self.notebook.grid(row=5,column=0,sticky='nsew',pady=8);self.panels={};self.targetboxes=[]
        for game in ('CoD4','MW2 Actors'):
            panel=ttk.Frame(self.notebook,padding=10);self.notebook.add(panel,text=game);panel.columnconfigure(0,weight=1);panel.rowconfigure(2,weight=1)
            controls=ttk.Frame(panel);controls.grid(row=0,column=0,sticky='ew')
            ttk.Label(controls,text='Search').pack(side='left');query=tk.StringVar();ttk.Entry(controls,textvariable=query,width=37).pack(side='left',padx=7)
            ttk.Label(controls,text='Scene / zone').pack(side='left',padx=(12,5));zone=tk.StringVar(value='All');zbox=ttk.Combobox(controls,textvariable=zone,values=['All'],state='readonly',width=23);zbox.pack(side='left')
            count=tk.StringVar();ttk.Label(panel,textvariable=count).grid(row=1,column=0,sticky='w',pady=7)
            table=ttk.Frame(panel);table.grid(row=2,column=0,sticky='nsew');tree=ttk.Treeview(table,columns=('name','zone','duration','loop','bones'),show='headings',selectmode='browse')
            for key,label,width in [('name','Source animation',420),('zone','Scene / zone',170),('duration','Seconds',85),('loop','Loop',60),('bones','Bones',60)]:tree.heading(key,text=label);tree.column(key,width=width,stretch=key=='name')
            tree.pack(side='left',fill='both',expand=True);scroll=ttk.Scrollbar(table,orient='vertical',command=tree.yview);scroll.pack(side='right',fill='y');tree.configure(yscrollcommand=scroll.set)
            footer=ttk.Frame(panel);footer.grid(row=3,column=0,sticky='ew',pady=(10,0));ttk.Label(footer,text='BO2 slot to replace').pack(side='left');combo=ttk.Combobox(footer,textvariable=self.target,values=self.targets,width=43);combo.pack(side='left',padx=8);self.targetboxes.append(combo);ttk.Button(footer,text='Use selected clip',command=lambda g=game:self.use_clip(g)).pack(side='left')
            combo.bind('<<ComboboxSelected>>',self.manual_target);combo.bind('<KeyPress>',self.manual_target)
            self.panels[game]=(query,zone,zbox,count,tree)
            query.trace_add('write',lambda *args,g=game:self.render_catalog(g));zone.trace_add('write',lambda *args,g=game:self.render_catalog(g));tree.bind('<<TreeviewSelect>>',lambda event,g=game:self.choose_target(g))
        panel=ttk.Frame(self.notebook,padding=10);self.notebook.add(panel,text='Selected replacements');panel.columnconfigure(0,weight=1);panel.rowconfigure(0,weight=1)
        self.tree=ttk.Treeview(panel,columns=('target','source'),show='headings',selectmode='extended');self.tree.heading('target',text='BO2 animation slot');self.tree.heading('source',text='Source clip');self.tree.column('target',width=410);self.tree.column('source',width=410);self.tree.grid(row=0,column=0,sticky='nsew')
        scroll=ttk.Scrollbar(panel,orient='vertical',command=self.tree.yview);scroll.grid(row=0,column=1,sticky='ns');self.tree.configure(yscrollcommand=scroll.set)
        controls=ttk.Frame(panel);controls.grid(row=1,column=0,sticky='w',pady=(10,0));ttk.Button(controls,text='Remove selected',command=self.remove).pack(side='left');ttk.Button(controls,text='Clear selection',command=self.clear).pack(side='left',padx=8)
        live_tab=ttk.Frame(self.notebook,padding=10);self.notebook.add(live_tab,text='Live target');live_tab.columnconfigure(0,weight=1);live_tab.rowconfigure(1,weight=1)
        ttk.Label(live_tab,text='These are the animation layers contributing to your current character pose.').grid(row=0,column=0,sticky='w',pady=(0,8))
        self.active_tree=ttk.Treeview(live_tab,columns=('target','layer','weight','action','replacement'),show='headings',selectmode='browse')
        for key,label,width in [('target','Active BO2 animation',330),('layer','Layer',100),('weight','Blend',70),('action','Action',140),('replacement','Your replacement',300)]:self.active_tree.heading(key,text=label);self.active_tree.column(key,width=width,stretch=key in ('target','replacement'))
        self.active_tree.grid(row=1,column=0,sticky='nsew');self.active_tree.tag_configure('upper',foreground='#777777')
        live_footer=ttk.Frame(live_tab);live_footer.grid(row=2,column=0,sticky='ew',pady=(10,0))
        ttk.Button(live_footer,text='Use highlighted target',command=self.lock_highlighted).pack(side='left')
        ttk.Label(live_footer,text='Choose a Body layer for a full-character animation.').pack(side='left',padx=12)
        row=ttk.Frame(body);row.grid(row=6,column=0,sticky='ew',pady=9)
        self.startbutton=ttk.Button(row,text='Launch BO2 & apply',command=self.start);self.startbutton.pack(side='left');ttk.Button(row,text='Stop & restore',command=self.stop).pack(side='left',padx=8)
        ttk.Button(row,text='Enable third-person camera',command=self.enable_camera).pack(side='left',padx=4)
        ttk.Label(body,textvariable=self.live,font=('Segoe UI',11,'bold')).grid(row=7,column=0,sticky='w')
        ttk.Label(body,textvariable=self.status,wraplength=1010).grid(row=8,column=0,sticky='w',pady=5)
        self.logbox=tk.Text(body,height=4,wrap='word',state='disabled',font=('Consolas',9));self.logbox.grid(row=9,column=0,sticky='ew')
        ttk.Label(body,text='Use selected clip applies live when your match is detected. Closing Yoroji Tool restores the animations.').grid(row=10,column=0,sticky='w',pady=(8,0))
        self.protocol('WM_DELETE_WINDOW',self.close_app);self.read_library();self.refresh()
        self.observer=threading.Thread(target=self.observe_game);self.observer.start()
        self.hotkey=ReplayHotkey();self.after(20,self.poll_replay_key)
    def post(self,fn):
        if not self.closing:self.after(0,fn)
    def log(self,text):
        def append():self.logbox.configure(state='normal');self.logbox.insert('end',str(text)+'\n');self.logbox.see('end');self.logbox.configure(state='disabled')
        self.post(append)
    def idle(self):return not ((self.worker and self.worker.is_alive()) or (self.indexthread and self.indexthread.is_alive()))
    def editable(self):return not self.closing and not (self.indexthread and self.indexthread.is_alive())
    def replay_settings_changed(self):self.save()
    def queue_restart(self,target,path,notify=False):
        self.restart_requests.put((target,path,notify,time.monotonic()+1.0));self.worker_wake.set()
    def request_replay(self):
        if not self.editable():return False
        if not self.replay_path:
            self.status.set('Select a CoD4 or MW2 clip first, then press your replay key.');return False
        if not self.last_snapshot.get('ready') or time.monotonic()-self.detected_at>2:
            self.status.set('Wait for a live character animation before pressing the replay key.');return False
        if self.worker and self.worker.is_alive() and self.stop_event.is_set():
            self.status.set('Wait for restoration to finish before replaying.');return False
        target=self.last_snapshot['primary']['target'] if self.follow_live.get() else self.target.get()
        if target not in self.targets:
            self.status.set('Choose a valid BO2 slot or enable Follow current animation.');return False
        path=self.replay_path;changed=self.mapping.get(target)!=path or self.replay_target!=target
        self.replay_target=target
        if changed:
            self.mapping={**self.mapping,target:path};self.refresh();self.save()
        self.update_replay_note()
        self.queue_restart(target,path,True);self.status.set('Replay queued: '+target)
        if self.idle():self.start()
        return True
    def update_replay_note(self):
        name=next((x['name'] for x in self.catalog if x['path']==self.replay_path),Path(self.replay_path).stem if self.replay_path else '')
        mode='current live slot' if self.follow_live.get() else self.target.get()
        self.replay_note.set('Replay: '+name+' → '+mode if name else 'Select a clip, then press the replay key.')
    def poll_replay_key(self):
        if self.closing:return
        pid=self.session.pid if self.session else self.last_snapshot.get('pid',0)
        self.hotkey.configure(self.replay_key.get(),pid,self.replay_enabled.get())
        if self.hotkey.error and not self.replay_error_shown:
            self.log('Replay key unavailable: '+self.hotkey.error+'. The Replay now button still works.');self.replay_error_shown=True
        while True:
            try:
                pressed_pid=self.hotkey.events.get_nowait()
                if pressed_pid==pid and self.replay_enabled.get():self.request_replay()
            except queue.Empty:break
        self.after(20,self.poll_replay_key)
    def update_target_note(self):
        mode='Automatic target' if self.follow_live.get() else 'Locked target'
        self.target_note.set(mode+': '+self.target.get())
        self.update_replay_note()
    def follow_changed(self):
        self.live_lock=not self.follow_live.get()
        if self.follow_live.get() and self.last_snapshot.get('ready'):self.target.set(self.last_snapshot['primary']['target'])
        self.update_target_note()
    def manual_target(self,event=None):
        self.follow_live.set(False);self.live_lock=True;self.update_target_note()
    def lock_current(self):
        if not self.last_snapshot.get('ready') or time.monotonic()-self.detected_at>2:
            self.status.set('Start a match and wait for a detected body animation first.');return
        self.target.set(self.last_snapshot['primary']['target']);self.manual_target()
        self.status.set('Target locked. Choose a CoD4 or MW2 actor clip, then Use selected clip.')
    def lock_highlighted(self):
        selected=self.active_tree.selection()
        if not selected:return
        name=selected[0]
        if not any(x['target']==name and x['selectable'] for x in self.last_snapshot.get('animations',[])):
            self.status.set('Choose a Body layer to replace with a full-character clip.');return
        self.target.set(name);self.manual_target();self.notebook.select(0)
    def show_snapshot(self,snapshot):
        self.last_snapshot=snapshot;self.detected_at=time.monotonic()
        primary=snapshot.get('primary')
        if primary:
            self.detected.set('Now: '+primary['action']+' • '+primary['target'])
            if self.follow_live.get():self.target.set(primary['target'])
        else:
            self.detected.set(snapshot.get('message','Waiting for the game.'))
            if self.follow_live.get():self.target_note.set('Automatic target: waiting for a match.')
        items=snapshot.get('animations',[]);names={x['target'] for x in items}
        for iid in self.active_tree.get_children():
            if iid not in names:self.active_tree.delete(iid)
        lookup={x['path']:x['name'] for x in self.catalog}
        for item in items:
            name=item['target'];path=self.mapping.get(name);source=lookup.get(path,Path(path).stem if path else 'Original BO2')
            values=(name,item['layer'],f"{item['weight']:.0%}",item['action'],source)
            if self.active_tree.exists(name):self.active_tree.item(name,values=values)
            else:self.active_tree.insert('','end',iid=name,values=values,tags=() if item['selectable'] else ('upper',))
            if item['selectable'] and name not in self.targets:
                self.targets=sorted([*self.targets,name])
                for box in self.targetboxes:box.configure(values=self.targets)
    def observe_game(self):
        session=None;reader=None;folder=None;last_message=None
        try:
            while not self.observe_stop.is_set():
                try:
                    current_folder=self.observer_folder;pids=game_pids(current_folder)
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
    def read_library(self):
        try:
            self.catalog=json.loads((ROOT/'library/catalog.json').read_text())
            for item in self.catalog:item['path']=str((ROOT/item['path']).resolve())
        except (OSError,ValueError):self.catalog=[]
        for game,(query,zone,zbox,count,tree) in self.panels.items():zbox.configure(values=['All']+sorted({x['zone'] for x in self.catalog if x['game']==game}));self.render_catalog(game)
    def render_catalog(self,game):
        query,zone,zbox,count,tree=self.panels[game];tree.delete(*tree.get_children());q=query.get().casefold();shown=0
        for index,item in enumerate(self.catalog):
            if item['game']!=game or (zone.get()!='All' and item['zone']!=zone.get()) or q not in (item['name']+' '+item['zone']).casefold():continue
            tree.insert('','end',iid=str(index),values=(item['name'],item['zone'],f"{item['frames']/item['fps']:.2f}",'Yes' if item['loop'] else 'No',item['bones']));shown+=1
        count.set(f'{shown:,} character clips • choose a looping slot for movement or a death slot for a death clip')
    def choose_target(self,game):
        tree=self.panels[game][4];selection=tree.selection()
        if selection:
            item=self.catalog[int(selection[0])];self.replay_path=item['path'];self.update_replay_note()
            if self.follow_live.get() or self.live_lock:return
            name=item['name']
            if name in self.targets:self.target.set(name)
    def use_clip(self,game):
        if not self.editable():return
        selection=self.panels[game][4].selection()
        if not selection:messagebox.showinfo('Select a clip','Choose an animation from this tab first.');return
        if self.follow_live.get() and not self.last_snapshot.get('ready'):
            self.status.set('Wait for a live body animation, or turn off Follow current animation and choose a slot manually.');return
        if self.target.get() not in self.targets:messagebox.showerror('Select a BO2 slot','Choose an existing BO2 animation slot.');return
        item=self.catalog[int(selection[0])];target=self.target.get();self.mapping={**self.mapping,target:item['path']}
        self.replay_target=target;self.replay_path=item['path'];self.queue_restart(target,item['path']);self.save();self.refresh();self.log(f"{game}: {item['name']} → {target}")
        if self.last_snapshot.get('ready') and self.idle():self.start()
    def refresh(self):
        if self.replay_target not in self.mapping:self.replay_target=''
        self.update_replay_note()
        for box in self.targetboxes:box.configure(values=self.targets)
        self.tree.delete(*self.tree.get_children());lookup={x['path']:x for x in self.catalog}
        for name,path in sorted(self.mapping.items()):
            item=lookup.get(path);label=f"{item['game']}: {item['name']} ({item['zone']})" if item else Path(path).stem
            self.tree.insert('','end',iid=name,values=(name,label))
        self.status.set(f'{len(self.mapping)} selected replacements. Use selected clip updates the current match.' if self.worker and self.worker.is_alive() else f'{len(self.mapping)} selected replacements. Lock a live target or choose a BO2 slot, then select a clip.')
    def save(self):
        mapping={}
        for name,path in self.mapping.items():
            try:mapping[name]=str(Path(path).resolve().relative_to(ROOT))
            except ValueError:mapping[name]=str(Path(path).resolve())
        replay_source=self.replay_path
        if replay_source:
            try:replay_source=str(Path(replay_source).resolve().relative_to(ROOT))
            except ValueError:pass
        (ROOT/'profile.json').write_text(json.dumps({'cod4':self.cod4.get(),'bo2':self.bo2.get(),'mw2':self.mw2.get(),'mapping':mapping,'targets':self.targets,'replay':{'key':self.replay_key.get(),'enabled':self.replay_enabled.get(),'target':self.replay_target,'source':replay_source}},indent=2))
    def settings(self):
        dialog=tk.Toplevel(self);dialog.title('Game folders');dialog.geometry('780x220');dialog.transient(self)
        for title,var in [('CoD4',self.cod4),('MW2',self.mw2),('BO2 Redacted',self.bo2)]:
            row=ttk.Frame(dialog,padding=8);row.pack(fill='x');ttk.Label(row,text=title,width=16).pack(side='left');ttk.Entry(row,textvariable=var).pack(side='left',fill='x',expand=True);ttk.Button(row,text='Browse',command=lambda v=var:self.browse(v)).pack(side='left',padx=5)
        ttk.Button(dialog,text='Save folders',command=lambda:(self.save(),dialog.destroy())).pack(pady=8)
    def browse(self,var):
        path=filedialog.askdirectory(initialdir=var.get())
        if path:var.set(path)
    def load(self):
        if not self.idle():return
        cod4=self.cod4.get();bo2=self.bo2.get();self.scanbutton.configure(state='disabled')
        def work():
            try:
                mapping,targets=scan(cod4,bo2,self.log)
                def done():self.mapping=mapping;self.targets=targets;self.refresh();self.save()
                self.post(done)
            except Exception as e:self.log(str(e))
            finally:self.post(lambda:self.scanbutton.configure(state='normal'))
        self.indexthread=threading.Thread(target=work);self.indexthread.start()
    def reindex(self):
        if not self.idle():return
        cod4=self.cod4.get();mw2=self.mw2.get();self.indexbutton.configure(state='disabled');self.startbutton.configure(state='disabled');self.status.set('Indexing character animations from your game folders…')
        def work():
            try:
                from library import index_libraries
                catalog=index_libraries(cod4,mw2,ROOT/'library',TOOLS/'Unlinker.exe',self.log,lambda:self.closing)
                if catalog is not None:
                    for item in catalog:item['path']=str(Path(item['path']).relative_to(ROOT))
                    (ROOT/'library/catalog.json').write_text(json.dumps(catalog));self.post(self.read_library);self.post(self.refresh)
            except Exception as e:self.log(str(e));self.post(lambda:self.status.set('Library scan stopped; see the log.'))
            finally:self.post(lambda:(self.indexbutton.configure(state='normal'),self.startbutton.configure(state='normal')))
        self.indexthread=threading.Thread(target=work);self.indexthread.start()
    def import_clip(self):
        if not self.editable():return
        if not self.targets:messagebox.showinfo('Load basics first','Load CoD4 basics to find BO2 target names.');return
        path=filedialog.askopenfilename(title='Select a compiled CoD4 / MW2 character animation',filetypes=[('Animation files','*')])
        if not path:return
        try:
            anim=load_clip(path)
            if not body_clip(anim):raise ValueError('Choose a character animation. Weapon, hand and vehicle rigs are not supported.')
        except Exception as e:messagebox.showerror('Unsupported animation',str(e));return
        if self.target.get() not in self.targets:messagebox.showerror('Select a slot','Choose the BO2 animation slot in either source tab first.');return
        if self.follow_live.get() and not self.last_snapshot.get('ready'):
            self.status.set('Wait for a live target, or turn off Follow current animation and choose a slot.');return
        target=self.target.get();self.mapping={**self.mapping,target:path};self.replay_target=target;self.replay_path=path;self.queue_restart(target,path);self.save();self.refresh()
        if self.last_snapshot.get('ready') and self.idle():self.start()
    def remove(self):
        if not self.editable():return
        removed=set(self.tree.selection());self.mapping={name:path for name,path in self.mapping.items() if name not in removed}
        self.worker_wake.set();self.refresh();self.save()
    def clear(self):
        if not self.editable():return
        self.mapping={};self.worker_wake.set();self.refresh();self.save()

    def start(self):
        if not self.idle():return
        cod4=self.cod4.get();bo2=self.bo2.get();mapping=dict(self.mapping);self.save()
        self.stop_event.clear();self.startbutton.configure(state='disabled');self.scanbutton.configure(state='disabled')
        self.live.set('Preparing animation imports…')
        def worker():
            failure=None
            try:
                pids=game_pids(bo2)
                if len(pids)>1:raise RuntimeError('More than one BO2 process is running. Close the extra game instance.')
                if not pids:
                    exe=Path(bo2)/'t6mpv43.exe'
                    if not exe.exists():exe=Path(bo2)/'t6mp.exe'
                    if not exe.exists():raise FileNotFoundError('Cannot find Redacted multiplayer in that folder.')
                    process=subprocess.Popen([str(exe)],cwd=bo2)
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
                                self.post(lambda:self.live.set('Waiting for BO2’s multiplayer animation bank…'))
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
                                if notify:replay_messages.append('Replayed '+target+' from the beginning.' if count else 'Replay target is not active: '+target+'. Use its matching pose, or assign your clip to an idle slot.')
                            except AnimationChanging:
                                if time.monotonic()<deadline:continue
                                if notify:replay_messages.append('Animation is transitioning. Press the replay key again.')
                            except (OSError,RuntimeError,ValueError) as e:
                                if notify:replay_messages.append('Replay unavailable: '+str(e))
                            pending_restarts.pop(target,None)
                    if restored:self.log(f'Restored {restored} removed replacements.')
                    if report:
                        applied=len(self.session.imported)
                        self.log(f'Applied and verified {len(report)} animation updates ({applied} active).')
                        omitted=sorted({bone for item in report for bone in item['omitted_bones']})
                        if omitted:self.log('Optional bones absent from this rig: '+', '.join(omitted))
                        (STATE/'last_import.json').write_text(json.dumps({'pid':pid,'active_count':applied,'updates':report},indent=2))
                    self.post(lambda count=applied,pid=pid:self.live.set(f'{count} imported animations active • BO2 process {pid}'))
                    for message in replay_messages:self.log(message);self.post(lambda value=message:self.status.set(value))
                    if (report or restored) and not replay_messages:self.post(lambda:self.status.set('Active. Map and demo reloads are checked automatically.'))
                    self.worker_wake.wait(0.5)
            except Exception as e:
                failure=str(e);self.log(failure);self.post(lambda:self.status.set('Import stopped: '+failure))
            finally:
                with self.lock:
                    if self.session:
                        try:
                            restored=self.session.restore();self.log(f'Restored {restored} original animation entries.')
                        except (OSError,RuntimeError):pass
                        self.session.close();self.session=None
                def finish():
                    self.startbutton.configure(state='normal');self.scanbutton.configure(state='normal');self.live.set('Importer stopped. BO2 animation files were never changed.')
                    self.status.set('Import stopped: '+failure if failure else 'Original animation entries restored. Live target detection continues.')
                self.post(finish)
        self.worker=threading.Thread(target=worker);self.worker.start()
    def stop(self):self.stop_event.set();self.worker_wake.set();self.status.set('Stopping and restoring the current session…')
    def enable_camera(self):
        try:
            path=install_camera(self.bo2.get())
            self.log('Installed the local-match camera helper: '+str(path))
            self.log('Start a new custom match. Third person turns on after spawning. Hold Use + scorestreak up (F + 1 with your bindings) to toggle.')
            self.status.set('Camera helper ready. Start a new custom match, then hold F and press 1 to switch views.')
        except (OSError,ValueError) as e:self.log(str(e));self.status.set('Camera setup stopped: '+str(e))
    def close_app(self):
        self.stop_event.set();self.worker_wake.set();self.observe_stop.set();self.hotkey.stop();self.closing=True
        def finish():
            if not self.idle() or self.observer.is_alive() or self.hotkey.is_alive():self.after(100,finish)
            else:self.destroy()
        finish()

def main():
    k.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR];k.CreateMutexW.restype=wintypes.HANDLE
    handle=k.CreateMutexW(None,False,r'Local\CoD4_BO2_Redacted_Animation_Importer')
    if not handle:raise OSError(ctypes.get_last_error(),'Cannot initialize importer')
    duplicate=ctypes.get_last_error()==183
    try:
        if duplicate:
            root=tk.Tk();root.withdraw();messagebox.showinfo('Importer already open','Use the existing animation importer window.');root.destroy()
        else:App().mainloop()
    finally:k.CloseHandle(handle)

if __name__=='__main__':main()
