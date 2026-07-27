#!/usr/bin/env python3
"""CI step: decode images-src/*.b64 into images/, then generate styled
placeholders for any recipe (and the cover) still missing an image file.

A photo arrives either as images-src/NAME.b64, or split across
images-src/NAME.b64.part1, .part2, ... which are joined in numeric order
(large photos can exceed a single upload's size limit). If both a whole
.b64 and loose .partN files exist for the same photo, the whole file wins
and the parts are ignored — never mixed together.
"""
import base64, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMG, SRC = ROOT / 'images', ROOT / 'images-src'
IMG.mkdir(exist_ok=True)

# 1. Decode uploaded photos (images-src/NNN-slug.jpg[.b64|.b64.partN] -> images/NNN-slug.jpg)
groups = {}
for f in sorted(SRC.iterdir()) if SRC.exists() else []:
    if f.name.endswith('.b64'):
        groups.setdefault(f.name[:-4], {})[0] = f
    else:
        m = re.match(r'^(.+)\.b64\.part(\d+)$', f.name)
        if m:
            groups.setdefault(m.group(1), {})[int(m.group(2))] = f

for name, parts in sorted(groups.items()):
    if 0 in parts and len(parts) > 1:
        print(f'{name}: whole .b64 present, ignoring {len(parts) - 1} loose part file(s)')
        parts = {0: parts[0]}
    text = ''.join(parts[k].read_text().strip() for k in sorted(parts))
    data = base64.b64decode(text.encode(), validate=False)
    (IMG / name).write_bytes(data)
    print(f'decoded {name} from {len(parts)} part(s) -> images/{name} ({len(data)} bytes)')

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
