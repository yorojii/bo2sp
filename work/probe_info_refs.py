import re,struct
from pathlib import Path
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
b=Path('work/research/game_code.bin').read_bytes();md=Cs(CS_ARCH_X86,CS_MODE_32)
for value in [0x2b6ee40,0x2b6ee54,0x2b6ee58,0x2b6ee6c,0x2e448c80,0x113f18c]:
    hits=[m.start() for m in re.finditer(re.escape(struct.pack('<I',value)),b)];print(hex(value),len(hits),[hex(0x401000+x) for x in hits[:20]])
    for h in hits[:3]:
        print('context',b[h-8:h+28].hex())
        for ins in md.disasm(b[max(0,h-16):h+50],0x401000+max(0,h-16)):print(hex(ins.address),ins.mnemonic,ins.op_str)
