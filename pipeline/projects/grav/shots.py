"""Blender builders for every 3D shot of the Gravitation chapter. Each builder(nf, rfps, dur) sets up scene + animation
for frames 1..nf. Camera sits at -Y looking +Y, Z up. Units ~ decimetres for the lab scenes (tank 6 wide, ball r 0.55),
scene units for space (Earth r 1..8 depending on the shot).
Hero assets built here: laboratory spring balance (bevelled helix curve, ring, hook, scale with ticks and numbers), a
stylised hand (bevelled capsules), a glass tank with real water (wave-modifier ripples, rising level), cast-iron and glossy
plastic balls, NASA Blue Marble Earth (clouds + atmosphere shell), LROC Moon (image displacement), a Sun with animated
surface + halo (+ volumetric corona in Cycles), planets with orbit tori, a single-mesh starfield, meteor rocks with spark
trails, a wooden block with the T-shaped thrust object. Force arrows (chevron streams, thrust arcs, pressure arrows) are 3D."""
import math, random, bpy, os, sys, bmesh
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from mathutils import Vector
from kit import *
from kit import _principled, _inp

def F(sec, rfps): return int(round(sec * rfps)) + 1     # seconds -> frame number (1-based)

# ================================================================= small utilities
def link(o): bpy.context.collection.objects.link(o); return o

def bevel(o, w=0.05, seg=8):
    try: mod = o.modifiers.new('bevel', 'BEVEL'); mod.width = w; mod.segments = seg; mod.limit_method = 'ANGLE'; return mod
    except Exception: return None

def mesh_obj(name, bm, mat=None, loc=(0, 0, 0)):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); o = link(bpy.data.objects.new(name, me)); o.location = loc
    if mat is not None: setmat(o, mat)
    return o

def box(name, size, loc=(0, 0, 0), mat=None, bev=0.0, seg=6):
    """Real-size cuboid (scale applied so bevels stay uniform and object-space textures keep their grain size)."""
    o = obj_add('cube', name, size=1); o.scale = size
    try: bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    except Exception: pass
    o.location = loc
    if mat is not None: setmat(o, mat)
    if bev: bevel(o, bev, seg); smooth(o)
    return o

def parent_keep(child, parent):
    """Parent while keeping the child's world placement (forces a depsgraph update first: a fresh object's matrix_world is stale)."""
    bpy.context.view_layer.update(); child.parent = parent; child.matrix_parent_inverse = parent.matrix_world.inverted()

def show_from(objs, f_on=None, f_off=None):
    """hide_render keyframes for a list of objects (parents do not hide children in Blender)."""
    for o in objs:
        if f_on is not None and f_on > 1: kf(o, 'hide_render', 1, True); kf(o, 'hide_render', f_on, False)
        elif f_on is not None: kf(o, 'hide_render', 1, False)
        if f_off is not None: kf(o, 'hide_render', f_off, True)

def _blend(m, shadow=False):
    for attr, val in [('surface_render_method', 'BLENDED'), ('blend_method', 'BLEND'), ('use_backface_culling', False), ('show_transparent_back', True), ('use_transparency_overlap', True)]:
        try: setattr(m, attr, val)
        except Exception: pass
    if not shadow:
        try: m.shadow_method = 'NONE'
        except Exception: pass
        try: m.use_transparent_shadow = True
        except Exception: pass
    return m

def color_kf(mat, keys, sockets=('Base Color', 'Emission Color')):
    """keys = [(frame, (r, g, b))] on a Principled material."""
    p = mat.node_tree.nodes.get('Principled BSDF')
    if p is None: return
    for f, c in keys:
        for s in sockets:
            if s in p.inputs: p.inputs[s].default_value = (*c, 1); p.inputs[s].keyframe_insert('default_value', frame=f)

def value_kf(mat, socket, keys):
    p = mat.node_tree.nodes.get('Principled BSDF')
    for f, v in keys: p.inputs[socket].default_value = v; p.inputs[socket].keyframe_insert('default_value', frame=f)

def text3d(name, body, loc, size=0.35, mat=None, align='CENTER', rot=(math.pi / 2, 0, 0)):
    tc = bpy.data.curves.new(name, 'FONT'); tc.body = body; tc.size = size; tc.align_x = align; tc.extrude = 0.004
    o = link(bpy.data.objects.new(name, tc)); o.location = loc; o.rotation_euler = rot
    if mat is not None: o.data.materials.append(mat)
    return o

def sawtooth(o, f0, f1, span, vec, period_frames):
    """Move o from 0 to vec over period frames, jump back, repeat (linear) -> endless streaming motion."""
    f = f0; base = Vector(o.location)
    while f <= f1:
        kf(o, 'location', f, tuple(base)); fe = min(f1, f + period_frames)
        kf(o, 'location', fe, tuple(base + Vector(vec) * ((fe - f) / period_frames)))
        f = fe + 1
        if f <= f1: kf(o, 'location', f, tuple(base))
    kf_lin(o)

# ================================================================= materials
def mat_skin(name='skin'):
    m = mat_plastic((0.86, 0.60, 0.46), rough=0.55, name=name, sss=0.25 if is_cycles() else 0.12); p = m.node_tree.nodes['Principled BSDF']
    _inp(p, 'Subsurface Radius', (1.0, 0.35, 0.2)); _inp(p, 'Specular IOR Level', 0.35); _inp(p, 'Coat Weight', 0.05)
    return m

def mat_iron(name='cast_iron'):
    m, p = _principled(name); nt = m.node_tree; n = nt.nodes
    tex = n.new('ShaderNodeTexCoord'); noise = n.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 38; noise.inputs['Detail'].default_value = 9; noise.inputs['Roughness'].default_value = 0.75
    ramp = n.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[0].color = (0.30, 0.31, 0.33, 1); ramp.color_ramp.elements[1].position = 0.7; ramp.color_ramp.elements[1].color = (0.55, 0.56, 0.58, 1)
    nt.links.new(tex.outputs['Object'], noise.inputs['Vector']); nt.links.new(noise.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], p.inputs['Base Color'])
    bump = n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.25; bump.inputs['Distance'].default_value = 0.02
    nt.links.new(noise.outputs['Fac'], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], p.inputs['Normal'])
    _inp(p, 'Metallic', 0.85); _inp(p, 'Roughness', 0.48)
    return m

def mat_plastic_ball(color=(0.12, 0.42, 0.95), name='plastic_ball'):
    m = mat_plastic(color, rough=0.22, name=name, coat=0.9); p = m.node_tree.nodes['Principled BSDF']; _inp(p, 'Coat Roughness', 0.05); _inp(p, 'Specular IOR Level', 0.6)
    return m

def mat_orange_ball(name='orange_ball'):
    m = mat_plastic((0.95, 0.42, 0.10), rough=0.35, name=name, coat=0.4); return m

def mat_rock(name='rock'):
    m, p = _principled(name); nt = m.node_tree; n = nt.nodes
    tex = n.new('ShaderNodeTexCoord'); noise = n.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 9; noise.inputs['Detail'].default_value = 10; noise.inputs['Roughness'].default_value = 0.7
    ramp = n.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position = 0.3; ramp.color_ramp.elements[0].color = (0.11, 0.08, 0.05, 1); ramp.color_ramp.elements[1].position = 0.75; ramp.color_ramp.elements[1].color = (0.36, 0.28, 0.18, 1)
    nt.links.new(tex.outputs['Object'], noise.inputs['Vector']); nt.links.new(noise.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], p.inputs['Base Color'])
    bump = n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.5; nt.links.new(noise.outputs['Fac'], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], p.inputs['Normal'])
    _inp(p, 'Roughness', 0.92)
    return m

def mat_wood_block(name='wood_block', scale=1.0, tint=(0.88, 0.64, 0.36)):
    """Blond solid wood (the reference's pine block): long distorted grain bands + fine noise + a soft bump, no plank seams."""
    m, p = _principled(name); nt = m.node_tree; n = nt.nodes
    tc = n.new('ShaderNodeTexCoord'); mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.9 * scale, 5.0 * scale, 0.9 * scale); mp.inputs['Rotation'].default_value = (0, 0, 0.06)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    wave = n.new('ShaderNodeTexWave'); wave.wave_type = 'BANDS'; wave.bands_direction = 'X'; wave.inputs['Scale'].default_value = 4.0; wave.inputs['Distortion'].default_value = 1.1; wave.inputs['Detail'].default_value = 6.0; wave.inputs['Detail Scale'].default_value = 2.0
    nt.links.new(mp.outputs['Vector'], wave.inputs['Vector'])
    noise = n.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 14.0 * scale; noise.inputs['Detail'].default_value = 8; noise.inputs['Roughness'].default_value = 0.65; nt.links.new(tc.outputs['Object'], noise.inputs['Vector'])
    mix = n.new('ShaderNodeMix'); mix.data_type = 'FLOAT'; mix.inputs['Factor'].default_value = 0.4; nt.links.new(wave.outputs['Fac'], mix.inputs[2]); nt.links.new(noise.outputs['Fac'], mix.inputs[3])
    ramp = n.new('ShaderNodeValToRGB'); cr = ramp.color_ramp; cr.elements[0].position = 0.2; cr.elements[0].color = (tint[0] * 0.8, tint[1] * 0.74, tint[2] * 0.68, 1); cr.elements[1].position = 0.85; cr.elements[1].color = (min(1, tint[0] * 1.06), min(1, tint[1] * 1.06), min(1, tint[2] * 1.08), 1)
    nt.links.new(mix.outputs[0], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], p.inputs['Base Color'])
    bump = n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.08; bump.inputs['Distance'].default_value = 0.03; nt.links.new(mix.outputs[0], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], p.inputs['Normal'])
    _inp(p, 'Roughness', 0.48); _inp(p, 'Specular IOR Level', 0.4); _inp(p, 'Coat Weight', 0.08)
    return m

def mat_tank_glass(name='tank_glass'):
    if is_cycles(): m = mat_glass_real((0.85, 0.92, 1.0), ior=1.5, rough=0.03, name=name)
    else:
        m = mat_glass((0.55, 0.66, 0.88), alpha=0.2, rough=0.18, name=name); p = m.node_tree.nodes['Principled BSDF']; _inp(p, 'Coat Weight', 0.15); _inp(p, 'Specular IOR Level', 0.4)
    return m

def mat_water(name='water', color=(0.10, 0.40, 0.95)):
    if is_cycles(): return mat_liquid_real((min(1, color[0] + 0.15), min(1, color[1] + 0.15), min(1, color[2] + 0.05)), ior=1.33, absorption=0.13, name=name)
    m = mat_glass(tint=color, alpha=0.42, rough=0.14, name=name); p = m.node_tree.nodes['Principled BSDF']; _inp(p, 'Coat Weight', 0.35); _inp(p, 'Specular IOR Level', 0.6)
    return m

def mat_emit_soft(color, strength=6.0, name='glow', alpha=0.45):
    return mat_emit(color, strength=strength, name=name, alpha=alpha)

# ================================================================= stages
def lab_stage(target=(0, 0, 3.0), key_e=2600, spot=55, fill_e=110, rim_e=320, key=(3.5, -5.0, 11.0)):
    """Dark void with the house key/fill/rim, HDRI reflections in the metal and glass, a faint dark glossy bench."""
    world(0.004, 0.006, 0.014); studio(key=key, key_e=key_e, fill_e=fill_e, rim_e=rim_e, target=target, spot=spot, blend=0.85)
    hdri(strength=0.3, rotation=0.6)

def bench(z=0.0, size=30.0):
    o = obj_add('plane', 'Bench', size=size, location=(0, 4, z))
    m = mat_plastic((0.008, 0.01, 0.016), rough=0.42, name='bench_m', coat=0.0); p = m.node_tree.nodes['Principled BSDF']; _inp(p, 'Specular IOR Level', 0.25); setmat(o, m); return o

def space_stage(sun_dir=(-4.0, -6.0, 5.0), sun_e=6.5, fill_e=0.35, stars=1600, star_r=90.0, seed=1):
    """Void black-navy, one distant sun lamp, a whisper of cool fill, and a single-mesh starfield."""
    world(0.0015, 0.0022, 0.005)
    d = bpy.data.lights.new('SunL', 'SUN'); d.energy = sun_e; d.color = (1.0, 0.96, 0.9); d.angle = math.radians(1.2)
    o = link(bpy.data.objects.new('SunL', d)); o.location = (0, 0, 0); o.rotation_euler = (Vector(sun_dir) * -1).to_track_quat('-Z', 'Y').to_euler()
    f = bpy.data.lights.new('FillL', 'SUN'); f.energy = fill_e; f.color = (0.55, 0.7, 1.0); fo = link(bpy.data.objects.new('FillL', f)); fo.rotation_euler = (Vector((3, 4, -2))).to_track_quat('-Z', 'Y').to_euler()
    starfield(n=stars, r=star_r, seed=seed)
    return o

def starfield(n=1600, r=90.0, seed=1):
    rnd = random.Random(seed); bm = bmesh.new(); me = bpy.data.meshes.new('Stars')
    mats = [mat_emit((1, 1, 1), strength=2.5, name='star_a'), mat_emit((0.85, 0.92, 1.0), strength=5.0, name='star_b'), mat_emit((1.0, 0.95, 0.85), strength=9.0, name='star_c')]
    faces = []
    for i in range(n):
        u, v = rnd.random(), rnd.random(); th = 2 * math.pi * u; ph = math.acos(2 * v - 1)
        c = Vector((math.sin(ph) * math.cos(th), math.sin(ph) * math.sin(th), math.cos(ph))) * r
        s = r * rnd.uniform(0.0006, 0.0018); a = c.normalized(); b = a.orthogonal().normalized(); d = a.cross(b)
        vs = [bm.verts.new(c + b * s * math.cos(k * math.pi / 3) + d * s * math.sin(k * math.pi / 3)) for k in range(6)]
        fc = bm.faces.new(vs); fc.material_index = rnd.choices((0, 1, 2), weights=(6, 3, 1))[0]
    bm.to_mesh(me); bm.free(); o = link(bpy.data.objects.new('Stars', me))
    for m in mats: o.data.materials.append(m)
    return o

# ================================================================= spring balance
def spring_coil(name, top, L=2.4, R=0.24, wire=0.035, turns=13, per=32, mat=None):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = wire; cu.bevel_resolution = 8; cu.use_fill_caps = True
    sp = cu.splines.new('POLY'); n = turns * per; sp.points.add(n)
    for i in range(n + 1):
        a = 2 * math.pi * i / per; ease = min(1.0, i / per, (n - i) / per)         # tighten the end coils a little
        sp.points[i].co = (R * math.cos(a) * (0.75 + 0.25 * ease), R * math.sin(a) * (0.75 + 0.25 * ease), -L * i / n, 1.0)
    sp.use_smooth = True
    o = link(bpy.data.objects.new(name, cu)); o.location = top
    o.data.materials.append(mat or mat_metal((0.82, 0.83, 0.86), rough=0.28, name=name + '_m'))
    return o

def spring_balance(top=(0, 0, 9.6), L=2.4, ball_r=0.55, ball_mat=None, hook_len=0.42, name='SB'):
    """Ring at the top (held by the hand), coil, J-hook at the bottom, ball with an eyelet. Coil origin = top; scale.z stretches.
    Returns dict; ball_root is an empty at the coil bottom whose children (hook, eyelet, ball) follow the stretch."""
    steel = mat_metal((0.82, 0.83, 0.86), rough=0.28, name=name + '_steel')
    ring = obj_add('torus', name + 'Ring', major_radius=0.17, minor_radius=0.032, major_segments=96, minor_segments=24, location=(top[0], top[1], top[2] + 0.2)); ring.rotation_euler = (math.pi / 2, 0, 0); setmat(ring, steel); smooth(ring)
    coil = spring_coil(name + 'Coil', top, L=L, mat=steel)
    br = empty(name + 'BallRoot', (top[0], top[1], top[2] - L))
    # J hook: straight shank then a half loop opening to +x, built as a bevelled poly curve in local coords of ball_root
    cu = bpy.data.curves.new(name + 'Hook', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.03; cu.bevel_resolution = 8; cu.use_fill_caps = True
    sp = cu.splines.new('POLY'); pts = [(0, 0, 0.05), (0, 0, -hook_len * 0.45)]
    for k in range(13):
        a = math.pi * (1 + k / 12.0); pts.append((0.11 + 0.11 * math.cos(a), 0, -hook_len * 0.45 - 0.11 * 1.0 + 0.11 * math.sin(a)))
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts): sp.points[i].co = (*p, 1.0)
    sp.use_smooth = True; hook = link(bpy.data.objects.new(name + 'Hook', cu)); hook.data.materials.append(steel); hook.parent = br
    eye = obj_add('torus', name + 'Eye', major_radius=0.09, minor_radius=0.022, major_segments=64, minor_segments=16, location=(0.11, 0, -hook_len - 0.02)); eye.rotation_euler = (math.pi / 2, 0, 0); setmat(eye, steel); smooth(eye); eye.parent = br
    ball = obj_add('uv_sphere', name + 'Ball', radius=ball_r, segments=96, ring_count=48, location=(0.11, 0, -hook_len - 0.1 - ball_r)); setmat(ball, ball_mat or mat_iron()); smooth(ball); ball.parent = br
    subsurf(ball, 1, 1)
    return dict(ring=ring, coil=coil, root=br, hook=hook, eye=eye, ball=ball, top=Vector(top), L=L, ball_r=ball_r, ball_dz=-hook_len - 0.1 - ball_r)

def hang_kf(sb, rfps, keys, ease=True):
    """keys = [(sec, stretch)] -> coil scale.z + ball_root z."""
    for t, s in keys:
        f = F(t, rfps); kf(sb['coil'], 'scale', f, (1, 1, s)); kf(sb['root'], 'location', f, (sb['top'].x, sb['top'].y, sb['top'].z - sb['L'] * s))
    (kf_ease if ease else kf_lin)(sb['coil']); (kf_ease if ease else kf_lin)(sb['root'])

def ball_world_z(sb, stretch): return sb['top'].z - sb['L'] * stretch + sb['ball_dz']

def ruler(x=1.75, z_top=8.6, length=5.2, n=50, name='Ruler', number_every=5, tick_w=0.16, y=0.0, num_size=0.26, marker_len=1.2):
    """Laboratory scale beside the spring: dark bar, minor/major ticks (array modifiers), glowing numbers, orange marker bar."""
    dark = mat_plastic((0.08, 0.10, 0.16), rough=0.5, name=name + '_bar'); white = mat_emit((1, 1, 1), strength=2.6, name=name + '_tick'); num_m = mat_emit((0.92, 0.94, 1.0), strength=3.0, name=name + '_num')
    bar = box(name + 'Bar', (0.34, 0.06, length + 0.3), (x + 0.17, y + 0.02, z_top - length / 2), dark, bev=0.02)
    sp = length / n
    mn = box(name + 'Tmin', (tick_w * 0.55, 0.02, 0.012), (x + tick_w * 0.55 / 2, y - 0.02, z_top), white)
    a = mn.modifiers.new('arr', 'ARRAY'); a.count = n + 1; a.use_relative_offset = False; a.use_constant_offset = True; a.constant_offset_displace = (0, 0, -sp)
    mj = box(name + 'Tmaj', (tick_w, 0.02, 0.02), (x + tick_w / 2, y - 0.02, z_top), white)
    a = mj.modifiers.new('arr', 'ARRAY'); a.count = n // number_every + 1; a.use_relative_offset = False; a.use_constant_offset = True; a.constant_offset_displace = (0, 0, -sp * number_every)
    nums = [text3d(f'{name}N{k}', str(k * number_every), (x + 0.27, y - 0.03, z_top - sp * k * number_every - 0.1), size=num_size, mat=num_m, align='LEFT') for k in range(1, n // number_every + 1)]
    nums.append(text3d(f'{name}N0', '1', (x + 0.27, y - 0.03, z_top - 0.1), size=num_size, mat=num_m, align='LEFT'))
    orange = mat_emit((1.0, 0.55, 0.08), strength=5.0, name=name + '_mark')
    mroot = empty(name + 'MarkerRoot', (x - marker_len / 2, y - 0.04, z_top - 2.0))
    marker = box(name + 'Marker', (marker_len, 0.03, 0.045), (0, 0, 0), orange); marker.parent = mroot
    tip = obj_add('cone', name + 'Tip', radius1=0.09, radius2=0.0, depth=0.22, vertices=32, location=(-marker_len / 2 - 0.1, 0, 0)); tip.rotation_euler = (0, -math.pi / 2, 0); setmat(tip, orange); smooth(tip); tip.parent = mroot
    return dict(bar=bar, marker=mroot, tip=tip, nums=nums, ticks=(mn, mj), x=x, y=y, z_top=z_top, sp=sp, marker_len=marker_len, marker_mesh=marker)

def ruler_marker_kf(ru, rfps, keys):
    """keys = [(sec, z)] world z of the marker line."""
    for t, z in keys: kf(ru['marker'], 'location', F(t, rfps), (ru['x'] - ru['marker_len'] / 2, ru['y'] - 0.04, z))
    kf_ease(ru['marker'])

def ruler_all(ru): return [ru['bar'], ru['marker_mesh'], ru['tip'], *ru['nums'], *ru['ticks']]

# ================================================================= hand
POSES = {'fist': ((85, 95, 70), (40, 60)), 'flat': ((4, 6, 6), (8, 10)), 'grip': ((48, 62, 45), (35, 45)), 'pinch': ((70, 80, 60), (50, 50))}
def hand(name, loc, pose='flat', rot=(0, 0, 0), scale=1.0, mat=None):
    """Stylised hand in its local frame: palm horizontal (back of the hand +Z, palm -Z), fingers along +Y, thumb on +X.
    Curl = rotation about local X so finger tips move toward -Z (palm side). ~17 bevelled parts."""
    m = mat or mat_skin(name + '_skin'); root = empty(name, loc); root.rotation_euler = rot; root.scale = (scale, scale, scale); parts = []
    def cap(n, r, length, pos, rot_e=(0, 0, 0), parent=None):
        o = obj_add('cylinder', n, radius=r, depth=length, vertices=40); o.location = pos; o.rotation_euler = rot_e
        try: mod = o.modifiers.new('bevel', 'BEVEL'); mod.width = r * 0.92; mod.segments = 10
        except Exception: pass
        setmat(o, m); smooth(o); o.parent = parent or root; parts.append(o); return o
    palm = box(name + 'Palm', (0.92, 1.0, 0.24), (0, 0, 0), m, bev=0.11, seg=8); subsurf(palm, 1, 2); palm.parent = root; parts.append(palm)
    cap(name + 'Wrist', 0.26, 1.6, (0, -1.15, 0.0), (math.pi / 2, 0, 0))
    curls, tcurl = POSES.get(pose, POSES['flat'])
    fingers = ((-0.36, 0.78, 0.105), (-0.12, 0.88, 0.11), (0.12, 0.84, 0.105), (0.36, 0.68, 0.095))
    for i, (x, Lf, r) in enumerate(fingers):
        prev = None; base = Vector((x, 0.48, 0.02)); seg_l = (Lf * 0.42, Lf * 0.32, Lf * 0.26)
        for j in range(3):
            e = empty(f'{name}F{i}J{j}', tuple(base) if prev is None else (0, seg_l[j - 1], 0)); e.parent = prev or root
            e.rotation_euler = (-math.radians(curls[j]), 0, 0)
            cap(f'{name}F{i}S{j}', r * (1 - 0.08 * j), seg_l[j] + r * 0.6, (0, seg_l[j] / 2, 0), (math.pi / 2, 0, 0), parent=e)
            prev = e
    # thumb: two segments angled outward
    tb = empty(name + 'T0', (0.46, 0.0, -0.04)); tb.parent = root; tb.rotation_euler = (-math.radians(tcurl[0]) * 0.4, math.radians(-20), math.radians(-48))
    cap(name + 'TS0', 0.12, 0.5, (0, 0.25, 0), (math.pi / 2, 0, 0), parent=tb)
    t1 = empty(name + 'T1', (0, 0.48, 0)); t1.parent = tb; t1.rotation_euler = (-math.radians(tcurl[1]), 0, 0)
    cap(name + 'TS1', 0.105, 0.4, (0, 0.2, 0), (math.pi / 2, 0, 0), parent=t1)
    return root, parts

# ================================================================= tank and water
def glass_tank(name='Tank', half=2.9, h=5.6, wall=0.16, loc=(0, 0, 0)):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * 2 * half, v.co.y * 2 * half, (v.co.z + 0.5) * h))
    top = [f for f in bm.faces if all(v.co.z > h - 1e-4 for v in f.verts)]
    bmesh.ops.delete(bm, geom=top, context='FACES')
    o = mesh_obj(name, bm, mat_tank_glass(name + '_g'), loc); solidify(o, wall); bevel(o, 0.03, 4); smooth(o, auto=True)
    rim = box(name + 'Rim', (2 * half + 2 * wall + 0.06, 2 * half + 2 * wall + 0.06, 0.08), (loc[0], loc[1], loc[2] + 0.02), mat_metal((0.35, 0.37, 0.4), rough=0.4, name=name + '_base'), bev=0.02)
    return o

def water_block(name='Water', half=2.78, level=3.6, loc=(0, 0, 0), grid=44, color=(0.10, 0.40, 0.95)):
    """Water with a subdivided top face (vertex group 'top') so ripples can be added with wave modifiers. Origin at the bottom:
    scale.z raises the level."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * 2 * half, v.co.y * 2 * half, (v.co.z + 0.5) * level))
    top_edges = [e for e in bm.edges if all(abs(v.co.z - level) < 1e-6 for v in e.verts)]
    bmesh.ops.subdivide_edges(bm, edges=top_edges, cuts=grid, use_grid_fill=True)
    o = mesh_obj(name, bm, mat_water(name + '_m', color), loc)
    vg = o.vertex_groups.new(name='top'); vg.add([v.index for v in o.data.vertices if abs(v.co.z - level) < 1e-6], 1.0, 'REPLACE')
    smooth(o, auto=True); o['level'] = level
    return o

def ripple(water, f_start, x=0.0, y=0.0, height=0.07, width=0.5, speed=0.22, life=70, damp=40, name='wave'):
    wm = water.modifiers.new(name, 'WAVE'); wm.vertex_group = 'top'; wm.height = height; wm.width = width; wm.narrowness = 1.6; wm.speed = speed
    wm.time_offset = f_start; wm.lifetime = life; wm.damping_time = damp; wm.start_position_x = x; wm.start_position_y = y; wm.use_normal = False
    return wm

def level_kf(water, rfps, keys):
    for t, lv in keys: kf(water, 'scale', F(t, rfps), (1, 1, lv / water['level']))
    kf_ease(water)

def surface_ring(name, loc, r0=0.3, r1=1.4, f0=1, f1=40, color=(0.75, 0.9, 1.0)):
    """A thin expanding splash ring on the surface when a ball breaks it."""
    o = obj_add('torus', name, major_radius=1.0, minor_radius=0.05, major_segments=128, minor_segments=12, location=loc); o.scale = (r0, r0, 0.5)
    m = mat_emit(color, strength=1.5, name=name + '_m', alpha=0.5); setmat(o, m); smooth(o)
    kf(o, 'hide_render', 1, True); kf(o, 'hide_render', f0, False); kf(o, 'hide_render', f1, True)
    kf(o, 'scale', f0, (r0, r0, 0.5)); kf(o, 'scale', f1, (r1, r1, 0.15)); kf_ease(o, 'EASE_OUT')
    return o

# ================================================================= force graphics
def chevron_mesh(name, w=0.2, h=0.13, t=0.055, color=(0.35, 0.6, 1.0), strength=6.0):
    bm = bmesh.new(); pts = [(-w, 0, h), (0, 0, 0), (w, 0, h), (w, 0, h + t), (0, 0, t), (-w, 0, h + t)]
    vs = [bm.verts.new(p) for p in pts]; bm.faces.new((vs[0], vs[1], vs[4], vs[5])); bm.faces.new((vs[1], vs[2], vs[3], vs[4]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(mat_emit(color, strength=strength, name=name + '_m'))
    return me

def _stream_rot(d, face=(0, -1, 0)):
    """Rotation whose local -Z follows d and whose local Y (the chevron plane normal) stays as close as possible to `face`
    (toward the camera at -Y), so the flat chevrons are never seen edge-on whatever the stream direction."""
    from mathutils import Matrix
    z = -Vector(d).normalized(); f = Vector(face); y = f - z * f.dot(z)
    if y.length < 1e-4: y = Vector((0, 0, 1)) - z * z.z
    y.normalize(); x = y.cross(z).normalized()
    return Matrix((x, y, z)).transposed()

def chevron_stream(name, p0, p1, n=9, color=(0.35, 0.6, 1.0), size=0.2, strength=6.0, rfps=12, nf=240, period=0.55, f_on=None, f_off=None, parent=None):
    """n chevrons streaming from p0 toward p1 (V tips point at p1). Returns (root, objects). Coordinates in parent's space."""
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0; L = d.length; sp = L / n
    root = empty(name, tuple(p0)); root.rotation_euler = _stream_rot(d).to_euler()
    if parent is not None: root.parent = parent
    slider = empty(name + 'Slide', (0, 0, 0)); slider.parent = root
    me = chevron_mesh(name + 'M', w=size, h=size * 0.65, t=size * 0.28, color=color, strength=strength); objs = []
    for i in range(n):
        o = link(bpy.data.objects.new(f'{name}{i}', me)); o.parent = slider; o.location = (0, 0, -sp * i - sp * 0.5); objs.append(o)
    sawtooth(slider, 1, nf, L, (0, 0, -sp), max(2, int(round(period * rfps))))
    show_from(objs, f_on, f_off)
    return root, objs

def arc_dots(name, center, radii=(0.95, 1.3, 1.65), n=13, color=(1.0, 0.42, 0.5), r=0.045, strength=5.0, rfps=12, nf=240, period=1.7, f_on=None, f_off=None, spread=62.0, column=True):
    """Upward-thrust marker: dots on U-shaped arcs below the ball that flow from the bottom up to both sides, plus a rising column."""
    m = mat_emit(color, strength=strength, name=name + '_m'); objs = []; cx, cy, cz = center; step = 2; pf = max(4, int(period * rfps))
    for ai, R in enumerate(radii):
        for i in range(n):
            o = obj_add('uv_sphere', f'{name}A{ai}D{i}', radius=r * (1.0 - 0.12 * ai), segments=16, ring_count=8); setmat(o, m); smooth(o, auto=False); objs.append(o)
            sgn = -1 if i % 2 == 0 else 1; phase = (i // 2) / (n / 2.0)
            for f in range(1, nf + 1, step):
                u = (phase + (f - 1) / pf) % 1.0; ang = math.radians(-90 + sgn * u * spread)
                kf(o, 'location', f, (cx + R * math.cos(ang), cy, cz + R * math.sin(ang)))
            kf_lin(o)
    if column:
        for i in range(6):
            o = obj_add('uv_sphere', f'{name}C{i}', radius=r * 0.9, segments=16, ring_count=8); setmat(o, m); smooth(o, auto=False); objs.append(o)
            for f in range(1, nf + 1, step):
                u = (i / 6.0 + (f - 1) / pf) % 1.0; kf(o, 'location', f, (cx, cy, cz - radii[-1] - 0.5 + u * (radii[-1] + 0.5 - 0.35)))
            kf_lin(o)
    show_from(objs, f_on, f_off)
    return objs

def down_arrows(name, center, nx=4, ny=3, dx=1.15, dy=1.1, drop=0.35, color=(1.0, 0.72, 0.1), rfps=12, nf=240, period=0.8, f_on=None, f_off=None, z_amp=0.3):
    """Atmospheric-pressure arrows: a grid of glowing arrowheads pressing down on the surface (bobbing sawtooth)."""
    m = mat_emit(color, strength=6.0, name=name + '_m'); objs = []; cx, cy, cz = center; pf = max(3, int(period * rfps))
    for ix in range(nx):
        for iy in range(ny):
            x = cx + (ix - (nx - 1) / 2) * dx; y = cy + (iy - (ny - 1) / 2) * dy
            root = empty(f'{name}R{ix}{iy}', (x, y, cz)); root.rotation_euler = (0, 0, 0)
            head = obj_add('cone', f'{name}H{ix}{iy}', radius1=0.16, radius2=0.0, depth=0.24, vertices=32, location=(0, 0, 0.12)); head.rotation_euler = (math.pi, 0, 0); setmat(head, m); smooth(head); head.parent = root
            stem = obj_add('cylinder', f'{name}S{ix}{iy}', radius=0.045, depth=0.32, vertices=16, location=(0, 0, 0.4)); setmat(stem, m); stem.parent = root
            objs += [head, stem]
            f = 1 + (ix * 3 + iy * 5) % pf
            kf(root, 'location', 1, (x, y, cz + z_amp));
            sawtooth(root, 1, nf, 0, (0, 0, -z_amp), pf)
    show_from(objs, f_on, f_off)
    return objs

def radial_arrows(name, center, n=10, r0=0.85, travel=0.55, color=(0.25, 0.75, 1.0), rfps=12, nf=240, period=1.0, f_on=None, f_off=None, size=0.16):
    """Displaced-water arrows: small glowing arrowheads flying outward from the ball (sawtooth)."""
    m = mat_emit(color, strength=6.0, name=name + '_m'); objs = []; cx, cy, cz = center; pf = max(3, int(period * rfps))
    for i in range(n):
        a = math.radians(-160 + 140 * i / (n - 1)) if n > 1 else 0.0; y_off = 0.0 if i % 3 else 0.5 * (1 if i % 2 else -1)
        d = Vector((math.cos(a), y_off * 0.6, math.sin(a))).normalized()
        root = empty(f'{name}R{i}', (cx + d.x * r0, cy + d.y * r0, cz + d.z * r0)); root.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
        head = obj_add('cone', f'{name}H{i}', radius1=size * 0.6, radius2=0.0, depth=size * 1.1, vertices=24, location=(0, 0, size * 0.55)); setmat(head, m); smooth(head); head.parent = root
        stem = obj_add('cylinder', f'{name}S{i}', radius=size * 0.16, depth=size * 0.9, vertices=12, location=(0, 0, -size * 0.45)); setmat(stem, m); stem.parent = root
        objs += [head, stem]
        sawtooth(root, 1, nf, 0, tuple(d * travel), pf)
    show_from(objs, f_on, f_off)
    return objs

def glow_line(name, p0, p1, r=0.035, color=(0.2, 0.8, 1.0), strength=7.0, f_on=None, f_off=None, dotted=False, n_dots=26):
    """Straight emissive line (or dotted line) between two points."""
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0; objs = []
    m = mat_emit(color, strength=strength, name=name + '_m')
    if dotted:
        for i in range(n_dots):
            o = obj_add('uv_sphere', f'{name}D{i}', radius=r * 1.6, segments=12, ring_count=6, location=tuple(p0 + d * ((i + 0.5) / n_dots))); setmat(o, m); smooth(o, auto=False); objs.append(o)
    else:
        o = obj_add('cylinder', name, radius=r, depth=d.length, vertices=24); o.location = tuple((p0 + p1) / 2); o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); setmat(o, m); smooth(o); objs.append(o)
    show_from(objs, f_on, f_off)
    return objs

def arrow_solid(name, p0, p1, r=0.05, color=(0.2, 0.8, 1.0), strength=7.0, head=0.3, f_on=None, f_off=None):
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0; L = d.length; u = d.normalized(); m = mat_emit(color, strength=strength, name=name + '_m')
    sh = obj_add('cylinder', name, radius=r, depth=L - head, vertices=24); sh.location = tuple(p0 + u * (L - head) / 2); sh.rotation_euler = u.to_track_quat('Z', 'Y').to_euler(); setmat(sh, m); smooth(sh)
    hd = obj_add('cone', name + 'Head', radius1=r * 2.8, radius2=0.0, depth=head, vertices=32); hd.location = tuple(p1 - u * head / 2); hd.rotation_euler = u.to_track_quat('Z', 'Y').to_euler(); setmat(hd, m); smooth(hd)
    show_from([sh, hd], f_on, f_off)
    return [sh, hd]

# ================================================================= space bodies
def _img(fn):
    p = os.path.join(ASSETS, fn); return bpy.data.images.load(p) if os.path.exists(p) else None

def earth(loc=(0, 0, 0), r=1.0, name='Earth', clouds=True, atmo=True, spin=None, nf=240, rfps=12, seg=160):
    """NASA Blue Marble Earth: image colour, ocean gloss from the blue channel, cloud shell (alpha), fresnel atmosphere rim."""
    o = obj_add('uv_sphere', name, radius=r, segments=seg, ring_count=seg // 2, location=loc); smooth(o); subsurf(o, 0, 1)
    m, p = _principled(name + '_m'); nt = m.node_tree; n = nt.nodes; img = _img('earth_day_5400.jpg') or _img('earth_day_2048.jpg')
    if img is not None:
        tc = n.new('ShaderNodeTexCoord'); ti = n.new('ShaderNodeTexImage'); ti.image = img
        nt.links.new(tc.outputs['UV'], ti.inputs['Vector']); nt.links.new(ti.outputs['Color'], p.inputs['Base Color'])
        sep = n.new('ShaderNodeSeparateColor'); nt.links.new(ti.outputs['Color'], sep.inputs['Color'])
        sub = n.new('ShaderNodeMath'); sub.operation = 'SUBTRACT'; nt.links.new(sep.outputs['Blue'], sub.inputs[0]); nt.links.new(sep.outputs['Red'], sub.inputs[1])
        mr = n.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.02; mr.inputs['From Max'].default_value = 0.16; mr.inputs['To Min'].default_value = 0.72; mr.inputs['To Max'].default_value = 0.22
        nt.links.new(sub.outputs[0], mr.inputs['Value']); nt.links.new(mr.outputs['Result'], p.inputs['Roughness'])
        _inp(p, 'Specular IOR Level', 0.55)
    else:   # procedural fallback: noise continents
        tc = n.new('ShaderNodeTexCoord'); noise = n.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 2.2; noise.inputs['Detail'].default_value = 9; noise.inputs['Roughness'].default_value = 0.62
        ramp = n.new('ShaderNodeValToRGB'); cr = ramp.color_ramp; cr.elements[0].position = 0.47; cr.elements[0].color = (0.02, 0.09, 0.35, 1); cr.elements[1].position = 0.52; cr.elements[1].color = (0.18, 0.36, 0.12, 1)
        e2 = cr.elements.new(0.62); e2.color = (0.42, 0.34, 0.2, 1)
        nt.links.new(tc.outputs['Object'], noise.inputs['Vector']); nt.links.new(noise.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], p.inputs['Base Color']); _inp(p, 'Roughness', 0.45)
    setmat(o, m); out = dict(body=o)
    if clouds:
        c = obj_add('uv_sphere', name + 'Clouds', radius=r * 1.012, segments=seg, ring_count=seg // 2, location=loc); smooth(c)
        cm, cp = _principled(name + '_clouds'); cnt = cm.node_tree; cn = cnt.nodes; cimg = _img('earth_clouds_2048.jpg')
        _inp(cp, 'Base Color', (1, 1, 1, 1)); _inp(cp, 'Roughness', 0.9)
        if cimg is not None:
            tc2 = cn.new('ShaderNodeTexCoord'); ti2 = cn.new('ShaderNodeTexImage'); ti2.image = cimg; cnt.links.new(tc2.outputs['UV'], ti2.inputs['Vector'])
            pw = cn.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 1.6; cnt.links.new(ti2.outputs['Color'], pw.inputs[0])
            ml = cn.new('ShaderNodeMath'); ml.operation = 'MULTIPLY'; ml.inputs[1].default_value = 0.9; cnt.links.new(pw.outputs[0], ml.inputs[0]); cnt.links.new(ml.outputs[0], cp.inputs['Alpha'])
        else:
            tc2 = cn.new('ShaderNodeTexCoord'); nz = cn.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 5; nz.inputs['Detail'].default_value = 8
            rp = cn.new('ShaderNodeValToRGB'); rp.color_ramp.elements[0].position = 0.5; rp.color_ramp.elements[1].position = 0.7
            cnt.links.new(tc2.outputs['Object'], nz.inputs['Vector']); cnt.links.new(nz.outputs['Fac'], rp.inputs['Fac']); cnt.links.new(rp.outputs['Color'], cp.inputs['Alpha'])
        _blend(cm); setmat(c, cm); parent_keep(c, o); out['clouds'] = c
    if atmo:
        a = obj_add('uv_sphere', name + 'Atmo', radius=r * 1.03, segments=seg, ring_count=seg // 2, location=loc); smooth(a)
        am, ap = _principled(name + '_atmo'); ant = am.node_tree; an = ant.nodes
        lw = an.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.6; pw = an.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 2.6
        mul = an.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 0.85
        ant.links.new(lw.outputs['Fresnel'], pw.inputs[0]); ant.links.new(pw.outputs[0], mul.inputs[0]); ant.links.new(mul.outputs[0], ap.inputs['Alpha'])
        _inp(ap, 'Base Color', (0.3, 0.55, 1.0, 1)); _inp(ap, 'Emission Color', (0.35, 0.6, 1.0, 1)); _inp(ap, 'Emission Strength', 1.6); _inp(ap, 'Roughness', 1.0)
        _blend(am); am.use_backface_culling = True; setmat(a, am); parent_keep(a, o); out['atmo'] = a
    if spin:   # degrees per second about Z
        kf(o, 'rotation_euler', 1, (0, 0, math.radians(spin[1]))); kf(o, 'rotation_euler', nf, (0, 0, math.radians(spin[1] + spin[0] * nf / rfps))); kf_lin(o)
    return out

def moon(loc=(0, 0, 0), r=0.27, name='Moon', seg=128, disp=0.03):
    o = obj_add('uv_sphere', name, radius=r, segments=seg, ring_count=seg // 2, location=loc); smooth(o)
    m, p = _principled(name + '_m'); nt = m.node_tree; n = nt.nodes; img = _img('moon_color_1k.jpg')
    if img is not None:
        tc = n.new('ShaderNodeTexCoord'); ti = n.new('ShaderNodeTexImage'); ti.image = img; nt.links.new(tc.outputs['UV'], ti.inputs['Vector']); nt.links.new(ti.outputs['Color'], p.inputs['Base Color'])
    else:
        tc = n.new('ShaderNodeTexCoord'); nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 12; nz.inputs['Detail'].default_value = 8
        rp = n.new('ShaderNodeValToRGB'); rp.color_ramp.elements[0].color = (0.25, 0.25, 0.26, 1); rp.color_ramp.elements[1].color = (0.6, 0.6, 0.62, 1)
        nt.links.new(tc.outputs['Object'], nz.inputs['Vector']); nt.links.new(nz.outputs['Fac'], rp.inputs['Fac']); nt.links.new(rp.outputs['Color'], p.inputs['Base Color'])
    _inp(p, 'Roughness', 0.95); _inp(p, 'Specular IOR Level', 0.2); setmat(o, m)
    dimg = _img('moon_disp_1k.jpg')
    try:
        if dimg is not None:
            tx = bpy.data.textures.new(name + '_disp', 'IMAGE'); tx.image = dimg; dm = o.modifiers.new('disp', 'DISPLACE'); dm.texture = tx; dm.texture_coords = 'UV'; dm.strength = r * disp * 2; dm.mid_level = 0.5
        else:
            tx = bpy.data.textures.new(name + '_disp', 'CLOUDS'); tx.noise_scale = 0.35; dm = o.modifiers.new('disp', 'DISPLACE'); dm.texture = tx; dm.strength = r * disp * 2
    except Exception as e: print('moon disp', e)
    return o

def sun(loc=(0, 0, 0), r=1.4, name='Sun', nf=240, rfps=12, light_e=2500, halo=True):
    o = obj_add('uv_sphere', name, radius=r, segments=128, ring_count=64, location=loc); smooth(o)
    m, p = _principled(name + '_m'); nt = m.node_tree; n = nt.nodes
    tc = n.new('ShaderNodeTexCoord'); mp = n.new('ShaderNodeMapping'); nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 4.5; nz.inputs['Detail'].default_value = 8; nz.inputs['Roughness'].default_value = 0.7
    rp = n.new('ShaderNodeValToRGB'); cr = rp.color_ramp; cr.elements[0].position = 0.3; cr.elements[0].color = (0.75, 0.1, 0.0, 1); cr.elements[1].position = 0.78; cr.elements[1].color = (1.0, 0.5, 0.1, 1)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], nz.inputs['Vector']); nt.links.new(nz.outputs['Fac'], rp.inputs['Fac']); nt.links.new(rp.outputs['Color'], p.inputs['Emission Color'])
    _inp(p, 'Emission Strength', 1.7); _inp(p, 'Base Color', (0, 0, 0, 1))
    mp.inputs['Location'].default_value = (0, 0, 0); mp.inputs['Location'].keyframe_insert('default_value', frame=1)
    mp.inputs['Location'].default_value = (0.6 * nf / rfps / 10.0, 0, 0.4 * nf / rfps / 10.0); mp.inputs['Location'].keyframe_insert('default_value', frame=nf)
    setmat(o, m)
    if halo:
        h = obj_add('uv_sphere', name + 'Halo', radius=r * 1.4, segments=96, ring_count=48, location=loc); smooth(h)
        hm, hp = _principled(name + '_halo'); hnt = hm.node_tree; hn = hnt.nodes
        lw = hn.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.5; pw = hn.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 3.0
        mul = hn.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 0.4
        hnt.links.new(lw.outputs['Facing'], pw.inputs[0]); hnt.links.new(pw.outputs[0], mul.inputs[0]); hnt.links.new(mul.outputs[0], hp.inputs['Alpha'])
        _inp(hp, 'Base Color', (0, 0, 0, 1)); _inp(hp, 'Emission Color', (1.0, 0.42, 0.08, 1)); _inp(hp, 'Emission Strength', 1.8); _blend(hm); setmat(h, hm)
        parent_keep(h, o)
        if is_cycles():   # volumetric corona
            v = obj_add('uv_sphere', name + 'Corona', radius=r * 1.6, segments=48, ring_count=24, location=loc)
            vm = bpy.data.materials.new(name + '_corona'); vm.use_nodes = True; vnt = vm.node_tree
            for nd in list(vnt.nodes): vnt.nodes.remove(nd)
            out = vnt.nodes.new('ShaderNodeOutputMaterial'); pv = vnt.nodes.new('ShaderNodeVolumePrincipled'); sph = vnt.nodes.new('ShaderNodeTexGradient'); sph.gradient_type = 'SPHERICAL'
            tcv = vnt.nodes.new('ShaderNodeTexCoord'); pwv = vnt.nodes.new('ShaderNodeMath'); pwv.operation = 'POWER'; pwv.inputs[1].default_value = 5.0; mlv = vnt.nodes.new('ShaderNodeMath'); mlv.operation = 'MULTIPLY'; mlv.inputs[1].default_value = 0.22
            vnt.links.new(tcv.outputs['Generated'], sph.inputs['Vector']); vnt.links.new(sph.outputs['Fac'], pwv.inputs[0]); vnt.links.new(pwv.outputs[0], mlv.inputs[0]); vnt.links.new(mlv.outputs[0], pv.inputs['Density'])
            pv.inputs['Color'].default_value = (1, 0.45, 0.12, 1); pv.inputs['Emission Color'].default_value = (1, 0.4, 0.08, 1); pv.inputs['Emission Strength'].default_value = 0.5
            vnt.links.new(pv.outputs['Volume'], out.inputs['Volume']); setmat(v, vm); parent_keep(v, o)
    L = light('POINT', loc, light_e, (1.0, 0.82, 0.55), name + 'Light')
    try: L.data.shadow_soft_size = r * 0.9
    except Exception: pass
    return o

def orbit_ring(name, R, loc=(0, 0, 0), color=(0.1, 0.28, 1.0), r=0.014, strength=2.6, segs=256):
    o = obj_add('torus', name, major_radius=R, minor_radius=r, major_segments=segs, minor_segments=8, location=loc); setmat(o, mat_emit(color, strength=strength, name=name + '_m')); smooth(o); return o

PLANETS = [  # name, orbit radius, planet radius, colour, band noise
    ('Mercury', 2.5, 0.11, (0.55, 0.52, 0.5), 0.0), ('Venus', 3.3, 0.19, (0.86, 0.72, 0.45), 0.2), ('Earth', 4.3, 0.21, None, 0.0),
    ('Mars', 5.3, 0.15, (0.8, 0.36, 0.18), 0.1), ('Jupiter', 6.9, 0.58, (0.78, 0.62, 0.45), 0.9), ('Saturn', 8.6, 0.5, (0.85, 0.75, 0.5), 0.6),
    ('Uranus', 10.1, 0.32, (0.55, 0.85, 0.92), 0.2), ('Neptune', 11.4, 0.31, (0.25, 0.4, 0.95), 0.3)]

def banded_mat(name, color, band):
    m, p = _principled(name); nt = m.node_tree; n = nt.nodes
    tc = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sep.inputs['Vector'])
    wave = n.new('ShaderNodeTexWave'); wave.inputs['Scale'].default_value = 9.0; wave.inputs['Distortion'].default_value = 1.6; wave.inputs['Detail'].default_value = 3.0
    nt.links.new(tc.outputs['Object'], wave.inputs['Vector']); wave.bands_direction = 'Z'
    ramp = n.new('ShaderNodeValToRGB'); c = color; ramp.color_ramp.elements[0].color = (c[0] * 0.65, c[1] * 0.6, c[2] * 0.55, 1); ramp.color_ramp.elements[1].color = (min(1, c[0] * 1.15), min(1, c[1] * 1.12), min(1, c[2] * 1.1), 1)
    mix = n.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.inputs['Factor'].default_value = band; mix.inputs[6].default_value = (*color, 1)
    nt.links.new(wave.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], mix.inputs[7]); nt.links.new(mix.outputs[2], p.inputs['Base Color'])
    _inp(p, 'Roughness', 0.7); return m

def solar_system(nf, rfps, sun_r=1.35, t_scale=1.0, earth_moon=True, rings=True, phase=0.0, orbit_speed=1.0):
    """Sun + 8 planets on orbit tori, all revolving (angular speed ~ 1/sqrt(R)); Earth carries the Moon on an orange ring."""
    S = sun((0, 0, 0), r=sun_r, nf=nf, rfps=rfps); out = dict(sun=S, planets={}, roots={})
    for i, (nm, R, pr, col, band) in enumerate(PLANETS):
        if rings: orbit_ring(f'Orb{nm}', R)
        root = empty(f'Root{nm}', (0, 0, 0)); a0 = phase + i * 1.9
        w = orbit_speed * 0.55 / math.sqrt(R / 2.5)          # rad/s
        kf(root, 'rotation_euler', 1, (0, 0, a0)); kf(root, 'rotation_euler', nf, (0, 0, a0 + w * nf / rfps)); kf_lin(root)
        if nm == 'Earth':
            e = earth((R, 0, 0), r=pr, name='Earth', clouds=True, atmo=True, seg=96)['body']; e.parent = root; e.location = (R, 0, 0)
            if earth_moon:
                orb = orbit_ring('OrbMoon', pr * 2.3, loc=(R, 0, 0), color=(1.0, 0.55, 0.12), r=0.012, strength=4.0, segs=128); orb.parent = root; orb.location = (R, 0, 0)
                mroot = empty('RootMoon', (R, 0, 0)); mroot.parent = root
                mo = moon((pr * 2.3, 0, 0), r=pr * 0.28, name='Moon', seg=64); mo.parent = mroot; mo.location = (pr * 2.3, 0, 0)
                kf(mroot, 'rotation_euler', 1, (0, 0, 0)); kf(mroot, 'rotation_euler', nf, (0, 0, 2.2 * nf / rfps)); kf_lin(mroot)
                out['moon'] = mo
            out['planets'][nm] = e
        else:
            o = obj_add('uv_sphere', nm, radius=pr, segments=64, ring_count=32, location=(R, 0, 0)); smooth(o); setmat(o, banded_mat(nm + '_m', col, band)); o.parent = root; o.location = (R, 0, 0)
            if nm == 'Saturn':
                rg = obj_add('torus', 'SaturnRing', major_radius=pr * 1.7, minor_radius=pr * 0.45, major_segments=96, minor_segments=8, location=(R, 0, 0)); rg.scale = (1, 1, 0.04); rg.rotation_euler = (math.radians(22), 0, 0)
                setmat(rg, mat_plastic((0.82, 0.74, 0.55), rough=0.6, name='sring_m')); smooth(rg); rg.parent = root; rg.location = (R, 0, 0)
            out['planets'][nm] = o
        out['roots'][nm] = root
    return out

# ================================================================= rocks and sparks
def rock(name, loc, r=0.3, seed=3, mat=None):
    rnd = random.Random(seed); o = obj_add('ico_sphere', name, radius=r, subdivisions=4, location=loc)
    bm = bmesh.new(); bm.from_mesh(o.data)
    for v in bm.verts:
        n = v.co.normalized(); k = 1 + 0.16 * math.sin(n.x * 7.1 + seed) * math.cos(n.y * 6.3) + 0.12 * math.sin(n.z * 9.7 + n.x * 3) + rnd.uniform(-0.03, 0.03)
        v.co = v.co * k
    bm.to_mesh(o.data); bm.free(); setmat(o, mat or mat_rock(name + '_m')); smooth(o); subsurf(o, 1, 1)
    o.rotation_euler = (rnd.random() * 3, rnd.random() * 3, rnd.random() * 3)
    return o

def fire_shell(name, parent, r, up=(0, 0, 1)):
    """Glowing hot front + halo around a meteor (alpha-blended emission), parented to the rock's root."""
    o = obj_add('uv_sphere', name, radius=r * 1.3, segments=48, ring_count=24, location=(0, 0, -r * 0.15)); o.scale = (1, 1, 1.3)
    m = mat_emit((1.0, 0.42, 0.06), strength=2.0, name=name + '_m', alpha=0.22); setmat(o, m); smooth(o); o.parent = parent
    c = obj_add('uv_sphere', name + 'Core', radius=r * 1.02, segments=32, ring_count=16, location=(0, 0, -r * 0.45)); setmat(c, mat_emit((1.0, 0.7, 0.25), strength=2.6, name=name + '_core', alpha=0.3)); smooth(c); c.parent = parent
    L = light('POINT', (0, 0, 0), 60, (1.0, 0.55, 0.2), name + 'L'); L.parent = parent
    return [o, c]

def sparks(name, path_fn, n, rfps, nf, t0=0.0, t1=None, life=0.9, spread=0.25, color=(1.0, 0.65, 0.2), seed=5, rise=(0, 0, 1.0), r=0.035):
    """Small glowing sparks spawned along a moving object's path (path_fn(sec) -> world Vector) that drift 'rise'-ward and vanish."""
    rnd = random.Random(seed); m = mat_emit(color, strength=8.0, name=name + '_m'); objs = []; t1 = (nf / rfps) if t1 is None else t1
    for i in range(n):
        ts = rnd.uniform(t0, t1 - 0.2); fs, fe = F(ts, rfps), F(min(t1, ts + life * rnd.uniform(0.6, 1.2)), rfps)
        if fe <= fs: continue
        o = obj_add('ico_sphere', f'{name}{i}', radius=r * rnd.uniform(0.6, 1.4), subdivisions=1); setmat(o, m); smooth(o, auto=False); objs.append(o)
        p0 = Vector(path_fn(ts)) + Vector((rnd.uniform(-spread, spread), rnd.uniform(-spread, spread) * 0.5, rnd.uniform(-spread, spread)))
        p1 = p0 + Vector(rise) * rnd.uniform(0.8, 1.6) + Vector((rnd.uniform(-spread, spread), 0, 0))
        kf(o, 'hide_render', 1, True); kf(o, 'hide_render', fs, False); kf(o, 'hide_render', fe, True)
        kf(o, 'location', fs, tuple(p0)); kf(o, 'location', fe, tuple(p1)); kf(o, 'scale', fs, (1, 1, 1)); kf(o, 'scale', fe, (0.15, 0.15, 0.15)); kf_lin(o)
    return objs

# ================================================================= wooden block + thrust object
def wood_block(name, loc, size=4.0, mat=None):
    o = box(name, (size, size, size), (loc[0], loc[1], loc[2] + size / 2), mat or mat_wood_block(name + '_m'), bev=0.07, seg=8); return o

def t_object(name, loc, plate=1.35, plate_h=0.16, stem=0.34, stem_h=1.25, top=1.05, top_h=0.13, color=(0.2, 0.42, 1.0), rot=(0, 0, 0), chevrons=True, rfps=12, nf=240, chev_on=None, glow=True):
    """T-shaped wooden press: coloured contact slab, base plate, square post, top plate. Local frame: base at z=0, up = +Z.
    The 'slab' is the coloured footprint whose scale/colour the pressure shots animate. Post chevrons (cyan) stream downward."""
    root = empty(name, loc); root.rotation_euler = rot; wood = mat_wood_block(name + '_w', scale=2.2, tint=(0.8, 0.56, 0.3)); parts = []
    slab_m = mat_plastic(tuple(c * 0.55 for c in color), rough=0.3, name=name + '_slab', coat=0.6); p = slab_m.node_tree.nodes['Principled BSDF']; _inp(p, 'Emission Color', (*color, 1)); _inp(p, 'Emission Strength', 1.4 if glow else 0.0)
    slab = box(name + 'Slab', (plate, plate, 0.07), (0, 0, 0.035), slab_m, bev=0.02); slab.parent = root; parts.append(slab)
    base = box(name + 'Base', (plate * 0.82, plate * 0.82, plate_h), (0, 0, 0.07 + plate_h / 2), wood, bev=0.03); base.parent = root; parts.append(base)
    post = box(name + 'Post', (stem, stem, stem_h), (0, 0, 0.07 + plate_h + stem_h / 2), wood, bev=0.03); post.parent = root; parts.append(post)
    topp = box(name + 'Top', (top, top, top_h), (0, 0, 0.07 + plate_h + stem_h + top_h / 2), wood, bev=0.03); topp.parent = root; parts.append(topp)
    out = dict(root=root, slab=slab, slab_m=slab_m, base=base, post=post, top=topp, parts=parts, top_z=0.07 + plate_h + stem_h + top_h, plate=plate)
    if chevrons:
        z0, z1 = 0.07 + plate_h + stem_h - 0.05, 0.07 + plate_h + 0.05
        for side, (dx, dy, rz) in {'front': (0, -stem / 2 - 0.02, 0), 'right': (stem / 2 + 0.02, 0, math.pi / 2)}.items():
            r_, objs = chevron_stream(name + 'Ch' + side, (dx, dy, z0), (dx, dy, z1), n=6, color=(0.15, 0.85, 1.0), size=stem * 0.36, strength=7.0, rfps=rfps, nf=nf, period=0.5, f_on=chev_on, parent=root)
            r_.rotation_euler = (0, 0, rz); out.setdefault('chev', []).extend(objs)
    return out

def slab_kf(t, rfps, keys):
    """keys = [(sec, size_scale, color)] -> animate the coloured footprint (stepwise: hold then quick change)."""
    for i, (sec, s, col) in enumerate(keys):
        f = F(sec, rfps)
        if i > 0: kf(t['slab'], 'scale', f - max(3, int(0.5 * rfps)), tuple(t['slab'].scale))
        kf(t['slab'], 'scale', f, (s, s, 1)); color_kf(t['slab_m'], [(f, col)], sockets=('Emission Color',)); color_kf(t['slab_m'], [(f, tuple(c * 0.55 for c in col))], sockets=('Base Color',))
    kf_ease(t['slab'])

# ================================================================= cameras
def cam_path(cam, tgt, rfps, keys, ease=True):
    """keys = [(sec, cam_loc, tgt_loc)] -> eased camera + target path."""
    for sec, cl, tl in keys:
        f = F(sec, rfps); kf(cam, 'location', f, cl)
        if tl is not None: kf(tgt, 'location', f, tl)
    (kf_ease if ease else kf_lin)(cam); (kf_ease if ease else kf_lin)(tgt)

# ================================================================= scene assemblies
def tank_scene(nf, rfps, level=3.6, target=(0, 0, 3.2), key_e=1900, spot=60, with_bench=False, water_color=(0.10, 0.40, 0.95)):
    reset(); lab_stage(target=target, key_e=key_e, spot=spot, key=(4.0, -6.0, 12.0))
    if with_bench: bench()
    tank = glass_tank('Tank'); water = water_block('Water', level=level, color=water_color)
    return tank, water

def spring_scene(nf, rfps, top=(0, 0, 9.6), hand_on=True, ball_mat=None, target=(0, 0, 7.0), key_e=2400, spot=55):
    """Hand holding the balance ring from above, ball hanging below; no tank."""
    reset(); lab_stage(target=target, key_e=key_e, spot=spot, key=(3.0, -5.5, 14.0))
    sb = spring_balance(top=top, ball_mat=ball_mat)
    hd = None
    if hand_on:
        hd, _ = hand('Hand', (top[0] - 0.05, top[1] + 0.1, top[2] + 0.55), pose='fist', rot=(-math.pi / 2, 0, 0), scale=0.95)
    return sb, hd

# ================================================================= BUILDERS: intro + Archimedes
def intro_tank(nf, rfps, dur):
    tank, water = tank_scene(nf, rfps, level=3.9, target=(0, 0, 3.4))
    sb = spring_balance(top=(0, 0, 8.1), L=2.6); hang_kf(sb, rfps, [(0, 1.6)])
    k = bpy.data.objects.get('Key'); kf(k.data, 'energy', F(1.2, rfps), 1900); kf(k.data, 'energy', F(2.6, rfps), 380)     # dim under the title
    for nm in ('Fill', 'Rim'):
        o = bpy.data.objects.get(nm); e0 = o.data.energy; kf(o.data, 'energy', F(1.2, rfps), e0); kf(o.data, 'energy', F(2.6, rfps), e0 * 0.35)
    cam, tgt = camera((0.6, -15.0, 6.0), (0, 0, 4.2), lens=40); cam_path(cam, tgt, rfps, [(0, (0.6, -15.0, 6.0), (0, 0, 4.2)), (dur, (0.2, -13.5, 5.4), (0, 0, 4.0))])

def spring_hang(nf, rfps, dur):
    sb, hd = spring_scene(nf, rfps)
    hang_kf(sb, rfps, [(0, 1.02), (4.0, 1.02), (11.0, 1.62), (dur, 1.62)])
    zb = lambda s: ball_world_z(sb, s) - sb['ball_r']
    root, ch = chevron_stream('Weight', (0.11, -0.3, zb(1.02) - 0.15), (0.11, -0.3, zb(1.02) - 2.3), n=9, color=(1.0, 0.85, 0.2), size=0.17, rfps=rfps, nf=nf, period=0.5, f_on=F(2.5, rfps))
    for t, s in ((0, 1.02), (4.0, 1.02), (11.0, 1.62), (dur, 1.62)): kf(root, 'location', F(t, rfps), (0.11, -0.3, zb(s) - 0.15))
    kf_ease(root)
    cam, tgt = camera((0.4, -11.5, 7.6), (0, 0, 7.4), lens=40)
    cam_path(cam, tgt, rfps, [(0, (0.4, -11.5, 7.6), (0, 0, 7.4)), (5.0, (0.3, -11.0, 7.3), (0, 0, 7.1)), (13.0, (0.2, -9.5, 5.6), (0, 0, 5.4)), (dur, (0.0, -9.0, 5.3), (0, 0, 5.2))])

def spring_scale(nf, rfps, dur):
    sb, hd = spring_scene(nf, rfps, target=(0.6, 0, 6.5))
    hang_kf(sb, rfps, [(0, 1.5), (5.0, 1.62), (dur, 1.62)])
    ru = ruler(x=1.55, z_top=sb['top'].z - 0.9, length=5.4)
    ztop = lambda s: sb['top'].z - sb['L'] * s - 0.1
    ruler_marker_kf(ru, rfps, [(0, ztop(1.5)), (5.0, ztop(1.62)), (dur, ztop(1.62))])
    for o in ruler_all(ru): kf(o, 'hide_render', 1, True); kf(o, 'hide_render', F(0.6, rfps), False)
    zb = lambda s: ball_world_z(sb, s) - sb['ball_r']
    root, ch = chevron_stream('Weight', (0.11, -0.3, zb(1.5) - 0.15), (0.11, -0.3, zb(1.5) - 2.0), n=8, color=(1.0, 0.85, 0.2), size=0.16, rfps=rfps, nf=nf, period=0.5)
    for t, s in ((0, 1.5), (5.0, 1.62), (dur, 1.62)): kf(root, 'location', F(t, rfps), (0.11, -0.3, zb(s) - 0.15))
    kf_ease(root)
    cam, tgt = camera((0.9, -12.5, 7.4), (0.7, 0, 7.0), lens=40)
    cam_path(cam, tgt, rfps, [(0, (0.9, -12.5, 7.4), (0.7, 0, 7.0)), (10.0, (0.9, -12.0, 7.2), (0.7, 0, 6.9)), (dur, (1.1, -8.2, 6.1), (0.9, 0, 6.0))])

def ball_into_water(nf, rfps, dur):
    tank, water = tank_scene(nf, rfps, level=3.4, target=(0, 0, 5.0))
    sb = spring_balance(top=(0, 0, 11.8), L=2.6); hd, _ = hand('Hand', (-0.05, 0.1, 12.35), pose='fist', rot=(-math.pi / 2, 0, 0), scale=0.95)
    # whole balance (hand + top) lowers 3.5..10 s so the ball enters the water; coil relaxes a little as buoyancy takes over
    for o in (hd, sb['ring'], sb['coil']):
        kf(o, 'location', F(3.5, rfps), tuple(o.location)); kf(o, 'location', F(10.0, rfps), (o.location.x, o.location.y, o.location.z - 4.2)); kf_ease(o)
    top_z = lambda t: 11.8 - 4.2 * (0 if t <= 3.5 else min(1.0, (t - 3.5) / 6.5))
    for t, s in ((0, 1.62), (3.5, 1.62), (10.0, 1.6), (dur, 1.6)):
        f = F(t, rfps); kf(sb['coil'], 'scale', f, (1, 1, s)); kf(sb['root'], 'location', f, (0, 0, top_z(t) - 2.6 * s))
    kf_ease(sb['coil']); kf_ease(sb['root'])
    entry_f = F(7.2, rfps); ripple(water, entry_f, x=0.11, y=0.0, height=0.09, width=0.55, speed=0.16 * 24 / rfps, life=int(4.0 * rfps), damp=int(2.5 * rfps))
    surface_ring('Splash', (0.11, 0, 3.42), r0=0.45, r1=2.2, f0=entry_f, f1=entry_f + int(1.6 * rfps))
    level_kf(water, rfps, [(6.8, 3.4), (10.5, 3.78), (dur, 3.78)])
    cam, tgt = camera((0.5, -13.0, 9.5), (0, 0, 8.6), lens=40)
    cam_path(cam, tgt, rfps, [(0, (0.5, -13.0, 9.5), (0, 0, 8.6)), (2.0, (0.5, -13.0, 9.5), (0, 0, 8.6)), (8.0, (0.5, -15.5, 6.2), (0, 0, 4.4)), (13.0, (0.6, -13.0, 5.0), (0, 0, 3.6)), (dur, (0.6, -11.0, 4.4), (0, 0, 3.2))])

def _immersed_scene(nf, rfps, level=3.78, stretch=1.6, top_z=7.6, arcs_on=None, arcs_color=(1.0, 0.42, 0.5), water_color=(0.10, 0.40, 0.95), hand_on=True, band=False):
    tank, water = tank_scene(nf, rfps, level=level, target=(0, 0, 3.4), water_color=water_color)
    sb = spring_balance(top=(0, 0, top_z), L=2.6); hang_kf(sb, rfps, [(0, stretch)])
    hd = None
    if hand_on: hd, _ = hand('Hand', (-0.05, 0.1, top_z + 0.55), pose='fist', rot=(-math.pi / 2, 0, 0), scale=0.95)
    bz = ball_world_z(sb, stretch)
    arcs = arc_dots('Thrust', (0.11, -0.2, bz - sb['ball_r'] - 0.35), radii=(0.9, 1.25, 1.6), n=13, color=arcs_color, rfps=rfps, nf=nf, f_on=arcs_on) if arcs_on is not None else []
    return tank, water, sb, hd, arcs, bz

def thrust_arcs(nf, rfps, dur):
    tank, water, sb, hd, arcs, bz = _immersed_scene(nf, rfps, arcs_on=F(0.4, rfps))
    # buoyancy lifts the ball: coil relaxes 8..14 s; the arcs follow the ball
    hang_kf(sb, rfps, [(0, 1.6), (8.0, 1.6), (14.0, 1.32), (dur, 1.32)])
    for o in arcs:
        # shift keyframed locations after 8 s by re-keying a parent: simpler -> parent all arcs to an empty that rises
        pass
    lift = empty('ArcLift', (0, 0, 0)); kf(lift, 'location', F(8.0, rfps), (0, 0, 0)); kf(lift, 'location', F(14.0, rfps), (0, 0, 2.6 * (1.6 - 1.32))); kf_ease(lift)
    for o in arcs: o.parent = lift
    cam, tgt = camera((0.3, -8.0, 2.9), (0.1, 0, 2.6), lens=45)
    cam_path(cam, tgt, rfps, [(0, (0.3, -8.0, 2.9), (0.1, 0, 2.6)), (7.0, (0.3, -7.2, 2.8), (0.1, 0, 2.5)), (10.0, (0.4, -14.5, 5.6), (0, 0, 4.6)), (dur, (0.4, -14.0, 5.4), (0, 0, 4.5))])

def scale_reading2(nf, rfps, dur):
    tank, water, sb, hd, arcs, bz = _immersed_scene(nf, rfps, stretch=1.32, arcs_on=1, hand_on=True)
    ru = ruler(x=2.3, z_top=sb['top'].z - 0.6, length=5.4, y=-3.5, num_size=0.3, marker_len=1.9)
    ztop = sb['top'].z - 2.6 * 1.32 - 0.1
    ruler_marker_kf(ru, rfps, [(0, ztop + 0.5), (2.5, ztop), (dur, ztop)])
    cam, tgt = camera((0.9, -12.0, 4.6), (0.9, 0, 3.6), lens=45)
    cam_path(cam, tgt, rfps, [(0, (0.9, -12.0, 4.6), (0.9, 0, 3.6)), (dur, (0.7, -12.8, 4.9), (0.8, 0, 3.7))])

def archimedes_state(nf, rfps, dur):
    tank, water, sb, hd, arcs, bz = _immersed_scene(nf, rfps, stretch=1.32, arcs_on=1, water_color=(0.16, 0.55, 1.0))
    cam, tgt = camera((0.4, -15.0, 6.2), (0, 0, 4.6), lens=40)
    cam_path(cam, tgt, rfps, [(0, (0.4, -15.0, 6.2), (0, 0, 4.6)), (dur, (-0.4, -14.2, 5.8), (0, 0, 4.4))])

# ================================================================= BUILDERS: buoyancy
def tank_fill(nf, rfps, dur):
    tank, water = tank_scene(nf, rfps, level=3.6, target=(0, 0, 2.8))
    level_kf(water, rfps, [(0, 0.35), (1.0, 0.35), (9.0, 3.6), (dur, 3.6)])
    stream = obj_add('cylinder', 'Stream', radius=0.13, depth=9.0, vertices=32, location=(0.8, 0.3, 6.0)); setmat(stream, mat_glass((0.6, 0.85, 1.0), alpha=0.55, rough=0.05, name='stream_m')); smooth(stream)
    kf(stream, 'hide_render', 1, True); kf(stream, 'hide_render', F(0.8, rfps), False); kf(stream, 'hide_render', F(9.0, rfps), True)
    ripple(water, F(1.0, rfps), x=0.8, y=0.3, height=0.05, width=0.4, speed=0.12 * 24 / rfps, life=int(9.0 * rfps), damp=int(1.0 * rfps))
    cam, tgt = camera((3.0, -16.0, 7.5), (0, 0, 3.0), lens=40)
    cam_path(cam, tgt, rfps, [(0, (3.0, -16.0, 7.5), (0, 0, 3.0)), (dur, (0.8, -14.5, 6.0), (0, 0, 2.9))])

def plastic_ball_push(nf, rfps, dur):
    tank, water = tank_scene(nf, rfps, level=3.6, target=(0, 0, 3.0))
    pm = mat_plastic_ball(); ball = obj_add('uv_sphere', 'PBall', radius=0.42, segments=96, ring_count=48, location=(0, 0, 4.4)); setmat(ball, pm); smooth(ball); subsurf(ball, 1, 1)
    hd, _ = hand('Hand', (0, -0.15, 4.95), pose='grip', rot=(0, 0, 0.35), scale=1.0)
    surf, deep = 3.6 + 0.12, 1.6
    # hand + ball: push under 1..6 s, release 8 s -> ball pops up 8..9.5 s; hand rises 8..10; push again 15..18.5, release 20, pops 20..21.5; hand leaves 26..28
    hz = [(0, 5.0), (1.0, 5.0), (6.0, deep + 0.55), (8.0, deep + 0.55), (10.0, 5.6), (14.5, 5.6), (15.0, 5.6), (18.5, deep + 0.55), (20.0, deep + 0.55), (22.0, 5.6), (25.5, 5.6), (28.0, 9.5)]
    for t, z in hz: kf(hd, 'location', F(t, rfps), (0, -0.15, z))
    kf_ease(hd)
    bz = [(0, 4.4), (1.0, 4.4), (6.0, deep), (8.0, deep), (9.0, surf + 0.25), (9.6, surf - 0.05), (10.2, surf + 0.06), (14.5, surf), (15.0, surf), (18.5, deep), (20.0, deep), (21.0, surf + 0.25), (21.6, surf - 0.05), (22.2, surf + 0.06), (dur, surf)]
    for t, z in bz: kf(ball, 'location', F(t, rfps), (0, 0, z))
    kf_ease(ball)
    for t in (2.2, 9.0, 16.2, 21.0): ripple(water, F(t, rfps), x=0, y=0, height=0.07, width=0.5, speed=0.16 * 24 / rfps, life=int(3.0 * rfps), damp=int(2.0 * rfps), name=f'w{int(t*10)}')
    for t in (9.0, 21.0): surface_ring(f'Ring{int(t)}', (0, 0, 3.62), r0=0.4, r1=1.6, f0=F(t, rfps), f1=F(t + 1.4, rfps))
    level_kf(water, rfps, [(1.0, 3.6), (6.0, 3.82), (8.0, 3.82), (9.5, 3.6), (15.0, 3.6), (18.5, 3.82), (20.0, 3.82), (21.5, 3.6)])
    cam, tgt = camera((0.8, -12.0, 5.0), (0, 0, 3.2), lens=42)
    cam_path(cam, tgt, rfps, [(0, (0.8, -12.0, 5.0), (0, 0, 3.2)), (6.0, (0.6, -10.0, 4.2), (0, 0, 2.9)), (12.0, (0.5, -12.5, 5.2), (0, 0, 3.4)), (19.0, (0.6, -9.6, 4.0), (0, 0, 2.8)), (dur, (0.4, -13.5, 5.6), (0, 0, 3.4))])

def displace_arrows(nf, rfps, dur):
    tank, water = tank_scene(nf, rfps, level=3.6, target=(0, 0, 3.0))
    ball = obj_add('uv_sphere', 'PBall', radius=0.42, segments=96, ring_count=48, location=(0, 0, 3.6)); setmat(ball, mat_plastic_ball()); smooth(ball); subsurf(ball, 1, 1)
    kf(ball, 'location', F(3.0, rfps), (0, 0, 3.62)); kf(ball, 'location', F(5.0, rfps), (0, 0, 2.1)); kf_ease(ball)
    radial_arrows('Disp', (0, -0.1, 2.1), n=10, r0=0.8, travel=0.6, rfps=rfps, nf=nf, f_on=F(5.5, rfps))
    level_kf(water, rfps, [(4.0, 3.6), (7.5, 3.95), (dur, 3.95)])
    ripple(water, F(4.0, rfps), x=0, y=0, height=0.06, width=0.5, speed=0.15 * 24 / rfps, life=int(3.0 * rfps), damp=int(2.0 * rfps))
    cam, tgt = camera((0.5, -16.0, 6.5), (0, 0, 3.0), lens=40)
    cam_path(cam, tgt, rfps, [(0, (0.5, -16.0, 6.5), (0, 0, 3.0)), (6.0, (0.5, -15.0, 6.2), (0, 0, 3.0)), (dur, (0.4, -11.5, 4.6), (0, 0, 2.7))])

def atm_pressure(nf, rfps, dur):
    tank, water = tank_scene(nf, rfps, level=3.95, target=(0, 0, 3.2))
    ball = obj_add('uv_sphere', 'PBall', radius=0.42, segments=96, ring_count=48, location=(0, 0, 2.1)); setmat(ball, mat_plastic_ball()); smooth(ball); subsurf(ball, 1, 1)
    down_arrows('Atm', (0, 0, 4.25), nx=4, ny=3, rfps=rfps, nf=nf, f_on=1)
    arc_dots('Thrust', (0, -0.15, 1.35), radii=(0.8, 1.1, 1.4), n=11, color=(1.0, 0.75, 0.15), rfps=rfps, nf=nf, f_on=F(1.5, rfps), spread=60)
    cam, tgt = camera((-1.5, -12.0, 6.5), (0, 0, 3.0), lens=42)
    cam_path(cam, tgt, rfps, [(0, (-1.5, -12.0, 6.5), (0, 0, 3.0)), (12.0, (-0.8, -10.5, 6.0), (0, 0, 3.1)), (26.0, (1.2, -10.8, 6.4), (0, 0, 3.0)), (38.0, (2.0, -14.0, 7.5), (0, 0, 3.0)), (dur, (2.4, -19.0, 9.0), (0, 0, 3.0))])

def iron_ball_sink(nf, rfps, dur):
    tank, water = tank_scene(nf, rfps, level=3.6, target=(0, 0, 2.6))
    ball = obj_add('uv_sphere', 'IBall', radius=0.48, segments=96, ring_count=48, location=(0, 0, 6.2)); setmat(ball, mat_iron()); smooth(ball); subsurf(ball, 1, 1)
    bz = [(0, 6.2), (1.0, 6.2), (4.0, 3.62), (6.5, 2.4), (9.5, 1.3), (14.0, 0.55), (dur, 0.55)]
    for t, z in bz: kf(ball, 'location', F(t, rfps), (0, 0, z))
    kf_ease(ball)
    ripple(water, F(4.0, rfps), x=0, y=0, height=0.1, width=0.55, speed=0.16 * 24 / rfps, life=int(4.0 * rfps), damp=int(2.5 * rfps))
    surface_ring('Splash', (0, 0, 3.62), r0=0.45, r1=2.3, f0=F(4.0, rfps), f1=F(5.6, rfps))
    level_kf(water, rfps, [(4.0, 3.6), (7.5, 3.9), (dur, 3.9)])
    da = radial_arrows('Disp', (0, -0.1, 2.3), n=10, r0=0.85, travel=0.6, rfps=rfps, nf=nf, f_on=F(6.5, rfps), f_off=F(14.0, rfps))
    chevron_stream('Grav', (0, -0.6, 0.0), (0, -0.6, -2.6), n=7, color=(0.15, 0.85, 1.0), size=0.2, rfps=rfps, nf=nf, period=0.5, f_on=F(20.0, rfps))
    arc_dots('Thrust', (0, -0.2, 0.3), radii=(0.75, 1.05, 1.35), n=11, color=(1.0, 0.75, 0.15), rfps=rfps, nf=nf, f_on=F(24.0, rfps), spread=58, column=False)
    cam, tgt = camera((0.4, -10.0, 5.6), (0, 0, 3.8), lens=42)
    cam_path(cam, tgt, rfps, [(0, (0.4, -10.0, 5.6), (0, 0, 3.8)), (8.0, (0.4, -11.0, 5.0), (0, 0, 3.2)), (16.0, (0.4, -12.5, 3.2), (0, 0, 1.4)), (dur, (0.3, -13.0, 2.6), (0, 0, 0.9))])

# ================================================================= BUILDERS: gravitation
def _space(nf, rfps, sun_dir=(-5.0, -7.0, 6.0), sun_e=6.0, stars=1600, seed=1, atmosphere_on=False):
    reset(); sc = bpy.context.scene
    try: sc.eevee.bloom_intensity = 0.08
    except Exception: pass
    space_stage(sun_dir=sun_dir, sun_e=sun_e, stars=stars, seed=seed)
    if atmosphere_on: atmosphere(density=0.0015)

def solar_system_reveal(nf, rfps, dur):
    _space(nf, rfps, sun_dir=(0.5, -8.0, 7.0), sun_e=1.3, stars=1800)
    ss = solar_system(nf, rfps, phase=0.6)
    e = ss['planets']['Earth']; R = PLANETS[2][1]; a0 = 0.6 + 2 * 1.9
    # camera starts tight on Earth+Moon (following Earth for 6 s), then pulls out to the whole system
    def epos(t):
        w = 0.55 / math.sqrt(R / 2.5); a = a0 + w * t; return Vector((R * math.cos(a), R * math.sin(a), 0))
    p0 = epos(0.0); p6 = epos(6.0)
    cam, tgt = camera((p0.x, p0.y - 3.2, 1.3), tuple(p0), lens=45)
    keys = [(0, (p0.x + 0.2, p0.y - 3.4, 1.4), tuple(p0)), (6.0, (p6.x + 0.4, p6.y - 3.6, 1.6), tuple(p6)), (14.0, (2.0, -16.0, 9.0), (0, 0, 0)), (dur, (3.0, -24.0, 15.0), (0, 0, 0))]
    cam_path(cam, tgt, rfps, keys)
    for t in (1.0, 2.0, 3.0, 4.0, 5.0):
        p = epos(t); kf(cam, 'location', F(t, rfps), (p.x + 0.2 + 0.03 * t, p.y - 3.4 - 0.03 * t, 1.4 + 0.03 * t)); kf(tgt, 'location', F(t, rfps), tuple(p))
    kf_ease(cam); kf_ease(tgt)

def force_lines(nf, rfps, dur):
    _space(nf, rfps, sun_dir=(0.5, -8.0, 7.0), sun_e=1.3, stars=1800)
    ss = solar_system(nf, rfps, phase=0.6 + 0.55 / math.sqrt(1.0) * 25.0 * 0.0 + 1.1, orbit_speed=0.6)
    # dotted lines Sun -> each planet, drawn in the planet's rotating frame so they stay attached
    for i, (nm, R, pr, col, band) in enumerate(PLANETS):
        root = ss['roots'][nm]; objs = glow_line(f'FL{nm}', (R * 0.0 + 1.6, 0, 0), (R - pr - 0.15, 0, 0), r=0.03, color=(1.0, 0.75, 0.35) if i % 2 else (0.7, 0.85, 1.0), strength=6.0, dotted=True, n_dots=int(R * 4), f_on=F(0.4 + 0.25 * i, rfps))
        for o in objs: o.parent = root
    cam, tgt = camera((2.0, -22.0, 12.0), (0, 0, 0), lens=42)
    cam_path(cam, tgt, rfps, [(0, (2.0, -22.0, 12.0), (0, 0, 0)), (5.0, (1.0, -14.0, 7.0), (0, 0, 0)), (dur, (0.5, -6.5, 3.2), (0, 0, 0.3))])

def law_moon_earth(nf, rfps, dur):
    _space(nf, rfps, sun_dir=(-3.0, -8.0, 5.0), sun_e=6.5, stars=1500, seed=4)
    mo = moon((-4.6, 0, 0), r=0.62, name='Moon', seg=160, disp=0.03)
    kf(mo, 'rotation_euler', 1, (0.2, 0, 0)); kf(mo, 'rotation_euler', nf, (0.2, 0, 0.5)); kf_lin(mo)
    ea = earth((4.6, 0, 0), r=1.05, name='Earth', spin=(1.6, 200), nf=nf, rfps=rfps)
    chevron_stream('MoonPull', (-3.75, -0.2, 0), (-0.35, -0.2, 0), n=12, color=(1.0, 0.96, 0.8), size=0.27, strength=8.0, rfps=rfps, nf=nf, period=0.6)
    chevron_stream('EarthPull', (3.3, -0.2, 0), (0.35, -0.2, 0), n=11, color=(0.35, 0.55, 1.0), size=0.27, strength=8.0, rfps=rfps, nf=nf, period=0.6)
    cam, tgt = camera((0, -13.5, 0.4), (0, 0, 0), lens=45)
    # composition shifts up a little at 16-19 s to make room for the equations below
    cam_path(cam, tgt, rfps, [(0, (0, -13.5, 0.4), (0, 0, 0)), (16.0, (0, -13.3, 0.4), (0, 0, 0)), (19.0, (0, -13.3, -0.3), (0, 0, -0.75)), (dur, (0.15, -13.0, -0.3), (0, 0, -0.75))])

def ball_throw_earth(nf, rfps, dur):
    _space(nf, rfps, sun_dir=(-4.0, -6.0, 7.0), sun_e=6.0, stars=1400, seed=7)
    R = 8.0; ea = earth((0, 6.0, -R - 0.55), r=R, name='Earth', spin=(0.5, 160), nf=nf, rfps=rfps, seg=192)
    ball = obj_add('uv_sphere', 'Ball', radius=0.14, segments=48, ring_count=24, location=(0, 0.2, -0.4)); setmat(ball, mat_orange_ball()); smooth(ball)
    # thrown up 0.5..6 s (decelerating), apex at ~6.5, falls 7..16 s, rests; then the camera pulls back to reveal the sphere
    bz = [(0, -0.4), (0.5, -0.4), (3.0, 1.9), (6.5, 3.0), (10.0, 2.2), (14.0, 0.3), (16.0, -0.4), (dur, -0.4)]
    for t, z in bz: kf(ball, 'location', F(t, rfps), (0, 0.2, z))
    kf_ease(ball)
    root, objs = chevron_stream('Grav', (0, 0.0, -0.25), (0, 0.0, -2.1), n=8, color=(0.4, 0.6, 1.0), size=0.13, rfps=rfps, nf=nf, period=0.5, f_on=F(13.5, rfps))
    for t, z in bz: kf(root, 'location', F(t, rfps), (0, 0.0, z - 0.25))
    kf_ease(root)
    cam, tgt = camera((0.4, -9.0, 1.2), (0, 0.2, 1.0), lens=40)
    cam_path(cam, tgt, rfps, [(0, (0.4, -9.0, 1.2), (0, 0.2, 1.0)), (16.0, (0.3, -9.5, 1.4), (0, 0.2, 1.1)), (22.0, (0.6, -22.0, 0.5), (0, 3.0, -4.0)), (dur, (1.0, -40.0, 3.0), (0, 6.0, -8.0))])

def moon_orbit(nf, rfps, dur):
    _space(nf, rfps, sun_dir=(-4.0, -7.0, 6.0), sun_e=6.0, stars=1500, seed=3)
    ea = earth((0, 0, 0), r=1.0, name='Earth', spin=(2.0, 40), nf=nf, rfps=rfps)
    Rm = 3.5; orbit_ring('MoonOrbit', Rm, color=(1.0, 0.55, 0.12), r=0.016, strength=4.0)
    mroot = empty('MoonRoot', (0, 0, 0)); mo = moon((Rm, 0, 0), r=0.27, name='Moon', seg=96); mo.parent = mroot; mo.location = (Rm, 0, 0)
    chevron_stream('Pull', (Rm - 0.45, 0, 0.05), (1.2, 0, 0.05), n=8, color=(0.4, 0.6, 1.0), size=0.2, strength=8.0, rfps=rfps, nf=nf, period=0.5, parent=mroot)
    a0 = math.radians(95); kf(mroot, 'rotation_euler', 1, (0, 0, a0)); kf(mroot, 'rotation_euler', nf, (0, 0, a0 - math.radians(235))); kf_lin(mroot)
    cam, tgt = camera((0, -9.5, 4.0), (0, 0, 0), lens=42)
    cam_path(cam, tgt, rfps, [(0, (0, -9.5, 4.2), (0, 0, 0)), (8.0, (0.3, -9.5, 3.2), (0, 0, 0)), (16.0, (0.6, -9.8, 1.9), (0, 0, 0)), (dur, (0.8, -10.0, 1.6), (0, 0, 0))])

def moon_inertia(nf, rfps, dur):
    _space(nf, rfps, sun_dir=(-4.0, -7.0, 5.0), sun_e=6.0, stars=1500, seed=5)
    mo = moon((0, 0, 0), r=0.55, name='Moon', seg=160, disp=0.03); kf(mo, 'rotation_euler', 1, (0.1, 0, 0)); kf(mo, 'rotation_euler', nf, (0.1, 0, 0.6)); kf_lin(mo)
    kf(mo, 'location', 1, (0, 0, -0.1)); kf(mo, 'location', nf, (0, 0, 1.3)); kf_lin(mo)
    ln = arrow_solid('Inertia', (0, -0.1, 0.1), (0, -0.1, 3.0), r=0.05, color=(0.2, 0.8, 1.0), head=0.35, f_on=F(2.0, rfps))
    for o in ln: parent_keep(o, mo)
    cam, tgt = camera((0, -7.0, 0.9), (0, 0, 0.9), lens=42)
    cam_path(cam, tgt, rfps, [(0, (0, -7.0, 0.9), (0, 0, 0.9)), (8.0, (0, -7.5, 1.0), (0, 0, 1.1)), (dur, (0.5, -19.0, 1.5), (0, 0, 1.4))])

def earth_moon_forces(nf, rfps, dur):
    _space(nf, rfps, sun_dir=(-3.0, -8.0, 5.0), sun_e=6.5, stars=1500, seed=6)
    ea = earth((-4.2, 0, 0), r=0.85, name='Earth', spin=(1.5, 120), nf=nf, rfps=rfps)
    mo = moon((4.2, 0, 0), r=0.28, name='Moon', seg=96)
    chevron_stream('Pull', (3.7, -0.15, 0), (-3.2, -0.15, 0), n=16, color=(0.45, 0.62, 1.0), size=0.22, strength=8.0, rfps=rfps, nf=nf, period=0.5, f_on=1, f_off=F(6.0, rfps))
    arrow_solid('InertiaL', (4.2, -0.1, 0.45), (4.2, -0.1, 3.2), r=0.045, color=(0.2, 0.8, 1.0), head=0.3, f_on=F(4.0, rfps))
    arrow_solid('PullL', (3.75, -0.1, 0.0), (1.2, -0.1, 0.0), r=0.045, color=(0.2, 0.8, 1.0), head=0.3, f_on=F(8.0, rfps))
    cam, tgt = camera((0, -12.5, 0.6), (0, 0, 0.5), lens=45)
    cam_path(cam, tgt, rfps, [(0, (0, -12.5, 0.6), (0, 0, 0.5)), (dur, (0.2, -12.2, 0.9), (0, 0, 0.7))])

def centripetal(nf, rfps, dur):
    _space(nf, rfps, sun_dir=(-4.0, -7.0, 5.0), sun_e=6.0, stars=1500, seed=8)
    ea = earth((0, 0, 0), r=0.42, name='Earth', spin=(3.0, 60), nf=nf, rfps=rfps, seg=96)
    Rm = 2.7; orbit_ring('MoonOrbit', Rm, color=(1.0, 0.55, 0.12), r=0.014, strength=4.0)
    mroot = empty('MoonRoot', (0, 0, 0)); mo = moon((Rm, 0, 0), r=0.13, name='Moon', seg=64); mo.parent = mroot; mo.location = (Rm, 0, 0)
    for o in glow_line('Radius', (0.55, 0, 0), (Rm - 0.2, 0, 0), r=0.02, color=(0.85, 0.9, 1.0), strength=5.0, dotted=True, n_dots=18): o.parent = mroot
    kf(mroot, 'rotation_euler', 1, (0, 0, math.radians(-10))); kf(mroot, 'rotation_euler', nf, (0, 0, math.radians(-10 + 95))); kf_lin(mroot)
    cam, tgt = camera((0, -8.5, 0.6), (0, 0, 0), lens=42)
    cam_path(cam, tgt, rfps, [(0, (0, -8.5, 0.6), (0, 0, 0)), (dur, (0.3, -8.0, 1.2), (0, 0, 0))])

def solar_system2(nf, rfps, dur):
    _space(nf, rfps, sun_dir=(-3.0, -8.0, 6.0), sun_e=1.3, stars=1800)
    solar_system(nf, rfps, phase=2.4, orbit_speed=0.8)
    cam, tgt = camera((-6.0, -16.0, 7.0), (0, 0, 0), lens=42)
    cam_path(cam, tgt, rfps, [(0, (-6.0, -16.0, 7.0), (0, 0, 0)), (dur, (-9.0, -14.0, 6.0), (0, 0, 0))])

# ================================================================= BUILDERS: gravity
def rocks_fall(nf, rfps, dur):
    _space(nf, rfps, sun_dir=(-2.5, -8.0, 5.0), sun_e=6.5, stars=1500, seed=9)
    ea = earth((0, 0, 0), r=2.3, name='Earth', spin=(1.2, 30), nf=nf, rfps=rfps, seg=192)
    for i, (x, z) in enumerate(((-3.6, 3.0), (0, 4.4), (3.6, 3.0))):
        root = empty(f'RockRoot{i}', (x, 0, z)); rk = rock(f'Rock{i}', (0, 0, 0), r=0.32, seed=3 + i); rk.parent = root
        d = Vector((x, 0, z)); u = d.normalized()
        kf(root, 'location', 1, tuple(d)); kf(root, 'location', nf, tuple(d - u * 1.6)); kf_lin(root)
        chevron_stream(f'Fall{i}', tuple(-u * 0.45), tuple(-u * 2.05), n=8, color=(1.0, 0.25, 0.15), size=0.19, strength=8.0, rfps=rfps, nf=nf, period=0.45, parent=root)
        path = lambda t, d=d, u=u: d - u * (1.6 * t / dur)
        sparks(f'Spark{i}', path, 120, rfps, nf, life=1.5, spread=0.3, seed=11 + i, rise=tuple(u * 1.5))
    cam, tgt = camera((0, -14.0, 1.4), (0, 0, 1.2), lens=42)
    cam_path(cam, tgt, rfps, [(0, (0, -14.0, 1.4), (0, 0, 1.2)), (dur, (0.3, -10.5, 2.0), (0, 0, 1.8))])

def free_fall_rock(nf, rfps, dur):
    _space(nf, rfps, sun_dir=(-4.0, -7.0, 7.0), sun_e=6.5, stars=1400, seed=10)
    R = 9.0; ea = earth((0, 11.0, -R - 9.6), r=R, name='Earth', spin=(0.4, 190), nf=nf, rfps=rfps, seg=192)
    root = empty('Rock', (0, 0, 0)); rk = rock('RockM', (0, 0, 0), r=0.3, seed=21); rk.parent = root; fire_shell('Fire', root, 0.3)
    kf(rk, 'rotation_euler', 1, (0, 0, 0)); kf(rk, 'rotation_euler', nf, (2.0, 3.5, 1.0)); kf_lin(rk)
    zf = lambda t: max(-9.3, -13.0 * (t / dur) ** 2)          # accelerating fall, lands on the surface near the end
    for t in [i * 0.5 for i in range(int(dur * 2) + 1)]: kf(root, 'location', F(t, rfps), (0, 0, zf(t)))
    kf_lin(root)
    sparks('Sp', lambda t: Vector((0, 0, zf(t))), 260, rfps, nf, t1=20.0, life=1.6, spread=0.22, seed=13, rise=(0, 0, 1.6))
    cam, tgt = camera((0.6, -6.5, 0.8), (0, 0, 0), lens=42)
    keys = []
    for t in [i * 1.0 for i in range(int(dur) + 1)]:
        z = zf(t); keys.append((t, (0.6 + 0.02 * t, -6.5 - 0.22 * t, z + 0.9), (0, 0, z - 0.6 - 0.05 * t)))
    cam_path(cam, tgt, rfps, keys, ease=False)

def rock_accel(nf, rfps, dur):
    _space(nf, rfps, sun_dir=(-4.0, -7.0, 7.0), sun_e=6.5, stars=1400, seed=12)
    ea = earth((0, 0, -3.2), r=1.9, name='Earth', spin=(1.0, 120), nf=nf, rfps=rfps, seg=160)
    root = empty('Rock', (0, 0, 2.6)); rk = rock('RockM', (0, 0, 0), r=0.22, seed=22); rk.parent = root; fire_shell('Fire', root, 0.22)
    kf(root, 'location', 1, (0, 0, 2.9)); kf(root, 'location', nf, (0, 0, 1.6)); kf_lin(root)
    chevron_stream('Acc', (0, -0.1, -0.35), (0, -0.1, -2.6), n=8, color=(0.2, 0.8, 1.0), size=0.14, rfps=rfps, nf=nf, period=0.45, parent=root)
    sparks('Sp', lambda t: Vector((0, 0, 2.9 - 1.3 * t / dur)), 110, rfps, nf, life=1.1, spread=0.2, seed=14, rise=(0, 0, 1.5))
    cam, tgt = camera((0.3, -9.0, 0.8), (0, 0, 0.2), lens=42)
    cam_path(cam, tgt, rfps, [(0, (0.3, -9.0, 0.8), (0, 0, 0.2)), (dur, (0.1, -9.6, 0.5), (0, 0, -0.1))])

def stone_newton(nf, rfps, dur):
    """Stone with a heavy red chevron stream falling to the Earth. Camera starts tight on the stone (548-556) and opens up
    to the whole Earth (560 and 590). EarthC empty exports the Earth centre for the 2D 'r' line."""
    _space(nf, rfps, sun_dir=(-4.0, -7.0, 7.0), sun_e=6.5, stars=1400, seed=15)
    ea = earth((0, 0, -3.6), r=2.5, name='Earth', spin=(0.9, 100), nf=nf, rfps=rfps, seg=192); empty('EarthC', (0, 0, -3.6))
    root = empty('Stone', (0, 0, 3.4)); rk = rock('StoneM', (0, 0, 0), r=0.2, seed=31); rk.parent = root; fire_shell('Fire', root, 0.2)
    kf(root, 'location', 1, (0, 0, 3.6)); kf(root, 'location', nf, (0, 0, 2.7)); kf_lin(root)
    chevron_stream('Red', (0, -0.1, -0.3), (0, -0.1, -3.0), n=9, color=(1.0, 0.28, 0.15), size=0.2, rfps=rfps, nf=nf, period=0.4, parent=root)
    sparks('Sp', lambda t: Vector((0, 0, 3.6 - 0.9 * t / dur)), 120, rfps, nf, life=1.0, spread=0.15, seed=16, rise=(0, 0, 1.2))
    cam, tgt = camera((0.2, -3.6, 3.4), (0, 0, 3.0), lens=42)
    cam_path(cam, tgt, rfps, [(0, (0.2, -3.6, 3.4), (0, 0, 3.0)), (5.0, (0.2, -3.8, 3.3), (0, 0, 2.9)), (12.0, (0.2, -12.0, 1.0), (0, 0, 0.4)), (40.0, (0.2, -12.5, 0.9), (0, 0, 0.3)), (44.0, (0.3, -16.5, 0.2), (0, 0, -0.6)), (dur, (0.3, -16.8, 0.2), (0, 0, -0.6))])

def earth_radius(nf, rfps, dur):
    _space(nf, rfps, sun_dir=(-4.0, -7.0, 7.0), sun_e=6.5, stars=1400, seed=17)
    ea = earth((0, 0, 0), r=2.2, name='Earth', spin=(1.4, 140), nf=nf, rfps=rfps, seg=192); empty('EarthC', (0, 0, 0)); empty('RMid', (0.05, -2.3, 1.15))
    root = empty('Stone', (0, 0, 2.38)); rk = rock('StoneM', (0, 0, 0), r=0.12, seed=32); rk.parent = root; fire_shell('Fire', root, 0.12)
    cam, tgt = camera((0.2, -11.0, 0.3), (0, 0, 0.1), lens=42)
    cam_path(cam, tgt, rfps, [(0, (0.2, -11.0, 0.3), (0, 0, 0.1)), (16.0, (0.6, -10.8, 0.5), (0, 0, 0.1)), (dur, (2.2, -10.5, 0.8), (0.8, 0, 0.1))])

# ================================================================= BUILDERS: thrust and pressure
def _press_stage(target=(0, 0, 4.2), key_e=2600, spot=60):
    if is_cycles(): key_e *= 0.62
    reset(); world(0.004, 0.006, 0.014); studio(key=(5.0, -6.0, 13.0), key_e=key_e, fill_e=140 if not is_cycles() else 80, rim_e=380, target=target, spot=spot, blend=0.8); hdri(strength=0.22, rotation=1.2)

def _hand_press(name, t, press_from=None, rfps=12, hover=0.9, side='top', rot_z=0.6):
    """Flat hand on top of the T object's top plate (local to the T root). press_from = sec when it lands (from hover)."""
    z = t['top_z'] + 0.16
    hd, parts = hand(name, (0.0, -0.05, z), pose='flat', rot=(0, 0, rot_z), scale=0.9)
    hd.parent = t['root']
    if press_from is not None:
        kf(hd, 'location', 1, (0.0, -0.05, z + hover)); kf(hd, 'location', F(press_from, rfps), (0.0, -0.05, z + hover)); kf(hd, 'location', F(press_from + 1.2, rfps), (0.0, -0.05, z)); kf_ease(hd)
    return hd, parts

def _block_t(nf, rfps, size=4.0, plate=1.35, color=(0.2, 0.42, 1.0), chev_on=None, t_rot=(0, 0, 0)):
    blk = wood_block('Block', (0, 0, 0), size=size); t = t_object('T', (0, 0, size), plate=plate, color=color, rfps=rfps, nf=nf, chev_on=chev_on, rot=t_rot)
    return blk, t

def thrust_intro(nf, rfps, dur):
    _press_stage(); blk, t = _block_t(nf, rfps, chev_on=1); _hand_press('Hand', t, rfps=rfps)
    cam, tgt = camera((4.5, -9.5, 8.5), (0, 0, 4.8), lens=40); cam_path(cam, tgt, rfps, [(0, (4.5, -9.5, 8.5), (0, 0, 4.8)), (dur, (4.2, -9.2, 8.3), (0, 0, 4.8))])

def block_alone(nf, rfps, dur):
    _press_stage(target=(0, 0, 2.0)); blk = wood_block('Block', (0, 0, 0), size=4.0)
    cam, tgt = camera((7.0, -13.0, 7.5), (0, 0, 2.0), lens=40); cam_path(cam, tgt, rfps, [(0, (7.0, -13.0, 7.5), (0, 0, 2.0)), (dur, (3.0, -11.0, 8.0), (0, 0, 2.4))])

def t_object_place(nf, rfps, dur):
    _press_stage(); blk, t = _block_t(nf, rfps)
    kf(t['root'], 'location', 1, (0, 0, 7.2)); kf(t['root'], 'location', F(0.5, rfps), (0, 0, 7.2)); kf(t['root'], 'location', F(4.0, rfps), (0, 0, 4.0)); kf_ease(t['root'])
    # highlight the top plate (pink-blue glow) at 10-12 s and 16-18 s; the base slab glows blue from 10 s
    tm = t['top'].data.materials[0]
    p = tm.node_tree.nodes['Principled BSDF']; _inp(p, 'Emission Color', (0.6, 0.45, 1.0, 1))
    value_kf(tm, 'Emission Strength', [(F(9.5, rfps), 0.0), (F(10.5, rfps), 1.4), (F(12.0, rfps), 1.4), (F(13.0, rfps), 0.0), (F(15.5, rfps), 0.0), (F(16.5, rfps), 1.4), (F(18.0, rfps), 1.4)])
    value_kf(t['slab_m'], 'Emission Strength', [(1, 0.0), (F(9.5, rfps), 0.0), (F(10.5, rfps), 1.0)])
    cam, tgt = camera((5.5, -11.0, 8.5), (0, 0, 4.6), lens=40); cam_path(cam, tgt, rfps, [(0, (5.5, -11.0, 8.5), (0, 0, 4.6)), (9.0, (4.5, -9.5, 8.0), (0, 0, 4.8)), (dur, (3.0, -8.5, 7.6), (0, 0, 5.0))])

def hand_press(nf, rfps, dur):
    _press_stage(); blk, t = _block_t(nf, rfps, chev_on=F(2.4, rfps)); _hand_press('Hand', t, press_from=1.2, rfps=rfps)
    value_kf(t['slab_m'], 'Emission Strength', [(1, 0.0), (F(11.0, rfps), 0.0), (F(12.0, rfps), 1.0)])
    cam, tgt = camera((4.0, -10.0, 8.8), (0, 0, 5.0), lens=40)
    cam_path(cam, tgt, rfps, [(0, (4.0, -10.0, 8.8), (0, 0, 5.0)), (6.0, (2.5, -8.0, 8.2), (0, 0, 5.4)), (dur, (-3.0, -8.5, 8.4), (0, 0, 5.2))])

def perpendicular_sides(nf, rfps, dur):
    _press_stage(target=(0, 0, 2.4), key_e=3400); blk = wood_block('Block', (0, 0, 0), size=4.0)
    cols = [(0.2, 0.42, 1.0), (0.2, 0.75, 0.7), (0.95, 0.35, 0.9), (1.0, 0.25, 0.15), (0.2, 0.75, 0.7), (1.0, 0.25, 0.15)]
    ts = []
    ts.append(t_object('Ttop', (0, 0, 4.0), plate=1.35, rfps=rfps, nf=nf, chev_on=1))
    ts.append(t_object('Tleft', (-2.0, 0, 2.0), plate=1.35, rfps=rfps, nf=nf, chev_on=F(2.0, rfps), rot=(0, -math.pi / 2, 0)))
    ts.append(t_object('Tright', (2.0, 0, 2.0), plate=1.35, rfps=rfps, nf=nf, chev_on=F(4.0, rfps), rot=(0, math.pi / 2, 0)))
    for i, t in enumerate(ts):
        _hand_press(f'Hand{i}', t, rfps=rfps, rot_z=0.6 if i == 0 else 0.0)
        for k, c in enumerate(cols): color_kf(t['slab_m'], [(F(4.0 + 2.0 * k, rfps), c)], sockets=('Emission Color',)); color_kf(t['slab_m'], [(F(4.0 + 2.0 * k, rfps), tuple(v * 0.55 for v in c))], sockets=('Base Color',))
    show_from(ts[1]['parts'] + [o for o in bpy.data.objects if o.name.startswith('Hand1')], F(1.5, rfps))
    show_from(ts[2]['parts'] + [o for o in bpy.data.objects if o.name.startswith('Hand2')], F(3.5, rfps))
    cam, tgt = camera((5.0, -13.5, 7.5), (0, 0, 3.4), lens=40)
    cam_path(cam, tgt, rfps, [(0, (5.0, -13.5, 7.5), (0, 0, 3.4)), (6.0, (1.5, -14.0, 6.8), (0, 0, 3.3)), (dur, (-3.0, -13.5, 7.0), (0, 0, 3.3))])

def area_decrease(nf, rfps, dur):
    _press_stage(); blk, t = _block_t(nf, rfps, plate=1.6, chev_on=1); _hand_press('Hand', t, rfps=rfps)
    steps = [(0.0, 1.0, (0.2, 0.42, 1.0)), (6.0, 1.0, (0.25, 0.6, 0.6)), (8.0, 1.12, (0.95, 0.35, 0.9)), (10.0, 1.08, (0.95, 0.4, 0.75)), (12.0, 0.9, (1.0, 0.35, 0.2)), (14.0, 0.82, (1.0, 0.25, 0.15)),
             (16.0, 0.74, (0.45, 0.55, 0.55)), (18.0, 0.66, (1.0, 0.25, 0.15)), (20.0, 0.6, (1.0, 0.3, 0.2)), (22.0, 0.54, (0.9, 0.35, 0.3)), (24.0, 0.5, (1.0, 0.25, 0.15)), (26.0, 0.46, (0.5, 0.55, 0.55)), (28.0, 0.42, (1.0, 0.25, 0.15))]
    slab_kf(t, rfps, steps)
    cam, tgt = camera((3.5, -9.5, 8.6), (0, 0, 5.0), lens=40)
    cam_path(cam, tgt, rfps, [(0, (3.5, -9.5, 8.6), (0, 0, 5.0)), (10.0, (2.0, -6.5, 7.6), (0, 0, 4.9)), (30.0, (1.5, -5.5, 7.2), (0, 0, 4.7)), (dur, (2.5, -8.0, 8.0), (0, 0, 4.9))])

def area_increase(nf, rfps, dur):
    _press_stage(); blk, t = _block_t(nf, rfps, plate=1.6, chev_on=1); _hand_press('Hand', t, rfps=rfps)
    steps = [(0.0, 0.42, (1.0, 0.25, 0.15)), (1.0, 0.6, (0.2, 0.42, 1.0)), (4.0, 0.75, (0.3, 0.5, 0.9)), (6.0, 0.9, (0.45, 0.6, 0.8)), (8.0, 1.05, (0.5, 0.8, 0.85)), (10.0, 1.2, (0.85, 0.9, 0.2)),
             (12.0, 1.35, (0.75, 0.9, 0.2)), (14.0, 1.5, (0.55, 0.85, 0.35)), (16.0, 1.65, (0.3, 0.7, 0.55)), (18.0, 1.8, (0.55, 0.9, 0.25)), (20.0, 1.95, (0.9, 0.95, 0.2)), (24.0, 2.1, (0.85, 0.95, 0.25)), (28.0, 2.2, (0.35, 0.75, 0.5))]
    slab_kf(t, rfps, steps)
    cam, tgt = camera((2.5, -7.5, 8.0), (0, 0, 4.9), lens=40)
    cam_path(cam, tgt, rfps, [(0, (2.5, -7.5, 8.0), (0, 0, 4.9)), (14.0, (2.0, -6.5, 7.8), (0, 0, 4.8)), (26.0, (1.5, -5.6, 7.3), (0, 0, 4.6)), (dur, (5.0, -10.5, 8.5), (0, 0, 4.6))])

def _two_blocks(nf, rfps, chev_on=1):
    _press_stage(target=(0, 0, 2.6), key_e=3400, spot=70)
    bl = wood_block('BlockL', (-2.6, 0, 0), size=3.4); br = wood_block('BlockR', (2.6, 0, 0), size=3.4)
    tl = t_object('TL', (-2.6, 0, 3.4), plate=1.1, color=(1.0, 0.25, 0.15), rfps=rfps, nf=nf, chev_on=chev_on); tl['slab'].scale = (0.62, 0.62, 1)
    tr = t_object('TR', (2.6, 0, 3.4), plate=1.1, color=(0.85, 0.95, 0.2), rfps=rfps, nf=nf, chev_on=chev_on); tr['slab'].scale = (2.1, 2.1, 1)
    _hand_press('HandL', tl, rfps=rfps); _hand_press('HandR', tr, rfps=rfps)
    empty('TopL', (-2.6, 0, 3.4 + tl['top_z'])); empty('TopR', (2.6, 0, 3.4 + tr['top_z']))
    return tl, tr

def two_blocks(nf, rfps, dur):
    _two_blocks(nf, rfps)
    cam, tgt = camera((0.5, -13.0, 7.0), (0, 0, 3.0), lens=40); cam_path(cam, tgt, rfps, [(0, (0.5, -13.0, 7.0), (0, 0, 3.0)), (dur, (0.2, -12.5, 6.8), (0, 0, 3.1))])

def closeup_small(nf, rfps, dur):
    _press_stage(target=(0, 0, 4.6)); blk, t = _block_t(nf, rfps, size=10.0, plate=1.1, color=(1.0, 0.25, 0.15), chev_on=1); t['slab'].scale = (0.5, 0.5, 1); t['root'].location = (0, 0, 10.0)
    _hand_press('Hand', t, rfps=rfps)
    cam, tgt = camera((1.0, -6.0, 12.6), (0, 0, 11.0), lens=42); cam_path(cam, tgt, rfps, [(0, (1.0, -6.0, 12.6), (0, 0, 11.0)), (dur, (0.6, -5.4, 12.4), (0, 0, 11.0))])

def closeup_large(nf, rfps, dur):
    _press_stage(target=(0, 0, 4.6)); blk, t = _block_t(nf, rfps, size=6.0, plate=1.1, color=(0.85, 0.95, 0.2), chev_on=1); t['slab'].scale = (2.2, 2.2, 1); t['root'].location = (0, 0, 6.0)
    _hand_press('Hand', t, rfps=rfps)
    cam, tgt = camera((1.5, -8.0, 9.5), (0, 0, 6.8), lens=42); cam_path(cam, tgt, rfps, [(0, (1.5, -8.0, 9.5), (0, 0, 6.8)), (dur, (1.0, -7.4, 9.3), (0, 0, 6.8))])

def two_blocks_formula(nf, rfps, dur):
    _two_blocks(nf, rfps)
    cam, tgt = camera((0.3, -12.5, 6.8), (0, 0, 3.0), lens=40); cam_path(cam, tgt, rfps, [(0, (0.3, -12.5, 6.8), (0, 0, 3.0)), (dur, (0.0, -12.0, 6.6), (0, 0, 3.0))])

BUILDERS = {k: v for k, v in globals().items() if callable(v) and not k.startswith('_') and k not in ('F',)}
