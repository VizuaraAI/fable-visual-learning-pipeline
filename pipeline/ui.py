"""Visual Learning 2D UI kit (PIL). Every on-screen text element of the reference.
All coordinates are given in the reference's 1280x720 space and scaled by SC (VL_SCALE, 1.5 for a 1080p master)."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math, os

SC = float(os.environ.get('VL_SCALE', '1.0'))
W, H = int(round(1280 * SC)), int(round(720 * SC))
def s(v): return int(round(v * SC))

_FONT_DIRS = ['/System/Library/Fonts/Supplemental/', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts/'), '/usr/share/fonts/truetype/liberation/', '/usr/share/fonts/truetype/liberation2/', '/usr/share/fonts/truetype/dejavu/']
_FONT_FILES = {'bold': ['Arial Bold.ttf', 'LiberationSans-Bold.ttf'], 'reg': ['Arial.ttf', 'LiberationSans-Regular.ttf'],
               'serifb': ['Times New Roman Bold.ttf', 'LiberationSerif-Bold.ttf'], 'serif': ['Times New Roman.ttf', 'LiberationSerif-Regular.ttf'],
               'uni': ['Arial Unicode.ttf', 'DejaVuSans-Bold.ttf', 'Arial Bold.ttf', 'LiberationSans-Bold.ttf']}
FONTS = {}
def font(name, size):
    key = (name, size)
    if key not in FONTS:
        for fn in _FONT_FILES[name]:            # file preference first, then directories (DejaVu must beat Liberation for 'uni')
            for d in _FONT_DIRS:
                pth = os.path.join(d, fn)
                if os.path.exists(pth):
                    FONTS[key] = ImageFont.truetype(pth, max(6, s(size))); break
            if key in FONTS: break
        else: FONTS[key] = ImageFont.load_default()
    return FONTS[key]

NAVY = (11, 26, 62); NAVY_B = (46, 110, 200); CYAN_B = (42, 183, 232)
PURPLE = (142, 47, 201); BLUE_BAR = (31, 111, 224); WHITE = (255, 255, 255)

def rgba(c, a): return (c[0], c[1], c[2], int(max(0, min(255, a))))
def layer(): return Image.new('RGBA', (W, H), (0, 0, 0, 0))
def text_size(d, txt, f):
    b = d.textbbox((0, 0), txt, font=f); return b[2] - b[0], b[3] - b[1]

def sub_text(d, x, y, txt, f, fsub, fill):
    """Draw text with _n subscripts ('H_2O' -> H₂O); returns end x. Coordinates already in output pixels."""
    import re
    parts = re.split(r'(_\d+|_\{[^}]*\})', txt); cx = x
    for p in parts:
        if not p: continue
        if p.startswith('_'):
            t = p[2:-1] if p.startswith('_{') else p[1:]
            d.text((cx, y + f.size * 0.42), t, font=fsub, fill=fill); cx += text_size(d, t, fsub)[0]
        else:
            d.text((cx, y), p, font=f, fill=fill); cx += text_size(d, p, f)[0]
    return cx

def measure_sub(d, txt, f, fsub):
    import re
    parts = re.split(r'(_\d+|_\{[^}]*\})', txt); w = 0
    for p in parts:
        if not p: continue
        if p.startswith('_'):
            t = p[2:-1] if p.startswith('_{') else p[1:]; w += text_size(d, t, fsub)[0]
        else: w += text_size(d, p, f)[0]
    return w

def pill(img, x, y, text, size=17, pad=(16, 7), extra_right=0, fill=NAVY, border=NAVY_B, bw=1, radius=3, alpha=255, fnt='bold', color=WHITE, min_w=0, center=False):
    """Navy label pill with a thin blue border. (x, y) in 720p space; centre if center=True. Returns the box in 720p space."""
    d = ImageDraw.Draw(img); f = font(fnt, size); fs = font(fnt, max(9, int(size * 0.62)))
    tw = measure_sub(d, text, f, fs); th = f.size
    w = max(s(min_w), tw + s(pad[0]) * 2 + s(extra_right)); h = th + s(pad[1]) * 2
    X, Y = s(x), s(y)
    if center: X, Y = X - w // 2, Y - h // 2
    ov = Image.new('RGBA', (w + 4, h + 4), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    od.rounded_rectangle((2, 2, w + 1, h + 1), radius=s(radius), fill=rgba(fill, alpha), outline=rgba(border, alpha), width=max(1, s(bw)))
    tx = 2 + s(pad[0]) if not center else 2 + (w - tw) // 2
    sub_text(od, tx, 2 + s(pad[1]) - f.size * 0.12, text, f, fs, rgba(color, alpha))
    img.alpha_composite(ov, (X - 2, Y - 2))
    return (X / SC, Y / SC, w / SC, h / SC)

def section_label(img, text, alpha=255):
    return pill(img, 16, 14, text, size=17, pad=(20, 6), extra_right=60, alpha=alpha)

def title_pill(img, text, cx=640, y=20, size=32, alpha=255):
    d = ImageDraw.Draw(img); f = font('bold', size); tw, th = text_size(d, text, f)
    w, h = tw + s(40), s(size + 22)
    ov = Image.new('RGBA', (w, h), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    od.rounded_rectangle((0, 0, w - 1, h - 1), radius=s(9), fill=rgba(PURPLE, alpha))
    od.text((s(20), s(8)), text, font=f, fill=rgba(WHITE, alpha))
    img.alpha_composite(ov, (int(s(cx) - w / 2), s(y)))

def topic_table(img, topics, x=110, y=210, w=1046, h=340, alpha=255, rows_visible=99):
    Wd, Hd = s(w), s(h)
    ov = Image.new('RGBA', (Wd, Hd), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    od.rounded_rectangle((0, 0, Wd - 1, Hd - 1), radius=s(8), fill=rgba((8, 34, 70), int(alpha * 0.93)), outline=rgba(CYAN_B, alpha), width=max(1, s(2)))
    fh = font('bold', 26); fr = font('bold', 20)
    od.text((s(36), s(26)), 'Topic includes', font=fh, fill=rgba(WHITE, alpha)); od.text((Wd - s(36) - text_size(od, 'Time line', fh)[0], s(26)), 'Time line', font=fh, fill=rgba(WHITE, alpha))
    for i, (name, tl) in enumerate(topics[:rows_visible]):
        yy = s(84 + i * 42)
        od.text((s(36), yy), name, font=fr, fill=rgba(WHITE, alpha)); od.text((Wd - s(36) - text_size(od, tl, fr)[0], yy + s(3)), tl, font=fr, fill=rgba(WHITE, alpha))
    img.alpha_composite(ov, (s(x), s(y)))

def section_card(img, text, alpha=255, y=300):
    d = ImageDraw.Draw(img); f = font('bold', 32); tw, th = text_size(d, text, f)
    w, h = max(s(600), tw + s(120)), s(92)
    ov = Image.new('RGBA', (w, h), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    od.rounded_rectangle((0, 0, w - 1, h - 1), radius=s(6), fill=rgba(BLUE_BAR, alpha))
    od.text(((w - tw) // 2, (h - th) // 2 - s(6)), text, font=f, fill=rgba(WHITE, alpha))
    img.alpha_composite(ov, (int(s(640) - w / 2), s(y)))

def definition_box(img, text, n_words=None, x=72, y=520, w=1136, h=112, alpha=255, size=21):
    """Serif bold centred definition, typewriter reveal: words up to n_words white, the next two dim."""
    words = text.split(); n = len(words) if n_words is None else max(0, min(len(words), n_words))
    Wd, Hd = s(w), s(h)
    ov = Image.new('RGBA', (Wd, Hd), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    od.rectangle((0, 0, Wd - 1, Hd - 1), fill=rgba((8, 26, 58), int(alpha * 0.92)), outline=rgba((46, 127, 224), alpha), width=max(1, s(2)))
    f = font('serifb', size)
    lines, cur = [], []
    for wd in words:
        trial = ' '.join(cur + [wd])
        if text_size(od, trial, f)[0] > Wd - s(60) and cur: lines.append(cur); cur = [wd]
        else: cur.append(wd)
    if cur: lines.append(cur)
    lh = f.size + s(8); total = lh * len(lines); yy = (Hd - total) // 2; idx = 0
    for ln in lines:
        txt = ' '.join(ln); lw = text_size(od, txt, f)[0]; cx = (Wd - lw) // 2
        for wd in ln:
            if idx < n: col = rgba(WHITE, alpha)
            elif idx < n + 2: col = rgba((90, 110, 150), alpha)
            else: col = (0, 0, 0, 0)
            od.text((cx, yy), wd, font=f, fill=col); cx += text_size(od, wd + ' ', f)[0]; idx += 1
        yy += lh
    img.alpha_composite(ov, (s(x), s(y)))

def callout(img, x, y, text, size=15, alpha=255, arrow=None, center=False):
    box = pill(img, x, y, text, size=size, pad=(14, 5), alpha=alpha, center=center)
    if arrow:
        d = ImageDraw.Draw(img); bx, by, bw, bh = box
        sx, sy = (bx + bw / 2, by + bh) if arrow[1] > by + bh else (bx + bw / 2, by)
        d.line((s(sx), s(sy), s(arrow[0]), s(arrow[1])), fill=rgba(WHITE, alpha), width=max(1, s(2)))
        ang = math.atan2(arrow[1] - sy, arrow[0] - sx)
        for sg in (-1, 1):
            d.line((s(arrow[0]), s(arrow[1]), s(arrow[0] - 9 * math.cos(ang + sg * 0.45)), s(arrow[1] - 9 * math.sin(ang + sg * 0.45))), fill=rgba(WHITE, alpha), width=max(1, s(2)))
    return box

def plain_text(img, x, y, text, size=20, alpha=255, fnt='bold', color=WHITE, center=False):
    d = ImageDraw.Draw(img); f = font(fnt, size); fs = font(fnt, int(size * 0.62))
    X = s(x) - (measure_sub(d, text, f, fs) / 2 if center else 0)
    sub_text(d, X, s(y), text, f, fs, rgba(color, alpha))

def equation(img, cx, y, tokens, size=16, alpha=255, gap=14, n_visible=None, bracket=None, arrows=None):
    """Equation row: species in navy pills, '+' and '→' as white glyphs. (cx, y) in 720p space."""
    d = ImageDraw.Draw(img); f = font('bold', size); fs = font('bold', int(size * 0.62))
    widths = [(text_size(d, '+', f)[0] + s(8)) if t in ('+', '→', '->') else (measure_sub(d, t, f, fs) + s(26)) for t in tokens]
    total = sum(widths) + s(gap) * (len(tokens) - 1); x = s(cx) - total / 2; Y = s(y); boxes = []
    for i, t in enumerate(tokens):
        vis = n_visible is None or i < n_visible
        if t in ('+', '→', '->'):
            if vis:
                if t == '+': d.text((x + s(4), Y + s(1)), '+', font=f, fill=rgba(WHITE, alpha))
                else:
                    ax0, ax1, ay = x + s(2), x + widths[i] - s(2), Y + f.size * 0.6
                    d.line((ax0, ay, ax1 + s(10), ay), fill=rgba(WHITE, alpha), width=max(1, s(2)))
                    d.line((ax1 + s(10), ay, ax1 + s(3), ay - s(5)), fill=rgba(WHITE, alpha), width=max(1, s(2))); d.line((ax1 + s(10), ay, ax1 + s(3), ay + s(5)), fill=rgba(WHITE, alpha), width=max(1, s(2)))
        else:
            if vis: pill(img, x / SC, y, t, size=size, pad=(13, 6), alpha=alpha)
        boxes.append((x, Y, widths[i], f.size + s(12))); x += widths[i] + s(gap)
    if bracket:
        i0, i1 = bracket; bx0 = boxes[i0][0]; bx1 = boxes[i1][0] + boxes[i1][2]; by = Y + f.size + s(20); c = rgba((60, 200, 230), alpha); lw = max(1, s(2))
        d.line((bx0, by, bx1, by), fill=c, width=lw); d.line((bx0, by - s(6), bx0, by), fill=c, width=lw); d.line((bx1, by - s(6), bx1, by), fill=c, width=lw)
        d.line(((bx0 + bx1) / 2, by, (bx0 + bx1) / 2, by + s(8)), fill=c, width=lw)
    if arrows:
        for i in arrows:
            bx, by, bw, bh = boxes[i]; tx, ty = bx + bw * 0.55, by + bh + s(3)
            d.line((tx - s(14), ty + s(16), tx, ty), fill=rgba(WHITE, alpha), width=max(1, s(3)))
            d.polygon([(tx, ty), (tx - s(9), ty + s(1)), (tx - s(2), ty + s(9))], fill=rgba(WHITE, alpha))
    return boxes

def numbered_list(img, x, y, items, n_visible, size=16, gap=46, alpha=255, center_x=None):
    for i, it in enumerate(items[:n_visible]):
        if center_x is not None: pill(img, center_x, y + i * gap, it, size=size, pad=(14, 6), alpha=alpha, center=True)
        else: pill(img, x, y + i * gap, it, size=size, pad=(14, 6), alpha=alpha)

def logo(img, cx=1208, cy=58, alpha=255):
    """Top-right channel mark: dark grey diamond, orange chevron on its left edges, serif 'VISUAL LEARNING' with big V/L."""
    size = s(150); ov = Image.new('RGBA', (size, size), (0, 0, 0, 0)); od = ImageDraw.Draw(ov); c = size / 2; r = s(52)
    od.polygon([(c, c - r), (c + r, c), (c, c + r), (c - r, c)], fill=rgba((58, 58, 60), alpha))
    od.line([(c - s(2), c - r - s(4)), (c - r - s(4), c), (c - s(2), c + r + s(4))], fill=rgba((242, 140, 20), alpha), width=max(2, s(5)))
    od.line([(c + s(4), c - r + s(2)), (c - r + s(6), c)], fill=rgba((90, 90, 92), alpha), width=max(1, s(3)))
    fb = font('serif', 30); fsm = font('serif', 12)
    od.text((c - s(22), c - s(26)), 'V', font=fb, fill=rgba((242, 140, 20), alpha)); od.text((c - s(2), c - s(14)), 'ISUAL', font=fsm, fill=rgba((242, 140, 20), alpha))
    od.text((c - s(14), c - s(12)), 'L', font=fb, fill=rgba(WHITE, alpha)); od.text((c + s(4), c + s(1)), 'EARNING', font=fsm, fill=rgba(WHITE, alpha))
    img.alpha_composite(ov, (int(s(cx) - c), int(s(cy) - c)))

_OUTRO_BG = None
def outro(img, t, alpha=255):
    """'THANKS FOR WATCHING' serif on a dark-blue radial gradient; LIKE + red subscribe after 1.5 s."""
    global _OUTRO_BG
    if _OUTRO_BG is None:
        import numpy as np
        yy, xx = np.mgrid[0:H, 0:W]; d = np.hypot((xx - s(640)) / s(640), (yy - s(400)) / s(400)); v = np.clip(1 - d, 0, 1)
        px = np.zeros((H, W, 4), dtype=np.uint8); px[:, :, 0] = 14 + 40 * v; px[:, :, 1] = 20 + 52 * v; px[:, :, 2] = 34 + 72 * v; px[:, :, 3] = 255
        _OUTRO_BG = Image.fromarray(px, 'RGBA')
    img.alpha_composite(_OUTRO_BG)
    d = ImageDraw.Draw(img); f = font('serif', 46); txt = 'THANKS FOR WATCHING'; tw, th = text_size(d, txt, f)
    d.text(((W - tw) / 2, s(300)), txt, font=f, fill=rgba(WHITE, alpha))
    if t > 1.5:
        a = int(min(1, (t - 1.5) / 0.4) * 255)
        pill(img, 540, 420, 'LIKE', size=13, pad=(18, 5), alpha=a, fill=(10, 40, 90), border=(70, 160, 230), center=True)
        d.rounded_rectangle((s(690), s(408), s(760), s(432)), radius=s(3), fill=rgba((190, 20, 20), a))

def fade_in(t, t0, dur=0.35): return max(0.0, min(1.0, (t - t0) / dur))
def fade_io(t, t0, t1, dur=0.35): return min(fade_in(t, t0, dur), max(0.0, min(1.0, (t1 - t) / dur)))
