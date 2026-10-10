"""Third-person freelook for the foreground BO2 process (GPL-3.0-or-later).

While the freelook key is held with BO2 in the foreground, mouse movement
orbits the third-person camera (cg_thirdPersonAngle) instead of turning the
character, and the mouse wheel changes camera distance (cg_thirdPersonRange).
Releasing the key restores both values. Only those two dvar floats are ever
written. Mouse events outside freelook, and mouse buttons, pass through.

While BO2 is in the foreground the freelook key itself is swallowed, so the
game never sees it held. With Alt that stops Windows treating other keys as
Alt+key menu shortcuts (the error beep). Pressing Tab, F4 or Enter during
freelook hands Alt back to Windows so Alt+Tab, Alt+F4 and Alt+Enter still work.
"""
import ctypes,struct,threading,time
from ctypes import wintypes
from replay_hotkey import foreground_pid

u=ctypes.WinDLL('user32',use_last_error=True)
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
LRESULT=ctypes.c_ssize_t
HOOKPROC=ctypes.WINFUNCTYPE(LRESULT,ctypes.c_int,wintypes.WPARAM,wintypes.LPARAM)
class KeyboardEvent(ctypes.Structure):
    _fields_=[('vk',wintypes.DWORD),('scan',wintypes.DWORD),('flags',wintypes.DWORD),('time',wintypes.DWORD),('extra',ctypes.c_size_t)]
class KeyInput(ctypes.Structure):
    _fields_=[('vk',wintypes.WORD),('scan',wintypes.WORD),('flags',wintypes.DWORD),('time',wintypes.DWORD),('extra',ctypes.c_size_t)]
class Input(ctypes.Structure):
    class Union(ctypes.Union):_fields_=[('ki',KeyInput),('padding',ctypes.c_byte*32)]
    _anonymous_=('u',);_fields_=[('type',wintypes.DWORD),('u',Union)]
class MouseEvent(ctypes.Structure):
    _fields_=[('pt',wintypes.POINT),('data',wintypes.DWORD),('flags',wintypes.DWORD),('time',wintypes.DWORD),('extra',ctypes.c_size_t)]
u.SetWindowsHookExW.argtypes=[ctypes.c_int,HOOKPROC,wintypes.HINSTANCE,wintypes.DWORD];u.SetWindowsHookExW.restype=wintypes.HANDLE
u.UnhookWindowsHookEx.argtypes=[wintypes.HANDLE];u.UnhookWindowsHookEx.restype=wintypes.BOOL
u.CallNextHookEx.argtypes=[wintypes.HANDLE,ctypes.c_int,wintypes.WPARAM,wintypes.LPARAM];u.CallNextHookEx.restype=LRESULT
u.GetMessageW.argtypes=[ctypes.POINTER(wintypes.MSG),wintypes.HWND,wintypes.UINT,wintypes.UINT];u.GetMessageW.restype=wintypes.BOOL
u.PeekMessageW.argtypes=[ctypes.POINTER(wintypes.MSG),wintypes.HWND,wintypes.UINT,wintypes.UINT,wintypes.UINT];u.PeekMessageW.restype=wintypes.BOOL
u.PostThreadMessageW.argtypes=[wintypes.DWORD,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM];u.PostThreadMessageW.restype=wintypes.BOOL
u.GetCursorPos.argtypes=[ctypes.POINTER(wintypes.POINT)];u.GetCursorPos.restype=wintypes.BOOL
u.SendInput.argtypes=[wintypes.UINT,ctypes.POINTER(Input),ctypes.c_int];u.SendInput.restype=wintypes.UINT
kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
kernel.ReadProcessMemory.argtypes=[wintypes.HANDLE,wintypes.LPCVOID,wintypes.LPVOID,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)];kernel.ReadProcessMemory.restype=wintypes.BOOL
kernel.WriteProcessMemory.argtypes=[wintypes.HANDLE,wintypes.LPVOID,wintypes.LPCVOID,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)];kernel.WriteProcessMemory.restype=wintypes.BOOL
kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle.restype=wintypes.BOOL
kernel.GetCurrentThreadId.restype=wintypes.DWORD
kernel.GetModuleHandleW.argtypes=[wintypes.LPCWSTR];kernel.GetModuleHandleW.restype=wintypes.HMODULE

# t6mpv43 43.1337.x dvar pool (T6SDK Addresses.h: dvarPool / g_dvarCount); dvar_s is 0x60 bytes,
# name pointer at +0, type at +0x10, current value at +0x18. Dvars are found by name, not address.
DVAR_POOL=0x400000+0x261FC48;DVAR_COUNT=0x400000+0x267FC4C;DVAR_SIZE=0x60;DVAR_FLOAT=2
WM_MOUSEMOVE=0x200;WM_MOUSEWHEEL=0x20A;LLMHF_INJECTED=1;LLKHF_INJECTED=0x10
ALT_KEYS=(0x12,0xA4,0xA5);SYSTEM_COMBO_KEYS=(0x09,0x73,0x0D) # Tab, F4, Enter
def matches(key,vk):return vk in ALT_KEYS if key==0x12 else vk==key

class CameraDvars:
    """Reads and writes the third-person camera dvars of one BO2 process."""
    def __init__(self,pid):
        self.pid=pid;self.handle=kernel.OpenProcess(0x438,False,pid) # query, VM read/write/operation.
        if not self.handle:raise OSError(ctypes.get_last_error(),'Cannot open BO2 process')
        try:
            self.angle=self.find('cg_thirdPersonAngle');self.range=self.find('cg_thirdPersonRange')
            self.limits={addr:struct.unpack('<ff',self.read(addr+0x48,8)) for addr in (self.angle,self.range)}
        except Exception:
            self.close();raise
    def read(self,addr,size):
        buf=ctypes.create_string_buffer(size);got=ctypes.c_size_t()
        if not kernel.ReadProcessMemory(self.handle,addr,buf,size,ctypes.byref(got)) or got.value!=size:
            raise OSError(ctypes.get_last_error(),f'Cannot read BO2 data at {addr:#x}')
        return buf.raw
    def find(self,name):
        count=struct.unpack('<I',self.read(DVAR_COUNT,4))[0]
        if not 0<count<=8192:raise RuntimeError('Unsupported BO2 dvar table')
        table=self.read(DVAR_POOL,count*DVAR_SIZE)
        for i in range(count):
            pointer,typ=struct.unpack_from('<I12xI',table,i*DVAR_SIZE)
            if typ==DVAR_FLOAT and pointer and self.read(pointer,len(name)+1)==name.encode()+b'\0':return DVAR_POOL+i*DVAR_SIZE
        raise RuntimeError(f'{name} was not found in this BO2 build')
    def get(self,addr):return struct.unpack('<f',self.read(addr+0x18,4))[0]
    def set(self,addr,value):
        low,high=self.limits[addr];data=struct.pack('<f',min(max(value,low),high));got=ctypes.c_size_t()
        if not kernel.WriteProcessMemory(self.handle,addr+0x18,data,4,ctypes.byref(got)) or got.value!=4:
            raise OSError(ctypes.get_last_error(),'Cannot update the BO2 camera')
    def close(self):
        if self.handle:kernel.CloseHandle(self.handle);self.handle=None

class Freelook:
    """Mouse hook plus a 100 Hz key poll. configure() sets the key, game pid and on/off at any time."""
    def __init__(self,degrees_per_pixel=0.15,range_step=15.0):
        self.config=(0x12,0,False);self.degrees_per_pixel=degrees_per_pixel;self.range_step=range_step
        self.camera=None;self.active=False;self.saved=None;self.angle=0.0;self.range=0.0;self.held=False;self.handed_back=False
        self.events=[];self.error=None;self.lock=threading.Lock();self.thread_id=0;self.hook=None
        self.stopped=threading.Event();self.ready=threading.Event();self.callback=HOOKPROC(self._callback);self.key_callback=HOOKPROC(self._key_callback);self.key_hook=None
        self.thread=threading.Thread(target=self._run,name='Freelook mouse');self.thread.start()
        self.poller=threading.Thread(target=self._poll,name='Freelook key');self.poller.start()
    def configure(self,vk,pid,enabled):self.config=(int(vk),int(pid or 0),bool(enabled))
    def _note(self,text):
        self.events.append((time.monotonic(),text))
        del self.events[:-50]
    def _begin(self,pid):
        if not self.camera or self.camera.pid!=pid:
            if self.camera:self.camera.close()
            self.camera=CameraDvars(pid)
        self.saved=(self.camera.get(self.camera.angle),self.camera.get(self.camera.range))
        self.angle,self.range=self.saved;self.active=True;self._note(f'freelook on (angle {self.angle:.1f}, range {self.range:.0f})')
    def _end(self):
        self.active=False
        if self.saved and self.camera:
            try:self.camera.set(self.camera.angle,self.saved[0]);self.camera.set(self.camera.range,self.saved[1])
            except OSError as e:self.error=str(e)
        self._note('freelook off, camera restored');self.saved=None
    def _poll(self):
        while not self.stopped.wait(0.01):
            vk,pid,enabled=self.config
            wanted=enabled and pid and self.held and foreground_pid()==pid
            with self.lock:
                try:
                    if wanted and not self.active:self._begin(pid)
                    elif not wanted and self.active:self._end()
                except (OSError,RuntimeError) as e:self.error=str(e);self.active=False
        with self.lock:
            if self.active:self._end()
            if self.camera:self.camera.close();self.camera=None
    def _key_event(self,vk,message,injected,foreground):
        """Returns True when the key event must be hidden from BO2 and Windows."""
        key,pid,enabled=self.config;down=message in (0x100,0x104);up=message in (0x101,0x105)
        if matches(key,vk) and not injected:
            if up:
                swallowed=self.held;self.held=False
                if self.handed_back:self.handed_back=False;return False # Windows got an injected press, so it gets this release.
                return swallowed # Only hide releases whose press was hidden, or Windows sees a stuck key.
            if down and enabled and pid and foreground==pid and not self.handed_back:self.held=True;return True
        elif down and self.held and vk in SYSTEM_COMBO_KEYS and key==0x12:
            self.held=False;self.handed_back=True # The poller ends freelook; Windows now gets Alt plus this key.
            press=Input(type=1);press.ki=KeyInput(vk=0x12);u.SendInput(1,ctypes.byref(press),ctypes.sizeof(Input))
        return False
    def _key_callback(self,code,message,data):
        try:
            if code>=0 and data:
                event=ctypes.cast(data,ctypes.POINTER(KeyboardEvent)).contents;key=self.config[0]
                if matches(key,event.vk) or (self.held and event.vk in SYSTEM_COMBO_KEYS):
                    if self._key_event(event.vk,message,bool(event.flags&LLKHF_INJECTED),foreground_pid()):return 1
        except Exception as e:self.error=str(e)
        return u.CallNextHookEx(None,code,message,data)
    def _callback(self,code,message,data):
        try:
            if code>=0 and data and self.active:
                event=ctypes.cast(data,ctypes.POINTER(MouseEvent)).contents
                if not event.flags&LLMHF_INJECTED and message in (WM_MOUSEMOVE,WM_MOUSEWHEEL):
                    with self.lock:
                        if self.active:
                            if message==WM_MOUSEMOVE:
                                cursor=wintypes.POINT();u.GetCursorPos(ctypes.byref(cursor)) # Blocked moves leave the cursor in place.
                                self.angle=(self.angle-(event.pt.x-cursor.x)*self.degrees_per_pixel)%360
                                self.camera.set(self.camera.angle,self.angle)
                            else:
                                notches=ctypes.c_short(event.data>>16).value/120
                                self.range=min(max(self.range-notches*self.range_step,30.0),1024.0)
                                self.camera.set(self.camera.range,self.range)
                            return 1 # Swallow the event so the character doesn't turn or switch weapons.
        except Exception as e:self.error=str(e)
        return u.CallNextHookEx(None,code,message,data)
    def _run(self):
        try:
            self.thread_id=kernel.GetCurrentThreadId();msg=wintypes.MSG()
            u.PeekMessageW(ctypes.byref(msg),None,0,0,0) # Create this thread's message queue.
            self.hook=u.SetWindowsHookExW(14,self.callback,kernel.GetModuleHandleW(None),0)
            if not self.hook:raise OSError(ctypes.get_last_error(),'Cannot listen for mouse movement')
            self.key_hook=u.SetWindowsHookExW(13,self.key_callback,kernel.GetModuleHandleW(None),0)
            if not self.key_hook:raise OSError(ctypes.get_last_error(),'Cannot listen for the freelook key')
            self.ready.set()
            while not self.stopped.is_set():
                result=u.GetMessageW(ctypes.byref(msg),None,0,0)
                if result==0:break
                if result==-1:raise OSError(ctypes.get_last_error(),'Freelook message loop stopped')
        except Exception as e:self.error=str(e)
        finally:
            if self.hook:u.UnhookWindowsHookEx(self.hook);self.hook=None
            if self.key_hook:u.UnhookWindowsHookEx(self.key_hook);self.key_hook=None
            self.ready.set()
    def stop(self):
        self.stopped.set()
        if self.thread_id:u.PostThreadMessageW(self.thread_id,0x12,0,0)
        self.poller.join(2);self.thread.join(2)
    def is_alive(self):return self.thread.is_alive() or self.poller.is_alive()
