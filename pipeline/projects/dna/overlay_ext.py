"""DNA-chapter 2D overlay elements. overlay.draw_event() calls draw_extra() for every kind it does not know.
All coordinates in 1280x720 space (helpers['s'] scales to the output). Kinds:
  table6        six-row 'Topic includes / Time line' table (the built-in 'table' is sized for three rows)
  text          bold white text, optional timed parts, x/left or cx/centre; understands _1 subscripts and ^{..} superscripts
  anchor_label  a small navy pill tied to a 3D anchor by a leader line and a dot (colour = border/text tint), dx/dy offset
  ptr_text      text with an arrow pointing at an anchor
  pill2         pill with custom fill/border colours
  base_ticker   the four (or five) letters in their palette colours lighting one after another, names beneath
  codon_strip   the message letters in a row with a three-letter reading window stepping along, then holding on one codon
  legend64      a miniature 8x8 codon table coloured by amino acid, with timed highlighted tiles
  letter_row    coloured letter tiles with arrows ('GAG -> GUG'); a tile can swap its letter at a given time
  dogma_row     DNA -> RNA -> Protein pills, arrows lighting at their spoken times"""
import re, math, sys, os
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from projects.dna.palette import BASE_2D, AMINO_2D, STOP_2D, START_2D, CODON, NAMES, AMBER_2D, ICE_2D

_TOK = re.compile(r'(\^\{[^}]*\}|_\{[^}]*\}|_\d)')
DEEP = (8, 26, 58); BORDER = (46, 127, 224); NAVY = (11, 26, 62)

def rich(d, x, y, txt, size, fill, ui, fnt='bold', measure=False):
    f = ui.font(fnt, size); fs = ui.font(fnt, max(8, int(size * 0.62))); cx = x
    for p in _TOK.split(txt):
        if not p: continue
        if p.startswith('^{'):
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

def _arrow(d, p0, p1, col, s, width=2, head=9):
    (x0, y0), (x1, y1) = p0, p1; d.line((x0, y0, x1, y1), fill=col, width=max(1, s(width)))
    ang = math.atan2(y1 - y0, x1 - x0); hl = s(head)
    d.polygon([(x1, y1), (x1 - hl * math.cos(ang - 0.42), y1 - hl * math.sin(ang - 0.42)), (x1 - hl * math.cos(ang + 0.42), y1 - hl * math.sin(ang + 0.42))], fill=col)

def _tint(c, k=0.35): return tuple(int(v * k) for v in c)

def draw_table6(img, e, t, a, ui, s):
    x, y, w, h = e.get('x', 140), e.get('y', 196), e.get('w', 1000), e.get('h', 470); Wd, Hd = s(w), s(h)
    ov = Image.new('RGBA', (Wd, Hd), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    od.rounded_rectangle((0, 0, Wd - 1, Hd - 1), radius=s(8), fill=ui.rgba((8, 34, 70), int(a * 0.93)), outline=ui.rgba(ui.CYAN_B, a), width=max(1, s(2)))
    fh = ui.font('bold', 26); fr = ui.font('bold', 20)
    od.text((s(40), s(24)), 'Topic includes', font=fh, fill=ui.rgba(ui.WHITE, a)); od.text((Wd - s(40) - ui.text_size(od, 'Time line', fh)[0], s(24)), 'Time line', font=fh, fill=ui.rgba(ui.WHITE, a))
    for i, (name, tl) in enumerate(e['topics']):
        yy = s(88 + i * e.get('row_h', 60)); od.text((s(48), yy), name, font=fr, fill=ui.rgba(ui.WHITE, a)); od.text((Wd - s(48) - ui.text_size(od, tl, fr)[0], yy + s(2)), tl, font=fr, fill=ui.rgba(ui.WHITE, a))
    img.alpha_composite(ov, (s(x), s(y)))

def draw_text(img, e, t, a, ui, s):
    d = ImageDraw.Draw(img); size = e.get('size', 20); col = e.get('color', ui.WHITE)
    parts = e.get('parts') or [(e['text'], e['t0'])]
    widths = [rich(d, 0, 0, p[0], size, None, ui, measure=True) for p in parts]; total = sum(widths)
    x = s(e['x']) if 'x' in e else s(e['cx']) - total / 2; y = s(e['y'])
    for (txt, ts), w in zip(parts, widths):
        if t >= ts: rich(d, x, y, txt, size, ui.rgba(col, int(a * ui.fade_in(t, ts, 0.4))), ui)
        x += w

def draw_anchor_label(img, e, t, a, ui, s, H):
    p = H['anchors'](e['spec'], t).get(e['name'])
    if not p: return
    col = e.get('color', ICE_2D); size = e.get('size', 15); dx, dy = e.get('dx', 90), e.get('dy', -60)
    tx, ty = p[0] + dx, p[1] + dy
    d = ImageDraw.Draw(img); f = ui.font('bold', size); tw = rich(d, 0, 0, e['text'], size, None, ui, measure=True)
    w = tw + s(28); h = f.size + s(12); X, Y = s(tx) - w / 2, s(ty) - h / 2
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    ex = X + (0 if p[0] < tx else w) if abs(p[0] - tx) > w / (2 * ui.SC) + 8 else X + w / 2; ey = Y + h / 2 if abs(p[0] - tx) > w / (2 * ui.SC) + 8 else (Y + h if p[1] > ty else Y)
    ld.line((ex, ey, s(p[0]), s(p[1])), fill=ui.rgba(col, int(a * 0.85)), width=max(1, s(2)))
    r = s(4); ld.ellipse((s(p[0]) - r, s(p[1]) - r, s(p[0]) + r, s(p[1]) + r), fill=ui.rgba(col, a))
    ld.rounded_rectangle((X, Y, X + w, Y + h), radius=s(4), fill=ui.rgba(NAVY, int(a * 0.92)), outline=ui.rgba(col, a), width=max(1, s(1.5)))
    img.alpha_composite(lay); d = ImageDraw.Draw(img)
    rich(d, X + s(14), Y + s(6) - f.size * 0.12, e['text'], size, ui.rgba(e.get('text_color', ui.WHITE), a), ui)

def draw_ptr_text(img, e, t, a, ui, s, H):
    p = H['anchors'](e['spec'], t).get(e['name'])
    if not p: return
    d = ImageDraw.Draw(img); size = e.get('size', 18); col = e.get('color', ui.WHITE); acol = e.get('arrow_color', ui.WHITE)
    tx, ty = p[0] + e['dx'], p[1] + e.get('dy', 0); f = ui.font('bold', size); tw = rich(d, 0, 0, e['text'], size, None, ui, measure=True)
    rich(d, s(tx) - tw / 2, s(ty) - f.size * 0.6, e['text'], size, ui.rgba(col, a), ui)
    sgn = 1 if p[0] > tx else -1; x0 = s(tx) + sgn * (tw / 2 + s(10)); x1 = s(p[0]) - sgn * s(e.get('gap', 26)); y1 = s(p[1])
    _arrow(d, (x0, s(ty)), (x1, y1), ui.rgba(acol, a), s, width=3, head=12)

def draw_pill2(img, e, t, a, ui, s):
    ui.pill(img, e['x'], e['y'], e['text'], size=e.get('size', 15), pad=e.get('pad', (16, 6)), alpha=a, fill=e.get('fill', DEEP), border=e.get('border', BORDER), center=e.get('center', True), color=e.get('color', ui.WHITE), min_w=e.get('min_w', 0))

def _tile(lay, ld, x, y, w, h, letter, col, a, ui, s, size=22, lit=1.0, radius=5):
    fill = ui.rgba(_tint(col, 0.30 + 0.25 * lit), int(a * (0.75 + 0.2 * lit))); ld.rounded_rectangle((x, y, x + w, y + h), radius=s(radius), fill=fill, outline=ui.rgba(col, int(a * (0.45 + 0.55 * lit))), width=max(1, s(1.5 if lit < 1 else 2.5)))
    f = ui.font('bold', size); tw, th = ui.text_size(ld, letter, f); ld.text((x + (w - tw) / 2, y + (h - th) / 2 - f.size * 0.16), letter, font=f, fill=ui.rgba(ui.WHITE if lit > 0.5 else (200, 210, 230), int(a * (0.7 + 0.3 * lit))))

def draw_base_ticker(img, e, t, a, ui, s):
    letters = e.get('letters', 'ATGC'); times = e['times']; cx, y = e.get('cx', 640), e.get('y', 600); tile = e.get('tile', 44); gap = e.get('gap', 22); names = e.get('names', True)
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(lay); n = len(letters); total = n * tile + (n - 1) * gap; x0 = cx - total / 2
    for k, L in enumerate(letters):
        if t < times[k]: continue
        aa = int(a * ui.fade_in(t, times[k], 0.3)); x = s(x0 + k * (tile + gap)); col = BASE_2D[L]
        _tile(lay, ld, x, s(y), s(tile), s(tile), L, col, aa, ui, s, size=24)
        if names:
            f = ui.font('bold', 12); nm = NAMES[L]; tw = ui.text_size(ld, nm, f)[0]; ld.text((x + s(tile) / 2 - tw / 2, s(y + tile + 6)), nm, font=f, fill=ui.rgba(col, aa))
    img.alpha_composite(lay)

def draw_codon_strip(img, e, t, a, ui, s):
    seq = e['seq']; t0, step = e['t0_win'], e.get('step', 0.62); hold = e.get('hold'); t_hold = e.get('t_hold', 1e9)
    cx, y = e.get('cx', 640), e.get('y', 612); tile = e.get('tile', 30); gap = e.get('gap', 6); n = len(seq); total = n * tile + (n - 1) * gap; x0 = cx - total / 2
    if t >= t_hold and hold is not None: win = hold
    elif t >= t0: win = min(n // 3 - 1, int((t - t0) / step))
    else: win = None
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    if win is not None:
        wx = s(x0 + 3 * win * (tile + gap) - 5); ww = s(3 * tile + 2 * gap + 10)
        ld.rounded_rectangle((wx, s(y - 6), wx + ww, s(y + tile + 6)), radius=s(7), fill=ui.rgba(AMBER_2D, int(a * 0.25)), outline=ui.rgba(AMBER_2D, a), width=max(1, s(2)))
    for k, L in enumerate(seq):
        lit = 1.0 if (win is not None and 3 * win <= k < 3 * win + 3) else 0.35
        _tile(lay, ld, s(x0 + k * (tile + gap)), s(y), s(tile), s(tile), L, BASE_2D[L], a, ui, s, size=17, lit=lit, radius=4)
    for j in range(1, n // 3):                                # thin ticks between codons
        xx = s(x0 + 3 * j * (tile + gap) - gap / 2); ld.line((xx, s(y - 4), xx, s(y + tile + 4)), fill=ui.rgba(ui.WHITE, int(a * 0.35)), width=max(1, s(1)))
    if e.get('label') and win is not None and t >= e.get('t_label', t0):
        f = ui.font('bold', 14); txt = e['label']; tw = ui.text_size(ld, txt, f)[0]; wx = x0 + 3 * win * (tile + gap) + (3 * tile + 2 * gap) / 2
        ld.text((s(wx) - tw / 2, s(y - 26)), txt, font=f, fill=ui.rgba(AMBER_2D, a))
    img.alpha_composite(lay)

def draw_legend64(img, e, t, a, ui, s):
    x, y = e.get('x', 1010), e.get('y', 430); tile = e.get('tile', 24); gap = 3; B = 'UCAG'
    hl = {}
    for cd, th in e.get('highlights', []):
        if t >= th: hl[cd] = ui.fade_in(t, th, 0.3)
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    W = 8 * tile + 7 * gap; ld.rounded_rectangle((s(x - 10), s(y - 10), s(x + W + 10), s(y + W + 10)), radius=s(6), fill=ui.rgba(NAVY, int(a * 0.85)), outline=ui.rgba(BORDER, a), width=max(1, s(1)))
    k = 0
    for a1 in B:
        for a2 in B:
            for a3 in B:
                cd = a1 + a2 + a3; col, row = k % 8, k // 8; aa = CODON[cd]; c = STOP_2D if aa == 'Stop' else (START_2D if cd == 'AUG' else AMINO_2D[aa])
                xx, yy = s(x + col * (tile + gap)), s(y + row * (tile + gap)); lit = hl.get(cd, 0.0)
                ld.rounded_rectangle((xx, yy, xx + s(tile), yy + s(tile)), radius=s(3), fill=ui.rgba(_tint(c, 0.45 + 0.55 * lit), int(a * (0.8 + 0.2 * lit))), outline=ui.rgba(ui.WHITE if lit else c, int(a * (0.3 + 0.7 * lit))), width=max(1, s(1 + lit)))
                if lit and tile >= 18:                      # the mini legend (tile < 18) only outlines its lit tiles: the letter_row below the wall names them
                    f = ui.font('bold', 9); tw = ui.text_size(ld, cd, f)[0]; ld.text((xx + s(tile) / 2 - tw / 2, yy + s(tile) / 2 - f.size * 0.6), cd, font=f, fill=ui.rgba(ui.WHITE, int(a * lit)))
                k += 1
    if e.get('title'):
        f = ui.font('bold', 13 if tile >= 18 else 11); ld.text((s(x), s(y - (30 if tile >= 18 else 26))), e['title'], font=f, fill=ui.rgba(ui.WHITE, a))
    img.alpha_composite(lay)

def draw_letter_row(img, e, t, a, ui, s):
    parts = e['parts']; swap = e.get('swap', {}); cx, y = e.get('cx', 640), e.get('y', 600); tile = e.get('tile', 40); gap = e.get('gap', 8); arrow_w = e.get('arrow_w', 46)
    items = []
    for i, (txt, col) in enumerate(parts):
        if i in swap and t >= swap[i][2]: txt, col = swap[i][0], swap[i][1]
        items.append((txt, col, i in swap and t >= swap[i][2] and t < swap[i][2] + 0.8))
    total = sum((arrow_w if txt == '→' else (tile if len(txt) == 1 else tile * len(txt) * 0.8)) for txt, col, fl in items) + gap * (len(items) - 1); x = cx - total / 2
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    for txt, col, flash in items:
        if txt in ('–', '-'):                                   # a pairing bar between two letters, not a tile
            ld.line((s(x + 4), s(y + tile / 2), s(x + tile - 4), s(y + tile / 2)), fill=ui.rgba(col, a), width=max(1, s(3))); x += tile + gap; continue
        if txt == '→':
            _arrow(ld, (s(x + 6), s(y + tile / 2)), (s(x + arrow_w - 6), s(y + tile / 2)), ui.rgba(ui.WHITE, a), s, width=3, head=11); x += arrow_w + gap; continue
        w = tile if len(txt) == 1 else tile * len(txt) * 0.8
        _tile(lay, ld, s(x), s(y), s(w), s(tile), txt, col, a, ui, s, size=22 if len(txt) == 1 else 16, lit=1.0)
        if flash: ld.rounded_rectangle((s(x - 4), s(y - 4), s(x + w + 4), s(y + tile + 4)), radius=s(7), outline=ui.rgba(ui.WHITE, int(a * 0.8)), width=max(1, s(2)))
        x += w + gap
    if e.get('caption') and t >= e.get('t_caption', e['t0']):
        f = ui.font('bold', 13); tw = ui.text_size(ld, e['caption'], f)[0]; ld.text((s(cx) - tw / 2, s(y + tile + 8)), e['caption'], font=f, fill=ui.rgba(e.get('caption_color', ui.WHITE), a))
    img.alpha_composite(lay)

def draw_dogma_row(img, e, t, a, ui, s):
    cx, y = e.get('cx', 640), e.get('y', 630); labels = e.get('labels', ['DNA', 'RNA', 'Protein']); cols = e.get('colors', [ICE_2D, AMBER_2D, (255, 150, 160)]); t_arr = e.get('t_arrows', [e['t0'], e['t0']]); t_lab = e.get('t_labels', [e['t0']] * 3)
    d = ImageDraw.Draw(img); f = ui.font('bold', 18); ws = [ui.text_size(d, L, f)[0] + s(32) for L in labels]; aw = s(70); total = sum(ws) + aw * (len(labels) - 1); x = s(cx) - total / 2
    for i, L in enumerate(labels):
        if t >= t_lab[i]:
            aa = int(a * ui.fade_in(t, t_lab[i], 0.35)); ui.pill(img, x / ui.SC, y, L, size=18, pad=(16, 6), alpha=aa, fill=_tint(cols[i], 0.25), border=cols[i])
        x += ws[i]
        if i < len(labels) - 1:
            if t >= t_arr[i]:
                aa = int(a * ui.fade_in(t, t_arr[i], 0.4)); d = ImageDraw.Draw(img); _arrow(d, (x + s(10), s(y) + f.size * 0.75), (x + aw - s(10), s(y) + f.size * 0.75), ui.rgba(ui.WHITE, aa), s, width=3, head=12)
            x += aw

def draw_extra(img, e, t, spec, ui, H):
    k = e['kind']; a = H['alpha']; s = H['s']; e = dict(e, spec=spec)
    if k == 'table6': draw_table6(img, e, t, a, ui, s)
    elif k == 'text': draw_text(img, e, t, a, ui, s)
    elif k == 'anchor_label': draw_anchor_label(img, e, t, a, ui, s, H)
    elif k == 'ptr_text': draw_ptr_text(img, e, t, a, ui, s, H)
    elif k == 'pill2': draw_pill2(img, e, t, a, ui, s)
    elif k == 'base_ticker': draw_base_ticker(img, e, t, a, ui, s)
    elif k == 'codon_strip': draw_codon_strip(img, e, t, a, ui, s)
    elif k == 'legend64': draw_legend64(img, e, t, a, ui, s)
    elif k == 'letter_row': draw_letter_row(img, e, t, a, ui, s)
    elif k == 'dogma_row': draw_dogma_row(img, e, t, a, ui, s)
    else: print('unknown overlay kind', k)
