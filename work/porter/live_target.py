"""Read the local character's live BO2 animation tree without changing it.

The three layouts are discovered from executable signatures and checked
against the current DObj, animation entries and parent links before use.
"""
import math,re,struct

class AnimationChanging(RuntimeError):pass

def action_name(name):
    n=name.casefold()
    if 'death' in n:return 'Death'
    if 'stumble' in n or 'pain' in n:return 'Stumble / pain'
    if 'sprint' in n:return 'Sprinting'
    if 'jump' in n:return 'Jumping'
    if 'climb' in n or 'mantle' in n:return 'Climbing'
    if 'crawl' in n:return 'Crawling'
    if 'run' in n or 'jog' in n:return 'Running'
    if 'walk' in n:return 'Walking'
    if 'turn' in n:return 'Turning'
    if 'crouch' in n:return 'Crouched idle'
    if 'prone' in n:return 'Prone idle'
    if 'shoot' in n or 'fire' in n:return 'Firing'
    if 'reload' in n:return 'Reloading'
    return 'Idle'

def read_tree_nodes(data,entries,root,names):
    """Return contributing leaves, including inherited blend weights."""
    if not root:return []
    capacity=len(data)//64;count=(len(entries)+12)//16;seen=set();output=[]
    stack=[(root,0,1.0)]
    while stack:
        index,parent,inherited=stack.pop()
        while index:
            if index>=capacity or index in seen or len(seen)>=1024:raise AnimationChanging('Animation links changed; retrying.')
            seen.add(index);off=index*64
            previous,next_index,child,actual_parent,anim_index=struct.unpack_from('<5H',data,off+8)
            if actual_parent!=parent or anim_index>=count:raise AnimationChanging('Animation tree changed; retrying.')
            weight=struct.unpack_from('<f',data,off+44)[0];phase=struct.unpack_from('<f',data,off+24)[0]
            if not math.isfinite(weight) or not 0<=weight<=1.01 or not math.isfinite(phase):raise AnimationChanging('Animation state changed; retrying.')
            effective=inherited*min(weight,1.0);part=struct.unpack_from('<I',data,off+20)[0]
            if child:stack.append((child,index,effective))
            else:
                # A leaf must reference the parts of this exact tree entry.
                expected=struct.unpack_from('<I',entries,anim_index*16)[0]
                name=names.get(part)
                if name and expected==part and effective>0.005 and name.startswith(('pb_','pt_','p_')):
                    output.append({'target':name,'weight':round(effective,4),'phase':max(0,min(phase,1.0)),
                                   'layer':'Body' if name.startswith('pb_') else 'Upper body',
                                   'action':action_name(name),'selectable':name.startswith('pb_'),'_nodes':[index]})
            index=next_index
    # The same parts can contribute through more than one branch.
    merged={}
    for item in output:
        name=item['target']
        if name not in merged:merged[name]=item
        else:
            nodes=merged[name]['_nodes']+item['_nodes']
            if item['weight']>merged[name]['weight']:merged[name]=item
            merged[name]['_nodes']=nodes
    return sorted(merged.values(),key=lambda x:(-x['weight'],x['target']))

class LiveTargetReader:
    def __init__(self,session):
        self.session=session;code=session.read(0x401000,0x800000)
        def unique(pattern,label):
            hits=list(re.finditer(pattern,code,re.S))
            if len(hits)!=1:raise RuntimeError('Live targeting is unavailable for this BO2 build ('+label+').')
            return hits[0].start()
        hit=unique(rb'\x8b\x4c\x24\x08\x8b\x44\x24\x04\x69\xc9....\x03\xc1\x0f\xb7\x04\x45....\x66\x85\xc0\x74.\x98\x6b\xc0.\x05....\xc3','DObj lookup')
        self.client_stride=struct.unpack_from('<I',code,hit+10)[0]
        self.object_map=struct.unpack_from('<I',code,hit+20)[0]
        self.object_size=code[hit+32]
        self.objects=struct.unpack_from('<I',code,hit+34)[0]
        if self.client_stride!=0x701 or self.object_size!=124:raise RuntimeError('Unsupported live DObj layout.')
        hit=unique(rb'\x8b\x44\x24\x04\xc1\xe0\x06\x05....\xc3\xcc\xcc\xcc','animation nodes')
        self.infos=struct.unpack_from('<I',code,hit+8)[0]
        hit=unique(rb'\xa1....\x83\xec\x0c\x53\x8b\x5c\x24\x14\x56\x8b\xb0\x8c\x80\x04\x00\x57','local client')
        self.cg_pointer=struct.unpack_from('<I',code,hit+1)[0]
        self.names={address:name for name,(address,data) in session.assets.items()}
        self.cache_key=None;self.entries=None
    def snapshot(self):
        s=self.session;cg=s.u32(self.cg_pointer)
        if not cg or s.u32(cg+24)!=1:return {'ready':False,'message':'Start a multiplayer match to detect your animation.'}
        ps=cg+0x480a8;client=s.u32(ps+0x1a0)
        if not 0<=client<18:return {'ready':False,'message':'Waiting for a playable character.'}
        ci=cg+0x69a60+client*0x808
        if s.u32(ci+4)!=1:return {'ready':False,'message':'Waiting for the character to spawn.'}
        dead=bool(s.u32(ci+0x8c));entity=client
        if dead:
            corpse=s.u32(ps+0xf4)
            if corpse<8:entity=18+corpse
        object_id=struct.unpack('<H',s.read(self.object_map+entity*2,2))[0]
        if not object_id:return {'ready':False,'message':'Waiting for the character model.'}
        obj=self.objects+object_id*self.object_size;head=s.read(obj,12)
        if struct.unpack_from('<H',head,6)[0]!=entity+1:raise AnimationChanging('The character model changed; retrying.')
        tree=struct.unpack_from('<I',head)[0]
        if not tree:return {'ready':False,'message':'This character has no active animation tree.'}
        tree_head=s.read(tree,8);anims,root=struct.unpack_from('<IH',tree_head)
        size=s.u32(anims+4)
        if not 1<=size<=4096 or root>=4096:raise RuntimeError('Unsupported live animation tree layout.')
        key=(anims,size)
        self.entries=s.read(anims+32,(size-1)*16+4)
        if key!=self.cache_key:
            self.cache_key=key
            s.refresh();self.names={address:name for name,(address,data) in s.assets.items()}
        data=s.read(self.infos,4096*64)
        items=read_tree_nodes(data,self.entries,root,self.names)
        stale=not items
        for item in items:
            part=s.u32(self.infos+item['_nodes'][0]*64+20)
            if s.text(s.u32(part))!=item['target']:stale=True;break
        if stale:
            s.refresh();self.names={address:name for name,(address,data) in s.assets.items()}
            items=read_tree_nodes(data,self.entries,root,self.names)
        if s.u32(obj)!=tree or s.read(tree,8)!=tree_head:raise AnimationChanging('The animation tree changed; retrying.')
        body=[x for x in items if x['selectable']]
        primary=body[0] if body else None
        return {'ready':bool(primary),'message':'Detected from the live character animation tree.' if primary else 'No replaceable body animation is contributing yet.',
                'client':client,'entity':entity,'dead':dead,'primary':primary,'animations':items}
    def restart(self,targets):
        """Restart only matching contributing nodes on the local character."""
        s=self.session
        if s.read_only:raise RuntimeError('The observer cannot restart an animation.')
        if not self.snapshot().get('ready'):return 0
        from runtime import n
        if n.NtSuspendProcess(s.handle)<0:raise RuntimeError('Cannot pause BO2 to restart the selected animation.')
        restarted=0
        try:
            # Read again while paused: node identifiers can be recycled during
            # transitions, so never write using an earlier observer snapshot.
            current=self.snapshot()
            for item in current.get('animations',[]):
                if item['target'] not in targets:continue
                for index in item['_nodes']:
                    s.write(self.infos+index*64+24,bytes(12));restarted+=1
        finally:n.NtResumeProcess(s.handle)
        return restarted
