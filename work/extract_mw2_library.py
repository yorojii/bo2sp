import sys,json,hashlib,zlib
from pathlib import Path
sys.path.insert(0,'work/porter')
from mw2_assets import extract_fastfile
root=Path(r'D:\SteamLibrary\steamapps\common\Call of Duty Modern Warfare 2\zone\english')
catalog=json.loads(Path('work/mw2_catalog.json').read_text());seen={}
for item in catalog:
    p=Path(item['path']);data=p.read_bytes()
    if not data.startswith(b'YANIM\x01'):data=b'YANIM\x01'+zlib.compress(data,6);p.write_bytes(data)
    seen[(item['name'],hashlib.sha256(data).digest())]=item
files=[p for p in sorted(root.glob('*.ff')) if p.stat().st_size>20_000_000 and not p.name.startswith(('mp_','localized_','code_','ui','dlc')) and p.name not in ('common.ff','common_mp.ff','iw4_credits.ff')]
skipped={}
for i,ff in enumerate(files):
    try:
        clips,errors=extract_fastfile(ff,Path('work/catalog/mw2')/ff.stem)
        if errors:skipped[ff.stem]=errors
        for item in clips:
            key=(item['name'],hashlib.sha256(Path(item['path']).read_bytes()).digest())
            if key not in seen:seen[key]=item;catalog.append(item)
    except (ValueError,zlib.error) as e:skipped[ff.stem]=str(e)
    print(f'{i+1}/{len(files)} {ff.stem}: {len(catalog)} unique verified actor clips',flush=True)
    Path('work/mw2_catalog.json').write_text(json.dumps(catalog,indent=2))
    Path('work/mw2_extraction_skips.json').write_text(json.dumps(skipped,indent=2))
