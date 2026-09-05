"""Side-by-side sheet: reference frame (left) vs recreation frame (right) at the same timestamps.
python3 compare.py <reference.mp4> <recreation.mp4> <out.png> [t1 t2 ...]"""
import sys, subprocess, os, tempfile
from PIL import Image, ImageDraw, ImageFont
ref, rec, out = sys.argv[1:4]
ts = [float(t) for t in sys.argv[4:]] or [3, 8, 21, 50, 111, 140, 190, 216, 240, 268, 333, 396, 440, 500, 528, 560, 604, 642, 700, 745, 766, 790]
f = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 18)
tmp = tempfile.mkdtemp(); rows = []
for t in ts:
    pair = []
    for src, tag in ((ref, 'reference'), (rec, 'recreation')):
        p = os.path.join(tmp, f'{tag}_{t}.png'); subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t), '-i', src, '-frames:v', '1', p])
        im = Image.open(p).convert('RGB').resize((640, 360)); ImageDraw.Draw(im).text((8, 334), f'{tag}  t={t:.0f}s', font=f, fill=(255, 255, 0)); pair.append(im)
    rows.append(pair)
cols = 2; per_row = 2  # two timestamp pairs per row -> 4 tiles wide
n = len(rows); R = (n + per_row - 1) // per_row
M = Image.new('RGB', (per_row * 2 * 640, R * 360), (40, 40, 40))
for i, (a, b) in enumerate(rows):
    x = (i % per_row) * 1280; y = (i // per_row) * 360; M.paste(a, (x, y)); M.paste(b, (x + 640, y))
M.save(out); print('wrote', out, M.size)
