"""Every on-screen text/graphic event of the Gravitation reference, absolute seconds and 720p positions (read off
full-resolution reference frames and the 2-second contact sheets). Built-in kinds are drawn by overlay.py; the
project kinds (table5, text, frac, panel, anchor_*, ptr_text, dbl_arrow, pill2, navy_panel, twin_pointer) by overlay_ext.py.
The reference's on-screen spelling 'Archemides' / 'Gravitatiional' is corrected."""

E = []
def add(kind, t0, t1, **kw): E.append(dict(kind=kind, t0=t0, t1=t1, **kw))

TOPICS = [('1.Archimedes principle', '00:17 - 02:08'), ('2. Buoyancy', '02:09 - 04:31'), ('3. Gravitation', '04:32 - 07:59'),
          ('4. Gravity', '08:00 - 10:49'), ('5. Thrust and pressure', '10:50 - 13:42')]

# ---- intro (0-19.5): title over the dimmed balance-in-tank plate, five-row topic table, section card
add('label', 0.0, 17.0, text='Archimedes Principle', alpha=0.35)
add('title', 1.0, 17.0, text='Gravitation', y=20, size=32)
add('title', 2.5, 17.0, text='Complete Chapter', y=110, size=24)
add('table5', 5.5, 17.0, topics=TOPICS)
add('card', 17.0, 19.5, text='1.Archimedes principle')

# ---- 1. Archimedes principle (19.5-128)
add('label', 19.8, 100.0, text='Archimedes Principle')
add('text', 80.0, 86.0, parts=[('Thrust', 80.0), ('  =  ', 82.0), ('Buoyancy', 83.5)], x=95, y=572, size=26)
add('text', 100.0, 128.0, text='According To', x=34, y=12, size=17)
add('text', 101.5, 128.0, text='Archimedes Principle', x=16, y=34, size=17)
add('text', 106.0, 112.0, parts=[('Thrust', 106.0), ('  =  Weight  of the water', 108.0)], x=110, y=562, size=24)
add('defbox', 118.0, 128.0, text='When a body is immersed fully or partially in a fluid, it experiences an upward force that is equal to the weight of the fluid displaced by it .', t_words=(118.5, 127.5), y=520)
add('card', 128.0, 131.0, text='2. Buoyancy')

# ---- 2. Buoyancy (131-272)
add('label', 131.3, 272.0, text='Buoyancy')
add('text', 190.0, 198.0, text='Atmospheric Pressure', cx=640, y=24, size=20)
add('text', 202.0, 216.0, parts=[('Thrust', 202.0), (' =  Buoyancy', 204.0)], x=40, y=596, size=22)
add('text', 216.0, 236.0, parts=[('Buoyancy', 216.0), ('   ∝   ', 220.0), ('Density Of Fluid', 218.0)], cx=640, y=582, size=26)
add('text', 264.0, 272.0, parts=[('Gravitational force', 264.0), ('  >>  Thrust', 266.0)], x=60, y=608, size=15)
add('card', 272.0, 275.0, text='3. Gravitation and Gravitational force')

# ---- 3. Gravitation and gravitational force (275-479.5)
add('label', 275.0, 278.5, text='Gravitation & Gravitational force', alpha=0.5)
add('label', 300.0, 310.0, text='Gravitational force')
add('pill', 304.0, 310.0, text='Law of Gravitation', x=560, y=652, center=True)
add('label', 310.0, 374.0, text='Law of Gravitation')
add('defbox', 311.5, 326.0, text='According to this law every body in the universe attract another body in the universe', t_words=(312.0, 317.0), y=505)
add('frac', 330.0, 374.0, lhs='F ∝', num='M_1M_2', den='R^{2}', x=90, y=452, size=24, t_lhs=330.0, t_num=332.0, t_bar=334.5, t_den=336.0)
add('dbl_arrow', 336.0, 374.0, a='Moon', b='Earth', dy=64, text='R^{2}', t_full=340.0, size=24)
add('anchor_label', 340.0, 374.0, name='Moon', text='M_1', dx=6, dy=122, size=26)
add('anchor_label', 340.0, 374.0, name='Earth', text='M_2', dx=0, dy=122, size=26)
add('anchor_label', 342.0, 374.0, name='Moon', text='A', dx=0, dy=-78, size=26)
add('anchor_label', 344.0, 374.0, name='Earth', text='B', dx=-12, dy=-124, size=26)
add('frac', 346.0, 374.0, lhs='F = G', num='M_1M_2', den='R^{2}', x=90, y=588, size=24, box_from=366.0, box_color=(235, 205, 60), box_fill=False)
add('pill', 350.0, 374.0, text='G = Universal Gravitational constant', x=676, y=435, center=True, size=15)
add('pill2', 360.0, 374.0, text='Universal law of gravitation', x=676, y=504, fill=(60, 10, 14), border=(185, 45, 55), size=15)
add('pill2', 365.0, 374.0, text='Gravitational Force', x=675, y=581, fill=(42, 40, 8), border=(220, 200, 60), size=15)
add('label', 388.0, 434.0, text='Gravitational Force')
add('pill', 453.0, 466.0, text='Gravitational force', x=240, y=655, center=True)
add('pill', 458.5, 466.0, text='Inertia force', x=1060, y=608, center=True)
add('label', 464.0, 479.5, text='Centripetal force')
add('card', 479.5, 482.5, text='4. Gravity')

# ---- 4. Gravity (482.5-650)
add('label', 482.8, 548.0, text='Gravity')
add('pill', 492.0, 506.0, text='Gravitational force', x=1080, y=272, center=True)
add('text', 500.0, 506.0, text='Free Fall', x=1010, y=76, size=17)
add('anchor_pill', 506.5, 530.0, name='Rock', dx=130, dy=-33, values=[(506.0 + 2 * i, f'v = {8 + 32 * i}') for i in range(13)], leader=True)
add('ptr_text', 508.0, 518.0, name='Rock', text='Free Fall', dx=-230, dy=0, size=20, arrow_color=(70, 170, 255))
add('frac', 520.0, 548.0, lhs='Acceleration =', num='Velocity', den='Time', cx=998, y=261, size=17, box=True, box_pad=(70, 40))
add('anchor_pill', 530.0, 548.0, name='Rock', dx=130, dy=-33, values=[(530.0 + 2 * i, f'v = {424 + 32 * i}') for i in range(10)], leader=True)
add('panel', 536.0, 548.0, x=22, y=350, w=330, h=110, lines=[dict(t=536.0, text='Acceleration due to gravity', size=15, x=165, y=16, center=True), dict(t=542.0, text='a = g', size=16, x=165, y=44, center=True), dict(t=544.5, text='SI unit of g = ms^{-2}', size=15, x=165, y=72, center=True)])
add('ptr_text', 550.0, 556.0, name='Stone', text='Mass = m', dx=120, dy=-14, size=18, arrow_color=(255, 255, 255))
add('label', 558.0, 616.0, text="According to Newton's 2nd Law")
add('panel', 558.5, 616.0, x=15, y=147, w=520, h=256, lines=[
    dict(t=560.0, text='Force = Mass*Acceleration', size=14, x=260, y=22, center=True),
    dict(t=566.0, text='F = ma', size=26, x=128, y=62, center=True),
    dict(t=572.0, text='a = Acceleration', size=18, x=358, y=70, center=True),
    dict(t=578.0, text='a = g', size=18, x=240, y=112, center=True),
    dict(t=584.0, text='F = mg', size=26, x=237, y=148, center=True),
    dict(t=588.0, text='g = Acceleration due to gravity', size=16, x=262, y=208, center=True)])
add('pill', 592.0, 616.0, text='Gravitational force', x=980, y=92, center=True)
add('panel', 594.0, 616.0, x=840, y=140, w=400, h=360, box=False, lines=[
    dict(t=596.0, kind='frac', lhs='F = G', num='Mm', den='r^{2}', x=150, y=60, size=22, box=True, center=True),
    dict(t=600.0, text='M = Mass of Earth', size=15, x=150, y=145, center=True),
    dict(t=602.0, text='m = Mass of Object', size=15, x=150, y=170, center=True),
    dict(t=605.0, text='r = Distance', size=15, x=150, y=195, center=True),
    dict(t=608.0, text='F = mg', size=15, x=60, y=236, center=True),
    dict(t=609.5, kind='frac', lhs='F = G', num='Mm', den='r^{2}', x=230, y=244, size=14, center=True),
    dict(t=611.0, kind='frac', lhs='mg = G', num='Mm', den='r^{2}', x=150, y=292, size=14, center=True),
    dict(t=612.5, kind='frac', lhs='g = G', num='M', den='r^{2}', x=150, y=340, size=16, box=True, center=True)])
add('anchor_line', 604.0, 616.0, a='Stone', b='EarthC', color=(60, 200, 255), text='r', dx=18, size=18)
add('anchor_line', 616.5, 650.0, a='Stone', b='EarthC', color=(60, 200, 255))
add('anchor_label', 626.0, 650.0, name='RMid', text='R', dx=20, dy=0, size=22, color=(120, 220, 255))
add('frac', 632.0, 650.0, lhs='g = G', num='M', den='R^{2}', cx=182, y=178, size=18, box=True)
add('panel', 638.0, 650.0, x=60, y=275, w=340, h=150, box=False, lines=[
    dict(t=638.0, text='G = 6.7×10^{-11} Nm^{2}kg^{-2}', size=15, x=30, y=20),
    dict(t=640.0, text='M = 6×10^{24} kg', size=15, x=55, y=48),
    dict(t=642.0, text='R = 6.4×10^{6} m', size=15, x=55, y=76),
    dict(t=644.0, text='g = 9.8 ms^{-2}', size=16, x=55, y=112, box=True)])
add('card', 650.0, 653.0, text='5. Thrust and pressure')

# ---- 5. Thrust and pressure (653-824)
add('label', 653.0, 656.0, text='Thrust & Pressure')
add('label', 656.3, 720.0, text='Thrust')
add('pill', 708.0, 716.0, text='Perpendicular force =  Thrust', x=410, y=632, center=True)
add('pill', 748.0, 754.0, text='More Force on each point of the surface', x=820, y=96, center=True)
add('pill', 780.0, 786.0, text='Less Force on each point of the surface', x=820, y=96, center=True)
add('twin_pointer', 790.0, 792.5, text='Pressure', x=640, y=62, a='TopL', b='TopR')
add('pill', 798.0, 810.0, text='Small Area', x=140, y=92, center=True)
add('pill', 801.5, 810.0, text='High Pressure', x=140, y=126, center=True)
add('pill', 806.0, 810.0, text='Large Area', x=1140, y=92, center=True)
add('pill', 807.5, 810.0, text='Low Pressure', x=1140, y=126, center=True)
add('navy_panel', 810.0, 824.0, box=(110, 350, 1090, 655))
add('frac', 812.0, 824.0, lhs='Pressure =', num='Thrust', den='Area', cx=690, y=470, size=28, t_lhs=819.0, t_num=812.0, t_bar=815.0, t_den=815.5)
add('outro', 824.0, 833.0)
