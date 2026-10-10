import sys,struct,json
sys.path.insert(0,'work/porter')
from runtime import Session
s=Session(int(sys.argv[1]));base=0x2b6ee40
lookup={addr:name for name,(addr,data) in s.assets.items()}
objid=struct.unpack('<H',s.read(0x262d1c0,2))[0];obj=0x25ef1b8+objid*124;tree=s.u32(obj);root=struct.unpack('<H',s.read(tree+4,2))[0]
print('obj',objid,'tree',hex(tree),'root',root)
for i in list(range(1,42))+[115,116,117,143,144]:
    h=s.read(base+i*64,64);v=struct.unpack_from('<4H4H2H',h);ptr=struct.unpack_from('<I',h,20)[0];floats=struct.unpack_from('<ffhhffff',h,24)
    print(i,'links',v,'part',hex(ptr),lookup.get(ptr),'state',floats,'tail',h[52:].hex())
s.close()
