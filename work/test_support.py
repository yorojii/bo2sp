"""Shared helpers for tests that drive core.Core without a window. No game writes by themselves.

isolated_root(name, edit=None) copies the release profile and catalog into work/<name>
(optionally editing the profile dict first) and points core at it. FakeUI records what
the core asks of a front end; pump() runs callbacks posted from worker threads.
"""
import json,sys,time
from pathlib import Path
sys.path.insert(0,'work/porter')
import core

FINAL=Path('outputs/BO2SPAnims').resolve()

def isolated_root(name,edit=None):
    root=Path('work',name).resolve();(root/'state').mkdir(parents=True,exist_ok=True);(root/'library').mkdir(exist_ok=True)
    profile=json.loads((FINAL/'profile.json').read_text());profile['mapping']={n:str(FINAL/p) for n,p in profile['mapping'].items()}
    if edit:edit(profile)
    (root/'profile.json').write_text(json.dumps(profile));catalog=json.loads((FINAL/'library/catalog.json').read_text())
    for item in catalog:item['path']=str(FINAL/item['path'])
    (root/'library/catalog.json').write_text(json.dumps(catalog));core.ROOT=root;core.STATE=root/'state'
    return root

class FakeUI:
    def __init__(self):self.queue=[];self.logs=[];self.messages=[];self.fields=set();self.text_answer=None;self.confirm_answer=True;self.file_answer=None
    def post(self,fn):self.queue.append(fn)
    def pump(self,seconds=0):
        end=time.monotonic()+seconds
        while True:
            while self.queue:self.queue.pop(0)()
            if time.monotonic()>=end:break
            time.sleep(0.02)
    def changed(self,*fields):self.fields.update(fields)
    def append_log(self,text):self.logs.append(text)
    def confirm(self,title,text):return self.confirm_answer
    def ask_text(self,title,prompt,initial):return self.text_answer
    def message(self,kind,title,text):self.messages.append((kind,title,text))
    def ask_file(self,title):return self.file_answer
    def focus_neutral(self):pass

def new_core(ui=None,start=None):
    """A Core whose importer never starts (start() is replaced) unless start is given."""
    ui=ui or FakeUI();app=core.Core(ui);app.start=start or (lambda:None);return app,ui

def close(app,ui):
    app.close();end=time.monotonic()+10
    while not app.finished() and time.monotonic()<end:ui.pump(0.05)
    assert app.finished(),'core threads did not stop'
