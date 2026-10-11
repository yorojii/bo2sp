"""Read MW2 SP's serialized 64-bit XAnim records without loading the game.

Only complete inline records with validated stream counts are accepted.
Layout references: OpenAssetTools IW4_Assets.h and XAssets/XAnimParts.txt.
"""
from pathlib import Path
import json,re,struct,zlib
from runtime import Reader,flatten,body_clip,pack16

INLINE=0xffffffffffffffff

def unflatten(header,names,arrays,notes,delta):
    frames=header['frames'];counts=header['counts']
    streams={key:Reader(data) for key,data in arrays.items()}
    b=streams['byte'];s=streams['short'];ints=streams['int'];rs=streams['randomshort'];rb=streams['randombyte'];ix=streams['indices']
    def indices():
        n=s.one('H')+1
        if n>frames+1:raise ValueError('Invalid keyed frame count')
        if frames<256:values=list(b.take(n))
        elif n>=65:s.take(((n-2)//256+2)*2);values=list(ix.unpack('H'*n))
        else:values=list(s.unpack('H'*n))
        if values!=sorted(set(values)) or values[-1]>frames:raise ValueError('Invalid keyed indices')
        return values
    tracks=[];cursor=0
    for typ in range(5):
        for _ in range(counts[typ]):
            q={'type':typ,'indices':[],'values':[]}
            if typ in (1,2):
                q['indices']=indices();width=2 if typ==1 else 4
                q['values']=[list(rs.unpack('h'*width)) for _ in q['indices']]
            elif typ in (3,4):q['values']=[list(s.unpack('h'*(2 if typ==3 else 4)))]
            tracks.append({'name':names[cursor],'quat':q,'trans':None});cursor+=1
    for typ in range(5,9):
        for _ in range(counts[typ]):
            bone=b.one('B')
            if bone>=len(tracks) or tracks[bone]['trans'] is not None:raise ValueError('Invalid translated bone index')
            t={'type':typ,'indices':[],'values':b''}
            if typ in (5,6):
                t['indices']=indices();t['mins']=ints.unpack('fff');t['size']=ints.unpack('fff');t['small']=typ==5
                t['values']=(rb if typ==5 else rs).take(len(t['indices'])*(3 if typ==5 else 6))
            elif typ==7:t['constant']=ints.unpack('fff')
            tracks[bone]['trans']=t
    if any(r.pos!=len(r.data) for r in streams.values()):raise ValueError('Animation stream counts do not match')
    anim={'frames':frames,'fps':header['fps'],'loop':header['loop'],'kind':header['kind'],'tracks':tracks,'delta':delta,'notes':notes}
    flat=flatten(anim)
    if any(flat[key]!=value for key,value in arrays.items()) or flat['counts']!=counts:raise ValueError('Animation reconstruction verification failed')
    return anim

def read_delta(r,frames):
    ptrs=r.unpack('QQQ');delta={'quat':{'type':0,'indices':[],'values':[]},'trans':{'type':8,'indices':[],'values':b''},'three_d':bool(ptrs[2])}
    def indices(n):
        vals=list(r.unpack(('B' if frames<256 else 'H')*n))
        if vals!=sorted(set(vals)) or vals[-1]>frames:raise ValueError('Invalid root-motion indices')
        return vals
    for kind,ptr in enumerate(ptrs):
        if not ptr:continue
        if ptr!=INLINE:raise ValueError('Shared root-motion record')
        size=r.one('H')
        if size>frames:raise ValueError('Invalid root-motion size')
        if kind==0:
            small=r.one('B');r.take(5)
            if not size:delta['trans']={'type':7,'constant':r.unpack('fff'),'indices':[],'values':b''}
            else:
                mins=r.unpack('fff');scale=r.unpack('fff');vp=r.one('Q')
                if small not in (0,1) or vp!=INLINE:raise ValueError('Unsupported root-motion storage')
                idx=indices(size+1);values=r.take((size+1)*(3 if small else 6))
                delta['trans']={'type':5 if small else 6,'small':bool(small),'mins':mins,'size':scale,'indices':idx,'values':values}
        else:
            r.take(6);width=2 if kind==1 else 4
            if not size:idx=[];values=[list(r.unpack('h'*width))]
            else:
                if r.one('Q')!=INLINE:raise ValueError('Shared root quaternion')
                idx=indices(size+1);values=[list(r.unpack('h'*width)) for _ in idx]
            delta['quat']={'type':(3 if kind==1 else 4) if not size else (1 if kind==1 else 2),'indices':idx,'values':values}
    return delta

def extract_fastfile(ff,output,log=print):
    ff=Path(ff);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    raw=ff.read_bytes()
    # MW2 (version 276) and MW3 (version 1) Steam fastfiles share this 64-bit serialized layout; MW3's file header has a
    # ninth block size, so its asset list starts 4 bytes later. Same XAnimParts header and arrays otherwise.
    layout={276:(40,'MW2 Actors'),1:(44,'MW3 Actors')}.get(struct.unpack_from('<I',raw,8)[0]) if raw[:8]==b'IWffu100' else None
    if not layout:raise ValueError('Expected an unsigned MW2 or MW3 SP PC fastfile')
    start,game=layout
    data=zlib.decompress(raw[21:])
    if len(data)>500_000_000:raise ValueError('Fastfile is too large')
    count,ptr=struct.unpack_from('<QQ',data,start)
    if not 1<count<65536 or ptr!=INLINE:raise ValueError('Unsupported script-string table')
    strings=[''];r=Reader(data);r.pos=start+32
    flags=r.unpack('Q'*count)
    for index,flag in enumerate(flags):
        if index==0:
            if flag:raise ValueError('Invalid script-string zero entry')
            continue
        strings.append(r.text() if flag else '')
    catalog=[];failures={}
    for match in re.finditer(re.escape(b'\xff'*8),data):
        pos=match.start()
        if pos+264>len(data):continue
        h=data[pos:pos+136];counts=list(h[21:31]);fps=struct.unpack_from('<f',h,44)[0]
        if not 3<=counts[9]<=200 or sum(counts[:5])!=counts[9] or sum(counts[5:9])!=counts[9] or not 1<=fps<=240:continue
        name=data[pos+136:pos+264].split(b'\0')[0]
        if not re.fullmatch(rb'[a-zA-Z0-9_.]+',name):continue
        try:
            bc,sc,ic,rbc,ric,frames=struct.unpack_from('<6H',h,8)
            rsc,indexcount=struct.unpack_from('<II',h,36);ptrs=struct.unpack_from('<10Q',h,56)
            if ric or any(p not in (0,INLINE) for p in ptrs):raise ValueError('Shared or unsupported animation array')
            rr=Reader(data);rr.pos=pos+136;name=rr.text()
            ids=rr.unpack('H'*counts[9]);names=[strings[i] for i in ids]
            if any(not n for n in names):raise ValueError('Unknown bone name')
            if not body_clip({'tracks':[{'name':n} for n in names]}):continue
            notes=[]
            if ptrs[8]:
                for _ in range(h[31]):
                    note,time=rr.unpack('H2xf')
                    if not 0<=time<=1.0001:raise ValueError('Invalid animation note time')
                    notes.append((strings[note],time))
            elif h[31]:raise ValueError('Missing note data')
            delta=read_delta(rr,frames) if ptrs[9] else None
            lengths=[bc,sc*2,ic*4,rsc*2,rbc,ric*4,indexcount*(1 if frames<256 else 2)]
            arrays={}
            for key,length,ptr in zip(['byte','short','int','randomshort','randombyte','randomint','indices'],lengths,ptrs[1:8]):
                if length and ptr!=INLINE:raise ValueError('Missing inline animation array')
                if key=='randomint':continue
                arrays[key]=rr.take(length)
            anim=unflatten({'frames':frames,'fps':fps,'loop':bool(h[20]&1),'kind':h[32],'counts':counts},names,arrays,notes,delta)
            path=output/(name+'.yanim')
            def serial(value):
                if isinstance(value,bytes):return value.hex()
                raise TypeError()
            path.write_bytes(b'YANIM\x01'+zlib.compress(json.dumps({'format':'yoroji.animation.v1','animation':anim},default=serial,separators=(',',':')).encode(),6))
            catalog.append({'game':game,'zone':ff.stem,'name':name,'path':str(path.resolve()),'frames':frames,'fps':fps,'loop':anim['loop'],'bones':len(names)})
        except (ValueError,IndexError,struct.error) as e:failures[str(e)]=failures.get(str(e),0)+1
    log(f'{ff.stem}: {len(catalog)} verified actor clips')
    return catalog,failures
