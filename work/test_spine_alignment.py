"""Audit actor spine positions against independently dumped model bind poses."""
import json,math,re,struct,sys,time,collections
from pathlib import Path
sys.path.insert(0,'work/porter')
from runtime import load_clip,adapt_tracks,flatten,DIRECT_SPINE_OFFSET
from mw2_assets import unflatten

def model_bones(path):
    text=path.read_text()
    labels={int(i):(int(parent),name) for i,parent,name in re.findall(r'^BONE (\d+) (-?\d+) "([^"]+)"',text,re.M)}
    output={}
    pattern=r'^BONE (\d+)\nOFFSET ([^\n]+)\nSCALE [^\n]+\nX ([^\n]+)\nY ([^\n]+)\nZ ([^\n]+)'
    for match in re.finditer(pattern,text,re.M):
        index=int(match[1])
        if index not in labels:continue
        parent,name=labels[index]
        vector=lambda value:tuple(float(x.strip()) for x in value.split(','))
        output[name]={'parent':labels[parent][1] if parent>=0 and parent in labels else None,
                      'position':vector(match[2]),'axes':tuple(vector(match[x]) for x in (3,4,5))}
    return output

def translation_keys(track):
    trans=track['trans'];typ=trans['type']
    if typ==8:return [(0,(0,0,0))]
    if typ==7:return [(0,tuple(trans['constant']))]
    width='B' if typ==5 else 'H';raw=struct.unpack('<'+width*(len(trans['values'])//struct.calcsize(width)),trans['values'])
    return [(frame,tuple(trans['mins'][j]+raw[i*3+j]*trans['size'][j] for j in range(3)))
            for i,frame in enumerate(trans['indices'])]

started=time.monotonic();rigs=[];source_rigs=[]
for folder in ('bo2_fbi','bo2_seals','cod4_actors'):
    for path in Path('work/spine_fix',folder,'model_export').glob('*lod0.xmodel_export'):
        bones=model_bones(path)
        if 'j_mainroot' not in bones or 'j_spinelower' not in bones:continue
        row={'file':str(path),'bones':bones}
        if folder.startswith('bo2'):rigs.append(row)
        elif bones['j_spinelower']['parent']=='j_mainroot':source_rigs.append(row)
assert len(rigs)==10 and source_rigs,'Required independently dumped body rigs are missing'
reference=rigs[0]['bones'];root=reference['j_mainroot'];spine=reference['j_spinelower']
bind=tuple(spine['position'][i]-root['position'][i] for i in range(3))
direct=tuple(sum(root['axes'][j][i]*bind[i] for i in range(3)) for j in range(3))
for rig in rigs:
    bones=rig['bones'];assert bones['j_spinelower']['parent']=='torso_stabilizer'
    assert bones['torso_stabilizer']['parent']=='pelvis'
    assert bones['j_mainroot']['axes']==root['axes']
    actual=tuple(bones['j_spinelower']['position'][i]-bones['j_mainroot']['position'][i] for i in range(3))
    assert actual==bind
assert all(abs(DIRECT_SPINE_OFFSET[i]-(direct[i]-bind[i]))<2e-6 for i in range(3))

original=load_clip('work/bo2/common_mp/xanim/pb_stand_alert')
target_names=[t['name'] for t in original['tracks']]
catalog=json.loads(Path('outputs/BO2SPAnims/library/catalog.json').read_text())
counts=collections.defaultdict(collections.Counter);key_count=0;maximum_error=0;roundtrips=0;errors=[]
for index,item in enumerate(catalog):
    try:
        anim=load_clip(Path('outputs/BO2SPAnims')/item['path']);source={t['name']:t for t in anim['tracks']}
        adapted,missing=adapt_tracks(anim,target_names);tracks={t['name']:t for t in adapted['tracks']}
        assert [t['name'] for t in adapted['tracks']]==target_names
        corrected='torso_stabilizer' not in source and 'j_spinelower' in source and 'j_mainroot' in source
        counts[item['game']]['checked']+=1
        if corrected:
            counts[item['game']]['direct_actor_spine_corrected']+=1
            old=source['j_spinelower'];new=tracks['j_spinelower']
            before=translation_keys(old);after=translation_keys(new)
            assert [f for f,v in before]==[f for f,v in after]
            # Each axis is evaluated independently from model-export data,
            # not from the implementation's correction constant. This is the
            # parent-space displacement seen by skinning before root rotation.
            for (_,a),(_,b) in zip(before,after):
                expected=tuple(direct[j]+a[j] for j in range(3))
                actual=tuple(bind[j]+b[j] for j in range(3))
                error=math.dist(expected,actual);maximum_error=max(maximum_error,error);key_count+=1
                assert error<2e-5,(item['name'],error)
            for name,t in source.items():
                if name in tracks and name!='j_spinelower':assert tracks[name]['trans']==t['trans']
            assert new['trans']['indices']==old['trans']['indices']
            assert new['trans']['values']==old['trans']['values']
        else:
            counts[item['game']]['authored_spine_preserved']+=1
            for name,t in source.items():
                if name in tracks:assert tracks[name]['trans']==t['trans']
        assert adapted['delta']==anim['delta'] and adapted['fps']==anim['fps'] and adapted['loop']==anim['loop']
        flat=flatten(adapted)
        inverse=unflatten({'frames':adapted['frames'],'fps':adapted['fps'],'loop':adapted['loop'],'kind':adapted['kind'],'counts':flat['counts']},
                         target_names,{k:v for k,v in flat.items() if k!='counts'},adapted['notes'],adapted['delta'])
        for old,new in zip(adapted['tracks'],inverse['tracks']):
            assert old['name']==new['name'] and old['quat']==new['quat']
            assert translation_keys(old)==translation_keys(new)
        roundtrips+=1
    except Exception as error:errors.append({'game':item['game'],'name':item['name'],'error':str(error)})
    if (index+1)%500==0:print('Spine checks',index+1,'errors',len(errors),flush=True)

report={'catalog':dict(counts),'model_rigs_verified':len(rigs),'direct_source_model_rigs':len(source_rigs),
        'translation_keys_checked':key_count,'maximum_position_error_units':maximum_error,
        'old_bind_position_error_units':math.dist(bind,direct),'inverse_stream_roundtrips':roundtrips,
        'errors':errors,'seconds':round(time.monotonic()-started,2),
        'coverage':'Data and model bind-position audit. Representative live visual tests are separate.'}
Path('work/spine_alignment_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps({**report,'errors':errors[:10],'error_count':len(errors)}),flush=True)
if errors:sys.exit(1)
