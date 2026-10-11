"""Render the Qt window offscreen to PNGs for visual review. No game writes.

Usage: python work/ui_snapshot.py [output folder]

Uses an isolated copy of the release profile/catalog (work/ui_snapshot_test),
disables the importer, lets the read-only observer run briefly, then saves one
PNG per tab.
"""
import os,sys,json,time
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen');os.environ.setdefault('QT_QPA_FONTDIR',r'C:\Windows\Fonts')
sys.path.insert(0,'work/porter')
import core
from PySide6 import QtWidgets,QtCore
out=Path(sys.argv[1] if len(sys.argv)>1 else 'work/ui_snapshots');out.mkdir(parents=True,exist_ok=True)
final=Path('outputs/BO2SPAnims').resolve();root=Path('work/ui_snapshot_test').resolve();(root/'state').mkdir(parents=True,exist_ok=True);(root/'library').mkdir(exist_ok=True)
profile=json.loads((final/'profile.json').read_text());profile['mapping']={n:str(final/p) for n,p in profile['mapping'].items()}
(root/'profile.json').write_text(json.dumps(profile));catalog=json.loads((final/'library/catalog.json').read_text())
for item in catalog:item['path']=str(final/item['path'])
(root/'library/catalog.json').write_text(json.dumps(catalog));core.ROOT=root;core.STATE=root/'state'
core.Core.start=lambda self:self.set_status('(importer disabled in snapshot mode)')
import bo2spanims
app=QtWidgets.QApplication(sys.argv);window=bo2spanims.Window();window.resize(1240,860);window.show()
end=time.monotonic()+2.5
while time.monotonic()<end:app.processEvents();time.sleep(0.02)
for i in range(window.tabs.count()):
    window.tabs.setCurrentIndex(i);app.processEvents()
    name=window.tabs.tabText(i).split()[0].strip('★ ').lower() or 'favorites'
    window.grab().save(str(out/f'{i:02d}_{name}.png'))
window.close()
while not window.core.finished():app.processEvents();time.sleep(0.05)
print('saved',sorted(p.name for p in out.glob('*.png')))
