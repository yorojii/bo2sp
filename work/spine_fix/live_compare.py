"""Temporary local-match A/B preview; restores the original slot on exit."""
import sys,json,time,struct,traceback
from pathlib import Path
sys.path.insert(0,'work/porter')
import runtime
from live_target import LiveTargetReader,AnimationChanging

control=Path('work/spine_fix/live_control.json');status=Path('work/spine_fix/live_status.json')
pid=int(sys.argv[1]);s=runtime.Session(pid);reader=LiveTargetReader(s);target='pb_stand_alert'
baseline=s.assets[target];normal=runtime.adapt_spine_translation;previous=None;results=[];started=time.monotonic()
catalog=json.loads(Path('outputs/Yoroji Tool/library/catalog.json').read_text())
try:
    while time.monotonic()-started<300:
        command=json.loads(control.read_text())
        if command.get('stop'):break
        key=(command['game'],command['clip'],command['mode'])
        if key!=previous:
            item=next(x for x in catalog if x['game']==key[0] and x['name']==key[1])
            clip=Path('outputs/Yoroji Tool')/item['path'];anim=runtime.load_clip(clip)
            assert not anim['loop'],'Use a one-shot clip for the frozen end-pose comparison'
            current=reader.snapshot();assert any(x['target']==target for x in current.get('animations',[])),'Stand still with the primary weapon'
            runtime.adapt_spine_translation=normal if key[2]=='fixed' else lambda anim,track,names:track['trans']
            s.imported_paths.pop(target,None);assert len(s.apply({target:str(clip)}))==1
            if runtime.n.NtSuspendProcess(s.handle)<0:raise RuntimeError('Cannot pause comparison')
            try:
                current=reader.snapshot()
                for layer in current.get('animations',[]):
                    if layer['target']==target:
                        for index in layer['_nodes']:s.write(reader.infos+index*64+24,struct.pack('<ffHH',1,1,0,0))
            finally:runtime.n.NtResumeProcess(s.handle)
            time.sleep(0.25)
            entry={'game':key[0],'clip':key[1],'mode':key[2],'pid':pid,'target':target,'name_pointer_preserved':s.imported[target][64:68]==baseline[1][64:68], 'snapshot':reader.snapshot()}
            results.append(entry);status.write_text(json.dumps(entry,indent=2));print(json.dumps({k:v for k,v in entry.items() if k!='snapshot'}),flush=True);previous=key
        time.sleep(0.1)
except Exception:
    status.write_text(json.dumps({'error':traceback.format_exc()},indent=2));raise
finally:
    runtime.adapt_spine_translation=normal
    s.restore();exact=s.read(baseline[0],104)==baseline[1];s.close()
    Path('work/spine_live_validation.json').write_text(json.dumps({'comparisons':results,'exact_original_restore':exact},indent=2))
    print('Original slot restored:',exact,flush=True)
