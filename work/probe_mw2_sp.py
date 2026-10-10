import struct,re
from pathlib import Path
d=Path('work/mw2_sp_zone.bin').read_bytes()
for stride in (4,8):
    size=88 if stride==4 else 136
    off=17 if stride==4 else 21
    fpsat=40 if stride==4 else 48
    found=[]
    for m in re.finditer(re.escape(b'\xff'*stride),d):
        p=m.start()
        if p+size+128>len(d):continue
        b=d[p+off:p+off+10];fps=struct.unpack_from('<f',d,p+fpsat)[0]
        if not 20<=b[9]<=200 or sum(b[:5])!=b[9] or sum(b[5:9])!=b[9] or not 1<=fps<=240:continue
        name=d[p+size:p+size+128].split(b'\0')[0]
        if not re.fullmatch(rb'[a-zA-Z0-9_.]+',name):continue
        found.append((p,name.decode(),b.hex(),fps))
    print(stride,len(found),found[:12])
print('header',struct.unpack_from('<18I',d))
print('table',d[72:120].hex(),'text',d[72+524*8:72+524*8+160])
