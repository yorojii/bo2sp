from pathlib import Path
import shutil, subprocess, json
ROOT=Path(__file__).resolve().parent
project=ROOT/'project'
(project/'raw/xanim').mkdir(parents=True,exist_ok=True)
(project/'zone_source').mkdir(exist_ok=True)
a=ROOT/'cod4/common_mp/xanim'; b=ROOT/'bo2/common_mp/xanim'
names=sorted(p.name for p in a.iterdir() if (b/p.name).exists() and p.name.startswith('pb_') and any(k in p.name for k in ('death','run','walk','sprint','jump','crawl','alert','ads','hold','prone2','crouch2')))
for n in names: shutil.copy2(a/n,project/'raw/xanim'/n)
lines=(ROOT/'common_mp_list.txt').read_text(encoding='utf-8-sig').splitlines()
start=lines.index('Content:')+1
assets=[]
for line in lines[start:]:
    if line.startswith('Unloaded'): break
    if ',' in line: assets.append(','.join(x.strip() for x in line.split(',')))
(project/'zone_source/common_mp.zone').write_text('>game,T6\n>name,common_mp\n>level.@00012d3c,0\n'+ '\n'.join(assets)+'\n',encoding='utf-8')
(project/'names.json').write_text(json.dumps(names,indent=2))
cmd=[str(ROOT/'oat/Linker.exe'),'-v','-b',str(project),'-l',r'D:\Call of Duty Black Ops II\zone\all\common_mp.ff','common_mp']
result=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
(ROOT/'probe_build.log').write_text(result.stdout,encoding='utf-8')
print('animations:',len(names),'assets:',len(assets),'exit:',result.returncode)
print(result.stdout[-3000:])
