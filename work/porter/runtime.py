"""Session-only compiled XAnim importer for BO2 Redacted MP.

Animation layout follows OpenAssetTools' T6 XAnim loader and Greyhound's
BO2 asset-pool discovery. No executable code or game files are patched.
"""
import ctypes, struct, math, re, json, zlib
from ctypes import wintypes
from pathlib import Path

def f32(x): return struct.unpack('<f',struct.pack('<f',x))[0]
def pack16(values): return struct.pack('<'+'H'*len(values),*(x&65535 for x in values))
def pack32(values): return struct.pack('<'+'I'*len(values),*values)

class Reader:
    def __init__(self,data): self.data=data; self.pos=0
    def take(self,n):
        if n<0 or self.pos+n>len(self.data):raise ValueError('Truncated XAnim')
        out=self.data[self.pos:self.pos+n];self.pos+=n;return out
    def unpack(self,fmt):return struct.unpack('<'+fmt,self.take(struct.calcsize('<'+fmt)))
    def one(self,fmt):return self.unpack(fmt)[0]
    def text(self):
        end=self.data.find(b'\0',self.pos)
        if end<0 or end-self.pos>256:raise ValueError('Invalid animation string')
        return self.take(end-self.pos+1)[:-1].decode('ascii')

def decode(data):
    r=Reader(data);version,stored,bones,flags,kind,fps=r.unpack('HHHBBH')
    if version not in (17,18,19) or flags&~(7 if version in (18,19) else 3) or not fps or bones>255:
        raise ValueError('Expected a CoD4 v17 or compatible v19 body animation')
    loop=bool(flags&1);frames=stored if loop else stored-1;coverage=frames+1
    if frames<0:raise ValueError('Invalid frame count')
    def indices(n):return list(range(n)) if n>=coverage else list(r.unpack(('B' if frames<256 else 'H')*n))
    def quats(n,half,flip=False):
        output=[]
        for i in range(n):
            q=list(r.unpack('h'*(1 if half else 3)))
            square=max(0,0x3fff0001-sum(x*x for x in q))
            q.append(math.floor(f32(f32(math.sqrt(f32(square)))+0.5)) if square else 0)
            if (i==0 and flip) or (i and sum(x*y for x,y in zip(q,output[-1]))<0):q=[-x for x in q]
            output.append(q)
        return output
    def read_quat(half,flip=False):
        n=r.one('H')
        idx=indices(n) if n>1 else []
        return {'type':0 if not n else (3 if half else 4) if n==1 else 1 if half else 2,
                'indices':idx,'values':quats(n,half,flip)}
    def read_trans():
        n=r.one('H')
        if not n:return {'type':8,'indices':[],'values':b''}
        if n==1:return {'type':7,'constant':r.unpack('fff'),'indices':[],'values':b''}
        idx=indices(n);small=bool(r.one('B'));mins=r.unpack('fff')
        scale=0.003921568859368563 if small else 0.00001525902189314365
        size=tuple(f32(x*scale) for x in r.unpack('fff'))
        values=r.take(n*(3 if small else 6))
        return {'type':5 if small else 6,'indices':idx,'values':values,'mins':mins,'size':size,'small':small}
    delta=None
    if flags&2 or (version==18 and flags&4):delta={'quat':read_quat(not (version==18 and flags&4)),'trans':read_trans(),'three_d':bool(version==18 and flags&4)}
    masksize=(bones+7)//8;flips=r.take(masksize);halves=r.take(masksize)
    names=[r.text() for _ in range(bones)]
    tracks=[]
    for i,name in enumerate(names):
        q=read_quat(bool(halves[i//8]&(1<<(i%8))),bool(flips[i//8]&(1<<(i%8))))
        tracks.append({'name':name,'quat':q,'trans':read_trans()})
    notes=[(r.text(),r.one('H')) for _ in range(r.one('B'))]
    notes=[(name,f32(frame/frames) if frames else 0) for name,frame in notes]
    notes.append(('end',1.0))
    if r.pos!=len(data):raise ValueError('Unexpected trailing animation data')
    tracks.sort(key=lambda t:t['quat']['type'])
    return {'frames':frames,'loop':loop,'delta':delta,'kind':kind,'fps':fps,'tracks':tracks,'notes':notes}

def flatten(anim,tracks=None):
    tracks=anim['tracks'] if tracks is None else tracks
    byte=[];short=[];integer=[];randomshort=[];randombyte=bytearray();rootindices=[];counts=[0]*10
    def indices(idx):
        short.append(len(idx)-1)
        if anim['frames']<256:byte.extend(idx)
        elif len(idx)>=65:
            rootindices.extend(idx)
            short.extend(idx[i*256] for i in range((len(idx)-2)//256+1));short.append(idx[-1])
        else:short.extend(idx)
    def floats(values):integer.extend(struct.unpack('<III',struct.pack('<fff',*values)))
    for track in tracks:
        q=track['quat'];counts[q['type']]+=1
        if q['type'] in (1,2):
            indices(q['indices']);randomshort.extend(x for v in q['values'] for x in v)
        elif q['type'] in (3,4):short.extend(q['values'][0])
        counts[track['trans']['type']]+=1
    for i in sorted(range(len(tracks)),key=lambda i:tracks[i]['trans']['type']):
        t=tracks[i]['trans'];byte.append(i)
        if t['type'] in (5,6):
            indices(t['indices']);floats(t['mins']);floats(t['size'])
            if t['type']==5:randombyte.extend(t['values'])
            else:randomshort.extend(struct.unpack('<'+'H'*(len(t['values'])//2),t['values']))
        elif t['type']==7:floats(t['constant'])
    counts[9]=len(tracks)
    if max(len(byte),len(short),len(integer),len(randombyte))>65535:raise ValueError('Animation exceeds T6 limits')
    return {'counts':counts,'byte':bytes(byte),'short':pack16(short),'int':pack32(integer),
            'randomshort':pack16(randomshort),'randombyte':bytes(randombyte),'indices':pack16(rootindices)}

def body_clip(anim):
    core={'j_mainroot','j_spinelower','j_spineupper','j_head','j_hip_le','j_hip_ri'}
    return len(core.intersection(t['name'] for t in anim['tracks']))>=3

# T6's standard human bind pose, checked against the FBI and SEAL body
# models. The stabilizer's bind axes are world-aligned; an actor rig without
# that bone instead expresses the lower-spine offset in mainroot's axes.
# Keeping a neutral stabilizer preserves actor rotations, but its child's
# default translation must also change basis. Otherwise the torso is moved
# sideways/downwards by about seven units even when all rotations are valid.
SPINE_BIND_OFFSET=(0.070130,0.000007,5.204613)
MAINROOT_BIND_AXES=((-0.024873,0.000031,0.999693),
                    (0.999693,-0.000032,0.024871),
                    (0.000031,1.000002,-0.000032))
DIRECT_SPINE_OFFSET=tuple(f32(sum(axis[i]*SPINE_BIND_OFFSET[i] for i in range(3))-SPINE_BIND_OFFSET[j])
                          for j,axis in enumerate(MAINROOT_BIND_AXES))

def adapt_spine_translation(anim,track,target_names):
    """Correct the bind-position basis for direct-pelvis actor spines.

    Existing stabilized multiplayer clips retain their authored tracks.
    Only a target with an explicitly neutralized stabilizer is corrected;
    adding/reordering destination bones would invalidate cached DObj maps.
    """
    trans=track['trans']
    if track['name']!='j_spinelower':return trans
    names={t['name'] for t in anim['tracks']}
    if ('torso_stabilizer' in names
        or 'torso_stabilizer' not in target_names or 'j_mainroot' not in names):
        return trans
    out=dict(trans);typ=trans['type']
    if typ==8:
        out={'type':7,'constant':DIRECT_SPINE_OFFSET,'indices':[],'values':b''}
    elif typ==7:
        out['constant']=tuple(f32(x+y) for x,y in zip(trans['constant'],DIRECT_SPINE_OFFSET))
    elif typ in (5,6):
        # Shift the decoded translation without resampling keys or changing
        # quantized values, scale, timing, loop flags, or root motion.
        out['mins']=tuple(f32(x+y) for x,y in zip(trans['mins'],DIRECT_SPINE_OFFSET))
    else:raise ValueError('Unsupported lower-spine translation type')
    return out

def adapt_tracks(anim,target_names):
    """Preserve the destination's cached bone indices without losing motion."""
    if not body_clip(anim):raise ValueError('This clip does not contain a compatible character rig')
    source={t['name']:t for t in anim['tracks']}
    if len(source)!=len(anim['tracks']):raise ValueError('Duplicate source bone names')
    missing=[name for name in source if name not in target_names]
    core=[name for name in missing if name in ('j_mainroot','j_hip_le','j_hip_ri','j_spinelower','j_spineupper','j_head','j_knee_le','j_knee_ri','j_ankle_le','j_ankle_ri')]
    if core:raise ValueError('Essential target bones unavailable: '+', '.join(core))
    # A one-frame static pose needs two equal keys in the animated-quaternion
    # group. This avoids a zero-sized interpolation interval in the engine.
    adapted=dict(anim);adapted['frames']=max(1,anim['frames']);tracks=[]
    for name in target_names:
        track=source.get(name)
        q=track['quat'] if track else {'type':0,'values':[],'indices':[]}
        typ=q['type'];values=q['values'] if typ else [[0,0,0,32767]]
        if typ in (1,3):values=[[0,0,*v] for v in values]
        if typ in (1,2) and len(q['indices'])>1:indices=q['indices']
        else:
            indices=[0,adapted['frames']];values=[values[0],values[0]]
        trans=adapt_spine_translation(anim,track,target_names) if track else {'type':8,'indices':[],'values':b''}
        tracks.append({'name':name,'quat':{'type':2,'indices':indices,'values':values},'trans':trans})
    adapted['tracks']=tracks
    return adapted,missing

def load_clip(path):
    data=Path(path).read_bytes()
    if Path(path).suffix.lower()=='.yanim':
        obj=json.loads(zlib.decompress(data[6:]) if data.startswith(b'YANIM\x01') else data)
        if obj.get('format')!='yoroji.animation.v1':raise ValueError('Unknown animation cache format')
        anim=obj['animation']
        for t in anim['tracks']:t['trans']['values']=bytes.fromhex(t['trans'].get('values',''))
        if anim.get('delta'):anim['delta']['trans']['values']=bytes.fromhex(anim['delta']['trans'].get('values',''))
        flatten(anim)
        return anim
    return decode(data)

k=ctypes.WinDLL('kernel32',use_last_error=True)
n=ctypes.WinDLL('ntdll')
k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE
k.ReadProcessMemory.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)];k.ReadProcessMemory.restype=wintypes.BOOL
k.WriteProcessMemory.argtypes=k.ReadProcessMemory.argtypes;k.WriteProcessMemory.restype=wintypes.BOOL
k.VirtualAllocEx.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_size_t,wintypes.DWORD,wintypes.DWORD];k.VirtualAllocEx.restype=ctypes.c_void_p
k.VirtualFreeEx.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_size_t,wintypes.DWORD];k.VirtualFreeEx.restype=wintypes.BOOL
k.CloseHandle.argtypes=[wintypes.HANDLE];k.CloseHandle.restype=wintypes.BOOL
n.NtSuspendProcess.argtypes=[wintypes.HANDLE];n.NtSuspendProcess.restype=ctypes.c_long
n.NtResumeProcess.argtypes=[wintypes.HANDLE];n.NtResumeProcess.restype=ctypes.c_long

class Session:
    def __init__(self,pid,read_only=False):
        self.pid=pid;self.read_only=read_only;self.handle=k.OpenProcess(0x410 if read_only else 0x438|0x800,False,pid)
        if not self.handle:raise OSError(ctypes.get_last_error(),'Cannot open BO2 process')
        self.allocations=[];self.arena_cursor=0;self.arena_remaining=0;self.originals={};self.imported={};self.imported_paths={}
        try:self.discover()
        except Exception:
            self.close();raise
    def read(self,addr,size):
        if not size:return b''
        if not addr or size>64*1024*1024:raise ValueError('Invalid memory request')
        buf=ctypes.create_string_buffer(size);got=ctypes.c_size_t()
        if not k.ReadProcessMemory(self.handle,addr,buf,size,ctypes.byref(got)) or got.value!=size:
            raise OSError(ctypes.get_last_error(),f'Cannot read BO2 data at {addr:#x}')
        return buf.raw
    def u32(self,addr):return struct.unpack('<I',self.read(addr,4))[0]
    def text(self,addr):return self.read(addr,128).split(b'\0')[0].decode('ascii',errors='replace')
    def write(self,addr,data):
        if self.read_only:raise RuntimeError('The live-target observer cannot write to the game.')
        if not data:return
        got=ctypes.c_size_t();buf=ctypes.create_string_buffer(data)
        if not k.WriteProcessMemory(self.handle,addr,buf,len(data),ctypes.byref(got)) or got.value!=len(data):
            raise OSError(ctypes.get_last_error(),'Cannot update animation data')
    def alloc(self,data):
        if self.read_only:raise RuntimeError('The live-target observer cannot allocate game memory.')
        if not data:return 0
        # Each separate Windows reservation occupies at least 64 KiB of
        # address space. Pack small streams into aligned shared blocks instead
        # of wasting one reservation on every short bone/notetrack array.
        size=(len(data)+15)&~15
        if self.arena_remaining<size:
            capacity=max(0x10000,(size+0xffff)&~0xffff);ptr=None
            for flags in (0x3000,0x103000):
                candidate=k.VirtualAllocEx(self.handle,None,capacity,flags,0x04)
                if candidate and candidate+capacity<=0x100000000:
                    ptr=candidate;break
                if candidate:k.VirtualFreeEx(self.handle,candidate,0,0x8000)
            if not ptr:raise OSError(ctypes.get_last_error(),'BO2 has no free 32-bit animation memory. Restart the game to clear previous session imports.')
            self.allocations.append(ptr);self.arena_cursor=ptr;self.arena_remaining=capacity
        ptr=self.arena_cursor;self.write(ptr,data)
        self.arena_cursor+=size;self.arena_remaining-=size
        return ptr
    def rollback_preparation(self,checkpoint):
        # Only call before any prepared headers have been published to BO2.
        count,cursor,remaining=checkpoint
        for ptr in self.allocations[count:]:k.VirtualFreeEx(self.handle,ptr,0,0x8000)
        del self.allocations[count:];self.arena_cursor=cursor;self.arena_remaining=remaining
    def discover(self):
        code=self.read(0x401000,0x800000)
        sig=bytes.fromhex('56 51 FF D2 8B F0 83 C4 04 85 F6')
        hits=[m.start() for m in re.finditer(re.escape(sig),code)]
        for offset in hits:
            hit=0x401000+offset;pools=self.u32(hit-11);sizes=self.u32(hit+59)
            try:
                model=self.u32(pools+20)
                if self.text(self.u32(model+4))!='defaultvehicle':continue
                self.pool=self.u32(pools+16);self.count=self.u32(sizes+16)
                if not 1000<=self.count<=50000:continue
                ss=code.find(bytes.fromhex('33 C9 66 89 0C 10 83 C0 02 83 F8 20'))
                if ss<0:continue
                self.strings=self.u32(0x401000+ss-46)
                self.refresh();return
            except (OSError,ValueError):continue
        raise RuntimeError('Unsupported BO2 build or multiplayer assets have not loaded yet')
    def refresh(self):
        pool=self.read(self.pool+4,self.count*104);assets={}
        for i in range(self.count):
            data=pool[i*104:(i+1)*104];ptr=struct.unpack_from('<I',data)[0]
            if not ptr or self.pool<=ptr<self.pool+4+self.count*104:continue
            try:name=self.text(ptr)
            except OSError:continue
            if re.fullmatch(r'[a-zA-Z0-9_.]+',name):assets[name]=(self.pool+4+i*104,data)
        self.assets=assets
        table=self.read(self.strings,24*65536+128);self.stringids={}
        for i in range(1,65536):
            segment=table[i*24+4:i*24+132];end=segment.find(b'\0')
            if end<=0:continue
            raw=segment[:end]
            if all(32<=x<127 for x in raw):self.stringids.setdefault(raw.decode('ascii'),i)
        return assets
    def native(self,anim,old):
        # BO2 caches each animation's bone map in live DObjs. Keep the target's
        # original name array and ordering, and encode rotations in one group,
        # so replacing a clip cannot reinterpret a cached head/arm bone index.
        count=old[33]
        ids=list(struct.unpack('<'+'H'*count,self.read(struct.unpack_from('<I',old,64)[0],count*2)))
        target_names=[self.text(self.strings+i*24+4) for i in ids]
        anim,missing=adapt_tracks(anim,target_names)
        flat=flatten(anim);out=bytearray(104);out[:4]=old[:4]
        def p(offset,fmt,*args):struct.pack_into('<'+fmt,out,offset,*args)
        p(4,'6H',len(flat['byte']),len(flat['short'])//2,len(flat['int'])//4,len(flat['randombyte']),0,anim['frames'])
        out[16]=anim['loop'];out[17]=bool(anim['delta']);out[18]=bool(anim['delta'] and anim['delta'].get('three_d'));out[24:34]=bytes(flat['counts']);out[35]=anim['kind']
        p(40,'II',len(flat['randomshort'])//2,len(flat['indices'])//2)
        p(48,'ffff',anim['fps'],f32(anim['fps']/anim['frames']) if anim['frames'] else 0,0,0)
        out[64:68]=old[64:68]
        for offset,key in [(68,'byte'),(72,'short'),(76,'int'),(80,'randomshort'),(84,'randombyte'),(92,'indices')]:p(offset,'I',self.alloc(flat[key]))
        notes=[(name,time) for name,time in anim['notes'] if name in self.stringids]
        if len(notes)>255:raise ValueError('Too many animation notetracks')
        out[34]=len(notes)
        p(96,'I',self.alloc(b''.join(struct.pack('<H2xf',self.stringids[name],time) for name,time in notes)))
        def ix(values):return bytes(values) if anim['frames']<256 else pack16(values)
        delta=anim['delta']
        if delta:
            q=delta['quat'];t=delta['trans'];qp=tp=0
            if q['values']:
                vals=pack16([x for v in q['values'] for x in v]);count=len(q['values'])
                if count==1:qp=self.alloc(bytes(4)+vals)
                else:qp=self.alloc(struct.pack('<H2xI',count-1,self.alloc(vals))+ix(q['indices']))
            if t['type']==7:tp=self.alloc(bytes(4)+struct.pack('<fff',*t['constant']))
            elif t['type'] in (5,6):
                tp=self.alloc(struct.pack('<HBxfff3fI',len(t['indices'])-1,t['small'],*t['mins'],*t['size'],self.alloc(t['values']))+ix(t['indices']))
            p(100,'I',self.alloc(struct.pack('<III',tp,0 if delta.get('three_d') else qp,qp if delta.get('three_d') else 0)))
        return bytes(out),missing
    def apply(self,mapping):
        if self.read_only:raise RuntimeError('The live-target observer cannot import animations.')
        self.refresh();plans=[];report=[]
        checkpoint=(len(self.allocations),self.arena_cursor,self.arena_remaining)
        try:
            for target,path in mapping.items():
                if target not in self.assets:continue
                addr,old=self.assets[target]
                source=Path(path).resolve();stat=source.stat();key=(str(source),stat.st_mtime_ns,stat.st_size)
                owned=self.imported.get(target)==old
                if owned and self.imported_paths.get(target)==key:continue
                original=self.originals[target][1] if owned else old
                anim=load_clip(path)
                new,missing=self.native(anim,old)
                plans.append((target,addr,old,new,original,key))
                report.append({'target':target,'frames':anim['frames'],'bones':new[33],'omitted_bones':missing})
        except Exception:
            self.rollback_preparation(checkpoint);raise
        if not plans:return report
        if n.NtSuspendProcess(self.handle)<0:raise RuntimeError('Cannot pause BO2 for an atomic animation update')
        written=[]
        try:
            for target,addr,old,new,original,key in plans:
                if self.read(addr,104)!=old:raise RuntimeError('Animation bank changed during import; retry')
            for target,addr,old,new,original,key in plans:
                self.write(addr,new);written.append((addr,old))
            for target,addr,old,new,original,key in plans:
                if self.read(addr,104)!=new:raise RuntimeError('Animation memory verification failed')
            for target,addr,old,new,original,key in plans:
                self.originals[target]=(addr,original);self.imported[target]=new;self.imported_paths[target]=key
        except Exception:
            for addr,old in reversed(written):self.write(addr,old)
            raise
        finally:n.NtResumeProcess(self.handle)
        return report
    def restore(self):
        return self.restore_targets(list(self.originals))
    def restore_targets(self,targets):
        if self.read_only:raise RuntimeError('The live-target observer cannot change animations.')
        targets=[target for target in targets if target in self.originals]
        if not targets:return 0
        if n.NtSuspendProcess(self.handle)<0:raise RuntimeError('Cannot pause BO2 for restore')
        restored=0
        try:
            for target in targets:
                addr,old=self.originals[target]
                if self.read(addr,104)==self.imported.get(target):self.write(addr,old);restored+=1
        finally:n.NtResumeProcess(self.handle)
        for target in targets:
            self.originals.pop(target,None);self.imported.pop(target,None);self.imported_paths.pop(target,None)
        return restored
    def close(self):
        # Allocations intentionally stay until BO2 exits: an animation tree may
        # still hold a reference while transitioning away from an imported clip.
        if self.handle:k.CloseHandle(self.handle);self.handle=None
