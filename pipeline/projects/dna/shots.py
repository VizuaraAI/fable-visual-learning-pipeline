"""Blender builders for every 3D shot of 'DNA: From Gene to Protein' (original chapter, Class 10-12 molecular biology).
Each builder(nf, rfps, dur) resets the scene, builds, animates frames 1..nf, and creates the camera (at -Y looking +Y, Z up).
Toolkit (this file, kit.py untouched):
  Helix     the DNA rig: two bevelled NURBS rails (sugar-phosphate backbones) with real sugar (oblate cream) and phosphate
            (blue) bead geometry, every base pair as two colour-coded half-rung capsules meeting at a gap where 2 (A-T) or
            3 (G-C) emissive hydrogen-bond dashes glow. individual=True builds per-base-pair half units that can unzip
            (rail control points are keyframed with them); individual=False batches everything for long helices.
  Ladder    a straight ladder with the same parts under a Simple-Deform twist (the 'twisted ladder' morph).
  RNA       single strand (amber rail, bases pointing to one side, U violet) that can grow base by base.
  blobs     metaball -> mesh organic bodies (RNA polymerase, ribosome subunits, enzyme, haemoglobin lobes) with subsurface.
  tRNA, amino-acid chains with per-frame refitted links, red cells with a disc->sickle shape key, cell / nucleus / pores."""
import math, random, bpy, os, sys, bmesh
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from mathutils import Vector, Matrix, Quaternion
from kit import *
from kit import _principled, _inp
from projects.dna.palette import *   # BASE, COMP, RNA_OF, THEMES, every named colour

def F(sec, rfps): return int(round(sec * rfps)) + 1     # seconds -> frame number (1-based)
CY = is_cycles()
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))

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
    """Soft waxy organic surface: subsurface + a light coat (the house look for membranes, enzymes, ribosomes)."""
    m, p = _principled(name)
    _inp(p, 'Base Color', (*color, 1)); _inp(p, 'Roughness', rough); _inp(p, 'Coat Weight', coat); _inp(p, 'Coat Roughness', 0.15)
    _inp(p, 'Subsurface Weight', sss); _inp(p, 'Subsurface Scale', scale); _inp(p, 'Specular IOR Level', spec)
    _inp(p, 'Subsurface Radius', radius or (color[0] * 1.2 + 0.2, color[1] * 0.8 + 0.1, color[2] * 0.6 + 0.05))
    return m

def mat_gloss(color, rough=0.22, coat=0.6, name='gloss', sss=0.08):
    """Glossy coated plastic for the molecular parts (beads, rungs, rails): saturated, clean highlights."""
    m, p = _principled(name)
    _inp(p, 'Base Color', (*color, 1)); _inp(p, 'Roughness', rough); _inp(p, 'Coat Weight', coat); _inp(p, 'Coat Roughness', 0.08)
    _inp(p, 'Subsurface Weight', sss); _inp(p, 'Subsurface Scale', 0.05); _inp(p, 'Specular IOR Level', 0.55)
    return m

def mat_glow(color, strength=6.0, name='glow', alpha=1.0): return mat_emit(color, strength=strength, name=name, alpha=alpha)

def mat_lit(color, emit=1.2, rough=0.3, name='lit'):
    """Coloured surface that also emits a little of its own colour (start/stop codons, highlighted gene)."""
    m, p = _principled(name)
    _inp(p, 'Base Color', (*color, 1)); _inp(p, 'Roughness', rough); _inp(p, 'Coat Weight', 0.4)
    _inp(p, 'Emission Color', (*color, 1)); _inp(p, 'Emission Strength', emit)
    return m

def mat_rim(color, rim, a_center=0.12, a_rim=0.85, emit=2.0, name='rim', blend=0.35, rough=0.25):
    """Translucent body whose edges glow (fresnel): cell membrane, nuclear envelope seen from inside, glow sleeves."""
    m, p = _principled(name); nt = m.node_tree; n = nt.nodes
    lw = n.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = blend
    mr = n.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.0; mr.inputs['From Max'].default_value = 1.0
    mr.inputs['To Min'].default_value = a_center; mr.inputs['To Max'].default_value = a_rim
    mul = n.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = emit
    nt.links.new(lw.outputs['Facing'], mr.inputs['Value']); nt.links.new(mr.outputs['Result'], p.inputs['Alpha'])
    nt.links.new(lw.outputs['Facing'], mul.inputs[0]); nt.links.new(mul.outputs[0], p.inputs['Emission Strength'])
    _inp(p, 'Base Color', (*color, 1)); _inp(p, 'Emission Color', (*rim, 1)); _inp(p, 'Roughness', rough); _inp(p, 'Specular IOR Level', 0.6)
    _blend(m)
    try: m.use_backface_culling = True
    except Exception: pass
    return m

def mat_translucent(color, alpha=0.6, rough=0.3, emit=0.0, name='transl', sss=0.0, coat=0.3):
    m, p = _principled(name)
    _inp(p, 'Base Color', (*color, 1)); _inp(p, 'Roughness', rough); _inp(p, 'Alpha', alpha); _inp(p, 'Coat Weight', coat); _inp(p, 'Subsurface Weight', sss)
    if emit: _inp(p, 'Emission Color', (*color, 1)); _inp(p, 'Emission Strength', emit)
    _blend(m)
    return m

def mat_blotch(base, spot, scale=5.0, lo=0.42, hi=0.62, rough=0.5, sss=0.25, name='blotch', detail=3.0, bump=0.0, coat=0.12):
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

def mat_marble(base=(0.93, 0.95, 1.0), vein=(0.1, 0.13, 0.5), scale=3.0, name='marble', bands=7.0):
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

_MATS = {}
def M(key, maker):
    """Per-scene material cache (reset() drops bpy data, so the cache is keyed by scene identity)."""
    sc = bpy.context.scene; tag = (id(sc), key)
    m = _MATS.get(tag)
    if m is None or m.name not in bpy.data.materials: m = maker(); _MATS[tag] = m
    return m
def m_base(b): return M('base' + b, lambda: mat_gloss(BASE[b], rough=0.25, coat=0.6, name='base_' + b, sss=0.1))
def m_sugar(): return M('sugar', lambda: mat_gloss(SUGAR, rough=0.3, coat=0.4, name='sugar', sss=0.15))
def m_phos(): return M('phos', lambda: mat_gloss(PHOS, rough=0.2, coat=0.7, name='phos'))
def m_rail(s): return M('rail' + str(s), lambda: mat_gloss(RAIL_A if s == 0 else RAIL_B, rough=0.28, coat=0.5, name='rail' + str(s)))
def m_hbond(): return M('hbond', lambda: _hbond_mat())     # was an emission of 7: the compositor bloom blew the dashes out to white; a lit ice-blue keeps the colour
def _hbond_mat():
    m = mat_lit(HBOND, emit=1.3, rough=0.3, name='hbond'); p = m.node_tree.nodes.get('Principled BSDF'); _inp(p, 'Emission Color', (0.45, 0.78, 1.0, 1)); return m
def m_rna_rail(): return M('rna_rail', lambda: mat_gloss(RNA_RAIL, rough=0.28, coat=0.5, name='rna_rail'))
def m_rna_sugar(): return M('rna_sugar', lambda: mat_gloss(RNA_SUGAR, rough=0.3, coat=0.4, name='rna_sugar', sss=0.15))
def m_amino(a): return M('aa' + a, lambda: mat_gloss(AMINO.get(a, (0.8, 0.8, 0.8)), rough=0.3, coat=0.5, name='aa_' + a, sss=0.2))

# ================================================================= mesh helpers
def mesh_obj(name, bm, mat=None, smooth_=True, loc=None):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth_:
        for pl in me.polygons: pl.use_smooth = True
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    if mat is not None: setmat(o, mat)
    if loc is not None: o.location = loc
    return o

def sphere(name, r, loc=(0, 0, 0), seg=48, ring=24, mat=None, scale=None):
    o = obj_add('uv_sphere', name, radius=r, segments=seg, ring_count=ring, location=loc)
    if scale: o.scale = scale
    if mat is not None: setmat(o, mat)
    smooth(o, auto=False); return o

def capsule_into(bm, p0, p1, r, seg=24, ring=12):
    """Append a capsule (round-capped tube) from p0 to p1 with radius r to a bmesh."""
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0; L = d.length
    if L < 1e-6: d = Vector((0, 0, 1e-6)); L = 1e-6
    res = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=ring, radius=r); vs = res['verts']
    for v in vs:
        if v.co.z > 1e-7: v.co.z += L
    Mx = Matrix.Translation(p0) @ d.normalized().to_track_quat('Z', 'Y').to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Mx, verts=vs)
    return vs

def capsule_obj(name, p0, p1, r, mat=None, seg=24, ring=12):
    bm = bmesh.new(); capsule_into(bm, p0, p1, r, seg, ring); return mesh_obj(name, bm, mat)

def unit_link(name, r, mat, seg=16, ring=8):
    """A capsule from (0,0,0) to (0,0,1): pose it with fit_link() (location = p0, quaternion = track, scale.z = length)."""
    o = capsule_obj(name, (0, 0, 0), (0, 0, 1), r, mat, seg, ring); o.rotation_mode = 'QUATERNION'; return o

def fit_link(o, p0, p1, frame=None, r_keep=True):
    """Pose a unit_link between two points (optionally keyframed): the capsule caps do not stretch because the sphere
    verts sit at z=0 and z=1 exactly -> scale.z stretches only the cylinder part."""
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0; L = max(1e-5, d.length)
    o.location = p0; o.rotation_quaternion = d.normalized().to_track_quat('Z', 'Y'); o.scale = (1, 1, L)
    if frame is not None:
        o.keyframe_insert('location', frame=frame); o.keyframe_insert('rotation_quaternion', frame=frame); o.keyframe_insert('scale', frame=frame)

def spheres_mesh(name, pts, r, mat, subdiv=2, rscale=None, scale3=None, normals=None):
    bm = bmesh.new()
    for i, p in enumerate(pts):
        rr = r * (rscale[i] if rscale is not None else 1.0)
        Mx = Matrix.Translation(Vector(p))
        if normals is not None: Mx = Mx @ Vector(normals[i]).to_track_quat('Z', 'Y').to_matrix().to_4x4()
        if scale3 is not None: Mx = Mx @ Matrix.Diagonal((scale3[0], scale3[1], scale3[2], 1.0))
        bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=rr, matrix=Mx)
    return mesh_obj(name, bm, mat)

def capsules_mesh(name, segs, r, mat, seg=20, ring=10):
    bm = bmesh.new()
    for p0, p1 in segs: capsule_into(bm, p0, p1, r, seg, ring)
    return mesh_obj(name, bm, mat)

def catmull(pts, n):
    P = [pts[0]] + list(pts) + [pts[-1]]; out = []; segs = len(pts) - 1
    for i in range(segs):
        p0, p1, p2, p3 = (Vector(P[i]), Vector(P[i + 1]), Vector(P[i + 2]), Vector(P[i + 3]))
        steps = max(1, int(round(n / segs)))
        for k in range(steps):
            t = k / steps; t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(Vector(pts[-1])); return out

def curve_obj(name, pts, r, mat, loc=(0, 0, 0), res=12, kind='NURBS', cyclic=False, bevel_res=8, order=4):
    """Bevelled curve (tube) through points: rails, chromatin, tRNA arms, protein chains."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = bevel_res; cu.use_fill_caps = True
    cu.resolution_u = res
    sp = cu.splines.new(kind); sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts): sp.points[i].co = (p[0], p[1], p[2], 1.0)
    sp.use_endpoint_u = True; sp.use_cyclic_u = cyclic
    try: sp.order_u = order
    except Exception: pass
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o); o.location = loc
    cu.materials.append(mat)
    for sp in cu.splines:
        try: sp.use_smooth = True
        except Exception: pass
    return o

def grow_curve(o, f0, f1, start=False):
    """Animate a bevelled curve growing from its first point (bevel_factor_end 0 -> 1) between frames."""
    cu = o.data; prop = 'bevel_factor_start' if start else 'bevel_factor_end'
    setattr(cu, prop, 0.0 if not start else 1.0); cu.keyframe_insert(prop, frame=1); cu.keyframe_insert(prop, frame=f0)
    setattr(cu, prop, 1.0 if not start else 0.0); cu.keyframe_insert(prop, frame=f1)
    ease_id(cu)

def text_obj(name, body, size=0.3, mat=None, loc=(0, 0, 0), rot=(math.pi / 2, 0, 0), extrude=0.01, align='CENTER'):
    """3D text (built-in font) facing -Y: codon letters on the 64-tile wall."""
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.size = size; cu.extrude = extrude; cu.align_x = align; cu.align_y = 'CENTER'
    try: cu.bevel_depth = 0.004; cu.bevel_resolution = 2
    except Exception: pass
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o); o.location = loc; o.rotation_euler = rot
    if mat is not None: cu.materials.append(mat)
    return o

def helix_pts(length, radius, turns, n=120, axis='x', phase=0.0, taper=0.0):
    out = []
    for i in range(n + 1):
        u = i / n; a = 2 * math.pi * turns * u + phase; rr = radius * (1 - taper * u)
        if axis == 'x': out.append((-length / 2 + length * u, rr * math.cos(a), rr * math.sin(a)))
        else: out.append((rr * math.cos(a), rr * math.sin(a), -length / 2 + length * u))
    return out

def wander_pts(rnd, start, n, step, box, smoothness=0.65):
    p = Vector(start); d = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))).normalized(); out = [tuple(p)]
    for i in range(n):
        nd = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))).normalized()
        d = (d * smoothness + nd * (1 - smoothness)).normalized(); p = p + d * step
        for k in range(3):
            lo, hi = box[k]
            if p[k] < lo: p[k] = lo + (lo - p[k]); d[k] = abs(d[k])
            if p[k] > hi: p[k] = hi - (p[k] - hi); d[k] = -abs(d[k])
        out.append(tuple(p))
    return out

def parent(o, root):
    o.parent = root; o.matrix_parent_inverse = Matrix.Identity(4)

def hide_until(o, f):
    kf(o, 'hide_render', 1, True); kf(o, 'hide_render', f, False)
    try: kf(o, 'hide_viewport', 1, True); kf(o, 'hide_viewport', f, False)
    except Exception: pass

def hide_from(o, f):
    kf(o, 'hide_render', 1, False); kf(o, 'hide_render', f, True)

def show_between(o, f0, f1):
    kf(o, 'hide_render', 1, True); kf(o, 'hide_render', f0, False); kf(o, 'hide_render', f1, True)

def anchor(name, loc, parent_to=None):
    """Sub-pixel mesh speck whose 2D position the compositor uses to pin a label (must be a visible MESH).
    Names get the 'Rp' prefix so shotlist anchors='auto' (Hp*/Op*/Rp*) exports them; the timeline uses 'Rp' + name."""
    o = obj_add('ico_sphere', 'Rp' + name, radius=0.002, subdivisions=1, location=loc)
    setmat(o, M('anch', lambda: mat_emit((0, 0, 0), strength=0.0, name='anch')))
    try: o.visible_shadow = False
    except Exception: pass
    if parent_to is not None: parent(o, parent_to)
    return o

def _fcurves_id(idb):
    """All fcurves animating an ID block, legacy or slotted action layout (never touches action.fcurves directly)."""
    ad = getattr(idb, 'animation_data', None)
    if not (ad and ad.action): return []
    act = ad.action
    if hasattr(act, 'fcurves'):
        try: return list(act.fcurves)
        except Exception: pass
    out = []
    try:
        for layer in act.layers:
            for strip in layer.strips:
                for cb in strip.channelbags: out.extend(cb.fcurves)
    except Exception: pass
    return out

def ease_id(idb, mode='EASE_IN_OUT'):
    for fc in _fcurves_id(idb):
        for k in fc.keyframe_points: k.interpolation = 'BEZIER'; k.easing = mode
def lin_id(idb):
    for fc in _fcurves_id(idb):
        for k in fc.keyframe_points: k.interpolation = 'LINEAR'

def smooth01(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)
def lerp(a, b, u): return a + (b - a) * u
def vlerp(a, b, u): return Vector(a) * (1 - u) + Vector(b) * u


# ================================================================= HD molecular geometry
# Ring-plate bases (purine = pentagon fused to a hexagon, pyrimidine = one hexagon), pentagon sugars, tetrahedral phosphates
# with their four oxygens, glycosidic stubs.  Every piece is built in a unit frame (+y radial toward the sugar, +x helix axis,
# plate in the y-z plane) and merged into batched meshes (long helices) or kept as one object per half-unit (animating rigs).
RP = 0.215; RH = RP * 1.176                 # pentagon / hexagon circumradius (fused rings share an edge: 2*RP*sin36 = RH)
L_PUR = 3.846 * RP; L_PYR = 2.0 * RH        # radial extent of a purine plate (pentagon + hexagon) and a pyrimidine plate
PLATE_T = 0.10; Y_OUT_IN = 0.14             # plate thickness; the plate starts this far inside the sugar-ring centre (radius R)
R_SUGAR_RING = 0.14; R_PHOS_T = 0.115; R_OXY = 0.042
def plate_len(b): return L_PUR if b in PURINE else L_PYR

def merge_into(bm, tmp, matrix=None):
    """Append a temp bmesh (after all its ops, e.g. bevels) into bm, transformed by matrix."""
    if matrix is not None: bmesh.ops.transform(tmp, matrix=matrix, verts=list(tmp.verts))
    me = bpy.data.meshes.new('_scratch'); tmp.to_mesh(me); tmp.free(); bm.from_mesh(me); bpy.data.meshes.remove(me)

def _ring_into(bm, n, cy, cz, r, thick, a0, hole=0.5, atoms=0.0, mi=0, bevel=True):
    """An n-gon ring plate (outer circumradius r, hole fraction) in the y-z plane, thickness along x, rounded rims, optional
    atom spheres on the ring vertices.  Vertex k sits at angle a0 + 2*pi*k/n measured from +y toward +z."""
    def ring(rad, x): return [bm.verts.new((x, cy + rad * math.cos(a0 + 2 * math.pi * k / n), cz + rad * math.sin(a0 + 2 * math.pi * k / n))) for k in range(n)]
    ot, it, ob, ib = ring(r, thick / 2), ring(r * hole, thick / 2), ring(r, -thick / 2), ring(r * hole, -thick / 2)
    faces = []
    for k in range(n):
        k1 = (k + 1) % n
        faces += [bm.faces.new((ot[k], ot[k1], it[k1], it[k])), bm.faces.new((ob[k1], ob[k], ib[k], ib[k1])),
                  bm.faces.new((ot[k1], ot[k], ob[k], ob[k1])), bm.faces.new((it[k], it[k1], ib[k1], ib[k]))]
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    for f in faces: f.material_index = mi
    if bevel:
        edges = []
        for vs in (ot, it, ob, ib):
            for k in range(n):
                e = bm.edges.get((vs[k], vs[(k + 1) % n]))
                if e: edges.append(e)
        try:
            res = bmesh.ops.bevel(bm, geom=edges, offset=thick * 0.30, offset_type='OFFSET', segments=2, profile=0.55, affect='EDGES', clamp_overlap=True)
            for f in res.get('faces', []): f.material_index = mi
        except Exception as ex: print('ring bevel', ex)
    if atoms:
        for k in range(n):
            a = a0 + 2 * math.pi * k / n
            res = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=atoms, matrix=Matrix.Translation((0, cy + r * math.cos(a), cz + r * math.sin(a))))
            for v in res['verts']:
                for f in v.link_faces: f.material_index = mi
    return faces

def plate_bmesh(b, y_out, thick=PLATE_T, atoms=0.026, mi=0):
    """Base plate for base b in the unit frame: outer vertex at y_out (touching the sugar), extending inward along -y."""
    bm = bmesh.new()
    if b in PURINE:
        cp = y_out - RP; _ring_into(bm, 5, cp, 0.0, RP, thick * 0.94, 0.0, hole=0.46, atoms=atoms, mi=mi)              # pentagon, vertex toward the sugar
        ch = cp - 0.809 * RP - 0.866 * RH; _ring_into(bm, 6, ch, 0.0, RH, thick, math.pi / 6, hole=0.52, atoms=atoms, mi=mi)   # hexagon fused on its far edge
    else:
        _ring_into(bm, 6, y_out - RH, 0.0, RH, thick, 0.0, hole=0.52, atoms=atoms, mi=mi)                                     # pointy hexagon
    return bm

def sugar_bmesh(R, stub_to=None, mi=0):
    """Deoxyribose: pentagon ring plate lying in the x-y plane (normal along the rail tangent), centred on the rail at radius R,
    plus the glycosidic stub down to the base plate."""
    bm = bmesh.new()
    _ring_into(bm, 5, 0.0, 0.0, R_SUGAR_RING, 0.075, -math.pi / 2, hole=0.42, atoms=0.024, mi=mi)
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, 'Y'), verts=list(bm.verts))
    bmesh.ops.translate(bm, vec=(0, R, 0), verts=list(bm.verts))
    if stub_to is not None:
        vs = capsule_into(bm, (0, R - 0.05, 0), (0, stub_to + 0.03, 0), 0.03, 10, 5)
        for v in vs:
            for f in v.link_faces: f.material_index = mi
    return bm

def phos_bmesh(pos, rnd=None, mi_p=0, mi_o=1, r=R_PHOS_T):
    """Phosphate: a P tetrahedron with its four oxygens on the vertices (two material slots), random orientation."""
    bm = bmesh.new(); rnd = rnd or random.Random(1)
    q = Quaternion((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)), rnd.uniform(0, math.pi)).to_matrix()
    dirs = [Vector(d).normalized() for d in ((1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1))]
    vs = [bm.verts.new(Vector(pos) + q @ (d * r)) for d in dirs]
    faces = [bm.faces.new((vs[0], vs[1], vs[2])), bm.faces.new((vs[0], vs[3], vs[1])), bm.faces.new((vs[0], vs[2], vs[3])), bm.faces.new((vs[1], vs[3], vs[2]))]
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    try:
        res = bmesh.ops.bevel(bm, geom=list(bm.edges), offset=r * 0.28, offset_type='OFFSET', segments=2, profile=0.6, affect='EDGES', clamp_overlap=True)
        for f in res.get('faces', []): f.material_index = mi_p
    except Exception as ex: print('phos bevel', ex)
    for f in bm.faces: f.material_index = mi_p
    for d in dirs:
        res = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=R_OXY, matrix=Matrix.Translation(Vector(pos) + q @ (d * r * 1.12)))
        for v in res['verts']:
            for f in v.link_faces: f.material_index = mi_o
    return bm

def mesh_obj_multi(name, bm, mats, loc=None):
    o = mesh_obj(name, bm, None, loc=loc)
    for m in mats: o.data.materials.append(m)
    return o

def unit_matrix(axis_pt, th): return Matrix.Translation(Vector(axis_pt)) @ Matrix.Rotation(th, 4, 'X')

def m_phos_o(): return M('phos_o', lambda: mat_gloss(PHOS_O, rough=0.25, coat=0.5, name='phos_o'))

# ================================================================= the DNA rig
class Helix:
    """Right-handed double helix along the local +X of a root empty.
    bp i sits at x_i = x0 + i*rise; strand 0 at angle th_i = phase + i*dth, strand 1 at th_i + pi (antiparallel partner).
    Radial unit vector at angle th is (0, cos th, sin th).  Sugars sit on the rails at th_i, phosphates half a step further
    along the rail (x_i + rise/2, th_i + dth/2) so the backbone reads as alternating sugar-phosphate units.
    hd=False: capsule rungs + bead sugars/phosphates (cheap, for far and long helices).  hd=True: ring-plate bases whose
    lengths differ (purine long, pyrimidine short, so the H-bond gap sits off-axis toward the pyrimidine as in real DNA),
    pentagon sugars, tetrahedral phosphates with oxygens.  individual=True builds per-base-pair half units (empties at the
    axis, rotated to th) that key_open/bubble can displace radially; batched builds one mesh per material."""
    def __init__(self, name, seq, loc=(0, 0, 0), rot=(0, 0, 0), R=1.0, rise=0.40, bp_turn=10, phase=0.0, individual=False,
                 hbonds=True, r_rail=0.085, r_sugar=0.16, r_phos=0.13, r_rung=0.12, gap=0.20, anchors=(), rails=True, beads=True, sub_pt=6,
                 base_mats=None, start_hidden=False, hd=False, atoms=True, seed=1):
        self.name, self.seq, self.R, self.rise, self.dth, self.phase = name, seq, R, rise, 2 * math.pi / bp_turn, phase
        self.N = len(seq); self.r_rung, self.r_sugar, self.r_phos, self.r_rail = r_rung, r_sugar, r_phos, r_rail
        self.hd = hd; self.atoms = 0.026 if atoms else 0.0; self.rnd = random.Random(seed)
        self.y_out = R - Y_OUT_IN if hd else R - 0.02
        self.gap = (2 * self.y_out - L_PUR - L_PYR) if hd else gap
        self.x0 = -(self.N - 1) * rise / 2
        self.root = empty(name, loc); self.root.rotation_euler = rot
        self.individual = individual; self.hbonds = hbonds; self.base_mats = base_mats or {}
        self.units = {}; self.disp = {}; self.rail_objs = []; self.rail_pts = {}; self.bead_objs = []; self.rung_objs = {}; self.hb_obj = None
        self.anchors = {}
        if individual: self._build_individual(rails, beads, sub_pt)
        else: self._build_batched(rails, beads, sub_pt)
        for (i, s) in anchors: self.add_anchor(i, s)
        if start_hidden:
            for o in self.all_objects(): hide_until(o, 10 ** 6)

    # ---- geometry
    def th(self, i, s=0): return self.phase + i * self.dth + (math.pi if s else 0.0)
    def rad(self, th): return Vector((0, math.cos(th), math.sin(th)))
    def axis_pt(self, i): return Vector((self.x0 + i * self.rise, 0, 0))
    def sugar_pt(self, i, s, d=0.0): return self.axis_pt(i) + self.rad(self.th(i, s)) * (self.R + d)
    def phos_pt(self, i, s, d=0.0): return Vector((self.x0 + (i + 0.5) * self.rise, 0, 0)) + self.rad(self.th(i, s) + self.dth / 2) * (self.R + d)
    def base_of(self, i, s): return self.seq[i] if s == 0 else COMP[self.seq[i]]
    def m(self, i): return (plate_len(self.base_of(i, 1)) - plate_len(self.base_of(i, 0))) / 2 if self.hd else 0.0   # gap centre shifts toward the pyrimidine
    def inner(self, i, s): return (self.m(i) if s == 0 else -self.m(i)) + self.gap / 2
    def rung_ends(self, i, s, d=0.0):
        n = self.rad(self.th(i, s)); a = self.axis_pt(i)
        return a + n * (self.y_out + d), a + n * (self.inner(i, s) + d)
    def base_mid(self, i, s): p0, p1 = self.rung_ends(i, s); return (p0 + p1) / 2
    def gap_centre(self, i): return self.axis_pt(i) + self.rad(self.th(i, 0)) * self.m(i)
    def world(self, p): return self.root.matrix_world @ Vector(p)
    def n_hb(self, i): return 2 if self.seq[i] in 'AT' else 3
    def hb_offsets(self, i): return [-0.055, 0.055] if self.n_hb(i) == 2 else [-0.085, 0.0, 0.085]
    def hbond_segs(self, i, d=0.0):
        n = self.rad(self.th(i, 0)); a = self.gap_centre(i)
        return [(a + X * o + n * (self.gap / 2 + 0.01 + d), a + X * o - n * (self.gap / 2 + 0.01 + d)) for o in self.hb_offsets(i)]
    def rail_samples(self, s, per_bp=6, d_fn=None):
        pts = []
        for k in range(self.N * per_bp + 1):
            u = k / per_bp; th = self.phase + u * self.dth + (math.pi if s else 0.0)
            d = d_fn(u, s) if d_fn else 0.0
            pts.append(Vector((self.x0 + u * self.rise, 0, 0)) + self.rad(th) * (self.R + d))
        return pts
    def U(self, i, s): return unit_matrix(self.axis_pt(i), self.th(i, s))
    def phos_local(self, s): return Vector((self.rise / 2, self.R * math.cos(self.dth / 2), self.R * math.sin(self.dth / 2)))
    def add_anchor(self, i, s, tag=None):
        a = anchor(tag or f'{self.name}_a{i}_{s}', self.base_mid(i, s), self.root); self.anchors[(i, s)] = a; return a

    # ---- batched build (long / static helices)
    def _build_batched(self, rails, beads, sub_pt):
        n = self.name
        if rails:
            for s in (0, 1):
                pts = self.rail_samples(s, per_bp=sub_pt)
                c = curve_obj(f'{n}_rail{s}', pts, self.r_rail, m_rail(s), res=6, kind='POLY' if sub_pt >= 8 else 'NURBS', order=3)
                parent(c, self.root); self.rail_objs.append(c)
        if beads and not self.hd:
            sug = [self.sugar_pt(i, s) for i in range(self.N) for s in (0, 1)]; nrm = [self.rad(self.th(i, s)) for i in range(self.N) for s in (0, 1)]
            so = spheres_mesh(f'{n}_sugar', sug, self.r_sugar, m_sugar(), subdiv=2, scale3=(1, 1, 0.68), normals=nrm); parent(so, self.root)
            pho = [self.phos_pt(i, s) for i in range(self.N) for s in (0, 1)]
            po = spheres_mesh(f'{n}_phos', pho, self.r_phos, m_phos(), subdiv=2); parent(po, self.root)
            self.bead_objs = [so, po]
        elif beads and self.hd:
            bs = bmesh.new(); bp = bmesh.new()
            for i in range(self.N):
                for s in (0, 1):
                    merge_into(bs, sugar_bmesh(self.R, stub_to=self.y_out), self.U(i, s))
                    merge_into(bp, phos_bmesh(self.phos_local(s), self.rnd), self.U(i, s))
            so = mesh_obj(f'{n}_sugar', bs, m_sugar()); parent(so, self.root)
            po = mesh_obj_multi(f'{n}_phos', bp, [m_phos(), m_phos_o()]); parent(po, self.root)
            self.bead_objs = [so, po]
        if self.hd:
            by = {}
            for i in range(self.N):
                for s in (0, 1): by.setdefault(self.base_of(i, s), []).append((i, s))
            for b, units in by.items():
                bm = bmesh.new()
                for (i, s) in units: merge_into(bm, plate_bmesh(b, self.y_out, atoms=self.atoms), self.U(i, s))
                o = mesh_obj(f'{n}_rung{b}', bm, self.base_mats.get(b, m_base(b))); parent(o, self.root); self.rung_objs[b] = o
        else:
            by = {}
            for i in range(self.N):
                for s in (0, 1): by.setdefault(self.base_of(i, s), []).append(self.rung_ends(i, s))
            for b, segs in by.items():
                o = capsules_mesh(f'{n}_rung{b}', segs, self.r_rung, self.base_mats.get(b, m_base(b)), seg=20, ring=10); parent(o, self.root); self.rung_objs[b] = o
        if self.hbonds:
            segs = [sg for i in range(self.N) for sg in self.hbond_segs(i)]
            h = capsules_mesh(f'{n}_hb', segs, 0.028, m_hbond(), seg=8, ring=4); parent(h, self.root); self.hb_obj = h
            try: h.visible_shadow = False
            except Exception: pass

    # ---- individual build (animatable half units)
    def _build_individual(self, rails, beads, sub_pt):
        n = self.name
        for i in range(self.N):
            for s in (0, 1):
                u = empty(f'{n}_u{i}_{s}', self.axis_pt(i)); u.rotation_euler = (self.th(i, s), 0, 0); parent(u, self.root)
                self.units[(i, s)] = u; self.disp[(i, s)] = 0.0
                b = self.base_of(i, s)
                if self.hd:
                    rg = mesh_obj(f'{n}_r{i}_{s}', plate_bmesh(b, self.y_out, atoms=self.atoms), self.base_mats.get(b, m_base(b))); parent(rg, u)
                    if beads:
                        sg = mesh_obj(f'{n}_s{i}_{s}', sugar_bmesh(self.R, stub_to=self.y_out), m_sugar()); parent(sg, u)
                        ph = mesh_obj_multi(f'{n}_p{i}_{s}', phos_bmesh(self.phos_local(s), self.rnd), [m_phos(), m_phos_o()]); parent(ph, u)
                else:
                    p0 = Vector((0, self.y_out, 0)); p1 = Vector((0, self.inner(i, s), 0))
                    rg = capsule_obj(f'{n}_r{i}_{s}', p0, p1, self.r_rung, self.base_mats.get(b, m_base(b)), seg=24, ring=12); parent(rg, u)
                    if beads:
                        sg = sphere(f'{n}_s{i}_{s}', self.r_sugar, (0, self.R, 0), seg=32, ring=16, mat=m_sugar(), scale=(1, 0.68, 1)); parent(sg, u)
                        ph = sphere(f'{n}_p{i}_{s}', self.r_phos, tuple(self.phos_local(s)), seg=32, ring=16, mat=m_phos()); parent(ph, u)
                u['rung'] = rg.name
                if self.hbonds and s == 0:
                    bm = bmesh.new(); m = self.m(i)
                    for o in self.hb_offsets(i): capsule_into(bm, (o, m + self.gap / 2 + 0.01, 0), (o, m - self.gap / 2 - 0.01, 0), 0.028, 8, 4)
                    hb = mesh_obj(f'{n}_h{i}', bm, m_hbond()); parent(hb, u); u['hb'] = hb.name
                    try: hb.visible_shadow = False
                    except Exception: pass
        if rails:
            for s in (0, 1):
                pts = []
                for i in range(self.N): pts += [self.sugar_pt(i, s), self.phos_pt(i, s)]
                pts = pts[:-1]
                c = curve_obj(f'{n}_rail{s}', pts, self.r_rail, m_rail(s), res=8, kind='NURBS', order=4); parent(c, self.root); self.rail_objs.append(c)

    def all_objects(self):
        out = list(self.rail_objs) + list(self.bead_objs) + list(self.rung_objs.values())
        if self.hb_obj: out.append(self.hb_obj)
        for u in self.units.values(): out += list(u.children)
        return out

    def unit_objs(self, i, s): return list(self.units[(i, s)].children) if (i, s) in self.units else []
    def hb_of(self, i):
        u = self.units.get((i, 0)); return bpy.data.objects[u['hb']] if (u is not None and 'hb' in u) else None

    # ---- animation of individual units
    def key_open(self, frame, amount_fn, keep_hb=0.06):
        """Displace every half unit radially by amount_fn(i) (0 = closed) and keyframe units, rails and the H-bond glow.
        H-bond dashes fade (scale to 0) once the gap opens beyond keep_hb."""
        cu = [c.data for c in self.rail_objs]
        for i in range(self.N):
            d = amount_fn(i)
            for s in (0, 1):
                u = self.units[(i, s)]; u.location = self.axis_pt(i) + self.rad(self.th(i, s)) * d; u.keyframe_insert('location', frame=frame)
                if s == 0 and 'hb' in u:
                    hb = bpy.data.objects[u['hb']]; k = 1.0 if d < keep_hb else max(0.0, 1 - (d - keep_hb) / 0.08)
                    hb.scale = (1, max(0.001, k), 1); hb.keyframe_insert('scale', frame=frame)
                    hb.location = (0, -d, 0); hb.keyframe_insert('location', frame=frame)      # dashes stay centred on the widening gap
                if cu:
                    sp = cu[s].splines[0]
                    for k, p in ((2 * i, self.sugar_pt(i, s, d)), (2 * i + 1, self.phos_pt(i, s, d))):
                        if k < len(sp.points):
                            sp.points[k].co = (p.x, p.y, p.z, 1.0); cu[s].keyframe_insert(data_path=f'splines[0].points[{k}].co', frame=frame)

    def bubble(self, rfps, t0, t1, centre_fn, width=3.5, depth=0.55, closed_after=None, step=1):
        """Per-frame unzip bubble: at time t the strands are apart by depth*bell((i - centre_fn(t))/width)."""
        f0, f1 = F(t0, rfps), F(t1, rfps)
        for f in range(f0, f1 + 1, step):
            t = (f - 1) / rfps; c = centre_fn(t)
            self.key_open(f, lambda i: depth * math.exp(-((i - c) / width) ** 2) if abs(i - c) < 3 * width else 0.0)
        if (f1 - f0) % step: self.key_open(f1, lambda i: depth * math.exp(-((i - centre_fn((f1 - 1) / rfps)) / width) ** 2) if abs(i - centre_fn((f1 - 1) / rfps)) < 3 * width else 0.0)
        for c in self.rail_objs: lin_id(c.data)
        for u in self.units.values(): lin_id(u)

    def open_all(self, rfps, t0, t1, depth=0.9, fn=None):
        """Every base pair opens (full unzip) between t0 and t1, eased; fn(i) scales the depth per bp."""
        f0, f1 = F(t0, rfps), F(t1, rfps)
        self.key_open(f0, lambda i: 0.0)
        self.key_open(f1, lambda i: depth * (fn(i) if fn else 1.0))
        for u in self.units.values(): kf_ease(u)
        for c in self.rail_objs: ease_id(c.data)

    def hide_all_until(self, f):
        for o in self.all_objects(): hide_until(o, f)
    def hide_strand_until(self, s, f):
        for (i, ss), u in self.units.items():
            if ss == s:
                for o in u.children: hide_until(o, f)
        if len(self.rail_objs) > s: hide_until(self.rail_objs[s], f)
    def hide_strand_from(self, s, f):
        for (i, ss), u in self.units.items():
            if ss == s:
                for o in u.children: hide_from(o, f)
        if len(self.rail_objs) > s: hide_from(self.rail_objs[s], f)

def helix_len(n_bp, rise=0.40): return (n_bp - 1) * rise

def rand_seq(n, seed=1):
    rnd = random.Random(seed); return ''.join(rnd.choice('ATGC') for _ in range(n))

# ================================================================= the twisted ladder (Simple Deform morph)
class Ladder:
    """A straight ladder (rails along X at y = +-R, rungs through the axis) built from meshes and twisted about X by a
    Simple Deform on every part (origin = the root), so 'twist' animates continuously between a flat ladder and a helix.
    hd=True uses the ring-plate bases, pentagon sugars and tetrahedral phosphates."""
    def __init__(self, name, seq, loc=(0, 0, 0), rot=(0, 0, 0), R=1.0, rise=0.40, r_rail=0.085, r_sugar=0.16, r_phos=0.13, r_rung=0.12, gap=0.20, hd=True, seed=3, rail_mats=None):
        self.name, self.seq, self.R, self.rise = name, seq, R, rise; self.hd = hd; rnd = random.Random(seed); self.rail_mats = rail_mats or [m_rail(0), m_rail(1)]; self.rails = []
        self.y_out = R - Y_OUT_IN if hd else R - 0.02
        self.gap = (2 * self.y_out - L_PUR - L_PYR) if hd else gap
        self.N = len(seq); self.x0 = -(self.N - 1) * rise / 2; L = (self.N - 1) * rise
        self.root = empty(name, loc); self.root.rotation_euler = rot; self.parts = []
        for s in (0, 1):
            y = R if s == 0 else -R; bm = bmesh.new(); rings = []; nseg = self.N * 8; sides = 24
            for k in range(nseg + 1):
                x = self.x0 - rise * 0.5 + (L + rise) * k / nseg; ring = []
                for j in range(sides):
                    a = 2 * math.pi * j / sides; ring.append(bm.verts.new((x, y + r_rail * math.cos(a), r_rail * math.sin(a))))
                rings.append(ring)
            for a, b in zip(rings[:-1], rings[1:]):
                for j in range(sides): bm.faces.new((a[j], a[(j + 1) % sides], b[(j + 1) % sides], b[j]))
            bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
            o = mesh_obj(f'{name}_rail{s}', bm, self.rail_mats[s]); self._add(o); self.rails.append(o)
            rotx = Matrix.Rotation(0.0 if s == 0 else math.pi, 4, 'X')
            if hd:
                bs = bmesh.new(); bp = bmesh.new()
                for i in range(self.N):
                    Mx = Matrix.Translation((self.x0 + i * rise, 0, 0)) @ rotx
                    merge_into(bs, sugar_bmesh(R, stub_to=self.y_out), Mx)
                    if i < self.N - 1: merge_into(bp, phos_bmesh(Vector((rise / 2, R, 0)), rnd), Mx)
                self._add(mesh_obj(f'{name}_sugar{s}', bs, m_sugar())); self._add(mesh_obj_multi(f'{name}_phos{s}', bp, [m_phos(), m_phos_o()]))
            else:
                sug = [(self.x0 + i * rise, y, 0) for i in range(self.N)]
                self._add(spheres_mesh(f'{name}_sugar{s}', sug, r_sugar, m_sugar(), subdiv=2, scale3=(1, 0.68, 1), normals=[(0, 1, 0)] * self.N))
                pho = [(self.x0 + (i + 0.5) * rise, y, 0) for i in range(self.N - 1)]
                self._add(spheres_mesh(f'{name}_phos{s}', pho, r_phos, m_phos(), subdiv=2))
        by = {}
        for i in range(self.N):
            x = self.x0 + i * rise
            m = (plate_len(COMP[seq[i]]) - plate_len(seq[i])) / 2 if hd else 0.0
            for s in (0, 1):
                b = seq[i] if s == 0 else COMP[seq[i]]; sg = 1 if s == 0 else -1; inner = (m if s == 0 else -m) + self.gap / 2
                if hd: by.setdefault(b, []).append(Matrix.Translation((x, 0, 0)) @ Matrix.Rotation(0.0 if s == 0 else math.pi, 4, 'X'))
                else: by.setdefault(b, []).append(((x, sg * self.y_out, 0), (x, sg * inner, 0)))
            bm = bmesh.new(); k = 2 if seq[i] in 'AT' else 3; offs = [-0.055, 0.055] if k == 2 else [-0.085, 0.0, 0.085]
            for o in offs: capsule_into(bm, (x + o, m + self.gap / 2 + 0.01, 0), (x + o, m - self.gap / 2 - 0.01, 0), 0.028, 8, 4)
            hb = mesh_obj(f'{name}_h{i}', bm, m_hbond()); self._add(hb)
            try: hb.visible_shadow = False
            except Exception: pass
        for b, items in by.items():
            if hd:
                bm = bmesh.new()
                for Mx in items: merge_into(bm, plate_bmesh(b, self.y_out), Mx)
                self._add(mesh_obj(f'{name}_r{b}', bm, m_base(b)))
            else: self._add(capsules_mesh(f'{name}_r{b}', items, r_rung, m_base(b), seg=24, ring=12))
        self.turn_per_len = 2 * math.pi / (10 * rise)      # full helix: 10 bp per turn

    def _add(self, o):
        """Simple-Deform twist about the root's X; angle per object = rate * its own X extent (the modifier spreads the
        angle over the object's bounding box), so every part shares one twist rate theta(x) = rate * x."""
        parent(o, self.root)
        xs = [v.co.x for v in o.data.vertices]; xlen = max(1e-4, max(xs) - min(xs))
        mod = o.modifiers.new('twist', 'SIMPLE_DEFORM'); mod.deform_method = 'TWIST'; mod.deform_axis = 'X'; mod.origin = self.root; mod.angle = 0.0
        self.parts.append((o, mod, xlen))

    def key_twist(self, frame, fraction):
        rate = self.turn_per_len * fraction
        for o, mod, xlen in self.parts:
            mod.angle = rate * xlen; mod.keyframe_insert('angle', frame=frame)

    def ease(self):
        for o, mod, xlen in self.parts: kf_ease(o)
    def objects(self): return [o for o, mod, xlen in self.parts]

# ================================================================= RNA (single strand)
class RNA:
    """Single strand along local +X of a root: amber rail, sugar + phosphate units, one base per nucleotide pointing along
    the local 'side' direction (a unit vector in the y-z plane; default +z), colour by base (U violet).  hd=True gives
    ring-plate bases, pentagon sugars and tetrahedral phosphates; individual=True one object set per nucleotide (grow /
    highlight / swap), else batched meshes.  Optional glow sleeves light up codons."""
    def __init__(self, name, seq, loc=(0, 0, 0), rot=(0, 0, 0), rise=0.40, side=(0, 0, 1), r_rail=0.075, r_sugar=0.14, r_phos=0.115, r_base=0.11,
                 base_len=0.62, individual=False, wave=0.0, wave_len=6.0, anchors=(), rail=True, start=None, hd=False, atoms=True, seed=2, base_mats=None, rail_mat=None, sugar_mat=None):
        self.name, self.seq, self.rise = name, seq, rise; self.rail_mat = rail_mat or m_rna_rail(); self.sugar_mat = sugar_mat or m_rna_sugar(); self.N = len(seq); self.side = Vector(side).normalized(); self.base_len = base_len
        self.hd = hd; self.atoms = 0.026 if atoms else 0.0; self.rnd = random.Random(seed); self.base_mats = base_mats or {}
        self.x0 = -(self.N - 1) * rise / 2 if start is None else start
        self.root = empty(name, loc); self.root.rotation_euler = rot; self.wave, self.wave_len = wave, wave_len
        self.bases = {}; self.sleeves = {}; self.anchors = {}; self.units = {}; self.r_base = r_base; self.rail = None
        self.ang = math.atan2(self.side.z, self.side.y)          # rotation about x taking local +y onto side
        pts = []
        for i in range(self.N): pts += [self.sugar_pt(i), self.phos_pt(i)]
        pts = pts[:-1]
        if rail: self.rail = curve_obj(f'{name}_rail', pts, r_rail, self.rail_mat, res=8, kind='NURBS', order=4); parent(self.rail, self.root)
        if individual:
            for i in range(self.N):
                u = empty(f'{name}_u{i}', self.axis_pt(i)); u.rotation_euler = (self.ang, 0, 0); parent(u, self.root); self.units[i] = u
                self._unit_parts(i, u)
        else:
            if hd:
                bs = bmesh.new(); bp = bmesh.new(); by = {}
                for i in range(self.N):
                    Mx = self.U(i); merge_into(bs, self._sugar_bm(), Mx); merge_into(bp, phos_bmesh(self._phos_local(i), self.rnd), Mx)
                    by.setdefault(seq[i], []).append(Mx)
                so = mesh_obj(f'{name}_sugar', bs, self.sugar_mat); parent(so, self.root); po = mesh_obj_multi(f'{name}_phos', bp, [m_phos(), m_phos_o()]); parent(po, self.root)
                for b, ms in by.items():
                    bm = bmesh.new()
                    for Mx in ms: merge_into(bm, plate_bmesh(b, -self.base_y0(), atoms=self.atoms), Mx @ Matrix.Rotation(math.pi, 4, 'Z'))   # flipped: sugar end at base_y0, pairing edge at the tip
                    o = mesh_obj(f'{name}_b{b}', bm, self.base_mats.get(b, m_base(b))); parent(o, self.root); self.bases[b] = o
            else:
                sug = [self.sugar_pt(i) for i in range(self.N)]; so = spheres_mesh(f'{name}_sugar', sug, r_sugar, self.sugar_mat, subdiv=2, scale3=(1, 1, 0.7), normals=[tuple(self.side)] * self.N); parent(so, self.root)
                pho = [self.phos_pt(i) for i in range(self.N - 1)]; po = spheres_mesh(f'{name}_phos', pho, r_phos, m_phos(), subdiv=2); parent(po, self.root)
                by = {}
                for i in range(self.N): by.setdefault(seq[i], []).append((self.axis_pt(i) + self.side * 0.02, self.axis_pt(i) + self.side * base_len))
                for b, segs in by.items():
                    o = capsules_mesh(f'{name}_b{b}', segs, r_base, self.base_mats.get(b, m_base(b)), seg=20, ring=10); parent(o, self.root); self.bases[b] = o
        for i in anchors: self.add_anchor(i)

    # geometry: the sugar sits on the axis point; the base points along `side`; the phosphate sits between sugars, slightly off the base side
    def axis_pt(self, i):
        x = self.x0 + i * self.rise; w = self.wave * math.sin(2 * math.pi * x / self.wave_len) if self.wave else 0.0
        return Vector((x, 0, 0)) + self.side.cross(X) * w
    def sugar_pt(self, i): return self.axis_pt(i)
    def phos_pt(self, i): return (self.axis_pt(i) + self.axis_pt(min(self.N - 1, i + 1))) / 2 - self.side * 0.12 if i < self.N - 1 else self.axis_pt(i) + X * self.rise / 2 - self.side * 0.12
    def base_y0(self): return R_SUGAR_RING - 0.02 if self.hd else 0.02
    def base_tip(self, i): return self.axis_pt(i) + self.side * (self.base_len if not self.hd else self.base_y0() + plate_len(self.seq[i]))
    def base_mid(self, i): return self.axis_pt(i) + self.side * (self.base_len * 0.55 if not self.hd else self.base_y0() + 0.5 * plate_len(self.seq[i]))
    def world(self, p): return self.root.matrix_world @ Vector(p)
    def U(self, i): return unit_matrix(self.axis_pt(i), self.ang)
    def _phos_local(self, i): return Vector((self.rise / 2, -0.12, 0))
    def _sugar_bm(self):
        bm = bmesh.new(); _ring_into(bm, 5, 0.0, 0.0, R_SUGAR_RING, 0.075, math.pi / 2, hole=0.42, atoms=0.024)
        bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, 'Y'), verts=list(bm.verts))
        return bm
    def _unit_parts(self, i, u):
        """Parts of nucleotide i in the unit frame (+y = side): sugar at the origin, base plate along +y, phosphate at +x/2."""
        n = self.name; b = self.seq[i]
        if self.hd:
            sg = mesh_obj(f'{n}_s{i}', self._sugar_bm(), self.sugar_mat); parent(sg, u)
            ph = mesh_obj_multi(f'{n}_p{i}', phos_bmesh(self._phos_local(i), self.rnd), [m_phos(), m_phos_o()]); parent(ph, u)
            bm = plate_bmesh(b, -self.base_y0(), atoms=self.atoms)
            bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi, 3, 'Z'), verts=list(bm.verts))     # plate grows along +y from the sugar
            stub = capsule_into(bm, (0, R_SUGAR_RING - 0.06, 0), (0, self.base_y0() + 0.03, 0), 0.03, 10, 5)
            bo = mesh_obj(f'{n}_b{i}', bm, self.base_mats.get(b, m_base(b))); parent(bo, u); self.bases[i] = bo
        else:
            sg = sphere(f'{n}_s{i}', 0.14, (0, 0, 0), seg=32, ring=16, mat=self.sugar_mat, scale=(1, 0.7, 1)); parent(sg, u)
            ph = sphere(f'{n}_p{i}', 0.115, tuple(self._phos_local(i)), seg=32, ring=16, mat=m_phos()); parent(ph, u)
            bo = capsule_obj(f'{n}_b{i}', (0, 0.02, 0), (0, self.base_len, 0), self.r_base, self.base_mats.get(b, m_base(b)), seg=24, ring=12); parent(bo, u); self.bases[i] = bo
    def add_anchor(self, i, tag=None):
        a = anchor(tag or f'{self.name}_a{i}', self.base_mid(i), self.root); self.anchors[i] = a; return a

    def sleeve(self, i, color, f_on, f_off=None, r=0.30, strength=2.2, n=1, tag=None):
        """Translucent emissive sleeve around bases i..i+n-1 (codon highlight), visible between frames."""
        m = mat_translucent(color, alpha=0.09, emit=strength * 0.5, name=f'{self.name}_sl{i}', rough=0.4)     # a window of light, never a slab: the bases inside must stay readable
        p0 = self.axis_pt(i) - self.side * 0.05; p1 = self.base_tip(i) + self.side * 0.06
        if n > 1:
            c0 = (self.axis_pt(i) + self.axis_pt(i + n - 1)) / 2; bm = bmesh.new()
            L = (self.axis_pt(i + n - 1) - self.axis_pt(i)).length + 2 * r; h = (p1 - p0).length + 0.1
            res = bmesh.ops.create_cube(bm, size=1.0); bmesh.ops.scale(bm, vec=(L, h, 2 * r), verts=res['verts'])
            bmesh.ops.bevel(bm, geom=list(bm.edges), offset=r * 0.8, offset_type='OFFSET', segments=6, profile=0.5, affect='EDGES', clamp_overlap=True)
            bmesh.ops.transform(bm, matrix=unit_matrix(c0 + (p0 + p1) / 2 - self.axis_pt(i), self.ang), verts=list(bm.verts))
            o = mesh_obj(tag or f'{self.name}_sleeve{i}', bm, m)
        else: o = capsule_obj(tag or f'{self.name}_sleeve{i}', p0, p1, r, m, seg=20, ring=10)
        parent(o, self.root)
        try: o.visible_shadow = False
        except Exception: pass
        if f_off is None: hide_until(o, f_on)
        else: show_between(o, f_on, f_off)
        self.sleeves[i] = o; return o

    def grow(self, rfps, t_start, t_per_base, from_i=0):
        """Nucleotides (individual build) appear one after another; the rail grows with them."""
        for i in range(from_i, self.N):
            f = F(t_start + (i - from_i) * t_per_base, rfps)
            if i in self.units:
                for c in self.units[i].children: hide_until(c, f)
        if self.rail:
            cu = self.rail.data; k0 = max(0.0, (2 * from_i) / max(1, 2 * self.N - 2))
            cu.bevel_factor_end = k0; cu.keyframe_insert('bevel_factor_end', frame=1); cu.keyframe_insert('bevel_factor_end', frame=F(t_start, rfps))
            cu.bevel_factor_end = 1.0; cu.keyframe_insert('bevel_factor_end', frame=F(t_start + (self.N - from_i) * t_per_base, rfps)); lin_id(cu)
    def all_objects(self):
        out = ([self.rail] if self.rail else []) + [o for o in self.bases.values()] + list(self.sleeves.values())
        for u in self.units.values(): out += list(u.children)
        return list(dict.fromkeys(out))
    def hide_all_until(self, f):
        for o in self.all_objects(): hide_until(o, f)

# ================================================================= amino acids (distinct side chains) and chains
def _ball(bm, p, r, mi=0, sub=2):
    res = bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r, matrix=Matrix.Translation(Vector(p)))
    for v in res['verts']:
        for f in v.link_faces: f.material_index = mi
def _stick(bm, p0, p1, r, mi=0):
    vs = capsule_into(bm, p0, p1, r, 12, 6)
    for v in vs:
        for f in v.link_faces: f.material_index = mi
def _ring(bm, n, c, r, normal, mi=0):
    tmp = bmesh.new(); _ring_into(tmp, n, 0, 0, r, 0.05, 0.0, hole=0.5, atoms=0.02, mi=mi)
    q = Vector(normal).to_track_quat('X', 'Y').to_matrix().to_4x4()
    merge_into(bm, tmp, Matrix.Translation(Vector(c)) @ q)

SIDE_CHAIN = {   # amino -> list of parts in the bead's local frame (bead radius r = 1.0 here, scaled later): balls, sticks, rings
    'Gly': [], 'Ala': [('b', (0, 0, 1.25), 0.36)],
    'Val': [('s', (0, 0, 0.9), (0, 0, 1.4), 0.12), ('b', (0.45, 0, 1.75), 0.32), ('b', (-0.45, 0, 1.75), 0.32)],
    'Leu': [('s', (0, 0, 0.9), (0, 0, 1.55), 0.12), ('b', (0, 0, 1.55), 0.28), ('b', (0.5, 0, 1.95), 0.3), ('b', (-0.5, 0, 1.95), 0.3)],
    'Ile': [('s', (0, 0, 0.9), (0.3, 0, 1.5), 0.12), ('b', (0.3, 0, 1.5), 0.3), ('b', (-0.4, 0, 1.6), 0.28), ('b', (0.55, 0, 2.05), 0.28)],
    'Pro': [('r', 5, (0, 0, 1.1), 0.5, (0, 1, 0))],
    'Phe': [('s', (0, 0, 0.9), (0, 0, 1.35), 0.12), ('r', 6, (0, 0, 1.95), 0.55, (0, 1, 0))],
    'Tyr': [('s', (0, 0, 0.9), (0, 0, 1.35), 0.12), ('r', 6, (0, 0, 1.95), 0.55, (0, 1, 0)), ('b', (0, 0, 2.75), 0.26, 2)],
    'Trp': [('s', (0, 0, 0.9), (0, 0, 1.3), 0.12), ('r', 5, (0, 0, 1.75), 0.45, (0, 1, 0)), ('r', 6, (0.55, 0, 2.35), 0.52, (0, 1, 0))],
    'His': [('s', (0, 0, 0.9), (0, 0, 1.3), 0.12), ('r', 5, (0, 0, 1.8), 0.48, (0, 1, 0))],
    'Ser': [('s', (0, 0, 0.9), (0, 0, 1.4), 0.12), ('b', (0, 0, 1.55), 0.28, 2)],
    'Thr': [('s', (0, 0, 0.9), (0, 0, 1.4), 0.12), ('b', (0.4, 0, 1.7), 0.28, 2), ('b', (-0.4, 0, 1.7), 0.28)],
    'Cys': [('s', (0, 0, 0.9), (0, 0, 1.4), 0.12), ('b', (0, 0, 1.6), 0.34, 3)],
    'Met': [('s', (0, 0, 0.9), (0, 0, 1.5), 0.12), ('b', (0, 0, 1.5), 0.24), ('s', (0, 0, 1.5), (0.35, 0, 2.05), 0.12), ('b', (0.35, 0, 2.05), 0.34, 3), ('b', (0.75, 0, 2.5), 0.24)],
    'Asp': [('s', (0, 0, 0.9), (0, 0, 1.45), 0.12), ('b', (0, 0, 1.45), 0.24), ('b', (0.42, 0, 1.85), 0.26, 2), ('b', (-0.42, 0, 1.85), 0.26, 2)],
    'Glu': [('s', (0, 0, 0.9), (0, 0, 1.5), 0.12), ('b', (0, 0, 1.5), 0.24), ('s', (0, 0, 1.5), (0, 0, 2.05), 0.12), ('b', (0, 0, 2.05), 0.24), ('b', (0.42, 0, 2.45), 0.26, 2), ('b', (-0.42, 0, 2.45), 0.26, 2)],
    'Asn': [('s', (0, 0, 0.9), (0, 0, 1.45), 0.12), ('b', (0, 0, 1.45), 0.24), ('b', (0.42, 0, 1.85), 0.26, 2), ('b', (-0.42, 0, 1.85), 0.26, 4)],
    'Gln': [('s', (0, 0, 0.9), (0, 0, 1.5), 0.12), ('b', (0, 0, 1.5), 0.24), ('s', (0, 0, 1.5), (0, 0, 2.05), 0.12), ('b', (0, 0, 2.05), 0.24), ('b', (0.42, 0, 2.45), 0.26, 2), ('b', (-0.42, 0, 2.45), 0.26, 4)],
    'Lys': [('s', (0, 0, 0.9), (0, 0, 2.3), 0.12), ('b', (0, 0, 1.4), 0.2), ('b', (0, 0, 1.85), 0.2), ('b', (0, 0, 2.3), 0.2), ('b', (0, 0, 2.75), 0.32, 4)],
    'Arg': [('s', (0, 0, 0.9), (0, 0, 2.2), 0.12), ('b', (0, 0, 1.4), 0.2), ('b', (0, 0, 1.85), 0.2), ('b', (0, 0, 2.3), 0.26, 4), ('b', (0.45, 0, 2.75), 0.26, 4), ('b', (-0.45, 0, 2.75), 0.26, 4)],
}
def m_atom(kind):
    return {2: M('atomO', lambda: mat_gloss((0.92, 0.22, 0.18), rough=0.3, coat=0.5, name='atomO')), 3: M('atomS', lambda: mat_gloss((0.98, 0.86, 0.20), rough=0.3, coat=0.5, name='atomS')),
            4: M('atomN', lambda: mat_gloss((0.30, 0.42, 0.98), rough=0.3, coat=0.5, name='atomN'))}[kind]

def amino_acid(name, aa, loc=(0, 0, 0), r=0.27, rot=(0, 0, 0), mat=None):
    """One amino acid: the alpha-carbon bead in its palette colour with a distinct side chain (balls / sticks / rings with
    red O, yellow S, blue N atoms).  Returns the root empty (bead + side chain are its children)."""
    root = empty(name, loc); root.rotation_euler = rot
    bm = bmesh.new(); _ball(bm, (0, 0, 0), 1.0, 0, 3)
    for part in SIDE_CHAIN.get(aa, SIDE_CHAIN['Ala']):
        if part[0] == 'b': _ball(bm, part[1], part[2], part[3] if len(part) > 3 else 0)
        elif part[0] == 's': _stick(bm, part[1], part[2], part[3], 0)
        elif part[0] == 'r': _ring(bm, part[1], part[2], part[3], part[4], 0)
    if SIDE_CHAIN.get(aa): _stick(bm, (0, 0, 0.6), (0, 0, 1.0), 0.12, 0)
    bmesh.ops.scale(bm, vec=(r, r, r), verts=list(bm.verts))
    o = mesh_obj_multi(name + '_m', bm, [mat or m_amino(aa), m_atom(2), m_atom(3), m_atom(4)]); parent(o, root)
    root['bead'] = o.name
    return root

class Chain:
    """Amino-acid chain: each residue is an amino_acid() root (bead + side chain), joined by peptide links refitted per frame;
    positions come from a callable pos_fn(k, t).  Side chains point away from the chain's local bend."""
    def __init__(self, name, aminos, r=0.27, r_link=0.08, link_mat=None, hd=True):
        self.name = name; self.beads = []; self.links = []; self.aminos = list(aminos); self.r = r
        lm = link_mat or M('peptide', lambda: mat_gloss(PEPTIDE, rough=0.3, coat=0.5, name='peptide'))
        for k, a in enumerate(self.aminos):
            if hd: self.beads.append(amino_acid(f'{name}_b{k}', a, (0, 0, 0), r=r))
            else: self.beads.append(sphere(f'{name}_b{k}', r, (0, 0, 0), seg=40, ring=20, mat=m_amino(a)))
            if k: self.links.append(unit_link(f'{name}_l{k}', r_link, lm))
    def pose(self, pts, frame=None, ups=None):
        for k, p in enumerate(pts):
            b = self.beads[k]; b.location = p
            if b.type == 'EMPTY':
                nxt = Vector(pts[min(k + 1, len(pts) - 1)]) - Vector(pts[max(k - 1, 0)])
                side = (ups[k] if ups is not None else Vector((0, -1, 0)))
                sd = Vector(side) - nxt.normalized() * Vector(side).dot(nxt.normalized()) if nxt.length > 1e-6 else Vector(side)
                if sd.length < 1e-4: sd = Vector((0, 0, 1))
                b.rotation_euler = sd.normalized().to_track_quat('Z', 'Y').to_euler()
                if frame is not None: b.keyframe_insert('rotation_euler', frame=frame)
            if frame is not None: b.keyframe_insert('location', frame=frame)
            if k: fit_link(self.links[k - 1], pts[k - 1], p, frame)
    def hide_until(self, k, f):
        b = self.beads[k]
        for o in ([b] + list(b.children)): hide_until(o, f)
        if k: hide_until(self.links[k - 1], f)
    def objects(self):
        out = []
        for b in self.beads: out += [b] + list(b.children)
        return out + list(self.links)
    def animate(self, pos_fn, rfps, t0, t1, step=1, ups=None):
        f0, f1 = F(t0, rfps), F(t1, rfps)
        frames = list(range(f0, f1 + 1, step))
        if frames[-1] != f1: frames.append(f1)
        for f in frames:
            t = (f - 1) / rfps; self.pose([pos_fn(k, t) for k in range(len(self.beads))], f, ups=ups)
        for b in self.beads: lin_id(b)
        for l in self.links: lin_id(l)

def fold_path(n, seed=2, box=1.6, step=0.5):
    """A compact folded conformation: a smooth random walk confined to a box, spacing ~step between beads."""
    rnd = random.Random(seed); pts = wander_pts(rnd, (0, 0, 0), n - 1, step, ((-box, box), (-box * 0.8, box * 0.8), (-box, box)), smoothness=0.55)
    c = sum((Vector(p) for p in pts), Vector()) / len(pts); return [Vector(p) - c for p in pts]

def straight_path(n, step=0.5, origin=(0, 0, 0), direction=(1, 0, 0), sag=0.0):
    d = Vector(direction).normalized(); o = Vector(origin) - d * step * (n - 1) / 2
    return [o + d * step * k + Vector((0, 0, -sag * math.sin(math.pi * k / max(1, n - 1)))) for k in range(n)]

def peptide_glow(name, p0, p1, f_on, f_off=None, r=0.13, color=(1.0, 0.85, 0.45), strength=5.0):
    """Emissive sleeve on a peptide bond between two residues."""
    o = capsule_obj(name, p0, p1, r, mat_translucent(color, alpha=0.55, emit=strength, name=name + '_m'), seg=16, ring=8)
    try: o.visible_shadow = False
    except Exception: pass
    if f_off is None: hide_until(o, f_on)
    else: show_between(o, f_on, f_off)
    return o

# ================================================================= stage / camera
def soft_light(loc, energy, size=4.0, color=(0.85, 0.92, 1.0), name='Soft', target=None):
    return light('AREA', loc, energy, color, name, size=size, target=target)

def cam_path(keys, rfps, lens=45, ease=True):
    """Multi-key camera: keys = [(t_sec, cam_loc, target_loc), ...] -> camera + target with eased keyframes."""
    cam, tgt = camera(keys[0][1], keys[0][2], lens=lens)
    for t, loc, tl in keys:
        f = F(t, rfps); kf(cam, 'location', f, loc); kf(tgt, 'location', f, tl)
    (kf_ease if ease else kf_lin)(cam); (kf_ease if ease else kf_lin)(tgt)
    return cam, tgt

def spin(o, rfps, dur, rate=0.15, axis=0, f0=1, start=0.0):
    """Constant slow rotation of an object about one local axis (rate in turns/second of narration time)."""
    e = [0, 0, 0]; e[axis] = start; kf(o, 'rotation_euler', f0, tuple(e))
    e[axis] = start + 2 * math.pi * rate * dur; kf(o, 'rotation_euler', F(dur, rfps), tuple(e)); kf_lin(o)

def lens_zoom(cam, rfps, keys):
    """Slow lens zoom: keys = [(t, focal_mm), ...]."""
    for t, mm in keys: cam.data.lens = mm; cam.data.keyframe_insert('lens', frame=F(t, rfps))
    ease_id(cam.data)

# ================================================================= keyed materials, instancing, arrows, sleeves
def upd(): bpy.context.view_layer.update()
def key_light(L, f, energy):
    L.data.energy = energy; L.data.keyframe_insert('energy', frame=f)

def key_socket(sock, f, v):
    sock.default_value = v; sock.keyframe_insert('default_value', frame=f)

def key_emission(m, f, strength, color=None):
    """Keyframe a Principled material's emission strength (and colour) on frame f; ease later with ease_id(m.node_tree)."""
    p = m.node_tree.nodes.get('Principled BSDF')
    if p is None: return
    if color is not None: key_socket(p.inputs['Emission Color'], f, (*color, 1))
    key_socket(p.inputs['Emission Strength'], f, strength)

def pulse(m, rfps, t, color, peak=3.0, base=0.0, rise=0.25, fall=0.9):
    """A soft emission pulse on a material at narration time t."""
    key_emission(m, F(t - rise, rfps), base, color); key_emission(m, F(t, rfps), peak, color); key_emission(m, F(t + fall, rfps), base, color)
    ease_id(m.node_tree)

def hold_glow(m, rfps, t0, t1, color, strength=2.0, rise=0.35):
    key_emission(m, F(t0 - rise, rfps), 0.0, color); key_emission(m, F(t0, rfps), strength, color)
    key_emission(m, F(t1, rfps), strength, color); key_emission(m, F(t1 + rise, rfps), 0.0, color); ease_id(m.node_tree)

def mat_rim2(color, rim, a_center=0.12, a_rim=0.85, emit=2.0, name='rim', blend=0.35, rough=0.25, bump=0.0, bump_scale=30.0, cull=True):
    """mat_rim with the node names stored on the material (for key_rim) and an optional fine bump (lipid-head micro-detail)."""
    m = mat_rim(color, rim, a_center=a_center, a_rim=a_rim, emit=emit, name=name, blend=blend, rough=rough)
    nt = m.node_tree; n = nt.nodes; p = n.get('Principled BSDF')
    mr = next(x for x in n if x.bl_idname == 'ShaderNodeMapRange'); mul = next(x for x in n if x.bl_idname == 'ShaderNodeMath')
    m['mr'] = mr.name; m['mul'] = mul.name
    if bump:
        tc = n.new('ShaderNodeTexCoord'); vor = n.new('ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = bump_scale
        bmp = n.new('ShaderNodeBump'); bmp.inputs['Strength'].default_value = bump
        nt.links.new(tc.outputs['Object'], vor.inputs['Vector']); nt.links.new(vor.outputs['Distance'], bmp.inputs['Height']); nt.links.new(bmp.outputs['Normal'], p.inputs['Normal'])
    try: m.use_backface_culling = cull
    except Exception: pass
    return m

def key_rim(m, f, a_center=None, emit=None):
    n = m.node_tree.nodes
    if a_center is not None and 'mr' in m: key_socket(n[m['mr']].inputs['To Min'], f, a_center)
    if emit is not None and 'mul' in m: key_socket(n[m['mul']].inputs[1], f, emit)

def crossing(m, rfps, t_cross, a_hi=0.75, emit_hi=6.0, a_lo=0.12, emit_lo=1.4, pre=0.9, post=0.5):
    """Make a membrane pass-through visible: its facing-alpha and glow rise as the camera reaches it, drop once inside."""
    key_rim(m, F(t_cross - pre, rfps), a_lo, emit_lo); key_rim(m, F(t_cross - 0.1, rfps), a_hi, emit_hi)
    key_rim(m, F(t_cross + post, rfps), 0.0, 0.3); ease_id(m.node_tree)

def link_dup(o, name, loc=None, rot=None, scale=None, parent_to=None):
    """Instance (shared mesh/curve data) of an object; no modifiers, so bake_mods() the source first if it has any."""
    d = bpy.data.objects.new(name, o.data); bpy.context.collection.objects.link(d)
    if loc is not None: d.location = loc
    if rot is not None: d.rotation_euler = rot
    if scale is not None: d.scale = scale
    if parent_to is not None: parent(d, parent_to)
    return d

def bake_mods(o):
    """Replace an object's mesh by its evaluated mesh (modifiers applied) so instances share the detailed geometry."""
    if not o.modifiers: return o
    dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    for m in o.data.materials: me.materials.append(m)
    old = o.data; o.data = me
    for mod in list(o.modifiers): o.modifiers.remove(mod)
    for pl in me.polygons: pl.use_smooth = True
    try: bpy.data.meshes.remove(old)
    except Exception: pass
    return o

def dup_tree(objs, name, loc, rot=(0, 0, 0), scale=1.0):
    """Instance a group of (baked) mesh/curve objects under a new root empty."""
    root = empty(name, loc); root.rotation_euler = rot; root.scale = (scale, scale, scale); out = []
    for k, o in enumerate(objs):
        d = link_dup(o, f'{name}_{k}', loc=tuple(o.location), rot=tuple(o.rotation_euler), scale=tuple(o.scale), parent_to=root); out.append(d)
    return root, out

def arrow3d(name, loc, direction, L=0.7, r=0.045, color=(1, 1, 1), strength=3.0, mat=None):
    """Small emissive 3D arrow (shaft + cone) pointing along direction from loc: 5'->3' markers."""
    d = Vector(direction).normalized(); m = mat or mat_glow(color, strength=strength, name=name + '_m')
    bm = bmesh.new(); capsule_into(bm, (0, 0, 0), (0, 0, L * 0.68), r, 12, 6)
    res = bmesh.ops.create_cone(bm, cap_ends=True, segments=18, radius1=r * 2.6, radius2=0.0, depth=L * 0.34)
    bmesh.ops.translate(bm, vec=(0, 0, L * 0.68 + L * 0.17), verts=res['verts'])
    o = mesh_obj(name, bm, m); o.location = loc; o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    try: o.visible_shadow = False
    except Exception: pass
    return o

def glow_sleeve(name, p0, p1, r, color, f_on=None, f_off=None, strength=2.0, alpha=0.30):
    o = capsule_obj(name, p0, p1, r, mat_translucent(color, alpha=alpha, emit=strength, name=name + '_m', rough=0.4), seg=24, ring=12)
    try: o.visible_shadow = False
    except Exception: pass
    if f_on is not None and f_off is not None: show_between(o, f_on, f_off)
    elif f_on is not None: hide_until(o, f_on)
    return o

def beam(name, p0, p1, r=0.05, color=(1.0, 0.8, 0.4), strength=4.0, f_on=None, f_off=None, alpha=0.7):
    return glow_sleeve(name, p0, p1, r, color, f_on, f_off, strength=strength, alpha=alpha)

def scale_in(o, rfps, t, dur=0.5, final=1.0):
    kf(o, 'scale', 1, (0.001, 0.001, 0.001)); kf(o, 'scale', F(t, rfps), (0.001, 0.001, 0.001)); kf(o, 'scale', F(t + dur, rfps), (final, final, final)); kf_ease(o)
def scale_out(o, rfps, t, dur=0.5, base=1.0):
    kf(o, 'scale', F(t, rfps), (base, base, base)); kf(o, 'scale', F(t + dur, rfps), (0.001, 0.001, 0.001)); kf_ease(o)
def move(o, rfps, keys, ease=True):
    for t, p in keys: kf(o, 'location', F(t, rfps), p)
    (kf_ease if ease else kf_lin)(o)
def rot_keys(o, rfps, keys, ease=True):
    for t, r in keys: kf(o, 'rotation_euler', F(t, rfps), r)
    (kf_ease if ease else kf_lin)(o)
def drift(o, rfps, dur, amp=0.15, seed=1, period=3.0):
    rnd = random.Random(seed); base = Vector(o.location); ph = rnd.uniform(0, 6.28)
    for k in range(int(dur / 0.5) + 2):
        t = min(dur, k * 0.5); kf(o, 'location', F(t, rfps), tuple(base + Vector((amp * math.sin(2 * math.pi * t / period + ph), amp * 0.6 * math.cos(2 * math.pi * t / (period * 1.3) + ph), amp * 0.8 * math.sin(2 * math.pi * t / (period * 0.8) + ph * 2)))))
    kf_ease(o)

# ================================================================= organic blobs (metaball -> mesh)
def blob(name, elements, mat, loc=(0, 0, 0), rot=(0, 0, 0), res=0.09, disp=0.0, disp_scale=0.6, subd=1, seed=0, disp2=0.0, disp2_scale=0.18):
    """Smooth organic body from metaball elements [(x, y, z, r), ...] converted to a mesh (no CSG seams), optional
    noise displacement for a sculpted skin (a second, finer displacement adds pores / grain), subdivision + smooth shading."""
    mb = bpy.data.metaballs.new(name + '_mb'); mb.resolution = res; mb.render_resolution = res; mb.threshold = 0.6
    for (x, y, z, r) in elements:
        el = mb.elements.new(); el.co = (x, y, z); el.radius = r; el.stiffness = 2.0
    mo = bpy.data.objects.new(name + '_mbo', mb); bpy.context.collection.objects.link(mo)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(mo.evaluated_get(dg))
    bpy.data.objects.remove(mo); bpy.data.metaballs.remove(mb)
    for pl in me.polygons: pl.use_smooth = True
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o); o.location = loc; o.rotation_euler = rot; setmat(o, mat)
    if disp:
        tx = bpy.data.textures.new(name + '_tx', 'CLOUDS'); tx.noise_scale = disp_scale
        try: tx.noise_depth = 2; tx.noise_basis = 'ORIGINAL_PERLIN'
        except Exception: pass
        md = o.modifiers.new('disp', 'DISPLACE'); md.texture = tx; md.strength = disp; md.mid_level = 0.5
    if subd: subsurf(o, subd, subd + 1)
    if disp2:
        tx2 = bpy.data.textures.new(name + '_tx2', 'VORONOI'); tx2.noise_scale = disp2_scale
        try: tx2.noise_intensity = 1.0
        except Exception: pass
        md2 = o.modifiers.new('disp2', 'DISPLACE'); md2.texture = tx2; md2.strength = disp2; md2.mid_level = 0.5
    return o

def rand_blob_elements(rnd, n, spread, r0, r1, squash=(1, 1, 1)):
    out = [(0, 0, 0, r1)]
    for k in range(n):
        v = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))).normalized() * spread * rnd.uniform(0.4, 1.0)
        out.append((v.x * squash[0], v.y * squash[1], v.z * squash[2], rnd.uniform(r0, r1)))
    return out

def mat_grain(color, rough=0.42, sss=0.3, coat=0.25, name='grain', scale=18.0, bump=0.35, spot=None):
    """Organic surface with a fine noise bump + subtle colour mottling (rRNA-like grain on the ribosome, enzyme skins)."""
    m = mat_organic(color, rough=rough, sss=sss, coat=coat, name=name); nt = m.node_tree; n = nt.nodes; p = n.get('Principled BSDF')
    tc = n.new('ShaderNodeTexCoord'); noise = n.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = scale; noise.inputs['Detail'].default_value = 4.0; noise.inputs['Roughness'].default_value = 0.6
    bmp = n.new('ShaderNodeBump'); bmp.inputs['Strength'].default_value = bump
    nt.links.new(tc.outputs['Object'], noise.inputs['Vector']); nt.links.new(noise.outputs['Fac'], bmp.inputs['Height']); nt.links.new(bmp.outputs['Normal'], p.inputs['Normal'])
    if spot:
        ramp = n.new('ShaderNodeValToRGB'); e = ramp.color_ramp.elements; e[0].position = 0.42; e[0].color = (*color, 1); e[1].position = 0.62; e[1].color = (*spot, 1)
        nt.links.new(noise.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], p.inputs['Base Color'])
    return m

# ================================================================= enzymes and protein heroes
def polymerase(name='Pol', loc=(0, 0, 0), s=1.0, rot=(0, 0, 0)):
    """RNA polymerase: a sculpted multi-lobed clamp around a channel along X (the helix threads through it): a crab-claw body
    of lobes around the axis, two hinged jaws (top / bottom, animatable via root['jaw_t'] / root['jaw_b']) that close on the
    DNA, a rudder lobe, a fine-grained skin.  Returns the root empty (children: Body, JawT, JawB, Rudder)."""
    rnd = random.Random(3); root = empty(name, loc); root.rotation_euler = rot
    m = mat_grain(POL, rough=0.38, sss=0.35, coat=0.35, name=name + '_m', scale=14.0, bump=0.3, spot=POL_2)
    els = []
    for a in [k * 2 * math.pi / 9 for k in range(9)]:                     # ring of lobes around the helix axis (x)
        if -0.35 < math.sin(a) < 0.35 and math.cos(a) > 0: continue          # leave the front (toward -y) partly open for the jaws
        els.append((rnd.uniform(-0.3, 0.3) * s, 1.55 * s * math.cos(a), 1.55 * s * math.sin(a), rnd.uniform(0.72, 0.95) * s))
    els += [(0.9 * s, 0.4 * s, 1.9 * s, 0.85 * s), (-0.9 * s, -0.4 * s, -1.9 * s, 0.8 * s), (0.2 * s, 1.4 * s, -1.2 * s, 0.7 * s), (-0.6 * s, 1.9 * s, 0.4 * s, 0.75 * s)]
    body = blob(name + 'Body', els, m, (0, 0, 0), res=0.10 * s, disp=0.05 * s, disp_scale=0.9 * s, subd=1, disp2=0.018 * s, disp2_scale=0.22 * s); parent(body, root)
    jt = blob(name + 'JawT', [(0, -1.5 * s, 1.35 * s, 0.75 * s), (0.5 * s, -1.9 * s, 1.0 * s, 0.55 * s), (-0.5 * s, -1.8 * s, 1.1 * s, 0.5 * s)], m, (0, 0, 0), res=0.1 * s, disp=0.04 * s, disp_scale=0.7 * s, subd=1)
    jb = blob(name + 'JawB', [(0, -1.5 * s, -1.35 * s, 0.75 * s), (0.5 * s, -1.9 * s, -1.0 * s, 0.55 * s), (-0.5 * s, -1.7 * s, -1.15 * s, 0.5 * s)], m, (0, 0, 0), res=0.1 * s, disp=0.04 * s, disp_scale=0.7 * s, subd=1)
    parent(jt, root); parent(jb, root); root['jaw_t'] = jt.name; root['jaw_b'] = jb.name
    rud = blob(name + 'Rudder', [(-1.6 * s, 0.9 * s, 0.9 * s, 0.55 * s), (-2.1 * s, 1.3 * s, 1.3 * s, 0.4 * s)], m, (0, 0, 0), res=0.1 * s, disp=0.04 * s, disp_scale=0.6 * s, subd=1); parent(rud, root)
    return root

def jaws(root, rfps, keys):
    """Open (1) / close (0) the polymerase jaws over time: keys = [(t, open), ...]."""
    jt, jb = bpy.data.objects[root['jaw_t']], bpy.data.objects[root['jaw_b']]
    for t, op in keys:
        kf(jt, 'rotation_euler', F(t, rfps), (-0.55 * op, 0, 0)); kf(jb, 'rotation_euler', F(t, rfps), (0.55 * op, 0, 0))
    kf_ease(jt); kf_ease(jb)

def ribosome(name='Ribo', loc=(0, 0, 0), s=1.0, translucent_large=True, gap=0.55, sites=True):
    """Two-subunit ribosome around an mRNA channel along X at z = 0: the large subunit above (lavender, rRNA-grained, with
    the polypeptide exit tunnel on top), the small subunit below (rose: a head lobe and a body lobe with the mRNA cleft
    between them), and three tRNA site pads E / P / A (violet / amber / mint rings) on the interface.
    Returns root, large, small, sites(dict A/P/E -> pad object)."""
    rnd = random.Random(7)
    large = [(0, 0, 1.45 * s, 1.55 * s), (1.2 * s, 0.2 * s, 1.5 * s, 1.1 * s), (-1.25 * s, -0.1 * s, 1.55 * s, 1.15 * s), (0.2 * s, 0.9 * s, 2.2 * s, 1.0 * s), (-0.4 * s, -0.8 * s, 2.1 * s, 0.95 * s),
             (0.6 * s, 0.1 * s, 2.9 * s, 0.85 * s), (-0.7 * s, 0.5 * s, 2.7 * s, 0.8 * s), (1.6 * s, -0.6 * s, 2.3 * s, 0.6 * s), (-1.7 * s, 0.7 * s, 2.2 * s, 0.55 * s)]
    small = [(0.35 * s, 0, -1.05 * s, 1.1 * s), (1.5 * s, 0.1 * s, -0.95 * s, 0.85 * s), (0.9 * s, 0.6 * s, -1.4 * s, 0.7 * s), (0.2 * s, -0.7 * s, -1.4 * s, 0.7 * s),      # body
             (-1.35 * s, 0.0, -0.95 * s, 0.85 * s), (-1.9 * s, 0.3 * s, -0.7 * s, 0.5 * s), (-1.5 * s, -0.5 * s, -1.3 * s, 0.5 * s)]                                       # head (a cleft between head and body carries the mRNA)
    if translucent_large: ml = mat_rim2(RIBO_L, (0.78, 0.65, 1.0), a_center=0.5, a_rim=0.96, emit=0.8, name=name + '_L', blend=0.3, rough=0.32, bump=0.25, bump_scale=18.0, cull=True)
    else: ml = mat_grain(RIBO_L, rough=0.4, sss=0.3, coat=0.3, name=name + '_L', scale=16.0, bump=0.35, spot=(0.62, 0.50, 0.95))
    ms = mat_grain(RIBO_S, rough=0.42, sss=0.3, coat=0.3, name=name + '_S', scale=16.0, bump=0.35, spot=(0.98, 0.66, 0.82))
    root = empty(name, loc)
    L = blob(name + 'Large', large, ml, (0, 0, gap / 2), res=0.11 * s, disp=0.07 * s, disp_scale=1.1 * s, subd=1, disp2=0.02 * s, disp2_scale=0.25 * s); parent(L, root)
    S = blob(name + 'Small', small, ms, (0, 0, -gap / 2), res=0.11 * s, disp=0.06 * s, disp_scale=1.0 * s, subd=1, disp2=0.02 * s, disp2_scale=0.25 * s); parent(S, root)
    tun = obj_add('torus', name + 'Tunnel', major_radius=0.30 * s, minor_radius=0.09 * s, major_segments=48, minor_segments=16, location=(-0.3 * s, 0.1 * s, gap / 2 + 3.15 * s))
    setmat(tun, mat_lit((0.85, 0.75, 1.0), emit=0.6, rough=0.3, name=name + '_tun')); smooth(tun); parent(tun, root)
    out = {}
    if sites:
        for key, x in (('E', -0.85 * s), ('P', 0.0), ('A', 0.85 * s)):
            pad = obj_add('torus', f'{name}Site{key}', major_radius=0.26 * s, minor_radius=0.05 * s, major_segments=40, minor_segments=12, location=(x, -0.05 * s, -gap / 2 + 0.05 * s))
            setmat(pad, mat_lit(SITE[key], emit=1.6, rough=0.3, name=f'{name}_site{key}')); smooth(pad); parent(pad, root); out[key] = pad
            try: pad.visible_shadow = False
            except Exception: pass
    return root, L, S, out

def enzyme(name='Enz', loc=(0, 0, 0), s=1.0, pocket=True):
    """A globular enzyme with an active-site pocket (a notch on the -y face, lit) and a fine-grained skin."""
    rnd = random.Random(11); els = rand_blob_elements(rnd, 9, 1.0 * s, 0.55 * s, 0.9 * s, squash=(1.2, 1.0, 0.85))
    els += [(0.7 * s, -0.9 * s, 0.3 * s, 0.55 * s), (-0.7 * s, -0.9 * s, 0.2 * s, 0.55 * s), (0, -0.4 * s, 0.9 * s, 0.5 * s)]   # rim of the pocket
    m = mat_grain((0.95, 0.62, 0.2), rough=0.4, sss=0.35, coat=0.35, name=name + '_m', scale=12.0, bump=0.3, spot=(0.98, 0.78, 0.35))
    o = blob(name, els, m, loc, res=0.1 * s, disp=0.06 * s, disp_scale=0.8 * s, subd=1, disp2=0.02 * s, disp2_scale=0.2 * s)
    return o

def haemoglobin(name='Hb', loc=(0, 0, 0), s=1.0, spread=1.0, o2=True, sickle=False):
    """Haemoglobin: four globin chains (2 alpha crimson, 2 beta indigo), each a folded tube whose longer segments coil into
    alpha helices, wrapped around a haem: a square porphyrin ring plate with four pyrrole rings, the orange iron atom and an
    O2 pair glowing on it.  Chains sit on per-lobe roots around a central pocket (animate `spread` by moving them).
    sickle=True stretches the chains and adds a sticky tail (the mutant that polymerises).  Returns root, lobe roots, O2."""
    root = empty(name, loc); lobes = []; rnd = random.Random(21)
    dirs = [Vector((1, 0.35, 0.5)), Vector((-1, -0.35, 0.5)), Vector((0.35, -1, -0.5)), Vector((-0.35, 1, -0.5))]
    cols = [HB_ALPHA, HB_ALPHA, HB_BETA, HB_BETA]
    heme_m = M('heme', lambda: mat_gloss(HEME, rough=0.3, coat=0.4, name='heme')); fe_m = M('iron', lambda: mat_gloss(IRON, rough=0.25, coat=0.5, name='iron'))
    for k, (d, c) in enumerate(zip(dirs, cols)):
        d = d.normalized(); lr = empty(f'{name}_lobe{k}', tuple(d * 0.95 * s * spread)); parent(lr, root); lr['dir'] = tuple(d)
        path = fold_path(7, seed=30 + k, box=0.55 * s, step=0.5 * s)
        if sickle: path = [Vector((p.x * 1.7, p.y * 0.85, p.z * 0.85)) for p in path] + [Vector((1.4 * s, 0.3 * s, 0.1 * s)), Vector((1.9 * s, 0.5 * s, 0.2 * s))]
        pts = []
        for j in range(len(path) - 1):
            a, b = path[j], path[j + 1]; seg = b - a; Lseg = seg.length
            if j % 3 == 1 and Lseg > 1e-4:          # every third segment coils into an alpha helix
                q = seg.normalized().to_track_quat('Z', 'Y').to_matrix()
                for u in range(10):
                    f = u / 9; ang = 2 * math.pi * 1.6 * f
                    pts.append(a + q @ Vector((0.15 * s * math.cos(ang), 0.15 * s * math.sin(ang), Lseg * f)))
            else: pts += [a + seg * u / 3 for u in range(3)]
        pts.append(path[-1])
        cm = mat_grain(c, rough=0.36, sss=0.3, coat=0.35, name=f'{name}_gm{k}', scale=20.0, bump=0.2)
        tube = curve_obj(f'{name}_g{k}', pts, 0.12 * s, cm, res=4, kind='NURBS', bevel_res=6, order=3); parent(tube, lr)
        hp = -d * 0.45 * s; q = d.to_track_quat('X', 'Y').to_matrix().to_4x4()
        bm = bmesh.new(); _ring_into(bm, 4, 0, 0, 0.36 * s, 0.05 * s, math.pi / 4, hole=0.55, atoms=0.03 * s)
        for a in (0, 90, 180, 270): _ring_into(bm, 5, 0.28 * s * math.cos(math.radians(a)), 0.28 * s * math.sin(math.radians(a)), 0.10 * s, 0.045 * s, math.radians(a), hole=0.45, atoms=0.0)
        bmesh.ops.transform(bm, matrix=Matrix.Translation(hp) @ q, verts=list(bm.verts))
        hm = mesh_obj(f'{name}_heme{k}', bm, heme_m); parent(hm, lr)
        fe = sphere(f'{name}_fe{k}', 0.08 * s, tuple(hp), seg=24, ring=12, mat=fe_m); parent(fe, lr)
        lobes.append(lr)
    o2o = None
    if o2:
        o2o = empty(name + '_O2', (0, 0, 0)); parent(o2o, root); mo = mat_lit(O2, emit=1.8, name=name + '_o2m')
        a = sphere(name + '_Oa', 0.12 * s, (-0.10 * s, 0, 0), seg=24, ring=12, mat=mo); b = sphere(name + '_Ob', 0.12 * s, (0.10 * s, 0, 0), seg=24, ring=12, mat=mo); parent(a, o2o); parent(b, o2o)
    return root, lobes, o2o

def hb_spread(lobes, rfps, keys):
    """Animate the four globin lobes moving in/out along their directions: keys = [(t, spread), ...]."""
    for lr in lobes:
        d = Vector(lr['dir']); base = Vector(lr.location) / max(1e-6, Vector(lr.location).length)
        for t, sp in keys: kf(lr, 'location', F(t, rfps), tuple(d * 0.95 * sp * (Vector(lr.location).length / 0.95 if False else 1.0)))
        kf_ease(lr)

def keratin(name='Ker', loc=(0, 0, 0), s=1.0, n=5, length=4.0):
    """Keratin: a bundle of coiled-coil fibres (pairs of helices wound around each other) lying along X, wrapped in a thin sheath."""
    root = empty(name, loc); rnd = random.Random(5); mats = [mat_gloss((0.95, 0.86, 0.6), rough=0.35, coat=0.3, name=name + '_m1', sss=0.2), mat_gloss((0.85, 0.72, 0.45), rough=0.35, coat=0.3, name=name + '_m2', sss=0.2)]
    for k in range(n):
        a = 2 * math.pi * k / n; off = Vector((0, 0.42 * s * math.cos(a), 0.42 * s * math.sin(a))) if k else Vector((0, 0, 0))
        for j in (0, 1):
            pts = [Vector(p) + off for p in helix_pts(length * s, 0.13 * s, length / 1.4, n=int(48 * length), axis='x', phase=j * math.pi)]
            c = curve_obj(f'{name}_f{k}{j}', pts, 0.075 * s, mats[j], res=4, kind='POLY'); parent(c, root)
    return root

# ================================================================= tRNA
def trna(name, anticodon, amino, loc=(0, 0, 0), s=1.0, rot=(0, 0, 0), with_aa=True, anchors=False, hd=True, yaw=0.0, ac_scale=None, ac_pitch=None):
    """tRNA in its L shape, three scales of detail: silhouette = the L (anticodon arm rising from the foot, elbow, acceptor
    arm to +x); secondary forms = four PAIRED STEMS (anticodon, D, T, acceptor), each two separated sea-teal tubes with a
    short ladder of colour-coded base-pair rungs between them, the D / T / anticodon loops as rings, the elbow, the CCA
    tail (three real C-C-A beads on a curling tail) with the amino acid on top; micro-detail = a fine noise bump + coat on
    the tubes, atoms on the anticodon plates, 3D letters on the three anticodon bases (hd only).  Local frame: foot at the
    origin, arm to +x; the amino acid sits at (2.78, 0, 2.2) * s (ARM in the translation rig).
    Returns root, amino-acid root (or None), anticodon base objects."""
    rnd = random.Random(sum(ord(c) for c in anticodon))
    root = empty(name, loc); root.rotation_euler = rot
    arm = empty(name + '_arm', (0, 0, 0)); arm.rotation_euler = (0, 0, yaw); parent(arm, root); root['arm'] = arm.name   # the arm swings about z, the anticodon stays on the codon
    m1 = M('trna1', lambda: mat_grain(TRNA, rough=0.30, sss=0.15, coat=0.55, name='trna1', scale=26.0, bump=0.16))
    m2 = M('trna2', lambda: mat_grain(TRNA_2, rough=0.30, sss=0.15, coat=0.55, name='trna2', scale=26.0, bump=0.16))
    path = [(0, 0, 0.15), (0, 0, 0.9), (0.05, 0, 1.5), (0.35, 0, 1.95), (0.9, 0, 2.15), (1.55, 0, 2.2), (2.1, 0, 2.2)]
    pts = [Vector(p) * s for p in path]; SEP = 0.15 * s; RT = 0.066 * s
    fine = catmull(pts, 84); YH = Vector((0, 1, 0))
    def nrm(q, k):                                                       # in-plane normal of a polyline: the two strands sit side by side INSIDE the L plane, so the ladder reads from the front
        a = q[max(0, k - 1)]; b = q[min(len(q) - 1, k + 1)]; tg = (b - a); tg = tg.normalized() if tg.length > 1e-6 else Vector((0, 0, 1)); return tg.cross(YH).normalized()
    for j, (m, sg) in enumerate(((m1, -1), (m2, 1))):
        q = [fine[k] + nrm(fine, k) * SEP * sg for k in range(len(fine))]
        c = curve_obj(f'{name}_arm{j}', q, RT, m, res=3, kind='NURBS'); parent(c, arm)
    # paired stems: rung ladders (two colour-coded half-rungs per pair) on the anticodon stem, the acceptor stem, the D stem and the T stem
    seq_stem = 'GCAUGCUACGAU'; bms = {b: bmesh.new() for b in 'AUGC'}; n_r = [0]
    def rung(p, n, r=0.034 * s, d=SEP - 0.018 * s):
        b = seq_stem[n_r[0] % len(seq_stem)]; c = RNA_COMP[b]; n_r[0] += 1
        capsule_into(bms[b], p - n * d, p, r, 10, 5); capsule_into(bms[c], p, p + n * d, r, 10, 5)
    def in_ac(p): return p.x < 0.08 * s and 0.36 * s <= p.z <= 1.30 * s          # anticodon stem
    def in_acc(p): return 0.98 * s <= p.x <= 2.06 * s and p.z > 2.05 * s          # acceptor stem
    acc = 1e9
    for k in range(1, len(fine)):
        acc += (fine[k] - fine[k - 1]).length
        if (in_ac(fine[k]) or in_acc(fine[k])) and acc >= 0.19 * s: rung(fine[k], nrm(fine, k)); acc = 0.0
        elif not (in_ac(fine[k]) or in_acc(fine[k])): acc = 1e9
    dpts = [Vector((0.12, 0, 1.74)) * s, Vector((-0.10, 0, 1.63)) * s, Vector((-0.24, 0, 1.58)) * s]          # D stem: short double tube from the elbow toward the D loop
    tpts = [Vector((0.42, 0, 2.28)) * s, Vector((0.50, 0, 2.40)) * s, Vector((0.55, 0, 2.48)) * s]            # T stem: up from the elbow to the T loop
    for tag, spts in (('D', dpts), ('T', tpts)):
        for j, sg in enumerate((-1, 1)):
            c = curve_obj(f'{name}_{tag}stem{j}', [spts[k] + nrm(spts, k) * SEP * 0.75 * sg for k in range(3)], RT * 0.8, m1 if j == 0 else m2, res=3, kind='NURBS', order=3); parent(c, arm)
        for k in (0, 1): rung((spts[k] + spts[k + 1]) / 2, nrm(spts, k), r=0.028 * s, d=SEP * 0.75 - 0.016 * s)
    for b, bm in bms.items():
        if len(bm.verts): o = mesh_obj(f'{name}_rungs{b}', bm, m_base(b)); parent(o, arm)
    el = sphere(f'{name}_elbow', 0.19 * s, tuple(Vector((0.3, 0, 1.9)) * s), seg=32, ring=16, mat=m1); parent(el, arm)
    for nm, c, r, rot_ in (('_Dloop', (-0.32, 0, 1.55), 0.19, (math.pi / 2, 0, 0.35)), ('_Tloop', (0.55, 0, 2.48), 0.17, (math.pi / 2, 0, -0.3)), ('_ACloop', (0, 0, 0.16), 0.24, (math.pi / 2, 0, 0))):
        lp = obj_add('torus', name + nm, major_radius=r * s, minor_radius=0.075 * s, major_segments=40, minor_segments=14, location=tuple(Vector(c) * s)); lp.rotation_euler = rot_
        setmat(lp, m2); smooth(lp); parent(lp, root if nm == '_ACloop' else arm)
    bases = []; acs = ac_scale if ac_scale is not None else 0.55 * s; pitch = ac_pitch if ac_pitch is not None else 0.36 * s
    tm = M('ac_txt', lambda: mat_lit((0.98, 0.98, 1.0), emit=0.9, rough=0.3, name='ac_txt'))
    for k, b in enumerate(anticodon):
        x = (k - 1) * pitch
        if hd:
            bmb = plate_bmesh(b, 0.0, thick=0.08 * s, atoms=0.02 * s)      # built along -y from y=0
            bmesh.ops.scale(bmb, vec=(acs, acs, acs), verts=list(bmb.verts))
            bmesh.ops.rotate(bmb, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, 'X'), verts=list(bmb.verts))   # -y -> -z: plate hangs down, thickness stays along x (parallel to the codon plates)
            bmesh.ops.translate(bmb, vec=(x, 0, 0.05 * s), verts=list(bmb.verts))
            bo = mesh_obj(f'{name}_ac{k}', bmb, m_base(b))
            L_b = plate_len(b) * acs; sz = min(0.16 * s, 0.42 * L_b)     # the letter floats just in front of the plate's front edge (plates face +-x, the camera looks along +y), centred on the plate
            tx = text_obj(f'{name}_acl{k}', b, size=sz, mat=tm, loc=(x, -(RH * acs) - 0.04 * s, 0.05 * s - 0.5 * L_b), rot=(math.pi / 2, 0, 0), extrude=0.012 * s); parent(tx, root)
        else: bo = capsule_obj(f'{name}_ac{k}', (x, 0, 0.1 * s), (x, 0, -0.42 * s), 0.10 * s, m_base(b), seg=24, ring=12)
        parent(bo, root); bases.append(bo)
        if anchors: anchor(f'{name}_aca{k}', (x, 0, -0.28 * s), root)
    aa = None
    tail = [Vector((2.1, 0, 2.2 + SEP / s)) * s, Vector((2.32, 0, 2.2 + 0.5 * SEP / s)) * s, Vector((2.52, 0, 2.2)) * s, Vector((2.62, 0, 2.2)) * s]     # the 3' (outer) strand runs on as the CCA tail
    cca = curve_obj(f'{name}_cca', tail, RT * 0.7, m2, res=6); parent(cca, arm)
    for k in range(3):
        bd = sphere(f'{name}_cca{k}', 0.085 * s, tuple(tail[k] + Vector((0.04 * s, 0, 0))), seg=16, ring=8, mat=m_base('CCA'[k])); parent(bd, arm)
    if with_aa:
        aa = amino_acid(f'{name}_aa', amino, (2.78 * s, 0, 2.2 * s), r=0.26 * s, rot=(0, 0, 0)); parent(aa, arm)
        if anchors: anchor(f'{name}_aaa', (2.78 * s, 0, 2.55 * s), arm)
    return root, aa, bases

# ================================================================= chromatin, chromosomes, nuclear pores, nucleus, cells
def nucleosome_fibre(name, path, spacing=0.9, r_spool=0.22, r_fibre=0.032, wraps=1.65, seed=1, mat_f=None, mat_s=None, spool_scale=(1, 1, 0.62)):
    """'Beads on a string': the DNA fibre (thin tube) wraps ~1.65 turns around each histone spool placed every `spacing`
    along a smooth path, with straight linker DNA between spools.  Returns root, fibre curve, spools mesh."""
    rnd = random.Random(seed); root = empty(name, (0, 0, 0))
    fine = catmull([Vector(p) for p in path], max(60, int(len(path) * 12)))
    # arc-length resample
    acc = [0.0]
    for a, b in zip(fine[:-1], fine[1:]): acc.append(acc[-1] + (b - a).length)
    total = acc[-1]; n_sp = max(1, int(total / spacing)); centres = []; axes = []
    def at(sdist):
        for k in range(len(acc) - 1):
            if acc[k] <= sdist <= acc[k + 1]:
                u = (sdist - acc[k]) / max(1e-6, acc[k + 1] - acc[k]); return fine[k] * (1 - u) + fine[k + 1] * u, (fine[k + 1] - fine[k]).normalized()
        return fine[-1], (fine[-1] - fine[-2]).normalized()
    pts = []
    for j in range(n_sp):
        sd = (j + 0.5) * spacing; c, tng = at(sd)
        up = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))); ax = (up - tng * up.dot(tng)).normalized()   # spool axis perpendicular to the path
        centres.append(c); axes.append(ax); q = ax.to_track_quat('Z', 'Y').to_matrix()
        nsteps = 22
        for u in range(nsteps + 1):
            f = u / nsteps; ang = 2 * math.pi * wraps * f - math.pi * wraps
            pts.append(c + q @ Vector((r_spool * 1.25 * math.cos(ang), r_spool * 1.25 * math.sin(ang), (f - 0.5) * r_spool * 0.6)))
    fm = mat_f or M('chromfib', lambda: mat_gloss(CHROM, rough=0.3, coat=0.5, name='chromfib'))
    fibre = curve_obj(name + '_fibre', pts, r_fibre, fm, res=2, kind='POLY', bevel_res=4); parent(fibre, root)
    sm = mat_s or M('histone', lambda: mat_gloss(HISTONE, rough=0.35, coat=0.35, name='histone', sss=0.2))
    spools = spheres_mesh(name + '_spools', centres, r_spool, sm, subdiv=3, scale3=spool_scale, normals=axes); parent(spools, root)
    return root, fibre, spools, centres

def chromosome(name, loc, s=1.0, rot=(0, 0, 0), seed=1, mat=None, fibre=True):
    """Metaphase chromosome: two bent chromatids joined at the centromere, each arm a condensed core wound with a visible
    chromatin fibre (solenoid coils with nucleosome beads).  Returns root; root['objs'] lists the mesh/curve children."""
    rnd = random.Random(seed); m = mat or M('chrom', lambda: mat_organic(CHROM, rough=0.38, sss=0.3, coat=0.35, name='chrom', radius=(0.3, 0.4, 1.0)))
    root = empty(name, loc); root.rotation_euler = rot; objs = []
    arms = []
    for sg in (-1, 1):
        for k, (dx, dz) in enumerate(((0.18, 1.0), (0.18, -0.85))):
            top = Vector((sg * 0.25 * s + sg * dx * s, 0, dz * s)); mid = Vector((sg * 0.2 * s, 0, 0.08 * s * (1 if dz > 0 else -1)))
            arms.append((mid, top))
    bm = bmesh.new()
    for mid, top in arms: capsule_into(bm, mid, top, 0.16 * s, 24, 12)
    o = mesh_obj(name + '_body', bm, m); parent(o, root)
    tx = bpy.data.textures.new(name + '_tx', 'CLOUDS'); tx.noise_scale = 0.28 * s
    md = o.modifiers.new('disp', 'DISPLACE'); md.texture = tx; md.strength = 0.05 * s; md.mid_level = 0.5
    subsurf(o, 1, 2); objs.append(o)
    cen = sphere(name + '_cen', 0.2 * s, (0, 0, 0), seg=32, ring=16, mat=m, scale=(1.5, 1.0, 0.8)); parent(cen, root); objs.append(cen)
    if fibre:
        fm = M('chromfib', lambda: mat_gloss(CHROM, rough=0.3, coat=0.5, name='chromfib')); sm = M('histone', lambda: mat_gloss(HISTONE, rough=0.35, coat=0.35, name='histone', sss=0.2))
        fpts = []; beads = []; bn = []
        for mid, top in arms:
            d = top - mid; L = d.length; q = d.normalized().to_track_quat('Z', 'Y').to_matrix(); turns = L / (0.14 * s)
            n = int(turns * 14)
            for u in range(n + 1):
                f = u / n; ang = 2 * math.pi * turns * f
                p = mid + q @ Vector((0.21 * s * math.cos(ang), 0.21 * s * math.sin(ang), L * f)); fpts.append(p)
                if u % 4 == 0: beads.append(p); bn.append(q @ Vector((math.cos(ang), math.sin(ang), 0)))
            fpts.append(mid)
        fib = curve_obj(name + '_fibre', fpts, 0.028 * s, fm, res=2, kind='POLY', bevel_res=4); parent(fib, root); objs.append(fib)
        bd = spheres_mesh(name + '_beads', beads, 0.05 * s, sm, subdiv=1, scale3=(1, 1, 0.7), normals=bn); parent(bd, root); objs.append(bd)
    root['objs'] = [x.name for x in objs]
    return root

def chromosome_field(proto_root, n, rnd, centre, radius, s_range=(0.8, 1.2), avoid=None, name='Chr'):
    """n instances of a chromosome (baked meshes shared) drifting inside a sphere; returns the roots."""
    objs = [bpy.data.objects[x] for x in proto_root['objs']]
    for o in objs:
        if o.type == 'MESH': bake_mods(o)
    roots = []
    for k in range(n):
        while True:
            v = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))
            if 0.12 < v.length < 1.0 and (avoid is None or (Vector(centre) + v * radius - Vector(avoid[0])).length > avoid[1]): break
        r, out = dup_tree(objs, f'{name}{k}', tuple(Vector(centre) + v * radius), rot=(rnd.uniform(0, 3.1), rnd.uniform(0, 3.1), rnd.uniform(0, 3.1)), scale=rnd.uniform(*s_range))
        roots.append(r)
    return roots

def pore_complex(name, loc=(0, 0, 0), direction=(0, 0, 1), r=0.3, mats=None):
    """Nuclear pore complex (eight-fold symmetry): outer ring of eight spoke knobs, inner ring of eight smaller knobs, a
    central transporter ring, eight cytoplasmic filaments flaring outward and the nuclear basket (eight struts converging
    to a distal ring) on the inside.  One mesh, two material slots.  Local +z = outward (cytoplasm side)."""
    bm = bmesh.new()
    for j in range(8):
        a = 2 * math.pi * j / 8; c, s_ = math.cos(a), math.sin(a)
        _ball(bm, (r * c, r * s_, 0), r * 0.30, 0); _ball(bm, (r * 0.58 * c, r * 0.58 * s_, 0.05 * r), r * 0.17, 0)
        _stick(bm, (r * 0.95 * c, r * 0.95 * s_, r * 0.15), (r * 1.25 * c, r * 1.25 * s_, r * 1.05), r * 0.06, 1)     # cytoplasmic filaments
        _ball(bm, (r * 1.25 * c, r * 1.25 * s_, r * 1.05), r * 0.08, 1)
        _stick(bm, (r * 0.72 * c, r * 0.72 * s_, -r * 0.15), (r * 0.38 * c, r * 0.38 * s_, -r * 1.25), r * 0.05, 1)    # nuclear basket struts
    tmp = bmesh.new(); _ring_into(tmp, 16, 0, 0, r * 0.36, r * 0.12, 0.0, hole=0.55, atoms=0.0, mi=1, bevel=False)
    merge_into(bm, tmp, Matrix.Rotation(math.pi / 2, 4, 'Y'))
    tmp = bmesh.new(); _ring_into(tmp, 16, 0, 0, r * 0.42, r * 0.07, 0.0, hole=0.7, atoms=0.0, mi=1, bevel=False)
    merge_into(bm, tmp, Matrix.Translation((0, 0, -r * 1.28)) @ Matrix.Rotation(math.pi / 2, 4, 'Y'))
    mk = (mats or [M('pore_k', lambda: mat_gloss(PORE, rough=0.35, coat=0.4, name='pore_k', sss=0.2)), M('pore_f', lambda: mat_gloss(PORE_FIL, rough=0.35, coat=0.4, name='pore_f', sss=0.2))])
    o = mesh_obj_multi(name, bm, mk); o.location = loc; o.rotation_euler = Vector(direction).normalized().to_track_quat('Z', 'Y').to_euler()
    return o

def nucleus_hd(name='Nuc', loc=(0, 0, 0), r=2.6, pores=40, hole_dirs=(), seed=2, inside=False, pore_r=None, rim=None, a_center=0.16, a_rim=0.9, emit=1.2, bump=0.12):
    """Amethyst double-membrane nucleus: outer and inner envelopes (translucent fresnel rims, fine lipid bump), pore complexes
    instanced from one detailed eight-fold complex; real holes bored along hole_dirs (boolean) so the camera / mRNA can pass.
    Returns root, outer shell, inner shell, pore objects, hole cutters."""
    rnd = random.Random(seed); root = empty(name, loc)
    m_out = mat_rim2(NUC, rim or NUC_RIM, a_center=a_center, a_rim=a_rim, emit=emit, name=name + '_out', blend=0.32, rough=0.3, bump=bump, bump_scale=40.0, cull=not inside)
    m_in = mat_rim2(tuple(c * 0.8 for c in NUC), (0.62, 0.45, 0.95), a_center=a_center * 0.8, a_rim=a_rim * 0.8, emit=emit * 0.6, name=name + '_in', blend=0.32, rough=0.3, bump=bump, bump_scale=40.0, cull=not inside)
    outer = sphere(name + 'Shell', r, (0, 0, 0), seg=128, ring=64, mat=m_out); parent(outer, root)
    inner = sphere(name + 'Inner', r * 0.94, (0, 0, 0), seg=96, ring=48, mat=m_in); parent(inner, root)
    for o in (outer, inner):
        try: o.visible_shadow = False
        except Exception: pass
    dirs = list(hole_dirs)
    while len(dirs) < pores:
        v = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))).normalized()
        if all((v - Vector(h).normalized()).length > 0.42 for h in dirs): dirs.append(tuple(v))
    pr = pore_r or 0.075 * r; pos = []
    if dirs:
        proto = pore_complex(name + 'Pore0', tuple(Vector(dirs[0]).normalized() * r * 0.97), dirs[0], pr); parent(proto, root); pos = [proto]
    for k, d in enumerate(dirs[1:], 1):
        d = Vector(d).normalized(); p = link_dup(proto, f'{name}Pore{k}', loc=tuple(d * r * 0.97), rot=d.to_track_quat('Z', 'Y').to_euler(), parent_to=root); pos.append(p)
    holes = []
    for k, d in enumerate(hole_dirs):
        d = Vector(d).normalized()
        c = obj_add('cylinder', f'{name}Hole{k}', radius=pr * 0.62, depth=0.6 * r, vertices=48, location=tuple(d * r)); c.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
        c.hide_render = True; c.display_type = 'WIRE'
        try: c.visible_camera = False; c.visible_shadow = False
        except Exception: pass
        parent(c, root); holes.append(c)
        for sh in (outer, inner):
            mod = sh.modifiers.new(f'hole{k}', 'BOOLEAN'); mod.operation = 'DIFFERENCE'; mod.object = c
            try: mod.solver = 'EXACT'
            except Exception: pass
    if hole_dirs: smooth(outer, auto=True); smooth(inner, auto=True)
    return root, outer, inner, pos, holes

def cell_body(name='Cell', loc=(0, 0, 0), r=6.0, color=(0.02, 0.12, 0.26), rim=CYTO_RIM, bump=0.10, a_center=0.10, emit=1.4):
    """Translucent fresnel-rimmed cell membrane with a lipid-head bump the camera can fly through (keyable via crossing())."""
    o = sphere(name, r, loc, seg=128, ring=64, mat=mat_rim2(color, rim, a_center=a_center, a_rim=0.9, emit=emit, name=name + '_m', blend=0.3, rough=0.5, bump=bump, bump_scale=55.0, cull=True), scale=(1.15, 1.0, 0.92))
    try: o.visible_shadow = False
    except Exception: pass
    return o

def organelles(name, rnd, n, center, radius, avoid_r=0.0, s=1.0):
    """Cytoplasm furniture: mitochondria (bean capsules with a cristae groove ring), vesicles, ER sheets (curved ribbons),
    ribosome dots; batched into a few meshes.  Returns the objects."""
    pts = []
    while len(pts) < n:
        v = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))
        if 0.15 < v.length < 1.0 and v.length * radius > avoid_r: pts.append(Vector(center) + v * radius)
    mito = M('mito', lambda: mat_grain(MITO, rough=0.4, sss=0.3, coat=0.3, name='mito', scale=10.0, bump=0.25, spot=(0.95, 0.45, 0.30)))
    ves = M('ves', lambda: mat_organic(VESICLE, rough=0.4, sss=0.3, coat=0.3, name='ves')); erm = M('er', lambda: mat_organic(ER, rough=0.45, sss=0.25, coat=0.25, name='er'))
    bm = bmesh.new(); k3 = max(1, n // 3)
    for k, p in enumerate(pts[:k3]):
        d = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))).normalized() * 0.45 * s
        capsule_into(bm, p - d, p + d, 0.17 * s, 20, 10)
        q = d.normalized().to_track_quat('Z', 'Y').to_matrix().to_4x4()
        for j in (-0.5, 0.0, 0.5):                       # cristae rings
            tmp = bmesh.new(); _ring_into(tmp, 20, 0, 0, 0.19 * s, 0.035 * s, 0.0, hole=0.82, atoms=0.0, bevel=False)
            merge_into(bm, tmp, Matrix.Translation(p + d * j * 0.9) @ q @ Matrix.Rotation(-math.pi / 2, 4, 'Y'))
    mo = mesh_obj(name + '_mito', bm, mito)
    vo = spheres_mesh(name + '_ves', pts[k3:2 * k3], 0.14 * s, ves, subdiv=2, rscale=[rnd.uniform(0.6, 1.4) for _ in pts[k3:2 * k3]])
    bm = bmesh.new()
    for p in pts[2 * k3:]:                              # ER: stacks of small curled, wavy-edged cisternae
        q = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))).normalized().to_track_quat('Z', 'Y').to_matrix().to_4x4()
        for layer in range(3):
            res = bmesh.ops.create_grid(bm, x_segments=12, y_segments=4, size=0.36 * s)
            for v in res['verts']:
                v.co.x *= 1.6; v.co.z += 0.55 * s * (v.co.x / (0.6 * s)) ** 2 + 0.05 * s * math.sin(v.co.y * 14 / s) + layer * 0.16 * s
                v.co.y *= 1.0 - 0.25 * (v.co.x / (0.6 * s)) ** 2
            bmesh.ops.transform(bm, matrix=Matrix.Translation(p) @ q, verts=res['verts'])
    eo = mesh_obj(name + '_er', bm, erm); solidify(eo, 0.05 * s)
    ribo = M('ribo_dots', lambda: mat_gloss((0.55, 0.42, 0.85), rough=0.4, name='ribo_dots'))
    rp = [Vector(center) + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))).normalized() * radius * rnd.uniform(0.3, 0.98) for _ in range(n * 3)]
    rp = [p for p in rp if (p - Vector(center)).length > avoid_r]
    ro = spheres_mesh(name + '_ribo', rp, 0.05 * s, ribo, subdiv=1)
    return [mo, vo, eo, ro]

def cytoplasm_bits(name, rnd, n, center, radius, avoid_r=0.0, rfps=12, nf=1, drift=0.15):
    return organelles(name, rnd, n, center, radius, avoid_r=avoid_r, s=radius / 6)

def red_cell(name, loc, r=1.0, mat=None, seed=0):
    """Biconcave red cell with a 'Sickle' shape key (crescent, pointed ends)."""
    o = obj_add('uv_sphere', name, radius=r, segments=64, ring_count=32, location=loc); me = o.data
    for v in me.vertices:
        rr = math.hypot(v.co.x, v.co.y) / r; t = 0.42 - 0.30 * math.exp(-6.0 * rr * rr)
        v.co.z *= t
    o.shape_key_add(name='Basis'); sk = o.shape_key_add(name='Sickle')
    for k, v in enumerate(me.vertices):
        x, y, z = v.co.x, v.co.y, v.co.z
        X_ = x * 1.35; Y_ = y * 0.62 + 0.55 * r * (X_ / (1.35 * r)) ** 2 - 0.22 * r; Z_ = z * 1.15 * (1 - 0.35 * (abs(X_) / (1.35 * r)) ** 2)
        e = (abs(X_) / (1.35 * r)) ** 3; Y_ *= (1 - 0.55 * e); Z_ *= (1 - 0.6 * e)
        sk.data[k].co = (X_, Y_, Z_)
    setmat(o, mat or M('rbc', lambda: mat_grain(RBC, rough=0.35, sss=0.4, coat=0.45, name='rbc', scale=8.0, bump=0.12))); smooth(o, auto=False)
    subsurf(o, 1, 2)
    return o, sk

def key_shape(sk, f, v):
    sk.value = v; sk.keyframe_insert('value', frame=f)

# ================================================================= codon wall
def wall_asset(name='Wall', loc=(0, 0, 0), tile=0.9, gap=0.12, rfps=12, t_rise=None, rise_dur=2.0, seed=4):
    """The 64-codon table as an 8x8 wall of bevelled tiles facing -Y, coloured by amino acid (stop = red, Met = start),
    with 3D codon letters; tiles rise into place in waves from t_rise.  Returns root, dict codon -> (tile, text)."""
    root = empty(name, loc); tiles = {}; rnd = random.Random(seed); B = 'UCAG'
    tm = M('tile_txt', lambda: mat_gloss((0.96, 0.96, 0.98), rough=0.3, coat=0.4, name='tile_txt'))
    codons = [a + b + c for a in B for b in B for c in B]
    for k, cd in enumerate(codons):
        col, row = k % 8, k // 8; x = (col - 3.5) * (tile + gap); z = (3.5 - row) * (tile + gap)
        aa = CODON[cd]; c = STOP if aa == 'Stop' else AMINO[aa]
        t = obj_add('cube', f'{name}_{cd}', size=1); t.scale = (tile, tile * 0.22, tile); t.location = (x, 0, z)
        setmat(t, mat_gloss(c, rough=0.32, coat=0.5, name=f'{name}_m{cd}', sss=0.1))
        try: bv = t.modifiers.new('bev', 'BEVEL'); bv.width = 0.06; bv.segments = 5
        except Exception: pass
        smooth(t); parent(t, root)
        tx = text_obj(f'{name}_t{cd}', cd, size=tile * 0.34, mat=tm, loc=(x, -tile * 0.13, z - tile * 0.12), extrude=0.02); parent(tx, root)
        tiles[cd] = (t, tx)
        if t_rise is not None:
            d = rnd.uniform(0, rise_dur); t0 = t_rise + d
            for o in (t, tx):
                kf(o, 'location', 1, (x, 0, z - 6)); kf(o, 'location', F(t0, rfps), (x, 0, z - 6)); kf(o, 'location', F(t0 + 1.2, rfps), (x, 0, z) if o is t else (x, -tile * 0.13, z - tile * 0.12)); kf_ease(o)
    return root, tiles

# ================================================================= environment kit (point 2: never an empty void)
def dust(name, rnd, n, center, spread, r=0.03, color=(0.7, 0.85, 1.0), strength=3.0, rfps=None, dur=None, drift_amp=0.35):
    """Faint drifting specks for depth in the void; the whole cloud drifts slowly when rfps/dur are given."""
    pts = [Vector(center) + Vector((rnd.uniform(-1, 1) * spread[0], rnd.uniform(-1, 1) * spread[1], rnd.uniform(-1, 1) * spread[2])) for _ in range(n)]
    o = spheres_mesh(name, pts, r, mat_glow(color, strength=strength, name=name + '_m'), subdiv=1, rscale=[rnd.uniform(0.5, 1.5) for _ in pts])
    try: o.visible_shadow = False
    except Exception: pass
    if rfps and dur:
        kf(o, 'location', 1, (0, 0, 0)); kf(o, 'location', F(dur, rfps), (drift_amp * rnd.uniform(-1, 1), drift_amp * rnd.uniform(-1, 1), drift_amp * 0.6)); kf_lin(o)
    return o

def mat_halo(color, strength=1.2, name='halo', power=3.0, alpha=1.0):
    """Soft radial glow disc: emission fades from the centre, alpha likewise (camera-facing halo behind a hero).
    alpha < 1 caps the centre opacity so a close, large halo stays a glow and never reads as a translucent sphere."""
    m, p = _principled(name); nt = m.node_tree; n = nt.nodes
    tc = n.new('ShaderNodeTexCoord'); gr = n.new('ShaderNodeTexGradient'); gr.gradient_type = 'SPHERICAL'
    mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (2, 2, 2); mp.inputs['Location'].default_value = (-1, -1, -1)
    pw = n.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = power
    mul = n.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = strength
    amul = n.new('ShaderNodeMath'); amul.operation = 'MULTIPLY'; amul.inputs[1].default_value = alpha
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], gr.inputs['Vector']); nt.links.new(gr.outputs['Fac'], pw.inputs[0])
    nt.links.new(pw.outputs[0], mul.inputs[0]); nt.links.new(mul.outputs[0], p.inputs['Emission Strength']); nt.links.new(pw.outputs[0], amul.inputs[0]); nt.links.new(amul.outputs[0], p.inputs['Alpha'])
    _inp(p, 'Base Color', (0, 0, 0, 1)); _inp(p, 'Emission Color', (*color, 1)); _inp(p, 'Roughness', 1.0); _inp(p, 'Specular IOR Level', 0.0)
    _blend(m)
    return m

def halo(name, loc, r, color, strength=1.2, cam=None, alpha=1.0):
    """Camera-facing glow disc behind the hero."""
    o = obj_add('plane', name, size=2 * r, location=loc); setmat(o, mat_halo(color, strength=strength, name=name + '_m', alpha=alpha))
    try: o.visible_shadow = False
    except Exception: pass
    if cam is not None:
        c = o.constraints.new('TRACK_TO'); c.target = cam; c.track_axis = 'TRACK_Z'; c.up_axis = 'UP_Y'
    else: o.rotation_euler = (math.pi / 2, 0, 0)
    return o

def bokeh_fg(cam, rnd, n=4, color=(0.75, 0.9, 1.0), depth=(1.4, 2.6), rfps=12, dur=5.0, alpha=0.05, emit=0.22, r=0.10):
    """Out-of-focus foreground: translucent specks parented to the camera, drifting across the frame."""
    m = mat_rim2(color, color, a_center=0.015, a_rim=0.16, emit=0.5, name='bokeh_m', blend=0.55, rough=0.6, cull=False); out = []
    for k in range(n):
        d = rnd.uniform(*depth); x0 = rnd.uniform(-0.7, 0.7) * d * 0.6; y0 = rnd.uniform(-0.4, 0.4) * d * 0.6
        o = obj_add('ico_sphere', f'Bokeh{k}', radius=r * rnd.uniform(0.6, 1.6) * d / 2, subdivisions=3, location=(x0, y0, -d)); setmat(o, m); smooth(o, auto=False)
        o.parent = cam; o.matrix_parent_inverse = Matrix.Identity(4)
        try: o.visible_shadow = False
        except Exception: pass
        vx, vy = rnd.uniform(-0.12, 0.12) * d, rnd.uniform(-0.06, 0.06) * d
        kf(o, 'location', 1, (x0, y0, -d)); kf(o, 'location', F(dur, rfps), (x0 + vx * dur, y0 + vy * dur, -d)); kf_lin(o); out.append(o)
    return out

def backdrop_helices(rnd, n, center, spread, rfps, dur, seed=5, bp=18, R=0.75, dim=0.55):
    """Distant secondary helices turning slowly in the background (cheap batched capsule helices in dimmed materials)."""
    out = []; mats = {b: mat_gloss(tuple(c * dim for c in BASE[b]), rough=0.4, coat=0.2, name=f'bg_{b}') for b in 'ATGC'}
    for k in range(n):
        p = Vector(center) + Vector((rnd.uniform(-1, 1) * spread[0], rnd.uniform(-1, 1) * spread[1], rnd.uniform(-1, 1) * spread[2]))
        h = Helix(f'BgHx{k}', rand_seq(bp, seed + k), loc=tuple(p), rot=(rnd.uniform(0, 3), rnd.uniform(0, 3), rnd.uniform(0, 3)), R=R, individual=False, hbonds=False, beads=False, base_mats=mats, sub_pt=4)
        spin(h.root, rfps, dur, rate=rnd.uniform(0.02, 0.05), axis=0); out.append(h)
    return out

def filaments(name, rnd, n, center, spread, mat=None, r=0.03, length=6.0):
    """Cytoskeleton / distant fibres: wandering thin tubes."""
    m = mat or M('fil', lambda: mat_gloss((0.35, 0.55, 0.62), rough=0.45, coat=0.2, name='fil')); out = []
    for k in range(n):
        p0 = Vector(center) + Vector((rnd.uniform(-1, 1) * spread[0], rnd.uniform(-1, 1) * spread[1], rnd.uniform(-1, 1) * spread[2]))
        pts = wander_pts(rnd, tuple(p0), 8, length / 8, ((p0.x - length, p0.x + length), (p0.y - length, p0.y + length), (p0.z - length, p0.z + length)), smoothness=0.8)
        c = curve_obj(f'{name}{k}', pts, r, m, res=6, kind='NURBS'); out.append(c)
    return out

def theme_lights(sec, target=(0, 0, 0), key=(3.5, -6.0, 6.5), key_e=2400, fill_e=160, rim_e=420, spot=55, blend=0.85, env=0.12, atm=0.0015, accent_e=0.0, accent_pos=(-4.0, 3.0, -2.0)):
    """Section lighting theme over the navy void: warm/cool key per THEMES, dim fill, coloured rim, optional accent rim,
    HDRI reflections (0.12) and the thin atmosphere (Cycles)."""
    th = THEMES.get(sec, THEMES[0]); world(*NAVY)
    k = light('SPOT', key, key_e, th['key'], 'Key', spot=spot, blend=blend, target=target)
    f = light('AREA', (-6, -5, 4), fill_e, th['fill'], 'Fill', size=6, target=target)
    r = light('AREA', (1.5, 6, 5), rim_e, th['rim'], 'Rim', size=3, target=target)
    if accent_e: light('AREA', accent_pos, accent_e, th['accent'], 'Accent', size=2.5, target=target)
    hdri(strength=env, rotation=1.3); atmosphere(density=atm)
    return k, f, r

def env_kit(sec, cam, rnd, rfps, dur, center=(0, 0, 0), dust_n=120, dust_spread=(14, 10, 8), halo_r=0.0, halo_at=None, bokeh=4, helices=0, fil=0, halo_strength=0.28, halo_alpha=1.0):
    """Point 2 in one call: drifting dust, a faint halo behind the hero, out-of-focus foreground specks, distant helices."""
    th = THEMES.get(sec, THEMES[0]); out = {}
    if dust_n: out['dust'] = dust('Dust', rnd, dust_n, (center[0], center[1] + 4, center[2]), dust_spread, color=th['accent'], strength=2.5, rfps=rfps, dur=dur)
    if halo_r: out['halo'] = halo('Halo', halo_at or (center[0], center[1] + 3.0, center[2]), halo_r, tuple(0.5 + 0.5 * c for c in th['accent']), strength=halo_strength, cam=cam, alpha=halo_alpha)
    if bokeh: out['bokeh'] = bokeh_fg(cam, rnd, n=bokeh, color=th['accent'], rfps=rfps, dur=dur)
    if helices: out['helices'] = backdrop_helices(rnd, helices, (center[0], center[1] + 9, center[2]), (10, 4, 5), rfps, dur)
    if fil: out['fil'] = filaments('Fil', rnd, fil, (center[0], center[1] + 6, center[2]), (10, 5, 5))
    return out

def helix_lights(target=(0, 0, 0), key_e=2400, spot=55, env=0.12, sec=1):
    """Standard helix lighting: warm key upper-left front, cool fill, rim from behind-right (themed), HDRI reflections."""
    return theme_lights(sec, target=target, key=(3.5, -6.0, 6.5), key_e=key_e, fill_e=160, rim_e=420, spot=spot, blend=0.85, env=env)

def stage(target=(0, 0, 0), key=(3.0, -5.5, 7.5), key_e=2200, fill_e=140, rim_e=380, spot=55, blend=0.85, env=0.12, world_col=NAVY, sec=0):
    return theme_lights(sec, target=target, key=key, key_e=key_e, fill_e=fill_e, rim_e=rim_e, spot=spot, blend=blend, env=env)

HERO_SEQ = 'ATGCCGTAAGCTTAGGCATCGATCCGTAGCAATGGCCTAGCTAGGATCCGATTACGGA'      # 58 bp hero sequence, reused so colours match across shots
GENE_SEQ = 'TACGGACCTGGACGAACCATT'                                           # template strand of the 'gene' (mRNA: AUG CCU GGA CCU GCU UGG UAA)
MRNA_SEQ = ''.join(RNA_OF[b] for b in GENE_SEQ)                              # AUGCCUGGACCUGCUUGGUAA : start, Pro, Gly, Pro, Ala, Trp, stop
assert MRNA_SEQ.startswith('AUG') and MRNA_SEQ.endswith('UAA')
from projects.dna.shotlist import SHOTS as _SHOTS
T0 = {s['id']: s['t0'] for s in _SHOTS}
def rt(sid, t_abs): return t_abs - T0[sid]                                   # absolute narration seconds -> shot-relative seconds

# ================================================================= builders: intro
def cold_open(nf, rfps, dur):
    """s01 0-13.3: the hero helix (ring-plate bases, pentagon sugars, tetrahedral phosphates) turning slowly in the navy void
    under the title; the camera drifts in and around it through drifting dust, a faint halo behind, distant helices."""
    reset(); rnd = random.Random(1); helix_lights(target=(0, 0, 0), key_e=2600, sec=0)
    h = Helix('DNA', HERO_SEQ[:44], loc=(0, 0, 0), rot=(0, 0, 0), individual=False, hd=True); spin(h.root, rfps, dur, rate=0.05)
    cam, tgt = cam_path([(0.0, (-4.5, -12.5, 2.4), (0.5, 0, 0.1)), (dur, (3.0, -9.0, 1.4), (-0.6, 0, 0.0))], rfps, lens=50)
    env_kit(0, cam, rnd, rfps, dur, center=(0, 0, 0), dust_n=140, halo_r=7.0, halo_at=(0, 4.0, 0), bokeh=4, helices=3)

def cell_preview(nf, rfps, dur):
    """s02 13.3-30.5 (under the topic table): a translucent cell full of organelles with its amethyst nucleus (double
    membrane, eight-fold pore complexes); the camera pushes toward the nucleus.  Ends on the framing s04 starts with."""
    reset(); rnd = random.Random(4); theme_lights(0, target=(0, 0, 0), key=(6, -10, 10), key_e=5000, spot=60, fill_e=300, rim_e=600)
    cell_body('Cell', (0, 0, 0), 6.0)
    nucleus_hd('Nuc', (0.4, 0.6, 0.2), r=2.2, pores=34, seed=3)
    for o in organelles('Cyto', rnd, 42, (0, 0, 0), 5.2, avoid_r=3.2, s=0.9): drift(o, rfps, dur, amp=0.12, seed=rnd.randint(1, 99), period=5.0)
    filaments('Fil', rnd, 6, (0, 0, 0), (3, 3, 2), r=0.025, length=5.0)
    cam, tgt = cam_path([(0.0, (-3.0, -22.0, 4.0), (0, 0, 0)), (dur, (0.5, -13.5, 2.2), (0.3, 0.4, 0.2))], rfps, lens=45)
    env_kit(0, cam, rnd, rfps, dur, center=(0, 0, 0), dust_n=100, dust_spread=(16, 10, 8), bokeh=3)

def _tk_test(nf, rfps, dur):
    """Scratch toolkit check: HD helix (individual + bubble), HD mRNA, tRNA, ribosome, polymerase, amino chain, haemoglobin,
    nucleosome fibre, chromosome, pore complex, red cell, halo."""
    reset(); rnd = random.Random(2); theme_lights(3, target=(0, 0, 0), key_e=3000, spot=70)
    h = Helix('DNA', HERO_SEQ[:14], loc=(-4.5, 0, 2.5), individual=True, hd=True, anchors=((3, 0), (3, 1)))
    h.bubble(rfps, 0.0, dur, lambda t: 7.0, width=3.0, depth=0.6)
    r = RNA('mRNA', MRNA_SEQ[:9], loc=(-4.5, 0, 0.0), side=(0, 0, 1), hd=True, individual=True); r.sleeve(3, GENE, F(0.1, rfps), n=3)
    trna('tRNA', 'CCA', 'Gly', loc=(0.5, 0, 0.0), s=0.6, anchors=True)
    ribosome('Ribo', (3.5, 0, 0.0), s=0.5)
    polymerase('Pol', (3.5, 0, 2.6), s=0.5)
    ch = Chain('Ch', ['Met', 'Pro', 'Gly', 'Glu', 'Val', 'Lys', 'Phe'], r=0.18); ch.pose([(-4.5 + 0.5 * k, 0, -2.2) for k in range(7)], 1)
    haemoglobin('Hb', (0.5, 0, -2.2), s=0.5)
    nucleosome_fibre('Fib', [(-1.5, -1, 4.2), (0.5, -1.2, 4.5), (2.5, -1, 4.2), (4.5, -1.2, 4.5)], spacing=0.8, r_spool=0.18, r_fibre=0.03)
    chromosome('Chr', (-1.5, 0, 1.0), s=0.6)
    pore_complex('Pore', (3.5, 0, -2.3), (0, -1, 0), r=0.5)
    red_cell('RBC', (-2.5, 0, -2.3), r=0.45)
    cam, tgt = cam_path([(0.0, (0, -14.0, 1.0), (0, 0, 1.0)), (dur, (0.3, -13.5, 1.0), (0, 0, 1.0))], rfps, lens=40)
    env_kit(3, cam, rnd, rfps, dur, center=(0, 0, 1), dust_n=80, halo_r=6.0, halo_at=(0, 5, 1), bokeh=3, helices=2, fil=3)

# ================================================================= section helpers (structure)
def single_base(name, b, loc=(0, 0, 0), s=1.0, rot=(0, 0, 0), mat=None, anchor_tag=None):
    """A lone nucleobase on its sugar: pentagon sugar ring + glycosidic stub + ring plate, plate facing local -x.  Local frame:
    sugar at the origin, base extending along -y (scaled by s).  Returns root (children: plate, sugar) and the plate object."""
    root = empty(name, loc); root.rotation_euler = rot; root.scale = (s, s, s)
    pl = mesh_obj(name + '_plate', plate_bmesh(b, -Y_OUT_IN), mat or m_base(b)); parent(pl, root)
    sbm = sugar_bmesh(0.0, stub_to=-Y_OUT_IN); bmesh.ops.rotate(sbm, cent=(0, 0, 0), matrix=Matrix.Rotation(0.9, 3, 'Y'), verts=list(sbm.verts))
    sg = mesh_obj(name + '_sugar', sbm, m_sugar()); parent(sg, root)
    if anchor_tag: anchor(anchor_tag, (0, -Y_OUT_IN - 0.5 * plate_len(b), 0), root)
    return root, pl

def base_pair(name, b, loc=(0, 0, 0), s=1.0, rot=(0, 0, 0), sep=0.0, dashes=True):
    """A base pair standing alone: strand-0 base b (sugar at local -x end... no: sugar at +y*R... ) laid along local y:
    base b hangs from its sugar at y = +R toward the centre, its partner from y = -R; H-bond dashes (individual objects)
    bridge the off-centre gap.  sep > 0 pulls the two halves apart (animate root['half0'] / ['half1'] locations).
    Returns dict(root, halves, plates, dashes, gap_centre)."""
    R = 1.0; root = empty(name, loc); root.rotation_euler = rot; root.scale = (s, s, s)
    halves = []; plates = []; c = COMP[b]
    m = (plate_len(c) - plate_len(b)) / 2; gap = 2 * (R - Y_OUT_IN) - plate_len(b) - plate_len(c)
    for k, (bb, sg) in enumerate(((b, 1), (c, -1))):
        h = empty(f'{name}_half{k}', (0, sg * sep, 0)); h.rotation_euler = (0.0 if k == 0 else math.pi, 0, 0); parent(h, root); halves.append(h)
        pl = mesh_obj(f'{name}_plate{k}', plate_bmesh(bb, R - Y_OUT_IN), m_base(bb)); parent(pl, h); plates.append(pl)
        sbm = sugar_bmesh(R, stub_to=R - Y_OUT_IN); bmesh.ops.rotate(sbm, cent=(0, R, 0), matrix=Matrix.Rotation(0.9, 3, 'Y'), verts=list(sbm.verts))
        su = mesh_obj(f'{name}_sugar{k}', sbm, m_sugar()); parent(su, h)
        ph = mesh_obj_multi(f'{name}_phos{k}', phos_bmesh(Vector((0.42, R * 0.98, 0.0)), random.Random(k + 3)), [m_phos(), m_phos_o()]); parent(ph, h)
    ds = []
    if dashes:
        offs = [-0.055, 0.055] if b in 'AT' else [-0.085, 0.0, 0.085]
        for j, o in enumerate(offs):
            d = capsule_obj(f'{name}_hb{j}', (o, m + gap / 2 + 0.01, 0), (o, m - gap / 2 - 0.01, 0), 0.03, m_hbond(), seg=10, ring=5); parent(d, root); ds.append(d)
            try: d.visible_shadow = False
            except Exception: pass
    root['half0'] = halves[0].name; root['half1'] = halves[1].name
    return dict(root=root, halves=halves, plates=plates, dashes=ds, gap_centre=Vector((0, m, 0)), m=m, gap=gap)

def photo51(name, loc, r=4.0, f_on=None, rfps=12, t_on=None):
    """Rosalind Franklin's Photo 51 as light: the X of diffraction dashes + layer lines on a soft halo disc, facing -Y."""
    root = empty(name, loc); mg = mat_glow((0.85, 0.92, 1.0), strength=5.0, name=name + '_g'); bm = bmesh.new()
    for sgx in (-1, 1):
        for sgz in (-1, 1):
            for k in range(1, 6):
                u = k / 6.0; p = Vector((sgx * u * r * 0.72, 0, sgz * u * r * 0.72)); L = 0.16 * r * (1 - 0.5 * u)
                capsule_into(bm, p - Vector((L * 0.5 * sgx, 0, -L * 0.5 * sgz * 0.0)), p + Vector((L * 0.5 * sgx, 0, 0)), 0.035 * r, 10, 5)
    for k in (-3, -2, 2, 3):
        z = k * r * 0.18; w = r * (0.18 if abs(k) == 3 else 0.10)
        capsule_into(bm, (-w, 0, z), (w, 0, z), 0.03 * r, 10, 5)
    x = mesh_obj(name + '_x', bm, mg); parent(x, root)
    try: x.visible_shadow = False
    except Exception: pass
    disc = obj_add('plane', name + '_disc', size=2.4 * r); disc.rotation_euler = (math.pi / 2, 0, 0); setmat(disc, mat_halo((0.6, 0.72, 0.95), strength=0.35, name=name + '_h', power=2.5)); parent(disc, root)
    try: disc.visible_shadow = False
    except Exception: pass
    if t_on is not None: scale_in(root, rfps, t_on, dur=1.2)
    return root

def helix_hero_env(sec, cam, rnd, rfps, dur, center=(0, 0, 0), helices=2, halo_r=7.0, halo_back=4.5, halo_alpha=1.0, halo_strength=0.28):
    return env_kit(sec, cam, rnd, rfps, dur, center=center, dust_n=130, halo_r=halo_r, halo_at=(center[0], center[1] + halo_back, center[2]), bokeh=4, helices=helices, halo_alpha=halo_alpha, halo_strength=halo_strength)

# ================================================================= builders: 1. Structure of DNA
def dive_to_chromosomes(nf, rfps, dur):
    """s04 33.1-46.75: from s02's framing the camera flies THROUGH the cell membrane (its lipid bump fills the frame and flares
    as we cross), up to the amethyst envelope, THROUGH an eight-fold pore complex, and the nucleus opens up: 46 chromosomes
    (fibre-wound X shapes) drifting in the nucleoplasm among loose chromatin threads; we push into one chromosome."""
    reset(); rnd = random.Random(4); T = lambda t: rt('s04', t)
    theme_lights(1, target=(0.4, 0.6, 0.2), key=(6, -10, 10), key_e=5000, spot=60, fill_e=300, rim_e=600)
    P0, N = Vector((0.5, -13.5, 2.2)), Vector((0.4, 0.6, 0.2)); d = N - P0; dh = d.normalized()
    cell = cell_body('Cell', (0, 0, 0), 6.0); crossing(cell.data.materials[0], rfps, 3.3, a_hi=0.8, emit_hi=7.0)
    for o in organelles('Cyto', rnd, 42, (0, 0, 0), 5.2, avoid_r=3.2, s=0.9): drift(o, rfps, dur, amp=0.1, seed=rnd.randint(1, 99), period=5.0)
    filaments('Fil', rnd, 6, (0, 0, 0), (3, 3, 2), r=0.025, length=5.0)
    nroot, outer, inner, pores, holes = nucleus_hd('Nuc', tuple(N), r=2.2, pores=34, hole_dirs=[tuple(-dh)], seed=3, inside=True, pore_r=0.20)
    crossing(outer.data.materials[0], rfps, 6.9, a_hi=0.55, emit_hi=4.0, a_lo=0.16, emit_lo=1.2, post=0.6)
    crossing(inner.data.materials[0], rfps=rfps, t_cross=7.05, a_hi=0.45, emit_hi=3.0, a_lo=0.13, emit_lo=0.7, post=0.6)
    light('POINT', tuple(N + Vector((0.3, -0.3, 0.6))), 60, (0.9, 0.8, 1.0), 'NucLight')
    proto = chromosome('Chr0', tuple(N + Vector((-0.6, 0.9, 0.5))), s=0.16, rot=(0.4, 0.2, 0.9), seed=1)
    pore_pt = N - dh * 2.2
    roots = chromosome_field(proto, 44, rnd, tuple(N), 1.75, s_range=(0.8, 1.15), avoid=(tuple(pore_pt), 0.9)) + [proto]
    hero = chromosome('ChrHero', tuple(N + Vector((0.5, 0.8, -0.2))), s=0.22, rot=(0.25, 0.1, 0.35), seed=1)
    for o in [bpy.data.objects[x] for x in hero['objs']]:
        if o.type == 'MESH': bake_mods(o)
    roots.append(hero); anchor('ChromAnchor', (0, 0, 0.32), hero)
    for k, r in enumerate(roots):
        drift(r, rfps, dur, amp=0.05, seed=k + 7, period=6.0)
        kf(r, 'rotation_euler', 1, tuple(r.rotation_euler)); kf(r, 'rotation_euler', nf, tuple(Vector(r.rotation_euler) + Vector((0.3, 0.2, 0.5)) * rnd.uniform(0.3, 1.0))); kf_lin(r)
    for k in range(3):
        pth = [tuple(N + Vector((rnd.uniform(-1.3, 1.3), rnd.uniform(-1.3, 1.3), rnd.uniform(-1.3, 1.3)))) for _ in range(4)]
        nucleosome_fibre(f'Thread{k}', pth, spacing=0.22, r_spool=0.045, r_fibre=0.009, seed=k + 2)
    HP = hero.location
    cam, tgt = cam_path([(0.0, tuple(P0), (0.3, 0.4, 0.2)), (3.3, tuple(P0 + d * 0.56), tuple(N)), (6.4, tuple(P0 + d * 0.80), tuple(pore_pt)), (7.4, tuple(pore_pt), tuple(N)),
                         (8.8, tuple(P0 + d * 0.90), tuple(N + Vector((0, 0.3, 0)))), (11.0, tuple(N + Vector((-0.6, -0.9, 0.35))), tuple(HP)), (dur, tuple(HP + Vector((-0.55, -1.45, 0.3))), tuple(HP))], rfps, lens=45)
    env_kit(1, cam, rnd, rfps, dur, center=(0, 0, 0), dust_n=90, dust_spread=(16, 10, 8), bokeh=2)
    dust('NucDust', rnd, 70, tuple(N), (1.6, 1.6, 1.6), r=0.006, color=(0.85, 0.75, 1.0), strength=2.0)

def double_helix_ladder(nf, rfps, dur):
    """s06 56.92-70.04: the helix (ring-plate ladder rig) turns; each strand lights in turn as 'two strands' are spoken; the
    camera orbits for 'double helix'; on 'twisted ladder' the helix untwists into a flat ladder facing us and twists back."""
    reset(); rnd = random.Random(6); T = lambda t: rt('s06', t); helix_lights(target=(0, 0, 0), key_e=2600, sec=1)
    rm = [mat_gloss(RAIL_A, rough=0.28, coat=0.5, name='lad_rail0'), mat_gloss(RAIL_B, rough=0.28, coat=0.5, name='lad_rail1')]
    lad = Ladder('Lad', HERO_SEQ[:32], loc=(0, 0, 0), rot=(math.pi / 2, 0, 0), hd=True, rail_mats=rm)
    lad.key_twist(1, 1.0); lad.key_twist(F(T(66.9), rfps), 1.0); lad.key_twist(F(T(68.1), rfps), 0.0); lad.key_twist(F(T(68.9), rfps), 0.0); lad.key_twist(F(T(70.04), rfps), 1.0); lad.ease()
    kf(lad.root, 'rotation_euler', 1, (math.pi / 2, 0, 0)); kf(lad.root, 'rotation_euler', F(T(66.9), rfps), (math.pi / 2 + 2 * math.pi * 0.06 * T(66.9), 0, 0)); kf_ease(lad.root)
    hold_glow(rm[0], rfps, T(57.4), T(59.6), (0.7, 0.85, 1.0), strength=2.5); hold_glow(rm[1], rfps, T(59.8), T(62.4), (0.9, 0.95, 1.0), strength=2.5)
    cam, tgt = cam_path([(0.0, (-5.2, -3.0, 1.4), (-2.5, 0.0, 0.4)), (T(60.0), (-4.0, -9.5, 2.5), (0.0, 0, 0.2)), (T(64.2), (2.0, -10.5, 1.5), (0.0, 0, 0.0)),
                         (T(66.9), (0.0, -9.6, 0.6), (0, 0, 0)), (dur, (0.6, -9.2, 0.8), (0, 0, 0))], rfps, lens=45)
    helix_hero_env(1, cam, rnd, rfps, dur, helices=3)

def backbone_rungs(nf, rfps, dur):
    """s07 70.04-80.93: close on one backbone, tracking along sugar - phosphate - sugar (each unit named as spoken, anchors
    RpS0/RpP0/... for the 2D labels), then pulling back as the rungs (base pairs) pulse for 'steps of the ladder'."""
    reset(); rnd = random.Random(7); T = lambda t: rt('s07', t); helix_lights(target=(0, 0, 0), key_e=2600, sec=1)
    ph = math.pi - 11 * (2 * math.pi / 10)
    h = Helix('DNA', HERO_SEQ[:26], loc=(0, 0, 0), individual=False, hd=True, phase=ph)
    spin(h.root, rfps, dur, rate=0.012)
    for k, i in enumerate((9, 10, 11, 12)):
        anchor(f'S{k}', h.sugar_pt(i, 0) + h.rad(h.th(i, 0)) * 0.22, h.root)
        if k < 3: anchor(f'P{k}', h.phos_pt(i, 0) + h.rad(h.th(i, 0) + h.dth / 2) * 0.22, h.root)
    anchor('Rung', h.gap_centre(11) + Vector((0, -0.1, 0.3)), h.root)
    pulse(m_sugar(), rfps, T(72.6), SUGAR, peak=2.2); pulse(m_phos(), rfps, T(73.4), PHOS, peak=2.5); pulse(m_sugar(), rfps, T(74.9), SUGAR, peak=2.2); pulse(m_phos(), rfps, T(75.6), PHOS, peak=2.5)
    for b in 'ATGC': pulse(m_base(b), rfps, T(78.2), BASE[b], peak=1.8, fall=1.6)
    p9, p12 = h.sugar_pt(9, 0), h.sugar_pt(12, 0)
    cam, tgt = cam_path([(0.0, (0.6, -9.2, 0.8), (0, 0, 0)), (T(71.6), tuple(p9 + Vector((-0.9, -3.2, 0.9))), tuple(p9)), (T(76.4), tuple(p12 + Vector((0.9, -3.0, 0.7))), tuple(p12)),
                         (T(78.0), (1.0, -8.0, 1.2), (0.2, 0, 0.1)), (dur, (-0.5, -8.8, 1.0), (0, 0, 0))], rfps, lens=45)
    if os.environ.get('VL_DOF', '0') == '1': rack_focus(cam, F(T(76.4), rfps), F(T(78.0), rfps), h.rail_objs[0], h.root)
    helix_hero_env(1, cam, rnd, rfps, dur, helices=2)

def four_bases(nf, rfps, dur):
    """s08 80.93-92.39: the four bases stand alone in their colours, each rising and turning as it is named (adenine and
    guanine two fused rings, thymine and cytosine one ring), letters follow at 'A, T, G, C'; slow lateral pan."""
    reset(); rnd = random.Random(8); T = lambda t: rt('s08', t)
    theme_lights(1, target=(0, 0, 0.3), key=(2.0, -7.0, 7.5), key_e=3000, spot=65, fill_e=220, rim_e=520, accent_e=260, accent_pos=(-5, 3, -3))
    for k, (b, t_on) in enumerate((('A', 82.2), ('T', 83.5), ('G', 84.7), ('C', 85.9))):
        x = -3.9 + k * 2.6
        root, pl = single_base(f'Base{b}', b, loc=(x, 0, 1.0), s=2.1, rot=(0, 0, math.pi / 2), anchor_tag=f'B{b}')
        scale_in(root, rfps, T(t_on), dur=0.6, final=2.1)
        kf(root, 'rotation_euler', F(T(t_on), rfps), (0, 0, math.pi / 2 - 0.4)); kf(root, 'rotation_euler', nf, (0, 0, math.pi / 2 + 0.4)); kf_lin(root)
        pulse(m_base(b), rfps, T(t_on + 6.1), BASE[b], peak=2.0, fall=1.0)
    bg = Helix('BgDNA', HERO_SEQ[:40], loc=(0, 7.5, -0.5), rot=(0, 0, 0.3), individual=False, hd=False); spin(bg.root, rfps, dur, rate=0.03)
    cam, tgt = cam_path([(0.0, (-2.6, -9.5, 1.4), (-1.6, 0, 0.6)), (T(86.5), (2.4, -9.2, 1.3), (1.6, 0, 0.6)), (dur, (0.4, -8.6, 1.2), (0, 0, 0.5))], rfps, lens=45)
    env_kit(1, cam, rnd, rfps, dur, center=(0, 0, 0), dust_n=120, halo_r=7.0, halo_at=(0, 5.5, 0.5), bokeh=4)

def nucleotide(nf, rfps, dur):
    """s09 92.39-100.03: one nucleotide (sugar + phosphate + base) slides out of the helix toward us and turns while its three
    parts are named (anchors RpSug/RpPho/RpBas) and 'nucleotide' lands; rack focus from the helix to the unit."""
    reset(); rnd = random.Random(9); T = lambda t: rt('s09', t); helix_lights(target=(0, 0, 0), key_e=2600, sec=1)
    ph = math.pi - 9 * (2 * math.pi / 10)
    h = Helix('DNA', HERO_SEQ[:18], loc=(0, 0, 0), individual=True, hd=True, phase=ph)
    u = h.units[(9, 0)]; n = h.rad(h.th(9, 0)); a = h.axis_pt(9)
    kf(u, 'location', 1, tuple(a)); kf(u, 'location', F(T(93.0), rfps), tuple(a)); kf(u, 'location', F(T(95.4), rfps), tuple(a + n * 2.6 + Vector((0.3, 0, 0.2)))); kf(u, 'location', nf, tuple(a + n * 2.9 + Vector((0.4, 0, 0.3)))); kf_ease(u)
    kf(u, 'rotation_euler', F(T(95.4), rfps), (h.th(9, 0), 0, 0)); kf(u, 'rotation_euler', nf, (h.th(9, 0), 0.9, 0.0)); kf_lin(u)
    hb = h.hb_of(9)
    if hb: kf(hb, 'scale', F(T(93.0), rfps), (1, 1, 1)); kf(hb, 'scale', F(T(93.6), rfps), (1, 0.001, 1))
    anchor('Sug', (0, h.R + 0.05, 0.25), u); anchor('Pho', tuple(h.phos_local(0) + Vector((0.15, 0.1, 0.2))), u); anchor('Bas', (0, h.y_out - 0.5 * plate_len(h.base_of(9, 0)), -0.35), u)
    spin(h.root, rfps, dur, rate=0.0)
    P = a + n * 2.6 + Vector((0.3, 0, 0.2))
    cam, tgt = cam_path([(0.0, (-0.5, -8.8, 1.0), (0, 0, 0)), (T(95.4), tuple(P + Vector((-0.9, -3.4, 0.9))), tuple(P)), (dur, tuple(P + Vector((0.9, -3.0, 0.7))), tuple(P + Vector((0.1, 0, 0.1))))], rfps, lens=50)
    if os.environ.get('VL_DOF', '0') == '1': rack_focus(cam, F(T(93.0), rfps), F(T(95.4), rfps), h.root, u)
    helix_hero_env(1, cam, rnd, rfps, dur, helices=2)

def pairing_rule(nf, rfps, dur):
    """s10 100.03-112.32: A-T (left) and G-C (right) stand side by side; on the rule sentence each pair slides together; then
    the hydrogen-bond dashes light and count: two between A and T, three between G and C; rack focus between the pairs."""
    reset(); rnd = random.Random(10); T = lambda t: rt('s10', t)
    theme_lights(1, target=(0, 0, 0.4), key=(2.0, -7.0, 7.5), key_e=3000, spot=65, fill_e=220, rim_e=520, accent_e=240, accent_pos=(-5, 3, -3))
    pairs = {}
    for b, x, t_join, t_dash in (('A', -2.6, 102.9, 107.3), ('G', 2.6, 104.7, 109.8)):
        bp = base_pair(f'Pair{b}', b, loc=(x, 0, 0.4), s=1.9, rot=(0, 0, math.pi / 2), sep=0.0); pairs[b] = bp
        for k, hf in enumerate(bp['halves']):
            sg = 1 if k == 0 else -1
            kf(hf, 'location', 1, (0, sg * 0.55, 0)); kf(hf, 'location', F(T(t_join), rfps), (0, sg * 0.55, 0)); kf(hf, 'location', F(T(t_join + 1.2), rfps), (0, 0, 0)); kf_ease(hf)
        for j, d in enumerate(bp['dashes']): scale_in(d, rfps, T(t_dash + 0.55 * j), dur=0.35)
        anchor(f'L{b}', (0, 1.0 - Y_OUT_IN - 0.5 * plate_len(b), 0.55), bp['halves'][0]); anchor(f'L{COMP[b]}', (0, 1.0 - Y_OUT_IN - 0.5 * plate_len(COMP[b]), 0.55), bp['halves'][1])
        anchor(f'HB{b}', tuple(bp['gap_centre'] + Vector((0, 0, -0.62))), bp['root'])
        kf(bp['root'], 'rotation_euler', 1, (0, 0, math.pi / 2 - 0.25)); kf(bp['root'], 'rotation_euler', nf, (0, 0, math.pi / 2 + 0.25)); kf_lin(bp['root'])
    bg = Helix('BgDNA', HERO_SEQ[:40], loc=(0, 8.0, -0.8), rot=(0, 0, -0.3), individual=False, hd=False); spin(bg.root, rfps, dur, rate=0.03)
    cam, tgt = cam_path([(0.0, (0.0, -9.6, 1.2), (0, 0, 0.4)), (T(102.9), (-1.6, -8.4, 1.0), (-2.2, 0, 0.4)), (T(104.7), (1.6, -8.4, 1.0), (2.2, 0, 0.4)),
                         (T(107.0), (-2.4, -6.2, 0.8), (-2.6, 0, 0.3)), (T(109.5), (2.4, -6.2, 0.8), (2.6, 0, 0.3)), (dur, (0.2, -8.2, 1.0), (0, 0, 0.4))], rfps, lens=45)
    if os.environ.get('VL_DOF', '0') == '1':
        rack_focus(cam, F(T(102.9), rfps), F(T(104.7), rfps), pairs['A']['root'], pairs['G']['root']); rack_focus(cam, F(T(107.0), rfps), F(T(109.5), rfps), pairs['A']['root'], pairs['G']['root'])
    env_kit(1, cam, rnd, rfps, dur, center=(0, 0, 0.4), dust_n=120, halo_r=7.5, halo_at=(0, 5.5, 0.5), bokeh=4)

def complementary(nf, rfps, dur):
    """s11 112.32-122.11: 5'->3' arrows slide opposite ways along the two rails (antiparallel) while 'reliable' is spoken; on
    'if we know one strand' the second strand fades away leaving one lettered strand, then rebuilds itself base by base
    with its rail growing back: the complement is automatic."""
    reset(); rnd = random.Random(11); T = lambda t: rt('s11', t); helix_lights(target=(0, 0, 0), key_e=2600, sec=1)
    seq = 'GATTACAGCTCAGG'; h = Helix('DNA', seq, loc=(0, 0, 0), rot=(0, 0, 0), individual=True, hd=True, phase=-0.6)
    for i in range(h.N):
        h.add_anchor(i, 0, tag=f'T{i}'); h.add_anchor(i, 1, tag=f'B{i}')
    f_gone = F(T(116.2), rfps)
    for i in range(h.N):
        for o in h.unit_objs(i, 1): hide_from(o, f_gone); kf(o, 'hide_render', F(T(117.2 + 0.28 * i), rfps), False)
        hb = h.hb_of(i)
        if hb: hide_from(hb, f_gone); kf(hb, 'hide_render', F(T(117.2 + 0.28 * i), rfps), False)
    r1 = h.rail_objs[1]; cu = r1.data
    hide_from(r1, f_gone); kf(r1, 'hide_render', F(T(117.2), rfps), False)
    cu.bevel_factor_end = 1.0; cu.keyframe_insert('bevel_factor_end', frame=1); cu.keyframe_insert('bevel_factor_end', frame=f_gone)
    cu.bevel_factor_end = 0.0; cu.keyframe_insert('bevel_factor_end', frame=f_gone + 1); cu.keyframe_insert('bevel_factor_end', frame=F(T(117.2), rfps))
    cu.bevel_factor_end = 1.0; cu.keyframe_insert('bevel_factor_end', frame=F(T(117.2 + 0.28 * h.N), rfps)); lin_id(cu)
    # antiparallel arrows riding the rails
    for s, col in ((0, (0.8, 0.95, 1.0)), (1, (1.0, 0.85, 0.6))):
        smp = h.rail_samples(s, per_bp=4); n = len(smp)
        idx = list(range(n)) if s == 0 else list(range(n - 1, -1, -1))
        ar = arrow3d(f'Arrow{s}', tuple(smp[idx[0]]), tuple(smp[idx[1]] - smp[idx[0]]), L=0.55, r=0.05, color=col); parent(ar, h.root)
        show_between(ar, F(T(112.6), rfps), F(T(116.0), rfps))
        for k in range(0, n - 1, 2):
            t = T(112.6) + (T(115.8) - T(112.6)) * k / (n - 2); p0, p1 = smp[idx[k]], smp[idx[min(n - 1, k + 1)]]
            kf(ar, 'location', F(t, rfps), tuple(p0 + h.rad(h.th(0, s) + (idx[k] / 4) * h.dth) * 0.16)); kf(ar, 'rotation_euler', F(t, rfps), (p1 - p0).normalized().to_track_quat('Z', 'Y').to_euler())
        kf_lin(ar)
        anchor(f'E{s}a', tuple(smp[0] + h.rad(h.th(0, s)) * 0.45), h.root); anchor(f'E{s}b', tuple(smp[-1] + h.rad(h.th(h.N - 1, s)) * 0.45), h.root)
    cam, tgt = cam_path([(0.0, (-1.5, -8.5, 1.6), (0, 0, 0)), (T(116.0), (1.2, -8.0, 1.2), (0, 0, 0)), (dur, (-0.8, -8.4, 0.9), (0, 0, 0))], rfps, lens=45)
    helix_hero_env(1, cam, rnd, rfps, dur, helices=2)

def watson_crick(nf, rfps, dur):
    """s12 122.11-134.0: slow orbit of the helix for the 1953 beat; on 'X-ray data' Photo 51 blooms as light behind it."""
    reset(); rnd = random.Random(12); T = lambda t: rt('s12', t); helix_lights(target=(0, 0, 0), key_e=2400, sec=1)
    h = Helix('DNA', HERO_SEQ[:40], loc=(0, 0, 0), individual=False, hd=True); spin(h.root, rfps, dur, rate=0.045)
    photo51('Photo51', (0.5, 7.5, 0.3), r=4.2, rfps=rfps, t_on=T(129.4))
    cam, tgt = camera((-3.0, -10.0, 1.6), (0, 0, 0), lens=45); orbit(cam, tgt, (0, 0, 0), 10.5, 1.8, -22, 24, 1, nf)
    lens_zoom(cam, rfps, [(0.0, 45), (dur, 52)])
    helix_hero_env(1, cam, rnd, rfps, dur, helices=3, halo_r=0.0)

def gene_segment(nf, rfps, dur):
    """s15 141.54-156.38: a lateral dolly along a long helix; a stretch of it lights amber as 'genes' is spoken (anchor RpGene);
    a small folded protein forms above it on a beam of light for 'the instruction to make one protein'; then the camera pulls
    back and many more gene stretches light up along the helix and its neighbours for 'twenty thousand'."""
    reset(); rnd = random.Random(15); T = lambda t: rt('s15', t)
    theme_lights(2, target=(0, 0, 0), key=(3.5, -7.0, 7.0), key_e=2800, spot=60, fill_e=200, rim_e=520, accent_e=260, accent_pos=(-5, 4, -3))
    h = Helix('DNA', rand_seq(70, 15), loc=(0, 0, 0), individual=False, hd=True); spin(h.root, rfps, dur, rate=0.02)
    g0, g1 = 26, 40
    gs = glow_sleeve('GeneGlow', h.axis_pt(g0) - X * 0.2, h.axis_pt(g1) + X * 0.2, 1.32, GENE, strength=0.7, alpha=0.13); parent(gs, h.root); scale_in(gs, rfps, T(143.8), dur=0.7)
    anchor('Gene', h.axis_pt((g0 + g1) // 2) + Vector((0, -0.3, 1.55)), h.root)
    gc = h.axis_pt((g0 + g1) // 2)
    ch = Chain('Prot', ['Met', 'Gly', 'Pro', 'Ala', 'Leu', 'Ser', 'Lys', 'Val', 'Glu', 'Phe', 'Thr', 'Asp'], r=0.16, r_link=0.05, hd=False)
    fp = fold_path(12, seed=4, box=0.7, step=0.42); ch.pose([tuple(p) for p in fp], 1)
    prot = empty('ProtRoot', tuple(gc + Vector((0, -0.4, 3.4))))
    for o in ch.objects(): parent(o, prot)
    scale_in(prot, rfps, T(149.0), dur=0.8); spin(prot, rfps, dur, rate=0.12, axis=2)
    anchor('Prot', (0, -0.5, 1.1), prot)
    bm = beam('Beam', gc + Vector((0, 0, 1.2)), gc + Vector((0, -0.4, 2.6)), r=0.07, color=GENE, strength=1.6, f_on=F(T(148.0), rfps), alpha=0.4); scale_in(bm, rfps, T(148.0), dur=0.5)
    for k in range(8):                                       # more genes along the helix for 'twenty thousand'
        a = rnd.choice([2, 8, 14, 46, 52, 58, 64]) + rnd.randint(-1, 1); b = a + rnd.randint(3, 6)
        g = glow_sleeve(f'Gene{k}', h.axis_pt(max(0, a)), h.axis_pt(min(69, b)), 1.3, GENE, strength=0.7, alpha=0.13); parent(g, h.root); scale_in(g, rfps, T(153.1 + 0.25 * k), dur=0.5)
    for k in range(3):
        bh = Helix(f'Far{k}', rand_seq(50, 20 + k), loc=(rnd.uniform(-6, 6), 9 + 3 * k, rnd.uniform(-4, 4)), rot=(0, 0, rnd.uniform(-0.4, 0.4)), individual=False, hd=False, sub_pt=4)
        spin(bh.root, rfps, dur, rate=0.03)
        for j in range(3):
            a = rnd.randint(2, 40); g = glow_sleeve(f'FarGene{k}{j}', bh.axis_pt(a), bh.axis_pt(a + 5), 1.25, GENE, strength=0.7, alpha=0.13); parent(g, bh.root); scale_in(g, rfps, T(153.4 + 0.3 * j + 0.2 * k), dur=0.5)
    cam, tgt = cam_path([(0.0, (-7.5, -9.0, 1.8), (-6.0, 0, 0.2)), (T(146.0), tuple(gc + Vector((-0.5, -8.5, 1.6))), tuple(gc + Vector((0, 0, 0.6)))), (T(152.5), tuple(gc + Vector((1.0, -8.0, 2.0))), tuple(gc + Vector((0, 0, 1.4)))),
                         (dur, tuple(gc + Vector((2.0, -19.0, 5.0))), tuple(gc + Vector((0, 2, 0.5))))], rfps, lens=45)
    env_kit(2, cam, rnd, rfps, dur, center=tuple(gc), dust_n=140, dust_spread=(18, 12, 8), halo_r=7.0, halo_at=tuple(gc + Vector((0, 5, 0.5))), bokeh=4)

def protein_gallery(nf, rfps, dur):
    """s16 156.38-168.81: pan across three protein heroes as they are named: haemoglobin (four folded chains, haems, O2 glowing
    in its pocket), an enzyme catching a substrate in its pocket, and keratin coiled coils; rack focus from one to the next."""
    reset(); rnd = random.Random(16); T = lambda t: rt('s16', t)
    theme_lights(2, target=(0, 0, 0.3), key=(2.0, -8.0, 8.0), key_e=3400, spot=75, fill_e=260, rim_e=560, accent_e=300, accent_pos=(-6, 4, -3))
    hb, lobes, o2 = haemoglobin('Hb', (-5.2, 0, 0.3), s=1.0, spread=1.0); spin(hb, rfps, dur, rate=0.05, axis=2)
    kf(o2, 'location', F(T(160.0), rfps), (0, -3.5, 0.8)); kf(o2, 'location', F(T(162.2), rfps), (0, 0, 0)); kf_ease(o2)
    anchor('Hb', (0, -0.6, 1.9), hb); anchor('O2', (0, 0, 0.35), o2)
    en = enzyme('Enz', (0.0, 0, 0.2), s=1.1); spin(en, rfps, dur, rate=0.04, axis=2); anchor('Enz', (0, -0.8, 1.9), en)
    sub = amino_acid('Sub', 'Tyr', (0, -3.6, 1.4), r=0.22); setmat(bpy.data.objects[sub['bead']], mat_lit((0.55, 0.95, 0.75), emit=1.2, name='sub_m'))
    kf(sub, 'location', F(T(163.3), rfps), (0, -3.6, 1.4)); kf(sub, 'location', F(T(165.0), rfps), (0, -1.05, 0.55)); kf_ease(sub); anchor('Sub', (0, -0.2, 0.55), sub)
    pulse(en.data.materials[0], rfps, T(165.2), (1.0, 0.85, 0.45), peak=1.6, fall=1.4)
    kr = empty('KerRoot', (5.4, 0, 0.3)); kr.rotation_euler = (0.3, 0.9, 0.2); ke = keratin('Ker', (0, 0, 0), s=0.9, n=5, length=4.6); parent(ke, kr); spin(ke, rfps, dur, rate=0.05, axis=0)
    anchor('Ker', (0, -0.9, 1.7), kr); ke = kr
    cam, tgt = cam_path([(0.0, (0.0, -13.5, 1.6), (0, 0, 0.4)), (T(160.3), (-4.0, -7.5, 1.4), (-5.2, 0, 0.3)), (T(163.4), (0.4, -7.2, 1.3), (0, 0, 0.3)), (T(166.2), (4.4, -7.4, 1.4), (5.4, 0, 0.3)),
                         (dur, (0.6, -12.5, 1.8), (0, 0, 0.4))], rfps, lens=45)
    if os.environ.get('VL_DOF', '0') == '1':
        rack_focus(cam, F(T(160.3), rfps), F(T(163.4), rfps), hb, en); rack_focus(cam, F(T(163.5), rfps), F(T(166.2), rfps), en, ke)
    env_kit(2, cam, rnd, rfps, dur, center=(0, 0, 0.3), dust_n=140, dust_spread=(18, 12, 8), halo_r=8.0, halo_at=(0, 5.5, 0.5), bokeh=4, fil=4)

def nucleus_barrier(nf, rfps, dur):
    """s17 168.81-183.78: in the cytoplasm, looking at the amethyst envelope: the helix inside drifts to the wall and stops
    (DNA never leaves); ribosomes wait outside among organelles (proteins are made here); on the question the camera pushes
    to a pore; on 'messenger' an amber spark is born on the gene and drifts toward the pore."""
    reset(); rnd = random.Random(17); T = lambda t: rt('s17', t)
    theme_lights(2, target=(0, 0, 0.2), key=(4.0, -9.0, 8.0), key_e=3600, spot=70, fill_e=260, rim_e=560, accent_e=200, accent_pos=(-6, 4, -3))
    nroot, outer, inner, pores, holes = nucleus_hd('Nuc', (0, 3.2, 0), r=3.2, pores=30, hole_dirs=[(0, -1, 0)], seed=5, pore_r=0.34, a_center=0.14, a_rim=0.85, emit=1.0)
    pulse(outer.data.materials[0], rfps, T(171.6), NUC_RIM, peak=3.0, base=1.0, fall=1.2)
    light('POINT', (0.3, 3.6, 0.6), 90, (0.9, 0.8, 1.0), 'NucLight')
    h = Helix('DNA', HERO_SEQ[:22], loc=(0.2, 3.9, 0.2), rot=(0, 0, 0.35), R=0.55, rise=0.22, individual=False, hd=False, r_rail=0.05, r_sugar=0.09, r_phos=0.075, r_rung=0.07, gap=0.12, sub_pt=4)
    spin(h.root, rfps, dur, rate=0.06)
    move(h.root, rfps, [(T(168.8), (0.2, 3.9, 0.2)), (T(171.4), (0.1, 1.15, 0.2)), (T(171.9), (0.15, 1.35, 0.2)), (T(176.0), (0.15, 1.5, 0.2))])
    anchor('DNA', (0, -0.3, 0.9), h.root); anchor('Nuc', (-2.4, -2.2, 1.6), nroot); anchor('Cyto', (-3.6, -2.5, -1.4)); anchor('Pore', (0, -0.05, 0.55), pores[0])
    for k, (p, r_) in enumerate((((3.4, -2.2, -0.6), 0.5), ((-3.6, -1.6, 0.9), 0.45), ((2.6, -4.0, 1.8), 0.4))):
        rb, L, S, sites = ribosome(f'Ribo{k}', p, s=r_, translucent_large=False, sites=False); rb.rotation_euler = (rnd.uniform(0, 1), rnd.uniform(0, 1), rnd.uniform(0, 3)); drift(rb, rfps, dur, amp=0.15, seed=k, period=6)
        pulse(S.data.materials[0], rfps, T(174.0 + 0.3 * k), (1.0, 0.75, 0.85), peak=1.6, fall=1.2)
        if k == 0: anchor('Ribo', (0, -0.8, 2.3), rb)
    for o in organelles('Cyto', rnd, 30, (0, -2.0, 0), 7.0, avoid_r=4.2, s=1.0): drift(o, rfps, dur, amp=0.1, seed=rnd.randint(1, 99), period=6.0)
    filaments('Fil', rnd, 5, (0, -2, 0), (6, 4, 4), r=0.03, length=6.0)
    spark = sphere('Msg', 0.11, (0.15, 1.5, 0.2), seg=32, ring=16, mat=mat_glow(RNA_RAIL, strength=9.0, name='spark_m')); hl = halo('MsgHalo', (0, 0, 0), 0.9, RNA_RAIL, strength=1.5); parent(hl, spark)
    scale_in(spark, rfps, T(180.4), dur=0.6); move(spark, rfps, [(T(180.4), (0.15, 1.5, 0.2)), (T(183.7), (0.05, 0.25, 0.05))]); anchor('Msg', (0, 0, 0.3), spark)
    SL = light('POINT', (0, 0, 0), 0, RNA_RAIL, 'SparkLight'); parent(SL, spark); key_light(SL, F(T(180.3), rfps), 0.0); key_light(SL, F(T(181.0), rfps), 40.0)
    cam, tgt = cam_path([(0.0, (-1.5, -12.5, 2.2), (0, 1.0, 0.2)), (T(172.5), (2.5, -10.5, 1.8), (0.2, 1.4, 0.2)), (T(176.8), (0.8, -9.5, 1.4), (0, 0.6, 0.2)), (T(180.0), (0.4, -5.0, 0.9), (0, 0.4, 0.15)),
                         (dur, (0.5, -4.2, 0.7), (0.05, 0.3, 0.05))], rfps, lens=45)
    env_kit(2, cam, rnd, rfps, dur, center=(0, -2, 0), dust_n=120, dust_spread=(14, 10, 8), bokeh=3)

# ================================================================= builders: 3. Transcription (one continuous rig)
TX_SEQ = 'GCATTC' + GENE_SEQ + 'GATCCGA'          # 34 bp: 6 upstream, the 21-bp gene (strand 0 = template), 7 downstream
TX_G0, TX_G1 = 6, 27

def transcription_rig(sid, rfps, dur, pol_s=1.4, mrna=True, phase=math.pi):
    """The shared transcription set: the gene helix (individual ring-plate rig, strand 0 = template, gene lit amber), the
    polymerase clamp, and the mRNA rig lying above the helix with its bases pointing down (nucleotide j sits over gene base j,
    so it appears exactly where the polymerase is when built).  Returns dict(h, pol, gene, rna, T)."""
    T = lambda t: rt(sid, t)
    theme_lights(3, target=(0, 0, 0), key=(3.5, -7.0, 7.0), key_e=3000, spot=62, fill_e=220, rim_e=560, accent_e=320, accent_pos=(5, 3, -3))
    h = Helix('DNA', TX_SEQ, loc=(0, 0, 0), individual=True, hd=True, phase=phase)
    gene = glow_sleeve('GeneGlow', h.axis_pt(TX_G0) - X * 0.2, h.axis_pt(TX_G1 - 1) + X * 0.2, 1.32, GENE, strength=0.6, alpha=0.11); parent(gene, h.root)
    pol = polymerase('Pol', loc=tuple(h.axis_pt(TX_G0)), s=pol_s)
    rna = None
    if mrna: rna = RNA('mRNA', MRNA_SEQ, loc=(0, 0.0, 1.5), side=(0, 0, -1), rise=h.rise, start=h.axis_pt(TX_G0).x, hd=True, individual=True)
    return dict(h=h, pol=pol, gene=gene, rna=rna, T=T)

def polymerase_lands(nf, rfps, dur):
    """s19 186.38-196.46: 'transcription' over the lit gene; on 'RNA polymerase' the clamp drifts in from the void with open
    jaws, settles on the start of the gene and closes on the helix (anchors RpPol, RpGene)."""
    reset(); rnd = random.Random(19); R = transcription_rig('s19', rfps, dur, mrna=False); h, pol, T = R['h'], R['pol'], R['T']
    g = h.axis_pt(TX_G0); far = g + Vector((-5.0, -3.5, 4.5))
    move(pol, rfps, [(T(186.4), tuple(far)), (T(189.6), tuple(far)), (T(194.3), tuple(g))]); rot_keys(pol, rfps, [(T(189.6), (0.5, -0.4, 0.3)), (T(194.3), (0, 0, 0))])
    jaws(pol, rfps, [(T(189.6), 1.0), (T(194.3), 1.0), (T(195.5), 0.0)])
    anchor('Pol', (0, -1.2, 2.9), pol); anchor('Gene', h.axis_pt((TX_G0 + TX_G1) // 2) + Vector((0, -0.5, -1.7)), h.root)
    pulse(R['gene'].data.materials[0], rfps, T(195.6), GENE, peak=2.6, base=0.9, fall=1.0)
    cam, tgt = cam_path([(0.0, (-2.5, -13.0, 3.0), (0, 0, 0.2)), (T(189.6), tuple(g + Vector((-3.5, -11.0, 2.8))), tuple(g + Vector((-2.0, 0, 1.2)))), (T(194.3), tuple(g + Vector((-1.6, -8.8, 2.2))), tuple(g)),
                         (dur, tuple(g + Vector((-1.2, -8.2, 1.9))), tuple(g + Vector((0.2, 0, 0.1))))], rfps, lens=45)
    env_kit(3, cam, rnd, rfps, dur, center=tuple(g), dust_n=130, halo_r=7.0, halo_at=tuple(g + Vector((0, 5, 0.5))), bokeh=4, helices=2)

def unzip_build(nf, rfps, dur):
    """s20 196.46-207.17: the polymerase opens the two strands like a zip (the bubble opens behind it as it crawls), reads the
    template (RpTempl) and builds the new amber strand nucleotide by nucleotide above it (RpNew); the camera tracks it."""
    reset(); rnd = random.Random(20); R = transcription_rig('s20', rfps, dur); h, pol, rna, T = R['h'], R['pol'], R['rna'], R['T']
    v = 0.85; t_go = T(197.2)
    pos = lambda t: TX_G0 + max(0.0, min(TX_G1 - TX_G0 - 0.5, v * (t - t_go)))
    depth = lambda t: 0.72 * smooth01((t - T(196.7)) / 2.6)
    f0, f1 = 1, nf
    for f in range(f0, f1 + 1, 2):
        t = (f - 1) / rfps; c = pos(t); dp = depth(t)
        h.key_open(f, lambda i: dp * math.exp(-((i - c) / 3.2) ** 2) if abs(i - c) < 9.6 else 0.0)
    if (f1 - f0) % 2: h.key_open(f1, lambda i: depth((f1 - 1) / rfps) * math.exp(-((i - pos((f1 - 1) / rfps)) / 3.2) ** 2))
    for c in h.rail_objs: lin_id(c.data)
    for u in h.units.values(): lin_id(u)
    for f in range(f0, f1 + 1, 3):
        t = (f - 1) / rfps; kf(pol, 'location', f, tuple(h.axis_pt(pos(t))))
    kf_lin(pol); jaws(pol, rfps, [(0.0, 0.0)])
    rna.grow(rfps, T(200.9), 1.0 / v)
    for j in range(rna.N):
        u = rna.units[j]; t_j = T(200.9) + j / v
        kf(u, 'location', F(t_j, rfps), tuple(rna.axis_pt(j) - Vector((0, 0, 0.9)))); kf(u, 'location', F(t_j + 0.6, rfps), tuple(rna.axis_pt(j))); kf_ease(u)
    anchor('Templ', (0, h.y_out + 0.35, 0.0), h.units[(TX_G0 + 4, 0)]); anchor('New', (0, -0.45, 0.0), rna.units[3])
    pulse(m_base('U'), rfps, T(203.4), BASE['U'], peak=2.0, fall=1.2)
    keys = []
    for t, ang in ((0.0, -0.35), (T(200.0), -0.15), (T(204.0), 0.15), (dur, 0.35)):
        p = h.axis_pt(pos(t)); off = Vector((-1.2 + 2.0 * math.sin(ang), -8.4 * math.cos(ang), 1.9))
        keys.append((t, tuple(p + off), tuple(p + Vector((0, 0, 0.35)))))
    cam, tgt = cam_path(keys, rfps, lens=45)
    env_kit(3, cam, rnd, rfps, dur, center=tuple(h.axis_pt(TX_G0 + 4)), dust_n=130, halo_r=7.0, halo_at=tuple(h.axis_pt(TX_G0 + 6) + Vector((0, 5, 0.5))), bokeh=4, helices=2)

def rna_vs_dna(nf, rfps, dur):
    """s21 207.17-225.22: open-book close-up: the template strand below, the new amber strand above, paired by glowing dashes.
    'RNA' lands; 'single stranded' lifts the strand alone; a ghost thymine appears beside the violet uracil that took its
    place ('U'); then the template A lights and a beam rises to the U above it: where DNA has A, RNA has U."""
    reset(); rnd = random.Random(21); T = lambda t: rt('s21', t)
    theme_lights(3, target=(0, 0, 0.6), key=(2.5, -7.5, 7.0), key_e=3000, spot=65, fill_e=230, rim_e=560, accent_e=320, accent_pos=(5, 3, -3))
    n = 12; tseq = GENE_SEQ[:n]; rseq = MRNA_SEQ[:n]; K = 5
    dna_rail = mat_gloss(RAIL_A, rough=0.28, coat=0.5, name='tmpl_rail'); dna_sugar = mat_gloss(SUGAR, rough=0.3, coat=0.4, name='tmpl_sugar', sss=0.15)
    tm = RNA('Templ', tseq, loc=(0, 0, -0.62), side=(0, 0, 1), rise=0.62, hd=True, individual=True, rail_mat=dna_rail, sugar_mat=dna_sugar)
    rn = RNA('mRNA', rseq, loc=(0, 0, 1.35), side=(0, 0, -1), rise=0.62, hd=True, individual=True); upd()
    mU = mat_gloss(BASE['U'], rough=0.25, coat=0.6, name='U_hero', sss=0.1); setmat(rn.bases[K], mU)
    mA = mat_gloss(BASE['A'], rough=0.25, coat=0.6, name='A_hero', sss=0.1); setmat(tm.bases[K], mA)
    dashes = []
    for j in range(n):
        p0 = tm.world(tm.base_tip(j)) + Vector((0, 0, 0.02)); p1 = rn.world(rn.base_tip(j)) - Vector((0, 0, 0.02)); k = 2 if rseq[j] in 'AU' else 3
        bm = bmesh.new()
        for o in ([-0.055, 0.055] if k == 2 else [-0.085, 0.0, 0.085]): capsule_into(bm, p0 + Vector((o, 0, 0)), p1 + Vector((o, 0, 0)), 0.028, 8, 4)
        d = mesh_obj(f'Dash{j}', bm, m_hbond()); dashes.append(d)
        try: d.visible_shadow = False
        except Exception: pass
    for d in dashes: kf(d, 'scale', F(T(214.0), rfps), (1, 1, 1)); kf(d, 'scale', F(T(214.6), rfps), (1, 1, 0.001)); kf(d, 'scale', F(T(220.2), rfps), (1, 1, 0.001)); kf(d, 'scale', F(T(220.9), rfps), (1, 1, 1)); kf_ease(d)
    move(rn.root, rfps, [(T(214.0), (0, 0, 1.35)), (T(215.0), (0, 0.3, 1.70)), (T(219.9), (0, 0.3, 1.70)), (T(220.9), (0, 0, 1.35))])   # 'single stranded': lifts half a unit, stays in the band with the template
    ghost = single_base('GhostT', 'T', loc=(0, 0, 0), s=1.0, rot=(0, 0, 0), mat=mat_translucent(BASE['T'], alpha=0.35, emit=0.6, name='ghostT'))[0]
    ghost.parent = rn.units[K]; ghost.matrix_parent_inverse = Matrix.Identity(4); ghost.location = (0, 0, -0.55); ghost.rotation_euler = (math.pi, 0, 0)
    scale_in(ghost, rfps, T(217.0), dur=0.5); scale_out(ghost, rfps, T(219.6), dur=0.4); anchor('Ghost', (0.0, 0.0, 0.5), ghost)
    pulse(mU, rfps, T(218.4), BASE['U'], peak=2.4, fall=1.2); pulse(mU, rfps, T(222.7), BASE['U'], peak=2.4, fall=1.2); pulse(mA, rfps, T(221.3), BASE['A'], peak=2.4, fall=1.2)
    bx = tm.world(tm.axis_pt(K)).x
    beam('AU', (bx, 0, -0.1), (bx, 0, 1.1), r=0.07, color=(0.8, 0.95, 1.0), strength=4.0, f_on=F(T(222.0), rfps), f_off=F(T(224.6), rfps), alpha=0.6)
    anchor('RNA', (0, 0, 0.55), rn.root); anchor('DNA', (0, 0, -0.55), tm.root); rn.add_anchor(K, tag='U'); tm.add_anchor(K, tag='A')
    drift(tm.root, rfps, dur, amp=0.03, seed=3, period=4.0)
    cam, tgt = cam_path([(0.0, (-3.0, -9.8, 1.5), (-1.0, 0, 0.45)), (T(213.0), (1.6, -9.2, 1.3), (0.5, 0, 0.5)), (T(216.6), (bx - 0.5, -7.4, 1.4), (bx, 0, 0.60)), (T(220.5), (bx + 0.5, -6.6, 1.1), (bx, 0, 0.5)),
                         (dur, (bx - 0.2, -6.9, 1.2), (bx, 0, 0.45))], rfps, lens=45)       # both strands stay inside the middle band of the frame; the A -> U column ends up centred
    env_kit(3, cam, rnd, rfps, dur, center=(0, 0, 0.5), dust_n=130, halo_r=6.5, halo_at=(0, 7.0, 0.6), bokeh=4, helices=2, halo_alpha=0.6)

def mrna_release(nf, rfps, dur):
    """s22 225.22-238.14: the polymerase reaches the gene end and lifts off; the finished copy lets go of the template, curls
    up and away, and the helix zips closed behind it; 'messenger RNA' lands on the drifting strand (RpMRNA)."""
    reset(); rnd = random.Random(22); R = transcription_rig('s22', rfps, dur); h, pol, rna, T = R['h'], R['pol'], R['rna'], R['T']
    v = 0.85; t_end = T(228.4)
    pos = lambda t: (23.3 + v * t) if t < t_end else (23.3 + v * t_end + 1.4 * v * (t - t_end))
    depth = lambda t: 0.72 * (1.0 - smooth01((t - T(229.0)) / 2.4))
    for f in range(1, nf + 1, 2):
        t = (f - 1) / rfps; c = pos(t); dp = depth(t)
        h.key_open(f, lambda i: dp * math.exp(-((i - c) / 3.2) ** 2) if abs(i - c) < 9.6 else 0.0)
    if nf % 2 == 0: h.key_open(nf, lambda i: 0.0)
    for c in h.rail_objs: lin_id(c.data)
    for u in h.units.values(): lin_id(u)
    for f in range(1, nf + 1, 3):
        t = (f - 1) / rfps; p = h.axis_pt(pos(t)); lift = 2.6 * smooth01((t - t_end) / 2.5)
        kf(pol, 'location', f, tuple(p + Vector((0, 1.2 * lift / 2.6, lift))))
    kf_lin(pol); jaws(pol, rfps, [(t_end, 0.0), (t_end + 1.4, 1.0)])
    rna.grow(rfps, 0.0, 0.0001); rna.hide_all_until(1)
    move(rna.root, rfps, [(T(228.6), (0, 0, 1.5)), (T(232.0), (-1.5, 1.6, 3.6)), (dur, (-6.0, 3.0, 4.6))]); rot_keys(rna.root, rfps, [(T(228.6), (0, 0, 0)), (T(232.0), (0.5, 0.15, 0.2)), (dur, (1.1, 0.3, 0.5))])
    anchor('MRNA', (0, -0.5, 0.0), rna.units[10]); anchor('Pol', (0, -1.0, 2.9), pol)
    pulse(m_rna_rail(), rfps, T(233.2), RNA_RAIL, peak=2.2, fall=1.4)
    gE = h.axis_pt(TX_G1 - 1)
    cam, tgt = cam_path([(0.0, tuple(gE + Vector((-2.5, -8.4, 1.9))), tuple(gE + Vector((-1.5, 0, 0.35)))), (T(229.0), tuple(gE + Vector((-1.0, -9.5, 2.4))), tuple(gE + Vector((-0.5, 0, 1.2)))),
                         (T(233.0), (-1.0, -11.0, 3.6), (-1.5, 1.6, 3.2)), (dur, (-2.5, -10.5, 4.6), (-6.0, 3.0, 4.4))], rfps, lens=45)
    env_kit(3, cam, rnd, rfps, dur, center=(0, 0, 1), dust_n=140, dust_spread=(16, 12, 9), halo_r=8.0, halo_at=(-2, 6, 2), bokeh=4, helices=2)

def pore_exit(nf, rfps, dur):
    """s23 238.14-247.44: the mRNA threads through an eight-fold pore complex in the nuclear wall while the camera follows it
    THROUGH the pore; the teal cytoplasm opens up beyond: organelles, filaments, ribosomes waiting (RpPore, RpCyto, RpMRNA)."""
    reset(); rnd = random.Random(23); T = lambda t: rt('s23', t)
    theme_lights(3, target=(0, 0, 0), key=(3.0, 4.0, 8.0), key_e=3200, spot=70, fill_e=260, rim_e=520, accent_e=300, accent_pos=(-5, 8, -2))
    NC = Vector((0, -12.0, 0)); R_ = 12.0
    nroot, outer, inner, pores, holes = nucleus_hd('Nuc', tuple(NC), r=R_, pores=14, hole_dirs=[(0, 1, 0)], seed=7, inside=True, pore_r=0.95, a_center=0.14, a_rim=0.9, emit=1.2)
    crossing(outer.data.materials[0], rfps, T(242.2), a_hi=0.5, emit_hi=4.0, a_lo=0.14, emit_lo=1.2, post=0.7); crossing(inner.data.materials[0], rfps, T(242.0), a_hi=0.4, emit_hi=3.0, a_lo=0.11, emit_lo=0.7, post=0.7)
    light('POINT', (0.5, -2.5, 1.0), 120, (0.9, 0.8, 1.0), 'NucLight'); light('POINT', (0.8, 3.5, 0.6), 160, (0.7, 1.0, 0.95), 'CytoLight')
    rna = RNA('mRNA', MRNA_SEQ, loc=(0, -6.5, 0), rot=(0, 0, math.pi / 2), side=(0, 0, 1), rise=0.40, hd=True, wave=0.10, wave_len=3.0)
    move(rna.root, rfps, [(0.0, (0, -7.0, 0)), (T(242.2), (0, 0.9, 0)), (dur, (0.6, 7.5, 0.4))], ease=False)
    kf(rna.root, 'rotation_euler', 1, (0, 0, math.pi / 2)); kf(rna.root, 'rotation_euler', nf, (2 * math.pi * 0.35, 0, math.pi / 2)); kf_lin(rna.root)
    anchor('MRNA', (0, 0, 0.7), rna.root); anchor('Pore', (1.2, 0.0, 0.9), pores[0]); anchor('Cyto', (3.0, 5.0, 1.5))
    for o in organelles('Cyto', rnd, 36, (0, 9.5, 0), 7.0, avoid_r=2.5, s=1.0): drift(o, rfps, dur, amp=0.1, seed=rnd.randint(1, 99), period=6.0)
    filaments('Fil', rnd, 6, (0, 8, 0), (6, 5, 4), r=0.03, length=7.0)
    for k, p in enumerate(((3.2, 6.5, -1.2), (-3.0, 8.0, 1.6), (1.5, 10.5, 2.4))):
        rb, L, S, sites = ribosome(f'Ribo{k}', p, s=0.55, translucent_large=False, sites=False); rb.rotation_euler = (rnd.uniform(0, 1), rnd.uniform(0, 1), rnd.uniform(0, 3)); drift(rb, rfps, dur, amp=0.15, seed=k, period=6)
    for k in range(3):
        pth = [(rnd.uniform(-5, 5), rnd.uniform(-9, -3), rnd.uniform(-3, 3)) for _ in range(4)]
        nucleosome_fibre(f'Thread{k}', pth, spacing=0.6, r_spool=0.14, r_fibre=0.025, seed=k + 5)
    cam, tgt = cam_path([(0.0, (0.9, -10.5, 1.3), (0, -5.5, 0.1)), (T(241.0), (0.5, -3.2, 0.9), (0, 0.2, 0.1)), (T(242.6), (0.15, 0.2, 0.35), (0.1, 2.5, 0.2)), (T(244.5), (0.4, 2.4, 0.9), (0.4, 6.0, 0.3)),
                         (dur, (1.4, 3.4, 1.4), (0.6, 8.0, 0.4))], rfps, lens=45)
    env_kit(3, cam, rnd, rfps, dur, center=(0, 4, 0), dust_n=140, dust_spread=(12, 14, 8), bokeh=3)


# ================================================================= shared helpers added in the finishing pass
def join_objects(name, objs, remove=True):
    """Bake a group of meshes / bevelled curves (world space, modifiers applied) into ONE mesh with all their materials."""
    upd(); dg = bpy.context.evaluated_depsgraph_get(); bm = bmesh.new(); mats = []
    for o in objs:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        base = len(mats); om = [m for m in o.data.materials if m is not None] or [None]; mats += om
        for pl in me.polygons: pl.material_index = min(len(om) - 1, pl.material_index) + base
        me.transform(o.matrix_world); bm.from_mesh(me); bpy.data.meshes.remove(me)
    out = mesh_obj(name, bm, None)
    for m in mats: out.data.materials.append(m)
    if remove:
        for o in objs: bpy.data.objects.remove(o)
    return out

def mat_fog(color=(0.012, 0.02, 0.05), alpha=0.10, name='fog'):
    m, p = _principled(name); _inp(p, 'Base Color', (*color, 1)); _inp(p, 'Alpha', alpha); _inp(p, 'Roughness', 1.0); _inp(p, 'Specular IOR Level', 0.0); _inp(p, 'Coat Weight', 0.0)
    _blend(m); return m

def fog_cards(n, d0, d1, color=(0.012, 0.02, 0.05), alpha=0.10, size=90, axis='y', name='Fog'):
    """Depth haze that works in EEVEE too: a stack of faint navy cards across the axis, so far things sink into the void."""
    m = mat_fog(color, alpha=alpha * (0.5 if CY else 1.0), name=name + '_m'); out = []
    for k in range(n):
        d = d0 + (d1 - d0) * k / max(1, n - 1)
        o = obj_add('plane', f'{name}{k}', size=size, location=(0, d, 0) if axis == 'y' else (d, 0, 0)); o.rotation_euler = (math.pi / 2, 0, 0) if axis == 'y' else (0, math.pi / 2, 0)
        setmat(o, m)
        try: o.visible_shadow = False
        except Exception: pass
        out.append(o)
    return out

def lathe_obj(name, prof_fn, z0, z1, n=90, verts=64, mat=None, bend=None):
    """Lathe a solid along z from a radius profile r(z) with an optional axis offset bend(z) -> (dx, dy)."""
    bm = bmesh.new(); rings = []
    for k in range(n + 1):
        z = z0 + (z1 - z0) * k / n; r = max(0.0, prof_fn(z)); off = bend(z) if bend else (0.0, 0.0)
        rings.append([bm.verts.new((off[0] + r * math.cos(2 * math.pi * j / verts), off[1] + r * math.sin(2 * math.pi * j / verts), z)) for j in range(verts)])
    for a, b in zip(rings[:-1], rings[1:]):
        for j in range(verts): bm.faces.new((a[j], a[(j + 1) % verts], b[(j + 1) % verts], b[j]))
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-4); bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    return mesh_obj(name, bm, mat)

def mat_chromatid(name='chromatid', base=CHROM, band=(0.55, 0.62, 1.0), scale=9.0):
    """Condensed chromatin skin: banded (G-band-like wave stripes distorted by noise), a fine coil bump, subsurface."""
    m = mat_organic(base, rough=0.4, sss=0.3, coat=0.3, name=name, radius=(0.3, 0.4, 1.0)); nt = m.node_tree; n = nt.nodes; p = n.get('Principled BSDF')
    tc = n.new('ShaderNodeTexCoord'); wv = n.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'Z'
    wv.inputs['Scale'].default_value = scale; wv.inputs['Distortion'].default_value = 2.2; wv.inputs['Detail'].default_value = 3.0; wv.inputs['Detail Scale'].default_value = 2.0
    ramp = n.new('ShaderNodeValToRGB'); e = ramp.color_ramp.elements; e[0].position = 0.3; e[0].color = (*base, 1); e[1].position = 0.7; e[1].color = (*band, 1)
    noise = n.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 40.0; noise.inputs['Detail'].default_value = 3.0
    bmp = n.new('ShaderNodeBump'); bmp.inputs['Strength'].default_value = 0.25; bmp2 = n.new('ShaderNodeBump'); bmp2.inputs['Strength'].default_value = 0.35
    nt.links.new(tc.outputs['Object'], wv.inputs['Vector']); nt.links.new(tc.outputs['Object'], noise.inputs['Vector'])
    nt.links.new(wv.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], p.inputs['Base Color'])
    nt.links.new(noise.outputs['Fac'], bmp.inputs['Height']); nt.links.new(wv.outputs['Fac'], bmp2.inputs['Height']); nt.links.new(bmp.outputs['Normal'], bmp2.inputs['Normal']); nt.links.new(bmp2.outputs['Normal'], p.inputs['Normal'])
    return m

def chromosome_hd(name, loc, s=1.0, rot=(0, 0, 0), seed=1, coil=True):
    """Detailed metaphase chromosome: two chromatids lathed from a banded profile (rounded arm tips, a deep centromere
    pinch, arms that diverge slightly), a noise-displaced + subdivided lumpy silhouette, a banded/bumped chromatin skin,
    a visible solenoid coil of chromatin fibre with nucleosome beads wound just under the surface of every arm, and a
    kinetochore knob at the centromere.  Returns root; root['objs'] lists the mesh/curve children."""
    rnd = random.Random(seed); root = empty(name, loc); root.rotation_euler = rot; objs = []
    L = 1.05 * s; m = mat_chromatid(name + '_m')
    def prof(z):
        u = min(1.0, abs(z) / L); tip = (1 - u ** 6) ** 0.5
        return 0.30 * s * (1 - 0.5 * math.exp(-(z / (0.20 * s)) ** 2)) * tip * (1 + 0.05 * math.sin(z * 16 / s) + 0.03 * math.sin(z * 37 / s + 1.0))
    for sg in (-1, 1):
        bend = lambda z, sg=sg: (sg * (0.20 + 0.12 * (abs(z) / L) ** 1.5) * s, 0.05 * s * math.sin(z * 3 / s + sg))
        o = lathe_obj(f'{name}_ct{sg}', prof, -L, L, n=110, verts=64, mat=m, bend=bend); parent(o, root); objs.append(o)
        tx = bpy.data.textures.new(f'{name}_tx{sg}', 'CLOUDS'); tx.noise_scale = 0.32 * s
        md = o.modifiers.new('disp', 'DISPLACE'); md.texture = tx; md.strength = 0.045 * s; md.mid_level = 0.5
        subsurf(o, 1, 2)
        if coil:
            fm = M('chromfib', lambda: mat_gloss(CHROM, rough=0.3, coat=0.5, name='chromfib')); sm = M('histone', lambda: mat_gloss(HISTONE, rough=0.35, coat=0.35, name='histone', sss=0.2))
            pts = []; beads = []; bn = []; turns = 2 * L / (0.095 * s); n = int(turns * 12)
            for u in range(n + 1):
                f = u / n; z = -L * 0.97 + 1.94 * L * f; ang = 2 * math.pi * turns * f; r = prof(z) * 1.03 + 0.005 * s; off = bend(z)
                p = Vector((off[0] + r * math.cos(ang), off[1] + r * math.sin(ang), z)); pts.append(p)
                if u % 6 == 0 and 0.06 * s < r: beads.append(p); bn.append(Vector((math.cos(ang), math.sin(ang), 0)))
            fib = curve_obj(f'{name}_coil{sg}', pts, 0.024 * s, fm, res=2, kind='POLY', bevel_res=4); parent(fib, root); objs.append(fib)
            bd = spheres_mesh(f'{name}_beads{sg}', beads, 0.038 * s, sm, subdiv=1, scale3=(1, 1, 0.7), normals=bn); parent(bd, root); objs.append(bd)
    kn = sphere(f'{name}_kin', 0.19 * s, (0, 0, 0), seg=32, ring=16, mat=M('kinet', lambda: mat_gloss((0.62, 0.66, 0.98), rough=0.35, coat=0.4, name='kinet', sss=0.2)), scale=(1.6, 1.0, 0.55)); parent(kn, root); objs.append(kn)
    for sg in (-1, 1):                                          # two kinetochore plates
        pl = sphere(f'{name}_kp{sg}', 0.11 * s, (0, sg * 0.16 * s, 0), seg=24, ring=12, mat=M('kinet2', lambda: mat_gloss((0.85, 0.80, 1.0), rough=0.35, coat=0.4, name='kinet2')), scale=(1.4, 0.5, 0.9)); parent(pl, root); objs.append(pl)
    root['objs'] = [x.name for x in objs]
    return root

# ================================================================= builders: 1. Structure of DNA (rebuilt s05, s13)
def unravel_two_metres(nf, rfps, dur):
    """s05 46.75-56.92: inside the nucleus a detailed condensed chromosome (two banded chromatids, centromere pinch, coiled
    fibre under the skin) holds the left of the frame while its chromatin fibre (beads on a string) unwinds out of the
    upper-right arm and runs off to the horizon for 'two metres'; on 'let us go closer' the camera pushes into a naked
    stretch where the double helix shows (match cut into s06).  Background chromosomes drift out of focus."""
    reset(); rnd = random.Random(5); T = lambda t: rt('s05', t)
    theme_lights(1, target=(0.5, 0, 0.6), key=(4, -8, 9), key_e=3400, spot=60, fill_e=240, rim_e=560, accent_e=320, accent_pos=(-6, 4, -3))
    nucleus_hd('Envelope', (0, 0, 0), r=16.0, pores=0, seed=3, inside=True, a_center=0.05, a_rim=0.35, emit=0.5, bump=0.0)
    ROT = (0.22, 0.12, 0.30); hero = chromosome_hd('ChrHero', (0, 0, 0.2), s=1.5, rot=ROT, seed=1)
    rot_keys(hero, rfps, [(0, ROT), (dur, (0.14, 0.06, 0.05))])
    proto = [bpy.data.objects[x] for x in hero['objs']]
    baked = [bake_mods(o) if o.type == 'MESH' else o for o in proto]
    rnd2 = random.Random(9)
    for k in range(7):
        p = Vector((rnd2.uniform(-10, 10), rnd2.uniform(6, 13), rnd2.uniform(-5, 5)))
        r, out = dup_tree(baked, f'ChrBg{k}', tuple(p), rot=(rnd2.uniform(0, 3), rnd2.uniform(0, 3), rnd2.uniform(0, 3)), scale=rnd2.uniform(0.5, 0.8)); drift(r, rfps, dur, amp=0.3, seed=k, period=7)
    # the fibre: from the upper-right arm tip out to the horizon; a naked helix stretch at its start
    import mathutils
    tip = Vector((0, 0, 0.2)) + mathutils.Euler(ROT).to_matrix() @ Vector((0.62 * 1.5, 0.0, 1.02 * 1.5))
    path = [tip, tip + Vector((0.9, 0.4, 0.25)), tip + Vector((2.5, 1.4, -0.2)), tip + Vector((5.3, 3.6, -0.8)), tip + Vector((9.3, 8.0, -1.4)), tip + Vector((15.3, 16.0, -2.2)), tip + Vector((23.3, 28.0, -3.0))]
    froot, fibre, spools, centres = nucleosome_fibre('Fibre', path, spacing=0.75, r_spool=0.19, r_fibre=0.03, seed=2)
    grow_curve(fibre, F(T(47.6), rfps), F(T(53.2), rfps)); bpy.data.objects.remove(spools)
    sm = M('histone', lambda: mat_gloss(HISTONE, rough=0.35, coat=0.35, name='histone', sss=0.2))
    nchunk = 6; per = max(1, len(centres) // nchunk + 1)
    for c in range(nchunk):
        cs = centres[c * per:(c + 1) * per]
        if not cs: continue
        o = spheres_mesh(f'Spools{c}', cs, 0.19, sm, subdiv=3, scale3=(1, 1, 0.62), normals=[(0, 0, 1)] * len(cs)); parent(o, froot)
        hide_until(o, F(T(47.6) + (T(53.2) - T(47.6)) * (c + 0.3) / nchunk, rfps))
    HX = tip + Vector((0.55, 0.22, 0.1))
    mini = Helix('Mini', rand_seq(40, 3), loc=tuple(HX), rot=(0, 0, 0.42), R=0.11, rise=0.045, individual=False, hbonds=True, sub_pt=4, r_rail=0.012, r_sugar=0.022, r_phos=0.018, r_rung=0.016, gap=0.03)
    for o in mini.all_objects(): hide_until(o, F(T(52.0), rfps))
    spin(mini.root, rfps, dur, rate=0.08)
    beam('Ray', tuple(HX), tuple(HX + Vector((1.4, 0.9, -0.1))), r=0.02, color=(0.75, 0.9, 1.0), strength=1.2, f_on=F(T(47.6), rfps), f_off=F(T(52.5), rfps), alpha=0.3)
    cam, tgt = cam_path([(0.0, (-3.2, -11.5, 2.0), (0.2, 0, 0.5)), (T(48.0), (-2.2, -10.5, 2.3), (0.6, 0.2, 1.0)), (T(53.5), tuple(tip + Vector((2.6, -7.2, 0.9))), tuple(tip + Vector((2.2, 1.6, -0.4)))),
                         (T(54.0), tuple(tip + Vector((2.6, -7.0, 0.9))), tuple(HX)), (dur, tuple(HX + Vector((0.3, -0.95, 0.15))), tuple(HX))], rfps, lens=45)
    env_kit(1, cam, rnd, rfps, dur, center=(0, 0, 0), dust_n=150, dust_spread=(14, 12, 8), halo_r=7.0, halo_at=(0.5, 5, 0.5), bokeh=3)
    dust('NucDust', rnd, 90, (2, 2, 0), (5, 5, 3), r=0.012, color=(0.85, 0.75, 1.0), strength=2.0, rfps=rfps, dur=dur)
    for k in range(3):
        pth = [(rnd.uniform(-8, 8), rnd.uniform(3, 10), rnd.uniform(-4, 4)) for _ in range(4)]
        nucleosome_fibre(f'Thread{k}', pth, spacing=0.6, r_spool=0.14, r_fibre=0.025, seed=k + 5)

def three_billion(nf, rfps, dur):
    """s13 134.0-138.94: one 10-bp HD helix segment (a full turn) baked to a single mesh and repeated by an Array modifier
    (700 bp, no per-base objects).  The helix starts BEHIND the camera and runs to the horizon: the lens sits just outside
    the near turns (rails, sugars and plates cross every frame edge, out of focus) and pulls back and up along the axis
    while the helix converges on a bright vanishing point through depth haze (fog cards); eight side helices fill the
    periphery, four more far off, point lights ride the axis so the receding turns glint, motes everywhere: vast."""
    reset(); rnd = random.Random(13); T = lambda t: rt('s13', t)
    theme_lights(1, target=(0, 6, 0), key=(3, -4, 6), key_e=3000, spot=85, fill_e=320, rim_e=520, accent_e=420, accent_pos=(-3, 14, 3))
    seg = Helix('Seg', HERO_SEQ[:10], loc=(0, 0, 0), individual=False, hd=True)
    one = join_objects('Turn', seg.all_objects()); bpy.data.objects.remove(seg.root)
    def long_helix(name, loc, rot, count, scale=1.0):
        o = link_dup(one, name, loc=loc, rot=rot, scale=(scale, scale, scale))
        mod = o.modifiers.new('arr', 'ARRAY'); mod.count = count; mod.use_relative_offset = False; mod.use_constant_offset = True; mod.constant_offset_displace = (10 * 0.40, 0, 0)
        return o
    hero = long_helix('Long', (0, -16.0, 0), (0, 0, math.pi / 2), 70)                       # y = -17.8 .. 262: it passes the camera and runs to the horizon
    kf(hero, 'rotation_euler', 1, (-0.4, 0, math.pi / 2)); kf(hero, 'rotation_euler', nf, (-0.4 + 2 * math.pi * 0.05 * dur, 0, math.pi / 2)); kf_lin(hero)
    one.hide_render = True; one.hide_viewport = True
    for k in range(8):                                                                         # side helices: a ring of six near the axis, two far out, all converging on the same vanishing point
        a = 2 * math.pi * k / 6 + rnd.uniform(-0.2, 0.2); rad = rnd.uniform(3.2, 6.0) if k < 6 else rnd.uniform(7.5, 11.0)
        b = long_helix(f'Side{k}', (rad * math.cos(a), rnd.uniform(-8, 2), rad * math.sin(a) * 0.85), (rnd.uniform(0, 3), rnd.uniform(-0.02, 0.02), math.pi / 2 + rnd.uniform(-0.025, 0.025)), 44, scale=rnd.uniform(0.7, 0.95))
        kf(b, 'rotation_euler', 1, tuple(b.rotation_euler)); kf(b, 'rotation_euler', nf, tuple(Vector(b.rotation_euler) + Vector((2 * math.pi * rnd.uniform(0.02, 0.04) * dur, 0, 0)))); kf_lin(b)
    fog_cards(10, 14.0, 130.0, alpha=0.10, size=140)
    for k, (y, e, col) in enumerate(((-2.0, 240, (0.85, 0.92, 1.0)), (4.0, 420, (1.0, 0.94, 0.84)), (12.0, 900, (0.7, 0.85, 1.0)), (24.0, 1800, (1.0, 0.94, 0.84)), (44.0, 3600, (0.7, 0.85, 1.0)))):
        light('POINT', (0.0, y, 0.0), e, col, f'Axis{k}')                                       # lights riding the axis: the receding turns glint instead of sinking to black
    cam, tgt = cam_path([(0.0, (0.55, -4.5, 1.30), (0, 60, 0.1)), (dur * 0.5, (0.75, -9.5, 1.55), (0, 50, 0.0)), (dur, (1.0, -15.5, 1.95), (0, 42, -0.1))], rfps, lens=26)
    lens_zoom(cam, rfps, [(0.0, 26), (dur, 30)])
    env_kit(1, cam, rnd, rfps, dur, center=(0, 24, 0), dust_n=260, dust_spread=(10, 50, 8), halo_r=16.0, halo_at=(0, 120, 0), bokeh=5, halo_strength=0.85)
    dust('Motes', rnd, 240, (0, 4, 0), (4, 16, 4), r=0.022, color=(0.85, 0.92, 1.0), strength=3.5, rfps=rfps, dur=dur, drift_amp=0.6)
    dust('MotesNear', rnd, 90, (0.6, -8, 1.2), (2.5, 8, 2.0), r=0.014, color=(1.0, 0.95, 0.85), strength=3.0, rfps=rfps, dur=dur, drift_amp=0.4)


def own_mat(o):
    """Give an object its own copy of its (shared) material so it can pulse alone."""
    m = o.data.materials[0].copy(); setmat(o, m); return m

def pulse_rim(m, rfps, t, peak=4.0, base=1.2, rise=0.3, fall=1.0):
    """Pulse of a mat_rim2 membrane (its emission is node-driven, so key the multiplier, not the socket)."""
    key_rim(m, F(t - rise, rfps), emit=base); key_rim(m, F(t, rfps), emit=peak); key_rim(m, F(t + fall, rfps), emit=base); ease_id(m.node_tree)

# ================================================================= section-4 assets: bacterium, letter strips, twenty-bead chain
def bacterium(name, loc, s=1.0, rot=(0, 0, 0), seed=3):
    """A rod bacterium: translucent rimmed capsule body (membrane bump) with a nucleoid fibre coiled inside, ribosome specks,
    three long wandering flagella at one pole and a fuzz of pili.  Returns root."""
    rnd = random.Random(seed); root = empty(name, loc); root.rotation_euler = rot
    mb = mat_rim2((0.10, 0.42, 0.34), (0.45, 0.95, 0.75), a_center=0.55, a_rim=0.97, emit=1.4, name=name + '_m', blend=0.35, rough=0.35, bump=0.18, bump_scale=30.0, cull=True)
    body = blob(name + 'Body', [(-1.2 * s, 0, 0, 0.85 * s), (-0.4 * s, 0, 0, 0.9 * s), (0.4 * s, 0, 0, 0.9 * s), (1.2 * s, 0, 0, 0.85 * s)], mb, res=0.09 * s, disp=0.03 * s, disp_scale=0.8 * s, subd=1); parent(body, root)
    try: body.visible_shadow = False
    except Exception: pass
    fm = M('chromfib', lambda: mat_gloss(CHROM, rough=0.3, coat=0.5, name='chromfib'))
    pts = wander_pts(rnd, (-0.8 * s, 0, 0), 40, 0.32 * s, ((-1.3 * s, 1.3 * s), (-0.45 * s, 0.45 * s), (-0.45 * s, 0.45 * s)), smoothness=0.5)
    nuc = curve_obj(name + 'Nucleoid', pts, 0.035 * s, fm, res=4, kind='NURBS'); parent(nuc, root)
    rp = [Vector((rnd.uniform(-1.4, 1.4) * s, rnd.uniform(-0.6, 0.6) * s, rnd.uniform(-0.6, 0.6) * s)) for _ in range(70)]
    rib = spheres_mesh(name + 'Ribo', rp, 0.05 * s, M('ribo_dots', lambda: mat_gloss((0.55, 0.42, 0.85), rough=0.4, name='ribo_dots')), subdiv=1); parent(rib, root)
    flm = M('flag', lambda: mat_gloss((0.55, 0.9, 0.8), rough=0.4, coat=0.3, name='flag'))
    for k in range(3):
        a = 2 * math.pi * k / 3; p0 = Vector((-1.9 * s, 0.25 * s * math.cos(a), 0.25 * s * math.sin(a)))
        fp = [p0 + Vector((-u * 0.5 * s, 0.35 * s * math.sin(u * 1.7 + a) * (0.3 + 0.15 * u), 0.35 * s * math.cos(u * 1.5 + a) * (0.3 + 0.15 * u))) for u in range(9)]
        fl = curve_obj(f'{name}Flag{k}', fp, 0.028 * s, flm, res=6, kind='NURBS'); parent(fl, root)
    bm = bmesh.new()
    for k in range(60):
        v = Vector((rnd.uniform(-1.4, 1.4) * s, rnd.gauss(0, 1), rnd.gauss(0, 1))); d = Vector((0, v.y, v.z)).normalized(); p = Vector((v.x, d.y * 0.92 * s, d.z * 0.92 * s))
        capsule_into(bm, p, p + d * rnd.uniform(0.12, 0.28) * s, 0.012 * s, 6, 3)
    pil = mesh_obj(name + 'Pili', bm, flm); parent(pil, root)
    return root

def letter_strip(name, seq, loc=(0, 0, 0), rot=(0, 0, 0), rise=0.62, anchors=True, individual=True, side=(0, 0, 1), tag=None):
    """A short mRNA strip (ring-plate bases) standing up from an amber rail: GGU / CCU / GAG etc.  Anchors Rp<tag><k> on the bases."""
    r = RNA(name, seq, loc=loc, rot=rot, rise=rise, side=side, hd=True, individual=individual)
    if anchors:
        for k in range(len(seq)): r.add_anchor(k, tag=f'{tag or name}{k}')
    return r

def twenty_chain(name='Twenty', r=0.24):
    aminos = ['Gly', 'Ala', 'Val', 'Leu', 'Ile', 'Pro', 'Phe', 'Tyr', 'Trp', 'Ser', 'Thr', 'Cys', 'Met', 'Asn', 'Gln', 'Asp', 'Glu', 'Lys', 'Arg', 'His']
    return Chain(name, aminos, r=r, r_link=0.07, hd=True), aminos

def bead_on_beam(name, aa, p_from, p_to, rfps, t_on, dur_=0.9, r=0.30, color=None):
    """An amino-acid bead that rises out of a lit codon on a beam of light: the codon -> amino-acid proof."""
    bd = amino_acid(name, aa, tuple(p_from), r=r); scale_in(bd, rfps, t_on, dur=0.5)
    move(bd, rfps, [(t_on, tuple(p_from)), (t_on + dur_, tuple(p_to))]); spin(bd, rfps, 60, rate=0.10, axis=2)
    bm = beam(name + 'Beam', tuple(p_from), tuple(p_to), r=0.06, color=color or AMINO.get(aa, GENE), strength=1.6, f_on=F(t_on, rfps), alpha=0.35)
    return bd, bm

# ================================================================= builders: 4. The Genetic Code
def two_languages(nf, rfps, dur):
    """s25 250.04-262.42: two languages face each other.  Above, an mRNA strip whose first four bases A U G C pulse and are
    lettered as 'four letters' is spoken (RpLA..RpLC); on 'protein language' a folded protein globule spins in at the right
    (RpProt); below, a chain of ALL twenty amino acids (distinct side chains, one colour each) links up bead by bead for
    'twenty kinds of amino acids joined in a chain' (RpChain, Rp20).  The camera pans from the strand down to the chain."""
    reset(); rnd = random.Random(25); T = lambda t: rt('s25', t)
    theme_lights(4, target=(0, 0, 0), key=(3.0, -7.5, 7.5), key_e=3000, spot=65, fill_e=220, rim_e=560, accent_e=300, accent_pos=(-5, 4, -3))
    rna = RNA('mRNA', MRNA_SEQ[:16], loc=(0.0, 0.0, 1.4), side=(0, 0, 1), rise=0.52, hd=True, individual=True)
    for k, b in enumerate('AUGC'):
        rna.add_anchor(k, tag=f'L{b}'); mk = mat_gloss(BASE[b], rough=0.25, coat=0.6, name=f'L{b}_m', sss=0.1); setmat(rna.bases[k], mk)
        pulse(mk, rfps, T(251.3 + 0.35 * k), BASE[b], peak=2.6, fall=1.4); pulse(mk, rfps, T(254.6 + 0.2 * k), BASE[b], peak=1.6, fall=1.0)
    drift(rna.root, rfps, dur, amp=0.05, seed=2, period=4.0)
    ch = Chain('Prot', ['Met', 'Gly', 'Pro', 'Ala', 'Leu', 'Ser', 'Lys', 'Val', 'Glu', 'Phe', 'Thr', 'Asp', 'Trp', 'His'], r=0.17, r_link=0.05, hd=False)
    fp = fold_path(14, seed=6, box=0.75, step=0.42); ch.pose([tuple(p) for p in fp], 1)
    prot = empty('ProtRoot', (5.4, 0.5, 1.6))
    for o in ch.objects(): parent(o, prot)
    scale_in(prot, rfps, T(253.6), dur=0.8); spin(prot, rfps, dur, rate=0.12, axis=2); anchor('Prot', (0, -0.5, 1.2), prot)
    hl = halo('ProtHalo', (5.4, 2.0, 1.6), 1.8, THEMES[4]['accent'], strength=0.5); scale_in(hl, rfps, T(253.6), dur=0.8)
    tw, aminos = twenty_chain('Twenty', r=0.24)
    pts = [Vector((-6.2 + 0.66 * k, 0.25 * math.sin(k * 0.9), -1.0 + 0.22 * math.sin(k * 0.55))) for k in range(20)]
    tw.pose([tuple(p) for p in pts], 1)
    for k in range(20):
        f = F(T(256.9 + 0.17 * k), rfps); tw.hide_until(k, f)
        b = tw.beads[k]; kf(b, 'location', f, tuple(pts[k] + Vector((0, 0, -0.9)))); kf(b, 'location', f + int(0.5 * rfps), tuple(pts[k])); kf_ease(b)
        if k: kf(tw.links[k - 1], 'scale', f, (1, 1, 0.001)); kf(tw.links[k - 1], 'scale', f + int(0.5 * rfps), (1, 1, (pts[k] - pts[k - 1]).length)); kf_ease(tw.links[k - 1])
    anchor('Chain', tuple(pts[9] + Vector((0, -0.4, 0.55)))); anchor('20', tuple(pts[19] + Vector((0.3, -0.3, 0.5))))
    bg = Helix('BgDNA', HERO_SEQ[:44], loc=(0, 8.5, 0.3), rot=(0, 0, 0.25), individual=False, hd=False); spin(bg.root, rfps, dur, rate=0.03)
    cam, tgt = cam_path([(0.0, (-3.0, -9.5, 2.2), (-1.0, 0, 1.4)), (T(253.6), (1.5, -9.0, 2.0), (1.6, 0, 1.2)), (T(256.6), (-2.5, -9.6, 1.2), (-2.0, 0, 0.5)), (T(259.5), (0.2, -9.8, 0.6), (0.3, 0, 0.0)), (dur, (2.0, -10.5, 0.3), (0.6, 0, -0.3))], rfps, lens=45)
    env_kit(4, cam, rnd, rfps, dur, center=(0, 0, 0.3), dust_n=140, halo_r=7.5, halo_at=(0, 5.5, 0.4), bokeh=4)

def codons_lit(nf, rfps, dur):
    """s26 262.42-273.0: the message strand slides slowly past while a three-base window of light steps along it (read in
    groups of three); on 'codon' the window holds on one triplet (RpCodon); on 'codes for one amino acid' a glycine bead
    rises out of that codon on a beam (RpAA).  The camera tracks the window."""
    reset(); rnd = random.Random(26); T = lambda t: rt('s26', t)
    theme_lights(4, target=(0, 0, 0.5), key=(3.0, -7.5, 7.5), key_e=3000, spot=65, fill_e=220, rim_e=560, accent_e=300, accent_pos=(5, 4, -3))
    rna = RNA('mRNA', MRNA_SEQ, loc=(0, 0, 0.2), side=(0, 0, 1), rise=0.56, hd=True, individual=True)
    move(rna.root, rfps, [(0.0, (1.5, 0, 0.2)), (dur, (-1.5, 0, 0.2))], ease=False)
    for j in range(6):
        t0 = T(262.9) + 0.62 * j
        rna.sleeve(3 * j, THEMES[4]['accent'], F(t0, rfps), F(t0 + 0.62, rfps), n=3, r=0.34, strength=1.8, tag=f'Win{j}')
    hold = rna.sleeve(6, GENE, F(T(266.6), rfps), None, n=3, r=0.36, strength=2.2, tag='Hold'); rna.add_anchor(7, tag='Codon')
    for k in (6, 7, 8): pulse(own_mat(rna.bases[k]), rfps, T(266.9), BASE[rna.seq[k]], peak=1.8, fall=1.2)
    c = rna.axis_pt(7); bd, bm = bead_on_beam('Gly', 'Gly', c + Vector((0, 0, 1.0)), c + Vector((0, 0, 2.4)), rfps, T(269.6), r=0.32)
    parent(bd, rna.root); parent(bm, rna.root); anchor('AA', (0, -0.2, 0.5), bd)
    bg = Helix('BgDNA', HERO_SEQ[:44], loc=(0, 8.5, -0.5), rot=(0, 0, -0.2), individual=False, hd=False); spin(bg.root, rfps, dur, rate=0.03)
    for k in range(3):
        r2 = RNA(f'Far{k}', MRNA_SEQ[:14], loc=(rnd.uniform(-5, 5), 6 + 2 * k, rnd.uniform(-3, 3)), rot=(0, 0, rnd.uniform(-0.4, 0.4)), side=(0, 0, 1), rise=0.5, hd=False); drift(r2.root, rfps, dur, amp=0.2, seed=k, period=6)
    wx = lambda t: 1.5 - 3.0 * t / dur
    keys = [(0.0, (wx(0) - 4.0 + 0.4 - 0.6, -8.8, 2.0), (wx(0) - 3.4, 0, 0.6)), (T(266.6), (wx(T(266.6)) + c.x - 0.4, -7.6, 1.9), (wx(T(266.6)) + c.x, 0, 0.7)),
            (T(269.6), (wx(T(269.6)) + c.x + 0.4, -7.2, 2.2), (wx(T(269.6)) + c.x, 0, 1.2)), (dur, (wx(dur) + c.x + 0.9, -7.8, 2.6), (wx(dur) + c.x, 0, 1.4))]
    cam, tgt = cam_path(keys, rfps, lens=45)
    env_kit(4, cam, rnd, rfps, dur, center=(0, 0, 0.5), dust_n=140, halo_r=7.0, halo_at=(0, 5.5, 0.6), bokeh=4)

def ggu_ccu(nf, rfps, dur):
    """s27 273.0-279.96: two triplets face us, GGU on the left and CCU on the right; as each is named, its bases pulse and its
    amino acid (glycine, then proline, each with its own side chain and colour) rises out of it on a beam (RpGGU/RpGly,
    RpCCU/RpPro).  Dolly from left to right with a rack focus between the two."""
    reset(); rnd = random.Random(27); T = lambda t: rt('s27', t)
    theme_lights(4, target=(0, 0, 0.6), key=(2.5, -7.5, 7.5), key_e=3000, spot=65, fill_e=220, rim_e=560, accent_e=300, accent_pos=(-5, 4, -3))
    heroes = {}
    for cd, aa, x, t_say in (('GGU', 'Gly', -2.6, 273.6), ('CCU', 'Pro', 2.6, 276.7)):
        st = letter_strip(cd, cd, loc=(x, 0, 0), rise=0.66, anchors=False)
        anchor(cd, (0.0, 0, -0.55), st.root); drift(st.root, rfps, dur, amp=0.05, seed=len(cd) + int(x), period=4.0)
        kf(st.root, 'rotation_euler', 1, (0, 0, -0.18)); kf(st.root, 'rotation_euler', nf, (0, 0, 0.18)); kf_lin(st.root)
        for k in range(3): pulse(own_mat(st.bases[k]), rfps, T(t_say + 0.25 * k), BASE[cd[k]], peak=2.4, fall=1.2)
        sl = st.sleeve(0, AMINO[aa], F(T(t_say + 0.5), rfps), None, n=3, r=0.36, strength=1.4, tag=cd + 'Sleeve')
        bd, bm = bead_on_beam(aa, aa, Vector((x, 0, 1.0)), Vector((x, 0, 2.5)), rfps, T(t_say + 1.2), r=0.34)
        anchor(aa, (0, -0.2, 0.55), bd); heroes[cd] = (st, bd)
    bg = Helix('BgDNA', HERO_SEQ[:44], loc=(0, 8.5, -0.5), rot=(0, 0, 0.3), individual=False, hd=False); spin(bg.root, rfps, dur, rate=0.03)
    r2 = RNA('FarRNA', MRNA_SEQ, loc=(1.0, 6.0, 3.2), rot=(0, 0, -0.3), side=(0, 0, 1), rise=0.5, hd=False); drift(r2.root, rfps, dur, amp=0.2, seed=3, period=6)
    cam, tgt = cam_path([(0.0, (-3.4, -8.0, 1.8), (-2.4, 0, 0.8)), (T(276.0), (-1.8, -7.6, 1.7), (-2.0, 0, 1.0)), (T(277.2), (2.0, -7.6, 1.7), (2.4, 0, 1.0)), (dur, (0.6, -8.8, 1.9), (0.2, 0, 1.0))], rfps, lens=45)
    if os.environ.get('VL_DOF', '0') == '1': rack_focus(cam, F(T(276.0), rfps), F(T(277.2), rfps), heroes['GGU'][0].root, heroes['CCU'][0].root)
    env_kit(4, cam, rnd, rfps, dur, center=(0, 0, 0.6), dust_n=130, halo_r=7.5, halo_at=(0, 5.5, 0.8), bokeh=4)

def codon_wall(nf, rfps, dur):
    """s28 279.96-289.85: the 64-tile codon wall (bevelled tiles coloured by amino acid, red stops, 3D letters) rises into
    place in waves for 'sixty-four combinations' while the camera orbits it; on 'more than one codon' glycine's four tiles
    GGU GGC GGA GGG pulse together and beams gather from them to one glycine bead floating in front of the wall."""
    reset(); rnd = random.Random(28); T = lambda t: rt('s28', t)
    theme_lights(4, target=(0, 0, 0), key=(4.0, -9.0, 8.0), key_e=4200, spot=70, fill_e=300, rim_e=600, accent_e=360, accent_pos=(-6, 4, -3))
    root, tiles = wall_asset('Wall', (0, 0, 0), tile=0.92, gap=0.12, rfps=rfps, t_rise=T(280.2), rise_dur=2.2, seed=4)
    kf(root, 'rotation_euler', 1, (0, 0, -0.06)); kf(root, 'rotation_euler', nf, (0, 0, 0.06)); kf_lin(root)
    gly = ['GGU', 'GGC', 'GGA', 'GGG']; bead_p = Vector((2.2, -3.2, -0.6))
    for cd in gly:
        t_, tx = tiles[cd]; m = t_.data.materials[0]
        for tp in (285.3, 286.7, 288.1): pulse(m, rfps, T(tp), AMINO['Gly'], peak=2.2, fall=1.0)
        p = Vector(t_.location) + Vector((0, -0.2, 0))
        beam(f'Beam{cd}', tuple(p), tuple(bead_p), r=0.03, color=AMINO['Gly'], strength=1.8, f_on=F(T(285.6), rfps), alpha=0.35)
    bd = amino_acid('GlyHero', 'Gly', tuple(bead_p), r=0.36); scale_in(bd, rfps, T(285.4), dur=0.5); spin(bd, rfps, dur, rate=0.12, axis=2)
    hl = halo('GlyHalo', tuple(bead_p + Vector((0, 1.0, 0))), 1.4, AMINO['Gly'], strength=0.6); scale_in(hl, rfps, T(285.4), dur=0.5)
    for cd in ('UAA', 'UAG', 'UGA', 'AUG'):
        t_, tx = tiles[cd]; pulse(t_.data.materials[0], rfps, T(283.0), STOP if cd != 'AUG' else START, peak=1.2, fall=1.4)
    cam, tgt = camera((-5.0, -13.0, 1.5), (0, 0, 0), lens=42); orbit(cam, tgt, (0, 0, 0), 13.5, 1.6, -28, 22, 1, nf)
    lens_zoom(cam, rfps, [(0.0, 42), (dur, 48)])
    env_kit(4, cam, rnd, rfps, dur, center=(0, 0, 0), dust_n=150, dust_spread=(14, 10, 9), halo_r=9.0, halo_at=(0, 5, 0), bokeh=4, helices=2)

def start_codon(nf, rfps, dur):
    """s29 289.85-297.0: the message strand slides in from the right; its first triplet AUG lights green as it is named
    (RpAUG), methionine docks above it (RpMet), and on 'start codon' a vertical start-line beam marks the beginning."""
    reset(); rnd = random.Random(29); T = lambda t: rt('s29', t)
    theme_lights(4, target=(0, 0, 0.5), key=(3.0, -7.5, 7.5), key_e=3000, spot=65, fill_e=220, rim_e=560, accent_e=300, accent_pos=(5, 4, -3))
    rna = RNA('mRNA', MRNA_SEQ, loc=(0, 0, 0.2), side=(0, 0, 1), rise=0.56, hd=True, individual=True)
    move(rna.root, rfps, [(0.0, (7.0, 0, 0.2)), (T(292.3), (2.6, 0, 0.2)), (dur, (2.0, 0, 0.2))])
    for k in range(3): pulse(own_mat(rna.bases[k]), rfps, T(291.3 + 0.25 * k), BASE[rna.seq[k]], peak=2.4, fall=1.2)
    rna.sleeve(0, START, F(T(291.6), rfps), None, n=3, r=0.36, strength=2.0, tag='AUGSleeve'); rna.add_anchor(1, tag='AUG')
    c = rna.axis_pt(1); bd, bm = bead_on_beam('Met', 'Met', c + Vector((0, 0, 1.0)), c + Vector((0, 0, 2.3)), rfps, T(293.3), r=0.32, color=START)
    parent(bd, rna.root); parent(bm, rna.root); anchor('Met', (0, -0.2, 0.55), bd)
    flag = beam('StartLine', c + Vector((-0.95, 0, -1.2)), c + Vector((-0.95, 0, 3.2)), r=0.05, color=START, strength=2.2, f_on=F(T(295.0), rfps), alpha=0.5); parent(flag, rna.root)
    bg = Helix('BgDNA', HERO_SEQ[:44], loc=(0, 8.5, -0.5), rot=(0, 0, 0.2), individual=False, hd=False); spin(bg.root, rfps, dur, rate=0.03)
    for k in range(2):
        r2 = RNA(f'Far{k}', MRNA_SEQ[:14], loc=(rnd.uniform(-5, 5), 6 + 2 * k, rnd.uniform(-2, 3)), rot=(0, 0, rnd.uniform(-0.4, 0.4)), side=(0, 0, 1), rise=0.5, hd=False); drift(r2.root, rfps, dur, amp=0.2, seed=k, period=6)
    cam, tgt = cam_path([(0.0, (-1.5, -10.5, 2.4), (1.0, 0, 0.6)), (T(292.3), (-2.4, -8.0, 1.9), (-1.6, 0, 0.9)), (T(295.0), (-2.9, -6.6, 1.7), (-2.2, 0, 1.1)), (dur, (-1.6, -7.4, 2.0), (-2.0, 0, 1.0))], rfps, lens=45)
    env_kit(4, cam, rnd, rfps, dur, center=(0, 0, 0.5), dust_n=140, halo_r=7.0, halo_at=(0, 5.5, 0.6), bokeh=4)

def stop_codons(nf, rfps, dur):
    """s30 297.0-306.54: three message strands stacked like three lines of text, each ending in a different stop triplet;
    UAA, UAG and UGA light red one after another as they are named (RpUAA/RpUAG/RpUGA) with a red stop beacon; on 'stop
    codons' all three pulse together.  The camera cranes down the three lines, then pulls back."""
    reset(); rnd = random.Random(30); T = lambda t: rt('s30', t)
    theme_lights(4, target=(0, 0, 0), key=(3.0, -8.0, 8.0), key_e=3200, spot=70, fill_e=240, rim_e=560, accent_e=300, accent_pos=(-5, 4, -3))
    for k, (seq, z, t_on) in enumerate((('GCUACCUAA', 1.9, 298.9), ('CCGGUAUAG', 0.0, 300.5), ('AAUGCCUGA', -1.9, 302.1))):
        r = RNA(f'Line{k}', seq, loc=(0.4 * (k - 1), 0, z), side=(0, 0, 1), rise=0.56, hd=True, individual=True)
        move(r.root, rfps, [(0.0, (0.4 * (k - 1) + 0.6, 0, z)), (dur, (0.4 * (k - 1) - 0.6, 0, z))], ease=False)
        cd = seq[6:]; r.add_anchor(7, tag=cd)
        for j in range(3): pulse(own_mat(r.bases[6 + j]), rfps, T(t_on + 0.22 * j), BASE[seq[6 + j]], peak=2.4, fall=1.2)
        sl = r.sleeve(6, STOP, F(T(t_on + 0.3), rfps), None, n=3, r=0.36, strength=2.2, tag=f'Stop{k}')
        for tp in (304.7, 305.5): pulse(sl.data.materials[0], rfps, T(tp), STOP, peak=5.0, base=2.2, fall=0.6)
        c = r.axis_pt(7) + Vector((0, 0, 1.15)); bcn = sphere(f'Beacon{k}', 0.14, tuple(c), seg=24, ring=12, mat=mat_glow(STOP, strength=4.0, name=f'bcn{k}')); parent(bcn, r.root)
        hl = halo(f'BeaconHalo{k}', tuple(c + Vector((0, 0.5, 0))), 0.9, STOP, strength=1.0); parent(hl, r.root); scale_in(bcn, rfps, T(t_on + 0.4), dur=0.4); scale_in(hl, rfps, T(t_on + 0.4), dur=0.4)
        L = light('POINT', tuple(c + Vector((0, -0.6, 0.3))), 0, STOP, f'StopLight{k}'); parent(L, r.root); key_light(L, F(T(t_on + 0.3), rfps), 0.0); key_light(L, F(T(t_on + 0.8), rfps), 60.0)
    bg = Helix('BgDNA', HERO_SEQ[:44], loc=(0, 8.5, 0), rot=(0, 0, -0.25), individual=False, hd=False); spin(bg.root, rfps, dur, rate=0.03)
    cam, tgt = cam_path([(0.0, (-2.0, -10.0, 3.6), (0.8, 0, 1.9)), (T(298.9), (0.0, -9.0, 3.0), (1.8, 0, 1.9)), (T(300.5), (0.4, -8.8, 1.0), (1.6, 0, 0.0)), (T(302.1), (0.8, -9.0, -1.0), (1.4, 0, -1.9)),
                         (T(304.5), (-1.5, -10.5, 0.6), (0, 0, 0)), (dur, (-2.5, -11.0, 1.0), (0, 0, 0))], rfps, lens=45)
    env_kit(4, cam, rnd, rfps, dur, center=(0, 0, 0), dust_n=140, halo_r=8.0, halo_at=(0, 5.5, 0), bokeh=4)

def universal_code(nf, rfps, dur):
    """s31 306.54-313.02: a rod bacterium (flagella, nucleoid, pili) on the left and a human cell (membrane, organelles,
    amethyst nucleus) on the right share one glowing codon in the middle: GGU -> glycine; beams link the codon to both as
    'bacteria' and 'humans' are spoken (RpBact, RpHuman, RpCode).  A wide, slow orbit."""
    reset(); rnd = random.Random(31); T = lambda t: rt('s31', t)
    theme_lights(4, target=(0, 0, 0), key=(4.0, -10.0, 9.0), key_e=4600, spot=75, fill_e=320, rim_e=640, accent_e=360, accent_pos=(-7, 5, -3))
    bac = bacterium('Bact', (-4.0, 0.4, 0.2), s=1.05, rot=(0.2, 0.15, 0.55)); anchor('Bact', (0, -0.9, 1.4), bac)
    rot_keys(bac, rfps, [(0, (0.2, 0.15, 0.55)), (dur, (0.1, 0.05, 0.9))]); drift(bac, rfps, dur, amp=0.1, seed=2, period=5)
    cell = cell_body('Human', (4.1, 0.5, 0.0), 2.1); nucleus_hd('Nuc', (4.3, 0.8, 0.1), r=0.85, pores=16, seed=3)
    for o in organelles('Cyto', rnd, 16, (4.1, 0.5, 0), 1.75, avoid_r=1.1, s=0.36): drift(o, rfps, dur, amp=0.06, seed=rnd.randint(1, 99), period=5.0)
    anchor('Human', (4.1, -1.3, 1.9))
    st = letter_strip('GGU', 'GGU', loc=(0, 0, -0.7), rise=0.62, anchors=False); anchor('Code', (0, -0.4, -0.5), st.root)
    kf(st.root, 'rotation_euler', 1, (0, 0, -0.5)); kf(st.root, 'rotation_euler', nf, (0, 0, 0.5)); kf_lin(st.root)
    bd, bm = bead_on_beam('Gly', 'Gly', Vector((0, 0, 0.4)), Vector((0, 0, 1.5)), rfps, T(306.9), r=0.32)
    for nm, p, t_on in (('ToBact', (-2.5, 0.2, 0.3), 308.6), ('ToHuman', (2.1, 0.4, 0.2), 310.4)):
        beam(nm, (0, 0, 0.3), p, r=0.035, color=AMINO['Gly'], strength=1.8, f_on=F(T(t_on), rfps), alpha=0.35)
    pulse_rim(cell.data.materials[0], rfps, T(310.6), peak=4.0, base=1.4, fall=1.2)
    for k in range(3):                                                                         # secondary structures behind: two far bacteria and a drifting distant cell
        b2 = bacterium(f'Far{k}', (rnd.uniform(-9, -1), 8 + 3 * k, rnd.uniform(-4, 4)), s=0.7, rot=(rnd.uniform(0, 1), rnd.uniform(0, 1), rnd.uniform(0, 3))); drift(b2, rfps, dur, amp=0.2, seed=k, period=6)
    far = cell_body('FarCell', (8.5, 12.0, -1.5), 2.4); drift(far, rfps, dur, amp=0.2, seed=9, period=7)
    cam, tgt = camera((-2.0, -12.5, 2.0), (0, 0, 0.2), lens=40); orbit(cam, tgt, (0, 0, 0.2), 12.5, 2.2, -14, 12, 1, nf)     # a closer orbit: both cells fill the middle third
    lens_zoom(cam, rfps, [(0.0, 40), (dur, 43)])
    env_kit(4, cam, rnd, rfps, dur, center=(0, 0, 0), dust_n=170, dust_spread=(16, 12, 9), halo_r=7.0, halo_at=(0, 7, 0), bokeh=4, fil=4, helices=2, halo_alpha=0.7)

# ================================================================= the translation rig (one continuous set for s33-s40)
TL_CODONS = [MRNA_SEQ[3 * j:3 * j + 3] for j in range(7)]          # AUG CCU GGA CCU GCU UGG UAA
TL_AA = [CODON[c] for c in TL_CODONS]                              # Met Pro Gly Pro Ala Trp Stop
TL_RISE = 0.40; TL_CW = 3 * TL_RISE                                # codon width 1.2
RS = TL_CW / 0.85                                                  # ribosome scale so the E / P / A pads sit one codon apart
ST = 0.8                                                           # tRNA scale in the rig
Z_RNA = -0.55                                                      # the message lies in the cleft of the small subunit
Z_DOCK = Z_RNA + 1.57                                              # tRNA foot height: anticodon tips 0.2 above the codon tips
ARM = Vector((2.78, 0, 2.2)) * ST                                  # amino-acid point in the tRNA arm frame
def anticodon_of(codon): return ''.join(RNA_COMP[b] for b in codon)   # written 3'->5' so it reads letter-under-letter
def hide_until_safe(o, f):
    """hide_until() with a show frame <= 1 would key 'hidden' at frame 1 AFTER 'shown' and hide the object for good."""
    if f > 1: hide_until(o, f)
def show_between_safe(o, f0, f1):
    if f0 > 1: show_between(o, f0, f1)
    else: hide_from(o, max(2, f1))

class TRig:
    """mRNA (individual HD nucleotides) along X with codon j centred at cx(j); a two-subunit ribosome whose P site sits on
    codon p_codon and which steps one codon at a time (ribo_keys); tRNAs that fly in from the upper right front, dock on
    their codon (anticodon plates meeting the codon plates, dashes between), stay while the ribosome walks over them, then
    leave to the upper left; an amino-acid Chain whose beads ride each tRNA's arm until the peptide bond hands them to the
    next tRNA and the chain rises out of the exit tunnel.  Everything is keyed per frame from analytic paths."""
    def __init__(self, sid, rfps, dur, x_rna=-3.4, p_codon=0, gap=1.0, ribo=True, sites=True):
        self.sid, self.rfps, self.dur = sid, rfps, dur; self.T = lambda t: rt(sid, t)
        self.rna = RNA('mRNA', MRNA_SEQ, loc=(0, 0, Z_RNA), side=(0, 0, 1), rise=TL_RISE, start=x_rna, hd=True, individual=True); self.x_rna = x_rna
        self.ribo = None
        if ribo:
            self.ribo, self.L, self.S, self.sites = ribosome('Ribo', (self.cx(p_codon), 0, 0), s=RS, gap=gap, sites=sites)
            self.L.location.z -= 1.0; self.S.location.z += 0.4          # metaball skins sit inside their element radii: close the cleft on the message
        self.ribo_keys = [(-1.0, p_codon)]; self.trnas = []; self.by_codon = {}; self.chain = None; self.bonds = []; self.frames = []
    def cx(self, j): return self.x_rna + TL_RISE * (3 * j + 1)
    def step(self, t_abs, j): self.ribo_keys.append((self.T(t_abs), j))
    def ribo_x(self, t):
        x = self.cx(self.ribo_keys[0][1])
        for (ta, ka), (tb, kb) in zip(self.ribo_keys[:-1], self.ribo_keys[1:]):
            if t >= tb - 0.9: x = lerp(self.cx(ka), self.cx(kb), smooth01((t - (tb - 0.9)) / 0.9))
        return x
    def sleeve(self, j, color, t_on, t_off=None, strength=2.0, tag=None):
        return self.rna.sleeve(3 * j, color, F(self.T(t_on), self.rfps), None if t_off is None else F(self.T(t_off), self.rfps), n=3, r=0.34, strength=strength, tag=tag or f'Sleeve{j}')
    def add_trna(self, j, t_arrive, t_dock, t_leave=None, yaw=-1.6, bounce=False, leave_dir=(-2.8, -1.6, 3.6)):
        """tRNA for codon j: flies in between t_arrive and t_dock, leaves from t_leave (1.5 s).  bounce=True: a wrong tRNA
        that approaches, cannot pair, and turns back (the stop-codon beat)."""
        cd = TL_CODONS[j]; ac = anticodon_of(cd); aa = TL_AA[j]
        root, aao, bases = trna(f'tRNA{j}', ac, aa if aa != 'Stop' else 'Ala', loc=(self.cx(j), 0, Z_DOCK), s=ST, with_aa=False, hd=True, yaw=yaw, ac_scale=0.75, ac_pitch=TL_RISE)
        dock = Vector((self.cx(j), 0, Z_DOCK)); far = dock + Vector((3.0, -2.2, 4.4)); away = dock + Vector(leave_dir)
        d = dict(j=j, root=root, bases=bases, dock=dock, far=far, away=away, ta=self.T(t_arrive), td=self.T(t_dock), tl=None if t_leave is None else self.T(t_leave), yaw=yaw, bounce=bounce)
        for o in [root] + list(root.children_recursive):
            if o.type != 'EMPTY': hide_until_safe(o, F(d['ta'], self.rfps))
        if bounce:
            d['dock'] = dock + Vector((0, 0, 1.1)); d['tl'] = d['td'] + 0.3
        # pairing dashes: codon tips to anticodon tips, appear at dock time
        if not bounce:
            bm = bmesh.new()
            for k in range(3):
                b = cd[k]; x = self.cx(j) + (k - 1) * TL_RISE; ztop = Z_RNA + R_SUGAR_RING - 0.02 + plate_len(b); zbot = Z_DOCK + 0.05 * ST - plate_len(RNA_COMP[b]) * 0.75
                for o in ([-0.05, 0.05] if b in 'AU' else [-0.075, 0.0, 0.075]): capsule_into(bm, (x + o, 0, ztop + 0.01), (x + o, 0, zbot - 0.01), 0.026, 8, 4)
            hb = mesh_obj(f'Pair{j}', bm, m_hbond()); d['hb'] = hb
            try: hb.visible_shadow = False
            except Exception: pass
            if d['tl'] is not None: show_between_safe(hb, F(d['td'], self.rfps), F(d['tl'], self.rfps))
            else: hide_until_safe(hb, F(d['td'], self.rfps))
        self.trnas.append(d)
        if not bounce: self.by_codon[j] = d
        return d
    def trna_loc(self, d, t):
        if t < d['ta']: return d['far']
        if t < d['td']:
            u = smooth01((t - d['ta']) / max(1e-3, d['td'] - d['ta'])); p = vlerp(d['far'], d['dock'], u); return p + Vector((0, 0, 1.6 * math.sin(math.pi * u) * (1 - u)))
        if d['tl'] is None or t < d['tl']: return d['dock']
        u = smooth01((t - d['tl']) / 1.5); return vlerp(d['dock'], d['far'] if d['bounce'] else d['away'], u)
    def aa_point(self, d, t): return self.trna_loc(d, t) + Matrix.Rotation(d['yaw'], 3, 'Z') @ ARM
    def build_chain(self, n, t_bonds):
        """Chain of the first n amino acids; t_bonds[k] (absolute) = when bead k joins the chain (k = 0: Met's dock time)."""
        self.chain = Chain('Chain', TL_AA[:n], r=0.26, r_link=0.08, hd=True); self.t_bonds = [self.T(t) for t in t_bonds]
        for k in range(n):
            d = self.by_codon.get(k); b = self.chain.beads[k]          # beads whose tRNA is already gone (earlier codons) are simply there
            for o in [b] + list(b.children): hide_until_safe(o, F(d['ta'], self.rfps) if d else 1)
            if k: hide_until_safe(self.chain.links[k - 1], F(self.t_bonds[k], self.rfps))
        return self.chain
    def chain_offset(self, n): return Vector((0.12 * math.sin(1.9 * n), -0.18 * n, 0.50 * n))
    def bead_pos(self, i, t):
        tb = self.t_bonds; latest = max([k for k in range(len(tb)) if tb[k] <= t] or [-1])
        if i > latest: return self.aa_point(self.by_codon[i], t)
        k = latest; u = smooth01((t - tb[k]) / 0.7)
        p_new = self.aa_point(self.by_codon[k], t) + self.chain_offset(k - i)
        p_old = (self.aa_point(self.by_codon[k - 1], t) + self.chain_offset(k - 1 - i)) if k - 1 >= i else self.aa_point(self.by_codon[i], t)
        return vlerp(p_old, p_new, u)
    def bond_glow(self, k, t_on, dur_=1.6):
        g = unit_link(f'Bond{k}', 0.15, mat_translucent((1.0, 0.85, 0.45), alpha=0.5, emit=4.0, name=f'bond{k}_m')); show_between(g, F(self.T(t_on), self.rfps), F(self.T(t_on) + dur_, self.rfps))
        try: g.visible_shadow = False
        except Exception: pass
        self.bonds.append((k, g)); return g
    def animate(self, step=2):
        """Key everything (ribosome walk, tRNA flights, chain beads, bond glows) over the whole shot."""
        nf = int(round(self.dur * self.rfps)); frames = list(range(1, nf + 1, step))
        if frames[-1] != nf: frames.append(nf)
        self.frames = frames
        for f in frames:
            t = (f - 1) / self.rfps
            if self.ribo is not None: kf(self.ribo, 'location', f, (self.ribo_x(t), 0, 0))
            for d in self.trnas: kf(d['root'], 'location', f, tuple(self.trna_loc(d, t)))
            if self.chain is not None:
                pts = [self.bead_pos(i, t) for i in range(len(self.chain.beads))]; self.chain.pose(pts, f, ups=[Vector((0, -1, 0.3))] * len(pts))
                for k, g in self.bonds: fit_link(g, pts[k - 1], pts[k], f)
        if self.ribo is not None: kf_ease(self.ribo)
        for d in self.trnas: kf_lin(d['root'])
        if self.chain is not None:
            for b in self.chain.beads: lin_id(b)
            for l in self.chain.links: lin_id(l)
        for k, g in self.bonds: lin_id(g)

def cyto_dressing(rnd, rfps, dur, center=(0, 6, 0), n=24, avoid=3.0, fil=4):
    for o in organelles('Cyto', rnd, n, center, 8.0, avoid_r=avoid, s=0.9): drift(o, rfps, dur, amp=0.1, seed=rnd.randint(1, 99), period=6.0)
    filaments('Fil', rnd, fil, center, (7, 5, 4), r=0.03, length=7.0)

# ================================================================= builders: 5. Translation
def ribosome_binds(nf, rfps, dur):
    """s33 315.62-322.59: in the teal cytoplasm (organelles, filaments, distant ribosomes) the message strand drifts in from
    the left (where s23 left it) and slides into the cleft of a waiting ribosome; on 'joins a ribosome' the small subunit
    pulses and the strand seats in (RpMRNA, RpRibo).  The camera follows the strand in."""
    reset(); rnd = random.Random(33); T = lambda t: rt('s33', t)
    theme_lights(5, target=(0, 0, 0), key=(3.5, -8.0, 8.0), key_e=3400, spot=65, fill_e=260, rim_e=600, accent_e=320, accent_pos=(-6, 4, -3))
    rig = TRig('s33', rfps, dur, p_codon=0, ribo=True); rna = rig.rna
    move(rna.root, rfps, [(0.0, (-7.5, -2.0, Z_RNA + 1.6)), (T(318.6), (-4.0, -0.8, Z_RNA + 0.8)), (T(321.2), (0, 0, Z_RNA)), (dur, (0, 0, Z_RNA))])
    rot_keys(rna.root, rfps, [(0.0, (0.5, 0.0, 0.3)), (T(321.2), (0, 0, 0)), (dur, (0, 0, 0))])
    kf(rna.root, 'location', 1, (-7.5, -2.0, Z_RNA + 1.6))
    anchor('MRNA', (0, -0.4, 0.9), rna.units[3]); anchor('Ribo', (0.0, -2.0, 4.6), rig.ribo)
    pulse(rig.S.data.materials[0], rfps, T(321.3), (1.0, 0.75, 0.85), peak=1.8, fall=1.2); pulse_rim(rig.L.data.materials[0], rfps, T(321.5), peak=2.6, base=0.8, fall=1.2)
    kf(rig.ribo, 'rotation_euler', 1, (0.06, 0, -0.12)); kf(rig.ribo, 'rotation_euler', nf, (-0.04, 0, 0.10)); kf_lin(rig.ribo)
    cyto_dressing(rnd, rfps, dur, center=(0, 7, 0), n=24, avoid=4.5)
    for k, p in enumerate(((7.5, 9.0, -2.5), (-6.5, 10.0, 3.0))):
        rb, L, S, st = ribosome(f'Far{k}', p, s=0.8, translucent_large=False, sites=False); rb.rotation_euler = (rnd.uniform(0, 1), rnd.uniform(0, 1), rnd.uniform(0, 3)); drift(rb, rfps, dur, amp=0.15, seed=k, period=6)
    cam, tgt = cam_path([(0.0, (-8.0, -13.0, 3.0), (-5.0, -1.0, 0.5)), (T(318.6), (-5.0, -14.0, 3.2), (-2.5, 0, 0.6)), (T(321.2), (-1.5, -14.5, 2.6), (0, 0, 0.5)), (dur, (0.0, -14.0, 2.4), (0, 0, 0.6))], rfps, lens=42)
    env_kit(5, cam, rnd, rfps, dur, center=(0, 0, 0), dust_n=150, dust_spread=(16, 12, 9), halo_r=8.0, halo_at=(0, 6, 0.5), bokeh=4)

def two_subunits(nf, rfps, dur):
    """s34 322.59-330.98: the ribosome hero.  Its two subunits part to show the small (rose, below, RpSmall) and the large
    (lavender, above, with the exit tunnel, RpLarge) as each is named, then close again while the message strand slides on
    through the channel between them (RpMRNA); the camera orbits the pair."""
    reset(); rnd = random.Random(34); T = lambda t: rt('s34', t)
    theme_lights(5, target=(0, 0, 0.5), key=(3.5, -8.0, 8.0), key_e=3400, spot=65, fill_e=260, rim_e=600, accent_e=320, accent_pos=(-6, 4, -3))
    rig = TRig('s34', rfps, dur, p_codon=0, ribo=True); rna = rig.rna
    L, S = rig.L, rig.S; gap = 1.0
    for o, sg in ((L, 1), (S, -1)):
        z0 = o.location.z
        kf(o, 'location', F(T(323.4), rfps), (0, 0, z0)); kf(o, 'location', F(T(324.6), rfps), (0, 0, z0 + sg * 1.4)); kf(o, 'location', F(T(327.6), rfps), (0, 0, z0 + sg * 1.4)); kf(o, 'location', F(T(328.9), rfps), (0, 0, z0)); kf_ease(o)
    for key, pad in rig.sites.items():
        kf(pad, 'location', F(T(323.4), rfps), tuple(pad.location)); kf(pad, 'location', F(T(324.6), rfps), tuple(Vector(pad.location) + Vector((0, 0, -1.4)))); kf(pad, 'location', F(T(327.6), rfps), tuple(Vector(pad.location) + Vector((0, 0, -1.4)))); kf(pad, 'location', F(T(328.9), rfps), tuple(pad.location)); kf_ease(pad)
    tun = bpy.data.objects.get('RiboTunnel')
    if tun: kf(tun, 'location', F(T(323.4), rfps), tuple(tun.location)); kf(tun, 'location', F(T(324.6), rfps), tuple(Vector(tun.location) + Vector((0, 0, 1.4)))); kf(tun, 'location', F(T(327.6), rfps), tuple(Vector(tun.location) + Vector((0, 0, 1.4)))); kf(tun, 'location', F(T(328.9), rfps), tuple(tun.location)); kf_ease(tun)
    pulse(S.data.materials[0], rfps, T(325.6), (1.0, 0.75, 0.85), peak=2.0, fall=1.2); pulse_rim(L.data.materials[0], rfps, T(326.8), peak=3.0, base=0.8, fall=1.2)
    anchor('Small', (1.6, -1.6, -2.4), S); anchor('Large', (-0.8, -1.8, 3.4), L)
    move(rna.root, rfps, [(0.0, (0, 0, Z_RNA)), (T(328.2), (-0.6, 0, Z_RNA)), (dur, (-2.4, 0, Z_RNA))]); anchor('MRNA', (0, -0.5, 0.8), rna.units[12])
    kf(rig.ribo, 'rotation_euler', 1, (0.0, 0, 0.0)); kf(rig.ribo, 'rotation_euler', nf, (0.0, 0, 0.0)); kf_lin(rig.ribo)
    cyto_dressing(rnd, rfps, dur, center=(0, 8, 0), n=20, avoid=5.0)
    cam, tgt = camera((-4.0, -16.0, 2.4), (0, 0, 0.6), lens=42); orbit(cam, tgt, (0, 0, 0.6), 16.5, 2.6, -24, 22, 1, nf)
    lens_zoom(cam, rfps, [(0.0, 42), (T(324.6), 40), (dur, 46)])
    env_kit(5, cam, rnd, rfps, dur, center=(0, 0, 0.5), dust_n=150, dust_spread=(16, 12, 9), halo_r=9.0, halo_at=(0, 6, 0.5), bokeh=4)

def trna_hero(nf, rfps, dur):
    """s35 330.98-346.36: the hero tRNA (two-tube stems with base-pair rungs, D / T / anticodon loops, elbow, CCA tail)
    turns in the void: it drifts in on 'transfer RNA'; on 'one end an amino acid' the amino acid on the CCA tail pulses
    (RpAA); on 'the other end three bases, the anticodon' the three anticodon plates pulse in turn (RpAC0..2, RpAnti).  Rack
    focus from the amino acid to the anticodon; the ribosome and message wait out of focus behind."""
    reset(); rnd = random.Random(35); T = lambda t: rt('s35', t)
    theme_lights(5, target=(0.6, 0, 1.2), key=(3.0, -7.5, 7.5), key_e=3200, spot=65, fill_e=240, rim_e=600, accent_e=340, accent_pos=(-5, 4, -3))
    root, aa, bases = trna('tRNA', 'GGA', 'Pro', loc=(-0.9, 0, -0.3), s=1.5, with_aa=True, anchors=True, hd=True, ac_scale=1.0, ac_pitch=0.55)
    move(root, rfps, [(0.0, (-6.5, -1.5, 2.6)), (T(333.6), (-0.9, 0, -0.3)), (dur, (-0.7, 0, -0.2))]); rot_keys(root, rfps, [(0.0, (0.4, 0.3, -1.4)), (T(333.6), (0, 0, -0.25)), (dur, (0, 0, 0.35))])
    bead = bpy.data.objects[aa['bead']]; ma = own_mat(bead)
    for tp in (337.4, 339.0): pulse(ma, rfps, T(tp), AMINO['Pro'], peak=2.6, fall=1.2)
    hl = halo('AAHalo', (2.78 * 1.5, 0.8, 2.2 * 1.5), 1.1, AMINO['Pro'], strength=0.9); parent(hl, bpy.data.objects[root['arm']]); show_between(hl, F(T(337.0), rfps), F(T(340.5), rfps))
    for k, bo in enumerate(bases):
        mb = own_mat(bo)
        for tp in (342.0 + 0.3 * k, 344.4 + 0.25 * k): pulse(mb, rfps, T(tp), BASE['GGA'[k]], peak=2.8, fall=1.3)
    anchor('Anti', (0, 0, -0.85 * 1.5), root); anchor('AA', (2.78 * 1.5, 0, 2.2 * 1.5 + 0.55), bpy.data.objects[root['arm']])
    hb = halo('AntiHalo', (0, 0.8, -0.35 * 1.5), 1.1, TRNA_2, strength=0.9); parent(hb, root); show_between(hb, F(T(341.6), rfps), F(T(346.0), rfps))
    rb, L, S, st = ribosome('Ribo', (5.5, 7.5, -1.5), s=1.2, translucent_large=False, sites=False); rb.rotation_euler = (0.2, 0, -0.4); drift(rb, rfps, dur, amp=0.15, seed=2, period=6)
    r2 = RNA('FarRNA', MRNA_SEQ, loc=(-3.0, 7.0, 3.0), rot=(0, 0, 0.3), side=(0, 0, 1), rise=0.5, hd=False); drift(r2.root, rfps, dur, amp=0.2, seed=3, period=6)
    for k in range(3):
        t2, a2, b2 = trna(f'Far{k}', 'UAC', 'Met', loc=(rnd.uniform(-8, 8), 8 + 2 * k, rnd.uniform(-4, 4)), s=0.9, rot=(rnd.uniform(0, 2), rnd.uniform(0, 2), rnd.uniform(0, 3)), hd=False); drift(t2, rfps, dur, amp=0.25, seed=k + 5, period=7)
    cam, tgt = cam_path([(0.0, (-4.0, -12.0, 3.0), (-2.0, 0, 1.5)), (T(333.6), (-1.0, -9.5, 2.2), (0.8, 0, 1.4)), (T(337.4), (2.6, -6.4, 3.6), (3.0, 0, 3.0)), (T(341.6), (-1.6, -5.6, 0.6), (-0.8, 0, -0.5)),
                         (dur, (0.4, -8.0, 1.6), (0.9, 0, 1.2))], rfps, lens=45)
    if os.environ.get('VL_DOF', '0') == '1': rack_focus(cam, F(T(338.5), rfps), F(T(341.6), rfps), bead, bases[1])
    env_kit(5, cam, rnd, rfps, dur, center=(0.6, 0, 1.2), dust_n=140, halo_r=8.0, halo_at=(0.6, 5.5, 1.2), bokeh=4)

def anticodon_match(nf, rfps, dur):
    """s36 346.36-352.27: close on one codon of the message (three plates standing up) as a tRNA's anticodon descends onto
    it; the plates meet edge to edge and the hydrogen-bond dashes light pair by pair, G-C three, C-G three, U-A two: the
    same pairing rule (RpCodon, RpAnti).  Slow push-in with a slight orbit."""
    reset(); rnd = random.Random(36); T = lambda t: rt('s36', t)
    theme_lights(5, target=(0, 0, 0.6), key=(2.5, -7.0, 7.0), key_e=3000, spot=65, fill_e=240, rim_e=600, accent_e=340, accent_pos=(5, 4, -3))
    rig = TRig('s36', rfps, dur, x_rna=-3.4, p_codon=1, ribo=False)
    rig.sleeve(1, THEMES[5]['accent'], 346.4, strength=1.4, tag='CodonSleeve'); rig.rna.add_anchor(4, tag='Codon')
    d = rig.add_trna(1, 346.4, 349.2, yaw=-1.7); d['far'] = d['dock'] + Vector((0.6, -0.4, 2.8)); anchor('Anti', (0, 0, -0.55), d['root'])
    for k in range(3):
        b = 'CCU'[k]; n_ = 2 if b in 'AU' else 3
        for o in (rig.rna.bases[3 + k], d['bases'][k]): pulse(own_mat(o), rfps, T(349.4 + 0.5 * k), BASE[b] if o is rig.rna.bases[3 + k] else BASE[RNA_COMP[b]], peak=2.4, fall=1.0)
    rig.animate(step=2)
    for k in range(2):
        r2 = RNA(f'Far{k}', MRNA_SEQ[:12], loc=(rnd.uniform(-4, 4), 6 + 2 * k, rnd.uniform(-2, 3)), rot=(0, 0, rnd.uniform(-0.4, 0.4)), side=(0, 0, 1), rise=0.5, hd=False); drift(r2.root, rfps, dur, amp=0.2, seed=k, period=6)
    rb, L, S, st = ribosome('FarRibo', (5.0, 8.0, -2.0), s=1.0, translucent_large=False, sites=False); drift(rb, rfps, dur, amp=0.15, seed=2, period=6)
    c = Vector((rig.cx(1), 0, Z_RNA + 0.7))
    cam, tgt = cam_path([(0.0, tuple(c + Vector((-2.2, -7.5, 1.8))), tuple(c + Vector((0, 0, 0.4)))), (T(349.2), tuple(c + Vector((0.6, -5.6, 1.4))), tuple(c + Vector((0, 0, 0.5)))), (dur, tuple(c + Vector((1.4, -5.0, 1.0))), tuple(c + Vector((0, 0, 0.4))))], rfps, lens=50)
    env_kit(5, cam, rnd, rfps, dur, center=tuple(c), dust_n=130, halo_r=6.5, halo_at=tuple(c + Vector((0, 5, 0))), bokeh=4)

def start_met(nf, rfps, dur):
    """s37 352.27-361.32: the ribosome sits with its P site on AUG, which lights green as 'start codon AUG' is spoken
    (RpAUG); on 'the first tRNA arrives carrying methionine' the Met-tRNA flies in and docks on AUG, its anticodon UAC
    pairing with the codon and the red methionine on its CCA tail (RpMet).  The camera pushes in on the P site."""
    reset(); rnd = random.Random(37); T = lambda t: rt('s37', t)
    theme_lights(5, target=(0, 0, 0.5), key=(3.0, -8.0, 8.0), key_e=3400, spot=65, fill_e=260, rim_e=600, accent_e=340, accent_pos=(-6, 4, -3))
    rig = TRig('s37', rfps, dur, p_codon=0)
    rig.sleeve(0, START, 353.4, strength=2.2, tag='AUGSleeve'); rig.rna.add_anchor(1, tag='AUG')
    for k in range(3): pulse(own_mat(rig.rna.bases[k]), rfps, T(353.6 + 0.25 * k), BASE['AUG'[k]], peak=2.4, fall=1.2)
    d0 = rig.add_trna(0, 357.0, 359.4, yaw=-1.75); rig.build_chain(1, [359.4])
    bead = bpy.data.objects[rig.chain.beads[0]['bead']]; pulse(own_mat(bead), rfps, T(359.6), AMINO['Met'], peak=2.6, fall=1.4)
    a = anchor('Met', (0, 0, 0.55)); a.parent = rig.chain.beads[0]; a.matrix_parent_inverse = Matrix.Identity(4)
    rig.animate(step=2)
    cyto_dressing(rnd, rfps, dur, center=(0, 9, 0), n=18, avoid=6.0)
    P = Vector((rig.cx(0), 0, 0.4))
    cam, tgt = cam_path([(0.0, tuple(P + Vector((-1.5, -12.0, 2.4))), tuple(P + Vector((0.8, 0, 0.6)))), (T(356.8), tuple(P + Vector((-0.5, -8.4, 2.0))), tuple(P + Vector((0.3, 0, 0.8)))), (dur, tuple(P + Vector((0.9, -7.2, 2.2))), tuple(P + Vector((0.2, 0, 1.0))))], rfps, lens=45)
    env_kit(5, cam, rnd, rfps, dur, center=tuple(P), dust_n=140, dust_spread=(16, 12, 9), halo_r=8.0, halo_at=tuple(P + Vector((0, 6, 0))), bokeh=4)

def peptide_bond(nf, rfps, dur):
    """s38 361.32-374.3: the next codon CCU lights in the A site (RpCodon2); its matching tRNA (anticodon GGA) flies in
    with proline on its tail (RpAA2); on 'joins them with a peptide bond' the two amino acids swing together and a golden
    bond glows between them (RpBond).  The camera orbits over the top of the ribosome."""
    reset(); rnd = random.Random(38); T = lambda t: rt('s38', t)
    theme_lights(5, target=(0, 0, 1.5), key=(3.0, -8.0, 8.0), key_e=3400, spot=65, fill_e=260, rim_e=600, accent_e=340, accent_pos=(-6, 4, -3))
    rig = TRig('s38', rfps, dur, p_codon=0)
    rig.sleeve(0, START, 361.3, strength=1.2, tag='AUGSleeve'); rig.sleeve(1, THEMES[5]['accent'], 362.6, strength=2.2, tag='CCUSleeve'); rig.rna.add_anchor(4, tag='Codon2')
    for k in range(3): pulse(own_mat(rig.rna.bases[3 + k]), rfps, T(362.8 + 0.25 * k), BASE['CCU'[k]], peak=2.4, fall=1.2)
    d0 = rig.add_trna(0, 361.0, 361.2, yaw=-1.75); d1 = rig.add_trna(1, 364.4, 367.2, yaw=-1.35)
    rig.build_chain(2, [361.2, 370.6]); rig.bond_glow(1, 370.4, dur_=2.6)
    b1 = bpy.data.objects[rig.chain.beads[1]['bead']]; pulse(own_mat(b1), rfps, T(367.4), AMINO['Pro'], peak=2.4, fall=1.2)
    a = anchor('AA2', (0, 0, 0.55)); a.parent = rig.chain.beads[1]; a.matrix_parent_inverse = Matrix.Identity(4)
    a2 = anchor('Bond', (0.35, -0.4, 0.45)); a2.parent = rig.chain.beads[1]; a2.matrix_parent_inverse = Matrix.Identity(4)
    rig.animate(step=2)
    cyto_dressing(rnd, rfps, dur, center=(0, 9, 0), n=18, avoid=6.0)
    P = Vector((rig.cx(0) + 0.6, 0, 1.6))
    cam, tgt = cam_path([(0.0, tuple(P + Vector((0.6, -8.0, 1.6))), tuple(P + Vector((0, 0, -0.6)))), (T(364.4), tuple(P + Vector((2.2, -7.6, 2.0))), tuple(P + Vector((0.6, 0, -0.4)))), (T(368.6), tuple(P + Vector((1.4, -6.4, 3.4))), tuple(P + Vector((0.4, 0, 0.6)))),
                         (dur, tuple(P + Vector((-0.6, -6.0, 3.8))), tuple(P + Vector((0.3, 0, 0.8))))], rfps, lens=45)
    env_kit(5, cam, rnd, rfps, dur, center=tuple(P), dust_n=140, dust_spread=(16, 12, 9), halo_r=8.0, halo_at=tuple(P + Vector((0, 6, 0))), bokeh=4)

def elongation(nf, rfps, dur):
    """s39 374.3-383.27: the empty Met-tRNA leaves to the upper left (RpEmpty) and the ribosome steps one codon to the
    right (RpRibo); then two more cycles run fast, codon by codon, the chain rising out of the exit tunnel (RpChain).
    The camera pulls back a little and pans with the ribosome."""
    reset(); rnd = random.Random(39); T = lambda t: rt('s39', t)
    theme_lights(5, target=(1.2, 0, 1.0), key=(3.5, -8.5, 8.0), key_e=3400, spot=65, fill_e=260, rim_e=600, accent_e=340, accent_pos=(-6, 4, -3))
    rig = TRig('s39', rfps, dur, p_codon=0)
    rig.step(377.4, 1); rig.step(380.6, 2); rig.step(382.4, 3)
    d0 = rig.add_trna(0, 374.0, 374.2, t_leave=374.8, yaw=-1.75); d1 = rig.add_trna(1, 374.0, 374.2, t_leave=380.4, yaw=-1.35)
    d2 = rig.add_trna(2, 378.2, 379.9, t_leave=382.2, yaw=-1.35); d3 = rig.add_trna(3, 380.9, 381.9, yaw=-1.35)
    rig.build_chain(4, [374.2, 374.2, 380.1, 382.1]); rig.bond_glow(2, 380.0, dur_=1.2); rig.bond_glow(3, 382.0, dur_=1.2)
    for j, col, t_on in ((1, THEMES[5]['accent'], 374.3), (2, THEMES[5]['accent'], 378.0), (3, THEMES[5]['accent'], 380.7)): rig.sleeve(j, col, t_on, strength=1.6)
    anchor('Empty', (0.4, 0, 1.6), d0['root']); anchor('Ribo', (0.4, -2.0, 4.8), rig.ribo)
    a = anchor('Chain', (0, -0.4, 0.5)); a.parent = rig.chain.beads[0]; a.matrix_parent_inverse = Matrix.Identity(4)
    rig.animate(step=2)
    cyto_dressing(rnd, rfps, dur, center=(0, 9, 0), n=18, avoid=6.0)
    keys = []
    for t, dz in ((0.0, 1.4), (T(377.4), 1.6), (T(380.6), 2.0), (dur, 2.4)):
        rx = rig.ribo_x(t); keys.append((t, (rx + 0.5, -10.5 - 0.6 * dz, 1.2 + dz), (rx + 0.4, 0, 1.0)))
    cam, tgt = cam_path(keys, rfps, lens=42)
    env_kit(5, cam, rnd, rfps, dur, center=(1, 0, 1), dust_n=140, dust_spread=(16, 12, 9), halo_r=8.5, halo_at=(1, 6, 0.8), bokeh=4)

def stop_release(nf, rfps, dur):
    """s40 383.27-394.46: the ribosome walks on to the stop codon UAA, which lights red (RpStop); two tRNAs approach and
    turn back, nothing pairs; on 'the chain is released' the finished chain floats free (RpChain) and on 'the subunits
    separate' large and small drift apart while the camera pulls back."""
    reset(); rnd = random.Random(40); T = lambda t: rt('s40', t)
    theme_lights(5, target=(2.0, 0, 1.0), key=(4.0, -9.0, 8.5), key_e=3600, spot=68, fill_e=280, rim_e=620, accent_e=340, accent_pos=(-6, 4, -3))
    rig = TRig('s40', rfps, dur, p_codon=4); rig.step(385.0, 5)
    rig.sleeve(6, STOP, 385.6, strength=2.6, tag='StopSleeve'); rig.rna.add_anchor(19, tag='Stop')
    for k in range(3): pulse(own_mat(rig.rna.bases[18 + k]), rfps, T(385.8 + 0.25 * k), BASE['UAA'[k]], peak=2.6, fall=1.2)
    d4 = rig.add_trna(4, 383.0, 383.2, t_leave=385.4, yaw=-1.75); d5 = rig.add_trna(5, 383.0, 383.2, t_leave=390.2, yaw=-1.35)
    b1 = rig.add_trna(6, 386.4, 387.6, yaw=-1.35, bounce=True); b2 = rig.add_trna(6, 388.0, 389.2, yaw=-1.35, bounce=True); b2['root'].name = 'tRNA6b'; b2['far'] = b2['dock'] + Vector((-2.4, -2.0, 4.0))
    rig.build_chain(6, [383.2, 383.2, 383.2, 383.2, 383.2, 383.2])
    rig.animate(step=2)
    # release: from 389.8 the whole chain floats up and away (re-keyed on the rig's own frames); the subunits part from 391.6
    ch = rig.chain; base = [Vector(rig.bead_pos(k, T(389.8))) for k in range(6)]
    def rel(k, t):
        u = smooth01((t - T(389.8)) / 3.6); p1 = base[k] + Vector((-1.6 + 0.1 * k, -2.2, 3.4 + 0.15 * k))
        return vlerp(base[k], p1, u) + Vector((0.3 * math.sin(2 * t + k), 0, 0.2 * math.sin(1.7 * t + 0.7 * k))) * u
    for fr in [f for f in rig.frames if f >= F(T(389.8), rfps)]:
        t = (fr - 1) / rfps; ch.pose([rel(k, t) for k in range(6)], fr, ups=[Vector((0, -1, 0.3))] * 6)
    a = anchor('Chain', (0, -0.4, 0.5)); a.parent = ch.beads[2]; a.matrix_parent_inverse = Matrix.Identity(4)
    for o, sg in ((rig.L, 1), (rig.S, -1)):
        z0 = o.location.z; kf(o, 'location', F(T(391.4), rfps), (0, 0, z0)); kf(o, 'location', F(T(394.4), rfps), (0.6 * sg, 1.2 * sg, z0 + sg * 3.0)); kf_ease(o)
        kf(o, 'rotation_euler', F(T(391.4), rfps), (0, 0, 0)); kf(o, 'rotation_euler', F(T(394.4), rfps), (0.25 * sg, 0.15, 0.3 * sg)); kf_ease(o)
    for key, pad in rig.sites.items(): hide_from(pad, F(T(391.6), rfps))
    tun = bpy.data.objects.get('RiboTunnel')
    if tun: upd(); tun.parent = rig.L; tun.matrix_parent_inverse = rig.L.matrix_world.inverted()
    cyto_dressing(rnd, rfps, dur, center=(2, 9, 0), n=18, avoid=6.0)
    keys = []
    for t, dist, dz in ((0.0, 11.0, 1.6), (T(385.6), 9.5, 1.6), (T(389.8), 11.5, 2.4), (dur, 15.5, 3.2)):
        rx = rig.ribo_x(t); keys.append((t, (rx + 0.6, -dist, dz), (rx + 0.3, 0, 1.0)))
    cam, tgt = cam_path(keys, rfps, lens=42)
    env_kit(5, cam, rnd, rfps, dur, center=(2, 0, 1), dust_n=150, dust_spread=(16, 12, 9), halo_r=9.0, halo_at=(2, 6, 0.8), bokeh=4)

def ribosome_field(nf, rfps, dur):
    """s41 394.46-399.62: a crane up and back reveals a field of ribosomes at work: forty instanced two-subunit ribosomes
    strung along message strands (polysomes), each with a chain of amino acids rising out of it, over rough ER sheets in
    the teal cytoplasm; every ribosome rocks and drifts."""
    reset(); rnd = random.Random(41); T = lambda t: rt('s41', t)
    theme_lights(5, target=(0, 4, 0), key=(5.0, -10.0, 10.0), key_e=5200, spot=75, fill_e=360, rim_e=700, accent_e=400, accent_pos=(-8, 6, -3))
    rb, L, S, st = ribosome('Proto', (0, 0, 0), s=0.7, translucent_large=False, sites=False)
    for o in (L, S): bake_mods(o)
    protos = [L, S]; roots = []
    am = [m_amino(a) for a in ('Met', 'Pro', 'Gly', 'Ala', 'Ser', 'Lys')]
    for k in range(40):
        p = Vector((rnd.uniform(-11, 11), rnd.uniform(-1, 14), rnd.uniform(-4, 4)))
        r, out = dup_tree(protos, f'R{k}', tuple(p), rot=(rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4), rnd.uniform(0, 6.3)), scale=rnd.uniform(0.75, 1.1))
        drift(r, rfps, dur, amp=0.12, seed=k, period=5 + rnd.random()); roots.append(r)
        kf(r, 'rotation_euler', 1, tuple(r.rotation_euler)); kf(r, 'rotation_euler', nf, tuple(Vector(r.rotation_euler) + Vector((0.1, 0.05, 0.25)) * rnd.uniform(-1, 1))); kf_lin(r)
        n = rnd.randint(3, 9); pts = [Vector((0.15 * math.sin(1.9 * i), -0.12 * i, 2.5 + 0.42 * i)) for i in range(n)]
        ch = spheres_mesh(f'Ch{k}', pts, 0.19, rnd.choice(am), subdiv=2); parent(ch, r)
        segs = [(pts[i], pts[i + 1]) for i in range(n - 1)]; lk = capsules_mesh(f'Lk{k}', segs, 0.06, M('peptide', lambda: mat_gloss(PEPTIDE, rough=0.3, coat=0.5, name='peptide')), seg=10, ring=5); parent(lk, r)
    for o in protos: o.hide_render = True; o.hide_viewport = True
    for k in range(6):                                          # message strands threading through groups (polysomes)
        rs = rnd.sample(roots, 4); pts = [Vector(r.location) + Vector((0, 0, -0.3)) for r in sorted(rs, key=lambda r: r.location.x)]
        pts = [pts[0] + Vector((-3, 0, 0.5))] + pts + [pts[-1] + Vector((3, 0, -0.5))]
        c = curve_obj(f'Msg{k}', pts, 0.06, m_rna_rail(), res=8, kind='NURBS')
    for o in organelles('Cyto', rnd, 36, (0, 8, 0), 12.0, avoid_r=0.0, s=1.1): drift(o, rfps, dur, amp=0.1, seed=rnd.randint(1, 99), period=6.0)
    filaments('Fil', rnd, 8, (0, 6, 0), (10, 6, 5), r=0.035, length=9.0)
    cam, tgt = cam_path([(0.0, (-1.0, -12.0, 1.0), (0, 2, 0.5)), (dur, (2.0, -22.0, 9.0), (0, 5, 0))], rfps, lens=40)
    env_kit(5, cam, rnd, rfps, dur, center=(0, 4, 0), dust_n=200, dust_spread=(20, 14, 10), halo_r=12.0, halo_at=(0, 12, 0), bokeh=5, halo_strength=0.4)

# ================================================================= section-6 assets: vessel, beta-globin segment, dogma stations
def vessel_tube(name, pts, r=3.2, color=(0.18, 0.03, 0.04), rim=(0.9, 0.35, 0.35)):
    """A blood vessel the camera flies inside: a bevelled tube with an inward-facing rimmed membrane, a lipid bump, and a
    ring texture of endothelial cells (voronoi) so the wall reads as tissue."""
    m = mat_rim2(color, rim, a_center=0.72, a_rim=0.97, emit=0.35, name=name + '_m', blend=0.4, rough=0.6, bump=0.35, bump_scale=6.0, cull=False)
    c = curve_obj(name, pts, r, m, res=12, kind='NURBS', bevel_res=12)
    try: c.visible_shadow = False
    except Exception: pass
    return c

def globin_segment(name, aminos, loc=(0, 0, 0), r=0.30, spacing=0.72, sag=0.25):
    """A short stretch of the beta-globin chain (V-H-L-T-P-E-E-K) as posed amino-acid roots joined by peptide links; returns
    (roots, links, points)."""
    pts = [Vector(loc) + Vector((spacing * (k - (len(aminos) - 1) / 2), 0.15 * math.sin(k * 1.3), -sag * math.sin(math.pi * k / (len(aminos) - 1)))) for k in range(len(aminos))]
    roots = []; links = []; lm = M('peptide', lambda: mat_gloss(PEPTIDE, rough=0.3, coat=0.5, name='peptide'))
    for k, a in enumerate(aminos):
        rt_ = amino_acid(f'{name}_{k}', a, tuple(pts[k]), r=r, rot=(0.6 * (1 if k % 2 else -1), 0, 0)); roots.append(rt_)
        if k: l = unit_link(f'{name}_l{k}', 0.09, lm); fit_link(l, pts[k - 1], pts[k]); links.append(l)
    return roots, links, pts

def dogma_station_dna(name, loc, n_bp=26, s=1.0):
    h = Helix(name, HERO_SEQ[:n_bp], loc=loc, rot=(0, -math.pi / 2, 0), R=1.0 * s, individual=False, hd=True); return h

# ================================================================= builders: 6. From Chain to Protein
def chain_folds(nf, rfps, dur):
    """s43 402.22-414.81: a sixteen-residue chain (distinct side chains) drifts straight and loose for 'not yet a protein'
    (RpChain); on 'folds by itself' it curls into a compact globule while turning (RpProt); on 'this shape decides its job'
    a pocket lights on the globule and a substrate molecule docks into it (RpSub).  Orbit + push in."""
    reset(); rnd = random.Random(43); T = lambda t: rt('s43', t)
    theme_lights(6, target=(0, 0, 0.3), key=(3.0, -8.0, 8.0), key_e=3200, spot=65, fill_e=240, rim_e=600, accent_e=340, accent_pos=(-6, 4, -3))
    aminos = ['Met', 'Leu', 'Ser', 'Pro', 'Ala', 'Gly', 'Lys', 'Phe', 'Val', 'Glu', 'Thr', 'Asp', 'Trp', 'His', 'Ile', 'Arg']
    ch = Chain('Chain', aminos, r=0.26, r_link=0.08, hd=True)
    straight = straight_path(16, step=0.62, origin=(0, 0, 0.3), direction=(1, 0, 0), sag=0.5); folded = [p + Vector((0, 0, 0.3)) for p in fold_path(16, seed=8, box=1.1, step=0.55)]
    t_f0, t_f1 = T(406.5), T(410.2)
    def pos(k, t):
        u = smooth01((t - t_f0) / (t_f1 - t_f0)); wob = Vector((0, 0.12 * math.sin(1.4 * t + k * 0.8), 0.16 * math.sin(1.1 * t + k * 0.5))) * (1 - u)
        p = vlerp(straight[k], folded[k], u) + wob
        ang = 0.35 * max(0.0, t - t_f0); c, s_ = math.cos(ang), math.sin(ang)          # the globule turns once it forms
        return Vector((p.x * c - p.y * s_, p.x * s_ + p.y * c, p.z))
    ch.animate(pos, rfps, 0.0, dur, step=2, ups=[Vector((0, -1, 0.4))] * 16)
    a = anchor('Chain', (0, -0.4, 0.55)); a.parent = ch.beads[7]; a.matrix_parent_inverse = Matrix.Identity(4)
    a2 = anchor('Prot', (0.0, -0.9, 1.1)); a2.parent = ch.beads[7]; a2.matrix_parent_inverse = Matrix.Identity(4)
    pocket = sphere('Pocket', 0.42, (0, 0, 0.3), seg=32, ring=16, mat=mat_translucent((1.0, 0.85, 0.45), alpha=0.22, emit=2.4, name='pocket_m')); scale_in(pocket, rfps, T(410.9), dur=0.6)
    try: pocket.visible_shadow = False
    except Exception: pass
    sub = amino_acid('Sub', 'Tyr', (0, -4.5, 2.6), r=0.22); setmat(bpy.data.objects[sub['bead']], mat_lit((0.55, 0.95, 0.75), emit=1.2, name='sub_m'))
    scale_in(sub, rfps, T(411.4), dur=0.4); move(sub, rfps, [(T(411.4), (0, -4.5, 2.6)), (T(413.4), (0, -0.2, 0.35))]); anchor('Sub', (0, -0.2, 0.5), sub)
    hl = halo('ProtHalo', (0, 2.2, 0.3), 2.6, THEMES[6]['accent'], strength=0.5); scale_in(hl, rfps, T(408.5), dur=1.2)
    rb, L, S, st = ribosome('FarRibo', (-6.5, 9.0, -1.5), s=1.2, translucent_large=False, sites=False); drift(rb, rfps, dur, amp=0.15, seed=2, period=6)
    r2 = RNA('FarRNA', MRNA_SEQ, loc=(4.0, 8.0, 3.0), rot=(0, 0, 0.3), side=(0, 0, 1), rise=0.5, hd=False); drift(r2.root, rfps, dur, amp=0.2, seed=3, period=6)
    cam, tgt = cam_path([(0.0, (-5.0, -11.0, 2.0), (-1.5, 0, 0.3)), (T(406.5), (3.0, -10.5, 2.4), (1.0, 0, 0.3)), (T(410.2), (2.2, -7.6, 2.8), (0, 0, 0.4)), (dur, (-1.6, -6.4, 1.6), (0, 0, 0.35))], rfps, lens=45)
    env_kit(6, cam, rnd, rfps, dur, center=(0, 0, 0.3), dust_n=140, halo_r=0.0, bokeh=4, helices=1)

def haemoglobin_pocket(nf, rfps, dur):
    """s44 414.81-423.99: haemoglobin hero.  Its four globin chains (two alpha crimson, two beta indigo, each with a haem
    plate and iron) hang apart for 'look at haemoglobin' (RpHb, RpAlpha, RpBeta), fold together on 'four chains fold
    together' into a pocket (RpPocket), and an O2 pair drifts in and glows in the pocket for 'can hold oxygen' (RpO2).
    Orbit and push toward the pocket."""
    reset(); rnd = random.Random(44); T = lambda t: rt('s44', t)
    theme_lights(6, target=(0, 0, 0.3), key=(3.0, -8.0, 8.0), key_e=3400, spot=65, fill_e=260, rim_e=620, accent_e=340, accent_pos=(-6, 4, -3))
    hb, lobes, o2 = haemoglobin('Hb', (0, 0, 0.3), s=1.5, spread=2.4, o2=True)
    hb_spread(lobes, rfps, [(T(416.8), 2.4), (T(420.2), 1.0)]); spin(hb, rfps, dur, rate=0.04, axis=2)
    for k, lr in enumerate(lobes):
        kf(lr, 'rotation_euler', 1, (0, 0, 0)); kf(lr, 'rotation_euler', F(T(420.2), rfps), (0.35 * (1 if k % 2 else -1), 0.2, 0.3)); kf_ease(lr)
    anchor('Hb', (0, -1.2, 3.6), hb); anchor('Alpha', (0, -0.6, 1.1), lobes[0]); anchor('Beta', (0, -0.6, 1.1), lobes[2]); anchor('Pocket', (0, -0.9, -0.3), hb)
    move(o2, rfps, [(T(414.8), (0, -5.5, 3.0)), (T(421.0), (0, -5.5, 3.0)), (T(423.2), (0, 0, 0))]); scale_in(o2, rfps, T(420.8), dur=0.3); anchor('O2', (0, 0, 0.4), o2)
    mo = bpy.data.objects['Hb_Oa'].data.materials[0]; pulse(mo, rfps, T(423.3), O2, peak=6.0, base=1.8, fall=0.8)
    pk = sphere('PocketGlow', 0.55, (0, 0, 0), seg=32, ring=16, mat=mat_translucent(O2, alpha=0.18, emit=2.0, name='pocket_m')); parent(pk, hb); scale_in(pk, rfps, T(420.4), dur=0.6)
    try: pk.visible_shadow = False
    except Exception: pass
    L = light('POINT', (0, -0.5, 0.3), 0, O2, 'O2Light'); parent(L, hb); key_light(L, F(T(423.0), rfps), 0.0); key_light(L, F(T(423.6), rfps), 80.0)
    for k in range(4):
        rc, sk = red_cell(f'RBC{k}', (rnd.uniform(-8, 8), 8 + 2 * k, rnd.uniform(-4, 4)), r=1.1); rc.rotation_euler = (rnd.uniform(0, 2), rnd.uniform(0, 2), 0); drift(rc, rfps, dur, amp=0.3, seed=k, period=7)
    cam, tgt = camera((-4.0, -12.0, 2.6), (0, 0, 0.5), lens=45); orbit(cam, tgt, (0, 0, 0.5), 12.5, 2.8, -30, 12, 1, F(T(420.2), rfps))
    kf(cam, 'location', F(T(423.9), rfps), (1.4, -8.0, 2.2)); kf_ease(cam)
    lens_zoom(cam, rfps, [(0.0, 45), (dur, 55)])
    if os.environ.get('VL_DOF', '0') == '1': rack_focus(cam, F(T(420.2), rfps), F(T(423.2), rfps), lobes[0], o2)
    env_kit(6, cam, rnd, rfps, dur, center=(0, 0, 0.3), dust_n=140, halo_r=8.0, halo_at=(0, 5.5, 0.3), bokeh=4)

def one_base_change(nf, rfps, dur):
    """s45 423.99-435.56: back on the helix: one base pair is singled out (a sleeve of light, RpDNA) for 'if just one base
    changes'; above it the codon it writes, G A G, stands as a strip (RpGAG); on 'GAG becomes GUG' the DNA pair flips its
    letters (T-A to A-T, plates swapped) and the middle A of the strip is replaced by a violet U (RpU).  Push in, tilt up."""
    reset(); rnd = random.Random(45); T = lambda t: rt('s45', t)
    theme_lights(6, target=(0, 0, 0.6), key=(3.0, -7.5, 7.5), key_e=3000, spot=65, fill_e=240, rim_e=600, accent_e=340, accent_pos=(5, 4, -3))
    seq = 'GCATTA' + 'CTC' + 'AGGTACA'; K = 7; ph = math.pi / 2 - K * (2 * math.pi / 10)          # pair K stands vertical in the y-z plane: seen face-on from -y, the hero rung
    h = Helix('DNA', seq, loc=(0, 0, 0), individual=True, hd=True, phase=ph); spin(h.root, rfps, dur, rate=0.0)
    c = h.axis_pt(K); sl = halo('PairGlow', tuple(c + Vector((0, 1.7, 0))), 1.05, THEMES[6]['accent'], strength=0.7, alpha=0.6); parent(sl, h.root); hide_until(sl, F(T(425.4), rfps))   # a soft spot of light right behind the hero rung (EEVEE renders translucent sleeves as slabs)
    anchor('DNA', c + Vector((0, -0.4, 1.35)), h.root)
    PL = light('POINT', tuple(c + Vector((0.4, -1.6, 0.6))), 0, THEMES[6]['accent'], 'PairLight'); parent(PL, h.root); key_light(PL, F(T(425.2), rfps), 0.0); key_light(PL, F(T(425.9), rfps), 70.0)
    for s_ in (0, 1):
        old_pl = [o for o in h.unit_objs(K, s_) if o.name.startswith('DNA_r')][0]; b_old = h.base_of(K, s_); b_new = COMP[b_old]
        pulse(own_mat(old_pl), rfps, T(425.6), BASE[b_old], peak=2.4, fall=1.4)
        scale_out(old_pl, rfps, T(431.6), dur=0.5)
        new_pl = mesh_obj(f'New{s_}', plate_bmesh(b_new, h.y_out, atoms=h.atoms), m_base(b_new)); parent(new_pl, h.units[(K, s_)]); scale_in(new_pl, rfps, T(431.9), dur=0.5)
        pulse(own_mat(new_pl), rfps, T(432.6), BASE[b_new], peak=2.6, fall=1.4)
    strip = letter_strip('GAG', 'GAG', loc=tuple(c + Vector((0, 0, 2.05))), rise=0.62, anchors=False, side=(0, 0, -1)); anchor('GAG', (0, 0, 0.35), strip.root); strip.add_anchor(1, tag='U')   # the codon hangs from its rail toward the pair it was read from
    drift(strip.root, rfps, dur, amp=0.04, seed=2, period=4.0)
    for k in range(3): pulse(own_mat(strip.bases[k]), rfps, T(429.6 + 0.3 * k), BASE['GAG'[k]], peak=2.4, fall=1.2)
    old_a = strip.bases[1]; scale_out(old_a, rfps, T(432.4), dur=0.45)
    ubm = plate_bmesh('U', -strip.base_y0(), atoms=strip.atoms); bmesh.ops.rotate(ubm, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi, 3, 'Z'), verts=list(ubm.verts))
    capsule_into(ubm, (0, R_SUGAR_RING - 0.06, 0), (0, strip.base_y0() + 0.03, 0), 0.03, 10, 5)
    newU = mesh_obj('NewU', ubm, mat_gloss(BASE['U'], rough=0.25, coat=0.6, name='U_new', sss=0.1)); parent(newU, strip.units[1]); scale_in(newU, rfps, T(432.7), dur=0.5)
    pulse(newU.data.materials[0], rfps, T(433.4), BASE['U'], peak=3.0, fall=1.4); pulse(newU.data.materials[0], rfps, T(434.8), BASE['U'], peak=2.0, fall=1.0)
    for k in (0, 2): pulse(own_mat(strip.bases[k]), rfps, T(433.4 + 0.2 * k), BASE['G'], peak=1.6, fall=1.0)
    bm = beam('Link', c + Vector((0, 0, 1.15)), c + Vector((0, 0, 1.38)), r=0.04, color=THEMES[6]['accent'], strength=1.4, f_on=F(T(428.8), rfps), alpha=0.3); parent(bm, h.root)
    cam, tgt = cam_path([(0.0, (-2.5, -9.5, 1.4), (0, 0, 0.2)), (T(425.4), tuple(c + Vector((-1.0, -6.6, 1.0))), tuple(c + Vector((0, 0, 0.15)))), (T(428.8), tuple(c + Vector((0.8, -7.2, 1.5))), tuple(c + Vector((0, 0, 0.62)))),
                         (T(432.0), tuple(c + Vector((0.6, -6.8, 1.4))), tuple(c + Vector((0, 0, 0.66)))), (dur, tuple(c + Vector((-0.6, -7.0, 1.3))), tuple(c + Vector((0, 0, 0.62))))], rfps, lens=48)   # the pair sits a third up the frame, its codon just above: one hero column
    helix_hero_env(6, cam, rnd, rfps, dur, center=tuple(c), helices=2, halo_r=1.5, halo_back=10.0, halo_alpha=0.3, halo_strength=0.5)   # a faint spot of glow far behind the pair (sized to the 48 mm lens), never a sphere

def glu_to_val(nf, rfps, dur):
    """s46 435.56-441.4: a stretch of the beta-globin chain (Val His Leu Thr Pro Glu Glu Lys, each its own side chain); the
    GUG strip below lights its U; on 'glutamic acid is replaced by valine' the magenta glutamic acid (RpGlu) lifts out of the
    chain and a teal valine (RpVal) drops into its place, the links re-fitting.  Push in with a rack focus."""
    reset(); rnd = random.Random(46); T = lambda t: rt('s46', t)
    theme_lights(6, target=(0, 0, 0.4), key=(3.0, -7.5, 7.5), key_e=3000, spot=65, fill_e=240, rim_e=600, accent_e=340, accent_pos=(-5, 4, -3))
    aminos = ['Val', 'His', 'Leu', 'Thr', 'Pro', 'Glu', 'Glu', 'Lys']; roots, links, pts = globin_segment('Glob', aminos, loc=(0, 0, 0.9), r=0.30, spacing=0.78)
    K = 5; glu = roots[K]; pg = pts[K]
    pulse(own_mat(bpy.data.objects[glu['bead']]), rfps, T(437.4), AMINO['Glu'], peak=2.6, fall=1.2)
    move(glu, rfps, [(T(438.2), tuple(pg)), (T(439.6), tuple(pg + Vector((0.4, -1.6, 2.6)))), (dur, tuple(pg + Vector((0.9, -2.4, 3.6))))]); rot_keys(glu, rfps, [(T(438.2), (0.6, 0, 0)), (dur, (1.8, 0.6, 0.4))])
    anchor('Glu', (0, -0.3, 0.6), glu)
    val = amino_acid('ValNew', 'Val', tuple(pg + Vector((-0.4, -1.8, 3.2))), r=0.30, rot=(0.6, 0, 0)); scale_in(val, rfps, T(438.6), dur=0.4)
    move(val, rfps, [(T(438.6), tuple(pg + Vector((-0.4, -1.8, 3.2)))), (T(440.2), tuple(pg))]); anchor('Val', (0, -0.3, 0.6), val)
    pulse(own_mat(bpy.data.objects[val['bead']]), rfps, T(440.4), AMINO['Val'], peak=3.0, fall=1.2)
    for f in range(F(T(438.2), rfps), nf + 1, 2):                          # links follow whichever bead occupies the slot
        t = (f - 1) / rfps; u = smooth01((t - T(438.6)) / 1.6); occ = vlerp(pg + Vector((-0.4, -1.8, 3.2)), pg, u) if t >= T(438.6) else vlerp(pg, pg + Vector((0.4, -1.6, 2.6)), smooth01((t - T(438.2)) / 1.4))
        fit_link(links[K - 1], pts[K - 1], occ, f); fit_link(links[K], occ, pts[K + 1], f)
    lin_id(links[K - 1]); lin_id(links[K])
    for r_ in roots:
        if r_ is not glu: drift(r_, rfps, dur, amp=0.03, seed=len(r_.name), period=3.5)
    strip = letter_strip('GUG', 'GUG', loc=(pg.x, 0, -1.3), rise=0.62, anchors=False); anchor('GUG', (0, 0, -0.5), strip.root)
    pulse(own_mat(strip.bases[1]), rfps, T(436.2), BASE['U'], peak=3.0, fall=1.4); strip.sleeve(0, AMINO['Val'], F(T(439.8), rfps), None, n=3, r=0.36, strength=1.4, tag='GUGSleeve')
    bm = beam('UpBeam', (pg.x, 0, -0.3), (pg.x, 0, 0.5), r=0.05, color=AMINO['Val'], strength=1.6, f_on=F(T(438.6), rfps), alpha=0.35)
    bg = Helix('BgDNA', HERO_SEQ[:44], loc=(0, 8.5, -0.5), rot=(0, 0, 0.2), individual=False, hd=False); spin(bg.root, rfps, dur, rate=0.03)
    cam, tgt = cam_path([(0.0, (-2.8, -9.0, 1.6), (-0.4, 0, 0.5)), (T(438.2), tuple(pg + Vector((0.6, -6.6, 1.2))), tuple(pg + Vector((0, 0, 0.2)))), (dur, tuple(pg + Vector((-0.8, -6.0, 1.6))), tuple(pg + Vector((0, 0, 0.0))))], rfps, lens=48)
    if os.environ.get('VL_DOF', '0') == '1': rack_focus(cam, F(T(438.6), rfps), F(T(440.2), rfps), glu, val)
    env_kit(6, cam, rnd, rfps, dur, center=(0, 0, 0.4), dust_n=130, halo_r=7.5, halo_at=(0, 5.5, 0.5), bokeh=4)

def sickle_cells(nf, rfps, dur):
    """s47 441.4-454.32: inside a vessel.  A haemoglobin at the front swaps to its stretched mutant and copies stack into a
    stiff rod for 'haemoglobin's shape changes' (RpHb); a stream of biconcave red cells flows toward us and, one after
    another, buckles into crescents for 'sickle-shaped' (RpRBC, RpSickle); 'sickle cell anaemia' lands on the stream.
    The camera dollies down the vessel."""
    reset(); rnd = random.Random(47); T = lambda t: rt('s47', t)
    theme_lights(6, target=(0, 4, 0), key=(3.0, -4.0, 7.0), key_e=3600, spot=80, fill_e=320, rim_e=600, accent_e=400, accent_pos=(-4, 14, 2))
    vessel_tube('Vessel', [(0, -12, 0), (0.3, -4, 0.2), (-0.4, 6, -0.3), (0.6, 16, 0.4), (-0.5, 28, -0.6), (0.2, 40, 0.2)], r=4.0)
    for k, p in enumerate(((2.0, 6.0, 1.5), (-2.2, 12.0, -1.2), (1.5, 20.0, 0.8), (-1.5, 28.0, 1.5))): light('POINT', p, 240, (1.0, 0.7, 0.7), f'VL{k}')
    hbN, lobesN, o2N = haemoglobin('HbN', (-2.4, -1.0, 1.3), s=0.55, spread=1.0, o2=True); spin(hbN, rfps, dur, rate=0.06, axis=2); scale_out(hbN, rfps, T(443.6), dur=0.5, base=1.0)
    hbS, lobesS, o2S = haemoglobin('HbS', (-2.4, -1.0, 1.3), s=0.55, spread=1.0, o2=False, sickle=True); scale_in(hbS, rfps, T(443.6), dur=0.5); spin(hbS, rfps, dur, rate=0.06, axis=2)
    anchor('Hb', (0, -0.6, 1.4), hbS)
    for k in range(1, 5):                                                    # the mutant polymerises into a stiff rod
        rr, lb, o2r = haemoglobin(f'Rod{k}', (0, 0, 0), s=0.55, spread=1.0, o2=False, sickle=True); rr.rotation_euler = (0, 0, 0.4 * k); parent(rr, hbS)
        kf(rr, 'location', F(T(444.4), rfps), (0, 0, 0)); kf(rr, 'location', F(T(445.6), rfps), (0, 0, -1.0 * k)); kf_ease(rr); scale_in(rr, rfps, T(444.4), dur=0.4)
    cells = []
    for k in range(14):
        y0 = 4.0 + 2.6 * k; x0 = rnd.uniform(-2.2, 2.2); z0 = rnd.uniform(-2.0, 2.0)
        rc, sk = red_cell(f'RBC{k}', (x0, y0, z0), r=1.0, seed=k); rc.rotation_euler = (rnd.uniform(0, 1.2), rnd.uniform(0, 1.2), 0)
        move(rc, rfps, [(0.0, (x0, y0, z0)), (dur, (x0 + rnd.uniform(-0.6, 0.6), y0 - 16.0, z0 + rnd.uniform(-0.5, 0.5)))], ease=False)
        kf(rc, 'rotation_euler', 1, tuple(rc.rotation_euler)); kf(rc, 'rotation_euler', nf, tuple(Vector(rc.rotation_euler) + Vector((0.6, 0.4, 0.8)) * rnd.uniform(0.5, 1.0))); kf_lin(rc)
        t_s = T(445.6) + 0.28 * k; key_shape(sk, F(t_s, rfps), 0.0); key_shape(sk, F(t_s + 1.6, rfps), 1.0); ease_id(rc.data.shape_keys)
        cells.append(rc)
    anchor('RBC', (0, -0.6, 1.2), cells[2]); anchor('Sickle', (0, -0.6, 1.2), cells[5])
    pulse(cells[0].data.materials[0], rfps, T(451.0), RBC, peak=1.2, fall=1.4)
    for k in range(40):
        p = (rnd.uniform(-3, 3), rnd.uniform(0, 30), rnd.uniform(-3, 3)); pl = sphere(f'Plate{k}', 0.12, p, seg=16, ring=8, mat=M('platelet', lambda: mat_gloss((0.95, 0.85, 0.7), rough=0.4, name='platelet')), scale=(1, 1, 0.4))
        move(pl, rfps, [(0.0, p), (dur, (p[0], p[1] - 14.0, p[2]))], ease=False)
    cam, tgt = cam_path([(0.0, (-1.0, -6.0, 0.8), (-2.0, 0, 1.2)), (T(445.6), (0.4, -3.0, 0.6), (0.2, 8, 0.3)), (T(450.5), (0.6, 2.0, 0.5), (0, 14, 0.2)), (dur, (0.2, 5.0, 0.8), (0, 18, 0))], rfps, lens=38)
    env_kit(6, cam, rnd, rfps, dur, center=(0, 8, 0), dust_n=160, dust_spread=(3, 18, 3), halo_r=9.0, halo_at=(0, 34, 0), bokeh=3, halo_strength=0.6)
    fog_cards(6, 10.0, 38.0, color=(0.10, 0.01, 0.015), alpha=0.09, size=30)

def one_base_pair(nf, rfps, dur):
    """s48 454.32-459.46: back to the hero helix: the camera pushes in from the whole molecule to a single base pair, which
    stays lit while everything around it dims (RpPair): 'how precise the sequence is'.  The helix keeps turning."""
    reset(); rnd = random.Random(48); T = lambda t: rt('s48', t); helix_lights(target=(0, 0, 0), key_e=2400, sec=6)
    K = 11; ph = math.pi / 2 - K * (2 * math.pi / 10)                                            # pair K vertical, face-on to the camera
    h = Helix('DNA', HERO_SEQ[:24], loc=(0, 0, 0), individual=True, hd=True, phase=ph)
    c = h.axis_pt(K); sl = halo('PairGlow', tuple(c + Vector((0, 1.7, 0))), 1.05, THEMES[6]['accent'], strength=0.8, alpha=0.6); parent(sl, h.root); hide_until(sl, F(T(456.0), rfps))   # a soft spot of light right behind the hero rung
    spin(h.root, rfps, dur, rate=0.02, start=-0.32)
    for s_ in (0, 1):
        pl = [o for o in h.unit_objs(K, s_) if o.name.startswith('DNA_r')][0]; pulse(own_mat(pl), rfps, T(456.3), BASE[h.base_of(K, s_)], peak=2.4, fall=2.0)
    anchor('Pair', c + Vector((0, -0.4, 1.5)), h.root)
    L = light('POINT', tuple(c + Vector((0.3, -1.4, 0.8))), 0, THEMES[6]['accent'], 'PairLight'); parent(L, h.root); key_light(L, F(T(455.8), rfps), 0.0); key_light(L, F(T(456.6), rfps), 90.0)
    key = bpy.data.objects.get('Key')
    if key: key_light(key, F(T(455.8), rfps), 2400); key_light(key, F(T(457.4), rfps), 1100)
    cam, tgt = cam_path([(0.0, (-3.0, -10.5, 1.8), (0, 0, 0)), (T(456.0), tuple(c + Vector((-1.2, -6.4, 1.0))), tuple(c + Vector((0, 0, 0.05)))), (dur, tuple(c + Vector((0.5, -4.4, 0.6))), tuple(c + Vector((0, 0, 0.0))))], rfps, lens=45)
    lens_zoom(cam, rfps, [(0.0, 45), (dur, 52)])
    if os.environ.get('VL_DOF', '0') == '1': rack_focus(cam, F(T(455.0), rfps), F(T(457.0), rfps), h.root, h.units[(K, 0)])
    helix_hero_env(6, cam, rnd, rfps, dur, center=tuple(c), helices=3, halo_r=1.3, halo_back=10.0, halo_alpha=0.3, halo_strength=0.5)

def central_dogma(nf, rfps, dur):
    """s49 459.46-469.76: three stations in a row, each at hero scale: a standing HD DNA helix (RpDNA), a standing mRNA
    strand with its plate bases (RpRNA), and a ribosome reading a message with a chain of amino acids rising out of its
    exit tunnel into the folded protein above it (RpProt); on 'DNA to RNA' a beam of light runs from the first to the
    second (RpArrow1), on 'RNA to protein' from the second to the third (RpArrow2); every station turns while the camera
    dollies past them close, then eases back to hold all three in the middle band for 'the central dogma'."""
    reset(); rnd = random.Random(49); T = lambda t: rt('s49', t)
    theme_lights(6, target=(0, 0, 0.5), key=(4.0, -10.0, 9.0), key_e=4400, spot=75, fill_e=320, rim_e=640, accent_e=360, accent_pos=(-7, 5, -3))
    # station 1: DNA
    st1 = empty('DNAStand', (-6.3, 0, 0.3)); st1.rotation_euler = (0, -math.pi / 2, 0); h = Helix('DNA', HERO_SEQ[:14], loc=(0, 0, 0), individual=False, hd=True); parent(h.root, st1)
    h.root.scale = (1.15, 1.15, 1.15); spin(h.root, rfps, dur, rate=0.05, axis=0); anchor('DNA', (-6.3, -1.6, 3.9))
    # station 2: mRNA
    st2 = empty('RNAStand', (0.0, 0, 0.3)); st2.rotation_euler = (0, -math.pi / 2, 0); r = RNA('mRNA', MRNA_SEQ[:12], loc=(0, 0, 0), side=(0, 0, 1), rise=0.44, hd=True); parent(r.root, st2)
    r.root.scale = (1.25, 1.25, 1.25); spin(r.root, rfps, dur, rate=0.06, axis=0); anchor('RNA', (0, -1.4, 3.8))
    # station 3: ribosome reading a message, the chain rising from its tunnel into the folded protein
    rb, L, S, st = ribosome('Ribo', (5.6, 0.2, -1.5), s=0.95, translucent_large=False, sites=False); kf(rb, 'rotation_euler', 1, (0.04, 0, -0.35)); kf(rb, 'rotation_euler', nf, (-0.03, 0, -0.05)); kf_lin(rb)
    r2 = RNA('mRNA2', MRNA_SEQ[:12], loc=(5.6, 0.2, -1.5 - 0.55), side=(0, 0, 1), rise=0.4, hd=True); parent(r2.root, rb); move(r2.root, rfps, [(0.0, (0.7, 0, -0.55)), (dur, (-0.8, 0, -0.55))], ease=False)
    tun_top = Vector((5.6 - 0.3 * 0.95, 0.3, -1.5 + 0.275 + 3.15 * 0.95))
    ch = Chain('Chain', ['Met', 'Pro', 'Gly', 'Pro', 'Ala', 'Trp', 'Ser', 'Lys'], r=0.25, r_link=0.08, hd=True)
    def pos(k, t): return tun_top + Vector((0.42 * k + 0.12 * math.sin(1.7 * k + 0.25 * t), -0.12 * k, 0.95 * math.sin(math.pi * k / 8.5) + 0.10 * math.sin(0.8 * t + k)))   # an arc from the exit tunnel over to the folding globule
    ch.animate(pos, rfps, 0.0, dur, step=2, ups=[Vector((0, -1, 0.3))] * 8)
    for k in range(8):
        for o in [ch.beads[k]] + list(ch.beads[k].children): hide_until_safe(o, F(T(459.5 + 0.7 * k), rfps))
        if k: hide_until_safe(ch.links[k - 1], F(T(459.5 + 0.7 * k), rfps))
    chp = Chain('Prot', ['Met', 'Gly', 'Pro', 'Ala', 'Leu', 'Ser', 'Lys', 'Val', 'Glu', 'Phe', 'Thr', 'Asp', 'Trp', 'His'], r=0.30, r_link=0.09, hd=True)
    fp = fold_path(14, seed=6, box=1.05, step=0.58); chp.pose([tuple(p) for p in fp], 1, ups=[Vector((0, -1, 0.4))] * 14)
    prot = empty('ProtRoot', (8.3, -0.4, 2.0))
    for o in chp.objects(): parent(o, prot)
    spin(prot, rfps, dur, rate=0.08, axis=2); anchor('Prot', (0, -1.2, 2.2), prot)
    hl = halo('ProtHalo', (8.3, 6.0, 2.0), 2.2, THEMES[6]['accent'], strength=0.4, alpha=0.35)
    for nm, p0, p1, t_on in (('Arrow1', (-4.7, 0, 0.6), (-1.5, 0, 0.6), 460.6), ('Arrow2', (1.5, 0, 0.6), (3.4, 0, 0.6), 462.3)):
        b = beam(nm, p0, p1, r=0.08, color=THEMES[6]['accent'], strength=2.2, f_on=F(T(t_on), rfps), alpha=0.5)
        ar = arrow3d(nm + 'Head', p1, Vector(p1) - Vector(p0), L=0.8, r=0.07, color=THEMES[6]['accent'], strength=2.6); hide_until(ar, F(T(t_on + 0.5), rfps))
        anchor(nm, tuple((Vector(p0) + Vector(p1)) / 2 + Vector((0, -0.3, 0.9))))
        for tp in (464.4, 466.2, 468.0): pulse(b.data.materials[0], rfps, T(tp), THEMES[6]['accent'], peak=4.0, base=1.6, fall=0.8)
    for k, (x, col) in enumerate(((-6.3, THEMES[1]['accent']), (0.0, RNA_RAIL), (6.4, THEMES[5]['accent']))): halo(f'Halo{k}', (x, 6.0, 0.8), 3.4, col, strength=0.35, alpha=0.35)
    rb2, L2, S2, st_ = ribosome('FarRibo', (2.5, 10.0, -2.8), s=1.0, translucent_large=False, sites=False); drift(rb2, rfps, dur, amp=0.15, seed=2, period=6)
    pol = polymerase('FarPol', (-9.5, 9.5, 3.2), s=1.0); drift(pol, rfps, dur, amp=0.15, seed=3, period=6)
    cam, tgt = cam_path([(0.0, (-7.6, -11.8, 1.6), (-5.9, 0, 0.6)), (T(462.3), (-0.6, -12.2, 1.4), (-0.2, 0, 0.7)), (T(465.0), (5.6, -12.6, 2.0), (6.2, 0, 1.1)), (dur, (1.4, -17.5, 2.9), (1.2, 0, 0.7))], rfps, lens=40)
    lens_zoom(cam, rfps, [(0.0, 40), (T(465.0), 40), (dur, 35)])
    env_kit(6, cam, rnd, rfps, dur, center=(0, 0, 0.5), dust_n=190, dust_spread=(20, 12, 9), halo_r=0.0, bokeh=4, fil=3, helices=2)

# ================================================================= builders: outro recap
def recap_helix(nf, rfps, dur):
    """s50 469.76-477.09: the hero helix again in a slow orbit; the four base colours pulse in turn on 'four letters' and the
    rails glow on 'double helix'."""
    reset(); rnd = random.Random(50); T = lambda t: rt('s50', t); helix_lights(target=(0, 0, 0), key_e=2600, sec=0)
    h = Helix('DNA', HERO_SEQ[:44], loc=(0, 0, 0), rot=(0, 0, 0), individual=False, hd=True); spin(h.root, rfps, dur, rate=0.05)
    for k, b in enumerate('ATGC'): pulse(m_base(b), rfps, T(472.6 + 0.3 * k), BASE[b], peak=2.2, fall=1.2)
    for s_ in (0, 1): pulse(m_rail(s_), rfps, T(475.6), (0.8, 0.9, 1.0), peak=2.0, fall=1.4)
    cam, tgt = camera((-3.0, -10.5, 1.8), (0, 0, 0), lens=45); orbit(cam, tgt, (0, 0, 0), 11.0, 1.8, -26, 22, 1, nf)
    lens_zoom(cam, rfps, [(0.0, 45), (dur, 50)])
    helix_hero_env(0, cam, rnd, rfps, dur, helices=3)

def recap_dogma(nf, rfps, dur):
    """s51 477.09-490.71: the whole dogma set in one wide orbit, every station at hero scale: the gene helix (angled back
    into the void) with its polymerase (RpTx), the messenger strand rising from it (RpMRNA), the ribosome reading it with a
    chain growing out of its tunnel (RpTl, RpRibo, RpChain) and the folded protein (RpProt); each pulses as it is named."""
    reset(); rnd = random.Random(51); T = lambda t: rt('s51', t)
    theme_lights(0, target=(0.8, 0, 0.8), key=(4.0, -11.0, 10.0), key_e=4800, spot=80, fill_e=340, rim_e=680, accent_e=380, accent_pos=(-8, 5, -3))
    h = Helix('DNA', HERO_SEQ[:22], loc=(-5.6, 1.2, 0.1), rot=(0, 0, -0.35), individual=False, hd=True); h.root.scale = (1.15, 1.15, 1.15)
    kf(h.root, 'rotation_euler', 1, (0, 0, -0.35)); kf(h.root, 'rotation_euler', nf, (2 * math.pi * 0.03 * dur, 0, -0.35)); kf_lin(h.root)
    gene = glow_sleeve('GeneGlow', h.axis_pt(7) - X * 0.2, h.axis_pt(17) + X * 0.2, 1.32, GENE, strength=0.5, alpha=0.07); parent(gene, h.root)
    pol = polymerase('Pol', loc=tuple(h.axis_pt(12)), s=1.15); parent(pol, h.root); jaws(pol, rfps, [(0.0, 0.0)]); anchor('Tx', (0, -1.2, 3.0), pol)
    pulse(gene.data.materials[0], rfps, T(477.6), GENE, peak=2.6, base=0.6, fall=1.4); pulse(pol.children[0].data.materials[0], rfps, T(478.0), POL_2, peak=1.4, fall=1.2)
    r = RNA('mRNA', MRNA_SEQ[:15], loc=(-2.3, -0.4, 2.9), rot=(0.4, 0, 0.25), side=(0, 0, 1), rise=0.42, hd=True); r.root.scale = (1.2, 1.2, 1.2); drift(r.root, rfps, dur, amp=0.15, seed=2, period=5); anchor('MRNA', (0, -0.6, 1.1), r.root)
    pulse(m_rna_rail(), rfps, T(480.0), RNA_RAIL, peak=2.4, fall=1.4)
    rb, L, S, st = ribosome('Ribo', (3.2, 0, -0.7), s=1.1, translucent_large=False, sites=False); kf(rb, 'rotation_euler', 1, (0, 0, -0.1)); kf(rb, 'rotation_euler', nf, (0.05, 0, 0.15)); kf_lin(rb)
    L.location.z -= 0.9; S.location.z += 0.35                                                  # close the cleft on the message (as the translation rig does)
    r2 = RNA('mRNA2', MRNA_SEQ, loc=(3.2, 0, -0.7 - 0.55), side=(0, 0, 1), rise=0.4, hd=True); parent(r2.root, rb)
    move(r2.root, rfps, [(0.0, (0.8, 0, -0.55)), (dur, (-1.2, 0, -0.55))], ease=False)
    anchor('Tl', (-2.6, -1.8, 2.8), rb); anchor('Ribo', (0.8, -1.8, -2.8), rb)
    RL = light('POINT', (3.2, -3.8, 2.2), 0, THEMES[5]['accent'], 'RiboLight'); key_light(RL, F(T(481.6), rfps), 0.0); key_light(RL, F(T(482.2), rfps), 550.0); key_light(RL, F(T(484.8), rfps), 550.0); key_light(RL, F(T(486.0), rfps), 60.0); ease_id(RL.data)
    ch = Chain('Chain', ['Met', 'Pro', 'Gly', 'Pro', 'Ala', 'Trp', 'Ser', 'Lys'], r=0.27, r_link=0.09, hd=True)
    top = Vector((3.2 - 0.33, -0.4, -0.7 - 0.9 + 0.275 + 3.15 * 1.1))
    def pos(k, t): return top + Vector((0.46 * k + 0.12 * math.sin(1.9 * k + 0.3 * t), -0.2 * k, 0.9 * math.sin(math.pi * k / 8.5) + 0.1 * math.sin(0.7 * t + k)))   # an arc from the exit tunnel toward the folding protein
    ch.animate(pos, rfps, 0.0, dur, step=2, ups=[Vector((0, -1, 0.3))] * 8)
    for k in range(8):
        for o in [ch.beads[k]] + list(ch.beads[k].children): hide_until_safe(o, F(T(477.1 + 1.0 * k), rfps))
        if k: hide_until_safe(ch.links[k - 1], F(T(477.1 + 1.0 * k), rfps))
    a = anchor('Chain', (0, -0.4, 0.5)); a.parent = ch.beads[3]; a.matrix_parent_inverse = Matrix.Identity(4)
    for k in range(8): pulse(own_mat(bpy.data.objects[ch.beads[k]['bead']]), rfps, T(485.8 + 0.1 * k), AMINO[ch.aminos[k]], peak=2.2, fall=1.2)
    chp = Chain('Prot', ['Met', 'Gly', 'Pro', 'Ala', 'Leu', 'Ser', 'Lys', 'Val', 'Glu', 'Phe', 'Thr', 'Asp', 'Trp', 'His'], r=0.32, r_link=0.09, hd=True)
    fp = fold_path(14, seed=6, box=1.1, step=0.6); chp.pose([tuple(p) for p in fp], 1, ups=[Vector((0, -1, 0.4))] * 14)
    prot = empty('ProtRoot', (6.6, -1.0, 2.8))
    for o in chp.objects(): parent(o, prot)
    spin(prot, rfps, dur, rate=0.08, axis=2); anchor('Prot', (0, -1.2, 2.4), prot); scale_in(prot, rfps, T(487.6), dur=0.8)
    hl = halo('ProtHalo', (6.6, 5.0, 2.8), 2.4, THEMES[6]['accent'], strength=0.45, alpha=0.35); scale_in(hl, rfps, T(487.6), dur=0.8)
    for nm, p0, p1, t_on in (('Beam1', (-4.2, 0.4, 1.4), (-3.0, 0, 2.3), 479.4), ('Beam2', (0.2, -0.2, 2.6), (1.4, 0, 0.9), 481.6), ('Beam3', (5.0, -0.4, 1.7), (5.6, -0.8, 2.3), 487.4)):
        beam(nm, p0, p1, r=0.06, color=THEMES[0]['accent'], strength=1.8, f_on=F(T(t_on), rfps), alpha=0.4)
    cam, tgt = camera((-6.0, -13.5, 3.2), (0.8, 0, 1.3), lens=40); orbit(cam, tgt, (0.8, 0, 1.3), 14.0, 3.2, -30, 8, 1, nf)
    lens_zoom(cam, rfps, [(0.0, 40), (dur, 32)])
    env_kit(0, cam, rnd, rfps, dur, center=(0.8, 0, 0.5), dust_n=200, dust_spread=(22, 14, 10), halo_r=0.0, bokeh=5, helices=2, fil=3)
