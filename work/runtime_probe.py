import ctypes,struct,sys,json
from ctypes import wintypes
from pathlib import Path
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]; k.OpenProcess.restype=wintypes.HANDLE
k.ReadProcessMemory.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)];k.ReadProcessMemory.restype=wintypes.BOOL
h=k.OpenProcess(0x410,False,int(sys.argv[1]))
def read(addr,n):
    b=ctypes.create_string_buffer(n);got=ctypes.c_size_t()
    if not k.ReadProcessMemory(h,addr,b,n,ctypes.byref(got)): raise OSError(ctypes.get_last_error(),hex(addr))
    return b.raw[:got.value]
def u32(addr):return struct.unpack('<I',read(addr,4))[0]
code=read(0x401000,0x800000)
sig=bytes.fromhex('56 51 FF D2 8B F0 83 C4 04 85 F6')
hits=[];start=0
while True:
    hit=code.find(sig,start)
    if hit<0:break
    hits.append(0x401000+hit);start=hit+1
for hit in hits:
    pools=u32(hit-11);sizes=u32(hit+59)
    try:
        anim=u32(pools+16); count=u32(sizes+16); model=u32(pools+20)
        name=read(u32(model+4),100).split(b'\0')[0]
        print('candidate',hex(hit),hex(pools),hex(sizes),hex(anim),count,name)
        if name!=b'defaultvehicle':continue
        string_sig=bytes.fromhex('33 C9 66 89 0C 10 83 C0 02 83 F8 20')
        string_hit=0x401000+code.find(string_sig)
        strings=u32(string_hit-46)
        print('STRINGS',hex(strings),read(strings+52,40))
        pool=read(anim+4,104*count)
        found={}
        for i in range(count):
            data=pool[i*104:(i+1)*104];ptr=struct.unpack('<I',data[:4])[0]
            if not ptr or anim<=ptr<=anim+104*count:continue
            try:n=read(ptr,128).split(b'\0')[0].decode()
            except Exception:continue
            if not n.startswith('pb_'):continue
            found[n]={'addr':anim+4+i*104,'data':data.hex(),'frames':struct.unpack_from('<H',data,14)[0],'bones':data[33]}
        Path('work/runtime_assets.json').write_text(json.dumps({'pools':pools,'sizes':sizes,'strings':strings,'animations':found},indent=2))
        print('body animations',len(found))
        print({n:x for n,x in found.items() if n in ('pb_combatrun_forward_loop','pb_stand_death_nervedeath')})
    except Exception as e:print(type(e).__name__,e)
print('signature hits',len(hits))
