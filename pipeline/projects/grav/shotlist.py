"""Master shot list for the recreation of 'Gravitation | Full Chapter' (Visual Learning, 13:53).
Absolute seconds, read off 2-second and 4-second contact sheets of the reference (4 s sheets: t = 192*sheet + 4*(6*row+col))
and cross-checked against the caption timestamps in transcript_hi.txt. mode '3d' = Blender plate, '2d' = drawn by the
compositor. rfps = rendered fps (12 is upsampled to 24; fast motion is rendered at 24). hold = seconds after which the plate is static.
Sections of the reference: 1 Archimedes (17-128), 2 Buoyancy (128-272), 3 Gravitation (272-480), 4 Gravity (480-650),
5 Thrust & pressure (650-824), outro (824-833)."""

SHOTS = [
    # ---- intro: spring balance in a tank, dimmed under the title card and topic table
    dict(id='s01', t0=0.0,   t1=17.0,  mode='3d', rfps=12, builder='intro_tank'),
    dict(id='s02', t0=17.0,  t1=19.5,  mode='2d', rfps=1,  builder='card', text='1.Archimedes principle', bg='s03'),
    # ---- 1. Archimedes principle
    dict(id='s03', t0=19.5,  t1=43.5,  mode='3d', rfps=12, builder='spring_hang'),
    dict(id='s04', t0=43.5,  t1=60.0,  mode='3d', rfps=12, builder='spring_scale'),
    dict(id='s05', t0=60.0,  t1=78.0,  mode='3d', rfps=24, builder='ball_into_water'),
    dict(id='s06', t0=78.0,  t1=96.0,  mode='3d', rfps=12, builder='thrust_arcs'),
    dict(id='s07', t0=96.0,  t1=104.0, mode='3d', rfps=12, builder='scale_reading2'),
    dict(id='s08', t0=104.0, t1=128.0, mode='3d', rfps=12, builder='archimedes_state', hold=16.0),
    # ---- 2. Buoyancy
    dict(id='s09', t0=128.0, t1=131.0, mode='2d', rfps=1,  builder='card', text='2. Buoyancy', bg='s13'),
    dict(id='s10', t0=131.0, t1=142.0, mode='3d', rfps=12, builder='tank_fill'),
    dict(id='s11', t0=142.0, t1=170.0, mode='3d', rfps=24, builder='plastic_ball_push'),
    dict(id='s12', t0=170.0, t1=190.0, mode='3d', rfps=12, builder='displace_arrows'),
    dict(id='s13', t0=190.0, t1=236.0, mode='3d', rfps=12, builder='atm_pressure'),
    dict(id='s14', t0=236.0, t1=272.0, mode='3d', rfps=24, builder='iron_ball_sink', hold=30.0),
    # ---- 3. Gravitation and gravitational force
    dict(id='s15', t0=272.0, t1=275.0, mode='2d', rfps=1,  builder='card', text='3. Gravitation and Gravitational force', bg='s17'),
    dict(id='s16', t0=275.0, t1=300.0, mode='3d', rfps=12, builder='solar_system_reveal'),
    dict(id='s17', t0=300.0, t1=310.0, mode='3d', rfps=12, builder='force_lines'),
    dict(id='s18', t0=310.0, t1=374.0, mode='3d', rfps=12, builder='law_moon_earth', anchors=['Moon', 'Earth'], hold=22.0),
    dict(id='s19', t0=374.0, t1=404.0, mode='3d', rfps=24, builder='ball_throw_earth'),
    dict(id='s20', t0=404.0, t1=434.0, mode='3d', rfps=12, builder='moon_orbit'),
    dict(id='s21', t0=434.0, t1=452.0, mode='3d', rfps=12, builder='moon_inertia'),
    dict(id='s22', t0=452.0, t1=466.0, mode='3d', rfps=12, builder='earth_moon_forces'),
    dict(id='s23', t0=466.0, t1=474.0, mode='3d', rfps=12, builder='centripetal'),
    dict(id='s24', t0=474.0, t1=479.5, mode='3d', rfps=12, builder='solar_system2'),
    # ---- 4. Gravity
    dict(id='s25', t0=479.5, t1=482.5, mode='2d', rfps=1,  builder='card', text='4. Gravity', bg='s26'),
    dict(id='s26', t0=482.5, t1=506.0, mode='3d', rfps=12, builder='rocks_fall'),
    dict(id='s27', t0=506.0, t1=530.0, mode='3d', rfps=24, builder='free_fall_rock', anchors=['Rock']),
    dict(id='s28', t0=530.0, t1=548.0, mode='3d', rfps=12, builder='rock_accel', anchors=['Rock']),
    dict(id='s29', t0=548.0, t1=616.0, mode='3d', rfps=12, builder='stone_newton', anchors=['Stone', 'EarthC'], hold=60.0),
    dict(id='s30', t0=616.0, t1=650.0, mode='3d', rfps=12, builder='earth_radius', anchors=['Stone', 'EarthC', 'RMid']),
    # ---- 5. Thrust and pressure
    dict(id='s31', t0=650.0, t1=653.0, mode='2d', rfps=1,  builder='card', text='5. Thrust and pressure', bg='s32'),
    dict(id='s32', t0=653.0, t1=656.0, mode='3d', rfps=12, builder='thrust_intro'),
    dict(id='s33', t0=656.0, t1=664.0, mode='3d', rfps=12, builder='block_alone'),
    dict(id='s34', t0=664.0, t1=682.0, mode='3d', rfps=12, builder='t_object_place'),
    dict(id='s35', t0=682.0, t1=698.0, mode='3d', rfps=12, builder='hand_press'),
    dict(id='s36', t0=698.0, t1=716.0, mode='3d', rfps=12, builder='perpendicular_sides'),
    dict(id='s37', t0=716.0, t1=754.0, mode='3d', rfps=12, builder='area_decrease'),
    dict(id='s38', t0=754.0, t1=788.0, mode='3d', rfps=12, builder='area_increase'),
    dict(id='s39', t0=788.0, t1=796.0, mode='3d', rfps=12, builder='two_blocks', anchors=['TopL', 'TopR']),
    dict(id='s40', t0=796.0, t1=804.0, mode='3d', rfps=12, builder='closeup_small'),
    dict(id='s41', t0=804.0, t1=810.0, mode='3d', rfps=12, builder='closeup_large'),
    dict(id='s42', t0=810.0, t1=824.0, mode='3d', rfps=12, builder='two_blocks_formula', hold=8.0),
    dict(id='s43', t0=824.0, t1=833.0, mode='2d', rfps=1,  builder='outro'),
]

TOTAL = 833.0
