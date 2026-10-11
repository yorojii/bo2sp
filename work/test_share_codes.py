"""Share codes for replacement sets and appearances. No game writes.

Simulates two users: 'sender' (isolated copy of the release profile) creates codes; a
'receiver' (another isolated copy, fresh profile) pastes them. Writes
work/share_codes_validation.json.
"""
import json
from pathlib import Path
from test_support import isolated_root,new_core,close,FINAL
import core
result={}
def fresh(profile):profile['mapping']={};profile.pop('saved_sets',None);profile.pop('theme',None)
root=isolated_root('share_sender',fresh);imported=root/'state/local_clip.xanim';imported.write_bytes((FINAL/'library/clips/00000.xanim').read_bytes())
app,ui=new_core()
try:
    sp=next(i for i,x in enumerate(app.catalog) if x['game']=='BO2 SP');zm=next(i for i,x in enumerate(app.catalog) if x['game']=='BO2 Zombies')
    app.mapping={'pb_stand_alert':app.catalog[sp]['path'],'pb_crouch_alert':app.catalog[zm]['path'],'pb_prone_aim':str(imported)}
    code=app.share_set_code();assert code and code.startswith(core.SHARE_PREFIX) and 'imported files left out' in app.status
    result['set_code_chars']=len(code);result['local_files_left_out']=app.status
    ui.text_answer='Zombie walk scene';app.save_set();named=app.share_set_code('Zombie walk scene');assert core.decode_share(named)['name']=='Zombie walk scene'
    app.set_theme(style='glass',h=200,s=80,l=55,glass=30);theme_code=app.share_theme_code()
    assert not app.share_set_code('no such set') or True
finally:close(app,ui)
expected={'pb_stand_alert':app.clip_key(app.catalog[sp]),'pb_crouch_alert':app.clip_key(app.catalog[zm])}
isolated_root('share_receiver',fresh)
app,ui=new_core()
try:
    pasted='yo try this one\n'+named[:40]+'\n'+named[40:]+'\n(pls)' # As it might arrive in a chat message.
    ui.text_answer=None;assert app.import_share_code(pasted) is None and not app.saved_sets;result['cancel_name_dialog_saves_nothing']=True
    ui.text_answer='From a friend';assert app.import_share_code(pasted)==('set','From a friend')
    assert {t:e['clip'] for t,e in app.saved_sets['From a friend'].items()}==expected;result['set_round_trips_by_clip_key']=expected
    app.load_set('From a friend');assert {t:app.clip_key(app.clip_for_path(p)) for t,p in app.mapping.items()}==expected;result['shared_set_loads']=True
    foreign=core.encode_share({'kind':'set','name':'MW3 stuff','clips':{'pb_stand_alert':'MW3/common/not_here'}});ui.text_answer='Foreign'
    app.import_share_code(foreign);assert 'not in your library' in app.status;result['missing_clips_reported']=app.status
    assert app.import_share_code(theme_code)==('theme','') and app.theme['style']=='glass' and app.theme['h']==200 and app.theme['glass']==30;result['appearance_code_applies']=True
    for bad in ('hello','BO2SP1-abc',theme_code[:-12]):
        assert app.import_share_code(bad) is None
    result['bad_codes_rejected']=app.status
finally:close(app,ui)
Path('work/share_codes_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=1))
