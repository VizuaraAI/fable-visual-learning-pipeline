"""Compositor: plates + UI events -> final frames streamed into x264. Works at any VL_SCALE (1.0 = 720p, 1.5 = 1080p).
python3 overlay.py <plates_root> <out_dir> [chunks] [chunk_index]"""
import sys, os, json, math, glob
from PIL import Image, ImageDraw, ImageFilter
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shotlist import SHOTS, FPS, TOTAL, shot_at, n_render_frames
import ui, timeline
from ui import W, H, SC, s, font, rgba, WHITE

PLATES = None
CACHE = {}
def plate_path(spec, k24):
    sid = spec['id']; d24 = os.path.join(PLATES, sid, 'f24')
    if os.path.isdir(d24):
        files = CACHE.get(sid)
        if files is None: files = sorted(glob.glob(os.path.join(d24, '*.png'))); CACHE[sid] = files
        if files: return files[min(k24, len(files) - 1)]
    nf = n_render_frames(spec); rf = min(nf, int(k24 * spec['rfps'] / FPS) + 1)
    return os.path.join(PLATES, sid, f'f_{rf:04d}.png')

def load_plate(spec, t):
    if spec['mode'] == '2d': return None
    k24 = int(round((t - spec['t0']) * FPS)); p = plate_path(spec, k24)
    if not os.path.exists(p):
        files = sorted(glob.glob(os.path.join(PLATES, spec['id'], 'f_*.png')))
        if not files: return None
        p = files[min(len(files) - 1, max(0, int(k24 * spec['rfps'] / FPS)))]
    im = Image.open(p).convert('RGBA')
    if im.size != (W, H): im = im.resize((W, H), Image.LANCZOS)
    return im

ANCH = {}
def anchors(spec, t):
    sid = spec['id']
    if sid not in ANCH:
        p = os.path.join(PLATES, sid, 'anchors.json'); ANCH[sid] = json.load(open(p)) if os.path.exists(p) else {}
    a = ANCH[sid]
    if not a: return {}
    nf = n_render_frames(spec); rf = min(nf, int((t - spec['t0']) * spec['rfps']) + 1)
    return a.get(str(rf)) or a.get(rf) or {}

def gradient_bg(top, bottom, radial=None):
    px = np.zeros((H, W, 4), dtype=np.uint8); ys = np.linspace(0, 1, H)[:, None]
    for c in range(3): px[:, :, c] = (top[c] + (bottom[c] - top[c]) * ys).astype(np.uint8)
    if radial:
        yy, xx = np.mgrid[0:H, 0:W]; d = np.hypot((xx - s(640)) / s(640), (yy - s(400)) / s(400)); v = np.clip(1 - d, 0, 1)[:, :, None]
        px[:, :, :3] = np.clip(px[:, :, :3] + (np.array(radial) * v), 0, 255).astype(np.uint8)
    px[:, :, 3] = 255
    return Image.fromarray(px, 'RGBA')

BG2D = {}
def background(spec, t):
    if spec['mode'] == '3d':
        im = load_plate(spec, t); return im if im is not None else Image.new('RGBA', (W, H), (10, 14, 24, 255))
    b = spec['builder']
    if b == 'card':
        key = ('card', spec.get('bg'))
        if key not in BG2D:
            bg = gradient_bg((10, 16, 30), (12, 20, 38), radial=(18, 26, 40)); src = spec.get('bg')
            if src:
                files = sorted(glob.glob(os.path.join(PLATES, src, 'f_*.png')))
                if files:
                    pl = Image.open(files[len(files) // 2]).convert('RGBA')
                    if pl.size != (W, H): pl = pl.resize((W, H), Image.LANCZOS)
                    pl = Image.blend(Image.new('RGBA', (W, H), (10, 16, 30, 255)), pl, 0.28); bg = Image.alpha_composite(bg, pl.filter(ImageFilter.GaussianBlur(s(1.5))))
            BG2D[key] = bg
        return BG2D[key].copy()
    if b == 'list':
        if 'list' not in BG2D: BG2D['list'] = gradient_bg((16, 32, 44), (10, 18, 28), radial=(10, 14, 16))
        return BG2D['list'].copy()
    if b == 'outro': return Image.new('RGBA', (W, H), (12, 18, 32, 255))
    if 'plain' not in BG2D: BG2D['plain'] = gradient_bg((10, 14, 26), (9, 12, 22), radial=(6, 8, 14))
    return BG2D['plain'].copy()

def glow_circle(img, x, y, r, color, text=None, size=16, alpha=255, ring=False):
    """Glowing token circle at (x, y) 720p-space with radius r (720p px)."""
    R = s(r); lay = Image.new('RGBA', (int(R * 6) + 4, int(R * 6) + 4), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); c = lay.width // 2
    d.ellipse((c - R * 1.6, c - R * 1.6, c + R * 1.6, c + R * 1.6), fill=rgba(color, int(alpha * 0.45)))
    lay = lay.filter(ImageFilter.GaussianBlur(R * 0.7)); d = ImageDraw.Draw(lay)
    if ring: d.ellipse((c - R, c - R, c + R, c + R), outline=rgba(color, alpha), width=max(2, s(3))); d.ellipse((c - R * 0.3, c - R * 0.3, c + R * 0.3, c + R * 0.3), fill=rgba(color, alpha))
    else: d.ellipse((c - R, c - R, c + R, c + R), fill=rgba(tuple(int(v * 0.55) for v in color), alpha), outline=rgba(color, alpha), width=max(1, s(2)))
    if text:
        f = font('bold', size); fs = font('bold', int(size * 0.62)); tw = ui.measure_sub(d, text, f, fs)
        ui.sub_text(d, c - tw / 2, c - f.size * 0.62, text, f, fs, rgba(WHITE, alpha))
    img.alpha_composite(lay, (int(s(x) - c), int(s(y) - c)))

def glow_line(img, p0, p1, color, alpha=255, wavy=True, width=3):
    """Wavy glowing bond between 720p-space points, drawn on a cropped layer."""
    (x0, y0), (x1, y1) = (s(p0[0]), s(p0[1])), (s(p1[0]), s(p1[1])); L = math.hypot(x1 - x0, y1 - y0)
    if L < 1: return
    m = s(18); bx0, by0 = int(min(x0, x1) - m), int(min(y0, y1) - m); bw, bh = int(abs(x1 - x0) + 2 * m), int(abs(y1 - y0) + 2 * m)
    lay = Image.new('RGBA', (bw, bh), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); n = max(2, int(L / 4)); pts = []
    for i in range(n + 1):
        u = i / n; x = x0 + (x1 - x0) * u; y = y0 + (y1 - y0) * u
        if wavy and 0.08 < u < 0.92:
            nx, ny = -(y1 - y0) / L, (x1 - x0) / L; a = s(5) * math.sin(u * L / (3.2 * SC)); x += nx * a; y += ny * a
        pts.append((x - bx0, y - by0))
    d.line(pts, fill=rgba(color, int(alpha * 0.5)), width=s(width + 6)); lay = lay.filter(ImageFilter.GaussianBlur(s(4))); d = ImageDraw.Draw(lay)
    d.line(pts, fill=rgba(color, alpha), width=max(1, s(width)))
    img.alpha_composite(lay, (bx0, by0))

def lerp(a, b, u): return a + (b - a) * u
def smooth01(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)

def draw_molecules(img, e, t, a):
    G = (110, 255, 120); B = (90, 190, 255)
    C = (330, 360); Hl = (120, 360); Ht = (330, 180); Hb = (330, 568); Hr0 = (540, 360); Cl0 = (820, 360); Cl1 = (1128, 360)
    u_break = smooth01((t - e['t_break']) / 1.5); u_move = smooth01((t - e['t_move0']) / (e['t_move1'] - e['t_move0']))
    Hr = (lerp(Hr0[0], 900, u_move), 360); ClA = (lerp(Cl0[0] - 40 * u_break, 540, u_move), 360); ClB = (Cl1[0] + 20 * u_break, 360)
    for h in (Hl, Ht, Hb): glow_line(img, C, h, G, a)
    if u_move < 0.5: glow_line(img, C, Hr, G, a)
    else: glow_line(img, C, ClA, B, a)
    if u_break < 0.99: glow_line(img, ClA, ClB, B, int(a * (1 - u_break)))
    if u_move > 0.5: glow_line(img, Hr, ClB, B, a)
    glow_circle(img, *C, 22, G, 'C', 20, a)
    for h in (Hl, Ht, Hb, Hr): glow_circle(img, *h, 18, G, 'H', 17, a)
    glow_circle(img, *ClA, 20, B, 'Cl', 17, a); glow_circle(img, *ClB, 20, B, 'Cl', 17, a)

def cyan_arrow(img, x, y, alpha):
    CY = (80, 225, 255); lay = Image.new('RGBA', (s(80), s(30)), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); w = max(2, s(4))
    d.line((s(4), s(15), s(64), s(15)), fill=rgba(CY, alpha), width=w); d.line((s(64), s(15), s(52), s(7)), fill=rgba(CY, alpha), width=w); d.line((s(64), s(15), s(52), s(23)), fill=rgba(CY, alpha), width=w)
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(s(1))), (s(x) - s(4), s(y) - s(15)))

def draw_disp_eq(img, e, t, a):
    Fe = (215, 130, 80); Cu = (90, 170, 255); SO = (235, 90, 205); CY = (80, 225, 255)
    def row(y, fe, cu, so, fe2, so2, cu2, plus1, arr, plus2, alpha):
        glow_circle(img, fe, y, 20, Fe, 'Fe', 15, alpha); ui.plain_text(img, plus1 - 10, y - 14, '+', 26, alpha, color=CY)
        glow_circle(img, cu, y, 18, Cu, 'Cu', 14, alpha); glow_circle(img, so, y, 20, SO, 'SO_4', 14, alpha); cyan_arrow(img, arr, y, alpha)
        glow_circle(img, fe2, y, 20, Fe, 'Fe', 15, alpha); glow_circle(img, so2, y, 20, SO, 'SO_4', 14, alpha); ui.plain_text(img, plus2 - 10, y - 14, '+', 26, alpha, color=CY); glow_circle(img, cu2, y, 18, Cu, 'Cu', 14, alpha)
    row(232, 300, 430, 478, 700, 748, 860, 365, 560, 810, a)
    if e['t_row2'] <= t < e['t_row2_end']:
        a2 = int(a * min(1, (t - e['t_row2']) / 0.4) * min(1, (e['t_row2_end'] - t) / 0.4))
        y = 488; up = smooth01((t - e['t_pop']) / 1.2); uj = smooth01((t - e['t_join0']) / (e['t_join1'] - e['t_join0']))
        fe_x = lerp(430, 560, uj); cu_x = lerp(560, 700, uj); cu_y = y - 55 * up * (1 - uj) if uj < 1 else y; plus_x = lerp(500, 640, uj)
        glow_circle(img, fe_x, y, 20, Fe, 'Fe', 15, a2); glow_circle(img, 608, y, 20, SO, 'SO_4', 14, a2)
        glow_circle(img, cu_x, cu_y, 18, Cu, 'Cu', 14, a2); ui.plain_text(img, plus_x - 10, y - 14, '+', 26, a2, color=CY)

def draw_event(img, e, t, spec):
    k = e['kind']; a = int(255 * ui.fade_io(t, e['t0'], e['t1'], 0.3))
    if a <= 0: return
    if k == 'label': ui.section_label(img, e['text'], alpha=int(a * e.get('alpha', 1.0)))
    elif k == 'title': ui.title_pill(img, e['text'], y=e['y'], size=e['size'], alpha=a)
    elif k == 'table': ui.topic_table(img, e['topics'], alpha=a, y=200, h=230)
    elif k == 'card': ui.section_card(img, e['text'], alpha=a)
    elif k == 'rect':
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); x0, y0, x1, y1 = e['box']; u = smooth01((t - e['t0']) / 1.2)
        cx = (x0 + x1) / 2; w = (x1 - x0) * u
        d.rounded_rectangle((s(cx - w / 2), s(y0), s(cx + w / 2), s(y1)), radius=s(3), fill=rgba((40, 120, 240), int(a * 0.55)), outline=rgba((90, 170, 255), a), width=max(1, s(1))); img.alpha_composite(lay)
    elif k == 'callout': ui.callout(img, e['x'], e['y'], e['text'], alpha=a, center=e.get('center', False))
    elif k == 'pill': ui.pill(img, e['x'], e['y'], e['text'], size=e.get('size', 15), pad=(14, 5), alpha=int(a * e.get('alpha', 1.0)), center=e.get('center', False), min_w=e.get('min_w', 0))
    elif k == 'text_eq':
        d = ImageDraw.Draw(img); f = font('bold', 24); parts = [p for p in e['parts'] if t >= p[1]]
        total = sum(ui.text_size(d, p[0], f)[0] + s(14) for p in parts) - s(14); x = s(e['cx']) - total / 2; Y = s(e['y'])
        for txt, ts in parts:
            aa = int(a * ui.fade_in(t, ts, 0.4)); col = (255, 90, 50) if txt == '→' else WHITE
            if txt == '→':
                d.line((x, Y + s(14), x + s(26), Y + s(14)), fill=rgba(col, aa), width=max(1, s(3))); d.line((x + s(26), Y + s(14), x + s(17), Y + s(7)), fill=rgba(col, aa), width=max(1, s(3))); d.line((x + s(26), Y + s(14), x + s(17), Y + s(21)), fill=rgba(col, aa), width=max(1, s(3)))
            else: d.text((x, Y), txt, font=f, fill=rgba(col, aa))
            x += ui.text_size(d, txt, f)[0] + s(14)
    elif k == 'list':
        for (txt, ts), y in zip(e['items'], e['ys']):
            if t >= ts: ui.pill(img, e['cx'], y, txt, size=15, pad=(14, 6), alpha=int(a * ui.fade_in(t, ts, 0.3)), center=True)
    elif k == 'eqpill':
        txt = ''.join(p[0] for p in e['parts'] if t >= p[1])
        if txt: ui.pill(img, e['x'], e['y'], txt, size=15, pad=(16, 6), alpha=a, center=e.get('center', False))
    elif k == 'equation':
        n = sum(1 for ts in e['times'] if t >= ts)
        if n == 0: return
        br = e.get('bracket'); arrows = e.get('arrows') or {}
        d = ImageDraw.Draw(img); f = font('bold', 16); fs = font('bold', 10)
        widths = [(ui.text_size(d, '+', f)[0] + s(8)) if tk in ('+', '→') else (ui.measure_sub(d, tk, f, fs) + s(26)) for tk in e['tokens']]
        total = sum(widths) + s(14) * (len(widths) - 1); cx = e['x'] + total / (2 * SC)
        ui.equation(img, cx, e['y'], e['tokens'], size=16, alpha=a, n_visible=n, bracket=(br[0] if br and t >= br[1] else None), arrows=[i for i, ts in arrows.items() if t >= ts])
    elif k == 'defbox':
        w0, w1 = e['t_words']; nw = len(e['text'].split()); n = int(nw * max(0.0, min(1.0, (t - w0) / (w1 - w0))))
        ui.definition_box(img, e['text'], n_words=n, y=e['y'], alpha=a)
    elif k == 'arrow':
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); x, y = e['x'], e['y']; sg = 1 if e['dir'] == 'left' else -1
        d.polygon([(s(x), s(y)), (s(x + sg * 22), s(y - 9)), (s(x + sg * 18), s(y)), (s(x + sg * 22), s(y + 9))], fill=rgba(WHITE, a)); d.line((s(x + sg * 18), s(y), s(x + sg * 40), s(y)), fill=rgba(WHITE, a), width=max(2, s(4))); img.alpha_composite(lay)
    elif k == 'anchor_text':
        for name, txt in e['names'].items():
            p = anchors(spec, t).get(name)
            if p: ui.plain_text(img, p[0], p[1] - 10, txt, size=17, alpha=a, center=True)
    elif k == 'anchor_particles':
        for name, p in anchors(spec, t).items():
            if name.startswith('Hp'): glow_circle(img, p[0], p[1], 9, (255, 80, 80), 'H', 11, a)
            elif name.startswith('Op'): glow_circle(img, p[0], p[1], 8, (110, 170, 255), None, 10, a, ring=True)
            elif name.startswith('Rp'): glow_circle(img, p[0], p[1], 5, (255, 170, 150), None, 8, int(a * 0.85), ring=True)
    elif k == 'molecules': draw_molecules(img, e, t, a)
    elif k == 'disp_eq': draw_disp_eq(img, e, t, a)
    elif k == 'listbg': pass
    elif k == 'outro': ui.outro(img, t - e['t0'], alpha=a)
    else:
        ext = _project_ext()
        if ext is not None: ext.draw_extra(img, e, t, spec, ui, dict(glow_circle=glow_circle, glow_line=glow_line, anchors=anchors, lerp=lerp, smooth01=smooth01, alpha=a, s=s, SC=SC, font=font, rgba=rgba))

_EXT = [None, False]
def _project_ext():
    if not _EXT[1]:
        _EXT[1] = True
        try:
            import importlib; _EXT[0] = importlib.import_module(f"projects.{os.environ.get('VL_PROJECT', 'chem')}.overlay_ext")
        except Exception: _EXT[0] = None
    return _EXT[0]

def render_frame(t):
    spec = shot_at(t); img = background(spec, t)
    for e in timeline.events_at(t):
        try: draw_event(img, e, t, spec)
        except Exception as ex: print('event error', e['kind'], ex)
    if spec['builder'] != 'outro': ui.logo(img, alpha=255 if t > 0.3 else int(255 * t / 0.3))
    return img.convert('RGB')

def encode_range(k0, k1, seg, crf=17):
    import subprocess
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', str(crf), '-pix_fmt', 'yuv420p', seg], stdin=subprocess.PIPE)
    for k in range(k0, k1):
        p.stdin.write(render_frame(k / FPS).tobytes())
        if (k - k0) % 240 == 0: print(f'{os.path.basename(seg)}: {k - k0}/{k1 - k0}', flush=True)
    p.stdin.close(); p.wait(); return seg

def main():
    global PLATES
    PLATES, out = sys.argv[1], sys.argv[2]; chunks = int(sys.argv[3]) if len(sys.argv) > 3 else 1; ci = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    os.makedirs(out, exist_ok=True); N = int(round(TOTAL * FPS)); per = math.ceil(N / chunks); k0, k1 = ci * per, min(N, (ci + 1) * per)
    print('done', encode_range(k0, k1, os.path.join(out, f'seg_{ci:02d}.mp4')))

if __name__ == '__main__': main()
