import sys,struct,ctypes,re,json,time
from pathlib import Path
from ctypes import wintypes
sys.path.insert(0,'work/porter')
from runtime import Session,k
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
s=Session(int(sys.argv[1]));objid=struct.unpack('<H',s.read(0x262d1c0,2))[0];tree=s.u32(0x25ef1b8+objid*124)
class MBI(ctypes.Structure):
    _fields_=[('BaseAddress',ctypes.c_void_p),('AllocationBase',ctypes.c_void_p),('AllocationProtect',wintypes.DWORD),('RegionSize',ctypes.c_size_t),('State',wintypes.DWORD),('Protect',wintypes.DWORD),('Type',wintypes.DWORD)]
k.VirtualQueryEx.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.POINTER(MBI),ctypes.c_size_t];k.VirtualQueryEx.restype=ctypes.c_size_t
keys={'tree':tree,'stand_alert':s.assets['pb_stand_alert'][0],'rifle_idle':s.assets.get('pb_stand_rifle_idle',s.assets['pb_stand_alert'])[0]}
needle=re.compile(b'|'.join(re.escape(struct.pack('<I',x)) for x in keys.values()))
address=0x10000;total=0;hits=[];start=time.monotonic()
while address<0x7fff0000:
    m=MBI()
    if not k.VirtualQueryEx(s.handle,address,ctypes.byref(m),ctypes.sizeof(m)):break
    base=m.BaseAddress or address;size=m.RegionSize;address=base+size
    if m.State!=0x1000 or m.Protect&0x101 or (m.Protect&255) not in (2,4,8,16,32,64,128):continue
    # Static runtime pools and ordinary heaps; skip the large texture assets.
    if size>64*1024*1024:continue
    try:data=s.read(base,size)
    except (OSError,ValueError):continue
    total+=size
    for match in needle.finditer(data):
        if match.start()%4:continue
        value=struct.unpack('<I',match.group())[0];kind=next(k for k,v in keys.items() if v==value);at=base+match.start()
        if kind=='tree' or 0xd00000<at<0x5000000:
            context=data[max(0,match.start()-32):match.start()+100]
            hits.append({'kind':kind,'address':hex(at),'context':context.hex()})
print('tree',hex(tree),'scanned MB',round(total/1024**2),'seconds',round(time.monotonic()-start,2),'hits',len(hits));print(json.dumps(hits,indent=2));Path('work/research/info_hits.json').write_text(json.dumps(hits));s.close()
