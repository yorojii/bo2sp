"""Local test helper using the command entry point of the installed BO2 Console V4.
Not part of the animation importer deliverable.
"""
import importlib.util,ctypes,struct,sys
from ctypes import wintypes
s=importlib.util.spec_from_file_location('runtime','work/porter/runtime.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
k=m.k
k.CreateRemoteThread.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)];k.CreateRemoteThread.restype=wintypes.HANDLE
k.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];k.WaitForSingleObject.restype=wintypes.DWORD
pid=int(sys.argv[1]);p=m.Session(pid)
print('command entry',p.read(0x5c6f10,16).hex(),'console guard',p.read(0x8c923a,2).hex())
h=k.OpenProcess(0x43a,False,pid)
command=(' '.join(sys.argv[2:])+'\n\0').encode('ascii')
textptr=k.VirtualAllocEx(h,None,len(command),0x3000,0x04)
p.write(textptr,command)
code=bytes.fromhex('55 8b ec 68')+struct.pack('<I',textptr)+bytes.fromhex('6a 00 b8')+struct.pack('<I',0x5c6f10)+bytes.fromhex('ff d0 83 c4 08 8b e5 5d 33 c0 c2 04 00')
codeptr=k.VirtualAllocEx(h,None,len(code),0x3000,0x40)
p.write(codeptr,code)
tid=wintypes.DWORD();thread=k.CreateRemoteThread(h,None,0,codeptr,None,0,ctypes.byref(tid))
if not thread:raise OSError(ctypes.get_last_error(),'Cannot invoke the local game command API')
wait=k.WaitForSingleObject(thread,5000)
print('command completion',wait,'thread',tid.value)
if wait==0:
    k.VirtualFreeEx(h,textptr,0,0x8000);k.VirtualFreeEx(h,codeptr,0,0x8000)
k.CloseHandle(thread);k.CloseHandle(h);p.close()
