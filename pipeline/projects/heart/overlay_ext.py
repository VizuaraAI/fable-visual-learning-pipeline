"""Heart-specific 2D overlay elements. overlay.draw_event() calls draw_extra() for every kind it does not know.
All coordinates in 1280x720 space (helpers['s'] scales to the output). Kinds:
  table6     six-row 'Topic includes / Time line' table (the built-in 'table' is sized for three rows)
  pill2      pill with custom fill / border / text colours (the palette's 8-bit twins)
  apill      coloured pill that follows a 3D anchor at an offset, with a leader line to the anchor
  bigtext    bold centred text with a soft glow (the Atria / Ventricles headings)
  measure    glowing bar between two anchors (outer / inner wall edge) with end ticks and a label: wall thickness
  trace      scrolling phonocardiogram: a baseline with a gold 'Lub' burst and a cyan 'Dub' burst on every beat
  cyclebar   the ticking heartbeat timeline: one 0.83 s cycle split into its four phases, a marker running along it
  gauge      live blood-pressure readout following an anchor ('118 mm Hg'), values keyed over time
  counter    'through the heart: N' pass counter that flashes on every pass
  markers    glowing coloured dots + labels on every anchor whose name starts with a prefix (O2p / CO2p / Nutp / Wsp)
  loop       banner pill with a subtitle (the Pulmonary / Systemic circulation loop names)
  toggle     two alternating words in beat rhythm (Contract / Relax)"""
import math
from PIL import Image, ImageDraw, ImageFilter

DEEP = (8, 26, 58)
def _lerp(a, b, u): return a + (b - a) * u

def _glow_layer(img, draw_fn, blur=4):
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); draw_fn(d); lay = lay.filter(ImageFilter.GaussianBlur(blur)); img.alpha_composite(lay)

def draw_table6(img, e, t, a, ui, s):
    x, y, w, h = e.get('x', 150), e.get('y', 190), e.get('w', 980), e.get('h', 470); Wd, Hd = s(w), s(h)
    ov = Image.new('RGBA', (Wd, Hd), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    od.rounded_rectangle((0, 0, Wd - 1, Hd - 1), radius=s(8), fill=ui.rgba((8, 34, 70), int(a * 0.93)), outline=ui.rgba(ui.CYAN_B, a), width=max(1, s(2)))
    fh = ui.font('bold', 26); fr = ui.font('bold', 20)
    od.text((s(40), s(24)), 'Topic includes', font=fh, fill=ui.rgba(ui.WHITE, a)); od.text((Wd - s(40) - ui.text_size(od, 'Time line', fh)[0], s(24)), 'Time line', font=fh, fill=ui.rgba(ui.WHITE, a))
    od.line((s(30), s(66), Wd - s(30), s(66)), fill=ui.rgba(ui.CYAN_B, int(a * 0.6)), width=max(1, s(1)))
    for i, (name, tl) in enumerate(e['topics']):
        yy = s(84 + i * e.get('row_h', 62)); od.text((s(48), yy), name, font=fr, fill=ui.rgba(ui.WHITE, a)); od.text((Wd - s(48) - ui.text_size(od, tl, fr)[0], yy + s(2)), tl, font=fr, fill=ui.rgba(ui.WHITE, a))
    img.alpha_composite(ov, (s(x), s(y)))

def draw_pill2(img, e, t, a, ui, s):
    ui.pill(img, e['x'], e['y'], e['text'], size=e.get('size', 15), pad=e.get('pad', (16, 6)), alpha=a, fill=e.get('fill', DEEP), border=e.get('border', ui.NAVY_B), center=e.get('center', True), color=e.get('color', ui.WHITE), min_w=e.get('min_w', 0))

def draw_apill(img, e, t, a, ui, s, H):
    p = H['anchors'](e['spec'], t).get(e['name'])
    if not p: return
    x, y = p[0] + e.get('dx', 110), p[1] + e.get('dy', -40); col = e.get('color', ui.WHITE)
    box = ui.pill(img, x, y, e['text'], size=e.get('size', 15), pad=(14, 5), alpha=a, fill=e.get('fill', DEEP), border=e.get('border', col), center=True, color=col)
    if e.get('leader', True):
        bx, by, bw, bh = box; d = ImageDraw.Draw(img)
        # leader from the nearest pill edge to a small ring on the anchor
        ex = min(max(p[0], bx), bx + bw); ey = by + bh if p[1] > by + bh else (by if p[1] < by else by + bh / 2)
        if bx <= p[0] <= bx + bw and by <= p[1] <= by + bh: return
        d.line((s(ex), s(ey), s(p[0]), s(p[1])), fill=ui.rgba(col, int(a * 0.85)), width=max(1, s(2)))
        d.ellipse((s(p[0]) - s(4), s(p[1]) - s(4), s(p[0]) + s(4), s(p[1]) + s(4)), outline=ui.rgba(col, a), width=max(1, s(2)))

def draw_bigtext(img, e, t, a, ui, s):
    d = ImageDraw.Draw(img); f = ui.font('bold', e.get('size', 22)); col = e.get('color', ui.WHITE); tw = ui.text_size(d, e['text'], f)[0]
    x = s(e['x']) - tw / 2; y = s(e['y'])
    _glow_layer(img, lambda dd: dd.text((x, y), e['text'], font=f, fill=ui.rgba(col, int(a * 0.6))), blur=s(5))
    d = ImageDraw.Draw(img); d.text((x, y), e['text'], font=f, fill=ui.rgba(col, a))

def draw_measure(img, e, t, a, ui, s, H):
    an = H['anchors'](e['spec'], t); pa, pb = an.get(e['a']), an.get(e['b'])
    if not (pa and pb): return
    col = e.get('color', ui.CYAN_B); p0, p1 = (s(pa[0]), s(pa[1])), (s(pb[0]), s(pb[1]))
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]; L = math.hypot(dx, dy)
    if L < 1: return
    nx, ny = -dy / L, dx / L; tk = s(9)
    def bar(dd):
        dd.line((*p0, *p1), fill=ui.rgba(col, int(a * 0.5)), width=max(2, s(8)))
    _glow_layer(img, bar, blur=s(3)); d = ImageDraw.Draw(img)
    d.line((*p0, *p1), fill=ui.rgba(col, a), width=max(1, s(3)))
    for p in (p0, p1): d.line((p[0] - nx * tk, p[1] - ny * tk, p[0] + nx * tk, p[1] + ny * tk), fill=ui.rgba(col, a), width=max(1, s(3)))
    if e.get('text'):
        mx, my = (pa[0] + pb[0]) / 2 + e.get('dx', 0), (pa[1] + pb[1]) / 2 + e.get('dy', 40)
        ui.pill(img, mx, my, e['text'], size=e.get('size', 14), pad=(12, 4), alpha=a, fill=DEEP, border=col, center=True, color=col)

def draw_trace(img, e, t, a, ui, s):
    x, y, w, h = e['x'], e['y'], e['w'], e['h']; win = e.get('window', 3.0); per = e['period']; t1 = e['t_first']
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle((s(x), s(y), s(x + w), s(y + h)), radius=s(6), fill=ui.rgba(DEEP, int(a * 0.8)), outline=ui.rgba(ui.NAVY_B, a), width=max(1, s(1)))
    base = y + h * 0.62; gold = (255, 190, 60); cyan = (80, 220, 255)
    def X(tt): return x + 16 + (w - 32) * (1 - (t - tt) / win)
    pts = []; k0 = int((t - win - t1) / per) - 1; k1 = int((t - t1) / per) + 1
    n = int(w / 2)
    for i in range(n + 1):
        tt = t - win + win * i / n; v = 0.0
        for k in range(max(0, k0), k1 + 1):
            for dt, amp, freq, col in ((e['lub'], 1.0, 34.0, gold), (e['dub'], 0.62, 46.0, cyan)):
                tb = t1 + k * per + dt; u = tt - tb
                if -0.02 < u < 0.16: v += amp * math.sin(u * freq * math.pi) * math.exp(-u * 18)
        pts.append((s(X(tt)), s(base - v * h * 0.42)))
    d.line(pts, fill=ui.rgba(ui.WHITE, int(a * 0.9)), width=max(1, s(2)))
    f = ui.font('bold', 14)
    for k in range(max(0, k0), k1 + 1):
        for dt, txt, col in ((e['lub'], 'Lub', gold), (e['dub'], 'Dub', cyan)):
            tb = t1 + k * per + dt
            if t - win + 0.15 < tb <= t:
                xx = s(X(tb)); ff = min(1.0, (t - tb) / 0.12)
                d.text((xx - s(12), s(y + 8)), txt, font=f, fill=ui.rgba(col, int(a * ff)))
                d.ellipse((xx - s(3), s(base) - s(3), xx + s(3), s(base) + s(3)), fill=ui.rgba(col, int(a * ff)))
    d.text((s(x + 12), s(y + h - 22)), 'heart sounds', font=ui.font('bold', 12), fill=ui.rgba((150, 175, 220), a))
    img.alpha_composite(lay)

PHASES = [('atria fill', 0.0, 0.22, (120, 170, 255)), ('atria contract', 0.22, 0.36, (255, 190, 60)), ('ventricles contract', 0.36, 0.7, (255, 120, 90)), ('relax', 0.7, 1.0, (80, 220, 255))]
def draw_cyclebar(img, e, t, a, ui, s):
    x, y, w = e['x'], e['y'], e['w']; per = e['period']; t1 = e['t_first']; h = 26
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); f = ui.font('bold', 13); fb = ui.font('bold', 16)
    d.rounded_rectangle((s(x - 14), s(y - 40), s(x + w + 14), s(y + h + 40)), radius=s(6), fill=ui.rgba(DEEP, int(a * 0.8)), outline=ui.rgba(ui.NAVY_B, a), width=max(1, s(1)))
    for name, u0, u1, col in PHASES:
        d.rounded_rectangle((s(x + w * u0) + 1, s(y), s(x + w * u1) - 1, s(y + h)), radius=s(3), fill=ui.rgba(col, int(a * 0.55)))
        d.text((s(x + w * (u0 + u1) / 2) - ui.text_size(d, name, f)[0] / 2, s(y + h + 6)), name, font=f, fill=ui.rgba(ui.WHITE, a))
    u = ((t - t1) / per) % 1.0 if t >= t1 else 0.0; cyc = int((t - t1) / per) + 1 if t >= t1 else 0
    xx = s(x + w * u); d.polygon([(xx, s(y - 4)), (xx - s(7), s(y - 16)), (xx + s(7), s(y - 16))], fill=ui.rgba(ui.WHITE, a))
    d.line((xx, s(y), xx, s(y + h)), fill=ui.rgba(ui.WHITE, a), width=max(1, s(2)))
    d.text((s(x), s(y - 36)), f'one cycle = {per:.2f} s', font=fb, fill=ui.rgba((255, 190, 60), a))
    if cyc: d.text((s(x + w) - ui.text_size(d, f'cycle {cyc}', fb)[0], s(y - 36)), f'cycle {cyc}', font=fb, fill=ui.rgba(ui.WHITE, a))
    img.alpha_composite(lay)

def _keyed(keys, t):
    if t <= keys[0][0]: return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys[:-1], keys[1:]):
        if t0 <= t <= t1:
            u = (t - t0) / max(1e-6, t1 - t0); u = u * u * (3 - 2 * u); return _lerp(v0, v1, u)
    return keys[-1][1]

def draw_gauge(img, e, t, a, ui, s, H):
    p = H['anchors'](e['spec'], t).get(e['name'])
    if not p: return
    v = _keyed(e['keys'], t); hi = v > 100; col = (255, 190, 60) if hi else (80, 220, 255)
    ui.pill(img, p[0] + e.get('dx', 0), p[1] + e.get('dy', -40), f'{int(round(v))} mm Hg', size=20, pad=(16, 6), alpha=a, fill=DEEP, border=col, center=True, color=col)

def draw_counter(img, e, t, a, ui, s, H):
    n = sum(1 for tp in e['passes'] if t >= tp); last = max([tp for tp in e['passes'] if t >= tp], default=None)
    flash = 0.0 if last is None else max(0.0, 1 - (t - last) / 0.6)
    col = (255, 190, 60); txt = f'through the heart:  {n}'
    box = ui.pill(img, e['x'], e['y'], txt, size=18, pad=(18, 7), alpha=a, fill=DEEP, border=col, center=True, color=ui.WHITE)
    if flash > 0:
        bx, by, bw, bh = box
        _glow_layer(img, lambda d: d.rounded_rectangle((s(bx) - s(6), s(by) - s(6), s(bx + bw) + s(6), s(by + bh) + s(6)), radius=s(6), outline=ui.rgba(col, int(a * flash)), width=max(2, s(4))), blur=s(4))
    p = H['anchors'](e['spec'], t).get(e.get('name', ''))
    if p and flash > 0:
        _glow_layer(img, lambda d: d.ellipse((s(p[0]) - s(26), s(p[1]) - s(26), s(p[0]) + s(26), s(p[1]) + s(26)), outline=ui.rgba(col, int(a * flash)), width=max(2, s(4))), blur=s(3))

def draw_markers(img, e, t, a, ui, s, H):
    an = H['anchors'](e['spec'], t); f = ui.font('bold', 12); fs = ui.font('bold', 8); d = ImageDraw.Draw(img); seen = set()
    for name, p in an.items():
        for prefix, txt, col in e['groups']:
            if name.startswith(prefix):
                H['glow_circle'](img, p[0], p[1], 7, col, None, 10, a, ring=True)
                if prefix not in seen:                                     # one label per group, on its first visible marker
                    seen.add(prefix); d = ImageDraw.Draw(img); ui.sub_text(d, s(p[0] + 12), s(p[1] - 18), txt, f, fs, ui.rgba(col, a))
                break

def draw_loop(img, e, t, a, ui, s):
    col = e.get('color', (255, 190, 60))
    box = ui.pill(img, e['x'], e['y'], e['text'], size=22, pad=(22, 8), alpha=a, fill=DEEP, border=col, center=True, color=col)
    if e.get('sub'):
        bx, by, bw, bh = box; ui.pill(img, e['x'], by + bh + 22, e['sub'], size=15, pad=(14, 5), alpha=a, fill=DEEP, border=ui.NAVY_B, center=True, color=ui.WHITE)

def draw_toggle(img, e, t, a, ui, s):
    per = e['period']; u = ((t - e['t_first']) / per) % 1.0 if t >= e['t_first'] else 1.0
    txt, col = e['items'][0] if u < e.get('split', 0.5) else e['items'][1]
    ui.pill(img, e['x'], e['y'], txt, size=e.get('size', 18), pad=(18, 7), alpha=a, fill=DEEP, border=col, center=True, color=col)

def draw_extra(img, e, t, spec, ui, H):
    k = e['kind']; a = H['alpha']; s = H['s']; e = dict(e, spec=spec)
    if k == 'table6': draw_table6(img, e, t, a, ui, s)
    elif k == 'pill2': draw_pill2(img, e, t, a, ui, s)
    elif k == 'apill': draw_apill(img, e, t, a, ui, s, H)
    elif k == 'bigtext': draw_bigtext(img, e, t, a, ui, s)
    elif k == 'measure': draw_measure(img, e, t, a, ui, s, H)
    elif k == 'trace': draw_trace(img, e, t, a, ui, s)
    elif k == 'cyclebar': draw_cyclebar(img, e, t, a, ui, s)
    elif k == 'gauge': draw_gauge(img, e, t, a, ui, s, H)
    elif k == 'counter': draw_counter(img, e, t, a, ui, s, H)
    elif k == 'markers': draw_markers(img, e, t, a, ui, s, H)
    elif k == 'loop': draw_loop(img, e, t, a, ui, s)
    elif k == 'toggle': draw_toggle(img, e, t, a, ui, s)
    else: print('unknown overlay kind', k)
