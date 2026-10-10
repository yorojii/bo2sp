"""Replay key events for the foreground BO2 process (GPL-3.0-or-later).

The callback considers only the configured function/numpad key, queues a
press, and passes every event through. No text or other keys are recorded.
Game memory and Tk widgets are handled by their existing worker threads.
"""
import ctypes,queue,threading
from ctypes import wintypes

KEYS={**{f'F{i}':0x6f+i for i in range(1,13)},**{f'Num {i}':0x60+i for i in range(10)}}
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
kernel.GetCurrentThreadId.argtypes=[];kernel.GetCurrentThreadId.restype=wintypes.DWORD
kernel.GetModuleHandleW.argtypes=[wintypes.LPCWSTR];kernel.GetModuleHandleW.restype=wintypes.HMODULE

def foreground_pid():
    pid=wintypes.DWORD();window=u.GetForegroundWindow()
    if window:u.GetWindowThreadProcessId(window,ctypes.byref(pid))
    return pid.value

class ReplayHotkey:
    def __init__(self):
        self.events=queue.SimpleQueue();self.config=(KEYS['F6'],0,False)
        self.down=False;self.seen_config=None;self.thread_id=0;self.hook=None;self.error=None
        self.ready=threading.Event();self.stopped=threading.Event();self.callback=HOOKPROC(self._callback)
        self.thread=threading.Thread(target=self._run,name='Yoroji replay key');self.thread.start()
    def configure(self,key,pid,enabled):
        self.config=(KEYS[key],int(pid or 0),bool(enabled))
    def _key_event(self,vk,message,pid):
        config=self.config
        if config!=self.seen_config:self.down=False;self.seen_config=config
        key,game_pid,enabled=config
        if vk!=key:return
        if message in (0x101,0x105):self.down=False
        elif message in (0x100,0x104):
            first=not self.down;self.down=True
            if first and enabled and game_pid and pid==game_pid:self.events.put(game_pid)
    def _callback(self,code,message,data):
        try:
            if code>=0 and data:
                vk=ctypes.cast(data,ctypes.POINTER(KeyboardEvent)).contents.vk
                if vk==self.config[0]:self._key_event(vk,message,foreground_pid())
        except Exception:pass
        return u.CallNextHookEx(None,code,message,data)
    def _run(self):
        try:
            self.thread_id=kernel.GetCurrentThreadId();msg=wintypes.MSG()
            u.PeekMessageW(ctypes.byref(msg),None,0,0,0) # Create this thread's message queue.
            self.hook=u.SetWindowsHookExW(13,self.callback,kernel.GetModuleHandleW(None),0)
            if not self.hook:raise OSError(ctypes.get_last_error(),'Cannot listen for the replay key')
            self.ready.set()
            while not self.stopped.is_set():
                result=u.GetMessageW(ctypes.byref(msg),None,0,0)
                if result==0:break
                if result==-1:raise OSError(ctypes.get_last_error(),'Replay key message loop stopped')
        except Exception as e:self.error=str(e)
        finally:
            if self.hook:u.UnhookWindowsHookEx(self.hook);self.hook=None
            self.ready.set()
    def stop(self):
        self.stopped.set()
        if self.thread_id:u.PostThreadMessageW(self.thread_id,0x12,0,0)
    def is_alive(self):return self.thread.is_alive()
