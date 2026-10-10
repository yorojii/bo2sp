import sys,ctypes,json
from ctypes import wintypes
sys.path.insert(0,'work/porter')
from runtime import Session,k
class MBI(ctypes.Structure):
    _fields_=[('base',ctypes.c_void_p),('allocation',ctypes.c_void_p),('allocprotect',wintypes.DWORD),('partition',wintypes.WORD),('size',ctypes.c_size_t),('state',wintypes.DWORD),('protect',wintypes.DWORD),('kind',wintypes.DWORD)]
k.VirtualQueryEx.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.POINTER(MBI),ctypes.c_size_t];k.VirtualQueryEx.restype=ctypes.c_size_t
s=Session(int(sys.argv[1]),read_only=True);regions=[];address=0;totals={}
while address<0x100000000:
    row=MBI()
    if not k.VirtualQueryEx(s.handle,address,ctypes.byref(row),ctypes.sizeof(row)):break
    start=row.base or 0;end=min(start+row.size,0x100000000)
    if end<=address:break
    totals[hex(row.state)]=totals.get(hex(row.state),0)+end-start
    if row.state==0x10000:regions.append({'base':hex(start),'size':end-start})
    address=end
s.close();print(json.dumps({'query_size':ctypes.sizeof(MBI),'totals':totals,'largest_free':sorted(regions,key=lambda x:x['size'],reverse=True)[:12],'free_regions':len(regions)}))
