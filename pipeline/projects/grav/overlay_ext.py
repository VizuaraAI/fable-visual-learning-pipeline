"""Gravitation-specific 2D overlay elements. overlay.draw_event() calls draw_extra() for every kind it does not know.
All coordinates in the reference's 1280x720 space (helpers['s'] scales to the output). Kinds:
  table5        five-row topic table (the built-in 'table' is sized for three rows)
  text          bold white text, optional timed parts, x/left or cx/centre; understands _1 subscripts, ^{-11} superscripts, ∝
  frac          fraction 'lhs  num/den' with per-part reveal times and an optional box (blue or yellow outline)
  panel         a dark bordered box (or a free group) with timed lines; a line may itself be a frac or a boxed text
  anchor_pill   pill that follows a 3D anchor (speedometer 'v = 40'), timed values, leader line
  anchor_label  text at an offset from an anchor (A, B, M1, M2, R)
  ptr_text      text with an arrow pointing at an anchor (Mass = m, Free Fall)
  dbl_arrow     double-headed arrow between two anchors with a label (R^2)
  anchor_line   glowing line between two anchors with an optional label (the r / R radius line)
  pill2         pill with custom fill/border colours (dark-red and olive pills of the reference)
  navy_panel    translucent navy rectangle (the Pressure = Thrust/Area panel)
  twin_pointer  pill with leader lines to two anchors ('Pressure' over the two blocks)"""
import re, math
from PIL import Image, ImageDraw

_TOK = re.compile(r'(\^\{[^}]*\}|_\{[^}]*\}|_\d|∝)')
DEEP = (8, 26, 58); BORDER = (46, 127, 224); CYAN = (60, 200, 255)

def rich(d, x, y, txt, size, fill, ui, fnt='bold', measure=False):
    """Draw (or measure) text with _n subscripts, ^{..} superscripts and the ∝ glyph (Arial Unicode). Returns width (px)."""
    f = ui.font(fnt, size); fs = ui.font(fnt, max(8, int(size * 0.62))); fu = ui.font('uni', int(size * 1.35)); cx = x
    for p in _TOK.split(txt):
        if not p: continue
        if p == '∝':
            if not measure: d.text((cx, y - f.size * 0.42), p, font=fu, fill=fill)
            cx += ui.text_size(d, p, fu)[0] + f.size * 0.1
        elif p.startswith('^{'):
            t = p[2:-1]
            if not measure: d.text((cx, y - f.size * 0.22), t, font=fs, fill=fill)
            cx += ui.text_size(d, t, fs)[0]
        elif p.startswith('_'):
            t = p[2:-1] if p.startswith('_{') else p[1:]
            if not measure: d.text((cx, y + f.size * 0.45), t, font=fs, fill=fill)
            cx += ui.text_size(d, t, fs)[0]
        else:
            if not measure: d.text((cx, y), p, font=f, fill=fill)
            cx += ui.text_size(d, p, f)[0]
    return cx - x

def _frac_geom(d, e, ui, s):
    size = e.get('size', 22); f = ui.font('bold', size); lhs = e.get('lhs', ''); num, den = e['num'], e['den']
    lw = rich(d, 0, 0, lhs, size, None, ui, measure=True) if lhs else 0
    nw = rich(d, 0, 0, num, size, None, ui, measure=True); dw = rich(d, 0, 0, den, size, None, ui, measure=True)
    fw = max(nw, dw) + s(10); total = lw + (s(9) if lhs else 0) + fw
    x0 = s(e['x']) if 'x' in e else s(e['cx']) - total / 2
    return size, f, lhs, num, den, lw, nw, dw, fw, total, x0, s(e['y'])

def draw_frac(img, e, t, a, ui, s, color=None):
    d = ImageDraw.Draw(img); size, f, lhs, num, den, lw, nw, dw, fw, total, x0, y = _frac_geom(d, e, ui, s)
    t0 = e.get('t0', t); t_lhs = e.get('t_lhs', t0); t_num = e.get('t_num', t0); t_bar = e.get('t_bar', t0); t_den = e.get('t_den', t0)
    col = color or e.get('color', ui.WHITE); fill = ui.rgba(col, a)
    box_from = e.get('box_from')
    if e.get('box') or (box_from is not None and t >= box_from):
        ab = a if box_from is None else int(a * ui.fade_in(t, box_from, 0.4)); px, py = e.get('box_pad', (12, 8))
        bx0, by0, bx1, by1 = x0 - s(px), y - f.size * 1.3 - s(py), x0 + total + s(px), y + f.size * 1.3 + s(py)
        d.rounded_rectangle((bx0, by0, bx1, by1), radius=s(3), fill=ui.rgba(DEEP, int(ab * 0.9)) if e.get('box_fill', True) else None, outline=ui.rgba(e.get('box_color', BORDER), ab), width=max(1, s(2)))
    if lhs and t >= t_lhs: rich(d, x0, y - f.size * 0.62, lhs, size, ui.rgba(col, int(a * ui.fade_in(t, t_lhs, 0.35))), ui)
    fx = x0 + lw + (s(9) if lhs else 0)
    if t >= t_num: rich(d, fx + (fw - nw) / 2, y - f.size * 1.22, num, size, ui.rgba(col, int(a * ui.fade_in(t, t_num, 0.35))), ui)
    if t >= t_bar: d.line((fx, y, fx + fw, y), fill=ui.rgba(col, int(a * ui.fade_in(t, t_bar, 0.3))), width=max(1, s(2)))
    if t >= t_den: rich(d, fx + (fw - dw) / 2, y + s(5), den, size, ui.rgba(col, int(a * ui.fade_in(t, t_den, 0.35))), ui)

def draw_text(img, e, t, a, ui, s):
    d = ImageDraw.Draw(img); size = e.get('size', 20); col = e.get('color', ui.WHITE)
    parts = e.get('parts') or [(e['text'], e['t0'])]
    widths = [rich(d, 0, 0, p[0], size, None, ui, measure=True) for p in parts]; total = sum(widths)
    x = s(e['x']) if 'x' in e else s(e['cx']) - total / 2; y = s(e['y'])
    for (txt, ts), w in zip(parts, widths):
        if t >= ts: rich(d, x, y, txt, size, ui.rgba(col, int(a * ui.fade_in(t, ts, 0.4))), ui)
        x += w

def draw_panel(img, e, t, a, ui, s):
    d = ImageDraw.Draw(img); x, y = e['x'], e['y']; w, h = e.get('w', 300), e.get('h', 100)
    if e.get('box', True):
        d.rounded_rectangle((s(x), s(y), s(x + w), s(y + h)), radius=s(3), fill=ui.rgba(DEEP, int(a * 0.88)), outline=ui.rgba(BORDER, a), width=max(1, s(2)))
    for ln in e['lines']:
        if t < ln['t']: continue
        aa = int(a * ui.fade_in(t, ln['t'], 0.4)); size = ln.get('size', 15); col = ln.get('color', ui.WHITE)
        if ln.get('kind') == 'frac':
            sub = dict(ln); sub['t0'] = ln['t']; sub['y'] = y + ln['y']
            if ln.get('center'): sub['cx'] = x + ln['x']; sub.pop('x', None)
            else: sub['x'] = x + ln['x']
            draw_frac(img, sub, t, aa, ui, s, color=col); d = ImageDraw.Draw(img); continue
        tw = rich(d, 0, 0, ln['text'], size, None, ui, measure=True); X = s(x + ln['x']) - (tw / 2 if ln.get('center') else 0); Y = s(y + ln['y'])
        if ln.get('box'):
            f = ui.font('bold', size); d.rounded_rectangle((X - s(10), Y - s(6), X + tw + s(10), Y + f.size + s(8)), radius=s(3), fill=ui.rgba(DEEP, int(aa * 0.9)), outline=ui.rgba(BORDER, aa), width=max(1, s(2)))
        rich(d, X, Y, ln['text'], size, ui.rgba(col, aa), ui)

def _arrow(d, p0, p1, col, s, width=2, head=9):
    (x0, y0), (x1, y1) = p0, p1; d.line((x0, y0, x1, y1), fill=col, width=max(1, s(width)))
    ang = math.atan2(y1 - y0, x1 - x0); hl = s(head)
    d.polygon([(x1, y1), (x1 - hl * math.cos(ang - 0.42), y1 - hl * math.sin(ang - 0.42)), (x1 - hl * math.cos(ang + 0.42), y1 - hl * math.sin(ang + 0.42))], fill=col)

def draw_anchor_pill(img, e, t, a, ui, s, H):
    p = H['anchors'](e['spec'], t).get(e['name'])
    if not p: return
    vals = [v for tv, v in e['values'] if t >= tv]
    if not vals: return
    txt = vals[-1]; x, y = p[0] + e.get('dx', 120), p[1] + e.get('dy', -30)
    if e.get('leader', True):
        d = ImageDraw.Draw(img); d.line((s(p[0] + 8), s(p[1]), s(x - 34), s(y + 8)), fill=ui.rgba((70, 170, 255), a), width=max(1, s(2)))
    ui.pill(img, x, y, txt, size=13, pad=(12, 4), alpha=a, fill=(6, 22, 52), border=(70, 170, 255), center=True)

def draw_anchor_label(img, e, t, a, ui, s, H):
    p = H['anchors'](e['spec'], t).get(e['name'])
    if not p: return
    d = ImageDraw.Draw(img); size = e.get('size', 22); col = e.get('color', ui.WHITE)
    tw = rich(d, 0, 0, e['text'], size, None, ui, measure=True); f = ui.font('bold', size)
    rich(d, s(p[0] + e.get('dx', 0)) - tw / 2, s(p[1] + e.get('dy', 0)) - f.size * 0.6, e['text'], size, ui.rgba(col, a), ui)

def draw_ptr_text(img, e, t, a, ui, s, H):
    p = H['anchors'](e['spec'], t).get(e['name'])
    if not p: return
    d = ImageDraw.Draw(img); size = e.get('size', 18); col = e.get('color', ui.WHITE); acol = e.get('arrow_color', ui.WHITE)
    tx, ty = p[0] + e['dx'], p[1] + e.get('dy', 0); f = ui.font('bold', size); tw = rich(d, 0, 0, e['text'], size, None, ui, measure=True)
    rich(d, s(tx) - tw / 2, s(ty) - f.size * 0.6, e['text'], size, ui.rgba(col, a), ui)
    sgn = 1 if p[0] > tx else -1; x0 = s(tx) + sgn * (tw / 2 + s(10)); x1 = s(p[0]) - sgn * s(e.get('gap', 26)); y1 = s(p[1])
    _arrow(d, (x0, s(ty)), (x1, y1), ui.rgba(acol, a), s, width=3, head=12)

def draw_dbl_arrow(img, e, t, a, ui, s, H):
    an = H['anchors'](e['spec'], t); pa, pb = an.get(e['a']), an.get(e['b'])
    if not (pa and pb): return
    d = ImageDraw.Draw(img); y = s(pa[1] + e.get('dy', 60)); xa, xb = s(pa[0]), s(pb[0]); u = H['smooth01']((t - e.get('t_full', e['t0'])) / 1.2) if 't_full' in e else 1.0
    cx = (xa + xb) / 2; half0 = abs(xb - xa) * 0.22; half1 = abs(xb - xa) / 2 - s(e.get('inset', 10)); half = half0 + (half1 - half0) * u
    col = ui.rgba(ui.WHITE, a); x0, x1 = cx - half, cx + half; d.line((x0, y, x1, y), fill=col, width=max(1, s(3)))
    for xe, sg in ((x0, 1), (x1, -1)):
        d.polygon([(xe, y), (xe + sg * s(14), y - s(7)), (xe + sg * s(14), y + s(7))], fill=col)
    if e.get('text'):
        size = e.get('size', 24); tw = rich(d, 0, 0, e['text'], size, None, ui, measure=True); rich(d, cx - tw / 2, y + s(14), e['text'], size, col, ui)

def draw_anchor_line(img, e, t, a, ui, s, H):
    an = H['anchors'](e['spec'], t); pa, pb = an.get(e['a']), an.get(e['b'])
    if not (pa and pb): return
    col = e.get('color', CYAN); lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    p0, p1 = (s(pa[0]), s(pa[1])), (s(pb[0]), s(pb[1])); d.line((*p0, *p1), fill=ui.rgba(col, int(a * 0.45)), width=max(2, s(7)))
    from PIL import ImageFilter; lay = lay.filter(ImageFilter.GaussianBlur(s(3))); d = ImageDraw.Draw(lay)
    d.line((*p0, *p1), fill=ui.rgba(col, a), width=max(1, s(2)))
    for p in (p0, p1): d.ellipse((p[0] - s(4), p[1] - s(4), p[0] + s(4), p[1] + s(4)), fill=ui.rgba(col, a))
    img.alpha_composite(lay)
    if e.get('text'):
        d = ImageDraw.Draw(img); size = e.get('size', 18); mx, my = (pa[0] + pb[0]) / 2 + e.get('dx', 16), (pa[1] + pb[1]) / 2 + e.get('dy', 0); f = ui.font('bold', size)
        rich(d, s(mx), s(my) - f.size * 0.6, e['text'], size, ui.rgba(e.get('text_color', ui.WHITE), a), ui)

def draw_pill2(img, e, t, a, ui, s):
    ui.pill(img, e['x'], e['y'], e['text'], size=e.get('size', 15), pad=e.get('pad', (16, 6)), alpha=a, fill=e.get('fill', DEEP), border=e.get('border', BORDER), center=e.get('center', True), color=e.get('color', ui.WHITE), min_w=e.get('min_w', 0))

def draw_navy_panel(img, e, t, a, ui, s):
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); x0, y0, x1, y1 = e['box']
    d.rounded_rectangle((s(x0), s(y0), s(x1), s(y1)), radius=s(3), fill=ui.rgba(e.get('fill', (10, 30, 72)), int(a * e.get('alpha', 0.62))), outline=ui.rgba(e.get('border', (46, 110, 200)), a), width=max(1, s(1)))
    img.alpha_composite(lay)

def draw_twin_pointer(img, e, t, a, ui, s, H):
    box = ui.pill(img, e['x'], e['y'], e['text'], size=e.get('size', 15), pad=(14, 5), alpha=a, center=True)
    an = H['anchors'](e['spec'], t); d = ImageDraw.Draw(img); bx, by, bw, bh = box; sx, sy = bx + bw / 2, by + bh
    for key in ('a', 'b'):
        p = an.get(e[key]) if isinstance(e.get(key), str) else e.get(key)
        if p: d.line((s(sx), s(sy), s(p[0]), s(p[1] - 12)), fill=ui.rgba(ui.WHITE, a), width=max(1, s(2)))

def draw_table5(img, e, t, a, ui, s):
    x, y, w, h = e.get('x', 150), e.get('y', 208), e.get('w', 980), e.get('h', 445); Wd, Hd = s(w), s(h)
    ov = Image.new('RGBA', (Wd, Hd), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    od.rounded_rectangle((0, 0, Wd - 1, Hd - 1), radius=s(8), fill=ui.rgba((8, 34, 70), int(a * 0.93)), outline=ui.rgba(ui.CYAN_B, a), width=max(1, s(2)))
    fh = ui.font('bold', 26); fr = ui.font('bold', 20)
    od.text((s(40), s(26)), 'Topic includes', font=fh, fill=ui.rgba(ui.WHITE, a)); od.text((Wd - s(40) - ui.text_size(od, 'Time line', fh)[0], s(26)), 'Time line', font=fh, fill=ui.rgba(ui.WHITE, a))
    for i, (name, tl) in enumerate(e['topics']):
        yy = s(96 + i * e.get('row_h', 66)); od.text((s(48), yy), name, font=fr, fill=ui.rgba(ui.WHITE, a)); od.text((Wd - s(48) - ui.text_size(od, tl, fr)[0], yy + s(2)), tl, font=fr, fill=ui.rgba(ui.WHITE, a))
    img.alpha_composite(ov, (s(x), s(y)))

def draw_extra(img, e, t, spec, ui, H):
    k = e['kind']; a = H['alpha']; s = H['s']; e = dict(e, spec=spec)
    if k == 'table5': draw_table5(img, e, t, a, ui, s)
    elif k == 'text': draw_text(img, e, t, a, ui, s)
    elif k == 'frac': draw_frac(img, e, t, a, ui, s)
    elif k == 'panel': draw_panel(img, e, t, a, ui, s)
    elif k == 'anchor_pill': draw_anchor_pill(img, e, t, a, ui, s, H)
    elif k == 'anchor_label': draw_anchor_label(img, e, t, a, ui, s, H)
    elif k == 'ptr_text': draw_ptr_text(img, e, t, a, ui, s, H)
    elif k == 'dbl_arrow': draw_dbl_arrow(img, e, t, a, ui, s, H)
    elif k == 'anchor_line': draw_anchor_line(img, e, t, a, ui, s, H)
    elif k == 'pill2': draw_pill2(img, e, t, a, ui, s)
    elif k == 'navy_panel': draw_navy_panel(img, e, t, a, ui, s)
    elif k == 'twin_pointer': draw_twin_pointer(img, e, t, a, ui, s, H)
    else: print('unknown overlay kind', k)
