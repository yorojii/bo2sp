"""Extract the MW3 campaign/Spec Ops actor library with the tool's own library build.

Usage: python work/extract_mw3_library.py "<MW3 folder>"

Runs library.index_libraries with only the MW3 folder set (every other game is skipped), so this
exercises exactly what Settings › Build libraries does. Clips go to work/catalog/mw3/; the
deduplicated catalog is written to work/mw3_catalog.json for add_bo2sp_to_release.py mw3.
"""
import json,sys,time
from pathlib import Path
WORK=Path(__file__).resolve().parent
sys.path.insert(0,str(WORK/'porter'))
from library import index_libraries
folder=sys.argv[1];started=time.monotonic()
result=index_libraries({'mw3':folder},WORK/'catalog/mw3',WORK.parent/'outputs/BO2SP/tools/Unlinker.exe',print,
                       progress=lambda done,total,text:print(f'{done}/{total} {text}',flush=True) if done%10==0 else None)
catalog,built,skipped=result
assert built==['MW3 Actors'],built
(WORK/'mw3_catalog.json').write_text(json.dumps(catalog))
print(json.dumps({'clips':len(catalog),'zones':len({x['zone'] for x in catalog}),'seconds':round(time.monotonic()-started,1)}))
