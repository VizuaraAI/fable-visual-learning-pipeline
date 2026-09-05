"""The chapter's designed palette: one harmonious set shared by the Blender builders (linear floats) and the PIL overlay (8-bit).
Semantic colours never change across the video: A mint, T coral, G cobalt, C amber, U orchid (RNA only, so 'U replaces T'
reads at a glance); sugar pearl, phosphate ice-blue, mRNA amber, cytoplasm teal, nucleus amethyst, ribosome lavender/rose,
tRNA sea-teal, haemoglobin crimson/indigo, red cells crimson.  The navy void is the ground of every shot; each section adds
its own lighting theme (THEMES: key temperature, fill, rim colour, accent) inside that one look."""
BASE = {'A': (0.20, 0.82, 0.46), 'T': (0.97, 0.34, 0.24), 'G': (0.18, 0.44, 0.98), 'C': (0.99, 0.72, 0.14), 'U': (0.74, 0.28, 0.96)}
BASE_2D = {'A': (86, 232, 150), 'T': (255, 128, 96), 'G': (96, 150, 255), 'C': (255, 206, 72), 'U': (214, 118, 250)}
NAMES = {'A': 'Adenine', 'T': 'Thymine', 'G': 'Guanine', 'C': 'Cytosine', 'U': 'Uracil'}
PURINE = {'A', 'G'}                                             # two fused rings; T, C, U are single-ring pyrimidines
COMP = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G'}                 # DNA pairing
RNA_OF = {'A': 'U', 'T': 'A', 'G': 'C', 'C': 'G'}               # template base -> RNA base
RNA_COMP = {'A': 'U', 'U': 'A', 'G': 'C', 'C': 'G'}             # codon <-> anticodon pairing
SUGAR = (0.95, 0.92, 0.84); PHOS = (0.40, 0.70, 1.00); PHOS_O = (0.86, 0.94, 1.00)
RAIL_A = (0.60, 0.70, 0.92); RAIL_B = (0.80, 0.86, 0.98)
RNA_RAIL = (0.98, 0.62, 0.18); RNA_SUGAR = (1.00, 0.88, 0.60)
HBOND = (0.75, 0.92, 1.00)
NAVY = (0.0025, 0.004, 0.009)
CYTO = (0.03, 0.22, 0.26); CYTO_RIM = (0.20, 0.85, 0.90)         # teal cytoplasm
NUC = (0.42, 0.22, 0.86); NUC_RIM = (0.78, 0.60, 1.00)           # amethyst nucleus
PORE = (0.96, 0.55, 0.66); PORE_FIL = (0.80, 0.62, 1.00)
CHROM = (0.34, 0.40, 0.96); HISTONE = (0.88, 0.80, 0.98)
POL = (0.14, 0.62, 0.56); POL_2 = (0.22, 0.78, 0.70)
RIBO_L = (0.46, 0.34, 0.86); RIBO_S = (0.88, 0.50, 0.70)
SITE = {'A': (0.20, 0.82, 0.46), 'P': (0.99, 0.72, 0.14), 'E': (0.74, 0.28, 0.96)}      # tRNA sites on the ribosome
TRNA = (0.14, 0.70, 0.66); TRNA_2 = (0.34, 0.88, 0.82)
PEPTIDE = (0.92, 0.92, 0.96); GENE = (1.00, 0.76, 0.30)
HB_ALPHA = (0.86, 0.16, 0.16); HB_BETA = (0.26, 0.30, 0.90); HEME = (0.45, 0.06, 0.05); IRON = (0.98, 0.55, 0.12); O2 = (0.55, 0.88, 1.00)
RBC = (0.78, 0.06, 0.05); MITO = (0.85, 0.30, 0.20); VESICLE = (0.95, 0.75, 0.30); ER = (0.30, 0.62, 0.72)
AMINO = {'Met': (0.90, 0.18, 0.18), 'Gly': (0.94, 0.94, 0.90), 'Pro': (0.95, 0.55, 0.12), 'Glu': (0.88, 0.16, 0.56), 'Val': (0.16, 0.84, 0.80),
         'Ala': (0.55, 0.85, 0.30), 'Leu': (0.30, 0.60, 0.95), 'Ser': (0.98, 0.85, 0.35), 'Thr': (0.85, 0.65, 0.95), 'Lys': (0.20, 0.35, 0.95),
         'Arg': (0.10, 0.20, 0.75), 'Asp': (0.95, 0.30, 0.30), 'Asn': (0.95, 0.60, 0.70), 'Gln': (0.80, 0.45, 0.85), 'His': (0.35, 0.75, 0.95),
         'Phe': (0.60, 0.40, 0.20), 'Tyr': (0.75, 0.60, 0.25), 'Trp': (0.45, 0.25, 0.55), 'Cys': (0.98, 0.95, 0.55), 'Ile': (0.20, 0.70, 0.45)}
AMINO_2D = {k: tuple(int(255 * (c ** (1 / 2.2))) for c in v) for k, v in AMINO.items()}
AMINO_FULL = {'Met': 'Methionine', 'Gly': 'Glycine', 'Pro': 'Proline', 'Glu': 'Glutamic acid', 'Val': 'Valine'}
STOP = (0.95, 0.12, 0.10); START = (0.20, 0.82, 0.46)
STOP_2D = (255, 70, 60); START_2D = (86, 232, 150)
AMBER_2D = (255, 178, 70); ICE_2D = (150, 210, 255); PEARL_2D = (245, 240, 225); TEAL_2D = (90, 220, 220); ORCHID_2D = (214, 118, 250)

# Per-section lighting themes inside one chapter look (key temperature / fill / rim / accent), all over the navy void.
THEMES = {
    0: dict(key=(1.00, 0.95, 0.86), fill=(0.70, 0.80, 1.00), rim=(0.65, 0.80, 1.00), accent=(0.75, 0.90, 1.00)),   # intro: neutral warm key, ice rim
    1: dict(key=(1.00, 0.94, 0.84), fill=(0.65, 0.78, 1.00), rim=(0.55, 0.78, 1.00), accent=(0.80, 0.92, 1.00)),   # structure: warm key, ice-blue rim
    2: dict(key=(1.00, 0.86, 0.62), fill=(0.60, 0.85, 0.90), rim=(0.40, 0.90, 0.85), accent=(1.00, 0.80, 0.40)),   # genes: golden key, teal rim
    3: dict(key=(0.82, 0.95, 1.00), fill=(0.55, 0.75, 0.95), rim=(1.00, 0.72, 0.35), accent=(1.00, 0.70, 0.30)),   # transcription: cool key, amber rim
    4: dict(key=(0.96, 0.90, 1.00), fill=(0.70, 0.60, 1.00), rim=(1.00, 0.90, 0.75), accent=(0.85, 0.55, 1.00)),   # genetic code: orchid key, warm rim
    5: dict(key=(1.00, 0.88, 0.80), fill=(0.75, 0.62, 1.00), rim=(0.70, 0.55, 1.00), accent=(1.00, 0.65, 0.75)),   # translation: coral key, violet rim
    6: dict(key=(1.00, 0.84, 0.80), fill=(0.60, 0.70, 1.00), rim=(0.55, 0.80, 1.00), accent=(1.00, 0.45, 0.45)),   # chain to protein: rose key, cool rim
}

CODON = {}
_B = 'UCAG'; _AA = 'FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG'
_ONE = {'F': 'Phe', 'L': 'Leu', 'S': 'Ser', 'Y': 'Tyr', 'C': 'Cys', 'W': 'Trp', 'P': 'Pro', 'H': 'His', 'Q': 'Gln', 'R': 'Arg', 'I': 'Ile',
        'M': 'Met', 'T': 'Thr', 'N': 'Asn', 'K': 'Lys', 'V': 'Val', 'A': 'Ala', 'D': 'Asp', 'E': 'Glu', 'G': 'Gly', '*': 'Stop'}
_k = 0
for _a in _B:
    for _b in _B:
        for _c in _B: CODON[_a + _b + _c] = _ONE[_AA[_k]]; _k += 1
assert CODON['GGU'] == 'Gly' and CODON['CCU'] == 'Pro' and CODON['AUG'] == 'Met' and CODON['GAG'] == 'Glu' and CODON['GUG'] == 'Val'
assert all(CODON[c] == 'Stop' for c in ('UAA', 'UAG', 'UGA'))
