import sys,re,struct,json
from pathlib import Path
sys.path.insert(0,'work/porter')
from runtime import Session
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
s=Session(int(sys.argv[1]));code=s.read(0x401000,0x800000);md=Cs(CS_ARCH_X86,CS_MODE_32)
patterns={'get_client_dobj':rb'\x8b\x4c\x24.\x8b\x44\x24.\x69\xc9....\x03\xc1'}
for name,pattern in patterns.items():
    hits=[0x401000+m.start() for m in re.finditer(pattern,code,re.S)];print(name,[hex(x) for x in hits])
    for addr in hits:
        for ins in md.disasm(s.read(addr,130),addr):print(hex(ins.address),ins.mnemonic,ins.op_str)
cg=0x2e448c80
try:
    h=s.read(cg,32);print('cg',h.hex(),'client',s.u32(cg),'in_game',s.u32(cg+24))
    ci=cg+0x69a60+s.u32(cg)*0x808;data=s.read(ci,0x808);Path('work/research/clientinfo.bin').write_bytes(data)
    print('clientinfo',hex(ci),'valid',struct.unpack_from('<I',data,4)[0])
    Path('work/research/playerstate.bin').write_bytes(s.read(cg+0x480a8,0x2a08))
except Exception as e:print('cg error',str(e))
Path('work/research/game_code.bin').write_bytes(code);s.close()
