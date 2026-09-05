"""Master shot list for the ORIGINAL chapter 'Human Heart and Circulation' (8:03.5, narration laid out in ../out/heart/timing.json).
Every cut sits on a sentence boundary of timing.json (each 3D shot starts exactly where its first sentence starts); the six
section cards sit at their card_t0. mode '3d' = Blender plate, '2d' = compositor (card / outro). rfps = rendered fps (the
cloud forces 24). anchors = object names whose 2D positions the overlay follows (missing names are skipped by the exporter).

STORYBOARD. A cold open on the hero heart beating at 72 bpm in the navy void with its great vessels (slow orbit, push-in,
lens creep). 'Under the skin, behind the ribs': from outside the chest the camera passes THROUGH the amber skin silhouette,
between two ribs, past the lungs and lands on the beating wall; the wall close-up pulls back into a calm orbit under the topic
table while a glowing drop of blood arrives down the vena cava. Section 1 pulls back to show the heart between the two
lungs in the ribcage, slightly to the left; a closed fist beside it for size; a dive through the wall into a slab of cardiac
muscle fibres (striations, branching bridges, nuclei) that contract and relax in pulses; the pump idea (cells in through the
venae cavae, out through the aorta with a pressure glow on every beat); 'not one pump but two' (the right half tints indigo,
the left crimson); and 'we must go inside': the camera pushes into the front wall, which dissolves, revealing the four
chambers (match cut into section 2). Section 2 lives on the cutaway hero (window cut, real wall thickness, trabeculae,
papillary muscles with chordae, leaflets and cusps, cells streaming): four chambers named as spoken; atria receive /
ventricles pump; the septum lights gold and indigo/crimson streams never mix; wall thickness measured on the cut lip (atria
thin, ventricles thick, LV thickest); four glowing valve rings; a hero mitral valve that slams shut against back-flowing
cells; a hero aortic valve whose three pockets snap shut when the ventricle relaxes. Section 3 runs one heartbeat on the
cutaway rig with staged cell streams: atria fill, atria contract (cells drop into the ventricles), ventricles contract (AV
valves shut, cells rush into the arteries), the whole heart relaxes and refills; a stethoscope on the chest with the heart
glowing beneath (Lub as the AV valves close, Dub as the artery valves close); then two full cycles at true speed under a
ticking timeline. Section 4: the vessel tree branching out of the heart (arteries crimson, veins indigo, capillaries between);
an artery cut open showing its three wall layers pulsing; a vein cut open (thin wall) with pocket valves that pass cells
forward and shut against back-flow; a capillary bed (arteriole -> capillaries -> venule) and a dive to one capillary whose wall
is a single layer of flat cells; oxygen and nutrients diffusing out, carbon dioxide and waste diffusing in; the capillaries
merging into a venule; a hero red cell whose membrane the camera crosses to reach a haemoglobin molecule with glowing haem
irons. Section 5 follows one glowing drop on a heart + lungs + organs rig: vena cava -> RA -> RV -> pulmonary artery -> lungs
(indigo turns crimson, CO2 out, O2 in) -> pulmonary veins -> LA (the pulmonary loop lights up) -> LV -> aorta -> brain,
muscles, kidney (crimson turns indigo) -> vena cava -> RA (the systemic loop lights up); the figure-8 loop diagram with a 1-2
counter; why: the septum keeps the two bloods apart; warm-blooded silhouettes burning oxygen; and the fish with its
two-chamber heart and single loop. Section 6: cells pressing on an artery wall (bulges, pressure arrows); the cutaway heart
driving a live gauge (120 on contraction, 80 on relaxation); the 120/80 gauge hero; the sphygmomanometer (cuff inflating,
bulb, dial); hypertension straining the wall. Outro: a slow recap orbit of the cutaway double pump with both loops lit, then
the channel outro card."""

SECTION_TITLES = ['1. The Heart', '2. Chambers and Valves', '3. One Heartbeat', '4. Blood Vessels', '5. Double Circulation', '6. Blood Pressure']
EXCH = [f'O2p{i}' for i in range(8)] + [f'Nutp{i}' for i in range(6)] + [f'CO2p{i}' for i in range(8)] + [f'Wsp{i}' for i in range(6)] + ['AnWall1', 'AnTissue', 'AnVenule']

SHOTS = [
    # ---- intro (0-30.48): cold open, the dive under the skin, the calm orbit under the topic table
    dict(id='s01', t0=0.0,    t1=13.08,  mode='3d', rfps=12, builder='cold_open'),
    dict(id='s02', t0=13.08,  t1=21.97,  mode='3d', rfps=12, builder='dive_torso'),
    dict(id='s03', t0=21.97,  t1=30.48,  mode='3d', rfps=12, builder='table_orbit'),
    dict(id='s04', t0=30.48,  t1=33.08,  mode='2d', rfps=1,  builder='card', text='1. The Heart', bg='s05'),
    # ---- 1. The Heart (33.08-75.04)
    dict(id='s05', t0=33.08,  t1=40.33,  mode='3d', rfps=12, builder='heart_in_chest', anchors=['AnHeart', 'AnLungR', 'AnLungL', 'AnLeft']),
    dict(id='s06', t0=40.33,  t1=44.66,  mode='3d', rfps=12, builder='fist_compare', anchors=['AnFist', 'AnHeart2']),
    dict(id='s07', t0=44.66,  t1=56.01,  mode='3d', rfps=12, builder='cardiac_muscle', anchors=['AnFibre', 'AnStria']),
    dict(id='s08', t0=56.01,  t1=63.66,  mode='3d', rfps=12, builder='pump_idea', anchors=['AnIn', 'AnOut']),
    dict(id='s09', t0=63.66,  t1=71.0,   mode='3d', rfps=12, builder='two_pumps', anchors=['AnRight', 'AnLeft']),
    dict(id='s10', t0=71.0,   t1=75.04,  mode='3d', rfps=12, builder='dive_inside'),
    dict(id='s11', t0=75.04,  t1=77.64,  mode='2d', rfps=1,  builder='card', text='2. Chambers and Valves', bg='s12'),
    # ---- 2. Chambers and Valves (77.64-152.81)
    dict(id='s12', t0=77.64,  t1=90.55,  mode='3d', rfps=12, builder='four_chambers', anchors=['AnRA', 'AnLA', 'AnRV', 'AnLV']),
    dict(id='s13', t0=90.55,  t1=96.32,  mode='3d', rfps=12, builder='receive_pump', anchors=['AnAtria', 'AnVent']),
    dict(id='s14', t0=96.32,  t1=109.07, mode='3d', rfps=12, builder='septum', anchors=['AnSeptum', 'AnBlue', 'AnRed']),
    dict(id='s15', t0=109.07, t1=126.15, mode='3d', rfps=12, builder='wall_thickness', anchors=['AnWRAo', 'AnWRAi', 'AnWRVo', 'AnWRVi', 'AnWLAo', 'AnWLAi', 'AnWLVo', 'AnWLVi']),
    dict(id='s16', t0=126.15, t1=133.23, mode='3d', rfps=12, builder='valves_exits', anchors=['AnVtri', 'AnVmit', 'AnVpul', 'AnVaor']),
    dict(id='s17', t0=133.23, t1=142.81, mode='3d', rfps=12, builder='av_valve_shut', anchors=['AnValve', 'AnAtrium', 'AnVentricle']),
    dict(id='s18', t0=142.81, t1=152.81, mode='3d', rfps=12, builder='semilunar_shut', anchors=['AnCusps', 'AnArtery', 'AnVent2']),
    dict(id='s19', t0=152.81, t1=155.41, mode='2d', rfps=1,  builder='card', text='3. One Heartbeat', bg='s20'),
    # ---- 3. One Heartbeat (155.41-205.59)
    dict(id='s20', t0=155.41, t1=158.85, mode='3d', rfps=12, builder='beat_intro'),
    dict(id='s21', t0=158.85, t1=168.54, mode='3d', rfps=12, builder='atria_fill', anchors=['AnRA', 'AnLA', 'AnRV', 'AnLV']),
    dict(id='s22', t0=168.54, t1=178.0,  mode='3d', rfps=12, builder='vent_contract', anchors=['AnRV', 'AnLV', 'AnVtri', 'AnVmit', 'AnPulm', 'AnAorta']),
    dict(id='s23', t0=178.0,  t1=183.37, mode='3d', rfps=12, builder='relax_refill', anchors=['AnRA', 'AnLA']),
    dict(id='s24', t0=183.37, t1=198.13, mode='3d', rfps=12, builder='stethoscope_chest', anchors=['AnChestPiece', 'AnHeartGhost']),
    dict(id='s25', t0=198.13, t1=205.59, mode='3d', rfps=12, builder='cycle_timer'),
    dict(id='s26', t0=205.59, t1=208.19, mode='2d', rfps=1,  builder='card', text='4. Blood Vessels', bg='s27'),
    # ---- 4. Blood Vessels (208.19-282.11)
    dict(id='s27', t0=208.19, t1=220.5,  mode='3d', rfps=12, builder='vessel_network', anchors=['AnArt', 'AnVein', 'AnCap']),
    dict(id='s28', t0=220.5,  t1=231.47, mode='3d', rfps=12, builder='artery_section', anchors=['AnIntima', 'AnMedia', 'AnAdv', 'AnLumen']),
    dict(id='s29', t0=231.47, t1=246.25, mode='3d', rfps=12, builder='vein_section', anchors=['AnVWall', 'AnVValve', 'AnVLumen']),
    dict(id='s30', t0=246.25, t1=257.27, mode='3d', rfps=12, builder='capillary_bed_shot', anchors=['AnArteriole', 'AnCapil', 'AnVenule', 'AnCellWall']),
    dict(id='s31', t0=257.27, t1=273.7,  mode='3d', rfps=12, builder='exchange', anchors=EXCH),
    dict(id='s32', t0=273.7,  t1=282.11, mode='3d', rfps=12, builder='rbc_hero_shot', anchors=['AnRBC', 'AnHb', 'AnFe']),
    dict(id='s33', t0=282.11, t1=284.71, mode='2d', rfps=1,  builder='card', text='5. Double Circulation', bg='s34'),
    # ---- 5. Double Circulation (284.71-409.67): one drop's journey on the heart + lungs + organs rig
    dict(id='s34', t0=284.71, t1=293.67, mode='3d', rfps=12, builder='circ_intro', anchors=['AnDrop']),
    dict(id='s35', t0=293.67, t1=307.35, mode='3d', rfps=12, builder='circ_cavae_ra_rv', anchors=['AnDrop', 'AnSVC', 'AnIVC', 'AnRA', 'AnRV']),
    dict(id='s36', t0=307.35, t1=318.89, mode='3d', rfps=12, builder='circ_lungs', anchors=['AnDrop', 'AnPulmA', 'AnLungR', 'CO2p0', 'CO2p1', 'CO2p2', 'O2p0', 'O2p1', 'O2p2']),
    dict(id='s37', t0=318.89, t1=331.73, mode='3d', rfps=12, builder='circ_pulm_veins', anchors=['AnDrop', 'AnPV', 'AnLA', 'AnLungR', 'AnLungL', 'AnHeartC']),
    dict(id='s38', t0=331.73, t1=343.65, mode='3d', rfps=12, builder='circ_la_lv_aorta', anchors=['AnDrop', 'AnLA', 'AnLV', 'AnAorta']),
    dict(id='s39', t0=343.65, t1=362.62, mode='3d', rfps=12, builder='circ_body', anchors=['AnDrop', 'AnBrain', 'AnMuscle', 'AnKidney', 'AnVC', 'AnHeartC', 'AnBody']),
    dict(id='s40', t0=362.62, t1=371.56, mode='3d', rfps=12, builder='twice_double', anchors=['AnDrop', 'AnLoopHeart', 'AnLoopLungs', 'AnLoopBody']),
    dict(id='s41', t0=371.56, t1=386.65, mode='3d', rfps=12, builder='why_no_mixing', anchors=['AnSeptum', 'AnBlue', 'AnRed', 'AnAorta']),
    dict(id='s42', t0=386.65, t1=397.43, mode='3d', rfps=12, builder='mammals_birds', anchors=['AnMammal', 'AnBird']),
    dict(id='s43', t0=397.43, t1=409.67, mode='3d', rfps=12, builder='fish_single', anchors=['AnFAtrium', 'AnFVent', 'AnGills', 'AnFBody']),
    dict(id='s44', t0=409.67, t1=412.27, mode='2d', rfps=1,  builder='card', text='6. Blood Pressure', bg='s45'),
    # ---- 6. Blood Pressure (412.27-456.66)
    dict(id='s45', t0=412.27, t1=420.3,  mode='3d', rfps=12, builder='pressure_walls', anchors=['AnWall', 'AnPush']),
    dict(id='s46', t0=420.3,  t1=434.0,  mode='3d', rfps=12, builder='systolic_diastolic', anchors=['AnGauge', 'AnHeartS', 'AnRV', 'AnLV']),
    dict(id='s47', t0=434.0,  t1=442.22, mode='3d', rfps=12, builder='gauge_120_80', anchors=['AnNeedle', 'AnDial']),
    dict(id='s48', t0=442.22, t1=447.72, mode='3d', rfps=12, builder='sphygmo', anchors=['AnCuff', 'AnGaugeS', 'AnBulb']),
    dict(id='s49', t0=447.72, t1=456.66, mode='3d', rfps=12, builder='hypertension', anchors=['AnDamage', 'AnHeartH']),
    # ---- outro (456.66-483.5)
    dict(id='s50', t0=456.66, t1=472.47, mode='3d', rfps=12, builder='recap_orbit', anchors=['AnRA', 'AnLA', 'AnRV', 'AnLV']),
    dict(id='s51', t0=472.47, t1=483.5,  mode='2d', rfps=1,  builder='outro'),
]

TOTAL = 483.5
assert abs(SHOTS[-1]['t1'] - TOTAL) < 1e-6 and all(a['t1'] == b['t0'] for a, b in zip(SHOTS[:-1], SHOTS[1:]))
