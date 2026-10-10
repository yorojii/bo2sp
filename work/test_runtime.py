import importlib.util,json,struct
from pathlib import Path
s=importlib.util.spec_from_file_location('runtime','work/porter/runtime.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
session=m.Session(10572)
names=json.loads(Path('work/project/names.json').read_text())
errors=[];matched=0
for name in names:
    data=(Path('work/bo2/common_mp/xanim')/name).read_bytes()
    try:
        anim=m.decode(data);flat=m.flatten(anim);addr,old=session.assets[name]
        if bytes(flat['counts'])!=old[24:34]:errors.append((name,'counts',flat['counts'],list(old[24:34])))
        for offset,key in [(68,'byte'),(72,'short'),(76,'int'),(80,'randomshort'),(84,'randombyte'),(92,'indices')]:
            expected=flat[key];actual=session.read(struct.unpack_from('<I',old,offset)[0],len(expected))
            if expected!=actual:
                first=next(i for i,(a,b) in enumerate(zip(expected,actual)) if a!=b)
                if key in ('randomshort','short'):
                    computed=set();cursor=0
                    for track in anim['tracks']:
                        q=track['quat']
                        if key=='randomshort' and q['type'] in (1,2):
                            width=2 if q['type']==1 else 4
                            computed.update(cursor+i*width+width-1 for i in range(len(q['values'])))
                            cursor+=len(q['values'])*width
                        elif key=='short':
                            if q['type'] in (1,2):
                                cursor+=1
                                if anim['frames']>=256:
                                    cursor+=((len(q['indices'])-2)//256+2) if len(q['indices'])>=65 else len(q['indices'])
                            elif q['type'] in (3,4):
                                width=2 if q['type']==3 else 4
                                computed.add(cursor+width-1);cursor+=width
                    vals=struct.unpack('<'+'h'*(len(expected)//2),expected)
                    actualvals=struct.unpack('<'+'h'*(len(actual)//2),actual)
                    mismatches=[(i,a,b) for i,(a,b) in enumerate(zip(vals,actualvals)) if a!=b and not (i in computed and abs(a-b)<=2)]
                    if mismatches:errors.append((name,key,mismatches[:3]))
                else:errors.append((name,key,first,expected[first:first+8].hex(),actual[first:first+8].hex()))
        matched+=1
    except Exception as e:errors.append((name,str(e)))
Path('work/runtime_flat_test.json').write_text(json.dumps({'checked':matched,'errors':errors},indent=2))
print('checked',matched,'errors',len(errors));print(errors[:12])
session.close()
