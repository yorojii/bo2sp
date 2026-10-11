import sys,json,ctypes,traceback,time
from pathlib import Path
sys.path.insert(0,'work/porter')
from runtime import Session,k
root=Path('outputs/BO2SPAnims').resolve()
mapping={name:str(root/path) for name,path in json.loads((root/'profile.json').read_text())['mapping'].items()}
s=Session(int(sys.argv[1]));baseline={name:s.assets[name] for name in mapping if name in s.assets}
normal=s.alloc;stats=[];report={};ever_published=False
def diagnostic(data):
    ctypes.set_last_error(0)
    try:
        ptr=normal(data)
        if ptr:stats.append({'size':len(data),'ptr':hex(ptr)})
        return ptr
    except Exception:
        report.update({'failed_size':len(data),'winerror':ctypes.get_last_error(),'successful_allocations':len(stats),'allocated_bytes':sum(x['size'] for x in stats),'last_allocations':stats[-8:]})
        raise
s.alloc=diagnostic
try:
    applied=s.apply(mapping);ever_published=True
    report.update({'imported':len(applied),'successful_allocations':len(stats),'allocated_bytes':sum(x['size'] for x in stats),'reserved_blocks':len(s.allocations)})
    repeated=[]
    for i in range(30):
        time.sleep(0.5)
        changed=s.apply(mapping)
        if changed:repeated.append({'poll':i,'updates':len(changed)})
    report['unchanged_selection_poll_updates']=repeated
    report['blocks_after_polling']=len(s.allocations)
except Exception as e:
    report['error']=str(e);traceback.print_exc()
finally:
    report['restored']=s.restore()
    report['all_original_headers_verified']=all(s.read(addr,104)==old for addr,old in baseline.values())
    if not ever_published:
        for ptr in s.allocations:k.VirtualFreeEx(s.handle,ptr,0,0x8000)
    s.close()
Path('work/allocation_probe.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
