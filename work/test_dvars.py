import importlib.util,struct,re,json,sys
from pathlib import Path
s=importlib.util.spec_from_file_location('r','work/porter/runtime.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
p=m.Session(10572)
names={'cg_thirdPerson':0xc360cc,'r_dof_enable':0xd2d2dc,'timescale':0xbd70d0,'cg_thirdPersonRange':0xc2d9e0,'cg_thirdPersonAngle':0xc0e9cc}
found={}
for base in range(0xd42000,0x43a8000,0x100000):
    try:data=p.read(base,min(0x100000,0x43a8000-base))
    except OSError:continue
    for name,ptr in names.items():
        for match in re.finditer(re.escape(struct.pack('<I',ptr)),data):
            addr=base+match.start()
            if addr%8:continue
            header=p.read(addr,96)
            kind=struct.unpack_from('<I',header,16)[0]
            if kind>12:continue
            description=struct.unpack_from('<I',header,4)[0]
            try:desc=p.text(description) if description else ''
            except OSError:continue
            print(name,hex(addr),'type',kind,'header',header.hex(),'description',desc)
            found[name]=addr
Path('work/dvar_addresses.json').write_text(json.dumps(found))
if len(sys.argv)>1 and sys.argv[1]=='thirdperson':
    addr=found['cg_thirdPerson'];old=p.read(addr+24,16)
    Path('work/thirdperson_recovery.json').write_text(json.dumps({'address':addr,'value':old.hex()}))
    p.write(addr+24,b'\x01'+old[1:]);print('thirdperson enabled')
p.close()
