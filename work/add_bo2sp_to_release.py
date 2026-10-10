"""Append the extracted BO2 SP library to the release's packaged library.

Usage: python work/add_bo2sp_to_release.py

Reads work/bo2sp_catalog.json (from extract_bo2sp_library.py). Copies each clip
to outputs/<release>/library/clips/ using numbers after the existing ones, and
appends catalog entries with release-relative paths. Existing entries and
their numbered files are never renumbered or rewritten, so saved mappings keep
pointing at the same clips. Refuses to run twice; the user profile is not read
or written.
"""
import json,shutil,sys
from pathlib import Path
WORK=Path(__file__).resolve().parent
release=WORK.parent/'outputs/Yoroji Tool'
catalog_path=release/'library/catalog.json'
catalog=json.loads(catalog_path.read_text())
if any(item['game']=='BO2 SP' for item in catalog):sys.exit('The release already contains BO2 SP clips; nothing changed.')
source=json.loads((WORK/'bo2sp_catalog.json').read_text())
start=1+max(int(Path(item['path']).stem) for item in catalog)
added=[]
for offset,item in enumerate(source):
    name=f'{start+offset:05d}.xanim';shutil.copy2(item['path'],release/'library/clips'/name)
    added.append({**item,'path':'library\\clips\\'+name})
catalog_path.write_text(json.dumps(catalog+added,separators=(',',':')))
print(json.dumps({'existing':len(catalog),'added':len(added),'first':added[0]['path'] if added else None,'last':added[-1]['path'] if added else None}))
