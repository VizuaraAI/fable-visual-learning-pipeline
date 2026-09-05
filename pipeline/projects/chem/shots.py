"""Blender builders for every 3D shot of the chem chapter -- cinematic v2.
Each builder(nf, rfps, dur) sets up scene + animation for frames 1..nf.
Coordinates: camera sits at -Y looking +Y, Z up. Units ~ decimetres-ish (candle height 2.6).

Shot ids, timings, builder names, camera framing and the overlay timeline were validated against the reference and
are unchanged. What changed: every prop is remodelled with real depth (lathed vessels with rolled rims and wall
thickness, subsurface wax with a melted rim and drips, a real spirit lamp, crucible tongs with jaws and finger loops,
a retort stand with boss head and clamp jaws, a drilled wooden rack, nails with heads and points, flaking rust, a gauze
with a ceramic centre, a gritty sandpaper, a sponge cake that grows mould, a smoother mannequin), the materials use the
v2 kit helpers (mat_glass_real + solidify, mat_liquid_real + meniscus, flame_volume, smoke_wisp, floor_wood_pbr) and
every scene gets hdri() reflections, atmosphere() and a subtle second rim light.  EEVEE (local tests) falls back to
alpha glass and the mesh flame through the kit helpers; Cycles is the target."""
import math, random, bpy, os, sys, bmesh
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from mathutils import Vector
from kit import *
from kit import _principled, _inp, _resample_profile

def F(sec, rfps): return int(round(sec * rfps)) + 1     # seconds -> frame number (1-based)
def CYC(): return is_cycles()
DOF = os.environ.get('VL_DOF', '0') == '1'

# ================================================================== materials
def _nodes(m): return m.node_tree, m.node_tree.nodes

def _noise(n, scale=8.0, detail=4.0, rough=0.5, dist=0.0):
    t = n.new('ShaderNodeTexNoise'); t.inputs['Scale'].default_value = scale; t.inputs['Detail'].default_value = detail
    t.inputs['Roughness'].default_value = rough
    try: t.inputs['Distortion'].default_value = dist
    except Exception: pass
    return t

def _ramp(n, stops):
    r = n.new('ShaderNodeValToRGB'); cr = r.color_ramp
    while len(cr.elements) > 1: cr.elements.remove(cr.elements[-1])
    cr.elements[0].position = stops[0][0]; cr.elements[0].color = stops[0][1]
    for pos, col in stops[1:]:
        e = cr.elements.new(pos); e.color = col
    return r

def _bump(nt, n, height, p, strength=0.3, distance=0.02):
    b = n.new('ShaderNodeBump'); b.inputs['Strength'].default_value = strength; b.inputs['Distance'].default_value = distance
    nt.links.new(height, b.inputs['Height']); nt.links.new(b.outputs['Normal'], p.inputs['Normal']); return b

def _blend(m):
    for attr, val in [('surface_render_method', 'BLENDED'), ('blend_method', 'BLEND'), ('show_transparent_back', True), ('use_transparency_overlap', True)]:
        try: setattr(m, attr, val)
        except Exception: pass
    try: m.shadow_method = 'NONE'
    except Exception: pass

def M_glass(tint=(0.92, 0.97, 1.0), rough=0.02, name='glass', ior=1.5):
    """Real refractive glass (Cycles) / alpha glass (EEVEE) via the kit."""
    return mat_glass_real(tint=tint, ior=ior, rough=rough, name=name)

def M_water(name='water'): return mat_glass_real(tint=(0.85, 0.94, 1.0), ior=1.33, rough=0.03, name=name)

def M_liquid(color, absorb=3.0, scatter=0.6, name='liquid'):
    """Kit liquid (transmission + absorption) plus a little in-scattering so the colour reads against the dark void."""
    m = mat_liquid_real(color=color, absorption=absorb, name=name)
    if not CYC(): return m
    nt, n = _nodes(m); out = n.get('Material Output')
    ab = next((x for x in n if x.bl_idname == 'ShaderNodeVolumeAbsorption'), None)
    if ab is None: return m
    sc_ = n.new('ShaderNodeVolumeScatter'); sc_.inputs['Color'].default_value = (*color, 1); sc_.inputs['Density'].default_value = scatter; sc_.inputs['Anisotropy'].default_value = 0.4
    add = n.new('ShaderNodeAddShader'); nt.links.new(ab.outputs['Volume'], add.inputs[0]); nt.links.new(sc_.outputs['Volume'], add.inputs[1]); nt.links.new(add.outputs['Shader'], out.inputs['Volume'])
    return m

def key_liquid_color(m, frame, color):
    """Keyframe the perceived colour of a liquid: the volume colours (Cycles) or the base colour (EEVEE)."""
    for nd in m.node_tree.nodes:
        if nd.bl_idname in ('ShaderNodeVolumeAbsorption', 'ShaderNodeVolumeScatter'): s = nd.inputs['Color']
        elif nd.bl_idname == 'ShaderNodeBsdfPrincipled' and not CYC(): s = nd.inputs['Base Color']
        else: continue
        s.default_value = (*color, 1); s.keyframe_insert('default_value', frame=frame)

def M_milk(color=(0.96, 0.96, 0.95), name='milk'):
    """Dense white precipitate: waxy subsurface paste."""
    m, p = _principled(name)
    _inp(p, 'Base Color', (*color, 1)); _inp(p, 'Roughness', 0.55); _inp(p, 'Subsurface Weight', 0.8 if CYC() else 0.3); _inp(p, 'Subsurface Radius', (0.3, 0.3, 0.3)); _inp(p, 'Subsurface Scale', 0.08)
    return m

def M_wax(name='wax', color=(0.93, 0.90, 0.84)):
    m, p = _principled(name); nt, n = _nodes(m)
    _inp(p, 'Base Color', (*color, 1)); _inp(p, 'Roughness', 0.32); _inp(p, 'Subsurface Weight', 0.75 if CYC() else 0.4)
    _inp(p, 'Subsurface Radius', (0.5, 0.35, 0.2)); _inp(p, 'Subsurface Scale', 0.18); _inp(p, 'Coat Weight', 0.15); _inp(p, 'Coat Roughness', 0.25)
    nz = _noise(n, 9.0, 5, 0.55); r = _ramp(n, [(0.3, (0.26, 0.26, 0.26, 1)), (0.7, (0.42, 0.42, 0.42, 1))])
    nt.links.new(nz.outputs['Fac'], r.inputs['Fac']); nt.links.new(r.outputs['Color'], p.inputs['Roughness'])
    _bump(nt, n, nz.outputs['Fac'], p, 0.08, 0.01)
    return m

def M_liquid_wax(name='meltwax'):
    m, p = _principled(name)
    _inp(p, 'Base Color', (0.96, 0.92, 0.82, 1)); _inp(p, 'Roughness', 0.05); _inp(p, 'Coat Weight', 1.0); _inp(p, 'Subsurface Weight', 0.5 if CYC() else 0.2); _inp(p, 'Subsurface Scale', 0.1)
    if CYC(): _inp(p, 'Transmission Weight', 0.25)
    return m

def M_metal(color=(0.8, 0.8, 0.83), rough=0.3, name='metal', aniso=0.35, radial=True):
    """Brushed metal: anisotropic highlights (radial tangents for lathed parts) and a fine roughness variation."""
    m = mat_metal(color, rough=rough, name=name); nt, n = _nodes(m); p = n['Principled BSDF']
    _inp(p, 'Anisotropic', aniso)
    if aniso and radial:
        try:
            tg = n.new('ShaderNodeTangent'); tg.direction_type = 'RADIAL'; tg.axis = 'Z'; nt.links.new(tg.outputs['Tangent'], p.inputs['Tangent'])
        except Exception: pass
    nz = _noise(n, 30, 3, 0.5); r = _ramp(n, [(0.35, (rough * 0.8,) * 3 + (1,)), (0.75, (min(1.0, rough * 1.35),) * 3 + (1,))])
    nt.links.new(nz.outputs['Fac'], r.inputs['Fac']); nt.links.new(r.outputs['Color'], p.inputs['Roughness'])
    return m

def M_rust(name='rust'):
    m, p = _principled(name); nt, n = _nodes(m)
    n1 = _noise(n, 22, 8, 0.6); n2 = _noise(n, 6, 4, 0.5, 1.5)
    add = n.new('ShaderNodeMath'); add.operation = 'ADD'; nt.links.new(n1.outputs['Fac'], add.inputs[0]); nt.links.new(n2.outputs['Fac'], add.inputs[1])
    half = n.new('ShaderNodeMath'); half.operation = 'MULTIPLY'; half.inputs[1].default_value = 0.5; nt.links.new(add.outputs[0], half.inputs[0])
    r = _ramp(n, [(0.2, (0.14, 0.05, 0.02, 1)), (0.5, (0.42, 0.17, 0.05, 1)), (0.8, (0.72, 0.36, 0.13, 1))])
    nt.links.new(half.outputs[0], r.inputs['Fac']); nt.links.new(r.outputs['Color'], p.inputs['Base Color'])
    _inp(p, 'Roughness', 0.88); _inp(p, 'Metallic', 0.05); _inp(p, 'Specular IOR Level', 0.3)
    _bump(nt, n, n1.outputs['Fac'], p, 0.7, 0.02)
    return m

def M_steel_rust(name='steelrust', steel=(0.8, 0.8, 0.83)):
    """Steel that rusts in patches: returns (material, value node); keyframe node.outputs[0].default_value 0 -> 1."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt, n = _nodes(m)
    for nd in list(n): n.remove(nd)
    out = n.new('ShaderNodeOutputMaterial'); mix = n.new('ShaderNodeMixShader')
    pm = n.new('ShaderNodeBsdfPrincipled'); _inp(pm, 'Base Color', (*steel, 1)); _inp(pm, 'Metallic', 1.0); _inp(pm, 'Roughness', 0.32); _inp(pm, 'Anisotropic', 0.3)
    pr = n.new('ShaderNodeBsdfPrincipled'); _inp(pr, 'Roughness', 0.88); _inp(pr, 'Metallic', 0.05); _inp(pr, 'Specular IOR Level', 0.3)
    n1 = _noise(n, 22, 8, 0.6); n2 = _noise(n, 5, 4, 0.5, 1.2)
    ramp = _ramp(n, [(0.2, (0.16, 0.05, 0.02, 1)), (0.5, (0.45, 0.18, 0.05, 1)), (0.85, (0.75, 0.38, 0.14, 1))])
    nt.links.new(n1.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], pr.inputs['Base Color'])
    bump = n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.6; bump.inputs['Distance'].default_value = 0.02
    nt.links.new(n1.outputs['Fac'], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], pr.inputs['Normal'])
    fac = n.new('ShaderNodeValue'); fac.name = 'RustFac'; fac.outputs[0].default_value = 0.0
    m1 = n.new('ShaderNodeMath'); m1.operation = 'MULTIPLY_ADD'; m1.inputs[1].default_value = 1.8; nt.links.new(fac.outputs[0], m1.inputs[0]); nt.links.new(n2.outputs['Fac'], m1.inputs[2])
    m2 = n.new('ShaderNodeMath'); m2.operation = 'SUBTRACT'; m2.inputs[1].default_value = 1.0; nt.links.new(m1.outputs[0], m2.inputs[0])
    m3 = n.new('ShaderNodeMath'); m3.operation = 'MULTIPLY'; m3.inputs[1].default_value = 4.0; m3.use_clamp = True; nt.links.new(m2.outputs[0], m3.inputs[0])
    nt.links.new(m3.outputs[0], mix.inputs['Fac']); nt.links.new(pm.outputs['BSDF'], mix.inputs[1]); nt.links.new(pr.outputs['BSDF'], mix.inputs[2]); nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])
    return m, fac

def key_rust(fac, frame, value):
    fac.outputs[0].default_value = value; fac.outputs[0].keyframe_insert('default_value', frame=frame)

def M_wood(name='woodfine', c1=(0.50, 0.29, 0.12), c2=(0.70, 0.45, 0.22), scale=3.0, rough=0.42):
    """Fine procedural plank wood: distorted bands stretched along X, warm two-tone ramp, gentle bump, light varnish."""
    m, p = _principled(name); nt, n = _nodes(m)
    tc = n.new('ShaderNodeTexCoord'); mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.35 * scale, 1.0 * scale, 0.7 * scale)
    wave = n.new('ShaderNodeTexWave'); wave.wave_type = 'BANDS'; wave.bands_direction = 'Y'
    for nm, v in (('Scale', 4.0), ('Distortion', 3.5), ('Detail', 3.0), ('Detail Scale', 1.5)):
        try: wave.inputs[nm].default_value = v
        except Exception: pass
    ramp = _ramp(n, [(0.15, (*c1, 1)), (0.85, (*c2, 1))])
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], wave.inputs['Vector']); nt.links.new(wave.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], p.inputs['Base Color'])
    _inp(p, 'Roughness', rough); _inp(p, 'Coat Weight', 0.2); _inp(p, 'Coat Roughness', 0.3)
    _bump(nt, n, wave.outputs['Fac'], p, 0.12, 0.01)
    return m

def M_holo(color=(1.0, 0.1, 0.04), name='holo', alpha=0.32, strength=2.2):
    """Translucent red hologram body: brighter and more opaque at grazing angles (fresnel), soft in the middle."""
    m, p = _principled(name); nt, n = _nodes(m)
    _inp(p, 'Base Color', (color[0] * 0.4, color[1] * 0.4, color[2] * 0.4, 1)); _inp(p, 'Emission Color', (*color, 1)); _inp(p, 'Roughness', 0.3); _inp(p, 'Coat Weight', 0.4)
    lw = n.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.45
    mr = n.new('ShaderNodeMapRange'); mr.inputs['To Min'].default_value = strength * 0.5; mr.inputs['To Max'].default_value = strength * 2.4
    nt.links.new(lw.outputs['Fresnel'], mr.inputs['Value']); nt.links.new(mr.outputs['Result'], p.inputs['Emission Strength'])
    ma = n.new('ShaderNodeMapRange'); ma.inputs['To Min'].default_value = alpha; ma.inputs['To Max'].default_value = min(1.0, alpha * 2.6)
    nt.links.new(lw.outputs['Fresnel'], ma.inputs['Value']); nt.links.new(ma.outputs['Result'], p.inputs['Alpha'])
    _blend(m)
    try: m.show_transparent_back = False
    except Exception: pass
    return m

def M_sandpaper(name='sandpaper'):
    m, p = _principled(name); nt, n = _nodes(m)
    tc = n.new('ShaderNodeTexCoord'); vor = n.new('ShaderNodeTexVoronoi'); vor.feature = 'F1'; vor.inputs['Scale'].default_value = 140
    nz = _noise(n, 3.0, 3, 0.5)
    ramp = _ramp(n, [(0.0, (0.5, 0.25, 0.07, 1)), (1.0, (0.85, 0.5, 0.2, 1))])
    nt.links.new(tc.outputs['Object'], vor.inputs['Vector']); nt.links.new(tc.outputs['Object'], nz.inputs['Vector']); nt.links.new(nz.outputs['Fac'], ramp.inputs['Fac'])
    mix = n.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 0.45
    nt.links.new(ramp.outputs['Color'], mix.inputs[6]); nt.links.new(vor.outputs['Distance'], mix.inputs[7]); nt.links.new(mix.outputs[2], p.inputs['Base Color'])
    _inp(p, 'Roughness', 0.95); _inp(p, 'Specular IOR Level', 0.25)
    _bump(nt, n, vor.outputs['Distance'], p, 0.9, 0.01)
    return m

def M_cake(name='cake', col=(0.86, 0.70, 0.14)):
    m, p = _principled(name); nt, n = _nodes(m)
    tc = n.new('ShaderNodeTexCoord'); n1 = _noise(n, 25, 6, 0.6); n2 = _noise(n, 4, 3, 0.5, 0.6)
    ramp = _ramp(n, [(0.3, (col[0] * 0.7, col[1] * 0.62, col[2] * 0.5, 1)), (0.7, (*col, 1))])
    nt.links.new(tc.outputs['Object'], n1.inputs['Vector']); nt.links.new(tc.outputs['Object'], n2.inputs['Vector'])
    nt.links.new(n2.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], p.inputs['Base Color'])
    _inp(p, 'Roughness', 0.62); _inp(p, 'Subsurface Weight', 0.35 if CYC() else 0.2); _inp(p, 'Subsurface Radius', (0.6, 0.35, 0.1)); _inp(p, 'Subsurface Scale', 0.12); _inp(p, 'Specular IOR Level', 0.3)
    _bump(nt, n, n1.outputs['Fac'], p, 0.45, 0.015)
    return m

def M_ceramic(color=(0.6, 0.6, 0.62), rough=0.15, name='ceramic', coat=0.6):
    m, p = _principled(name)
    _inp(p, 'Base Color', (*color, 1)); _inp(p, 'Roughness', rough); _inp(p, 'Coat Weight', coat); _inp(p, 'Subsurface Weight', 0.1 if CYC() else 0.0); _inp(p, 'Subsurface Scale', 0.05)
    return m

def M_rough_ceramic(color=(0.86, 0.83, 0.76), name='ceramic_rough'):
    m, p = _principled(name); nt, n = _nodes(m)
    nz = _noise(n, 40, 5, 0.6); _inp(p, 'Base Color', (*color, 1)); _inp(p, 'Roughness', 0.8); _inp(p, 'Specular IOR Level', 0.3)
    _bump(nt, n, nz.outputs['Fac'], p, 0.35, 0.01); return m

def M_ice(name='ice'):
    if not CYC(): return mat_glass((0.6, 0.78, 0.95), alpha=0.55, rough=0.2, name=name)
    m, p = _principled(name); nt, n = _nodes(m)
    _inp(p, 'Base Color', (0.9, 0.96, 1.0, 1)); _inp(p, 'Roughness', 0.1); _inp(p, 'IOR', 1.31); _inp(p, 'Transmission Weight', 1.0)
    nz = _noise(n, 6, 4, 0.5); rr = _ramp(n, [(0.3, (0.04,) * 3 + (1,)), (0.7, (0.25,) * 3 + (1,))]); nt.links.new(nz.outputs['Fac'], rr.inputs['Fac']); nt.links.new(rr.outputs['Color'], p.inputs['Roughness'])
    _bump(nt, n, nz.outputs['Fac'], p, 0.15, 0.03)
    ab = n.new('ShaderNodeVolumeAbsorption'); ab.inputs['Color'].default_value = (0.75, 0.88, 1.0, 1); ab.inputs['Density'].default_value = 0.35
    sc_ = n.new('ShaderNodeVolumeScatter'); sc_.inputs['Density'].default_value = 0.12; add = n.new('ShaderNodeAddShader')
    nt.links.new(ab.outputs['Volume'], add.inputs[0]); nt.links.new(sc_.outputs['Volume'], add.inputs[1]); nt.links.new(add.outputs['Shader'], n['Material Output'].inputs['Volume'])
    return m

def M_water_film(name='waterfilm'):
    m, p = _principled(name)
    _inp(p, 'Base Color', (0.6, 0.75, 0.9, 1)); _inp(p, 'Roughness', 0.02); _inp(p, 'Coat Weight', 1.0); _inp(p, 'Alpha', 0.35); _blend(m); return m

def M_crystal(color=(0.3, 0.9, 0.25), name='crystal'):
    m, p = _principled(name)
    _inp(p, 'Base Color', (*color, 1)); _inp(p, 'Roughness', 0.22); _inp(p, 'Coat Weight', 0.5)
    if CYC(): _inp(p, 'Transmission Weight', 0.55); _inp(p, 'IOR', 1.45)
    else: _inp(p, 'Subsurface Weight', 0.3)
    return m

def M_powder(color, name='powder', metallic=0.0, rough=0.8):
    m, p = _principled(name)
    _inp(p, 'Base Color', (*color, 1)); _inp(p, 'Roughness', rough); _inp(p, 'Metallic', metallic); _inp(p, 'Specular IOR Level', 0.3)
    return m

def M_mould(name='mould'):
    m, p = _principled(name); nt, n = _nodes(m)
    lw = n.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.6
    ramp = _ramp(n, [(0.0, (0.55, 0.6, 0.45, 1)), (0.45, (0.22, 0.24, 0.12, 1)), (1.0, (0.09, 0.08, 0.05, 1))])
    nt.links.new(lw.outputs['Facing'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], p.inputs['Base Color'])
    _inp(p, 'Roughness', 0.9); _inp(p, 'Specular IOR Level', 0.15); _inp(p, 'Sheen Weight', 0.8)
    return m

def M_leaf(name='leaf'):
    m, p = _principled(name); nt, n = _nodes(m)
    nz = _noise(n, 12, 4, 0.5); ramp = _ramp(n, [(0.3, (0.10, 0.42, 0.08, 1)), (0.7, (0.2, 0.62, 0.14, 1))])
    nt.links.new(nz.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], p.inputs['Base Color'])
    _inp(p, 'Roughness', 0.55); _inp(p, 'Specular IOR Level', 0.2); _inp(p, 'Subsurface Weight', 0.3 if CYC() else 0.15); _inp(p, 'Subsurface Radius', (0.2, 0.5, 0.1)); _inp(p, 'Subsurface Scale', 0.1)
    return m

def M_wick(name='wick'):
    """Cotton wick: pale fibres at the bottom, charred black near the top (Generated z), an ember glow at the tip."""
    m, p = _principled(name); nt, n = _nodes(m)
    tc = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Generated'], sep.inputs['Vector'])
    ramp = _ramp(n, [(0.35, (0.75, 0.7, 0.6, 1)), (0.6, (0.12, 0.1, 0.08, 1)), (1.0, (0.03, 0.02, 0.02, 1))])
    nt.links.new(sep.outputs['Z'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], p.inputs['Base Color'])
    er = _ramp(n, [(0.8, (0, 0, 0, 1)), (1.0, (1.0, 0.35, 0.05, 1))]); nt.links.new(sep.outputs['Z'], er.inputs['Fac']); nt.links.new(er.outputs['Color'], p.inputs['Emission Color'])
    _inp(p, 'Emission Strength', 6.0); _inp(p, 'Roughness', 0.9)
    return m

# ================================================================== geometry helpers
def arc(cx, cz, rad, a0, a1, n):
    """(r, z) points on a circle in the profile plane from angle a0 to a1 (degrees), n segments."""
    return [(cx + rad * math.cos(math.radians(a0 + (a1 - a0) * k / n)), cz + rad * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]

def lathe(name, profile, loc=(0, 0, 0), verts=128, cap_bottom=True, cap_top=False, mat=None):
    """Lathe a dense (r, z) profile (bottom -> top) into a smooth-shaded mesh. r ~ 0 makes a single apex vertex, so
    closed bottoms/tops are clean fans (no degenerate rings). Outward normals as long as the profile runs bottom-up."""
    me = bpy.data.meshes.new(name); o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    bm = bmesh.new(); rings = []
    for (r, z) in profile:
        if r < 1e-5: rings.append(bm.verts.new((0.0, 0.0, z)))
        else: rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / verts), r * math.sin(2 * math.pi * i / verts), z)) for i in range(verts)])
    for a, b in zip(rings[:-1], rings[1:]):
        if isinstance(a, list) and isinstance(b, list):
            for i in range(verts): bm.faces.new((a[i], a[(i + 1) % verts], b[(i + 1) % verts], b[i]))
        elif isinstance(a, list):
            for i in range(verts): bm.faces.new((a[i], a[(i + 1) % verts], b))
        elif isinstance(b, list):
            for i in range(verts): bm.faces.new((a, b[(i + 1) % verts], b[i]))
    try:
        if cap_bottom and isinstance(rings[0], list): bm.faces.new(rings[0][::-1])
        if cap_top and isinstance(rings[-1], list): bm.faces.new(rings[-1])
    except Exception: pass
    bm.to_mesh(me); bm.free(); o.location = loc
    if mat is not None: setmat(o, mat)
    smooth(o)
    return o

def bevel(o, width=0.03, segments=6, angle=None):
    try:
        mod = o.modifiers.new('bevel', 'BEVEL'); mod.width = width; mod.segments = segments
        if angle is not None: mod.limit_method = 'ANGLE'; mod.angle_limit = math.radians(angle)
        return mod
    except Exception: return None

def box(name, dims, loc=(0, 0, 0), mat=None, bev=0.02, seg=4, rot=None):
    """A bevelled box whose MESH is scaled (not the object) so the bevel stays uniform."""
    o = obj_add('cube', name, size=1)
    for v in o.data.vertices: v.co = (v.co.x * dims[0], v.co.y * dims[1], v.co.z * dims[2])
    o.location = loc
    if rot is not None: o.rotation_euler = rot
    if bev: bevel(o, bev, seg)
    smooth(o, auto=True)
    if mat is not None: setmat(o, mat)
    return o

def curve_obj(name, pts, bevel_r=0.06, res=8, cyclic=False, mat=None, radii=None):
    """Smooth bent rod (bezier curve with a round bevel)."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = bevel_r; cu.bevel_resolution = res; cu.fill_mode = 'FULL'; cu.use_fill_caps = True
    try: cu.resolution_u = 16
    except Exception: pass
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for i, bp in enumerate(sp.bezier_points):
        bp.co = pts[i]; bp.handle_left_type = 'AUTO'; bp.handle_right_type = 'AUTO'
        if radii: bp.radius = radii[i]
    sp.use_cyclic_u = cyclic; sp.use_smooth = True
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    if mat is not None: cu.materials.append(mat)
    return o

def displace(o, name, strength=0.05, scale=0.3, basis=None, direction='NORMAL', vgroup=None, depth=2, hard=False):
    try:
        tx = bpy.data.textures.new(name + '_tx', 'CLOUDS'); tx.noise_scale = scale; tx.noise_depth = depth
        if basis: tx.noise_basis = basis
        if hard: tx.noise_type = 'HARD_NOISE'
        mod = o.modifiers.new(name, 'DISPLACE'); mod.texture = tx; mod.strength = strength; mod.mid_level = 0.5; mod.direction = direction
        if vgroup: mod.vertex_group = vgroup
        return mod
    except Exception as e: print('displace', e); return None

def vgroup_z(o, name, z0, z1):
    """Vertex group with weight ramping 0 at z0 -> 1 at z1 (local z)."""
    vg = o.vertex_groups.new(name=name)
    for v in o.data.vertices:
        w = (v.co.z - z0) / max(1e-6, (z1 - z0)); w = max(0.0, min(1.0, w)); w = w * w * (3 - 2 * w)
        if w > 0: vg.add([v.index], w, 'REPLACE')
    return name

def subdiv_side_edges(o, cuts=30, min_dz=0.1):
    """Cut the long side edges of a cylinder mesh so displacement has vertices to work with."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    edges = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > min_dz]
    bmesh.ops.subdivide_edges(bm, edges=edges, cuts=cuts, use_grid_fill=True); bm.to_mesh(o.data); bm.free()

# ================================================================== vessel profiles (outer surfaces, bottom -> top)
def prof_tube(r, h):
    """Test/boiling tube: hemispherical bottom, straight wall, rolled bead rim (solidify adds the wall)."""
    P = [(0.0, 0.0)] + [(r * math.cos(math.radians(-90 + 90 * k / 12)), r + r * math.sin(math.radians(-90 + 90 * k / 12))) for k in range(1, 13)]
    rb = 0.065; cx, cz = r - 0.02, h - rb; a_join = -math.degrees(math.acos(min(1.0, 0.02 / rb)))
    P.append((r, cz + rb * math.sin(math.radians(a_join))))
    P += arc(cx, cz, rb, a_join, 128, 14)[1:]
    return P

def prof_tube_liquid(r, level, th=0.03, eps=0.006, men=0.035):
    ri = r - th + eps; P = [(0.0, th - eps * 0.5)]
    P += [(ri * math.cos(math.radians(-90 + 90 * k / 12)), r + ri * math.sin(math.radians(-90 + 90 * k / 12))) for k in range(1, 13)]
    P.append((ri, level + men))
    P += [(ri * (1 - u), level + men * (1 - u) ** 2.2) for u in (0.08, 0.2, 0.4, 0.6, 0.8, 1.0)]
    return P

def prof_tube_fill(r, z_top, dome=0.08, th=0.03):
    """A solid filling the round bottom of a tube up to z_top with a soft dome (powder / crystal mass)."""
    ri = r - th + 0.004; P = [(0.0, th - 0.003)]
    a_top = math.degrees(math.asin(max(-1.0, min(1.0, (z_top - r) / ri))))
    P += [(ri * math.cos(math.radians(-90 + (a_top + 90) * k / 10)), r + ri * math.sin(math.radians(-90 + (a_top + 90) * k / 10))) for k in range(1, 11)]
    xe = P[-1][0]; P += [(xe * 0.7, z_top + dome * 0.55), (xe * 0.4, z_top + dome * 0.88), (0.0, z_top + dome)]
    return P

def prof_beaker(r, h):
    P = [(0.0, 0.0), (r - 0.10, 0.0)] + arc(r - 0.08, 0.08, 0.08, -90, 0, 5)[1:]
    P += [(r, h - 0.22), (r + 0.006, h - 0.12), (r + 0.03, h - 0.05), (r + 0.065, h - 0.005), (r + 0.075, h)]
    return P

def prof_beaker_liquid(r, level, th=0.04, eps=0.006, men=0.03):
    ri = r - th + eps
    P = [(0.0, th - eps * 0.5), (ri - 0.06, th - eps * 0.5), (ri, th + 0.04), (ri, level + men)]
    P += [(ri * (1 - u), level + men * (1 - u) ** 2.2) for u in (0.06, 0.15, 0.3, 0.5, 0.75, 1.0)]
    return P

def prof_jar(r, h):
    """Bell jar: open bottom with a rolled bead, straight wall, rounded shoulder, closed top."""
    rb = 0.085; cx, cz = r - 0.015, rb + 0.01; a_top = math.degrees(math.acos(min(1.0, (r - cx) / rb)))
    P = arc(cx, cz, rb, 215, 360 + a_top, 18)
    P += [(r, h - 0.45)] + arc(r - 0.45, h - 0.45, 0.45, 0, 90, 10)[1:] + [(0.0, h)]
    return P

def prof_dome(R):
    rb = 0.10; cx, cz = R - 0.03, rb + 0.005
    P = arc(cx, cz, rb, 215, 420, 16); z0 = P[-1][1]; a0 = math.degrees(math.asin(min(1.0, z0 / R)))
    P += [(R * math.cos(math.radians(a)), R * math.sin(math.radians(a))) for a in [a0 + (90 - a0) * k / 44 for k in range(1, 45)]]
    return P

def prof_watch(r, sag=0.36):
    Rc = (r * r + sag * sag) / (2 * sag); amax = math.degrees(math.asin(min(1.0, r / Rc)))
    return [(0.0, 0.0)] + [(Rc * math.sin(math.radians(amax * k / 18)), Rc * (1 - math.cos(math.radians(amax * k / 18)))) for k in range(1, 19)]

def prof_dish(r, h=1.45):
    coarse = [(0.0, 0.0), (r * 0.34, 0.0), (r * 0.52, 0.07), (r * 0.72, 0.42), (r * 0.87, 0.85), (r * 0.96, 1.18), (r, h - 0.13)]
    P = [(p[0], max(0.0, p[1])) for p in _resample_profile(coarse, 40)]
    P += arc(r - 0.02, h - 0.065, 0.065, -72, 130, 12)[1:]
    return P

def prof_plate(r):
    coarse = [(0.0, 0.0), (r * 0.62, 0.02), (r * 0.82, 0.08), (r * 0.94, 0.18), (r * 0.985, 0.26)]
    P = [(p[0], max(0.0, p[1])) for p in _resample_profile(coarse, 30)]
    return P + arc(r * 0.985 - 0.02, 0.26, 0.04, -80, 95, 7)[1:]

def liquid_from_outer(P_outer, level, th=0.035, eps=0.006, men=0.03):
    """Liquid volume for any lathed vessel: the outer profile shrunk by the wall, cut at level, capped with a meniscus."""
    P = [(max(0.0, r - th + eps) if r > 1e-5 else 0.0, z + (th - eps * 0.5 if r < 1e-5 else 0.0)) for (r, z) in P_outer if z <= level]
    if not P or P[0][0] > 1e-5: P = [(0.0, th - eps * 0.5)] + P
    ri = P[-1][0]; P.append((ri, level + men))
    P += [(ri * (1 - u), level + men * (1 - u) ** 2.2) for u in (0.08, 0.2, 0.4, 0.6, 0.8, 1.0)]
    return P

# ================================================================== glassware
def glass_tube(loc, r=0.34, h=3.2, name='TestTube', th=0.03, tint=(0.92, 0.97, 1.0)):
    o = lathe(name, prof_tube(r, h), loc, verts=128, cap_bottom=False, mat=M_glass(tint, name=name + '_g')); solidify(o, th); return o

def liquid_in_tube(loc, r, level, color, name='TubeLiquid', th=0.03, absorb=4.5, scatter=0.8):
    return lathe(name, prof_tube_liquid(r, level, th), loc, verts=128, cap_bottom=False, mat=M_liquid(color, absorb, scatter, name=name + '_m'))

def glass_beaker(loc, r=1.2, h=1.7, name='Beaker', th=0.04):
    o = lathe(name, prof_beaker(r, h), loc, verts=128, cap_bottom=False, mat=M_glass(name=name + '_g')); solidify(o, th); return o

def liquid_in_beaker(loc, r, level, color, name='BeakerLiquid', th=0.04, absorb=2.2, scatter=0.5, mat=None):
    return lathe(name, prof_beaker_liquid(r, level, th), loc, verts=128, cap_bottom=False, mat=mat or M_liquid(color, absorb, scatter, name=name + '_m'))

def glass_jar(r=1.35, h=3.9, loc=(0, 0, 0), name='Jar'):
    o = lathe(name, prof_jar(r, h), loc, verts=128, cap_bottom=False, mat=M_glass((0.9, 0.96, 1.0), name='jar_g')); solidify(o, 0.045); return o

def glass_dome(R=3.4, loc=(0, 0, 0), tint=(0.78, 0.92, 1.0)):
    o = lathe('Dome', prof_dome(R), loc, verts=160, cap_bottom=False, mat=M_glass(tint, name='dome_g')); solidify(o, 0.05); return o

def watch_glass_v2(loc, r=1.4, name='WatchGlass'):
    o = lathe(name, prof_watch(r), loc, verts=128, cap_bottom=False, mat=M_glass((0.72, 0.88, 1.0), name=name + '_g')); solidify(o, 0.035); return o

def china_dish_v2(loc, r=2.1, name='ChinaDish'):
    o = lathe(name, prof_dish(r), loc, verts=160, cap_bottom=False, mat=M_glass((0.6, 0.83, 1.0), name=name + '_g')); solidify(o, 0.06); return o

# ================================================================== powders, specks, sparks
def powder_pile(center, n, spread, r, color, name='Gran', flat=0.6, seed=7, mat=None, mound=True, metallic=0.0):
    """A pile: a displaced mound (so it reads as a solid heap) with detailed grains scattered on top."""
    rnd = random.Random(seed); m = mat or M_powder(color, name + '_m', metallic=metallic); out = []; md = None
    if mound:
        hm = r * flat * 0.9
        P = [(spread * 1.02, 0.0)] + [(spread * 1.02 * (1 - k / 10), hm * (1 - (1 - k / 10) ** 2)) for k in range(1, 11)]
        md = lathe(name + 'Mound', P, (center[0], center[1], center[2] - 0.01), verts=64, cap_bottom=True, mat=m)
        displace(md, name + 'rough', strength=r * 0.5, scale=0.12, depth=3)
    for i in range(n):
        a = rnd.random() * 2 * math.pi; d = spread * math.sqrt(rnd.random())
        o = obj_add('uv_sphere', f'{name}{i}', radius=r * rnd.uniform(0.7, 1.3), segments=16, ring_count=8)
        o.location = (center[0] + d * math.cos(a), center[1] + d * math.sin(a), center[2] + r * flat * (1 - (d / spread) ** 2) * rnd.uniform(0.3, 1.0))
        o.scale = (rnd.uniform(0.8, 1.2), rnd.uniform(0.8, 1.2), rnd.uniform(0.7, 1.0)); o.rotation_euler = (rnd.random() * 3, rnd.random() * 3, rnd.random() * 3)
        setmat(o, m); smooth(o, auto=False); out.append(o)
    return out, m, md

def specks(n, center, spread, r=0.035, color=(0.9, 0.95, 1.0), strength=6.0, seed=2, f0=1, f1=240, drift=0.6, name='Fl', alpha=1.0):
    """Slow-drifting glowing specks as smooth spheres (CO2 dots, gas molecules, rust particles). Same drift as kit.floaters."""
    rnd = random.Random(seed); m = mat_emit(color, strength=strength, name=name + '_m', alpha=alpha); out = []
    for i in range(n):
        p = Vector((center[0] + rnd.uniform(-spread[0], spread[0]), center[1] + rnd.uniform(-spread[1], spread[1]), center[2] + rnd.uniform(-spread[2], spread[2])))
        o = obj_add('uv_sphere', f'{name}{i}', radius=r * rnd.uniform(0.6, 1.4), segments=20, ring_count=10, location=p); setmat(o, m); smooth(o, auto=False)
        f = f0
        while f <= f1:
            kf(o, 'location', f, tuple(p)); p = p + Vector((rnd.uniform(-drift, drift), rnd.uniform(-drift, drift), rnd.uniform(-drift, drift) * 0.7)); f += 36
        kf_ease(o); out.append(o)
    return out

def spark(name, mat, r=0.028):
    s = obj_add('uv_sphere', name, radius=r, segments=16, ring_count=8); setmat(s, mat); smooth(s, auto=False); return s

# ================================================================== flames, candle, spirit lamp
def flame_at(loc, scale=1.0, name='Flame', nf=48, smoke=True, smoke_h=2.5):
    """Volumetric flame (Cycles) / mesh flame (EEVEE) under a rig empty: flicker keys the flame, growth keys the rig."""
    rig = empty(name + 'Rig', loc)
    fl, L = flame_volume(loc, scale=scale, name=name, f0=1, f1=max(2, nf))
    fl.parent = rig; fl.matrix_parent_inverse = rig.matrix_world.inverted()
    sm = None
    if smoke:
        sm = smoke_wisp((loc[0], loc[1], loc[2] + 0.55 * scale), height=smoke_h, name=name + 'Smoke', density=0.045, f0=1, f1=max(2, nf))
        if sm is not None: sm.parent = rig; sm.matrix_parent_inverse = rig.matrix_world.inverted()
    return fl, L, sm, rig

def candle_v2(loc=(0, 0, 0), r=0.32, h=2.6, seed=3):
    """Wax candle: subsurface wax, concave melt pool, irregular (displaced) melted rim, drips, bent wick, pewter holder.
    Origin at the base so a Z scale melts it down in place. Returns (body, wick, parts); pool/drips/wick are parented."""
    rnd = random.Random(seed); wax = M_wax(); parts = []
    P = [(0.0, 0.0), (r - 0.05, 0.0)] + arc(r - 0.05, 0.05, 0.05, -90, 0, 4)[1:] + [(r, h - 0.35), (r, h - 0.12), (r * 0.985, h)]
    P += [(r * 0.9, h - 0.01), (r * 0.72, h - 0.07), (r * 0.45, h - 0.13), (r * 0.2, h - 0.16), (0.0, h - 0.17)]
    body = lathe('Candle', P, loc, verts=128, cap_bottom=False, mat=wax)
    vg = vgroup_z(body, 'rim', h - 0.55, h); displace(body, 'melt', strength=0.09, scale=0.3, direction='Z', vgroup=vg); displace(body, 'sag', strength=0.02, scale=0.18, direction='NORMAL', vgroup=vg)
    pool = lathe('MeltPool', [(0.0, h - 0.145), (r * 0.5, h - 0.14), (r * 0.72, h - 0.125), (r * 0.8, h - 0.10)], loc, verts=96, cap_bottom=False, mat=M_liquid_wax()); parts.append(pool)
    for i in range(3):
        a = rnd.uniform(0, 2 * math.pi) if i else 0.6; Ld = rnd.uniform(0.45, 1.0); ca, sa = math.cos(a), math.sin(a)
        pts = [(loc[0] + r * 0.9 * ca, loc[1] + r * 0.9 * sa, loc[2] + h + 0.01), (loc[0] + r * 1.03 * ca, loc[1] + r * 1.03 * sa, loc[2] + h - 0.12), (loc[0] + (r + 0.025) * ca, loc[1] + (r + 0.025) * sa, loc[2] + h - Ld)]
        d = curve_obj(f'Drip{i}', pts, bevel_r=0.045, mat=wax, radii=[1.1, 0.8, 1.0]); parts.append(d)
        bulb = obj_add('uv_sphere', f'DripBulb{i}', radius=0.06, segments=32, ring_count=16, location=(pts[-1][0], pts[-1][1], pts[-1][2] - 0.02)); bulb.scale = (1, 1, 1.35); setmat(bulb, wax); smooth(bulb); parts.append(bulb)
    wick = curve_obj('Wick', [(loc[0], loc[1], loc[2] + h - 0.3), (loc[0] + 0.01, loc[1], loc[2] + h + 0.02), (loc[0] + 0.035, loc[1] + 0.015, loc[2] + h + 0.15)], bevel_r=0.02, mat=M_wick(), radii=[1.0, 1.0, 0.75]); parts.append(wick)
    holder = lathe('CandleBase', [(0.0, 0.0), (r * 1.35, 0.0), (r * 1.42, 0.03), (r * 1.45, 0.08), (r * 1.4, 0.11), (r * 1.25, 0.1), (r * 1.15, 0.06), (r * 1.02, 0.06), (r * 1.0, 0.09)], loc, verts=128, cap_bottom=False, mat=M_metal((0.62, 0.62, 0.64), rough=0.3, name='holder_m'))
    solidify(holder, 0.03)
    for o in parts: o.parent = body; o.matrix_parent_inverse = body.matrix_world.inverted()
    return body, wick, parts

def lit_candle(loc=(0, 0, 0), rfps=12, nf=48, scale=1.0, on_from=None, off_at=None):
    body, wick, parts = candle_v2(loc)
    fl, L, sm, rig = flame_at((loc[0], loc[1], loc[2] + 2.6), scale=scale, name='Flame', nf=nf)
    flicker(fl, 1, nf, seed=3)
    objs = [fl, L] + [c for c in fl.children if c is not L]
    if on_from is not None:
        f = F(on_from, rfps)
        for o in objs: kf(o, 'hide_render', 1, True); kf(o, 'hide_render', f, False)
        kf(L.data, 'energy', 1, 0.0); kf(L.data, 'energy', f, 45.0 * scale)
        if sm is not None: kf(sm, 'hide_render', 1, True); kf(sm, 'hide_render', f, False)
    if off_at is not None:
        f = F(off_at, rfps); kf(fl, 'scale', f - 1, tuple(fl.scale)); kf(fl, 'scale', f + int(rfps * 1.5), (0.001, 0.001, 0.001))
        for o in objs: kf(o, 'hide_render', f + int(rfps * 1.6), True)
        kf(L.data, 'energy', f - 1, 45.0 * scale); kf(L.data, 'energy', f + int(rfps * 1.5), 0.0)
        if sm is not None: kf(sm, 'scale', f, (1, 1, 1)); kf(sm, 'scale', f + rfps * 2, (1.7, 1.7, 1.3)); kf_ease(sm)
    return body, fl, L

def spirit_lamp_v2(loc=(0, 0, 0), r=0.34, h=2.6, name='Lamp', nf=48):
    """Real spirit lamp: tall glass reservoir with spirit inside, brass collar with a wick tube, cotton wick, volumetric
    flame at local (0, 0, h + 0.15) -- the same flame position as before so the validated layouts hold."""
    root = empty(name, loc); parts = []
    coarse = [(0.0, 0.0), (1.3 * r, 0.0), (1.42 * r, 0.1), (1.45 * r, 0.5), (1.4 * r, 1.1), (1.15 * r, 1.55), (0.72 * r, 1.85), (0.55 * r, 2.0), (0.55 * r, h - 0.55)]
    P = [(p[0], max(0.0, p[1])) for p in _resample_profile(coarse, 44)]
    body = lathe(name + 'Glass', P, (0, 0, 0), verts=128, cap_bottom=False, mat=M_glass((0.9, 0.96, 1.0), name=name + '_g')); solidify(body, 0.035); parts.append(body)
    fuel = lathe(name + 'Fuel', liquid_from_outer(P, 1.15, th=0.035), (0, 0, 0), verts=128, cap_bottom=False, mat=M_liquid((0.55, 0.7, 0.95), absorb=1.2, scatter=0.15, name=name + '_fuel')); parts.append(fuel)
    brass = M_metal((0.85, 0.62, 0.3), rough=0.3, name=name + '_brass')
    collar = lathe(name + 'Collar', [(0.52 * r, h - 0.62), (0.63 * r, h - 0.6), (0.68 * r, h - 0.5), (0.66 * r, h - 0.34), (0.5 * r, h - 0.3), (0.3 * r, h - 0.28), (0.22 * r, h - 0.24), (0.2 * r, h - 0.06), (0.24 * r, h - 0.03), (0.24 * r, h), (0.17 * r, h)], (0, 0, 0), verts=96, cap_bottom=False, mat=brass)
    solidify(collar, 0.03); parts.append(collar)
    wick = obj_add('cylinder', name + 'Wick', radius=0.13 * r, depth=0.75, vertices=32, location=(0, 0, h - 0.2)); bevel(wick, 0.01, 3); smooth(wick); setmat(wick, M_wick(name + '_wick')); parts.append(wick)
    for o in parts: o.parent = root
    fl, L, sm, rig = flame_at((0, 0, h + 0.15), scale=1.15, name=name + 'Flame', nf=nf, smoke_h=2.0)
    rig.parent = root
    return root, body, fl, L, rig

# ================================================================== lab hardware
def tongs_v2(loc=(0, 0, 0), L=3.4, name='Tongs'):
    """Crucible tongs in the X-Z plane: two bent arms (bezier rods) with finger loops, cupped jaw pads, riveted pivot."""
    m = M_metal((0.84, 0.85, 0.88), rough=0.32, name='tongs_m', aniso=0.3, radial=False); root = empty(name, loc); parts = []
    def add(o): o.parent = root; parts.append(o); return o
    for s in (-1, 1):
        y = s * 0.055
        add(curve_obj(f'Arm{s}', [(s * 0.02, y, -L * 0.36), (s * 0.10, y, -L * 0.22), (s * 0.05, y * 0.6, 0.0), (s * 0.20, y, L * 0.32), (s * 0.34, y, L * 0.66)], bevel_r=0.085, mat=m))
        cx, cz = s * 0.58, L * 0.66 + 0.24
        add(curve_obj(f'Loop{s}', [(cx + 0.34 * math.cos(math.radians(a)), y, cz + 0.26 * math.sin(math.radians(a))) for a in range(0, 360, 45)], bevel_r=0.075, cyclic=True, mat=m))
        jaw = add(box(f'Jaw{s}', (0.09, 0.2, 0.34), (s * 0.055, y * 0.7, -L * 0.36 + 0.12), m, bev=0.035, seg=5, rot=(0, s * math.radians(-12), 0)))
    piv = add(obj_add('cylinder', 'Pivot', radius=0.075, depth=0.22, vertices=48)); piv.rotation_euler = (math.pi / 2, 0, 0); bevel(piv, 0.02, 4); smooth(piv); setmat(piv, m)
    for s in (-1, 1):
        head = add(obj_add('uv_sphere', f'Rivet{s}', radius=0.055, segments=32, ring_count=16, location=(0, s * 0.11, 0))); head.scale = (1, 0.5, 1); smooth(head); setmat(head, m)
    return root, parts

def retort_stand_v2(loc=(0, 0, 0), h=5.5, tube=(0.35, 0, 3.96), tube_r=0.36):
    """Cast base, rod with foot nut, boss head with thumbscrews, horizontal arm, clamp body and two padded jaws."""
    m = M_metal((0.72, 0.73, 0.76), rough=0.35, name='stand_m'); dark = M_metal((0.22, 0.22, 0.24), rough=0.5, name='stand_dark', aniso=0.0); cork = mat_plastic((0.55, 0.38, 0.22), rough=0.85, name='cork'); parts = []
    x0, y0, z0 = loc; bz = tube[2]
    parts.append(box('StandBase', (1.9, 1.2, 0.16), (x0 - 0.4, y0, z0 + 0.08), dark, bev=0.06, seg=6))
    pole = obj_add('cylinder', 'StandPole', radius=0.09, depth=h, vertices=64, location=(x0 - 1.1, y0, z0 + h / 2)); bevel(pole, 0.03, 4); smooth(pole); setmat(pole, m); parts.append(pole)
    nut = obj_add('cylinder', 'StandNut', radius=0.17, depth=0.14, vertices=48, location=(x0 - 1.1, y0, z0 + 0.23)); bevel(nut, 0.03, 4); smooth(nut); setmat(nut, m); parts.append(nut)
    parts.append(box('Boss', (0.34, 0.30, 0.46), (x0 - 1.1, y0, z0 + bz), dark, bev=0.04, seg=5))
    for i, dz in enumerate((0.12, -0.12)):
        sc = obj_add('cylinder', f'Screw{i}', radius=0.045, depth=0.34, vertices=32, location=(x0 - 1.1, y0 - 0.3, z0 + bz + dz)); sc.rotation_euler = (math.pi / 2, 0, 0); smooth(sc); setmat(sc, m); parts.append(sc)
        kn = obj_add('cylinder', f'Knob{i}', radius=0.09, depth=0.08, vertices=32, location=(x0 - 1.1, y0 - 0.47, z0 + bz + dz)); kn.rotation_euler = (math.pi / 2, 0, 0); bevel(kn, 0.02, 3); smooth(kn); setmat(kn, dark); parts.append(kn)
    ax0 = x0 - 1.1 + 0.15; ax1 = tube[0] - tube_r - 0.16
    arm = obj_add('cylinder', 'StandArm', radius=0.06, depth=ax1 - ax0, vertices=48, location=((ax0 + ax1) / 2, y0, z0 + bz)); arm.rotation_euler = (0, math.pi / 2, 0); smooth(arm); setmat(arm, m); parts.append(arm)
    parts.append(box('ClampBody', (0.24, 0.22, 0.26), (ax1, y0, z0 + bz), dark, bev=0.03, seg=5))
    sc = obj_add('cylinder', 'ClampScrew', radius=0.035, depth=0.36, vertices=32, location=(ax1 - 0.2, y0, z0 + bz)); sc.rotation_euler = (0, math.pi / 2, 0); smooth(sc); setmat(sc, m); parts.append(sc)
    kn = obj_add('cylinder', 'ClampKnob', radius=0.08, depth=0.07, vertices=32, location=(ax1 - 0.4, y0, z0 + bz)); kn.rotation_euler = (0, math.pi / 2, 0); bevel(kn, 0.02, 3); smooth(kn); setmat(kn, dark); parts.append(kn)
    R = tube_r + 0.07
    for s, (a0, a1) in ((1, (180, 30)), (-1, (180, 330))):
        pts = [(tube[0] + R * math.cos(math.radians(a)), y0 + R * math.sin(math.radians(a)), z0 + bz) for a in (a0, a0 + (a1 - a0) * 0.33, a0 + (a1 - a0) * 0.66, a1)]
        parts.append(curve_obj(f'Jaw{s}', pts, bevel_r=0.045, mat=m))
        pad = obj_add('uv_sphere', f'Pad{s}', radius=0.065, segments=24, ring_count=12, location=(tube[0] + (tube_r + 0.03) * math.cos(math.radians(a1)), y0 + (tube_r + 0.03) * math.sin(math.radians(a1)), z0 + bz)); smooth(pad); setmat(pad, cork); parts.append(pad)
    return parts

def tube_rack_v2(loc=(0, 0, 0), w=4.4, d=1.6, h=2.3, holes=(-0.9, 0.9), hole_r=0.42, hole_y=-0.2):
    """Wooden rack: bevelled planks, a top plank with drilled holes, a lower shelf with smaller holes for the round
    bottoms, a pale back board. Cutters are render-hidden."""
    wood = M_wood('rack_wood', (0.44, 0.24, 0.10), (0.68, 0.42, 0.20), scale=2.5); pale = M_wood('rack_pale', (0.70, 0.56, 0.34), (0.86, 0.74, 0.5), scale=2.5)
    x0, y0, z0 = loc; t = 0.15; parts = []
    parts.append(box('RackBack', (w - 2 * t, 0.12, h - 2 * t), (x0, y0 + d / 2 - 0.06, z0 + h / 2), pale, bev=0.015))
    parts.append(box('RackBase', (w, d, t), (x0, y0, z0 + t / 2), wood, bev=0.02))
    for s in (-1, 1): parts.append(box(f'RackSide{s}', (t, d, h), (x0 + s * (w / 2 - t / 2), y0, z0 + h / 2), wood, bev=0.02))
    for nm, z, rr in (('RackTop', z0 + h - t / 2, hole_r), ('RackShelf', z0 + 0.545, hole_r * 0.72)):
        pl = box(nm, (w - 2 * t, d - 0.1, t), (x0, y0 - 0.05, z), wood, bev=0.02); parts.append(pl)
        for i, hx in enumerate(holes):
            cut = obj_add('cylinder', f'{nm}Cut{i}', radius=rr, depth=t * 3, vertices=64, location=(x0 + hx, y0 + hole_y, z)); cut.hide_render = True; cut.display_type = 'WIRE'
            try:
                mod = pl.modifiers.new(f'hole{i}', 'BOOLEAN'); mod.operation = 'DIFFERENCE'; mod.object = cut
                try: mod.solver = 'EXACT'
                except Exception: pass
            except Exception as e: print('boolean', e)
        bevel(pl, 0.012, 3, angle=40)
    return parts

def nail_v2(loc=(0, 0, 0), L=2.4, r=0.055, mat=None, name='Nail'):
    """Wire nail: shaft, conical point, domed head with a rounded edge. Origin at the shaft centre (as before)."""
    m = mat or M_metal((0.78, 0.78, 0.8), rough=0.32, name=name + '_m', aniso=0.3)
    zc = loc[2] + L * 0.14 + L * 0.43
    shaft = obj_add('cylinder', name, radius=r, depth=L * 0.86, vertices=48, location=(loc[0], loc[1], zc)); smooth(shaft); setmat(shaft, m)
    tip = obj_add('cone', name + 'Tip', radius1=r, radius2=0.0, depth=L * 0.14, vertices=48, location=(loc[0], loc[1], loc[2] + L * 0.07)); tip.rotation_euler = (math.pi, 0, 0); smooth(tip); setmat(tip, m)
    rr = r * 0.6
    P = [(0.0, 0.0), (r * 2.3, 0.0)] + arc(r * 2.3, rr, rr, -90, 60, 6)[1:] + [(r * 1.6, rr * 2.05), (r * 0.8, rr * 2.3), (0.0, rr * 2.4)]
    head = lathe(name + 'Head', P, (loc[0], loc[1], loc[2] + L - 0.01), verts=64, mat=m)
    for p in (tip, head): p.parent = shaft; p.matrix_parent_inverse = shaft.matrix_world.inverted()
    return shaft, m

def rust_coat(loc, L, r, name='RustCoat', seed=5):
    """Flaky rust crust around a nail shaft: a displaced (crackle) tube plus scattered lifted flakes, parented so the
    scale-in animation carries everything."""
    rnd = random.Random(seed); rm = M_rust(name + '_m'); zc = loc[2] + L * 0.14 + L * 0.43
    coat = obj_add('cylinder', name, radius=r * 1.22, depth=L * 0.86, vertices=96, location=(loc[0], loc[1], zc)); subdiv_side_edges(coat, 70)
    smooth(coat, auto=False); setmat(coat, rm); displace(coat, name + 'crust', strength=0.07, scale=0.16, depth=4); displace(coat, name + 'pits', strength=0.025, scale=0.05, depth=2, hard=True)
    flakes = []
    for i in range(30):
        a = rnd.uniform(0, 2 * math.pi); z = rnd.uniform(-L * 0.4, L * 0.4)
        fk = box(f'{name}Flake{i}', (rnd.uniform(0.06, 0.13), rnd.uniform(0.05, 0.1), 0.018), (loc[0] + r * 1.3 * math.cos(a), loc[1] + r * 1.3 * math.sin(a), zc + z), rm, bev=0.006, seg=2,
                 rot=(math.pi / 2 + rnd.uniform(-0.35, 0.35), rnd.uniform(-0.3, 0.3), a + math.pi / 2))
        fk.parent = coat; fk.matrix_parent_inverse = coat.matrix_world.inverted(); flakes.append(fk)
    return coat, flakes

def tripod_v2(loc=(0, 0, 0), h=3.6, r=1.5):
    m = M_metal((0.86, 0.86, 0.88), rough=0.3, name='tripod_m', aniso=0.25); parts = []
    ringo = obj_add('torus', 'TripodRing', major_radius=r, minor_radius=0.075, major_segments=160, minor_segments=32, location=(loc[0], loc[1], loc[2] + h)); smooth(ringo); setmat(ringo, m); parts.append(ringo)
    rub = mat_plastic((0.07, 0.07, 0.07), rough=0.85, name='foot_m')
    for i in range(3):
        a = math.radians(90 + i * 120); ca, sa = math.cos(a), math.sin(a)
        pts = [(loc[0] + (r - 0.05) * ca, loc[1] + (r - 0.05) * sa, loc[2] + h - 0.02), (loc[0] + (r + 0.12) * ca, loc[1] + (r + 0.12) * sa, loc[2] + h - 0.25),
               (loc[0] + (r + 0.3) * ca, loc[1] + (r + 0.3) * sa, loc[2] + h * 0.55), (loc[0] + (r + 0.38) * ca, loc[1] + (r + 0.38) * sa, loc[2] + 0.06)]
        parts.append(curve_obj(f'Leg{i}', pts, bevel_r=0.07, mat=m))
        ft = obj_add('cylinder', f'Foot{i}', radius=0.1, depth=0.1, vertices=32, location=(pts[-1][0], pts[-1][1], loc[2] + 0.05)); bevel(ft, 0.02, 3); smooth(ft); setmat(ft, rub); parts.append(ft)
    return parts

def gauze_v2(loc=(0, 0, 0), size=4.2, n=10):
    """Wire gauze: two arrayed wire runs (2 objects) and a thin ceramic centre disc."""
    m = M_metal((0.88, 0.88, 0.9), rough=0.35, name='gauze_m', aniso=0.0); sp = size / n; rw = 0.028; parts = []
    a = obj_add('cylinder', 'GauzeX', radius=rw, depth=size, vertices=16, location=(loc[0], loc[1] - size / 2, loc[2] + rw)); a.rotation_euler = (0, math.pi / 2, 0); smooth(a); setmat(a, m)
    b = obj_add('cylinder', 'GauzeY', radius=rw, depth=size, vertices=16, location=(loc[0] - size / 2, loc[1], loc[2] - rw)); b.rotation_euler = (math.pi / 2, 0, 0); smooth(b); setmat(b, m)
    for o, off in ((a, (0, sp, 0)), (b, (sp, 0, 0))):
        try: mod = o.modifiers.new('arr', 'ARRAY'); mod.count = n + 1; mod.use_relative_offset = False; mod.use_constant_offset = True; mod.constant_offset_displace = off
        except Exception as e: print('array', e)
        parts.append(o)
    cc = lathe('GauzeCentre', [(0.0, 0.0), (0.82, 0.0), (0.88, 0.012), (0.88, 0.024), (0.84, 0.03), (0.3, 0.032), (0.0, 0.033)], (loc[0], loc[1], loc[2] + rw * 2), verts=96, cap_bottom=False, mat=M_rough_ceramic())
    solidify(cc, 0.012); parts.append(cc)
    return parts

def sandpaper_v2(name='Sandpaper'):
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=64, y_subdivisions=52, size=1); o = bpy.context.object; o.name = name
    for v in o.data.vertices: v.co = (v.co.x * 1.5, v.co.y * 1.2, 0)
    smooth(o, auto=False); setmat(o, M_sandpaper())
    try:
        tx = bpy.data.textures.new('grit_tx', 'VORONOI'); tx.noise_scale = 0.025
        mod = o.modifiers.new('grit', 'DISPLACE'); mod.texture = tx; mod.strength = 0.012; mod.mid_level = 0.5; mod.direction = 'Z'
        sd = o.modifiers.new('curl', 'SIMPLE_DEFORM'); sd.deform_method = 'BEND'; sd.angle = math.radians(28); sd.deform_axis = 'Y'
        so = o.modifiers.new('solid', 'SOLIDIFY'); so.thickness = 0.02; so.offset = -1
    except Exception as e: print('sandpaper', e)
    return o

def M_magnesium(rough=0.6, name='mg'):
    """Dull magnesium ribbon: grey metal under a mottled oxide film, brushed streaks along the strip. Roughness stays a
    plain socket so a builder can keyframe the sanding."""
    m, p = _principled(name); nt, n = _nodes(m)
    tc = n.new('ShaderNodeTexCoord'); mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1.0, 14.0, 6.0)
    streak = _noise(n, 6.0, 3, 0.55); blot = _noise(n, 3.0, 4, 0.6, 0.8)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], streak.inputs['Vector']); nt.links.new(tc.outputs['Object'], blot.inputs['Vector'])
    r1 = _ramp(n, [(0.3, (0.36, 0.38, 0.41, 1)), (0.7, (0.6, 0.62, 0.66, 1))]); nt.links.new(blot.outputs['Fac'], r1.inputs['Fac'])
    mix = n.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 0.35
    r2 = _ramp(n, [(0.35, (0.7, 0.7, 0.7, 1)), (0.65, (1.1, 1.1, 1.1, 1))]); nt.links.new(streak.outputs['Fac'], r2.inputs['Fac'])
    nt.links.new(r1.outputs['Color'], mix.inputs[6]); nt.links.new(r2.outputs['Color'], mix.inputs[7]); nt.links.new(mix.outputs[2], p.inputs['Base Color'])
    _inp(p, 'Metallic', 0.9); _inp(p, 'Roughness', rough); _inp(p, 'Anisotropic', 0.5)
    _bump(nt, n, streak.outputs['Fac'], p, 0.25, 0.01)
    return m

def mg_ribbon_obj(name='Ribbon', dims=(2.2, 0.7, 0.04), rough=0.6):
    m = M_magnesium(rough, name='mg'); o = box(name, dims, (0, 0, 0), m, bev=min(0.012, dims[2] * 0.4), seg=3)
    try: mod = o.modifiers.new('bend', 'SIMPLE_DEFORM'); mod.deform_method = 'BEND'; mod.angle = math.radians(9); mod.deform_axis = 'X'
    except Exception: pass
    return o, m

def ice_v2():
    ice = obj_add('cube', 'Ice', size=1.6, location=(0, 0, 0.8)); bevel(ice, 0.28, 14); subsurf(ice, 1, 2)
    displace(ice, 'icerough', strength=0.05, scale=0.5); smooth(ice, auto=False); setmat(ice, M_ice()); return ice

def puddle_v2(R=0.9, seed=3):
    rnd = random.Random(seed); me = bpy.data.meshes.new('Puddle'); bm = bmesh.new(); c = bm.verts.new((0, 0, 0)); ring = []; ph = [rnd.uniform(0, 6.3) for _ in range(3)]
    for i in range(96):
        a = 2 * math.pi * i / 96; rr = R * (1 + 0.10 * math.sin(3 * a + ph[0]) + 0.06 * math.sin(5 * a + ph[1]) + 0.04 * math.sin(8 * a + ph[2]))
        ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), 0)))
    for i in range(96): bm.faces.new((c, ring[i], ring[(i + 1) % 96]))
    bm.to_mesh(me); bm.free(); o = bpy.data.objects.new('Puddle', me); bpy.context.collection.objects.link(o); o.location = (0, 0, 0.004)
    for p in me.polygons: p.use_smooth = True
    setmat(o, M_water_film()); return o

def plate_v2(loc=(0, 0, 0), r=2.6):
    o = lathe('Plate', prof_plate(r), loc, verts=160, cap_bottom=False, mat=M_ceramic((0.58, 0.58, 0.6), rough=0.12, name='plate_m')); solidify(o, 0.07); return o

def cake_v2(loc=(0, 0, 0), r=1.6, seed=5):
    """Sponge cake dome with a crumbly displaced surface, candied-fruit toppings and sprinkles (the rancidity prop)."""
    rnd = random.Random(seed)
    o = obj_add('uv_sphere', 'Food', radius=r, segments=96, ring_count=48, location=(loc[0], loc[1], loc[2] + 0.05)); o.scale = (1, 1, 0.75)
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.02], context='VERTS')
    for v in bm.verts: v.co *= 1 + 0.03 * math.sin(v.co.x * 5) * math.cos(v.co.y * 4.2)
    bm.to_mesh(o.data); bm.free()
    setmat(o, M_cake()); smooth(o, auto=False); displace(o, 'crumb', strength=0.07, scale=0.22, depth=3); subsurf(o, 1, 2)
    bits = []; cols = [(0.9, 0.2, 0.55), (0.95, 0.45, 0.1), (0.85, 0.15, 0.3)]
    for i in range(16):
        th = rnd.uniform(0, 2 * math.pi); ph = rnd.uniform(0.15, 1.2)
        p = (loc[0] + r * math.sin(ph) * math.cos(th), loc[1] + r * math.sin(ph) * math.sin(th), loc[2] + 0.05 + r * 0.75 * math.cos(ph))
        b = box(f'Bit{i}', (rnd.uniform(0.22, 0.34), rnd.uniform(0.16, 0.24), 0.1), p, mat_plastic(rnd.choice(cols), rough=0.35, name=f'bit{i}', coat=0.6, sss=0.2), bev=0.04, seg=5, rot=(ph, 0, th)); subsurf(b, 1, 1); bits.append(b)
    for i in range(14):
        th = rnd.uniform(0, 2 * math.pi); ph = rnd.uniform(0.1, 1.25)
        p = (loc[0] + r * 1.01 * math.sin(ph) * math.cos(th), loc[1] + r * 1.01 * math.sin(ph) * math.sin(th), loc[2] + 0.05 + r * 0.76 * math.cos(ph))
        s = obj_add('cylinder', f'Sprinkle{i}', radius=0.025, depth=0.12, vertices=12, location=p); s.rotation_euler = (ph, 0, th + rnd.uniform(0, 3)); bevel(s, 0.02, 3); smooth(s); setmat(s, mat_plastic(rnd.choice([(0.95, 0.95, 0.9), (0.3, 0.6, 0.95), (0.95, 0.85, 0.2)]), rough=0.4, name=f'spr{i}', coat=0.5)); bits.append(s)
    return o, bits

def mould_v2(food_loc, r, n=90, seed=11):
    rnd = random.Random(seed); m = M_mould(); dots = []
    for i in range(n):
        th = rnd.uniform(0, 2 * math.pi); ph = rnd.uniform(0.1, 1.35)
        p = (food_loc[0] + r * 1.01 * math.sin(ph) * math.cos(th), food_loc[1] + r * 1.01 * math.sin(ph) * math.sin(th), food_loc[2] + 0.05 + r * 0.76 * math.cos(ph))
        d = obj_add('uv_sphere', f'Mould{i}', radius=rnd.uniform(0.05, 0.1), segments=24, ring_count=12, location=p); d.scale = (rnd.uniform(0.9, 1.3), 1, 0.45); d.rotation_euler = (ph, 0, th); setmat(d, m); smooth(d, auto=False); dots.append(d)
    return dots

def mannequin_v2(loc=(0, 0, 0), h=3.6):
    """Smoother human silhouette: tapered capsules with joints, shoulders, pelvis, hands, subdivided; hologram-red skin."""
    m = M_holo((1.0, 0.1, 0.04)); u = h / 8.0; x, y, z = loc; parts = []
    def part(o, sub=True):
        smooth(o, auto=False); setmat(o, m); parts.append(o)
        if sub: subsurf(o, 1, 2)
        return o
    def capsule(name, r0, r1, length, pos, rot=(0, 0, 0)):
        o = obj_add('cone', name, radius1=r0, radius2=r1, depth=length, vertices=48); o.location = pos; o.rotation_euler = rot; bevel(o, min(r0, r1) * 0.9, 10); return part(o)
    def ball(name, r, pos, scale=(1, 1, 1)):
        o = obj_add('uv_sphere', name, radius=r, segments=48, ring_count=24, location=pos); o.scale = scale; return part(o, sub=False)
    ball('Head', 0.52 * u, (x, y, z + 7.35 * u), (0.9, 1.0, 1.15)); capsule('Neck', 0.2 * u, 0.22 * u, 0.55 * u, (x, y, z + 6.7 * u))
    capsule('Torso', 0.58 * u, 0.82 * u, 2.3 * u, (x, y, z + 5.35 * u)); ball('Shoulders', 0.82 * u, (x, y, z + 6.35 * u), (1.0, 0.7, 0.35)); ball('Pelvis', 0.7 * u, (x, y, z + 3.95 * u), (1.0, 0.75, 0.75))
    for s in (-1, 1):
        capsule(f'UpperArm{s}', 0.19 * u, 0.24 * u, 1.45 * u, (x + s * 1.08 * u, y, z + 5.55 * u), (0, math.radians(7 * s), 0)); ball(f'Elbow{s}', 0.2 * u, (x + s * 1.15 * u, y, z + 4.82 * u))
        capsule(f'LowerArm{s}', 0.14 * u, 0.19 * u, 1.35 * u, (x + s * 1.22 * u, y, z + 4.15 * u), (0, math.radians(4 * s), 0)); ball(f'Hand{s}', 0.17 * u, (x + s * 1.27 * u, y, z + 3.35 * u), (0.8, 0.5, 1.2))
        capsule(f'Thigh{s}', 0.25 * u, 0.33 * u, 1.9 * u, (x + s * 0.4 * u, y, z + 2.55 * u)); ball(f'Knee{s}', 0.25 * u, (x + s * 0.41 * u, y, z + 1.62 * u))
        capsule(f'Shin{s}', 0.17 * u, 0.25 * u, 1.75 * u, (x + s * 0.42 * u, y, z + 0.85 * u))
        part(box(f'Foot{s}', (0.3 * u, 0.62 * u, 0.16 * u), (x + s * 0.43 * u, y - 0.16 * u, z + 0.08 * u), None, bev=0.05 * u, seg=5), sub=False)
    return parts

def platform_v2(loc=(0, 0, 0), size=6.0, color=(0.03, 0.28, 0.65)):
    o = box('Platform', (size, size * 0.7, 0.1), (loc[0], loc[1], loc[2] - 0.05), mat_emit(color, strength=0.45, name='platform'), bev=0.03, seg=5)
    rim = box('PlatformRim', (size + 0.12, size * 0.7 + 0.12, 0.04), (loc[0], loc[1], loc[2] - 0.11), mat_emit((color[0] * 2, color[1] * 1.6, color[2] * 1.3), strength=1.6, name='platform_rim'), bev=0.015, seg=3)
    return o, rim

def leaf_mesh_data(name='LeafMesh', length=0.45, width=0.22, n=14, m=6):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); grid = []
    for i in range(n + 1):
        t = i / n; hw = width * 0.5 * (math.sin(math.pi * t) ** 0.65) * (1 - 0.15 * t); row = []
        for j in range(m + 1):
            u = -1 + 2 * j / m; row.append(bm.verts.new((length * t, hw * u, 0.10 * length * t * t - 0.25 * hw * u * u)))
        grid.append(row)
    for i in range(n):
        for j in range(m):
            try: bm.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
            except Exception: pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    return me

def plant_v2(loc=(0, 0, 0), h=2.2, leaves=14, seed=3):
    rnd = random.Random(seed); stem_m = mat_plastic((0.18, 0.42, 0.10), rough=0.55, name='stem'); leaf_m = M_leaf(); parts = []
    parts.append(curve_obj('Stem', [(loc[0], loc[1], loc[2] - 0.05), (loc[0] + 0.05, loc[1] - 0.03, loc[2] + h * 0.4), (loc[0] - 0.04, loc[1] + 0.04, loc[2] + h * 0.75), (loc[0] + 0.02, loc[1], loc[2] + h)], bevel_r=0.045, mat=stem_m, radii=[1.3, 1.0, 0.8, 0.5]))
    leaf_me = leaf_mesh_data(); leaf_me.materials.append(leaf_m)
    for i in range(leaves):
        z = loc[2] + 0.35 + (h - 0.4) * (i + 0.5) / leaves; ang = i * 2.399 + rnd.random() * 0.4; br_len = 0.55 + rnd.random() * 0.35
        pts = [(loc[0], loc[1], z), (loc[0] + math.cos(ang) * br_len * 0.5, loc[1] + math.sin(ang) * br_len * 0.5, z + 0.12), (loc[0] + math.cos(ang) * br_len, loc[1] + math.sin(ang) * br_len, z + 0.22)]
        parts.append(curve_obj(f'Branch{i}', pts, bevel_r=0.02, mat=stem_m, radii=[1.0, 0.8, 0.5]))
        for j in range(3):
            t = 0.5 + 0.25 * j; lf = bpy.data.objects.new(f'Leaf{i}_{j}', leaf_me); bpy.context.collection.objects.link(lf)
            lf.location = (loc[0] + math.cos(ang) * br_len * t, loc[1] + math.sin(ang) * br_len * t, z + 0.22 * t + 0.03 * j)
            s = rnd.uniform(0.75, 1.1); lf.scale = (s, s, s); lf.rotation_euler = (0.25 + rnd.uniform(-0.2, 0.2), -0.35, ang + (j - 1) * 0.9); parts.append(lf)
    return parts

def soil_v2(r=3.0, loc=(0, 0, 0)):
    P = [(r, -0.35), (r, -0.06)] + arc(r - 0.06, -0.06, 0.06, 0, 90, 4)[1:] + [((r - 0.06) * (1 - k / 24), 0.0) for k in range(1, 25)]
    o = lathe('Soil', P, loc, verts=128, cap_bottom=True, mat=mat_soil())
    vg = vgroup_z(o, 'top', -0.05, 0.0); displace(o, 'soilbump', strength=0.07, scale=0.4, direction='Z', vgroup=vg, depth=3)
    powder_pile((loc[0], loc[1], loc[2] + 0.02), 22, r * 0.85, 0.05, (0.5, 0.42, 0.34), name='Pebble', flat=0.5, seed=9, mound=False)
    return o

def token_sphere(name, loc, color, r=0.42, strength=1.6):
    o = obj_add('uv_sphere', name, radius=r, segments=64, ring_count=32, location=loc); m = mat_plastic(color, rough=0.25, name=name + '_m', coat=0.7); setmat(o, m); smooth(o)
    g = obj_add('uv_sphere', name + 'Glow', radius=r * 1.25, segments=48, ring_count=24, location=loc); setmat(g, mat_emit(color, strength=strength, name=name + '_g', alpha=0.25)); smooth(g); g.parent = o; g.matrix_parent_inverse = o.matrix_world.inverted()
    return o

# ================================================================== stages
def finish(target, rim2=120, hdri_strength=0.3, atmos=0.004):
    """Every scene: HDRI reflections (camera still sees the dark void), thin atmosphere for beams, a subtle 2nd rim."""
    hdri(strength=hdri_strength, rotation=math.radians(120)); atmosphere(atmos)
    light('AREA', (-5.0, 5.5, 4.5), rim2, (0.8, 0.88, 1.0), 'Rim2', size=3.5, target=target)

def stage_wood(target=(0, 0, 1.2), key_e=2600, spot=42):
    floor_wood_pbr(); studio(key=(2.5, -4.0, 7.5), key_e=key_e, target=target, spot=spot); finish(target, rim2=110, hdri_strength=0.18)

def stage_void(target=(0, 0, 1.5), key_e=1500, spot=70, fill_e=90):
    studio(key=(3.0, -5.0, 6.5), key_e=key_e, fill_e=fill_e, rim_e=300, target=target, spot=spot, blend=0.9); finish(target, rim2=140, hdri_strength=0.12)

def focus_pull(cam, f0, f1, o0, o1):
    if DOF: rack_focus(cam, f0, f1, o0, o1)

# ================================================================== builders
def candle_dome_intro(nf, rfps, dur):
    reset(); stage_wood(target=(0, 0, 1.3))
    lit_candle(nf=nf); glass_dome(3.4)
    specks(60, (0, 0, 1.7), (2.6, 2.4, 1.5), r=0.03, strength=4, f0=1, f1=nf, name='Sp')
    cam, tgt = camera((0.8, -12.0, 3.0), (0, 0, 1.4), lens=50); dolly(cam, tgt, 1, nf, (0.8, -12.0, 3.0), (0.4, -10.8, 2.7))

def mannequin_platform(nf, rfps, dur, dim=False):
    reset(); world(0.004, 0.006, 0.014); stage_void(target=(0, 0, 1.8), key_e=900, spot=80)
    platform_v2((0, 0, 0), size=7.5, color=(0.05, 0.32, 0.7)); mannequin_v2((0, 0, 0.05), h=3.8)
    cam, tgt = camera((0, -11.5, 2.6), (0, 0, 1.9), lens=45); dolly(cam, tgt, 1, nf, (0, -11.5, 2.6), (0, -11.0, 2.5))

def mannequin_platform2(nf, rfps, dur): mannequin_platform(nf, rfps, dur)

def plant_cone_intro(nf, rfps, dur):
    reset(); stage_void(target=(0, 0, 1.0), key_e=2200, spot=38)
    soil_v2(r=3.2); plant_v2((0, 0, 0), h=2.3); light_cone(top=(1.5, -1.0, 11), base=(0, 0, 0.1), r_top=0.4, r_base=3.3, alpha=0.09)
    cam, tgt = camera((1.0, -11.0, 3.2), (0, 0, 1.2), lens=45); dolly(cam, tgt, 1, nf, (1.0, -11.0, 3.2), (0.6, -8.6, 2.6))

def plant_cone2(nf, rfps, dur):
    reset(); stage_void(target=(0, 0, 1.0), key_e=2200, spot=38)
    soil_v2(r=3.2); plant_v2((0, 0, 0), h=2.3); light_cone(top=(1.5, -1.0, 11), base=(0, 0, 0.1), r_top=0.4, r_base=3.3, alpha=0.09)
    cam, tgt = camera((0.9, -9.5, 2.8), (0, 0, 1.2), lens=45); dolly(cam, tgt, 1, nf, (0.9, -9.5, 2.8), (0.3, -7.2, 2.3), (0, 0, 1.2), (0, 0, 1.3))

def candle_burn(nf, rfps, dur):
    reset(); stage_wood(target=(0, 0, 1.3))
    body, fl, L = lit_candle(nf=nf, rfps=rfps, on_from=2.5)
    # slow melt: candle shortens a little (origin at the base), flame follows
    kf(body, 'scale', F(2.5, rfps), (1, 1, 1)); kf(body, 'scale', nf, (1, 1, 0.86)); kf_lin(body)
    kf(fl, 'location', F(2.5, rfps), tuple(fl.location)); kf(fl, 'location', nf, (fl.location.x, fl.location.y, fl.location.z - 2.6 * 0.14))
    cam, tgt = camera((0.5, -16.0, 3.4), (0, 0, 1.5), lens=45); dolly(cam, tgt, 1, nf, (0.5, -16.0, 3.4), (0.3, -9.5, 2.6), (0, 0, 1.5), (0, 0, 1.4))

def candle_far(nf, rfps, dur):
    reset(); stage_wood(target=(0, 0, 1.3)); lit_candle(nf=nf)
    cam, tgt = camera((0.4, -17.0, 3.6), (0, 0, 1.4), lens=45); dolly(cam, tgt, 1, nf, (0.4, -17.0, 3.6), (0.4, -15.5, 3.4))

def candle_jar(nf, rfps, dur):
    reset(); stage_wood(target=(0, 0, 1.5))
    body, fl, L = lit_candle(nf=nf, rfps=rfps, off_at=3.5)
    j = glass_jar(r=1.35, h=3.9); kf(j, 'location', 1, (0, 0, 6.0)); kf(j, 'location', F(3.0, rfps), (0, 0, 0)); kf_ease(j)
    cam, tgt = camera((0.6, -12.5, 3.0), (0, 0, 1.6), lens=45); dolly(cam, tgt, 1, nf, (0.6, -12.5, 3.0), (0.5, -11.5, 2.8))

def _dome_scene(nf, rfps):
    reset(); stage_wood(target=(0, 0, 1.3)); lit_candle(nf=nf); glass_dome(3.4, tint=(0.72, 0.9, 1.0))
    specks(70, (0, 0, 1.7), (2.6, 2.4, 1.5), r=0.03, strength=4, f0=1, f1=nf, name='Sp')

def candle_dome_orbit(nf, rfps, dur):
    _dome_scene(nf, rfps)
    cam, tgt = camera((-2.5, -11.0, 3.0), (0, 0, 1.4), lens=45); orbit(cam, tgt, (0, 0, 1.4), 11.0, 3.0, -13.0, 13.0, 1, nf)

def candle_dome_pull(nf, rfps, dur):
    _dome_scene(nf, rfps)
    cam, tgt = camera((1.5, -9.5, 2.8), (0, 0, 1.4), lens=45); dolly(cam, tgt, 1, nf, (1.5, -9.5, 2.8), (-1.5, -11.5, 3.2))

def ice_block(nf, rfps, dur):
    reset(); floor_wood_pbr(); studio(key=(2.5, -4.0, 7.5), key_e=2000, target=(0, 0, 0.6), spot=50); finish((0, 0, 0.6), rim2=110)
    ice = ice_v2()
    kf(ice, 'scale', 1, (1, 1, 1)); kf(ice, 'scale', nf, (1.15, 1.15, 0.72)); kf(ice, 'location', 1, (0, 0, 0.8)); kf(ice, 'location', nf, (0, 0, 0.58)); kf_lin(ice)
    pud = puddle_v2(0.9); kf(pud, 'scale', 1, (0.3, 0.3, 1)); kf(pud, 'scale', nf, (1.6, 1.6, 1)); kf_lin(pud)
    cam, tgt = camera((2.5, -7.0, 3.6), (0, 0, 0.7), lens=50); dolly(cam, tgt, 1, nf, (2.5, -7.0, 3.6), (2.0, -6.4, 3.3))

def mg_ribbon(nf, rfps, dur):
    reset(); stage_void(target=(0, 0, 1.5), key_e=1400, spot=70)
    rib, rm = mg_ribbon_obj('Ribbon', (2.2, 0.7, 0.04), rough=0.7); rib.location = (0, 0, 1.5); rib.rotation_euler = (math.radians(65), 0.12, 0.35)
    kf(rib, 'rotation_euler', 1, (math.radians(65), 0.12, 0.35)); kf(rib, 'rotation_euler', nf, (math.radians(62), 0.02, 0.08)); kf_ease(rib)
    p = rm.node_tree.nodes['Principled BSDF']         # the sanding polishes the dull oxide skin
    for f, rg, col in ((F(7.0, rfps), 0.7, (0.6, 0.62, 0.66, 1)), (F(11.5, rfps), 0.28, (0.72, 0.74, 0.78, 1))):
        p.inputs['Roughness'].default_value = rg; p.inputs['Roughness'].keyframe_insert('default_value', frame=f); p.inputs['Base Color'].default_value = col; p.inputs['Base Color'].keyframe_insert('default_value', frame=f)
    sp = sandpaper_v2()
    f0 = F(5.0, rfps); kf(sp, 'hide_render', 1, True); kf(sp, 'hide_render', f0, False)
    kf(sp, 'location', f0, (-2.6, -1.2, 3.8)); kf(sp, 'location', F(6.5, rfps), (-0.3, -0.25, 1.62))
    for i, t in enumerate([7.5, 8.5, 9.5, 10.5, 11.5]):
        kf(sp, 'location', F(t, rfps), (0.8 if i % 2 == 0 else -0.8, -0.25, 1.62))
    kf(sp, 'rotation_euler', f0, (math.radians(65), 0.05, 0.3)); kf_ease(sp)
    cam, tgt = camera((0, -8.5, 2.6), (0, 0, 1.5), lens=50); dolly(cam, tgt, 1, nf, (0, -8.5, 2.6), (0, -7.8, 2.4))

def _tongs_lamp_scene(nf, rfps, ignite=None, burn_until=None, lamp_in=0.0, tongs_in=0.0):
    """Reference layout: tongs enter from the top-right holding the ribbon at centre, the spirit lamp leans in from the
    bottom-left, the watch glass waits at the bottom centre."""
    reset(); stage_void(target=(0, 0, 0.5), key_e=1300, spot=75)
    tg, parts = tongs_v2((1.2, 0, 2.2)); tg.rotation_euler = (0, math.radians(35), 0)
    rib, rm = mg_ribbon_obj('Ribbon', (0.9, 0.025, 0.3), rough=0.55); rib.location = (0.25, 0, 0.85); rib.rotation_euler = (0, math.radians(125), 0)
    lamp, body, fl, L, rig = spirit_lamp_v2((-2.0, 0, -1.7), nf=nf); lamp.rotation_euler = (0, math.radians(40), 0); flicker(fl, 1, nf, seed=5)
    if lamp_in > 0:
        kf(lamp, 'location', 1, (-5.5, 0, -4.0)); kf(lamp, 'location', F(lamp_in, rfps), (-5.5, 0, -4.0)); kf(lamp, 'location', F(lamp_in + 2.5, rfps), (-2.0, 0, -1.7)); kf_ease(lamp)
    if tongs_in > 0:
        for o in (tg, rib):
            base = tuple(o.location); kf(o, 'location', 1, (base[0] + 4, base[1], base[2] + 3.5)); kf(o, 'location', F(tongs_in, rfps), (base[0] + 4, base[1], base[2] + 3.5)); kf(o, 'location', F(tongs_in + 2.0, rfps), base); kf_ease(o)
    wg = watch_glass_v2((0.5, 0, -1.6), r=1.5)
    return tg, rib, lamp, fl, wg

def tongs_lamp(nf, rfps, dur):
    tg, rib, lamp, fl, wg = _tongs_lamp_scene(nf, rfps, lamp_in=2.5, tongs_in=0.5)
    cam, tgt = camera((0.2, -10.0, 1.2), (0, 0, 0.3), lens=45); dolly(cam, tgt, 1, nf, (0.2, -10.0, 1.2), (0.2, -9.6, 1.1))

def mg_burn(nf, rfps, dur):
    tg, rib, lamp, fl, wg = _tongs_lamp_scene(nf, rfps)
    # dazzling white-blue glow at the ribbon tip + falling sparks into the watch glass, ribbon shrinks, white powder grows
    glow = obj_add('uv_sphere', 'Glow', radius=0.26, segments=48, ring_count=24, location=(0.0, 0, 0.45)); setmat(glow, mat_emit((0.7, 0.85, 1.0), strength=30, name='mgglow')); smooth(glow)
    halo = obj_add('uv_sphere', 'GlowHalo', radius=0.55, segments=48, ring_count=24, location=(0.0, 0, 0.45)); setmat(halo, mat_emit((0.7, 0.85, 1.0), strength=4, name='mghalo', alpha=0.18)); smooth(halo); halo.parent = glow; halo.matrix_parent_inverse = glow.matrix_world.inverted()
    gl = light('POINT', (0.0, 0, 0.45), 700, (0.75, 0.85, 1.0), 'MgLight')
    burn_end = F(21.0, rfps)
    kf(glow, 'scale', 1, (1, 1, 1)); kf(glow, 'scale', burn_end, (1, 1, 1)); kf(glow, 'scale', burn_end + rfps, (0.01, 0.01, 0.01)); kf(glow, 'hide_render', burn_end + rfps, True); kf(halo, 'hide_render', burn_end + rfps, True)
    kf(gl.data, 'energy', 1, 900); kf(gl.data, 'energy', burn_end, 900); kf(gl.data, 'energy', burn_end + rfps, 0)
    kf(rib, 'scale', 1, (1, 1, 1)); kf(rib, 'scale', burn_end, (0.28, 1, 1)); kf_lin(rib)
    rnd = random.Random(9); sm = mat_emit((1.0, 0.95, 0.85), strength=12, name='spark')
    for i in range(60):
        t0 = rnd.uniform(0, 19.0); f0 = F(t0, rfps); f1 = F(t0 + 1.1, rfps)
        s = spark(f'Spark{i}', sm)
        x0, z0 = 0.0 + rnd.uniform(-0.15, 0.15), 0.45; x1 = 0.5 + rnd.uniform(-0.6, 0.6); y1 = rnd.uniform(-0.5, 0.5)
        kf(s, 'hide_render', 1, True); kf(s, 'hide_render', f0, False); kf(s, 'hide_render', f1, True)
        kf(s, 'location', f0, (x0, 0, z0)); kf(s, 'location', f1, (x1, y1, -1.45)); kf_lin(s)
    pw, _, md = powder_pile((0.5, 0, -1.5), 70, 0.45, 0.042, (0.94, 0.94, 0.92), name='Powder', flat=0.6)
    for i, g in enumerate(pw):
        fa = F(3.0 + 16.0 * i / len(pw), rfps); kf(g, 'hide_render', 1, True); kf(g, 'hide_render', fa, False)
    kf(md, 'scale', F(3.0, rfps), (0.05, 0.05, 0.01)); kf(md, 'scale', F(19.0, rfps), (1, 1, 1)); kf_lin(md)
    cam, tgt = camera((0.2, -9.6, 1.1), (0, 0, 0.3), lens=45)
    dolly(cam, tgt, 1, F(20, rfps), (0.2, -9.6, 1.1), (0.1, -8.6, 0.9), (0, 0, 0.3), (0.1, 0, 0.0))
    kf(cam, 'location', F(29.0, rfps), (0.1, -8.6, 0.9)); kf(cam, 'location', nf, (0.3, -13.0, 1.4)); kf(tgt, 'location', F(29.0, rfps), (0.1, 0, 0.0)); kf(tgt, 'location', nf, (0, 0, 0.3)); kf_ease(cam); kf_ease(tgt)
    focus_pull(cam, F(14.0, rfps), F(18.0, rfps), glow, md)        # focus slides from the dazzling tip to the white powder as its label appears

def tongs_lamp_small(nf, rfps, dur):
    tg, rib, lamp, fl, wg = _tongs_lamp_scene(nf, rfps); rib.scale = (0.28, 1, 1)
    cam, tgt = camera((5.5, -15.0, 1.4), (2.5, 0, 0.3), lens=45); dolly(cam, tgt, 1, nf, (5.5, -15.0, 1.4), (6.0, -15.5, 1.5), (2.5, 0, 0.3), (3.0, 0, 0.3))

def _labelled_sphere(name, loc, color, r=0.42, strength=1.6): return token_sphere(name, loc, color, r, strength)

def na_cl_combine(nf, rfps, dur):
    reset(); world(0.004, 0.006, 0.014); stage_void(target=(0, 0, 1.5), key_e=1200, spot=80)
    na = _labelled_sphere('Na', (-3.6, 0, 1.9), (0.22, 0.32, 0.95)); cl = _labelled_sphere('Cl2', (3.6, 0, 1.9), (0.95, 0.75, 0.2))
    f0, f1 = F(12.0, rfps), F(15.5, rfps)
    kf(na, 'location', 1, (-3.6, 0, 1.9)); kf(na, 'location', f0, (-3.6, 0, 1.9)); kf(na, 'location', f1, (-0.32, 0, 1.5)); kf_ease(na)
    kf(cl, 'location', 1, (3.6, 0, 1.9)); kf(cl, 'location', f0, (3.6, 0, 1.9)); kf(cl, 'location', f1, (0.32, 0, 1.5)); kf_ease(cl)
    kf(na, 'scale', f1, (1, 1, 1)); kf(na, 'scale', f1 + rfps, (0.85, 0.85, 0.85)); kf(cl, 'scale', f1, (1, 1, 1)); kf(cl, 'scale', f1 + rfps, (0.85, 0.85, 0.85))
    # Na turns orange as it becomes NaCl (the reference recolours the pair orange/blue)
    m = na.data.materials[0]; p = m.node_tree.nodes['Principled BSDF']; p.inputs['Base Color'].default_value = (0.22, 0.32, 0.95, 1); p.inputs['Base Color'].keyframe_insert('default_value', frame=f1)
    p.inputs['Base Color'].default_value = (0.95, 0.5, 0.15, 1); p.inputs['Base Color'].keyframe_insert('default_value', frame=f1 + rfps)
    m2 = cl.data.materials[0]; p2 = m2.node_tree.nodes['Principled BSDF']; p2.inputs['Base Color'].default_value = (0.95, 0.75, 0.2, 1); p2.inputs['Base Color'].keyframe_insert('default_value', frame=f1)
    p2.inputs['Base Color'].default_value = (0.25, 0.65, 0.95, 1); p2.inputs['Base Color'].keyframe_insert('default_value', frame=f1 + rfps)
    cam, tgt = camera((0, -11.0, 2.0), (0, 0, 1.6), lens=45); dolly(cam, tgt, 1, nf, (0, -11.0, 2.0), (0, -9.5, 1.9))

def nacl_split(nf, rfps, dur):
    reset(); world(0.004, 0.006, 0.014); stage_void(target=(0, 0, 1.5), key_e=1200, spot=80)
    na = _labelled_sphere('Na', (-0.3, 0, 1.5), (0.95, 0.5, 0.15), r=0.36); cl = _labelled_sphere('Cl2', (0.3, 0, 1.5), (0.25, 0.65, 0.95), r=0.36)
    f0, f1 = F(8.0, rfps), F(13.0, rfps)
    kf(na, 'location', 1, (-0.3, 0, 1.5)); kf(na, 'location', f0, (-0.3, 0, 1.5)); kf(na, 'location', f1, (-3.2, 0, 1.9)); kf_ease(na)
    kf(cl, 'location', 1, (0.3, 0, 1.5)); kf(cl, 'location', f0, (0.3, 0, 1.5)); kf(cl, 'location', f1, (3.2, 0, 1.9)); kf_ease(cl)
    for o, c0, c1 in ((na, (0.95, 0.5, 0.15, 1), (0.22, 0.32, 0.95, 1)), (cl, (0.25, 0.65, 0.95, 1), (0.95, 0.75, 0.2, 1))):
        p = o.data.materials[0].node_tree.nodes['Principled BSDF']; p.inputs['Base Color'].default_value = c0; p.inputs['Base Color'].keyframe_insert('default_value', frame=f0); p.inputs['Base Color'].default_value = c1; p.inputs['Base Color'].keyframe_insert('default_value', frame=f1)
    cam, tgt = camera((0, -10.0, 2.0), (0, 0, 1.6), lens=45); dolly(cam, tgt, 1, nf, (0, -10.0, 2.0), (0, -10.5, 2.0))

def beaker_cao_water(nf, rfps, dur):
    reset(); world(0.004, 0.006, 0.014); stage_void(target=(0, 0, 1.0), key_e=1600, spot=60)
    bk = glass_beaker((0, 0, 0), r=1.3, h=1.9)
    kf(bk, 'scale', 1, (0.2, 0.2, 0.2)); kf(bk, 'scale', F(2.5, rfps), (1, 1, 1)); kf_ease(bk)
    # powder pile grows 4..10 s ; falling white grains 4..9 s
    pw, _, md = powder_pile((0, 0, 0.05), 60, 0.5, 0.045, (0.95, 0.95, 0.93), name='CaO', flat=0.7)
    for i, g in enumerate(pw):
        fa = F(3.5 + 4.0 * i / len(pw), rfps); kf(g, 'hide_render', 1, True); kf(g, 'hide_render', fa, False)
    kf(md, 'scale', F(3.5, rfps), (0.05, 0.05, 0.01)); kf(md, 'scale', F(7.5, rfps), (1, 1, 1)); kf_lin(md)
    rnd = random.Random(4); gm = M_powder((0.95, 0.95, 0.93), 'grain')
    for i in range(50):
        t0 = rnd.uniform(3.0, 7.0); f0 = F(t0, rfps); f1 = F(t0 + 0.9, rfps)
        s = spark(f'Grain{i}', gm, r=0.04)
        kf(s, 'hide_render', 1, True); kf(s, 'hide_render', f0, False); kf(s, 'hide_render', f1, True)
        kf(s, 'location', f0, (rnd.uniform(-0.25, 0.25), rnd.uniform(-0.2, 0.2), 5.0)); kf(s, 'location', f1, (rnd.uniform(-0.5, 0.5), rnd.uniform(-0.4, 0.4), 0.1)); kf_lin(s)
    # water stream 10..15 s and level rising
    stream = obj_add('cylinder', 'Stream', radius=0.09, depth=5.0, vertices=32, location=(0.15, 0, 2.6)); subdiv_side_edges(stream, 30); smooth(stream); setmat(stream, M_water('stream')); displace(stream, 'ripple', strength=0.03, scale=0.15)
    kf(stream, 'hide_render', 1, True); kf(stream, 'hide_render', F(7.0, rfps), False); kf(stream, 'hide_render', F(12.0, rfps), True)
    liq = liquid_in_beaker((0, 0, 0), 1.3, 1.2, (0.55, 0.78, 0.98), absorb=1.0, scatter=0.25)
    kf(liq, 'scale', 1, (1, 1, 0.01)); kf(liq, 'scale', F(7.0, rfps), (1, 1, 0.01)); kf(liq, 'scale', F(12.5, rfps), (1, 1, 1)); kf_lin(liq)
    cam, tgt = camera((0, -9.0, 2.2), (0, 0, 1.0), lens=50); dolly(cam, tgt, 1, nf, (0, -9.0, 2.2), (0, -8.4, 2.1))

def beaker_glow(nf, rfps, dur):
    reset(); world(0.004, 0.006, 0.014); stage_void(target=(0, 0, 1.0), key_e=1400, spot=60)
    bk = glass_beaker((0, 0, 0), r=1.3, h=1.9); liq = liquid_in_beaker((0, 0, 0), 1.3, 1.25, (0.55, 0.78, 0.98), absorb=1.4, scatter=0.5)
    pw, _, md = powder_pile((0, 0, 0.05), 50, 0.5, 0.045, (0.95, 0.95, 0.93), name='CaO', flat=0.7)
    lm = liq.data.materials[0]; p = lm.node_tree.nodes['Principled BSDF']
    f0, f1 = F(1.0, rfps), F(4.5, rfps)
    key_liquid_color(lm, f0, (0.55, 0.78, 0.98)); key_liquid_color(lm, f1, (0.95, 0.3, 0.06))
    p.inputs['Emission Color'].default_value = (1.0, 0.28, 0.04, 1); p.inputs['Emission Strength'].default_value = 0.0; p.inputs['Emission Strength'].keyframe_insert('default_value', frame=f0)
    p.inputs['Emission Strength'].default_value = 0.6; p.inputs['Emission Strength'].keyframe_insert('default_value', frame=f1)
    if not CYC(): p.inputs['Alpha'].default_value = 0.95
    hl = light('POINT', (0, 0, 0.7), 0, (1.0, 0.45, 0.1), 'HeatLight'); kf(hl.data, 'energy', f0, 0); kf(hl.data, 'energy', f1, 50)
    cam, tgt = camera((0, -7.5, 1.9), (0, 0, 0.9), lens=50); dolly(cam, tgt, 1, F(2.5, rfps), (0, -7.5, 1.9), (0, -10.5, 2.4)); kf(cam, 'location', nf, (0, -10.5, 2.4))

def boiling_tube(nf, rfps, dur):
    reset(); world(0.004, 0.006, 0.014); stage_void(target=(0, 0, 1.6), key_e=1400, spot=70)
    tb = glass_tube((0, 0, 0), r=0.42, h=4.2, name='BoilTube')
    kf(tb, 'scale', 1, (0.35, 0.35, 0.35)); kf(tb, 'scale', F(5.0, rfps), (1, 1, 1)); kf_ease(tb)
    cm = M_crystal((0.3, 0.9, 0.25), 'FeSO4_m'); fill = lathe('FeSO4Mass', prof_tube_fill(0.42, 0.30), (0, 0, 0), verts=96, cap_bottom=False, mat=cm)
    gr, _, _ = powder_pile((0, 0, 0.32), 45, 0.28, 0.06, (0.3, 0.9, 0.25), name='FeSO4', flat=0.8, mat=cm, mound=False)
    kf(fill, 'scale', F(5.0, rfps), (0.4, 0.4, 0.05)); kf(fill, 'scale', F(8.0, rfps), (1, 1, 1)); kf_lin(fill)
    for i, g in enumerate(gr):
        fa = F(5.0 + 3.0 * i / len(gr), rfps); kf(g, 'hide_render', 1, True); kf(g, 'hide_render', fa, False)
    rnd = random.Random(6)
    for i in range(24):
        t0 = rnd.uniform(4.5, 8.0); f0 = F(t0, rfps); f1 = F(t0 + 0.7, rfps)
        s = spark(f'Cr{i}', cm, r=0.05)
        kf(s, 'hide_render', 1, True); kf(s, 'hide_render', f0, False); kf(s, 'hide_render', f1, True)
        kf(s, 'location', f0, (rnd.uniform(-0.1, 0.1), 0, 5.2)); kf(s, 'location', f1, (rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2), 0.35)); kf_lin(s)
    cam, tgt = camera((0, -9.0, 2.0), (0, 0, 1.8), lens=50); dolly(cam, tgt, 1, nf, (0, -9.0, 2.0), (0, -8.5, 2.0))

def tube_heat(nf, rfps, dur):
    reset(); world(0.004, 0.006, 0.014); stage_void(target=(0, 0, 1.6), key_e=1200, spot=70)
    tb = glass_tube((0, 0, 0), r=0.42, h=4.2, name='BoilTube')
    gm = M_crystal((0.3, 0.9, 0.25), 'FeSO4_m'); lathe('FeSO4Mass', prof_tube_fill(0.42, 0.30), (0, 0, 0), verts=96, cap_bottom=False, mat=gm)
    powder_pile((0, 0, 0.32), 45, 0.28, 0.06, (0.3, 0.9, 0.25), name='FeSO4', flat=0.8, mat=gm, mound=False)
    p = gm.node_tree.nodes['Principled BSDF']
    for f, c in ((F(6.0, rfps), (0.3, 0.9, 0.25, 1)), (F(9.5, rfps), (0.95, 0.6, 0.1, 1)), (F(14.0, rfps), (0.75, 0.2, 0.08, 1))):
        p.inputs['Base Color'].default_value = c; p.inputs['Base Color'].keyframe_insert('default_value', frame=f)
    lamp, body, fl, L, rig = spirit_lamp_v2((0, 0, -4.0), nf=nf); flicker(fl, 1, nf, seed=8)
    kf(lamp, 'location', 1, (0, 0, -9.0)); kf(lamp, 'location', F(1.0, rfps), (0, 0, -9.0)); kf(lamp, 'location', F(4.0, rfps), (0, 0, -3.3)); kf_ease(lamp)
    kf(rig, 'scale', F(4.0, rfps), (1.0, 1.0, 1.0)); kf(rig, 'scale', F(7.0, rfps), (1.3, 1.3, 1.3)); kf_ease(rig)
    cam, tgt = camera((0, -9.5, 0.8), (0, 0, 0.6), lens=50); dolly(cam, tgt, 1, F(6.0, rfps), (0, -9.5, 0.8), (0, -10.5, 0.4), (0, 0, 0.6), (0, 0, -0.2))

def three_nails(nf, rfps, dur):
    reset(); world(0.004, 0.006, 0.014); stage_void(target=(0, 0, 1.5), key_e=1300, spot=70)
    for i, x in enumerate((-1.3, 0, 1.3)):
        n, m = nail_v2((x, 0, 0.4), L=2.6, r=0.06, name=f'Nail{i}'); n.rotation_euler = (0, 0, 0)
        kf(n, 'rotation_euler', 1, (0, 0.0, 0)); kf(n, 'rotation_euler', nf, (0, 0.35, 0)); kf_lin(n)
    cam, tgt = camera((0, -9.0, 2.0), (0, 0, 1.6), lens=50); dolly(cam, tgt, 1, nf, (0, -9.0, 2.0), (0, -8.6, 2.0))

def _two_tubes(rfps, fill_at=None, colors=((0.08, 0.15, 0.85), (0.08, 0.15, 0.85)), sep=2.6, level=1.5):
    reset(); world(0.004, 0.006, 0.014); stage_void(target=(0, 0, 1.6), key_e=1300, spot=70); tubes = []
    for i, x in enumerate((-sep / 2, sep / 2)):
        tb = glass_tube((x, 0, 0), r=0.36, h=3.4, name=f'Tube{i}'); lq = liquid_in_tube((x, 0, 0), 0.36, level, colors[i], name=f'Liq{i}')
        if fill_at is not None:
            kf(lq, 'scale', 1, (1, 1, 0.02)); kf(lq, 'scale', F(fill_at, rfps), (1, 1, 0.02)); kf(lq, 'scale', F(fill_at + 4.0, rfps), (1, 1, 1)); kf_lin(lq)
        tubes.append((tb, lq))
    return tubes

def two_tubes_fill(nf, rfps, dur):
    _two_tubes(rfps, fill_at=3.0)
    cam, tgt = camera((0, -9.5, 2.0), (0, 0, 1.6), lens=50); dolly(cam, tgt, 1, nf, (0, -9.5, 2.0), (0, -9.0, 2.0))

def stand_nail(nf, rfps, dur):
    reset(); world(0.004, 0.006, 0.014); stage_void(target=(0, 0, 2.2), key_e=1400, spot=70)
    retort_stand_v2((0, 0, 0), h=5.5); tb = glass_tube((0.35, 0, 1.6), r=0.36, h=3.4, name='TubeB'); liquid_in_tube((0.35, 0, 1.6), 0.36, 1.6, (0.08, 0.15, 0.85), name='LiqB')
    n, m = nail_v2((0.35, 0, 5.8), L=1.6, r=0.05, name='NailB')
    thread = curve_obj('Thread', [(0.35, 0, 5.8 + 1.55), (0.36, 0.01, 5.8 + 2.6), (0.34, -0.01, 5.8 + 3.6)], bevel_r=0.012, res=4, mat=mat_plastic((0.9, 0.9, 0.9), rough=0.7, name='thread'))
    thread.parent = n; thread.matrix_parent_inverse = n.matrix_world.inverted()
    kf(n, 'location', F(6.0, rfps), (0.35, 0, 5.8)); kf(n, 'location', F(11.0, rfps), (0.35, 0, 1.75)); kf_ease(n)
    cam, tgt = camera((1.2, -11.0, 3.2), (0, 0, 2.6), lens=45); dolly(cam, tgt, 1, nf, (1.2, -11.0, 3.2), (1.0, -9.0, 3.0), (0, 0, 2.6), (0.3, 0, 2.4))

def rack_tubes(nf, rfps, dur):
    reset(); world(0.004, 0.006, 0.014); stage_void(target=(0, 0, 1.4), key_e=1500, spot=60)
    tube_rack_v2((0, 0, 0), w=4.4, d=1.6, h=2.3, holes=(-0.9, 0.9), hole_r=0.42, hole_y=-0.2)
    for i, x in enumerate((-0.9, 0.9)):
        tb = glass_tube((x, -0.2, 0.5), r=0.34, h=3.2, name=f'Tube{i}'); lq = liquid_in_tube((x, -0.2, 0.5), 0.34, 1.6, (0.08, 0.15, 0.85), name=f'Liq{i}')
        if i == 1:
            lm = lq.data.materials[0]; key_liquid_color(lm, F(12.0, rfps), (0.08, 0.15, 0.85)); key_liquid_color(lm, F(16.0, rfps), (0.35, 0.75, 0.6))
            rm, fac = M_steel_rust('nailB_m'); n, m = nail_v2((x, -0.2, 0.62), L=1.5, r=0.045, mat=rm, name='NailB')
            key_rust(fac, F(12.0, rfps), 0.0); key_rust(fac, F(16.0, rfps), 1.0)
    cam, tgt = camera((0.5, -9.5, 2.8), (0, 0, 1.4), lens=50); dolly(cam, tgt, 1, nf, (0.5, -9.5, 2.8), (0.2, -8.5, 2.6))

def nails_compare(nf, rfps, dur):
    reset(); world(0.004, 0.006, 0.014); stage_void(target=(0, 0, 1.5), key_e=1300, spot=70)
    nail_v2((-1.1, 0, 0.5), L=2.4, r=0.055, name='NailA'); rm, fac = M_steel_rust('rusty', steel=(0.75, 0.45, 0.2)); key_rust(fac, 1, 1.0); nail_v2((1.1, 0, 0.5), L=2.4, r=0.055, mat=rm, name='NailB')
    cam, tgt = camera((0, -9.0, 2.0), (0, 0, 1.6), lens=50); dolly(cam, tgt, 1, nf, (0, -9.0, 2.0), (0, -9.2, 2.0))

def two_tubes_dd(nf, rfps, dur):
    tubes = _two_tubes(rfps, colors=((0.08, 0.15, 0.85), (0.75, 0.15, 0.35)), sep=3.2)
    tb1, lq1 = tubes[1]
    for o in (tb1, lq1): kf(o, 'hide_render', 1, True); kf(o, 'hide_render', F(9.0, rfps), False)
    cam, tgt = camera((0, -9.5, 2.0), (0, 0, 1.6), lens=50)
    kf(cam, 'location', 1, (-1.6, -8.0, 2.0)); kf(cam, 'location', F(8.0, rfps), (-1.6, -8.0, 2.0)); kf(cam, 'location', F(10.0, rfps), (0, -9.5, 2.0))
    kf(tgt, 'location', 1, (-1.6, 0, 1.6)); kf(tgt, 'location', F(8.0, rfps), (-1.6, 0, 1.6)); kf(tgt, 'location', F(10.0, rfps), (0, 0, 1.6)); kf_ease(cam); kf_ease(tgt)

def pour_beaker(nf, rfps, dur):
    reset(); world(0.004, 0.006, 0.014); stage_void(target=(0, 0, 1.2), key_e=1500, spot=65)
    bk = glass_beaker((0, 0, 0), r=1.1, h=1.8)
    lq = liquid_in_beaker((0, 0, 0), 1.1, 1.2, (0.12, 0.25, 0.9), absorb=2.4, scatter=0.5); kf(lq, 'scale', 1, (1, 1, 0.02)); kf(lq, 'scale', F(2.0, rfps), (1, 1, 0.02)); kf(lq, 'scale', F(9.0, rfps), (1, 1, 1)); kf_lin(lq)
    ppt = liquid_in_beaker((0, 0, 0), 1.1, 0.35, (0.95, 0.95, 0.97), name='Ppt', mat=M_milk()); kf(ppt, 'scale', 1, (1, 1, 0.02)); kf(ppt, 'scale', F(8.0, rfps), (1, 1, 0.02)); kf(ppt, 'scale', F(14.0, rfps), (1, 1, 1)); kf_lin(ppt)
    for i, (x, col) in enumerate(((-2.4, (0.08, 0.15, 0.85)), (2.4, (0.75, 0.15, 0.35)))):
        s = 1 if x < 0 else -1
        root = empty(f'TubeRoot{i}', (x, 0, 3.4))                       # pivot = tube mouth
        tb = glass_tube((0, 0, -3.2), r=0.34, h=3.2, name=f'Tube{i}'); lqt = liquid_in_tube((0, 0, -3.2), 0.34, 1.4, col, name=f'TLiq{i}')
        tb.parent = root; lqt.parent = root
        kf(root, 'rotation_euler', 1, (0, 0, 0)); kf(root, 'rotation_euler', F(1.5, rfps), (0, 0, 0)); kf(root, 'rotation_euler', F(3.5, rfps), (0, s * math.radians(125), 0)); kf(root, 'rotation_euler', F(9.0, rfps), (0, s * math.radians(125), 0)); kf(root, 'rotation_euler', F(11.0, rfps), (0, s * math.radians(100), 0)); kf_ease(root)
        kf(root, 'location', 1, (x, 0, 3.4)); kf(root, 'location', F(1.5, rfps), (x, 0, 3.4)); kf(root, 'location', F(3.5, rfps), (x * 0.4, 0, 2.5)); kf(root, 'location', F(11.0, rfps), (x * 0.55, 0, 2.9)); kf_ease(root)
        kf(lqt, 'scale', F(3.0, rfps), (1, 1, 1)); kf(lqt, 'scale', F(9.0, rfps), (1, 1, 0.05)); kf_lin(lqt)
        st = obj_add('cylinder', f'Stream{i}', radius=0.05, depth=2.2, vertices=32, location=(x * 0.3, 0, 1.4)); subdiv_side_edges(st, 20); smooth(st); setmat(st, M_liquid(col, absorb=3.0, scatter=0.8, name=f'st{i}')); displace(st, f'ripple{i}', strength=0.02, scale=0.12)
        kf(st, 'hide_render', 1, True); kf(st, 'hide_render', F(3.2, rfps), False); kf(st, 'hide_render', F(9.0, rfps), True)
    cam, tgt = camera((0, -9.5, 2.4), (0, 0, 1.4), lens=50); dolly(cam, tgt, 1, nf, (0, -9.5, 2.4), (0, -9.0, 2.3))

def beaker_small(nf, rfps, dur):
    reset(); world(0.004, 0.006, 0.014); stage_void(target=(0, 0, 1.2), key_e=1500, spot=65)
    bk = glass_beaker((0, 0, 0), r=1.1, h=1.8); liquid_in_beaker((0, 0, 0), 1.1, 1.2, (0.12, 0.25, 0.9), absorb=2.4, scatter=0.5); liquid_in_beaker((0, 0, 0), 1.1, 0.35, (0.95, 0.95, 0.97), name='Ppt', mat=M_milk())
    for i, x in enumerate((-2.2, 2.2)):
        root = empty(f'TubeRoot{i}', (x * 0.55, 0, 2.9)); tb = glass_tube((0, 0, -3.2), r=0.34, h=3.2, name=f'Tube{i}'); tb.parent = root; root.rotation_euler = (0, (1 if x < 0 else -1) * math.radians(100), 0)
    cam, tgt = camera((5.5, -15.0, 3.4), (3.5, 0, 2.6), lens=45); dolly(cam, tgt, 1, nf, (5.5, -15.0, 3.4), (5.8, -15.5, 3.5))

def _tripod_scene(nf, rfps, powder_col=(0.85, 0.45, 0.12), h_particles=False, o_particles=False, f0=1):
    reset(); world(0.004, 0.006, 0.014); stage_void(target=(0, 0, 2.5), key_e=1400, spot=70)
    tripod_v2((0, 0, 0), h=3.6, r=1.6); gauze_v2((0, 0, 3.66), size=4.2, n=10)
    dish = china_dish_v2((0, 0, 3.72), r=2.1)
    gr, gm, md = powder_pile((0, 0, 3.8), 130, 0.75, 0.068, powder_col, name='Cu', flat=0.9, metallic=0.3)
    lamp, body, fl, L, rig = spirit_lamp_v2((0, 0, 0.0), r=0.36, h=2.4, nf=nf); flicker(fl, 1, nf, seed=12)
    rig.scale = (1.5, 1.5, 1.4)
    out = dict(dish=dish, gm=gm, fl=fl, lamp=lamp, rig=rig)
    if h_particles:
        out['H'] = specks(18, (0, 0, 5.3), (1.3, 0.8, 0.7), r=0.035, color=(1.0, 0.3, 0.3), strength=1.0, seed=21, f0=1, f1=nf, drift=0.35, name='Hp')
    if o_particles:
        out['O'] = specks(22, (0, 0, 5.1), (1.4, 0.8, 0.7), r=0.035, color=(0.35, 0.6, 1.0), strength=1.0, seed=22, f0=1, f1=nf, drift=0.35, name='Op')
    return out

def tripod_push(nf, rfps, dur):
    sc = _tripod_scene(nf, rfps, h_particles=True, o_particles=True)
    for o in sc['H']: kf(o, 'hide_render', 1, True); kf(o, 'hide_render', F(16.0, rfps), False)
    for o in sc['O']: kf(o, 'hide_render', 1, True); kf(o, 'hide_render', F(9.0, rfps), False)
    cam, tgt = camera((0, -16.0, 3.0), (0, 0, 2.4), lens=45); dolly(cam, tgt, 1, F(13.0, rfps), (0, -16.0, 3.0), (0, -8.5, 5.2), (0, 0, 2.4), (0, 0, 4.2))
    kf(cam, 'location', nf, (0, -8.5, 5.2)); kf(tgt, 'location', nf, (0, 0, 4.2))
    focus_pull(cam, 1, F(13.0, rfps), sc['lamp'], sc['dish'])

def tripod_wide(nf, rfps, dur):
    sc = _tripod_scene(nf, rfps, o_particles=True)
    for o in sc['O']: kf(o, 'hide_render', 1, True); kf(o, 'hide_render', F(3.0, rfps), False)
    kf(sc['rig'], 'scale', F(6.0, rfps), (1.5, 1.5, 1.4)); kf(sc['rig'], 'scale', F(11.0, rfps), (1.9, 1.9, 1.9)); kf_ease(sc['rig'])
    cam, tgt = camera((0, -10.5, 4.6), (0, 0, 3.6), lens=45); dolly(cam, tgt, 1, nf, (0, -10.5, 4.6), (0, -13.5, 3.4), (0, 0, 3.6), (0, 0, 2.6))

def dish_close(nf, rfps, dur):
    sc = _tripod_scene(nf, rfps, h_particles=True, o_particles=True); sc['rig'].scale = (1.9, 1.9, 1.9)
    for o in sc['O']: kf(o, 'hide_render', 1, False); kf(o, 'hide_render', F(18.0, rfps), True)
    for o in sc['H']: kf(o, 'hide_render', 1, True); kf(o, 'hide_render', F(19.0, rfps), False)
    p = sc['gm'].node_tree.nodes['Principled BSDF']
    for f, c in ((F(3.0, rfps), (0.85, 0.45, 0.12, 1)), (F(8.0, rfps), (0.12, 0.1, 0.09, 1)), (F(26.0, rfps), (0.12, 0.1, 0.09, 1)), (F(34.0, rfps), (0.7, 0.35, 0.12, 1))):
        p.inputs['Base Color'].default_value = c; p.inputs['Base Color'].keyframe_insert('default_value', frame=f)
    cam, tgt = camera((0, -8.8, 5.4), (0, 0, 4.3), lens=45); dolly(cam, tgt, 1, nf, (0, -8.8, 5.4), (0, -8.4, 5.3))

def corrosion_trio(nf, rfps, dur):
    reset(); world(0.004, 0.006, 0.014); stage_void(target=(0, 0, 1.3), key_e=1400, spot=70)
    rm, fac = M_steel_rust('steel')
    rg = obj_add('torus', 'Ring', major_radius=0.65, minor_radius=0.13, major_segments=128, minor_segments=40, location=(-2.2, 0, 0.5)); smooth(rg); setmat(rg, rm)
    rd = obj_add('cylinder', 'Rod', radius=0.2, depth=2.6, vertices=64, location=(0, 0, 0.2 + 1.3)); bevel(rd, 0.05, 8); smooth(rd); setmat(rd, rm)
    for i, x in enumerate((1.8, 2.15, 2.5, 2.85)): nail_v2((x, 0, 0.9), L=1.4, r=0.04, mat=rm, name=f'N{i}')
    key_rust(fac, F(6.0, rfps), 0.0); key_rust(fac, F(11.0, rfps), 1.0)
    cam, tgt = camera((0, -9.5, 3.2), (0, 0, 1.0), lens=50); dolly(cam, tgt, 1, nf, (0, -9.5, 3.2), (0, -9.0, 3.1))

def _rust_nail_scene(nf, rfps, rust_from=4.0, rust_to=10.0, particles=True, particles_from=2.0):
    reset(); world(0.004, 0.006, 0.014); stage_void(target=(0, 0, 1.6), key_e=1300, spot=70)
    n, m = nail_v2((0, 0, 0.3), L=2.9, r=0.07, name='Nail')
    coat, flakes = rust_coat((0, 0, 0.3), 2.9, 0.07)
    kf(coat, 'scale', F(rust_from, rfps), (0.01, 0.01, 0.0)); kf(coat, 'scale', F(rust_to, rfps), (1.0, 1.0, 1.0)); kf_lin(coat)
    if particles:
        fl_ = specks(60, (0, 0, 1.7), (4.5, 2.0, 2.6), r=0.045, color=(1.0, 0.55, 0.45), strength=1.2, seed=31, f0=1, f1=nf, drift=0.45, name='Rp')
        if particles_from > 0:
            for o in fl_: kf(o, 'hide_render', 1, True); kf(o, 'hide_render', F(particles_from, rfps), False)
    return n

def nail_rust(nf, rfps, dur):
    _rust_nail_scene(nf, rfps)
    cam, tgt = camera((0, -9.0, 2.0), (0, 0, 1.7), lens=50); dolly(cam, tgt, 1, nf, (0, -9.0, 2.0), (0, -8.8, 2.0))

def nail_rust_pull(nf, rfps, dur):
    _rust_nail_scene(nf, rfps, rust_from=-2, rust_to=-1, particles_from=0)
    cam, tgt = camera((0, -8.8, 2.0), (0, 0, 1.7), lens=50); dolly(cam, tgt, 1, nf, (0, -8.8, 2.0), (0, -13.5, 2.4))

def rancidity(nf, rfps, dur):
    reset(); world(0.004, 0.006, 0.014); stage_void(target=(0, 0, 1.0), key_e=1600, spot=60)
    plate_v2((0, 0, 0), r=2.7); food, bits = cake_v2((0, 0, 0.25), r=1.7)
    light_cone(top=(-4.0, 4.0, 11), base=(0, 0, 0.3), r_top=0.25, r_base=1.9, alpha=0.05)
    dots = mould_v2((0, 0, 0.25), 1.7)
    for i, d in enumerate(dots):
        fa = F(24.0 + 8.0 * i / len(dots), rfps); kf(d, 'hide_render', 1, True); kf(d, 'hide_render', fa, False)
    specks(50, (0, 0, 2.0), (5.0, 2.5, 2.5), r=0.05, color=(1.0, 0.6, 0.5), strength=1.2, seed=41, f0=1, f1=nf, drift=0.4, name='Rp')
    cam, tgt = camera((0, -8.0, 2.6), (0, 0, 0.9), lens=50)
    dolly(cam, tgt, 1, F(3.0, rfps), (0, -8.0, 2.6), (0, -8.0, 2.6)); kf(cam, 'location', F(15.0, rfps), (0, -8.0, 2.6)); kf(cam, 'location', F(18.0, rfps), (0, -16.0, 4.0))
    kf(cam, 'location', F(23.0, rfps), (0, -16.0, 4.0)); kf(cam, 'location', F(24.5, rfps), (0, -6.0, 2.2)); kf(cam, 'location', nf, (0.6, -5.8, 2.1)); kf_ease(cam)

BUILDERS = {k: v for k, v in globals().items() if callable(v) and not k.startswith('_') and k not in ('F',)}
