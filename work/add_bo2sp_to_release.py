"""Append an extracted BO2 library to the release's packaged library.

Usage: python work/add_bo2sp_to_release.py [sp|zombies]

Reads work/bo2<kind>_catalog.json (from extract_bo2sp_library.py). Copies each clip
to outputs/<release>/library/clips/ using numbers after the existing ones, and
appends catalog entries with release-relative paths. Existing entries and
their numbered files are never renumbered or rewritten, so saved mappings keep
pointing at the same clips. Refuses to add a game twice; the user profile is not
read or written.
"""
import json,shutil,sys
from pathlib import Path
WORK=Path(__file__).resolve().parent
kind=sys.argv[1] if len(sys.argv)>1 else 'sp'
release=WORK.parent/'outputs/Yoroji Tool'
catalog_path=release/'library/catalog.json'
catalog=json.loads(catalog_path.read_text())
source=json.loads((WORK/f'bo2{kind}_catalog.json').read_text());game=source[0]['game']
if any(item['game']==game for item in catalog):sys.exit(f'The release already contains {game} clips; nothing changed.')
start=1+max(int(Path(item['path']).stem) for item in catalog)
added=[]
for offset,item in enumerate(source):
    name=f'{start+offset:05d}.xanim';shutil.copy2(item['path'],release/'library/clips'/name)
    added.append({**item,'path':'library\\clips\\'+name})
catalog_path.write_text(json.dumps(catalog+added,separators=(',',':')))
print(json.dumps({'existing':len(catalog),'added':len(added),'first':added[0]['path'] if added else None,'last':added[-1]['path'] if added else None}))
