import sys,struct,re,json
from pathlib import Path
sys.path.insert(0,'work/porter')
from runtime import Session
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
s=Session(int(sys.argv[1]));objid=struct.unpack('<H',s.read(0x262d1c0,2))[0];obj=0x25ef1b8+objid*124;tree=s.u32(obj);anims=s.u32(tree);head=s.read(anims,16);size=struct.unpack_from('<I',head,4)[0];debug=s.u32(anims+12)
print('tree',hex(tree),'root info',struct.unpack('<H',s.read(tree+4,2))[0],'anims',hex(anims),'size',size,'debug',hex(debug))
lookup={addr:name for name,(addr,data) in s.assets.items()}
for i in range(30):
    entry=s.read(anims+16+i*16,16);part=struct.unpack_from('<I',entry)[0]
    try:name=s.text(s.u32(debug+i*4))
    except Exception:name='?'
    print('entry',i,entry.hex(),lookup.get(part),name)
Path('work/research/anim_tree.bin').write_bytes(s.read(anims,16+size*16))
code=s.read(0x401000,0x800000);md=Cs(CS_ARCH_X86,CS_MODE_32)
# Multiplication-based references to small runtime node arrays.
for m in re.finditer(rb'\x69[\xc0-\xff][\x38\x40\x44\x48\x4c\x50\x54\x58\x5c\x60\x64\x68\x70\x80\x90\xa0]\x00\x00\x00',code):
    addr=0x401000+m.start();block=list(md.disasm(code[m.start():m.start()+25],addr))
    if any(('0x2' in x.op_str or '0x3' in x.op_str) and x.mnemonic in ('add','lea','mov') for x in block):
        print('candidate',hex(addr),'; '.join(x.mnemonic+' '+x.op_str for x in block))
s.close()
