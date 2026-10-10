"""Hotkeys for the foreground BO2 process (GPL-3.0-or-later).

The callback looks only at keys bound to an action, or at the next key while a
new binding is being captured. It queues one event per press and passes every
event through. No text or other keys are recorded. Game memory and Tk widgets
are handled by their existing worker threads.
"""
import ctypes,queue,threading
from ctypes import wintypes

# Key names used by profiles saved before any-key binding existed.
KEYS={**{f'F{i}':0x6f+i for i in range(1,13)},**{f'Num {i}':0x60+i for i in range(10)}}
ESCAPE=0x1B
u=ctypes.WinDLL('user32',use_last_error=True)
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
LRESULT=ctypes.c_ssize_t
HOOKPROC=ctypes.WINFUNCTYPE(LRESULT,ctypes.c_int,wintypes.WPARAM,wintypes.LPARAM)
class KeyboardEvent(ctypes.Structure):
    _fields_=[('vk',wintypes.DWORD),('scan',wintypes.DWORD),('flags',wintypes.DWORD),('time',wintypes.DWORD),('extra',ctypes.c_size_t)]
u.SetWindowsHookExW.argtypes=[ctypes.c_int,HOOKPROC,wintypes.HINSTANCE,wintypes.DWORD];u.SetWindowsHookExW.restype=wintypes.HANDLE
u.UnhookWindowsHookEx.argtypes=[wintypes.HANDLE];u.UnhookWindowsHookEx.restype=wintypes.BOOL
u.CallNextHookEx.argtypes=[wintypes.HANDLE,ctypes.c_int,wintypes.WPARAM,wintypes.LPARAM];u.CallNextHookEx.restype=LRESULT
u.GetForegroundWindow.argtypes=[];u.GetForegroundWindow.restype=wintypes.HWND
u.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)];u.GetWindowThreadProcessId.restype=wintypes.DWORD
u.GetMessageW.argtypes=[ctypes.POINTER(wintypes.MSG),wintypes.HWND,wintypes.UINT,wintypes.UINT];u.GetMessageW.restype=wintypes.BOOL
u.PeekMessageW.argtypes=[ctypes.POINTER(wintypes.MSG),wintypes.HWND,wintypes.UINT,wintypes.UINT,wintypes.UINT];u.PeekMessageW.restype=wintypes.BOOL
u.PostThreadMessageW.argtypes=[wintypes.DWORD,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM];u.PostThreadMessageW.restype=wintypes.BOOL
u.MapVirtualKeyW.argtypes=[wintypes.UINT,wintypes.UINT];u.MapVirtualKeyW.restype=wintypes.UINT
u.GetKeyNameTextW.argtypes=[wintypes.LONG,wintypes.LPWSTR,ctypes.c_int];u.GetKeyNameTextW.restype=ctypes.c_int
kernel.GetCurrentThreadId.argtypes=[];kernel.GetCurrentThreadId.restype=wintypes.DWORD
kernel.GetModuleHandleW.argtypes=[wintypes.LPCWSTR];kernel.GetModuleHandleW.restype=wintypes.HMODULE

# Keys BO2 binds by default; binding one still lets the game receive it.
GAME_KEYS={0x57,0x41,0x53,0x44,0x20,0x43,0x46,0x52,0x47,0x51,0x45,0x54,0x59,0x09,0x31,0x32,0x33,0x34,0x35,0x10,0x11,0xA0,0xA1,0xA2,0xA3}
EXTENDED={0x21,0x22,0x23,0x24,0x25,0x26,0x27,0x28,0x2D,0x2E,0x6F,0x90,0xA3,0xA5,0x5B,0x5C,0x5D}

def key_name(vk,scan=0,extended=None):
    """Readable keyboard-layout name for a virtual key, e.g. 'F6', 'Right Alt'."""
    vk=int(vk)
    if extended is None:extended=vk in EXTENDED
    scan=scan or u.MapVirtualKeyW(vk,0)
    buffer=ctypes.create_unicode_buffer(64)
    if scan and u.GetKeyNameTextW((scan<<16)|(1<<24 if extended else 0),buffer,64):return buffer.value.title() if len(buffer.value)>1 else buffer.value.upper()
    return f'Key 0x{vk:02X}'

def foreground_pid():
    pid=wintypes.DWORD();window=u.GetForegroundWindow()
    if window:u.GetWindowThreadProcessId(window,ctypes.byref(pid))
    return pid.value

class HotkeyListener:
    """Low-level keyboard hook delivering ('press',action,pid), ('capture',vk,name) and ('cancel',) events."""
    def __init__(self):
        self.events=queue.SimpleQueue();self.config=({},0)
        self.down=set();self.capturing=False;self.thread_id=0;self.hook=None;self.error=None
        self.ready=threading.Event();self.stopped=threading.Event();self.callback=HOOKPROC(self._callback)
        self.thread=threading.Thread(target=self._run,name='Hotkey listener');self.thread.start()
    def configure(self,bindings,pid):
        """bindings: {virtual key: action}. Presses fire only while process pid is in the foreground."""
        self.config=(dict(bindings),int(pid or 0))
    def capture(self):self.capturing=True
    def cancel_capture(self):self.capturing=False
    def _key_event(self,vk,scan,flags,message,pid):
        if message in (0x101,0x105):self.down.discard(vk);return
        if message not in (0x100,0x104) or vk in self.down:return
        self.down.add(vk)
        if self.capturing:
            self.capturing=False
            self.events.put(('cancel',) if vk==ESCAPE else ('capture',vk,key_name(vk,scan,bool(flags&1))));return
        bindings,game_pid=self.config;action=bindings.get(vk)
        if action and game_pid and pid==game_pid:self.events.put(('press',action,game_pid))
    def _callback(self,code,message,data):
        try:
            if code>=0 and data:
                event=ctypes.cast(data,ctypes.POINTER(KeyboardEvent)).contents;vk=event.vk
                if self.capturing or vk in self.config[0] or vk in self.down:
                    self._key_event(vk,event.scan,event.flags,message,foreground_pid())
        except Exception:pass
        return u.CallNextHookEx(None,code,message,data)
    def _run(self):
        try:
            self.thread_id=kernel.GetCurrentThreadId();msg=wintypes.MSG()
            u.PeekMessageW(ctypes.byref(msg),None,0,0,0) # Create this thread's message queue.
            self.hook=u.SetWindowsHookExW(13,self.callback,kernel.GetModuleHandleW(None),0)
            if not self.hook:raise OSError(ctypes.get_last_error(),'Cannot listen for hotkeys')
            self.ready.set()
            while not self.stopped.is_set():
                result=u.GetMessageW(ctypes.byref(msg),None,0,0)
                if result==0:break
                if result==-1:raise OSError(ctypes.get_last_error(),'Hotkey message loop stopped')
        except Exception as e:self.error=str(e)
        finally:
            if self.hook:u.UnhookWindowsHookEx(self.hook);self.hook=None
            self.ready.set()
    def stop(self):
        self.stopped.set()
        if self.thread_id:u.PostThreadMessageW(self.thread_id,0x12,0,0)
    def is_alive(self):return self.thread.is_alive()
