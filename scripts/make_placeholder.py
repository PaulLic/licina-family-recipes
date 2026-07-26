#!/usr/bin/env python3
"""Generate a styled placeholder image for a recipe awaiting a real photo.
Usage: make_placeholder.py "Recipe Title" output.png [--cover]
House style: warm cream, dark brown serif, thin double frame."""
import sys
from PIL import Image, ImageDraw, ImageFont

CREAM, BROWN, ACCENT = (245,239,230), (62,39,35), (141,110,99)

def serif(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"):
        try: return ImageFont.truetype(p, size)
        except OSError: pass
    return ImageFont.load_default()

def wrap(d, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur+" "+w_).strip()
        if d.textlength(t, font=font) <= maxw: cur = t
        else: lines.append(cur); cur = w_
    lines.append(cur); return lines

def make(title, out, cover=False):
    W,H = (1200,1600) if cover else (1200,900)
    img = Image.new("RGB",(W,H),CREAM); d = ImageDraw.Draw(img)
    d.rectangle([40,40,W-40,H-40], outline=BROWN, width=3)
    d.rectangle([52,52,W-52,H-52], outline=ACCENT, width=1)
    big, small = serif(72 if cover else 64), serif(30)
    lines = wrap(d, title.upper(), big, W-240)
    lh = 90; ty = H/2 - lh*len(lines)/2 - 30
    for i,l in enumerate(lines):
        d.text((W/2, ty+i*lh), l, font=big, fill=BROWN, anchor="mm")
    y = ty + lh*len(lines) + 10
    d.line([W/2-80,y,W/2+80,y], fill=ACCENT, width=2)
    d.ellipse([W/2-5,y-5,W/2+5,y+5], fill=ACCENT)
    d.text((W/2, y+50), "photograph to come", font=small, fill=ACCENT, anchor="mm")
    img.save(out); print("wrote", out)

if __name__ == "__main__":
    make(sys.argv[1], sys.argv[2], "--cover" in sys.argv)
