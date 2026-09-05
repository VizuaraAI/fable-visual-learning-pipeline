"""Chapter palette for 'Human Heart and Circulation': one designed set of named colours shared by every Blender builder
(linear floats) and by the PIL overlay (8-bit sRGB, the *_2D twins / the C2D dict).
Look: a navy void ground; oxygenated blood a rich crimson with a warm glow, deoxygenated blood an indigo violet-blue;
cardiac muscle a deep wine-red under a wet pericardial coat, endocardium a pale rose with a faint warm emission; bone ivory;
lungs dusty salmon; skin a translucent warm amber rim; labels and accents in ONE warm gold and ONE cool cyan.
Semantic colours (OXY / DEOXY, O2 / CO2, systolic gold / diastolic cyan) are identical in every 3D shot and on the overlay.
Each section gets its own lighting theme (THEME[section]: key temperature, rim colour, fill, accent) inside this one look."""

def lin2srgb(v):
    v = max(0.0, min(1.0, v))
    return 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055

def srgb8(c): return tuple(int(round(255 * lin2srgb(v))) for v in c[:3])

def mix(a, b, u): return tuple(a[i] + (b[i] - a[i]) * u for i in range(3))

def scale(c, k): return tuple(min(1.0, v * k) for v in c)

# ---- ground and blood (the two semantic colours of the whole chapter)
VOID = (0.0025, 0.004, 0.009)          # navy void world colour
OXY = (0.60, 0.028, 0.030)             # oxygenated blood: rich crimson
OXY_LIT = (1.00, 0.14, 0.08)           # its emission / glow / highlight
DEOXY = (0.095, 0.075, 0.46)           # deoxygenated blood: indigo violet-blue
DEOXY_LIT = (0.30, 0.26, 0.98)         # its emission / glow

# ---- tissue
MUSCLE = (0.36, 0.045, 0.055)          # cardiac muscle: deep wine-red
MUSCLE_DK = (0.17, 0.018, 0.028)       # its blotch / groove shadow tone
MUSCLE_LIT = (0.62, 0.12, 0.10)        # its lit fibre highlight
CUT = (0.42, 0.040, 0.048)             # sliced myocardium (cut face)
CUT_FIBRE = (0.64, 0.14, 0.12)         # the lighter fibre streak on the cut face
ENDO = (0.86, 0.40, 0.40)              # endocardium lining: pale rose
ENDO_EMIT = (1.00, 0.55, 0.45)         # its faint warm emission
ENDO_R = (0.55, 0.36, 0.62)            # right-side lining, rose tinted toward the deoxygenated violet
ENDO_L = (0.92, 0.36, 0.34)            # left-side lining, rose tinted toward crimson
VALVE = (0.94, 0.80, 0.70)             # valve leaflets / cusps: pale ivory-pink, translucent
CHORDAE = (0.96, 0.92, 0.86)           # chordae tendineae: pearly white cords
FAT = (0.86, 0.70, 0.40)               # epicardial fat pads in the grooves
BONE = (0.90, 0.85, 0.72)              # ivory bone
CARTILAGE = (0.80, 0.86, 0.82)         # costal cartilage: pale blue-white
LUNG = (0.80, 0.40, 0.34)              # lungs: dusty salmon
LUNG_RIM = (1.00, 0.62, 0.50)          # lung rim glow
SKIN = (0.88, 0.50, 0.28)              # skin silhouette: warm amber
SKIN_RIM = (1.00, 0.72, 0.42)          # skin fresnel rim
CAPILLARY = (0.82, 0.55, 0.50)         # capillary endothelium (single cells)
NUCLEUS = (0.40, 0.18, 0.45)           # endothelial cell nucleus: plum
ARTERY_WALL = (0.72, 0.30, 0.28)       # artery media (thick muscular/elastic layer)
INTIMA = (0.92, 0.66, 0.62)            # inner endothelium layer of a vessel
ADVENTITIA = (0.86, 0.74, 0.56)        # outer connective sheath
VEIN_WALL = (0.42, 0.36, 0.62)         # vein wall (thin, violet-grey)
ORGAN = (0.62, 0.36, 0.34)             # body organs (brain / muscle / kidney) in the circulation rig
BRAIN = (0.86, 0.68, 0.62)
KIDNEY = (0.55, 0.16, 0.16)
HAEMOGLOBIN = (0.95, 0.10, 0.06)       # the red pigment inside a red cell
HAEM_IRON = (1.00, 0.55, 0.20)         # the iron centre glow

# ---- particles
O2 = (1.00, 0.85, 0.55)                # oxygen: warm gold-white
CO2 = (0.55, 0.50, 0.90)               # carbon dioxide: cool violet
NUTRIENT = (0.55, 0.95, 0.45)          # nutrients: soft green
WASTE = (0.50, 0.46, 0.44)             # waste: grey
PLASMA = (1.00, 0.85, 0.70)            # plasma motes (warm, catch the key)
DUST = (0.70, 0.80, 1.00)              # void dust (cool, catch the rim)

# ---- accents (labels, gauges, highlights) : ONE warm, ONE cool
GOLD = (1.00, 0.70, 0.20)
CYAN = (0.28, 0.85, 1.00)
DANGER = (1.00, 0.22, 0.10)            # hypertension warning tint
WHITE = (1.0, 1.0, 1.0)

# ---- instruments
CHROME = (0.85, 0.86, 0.88)
RUBBER = (0.05, 0.05, 0.06)
CUFF = (0.12, 0.20, 0.42)              # sphygmomanometer cuff fabric: slate blue
DIAL = (0.96, 0.95, 0.90)              # gauge face: warm white
NEEDLE = (0.90, 0.10, 0.08)

# ---- per-section lighting themes (key colour temperature, rim colour, fill colour, accent) inside the one chapter look
THEME = {
    0: dict(key=(1.00, 0.93, 0.84), rim=(0.55, 0.75, 1.00), fill=(0.60, 0.70, 1.00), accent=GOLD),      # intro: warm key, cool rim
    1: dict(key=(1.00, 0.90, 0.78), rim=(0.70, 0.85, 1.00), fill=(0.65, 0.72, 1.00), accent=GOLD),      # the heart: amber key
    2: dict(key=(1.00, 0.96, 0.92), rim=(0.40, 0.82, 1.00), fill=(0.55, 0.75, 1.00), accent=CYAN),      # chambers: clean key, cyan rim
    3: dict(key=(1.00, 0.86, 0.72), rim=(1.00, 0.55, 0.45), fill=(0.70, 0.60, 0.90), accent=GOLD),      # one heartbeat: warm, pulsing
    4: dict(key=(0.95, 0.96, 1.00), rim=(0.50, 0.70, 1.00), fill=(0.45, 0.60, 1.00), accent=CYAN),      # vessels: cool blue
    5: dict(key=(1.00, 0.92, 0.82), rim=(0.62, 0.55, 1.00), fill=(0.55, 0.55, 1.00), accent=GOLD),      # double circulation: violet rim
    6: dict(key=(1.00, 0.88, 0.76), rim=(1.00, 0.45, 0.30), fill=(0.80, 0.55, 0.60), accent=GOLD),      # blood pressure: red rim
}

# ---- 8-bit twins for the overlay: every 3-tuple colour above gets NAME_2D, plus the C2D dict
C2D = {}
for _k, _v in list(globals().items()):
    if isinstance(_v, tuple) and len(_v) == 3 and all(isinstance(x, (int, float)) for x in _v) and _k.isupper():
        C2D[_k] = srgb8(_v)
for _k, _v in list(C2D.items()): globals()[_k + '_2D'] = _v
# brighter label colours for text on the navy ground (linear glow colours map to readable sRGB)
LABEL_OXY = srgb8(OXY_LIT); LABEL_DEOXY = srgb8(DEOXY_LIT); LABEL_GOLD = srgb8(GOLD); LABEL_CYAN = srgb8(CYAN)
LABEL_O2 = srgb8(O2); LABEL_CO2 = srgb8(CO2); LABEL_NUTRIENT = srgb8(NUTRIENT); LABEL_WASTE = srgb8(scale(WASTE, 1.6))
LABEL_DANGER = srgb8(DANGER); LABEL_MUSCLE = srgb8(scale(MUSCLE_LIT, 1.5)); LABEL_BONE = srgb8(BONE); LABEL_LUNG = srgb8(LUNG_RIM)
PILL_FILL = (10, 24, 56)               # navy pill fill used by the overlay's coloured pills
