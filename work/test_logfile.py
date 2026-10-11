"""Session log file: written, rotated, capped, redacted, and catches crashes. No game writes.
Writes work/logfile_validation.json.
"""
import json,os,threading,time
from pathlib import Path
from test_support import isolated_root,new_core,close
import logfile
result={}
root=isolated_root('logfile_test')
app,ui=new_core()
try:
    path=app.logfile.path;assert path.parent.name=='logs' and path.exists()
    app.log('hello from a worker');app.set_status('Testing status line');app.set_status('Testing status line')
    text=path.read_text(encoding='utf-8')
    assert 'BO2SPAnims session started' in text and 'version: source' in text and 'library clips:' in text
    assert 'hello from a worker' in text and text.count('status: Testing status line')==1;result['written_with_header_and_status']=True
    app.log('my folder is '+os.path.expanduser('~')+r'\Desktop and C:\Users\SomeoneElse\x')
    support=app.support_text();assert os.path.expanduser('~') not in support and r'%USERPROFILE%\Desktop' in support and r'C:\Users\<user>\x' in support
    assert support.startswith('BO2SPAnims support log') and 'hello from a worker' in support;result['support_text_redacted']=True
    logfile.install_crash_hooks()
    def boom():raise ValueError('test crash in a worker')
    t=threading.Thread(target=boom,name='Test worker');t.start();t.join()
    text=path.read_text(encoding='utf-8');assert 'error in Test worker' in text and 'ValueError: test crash in a worker' in text and 'Traceback' in text
    result['thread_crash_logged']=True
finally:close(app,ui)
first=path.read_text(encoding='utf-8')
app,ui=new_core()
try:
    old=app.logfile.old;assert old.read_text(encoding='utf-8')==first and 'hello from a worker' not in path.read_text(encoding='utf-8');result['previous_session_kept']=True
    logfile.MAX_BYTES=2000
    for i in range(200):app.log(f'line {i} '+'x'*40)
    text=path.read_text(encoding='utf-8');assert 'size limit reached' in text and 'line 199' not in text and len(text)<4000;result['size_capped']=True
finally:close(app,ui)
Path('work/logfile_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=1))
