"""Volume-side review helpers for the Visual Learning cloud renders (never trust the driver log counters).
  python3 cloud_tools.py frames <project>                 # frames on the volume per shot vs expected (24 fps), from shotlist
  python3 cloud_tools.py frames <project> s01 s02          # only these shots
  python3 cloud_tools.py log <project> <name>              # print /vol/<project>/<name>  e.g. render_test1.log
  python3 cloud_tools.py pull <project> <out.png> s01:1,4 s07:2   # pull those frames (1-based) and tile a review sheet
  python3 cloud_tools.py sample <project> <out.png> [n_per_shot]  # one (or n) evenly spaced frames of EVERY 3d shot that has frames
  python3 cloud_tools.py segs <project> <dir>              # download segments and ffprobe each (durations, frame counts)
"""
import sys, os, io, re, json, subprocess
PIPE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPE)
import modal
from PIL import Image, ImageDraw, ImageFont

cmd, proj = sys.argv[1], sys.argv[2]
os.environ['VL_PROJECT'] = proj; os.environ['VL_FPS_ALL'] = '24'
vol = modal.Volume.from_name('vl-plates')
FONT = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 18)

def expected():
    from shotlist import SHOTS, n_render_frames
    return [(s['id'], n_render_frames(s), s) for s in SHOTS if s['mode'] == '3d']

def have_frames(shots=None):
    """{sid: sorted frame numbers on the volume}"""
    out = {}
    try:
        entries = vol.listdir(f'/{proj}/plates', recursive=True)
    except Exception as e:
        print('listdir failed:', e); return out
    for ent in entries:
        m = re.match(rf'{proj}/plates/([^/]+)/f_(\d+)\.png$', ent.path)
        if m and (not shots or m.group(1) in shots): out.setdefault(m.group(1), []).append(int(m.group(2)))
    for k in out: out[k].sort()
    return out

def tile(frames, out, cols=4, size=(640, 360)):
    n = len(frames); rows = (n + cols - 1) // cols
    M = Image.new('RGB', (cols * size[0], rows * size[1]), (30, 30, 30))
    for i, (cap, im) in enumerate(frames):
        im = im.convert('RGB').resize(size, Image.LANCZOS); ImageDraw.Draw(im).text((8, size[1] - 26), cap, font=FONT, fill=(255, 255, 0))
        M.paste(im, ((i % cols) * size[0], (i // cols) * size[1]))
    M.save(out); print('wrote', out, M.size, n, 'tiles')

def read_png(path):
    data = b''.join(vol.read_file(path))
    return Image.open(io.BytesIO(data))

if cmd == 'frames':
    only = sys.argv[3:] or None
    have = have_frames(set(only) if only else None); tot_have = tot_exp = 0; missing = []
    for sid, nf, s in expected():
        if only and sid not in only: continue
        h = have.get(sid, []); tot_have += len(h); tot_exp += nf
        gaps = nf - len(set(k for k in h if 1 <= k <= nf))
        flag = '' if gaps == 0 else f'  MISSING {gaps}'
        print(f'{sid} {s["builder"]:<24} {len(h):5d}/{nf:<5d}{flag}')
        if gaps: missing.append(sid)
    print(f'TOTAL {tot_have}/{tot_exp} frames ({100.0*tot_have/max(1,tot_exp):.1f}%), shots incomplete: {len(missing)} {missing[:20]}')
elif cmd == 'log':
    print(b''.join(vol.read_file(f'/{proj}/{sys.argv[3]}')).decode(errors='replace'))
elif cmd == 'pull':
    out = sys.argv[3]; frames = []
    for spec in sys.argv[4:]:
        sid, ks = spec.split(':')
        for k in ks.split(','):
            k = int(k); p = f'/{proj}/plates/{sid}/f_{k:04d}.png'
            try: frames.append((f'{sid} f{k}', read_png(p)))
            except Exception as e: print('missing', p, e)
    tile(frames, out)
elif cmd == 'sample':
    out = sys.argv[3]; n = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    have = have_frames(); frames = []
    for sid, nf, s in expected():
        h = have.get(sid, [])
        if not h: print('no frames yet', sid); continue
        picks = [h[int(round(i * (len(h) - 1) / max(1, n - 1)))] for i in range(n)] if n > 1 else [h[len(h) // 2]]
        for k in sorted(set(picks)):
            try: frames.append((f'{sid} {s["builder"]} f{k}/{nf} t={s["t0"] + (k - 1) / 24:.1f}', read_png(f'/{proj}/plates/{sid}/f_{k:04d}.png')))
            except Exception as e: print('fail', sid, k, e)
    tile(frames, out, cols=6 if n == 1 else 4, size=(480, 270) if n == 1 else (640, 360))
elif cmd == 'segs':
    d = sys.argv[3]; os.makedirs(d, exist_ok=True)
    subprocess.run(['python3', '-m', 'modal', 'volume', 'get', 'vl-plates', f'{proj}/segments', d, '--force'], check=True)
    segs = sorted(f for f in os.listdir(os.path.join(d, 'segments')) if f.endswith('.mp4'))
    tot = 0.0
    for f in segs:
        p = os.path.join(d, 'segments', f)
        r = subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries', 'stream=nb_read_frames,duration', '-of', 'csv=p=0', p], capture_output=True, text=True)
        print(f, r.stdout.strip(), os.path.getsize(p) // 1024, 'KB');
        try: tot += float(r.stdout.strip().split(',')[0])
        except Exception: pass
    print('segments', len(segs), 'total duration', round(tot, 2))
