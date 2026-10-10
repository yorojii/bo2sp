"""CoD4 compiled XAnim -> BO2 Redacted common_mp pack builder.

Uses OpenAssetTools v0.33.0; never edits a game's fastfiles until verification passes.
"""
from pathlib import Path
import csv, hashlib, json, os, re, shutil, struct, subprocess, threading, time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

HERE = Path(__file__).resolve().parent
TOOLS = HERE / 'tools'
STATE = HERE / 'state'
SAFE_NAME = re.compile(r'^[A-Za-z0-9_\-.]+$')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def run(tool, args, log):
    result = subprocess.run([str(TOOLS / tool), *map(str,args)], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace',
                            creationflags=subprocess.CREATE_NO_WINDOW)
    log(result.stdout)
    if result.returncode or re.search(r'\bERROR:', result.stdout):
        raise RuntimeError(result.stdout[-2500:] or f'{tool} failed with exit code {result.returncode}.')
    return result.stdout

def assets_from_list(text):
    result=[]; active=False
    for line in text.splitlines():
        if line == 'Content:': active=True; continue
        if active and line.startswith('Unloaded'): break
        if active and ',' in line:
            row=[x.strip() for x in next(csv.reader([line]))]
            result.append(row)
    if not result: raise ValueError('No assets found in the BO2 fastfile.')
    return result

def header(path):
    data=Path(path).read_bytes()
    if len(data)<12: raise ValueError(f'Not a compiled XAnim: {path}')
    v,frames,bones,flags,kind,fps=struct.unpack('<HHHBBH',data[:10])
    if v not in (17,18,19) or not fps or bones>255:
        raise ValueError(f'Unsupported compiled animation: {path}')
    return data,(v,frames,bones,flags,kind,fps)

def ensure_closed():
    result=subprocess.run(['tasklist','/FO','CSV','/NH'],capture_output=True,text=True,
                          creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode: raise RuntimeError('Cannot check whether BO2 is running.')
    if any(re.match(r'^"t6(?:mp|zm).*\.exe"', line, re.I) for line in result.stdout.splitlines()):
        raise RuntimeError('Close BO2 before building, installing, or restoring the pack.')

class Engine:
    def __init__(self,cod4,bo2,log=print):
        self.cod4=Path(cod4); self.bo2=Path(bo2); self.log=log
        self.live=self.bo2/'zone/all/common_mp.ff'
        self.key=hashlib.sha256(str(self.live.resolve()).lower().encode()).hexdigest()[:16]
        self.root=STATE/self.key; self.root.mkdir(parents=True,exist_ok=True)
        self.backup=self.root/'original_common_mp.ff'
        self.manifest=self.root/'install.json'
        self.source=self.root/'cod4/common_mp/xanim'

    def baseline(self):
        if not self.live.exists(): raise FileNotFoundError(f'BO2 fastfile missing: {self.live}')
        if self.backup.exists():
            meta=json.loads(self.manifest.read_text())
            if digest(self.backup)!=meta['original_sha256']:
                raise RuntimeError('Original backup checksum failed. No game files were changed.')
            if digest(self.live) not in (meta['original_sha256'],meta.get('installed_sha256')):
                raise RuntimeError('The game fastfile changed outside this tool. Preserve it before continuing.')
            return self.backup
        return self.live

    def scan(self):
        base=self.baseline()
        listing=run('Unlinker.exe',['--list',base],self.log)
        self.assets=assets_from_list(listing)
        self.targets=sorted(row[-1] for row in self.assets if row[0]=='xanim' and len(row)==2)
        source_ff=self.cod4/'zone/english/common_mp.ff'
        if not source_ff.exists():
            found=list((self.cod4/'zone').glob('*/common_mp.ff'))
            if len(found)!=1: raise FileNotFoundError('Cannot locate CoD4 zone/<language>/common_mp.ff.')
            source_ff=found[0]
        run('Unlinker.exe',['--include-assets','xanim','-o',self.source.parent,source_ff],self.log)
        self.sources=sorted(p.name for p in self.source.iterdir() if p.is_file())
        basics=('death','run','walk','sprint','jump','crawl','alert','ads','hold','prone2','crouch2')
        return {n:n for n in self.sources if n in self.targets and n.startswith('pb_') and any(k in n for k in basics)}

    def build(self,mapping,install=False):
        ensure_closed()
        if not hasattr(self,'assets'): self.scan()
        base=self.baseline()
        if not mapping: raise ValueError('Select at least one animation.')
        project=self.root/('build_'+time.strftime('%Y%m%d_%H%M%S'))
        raw=project/'raw/xanim'; raw.mkdir(parents=True)
        (project/'zone_source').mkdir()
        checks={}
        for target,source in mapping.items():
            if target not in self.targets or not SAFE_NAME.fullmatch(target):
                raise ValueError(f'Unknown BO2 animation target: {target}')
            path=Path(source)
            if not path.is_absolute(): path=self.source/source
            data,h=header(path)
            if h[0]!=17: raise ValueError(f'Expected CoD4 version 17 XAnim: {path.name}')
            if target.startswith('pb_') and not path.name.startswith('pb_'):
                raise ValueError('A body animation requires a CoD4 pb_ animation.')
            (raw/target).write_bytes(data); checks[target]=data
        lines=['>game,T6','>name,common_mp']
        for row in self.assets:
            lines.append(row[0]+','+','.join('"'+x.replace('"','""')+'"' if x else '' for x in row[1:]))
        (project/'zone_source/common_mp.zone').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        build_log=[]
        run('Linker.exe',['-b',project,'-l',base,'common_mp'],build_log.append)
        (project/'build.log').write_text('\n'.join(build_log),encoding='utf-8')
        built=project/'zone_out/common_mp/common_mp.ff'
        verify=project/'verify'
        verify_args=['--include-assets','xanim','-o',verify,built]
        if (self.bo2/'sound').is_dir(): verify_args[0:0]=['--search-path',self.bo2/'sound']
        run('Unlinker.exe',verify_args,self.log)
        for target,data in checks.items():
            converted,h=header(verify/'xanim'/target)
            if h[0]!=19 or data[2:]!=converted[2:]:
                raise RuntimeError(f'Animation data verification failed: {target}')
        listed=assets_from_list(run('Unlinker.exe',['--list',built],self.log))
        if sorted(map(tuple,listed))!=sorted(map(tuple,self.assets)):
            raise RuntimeError('The rebuilt fastfile asset inventory changed unexpectedly.')
        report={'count':len(mapping),'death_count':sum('death' in n for n in mapping),
                'sha256':digest(built),'mapping':mapping,'verified':'XAnim payloads and complete asset inventory',
                'runtime_verified':False}
        (project/'verification.json').write_text(json.dumps(report,indent=2))
        if install:
            ensure_closed()
            if not self.backup.exists():
                shutil.copy2(self.live,self.backup)
                meta={'game':str(self.bo2),'original_sha256':digest(self.backup)}
            else: meta=json.loads(self.manifest.read_text())
            meta['installed_sha256']=digest(built)
            self.manifest.write_text(json.dumps(meta,indent=2))
            temp=self.live.with_name('common_mp.cod4-import.tmp')
            shutil.copy2(built,temp); os.replace(temp,self.live)
        self.log(f'Verified {len(mapping)} animations. '+('Installed.' if install else f'Built: {built}'))
        return built,report

    def restore(self):
        ensure_closed(); self.baseline()
        if not self.backup.exists(): raise ValueError('There is no saved original for this game folder.')
        temp=self.live.with_name('common_mp.cod4-restore.tmp')
        shutil.copy2(self.backup,temp); os.replace(temp,self.live)
        self.log('Original BO2 animations restored.')

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title('CoD4 animations into BO2 Redacted'); self.geometry('900x660')
        self.mapping={}; self.engine=None
        self.cod4=tk.StringVar(value=r'D:\Call of Duty 4'); self.bo2=tk.StringVar(value=r'D:\Call of Duty Black Ops II')
        body=ttk.Frame(self,padding=16); body.pack(fill='both',expand=True)
        ttk.Label(body,text='CoD4 → BO2 Redacted body animations',font=('Segoe UI',17,'bold')).pack(anchor='w')
        ttk.Label(body,text='Select basic animations, import compiled CoD4 clips, then build and install. Close BO2 first.').pack(anchor='w',pady=(4,12))
        for label,var in [('CoD4 folder',self.cod4),('BO2 folder',self.bo2)]:
            row=ttk.Frame(body); row.pack(fill='x',pady=3)
            ttk.Label(row,text=label,width=14).pack(side='left')
            ttk.Entry(row,textvariable=var).pack(side='left',fill='x',expand=True)
            ttk.Button(row,text='Browse',command=lambda v=var:self.browse(v)).pack(side='left',padx=4)
        buttons=ttk.Frame(body); buttons.pack(fill='x',pady=10)
        self.buttons=[]
        for title,cmd in [('Scan / load basics',self.scan),('Import clip',self.import_clip),('Remove selected',self.remove),('Build & install',self.install),('Restore BO2',self.restore)]:
            b=ttk.Button(buttons,text=title,command=cmd); b.pack(side='left',padx=(0,6)); self.buttons.append(b)
        self.tree=ttk.Treeview(body,columns=('target','source'),show='headings',height=15)
        self.tree.heading('target',text='BO2 animation to replace'); self.tree.heading('source',text='CoD4 animation')
        self.tree.column('target',width=350); self.tree.column('source',width=440)
        self.tree.pack(fill='both',expand=True)
        self.status=tk.StringVar(value='Ready.'); ttk.Label(body,textvariable=self.status).pack(anchor='w',pady=8)
        self.logbox=tk.Text(body,height=6,wrap='word',state='disabled'); self.logbox.pack(fill='x')
        ttk.Label(body,text='Multiplayer third-person animations. Imported clips must be compiled XAnim v17; GIF/SEAnim files are unsupported.').pack(anchor='w',pady=(8,0))

    def browse(self,var):
        folder=filedialog.askdirectory(initialdir=var.get())
        if folder: var.set(folder)
    def log(self,text):
        short=text[-1600:]
        self.after(0,lambda:self.append_log(short))
    def append_log(self,text):
        self.logbox.configure(state='normal'); self.logbox.insert('end',text+'\n'); self.logbox.see('end'); self.logbox.configure(state='disabled')
    def job(self,fn,done=None):
        for b in self.buttons: b.configure(state='disabled')
        self.status.set('Working…')
        def worker():
            try:
                result=fn()
                self.after(0,lambda:self.finish(done,result))
            except Exception as error:
                message=str(error)
                self.after(0,lambda:self.fail(message))
        threading.Thread(target=worker,daemon=True).start()
    def finish(self,done,result):
        for b in self.buttons:b.configure(state='normal')
        if done:done(result)
        self.status.set(f'{len(self.mapping)} animations selected. Ready.')
    def fail(self,message):
        for b in self.buttons:b.configure(state='normal')
        self.status.set('Stopped. See error.'); messagebox.showerror('Could not finish',message)
    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for target,source in sorted(self.mapping.items()):self.tree.insert('', 'end',iid=target,values=(target,source))
    def scan(self):
        self.engine=Engine(self.cod4.get(),self.bo2.get(),self.log)
        def done(mapping):self.mapping=mapping; self.refresh()
        self.job(self.engine.scan,done)
    def import_clip(self):
        if not self.engine or not hasattr(self.engine,'targets'):messagebox.showinfo('Scan first','Use Scan / load basics first.');return
        path=filedialog.askopenfilename(title='Select compiled CoD4 XAnim',filetypes=[('Compiled XAnim','*')])
        if not path:return
        try: header(path)
        except Exception as e:messagebox.showerror('Unsupported file',str(e));return
        dialog=tk.Toplevel(self); dialog.title('Choose BO2 animation to replace'); dialog.geometry('520x160')
        ttk.Label(dialog,text='BO2 target animation').pack(anchor='w',padx=15,pady=10)
        target=tk.StringVar(value=Path(path).name if Path(path).name in self.engine.targets else '')
        combo=ttk.Combobox(dialog,textvariable=target,values=[n for n in self.engine.targets if n.startswith('pb_')],width=65)
        combo.pack(padx=15)
        def add():
            if target.get() not in self.engine.targets:messagebox.showerror('Choose a target','Select an existing BO2 animation.');return
            self.mapping[target.get()]=path;self.refresh();dialog.destroy()
        ttk.Button(dialog,text='Add replacement',command=add).pack(pady=15)
    def remove(self):
        for target in self.tree.selection():self.mapping.pop(target,None)
        self.refresh()
    def install(self):
        if not self.engine:messagebox.showinfo('Scan first','Use Scan / load basics first.');return
        mapping=dict(self.mapping)
        self.job(lambda:self.engine.build(mapping,install=True),lambda result:messagebox.showinfo('Installed',f'{result[1]["count"]} animations verified and installed. Start BO2 normally.'))
    def restore(self):
        engine=Engine(self.cod4.get(),self.bo2.get(),self.log)
        self.job(engine.restore)

if __name__=='__main__':App().mainloop()
