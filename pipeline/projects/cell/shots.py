"""Blender builders for every 3D shot of 'The Fundamental Unit of Life' (Class 9 biology, cells).
Each builder(nf, rfps, dur) sets up scene + animation for frames 1..nf.  Camera sits at -Y looking +Y, Z up.
Organic toolkit: cutaway cells (boolean wedge + solidified membrane + blotchy translucent cytoplasm), nucleus
(marbled interior, speckled nucleolus, pore blobs, beaded chromatin), rough/smooth ER, Golgi stacks, lysosomes,
mitochondria with folded cristae, plastids, bacterium, lipid bilayer, molecules (Hp*/Op*/Rp* -> 2D markers),
onion + the peel experiment props, compound microscope, cork + honeycomb."""
import math, random, bpy, os, sys, bmesh
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from mathutils import Vector, Matrix
from kit import *
from kit import _principled, _inp, _resample_profile

def F(sec, rfps): return int(round(sec * rfps)) + 1     # seconds -> frame number (1-based)
CY = is_cycles()

# ================================================================= materials
def _blend(m):
    for attr, val in [('surface_render_method', 'BLENDED'), ('blend_method', 'BLEND'), ('use_backface_culling', False),
                      ('show_transparent_back', True), ('use_transparency_overlap', True)]:
        try: setattr(m, attr, val)
        except Exception: pass
    try: m.shadow_method = 'NONE'
    except Exception: pass
    try: m.use_transparent_shadow = True
    except Exception: pass

def mat_organic(color, rough=0.42, sss=0.3, coat=0.2, name='organic', radius=None, spec=0.5, scale=0.08):
    """Soft waxy organic surface: subsurface + a light coat. The house look for membranes and organelles."""
    m, p = _principled(name)
    _inp(p, 'Base Color', (*color, 1)); _inp(p, 'Roughness', rough); _inp(p, 'Coat Weight', coat); _inp(p, 'Coat Roughness', 0.15)
    _inp(p, 'Subsurface Weight', sss); _inp(p, 'Subsurface Scale', scale); _inp(p, 'Specular IOR Level', spec)
    _inp(p, 'Subsurface Radius', radius or (color[0] * 1.2 + 0.2, color[1] * 0.8 + 0.1, color[2] * 0.6 + 0.05))
    return m

def mat_membrane(name='membrane'): return mat_organic((0.98, 0.5, 0.07), rough=0.3, sss=0.18, coat=0.5, name=name, radius=(1.0, 0.3, 0.05))

def mat_blotch(base, spot, scale=5.0, lo=0.42, hi=0.62, rough=0.5, sss=0.25, name='blotch', detail=3.0, bump=0.0, coat=0.12):
    """Pale ground with soft darker blotches (the reference's cytoplasm): noise -> ramp -> base colour."""
    m, p = _principled(name); nt = m.node_tree; n = nt.nodes
    tc = n.new('ShaderNodeTexCoord'); noise = n.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = scale; noise.inputs['Detail'].default_value = detail; noise.inputs['Roughness'].default_value = 0.55
    ramp = n.new('ShaderNodeValToRGB'); e = ramp.color_ramp.elements
    e[0].position = lo; e[0].color = (*base, 1); e[1].position = hi; e[1].color = (*spot, 1)
    nt.links.new(tc.outputs['Object'], noise.inputs['Vector']); nt.links.new(noise.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], p.inputs['Base Color'])
    if bump:
        bmp = n.new('ShaderNodeBump'); bmp.inputs['Strength'].default_value = bump
        nt.links.new(noise.outputs['Fac'], bmp.inputs['Height']); nt.links.new(bmp.outputs['Normal'], p.inputs['Normal'])
    _inp(p, 'Roughness', rough); _inp(p, 'Subsurface Weight', sss); _inp(p, 'Subsurface Scale', 0.1); _inp(p, 'Coat Weight', coat)
    _inp(p, 'Subsurface Radius', (base[0], base[1], base[2]))
    return m

def mat_cytoplasm(name='cyto'): return mat_blotch((0.6, 0.83, 0.9), (0.3, 0.52, 0.72), scale=4.5, lo=0.4, hi=0.6, rough=0.55, sss=0.3, name=name)
def mat_cyto_interior(name='cyto_in'): return mat_blotch((0.86, 0.92, 0.97), (0.42, 0.62, 0.88), scale=2.2, lo=0.45, hi=0.6, rough=0.6, sss=0.2, name=name)

def mat_marble(base=(0.93, 0.95, 1.0), vein=(0.1, 0.13, 0.5), scale=3.0, name='marble', bands=7.0):
    """White marble with dark-blue swirl contours (the nucleus interior of the reference)."""
    m, p = _principled(name); nt = m.node_tree; n = nt.nodes
    tc = n.new('ShaderNodeTexCoord'); noise = n.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = scale; noise.inputs['Detail'].default_value = 2.0; noise.inputs['Distortion'].default_value = 1.4
    mul = n.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = bands
    pp = n.new('ShaderNodeMath'); pp.operation = 'PINGPONG'; pp.inputs[1].default_value = 1.0
    ramp = n.new('ShaderNodeValToRGB'); e = ramp.color_ramp.elements
    e[0].position = 0.14; e[0].color = (*vein, 1); e[1].position = 0.32; e[1].color = (*base, 1)
    nt.links.new(tc.outputs['Object'], noise.inputs['Vector']); nt.links.new(noise.outputs['Fac'], mul.inputs[0]); nt.links.new(mul.outputs[0], pp.inputs[0])
    nt.links.new(pp.outputs[0], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], p.inputs['Base Color'])
    _inp(p, 'Roughness', 0.5); _inp(p, 'Subsurface Weight', 0.2); _inp(p, 'Coat Weight', 0.1)
    return m

def mat_speckle(base, speck, scale=40.0, thr=0.6, name='speckle', rough=0.5, bump=0.3):
    m, p = _principled(name); nt = m.node_tree; n = nt.nodes
    tc = n.new('ShaderNodeTexCoord'); noise = n.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = scale; noise.inputs['Detail'].default_value = 2.0
    ramp = n.new('ShaderNodeValToRGB'); e = ramp.color_ramp.elements
    e[0].position = thr - 0.03; e[0].color = (*base, 1); e[1].position = thr + 0.03; e[1].color = (*speck, 1)
    nt.links.new(tc.outputs['Object'], noise.inputs['Vector']); nt.links.new(noise.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], p.inputs['Base Color'])
    if bump:
        bmp = n.new('ShaderNodeBump'); bmp.inputs['Strength'].default_value = bump
        nt.links.new(noise.outputs['Fac'], bmp.inputs['Height']); nt.links.new(bmp.outputs['Normal'], p.inputs['Normal'])
    _inp(p, 'Roughness', rough); _inp(p, 'Coat Weight', 0.1)
    return m

def mat_cork(name='cork', light=(0.88, 0.68, 0.4), dark=(0.42, 0.26, 0.12), scale=7.0, pits=True, rough=0.75, bump=0.5):
    """Mottled cork: two noise octaves (tan/brown) with small dark pits and a bump."""
    m, p = _principled(name); nt = m.node_tree; n = nt.nodes
    tc = n.new('ShaderNodeTexCoord')
    n1 = n.new('ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = scale; n1.inputs['Detail'].default_value = 7; n1.inputs['Roughness'].default_value = 0.65
    ramp = n.new('ShaderNodeValToRGB'); e = ramp.color_ramp.elements
    e[0].position = 0.4; e[0].color = (*dark, 1); e[1].position = 0.6; e[1].color = (*light, 1)
    nt.links.new(tc.outputs['Object'], n1.inputs['Vector']); nt.links.new(n1.outputs['Fac'], ramp.inputs['Fac'])
    cur = ramp.outputs['Color']
    if pits:
        vor = n.new('ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = scale * 5; vor.feature = 'F1'
        try: vor.inputs['Randomness'].default_value = 1.0
        except Exception: pass
        pr = n.new('ShaderNodeValToRGB'); pe = pr.color_ramp.elements
        pe[0].position = 0.12; pe[0].color = (0.35, 0.22, 0.1, 1); pe[1].position = 0.3; pe[1].color = (1, 1, 1, 1)
        mix = n.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 0.45
        nt.links.new(tc.outputs['Object'], vor.inputs['Vector']); nt.links.new(vor.outputs['Distance'], pr.inputs['Fac'])
        nt.links.new(cur, mix.inputs[6]); nt.links.new(pr.outputs['Color'], mix.inputs[7]); cur = mix.outputs[2]
    nt.links.new(cur, p.inputs['Base Color'])
    if bump:
        bmp = n.new('ShaderNodeBump'); bmp.inputs['Strength'].default_value = bump
        nt.links.new(n1.outputs['Fac'], bmp.inputs['Height']); nt.links.new(bmp.outputs['Normal'], p.inputs['Normal'])
    _inp(p, 'Roughness', rough); _inp(p, 'Specular IOR Level', 0.35)
    return m

def mat_comb_floor(name='comb_floor'):
    """Cream honeycomb floor with orange-brown veins (the reference's cork-like cell floors)."""
    m, p = _principled(name); nt = m.node_tree; n = nt.nodes
    tc = n.new('ShaderNodeTexCoord')
    n1 = n.new('ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = 1.3; n1.inputs['Detail'].default_value = 5; n1.inputs['Roughness'].default_value = 0.72; n1.inputs['Distortion'].default_value = 1.1
    ramp = n.new('ShaderNodeValToRGB'); cr = ramp.color_ramp
    cr.elements[0].position = 0.36; cr.elements[0].color = (0.98, 0.92, 0.78, 1)
    cr.elements[1].position = 0.45; cr.elements[1].color = (0.85, 0.45, 0.12, 1)
    e2 = cr.elements.new(0.52); e2.color = (0.99, 0.93, 0.8, 1)
    e3 = cr.elements.new(0.6); e3.color = (0.78, 0.4, 0.12, 1)
    e4 = cr.elements.new(0.68); e4.color = (0.98, 0.9, 0.74, 1)
    nt.links.new(tc.outputs['Object'], n1.inputs['Vector']); nt.links.new(n1.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], p.inputs['Base Color'])
    bmp = n.new('ShaderNodeBump'); bmp.inputs['Strength'].default_value = 0.25
    nt.links.new(n1.outputs['Fac'], bmp.inputs['Height']); nt.links.new(bmp.outputs['Normal'], p.inputs['Normal'])
    _inp(p, 'Roughness', 0.7); _inp(p, 'Subsurface Weight', 0.2)
    return m

def mat_rim(color, rim, a_center=0.12, a_rim=0.85, emit=2.0, name='rim', blend=0.35, rough=0.25):
    """Translucent body whose edges glow (fresnel): the environment sphere, the diffusion cell, division cells."""
    m, p = _principled(name); nt = m.node_tree; n = nt.nodes
    lw = n.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = blend
    mr = n.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.0; mr.inputs['From Max'].default_value = 1.0
    mr.inputs['To Min'].default_value = a_center; mr.inputs['To Max'].default_value = a_rim
    mul = n.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = emit
    nt.links.new(lw.outputs['Facing'], mr.inputs['Value']); nt.links.new(mr.outputs['Result'], p.inputs['Alpha'])
    nt.links.new(lw.outputs['Facing'], mul.inputs[0]); nt.links.new(mul.outputs[0], p.inputs['Emission Strength'])
    _inp(p, 'Base Color', (*color, 1)); _inp(p, 'Emission Color', (*rim, 1)); _inp(p, 'Roughness', rough); _inp(p, 'Specular IOR Level', 0.6)
    _blend(m)
    try: m.use_backface_culling = True          # two-sided blending shows a draw-order seam along the sphere's meridian
    except Exception: pass
    return m

def mat_translucent(color, alpha=0.6, rough=0.3, emit=0.0, name='transl', sss=0.0):
    m, p = _principled(name)
    _inp(p, 'Base Color', (*color, 1)); _inp(p, 'Roughness', rough); _inp(p, 'Alpha', alpha); _inp(p, 'Coat Weight', 0.3); _inp(p, 'Subsurface Weight', sss)
    if emit: _inp(p, 'Emission Color', (*color, 1)); _inp(p, 'Emission Strength', emit)
    _blend(m)
    return m

def mat_glassy(tint, alpha=0.3, rough=0.08, name='glassy', ior=1.5):
    """Glass that also reads in EEVEE: real refraction in Cycles, alpha-blended tint otherwise."""
    if CY:
        m = mat_glass_real(tint=tint, ior=ior, rough=rough, name=name); return m
    return mat_glass(tint, alpha=alpha, rough=rough, name=name)

def mat_tissue(name='tissue'):
    """Onion epidermis under the microscope: pink polygonal cells, dark cell walls, puffy bump (Voronoi)."""
    m, p = _principled(name); nt = m.node_tree; n = nt.nodes
    tc = n.new('ShaderNodeTexCoord'); mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1.0, 1.7, 1.0)
    vor = n.new('ShaderNodeTexVoronoi'); vor.feature = 'DISTANCE_TO_EDGE'; vor.inputs['Scale'].default_value = 3.0
    try: vor.inputs['Randomness'].default_value = 0.75
    except Exception: pass
    vc = n.new('ShaderNodeTexVoronoi'); vc.feature = 'F1'; vc.inputs['Scale'].default_value = 3.0
    try: vc.inputs['Randomness'].default_value = 0.75
    except Exception: pass
    edge = n.new('ShaderNodeValToRGB'); ee = edge.color_ramp.elements
    ee[0].position = 0.02; ee[0].color = (0.12, 0.03, 0.08, 1); ee[1].position = 0.09; ee[1].color = (1, 1, 1, 1)
    tint = n.new('ShaderNodeValToRGB'); te = tint.color_ramp.elements
    te[0].position = 0.0; te[0].color = (0.96, 0.5, 0.72, 1); te[1].position = 1.0; te[1].color = (0.72, 0.22, 0.5, 1)
    mix = n.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 1.0
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], vor.inputs['Vector']); nt.links.new(mp.outputs['Vector'], vc.inputs['Vector'])
    nt.links.new(vor.outputs['Distance'], edge.inputs['Fac']); nt.links.new(vc.outputs['Color'], tint.inputs['Fac'])
    nt.links.new(tint.outputs['Color'], mix.inputs[6]); nt.links.new(edge.outputs['Color'], mix.inputs[7]); nt.links.new(mix.outputs[2], p.inputs['Base Color'])
    bmp = n.new('ShaderNodeBump'); bmp.inputs['Strength'].default_value = 0.55; bmp.inputs['Distance'].default_value = 0.4
    nt.links.new(vor.outputs['Distance'], bmp.inputs['Height']); nt.links.new(bmp.outputs['Normal'], p.inputs['Normal'])
    _inp(p, 'Roughness', 0.45); _inp(p, 'Coat Weight', 0.3); _inp(p, 'Subsurface Weight', 0.2)
    return m

def mat_streaks(base, streak, name='streaks', scale=(1.0, 1.0, 0.08), rough=0.3, coat=0.5):
    """Vertically stretched noise: the onion skin's fibres."""
    m, p = _principled(name); nt = m.node_tree; n = nt.nodes
    tc = n.new('ShaderNodeTexCoord'); mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (scale[0] * 6, scale[1] * 6, scale[2] * 6)
    noise = n.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 1.0; noise.inputs['Detail'].default_value = 4
    ramp = n.new('ShaderNodeValToRGB'); e = ramp.color_ramp.elements
    e[0].position = 0.38; e[0].color = (*streak, 1); e[1].position = 0.62; e[1].color = (*base, 1)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], noise.inputs['Vector'])
    nt.links.new(noise.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], p.inputs['Base Color'])
    _inp(p, 'Roughness', rough); _inp(p, 'Coat Weight', coat); _inp(p, 'Subsurface Weight', 0.25)
    return m

def mat_white_plastic(name='white_pl'): return mat_plastic((0.92, 0.92, 0.9), rough=0.3, name=name, coat=0.5)
def mat_black_rubber(name='black_rb'): return mat_plastic((0.03, 0.03, 0.035), rough=0.6, name=name)
def mat_chrome(name='chrome'): return mat_metal((0.85, 0.86, 0.88), rough=0.18, name=name)

# ================================================================= mesh helpers
def mesh_obj(name, bm, mat=None, smooth_=True, loc=None):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth_:
        for pl in me.polygons: pl.use_smooth = True
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    if mat is not None: setmat(o, mat)
    if loc is not None: o.location = loc
    return o

def sphere(name, r, loc=(0, 0, 0), seg=64, ring=32, mat=None, scale=None):
    o = obj_add('uv_sphere', name, radius=r, segments=seg, ring_count=ring, location=loc)
    if scale: o.scale = scale
    if mat is not None: setmat(o, mat)
    smooth(o, auto=False); return o

def bean(name, r, loc=(0, 0, 0), mat=None, seg=96, ring=48, egg=0.14, squash=(1.0, 0.92, 0.9), dimple=0.0):
    """An egg/bean shaped cell body: a UV sphere widened toward +x, slightly flattened, optional kidney dimple."""
    o = sphere(name, r, loc, seg, ring, mat); me = o.data
    for v in me.vertices:
        u = v.co.x / r
        v.co.y *= (1 + egg * u) * squash[1]; v.co.z *= (1 + egg * 0.6 * u) * squash[2]; v.co.x *= squash[0]
        if dimple and v.co.z < 0:
            k = math.exp(-((v.co.x / r) ** 2) * 4) * (-v.co.z / r) ** 2
            v.co.z += dimple * r * k
    me.update(); return o

def capsule(name, R, h, loc=(0, 0, 0), mat=None, seg=64, ring=32, zscale=1.0):
    """Cylinder of length h along X with hemispherical caps: mitochondria, bacteria."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=ring, radius=R, matrix=Matrix.Rotation(math.pi / 2, 4, 'Y'))
    for v in bm.verts:
        v.co.x += h / 2 if v.co.x > 1e-6 else (-h / 2 if v.co.x < -1e-6 else 0.0)
        v.co.z *= zscale
    o = mesh_obj(name, bm, mat, loc=loc); return o

def lathe(name, profile, mat, loc=(0, 0, 0), verts=96, resample=True):
    o = glass_vessel(name, profile, loc, verts=verts, resample=resample); setmat(o, mat); return o

def cutter_box(name, loc, size, rot=(0, 0, 0)):
    c = obj_add('cube', name, size=1.0, location=loc); c.scale = size; c.rotation_euler = rot
    c.hide_render = True; c.display_type = 'WIRE'
    try: c.visible_camera = False; c.visible_shadow = False
    except Exception: pass
    return c

BOOL_SOLVER = os.environ.get('VL_BOOL', 'EXACT')
EPS = 0.0037            # cutter faces are nudged off the sphere's own vertex rings (a meridian/equator lying exactly on a cutter face breaks the boolean)
def boolean_cut(o, cutter, name='cut', solver=None):
    mod = o.modifiers.new(name, 'BOOLEAN'); mod.operation = 'DIFFERENCE'; mod.object = cutter
    for sv in ((solver or BOOL_SOLVER), 'EXACT', 'FAST'):
        try: mod.solver = sv; break
        except Exception: continue
    smooth(o, auto=True)          # 'smooth by angle' lands after the boolean: flat cut faces stay flat
    return mod

def bevel(o, width=0.05, segments=6):
    try: mod = o.modifiers.new('bev', 'BEVEL'); mod.width = width; mod.segments = segments; mod.limit_method = 'ANGLE'; return mod
    except Exception: return None

def displace(o, scale=0.5, strength=0.1, name='disp', seed=0, kind='CLOUDS'):
    try:
        tx = bpy.data.textures.new(name + '_tx', kind); tx.noise_scale = scale
        try: tx.noise_depth = 2
        except Exception: pass
        mod = o.modifiers.new(name, 'DISPLACE'); mod.texture = tx; mod.strength = strength; mod.mid_level = 0.5
        return mod
    except Exception: return None

def spheres_mesh(name, pts, r, mat, subdiv=1, rscale=None, scale3=None, normals=None):
    """One mesh holding many tiny spheres (ribosomes, pores, beads, dots) -> keeps the object count low."""
    bm = bmesh.new()
    for i, p in enumerate(pts):
        rr = r * (rscale[i] if rscale is not None else 1.0)
        M = Matrix.Translation(Vector(p))
        if normals is not None:
            M = M @ Vector(normals[i]).to_track_quat('Z', 'Y').to_matrix().to_4x4()
        if scale3 is not None:
            M = M @ Matrix.Diagonal((scale3[0], scale3[1], scale3[2], 1.0))
        bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=rr, matrix=M)
    return mesh_obj(name, bm, mat)

def tubes_mesh(name, segs, r, mat, sides=8):
    """One mesh of thin cylinders between point pairs (vesicle stalks, thin rods)."""
    bm = bmesh.new()
    for p0, p1 in segs:
        p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
        if d.length < 1e-6: continue
        M = Matrix.Translation((p0 + p1) / 2) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=sides, radius1=r, radius2=r, depth=d.length, matrix=M)
    return mesh_obj(name, bm, mat)

def catmull(pts, n):
    """Resample a polyline through the control points (Catmull-Rom), n samples."""
    P = [pts[0]] + list(pts) + [pts[-1]]; out = []
    segs = len(pts) - 1
    for i in range(segs):
        p0, p1, p2, p3 = (Vector(P[i]), Vector(P[i + 1]), Vector(P[i + 2]), Vector(P[i + 3]))
        steps = max(1, int(round(n / segs)))
        for k in range(steps):
            t = k / steps; t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(Vector(pts[-1])); return out

def curve_obj(name, pts, r, mat, loc=(0, 0, 0), res=12, smooth_pts=True, cyclic=False):
    """Bevelled curve (tube) through points: chromatin, nucleoid coil, DNA, flagella, tubules."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 6; cu.use_fill_caps = True
    cu.resolution_u = res
    sp = cu.splines.new('NURBS' if smooth_pts else 'POLY'); sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts): sp.points[i].co = (p[0], p[1], p[2], 1.0)
    sp.use_endpoint_u = True; sp.use_cyclic_u = cyclic
    try: sp.order_u = 4
    except Exception: pass
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o); o.location = loc
    cu.materials.append(mat)
    return o

def helix_pts(length, radius, turns, n=120, axis='x', phase=0.0, taper=0.0):
    out = []
    for i in range(n + 1):
        u = i / n; a = 2 * math.pi * turns * u + phase; rr = radius * (1 - taper * u)
        if axis == 'x': out.append((-length / 2 + length * u, rr * math.cos(a), rr * math.sin(a)))
        else: out.append((rr * math.cos(a), rr * math.sin(a), -length / 2 + length * u))
    return out

def wander_pts(rnd, start, n, step, box, z_fixed=None, smoothness=0.65):
    """Random smooth walk inside a box: chromatin threads, tubules."""
    p = Vector(start); d = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.3, 0.3))).normalized(); out = [tuple(p)]
    for i in range(n):
        nd = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.4, 0.4))).normalized()
        d = (d * smoothness + nd * (1 - smoothness)).normalized(); p = p + d * step
        for k in range(3):
            lo, hi = box[k]
            if p[k] < lo: p[k] = lo + (lo - p[k]); d[k] = abs(d[k])
            if p[k] > hi: p[k] = hi - (p[k] - hi); d[k] = -abs(d[k])
        if z_fixed is not None: p.z = z_fixed
        out.append(tuple(p))
    return out

def rand_on_ellipsoid(rnd, center, radii, n, front=None):
    """Random points on an ellipsoid surface (with normals); front=(nx,ny,nz) keeps only the hemisphere facing it."""
    pts, nrm = [], []
    tries = 0
    while len(pts) < n and tries < n * 30:
        tries += 1
        v = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))).normalized()
        if front is not None and v.dot(Vector(front)) < 0.05: continue
        p = Vector(center) + Vector((v.x * radii[0], v.y * radii[1], v.z * radii[2]))
        nn = Vector((v.x / radii[0], v.y / radii[1], v.z / radii[2])).normalized()
        pts.append(tuple(p)); nrm.append(tuple(nn))
    return pts, nrm

def parent(o, root):
    """Parent with LOCAL semantics: every helper authors its children in root-local coordinates, so the parent
    inverse is the identity (matrix_world of a fresh empty is stale until a depsgraph update, which made the old
    'keep world transform' inverse land children at the origin whenever an operator had run in between)."""
    o.parent = root; o.matrix_parent_inverse = Matrix.Identity(4)

def hide_until(o, f, rfps=None):
    kf(o, 'hide_render', 1, True); kf(o, 'hide_render', f, False)

def hide_from(o, f):
    kf(o, 'hide_render', 1, False); kf(o, 'hide_render', f, True)

def anchor(name, loc, parent_to=None):
    """A sub-pixel mesh speck whose 2D position the compositor uses to pin a tag (must be a visible MESH).
    With parent_to, loc is in that object's local space."""
    o = obj_add('ico_sphere', name, radius=0.002, subdivisions=1, location=loc)
    setmat(o, mat_emit((0, 0, 0), strength=0.0, name='anch'))
    try: o.visible_shadow = False
    except Exception: pass
    if parent_to is not None: parent(o, parent_to)
    return o

# ================================================================= lighting / stage
def stage(target=(0, 0, 0.8), key=(3.0, -5.5, 7.5), key_e=2200, fill_e=140, rim_e=380, spot=55, blend=0.85, env=0.32, world_col=(0.0025, 0.004, 0.009)):
    """Dark navy void, warm pooled key, cool fill + rim, HDRI reflections, thin atmosphere in Cycles."""
    world(*world_col)
    k, f, r = studio(key=key, key_e=key_e, fill_e=fill_e, rim_e=rim_e, target=target, spot=spot, blend=blend)
    hdri(strength=env, rotation=1.3); atmosphere(density=0.0025)
    return k, f, r

def soft_light(loc, energy, size=4.0, color=(0.85, 0.92, 1.0), name='Soft', target=None):
    return light('AREA', loc, energy, color, name, size=size, target=target)

def cam_path(keys, rfps, lens=45, ease=True):
    """Multi-key camera: keys = [(t_sec, cam_loc, target_loc), ...] -> camera + target with eased keyframes."""
    cam, tgt = camera(keys[0][1], keys[0][2], lens=lens)
    for t, loc, tl in keys:
        f = F(t, rfps); kf(cam, 'location', f, loc); kf(tgt, 'location', f, tl)
    (kf_ease if ease else kf_lin)(cam); (kf_ease if ease else kf_lin)(tgt)
    return cam, tgt

# ================================================================= the cell
def cutaway_cell(loc=(0, 0, 0), r=1.6, cut='wedge', nucleus='wedge', name='Cell', thick=0.085, interior='cell', open_from=None, open_to=None, rfps=12, close_from=None, close_to=None, egg=0.2, seg=96):
    """Orange membrane (solidified bean) with a boolean wedge removed, translucent blotchy cytoplasm filling it,
    an optional nucleus.  cut='wedge': front-top quarter removed (vertical back wall + horizontal floor);
    cut='scoop': one inclined plane; cut=None: whole cell.  open_from/to animate the cutter sliding in."""
    x, y, z = loc; out = {}
    mem = bean(name + 'Membrane', r, loc, mat_membrane(name + '_mem'), seg=seg, ring=seg // 2, egg=egg); subsurf(mem, 1, 1); solidify(mem, thick * r)
    cyt = bean(name + 'Cyto', r * (1 - thick - 0.006), loc, mat_cytoplasm(name + '_cyto') if interior == 'cell' else mat_cyto_interior(name + '_cyto'), seg=seg, ring=seg // 2, egg=egg); subsurf(cyt, 1, 1)
    out['membrane'] = mem; out['cyto'] = cyt
    cutter = None
    if cut == 'wedge':
        cutter = cutter_box(name + 'Cutter', (x, y - 1.3 * r + EPS * r, z + 1.3 * r - EPS * r), (3.2 * r, 2.6 * r, 2.6 * r))
    elif cut == 'scoop':
        cutter = cutter_box(name + 'Cutter', (x + 0.1 * r, y - 1.55 * r, z + 1.25 * r), (3.2 * r, 2.6 * r, 2.6 * r), rot=(math.radians(-38), 0, 0))
    elif cut == 'half':
        cutter = cutter_box(name + 'Cutter', (x, y - 1.3 * r + EPS * r, z), (3.2 * r, 2.6 * r, 3.2 * r))
    if cutter is not None:
        boolean_cut(mem, cutter); boolean_cut(cyt, cutter); out['cutter'] = cutter
        base = tuple(cutter.location); out['anim_cutters'] = [cutter]
        def _slide(cc):
            b = tuple(cc.location); far = (b[0], b[1] - 2.8 * r, b[2] + 0.4 * r)
            if open_from is not None:
                kf(cc, 'location', 1, far); kf(cc, 'location', F(open_from, rfps), far); kf(cc, 'location', F(open_to, rfps), b)
            if close_from is not None:
                kf(cc, 'location', F(close_from, rfps), b); kf(cc, 'location', F(close_to, rfps), far)
            if open_from is not None or close_from is not None: kf_ease(cc)
        out['_slide'] = _slide; _slide(cutter)
    if nucleus and cutter is not None:
        rn = 0.3 * r
        if nucleus == 'wedge':
            # purple double-membrane ball resting on the cut floor, front cap sliced off -> dark speckled interior shows
            ln = (x + 0.04 * r, y - 0.36 * r, z + 0.12 * r)
            ncut = cutter_box(name + 'NucCutter', (ln[0], ln[1] - 0.62 * rn - 1.3 * rn, ln[2]), (3.2 * rn, 2.6 * rn, 3.2 * rn))
            ccut = cutter_box(name + 'CoreCutter', (ln[0], ln[1] - 0.48 * rn - 1.3 * rn, ln[2]), (3.2 * rn, 2.6 * rn, 3.2 * rn))
            if '_slide' in out:
                for cc in (ncut, ccut): out['_slide'](cc)          # slide in and out together with the main cutter
            shell = sphere(name + 'NucShell', rn, ln, mat=mat_organic((0.5, 0.2, 0.9), rough=0.3, sss=0.25, coat=0.5, name=name + '_nuc')); solidify(shell, 0.14 * rn); boolean_cut(shell, ncut)
            inner = sphere(name + 'NucInner', rn * 0.86, ln, mat=mat_speckle((0.2, 0.05, 0.48), (0.62, 0.42, 0.95), scale=30 / rn, thr=0.55, name=name + '_nucin', bump=0.5)); boolean_cut(inner, ccut)
            out['nucleus'] = (shell, inner)
    return out

def nucleus_organelle(loc, rn=1.2, name='Nuc', cut='half', pores=0, chromatin=0, membrane=True, seed=2, front_y=None, thick=0.11, rot=0.0, core_r=0.42):
    """Stand-alone nucleus: purple double-membrane shell (cut open at the front: 'half' = front half removed, 'wedge' =
    front-top quarter removed so a floor and a back wall show), marbled interior, dark speckled nucleolus resting on
    the cut, pink pore blobs on the outside, blue beaded chromatin threads lying on the cut faces."""
    x, y, z = loc; rnd = random.Random(seed); out = {}
    root = empty(name, loc); root.rotation_euler = (0, 0, rot); out['root'] = root
    cutter = None
    if cut == 'half':
        cutter = cutter_box(name + 'Cut', (0, -1.6 * rn + EPS * rn, 0), (3.4 * rn, 3.2 * rn, 3.4 * rn)); parent(cutter, root)
    elif cut == 'wedge':
        cutter = cutter_box(name + 'Cut', (0, -1.3 * rn + EPS * rn, 1.3 * rn - EPS * rn), (3.2 * rn, 2.6 * rn, 2.6 * rn)); parent(cutter, root)
    out['cutter'] = cutter
    if membrane:
        shell = sphere(name + 'Shell', rn, (0, 0, 0), seg=96, ring=48, mat=mat_organic((0.46, 0.2, 0.9), rough=0.3, sss=0.25, coat=0.5, name=name + '_shell')); solidify(shell, thick * rn)
        parent(shell, root); out['shell'] = shell
        if cutter: boolean_cut(shell, cutter)
    inner = sphere(name + 'Inner', rn * (1.0 - thick - 0.02 if membrane else 1.0), (0, 0, 0), seg=96, ring=48, mat=mat_marble(name=name + '_marble', scale=2.2 / rn)); parent(inner, root); out['inner'] = inner
    if cutter: boolean_cut(inner, cutter)
    core_m = mat_speckle((0.07, 0.09, 0.42), (0.55, 0.6, 0.95), scale=22 / rn, thr=0.58, name=name + '_core', bump=0.5)
    if cut == 'wedge': cl = (0, -0.24 * rn, 0.03 * rn)            # a dome at the floor/wall corner, nothing to cut
    elif cut == 'half': cl = (0, 0.05 * rn, 0)
    else: cl = (0, 0, 0)
    core = sphere(name + 'Core', rn * core_r, cl, seg=64, ring=32, mat=core_m); parent(core, root); out['core'] = core
    if pores and membrane:
        pts, nrm = rand_on_ellipsoid(rnd, (0, 0, 0), (rn, rn, rn), pores * (2 if cut == 'wedge' else 1), front=(0, 1, 0) if cut == 'half' else None)
        if cut == 'wedge':
            keep = [i for i, p in enumerate(pts) if not (p[1] < 0.02 * rn and p[2] > -0.02 * rn)][:pores]
            pts = [pts[i] for i in keep]; nrm = [nrm[i] for i in keep]
        po = spheres_mesh(name + 'Pores', pts, 0.085 * rn, mat_organic((0.95, 0.5, 0.6), rough=0.4, sss=0.4, name=name + '_pore'), subdiv=2, scale3=(1.0, 1.0, 0.75), normals=nrm)
        parent(po, root); out['pores'] = po
    if chromatin:
        blue = mat_organic((0.2, 0.42, 0.95), rough=0.35, sss=0.1, coat=0.4, name=name + '_chrom'); beads = []
        ri = rn * (1.0 - thick - 0.02 if membrane else 1.0)
        for i in range(chromatin):
            if cut == 'wedge' and i % 2 == 0:      # on the floor (z = 0 plane, front half)
                st = (rnd.uniform(-0.5, 0.5) * ri, rnd.uniform(-0.75, -0.15) * ri, 0.03 * rn)
                pts = wander_pts(rnd, st, 9, 0.2 * rn, ((-0.85 * ri, 0.85 * ri), (-0.9 * ri, -0.03 * ri), (0.03 * rn, 0.03 * rn)), z_fixed=0.03 * rn)
            elif cut == 'wedge':                    # on the back wall (y = 0 plane, upper half): wander in (x, z)
                w = wander_pts(rnd, (rnd.uniform(-0.5, 0.5) * ri, rnd.uniform(0.15, 0.7) * ri, 0.0), 9, 0.2 * rn, ((-0.85 * ri, 0.85 * ri), (0.05 * ri, 0.9 * ri), (0, 0)), z_fixed=0.0)
                pts = [(q[0], -0.03 * rn, q[1]) for q in w]
            else:                                   # 'half': on the vertical cut face
                w = wander_pts(rnd, (rnd.uniform(-0.5, 0.5) * ri, rnd.uniform(-0.6, 0.6) * ri, 0.0), 9, 0.2 * rn, ((-0.85 * ri, 0.85 * ri), (-0.85 * ri, 0.85 * ri), (0, 0)), z_fixed=0.0)
                pts = [(q[0], -0.03 * rn, q[1]) for q in w]
            # keep inside the interior disc
            pts = [p for p in pts if (p[0] ** 2 + p[1] ** 2 + p[2] ** 2) < (0.93 * ri) ** 2] or pts[:2]
            if len(pts) < 2: continue
            c = curve_obj(f'{name}Chrom{i}', pts, 0.018 * rn, blue); parent(c, root)
            for p in catmull(pts, 40): beads.append(p)
        if beads:
            bd = spheres_mesh(name + 'Beads', beads, 0.032 * rn, blue, subdiv=1); parent(bd, root); out['beads'] = bd
    return out

# ================================================================= organelles
def rough_er(loc, s=1.0, name='ER', n_lobes=13, ribo=240, seed=3, rot=0.0, trumpets=7):
    """Rough ER: two staggered arcs of pink lobes studded with dark ribosomes; smooth ER as orange trumpet tubules."""
    rnd = random.Random(seed); root = empty(name, loc); root.rotation_euler = (0, 0, rot); out = {'root': root, 'lobes': []}
    pink = mat_organic((0.95, 0.5, 0.56), rough=0.45, sss=0.45, coat=0.25, name=name + '_pink', radius=(1.0, 0.3, 0.3))
    dots = []; ndot = []
    for row in range(2):
        nl = n_lobes - row * 2
        for i in range(nl):
            u = (i - (nl - 1) / 2) / max(1, nl - 1); ang = u * 1.7
            R = (1.2 + 0.45 * row) * s
            cx = R * math.sin(ang); cy = -R * math.cos(ang) + R * 0.8 + 0.1 * s
            h = s * rnd.uniform(0.34, 0.46) * (1 + 0.3 * row)
            lo = sphere(f'{name}Lobe{row}_{i}', 0.24 * s, (cx, cy, h * 0.85), seg=48, ring=24, mat=pink, scale=(0.78, 1.35, h / (0.24 * s)))
            lo.rotation_euler = (rnd.uniform(-0.12, 0.12), rnd.uniform(-0.12, 0.12), ang); subsurf(lo, 1, 1); parent(lo, root); out['lobes'].append(lo)
            pts, nrm = rand_on_ellipsoid(rnd, (cx, cy, h * 0.9), (0.2 * s, 0.3 * s, h), max(4, ribo // (2 * n_lobes)), front=(0, -1, 0.3))
            dots += pts; ndot += nrm
    rib = spheres_mesh(name + 'Ribosomes', dots, 0.045 * s, mat_organic((0.33, 0.1, 0.32), rough=0.35, sss=0.1, coat=0.3, name=name + '_ribo'), subdiv=1, rscale=[rnd.uniform(0.7, 1.3) for _ in dots])
    parent(rib, root); out['ribosomes'] = rib
    orange = mat_organic((0.92, 0.4, 0.04), rough=0.5, sss=0.08, coat=0.05, name=name + '_orange', radius=(1.0, 0.4, 0.1))
    prof = [(0.0, 0.0), (0.05, 0.0), (0.052, 0.55), (0.08, 0.8), (0.2, 0.96), (0.24, 1.0), (0.2, 1.0), (0.075, 0.82), (0.04, 0.58), (0.0, 0.58)]
    out['trumpets'] = []
    for i in range(trumpets):
        u = (i - (trumpets - 1) / 2) / max(1, trumpets - 1)
        hh = s * rnd.uniform(1.05, 1.55); tr = lathe(f'{name}Trumpet{i}', [(a * s * 0.85, b * hh) for a, b in prof], orange, loc=(-0.55 * s + u * 1.1 * s + rnd.uniform(-0.1, 0.1) * s, -0.55 * s + rnd.uniform(-0.25, 0.2) * s, 0.02))
        tr.rotation_euler = (rnd.uniform(-0.22, 0.02), rnd.uniform(-0.18, 0.18), 0); parent(tr, root); out['trumpets'].append(tr)
    base = sphere(name + 'Base', 0.8 * s, (-0.5 * s, -0.5 * s, 0.0), seg=64, ring=32, mat=mat_translucent((1.0, 0.35, 0.12), alpha=0.5, rough=0.5, emit=0.8, name=name + '_base'), scale=(1.0, 0.7, 0.08)); parent(base, root)
    return out

def golgi(loc, s=1.0, name='Golgi', n_sheets=6, rot=0.0, seed=4, vesicles=12):
    """Golgi apparatus: a stack of curved orange cisternae (flattened, upturned ends) with vesicles budding off on stalks."""
    rnd = random.Random(seed); root = empty(name, loc); root.rotation_euler = (0, 0, rot); out = {'root': root, 'sheets': []}
    orange = mat_organic((0.9, 0.36, 0.05), rough=0.5, sss=0.08, coat=0.05, name=name + '_or', radius=(1.0, 0.4, 0.1))
    ves, stalks = [], []
    for i in range(n_sheets):
        w = s * (1.55 - 0.1 * abs(i - (n_sheets - 1) / 2)); d = s * (0.62 - 0.03 * i); t = 0.11 * s; z0 = i * 0.25 * s; curv = 0.2 + 0.05 * i
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=24, radius=1.0)
        for v in bm.verts:
            X = v.co.x * w; Y = v.co.y * d; Z = v.co.z * t + curv * X * X / w + 0.42 * Y * Y / d + 0.05 * s * math.sin(v.co.y * 2.5)
            v.co = (X, Y, Z + z0)
        sh = mesh_obj(f'{name}Sheet{i}', bm, orange); subsurf(sh, 1, 2); parent(sh, root); out['sheets'].append(sh)
        for e in range(2):
            if rnd.random() < 0.85:
                sx = (1 if e else -1) * w * rnd.uniform(0.86, 1.02); sy = rnd.uniform(-0.6, 0.6) * d
                base = (sx * 0.96, sy, z0 + curv * (sx * 0.96) ** 2 / w + 0.02 * s); tip = (sx * 1.12, sy, base[2] + rnd.uniform(0.08, 0.2) * s)
                stalks.append((base, tip)); ves.append(tip)
    vs = spheres_mesh(name + 'Vesicles', ves, 0.085 * s, orange, subdiv=2, rscale=[rnd.uniform(0.8, 1.2) for _ in ves]); parent(vs, root); out['vesicles'] = vs
    st = tubes_mesh(name + 'Stalks', stalks, 0.016 * s, orange); parent(st, root); out['stalks'] = st
    return out

def lysosome(loc, r=0.5, name='Lys', seed=1, patches=8):
    """Bumpy green sac with pale mint patches (subsurface), displaced + subdivided."""
    rnd = random.Random(seed)
    o = sphere(name, r, loc, seg=96, ring=48, mat=mat_organic((0.1, 0.5, 0.1), rough=0.5, sss=0.35, coat=0.15, name=name + '_g', radius=(0.3, 0.9, 0.2)), scale=(1.0, 1.0, 0.72))
    displace(o, scale=r * 1.1, strength=r * 0.16, name=name + '_d'); subsurf(o, 1, 2)
    pts, nrm = rand_on_ellipsoid(rnd, (0, 0, 0), (r * 0.98, r * 0.98, r * 0.98), patches)
    pm = spheres_mesh(name + 'Patches', pts, r * 0.36, mat_organic((0.78, 0.92, 0.7), rough=0.55, sss=0.5, name=name + '_p'), subdiv=3, scale3=(1.0, 1.0, 0.32), normals=nrm)
    displace(pm, scale=r * 0.5, strength=r * 0.05, name=name + '_pd'); parent(pm, o)
    return o

def serpentine_wall(name, length, amp, waves, height, z0, mat, thick, n=160, taper=True):
    bm = bmesh.new(); prev = None
    for i in range(n + 1):
        u = i / n; x = -length / 2 + length * u; y = amp * math.sin(2 * math.pi * waves * u)
        hh = height * (1 - 0.35 * (2 * u - 1) ** 4) if taper else height
        a = bm.verts.new((x, y, z0)); b = bm.verts.new((x, y, z0 + hh))
        if prev is not None: bm.faces.new((prev[0], a, b, prev[1]))
        prev = (a, b)
    o = mesh_obj(name, bm, mat); solidify(o, thick); subsurf(o, 1, 2); return o

def mitochondrion(loc, L=2.0, name='Mito', cut=True, detail=1, rot=0.0, seed=5, tilt=0.0):
    """Double-membrane capsule cut open on top: gold outer rim, cream matrix, deeply folded green inner membrane
    (cristae) with orange ATP beads; detail=2 adds ribosome dots and DNA helices."""
    rnd = random.Random(seed); root = empty(name, loc); root.rotation_euler = (tilt, 0, rot); out = {'root': root}
    R = 0.25 * L; h = L - 2 * R
    outer = capsule(name + 'Outer', R, h, mat=mat_organic((0.95, 0.7, 0.16), rough=0.35, sss=0.3, coat=0.4, name=name + '_outer', radius=(1.0, 0.6, 0.1)), zscale=0.72); solidify(outer, 0.055 * L); subsurf(outer, 1, 1); parent(outer, root)
    matrix = capsule(name + 'Matrix', R * 0.93, h, mat=mat_organic((0.93, 0.9, 0.7), rough=0.5, sss=0.4, coat=0.1, name=name + '_matrix'), zscale=0.72 * 0.93); subsurf(matrix, 1, 1); parent(matrix, root)
    if cut:
        cutter = cutter_box(name + 'Cut', (0, 0, 1.3 * R + 0.143 * R), (1.4 * L, 1.4 * L, 2.6 * R)); parent(cutter, root)
        boolean_cut(outer, cutter); boolean_cut(matrix, cutter); out['cutter'] = cutter
    green = mat_organic((0.12, 0.5, 0.17), rough=0.38, sss=0.3, coat=0.35, name=name + '_green', radius=(0.2, 0.8, 0.2))
    waves = 4 if detail == 1 else 5
    wall = serpentine_wall(name + 'Cristae', L * 0.78, 0.5 * R, waves, 0.42 * R, -0.05 * R, green, (0.11 if detail == 1 else 0.2) * R); parent(wall, root); out['cristae'] = wall
    if detail >= 2: displace(wall, scale=0.35 * R, strength=0.06 * R, name=name + '_cd')
    pts = []; nrm = []
    for i in range(22 if detail == 1 else 34):
        u = rnd.random(); x = -L * 0.39 + L * 0.78 * u; y = 0.5 * R * math.sin(2 * math.pi * waves * u)
        pts.append((x, y, 0.37 * R * (1 - 0.35 * (2 * u - 1) ** 4) + 0.02 * R))
    out['atp'] = spheres_mesh(name + 'ATP', pts, 0.045 * R, mat_organic((0.98, 0.62, 0.1), rough=0.3, coat=0.5, sss=0.2, name=name + '_atp'), subdiv=2); parent(out['atp'], root)
    if detail >= 2:
        bp = []
        for i in range(160):
            u = rnd.random(); x = -L * 0.39 + L * 0.78 * u; y = 0.5 * R * math.sin(2 * math.pi * waves * u) + rnd.choice((-1, 1)) * 0.07 * R
            bp.append((x, y, rnd.uniform(0.0, 0.34 * R)))
        out['ribo'] = spheres_mesh(name + 'Ribo', bp, 0.02 * R, mat_organic((0.12, 0.25, 0.95), rough=0.3, coat=0.4, name=name + '_ribo'), subdiv=1); parent(out['ribo'], root)
        blue = mat_organic((0.25, 0.55, 0.98), rough=0.3, coat=0.4, name=name + '_dna')
        for i in range(2):
            pts = helix_pts(0.32 * L, 0.05 * R, 6, n=140)
            c = curve_obj(f'{name}DNA{i}', [(p[0] + (-0.18 if i == 0 else 0.22) * L, p[1] + (0.75 if i == 0 else -0.7) * R, p[2] + 0.09 * R) for p in pts], 0.012 * R, blue, res=6)
            parent(c, root)
    return out

def chloroplast(loc, s=1.0, name='Chloro', cut=True, grana=7, rot=0.0, tilt=0.0, seed=6):
    """Green lens-shaped plastid opened on top, stacks of thylakoid discs (grana) standing inside."""
    rnd = random.Random(seed); root = empty(name, loc); root.rotation_euler = (tilt, 0, rot); out = {'root': root}
    shell = sphere(name + 'Shell', 1.0, (0, 0, 0), seg=96, ring=48, mat=mat_organic((0.1, 0.42, 0.08), rough=0.45, sss=0.3, coat=0.15, name=name + '_shell', radius=(0.1, 0.6, 0.1)), scale=(1.0 * s, 0.62 * s, 0.5 * s))
    solidify(shell, 0.05 * s); parent(shell, root); out['shell'] = shell
    stroma = sphere(name + 'Stroma', 0.96, (0, 0, 0), seg=64, ring=32, mat=mat_organic((0.18, 0.55, 0.14), rough=0.55, sss=0.35, name=name + '_stroma', radius=(0.2, 0.8, 0.2)), scale=(1.0 * s, 0.62 * s, 0.5 * s)); parent(stroma, root)
    if cut:
        cutter = cutter_box(name + 'Cut', (0, 0, 0.143 * s + 1.0 * s), (3 * s, 3 * s, 2 * s)); parent(cutter, root)
        boolean_cut(shell, cutter); boolean_cut(stroma, cutter); out['cutter'] = cutter
    gm = mat_organic((0.36, 0.86, 0.22), rough=0.4, sss=0.3, coat=0.25, name=name + '_grana', radius=(0.2, 0.9, 0.2))
    out['grana'] = []
    for i in range(grana):
        for tries in range(40):
            gx, gy = rnd.uniform(-0.72, 0.72) * s, rnd.uniform(-0.36, 0.36) * s
            if (gx / (0.78 * s)) ** 2 + (gy / (0.42 * s)) ** 2 <= 1 and all((gx - g.location.x) ** 2 + (gy - g.location.y) ** 2 > (0.3 * s) ** 2 for g in out['grana']): break
        nz = rnd.randint(5, 7)
        g = obj_add('cylinder', f'{name}Grana{i}', radius=0.135 * s, depth=0.032 * s, vertices=48, location=(gx, gy, 0.1 * s))
        setmat(g, gm); smooth(g); bevel(g, 0.008 * s, 4)
        try: arr = g.modifiers.new('stack', 'ARRAY'); arr.count = nz; arr.relative_offset_displace = (0, 0, 1.55)
        except Exception: pass
        g.rotation_euler = (rnd.uniform(-0.1, 0.1), rnd.uniform(-0.1, 0.1), 0); parent(g, root); out['grana'].append(g)
    return out

def leucoplast_cell(loc, r=1.0, name='Leuco', seed=7, starch=4):
    rnd = random.Random(seed); root = empty(name, loc)
    shell = sphere(name + 'Shell', r, (0, 0, 0), seg=96, ring=48, mat=mat_rim((0.55, 0.58, 0.62), (0.75, 0.8, 0.88), a_center=0.25, a_rim=0.9, emit=0.35, name=name + '_shell', rough=0.35)); parent(shell, root)
    white = mat_speckle((0.85, 0.88, 0.9), (0.55, 0.6, 0.68), scale=35 / r, thr=0.55, name=name + '_starch', rough=0.7, bump=0.6)
    pts = [(rnd.uniform(-0.4, 0.4) * r, rnd.uniform(-0.25, 0.35) * r, rnd.uniform(-0.35, 0.35) * r) for _ in range(starch)]
    for i, p in enumerate(pts):
        g = sphere(f'{name}Starch{i}', r * rnd.uniform(0.16, 0.26), p, seg=64, ring=32, mat=white); displace(g, scale=r * 0.25, strength=r * 0.04, name=f'{name}_sd{i}'); parent(g, root)
    return root

def chloroplast_cell(loc, r=1.0, name='Chromo', seed=8, n=5):
    rnd = random.Random(seed); root = empty(name, loc)
    shell = sphere(name + 'Shell', r, (0, 0, 0), seg=96, ring=48, mat=mat_rim((0.42, 0.3, 0.16), (0.75, 0.55, 0.3), a_center=0.35, a_rim=0.9, emit=0.3, name=name + '_shell', rough=0.4)); parent(shell, root)
    plast = []
    for i in range(n):
        for tries in range(60):
            p = (rnd.uniform(-0.55, 0.55) * r, rnd.uniform(-0.3, 0.3) * r, rnd.uniform(-0.45, 0.45) * r)
            if all((Vector(p) - Vector(q)).length > 0.5 * r for q in plast): break
        plast.append(p)
        c = chloroplast((0, 0, 0), s=0.34 * r, name=f'{name}Chl{i}', grana=5, seed=seed + i)
        c['root'].location = p; c['root'].rotation_euler = (rnd.uniform(-0.5, 0.5), rnd.uniform(-0.6, 0.6), rnd.uniform(0, 3.14)); parent(c['root'], root)
    return {'root': root, 'positions': plast}

def bacterium(loc, L=2.4, name='Bact', seed=9, rot=0.0, cut=True, flagella=False):
    """Lilac capsule (flagella at the poles) opened front-top: speckled interior, purple coiled nucleoid, blue threads."""
    rnd = random.Random(seed); root = empty(name, loc); root.rotation_euler = (0, 0, rot); out = {'root': root}
    R = 0.3 * L; h = L - 2 * R
    shell = capsule(name + 'Shell', R, h, mat=mat_translucent((0.72, 0.6, 0.92), alpha=0.6, rough=0.25, name=name + '_shell', sss=0.2), zscale=0.8); solidify(shell, 0.03 * L); subsurf(shell, 1, 1); parent(shell, root)
    inner = capsule(name + 'Inner', R * 0.96, h, mat=mat_blotch((0.8, 0.7, 0.92), (0.6, 0.45, 0.8), scale=14 / L, lo=0.4, hi=0.62, rough=0.6, sss=0.3, name=name + '_in'), zscale=0.8 * 0.96); subsurf(inner, 1, 1); parent(inner, root)
    if cut:
        cutter = cutter_box(name + 'Cut', (0.15 * L, -1.1 * R + EPS * R, 1.1 * R - EPS * R), (1.6 * L, 2.2 * R, 2.2 * R)); parent(cutter, root)
        boolean_cut(shell, cutter); boolean_cut(inner, cutter); out['cutter'] = cutter
    purple = mat_organic((0.5, 0.15, 0.85), rough=0.3, coat=0.5, sss=0.2, name=name + '_nucleoid')
    pts = helix_pts(0.34 * L, 0.16 * R, 3.0, n=100, taper=0.25)
    coil = curve_obj(name + 'Nucleoid', [(p[0], p[1] * 0.6 - 0.4 * R, p[2] + 0.2 * R) for p in pts], 0.055 * R, purple); parent(coil, root); out['nucleoid'] = coil
    blue = mat_organic((0.25, 0.5, 0.98), rough=0.3, coat=0.4, name=name + '_thread'); beads = []
    for i in range(5):
        st = (rnd.uniform(-0.3, 0.3) * L, rnd.uniform(-0.75, -0.15) * R, 0.035 * R)
        p = wander_pts(rnd, st, 8, 0.12 * L, ((-0.45 * L, 0.45 * L), (-0.85 * R, -0.05 * R), (0.03 * R, 0.04 * R)), z_fixed=0.035 * R)
        c = curve_obj(f'{name}Thread{i}', p, 0.012 * R, blue, res=8); parent(c, root); beads += catmull(p, 36)
    bd = spheres_mesh(name + 'Beads', beads, 0.024 * R, blue, subdiv=1); parent(bd, root)
    lil = mat_organic((0.8, 0.7, 0.95), rough=0.4, name=name + '_flag')
    for sgn in ((-1, 1) if flagella else ()):
        pts = [((h / 2 + R * 0.9) * sgn + sgn * 0.55 * L * u, 0.12 * L * math.sin(u * 7) * u, 0.05 * L * math.cos(u * 5) * u) for u in [k / 24 for k in range(25)]]
        fl = curve_obj(f'{name}Flag{sgn}', pts, 0.012 * L, lil, res=8); parent(fl, root)
    return out

def lipid_prop(loc, n=12, spacing=0.36, name='Lipid'):
    """Two layers of orange phospholipid heads with pale tails between: one unit + two Array modifiers."""
    root = empty(name, loc); head = mat_organic((0.98, 0.62, 0.16), rough=0.32, sss=0.3, coat=0.5, name='lipid_head', radius=(1.0, 0.4, 0.1))
    tail = mat_organic((0.95, 0.85, 0.55), rough=0.5, name='lipid_tail'); parts = []
    for sgn, tag in ((1, 'T'), (-1, 'B')):
        hz = sgn * 0.55
        hd = sphere(f'{name}Head{tag}', 0.165, (0, 0, hz), seg=48, ring=24, mat=head, scale=(1, 1, 1.2)); parts.append(hd)
        for k, dx in enumerate((-0.07, 0.07)):
            tl = obj_add('cylinder', f'{name}Tail{tag}{k}', radius=0.028, depth=0.5, vertices=16, location=(dx, 0.03 * (1 if k else -1), hz - sgn * 0.33))
            tl.rotation_euler = (0.18 * (1 if k else -1), -dx * 1.2 * sgn, 0); setmat(tl, tail); smooth(tl); parts.append(tl)
    for o in parts:
        for ax, nm in ((0, 'ax'), (1, 'ay')):
            try:
                arr = o.modifiers.new(nm, 'ARRAY'); arr.count = n; arr.use_relative_offset = False; arr.use_constant_offset = True
                arr.constant_offset_displace = (spacing if ax == 0 else 0, spacing if ax == 1 else 0, 0)
            except Exception: pass
        o.location = (o.location.x - spacing * (n - 1) / 2, o.location.y - spacing * (n - 1) / 2, o.location.z); parent(o, root)
    return root

def env_sphere(loc=(0, 0, 0), r=4.5, name='Env'):
    o = sphere(name, r, loc, seg=128, ring=64, mat=mat_rim((0.02, 0.12, 0.3), (0.15, 0.6, 1.0), a_center=0.35, a_rim=0.95, emit=1.6, name='env_m', blend=0.25, rough=0.5))
    try: o.visible_shadow = False
    except Exception: pass
    return o

def molecules(prefix, n, cell_r, seed, rfps, nf, t_show, t_in0, t_in1, r=0.09, color=(0.85, 0.95, 1.0), inside_frac=0.75, center=(0, 0, 0)):
    """Small glowing spheres named prefix+i (Hp*=H2O, Op*=O2, Rp*=CO2 -> 2D markers). They appear at t_show scattered
    outside the cell, then drift through the membrane to random interior points between t_in0 and t_in1."""
    rnd = random.Random(seed); m = mat_translucent(color, alpha=0.55, rough=0.2, emit=1.2, name=prefix + '_m'); out = []
    for i in range(n):
        a = rnd.uniform(0, 2 * math.pi); el = rnd.uniform(-0.5, 0.5); d = cell_r * rnd.uniform(1.6, 2.4)
        p0 = Vector((center[0] + d * math.cos(a) * math.cos(el), center[1] + d * math.sin(a) * math.cos(el) * 0.5, center[2] + d * math.sin(el)))
        o = obj_add('uv_sphere', f'{prefix}{i}', radius=r, segments=32, ring_count=16, location=tuple(p0)); setmat(o, m); smooth(o, auto=False)
        hide_until(o, F(t_show + rnd.uniform(0, 1.5), rfps))
        goes_in = rnd.random() < inside_frac
        t0 = t_in0 + (t_in1 - t_in0) * rnd.random() * 0.7; t1 = t0 + (t_in1 - t_in0) * 0.3
        if goes_in:
            b = rnd.uniform(0, 2 * math.pi); e2 = rnd.uniform(-0.6, 0.6); dd = cell_r * rnd.uniform(0.15, 0.75)
            p1 = Vector((center[0] + dd * math.cos(b) * math.cos(e2), center[1] + dd * math.sin(b) * math.cos(e2) * 0.4 - 0.2 * cell_r, center[2] + dd * math.sin(e2)))
        else:
            p1 = p0 + Vector((rnd.uniform(-0.6, 0.6), rnd.uniform(-0.3, 0.3), rnd.uniform(-0.5, 0.5))) * cell_r * 0.6
        kf(o, 'location', 1, tuple(p0)); kf(o, 'location', F(t0, rfps), tuple(p0)); kf(o, 'location', F(t1, rfps), tuple(p1))
        drift = p1 + Vector((rnd.uniform(-0.15, 0.15), rnd.uniform(-0.1, 0.1), rnd.uniform(-0.15, 0.15))) * cell_r
        kf(o, 'location', nf, tuple(drift)); kf_ease(o); out.append(o)
    return out

# ================================================================= props: onion, lab, microscope, cork, honeycomb
def onion(loc=(0, 0, 0), r=1.0, name='Onion'):
    skin = mat_streaks((0.5, 0.03, 0.12), (0.72, 0.1, 0.2), name='onion_skin', rough=0.3, coat=0.6)
    o = sphere(name, r, loc, seg=128, ring=64, mat=skin); me = o.data
    for v in me.vertices:
        u = v.co.z / r; v.co.z *= 1.04
        if u > 0.6: v.co.z += 0.14 * r * ((u - 0.6) / 0.4) ** 2.5
        s_ = 1 + 0.035 * math.sin(math.atan2(v.co.y, v.co.x) * 9) * max(0.0, 1 - abs(u))
        v.co.x *= s_; v.co.y *= s_
    me.update(); subsurf(o, 1, 1)
    return o

def onion_cups(loc=(0, 0, 0), r=1.0, name='Cup', radii=(1.0, 0.86, 0.72, 0.58, 0.44, 0.3), spread=0.0, cutter=None, col0=0):
    """Concentric onion layers cut in half (opening faces the camera at -Y). spread pushes them apart along X."""
    cols = [(0.5, 0.03, 0.12), (0.9, 0.62, 0.78), (0.96, 0.85, 0.94), (0.94, 0.8, 0.92), (0.97, 0.9, 0.96), (0.9, 0.7, 0.85), (0.95, 0.85, 0.93)]
    if cutter is None:
        cutter = cutter_box(name + 'Cut', (loc[0], loc[1] - 1.6 * r + EPS * r, loc[2]), (6 * r, 3.2 * r, 4 * r))
    cups = []
    for i, rr in enumerate(radii):
        ci = i + col0
        m = mat_streaks(cols[ci], tuple(c * 0.85 for c in cols[ci]), name=f'{name}_m{i}', rough=0.3, coat=0.5) if ci == 0 else mat_organic(cols[ci], rough=0.4, sss=0.5, coat=0.4, name=f'{name}_m{i}', radius=(1.0, 0.6, 0.8))
        c = sphere(f'{name}{i}', rr * r, (loc[0] + spread * i * r, loc[1], loc[2]), seg=96, ring=48, mat=m); solidify(c, 0.075 * r); boolean_cut(c, cutter); cups.append(c)
    return cups, cutter

def onion_piece(loc=(0, 0, 0), size=0.9, name='Piece', bend=0.12, seed=3, curl=False):
    """A peeled scrap of onion layer: irregular outline, gentle curvature, thin, translucent."""
    rnd = random.Random(seed); bm = bmesh.new(); n = 32; ring = []
    for i in range(n):
        a = 2 * math.pi * i / n; rr = size * (0.5 + 0.09 * math.sin(a * 3 + 1) + 0.05 * math.sin(a * 7 + rnd.random()))
        ring.append(bm.verts.new((rr * math.cos(a) * 1.2, rr * math.sin(a) * 0.85, 0)))
    f = bm.faces.new(ring)
    bmesh.ops.triangulate(bm, faces=[f]); bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=3, use_grid_fill=True)
    for v in bm.verts:
        v.co.z = bend * (v.co.x ** 2 + 0.5 * v.co.y ** 2) / size + (0.35 * size * (v.co.x / size) ** 2 if curl else 0.0)
    o = mesh_obj(name, bm, mat_organic((0.96, 0.88, 0.95), rough=0.35, sss=0.6, coat=0.4, name=name + '_m', radius=(1.0, 0.7, 0.9)), loc=loc)
    solidify(o, 0.02 * size); subsurf(o, 2, 2); return o

def forceps(loc=(0, 0, 0), L=2.4, name='Forceps', open_ang=0.14):
    """White lab forceps: two tapered arms joined at the top, tips slightly curved in. Returns root + arms."""
    root = empty(name, loc); white = mat_white_plastic(name + '_m'); arms = []
    for s in (-1, 1):
        bm = bmesh.new(); n = 12; prev = None
        for i in range(n + 1):
            u = i / n; z = -L * u; w = 0.13 * (1 - 0.55 * u) + 0.03; t = 0.05 * (1 - 0.4 * u) + 0.012
            xo = 0.05 * (1 - u) ** 0.5 * 0 - 0.04 * u ** 3        # tip curves inward
            vs = [bm.verts.new((s * (xo + w / 2) + s * 0.03, -t / 2, z)), bm.verts.new((s * (xo - w / 2) + s * 0.03, -t / 2, z)),
                  bm.verts.new((s * (xo - w / 2) + s * 0.03, t / 2, z)), bm.verts.new((s * (xo + w / 2) + s * 0.03, t / 2, z))]
            if prev is not None:
                for k in range(4): bm.faces.new((prev[k], prev[(k + 1) % 4], vs[(k + 1) % 4], vs[k]))
            else: bm.faces.new(vs)
            prev = vs
        bm.faces.new(list(reversed(prev)))
        arm = mesh_obj(f'{name}Arm{s}', bm, white, smooth_=False); bevel(arm, 0.008, 3); smooth(arm); arm.rotation_euler = (0, s * open_ang, 0); parent(arm, root); arms.append(arm)
    piv = obj_add('cylinder', name + 'Pivot', radius=0.07, depth=0.16, vertices=32, location=(0, 0, 0.02)); piv.rotation_euler = (math.pi / 2, 0, 0); setmat(piv, white); smooth(piv); parent(piv, root)
    return root, arms

def watch_glass_dark(loc=(0, 0, 0), r=1.3, name='WatchGlass', water=True):
    prof = [(0.0, 0.0), (r * 0.45, 0.03), (r * 0.8, 0.14), (r * 0.97, 0.3), (r, 0.36)]
    m = mat_glassy((0.12, 0.14, 0.17), alpha=0.9, rough=0.15, name=name + '_g')
    if not CY:
        m = mat_glass((0.06, 0.07, 0.09), alpha=0.93, rough=0.22, name=name + '_g'); p = m.node_tree.nodes.get('Principled BSDF'); _inp(p, 'Coat Weight', 0.6); _inp(p, 'Specular IOR Level', 0.8)
    o = lathe(name, prof, m, loc=loc); solidify(o, 0.035); bevel(o, 0.01, 3)
    out = {'dish': o}
    if water:
        wm = mat_glassy((0.7, 0.85, 1.0), alpha=0.3, rough=0.05, name=name + '_water') if CY else mat_glass((0.7, 0.88, 1.0), alpha=0.28, rough=0.05, name=name + '_water')
        w = liquid_column(name + 'Water', [(0.0, 0.03), (r * 0.5, 0.06), (r * 0.78, 0.15), (r * 0.9, 0.24)], loc, alpha=0.3); setmat(w, wm); out['water'] = w
    return out

def glass_slide(loc=(0, 0, 0), name='Slide', size=(2.6, 1.0, 0.07), tint=(0.2, 0.5, 0.55)):
    o = obj_add('cube', name, size=1.0, location=loc); o.scale = size
    if CY: m = mat_liquid_real(color=(0.12, 0.42, 0.48), ior=1.5, absorption=1.6, name=name + '_m')
    else: m = mat_glass(tint, alpha=0.82, rough=0.06, name=name + '_m'); _inp(m.node_tree.nodes.get('Principled BSDF'), 'Coat Weight', 1.0)
    setmat(o, m); bevel(o, 0.012, 4); smooth(o)
    return o

def cover_slip_obj(loc=(0, 0, 0), name='CoverSlip', size=(0.85, 0.85, 0.014)):
    o = obj_add('cube', name, size=1.0, location=loc); o.scale = size
    setmat(o, mat_glassy((0.9, 0.97, 1.0), alpha=0.22, rough=0.03, name=name + '_m')); bevel(o, 0.004, 2); smooth(o); return o

def dropper_bottle(loc=(0, 0, 0), h=1.0, name='Bottle', cap_col=(0.04, 0.04, 0.05)):
    """Small white dropper bottle: squat body, shoulder, black cap + rubber bulb."""
    root = empty(name, loc); white = mat_white_plastic(name + '_w'); black = mat_plastic(cap_col, rough=0.45, name=name + '_k')
    prof = [(0.0, 0.0), (0.2 * h, 0.0), (0.24 * h, 0.03 * h), (0.24 * h, 0.55 * h), (0.2 * h, 0.64 * h), (0.11 * h, 0.7 * h), (0.11 * h, 0.74 * h), (0.0, 0.74 * h)]
    body = lathe(name + 'Body', prof, white); parent(body, root)
    cap = obj_add('cylinder', name + 'Cap', radius=0.13 * h, depth=0.16 * h, vertices=64, location=(0, 0, 0.8 * h)); setmat(cap, black); smooth(cap); bevel(cap, 0.015 * h, 4); parent(cap, root)
    bulb = sphere(name + 'Bulb', 0.1 * h, (0, 0, 0.96 * h), seg=48, ring=24, mat=black, scale=(1, 1, 1.25)); parent(bulb, root)
    return root

def dropper(loc=(0, 0, 0), L=1.1, name='Dropper'):
    root = empty(name, loc); glass = mat_glassy((0.9, 0.97, 1.0), alpha=0.3, rough=0.05, name=name + '_g'); black = mat_black_rubber(name + '_k')
    tube = lathe(name + 'Tube', [(0.0, 0.0), (0.03 * L, 0.0), (0.05 * L, 0.2 * L), (0.06 * L, 0.75 * L), (0.06 * L, 0.8 * L), (0.0, 0.8 * L)], glass); parent(tube, root)
    bulb = sphere(name + 'Bulb', 0.11 * L, (0, 0, 0.9 * L), seg=48, ring=24, mat=black, scale=(1, 1, 1.4)); parent(bulb, root)
    return root

def drops(n, start, end, t0, dt, rfps, name='Drop', color=(0.7, 0.85, 1.0), r=0.05, seed=4, alpha=0.6, emit=0.0):
    """Falling drops: spawn at `start`, fall to `end` in 0.5 s, one every dt seconds from t0."""
    rnd = random.Random(seed); m = mat_translucent(color, alpha=alpha, rough=0.05, emit=emit, name=name + '_m'); out = []
    for i in range(n):
        d = sphere(f'{name}{i}', r, start, seg=32, ring=16, mat=m, scale=(1, 1, 1.4))
        ts = t0 + i * dt; f0, f1 = F(ts, rfps), F(ts + 0.5, rfps)
        kf(d, 'hide_render', 1, True); kf(d, 'hide_render', f0, False); kf(d, 'hide_render', f1, True)
        kf(d, 'location', f0, start); kf(d, 'location', f1, (end[0] + rnd.uniform(-0.05, 0.05), end[1] + rnd.uniform(-0.05, 0.05), end[2])); kf_lin(d); out.append(d)
    return out

def microscope(loc=(0, 0, 0), s=1.0, name='Scope', slide=None):
    """Compound microscope: bevelled base, leaning arm, black stage with clips, inclined eyepiece tube, nosepiece
    with three chrome objectives, coarse/fine focus knobs, condenser + blue illuminator."""
    root = empty(name, loc); white = mat_white_plastic(name + '_w'); black = mat_black_rubber(name + '_k'); chrome = mat_chrome(name + '_c'); grey = mat_plastic((0.3, 0.31, 0.33), rough=0.45, name=name + '_g')
    def box(n, size, pos, m, bw=0.06, rot=(0, 0, 0)):
        o = obj_add('cube', n, size=1.0, location=pos); o.scale = size; o.rotation_euler = rot; setmat(o, m); bevel(o, bw * s, 8); smooth(o); parent(o, root); return o
    def cyl(n, r, d, pos, m, rot=(0, 0, 0), bw=0.0):
        o = obj_add('cylinder', n, radius=r, depth=d, vertices=64, location=pos); o.rotation_euler = rot; setmat(o, m); smooth(o)
        if bw: bevel(o, bw, 4)
        parent(o, root); return o
    box(name + 'Base', (1.7 * s, 1.15 * s, 0.34 * s), (0, 0.05 * s, 0.17 * s), white, bw=0.1)
    box(name + 'Foot', (1.75 * s, 1.2 * s, 0.06 * s), (0, 0.05 * s, 0.03 * s), black, bw=0.02)
    box(name + 'Arm', (0.42 * s, 0.4 * s, 2.3 * s), (0, 0.42 * s, 1.35 * s), white, bw=0.12, rot=(math.radians(-8), 0, 0))
    box(name + 'Head', (0.5 * s, 0.7 * s, 0.42 * s), (0, 0.1 * s, 2.55 * s), white, bw=0.1)
    box(name + 'Stage', (1.25 * s, 1.1 * s, 0.08 * s), (0, 0.0, 1.25 * s), black, bw=0.02)
    for sx in (-0.38, 0.38): box(f'{name}Clip{sx}', (0.06 * s, 0.45 * s, 0.02 * s), (sx * s, -0.05 * s, 1.31 * s), chrome, bw=0.005)
    cyl(name + 'Tube', 0.15 * s, 1.15 * s, (0, -0.28 * s, 3.1 * s), white, rot=(math.radians(-32), 0, 0), bw=0.02 * s)
    cyl(name + 'Eyepiece', 0.13 * s, 0.22 * s, (0, -0.63 * s, 3.66 * s), black, rot=(math.radians(-32), 0, 0), bw=0.02 * s)
    ep = cyl(name + 'EyeLens', 0.09 * s, 0.03 * s, (0, -0.7 * s, 3.77 * s), mat_glassy((0.5, 0.75, 1.0), alpha=0.6, rough=0.05, name=name + '_lens'), rot=(math.radians(-32), 0, 0))
    cyl(name + 'Nose', 0.3 * s, 0.14 * s, (0, -0.05 * s, 2.3 * s), black, bw=0.02 * s)
    for i, a in enumerate((-0.5, 0.0, 0.5)):
        r_ = 0.24 * s; px, py = r_ * math.sin(a), -0.05 * s - r_ * math.cos(a) * 0.5
        o = cyl(f'{name}Obj{i}', 0.065 * s, 0.5 * s * (1.0 - 0.18 * abs(a)), (px, py, 2.0 * s), chrome, rot=(math.radians(-14) * math.cos(a), math.radians(14) * math.sin(a), 0), bw=0.008 * s)
        band = cyl(f'{name}ObjBand{i}', 0.07 * s, 0.1 * s, (px, py, 2.1 * s), black, rot=(math.radians(-14) * math.cos(a), math.radians(14) * math.sin(a), 0))
    for sx in (-1, 1):
        cyl(f'{name}Knob{sx}', 0.2 * s, 0.13 * s, (sx * 0.34 * s, 0.35 * s, 0.9 * s), black, rot=(0, math.pi / 2, 0), bw=0.025 * s)
        cyl(f'{name}KnobF{sx}', 0.11 * s, 0.1 * s, (sx * 0.45 * s, 0.35 * s, 0.9 * s), chrome, rot=(0, math.pi / 2, 0), bw=0.01 * s)
    cyl(name + 'Condenser', 0.18 * s, 0.25 * s, (0, 0, 1.05 * s), chrome, bw=0.01 * s)
    lamp = cyl(name + 'Lamp', 0.16 * s, 0.03 * s, (0, 0.05 * s, 0.35 * s), mat_emit((0.55, 0.8, 1.0), strength=6, name=name + '_lamp'))
    light('POINT', (loc[0], loc[1] + 0.05 * s, loc[2] + 0.55 * s), 40 * s * s, (0.6, 0.8, 1.0), name + 'Glow')
    if slide is not None:
        slide.location = (loc[0] + 0.05 * s, loc[1] - 0.05 * s, loc[2] + 1.33 * s); slide.scale = (1.0 * s, 0.38 * s, 0.03 * s)
    return root

def cork_prop(loc=(0, 0, 0), h=2.0, name='Cork'):
    """Tapered cork stopper: hand-rounded corners (no spline overshoot), mottled cork material, faint displacement."""
    rt, rb = 0.86, 0.72
    prof = [(0.0, 0.0), (rb - 0.06, 0.0), (rb - 0.02, 0.012), (rb, 0.04), (rb + 0.005, 0.08)]
    for i in range(1, 8):
        u = i / 8; prof.append((rb + (rt - rb) * u, 0.08 + (h - 0.16) * u))
    prof += [(rt, h - 0.08), (rt - 0.006, h - 0.035), (rt - 0.03, h - 0.01), (rt - 0.08, h), (0.0, h)]
    o = lathe(name, prof, mat_cork(name + '_m', scale=5.0), loc=loc, verts=128, resample=False); displace(o, scale=0.4, strength=0.025, name=name + '_d')
    return o

def hex_grid(R, cols, rows, disc=None):
    """Centres of a pointy-top hex grid; keep those inside `disc` radius if given."""
    w = math.sqrt(3) * R; out = []
    for j in range(rows):
        for i in range(cols):
            x = (i - (cols - 1) / 2) * w + (w / 2 if j % 2 else 0); y = (j - (rows - 1) / 2) * 1.5 * R
            if disc is None or math.hypot(x, y) <= disc - R * 0.9: out.append((x, y))
    return out

def honeycomb(loc=(0, 0, 0), R=0.5, cols=16, rows=12, h=0.2, wall=0.07, disc=None, name='Comb', floor=True, z0=0.0, floor_mat=None):
    """Hexagonal-prism walls as one mesh (shared edges de-duplicated, solidified), on a mottled cream floor."""
    centres = hex_grid(R, cols, rows, disc); bm = bmesh.new(); vmap = {}; edges = set()
    def vid(p):
        k = (round(p[0], 4), round(p[1], 4))
        if k not in vmap: vmap[k] = len(vmap)
        return vmap[k]
    corners = {}
    for (cx, cy) in centres:
        ids = []
        for i in range(6):
            a = math.radians(60 * i + 30); p = (cx + R * math.cos(a), cy + R * math.sin(a)); ids.append(vid(p)); corners[vid(p)] = p
        for i in range(6): edges.add(frozenset((ids[i], ids[(i + 1) % 6])))
    lo = {}; hi = {}
    for k, p in corners.items():
        lo[k] = bm.verts.new((p[0], p[1], z0)); hi[k] = bm.verts.new((p[0], p[1], z0 + h))
    for e in edges:
        a, b = tuple(e); bm.faces.new((lo[a], lo[b], hi[b], hi[a]))
    walls = mesh_obj(name + 'Walls', bm, mat_organic((0.68, 0.5, 0.07), rough=0.32, sss=0.0, coat=0.35, name=name + '_wall'), smooth_=False, loc=loc)
    solidify(walls, wall)
    out = {'walls': walls}
    if floor:
        if disc is None:
            fl = obj_add('plane', name + 'Floor', size=1.0, location=(loc[0], loc[1], loc[2] + z0)); fl.scale = (cols * R * 2.0, rows * R * 1.6, 1)
        else:
            fl = obj_add('cylinder', name + 'Floor', radius=disc, depth=0.08, vertices=128, location=(loc[0], loc[1], loc[2] + z0 - 0.04)); smooth(fl); bevel(fl, 0.02, 3)
        setmat(fl, floor_mat or mat_comb_floor(name + '_floor')); out['floor'] = fl
    return out

def tissue_plane(loc=(0, 0, 0), size=(4.6, 2.7), name='Tissue'):
    o = obj_add('plane', name, size=1.0, location=loc); o.scale = (size[0], size[1], 1); setmat(o, mat_tissue(name + '_m'))
    return o

def em_column(loc=(0, 0, 0), s=1.0, name='EM'):
    """Electron microscope column seen down its axis: stacked lens coils with a blue glowing bore, on a console."""
    root = empty(name, loc); chrome = mat_chrome(name + '_c'); grey = mat_plastic((0.78, 0.8, 0.83), rough=0.35, name=name + '_g', coat=0.3); dark = mat_plastic((0.12, 0.13, 0.16), rough=0.5, name=name + '_d')
    base = obj_add('cylinder', name + 'Base', radius=1.9 * s, depth=0.35 * s, vertices=128, location=(0, 0, 0.17 * s)); setmat(base, dark); smooth(base); bevel(base, 0.05 * s, 6); parent(base, root)
    z = 0.35 * s
    for i in range(5):
        seg = obj_add('cylinder', f'{name}Seg{i}', radius=(1.05 - 0.06 * i) * s, depth=0.55 * s, vertices=128, location=(0, 0, z + 0.275 * s)); setmat(seg, grey); smooth(seg); bevel(seg, 0.04 * s, 6); parent(seg, root)
        ring_ = obj_add('cylinder', f'{name}Ring{i}', radius=(1.18 - 0.06 * i) * s, depth=0.12 * s, vertices=128, location=(0, 0, z + 0.6 * s)); setmat(ring_, chrome); smooth(ring_); bevel(ring_, 0.02 * s, 4); parent(ring_, root)
        z += 0.7 * s
    bore = obj_add('cylinder', name + 'Bore', radius=0.5 * s, depth=z - 0.35 * s, vertices=96, location=(0, 0, (z + 0.35 * s) / 2)); setmat(bore, mat_emit((0.25, 0.55, 1.0), strength=2.5, name=name + '_bore')); smooth(bore); parent(bore, root)
    for i, (rr, e) in enumerate(((0.45, 6.0), (0.3, 10.0), (0.16, 18.0))):
        d = obj_add('cylinder', f'{name}Lens{i}', radius=rr * s, depth=0.04 * s, vertices=96, location=(0, 0, z - 0.02 * s - 0.25 * s * i)); setmat(d, mat_emit((0.35 + 0.2 * i, 0.65 + 0.12 * i, 1.0), strength=e, name=f'{name}_lens{i}', alpha=0.55)); smooth(d); parent(d, root)
    cap = obj_add('cylinder', name + 'Cap', radius=1.0 * s, depth=0.25 * s, vertices=128, location=(0, 0, z + 0.12 * s)); setmat(cap, grey); smooth(cap); bevel(cap, 0.05 * s, 6); parent(cap, root)
    hole = cutter_box(name + 'Hole', (0, 0, z + 0.12 * s), (1.0 * s, 1.0 * s, 0.6 * s))
    boolean_cut(cap, hole)
    light('POINT', (loc[0], loc[1], loc[2] + z + 0.4 * s), 120 * s * s, (0.4, 0.65, 1.0), name + 'Glow')
    return root, z

# ================================================================= interior set (cell organelles section)
def er_golgi_network(name, er_root, golgi_root, seed=3, n=9, mat=None):
    """The thin green membrane 'wires' the reference draws between the ER and the Golgi (a sparse branching net)."""
    rnd = random.Random(seed); m = mat or mat_organic((0.55, 0.85, 0.3), rough=0.4, coat=0.3, name=name + '_m'); segs = []
    a = Vector(er_root.location); b = Vector(golgi_root.location); d = b - a
    for i in range(n):
        u0 = rnd.uniform(0.2, 0.55); u1 = u0 + rnd.uniform(0.25, 0.45)
        p0 = a + d * u0 + Vector((rnd.uniform(-0.4, 0.4), rnd.uniform(-0.5, 0.5), rnd.uniform(0.05, 0.5)))
        p1 = a + d * min(1.0, u1) + Vector((rnd.uniform(-0.4, 0.4), rnd.uniform(-0.5, 0.5), rnd.uniform(0.05, 0.5)))
        mid = (p0 + p1) / 2 + Vector((rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2), rnd.uniform(-0.1, 0.25)))
        segs += [(tuple(p0), tuple(mid)), (tuple(mid), tuple(p1))]
        if rnd.random() < 0.6:
            q = mid + Vector((rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5), rnd.uniform(0.0, 0.4))); segs.append((tuple(mid), tuple(q)))
    return tubes_mesh(name, segs, 0.009, m, sides=6)

INTERIOR = {}   # filled by interior_set: world positions of the organelles (for cameras)
def interior_set(nf, rfps, r=6.0, cell_loc=(0, 0, 0), tags=True, lights=True, seed=1, mito_detail=1, network=True, plastid=False):
    """The hero set for the organelle section: a big cutaway cell whose floor and back wall are the blotchy cytoplasm,
    with nucleus (back centre), rough+smooth ER in front of it, Golgi to the right, lysosomes and mitochondria around.
    Tag anchors are tiny specks named Tag* (listed in shotlist anchors) that the 2D shield labels hang from."""
    reset(); world(0.0025, 0.004, 0.009); hdri(strength=0.3, rotation=1.3); atmosphere(density=0.002)
    cell = cutaway_cell(cell_loc, r, cut='wedge', nucleus=None, name='Cell', thick=0.06, interior='interior', seg=128)
    x, y, z = cell_loc; out = {'cell': cell}
    P = {'nuc': (x - 0.4, y - 1.75, z + 1.5), 'er': (x - 0.7, y - 3.7, z), 'golgi': (x + 3.0, y - 2.9, z + 0.05),
         'lyso0': (x - 2.5, y - 3.9, z + 0.5), 'lyso1': (x + 1.3, y - 4.9, z + 0.45),
         'mito0': (x - 4.2, y - 1.6, z + 0.22), 'mito1': (x + 3.6, y - 5.0, z + 0.22), 'mito2': (x - 1.0, y - 5.6, z + 0.22), 'mito3': (x + 4.6, y - 0.9, z + 0.22)}
    INTERIOR.clear(); INTERIOR.update(P)
    nuc = nucleus_organelle(P['nuc'], rn=1.55, name='Nuc', cut='half', pores=34, chromatin=0, seed=seed); out['nuc'] = nuc
    er = rough_er(P['er'], s=1.2, name='ER', seed=seed + 2); out['er'] = er
    go = golgi(P['golgi'], s=1.3, name='Golgi', rot=-0.35, seed=seed + 3, n_sheets=7); out['golgi'] = go
    out['lyso'] = [lysosome(P['lyso0'], r=0.66, name='Lyso0', seed=seed + 4), lysosome(P['lyso1'], r=0.62, name='Lyso1', seed=seed + 5)]
    out['mito'] = [mitochondrion(P['mito0'], L=3.1, name='Mito0', rot=0.3, seed=seed + 6, detail=mito_detail), mitochondrion(P['mito1'], L=2.9, name='Mito1', rot=-0.2, seed=seed + 7, detail=mito_detail),
                   mitochondrion(P['mito2'], L=2.6, name='Mito2', rot=0.95, seed=seed + 8, detail=mito_detail), mitochondrion(P['mito3'], L=2.5, name='Mito3', rot=1.25, seed=seed + 9, detail=mito_detail)]
    if network: out['net'] = er_golgi_network('Net', er['root'], go['root'], seed=seed + 11)
    if tags:
        nx, ny, nz = P['nuc']; anchor('TagNuc', (nx, ny - 0.4, nz + 1.6))
        ex, ey, ez = P['er']; anchor('TagER', (ex + 0.1, ey - 0.5, ez + 1.4)); anchor('TagRough', (ex + 1.0, ey - 0.8, ez + 0.95)); anchor('TagSmooth', (ex - 0.7, ey - 1.1, ez + 1.9)); anchor('TagRibo', (ex + 0.5, ey - 1.4, ez + 0.7))
        gx, gy, gz = P['golgi']; anchor('TagGolgi', (gx, gy - 0.3, gz + 2.6))
        for k, nm in (('lyso0', 'TagLyso0'), ('lyso1', 'TagLyso')): lx, ly, lz = P[k]; anchor(nm, (lx, ly - 0.1, lz + 0.6))
        for k, nm in (('mito0', 'TagMito'), ('mito1', 'TagMito1'), ('mito2', 'TagMito2'), ('mito3', 'TagMito3')): mx, my, mz = P[k]; anchor(nm, (mx, my, mz + 0.8))
    if plastid: out['plastid'] = plant_cell_beside((x + 10.5, y - 1.0, z + 2.8), s=3.4)
    if lights:
        light('SPOT', (x + 3.5, y - 7.0, z + 11.0), 2100, (1.0, 0.95, 0.87), 'Key', spot=60, blend=0.85, target=(x, y - 1.5, z + 0.5))
        soft_light((x - 6.0, y - 8.0, z + 4.0), 240, size=6, name='Fill', target=(x, y - 1.5, z + 0.5))
        try: bpy.context.scene.view_settings.exposure = -0.35          # keeps the orange / pink organelles saturated
        except Exception: pass
        soft_light((x + 2.0, y - 2.5, z + 6.5), 160, size=5, color=(0.8, 0.9, 1.0), name='Top', target=(x, y - 2.0, z))
        light('AREA', (x + 4.0, y - 5.5, z + 2.0), 120, (0.75, 0.85, 1.0), 'Rim', size=3, target=(x - 1, y - 1.5, z + 0.8))
        if plastid: light('SPOT', (x + 12.5, y - 7.0, z + 10.0), 2600, (1.0, 0.95, 0.87), 'KeyP', spot=50, blend=0.8, target=(x + 10.5, y - 1.0, z + 2.8))
    return out

def plant_cell_beside(loc, s=3.0):
    """The lone green plastid standing next to the animal cell in the organelle overview (upright, opening to camera)."""
    c = chloroplast((0, 0, 0), s=s, name='Plastid', grana=12, seed=6)
    c['root'].location = loc; c['root'].rotation_euler = (0, math.radians(72), math.radians(-90))
    anchor('TagPlastid', (loc[0], loc[1] - 0.25 * s, loc[2] + 1.02 * s))
    return c

# ================================================================= builders: intro
def intro_cell(nf, rfps, dur):
    reset(); stage(target=(0, 0, 0.2), key_e=2400, spot=50)
    cutaway_cell((0, 0, 0), 1.7, cut='wedge', nucleus='wedge')
    cam, tgt = camera((-2.0, -8.5, 3.0), (0.1, 0, 0.1), lens=50); orbit(cam, tgt, (0, 0, 0.1), 9.0, 3.0, -14, 12, 1, nf)

def intro_cork(nf, rfps, dur):
    reset(); stage(target=(0, 0, 1.0), key_e=2400, spot=50)
    ck = cork_prop((0, 0, 0), h=2.0); kf(ck, 'rotation_euler', 1, (0, 0, 0)); kf(ck, 'rotation_euler', nf, (0, 0, 0.6)); kf_lin(ck)
    cam, tgt = camera((0.5, -8.0, 2.6), (0, 0, 1.0), lens=50); dolly(cam, tgt, 1, nf, (0.5, -8.0, 2.6), (0.2, -7.2, 2.3))

def intro_comb(nf, rfps, dur):
    reset(); stage(target=(0, 0, 0.1), key_e=2200, spot=55)
    honeycomb((0, 0, 0), R=0.3, cols=18, rows=16, h=0.1, wall=0.045, disc=2.4, name='Comb')
    cam, tgt = camera((0.6, -8.0, 4.2), (0, 0, 0.0), lens=50); dolly(cam, tgt, 1, nf, (0.6, -8.0, 4.2), (-0.3, -7.2, 3.6))

# ================================================================= builders: Hooke and cork
def cork_stopper(nf, rfps, dur):
    reset(); stage(target=(0, 0, 1.0), key_e=2400, spot=50)
    ck = cork_prop((0, 0, 0), h=2.0)
    kf(ck, 'rotation_euler', 1, (0, 0, -0.3)); kf(ck, 'rotation_euler', nf, (0, 0, 0.5)); kf_lin(ck)
    cam, tgt = camera((0.4, -13.0, 3.5), (0, 0, 1.0), lens=50); dolly(cam, tgt, 1, nf, (0.4, -13.0, 3.5), (0.3, -7.0, 2.4))

def cork_slice(nf, rfps, dur):
    """Thin cork disc -> honeycomb walls grow out of it -> camera dives to the cells."""
    reset(); stage(target=(0, 0, 0.1), key_e=2300, spot=55)
    comb = honeycomb((0, 0, 0), R=0.32, cols=18, rows=16, h=0.12, wall=0.05, disc=2.5, name='Comb', floor_mat=mat_cork('slice_m', light=(0.95, 0.88, 0.72), dark=(0.82, 0.55, 0.25), scale=5.0, bump=0.35))
    w = comb['walls']; f0, f1 = F(2.0, rfps), F(4.0, rfps)
    kf(w, 'scale', 1, (1, 1, 0.001)); kf(w, 'scale', f0, (1, 1, 0.001)); kf(w, 'scale', f1, (1, 1, 1)); kf_ease(w)
    cam_path([(0.0, (0.0, -9.5, 5.5), (0, 0, 0.0)), (4.0, (0.0, -7.8, 4.6), (0, 0, 0.0)), (8.0, (0.2, -2.6, 1.9), (0.1, 0.4, 0.05)), (dur, (0.1, -1.8, 1.3), (0.1, 0.5, 0.05))], rfps, lens=45)

def hooke_microscope(nf, rfps, dur):
    reset(); stage(target=(0.5, 0, 1.6), key_e=2600, spot=55)
    sl = glass_slide((0, 0, 0), 'Slide'); microscope((0.9, 0, 0), s=1.0, slide=sl)
    ck = cork_prop((-1.9, -0.4, 0), h=1.1); ck.scale = (0.5, 0.5, 1)
    cam, tgt = camera((-0.8, -10.5, 3.4), (0.2, 0, 1.9), lens=50); dolly(cam, tgt, 1, nf, (-0.8, -10.5, 3.4), (0.0, -9.6, 3.2))

def honeycomb_cells(nf, rfps, dur):
    reset(); stage(target=(0, 0.5, 0.05), key=(2.5, -4.0, 6.0), key_e=2000, spot=70)
    honeycomb((0, 0, 0), R=0.5, cols=22, rows=16, h=0.2, wall=0.075, name='Comb')
    anchor('CombAnchor', (0.0, 0.4, 0.22))
    cam_path([(0.0, (-0.8, -4.2, 2.6), (0.0, 0.6, 0.0)), (dur, (0.9, -3.6, 2.3), (0.2, 1.0, 0.0))], rfps, lens=40)

# ================================================================= builders: onion experiment
def onion_whole(nf, rfps, dur):
    reset(); stage(target=(0, 0, 0.0), key_e=2200, spot=50)
    o = onion((0, 0, 0), r=1.0); kf(o, 'rotation_euler', 1, (0.1, 0, 0)); kf(o, 'rotation_euler', nf, (0.1, 0, 1.2)); kf_lin(o)
    cam, tgt = camera((0.2, -7.5, 1.6), (0, 0, 0.1), lens=55); dolly(cam, tgt, 1, nf, (0.2, -7.5, 1.6), (0.1, -6.8, 1.4))

def onion_cut(nf, rfps, dur):
    """Half onion showing its rings (66-70 s), then the layers slide apart into a row of cups (70-72 s)."""
    reset(); stage(target=(0, 0, 0.0), key_e=2200, spot=55)
    cups, cutter = onion_cups((0, 0, 0), r=1.0)
    f0, f1 = F(3.6, rfps), F(5.8, rfps)
    for i, c in enumerate(cups):
        kf(c, 'location', 1, (0, 0, 0)); kf(c, 'location', f0, (0, 0, 0)); kf(c, 'location', f1, (-2.6 + i * 1.05, 0.0, 0.0)); kf_ease(c)
    cam_path([(0.0, (0.3, -6.5, 1.8), (0, 0, 0.0)), (3.5, (0.2, -6.0, 1.6), (0, 0, 0.0)), (dur, (0.0, -8.5, 2.2), (-0.3, 0, 0.0))], rfps, lens=50)

def onion_layers(nf, rfps, dur):
    """One pale cup, then a second one lifts away (forceps in frame), then a flat scrap is peeled off."""
    reset(); stage(target=(0, 0, 0.2), key_e=2300, spot=55)
    cutter = cutter_box('CupCut', (0, -1.6 + EPS, 0), (6, 3.2, 4))
    cups, _ = onion_cups((0, 0, 0), r=0.9, radii=(0.86, 0.72), cutter=cutter, col0=2)
    c0, c1 = cups; c0.name = 'CupOuter'; c1.name = 'CupInner'
    f_a, f_b = F(3.5, rfps), F(6.0, rfps)
    hide_until(c1, F(3.0, rfps)); kf(c1, 'location', f_a, (0, 0, 0)); kf(c1, 'location', f_b, (0.9, 0.3, 1.3)); kf(c1, 'rotation_euler', f_a, (0, 0, 0)); kf(c1, 'rotation_euler', f_b, (0.3, 0.5, 0.2)); kf_ease(c1)
    pc = onion_piece((0.6, 0.2, 1.05), size=0.6, name='Piece', curl=True); pc.rotation_euler = (0.2, 0.15, 0.3)
    hide_until(pc, F(7.5, rfps)); kf(pc, 'location', F(7.5, rfps), (0.5, 0.2, 0.5)); kf(pc, 'location', F(9.5, rfps), (0.9, 0.1, 1.2)); kf(pc, 'location', nf, (1.1, 0.0, 1.35)); kf_ease(pc)
    hide_from(c1, F(8.0, rfps)); kf(c0, 'scale', F(9.0, rfps), (1, 1, 1)); kf(c0, 'scale', F(11.0, rfps), (0.001, 0.001, 0.001)); kf_ease(c0)
    fr, arms = forceps((0.9, 0.0, 3.4), L=2.2, open_ang=0.16); fr.rotation_euler = (0.25, 0.0, 0.0)
    hide_until(fr, F(6.8, rfps))
    for a in arms: hide_until(a, F(6.8, rfps))
    kf(fr, 'location', F(6.8, rfps), (0.9, -0.2, 4.6)); kf(fr, 'location', F(7.6, rfps), (0.55, 0.2, 2.6)); kf(fr, 'location', F(9.5, rfps), (0.95, 0.1, 3.3)); kf(fr, 'location', nf, (1.15, 0.0, 3.45)); kf_ease(fr)
    for s, a in zip((-1, 1), arms):
        kf(a, 'rotation_euler', F(6.8, rfps), (0, s * 0.16, 0)); kf(a, 'rotation_euler', F(7.6, rfps), (0, s * 0.03, 0)); kf_ease(a)
    cam_path([(0.0, (0.3, -6.0, 2.0), (0, 0, 0.3)), (6.0, (0.3, -6.2, 2.2), (0.3, 0, 0.5)), (dur, (0.6, -5.4, 2.6), (0.9, 0, 1.1))], rfps, lens=50)

def watch_glass_layer(nf, rfps, dur):
    reset(); stage(target=(0, 0, 0.2), key_e=2300, spot=55)
    wg = watch_glass_dark((0, 0, 0), r=1.4)
    pc = onion_piece((0, 0, 0.22), size=0.7, name='Piece', bend=0.08)
    kf(pc, 'location', 1, (0.3, -0.2, 2.4)); kf(pc, 'location', F(2.0, rfps), (0.3, -0.2, 2.4)); kf(pc, 'location', F(3.5, rfps), (0.05, 0.0, 0.2)); kf(pc, 'rotation_euler', 1, (0.4, 0.3, 0.2)); kf(pc, 'rotation_euler', F(3.5, rfps), (0, 0, 0.1)); kf_ease(pc)
    fr, arms = forceps((0.3, -0.2, 2.5), L=2.0, open_ang=0.05); fr.rotation_euler = (0.2, 0.1, 0.0)
    kf(fr, 'location', 1, (0.35, -0.3, 4.6)); kf(fr, 'location', F(2.0, rfps), (0.35, -0.3, 4.6)); kf(fr, 'location', F(3.0, rfps), (0.35, -0.3, 6.5)); kf_ease(fr)
    hide_from(fr, F(3.2, rfps))
    for a in arms: hide_from(a, F(3.2, rfps))
    cam_path([(0.0, (0.2, -6.5, 3.2), (0, 0, 0.3)), (dur, (0.5, -5.8, 3.4), (0, 0, 0.2))], rfps, lens=50)

def slide_water(nf, rfps, dur):
    reset(); stage(target=(0, 0, 0.2), key_e=2300, spot=60)
    wg = watch_glass_dark((0.4, 1.9, 0), r=1.1); onion_piece((0.45, 1.9, 0.18), size=0.55, name='Piece', bend=0.08)
    sl = glass_slide((0, -0.8, 0.035), 'Slide'); sl.rotation_euler = (0, 0, 0.35)
    kf(sl, 'location', 1, (-6.0, -0.8, 0.035)); kf(sl, 'location', F(0.5, rfps), (-6.0, -0.8, 0.035)); kf(sl, 'location', F(2.5, rfps), (0, -0.8, 0.035)); kf_ease(sl)
    dr = dropper((0.1, -0.7, 2.4), L=1.1); dr.rotation_euler = (0.35, 0.3, 0.0)
    kf(dr, 'location', 1, (2.5, -1.5, 5.0)); kf(dr, 'location', F(2.5, rfps), (2.5, -1.5, 5.0)); kf(dr, 'location', F(3.5, rfps), (0.1, -0.7, 2.4)); kf(dr, 'location', F(6.5, rfps), (0.1, -0.7, 2.4)); kf(dr, 'location', F(7.5, rfps), (2.5, -1.5, 5.0)); kf_ease(dr)
    drops(3, (0.1, -0.7, 2.3), (0.05, -0.75, 0.12), 3.8, 0.7, rfps, name='Drop')
    dp = sphere('Droplet', 0.16, (0.05, -0.75, 0.08), seg=48, ring=24, mat=mat_glassy((0.75, 0.9, 1.0), alpha=0.35, rough=0.05, name='drop_m'), scale=(1, 1, 0.45))
    kf(dp, 'scale', 1, (0.001, 0.001, 0.001)); kf(dp, 'scale', F(4.2, rfps), (0.001, 0.001, 0.001)); kf(dp, 'scale', F(6.0, rfps), (1.3, 1.3, 0.45)); kf_ease(dp)
    cam_path([(0.0, (0.3, -7.5, 4.2), (0.1, 0.4, 0.2)), (dur, (0.0, -6.6, 3.8), (0.0, 0.2, 0.1))], rfps, lens=50)

def forceps_transfer(nf, rfps, dur):
    """Forceps lift the onion scrap from the watch glass and lay it flat on the wet slide."""
    reset(); stage(target=(0, 0, 0.2), key_e=2300, spot=60)
    wg = watch_glass_dark((-1.3, 1.2, 0), r=1.1); sl = glass_slide((1.0, -0.6, 0.035), 'Slide'); sl.rotation_euler = (0, 0, 0.35)
    dp = sphere('Droplet', 0.18, (1.0, -0.6, 0.08), seg=48, ring=24, mat=mat_glassy((0.75, 0.9, 1.0), alpha=0.3, rough=0.05, name='drop_m'), scale=(1.3, 1.3, 0.4))
    pc = onion_piece((-1.25, 1.2, 0.18), size=0.55, name='Piece', bend=0.06)
    fa, fb, fc, fd = F(1.0, rfps), F(3.0, rfps), F(5.5, rfps), F(7.5, rfps)
    kf(pc, 'location', fb, (-1.25, 1.2, 0.18)); kf(pc, 'location', fc, (0.0, 0.3, 1.6)); kf(pc, 'location', fd, (1.0, -0.6, 0.11)); kf(pc, 'rotation_euler', fb, (0, 0, 0)); kf(pc, 'rotation_euler', fc, (0.4, 0.2, 0.3)); kf(pc, 'rotation_euler', fd, (0, 0, 0.35)); kf_ease(pc)
    fr, arms = forceps((-1.25, 1.2, 2.3), L=2.1, open_ang=0.18); fr.rotation_euler = (0.25, 0.0, 0.0)
    kf(fr, 'location', 1, (-1.4, 0.8, 5.0)); kf(fr, 'location', fa, (-1.4, 0.8, 5.0)); kf(fr, 'location', fb, (-1.25, 1.1, 2.35)); kf(fr, 'location', fc, (0.0, 0.2, 3.7)); kf(fr, 'location', fd, (1.0, -0.7, 2.3)); kf(fr, 'location', F(9.0, rfps), (1.2, -1.2, 4.5)); kf_ease(fr)
    for s, a in zip((-1, 1), arms):
        kf(a, 'rotation_euler', fa, (0, s * 0.18, 0)); kf(a, 'rotation_euler', fb, (0, s * 0.18, 0)); kf(a, 'rotation_euler', F(3.5, rfps), (0, s * 0.03, 0)); kf(a, 'rotation_euler', fd, (0, s * 0.03, 0)); kf(a, 'rotation_euler', F(8.2, rfps), (0, s * 0.18, 0)); kf_ease(a)
    cam_path([(0.0, (0.0, -7.0, 4.4), (0.0, 0.4, 0.3)), (dur, (0.6, -6.2, 3.6), (0.6, -0.2, 0.2))], rfps, lens=50)

def safranin(nf, rfps, dur):
    """Purple safranin drops from a dropper stain the scrap on the slide; the bottle sits top-left."""
    reset(); stage(target=(0, 0, 0.2), key_e=2300, spot=60)
    wg = watch_glass_dark((0.3, 1.6, 0), r=1.05); sl = glass_slide((0.4, -0.7, 0.035), 'Slide'); sl.rotation_euler = (0, 0, 0.1)
    pc = onion_piece((0.4, -0.7, 0.11), size=0.55, name='Piece', bend=0.05); pc.rotation_euler = (0, 0, 0.1)
    stain = sphere('Stain', 0.3, (0.4, -0.7, 0.13), seg=48, ring=24, mat=mat_translucent((0.6, 0.12, 0.55), alpha=0.75, rough=0.2, name='stain_m'), scale=(1.4, 1.0, 0.08))
    kf(stain, 'scale', 1, (0.001, 0.001, 0.001)); kf(stain, 'scale', F(2.8, rfps), (0.001, 0.001, 0.001)); kf(stain, 'scale', F(6.0, rfps), (1.4, 1.0, 0.08)); kf_ease(stain)
    bt = dropper_bottle((-3.6, 1.2, 0.0), h=1.2)
    dr = dropper((0.4, -0.7, 2.3), L=1.0); dr.rotation_euler = (0.3, 0.25, 0.0)
    kf(dr, 'location', 1, (-1.5, -0.4, 4.6)); kf(dr, 'location', F(0.8, rfps), (-1.5, -0.4, 4.6)); kf(dr, 'location', F(2.0, rfps), (0.4, -0.7, 2.3)); kf(dr, 'location', F(6.0, rfps), (0.4, -0.7, 2.3)); kf(dr, 'location', F(7.2, rfps), (-1.5, -0.4, 4.6)); kf_ease(dr)
    drops(4, (0.4, -0.7, 2.2), (0.4, -0.7, 0.15), 2.4, 0.8, rfps, name='SDrop', color=(0.7, 0.1, 0.6), alpha=0.85, r=0.06)
    cam_path([(0.0, (-0.2, -7.2, 4.0), (-0.3, 0.2, 0.3)), (dur, (0.2, -6.4, 3.6), (0.0, -0.1, 0.2))], rfps, lens=50)

def cover_slip(nf, rfps, dur):
    reset(); stage(target=(0, 0, 0.2), key_e=2300, spot=60)
    wg = watch_glass_dark((0.3, 1.6, 0), r=1.05); sl = glass_slide((0.4, -0.7, 0.035), 'Slide'); sl.rotation_euler = (0, 0, 0.1)
    pc = onion_piece((0.4, -0.7, 0.11), size=0.55, name='Piece', bend=0.05); setmat(pc, mat_organic((0.85, 0.5, 0.75), rough=0.35, sss=0.5, name='stained_m'))
    cs = cover_slip_obj((0.4, -0.7, 0.16), 'CoverSlip'); cs.rotation_euler = (0, 0, 0.1)
    kf(cs, 'location', 1, (0.4, -0.7, 2.6)); kf(cs, 'location', F(0.8, rfps), (0.4, -0.7, 2.6)); kf(cs, 'location', F(3.2, rfps), (0.4, -0.7, 0.16)); kf(cs, 'rotation_euler', 1, (0.5, 0, 0.1)); kf(cs, 'rotation_euler', F(3.2, rfps), (0, 0, 0.1)); kf_ease(cs)
    cam_path([(0.0, (0.2, -6.8, 3.8), (0.2, -0.2, 0.3)), (dur, (0.4, -5.6, 3.0), (0.4, -0.5, 0.15))], rfps, lens=50)

def microscope_slide(nf, rfps, dur):
    """The slide travels to the stage; the camera swings from three-quarter to the front view."""
    reset(); stage(target=(0, 0, 1.8), key_e=2600, spot=55)
    sl = glass_slide((0, 0, 0), 'Slide'); ms = microscope((0.3, 0, 0), s=1.0, slide=None)
    sl.scale = (1.0, 0.38, 0.03); sl.rotation_euler = (0, 0, 0.35)
    kf(sl, 'location', 1, (-3.2, -1.8, 0.05)); kf(sl, 'location', F(1.0, rfps), (-3.2, -1.8, 0.05)); kf(sl, 'location', F(4.5, rfps), (0.35, -0.05, 1.33)); kf(sl, 'rotation_euler', 1, (0, 0, 0.35)); kf(sl, 'rotation_euler', F(4.5, rfps), (0, 0, 0)); kf_ease(sl)
    cam_path([(0.0, (-4.6, -9.5, 3.6), (0.0, 0, 1.9)), (5.0, (-2.2, -9.8, 3.4), (0.2, 0, 2.0)), (dur, (0.3, -8.6, 3.6), (0.3, 0, 2.1))], rfps, lens=50)

def onion_tissue(nf, rfps, dur):
    """Pink scraps swarm in and settle into the epidermis sheet (136-141 s), then the sheet holds under a slow push."""
    reset(); stage(target=(0, 0, 0.0), key=(0.5, -3.0, 8.0), key_e=2200, spot=70, fill_e=200)
    ts = tissue_plane((0, 0, 0), size=(4.8, 2.8)); hide_until(ts, F(4.6, rfps))
    rnd = random.Random(5); fm = mat_organic((0.95, 0.6, 0.75), rough=0.4, sss=0.4, name='flake_m'); f1 = F(4.8, rfps)
    for i in range(140):
        gx, gy = rnd.uniform(-2.3, 2.3), rnd.uniform(-1.35, 1.35)
        fl = obj_add('ico_sphere', f'Flake{i}', radius=rnd.uniform(0.09, 0.16), subdivisions=1, location=(gx, gy, 0.02)); fl.scale = (1.3, 1, 0.12); setmat(fl, fm)
        p0 = (gx + rnd.uniform(-5, 5), gy + rnd.uniform(-3, 3), rnd.uniform(0.5, 4.0)); t0 = rnd.uniform(0.0, 2.0)
        kf(fl, 'location', 1, p0); kf(fl, 'location', F(t0, rfps), p0); kf(fl, 'location', F(t0 + 2.6, rfps), (gx, gy, 0.02)); kf(fl, 'rotation_euler', 1, (rnd.uniform(0, 3), rnd.uniform(0, 3), 0)); kf(fl, 'rotation_euler', F(t0 + 2.6, rfps), (0, 0, 0)); kf_ease(fl)
        hide_from(fl, f1)
    cam_path([(0.0, (0.0, -3.5, 6.5), (0, 0, 0)), (5.0, (0.0, -3.0, 6.0), (0, 0, 0)), (dur, (0.3, -2.2, 4.8), (0.2, 0.2, 0))], rfps, lens=45)

# ================================================================= builders: cell structure
def cutaway_cell_brief(nf, rfps, dur):
    reset(); stage(target=(0, 0, 0.2), key_e=2400, spot=50)
    cutaway_cell((0, 0, 0), 1.7, cut='wedge', nucleus='wedge')
    cam, tgt = camera((-1.2, -8.8, 3.2), (0.1, 0, 0.1), lens=50); dolly(cam, tgt, 1, nf, (-1.2, -8.8, 3.2), (-0.6, -8.4, 3.0))

def microscope_turn(nf, rfps, dur):
    reset(); stage(target=(0, 0, 1.8), key_e=2600, spot=55)
    sl = glass_slide((0, 0, 0), 'Slide'); microscope((0.0, 0, 0), s=1.0, slide=sl)
    honeycomb((0.0, -0.05, 1.37), R=0.03, cols=14, rows=10, h=0.01, wall=0.006, disc=0.16, name='SlideComb')
    cam_path([(0.0, (-3.0, -8.0, 3.4), (0, 0, 1.7)), (dur, (0.4, -6.8, 3.8), (0.1, 0, 2.0))], rfps, lens=50)

def honeycomb_dive(nf, rfps, dur):
    """Camera sinks from a cork close-up into the honeycomb cells and skims the floor texture."""
    reset(); stage(target=(0, 0.5, 0.05), key=(2.0, -3.0, 6.0), key_e=2000, spot=75, fill_e=220)
    honeycomb((0, 0, 0), R=0.5, cols=22, rows=16, h=0.2, wall=0.075, name='Comb')
    cam_path([(0.0, (0.0, -0.4, 0.55), (0.2, 0.9, 0.0)), (2.5, (0.2, -3.5, 2.8), (0.4, 0.6, 0.0)), (5.0, (0.6, -1.2, 0.55), (0.9, 0.3, 0.0)), (dur, (0.9, -0.5, 0.3), (1.1, 0.2, 0.0))], rfps, lens=35)

def cell_grid(nf, rfps, dur):
    reset(); stage(target=(0, 0, 0.0), key=(3.0, -4.0, 8.0), key_e=2600, spot=70)
    b = bean('GridCell', 0.5, (0, 0, 0), mat_membrane('grid_mem'), seg=48, ring=24); subsurf(b, 1, 1)
    for ax, nm in ((0, 'ax'), (1, 'ay')):
        arr = b.modifiers.new(nm, 'ARRAY'); arr.count = 11 if ax == 0 else 8; arr.use_relative_offset = True; arr.relative_offset_displace = (1.06, 0, 0) if ax == 0 else (0, 1.06, 0)
    b.location = (-5.5, -3.5, 0)
    cam_path([(0.0, (0.0, -2.5, 3.6), (0.0, 0.8, 0.0)), (dur, (0.8, -3.6, 4.8), (0.6, 0.6, 0.0))], rfps, lens=40)

def cutaway_cell_labels(nf, rfps, dur):
    """Whole cell, the wedge opens (178-180), slow turn while the three labels point at membrane / nucleus /
    cytoplasm, then the wedge closes again (202-204)."""
    reset(); stage(target=(0, 0, 0.2), key_e=2400, spot=50)
    c = cutaway_cell((0, 0, 0), 1.7, cut='wedge', nucleus='wedge', open_from=0.5, open_to=2.8, rfps=rfps, close_from=24.0, close_to=26.2)
    anchor('MembraneAnchor', (-0.2, -0.8, 1.45)); anchor('NucleusAnchor', (0.05, 0.05, 0.25)); anchor('CytoAnchor', (0.9, -0.9, 0.1))
    cam_path([(0.0, (0.0, -9.0, 2.6), (0.1, 0, 0.1)), (10.0, (-1.4, -8.6, 3.2), (0.1, 0, 0.1)), (20.0, (0.6, -8.2, 3.0), (0.1, 0, 0.1)), (dur, (0.0, -9.0, 2.6), (0.1, 0, 0.1))], rfps, lens=50)

def cell_whole_open(nf, rfps, dur):
    reset(); stage(target=(0, 0, 0.2), key_e=2400, spot=50)
    c = cutaway_cell((0, 0, 0), 1.7, cut='wedge', nucleus='wedge', open_from=4.0, open_to=6.2, rfps=rfps)
    anchor('MembraneAnchor', (-0.5, -0.9, 1.35))
    cam_path([(0.0, (0.5, -9.5, 2.4), (0.1, 0, 0.1)), (dur, (-0.6, -8.6, 3.0), (0.1, 0, 0.1))], rfps, lens=50)

def cell_in_env(nf, rfps, dur):
    reset(); stage(target=(0, 0, 0.2), key_e=2400, spot=50, env=0.25)
    cutaway_cell((0, 0, 0), 1.5, cut='wedge', nucleus='wedge'); env_sphere((0, 0, 0), r=4.6)
    cam_path([(0.0, (-0.8, -10.5, 2.8), (0.0, 0, 0.1)), (dur, (0.8, -9.6, 3.2), (0.0, 0, 0.1))], rfps, lens=45)

def cell_whole_rect(nf, rfps, dur):
    reset(); stage(target=(0, 0, 0.2), key_e=2400, spot=50)
    cutaway_cell((0, 0, 0), 1.7, cut=None, nucleus=None)
    cam_path([(0.0, (0.3, -8.5, 2.2), (0.1, 0, 0.1)), (dur, (-0.4, -7.8, 2.6), (0.1, 0, 0.1))], rfps, lens=50)

def _membrane_cell():
    """The translucent red cell used for diffusion/osmosis (bean, fresnel rim)."""
    c = bean('RedCell', 1.6, (0, 0, 0), mat_rim((0.7, 0.2, 0.22), (1.0, 0.55, 0.5), a_center=0.55, a_rim=0.95, emit=1.1, name='redcell_m', blend=0.3, rough=0.3), seg=96, ring=48, egg=0.1, squash=(1.0, 0.85, 1.15))
    subsurf(c, 1, 1)
    try: c.visible_shadow = False
    except Exception: pass
    return c

def diffusion(nf, rfps, dur):
    reset(); stage(target=(0, 0, 0.0), key_e=2000, spot=60, env=0.2)
    _membrane_cell(); env_sphere((0, 0, 0), r=5.0)
    molecules('Rp', 11, 1.6, 21, rfps, nf, 6.5, 8.0, 17.0, r=0.1, color=(0.9, 0.95, 0.9))      # CO2
    molecules('Op', 10, 1.6, 22, rfps, nf, 7.0, 8.5, 17.5, r=0.1, color=(0.85, 0.9, 1.0))      # O2
    cam_path([(0.0, (0.3, -10.5, 1.6), (0, 0, 0.0)), (dur, (-0.3, -9.8, 2.0), (0, 0, 0.0))], rfps, lens=45)

def osmosis(nf, rfps, dur):
    reset(); stage(target=(0, 0, 0.0), key_e=2000, spot=60, env=0.2)
    _membrane_cell(); env_sphere((0, 0, 0), r=5.0)
    molecules('Hp', 22, 1.6, 23, rfps, nf, 2.0, 4.0, 26.0, r=0.1, color=(0.4, 0.55, 1.0), inside_frac=0.8)
    cam_path([(0.0, (-0.3, -10.0, 1.8), (0, 0, 0.0)), (16.0, (0.4, -9.4, 2.0), (0, 0, 0.0)), (dur, (0.0, -10.2, 1.6), (0, 0, 0.0))], rfps, lens=45)

def cell_flexible(nf, rfps, dur):
    """Whole cell, gently wobbling (flexible), then the camera pulls far back."""
    reset(); stage(target=(0, 0, 0.2), key_e=2400, spot=50)
    c = cutaway_cell((0, 0, 0), 1.7, cut=None, nucleus=None); mem, cyt = c['membrane'], c['cyto']
    for o in (mem, cyt):
        for i, t in enumerate([0, 2, 4, 6, 8]):
            s = 1 + 0.06 * (1 if i % 2 else -1)
            kf(o, 'scale', F(t, rfps), (s, 1 / s, 1.0))
        kf_ease(o)
    cam_path([(0.0, (0.3, -8.5, 2.2), (0.1, 0, 0.1)), (7.5, (0.0, -8.8, 2.4), (0.1, 0, 0.1)), (dur, (0.0, -24.0, 5.0), (0.1, 0, 0.1))], rfps, lens=50)

def lipid_bilayer(nf, rfps, dur):
    reset(); stage(target=(0, 0, 0.3), key=(2.0, -4.0, 7.0), key_e=2400, spot=65)
    lipid_prop((0, 0, 0))
    cam_path([(0.0, (-1.5, -6.5, 3.6), (0, 0, 0.3)), (dur, (1.2, -5.8, 3.2), (0, 0, 0.3))], rfps, lens=45)

def electron_microscope(nf, rfps, dur):
    """Cork disc specimen (300-301.5), then the camera rises up the EM column's blue bore (302-304)."""
    reset(); stage(target=(0, 0, 0.5), key_e=2200, spot=55)
    disc = obj_add('cylinder', 'Specimen', radius=1.2, depth=0.1, vertices=128, location=(0, 0, 0.2)); setmat(disc, mat_cork('spec_m', light=(0.95, 0.75, 0.42), dark=(0.7, 0.42, 0.18), scale=8.0)); smooth(disc); bevel(disc, 0.02, 3)
    kf(disc, 'rotation_euler', 1, (0, 0, 0)); kf(disc, 'rotation_euler', nf, (0, 0, 0.9)); kf_lin(disc)
    root, ztop = em_column((0, 0, -0.1), s=1.2)
    cam_path([(0.0, (0.6, -6.0, 2.6), (0, 0, 0.3)), (1.5, (0.3, -5.6, 2.6), (0, 0, 0.3)), (2.2, (0.0, 0.0, ztop + 4.0), (0, 0, ztop - 4.0)), (dur, (0.0, -0.3, ztop + 3.2), (0, 0, ztop - 3.0))], rfps, lens=40)
    light('POINT', (0, 0, ztop + 2.5), 300, (0.5, 0.7, 1.0), 'TopGlow')

# ================================================================= extra helpers for the organelle / nucleus section
def dna_helix(name, loc, length=2.0, radius=0.12, turns=5, r_tube=0.018, mat=None, mat2=None, rungs=True, axis='x', rot=(0, 0, 0), n=160):
    """Double helix: two bevelled NURBS strands half a turn apart plus rung tubes between them (one mesh)."""
    root = empty(name, loc); root.rotation_euler = rot
    m1 = mat or mat_organic((0.25, 0.55, 0.98), rough=0.3, coat=0.4, name=name + '_a'); m2 = mat2 or mat_organic((0.45, 0.75, 1.0), rough=0.3, coat=0.4, name=name + '_b')
    a = helix_pts(length, radius, turns, n=n, axis=axis, phase=0.0); b = helix_pts(length, radius, turns, n=n, axis=axis, phase=math.pi)
    ca = curve_obj(name + 'A', a, r_tube, m1, res=8); cb = curve_obj(name + 'B', b, r_tube, m2, res=8); parent(ca, root); parent(cb, root)
    if rungs:
        segs = [(a[i], b[i]) for i in range(0, n + 1, max(1, n // (turns * 5)))]
        rg = tubes_mesh(name + 'Rungs', segs, r_tube * 0.55, mat_organic((0.85, 0.9, 1.0), rough=0.4, name=name + '_r'), sides=6); parent(rg, root)
    return root

def mini_mito(loc, L=0.7, rot=0.0, name='MiniMito', seed=1):
    """The small red mitochondrion with a cream folded crista used in the closing cytoplasm cell."""
    root = empty(name, loc); root.rotation_euler = (0, 0, rot); R = 0.27 * L
    body = capsule(name + 'Body', R, L - 2 * R, mat=mat_organic((0.85, 0.12, 0.08), rough=0.35, sss=0.3, coat=0.4, name=name + '_m', radius=(1.0, 0.2, 0.1)), zscale=0.7); subsurf(body, 1, 1); parent(body, root)
    pts = [(-L * 0.36 + L * 0.72 * u, 0.42 * R * math.sin(2 * math.pi * 3.0 * u), 0.72 * R * 0.98) for u in [k / 40 for k in range(41)]]
    c = curve_obj(name + 'Crista', pts, 0.055 * R, mat_organic((0.95, 0.93, 0.8), rough=0.45, name=name + '_c'), res=6); parent(c, root)
    return root

def rim_cell(name, r, loc=(0, 0, 0), color=(0.02, 0.12, 0.3), rim=(0.15, 0.6, 1.0), a_center=0.35, a_rim=0.95, emit=1.6, egg=0.12, squash=(1.0, 0.9, 1.1)):
    """Translucent fresnel-rimmed bean (the division / dark cells)."""
    o = bean(name, r, loc, mat_rim(color, rim, a_center=a_center, a_rim=a_rim, emit=emit, name=name + '_m', blend=0.25, rough=0.5), seg=96, ring=48, egg=egg, squash=squash); subsurf(o, 1, 1)
    try: o.visible_shadow = False
    except Exception: pass
    return o

# ================================================================= builders: 3. cell organelles
def organelle_overview(nf, rfps, dur):
    """Cutaway cell full of organelles at left, the lone plastid at right; the camera settles on the cell (306-320)."""
    interior_set(nf, rfps, plastid=True)
    cam_path([(0.0, (4.5, -27.0, 8.0), (4.0, -0.5, 1.6)), (6.0, (3.0, -24.5, 7.4), (3.0, -0.5, 1.6)), (dur, (0.5, -19.0, 6.2), (0.2, -0.8, 1.4))], rfps, lens=45)

def interior_tour(nf, rfps, dur):
    """Slow 40 s glide among the organelles: ER + Golgi, then the lysosome / mitochondria group, back out (320-360)."""
    interior_set(nf, rfps)
    cam_path([(0.0, (0.3, -17.5, 5.8), (0.0, -1.2, 1.3)), (9.0, (-0.4, -11.5, 3.8), (0.0, -1.4, 1.1)), (20.0, (1.4, -7.6, 2.8), (0.8, -1.8, 0.9)),
              (30.0, (-1.6, -6.9, 2.5), (-0.6, -2.0, 0.8)), (dur, (-0.4, -9.5, 3.2), (0.0, -1.6, 1.0))], rfps, lens=45)

def interior_overview(nf, rfps, dur):
    interior_set(nf, rfps)
    cam_path([(0.0, (0.8, -18.0, 6.0), (0.2, -1.0, 1.4)), (dur, (0.4, -16.8, 5.6), (0.2, -1.0, 1.4))], rfps, lens=45)

def er_close(nf, rfps, dur):
    """Rough ER lobes with ribosomes and the orange smooth-ER trumpets, seen from the front (364-372)."""
    interior_set(nf, rfps); ex, ey, ez = INTERIOR['er']
    cam_path([(0.0, (ex + 0.5, ey - 8.6, ez + 3.4), (ex, ey, ez + 0.8)), (dur, (ex - 0.3, ey - 7.0, ez + 2.8), (ex - 0.2, ey + 0.1, ez + 0.75))], rfps, lens=45)

def golgi_close(nf, rfps, dur):
    interior_set(nf, rfps); gx, gy, gz = INTERIOR['golgi']
    cam_path([(0.0, (gx - 1.0, gy - 6.6, gz + 2.8), (gx, gy, gz + 0.8)), (dur, (gx - 0.4, gy - 5.6, gz + 2.4), (gx, gy, gz + 0.8))], rfps, lens=45)

def lysosome_close(nf, rfps, dur):
    """The front lysosome between the ER (left) and the Golgi (right), a mitochondrion below right (376-382)."""
    interior_set(nf, rfps); lx, ly, lz = INTERIOR['lyso1']
    cam_path([(0.0, (lx - 0.3, ly - 6.0, lz + 2.5), (lx, ly + 0.4, lz + 0.5)), (dur, (lx + 0.1, ly - 5.0, lz + 2.1), (lx, ly + 0.4, lz + 0.45))], rfps, lens=45)

def mito_close(nf, rfps, dur):
    """Low camera on the left mitochondrion, the ER rising behind it (382-390)."""
    interior_set(nf, rfps); mx, my, mz = INTERIOR['mito0']
    cam_path([(0.0, (mx + 1.6, my - 6.2, mz + 2.4), (mx, my, mz + 0.4)), (dur, (mx + 0.8, my - 5.0, mz + 1.9), (mx, my, mz + 0.4))], rfps, lens=45)

def chloroplast_solo(nf, rfps, dur):
    """One big plastid on black, opened on top so the grana stacks show; slow orbit (390-398)."""
    reset(); stage(target=(0, 0, 0.6), key=(3.0, -5.0, 8.0), key_e=2600, spot=55, fill_e=200)
    c = chloroplast((0, 0, 0), s=2.2, name='Plastid', grana=13, seed=6); c['root'].rotation_euler = (0, math.radians(52), math.radians(-58)); c['root'].location = (0, 0, 0.6)
    anchor('TagPlastid', (-0.3, -0.9, 3.0))
    cam, tgt = camera((-1.5, -12.0, 4.6), (0, 0, 0.5), lens=50); orbit(cam, tgt, (0, 0, 0.5), 12.5, 4.6, -20, 8, 1, nf)

def two_cells(nf, rfps, dur):
    """The organelle cell (tags) beside the plastid, both in frame, slow push (398-408)."""
    interior_set(nf, rfps, plastid=True)
    cam_path([(0.0, (5.2, -30.0, 8.5), (5.0, -0.5, 1.8)), (dur, (5.0, -27.0, 8.0), (5.0, -0.5, 1.8))], rfps, lens=45)

def interior_overview2(nf, rfps, dur):
    interior_set(nf, rfps)
    cam_path([(0.0, (-2.5, -17.0, 6.4), (-0.3, -1.0, 1.3)), (dur, (-2.0, -15.5, 6.0), (-0.3, -1.0, 1.3))], rfps, lens=45)

def er_zoom(nf, rfps, dur):
    """From the overview down into the ER: the pink lobes fill the frame, then the orange trumpets (412-436)."""
    interior_set(nf, rfps); ex, ey, ez = INTERIOR['er']
    cam_path([(0.0, (-2.0, -15.5, 6.0), (-0.3, -1.0, 1.3)), (8.0, (ex - 0.2, ey - 10.0, ez + 4.0), (ex, ey, ez + 0.9)),
              (16.0, (ex + 0.5, ey - 6.6, ez + 2.6), (ex, ey + 0.1, ez + 0.8)), (dur, (ex - 1.3, ey - 5.2, ez + 1.9), (ex - 0.4, ey + 0.1, ez + 0.75))], rfps, lens=45)

def er_rough_smooth(nf, rfps, dur):
    """44 s at the ER: smooth trumpets left, rough lobes with ribosomes right, drift across, end on the trumpets (436-480)."""
    interior_set(nf, rfps); ex, ey, ez = INTERIOR['er']
    cam_path([(0.0, (ex - 1.8, ey - 5.2, ez + 2.0), (ex - 0.4, ey + 0.1, ez + 0.8)), (14.0, (ex - 0.9, ey - 4.6, ez + 1.7), (ex - 0.1, ey + 0.2, ez + 0.75)),
              (26.0, (ex + 1.4, ey - 4.4, ez + 1.7), (ex + 0.7, ey + 0.2, ez + 0.75)), (36.0, (ex - 0.6, ey - 4.7, ez + 1.8), (ex - 0.3, ey + 0.1, ez + 0.75)),
              (dur, (ex - 2.0, ey - 4.3, ez + 1.6), (ex - 0.9, ey + 0.0, ez + 0.9))], rfps, lens=45)

def golgi_intro(nf, rfps, dur):
    """The Golgi stack from the front-left, ER at the left edge, nucleus behind (480-492)."""
    interior_set(nf, rfps); gx, gy, gz = INTERIOR['golgi']
    cam_path([(0.0, (gx - 2.2, gy - 7.8, gz + 3.0), (gx, gy, gz + 0.85)), (dur, (gx - 1.2, gy - 6.4, gz + 2.6), (gx, gy, gz + 0.85))], rfps, lens=45)

def golgi_network(nf, rfps, dur):
    """Close orbit around the cisternae and their budding vesicles, the green net to the ER visible (492-524)."""
    interior_set(nf, rfps); gx, gy, gz = INTERIOR['golgi']
    cam_path([(0.0, (gx - 1.7, gy - 5.4, gz + 2.3), (gx, gy, gz + 0.9)), (12.0, (gx + 0.6, gy - 5.0, gz + 1.9), (gx, gy, gz + 0.9)),
              (22.0, (gx + 2.4, gy - 4.3, gz + 1.5), (gx, gy, gz + 0.9)), (dur, (gx + 1.4, gy - 4.7, gz + 1.8), (gx - 0.1, gy, gz + 0.85))], rfps, lens=45)

def golgi_functions(nf, rfps, dur):
    """Very close along the cisternae (the functions list sits over the stack), then pulls back to Golgi + ER (524-548)."""
    interior_set(nf, rfps); gx, gy, gz = INTERIOR['golgi']
    cam_path([(0.0, (gx - 0.9, gy - 4.1, gz + 1.5), (gx, gy, gz + 0.7)), (12.0, (gx - 0.3, gy - 3.9, gz + 1.4), (gx + 0.1, gy, gz + 0.7)),
              (18.0, (gx - 1.4, gy - 6.6, gz + 2.5), (gx - 0.3, gy, gz + 0.8)), (dur, (gx - 1.8, gy - 8.2, gz + 3.1), (gx - 0.6, gy, gz + 0.9))], rfps, lens=45)

def lysosomes(nf, rfps, dur):
    """Front lysosome centred (ER top-left, Golgi top-right, mitochondrion bottom-right), settling in; static after 30 s (548-588)."""
    interior_set(nf, rfps); lx, ly, lz = INTERIOR['lyso1']
    cam_path([(0.0, (lx - 0.4, ly - 6.4, lz + 2.6), (lx, ly + 0.4, lz + 0.5)), (12.0, (lx, ly - 5.2, lz + 2.1), (lx, ly + 0.4, lz + 0.45)),
              (30.0, (lx + 0.1, ly - 4.8, lz + 1.9), (lx, ly + 0.4, lz + 0.45)), (dur, (lx + 0.1, ly - 4.8, lz + 1.9), (lx, ly + 0.4, lz + 0.45))], rfps, lens=45)

def interior_to_mito(nf, rfps, dur):
    """Overview of the cell again, then the camera drops to the left mitochondrion (588-600)."""
    interior_set(nf, rfps); mx, my, mz = INTERIOR['mito0']
    cam_path([(0.0, (0.3, -17.0, 5.8), (0.0, -1.2, 1.3)), (5.5, (-2.0, -10.5, 3.6), (-1.8, -1.6, 0.9)), (dur, (mx + 1.2, my - 5.4, mz + 2.0), (mx, my, mz + 0.4))], rfps, lens=45)

def _mito_hero(detail=2, L=6.0):
    reset(); stage(target=(0, 0, 0.4), key=(3.0, -5.0, 9.0), key_e=2800, spot=60, fill_e=220, rim_e=300)
    m = mitochondrion((0, 0, 0), L=L, name='Mito', cut=True, detail=detail, rot=0.0, seed=5, tilt=0.0)
    R = 0.25 * L
    anchor('TagFold', (-0.6, 0.45 * R, 0.45 * R)); anchor('TagATP', (0.9, -0.2 * R, 0.45 * R)); anchor('TagMito', (0.0, -0.3 * R, 0.95 * R))
    anchor('TagDNA', (-0.18 * L, 0.75 * R, 0.2 * R)); anchor('TagRibo', (0.25 * L, -0.6 * R, 0.3 * R))
    return m, R

def mito_solo(nf, rfps, dur):
    """One mitochondrion on black, cut open on top: folded green cristae, ATP beads; slow orbit (600-624)."""
    m, R = _mito_hero(detail=2)
    cam, tgt = camera((-2.0, -9.5, 4.0), (0, 0, 0.3), lens=50); orbit(cam, tgt, (0, 0, 0.3), 10.0, 4.0, -26, 10, 1, nf)

def mito_cristae(nf, rfps, dur):
    """Inside the fold: the camera skims along the cristae wall past ATP beads and DNA, then pulls back (624-644)."""
    m, R = _mito_hero(detail=2)
    cam_path([(0.0, (-2.4, -1.9, 0.9), (-0.9, 0.3, 0.35)), (10.0, (0.4, -1.7, 0.8), (1.2, 0.35, 0.35)), (14.0, (1.2, -2.6, 1.1), (0.9, 0.2, 0.3)), (dur, (0.3, -9.0, 3.8), (0.0, 0.0, 0.3))], rfps, lens=40)

def mito_dna(nf, rfps, dur):
    """Close on the DNA helix and ribosome dots between the folds, then out to the whole mitochondrion (644-664)."""
    m, R = _mito_hero(detail=2)
    cam_path([(0.0, (-0.4, -3.2, 1.5), (-0.9, 0.5, 0.3)), (9.0, (-0.9, -2.4, 1.05), (-1.0, 0.7, 0.25)), (13.0, (0.2, -3.0, 1.4), (0.4, 0.2, 0.3)), (dur, (0.6, -9.2, 3.9), (0.0, 0.0, 0.3))], rfps, lens=40)

def plastid_cells(nf, rfps, dur):
    """Two translucent cells: brown one full of chloroplasts, grey one with starch grains (664-680)."""
    reset(); stage(target=(0, 0, 0), key=(2.0, -6.0, 9.0), key_e=2600, spot=70, fill_e=220, env=0.3)
    chloroplast_cell((-2.7, 0, 0), r=2.0, name='Chromo', n=6); leucoplast_cell((2.7, 0, 0), r=1.85, name='Leuco', starch=4)
    cam_path([(0.0, (0.0, -12.5, 1.4), (0, 0, 0.0)), (dur, (0.1, -11.3, 1.2), (0, 0, 0.0))], rfps, lens=45)

def chloroplast_zoom(nf, rfps, dur):
    """Into the brown cell: the chloroplasts fill the frame, ending on one plastid's grana stacks (680-700)."""
    reset(); stage(target=(0, 0, 0), key=(2.0, -6.0, 9.0), key_e=2600, spot=70, fill_e=240, env=0.3)
    c = chloroplast_cell((0, 0, 0), r=2.6, name='Chromo', n=6, seed=8); px, py, pz = c['positions'][0]
    cam_path([(0.0, (-0.3, -12.0, 1.4), (0, 0, 0)), (8.0, (-0.2, -6.2, 0.9), (0.1, 0, 0.1)), (15.0, (px * 0.5, py - 3.4, pz + 0.9), (px, py, pz)), (dur, (px * 0.7, py - 2.1, pz + 0.75), (px, py, pz))], rfps, lens=45)

def leucoplast_zoom(nf, rfps, dur):
    reset(); stage(target=(0, 0, 0), key=(2.0, -6.0, 9.0), key_e=2400, spot=70, fill_e=220, env=0.3)
    leucoplast_cell((0, 0, 0), r=2.2, name='Leuco', starch=4)
    cam_path([(0.0, (0.2, -8.6, 1.1), (0, 0, 0)), (dur, (0.1, -7.4, 1.0), (0, 0, 0))], rfps, lens=45)

# ================================================================= builders: 4. nucleus and cytoplasm
def _big_cell(r=6.0, nucleus_rn=1.4, chromatin=0, pores=0, nuc_cut='wedge'):
    reset(); world(0.0025, 0.004, 0.009); hdri(strength=0.3, rotation=1.3); atmosphere(density=0.002)
    cutaway_cell((0, 0, 0), r, cut='wedge', nucleus=None, name='Cell', thick=0.06, interior='interior', seg=128)
    n = nucleus_organelle((-0.3, -1.35 * nucleus_rn, 1.05 * nucleus_rn), rn=nucleus_rn, name='Nuc', cut=nuc_cut, pores=pores, chromatin=chromatin)
    light('SPOT', (3.5, -7.0, 11.0), 3200, (1.0, 0.95, 0.87), 'Key', spot=60, blend=0.85, target=(0, -1.5, 0.5))
    soft_light((-6.0, -8.0, 4.0), 260, size=6, name='Fill', target=(0, -1.5, 0.5)); soft_light((2.0, -2.5, 6.5), 160, size=5, color=(0.8, 0.9, 1.0), name='Top', target=(0, -2.0, 0))
    light('AREA', (4.0, -5.5, 2.0), 120, (0.75, 0.85, 1.0), 'Rim', size=3, target=(-1, -1.5, 0.8))
    return n

def nucleus_in_cell(nf, rfps, dur):
    """The big cutaway cell with only its nucleus; the camera pushes in until the nucleus fills the frame (710.5-732)."""
    _big_cell(); anchor('TagNucleus', (-0.3, -2.3, 3.2))
    cam_path([(0.0, (0.5, -21.0, 7.0), (0.0, -0.5, 1.5)), (8.0, (-1.2, -14.5, 4.8), (-0.3, -1.0, 1.4)), (16.0, (-1.0, -8.6, 3.0), (-0.3, -1.9, 1.4)), (dur, (-0.8, -7.6, 2.7), (-0.3, -1.9, 1.4))], rfps, lens=45)

def pro_vs_eu(nf, rfps, dur):
    """Two cutaway cells: nucleus without membrane (left) and with the purple nuclear membrane (right) (732-748)."""
    reset(); world(0.0025, 0.004, 0.009); hdri(strength=0.3, rotation=1.3); atmosphere(density=0.002)
    for sx, nm, mem in ((-3.9, 'L', False), (3.9, 'R', True)):
        cutaway_cell((sx, 0, 0), 3.4, cut='wedge', nucleus=None, name='Cell' + nm, thick=0.07, interior='interior', seg=128)
        nucleus_organelle((sx - 0.1, -1.3, 1.0), rn=0.95, name='Nuc' + nm, cut='wedge', pores=0, chromatin=0, membrane=mem, seed=3)
        anchor('TagPro' if not mem else 'TagEu', (sx - 0.1, -1.4, 2.05))
    light('SPOT', (2.5, -8.0, 11.0), 3400, (1.0, 0.95, 0.87), 'Key', spot=70, blend=0.85, target=(0, -1.0, 0.5))
    soft_light((-7.0, -8.0, 4.0), 300, size=7, name='Fill', target=(0, -1.0, 0.5)); soft_light((0.0, -3.0, 7.0), 200, size=6, color=(0.8, 0.9, 1.0), name='Top', target=(0, -1.5, 0))
    cam_path([(0.0, (0.0, -16.5, 4.6), (0, -0.2, 0.9)), (dur, (0.0, -15.2, 4.3), (0, -0.2, 0.9))], rfps, lens=45)

def cell_whole_short(nf, rfps, dur):
    reset(); stage(target=(0, 0, 0.2), key_e=2400, spot=50)
    cutaway_cell((0, 0, 0), 1.7, cut=None, nucleus=None)
    cam_path([(0.0, (0.6, -9.0, 2.2), (0.1, 0, 0.1)), (dur, (0.2, -8.4, 2.4), (0.1, 0, 0.1))], rfps, lens=50)

def _nucleus_hero(rn=2.3, pores=64, chromatin=10, open_from=None, open_to=None, rfps=12):
    reset(); stage(target=(0, 0, 0), key=(2.5, -5.0, 8.5), key_e=2600, spot=60, fill_e=220, rim_e=320)
    n = nucleus_organelle((0, 0, 0), rn=rn, name='Nuc', cut='wedge', pores=pores, chromatin=chromatin, seed=4)
    if open_from is not None:
        cu = n['cutter']; base = tuple(cu.location); far = (base[0], base[1] - 3.2 * rn, base[2] + 0.6 * rn)
        kf(cu, 'location', 1, far); kf(cu, 'location', F(open_from, rfps), far); kf(cu, 'location', F(open_to, rfps), base); kf_ease(cu)
    anchor('TagNucMem', (-0.95 * rn, -0.15 * rn, 0.55 * rn)); anchor('TagPores', (0.72 * rn, -0.62 * rn, 0.18 * rn))
    anchor('TagChrom', (0.35 * rn, -0.45 * rn, 0.06 * rn))
    return n

def nucleus_pores(nf, rfps, dur):
    """A small whole nucleus dotted with pores, the camera pushes in while the wedge opens to show the inside (752-770)."""
    _nucleus_hero(open_from=4.0, open_to=7.0, rfps=rfps)
    cam_path([(0.0, (0.5, -19.0, 2.4), (0, 0, 0)), (7.0, (-0.9, -10.0, 2.2), (0, 0, 0.1)), (dur, (-1.3, -8.4, 2.0), (0, 0, 0.1))], rfps, lens=45)

def chromosomes_dna(nf, rfps, dur):
    """The open nucleus with its beaded chromatin threads; the camera dives to a thread and a DNA double helix (770-792)."""
    n = _nucleus_hero()
    dna_helix('DNA', (0.55, -1.15, 0.12), length=1.5, radius=0.09, turns=5, r_tube=0.014, rot=(0, 0, 0.5)); anchor('TagDNA', (0.55, -1.15, 0.32))
    cam_path([(0.0, (-1.3, -8.6, 2.0), (0, 0, 0.1)), (8.0, (0.6, -7.0, 1.4), (0.2, -0.3, 0.0)), (16.0, (0.9, -3.3, 0.7), (0.55, -1.1, 0.1)), (dur, (0.7, -2.6, 0.55), (0.55, -1.15, 0.1))], rfps, lens=45)

def cell_division(nf, rfps, dur):
    """A translucent blue cell wobbles, pinches into two, then a cluster of five daughter cells with lilac nuclei (792-806)."""
    reset(); stage(target=(0, 0, 0), key=(2.0, -5.0, 8.0), key_e=2200, spot=65, fill_e=200, env=0.25)
    nuc_m = mat_organic((0.62, 0.5, 0.9), rough=0.35, sss=0.3, coat=0.3, name='dnuc')
    layout = [(0, 0, 0), (-2.4, 0.3, 0.1), (0.1, 0.4, 2.35), (2.4, 0.2, 0.3), (0.5, -0.2, -2.3)]
    t_split = [0.0, 3.0, 5.0, 6.5, 8.0]
    for i, (px, py, pz) in enumerate(layout):
        c = rim_cell(f'DCell{i}', 1.15, (0, 0, 0)); nu = sphere(f'DNuc{i}', 0.22, (0, 0, 0), seg=48, ring=24, mat=nuc_m); parent(nu, c)
        f0 = F(t_split[i], rfps); f1 = F(t_split[i] + 2.6, rfps)
        if i == 0:
            for k, t in enumerate([0, 0.9, 1.8, 2.7, 3.6]):
                sc = 1 + 0.07 * (1 if k % 2 else -1); kf(c, 'scale', F(t, rfps), (sc, 1 / sc, 1.0))
            kf(c, 'scale', F(5.0, rfps), (1, 1, 1))
        else:
            kf(c, 'scale', 1, (0.001, 0.001, 0.001)); kf(c, 'scale', f0, (0.001, 0.001, 0.001)); kf(c, 'scale', f1, (1, 1, 1))
        kf(c, 'location', 1, (0, 0, 0)); kf(c, 'location', f0, (0, 0, 0)); kf(c, 'location', f1, (px, py, pz)); kf(c, 'location', nf, (px * 1.03, py, pz * 1.03)); kf_ease(c)
    cam_path([(0.0, (0.0, -12.0, 0.8), (0, 0, 0)), (dur, (0.4, -13.5, 1.2), (0, 0, 0.1))], rfps, lens=45)

def dark_cell_nucleus(nf, rfps, dur):
    """Dim translucent blue cell with a purple pore-studded nucleus inside; slow push (806-820)."""
    reset(); stage(target=(0, 0, 0), key=(2.0, -5.0, 8.0), key_e=2000, spot=65, fill_e=160, env=0.2)
    rim_cell('DarkCell', 2.6, (0, 0, 0), color=(0.01, 0.06, 0.16), rim=(0.05, 0.35, 0.7), a_center=0.5, a_rim=0.95, emit=0.9, egg=0.25, squash=(1.0, 0.85, 0.72))
    n = nucleus_organelle((-0.2, -0.3, 0.35), rn=0.75, name='Nuc', cut=None, pores=70, chromatin=0, seed=5)
    kf(n['root'], 'rotation_euler', 1, (0, 0, 0)); kf(n['root'], 'rotation_euler', nf, (0.1, 0, 1.4)); kf_lin(n['root'])
    cam_path([(0.0, (0.2, -11.0, 1.0), (0, 0, 0.1)), (dur, (0.0, -8.6, 0.9), (-0.1, -0.2, 0.2))], rfps, lens=45)

def bacteria(nf, rfps, dur):
    """Lilac capsule cut open (front-top), purple coiled nucleoid and blue beaded threads; the camera pushes in (820-842)."""
    reset(); stage(target=(0, 0, 0.3), key=(3.0, -6.0, 9.0), key_e=2600, spot=60, fill_e=220, rim_e=300, env=0.3)
    b = bacterium((0, 0, 0), L=6.0, name='Bact', seed=9, rot=0.35, cut=True)
    anchor('TagNucleoid', (0.9, -0.1, 0.9))
    cam_path([(0.0, (1.5, -14.0, 5.0), (0.3, 0, 0.2)), (12.0, (0.8, -8.0, 3.0), (0.3, 0, 0.3)), (dur, (0.4, -6.3, 2.5), (0.3, 0.1, 0.4))], rfps, lens=45)

def cytoplasm_cup(nf, rfps, dur):
    """Whole orange cell scooped open like a cup: the blotchy cytoplasm inside; slow turn toward the opening (842-866)."""
    reset(); stage(target=(0, 0, 0.2), key=(2.5, -5.0, 8.0), key_e=2500, spot=55, fill_e=200)
    c = cutaway_cell((0, 0, 0), 2.2, cut='scoop', nucleus=None, interior='interior', seg=128)
    anchor('TagCyto', (0.3, -0.9, 0.6))
    cam_path([(0.0, (1.2, -10.5, 3.6), (0.1, 0, 0.2)), (12.0, (-0.6, -10.0, 4.0), (0.1, 0, 0.2)), (dur, (0.2, -9.4, 4.4), (0.1, 0, 0.2))], rfps, lens=50)

def cell_organelles_small(nf, rfps, dur):
    """Cutaway cell with small organelles scattered on the cytoplasm floor: nucleus, red mitochondria, green
    lysosomes, a golden golgi (866-881)."""
    reset(); world(0.0025, 0.004, 0.009); hdri(strength=0.3, rotation=1.3); atmosphere(density=0.002)
    cutaway_cell((0, 0, 0), 3.2, cut='wedge', nucleus=None, name='Cell', thick=0.07, interior='interior', seg=128)
    nucleus_organelle((0.0, -0.95, 0.68), rn=0.62, name='Nuc', cut='wedge', pores=0, chromatin=0, seed=3)
    rnd = random.Random(12)
    for i, (px, py, rot) in enumerate([(-1.7, -0.8, 0.3), (1.6, -0.7, -0.4), (-1.3, -2.2, 1.1), (1.0, -2.4, 0.2), (-0.3, -1.9, -0.9), (2.0, -1.8, 0.9)]):
        mini_mito((px, py, 0.2), L=0.9, rot=rot, name=f'MiniMito{i}', seed=i)
    for i, (px, py) in enumerate([(-2.2, -1.6), (0.75, -1.2), (-0.7, -2.8), (1.5, -1.4), (0.2, -2.9)]):
        lysosome((px, py, 0.18), r=0.24, name=f'Lys{i}', seed=20 + i, patches=4)
    g = golgi((1.2, -1.7, 0.05), s=0.55, name='Golgi', rot=-0.6, seed=4, n_sheets=5)
    for sh in g['sheets']: setmat(sh, mat_organic((0.75, 0.6, 0.18), rough=0.4, sss=0.2, coat=0.35, name='gold'))
    light('SPOT', (3.0, -6.0, 9.0), 2800, (1.0, 0.95, 0.87), 'Key', spot=60, blend=0.85, target=(0, -1.0, 0.3))
    soft_light((-6.0, -7.0, 4.0), 240, size=6, name='Fill', target=(0, -1.0, 0.3)); soft_light((2.0, -2.5, 6.0), 150, size=5, color=(0.8, 0.9, 1.0), name='Top', target=(0, -1.5, 0))
    cam_path([(0.0, (0.8, -12.5, 4.0), (0.0, -0.3, 0.6)), (dur, (0.3, -11.2, 3.7), (0.0, -0.3, 0.6))], rfps, lens=45)
