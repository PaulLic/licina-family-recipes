#!/usr/bin/env python3
"""CI step: decode photo uploads, validate them, clean up, generate placeholders.

Guarantees (the site and book can never show a broken photo):
1. An upload (images-src/NAME.b64, or NAME.b64.part1..N joined in order) is
   decoded ONLY if the base64 is intact (clean alphabet, length % 4 == 0, all
   parts present) AND the decoded bytes open as a complete, readable image.
   Anything else is rejected with a warning — an existing good image is never
   overwritten by a bad upload.
2. Source files are one-shot: consumed or rejected, they are deleted either
   way, so stale uploads can't be re-decoded or collide with later ones.
3. Any existing image referenced by a recipe that no longer loads (corrupt)
   is removed, so a clean placeholder takes its place on the next build.
4. Orphaned images (referenced by no recipe and not the cover) are removed.
"""
import base64
import io
import pathlib
import re
import subprocess
import sys

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMG, SRC = ROOT / 'images', ROOT / 'images-src'
IMG.mkdir(exist_ok=True)

B64_CLEAN = re.compile(r'^[A-Za-z0-9+/]+={0,2}$')


def image_ok(data: bytes) -> bool:
    """True only if the bytes are a complete, fully decodable image."""
    try:
        im = Image.open(io.BytesIO(data))
        im.load()  # forces a full decode — catches truncated/garbled streams
        return True
    except Exception:
        return False


# ---- 1. Decode uploads --------------------------------------------------
groups = {}
for f in (sorted(SRC.iterdir()) if SRC.exists() else []):
    if f.name == '.gitkeep':
        continue
    if f.name.endswith('.b64'):
        groups.setdefault(f.name[:-4], {})[0] = f
    else:
        m = re.match(r'^(.+)\.b64\.part(\d+)$', f.name)
        if m:
            groups.setdefault(m.group(1), {})[int(m.group(2))] = f

for name, parts in sorted(groups.items()):
    all_files = list(parts.values())
    use = parts
    if 0 in parts and len(parts) > 1:
        print(f'{name}: whole .b64 present, ignoring loose part file(s)')
        use = {0: parts[0]}

    data, reason = None, None
    if 0 not in use:
        nums = sorted(use)
        missing = set(range(1, max(nums) + 1)) - set(nums)
        if missing:
            reason = f'missing part(s) {sorted(missing)}'
    if reason is None:
        # join, dropping ALL whitespace (line wraps etc.) before checking
        text = ''.join(''.join(use[k].read_text().split()) for k in sorted(use))
        if not B64_CLEAN.match(text) or len(text) % 4 != 0:
            reason = ('base64 is damaged (stray characters or misaligned length '
                      '— characters were likely lost in transit)')
    if reason is None:
        try:
            data = base64.b64decode(text.encode(), validate=True)
        except Exception as e:
            reason = f'base64 failed to decode ({e})'
    if reason is None and not image_ok(data):
        reason = 'decoded bytes are not a complete, readable image'

    if reason is None:
        (IMG / name).write_bytes(data)
        print(f'OK: images/{name} ({len(data)} bytes) from {len(use)} file(s)')
    else:
        print(f'::warning::{name}: upload REJECTED — {reason}. '
              f'The photo needs to be re-sent. Any existing image was kept.')

    for f in all_files:  # one-shot either way
        f.unlink()

# ---- 2. Collect recipe references; heal corrupt existing images ---------
referenced = set()
for md in sorted((ROOT / 'recipes').glob('*.md')):
    text = md.read_text(encoding='utf-8')
    m = re.search(r'^image: "?([^"\n]+)"?$', text, re.M)
    t = re.search(r'^title: "?([^"\n]+)"?$', text, re.M)
    if not m or not t:
        continue
    target = ROOT / m.group(1)
    referenced.add(target.name)
    if target.exists() and not image_ok(target.read_bytes()):
        print(f'::warning::images/{target.name} is corrupt — removed; '
              f'a placeholder will take its place until the photo is re-sent.')
        target.unlink()
    if not target.exists():
        subprocess.run([sys.executable, str(ROOT / 'scripts/make_placeholder.py'),
                        t.group(1), str(target)], check=True)

# ---- 3. Cover ------------------------------------------------------------
covers = [p for p in IMG.glob('cover.*') if p.suffix.lower() in ('.png', '.jpg', '.jpeg')]
for c in covers:
    if not image_ok(c.read_bytes()):
        print(f'::warning::{c.name} is corrupt — removed.')
        c.unlink()
covers = [p for p in IMG.glob('cover.*') if p.suffix.lower() in ('.png', '.jpg', '.jpeg')]
if not covers:
    subprocess.run([sys.executable, str(ROOT / 'scripts/make_placeholder.py'),
                    'The Licina Family Recipe Collection', str(IMG / 'cover.png'),
                    '--cover'], check=True)

# ---- 4. Remove orphans ----------------------------------------------------
for p in sorted(IMG.iterdir()):
    if p.suffix.lower() not in ('.png', '.jpg', '.jpeg'):
        continue
    if p.name in referenced or p.name.startswith('cover.'):
        continue
    print(f'removing orphaned images/{p.name} (no recipe references it)')
    p.unlink()

print('images ready')
