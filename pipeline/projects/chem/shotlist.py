"""Master shot list for the recreation of 'Chemical Reactions and Equations | Full Chapter' (Visual Learning, 13:12).
Absolute seconds, read off 3-second contact sheets of the reference (t = 144*sheet + 3*(6*row+col)) and cross-checked
against the caption timestamps. mode '3d' = Blender plate, '2d' = drawn by the compositor. rfps = rendered fps (upsampled to 24).
hold = seconds after which the plate is static (last rendered frame is held)."""

SHOTS = [
    dict(id='s01', t0=0.0,   t1=4.5,   mode='3d', rfps=12, builder='candle_dome_intro'),
    dict(id='s02', t0=4.5,   t1=10.5,  mode='3d', rfps=12, builder='mannequin_platform'),
    dict(id='s03', t0=10.5,  t1=16.5,  mode='3d', rfps=12, builder='plant_cone_intro'),
    dict(id='s05', t0=16.5,  t1=18.5,  mode='2d', rfps=1,  builder='card', text='1. Chemical reaction', bg='s02'),
    dict(id='s06', t0=18.5,  t1=26.5,  mode='3d', rfps=12, builder='mannequin_platform2'),
    dict(id='s07', t0=26.5,  t1=42.0,  mode='3d', rfps=12, builder='plant_cone2'),
    dict(id='s08', t0=42.0,  t1=78.0,  mode='3d', rfps=12, builder='candle_burn'),
    dict(id='s10', t0=78.0,  t1=80.5,  mode='3d', rfps=12, builder='candle_far'),
    dict(id='s11', t0=80.5,  t1=104.0, mode='3d', rfps=12, builder='candle_jar', hold=12.0),
    dict(id='s12', t0=104.0, t1=122.5, mode='3d', rfps=12, builder='candle_dome_orbit'),
    dict(id='s13', t0=122.5, t1=129.0, mode='3d', rfps=12, builder='ice_block'),
    dict(id='s14', t0=129.0, t1=149.0, mode='3d', rfps=12, builder='candle_dome_pull'),
    dict(id='s15', t0=149.0, t1=158.0, mode='3d', rfps=12, builder='mg_ribbon'),
    dict(id='s16', t0=158.0, t1=166.0, mode='3d', rfps=12, builder='tongs_lamp'),
    dict(id='s17', t0=166.0, t1=199.0, mode='3d', rfps=24, builder='mg_burn'),
    dict(id='s18', t0=199.0, t1=218.0, mode='3d', rfps=12, builder='tongs_lamp_small', hold=4.0),
    dict(id='s19', t0=218.0, t1=251.0, mode='2d', rfps=1,  builder='molecules'),
    dict(id='s21', t0=251.0, t1=278.0, mode='2d', rfps=1,  builder='list'),
    dict(id='s22', t0=278.0, t1=302.0, mode='3d', rfps=12, builder='na_cl_combine', anchors=['Na', 'Cl2']),
    dict(id='s23', t0=302.0, t1=315.0, mode='3d', rfps=24, builder='beaker_cao_water'),
    dict(id='s24', t0=315.0, t1=347.0, mode='3d', rfps=12, builder='beaker_glow', hold=14.0),
    dict(id='s26', t0=347.0, t1=362.0, mode='3d', rfps=12, builder='nacl_split', anchors=['Na', 'Cl2']),
    dict(id='s27', t0=362.0, t1=378.0, mode='3d', rfps=12, builder='boiling_tube'),
    dict(id='s28', t0=378.0, t1=404.0, mode='3d', rfps=12, builder='tube_heat', hold=16.0),
    dict(id='s29', t0=404.0, t1=452.0, mode='2d', rfps=1,  builder='displacement_eq'),
    dict(id='s31', t0=452.0, t1=458.0, mode='3d', rfps=12, builder='three_nails'),
    dict(id='s32', t0=458.0, t1=470.0, mode='3d', rfps=12, builder='two_tubes_fill', hold=9.0),
    dict(id='s33', t0=470.0, t1=482.0, mode='3d', rfps=12, builder='stand_nail'),
    dict(id='s34', t0=482.0, t1=504.0, mode='3d', rfps=12, builder='rack_tubes', hold=17.0),
    dict(id='s35', t0=504.0, t1=531.0, mode='3d', rfps=12, builder='nails_compare', hold=3.0),
    dict(id='s36', t0=531.0, t1=546.0, mode='3d', rfps=12, builder='two_tubes_dd', hold=12.0),
    dict(id='s38', t0=546.0, t1=563.0, mode='3d', rfps=24, builder='pour_beaker'),
    dict(id='s39', t0=563.0, t1=584.0, mode='3d', rfps=12, builder='beaker_small', hold=2.0),
    dict(id='s40', t0=584.0, t1=614.0, mode='3d', rfps=12, builder='tripod_push', anchors='auto'),
    dict(id='s41', t0=614.0, t1=626.0, mode='3d', rfps=12, builder='tripod_wide'),
    dict(id='s42', t0=626.0, t1=662.0, mode='3d', rfps=12, builder='dish_close', anchors='auto'),
    dict(id='s43', t0=662.0, t1=666.0, mode='2d', rfps=1,  builder='card', text='3.corrosion and rancidity', bg='s44'),
    dict(id='s44', t0=666.0, t1=684.0, mode='3d', rfps=12, builder='corrosion_trio'),
    dict(id='s45', t0=684.0, t1=721.0, mode='3d', rfps=12, builder='nail_rust', anchors='auto', hold=20.0),
    dict(id='s46', t0=721.0, t1=737.0, mode='3d', rfps=12, builder='nail_rust_pull', anchors='auto'),
    dict(id='s47', t0=737.0, t1=785.0, mode='3d', rfps=12, builder='rancidity', anchors='auto'),
    dict(id='s48', t0=785.0, t1=792.2, mode='2d', rfps=1,  builder='outro'),
]


TOTAL = 792.2
