"""Movement speed slider for the attached BO2 process (GPL-3.0-or-later).

Scales g_speed (walk/run speed, also the base for sprinting) as a percentage of the game's own
value. Not timescale: the game clock, animations and everything else run at normal speed. Only
that dvar value is written; the game's value is read on attach and written back when the slider
returns to 100% or the tool closes. It's a server dvar, so it takes effect in matches you host.

Sprint (player_sprintSpeedScale) and jump (jump_height) were tried and dropped on 2026-10-11:
those are synced bg dvars the movement code doesn't pick up from a memory write, and BO2 MP
ignores jump_height even when set from the console.
"""
import ctypes,struct,time
from freelook import kernel,DVAR_POOL,DVAR_COUNT,DVAR_SIZE,DVAR_FLOAT

DVAR_INT=6
# key, dvar, type, (lowest, highest) percent.
SETTINGS=(('speed','g_speed',DVAR_INT,(10,300)),)
LIMITS={key:limits for key,name,kind,limits in SETTINGS}
def clamp_percent(key,value):
    low,high=LIMITS[key]
    try:return int(min(max(round(float(value)),low),high))
    except (TypeError,ValueError):return 100

class MovementDvars:
    """Finds the movement dvars in one BO2 process and reads/writes their current values."""
    def __init__(self,pid):
        self.pid=pid;self.handle=kernel.OpenProcess(0x438,False,pid) # query, VM read/write/operation.
        if not self.handle:raise OSError(ctypes.get_last_error(),'Cannot open BO2 process')
        try:self.address=self.find_all()
        except Exception:self.close();raise
    def read(self,addr,size):
        buf=ctypes.create_string_buffer(size);got=ctypes.c_size_t()
        if not kernel.ReadProcessMemory(self.handle,addr,buf,size,ctypes.byref(got)) or got.value!=size:
            raise OSError(ctypes.get_last_error(),f'Cannot read BO2 data at {addr:#x}')
        return buf.raw
    def find_all(self):
        count=struct.unpack('<I',self.read(DVAR_COUNT,4))[0]
        if not 0<count<=8192:raise RuntimeError('Unsupported BO2 dvar table')
        table=self.read(DVAR_POOL,count*DVAR_SIZE);wanted={name:kind for key,name,kind,limits in SETTINGS};found={}
        for i in range(count):
            pointer,kind=struct.unpack_from('<I12xI',table,i*DVAR_SIZE)
            if not pointer or kind not in (DVAR_INT,DVAR_FLOAT):continue
            name=self.read(pointer,40).split(b'\0')[0].decode('latin1')
            if wanted.get(name)==kind:found[name]=DVAR_POOL+i*DVAR_SIZE
        missing=[name for name in wanted if name not in found]
        if missing:raise RuntimeError(', '.join(missing)+' not found in this BO2 build')
        return {key:found[name] for key,name,kind,limits in SETTINGS}
    def get(self,key):
        kind=dict((k,t) for k,n,t,l in SETTINGS)[key];raw=self.read(self.address[key]+0x18,4)
        return struct.unpack('<i' if kind==DVAR_INT else '<f',raw)[0]
    def set(self,key,value):
        kind=dict((k,t) for k,n,t,l in SETTINGS)[key];addr=self.address[key]
        fmt='<ii' if kind==DVAR_INT else '<ff';low,high=struct.unpack(fmt,self.read(addr+0x48,8)) # The dvar's own allowed range.
        value=min(max(value,low),high);data=struct.pack('<i' if kind==DVAR_INT else '<f',int(round(value)) if kind==DVAR_INT else float(value))
        got=ctypes.c_size_t()
        if not kernel.WriteProcessMemory(self.handle,addr+0x18,data,4,ctypes.byref(got)) or got.value!=4:
            raise OSError(ctypes.get_last_error(),'Cannot update BO2 movement')
    def close(self):
        if self.handle:kernel.CloseHandle(self.handle);self.handle=None

class Movement:
    """Keeps the attached game's movement dvars at the chosen percentages. update() is called from the UI tick;
    it rewrites a value only when the game's differs (e.g. a gametype reset it), at most every half second."""
    def __init__(self):self.dvars=None;self.original=None;self.checked=0.0;self.error=None;self.failed_pid=0
    def update(self,pid,percent):
        custom=any(percent[key]!=100 for key in LIMITS)
        if self.dvars and self.dvars.pid!=pid:self.restore(quiet=True) # Game closed or another one attached.
        if not pid or pid==self.failed_pid:return # Don't retry a game that failed; report once.
        if not custom and not self.original:return # Nothing to do: never touch the game at 100%.
        now=time.monotonic()
        if now-self.checked<0.5:return
        self.checked=now
        try:
            if not self.dvars:self.dvars=MovementDvars(pid);self.original={key:self.dvars.get(key) for key in LIMITS}
            if not custom:self.restore();return
            for key in LIMITS:
                wanted=self.original[key]*percent[key]/100
                if abs(self.dvars.get(key)-wanted)>1e-3:self.dvars.set(key,wanted)
        except (OSError,RuntimeError) as e:self.error=str(e);self.failed_pid=pid;self.detach()
    def restore(self,quiet=False):
        """Put the game's own values back and let go of the process (quiet: it may already have exited)."""
        if self.dvars and self.original:
            try:
                for key,value in self.original.items():self.dvars.set(key,value)
            except OSError as e:
                if not quiet:self.error=str(e)
        self.detach()
    def detach(self):
        if self.dvars:self.dvars.close()
        self.dvars=None;self.original=None
