"""Cell-chapter 2D overlay elements. overlay.draw_event() calls draw_extra() for every kind it does not know.
All coordinates in the reference's 1280x720 space (helpers['s'] scales to the output). Kinds:
  stag      slanted dark parallelogram tag with cyan edges (section tags top-left: 'Cell Organelles', '1.ENDOPLASMIC RETICULUM',
            'Bacteria'; also the in-scene 'Chromosomes' / 'DNA' / '1665' tags, optionally pinned to an anchor + hollow arrow)
  shield    dark translucent pentagon (rectangle + pointed bottom, cyan border) hanging from a 3D anchor or a fixed point
  atext     plain bold text (multi-line ok) with an optional hollow white arrow to an anchor or a point
  obox      outlined box with an optional coloured title and timed lines (Functions / Stored / Chromoplasts / ATP / Energy)
  harrow    stand-alone hollow arrow between two points or from a point to an anchor
  mol       glowing molecule markers at the Hp* (H2O) / Op* (O2) / Rp* (CO2) anchors
  table4    the four-row 'Topic includes / Time line' intro table
  outro_vl  the channel's outro: vl mark + wordmark, Subscribe / LIKE buttons"""
import math
from PIL import Image, ImageDraw, ImageFilter

CYAN = (74, 208, 222); NAVY = (10, 30, 62); DARK = (16, 20, 27); WHITE = (255, 255, 255)
INK = (20, 24, 32)

def _lines(txt): return [ln for ln in str(txt).split('\n')]

def _text_block(d, lines, f, ui, gap=4):
    ws = [ui.text_size(d, ln, f)[0] for ln in lines]; h = len(lines) * f.size + (len(lines) - 1) * ui.s(gap)
    return max(ws) if ws else 0, h, ws

def _draw_block(d, x, y, lines, f, ui, fill, gap=4, center=True, width=None):
    """Draw lines of text; x = left edge (or centre-x when center) in output px, y = top in output px."""
    yy = y
    for ln in lines:
        w = ui.text_size(d, ln, f)[0]
        xx = x - w / 2 if center else x
        d.text((xx, yy - f.size * 0.18), ln, font=f, fill=fill); yy += f.size + ui.s(gap)

def _anchor_pt(e, t, H):
    if e.get('anchor'):
        p = H['anchors'](e['spec'], t).get(e['anchor'])
        if not p: return None
        return (p[0] + e.get('dx', 0), p[1] + e.get('dy', 0))
    return None

def hollow_arrow(img, p0, p1, a, ui, s, shaft=5, head_w=13, head_l=22, width=2, fill=None):
    """Outlined (hollow) white arrow from p0 (tail) to p1 (tip), 720p coordinates."""
    (x0, y0), (x1, y1) = p0, p1; L = math.hypot(x1 - x0, y1 - y0)
    if L < 4: return
    ux, uy = (x1 - x0) / L, (y1 - y0) / L; nx, ny = -uy, ux
    hl = min(head_l, L * 0.55); bx, by = x1 - ux * hl, y1 - uy * hl
    pts = [(x0 + nx * shaft, y0 + ny * shaft), (bx + nx * shaft, by + ny * shaft), (bx + nx * head_w, by + ny * head_w), (x1, y1),
           (bx - nx * head_w, by - ny * head_w), (bx - nx * shaft, by - ny * shaft), (x0 - nx * shaft, y0 - ny * shaft)]
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.polygon([(s(x), s(y)) for x, y in pts], fill=ui.rgba(fill or INK, int(a * 0.8)), outline=ui.rgba(WHITE, a))
    d.line([(s(x), s(y)) for x, y in pts] + [(s(pts[0][0]), s(pts[0][1]))], fill=ui.rgba(WHITE, a), width=max(1, s(width)), joint='curve')
    img.alpha_composite(lay)

def draw_stag(img, e, t, a, ui, s, H):
    size = e.get('size', 19); f = ui.font('bold', size); d = ImageDraw.Draw(img); lines = _lines(e['text'])
    tw, th, _ = _text_block(d, lines, f, ui); padx, pady = e.get('pad', (34, 9)); slant = e.get('slant', 26)
    w = tw + s(padx) * 2 + s(slant); h = th + s(pady) * 2
    ap = _anchor_pt(e, t, H)
    if ap is not None: X, Y = s(ap[0]) - w / 2, s(ap[1]) - h / 2
    elif e.get('center'): X, Y = s(e['x']) - w / 2, s(e['y']) - h / 2
    else: X, Y = s(e['x']), s(e['y'])
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    pts = [(X + s(slant), Y), (X + w, Y), (X + w - s(slant), Y + h), (X, Y + h)]
    aa = int(a * e.get('alpha', 1.0))
    ld.polygon(pts, fill=ui.rgba(e.get('fill', DARK), int(aa * 0.9)))
    col = ui.rgba(e.get('border', CYAN), aa); lw = max(1, s(2))
    ld.line(pts + [pts[0]], fill=col, width=lw, joint='curve')
    ld.line((pts[0], pts[1]), fill=ui.rgba(e.get('border', CYAN), aa), width=max(1, s(3)))
    img.alpha_composite(lay); d = ImageDraw.Draw(img)
    _draw_block(d, X + w / 2, Y + s(pady), lines, f, ui, ui.rgba(WHITE, aa))
    if e.get('arrow') or (ap is not None and e.get('arrow_len')):
        if e.get('arrow'): p0, p1 = (e['arrow'][0], e['arrow'][1]), (e['arrow'][2], e['arrow'][3])
        else:
            p1 = H['anchors'](e['spec'], t).get(e['anchor']); tail = ((X + w / 2) / ui.SC, (Y + h) / ui.SC)
            if not p1: return
            p0 = tail
        hollow_arrow(img, p0, p1, aa, ui, s)

def draw_shield(img, e, t, a, ui, s, H):
    size = e.get('size', 18); f = ui.font(e.get('fnt', 'reg'), size); d = ImageDraw.Draw(img); lines = _lines(e['text'])
    tw, th, _ = _text_block(d, lines, f, ui, gap=2); padx, pady = e.get('pad', (22, 14)); tip = s(e.get('tip', 34))
    w = max(tw + s(padx) * 2, s(e.get('min_w', 0))); h = th + s(pady) * 2
    if e.get('anchor'):
        p = H['anchors'](e['spec'], t).get(e['anchor'])
        if not p: return
        tx, ty = s(p[0] + e.get('dx', 0)), s(p[1] + e.get('dy', 0))
    else: tx, ty = s(e['x']), s(e['y'])
    x0, x1 = tx - w / 2, tx + w / 2; y1 = ty - tip; y0 = y1 - h
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    pts = [(x0, y0), (x1, y0), (x1, y1), (tx, ty), (x0, y1)]
    aa = int(a * e.get('alpha', 1.0))
    ld.polygon(pts, fill=ui.rgba(e.get('fill', NAVY), int(aa * e.get('fill_alpha', 0.78))))
    ld.line(pts + [pts[0]], fill=ui.rgba(e.get('border', (90, 205, 240)), aa), width=max(1, s(2)), joint='curve')
    img.alpha_composite(lay); d = ImageDraw.Draw(img)
    _draw_block(d, tx, y0 + s(pady), lines, f, ui, ui.rgba(WHITE, aa), gap=2)

def draw_atext(img, e, t, a, ui, s, H):
    size = e.get('size', 20); f = ui.font(e.get('fnt', 'bold'), size); d = ImageDraw.Draw(img); lines = _lines(e.get('text', ''))
    tw, th, _ = _text_block(d, lines, f, ui); aa = int(a * e.get('alpha', 1.0)); col = e.get('color', WHITE)
    ap = None
    if e.get('anchor') and 'x' not in e and 'cx' not in e:
        ap = _anchor_pt(e, t, H)
        if ap is None: return
        cx, y = s(ap[0]), s(ap[1]) - th / 2
    elif 'cx' in e: cx, y = s(e['cx']), s(e['y'])
    else: cx, y = s(e['x']) + tw / 2, s(e['y'])
    if lines and lines != ['']: _draw_block(d, cx, y, lines, f, ui, ui.rgba(col, aa), center=True)
    arr = e.get('arrow')
    if arr == 'anchor' or (e.get('anchor') and arr is None and e.get('arrow_from')):
        p1 = H['anchors'](e['spec'], t).get(e['anchor'])
        if not p1: return
        p1 = (p1[0] + e.get('adx', 0), p1[1] + e.get('ady', 0))
        fr = e.get('arrow_from')
        if fr is None: fr = (cx / ui.SC, (y + th) / ui.SC + 10)
        hollow_arrow(img, fr, p1, aa, ui, s)
    elif isinstance(arr, (list, tuple)) and len(arr) == 4:
        hollow_arrow(img, (arr[0], arr[1]), (arr[2], arr[3]), aa, ui, s)

def draw_harrow(img, e, t, a, ui, s, H):
    if e.get('anchor'):
        p1 = H['anchors'](e['spec'], t).get(e['anchor'])
        if not p1: return
        p1 = (p1[0] + e.get('adx', 0), p1[1] + e.get('ady', 0))
        L = e.get('len', 70); ang = math.radians(e.get('angle', -135))        # arrow arrives from angle (default: from upper-left)
        p0 = (p1[0] + L * math.cos(ang), p1[1] + L * math.sin(ang))
    else: p0, p1 = (e['x0'], e['y0']), (e['x1'], e['y1'])
    hollow_arrow(img, p0, p1, a, ui, s, shaft=e.get('shaft', 5), head_w=e.get('head_w', 13), head_l=e.get('head_l', 22))

def draw_obox(img, e, t, a, ui, s, H):
    """Outlined box: optional title (coloured), timed lines below it, all centred. w/h optional (auto from text)."""
    size = e.get('size', 22); f = ui.font('bold', size); d = ImageDraw.Draw(img)
    title = e.get('title'); tf = ui.font('bold', e.get('title_size', size + 4))
    lines = e.get('lines', []); shown = [ln for ln in lines if t >= (ln[1] if isinstance(ln, (list, tuple)) else e['t0'])]
    texts = [ln[0] if isinstance(ln, (list, tuple)) else ln for ln in lines]
    tw, th, _ = _text_block(d, texts, f, ui, gap=e.get('gap', 8)) if texts else (0, 0, [])
    ttw = ui.text_size(d, title, tf)[0] if title else 0
    padx, pady = e.get('pad', (22, 14))
    w = s(e['w']) if 'w' in e else max(tw, ttw) + s(padx) * 2
    h = s(e['h']) if 'h' in e else th + (tf.size + s(10) if title else 0) + s(pady) * 2
    X = s(e['x']) - (w / 2 if e.get('center') else 0); Y = s(e['y'])
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    ld.rectangle((X, Y, X + w, Y + h), fill=ui.rgba(e.get('fill', DARK), int(a * e.get('fill_alpha', 0.55))), outline=ui.rgba(e.get('border', (225, 40, 40)), a), width=max(1, s(e.get('bw', 2))))
    img.alpha_composite(lay); d = ImageDraw.Draw(img); yy = Y + s(pady); cx = X + w / 2
    if title:
        d.text((cx - ttw / 2, yy - tf.size * 0.18), title, font=tf, fill=ui.rgba(e.get('title_color', (80, 200, 255)), a)); yy += tf.size + s(10)
    for ln in lines:
        txt, ts = (ln[0], ln[1]) if isinstance(ln, (list, tuple)) else (ln, e['t0'])
        if t >= ts:
            aa = int(a * ui.fade_in(t, ts, 0.35)); w_ = ui.text_size(d, txt, f)[0]
            d.text((cx - w_ / 2, yy - f.size * 0.18), txt, font=f, fill=ui.rgba(e.get('color', WHITE), aa))
        yy += f.size + s(e.get('gap', 8))

MOL = {'Hp': ('H_2O', (60, 120, 230), 22, 17), 'Op': ('O_2', (215, 80, 60), 30, 24), 'Rp': ('CO_2', (120, 175, 110), 32, 22)}
def draw_mol(img, e, t, a, ui, s, H):
    for name, p in H['anchors'](e['spec'], t).items():
        spec = MOL.get(name[:2])
        if not spec: continue
        txt, col, r, fs = spec
        H['glow_circle'](img, p[0], p[1], r, col, txt, fs, int(a * e.get('alpha', 0.9)))

def draw_table4(img, e, t, a, ui, s, H):
    x, y, w, h = e.get('x', 75), e.get('y', 222), e.get('w', 1100), e.get('h', 455); Wd, Hd = s(w), s(h)
    ov = Image.new('RGBA', (Wd, Hd), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    od.rounded_rectangle((0, 0, Wd - 1, Hd - 1), radius=s(8), fill=ui.rgba((8, 34, 70), int(a * 0.9)), outline=ui.rgba(ui.CYAN_B, a), width=max(1, s(2)))
    fh = ui.font('bold', 27); fr = ui.font('bold', 22)
    od.text((s(74), s(38)), 'Topic includes', font=fh, fill=ui.rgba(WHITE, a)); od.text((Wd - s(96) - ui.text_size(od, 'Time line', fh)[0], s(38)), 'Time line', font=fh, fill=ui.rgba(WHITE, a))
    for i, (name, tl) in enumerate(e['topics']):
        yy = s(112 + i * e.get('row_h', 85)); od.text((s(76), yy), name, font=fr, fill=ui.rgba(WHITE, a)); od.text((Wd - s(80) - ui.text_size(od, tl, fr)[0], yy + s(2)), tl, font=fr, fill=ui.rgba(WHITE, a))
    img.alpha_composite(ov, (s(x), s(y)))

def _tri(cx, cy, r, rot):
    return [(cx + r * math.cos(rot + k * 2 * math.pi / 3), cy + r * math.sin(rot + k * 2 * math.pi / 3)) for k in range(3)]

def draw_outro_vl(img, e, t, a, ui, s, H):
    """'vl' mark (three rounded, rotated triangles: orange, blue, purple) + 'Visual Learning' wordmark; buttons after 1.8 s."""
    tt = t - e['t0']; d = ImageDraw.Draw(img)
    cx, cy = s(430), s(330); R = s(78)
    for col, rot, rr in (((242, 160, 40), -0.35, R * 1.0), ((50, 120, 220), 0.45, R * 0.96), ((150, 60, 200), 1.15, R * 0.92)):
        lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
        ld.polygon(_tri(cx, cy, rr, rot), fill=ui.rgba(col, a))
        lay = lay.filter(ImageFilter.GaussianBlur(s(1.2))); img.alpha_composite(lay)
    f = ui.font('bold', 54); tw = ui.text_size(d, 'vl', f)[0]; d.text((cx - tw / 2, cy - f.size * 0.62), 'vl', font=f, fill=ui.rgba(WHITE, a))
    fw = ui.font('bold', 46); d.text((s(560), s(268)), 'Visual', font=fw, fill=ui.rgba(WHITE, a)); d.text((s(560), s(330)), 'Learning', font=fw, fill=ui.rgba(WHITE, a))
    if tt > 1.8:
        aa = int(a * min(1.0, (tt - 1.8) / 0.4))
        bx, by = s(300), s(560); bw, bh = s(190), s(46)
        d.rounded_rectangle((bx - bw / 2, by - bh / 2, bx + bw / 2, by + bh / 2), radius=s(6), fill=ui.rgba((205, 20, 20), aa))
        d.polygon([(bx - bw / 2 + s(18), by - s(9)), (bx - bw / 2 + s(18), by + s(9)), (bx - bw / 2 + s(32), by)], fill=ui.rgba(WHITE, aa))
        fb = ui.font('bold', 20); d.text((bx - bw / 2 + s(44), by - fb.size * 0.62), 'Subscribe', font=fb, fill=ui.rgba(WHITE, aa))
        ui.pill(img, 570, 560, 'LIKE', size=18, pad=(26, 9), alpha=aa, fill=(12, 40, 92), border=(70, 160, 230), center=True)

def draw_extra(img, e, t, spec, ui, H):
    k = e['kind']; a = H['alpha']; s = H['s']; e = dict(e, spec=spec)
    if k == 'stag': draw_stag(img, e, t, a, ui, s, H)
    elif k == 'shield': draw_shield(img, e, t, a, ui, s, H)
    elif k == 'atext': draw_atext(img, e, t, a, ui, s, H)
    elif k == 'harrow': draw_harrow(img, e, t, a, ui, s, H)
    elif k == 'obox': draw_obox(img, e, t, a, ui, s, H)
    elif k == 'mol': draw_mol(img, e, t, a, ui, s, H)
    elif k == 'table4': draw_table4(img, e, t, a, ui, s, H)
    elif k == 'outro_vl': draw_outro_vl(img, e, t, a, ui, s, H)
    else: print('unknown overlay kind', k)
