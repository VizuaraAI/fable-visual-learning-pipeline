"""Contact sheet of a finished master (originals have no reference video to compare against).
python3 master_sheet.py <master.mp4> <out.png> [n_tiles]   evenly spaced frames, 4 columns, 640x360, timestamps burned in."""
import sys, subprocess, os, tempfile
from PIL import Image, ImageDraw, ImageFont
src, out = sys.argv[1], sys.argv[2]; n = int(sys.argv[3]) if len(sys.argv) > 3 else 24
dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout.strip())
ts = [round(2 + (dur - 6) * i / (n - 1), 2) for i in range(n)]
f = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 18); tmp = tempfile.mkdtemp(); tiles = []
for t in ts:
    p = os.path.join(tmp, f'{t}.png'); subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t), '-i', src, '-frames:v', '1', p])
    im = Image.open(p).convert('RGB').resize((640, 360)); ImageDraw.Draw(im).text((8, 334), f't={t:.0f}s  ({int(t//60):02d}:{int(t%60):02d})', font=f, fill=(255, 255, 0)); tiles.append(im)
cols = 4; rows = (n + cols - 1) // cols; M = Image.new('RGB', (cols * 640, rows * 360), (40, 40, 40))
for i, im in enumerate(tiles): M.paste(im, ((i % cols) * 640, (i // cols) * 360))
M.save(out); print('wrote', out, M.size, 'duration', dur)
