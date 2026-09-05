"""Master shot list for the recreation of 'The Fundamental Unit of Life | Full Chapter' (Visual Learning, 14:51).
Absolute seconds read off the 4-second contact sheets (projects/cell/refs/cell4_0*.png, tile k*48+6r+c sits at about
t = 4*(48k+6r+c)+2) and 1-2 second ffmpeg strips around every transition, cross-checked with the caption timestamps
in transcript_hi.txt.  mode '3d' = Blender plate, '2d' = drawn by the compositor.  rfps = rendered fps (upsampled
to 24; the cloud forces 24).  hold = seconds after which the plate is static.  anchors='auto' = objects named
Hp*/Op*/Rp* get 2D molecule markers (H2O / O2 / CO2, drawn by overlay_ext); anchors=TAGS = the Tag* specks the
organelle shield labels hang from (missing names are skipped by the exporter)."""

TAGS = ['TagNuc', 'TagER', 'TagRough', 'TagSmooth', 'TagRibo', 'TagGolgi', 'TagLyso', 'TagLyso0', 'TagMito', 'TagMito1', 'TagMito2', 'TagMito3',
        'TagPlastid', 'TagFold', 'TagATP', 'TagDNA', 'TagNucleus', 'TagPro', 'TagEu', 'TagNucMem', 'TagPores', 'TagChrom', 'TagNucleoid', 'TagCyto']

SHOTS = [
    # ---- intro (title, complete chapter, topic table over a preview montage)
    dict(id='s01', t0=0.0,   t1=7.5,   mode='3d', rfps=12, builder='intro_cell'),
    dict(id='s02', t0=7.5,   t1=14.0,  mode='3d', rfps=12, builder='intro_cork'),
    dict(id='s03', t0=14.0,  t1=19.5,  mode='3d', rfps=12, builder='intro_comb'),
    dict(id='s04', t0=19.5,  t1=22.5,  mode='2d', rfps=1,  builder='card', text='1.Cell', bg='s01'),
    # ---- 1. Cell: Hooke and cork
    dict(id='s05', t0=22.5,  t1=30.0,  mode='3d', rfps=12, builder='cork_stopper'),
    dict(id='s06', t0=30.0,  t1=41.5,  mode='3d', rfps=12, builder='cork_slice'),
    dict(id='s07', t0=41.5,  t1=46.0,  mode='3d', rfps=12, builder='hooke_microscope'),
    dict(id='s08', t0=46.0,  t1=62.0,  mode='3d', rfps=12, builder='honeycomb_cells', anchors=['CombAnchor']),
    # ---- onion peel experiment
    dict(id='s09', t0=62.0,  t1=66.0,  mode='3d', rfps=12, builder='onion_whole'),
    dict(id='s10', t0=66.0,  t1=72.0,  mode='3d', rfps=12, builder='onion_cut'),
    dict(id='s11', t0=72.0,  t1=84.0,  mode='3d', rfps=12, builder='onion_layers'),
    dict(id='s12', t0=84.0,  t1=94.0,  mode='3d', rfps=12, builder='watch_glass_layer'),
    dict(id='s13', t0=94.0,  t1=102.0, mode='3d', rfps=12, builder='slide_water'),
    dict(id='s14', t0=102.0, t1=112.0, mode='3d', rfps=12, builder='forceps_transfer'),
    dict(id='s15', t0=112.0, t1=120.0, mode='3d', rfps=12, builder='safranin'),
    dict(id='s16', t0=120.0, t1=126.0, mode='3d', rfps=12, builder='cover_slip'),
    dict(id='s17', t0=126.0, t1=136.0, mode='3d', rfps=12, builder='microscope_slide'),
    dict(id='s18', t0=136.0, t1=157.0, mode='3d', rfps=12, builder='onion_tissue', hold=12.0),
    # ---- 2. Cell structure
    dict(id='s19', t0=157.0, t1=159.5, mode='2d', rfps=1,  builder='card', text='2.Cell Structure', bg='s20'),
    dict(id='s20', t0=159.5, t1=162.0, mode='3d', rfps=12, builder='cutaway_cell_brief'),
    dict(id='s21', t0=162.0, t1=168.0, mode='3d', rfps=12, builder='microscope_turn'),
    dict(id='s22', t0=168.0, t1=174.5, mode='3d', rfps=12, builder='honeycomb_dive'),
    dict(id='s23', t0=174.5, t1=177.5, mode='3d', rfps=12, builder='cell_grid'),
    dict(id='s24', t0=177.5, t1=204.0, mode='3d', rfps=12, builder='cutaway_cell_labels', anchors=['MembraneAnchor', 'NucleusAnchor', 'CytoAnchor']),
    dict(id='s25', t0=204.0, t1=212.0, mode='3d', rfps=12, builder='cell_whole_open', anchors=['MembraneAnchor']),
    dict(id='s26', t0=212.0, t1=220.0, mode='3d', rfps=12, builder='cell_in_env'),
    dict(id='s27', t0=220.0, t1=232.0, mode='3d', rfps=12, builder='cell_whole_rect'),
    dict(id='s28', t0=232.0, t1=252.0, mode='3d', rfps=12, builder='diffusion', anchors='auto'),
    dict(id='s29', t0=252.0, t1=284.0, mode='3d', rfps=12, builder='osmosis', anchors='auto'),
    dict(id='s30', t0=284.0, t1=296.0, mode='3d', rfps=12, builder='cell_flexible'),
    dict(id='s31', t0=296.0, t1=300.0, mode='3d', rfps=12, builder='lipid_bilayer'),
    dict(id='s32', t0=300.0, t1=304.0, mode='3d', rfps=12, builder='electron_microscope'),
    # ---- 3. Cell organelles
    dict(id='s33', t0=304.0, t1=306.0, mode='2d', rfps=1,  builder='card', text='3. Cell Organelles', bg='s34'),
    dict(id='s34', t0=306.0, t1=320.0, mode='3d', rfps=12, builder='organelle_overview', anchors=TAGS),
    dict(id='s35', t0=320.0, t1=360.0, mode='3d', rfps=12, builder='interior_tour', anchors=TAGS),
    dict(id='s36', t0=360.0, t1=364.0, mode='3d', rfps=12, builder='interior_overview', anchors=TAGS),
    dict(id='s37', t0=364.0, t1=372.0, mode='3d', rfps=12, builder='er_close', anchors=TAGS),
    dict(id='s38', t0=372.0, t1=376.0, mode='3d', rfps=12, builder='golgi_close', anchors=TAGS),
    dict(id='s39', t0=376.0, t1=382.0, mode='3d', rfps=12, builder='lysosome_close', anchors=TAGS),
    dict(id='s40', t0=382.0, t1=390.0, mode='3d', rfps=12, builder='mito_close', anchors=TAGS),
    dict(id='s41', t0=390.0, t1=398.0, mode='3d', rfps=12, builder='chloroplast_solo', anchors=TAGS),
    dict(id='s42', t0=398.0, t1=408.0, mode='3d', rfps=12, builder='two_cells', anchors=TAGS),
    dict(id='s43', t0=408.0, t1=412.0, mode='3d', rfps=12, builder='interior_overview2', anchors=TAGS),
    dict(id='s44', t0=412.0, t1=436.0, mode='3d', rfps=12, builder='er_zoom', anchors=TAGS),
    dict(id='s45', t0=436.0, t1=480.0, mode='3d', rfps=12, builder='er_rough_smooth', anchors=TAGS),
    dict(id='s46', t0=480.0, t1=492.0, mode='3d', rfps=12, builder='golgi_intro', anchors=TAGS),
    dict(id='s47', t0=492.0, t1=524.0, mode='3d', rfps=12, builder='golgi_network', anchors=TAGS),
    dict(id='s48', t0=524.0, t1=548.0, mode='3d', rfps=12, builder='golgi_functions', anchors=TAGS),
    dict(id='s49', t0=548.0, t1=588.0, mode='3d', rfps=12, builder='lysosomes', anchors=TAGS, hold=30.0),
    dict(id='s50', t0=588.0, t1=600.0, mode='3d', rfps=12, builder='interior_to_mito', anchors=TAGS),
    dict(id='s51', t0=600.0, t1=624.0, mode='3d', rfps=12, builder='mito_solo', anchors=TAGS),
    dict(id='s52', t0=624.0, t1=644.0, mode='3d', rfps=12, builder='mito_cristae', anchors=TAGS),
    dict(id='s53', t0=644.0, t1=664.0, mode='3d', rfps=12, builder='mito_dna', anchors=TAGS),
    dict(id='s54', t0=664.0, t1=680.0, mode='3d', rfps=12, builder='plastid_cells'),
    dict(id='s55', t0=680.0, t1=700.0, mode='3d', rfps=12, builder='chloroplast_zoom', anchors=TAGS),
    dict(id='s56', t0=700.0, t1=708.0, mode='3d', rfps=12, builder='leucoplast_zoom'),
    # ---- 4. Nucleus and cytoplasm
    dict(id='s57', t0=708.0, t1=710.5, mode='2d', rfps=1,  builder='card', text='4.Nucleus and Cytoplasm', bg='s58'),
    dict(id='s58', t0=710.5, t1=732.0, mode='3d', rfps=12, builder='nucleus_in_cell', anchors=TAGS),
    dict(id='s59', t0=732.0, t1=748.0, mode='3d', rfps=12, builder='pro_vs_eu', anchors=TAGS),
    dict(id='s60', t0=748.0, t1=752.0, mode='3d', rfps=12, builder='cell_whole_short'),
    dict(id='s61', t0=752.0, t1=770.0, mode='3d', rfps=12, builder='nucleus_pores', anchors=TAGS),
    dict(id='s62', t0=770.0, t1=792.0, mode='3d', rfps=12, builder='chromosomes_dna', anchors=TAGS),
    dict(id='s63', t0=792.0, t1=806.0, mode='3d', rfps=12, builder='cell_division'),
    dict(id='s64', t0=806.0, t1=820.0, mode='3d', rfps=12, builder='dark_cell_nucleus'),
    dict(id='s65', t0=820.0, t1=842.0, mode='3d', rfps=12, builder='bacteria', anchors=TAGS),
    dict(id='s66', t0=842.0, t1=866.0, mode='3d', rfps=12, builder='cytoplasm_cup', anchors=TAGS),
    dict(id='s67', t0=866.0, t1=881.0, mode='3d', rfps=12, builder='cell_organelles_small'),
    dict(id='s68', t0=881.0, t1=891.1, mode='2d', rfps=1,  builder='outro'),
]

TOTAL = 891.1
