"""Session log on disk, for helping users with problems (GPL-3.0-or-later).

Everything the Debug log shows, status changes, and unexpected errors (with tracebacks) are written
with timestamps to logs/bo2sp.log next to the tool. Starting a new session keeps the previous
one as bo2sp.old.log, so the run that went wrong survives a restart. A session stops writing at
MAX_BYTES so the file can't grow without bound. support_text() is what "Copy log for support" puts
on the clipboard: a header describing the setup plus the recent lines, with the Windows user folder
replaced by %USERPROFILE% so usernames aren't shared.
"""
import os,platform,re,sys,threading,time,traceback
from pathlib import Path

MAX_BYTES=4*1024*1024
CURRENT=None # The session's log, for the crash hooks.
SUPPORT_LINES=400

class LogFile:
    def __init__(self,root):
        self.folder=Path(root)/'logs';self.path=self.folder/'bo2sp.log';self.old=self.folder/'bo2sp.old.log'
        self.lock=threading.Lock();self.file=None;self.written=0;self.full=False;self.header_lines=[]
        try:
            self.folder.mkdir(exist_ok=True)
            if self.path.exists():os.replace(self.path,self.old)
            self.file=open(self.path,'w',encoding='utf-8',newline='\n',buffering=1) # Line-buffered: a crash loses nothing.
        except OSError:self.file=None # Read-only folder etc.: the tool still works, just without a log file.
        global CURRENT;CURRENT=self
    def write(self,text,kind=''):
        stamp=time.strftime('%Y-%m-%d %H:%M:%S')+f'.{int(time.time()*1000)%1000:03d}'
        lines=[f'{stamp} {kind+": " if kind else ""}{line}' for line in str(text).splitlines() or ['']]
        with self.lock:
            if not self.file or self.full:return
            for line in lines:
                self.file.write(line+'\n');self.written+=len(line)+1
            if self.written>MAX_BYTES:
                self.file.write(f'{stamp} log: size limit reached; nothing more is written this session\n');self.full=True
    def header(self,info):
        """Describe the setup once per session (tool version, Windows, game folder, library)."""
        self.header_lines=[f'{key}: {value}' for key,value in info.items()]
        self.write('\n'.join(['BO2SP session started']+self.header_lines))
    def exception(self,kind,error,trace,where=''):
        self.write(''.join(traceback.format_exception(kind,error,trace)).rstrip(),'error'+(f' in {where}' if where else ''))
    def support_text(self):
        """Header plus the most recent lines of this session's log, ready to paste; usernames hidden."""
        try:recent=self.path.read_text(encoding='utf-8',errors='replace').splitlines()[-SUPPORT_LINES:]
        except OSError:recent=['(no log file)']
        return redact('\n'.join(['BO2SP support log','']+self.header_lines+['','Recent log:']+recent))
    def close(self):
        with self.lock:
            if self.file:self.file.close();self.file=None

def redact(text):
    home=os.path.expanduser('~')
    if home and home!='~':text=re.sub(re.escape(home),'%USERPROFILE%',text,flags=re.I)
    return re.sub(r'(?i)([A-Z]:\\Users\\)[^\\/\s]+',r'\1<user>',text) # Other users' folders too.

def setup_info(root,bo2,clips,mapped):
    exe=Path(sys.executable)
    if getattr(sys,'frozen',False):
        import hashlib
        try:version='EXE '+hashlib.sha256(exe.read_bytes()).hexdigest()[:8]
        except OSError:version='EXE (unreadable)'
    else:version='source'
    folder=Path(bo2) if bo2 else None
    game=('t6mpv43.exe' if (folder/'t6mpv43.exe').is_file() else 't6mp.exe' if (folder/'t6mp.exe').is_file() else 'no BO2 exe') if folder else 'not set'
    build=sys.getwindowsversion().build if hasattr(sys,'getwindowsversion') else 0
    windows=f'Windows {11 if build>=22000 else 10} build {build}' if build else platform.platform() # platform says 10 for 11.
    return {'version':version,'windows':windows,'python':platform.python_version(),'tool folder':str(root),
            'bo2 folder':f'{bo2 or "not set"} ({game})','library clips':clips,'replacements':mapped}

def install_crash_hooks():
    """Unexpected errors anywhere (Qt slots, worker threads) go to the session log as well as stderr."""
    def main_hook(kind,error,trace):
        if CURRENT:CURRENT.exception(kind,error,trace)
        if sys.stderr:sys.__excepthook__(kind,error,trace) # The windowed EXE has no stderr.
    def thread_hook(args):
        if CURRENT and args.exc_type is not SystemExit:CURRENT.exception(args.exc_type,args.exc_value,args.exc_traceback,args.thread.name if args.thread else '')
        if sys.stderr:threading.__excepthook__(args)
    sys.excepthook=main_hook;threading.excepthook=thread_hook
