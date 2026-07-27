#!/usr/bin/env python3
"""CI step: decode images-src/*.b64 into images/, then generate styled
placeholders for any recipe (and the cover) still missing an image file."""
import base64, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMG, SRC = ROOT / 'images', ROOT / 'images-src'
IMG.mkdir(exist_ok=True)

# 1. Decode uploaded photos (images-src/NNN-slug.jpg.b64 -> images/NNN-slug.jpg)
for f in sorted(SRC.glob('*.b64')) if SRC.exists() else []:
    out = IMG / f.name[:-4]
    data = base64.b64decode(f.read_text().strip().encode(), validate=False)
    out.write_bytes(data)
    print(f'decoded {f.name} -> images/{out.name} ({len(data)} bytes)')

# 2. Placeholders for recipes with no image file
for md in sorted((ROOT / 'recipes').glob('*.md')):
    text = md.read_text(encoding='utf-8')
    m = re.search(r'^image: "?([^"\n]+)"?$', text, re.M)
    t = re.search(r'^title: "?([^"\n]+)"?$', text, re.M)
    if not m or not t:
        continue
    target = ROOT / m.group(1)
    if not target.exists():
        subprocess.run([sys.executable, str(ROOT / 'scripts/make_placeholder.py'),
                        t.group(1), str(target)], check=True)

# 3. Cover placeholder if missing entirely
if not any(IMG.glob('cover.*')):
    subprocess.run([sys.executable, str(ROOT / 'scripts/make_placeholder.py'),
                    'The Licina Family Recipe Collection', str(IMG / 'cover.png'), '--cover'], check=True)
print('images ready')
