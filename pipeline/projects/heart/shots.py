"""Blender builders for every 3D shot of 'Human Heart and Circulation' (Class 10, Life Processes) - an ORIGINAL chapter.
Each builder(nf, rfps, dur) resets the scene, builds, animates frames 1..nf and creates the camera (at -Y looking +Y, Z up).
The body faces the camera, so anatomical LEFT is +X (the viewer's right), exactly like a textbook front view.
Every colour comes from projects/heart/palette.py (linear floats here, 8-bit twins on the overlay).

Organic toolkit (all project-local, kit.py is untouched):
  heart()          the hero: metaball-sculpted myocardium -> mesh; four REAL cavities cut in with an exact boolean (right side
                   lined violet-rose, left side crimson-rose), optional front cutaway (angled cut plane) that exposes wall
                   thickness (LV thickest, atria thin, a thick septum), trabeculae carneae ridges, papillary muscles with chordae
                   tendineae to the AV leaflets (tricuspid 3, mitral 2), three semilunar cusps at each artery mouth, hollow
                   great vessels whose cut mouths show wall thickness; outside: epicardial fat pads in the grooves, a branching
                   coronary tree (trunks + 2nd/3rd-order branches + cardiac veins), wet pericardial coat, fine bump + vein noise;
                   contraction shape keys (atria / vent) and a whole-heart beat.
  lungs(), torso(), ribcage(), fist(), muscle_fibres(), av_valve() / semilunar_valve() hero rigs, vessel_section() (three-layer
  wall), vein_valves(), capillary_bed() (single-cell wall), rbc()/rbc_flow() (biconcave cells on Follow-Path), haemoglobin(),
  organ blobs, loop_diagram(), fish(), gauge(), cuff_arm(), stethoscope(); motes()/backglow()/fg_cells() for the environment.
"""
import math, random, bpy, os, sys, bmesh
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from mathutils import Vector, Matrix, Euler
from kit import *
from kit import _principled, _inp, _resample_profile, _fcurves
from projects.heart import palette as P
from projects.heart.palette import (VOID, OXY, OXY_LIT, DEOXY, DEOXY_LIT, MUSCLE, MUSCLE_DK, MUSCLE_LIT, CUT, CUT_FIBRE, ENDO, ENDO_EMIT,
                                    ENDO_R, ENDO_L, CHORDAE, FAT, BONE, CARTILAGE, LUNG, LUNG_RIM, SKIN, SKIN_RIM, CAPILLARY, NUCLEUS,
                                    ARTERY_WALL, INTIMA, ADVENTITIA, VEIN_WALL, ORGAN, BRAIN, KIDNEY, HAEMOGLOBIN, HAEM_IRON, O2, CO2,
                                    NUTRIENT, WASTE, PLASMA, DUST, GOLD, CYAN, DANGER, WHITE, CHROME, RUBBER, CUFF, DIAL, NEEDLE, THEME)

def F(sec, rfps): return int(round(sec * rfps)) + 1     # seconds -> frame number (1-based)
CY = is_cycles()
DOF = os.environ.get('VL_DOF', '0') == '1'

# legacy aliases (older helpers below still use these names; they now resolve to the palette)
RED, RED_LIT, BLUE, BLUE_LIT, PINK = OXY, OXY_LIT, DEOXY, DEOXY_LIT, ENDO

def smooth01(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)
def lerp(a, b, u): return a + (b - a) * u
def vlerp(a, b, u): return Vector(a) * (1 - u) + Vector(b) * u

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
    """Soft waxy organic surface: subsurface + a light coat. The house look for tissue."""
    m, p = _principled(name)
    _inp(p, 'Base Color', (*color, 1)); _inp(p, 'Roughness', rough); _inp(p, 'Coat Weight', coat); _inp(p, 'Coat Roughness', 0.15)
    _inp(p, 'Subsurface Weight', sss); _inp(p, 'Subsurface Scale', scale); _inp(p, 'Specular IOR Level', spec)
    _inp(p, 'Subsurface Radius', radius or (color[0] * 1.2 + 0.2, color[1] * 0.8 + 0.1, color[2] * 0.6 + 0.05))
    return m

def _noise_bump(m, p, scale=16.0, strength=0.08, detail=6.0, distance=0.05, prev=None):
    """Add a fine noise bump layer to a Principled material (chained after `prev` bump node if given)."""
    nt = m.node_tree; n = nt.nodes
    tc = n.new('ShaderNodeTexCoord'); vn = n.new('ShaderNodeTexNoise'); vn.inputs['Scale'].default_value = scale; vn.inputs['Detail'].default_value = detail; vn.inputs['Roughness'].default_value = 0.7
    b = n.new('ShaderNodeBump'); b.inputs['Strength'].default_value = strength; b.inputs['Distance'].default_value = distance
    nt.links.new(tc.outputs['Object'], vn.inputs['Vector']); nt.links.new(vn.outputs['Fac'], b.inputs['Height'])
    if prev is not None: nt.links.new(prev.outputs['Normal'], b.inputs['Normal'])
    nt.links.new(b.outputs['Normal'], p.inputs['Normal'])
    return b

def mat_blotch(base, spot, scale=5.0, lo=0.42, hi=0.62, rough=0.5, sss=0.25, name='blotch', detail=3.0, bump=0.0, coat=0.12):
    """Ground colour with soft darker blotches (noise -> ramp -> base colour), optional bump from the same noise."""
    m, p = _principled(name); nt = m.node_tree; n = nt.nodes
    tc = n.new('ShaderNodeTexCoord'); noise = n.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = scale; noise.inputs['Detail'].default_value = detail; noise.inputs['Roughness'].default_value = 0.55
    ramp = n.new('ShaderNodeValToRGB'); e = ramp.color_ramp.elements
    e[0].position = lo; e[0].color = (*base, 1); e[1].position = hi; e[1].color = (*spot, 1)
    nt.links.new(tc.outputs['Object'], noise.inputs['Vector']); nt.links.new(noise.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], p.inputs['Base Color'])
    bmp = None
    if bump:
        bmp = n.new('ShaderNodeBump'); bmp.inputs['Strength'].default_value = bump
        nt.links.new(noise.outputs['Fac'], bmp.inputs['Height']); nt.links.new(bmp.outputs['Normal'], p.inputs['Normal'])
    _inp(p, 'Roughness', rough); _inp(p, 'Subsurface Weight', sss); _inp(p, 'Subsurface Scale', 0.1); _inp(p, 'Coat Weight', coat)
    _inp(p, 'Subsurface Radius', (base[0], base[1], base[2]))
    m['bump_node'] = bmp.name if bmp else ''
    return m, noise, ramp

def mat_muscle(name='muscle', split=False, coat=0.7):
    """Wet cardiac muscle under its pericardial sheen: deep wine ground with darker blotches, lighter fibre streaks, a
    two-scale bump (blotch + fine vein noise), high glossy coat. With split=True the material carries an animatable 'Split'
    value: 0 = plain muscle, 1 = right half tinted deoxygenated violet, left half crimson (the 'two pumps' beat)."""
    m, noise, ramp = mat_blotch(MUSCLE, MUSCLE_DK, scale=2.2, lo=0.36, hi=0.68, rough=0.30, sss=0.32, name=name, detail=4.0, bump=0.14, coat=coat)
    p = m.node_tree.nodes.get('Principled BSDF'); nt = m.node_tree; n = nt.nodes
    _inp(p, 'Coat Roughness', 0.08); _inp(p, 'Subsurface Radius', (0.9, 0.2, 0.1)); _inp(p, 'Subsurface Scale', 0.12); _inp(p, 'Specular IOR Level', 0.55)
    # fibre streaks: a stretched wave along z brightens ridges toward MUSCLE_LIT
    tc = n.new('ShaderNodeTexCoord'); mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1.0, 1.0, 0.18)
    wave = n.new('ShaderNodeTexWave'); wave.inputs['Scale'].default_value = 9.0; wave.inputs['Distortion'].default_value = 4.0; wave.inputs['Detail'].default_value = 2.0
    wr = n.new('ShaderNodeValToRGB'); we = wr.color_ramp.elements; we[0].position = 0.55; we[0].color = (0, 0, 0, 1); we[1].position = 0.95; we[1].color = (1, 1, 1, 1)
    fib = n.new('ShaderNodeMix'); fib.data_type = 'RGBA'; fib.inputs[7].default_value = (*MUSCLE_LIT, 1)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], wave.inputs['Vector']); nt.links.new(wave.outputs['Fac'], wr.inputs['Fac'])
    fac = n.new('ShaderNodeMath'); fac.operation = 'MULTIPLY'; fac.inputs[1].default_value = 0.22
    nt.links.new(wr.outputs['Color'], fac.inputs[0]); nt.links.new(fac.outputs[0], fib.inputs['Factor']); nt.links.new(ramp.outputs['Color'], fib.inputs[6])
    base_out = fib.outputs[2]
    bmp = n.get(m['bump_node']) if m['bump_node'] else None
    _noise_bump(m, p, scale=18.0, strength=0.07, detail=6.0, distance=0.04, prev=bmp)
    if split:
        tc2 = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); nt.links.new(tc2.outputs['Object'], sep.inputs['Vector'])
        mr = n.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -0.12; mr.inputs['From Max'].default_value = 0.12
        nt.links.new(sep.outputs['X'], mr.inputs['Value'])
        side = n.new('ShaderNodeMix'); side.data_type = 'RGBA'; side.inputs[6].default_value = (*DEOXY_LIT, 1); side.inputs[7].default_value = (*OXY_LIT, 1)
        nt.links.new(mr.outputs['Result'], side.inputs['Factor'])
        val = n.new('ShaderNodeValue'); val.name = 'Split'; val.label = 'Split'; val.outputs[0].default_value = 0.0
        # tint the BLOTCHED ground only part-way toward the side colour (the muscle texture survives), then the fibre streaks
        # and the two-scale bump stay on top; emission is a faint accent, never a flat glow
        fac2 = n.new('ShaderNodeMath'); fac2.operation = 'MULTIPLY'; fac2.inputs[1].default_value = 0.55; nt.links.new(val.outputs[0], fac2.inputs[0])
        sideD = n.new('ShaderNodeMix'); sideD.data_type = 'RGBA'; sideD.inputs[6].default_value = (*P.scale(DEOXY, 1.6), 1); sideD.inputs[7].default_value = (*P.scale(OXY, 1.3), 1)
        nt.links.new(mr.outputs['Result'], sideD.inputs['Factor'])
        mix = n.new('ShaderNodeMix'); mix.data_type = 'RGBA'; nt.links.new(fac2.outputs[0], mix.inputs['Factor'])
        nt.links.new(ramp.outputs['Color'], mix.inputs[6]); nt.links.new(sideD.outputs[2], mix.inputs[7])
        fib2 = n.new('ShaderNodeMix'); fib2.data_type = 'RGBA'; fib2.inputs[7].default_value = (*MUSCLE_LIT, 1)
        nt.links.new(fac.outputs[0], fib2.inputs['Factor']); nt.links.new(mix.outputs[2], fib2.inputs[6]); nt.links.new(fib2.outputs[2], p.inputs['Base Color'])
        em = n.new('ShaderNodeMath'); em.operation = 'MULTIPLY'; em.inputs[1].default_value = 0.22
        nt.links.new(val.outputs[0], em.inputs[0]); nt.links.new(em.outputs[0], p.inputs['Emission Strength']); nt.links.new(side.outputs[2], p.inputs['Emission Color'])
        m['split_node'] = 'Split'
    else: nt.links.new(base_out, p.inputs['Base Color'])
    return m

def set_split(m, keys):
    """keys = [(frame, value)] for the muscle 'Split' value node."""
    nd = m.node_tree.nodes.get('Split')
    for f, v in keys:
        nd.outputs[0].default_value = v; nd.outputs[0].keyframe_insert('default_value', frame=f)

def mat_endo(color, name='endo', emit=0.05, bump=0.09, depth=(0.04, 0.42), dark=0.2, ridges=0.35, plane=None, matte=False, ridge_scale=11.0, lip=None, ior=None, sss=None):
    """Chamber lining: wet rose MUSCLE (matte-ish, light coat, faintly warm-emissive) with trabecular RIDGES (a distorted
    wave pattern in colour + bump) and fine noise, plus DEPTH SHADING: the colour darkens with object-space Y (deeper
    behind the cut plane) so the hollows read as carved hollows, never as glass bulbs.
    plane=(pivot, normal): the depth is measured from THAT (tilted) section plane instead of along Y, so the darkening
    starts exactly at the cut lip. matte=True (the cutaway): IOR 1.0 (NO dielectric Fresnel at all: the grazing-angle
    sheen on the hollow's rim was what read as a glass bowl, measured with diag D/E), no coat, rough, fleshy subsurface,
    a low-frequency flesh blotch and coarser, higher-contrast ridges (ridge_scale) - a matte hole, never a glass dome.
    lip = brightness factor at the cut lip (the depth mask's near end)."""
    if matte: m = mat_organic(color, rough=0.85, sss=0.3 if sss is None else sss, coat=0.0, name=name, radius=(0.55, 0.14, 0.12), spec=0.0, scale=0.1)
    else: m = mat_organic(color, rough=0.5, sss=0.3 if sss is None else sss, coat=0.14, name=name, radius=(color[0] * 0.6 + 0.1, color[1] * 0.6 + 0.05, color[2] * 0.6 + 0.05), spec=0.38)
    p = m.node_tree.nodes.get('Principled BSDF'); nt = m.node_tree; n = nt.nodes
    if matte or ior is not None: _inp(p, 'IOR', 1.0 if ior is None else ior)
    _inp(p, 'Emission Color', (*ENDO_EMIT, 1)); _inp(p, 'Emission Strength', emit); _inp(p, 'Coat Roughness', 0.35)
    tc = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); mr = n.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = depth[0]; mr.inputs['From Max'].default_value = depth[1]; mr.inputs['To Min'].default_value = (0.9 if matte else 1.0) if lip is None else lip; mr.inputs['To Max'].default_value = dark
    deep = (0.02, 0.005, 0.01, 1) if not matte else (color[0] * 0.08, color[1] * 0.06, color[2] * 0.08, 1)
    mix = n.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.inputs[6].default_value = deep; mix.inputs[7].default_value = (*color, 1)
    nt.links.new(tc.outputs['Object'], sep.inputs['Vector']); nt.links.new(mr.outputs['Result'], mix.inputs['Factor'])
    if plane is not None:                                   # signed distance behind the section plane
        piv, nrm = plane
        sub = n.new('ShaderNodeVectorMath'); sub.operation = 'SUBTRACT'; sub.inputs[1].default_value = tuple(piv)
        dot = n.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'; dot.inputs[1].default_value = tuple(nrm)
        nt.links.new(tc.outputs['Object'], sub.inputs[0]); nt.links.new(sub.outputs['Vector'], dot.inputs[0]); nt.links.new(dot.outputs['Value'], mr.inputs['Value'])
    else: nt.links.new(sep.outputs['Y'], mr.inputs['Value'])
    col_out = mix.outputs[2]
    if matte:                                               # low-frequency flesh blotch: the lining is never one flat tone
        bn = n.new('ShaderNodeTexNoise'); bn.inputs['Scale'].default_value = 2.6; bn.inputs['Detail'].default_value = 3.0; bn.inputs['Roughness'].default_value = 0.5
        br = n.new('ShaderNodeValToRGB'); be = br.color_ramp.elements; be[0].position = 0.35; be[0].color = (0.62, 0.5, 0.52, 1); be[1].position = 0.7; be[1].color = (1.12, 1.06, 1.04, 1)
        bmix = n.new('ShaderNodeMix'); bmix.data_type = 'RGBA'; bmix.blend_type = 'MULTIPLY'; bmix.inputs['Factor'].default_value = 1.0
        nt.links.new(tc.outputs['Object'], bn.inputs['Vector']); nt.links.new(bn.outputs['Fac'], br.inputs['Fac'])
        nt.links.new(col_out, bmix.inputs[6]); nt.links.new(br.outputs['Color'], bmix.inputs[7]); col_out = bmix.outputs[2]
    prev = None
    if ridges:
        wave = n.new('ShaderNodeTexWave'); wave.inputs['Scale'].default_value = ridge_scale; wave.inputs['Distortion'].default_value = 7.0 if not matte else 5.5; wave.inputs['Detail'].default_value = 3.0
        try: wave.inputs['Detail Roughness'].default_value = 0.65
        except Exception: pass
        nt.links.new(tc.outputs['Object'], wave.inputs['Vector'])
        wr = n.new('ShaderNodeValToRGB'); e = wr.color_ramp.elements; e[0].position = 0.3; e[0].color = ((0.5, 0.42, 0.44, 1) if matte else (0.55, 0.55, 0.55, 1)); e[1].position = 0.75; e[1].color = (1, 1, 1, 1)
        nt.links.new(wave.outputs['Fac'], wr.inputs['Fac'])
        dk = n.new('ShaderNodeMix'); dk.data_type = 'RGBA'; dk.blend_type = 'MULTIPLY'; dk.inputs['Factor'].default_value = 0.62 if matte else 0.55
        nt.links.new(col_out, dk.inputs[6]); nt.links.new(wr.outputs['Color'], dk.inputs[7]); nt.links.new(dk.outputs[2], p.inputs['Base Color'])
        prev = n.new('ShaderNodeBump'); prev.inputs['Strength'].default_value = ridges; prev.inputs['Distance'].default_value = 0.03 if not matte else 0.05
        nt.links.new(wr.outputs['Color'], prev.inputs['Height'])
    else: nt.links.new(col_out, p.inputs['Base Color'])
    if bump: _noise_bump(m, p, scale=16.0, strength=bump, detail=5.0, distance=0.03, prev=prev)
    elif prev is not None: nt.links.new(prev.outputs['Normal'], p.inputs['Normal'])
    return m

def septum_nodes(m, x0=0.08, half=0.2, z0=-0.62, zhalf=0.95, color=P.scale(GOLD, 2.0), strength=0.85, base_emit=None, base_col=None):
    """Add a keyable 'Septum' value to a Principled material: gold emission on the muscle BAND between the two sides
    (object-space |x - x0| < half, |z - z0| < zhalf), so the septum lights up as the wall it is, with no slab."""
    p = m.node_tree.nodes.get('Principled BSDF'); nt = m.node_tree; n = nt.nodes
    tc = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sep.inputs['Vector'])
    def band(sock, c, h):
        sub = n.new('ShaderNodeMath'); sub.operation = 'SUBTRACT'; sub.inputs[1].default_value = c; nt.links.new(sock, sub.inputs[0])
        ab = n.new('ShaderNodeMath'); ab.operation = 'ABSOLUTE'; nt.links.new(sub.outputs[0], ab.inputs[0])
        mr = n.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = h; mr.inputs['From Max'].default_value = h * 0.4; mr.clamp = True
        nt.links.new(ab.outputs[0], mr.inputs['Value']); return mr.outputs['Result']
    mask = n.new('ShaderNodeMath'); mask.operation = 'MULTIPLY'; nt.links.new(band(sep.outputs['X'], x0, half), mask.inputs[0]); nt.links.new(band(sep.outputs['Z'], z0, zhalf), mask.inputs[1])
    val = n.new('ShaderNodeValue'); val.name = 'Septum'; val.label = 'Septum'; val.outputs[0].default_value = 0.0
    k = n.new('ShaderNodeMath'); k.operation = 'MULTIPLY'; nt.links.new(mask.outputs[0], k.inputs[0]); nt.links.new(val.outputs[0], k.inputs[1])
    st = n.new('ShaderNodeMath'); st.operation = 'MULTIPLY_ADD'; st.inputs[1].default_value = strength; st.inputs[2].default_value = base_emit if base_emit is not None else float(p.inputs['Emission Strength'].default_value)
    nt.links.new(k.outputs[0], st.inputs[0]); nt.links.new(st.outputs[0], p.inputs['Emission Strength'])
    tint = n.new('ShaderNodeMix'); tint.data_type = 'RGBA'; tint.blend_type = 'MULTIPLY'; tint.inputs['Factor'].default_value = 1.0; tint.inputs[6].default_value = (*color, 1); tint.inputs[7].default_value = (1, 1, 1, 1)
    bl = next((l for l in nt.links if l.to_socket == p.inputs['Base Color']), None)
    if bl is not None: nt.links.new(bl.from_socket, tint.inputs[7])            # gold x the fibre texture: the streaks stay visible inside the glow
    cm = n.new('ShaderNodeMix'); cm.data_type = 'RGBA'; cm.inputs[6].default_value = (*(base_col or tuple(p.inputs['Emission Color'].default_value)[:3]), 1)
    nt.links.new(tint.outputs[2], cm.inputs[7]); nt.links.new(k.outputs[0], cm.inputs['Factor']); nt.links.new(cm.outputs[2], p.inputs['Emission Color'])
    return val

def set_septum(h, keys):
    """keys = [(frame, 0..1)] for the septum highlight on the cutaway heart's cut-face and lining materials."""
    for m in h.get('septum_mats', []):
        nd = m.node_tree.nodes.get('Septum')
        for f, v in keys:
            nd.outputs[0].default_value = v; nd.outputs[0].keyframe_insert('default_value', frame=f)

def mat_cut(name='cutface'):
    """The sliced myocardium: dark wine with fine lighter fibre streaks running with the wall, matte, subsurface."""
    m, p = _principled(name); nt = m.node_tree; n = nt.nodes
    tc = n.new('ShaderNodeTexCoord'); mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1.0, 1.0, 0.45)
    wave = n.new('ShaderNodeTexWave'); wave.inputs['Scale'].default_value = 9.0; wave.inputs['Distortion'].default_value = 7.0; wave.inputs['Detail'].default_value = 3.0; wave.inputs['Detail Roughness'].default_value = 0.7
    noise = n.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 5.0; noise.inputs['Detail'].default_value = 5.0
    mul = n.new('ShaderNodeMath'); mul.operation = 'MULTIPLY_ADD'; mul.inputs[1].default_value = 0.5; nt.links.new(wave.outputs['Fac'], mul.inputs[0]); nt.links.new(noise.outputs['Fac'], mul.inputs[2])
    ramp = n.new('ShaderNodeValToRGB'); e = ramp.color_ramp.elements; e[0].position = 0.35; e[0].color = (*P.scale(CUT, 0.42), 1); e[1].position = 1.0; e[1].color = (*P.scale(CUT_FIBRE, 0.5), 1)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], wave.inputs['Vector']); nt.links.new(tc.outputs['Object'], noise.inputs['Vector'])
    nt.links.new(mul.outputs[0], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], p.inputs['Base Color'])
    bmp = n.new('ShaderNodeBump'); bmp.inputs['Strength'].default_value = 0.08; bmp.inputs['Distance'].default_value = 0.02
    nt.links.new(mul.outputs[0], bmp.inputs['Height']); nt.links.new(bmp.outputs['Normal'], p.inputs['Normal'])
    _inp(p, 'Roughness', 0.55); _inp(p, 'Subsurface Weight', 0.15); _inp(p, 'Subsurface Radius', (0.8, 0.2, 0.1)); _inp(p, 'Coat Weight', 0.15); _inp(p, 'Coat Roughness', 0.3)
    return m

def mat_vessel(color, name='vessel', rough=0.3, coat=0.5, sss=0.25, emit=0.0, veins=True, vein_scale=5.0):
    """Vessel wall: waxy organic ground, a faint network of surface vessels (vasa vasorum: Voronoi edges, slightly darker
    and sunk into the surface) and a fine noise bump so no vessel reads as a clean cylinder."""
    m = mat_organic(color, rough=rough, sss=sss, coat=coat, name=name)
    p = m.node_tree.nodes.get('Principled BSDF'); nt = m.node_tree; n = nt.nodes
    if emit: _inp(p, 'Emission Color', (*color, 1)); _inp(p, 'Emission Strength', emit)
    prev = None
    if veins:
        tc = n.new('ShaderNodeTexCoord'); vor = n.new('ShaderNodeTexVoronoi'); vor.feature = 'DISTANCE_TO_EDGE'; vor.inputs['Scale'].default_value = vein_scale
        try: vor.inputs['Randomness'].default_value = 0.85
        except Exception: pass
        ramp = n.new('ShaderNodeValToRGB'); e = ramp.color_ramp.elements; e[0].position = 0.0; e[0].color = (0.62, 0.62, 0.62, 1); e[1].position = 0.06; e[1].color = (1, 1, 1, 1)
        mixc = n.new('ShaderNodeMix'); mixc.data_type = 'RGBA'; mixc.blend_type = 'MULTIPLY'; mixc.inputs['Factor'].default_value = 0.8
        mixc.inputs[6].default_value = (*color, 1)
        nt.links.new(tc.outputs['Object'], vor.inputs['Vector']); nt.links.new(vor.outputs['Distance'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], mixc.inputs[7])
        nt.links.new(mixc.outputs[2], p.inputs['Base Color'])
        prev = n.new('ShaderNodeBump'); prev.inputs['Strength'].default_value = 0.25; prev.inputs['Distance'].default_value = 0.02
        nt.links.new(ramp.outputs['Color'], prev.inputs['Height'])
    _noise_bump(m, p, scale=9.0, strength=0.12, detail=5.0, distance=0.04, prev=prev)
    return m

def organic_mesh(o, disp_scale=0.7, disp_strength=0.03, sub=1):
    """Curve tube -> mesh with a soft noise displacement (organic wobble) and one subdivision level. Returns the new object."""
    o = to_mesh(o)
    if sub: subsurf(o, 0, sub)
    displace(o, scale=disp_scale, strength=disp_strength, name=o.name + '_d')
    smooth(o, auto=False); return o

def mat_rim(color, rim, a_center=0.12, a_rim=0.85, emit=2.0, name='rim', blend=0.35, rough=0.25, emit_min=0.0):
    """Translucent body whose edges glow (fresnel): skin, lungs, the body silhouette."""
    m, p = _principled(name); nt = m.node_tree; n = nt.nodes
    lw = n.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = blend
    mr = n.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.0; mr.inputs['From Max'].default_value = 1.0
    mr.inputs['To Min'].default_value = a_center; mr.inputs['To Max'].default_value = a_rim
    mul = n.new('ShaderNodeMath'); mul.operation = 'MULTIPLY_ADD'; mul.inputs[1].default_value = emit; mul.inputs[2].default_value = emit_min
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

def mat_cell(name='cell_m', ox=1.0, animated=False):
    """Blood cell: haemoglobin crimson when oxygenated, indigo-violet when not. animated=True reads the object's custom
    property 'ox' (0..1) so ONE material serves every cell and each cell can turn red inside the lungs."""
    m, p = _principled(name); nt = m.node_tree; n = nt.nodes
    mix = n.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.inputs[6].default_value = (*DEOXY, 1); mix.inputs[7].default_value = (*OXY, 1)
    em = n.new('ShaderNodeMix'); em.data_type = 'RGBA'; em.inputs[6].default_value = (*DEOXY_LIT, 1); em.inputs[7].default_value = (*OXY_LIT, 1)
    if animated:
        at = n.new('ShaderNodeAttribute'); at.attribute_type = 'OBJECT'; at.attribute_name = 'ox'
        nt.links.new(at.outputs['Fac'], mix.inputs['Factor']); nt.links.new(at.outputs['Fac'], em.inputs['Factor'])
    else: mix.inputs['Factor'].default_value = ox; em.inputs['Factor'].default_value = ox
    nt.links.new(mix.outputs[2], p.inputs['Base Color']); nt.links.new(em.outputs[2], p.inputs['Emission Color'])
    _inp(p, 'Emission Strength', 0.55); _inp(p, 'Roughness', 0.28); _inp(p, 'Coat Weight', 0.5); _inp(p, 'Subsurface Weight', 0.35); _inp(p, 'Subsurface Radius', (0.8, 0.15, 0.1)); _inp(p, 'Subsurface Scale', 0.05)
    return m

def mat_glow(color, strength=6.0, name='glow', alpha=1.0): return mat_emit(color, strength=strength, name=name, alpha=alpha)
def mat_chrome(name='chrome'): return mat_metal(CHROME, rough=0.16, name=name)
def mat_rubber(name='rubber', color=RUBBER): return mat_plastic(color, rough=0.55, name=name)
def mat_skin(name='skin'): return mat_organic(SKIN, rough=0.45, sss=0.45, coat=0.1, name=name, radius=(1.0, 0.35, 0.2), scale=0.12)
def mat_bone(name='bone'):
    m = mat_organic(BONE, rough=0.5, sss=0.25, coat=0.15, name=name, radius=(0.6, 0.5, 0.35))
    _noise_bump(m, m.node_tree.nodes.get('Principled BSDF'), scale=12.0, strength=0.1, detail=4.0, distance=0.03); return m
def mat_fat(name='fat'): return mat_organic(P.mix(FAT, MUSCLE, 0.42), rough=0.55, sss=0.5, coat=0.2, name=name, radius=(1.0, 0.7, 0.3), scale=0.12)
def mat_valve(name='valve', alpha=0.9):
    m = mat_translucent(P.VALVE, alpha=alpha, rough=0.3, name=name, sss=0.3, coat=0.4)
    p = m.node_tree.nodes.get('Principled BSDF'); _inp(p, 'Subsurface Radius', (0.9, 0.5, 0.4)); _inp(p, 'Subsurface Scale', 0.05); return m
def mat_chordae(name='chordae'): return mat_organic(CHORDAE, rough=0.35, sss=0.2, coat=0.3, name=name)
def mat_lung(name='lung', rim=True, a_center=0.55, veins=False):
    if rim:
        m = mat_rim(LUNG, LUNG_RIM, a_center=a_center, a_rim=0.95, emit=0.6, name=name, blend=0.45, rough=0.4)
        if veins: lung_veins(m)
        return m
    m = mat_organic(LUNG, rough=0.45, sss=0.4, coat=0.3, name=name, radius=(1.0, 0.45, 0.35), scale=0.1)
    _noise_bump(m, m.node_tree.nodes.get('Principled BSDF'), scale=24.0, strength=0.25, detail=6.0, distance=0.04)
    if veins: lung_veins(m)
    return m
def mat_fabric(color=CUFF, name='fabric'):
    m, p = _principled(name); nt = m.node_tree; n = nt.nodes
    _inp(p, 'Base Color', (*color, 1)); _inp(p, 'Roughness', 0.85); _inp(p, 'Sheen Weight', 0.6)
    tc = n.new('ShaderNodeTexCoord'); w1 = n.new('ShaderNodeTexWave'); w1.inputs['Scale'].default_value = 38.0; w1.bands_direction = 'X'
    w2 = n.new('ShaderNodeTexWave'); w2.inputs['Scale'].default_value = 38.0; w2.bands_direction = 'Z'
    mx = n.new('ShaderNodeMath'); mx.operation = 'MULTIPLY'; bmp = n.new('ShaderNodeBump'); bmp.inputs['Strength'].default_value = 0.6; bmp.inputs['Distance'].default_value = 0.02
    nt.links.new(tc.outputs['Object'], w1.inputs['Vector']); nt.links.new(tc.outputs['Object'], w2.inputs['Vector'])
    nt.links.new(w1.outputs['Fac'], mx.inputs[0]); nt.links.new(w2.outputs['Fac'], mx.inputs[1]); nt.links.new(mx.outputs[0], bmp.inputs['Height']); nt.links.new(bmp.outputs['Normal'], p.inputs['Normal'])
    return m
def mat_gradient(c0, c1, axis='X', lo=-1.0, hi=1.0, name='grad', emit=0.4, coat=0.5):
    """Colour blends from c0 to c1 along an object-space axis (capillaries: crimson in, violet out)."""
    m, p = _principled(name); nt = m.node_tree; n = nt.nodes
    tc = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); mr = n.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = lo; mr.inputs['From Max'].default_value = hi
    mix = n.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.inputs[6].default_value = (*c0, 1); mix.inputs[7].default_value = (*c1, 1)
    nt.links.new(tc.outputs['Object'], sep.inputs['Vector']); nt.links.new(sep.outputs[axis], mr.inputs['Value']); nt.links.new(mr.outputs['Result'], mix.inputs['Factor'])
    nt.links.new(mix.outputs[2], p.inputs['Base Color']); nt.links.new(mix.outputs[2], p.inputs['Emission Color'])
    _inp(p, 'Emission Strength', emit); _inp(p, 'Roughness', 0.3); _inp(p, 'Coat Weight', coat); _inp(p, 'Subsurface Weight', 0.25)
    return m

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

def spheres_mesh(name, pts, r, mat, subdiv=2, rscale=None):
    """Many small spheres joined into ONE mesh object (dust, motes, granules) - keeps the object count low."""
    bm = bmesh.new()
    for i, p in enumerate(pts):
        rr = r * (rscale[i] if rscale else 1.0)
        bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=rr, matrix=Matrix.Translation(Vector(p)))
    return mesh_obj(name, bm, mat)

def parent(o, root):
    o.parent = root; o.matrix_parent_inverse = Matrix.Identity(4)

def hide_until(o, f): kf(o, 'hide_render', 1, True); kf(o, 'hide_render', f, False)
def hide_from(o, f): kf(o, 'hide_render', 1, False); kf(o, 'hide_render', f, True)
def hide_between(o, f0, f1): kf(o, 'hide_render', 1, False); kf(o, 'hide_render', f0, True); kf(o, 'hide_render', f1, False)
def show_between(o, f0, f1): kf(o, 'hide_render', 1, True); kf(o, 'hide_render', f0, False); kf(o, 'hide_render', f1, True)

def anchor(name, loc, parent_to=None):
    """A sub-pixel mesh speck whose 2D position the compositor uses to pin a label (must be a visible MESH)."""
    o = obj_add('ico_sphere', name, radius=0.002, subdivisions=1, location=loc)
    setmat(o, mat_emit((0, 0, 0), strength=0.0, name='anch'))
    try: o.visible_shadow = False
    except Exception: pass
    if parent_to is not None: parent(o, parent_to)
    return o

def cutter_box(name, loc, size, rot=(0, 0, 0), mat=None, bevel=0.0, pivot=None):
    """Hidden boolean cutter. pivot = world point the rotation turns about (the cut PLANE stays through it)."""
    if pivot is not None and any(rot):
        R = Euler(rot).to_matrix(); loc = tuple(Vector(pivot) + R @ (Vector(loc) - Vector(pivot)))
    c = obj_add('cube', name, size=1.0, location=loc); c.scale = size; c.rotation_euler = rot
    c.hide_render = True; c.display_type = 'WIRE'
    if bevel > 0:                                       # rounded window: bevel in local units (the cube is unit-sized, scaled by size)
        bm = bmesh.new(); bm.from_mesh(c.data)
        for v in bm.verts: v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
        bmesh.ops.bevel(bm, geom=[e for e in bm.edges if abs(e.verts[0].co.y - e.verts[1].co.y) > 1e-6], offset=bevel, segments=8, profile=0.5, affect='EDGES')
        bm.to_mesh(c.data); bm.free(); c.scale = (1, 1, 1)
    if mat is not None: setmat(c, mat)
    try: c.visible_camera = False; c.visible_shadow = False
    except Exception: pass
    return c

def boolean(o, cutter, op='DIFFERENCE', name='bool', transfer=True):
    mod = o.modifiers.new(name, 'BOOLEAN'); mod.operation = op; mod.object = cutter
    for sv in ('EXACT', 'FAST'):
        try: mod.solver = sv; break
        except Exception: continue
    if transfer:
        try: mod.material_mode = 'TRANSFER'
        except Exception: pass
    return mod

def subsurf_(o, levels=1, render_levels=2): return subsurf(o, levels, render_levels)

def bake(o):
    """Apply the whole modifier stack into a plain mesh (materials kept) - then shape keys / cheap per-frame evaluation."""
    dg = bpy.context.evaluated_depsgraph_get(); ev = o.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    old = o.data; o.modifiers.clear(); o.data = me
    if not me.materials:
        for m in old.materials: me.materials.append(m)
    for pl in me.polygons: pl.use_smooth = True
    bpy.context.view_layer.update()          # re-evaluate NOW: closest_point_on_mesh / ray_cast otherwise query the stale pre-bake surface (buried every coronary)
    return o

def to_mesh(o, name=None):
    """Replace a curve object by an equivalent mesh object (same name/parent/materials) so it can be boolean-cut."""
    dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), depsgraph=dg)
    for pl in me.polygons: pl.use_smooth = True
    if not me.materials:
        for m in o.data.materials: me.materials.append(m)
    nm = name or o.name; par = o.parent; mw = o.matrix_world.copy()
    bpy.data.objects.remove(o)
    n = bpy.data.objects.new(nm, me); bpy.context.collection.objects.link(n)
    if par is not None: parent(n, par)
    n.matrix_world = mw                      # after parenting, so a root away from the origin is not applied twice
    return n

META_K = 0.76          # with stiffness 4 / threshold 0.3 a lone element's visible radius is ~0.76 of its field radius
def meta_mesh(name, elements, res=0.06, mat=None, threshold=0.3):
    """Metaball sculpt -> mesh. elements = [(co, VISIBLE radius, (sx, sy, sz) or None)] (radii are what you see, the field
    radius is derived). Distinct base names = distinct metaball families (same-name objects would blend together)."""
    mb = bpy.data.metaballs.new(name); mb.resolution = res; mb.render_resolution = res; mb.threshold = threshold
    for el in elements:
        co, r = el[0], el[1] / META_K; sc = el[2] if len(el) > 2 else None; st = 4.0
        e = mb.elements.new(); e.co = co; e.radius = r; e.stiffness = st
        if sc:
            e.type = 'ELLIPSOID'; e.size_x, e.size_y, e.size_z = sc
        if len(el) > 3 and el[3]: e.use_negative = True
    tmp = bpy.data.objects.new(name + '_mb', mb); bpy.context.collection.objects.link(tmp)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg), depsgraph=dg)
    bpy.data.objects.remove(tmp); bpy.data.metaballs.remove(mb)
    for pl in me.polygons: pl.use_smooth = True
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    if mat is not None: setmat(o, mat)
    return o

def catmull(pts, n):
    P = [pts[0]] + list(pts) + [pts[-1]]; out = []; segs = len(pts) - 1
    for i in range(segs):
        p0, p1, p2, p3 = (Vector(P[i]), Vector(P[i + 1]), Vector(P[i + 2]), Vector(P[i + 3]))
        steps = max(1, int(round(n / segs)))
        for k in range(steps):
            t = k / steps; t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(Vector(pts[-1])); return out

def tube(name, pts, r, mat, r1=None, res=16, bevel_res=8, cyclic=False, loc=(0, 0, 0), caps=True, hollow=0.0, radii=None):
    """Smooth bevelled Bezier tube through pts, tapering from r to r1 (per-point radii override). hollow>0 -> a pipe of
    that wall thickness (solidify on the curve's open bevel) for 'look down the vessel' shots."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 1.0; cu.bevel_resolution = bevel_res; cu.use_fill_caps = caps and hollow <= 0
    cu.resolution_u = res
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    n = len(pts)
    if radii is not None and len(radii) != n:              # a coarse radius list over a resampled curve: interpolate it
        m_ = len(radii) - 1; radii = [radii[min(m_, int((i / max(1, n - 1)) * m_))] + (radii[min(m_, int((i / max(1, n - 1)) * m_) + 1)] - radii[min(m_, int((i / max(1, n - 1)) * m_))]) * (((i / max(1, n - 1)) * m_) % 1.0) for i in range(n)]
    for i, p in enumerate(pts):
        b = sp.bezier_points[i]; b.co = p; b.handle_left_type = b.handle_right_type = 'AUTO'
        u = i / max(1, n - 1)
        b.radius = radii[i] if radii is not None else (r + (r1 - r) * u if r1 is not None else r)
    sp.use_cyclic_u = cyclic
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o); o.location = loc
    cu.materials.append(mat)
    if hollow > 0:
        cu.fill_mode = 'FULL'; cu.use_fill_caps = False
        try: cu.bevel_mode = 'ROUND'
        except Exception: pass
        solidify(o, hollow)
    return o

def path_curve(name, pts, cyclic=False, res=24):
    """Invisible guide curve for Follow-Path constraints."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.resolution_u = res; cu.use_path = True; cu.path_duration = 100
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        b = sp.bezier_points[i]; b.co = p; b.handle_left_type = b.handle_right_type = 'AUTO'
    sp.use_cyclic_u = cyclic
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o); o.hide_render = True
    try: o.visible_camera = False
    except Exception: pass
    return o

def follow(o, path, keys, follow_dir=True):
    """Ride a path: keys = [(frame, u)] with u in 0..1 (u may exceed 1 for cyclic paths -> wrapped by Blender)."""
    c = o.constraints.new('FOLLOW_PATH'); c.target = path; c.use_fixed_location = True; c.use_curve_follow = follow_dir; c.forward_axis = 'FORWARD_Y'; c.up_axis = 'UP_Z'
    for f, u in keys:
        c.offset_factor = u % 1.0 if path.data.splines[0].use_cyclic_u else max(0.0, min(1.0, u)); c.keyframe_insert('offset_factor', frame=f)
    for fc in _fc_all(o):
        for k in fc.keyframe_points: k.interpolation = 'LINEAR'
    return c

def _fc_all(o): return _fcurves(o)
def ease_all(o, mode='EASE_IN_OUT'): kf_ease(o, mode)

def ride(o, samples, rfps, t0, t1, step=1, ease=False, hold=True):
    """Key an object's location along a list of sampled points (catmull output) between t0 and t1."""
    f0, f1 = F(t0, rfps), F(t1, rfps); n = len(samples) - 1
    for f in range(f0, f1 + 1, step):
        u = (f - f0) / max(1, f1 - f0); u = smooth01(u) if ease else u
        kf(o, 'location', f, tuple(samples[min(n, int(round(u * n)))]))
    if f1 % step: kf(o, 'location', f1, tuple(samples[n]))
    kf_lin(o)

def displace(o, scale=0.5, strength=0.1, name='disp', kind='CLOUDS', depth=2):
    try:
        tx = bpy.data.textures.new(name + '_tx', kind); tx.noise_scale = scale
        try: tx.noise_depth = depth
        except Exception: pass
        mod = o.modifiers.new(name, 'DISPLACE'); mod.texture = tx; mod.strength = strength; mod.mid_level = 0.5
        return mod
    except Exception: return None

def orient(o, p0, p1):
    """Place a Z-long object between two points (cylinder/cone axis from p0 to p1)."""
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
    o.location = (p0 + p1) / 2; o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); return d.length

def cone(name, p0, p1, r0, r1, mat, verts=48):
    p0, p1 = Vector(p0), Vector(p1)
    o = obj_add('cone', name, radius1=r0, radius2=r1, depth=(p1 - p0).length, vertices=verts); orient(o, p0, p1)
    setmat(o, mat); smooth(o, auto=False); subsurf(o, 1, 2); return o

def rbc_mesh(name='RBCMesh', R=0.11, deep=False):
    """Biconcave red-cell disc (lathed profile), shared by every instance. deep=True: the hero profile, a broad deep
    dimple (centre 0.06 R thick, rim torus 0.3 R) so the concavity reads as a shaded bowl."""
    prof = []; N = 14 if not deep else 24
    for i in range(N + 1):
        u = i / N
        if deep:
            up = 0.72
            z = (0.12 + 0.5 * math.sin(math.pi / 2 * min(1.0, u / up)) ** 2) if u < up else 0.62 * math.cos(math.pi / 2 * (u - up) / (1 - up)) ** 0.8
        else: z = 0.30 + 1.6 * u * u - 1.9 * u ** 4
        prof.append((R * u, R * 0.5 * max(0.02, z)))
    top = prof; bot = [(r, -z) for (r, z) in reversed(prof[:-1])]
    full = [(0.0, top[0][1])] + top[1:] + bot
    bm = bmesh.new(); rings = []; verts = 40 if not deep else 64
    for (r, z) in full:
        if r < 1e-5: rings.append([bm.verts.new((0, 0, z))]); continue
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * k / verts), r * math.sin(2 * math.pi * k / verts), z)) for k in range(verts)])
    for a, b in zip(rings[:-1], rings[1:]):
        if len(a) == 1:
            for k in range(verts): bm.faces.new((a[0], b[(k + 1) % verts], b[k]))
        elif len(b) == 1:
            for k in range(verts): bm.faces.new((a[k], a[(k + 1) % verts], b[0]))
        else:
            for k in range(verts): bm.faces.new((a[k], a[(k + 1) % verts], b[(k + 1) % verts], b[k]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for pl in me.polygons: pl.use_smooth = True
    return me

_RBC = {}
def rbc(name, loc=(0, 0, 0), R=0.11, mat=None, rot=None):
    key = (round(R, 4), id(bpy.context.scene))
    me = _RBC.get(key)
    if me is None or me.name not in bpy.data.meshes: me = rbc_mesh('RBCMesh%.3f' % R, R); _RBC[key] = me
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o); o.location = loc
    if rot: o.rotation_euler = rot
    if mat is not None and not me.materials: me.materials.append(mat)
    return o

def rbc_flow(prefix, path, n, rfps, nf, speed, R=0.11, mat=None, seed=1, spread=0.0, u0=0.0, ox_keys=None, follow_dir=True, wobble=True, u_span=1.0):
    """n red cells riding `path` at `speed` (path lengths per second), staggered along it; cyclic paths loop.
    ox_keys = [(u, ox)] colour-by-position table (needs a mat_cell(animated=True) material)."""
    rnd = random.Random(seed); out = []; cyc = path.data.splines[0].use_cyclic_u
    for i in range(n):
        o = rbc(f'{prefix}{i}', R=R * rnd.uniform(0.85, 1.15), mat=mat)
        if spread:
            o.location = (rnd.uniform(-spread, spread), rnd.uniform(-spread, spread), rnd.uniform(-spread, spread))    # offset is applied in path-local frame by the constraint
        start = (u0 + u_span * i / n + rnd.uniform(0, 0.4 / n)) % 1.0 if cyc else u0 + u_span * i / n
        if cyc: keys = [(1, start), (nf, start + speed * (nf - 1) / rfps)]
        else:                                        # open path: the cell RECYCLES (u wraps to 0, hidden for the wrap frame) so the stream never runs dry
            keys = []; prev = None; hid = []
            for f in range(1, nf + 1):
                u = (start + speed * (f - 1) / rfps) % 1.0
                if prev is not None and u < prev: hid.append(f)
                keys.append((f, u)); prev = u
            for f in hid:
                kf(o, 'hide_render', f, True); kf(o, 'hide_render', f + 1, False)
            if hid: kf(o, 'hide_render', 1, False)
        follow(o, path, keys, follow_dir)
        if wobble:
            o.rotation_euler = (rnd.uniform(0, 3), rnd.uniform(0, 3), rnd.uniform(0, 3))
            kf(o, 'rotation_euler', 1, tuple(o.rotation_euler)); kf(o, 'rotation_euler', nf, (o.rotation_euler[0] + rnd.uniform(1, 3), o.rotation_euler[1] + rnd.uniform(-2, 2), o.rotation_euler[2] + rnd.uniform(1, 2)));
        if ox_keys is not None:
            for f, u in [(f, (start + speed * (f - 1) / rfps) % 1.0 if cyc else min(1.0, start + speed * (f - 1) / rfps)) for f in range(1, nf + 1, 3)]:
                o['ox'] = _ox_at(ox_keys, u); o.keyframe_insert('["ox"]', frame=f)
        for fc in _fc_all(o):
            if fc.data_path.startswith('constraints'):
                for k in fc.keyframe_points: k.interpolation = 'LINEAR'
        out.append(o)
    return out

def _ox_at(keys, u):
    keys = sorted(keys); v = keys[0][1]
    for (ku, kv) in keys:
        if u >= ku: v = kv
    return v

# ================================================================= environment: motes, glow, foreground cells
def motes(name, n, center, spread, color=PLASMA, r=0.02, strength=4.0, seed=3, drift=0.0, rfps=12, nf=1, subdiv=1):
    """Floating plasma motes / void dust that catch the light: ONE mesh; optional slow drift keyed on the object."""
    rnd = random.Random(seed)
    pts = [Vector(center) + Vector((rnd.uniform(-1, 1) * spread[0], rnd.uniform(-1, 1) * spread[1], rnd.uniform(-1, 1) * spread[2])) for _ in range(n)]
    o = spheres_mesh(name, pts, r, mat_glow(color, strength=strength, name=name + '_m'), subdiv=subdiv, rscale=[rnd.uniform(0.4, 1.6) for _ in pts])
    try: o.visible_shadow = False
    except Exception: pass
    if drift and nf > 1:
        kf(o, 'location', 1, (0, 0, 0)); kf(o, 'location', nf, (drift * 0.3, drift * 0.1, drift)); kf_lin(o)
    return o

def backglow(center, color, r=4.0, strength=0.55, depth=6.0, name='BackGlow', alpha=0.75):
    """A faint soft glow DISC behind the hero: the glow reaches zero at radius r (the plane is 1.7x wider, its edges fully
    transparent), so the frame edges stay navy void and no plane edge can ever show. r = the visible glow radius."""
    o = obj_add('plane', name, size=2 * r * 1.7, location=(center[0], center[1] + depth, center[2])); o.rotation_euler = (math.pi / 2, 0, 0)
    m, p = _principled(name + '_m'); nt = m.node_tree; n = nt.nodes
    tc = n.new('ShaderNodeTexCoord'); g = n.new('ShaderNodeTexGradient'); g.gradient_type = 'SPHERICAL'
    mp = n.new('ShaderNodeMapping'); mp.inputs['Location'].default_value = (-0.5, -0.5, 0); mp.inputs['Scale'].default_value = (1, 1, 1)
    # generated coords 0..1 -> centre at 0.5; spherical gradient = 1 - distance; remap so the glow is 1 at the centre and 0 at
    # distance 0.5/1.7 (= radius r), then a soft power curve
    mr = n.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 1.0 - 0.5 / 1.7; mr.inputs['From Max'].default_value = 1.0; mr.clamp = True
    pw = n.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 1.4
    mul = n.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = alpha
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], g.inputs['Vector']); nt.links.new(g.outputs['Fac'], mr.inputs['Value'])
    nt.links.new(mr.outputs['Result'], pw.inputs[0]); nt.links.new(pw.outputs[0], mul.inputs[0]); nt.links.new(mul.outputs[0], p.inputs['Alpha'])
    _inp(p, 'Base Color', (0, 0, 0, 1)); _inp(p, 'Emission Color', (*color, 1)); _inp(p, 'Emission Strength', strength); _inp(p, 'Roughness', 1.0); _inp(p, 'Specular IOR Level', 0.0)
    _blend(m); setmat(o, m)
    try: o.visible_shadow = False
    except Exception: pass
    return o

def fg_cells(prefix, n, cam_loc, tgt_loc, rfps, nf, seed=5, R=0.085, dist=3.6, mat=None, spread=2.4, drift=1.3):
    """Out-of-focus red cells drifting ACROSS the frame between the camera and the hero: small, soft (low emission), and
    moving sideways so they cross rather than sit as a bokeh ball."""
    rnd = random.Random(seed); m = mat or mat_cell(prefix + '_m', ox=1.0); out = []
    if mat is None: _inp(m.node_tree.nodes.get('Principled BSDF'), 'Emission Strength', 0.25)
    c, t = Vector(cam_loc), Vector(tgt_loc); d = (t - c).normalized(); right = d.cross(Vector((0, 0, 1))).normalized(); up = right.cross(d).normalized()
    for i in range(n):
        base = c + d * (dist * rnd.uniform(0.8, 1.6)) + right * rnd.uniform(-spread, spread) + up * rnd.uniform(-spread * 0.6, spread * 0.6)
        o = rbc(f'{prefix}{i}', tuple(base), R=R * rnd.uniform(0.7, 1.3), mat=m, rot=(rnd.uniform(0, 3), rnd.uniform(0, 3), rnd.uniform(0, 3)))
        vel = right * rnd.uniform(-drift, drift) + up * rnd.uniform(-drift * 0.4, drift * 0.4)
        kf(o, 'location', 1, tuple(base)); kf(o, 'location', nf, tuple(base + vel * (nf / rfps)))
        kf(o, 'rotation_euler', 1, tuple(o.rotation_euler)); kf(o, 'rotation_euler', nf, (o.rotation_euler[0] + rnd.uniform(0.5, 2), o.rotation_euler[1] + rnd.uniform(-1, 1), o.rotation_euler[2] + 0.5)); kf_lin(o)
        try: o.visible_shadow = False
        except Exception: pass
        out.append(o)
    return out

# ================================================================= lighting / stage / camera
def stage(target=(0, 0, 0.3), key=(3.0, -5.5, 7.5), key_e=2400, fill_e=160, rim_e=420, spot=55, blend=0.85, env=0.12, world_col=VOID, section=0, atm=0.0015):
    """Dark navy void, warm pooled key, cool fill + rim (colours from the section's THEME), HDRI reflections, thin atmosphere."""
    world(*world_col); th = THEME.get(section, THEME[0])
    k, f, r = studio(key=key, key_e=key_e, fill_e=fill_e, rim_e=rim_e, target=target, spot=spot, blend=blend)
    k.data.color = th['key']; f.data.color = th['fill']; r.data.color = th['rim']
    hdri(strength=env, rotation=1.3); atmosphere(density=atm)
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

def cam_orbit(center, radius, height, a0, a1, t0, t1, rfps, lens=45, push=None, tilt=None):
    """Orbit around center (deg, 0 = from -Y) while optionally pushing in (radius -> push) and rising (height -> tilt)."""
    cam, tgt = camera((center[0] + radius * math.sin(math.radians(a0)), center[1] - radius * math.cos(math.radians(a0)), height), center, lens=lens)
    f0, f1 = F(t0, rfps), F(t1, rfps); steps = max(2, int((f1 - f0) / 4))
    for i in range(steps + 1):
        u = i / steps; ue = u * u * (3 - 2 * u); a = math.radians(a0 + (a1 - a0) * ue)
        rr = radius + ((push - radius) * ue if push is not None else 0); hh = height + ((tilt - height) * ue if tilt is not None else 0)
        kf(cam, 'location', int(f0 + (f1 - f0) * u), (center[0] + rr * math.sin(a), center[1] - rr * math.cos(a), hh))
    kf_lin(cam); return cam, tgt

def lens_kf(cam, keys):
    for f, mm in keys:
        cam.data.lens = mm; cam.data.keyframe_insert('lens', frame=f)

def focus(cam, f0, f1, o0, o1):
    """Rack focus only when DOF is on (the cloud); locally the plain camera stays sharp."""
    if DOF: rack_focus(cam, f0, f1, o0, o1)

def pulse_scale(o, t0, t1, rfps, period=0.83, amp=0.05, base=(1, 1, 1), phase=0.0):
    """A heartbeat-shaped scale pulse (quick swell, slower relax) repeated from t0 to t1."""
    t = t0 + phase
    while t < t1:
        for dt, s in ((0.0, 1.0), (0.13, 1 + amp), (0.42, 1.0)):
            kf(o, 'scale', F(t + dt, rfps), (base[0] * s, base[1] * s, base[2] * (1 + (s - 1) * 0.6)))
        t += period
    kf_ease(o)

# ================================================================= THE HEART
# chamber cavity centres (heart-local; anatomical left = +X). The AV plane sits near z = 0.
CH = {'RA': Vector((-0.82, 0.16, 0.60)), 'LA': Vector((0.80, 0.18, 0.62)), 'RV': Vector((-0.66, 0.12, -0.70)), 'LV': Vector((0.70, 0.10, -0.74))}
VALVE = {'tri': Vector((-0.70, 0.14, -0.08)), 'mit': Vector((0.72, 0.14, -0.08)), 'pul': Vector((-0.32, 0.10, 0.52)), 'aor': Vector((0.15, 0.13, 0.56))}
CUT_Y = 0.0837         # front cutaway plane through the pivot (everything in front removed): slices every cavity near its middle; off the metaball grid (coplanar faces break the exact boolean)
CUT_PIVOT = (0.35, CUT_Y, -0.2)
CUT_TILT = (0.06, 0.0, 0.08)   # the section plane is NOT square to the camera: tilted about X (top deeper) and turned about Z, so the cut lip shows the wall thickness in depth
def cut_y(x, z=0.0, tilt=None):
    """y of the section plane at (x, z): the plane passes through CUT_PIVOT with normal R @ (0, 1, 0)."""
    n = Euler(tilt or CUT_TILT).to_matrix() @ Vector((0, 1, 0)); px, py, pz = CUT_PIVOT
    return py - (n.x * (x - px) + n.z * (z - pz)) / n.y

def heart_outer_elements():
    return [((0.0, 0.05, -0.2), 1.05, (1.3, 1.0, 1.05)),        # ventricular mass, broad at the base
            ((0.45, 0.02, -0.85), 0.9, (1.0, 0.85, 0.95)),      # left ventricle bulk (the thick wall lives here)
            ((0.85, -0.05, -1.3), 0.62, (0.9, 0.8, 0.9)),       # toward the apex
            ((1.1, -0.1, -1.7), 0.38, None),                    # apex, pointing to the anatomical left and down
            ((-0.75, 0.0, -0.5), 0.72, (1.0, 0.85, 1.0)),       # right ventricle, in front-left
            ((-0.62, -0.12, 0.12), 0.5, (1.0, 0.8, 0.8)),       # fills the front atrio-ventricular groove
            ((-0.95, 0.08, 0.62), 0.64, (1.0, 0.92, 0.85)),      # right atrium
            ((0.95, 0.18, 0.7), 0.6, (1.0, 0.92, 0.8)),         # left atrium
            ((0.12, 0.2, 0.85), 0.4, None),                     # aortic root
            ((-0.3, 0.0, 0.85), 0.34, None)]                    # pulmonary trunk root

def heart_cavity_elements():
    RA, LA, RV, LV = CH['RA'], CH['LA'], CH['RV'], CH['LV']
    return [(tuple(RA), 0.52, (1.15, 0.85, 0.85)),                                          # 0 RA: thin-walled
            (tuple(RV + Vector((-0.06, 0, 0.02))), 0.5, (1.12, 0.7, 1.12)),                # 1 RV: wide flat crescent, thinner free wall than the LV
            (tuple(VALVE['tri'] + Vector((0, 0, 0.05))), 0.21, (0.95, 0.95, 1.2)),         # 2 tricuspid neck
            (tuple(LA), 0.46, (1.12, 0.95, 0.82)),                                          # 3 LA: thin-walled
            (tuple(LV), 0.42, (0.72, 0.85, 1.5)),                                           # 4 LV: narrow and tall -> thick walls
            (tuple(VALVE['mit'] + Vector((0, 0, 0.05))), 0.19, (0.9, 0.9, 1.2)),           # 5 mitral neck
            ((-0.32, 0.1, 0.25), 0.2, (0.8, 0.8, 1.7)),                                     # 6 RV outflow -> pulmonary valve
            ((0.15, 0.0, 0.3), 0.18, (0.8, 0.8, 1.7)),                                      # 7 LV outflow -> aortic valve (opened by the cut)
            ((-0.9, 0.2, 1.05), 0.2, (0.9, 0.9, 1.3)),                                      # 8 SVC mouth (top of RA)
            ((-0.98, 0.3, 0.05), 0.2, (0.9, 0.9, 1.3)),                                     # 9 IVC mouth (floor of RA)
            # organic lobes so no cavity is a clean ellipsoid: the right auricle, the RV apex recess, the LA appendage, the LV apex
            (tuple(RA + Vector((-0.28, -0.1, 0.32))), 0.24, (1.1, 0.8, 0.8)),               # 10 RA auricle
            (tuple(RV + Vector((0.18, 0.05, -0.42))), 0.28, (1.1, 0.7, 1.0)),               # 11 RV toward the apex
            (tuple(LA + Vector((0.3, -0.05, 0.22))), 0.2, (1.2, 0.8, 0.8)),                 # 12 LA appendage
            (tuple(LV + Vector((0.14, 0.02, -0.62))), 0.22, (0.8, 0.85, 1.1))]              # 13 LV apex]

_BVH = {}
def bvh_of(o):
    """A BVH of the object's BASIS mesh data. Object.closest_point_on_mesh / ray_cast answer from the active shape key
    once key data exists (measured: every coronary landed 0.2-0.4 inside the resting wall), so all surface queries go
    through this instead."""
    from mathutils.bvhtree import BVHTree
    t = _BVH.get(o.name)
    if t is None:
        bm = bmesh.new(); bm.from_mesh(o.data); t = BVHTree.FromBMesh(bm); bm.free(); _BVH[o.name] = t
    return t

def nearest(o, p):
    loc, nrm, idx, dist = bvh_of(o).find_nearest(Vector(p))
    return (loc is not None), loc, nrm, idx

def surface_pt(mesh_o, seed, inward=0.0):
    """Closest point on a (local-space) mesh to `seed`, offset along the normal (negative = inward)."""
    ok, loc, nrm, idx = nearest(mesh_o, seed)
    return (Vector(loc) + Vector(nrm) * inward) if ok else Vector(seed)

def petal(name, hinge, tangent, inward, down, w, L, mat, curl=0.35, segs=(10, 8), thick=0.012, taper=0.55, scallop=0.0, lobes=3):
    """A thin curved leaflet hanging from a hinge line: local frame X = tangent (hinge line), Y = inward (toward the
    orifice centre), Z = -down. Returns (hinge_empty, mesh); rotate the empty about its local X to swing the leaflet."""
    t, i_, d = Vector(tangent).normalized(), Vector(inward).normalized(), Vector(down).normalized()
    M = Matrix((( t.x, i_.x, -d.x, hinge[0]), (t.y, i_.y, -d.y, hinge[1]), (t.z, i_.z, -d.z, hinge[2]), (0, 0, 0, 1)))
    e = empty(name + '_h'); e.matrix_world = M
    bm = bmesh.new(); nu, nv = segs; grid = []
    for iv in range(nv + 1):
        v = iv / nv; row = []
        for iu in range(nu + 1):
            u = -1 + 2 * iu / nu; ww = w * (1 - taper * v * v)
            sc = 1.0 - scallop * (0.5 + 0.5 * math.cos(math.pi * lobes * u)) * v * v          # scalloped free edge (lobes)
            row.append(bm.verts.new((u * ww, curl * L * v * v * sc, -L * v * (1 - 0.15 * u * u) * sc)))
        grid.append(row)
    for iv in range(nv):
        for iu in range(nu): bm.faces.new((grid[iv][iu], grid[iv][iu + 1], grid[iv + 1][iu + 1], grid[iv + 1][iu]))
    o = mesh_obj(name, bm, mat); solidify(o, thick); subsurf(o, 1, 2)
    o.parent = e; o.matrix_parent_inverse = Matrix.Identity(4)
    return e, o

def key_swing(e, keys):
    """keys = [(frame, degrees)]: swing a leaflet about its hinge line = the hinge empty's local X. Keyed on the CHILD
    mesh's rotation_euler.x (an object's rotation_euler is applied in its own parent-local frame, so this IS the hinge
    axis); delta_rotation_euler on the empty was applied in parent space (world X) and swung most flaps sideways."""
    for ch in [c for c in e.children if c.type == 'MESH'] or [e]:
        for f, deg in keys:
            ch.rotation_euler = (math.radians(deg), 0, 0); ch.keyframe_insert('rotation_euler', frame=f)
        kf_ease(ch)

def swing_static(e, deg):
    for ch in [c for c in e.children if c.type == 'MESH'] or [e]: ch.rotation_euler = (math.radians(deg), 0, 0)

def av_leaflets(root, name, centre, ring_r, n, back_only, open_deg, closed_deg, mat, chord_mat, cav=None, pap_mat=None, valves_open=None, rfps=12):
    """Ring + n leaflets hanging into the ventricle, two papillary muscles on the cavity wall with chordae to the free edges.
    valves_open = [(t, open01)] (1 = hanging open, 0 = swung shut). Returns dict(ring, hinges, leaflets, chordae, paps)."""
    c = Vector(centre); m_ring = mat_organic(P.mix(P.VALVE, MUSCLE, 0.45), rough=0.4, sss=0.3, coat=0.3, name=name + '_ringm')
    if back_only:                                          # the cutaway keeps only the back half of the annulus (the front half was cut away with the wall)
        arc = [tuple(c + Vector((math.cos(a) * ring_r, math.sin(a) * ring_r, 0))) for a in [math.radians(2 + 176 * k / 14) for k in range(15)]]
        ring = tube(name + 'Ring', arc, 0.022, m_ring, res=6, bevel_res=6); parent(ring, root)
    else:
        ring = obj_add('torus', name + 'Ring', major_radius=ring_r, minor_radius=0.022, major_segments=64, minor_segments=16, location=tuple(c))
        setmat(ring, m_ring); smooth(ring, auto=False); parent(ring, root)
    hinges, leaves, chords, paps = [], [], [], []
    angs = [math.radians(35 + 110 * k / max(1, n - 1)) for k in range(n)] if back_only else [math.radians(90 + 360 * k / n) for k in range(n)]
    for k, a in enumerate(angs):
        hp = c + Vector((math.cos(a) * ring_r, math.sin(a) * ring_r, 0)); tangent = Vector((-math.sin(a), math.cos(a), 0)); inward = (c - hp).normalized()
        e, o = petal(f'{name}Leaf{k}', tuple(hp), tangent, inward, (0, 0, -1), ring_r * 0.72, ring_r * 1.35, mat, curl=0.45)
        parent(e, root); hinges.append(e); leaves.append(o)
        if valves_open: key_swing(e, [(F(t, rfps), open_deg + (closed_deg - open_deg) * (1 - v)) for t, v in valves_open])
        else: swing_static(e, open_deg)
    # papillary muscles: from the cavity's back-lower wall up toward the ring, chordae to each leaflet's free edge
    if cav is not None:
        for j, pa in enumerate((math.radians(60), math.radians(125))):
            seed = c + Vector((math.cos(pa) * 1.6, math.sin(pa) * 1.6, -0.55 * ring_r - 0.55))
            base = surface_pt(cav, seed, inward=-0.03); tip = base + (c + Vector((0, 0, -ring_r * 1.6)) - base) * 0.55
            pm = pap_muscle(f'{name}Pap{j}', base, tip, 0.11, pap_mat or mat_flesh(P.mix(MUSCLE, ENDO_L, 0.3), name=name + '_papm', rough=0.62, spec=0.28, bump=0.3, scale=14.0)); parent(pm, root); paps.append(pm)
            for k, e in enumerate(hinges):
                # free edge point of leaflet k in world (hinge-local (0, curl*L, -L)); chordae are re-fit per frame by a hook-free trick: straight tube from tip to the OPEN edge
                edge_local = Vector((0, 0.45 * (ring_r * 1.35), -(ring_r * 1.35)))
                edge = e.matrix_world @ edge_local
                mid = (tip + edge) / 2 + Vector((0, 0.03, -0.04))
                ch = tube(f'{name}Ch{j}{k}', [tuple(tip), tuple(mid), tuple(edge)], 0.009, chord_mat, res=8, bevel_res=4); parent(ch, root); chords.append(ch)
    return dict(ring=ring, hinges=hinges, leaflets=leaves, chordae=chords, paps=paps)

def semilunar_cusps(root, name, centre, r, axis, mat, valves_open=None, rfps=12, back_only=True):
    """Three pocket cusps at an artery mouth: open = pressed flat against the wall (pointing along the flow), shut = swung
    inward to meet at the centre. axis = flow direction."""
    c = Vector(centre); ax = Vector(axis).normalized(); ref = Vector((0, 1, 0)) if abs(ax.y) < 0.9 else Vector((1, 0, 0))
    u = ax.cross(ref).normalized(); v = ax.cross(u).normalized(); hinges = []
    angs = [math.radians(40 + 100 * k / 2) for k in range(3)] if back_only else [math.radians(30 + 120 * k) for k in range(3)]
    for k, a in enumerate(angs):
        radial = (u * math.cos(a) + v * math.sin(a)).normalized(); hp = c + radial * r
        tangent = ax.cross(radial); inward = -radial
        e, o = petal(f'{name}Cusp{k}', tuple(hp), tangent, inward, tuple(-ax), r * 0.66, r * (1.1 if back_only else 1.28), mat, curl=0.55, taper=0.7)
        parent(e, root); hinges.append(e)
        keys = [(F(t, rfps), 170 - 80 * v_) for t, v_ in valves_open] if valves_open else None       # 170 deg = flat along the flow (open), 90 = closed across the mouth
        if keys: key_swing(e, keys)
        else: swing_static(e, 170)
    return hinges

def pap_muscle(name, base, tip, r, mat):
    """A papillary muscle: a meaty column (three blended metaballs, widest at its rooted base) with a soft displacement."""
    base, tip = Vector(base), Vector(tip); d = tip - base
    els = [(tuple(base), r * 1.25, (1.2, 1.2, 0.8)), (tuple(base + d * 0.35), r * 0.95, None), (tuple(base + d * 0.7), r * 0.7, None), (tuple(tip), r * 0.45, None)]
    o = meta_mesh(name, els, res=0.028, mat=mat); displace(o, scale=0.18, strength=0.02, name=name + '_d'); return o

def trabeculae(root, name, cav, centre, n, z_span, mat, rnd, r=0.028):
    """Trabeculae carneae: ridges of muscle draped on the back inner wall of a ventricle (seen through the cutaway), each
    a slightly wavy bevelled curve half-sunk into the lining, some forking into a short side ridge."""
    out = []
    for k in range(n):
        a = math.radians(15 + 150 * (k + rnd.uniform(0.2, 0.8)) / n); tilt = rnd.uniform(-0.7, 0.7); z_len = z_span * rnd.uniform(0.4, 0.85)
        pts = []
        for j in range(5):
            u = j / 4; z = centre.z - z_len * 0.5 + z_len * u + rnd.uniform(-0.03, 0.03); aa = a + tilt * (u - 0.5) + rnd.uniform(-0.06, 0.06)
            seed = Vector((centre.x + math.cos(aa) * 1.5, centre.y + math.sin(aa) * 1.5, z))
            pts.append(tuple(surface_pt(cav, seed, inward=-r * 0.5)))
        rr = r * rnd.uniform(0.7, 1.25)
        o = tube(f'{name}Trab{k}', catmull(pts, 16), rr, mat, res=8, bevel_res=5, radii=[rr * 0.5, rr, rr * 1.05, rr * 0.9, rr * 0.45]); parent(o, root); out.append(o)
        if k % 3 == 1:                                          # a fork
            p0 = Vector(pts[2]); ab = a + rnd.choice((-1, 1)) * 0.35
            q = [tuple(p0)] + [tuple(surface_pt(cav, Vector((centre.x + math.cos(ab) * 1.5, centre.y + math.sin(ab) * 1.5, p0.z + s_ * z_len * 0.25)), inward=-r * 0.5)) for s_ in (0.5, 1.0)]
            f_ = tube(f'{name}Trab{k}f', catmull(q, 8), rr * 0.7, mat, res=6, bevel_res=4, radii=[rr * 0.8, rr * 0.6, rr * 0.3]); parent(f_, root); out.append(f_)
    return out

def heart(loc=(0, 0, 0), cut=False, split=False, vessels=True, coronaries=True, name='Heart', beat=None, rfps=12, nf=1, res=0.05, ghost=False,
          keep_front=False, fat=True, cut_rot=0.0, valves_open=None, interior=True, hollow_vessels=None, coat=0.7, window=True, front_cap=False):
    """The hero. Returns dict(root, body, mat, vessels, keys, interior) where keys = shape keys 'atria', 'vent' (0..1 contraction).
    beat=(t_start_sec, period_sec, amp) adds a whole-heart pulse on the root scale. valves_open = [(t, open01)] drives the AV
    leaflets (semilunar cusps get the complement)."""
    root = empty(name, loc); out = {'root': root}
    m_mus = mat_muscle(name + '_mus', split=split, coat=coat); out['mat'] = m_mus
    body = meta_mesh(name + 'Body', heart_outer_elements(), res=res, mat=m_mus)
    cut_plane = None
    if cut:
        # the cutaway lining: matte, no coat, and its depth shading measured from the tilted section plane itself, so every
        # cavity reads as a HOLE carved into the muscle (dark far wall, lit lip), never as a glossy translucent dome
        rot0 = (CUT_TILT[0], 0.0, CUT_TILT[2] + cut_rot); nrm0 = Euler(rot0).to_matrix() @ Vector((0, 1, 0))
        cut_plane = (tuple(CUT_PIVOT), (nrm0.x, nrm0.y, nrm0.z))
        # fleshy linings (rose-violet right, rose-crimson left, both pulled 30 % toward the muscle), IOR 1 (no Fresnel sheen),
        # a steep depth mask (lit lip zone -> dark floor within 0.24) and coarse trabecular ridges
        mR = mat_endo(P.mix(ENDO_R, MUSCLE, 0.3), name + '_endoR', emit=0.0, depth=(0.0, 0.24), dark=0.1, ridges=0.6, ridge_scale=5.5, plane=cut_plane, matte=True, bump=0.12)
        mL = mat_endo(P.mix(ENDO_L, MUSCLE, 0.3), name + '_endoL', emit=0.0, depth=(0.0, 0.24), dark=0.1, ridges=0.6, ridge_scale=5.5, plane=cut_plane, matte=True, bump=0.12)
    else: mR = mat_endo(ENDO_R, name + '_endoR'); mL = mat_endo(ENDO_L, name + '_endoL')
    mC = mat_cut(name + '_cut')
    body.data.materials.append(mR); body.data.materials.append(mL); body.data.materials.append(mC)
    displace(body, scale=0.9, strength=0.05, name=name + '_d')
    els = heart_cavity_elements()
    cavR = meta_mesh(name + 'CavR', [els[i] for i in (0, 1, 2, 6, 8, 9)], res=res, mat=mR); cavL = meta_mesh(name + 'CavL', [els[i] for i in (3, 4, 5, 7)], res=res, mat=mL)
    for c in (cavR, cavL):
        c.hide_render = True; c.display_type = 'WIRE'
        try: c.visible_camera = False; c.visible_shadow = False
        except Exception: pass
        boolean(body, c, name='cav')
    cb = None
    if cut:
        # a full CORONAL SECTION on a tilted plane (never a rectangular window): the outline stays heart-shaped, every cavity
        # is a hollow carved into the thick muscle, and the cut lip (bevelled below) shows each wall's thickness in depth
        rot = (CUT_TILT[0], 0.0, CUT_TILT[2] + cut_rot)
        cb = cutter_box(name + 'Cut', (CUT_PIVOT[0], CUT_Y - 3.0, CUT_PIVOT[2]), (7.0, 6.0, 7.0), rot=rot, mat=mC, pivot=CUT_PIVOT)
        boolean(body, cb, name='cut')
        try:
            bv = body.modifiers.new('lip', 'BEVEL'); bv.width = 0.028; bv.segments = 3; bv.limit_method = 'ANGLE'; bv.angle_limit = math.radians(38)
        except Exception as e: print('lip bevel', e)
        out['septum_mats'] = [mC, mR, mL]
        septum_nodes(mC, base_emit=0.0, base_col=GOLD); septum_nodes(mR, base_emit=0.0, base_col=ENDO_EMIT); septum_nodes(mL, base_emit=0.0, base_col=ENDO_EMIT)
    # interior anatomy is fitted to the cavity meshes BEFORE they are deleted
    if interior and (cut or ghost):
        rnd = random.Random(7); m_valve = mat_valve(name + '_valve'); m_ch = mat_chordae(name + '_chordae')
        m_trab = mat_flesh(P.mix(ENDO_L, MUSCLE, 0.55), name=name + '_trab', rough=0.68, spec=0.22, bump=0.2) if cut else mat_endo(P.mix(ENDO_L, MUSCLE, 0.5), name=name + '_trab', emit=0.03, bump=0.06, ridges=0.0, plane=cut_plane, matte=False, depth=(0.04, 0.42), dark=0.2)
        I = {}
        I['tri'] = av_leaflets(root, name + 'Tri', VALVE['tri'], 0.2, 3, cut, 8, 80, m_valve, m_ch, cav=cavR, valves_open=valves_open, rfps=rfps)
        I['mit'] = av_leaflets(root, name + 'Mit', VALVE['mit'], 0.185, 2, cut, 8, 80, m_valve, m_ch, cav=cavL, valves_open=valves_open, rfps=rfps)
        sl_open = [(t, 1 - v) for t, v in valves_open] if valves_open else None
        I['pul'] = semilunar_cusps(root, name + 'Pul', VALVE['pul'], 0.15, (0, 0, 1), m_valve, valves_open=sl_open, rfps=rfps, back_only=cut)
        I['aor'] = semilunar_cusps(root, name + 'Aor', VALVE['aor'], 0.14, (0, 0.05, 1), m_valve, valves_open=sl_open, rfps=rfps, back_only=cut)
        I['trabR'] = trabeculae(root, name + 'R', cavR, CH['RV'], 16, 0.95, m_trab, rnd, r=0.042)
        I['trabL'] = trabeculae(root, name + 'L', cavL, CH['LV'], 16, 1.05, m_trab, rnd, r=0.044)
        out['interior'] = I
    if cut and front_cap:                       # the piece the window removes, kept as its own object (dissolvable)
        cap = meta_mesh(name + 'Cap', heart_outer_elements(), res=res, mat=None)
        mcap = mat_muscle(name + '_capm', split=split, coat=coat); _blend(mcap); setmat(cap, mcap); cap.data.materials.append(mR); cap.data.materials.append(mL)
        displace(cap, scale=0.9, strength=0.05, name=name + '_capd')
        for c in (cavR, cavL): boolean(cap, c, name='cav')
        boolean(cap, cb, op='INTERSECT', name='keep', transfer=False); bake(cap); parent(cap, root); smooth(cap, auto=True); out['cap'] = cap; out['cap_mat'] = mcap
    bake(body); _BVH.pop(body.name, None); bvh_of(body)          # cache the BASIS surface now: shape keys added below would poison every later query
    for c in (cavR, cavL): bpy.data.objects.remove(c)
    parent(body, root); out['body'] = body
    smooth(body, auto=True)
    # contraction shape keys
    body.shape_key_add(name='Basis', from_mix=False)
    ka = body.shape_key_add(name='atria', from_mix=False); kv = body.shape_key_add(name='vent', from_mix=False)
    RA, LA, RV, LV = CH['RA'], CH['LA'], CH['RV'], CH['LV']
    for i, v in enumerate(body.data.vertices):
        p = v.co
        wa = math.exp(-((max(0.0, 0.15 - p.z)) ** 2) * 6.0) if p.z > -0.35 else 0.0          # atria region: above the AV plane
        wv = math.exp(-((max(0.0, p.z + 0.05)) ** 2) * 5.0) if p.z < 0.45 else 0.0            # ventricles: below it
        ca = RA if p.x < 0 else LA; cv = RV if p.x < 0.05 else LV
        ka.data[i].co = p + (Vector((ca.x, ca.y, ca.z)) - p) * 0.22 * wa
        kv.data[i].co = p + (Vector((cv.x, cv.y, cv.z)) - p) * 0.18 * wv
    out['keys'] = {'atria': ka, 'vent': kv}
    if ghost:
        gm = mat_rim(MUSCLE, (1.0, 0.5, 0.4), a_center=0.16, a_rim=0.8, emit=0.9, name=name + '_ghost', blend=0.4); body.data.materials[0] = gm
        for em in (mR, mL):                      # the chamber linings become translucent shells: the far wall shows, the near wall is culled, a drop inside stays visible
            _inp(em.node_tree.nodes.get('Principled BSDF'), 'Alpha', 0.42); _blend(em)
            try: em.use_backface_culling = True
            except Exception: pass
        out['ghost_mat'] = gm
    if coronaries and not cut and not ghost: out['coronaries'] = coronary_tree(body, root, name)
    if fat and not cut and not ghost: out['fat'] = fat_pads(body, root, name)
    if vessels: out['vessels'] = great_vessels(root, name, cut=cut, cutter=cb, hollow=hollow_vessels if hollow_vessels is not None else cut)
    if cb is not None: bpy.data.objects.remove(cb)
    if beat is not None:
        t0, period, amp = beat; f = F(t0, rfps)
        while f <= nf + 1:
            kf(root, 'scale', f, (1, 1, 1)); kf(root, 'scale', f + max(1, int(period * rfps * 0.14)), (1 + amp, 1 + amp, 1 + amp * 0.6)); kf(root, 'scale', f + max(2, int(period * rfps * 0.42)), (1, 1, 1))
            t0 += period; f = F(t0, rfps)
        kf_ease(root)
    return out

def drape_tube(body, root, pts, r0, r1, nm, mat, lift=0.55, n=40, res=12, bevel_res=6):
    proj = []
    for p in pts:
        ok, loc, nrm, idx = nearest(body, p)
        proj.append(tuple(loc + nrm * (r0 * lift)) if ok else p)
    o = tube(nm, catmull(proj, n), r0, mat, r1=r1, res=res, bevel_res=bevel_res); parent(o, root); return o

def coronary_tree(body, root, name):
    """Coronary arteries draped on the epicardium (LAD, RCA, circumflex, diagonals), each trunk sprouting 2nd- and 3rd-order
    branches, plus the great and middle cardiac veins in the grooves."""
    mA = mat_vessel(P.mix(OXY, MUSCLE_LIT, 0.25), name=name + '_cor', rough=0.26, coat=0.65); mV = mat_vessel(P.mix(DEOXY, VEIN_WALL, 0.5), name=name + '_corv', rough=0.3, coat=0.5)
    rnd = random.Random(11); out = []
    trunks = {'LAD': ([(-0.05, -1.05, 0.55), (-0.18, -1.2, 0.1), (-0.05, -1.35, -0.35), (0.25, -1.25, -0.85), (0.6, -1.0, -1.3), (0.95, -0.6, -1.55)], 0.05, 0.018),
              'RCA': ([(-0.25, -1.25, 0.05), (-0.75, -1.15, -0.35), (-1.1, -0.85, -0.65), (-1.05, -0.3, -1.0), (-0.75, 0.2, -1.2)], 0.045, 0.016),
              'D1': ([(0.05, -1.3, -0.15), (-0.55, -1.25, -0.75), (-0.85, -0.85, -1.1), (-0.6, -0.4, -1.35)], 0.028, 0.012),
              'Cx': ([(0.45, -0.8, 0.55), (0.95, -0.55, 0.35), (1.35, -0.2, -0.15), (1.45, 0.25, -0.65), (1.25, 0.55, -1.05)], 0.04, 0.015),
              'D2': ([(0.45, -1.15, -0.55), (0.75, -1.1, -0.95), (0.9, -0.85, -1.3)], 0.024, 0.01)}
    for key, (pts, r0, r1) in trunks.items():
        t = drape_tube(body, root, pts, r0, r1, f'{name}Cor{key}', mA); out.append(t)
        sm = catmull(pts, 12)
        for b in range(2 if key in ('D1', 'D2') else 3):                       # 2nd order
            i = 2 + b * 3 + rnd.randint(0, 1); i = min(i, len(sm) - 2)
            p0 = Vector(sm[i]); d = (Vector(sm[i + 1]) - p0).normalized(); side = d.cross(Vector((0, -1, 0))).normalized() * (1 if b % 2 else -1)
            pts2 = [tuple(p0), tuple(p0 + side * 0.28 + d * 0.12), tuple(p0 + side * 0.55 + d * 0.3 + Vector((0, 0, -0.1))), tuple(p0 + side * 0.75 + d * 0.5 + Vector((0, 0, -0.25)))]
            rb = r1 * 1.3 + (r0 - r1) * 0.35
            br = drape_tube(body, root, pts2, rb, rb * 0.35, f'{name}Cor{key}b{b}', mA, n=18, res=8, bevel_res=5); out.append(br)
            for c in range(2):                                                    # 3rd order twigs
                q0 = Vector(pts2[1 + c]); dd = (Vector(pts2[2 + c]) - q0).normalized(); s2 = dd.cross(Vector((0, -1, 0))).normalized() * (1 if c else -1)
                pts3 = [tuple(q0), tuple(q0 + s2 * 0.16 + dd * 0.08), tuple(q0 + s2 * 0.3 + dd * 0.18 + Vector((0, 0, -0.08)))]
                tw = drape_tube(body, root, pts3, rb * 0.45, rb * 0.15, f'{name}Cor{key}b{b}t{c}', mA, n=10, res=6, bevel_res=4); out.append(tw)
    # cardiac veins: the great cardiac vein beside the LAD, a middle cardiac vein toward the apex, a small vein on the RV
    out.append(drape_tube(body, root, [(0.15, -1.0, 0.5), (0.05, -1.25, 0.05), (0.15, -1.35, -0.45), (0.45, -1.2, -0.95), (0.8, -0.9, -1.4)], 0.036, 0.014, name + 'VeinGreat', mV, lift=0.5))
    out.append(drape_tube(body, root, [(-0.4, -1.1, -0.9), (-0.1, -1.15, -1.25), (0.35, -0.95, -1.55), (0.75, -0.6, -1.7)], 0.03, 0.012, name + 'VeinMid', mV, lift=0.5))
    out.append(drape_tube(body, root, [(-0.9, -1.0, -0.2), (-1.15, -0.7, -0.55), (-1.2, -0.35, -0.95)], 0.024, 0.01, name + 'VeinR', mV, lift=0.5))
    return out

def fat_pads(body, root, name):
    """Epicardial fat: a few flat, irregular, semi-translucent pale-yellow drapes hugging the atrio-ventricular and
    interventricular grooves (ONE lumpy metaball chain per groove, sunk into the surface), never a row of kernels."""
    m = mat_organic(P.mix(FAT, WHITE, 0.1), rough=0.55, sss=0.5, coat=0.1, name=name + '_fat', radius=(1.0, 0.8, 0.4), scale=0.12)
    p = m.node_tree.nodes.get('Principled BSDF'); _inp(p, 'Alpha', 0.4); _inp(p, 'Specular IOR Level', 0.2); _blend(m)
    try: m.use_backface_culling = True
    except Exception: pass
    _noise_bump(m, p, scale=9.0, strength=0.2, detail=4.0, distance=0.03)
    out = []
    grooves = {'AV': [(-1.1, -0.9, 0.2), (-0.9, -1.05, 0.18), (-0.7, -1.15, 0.15), (-0.5, -1.22, 0.13), (-0.3, -1.25, 0.12), (-0.05, -1.24, 0.15), (0.2, -1.2, 0.2), (0.45, -1.12, 0.27), (0.7, -1.0, 0.35), (0.92, -0.82, 0.38), (1.15, -0.6, 0.4)],
               'IV': [(-0.1, -1.2, 0.3), (-0.08, -1.3, 0.05), (-0.05, -1.35, -0.2), (0.05, -1.34, -0.45), (0.15, -1.3, -0.7), (0.32, -1.2, -0.95), (0.5, -1.05, -1.2)]}
    rnd = random.Random(5)
    for key, pts in grooves.items():
        els = []
        for k, q in enumerate(pts):
            ok, loc, nrm, idx = nearest(body, q)
            if not ok or rnd.random() < 0.3: continue                                          # irregular: gaps along the groove
            c = Vector(loc) - Vector(nrm) * 0.05; w = rnd.uniform(0.6, 1.3)
            els.append((tuple(c), 0.062 * w, (1.8, 0.3, 1.0)))
            if k % 2 == 0: els.append((tuple(c + Vector((rnd.uniform(-0.08, 0.08), 0, rnd.uniform(-0.1, 0.1)))), 0.045 * w, (1.3, 0.3, 1.2)))
        if not els: continue
        o = meta_mesh(f'{name}Fat{key}', els, res=0.035, mat=m); displace(o, scale=0.3, strength=0.025, name=f'{name}fat{key}'); parent(o, root); out.append(o)
        try: o.visible_shadow = False
        except Exception: pass
    return out

def great_vessels(root, name, cut=False, top=3.4, cutter=None, hollow=False):
    """Aorta (crimson, arching up-back-left with three arch branches), pulmonary trunk (indigo, splitting left/right behind
    the aorta), superior + inferior vena cava (indigo, into the right atrium), four pulmonary veins (crimson, into the left
    atrium). hollow=True builds them as pipes with wall thickness and, with `cutter`, slices them on the cutaway plane."""
    mR = mat_vessel(OXY, name=name + '_art', coat=0.6, vein_scale=4.0); mB = mat_vessel(DEOXY, name=name + '_vein', coat=0.5, vein_scale=4.5); V = {}
    hw = 0.06 if hollow else 0.0
    # every trunk starts INSIDE the muscle with a flared root (first radius largest) so it grows out of the heart, then tapers
    V['aorta'] = tube(name + 'Aorta', [(0.12, 0.25, 0.45), (0.12, 0.3, 0.8), (0.1, 0.25, 1.35), (0.05, 0.4, 1.9), (0.2, 0.62, 2.35), (0.65, 0.95, 2.45), (1.0, 1.1, 2.1), (1.05, 1.15, 1.4), (1.0, 1.15, 0.3), (0.95, 1.1, -1.4), (0.9, 1.05, -2.6)],
                      0.3, mR, res=16, radii=[0.4, 0.31, 0.28, 0.275, 0.27, 0.26, 0.25, 0.24, 0.23, 0.22, 0.21])
    for i, (x, dx) in enumerate(((0.16, -0.12), (0.42, -0.02), (0.68, 0.12))):        # brachiocephalic, left carotid, left subclavian: curving up off the arch
        V[f'arch{i}'] = tube(f'{name}Arch{i}', [(x, 0.72 + 0.12 * i, 2.15), (x, 0.74 + 0.12 * i, 2.5), (x + dx * 0.8, 0.72 + 0.12 * i, 2.95), (x + dx * 2.2, 0.66 + 0.1 * i, top + 0.3)],
                             0.1, mR, res=12, radii=[0.16, 0.11, 0.095, 0.08])
    py = 0.32 if cut else -0.15
    # pulmonary trunk: up and BACK from the RV, bifurcating behind the ascending aorta under the arch
    V['pulm'] = tube(name + 'PulmTrunk', [(-0.3, py + 0.05, 0.45), (-0.3, py, 0.8), (-0.34, py + 0.05, 1.25), (-0.25, 0.35, 1.7), (-0.05, 0.62, 1.98)], 0.26, mB, res=14, radii=[0.36, 0.28, 0.26, 0.245, 0.235])
    V['pulmL'] = tube(name + 'PulmL', [(-0.05, 0.62, 1.98), (0.45, 0.78, 1.98), (1.2, 0.85, 1.82), (2.3, 0.9, 1.6)], 0.2, mB, res=12, radii=[0.235, 0.2, 0.17, 0.14])
    V['pulmR'] = tube(name + 'PulmR', [(-0.05, 0.62, 1.98), (-0.55, 0.78, 1.98), (-1.35, 0.85, 1.8), (-2.3, 0.9, 1.55)], 0.2, mB, res=12, radii=[0.235, 0.2, 0.17, 0.14])
    V['svc'] = tube(name + 'SVC', [(-0.9, 0.2, 0.95), (-0.9, 0.2, 1.3), (-0.88, 0.24, 1.7), (-0.85, 0.3, 2.3), (-0.7, 0.45, top + 0.2)], 0.22, mB, res=12, hollow=hw, radii=[0.3, 0.23, 0.22, 0.21, 0.2])
    V['ivc'] = tube(name + 'IVC', [(-1.02, 0.4, 0.2), (-1.05, 0.42, -0.15), (-1.1, 0.55, -0.8), (-1.1, 0.6, -1.8), (-1.1, 0.62, -2.9)], 0.23, mB, res=12, hollow=hw, radii=[0.31, 0.24, 0.235, 0.24, 0.25])
    for i, (sx, z) in enumerate(((1, 0.85), (1, 0.45), (-1, 0.85), (-1, 0.45))):
        V[f'pv{i}'] = tube(f'{name}PV{i}', [(0.8 + 0.25 * sx, 0.62, z - 0.05), (0.8 + 0.5 * sx, 0.75, z - 0.02), (0.8 + 0.95 * sx, 0.85, z + 0.02), (0.8 + 1.8 * sx, 0.95, z + 0.15 * (1 if i % 2 == 0 else -1))], 0.1, mR, res=10, radii=[0.15, 0.105, 0.095, 0.085])
    for k, o in list(V.items()):
        parent(o, root)
        if hollow and cutter is not None and k in ('svc', 'ivc'):
            o = to_mesh(o); boolean(o, cutter, name='cut', transfer=False); bake(o); V[k] = o
        elif hw <= 0 or k not in ('svc', 'ivc'):
            V[k] = organic_mesh(o, disp_scale=0.8, disp_strength=0.018 if k.startswith('pv') or k.startswith('arch') else 0.03, sub=0)
    return V

def chamber_anchors(root, name='Tag'):
    A = {}
    for k, c in CH.items(): A[k] = anchor(f'{name}{k}', tuple(c + Vector((0, -0.1, 0))), parent_to=root)
    return A

def heart_pose(h, keys_a, keys_v, rfps):
    """Keyframe the atria / ventricle contraction shape keys: lists of (t_sec, value)."""
    for kb, keys in ((h['keys']['atria'], keys_a), (h['keys']['vent'], keys_v)):
        for t, v in keys:
            kb.value = v; kb.keyframe_insert('value', frame=F(t, rfps))
    try:
        class _O:  # reuse kit's fcurve walker on the shape-key action
            animation_data = h['body'].data.shape_keys.animation_data
        for fc in _fcurves(_O):
            for k in fc.keyframe_points: k.interpolation = 'BEZIER'; k.easing = 'EASE_IN_OUT'
    except Exception as e: print('heart_pose ease', e)

def heartbeat_cycle(h, t0, rfps, n=1, period=0.83):
    """One or more textbook cycles from t0: atria fill -> atria contract -> ventricles contract -> relax."""
    ka, kv = [], []
    for i in range(n):
        t = t0 + i * period
        ka += [(t, 0.0), (t + period * 0.12, 0.85), (t + period * 0.3, 0.0)]
        kv += [(t + period * 0.22, 0.0), (t + period * 0.36, 1.0), (t + period * 0.6, 1.0), (t + period * 0.82, 0.0)]
    heart_pose(h, ka, kv, rfps)

def beat_all(h, t0, t1, rfps, period=0.83):
    """Continuous 72-bpm beating (shape keys) from t0 to t1."""
    n = max(1, int((t1 - t0) / period) + 1); heartbeat_cycle(h, t0, rfps, n=n, period=period)

def valve_schedule(t0, t1, period=0.83):
    """AV-valve open01 keys matching heartbeat_cycle: open while filling, shut during ventricular systole."""
    keys = []; t = t0
    while t < t1 + period:
        keys += [(t, 1.0), (t + period * 0.22, 1.0), (t + period * 0.30, 0.0), (t + period * 0.62, 0.0), (t + period * 0.72, 1.0)]
        t += period
    return keys

def key_alpha(m, keys):
    """keys = [(frame, alpha)] on a blended Principled material."""
    p = m.node_tree.nodes.get('Principled BSDF')
    for f, a in keys:
        p.inputs['Alpha'].default_value = a; p.inputs['Alpha'].keyframe_insert('default_value', frame=f)

def key_input(m, name, keys):
    p = m.node_tree.nodes.get('Principled BSDF')
    for f, v in keys:
        p.inputs[name].default_value = v; p.inputs[name].keyframe_insert('default_value', frame=f)

def wall_edges(body, z, x_from, direction, y=None):
    """Outer and inner edge points of a wall on the cut face: two successive ray casts running IN the (tilted) section
    plane, 0.03 behind it, at height z."""
    R = Euler(CUT_TILT).to_matrix(); u = R @ Vector((direction, 0, 0)); n = R @ Vector((0, 1, 0)); w = R @ Vector((0, 0, 1))
    piv = Vector(CUT_PIVOT); o = piv + u * (x_from - piv.x) * direction + w * (z - piv.z) + n * 0.03
    t = bvh_of(body); loc, nrm, idx, dist = t.ray_cast(o, u)
    if loc is None: return None, None
    outer = Vector(loc); loc2, nrm2, idx2, dist2 = t.ray_cast(outer + u * 0.01, u)
    return outer, (Vector(loc2) if loc2 is not None else None)

# ---- cell routes inside the cut heart (heart-local): right side via the SVC, left side via a pulmonary vein; each loops
#      back behind the heart (hidden by its back wall) so streams can run continuously on cyclic paths
ROUTE_R = [(-0.9, 0.25, 2.3), (-0.9, 0.2, 1.4), (-0.85, 0.18, 0.72), (-0.74, 0.15, 0.15), (-0.7, 0.12, -0.4), (-0.6, 0.1, -0.75), (-0.38, 0.1, -0.25),
           (-0.32, 0.1, 0.3), (-0.32, 0.14, 0.8), (-0.3, 0.3, 1.45), (-0.2, 0.8, 2.2), (-0.5, 2.2, 2.9), (-0.9, 1.8, 3.0)]
ROUTE_L = [(2.2, 0.95, 0.9), (1.35, 0.85, 0.7), (0.82, 0.3, 0.62), (0.75, 0.16, 0.12), (0.7, 0.1, -0.4), (0.62, 0.08, -0.72), (0.32, 0.02, -0.2),
           (0.16, 0.0, 0.32), (0.13, 0.12, 0.72), (0.1, 0.32, 1.4), (0.25, 0.7, 2.35), (1.0, 2.0, 2.9), (2.0, 1.8, 1.8)]
U_R = dict(svc=0.05, ra=0.16, tri=0.24, rv=0.38, out=0.54, pul=0.66, trunk=0.74)     # station fractions on ROUTE_R (cyclic, 13 segments)
U_L = dict(pv=0.05, la=0.16, mit=0.24, lv=0.38, out=0.54, aor=0.66, arch=0.76)

def rbc_stream(prefix, path, n, rfps, head_keys, spacing, R=0.075, mat=None, seed=2, nf=1, wobble=True):
    """A queue of cells on a path whose HEAD position (u) is keyed over time: head_keys = [(t_sec, u)]. Cell i trails the
    head by i*spacing; cells are hidden while their u <= 0 (not yet arrived) so the stream 'fills' station by station."""
    rnd = random.Random(seed); out = []; cyc = path.data.splines[0].use_cyclic_u
    keys = sorted(head_keys)
    def head(t):
        if t <= keys[0][0]: return keys[0][1]
        for (t0, u0), (t1, u1) in zip(keys[:-1], keys[1:]):
            if t0 <= t <= t1: return u0 + (u1 - u0) * (t - t0) / max(1e-6, t1 - t0)
        return keys[-1][1]
    for i in range(n):
        o = rbc(f'{prefix}{i}', R=R * rnd.uniform(0.85, 1.15), mat=mat)
        o.location = (rnd.uniform(-0.05, 0.05), rnd.uniform(-0.05, 0.05), rnd.uniform(-0.05, 0.05))
        c = o.constraints.new('FOLLOW_PATH'); c.target = path; c.use_fixed_location = True; c.use_curve_follow = True; c.forward_axis = 'FORWARD_Y'; c.up_axis = 'UP_Z'
        lag = i * spacing + rnd.uniform(0, spacing * 0.5); prev_vis = None
        for f in range(1, nf + 1, 2):
            t = (f - 1) / rfps; u = head(t) - lag; vis = u > 0.0 and (cyc or u < 1.0)
            c.offset_factor = (u % 1.0) if cyc else max(0.0, min(1.0, u)); c.keyframe_insert('offset_factor', frame=f)
            if vis != prev_vis: kf(o, 'hide_render', f, not vis); prev_vis = vis
        for fc in _fc_all(o):
            if fc.data_path.startswith('constraints'):
                for k in fc.keyframe_points: k.interpolation = 'LINEAR'
        if wobble:
            o.rotation_euler = (rnd.uniform(0, 3), rnd.uniform(0, 3), rnd.uniform(0, 3))
            kf(o, 'rotation_euler', 1, tuple(o.rotation_euler)); kf(o, 'rotation_euler', nf, (o.rotation_euler[0] + 2.0, o.rotation_euler[1] + 1.0, o.rotation_euler[2] + 1.5))
        out.append(o)
    return out

def time_route(o, waypoints, rfps, t_shot0, nf, ease_ends=False):
    """Key an object along waypoints [(t_abs, point)] (catmull through the points, time-parametrised) for this shot's
    frames. Before the first waypoint it waits at the start; after the last it stays at the end."""
    W = sorted(waypoints, key=lambda w: w[0]); P = [Vector(w[1]) for w in W]; T = [w[0] for w in W]
    P2 = [P[0]] + P + [P[-1]]
    def at(t):
        if t <= T[0]: return P[0]
        if t >= T[-1]: return P[-1]
        for i in range(len(T) - 1):
            if T[i] <= t <= T[i + 1]:
                u = (t - T[i]) / max(1e-6, T[i + 1] - T[i]); p0, p1, p2, p3 = P2[i], P2[i + 1], P2[i + 2], P2[i + 3]; u2, u3 = u * u, u * u * u
                return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u2 + (-p0 + 3 * p1 - 3 * p2 + p3) * u3)
        return P[-1]
    for f in range(1, nf + 1):
        kf(o, 'location', f, tuple(at(t_shot0 + (f - 1) / rfps)))
    kf_lin(o); return at

def cam_follow(at_fn, rfps, nf, t_shot0, offset, look_ahead=0.0, lens=40, smooth_n=8, tgt_offset=(0, 0, 0)):
    """Camera tracking a moving point (at_fn(t) -> Vector) from a fixed world offset; keys are smoothed over ~smooth_n frames."""
    pts = [at_fn(t_shot0 + (f - 1) / rfps) for f in range(1, nf + 1)]
    sm = []
    for i in range(len(pts)):
        a, b = max(0, i - smooth_n), min(len(pts), i + smooth_n + 1); sm.append(sum(pts[a:b], Vector()) / (b - a))
    cam, tgt = camera(tuple(sm[0] + Vector(offset)), tuple(sm[0] + Vector(tgt_offset)), lens=lens)
    for f in range(1, nf + 1, 2):
        kf(cam, 'location', f, tuple(sm[f - 1] + Vector(offset))); kf(tgt, 'location', f, tuple(sm[f - 1] + Vector(tgt_offset)))
    kf_lin(cam); kf_lin(tgt); return cam, tgt

# ================================================================= shared rigs
CUT_KEY = dict(target=(0, 0, -0.2), key=(5.5, -2.8, 4.5), key_e=2400, fill_e=110, rim_e=500, spot=44, blend=0.5)
CAM_HERO = ((-2.2, -7.4, 0.8), (0.05, 0.1, -0.2))          # 3/4 view of the cutaway from the viewer's left
CAM_CLOSE = ((-0.9, -2.9, 0.1), (0.0, 0.2, -0.25))         # inside-close (end of the dive = start of section 2)
CAM_EXT = ((0.4, -7.2, 0.5), (0.1, 0.1, -0.1))              # exterior hero framing

def cut_rig(nf, rfps, dur, section=2, beat=True, valves=True, split=False, cap=False, period=0.83, valve_keys=None, glow_col=None, motes_n=160):
    reset(); stage(section=section, **CUT_KEY)
    soft_light((-3.0, -5.0, 0.2), 110, size=3.0, color=(1.0, 0.85, 0.75), name='CavFill', target=(0, 0, -0.2))
    light('AREA', (-4.5, 3.5, 2.5), 600, THEME[section]['rim'], 'RimL', size=3.0, target=(0, 0, 0))
    vo = valve_keys if valve_keys is not None else (valve_schedule(0.0, dur, period) if valves else None)
    h = heart(cut=True, rfps=rfps, nf=nf, valves_open=vo, split=split, front_cap=cap)
    cavity_lights(h['root'])                       # warm light inside every hollow: the linings and papillary muscles shade from within
    if beat: beat_all(h, 0.0, dur, rfps, period=period)
    motes('Motes', motes_n, (0, 2.5, 0), (7, 5, 4.5), color=PLASMA, r=0.018, strength=3.5, seed=3, drift=0.25, rfps=rfps, nf=nf)
    motes('Dust', 90, (0, -2, 0), (8, 3, 5), color=DUST, r=0.012, strength=2.5, seed=9, drift=-0.15, rfps=rfps, nf=nf)
    backglow((0, 0, -0.2), glow_col or P.mix(CYAN, DEOXY_LIT, 0.4), r=5.5, strength=0.35)
    return h

def cut_streams(h, nf, rfps, dur, n=16, speed=0.09, R=0.07, spread=0.06):
    """Continuous cell traffic through both sides of the cutaway heart."""
    pr = path_curve('RouteR', ROUTE_R, cyclic=True); pl = path_curve('RouteL', ROUTE_L, cyclic=True); parent(pr, h['root']); parent(pl, h['root'])
    cr = rbc_flow('CellR', pr, n, rfps, nf, speed, R=R, mat=mat_cell('cellR', ox=0.0), seed=4, spread=spread, u_span=0.85)
    cl = rbc_flow('CellL', pl, n, rfps, nf, speed, R=R, mat=mat_cell('cellL', ox=1.0), seed=5, spread=spread, u_span=0.85)
    return pr, pl, cr, cl

def ext_rig(nf, rfps, dur, section=1, beat=True, split=False, key=(3.0, -5.5, 6.0), lungs_=False, glow_col=None, motes_n=160, key_e=2400):
    reset(); stage(target=(0, 0, 0), key=key, key_e=key_e, fill_e=150, rim_e=460, section=section)
    h = heart(beat=(0.1, 0.83, 0.025), rfps=rfps, nf=nf, split=split)
    if beat: beat_all(h, 0.0, dur, rfps)
    motes('Motes', motes_n, (0, 2.5, 0), (7, 5, 4.5), color=PLASMA, r=0.018, strength=3.5, seed=3, drift=0.25, rfps=rfps, nf=nf)
    motes('Dust', 90, (0, -2, 0), (8, 3, 5), color=DUST, r=0.012, strength=2.5, seed=9, drift=-0.15, rfps=rfps, nf=nf)
    backglow((0, 0, 0), glow_col or P.mix(OXY_LIT, GOLD, 0.35), r=5.5, strength=0.45)
    if lungs_: h['lungs'] = lungs(h['root'], rim=True)
    return h

def chest_rig(nf, rfps, dur, section=1, heart_kw=None, skin_alpha=0.10, rib_ghost=False, lungs_rim=True, beat=True):
    """Torso + ribcage + lungs around the beating heart."""
    reset(); stage(target=(0, 0, 0.2), key=(4.0, -7.0, 7.0), key_e=3200, fill_e=200, rim_e=600, spot=60, section=section)
    h = heart(beat=(0.1, 0.83, 0.025), rfps=rfps, nf=nf, **(heart_kw or {}))
    if beat: beat_all(h, 0.0, dur, rfps)
    root = h['root']
    h['lungs'] = lungs(root, rim=lungs_rim); h['ribs'] = ribcage(root, ghost=rib_ghost); h['torso'] = torso(root, a_center=skin_alpha)
    motes('Motes', 120, (0, 0, 0), (9, 6, 6), color=PLASMA, r=0.02, strength=3.0, seed=3, drift=0.2, rfps=rfps, nf=nf)
    backglow((0, 0, 0), P.mix(OXY_LIT, GOLD, 0.3), r=7, strength=0.4, depth=9)
    return h

# ================================================================= INTRO
def cold_open(nf, rfps, dur):
    """0-13.08: the hero heart beating at 72 bpm in the navy void with its great vessels; slow orbit + push-in + lens creep."""
    h = ext_rig(nf, rfps, dur, section=0)
    cam, tgt = cam_orbit((0.05, 0.1, -0.1), 9.6, 1.1, -28, 14, 0.0, dur, rfps, lens=45, push=7.0, tilt=0.5)
    lens_kf(cam, [(1, 42), (nf, 50)]); fg_cells('FG', 6, (1, -8, 0.6), (0, 0, 0), rfps, nf, seed=5, R=0.085, dist=3.6)
    focus(cam, 1, nf, h['body'], h['body'])

def dive_torso(nf, rfps, dur):
    """13.08-21.97: 'under the skin, behind the ribs' - from outside the chest the camera passes THROUGH the amber skin,
    between two ribs, past the lungs, and lands on the beating heart's wall (fills the frame = the next shot's first frame)."""
    h = chest_rig(nf, rfps, dur, section=0, skin_alpha=0.12)
    cam, tgt = cam_path([(0.0, (1.2, -19.0, 2.4), (0.0, 0.0, 0.6)), (dur * 0.42, (1.0, -8.5, 1.2), (0.2, 0.0, 0.4)), (dur * 0.72, (0.95, -3.2, 0.5), (0.35, 0.0, 0.2)), (dur, CAM_CLOSE_WALL[0], CAM_CLOSE_WALL[1])], rfps, lens=35)
    lens_kf(cam, [(1, 32), (F(dur * 0.6, rfps), 35), (nf, 35)])
    # the skin brightens as we cross it (its rim emission keyed up), then the ribs slide past
    key_input(h['torso'].data.materials[0], 'Emission Strength', [(F(dur * 0.40, rfps), 1.6), (F(dur * 0.55, rfps), 4.0), (F(dur * 0.66, rfps), 0.8)])
    focus(cam, 1, nf, h['torso'], h['body'])
CAM_CLOSE_WALL = ((0.9, -1.95, 0.25), (0.3, 0.0, 0.1))

def table_orbit(nf, rfps, dur):
    """21.97-30.48 (under the topic table): from the wall close-up the camera pulls back into a calm orbit of the heart;
    a glowing drop of blood arrives down the superior vena cava and enters the right atrium."""
    h = ext_rig(nf, rfps, dur, section=0)
    cam, tgt = cam_path([(0.0, CAM_CLOSE_WALL[0], CAM_CLOSE_WALL[1]), (dur * 0.35, (1.6, -7.5, 0.9), (0.1, 0.1, -0.1)), (dur, (-1.8, -8.0, 0.6), (0.05, 0.1, -0.15))], rfps, lens=35)
    lens_kf(cam, [(1, 35), (F(dur * 0.35, rfps), 45), (nf, 48)])
    drop = rbc('Drop', R=0.16, mat=mat_cell('drop_m', ox=0.0)); drop.data.materials.append(mat_glow(DEOXY_LIT, strength=6.0, name='dropglow'))
    glow = sphere('DropGlow', 0.26, mat=mat_glow(DEOXY_LIT, strength=1.8, name='dropglow2', alpha=0.35)); parent(glow, drop)
    pth = path_curve('DropPath', [(-0.7, 0.45, 4.2), (-0.85, 0.3, 2.3), (-0.9, 0.2, 1.5), (-0.9, 0.2, 1.05)]); parent(pth, h['root'])
    follow(drop, pth, [(F(dur * 0.3, rfps), 0.0), (F(dur * 0.92, rfps), 1.0)]); hide_until(drop, F(dur * 0.3, rfps)); hide_from(drop, F(dur * 0.93, rfps))
    fg_cells('FG', 5, (0, -8, 0.6), (0, 0, 0), rfps, nf, seed=8, R=0.085, dist=3.6)
    focus(cam, 1, nf, h['body'], h['body'])

# ================================================================= 1. THE HEART
def heart_in_chest(nf, rfps, dur):
    """33.08-40.33: pull-back reveal: the heart between the two lungs in the chest, slightly to the (anatomical) left,
    the ribcage and the amber torso silhouette around it."""
    h = chest_rig(nf, rfps, dur, section=1, skin_alpha=0.07, lungs_rim=False)
    A = {k: anchor('An' + k, v, parent_to=h['root']) for k, v in (('Heart', (0.1, -1.4, -0.3)), ('LungR', (-2.9, -0.4, 0.6)), ('LungL', (3.0, -0.3, 0.6)), ('Left', (1.3, -1.2, -1.5)))}
    cam, tgt = cam_path([(0.0, (0.4, -6.8, 0.5), (0.1, 0.0, -0.1)), (dur * 0.55, (0.8, -12.5, 1.2), (0.0, 0.0, 0.2)), (dur, (2.4, -13.5, 1.4), (0.0, 0.0, 0.2))], rfps, lens=45)
    lens_kf(cam, [(1, 48), (nf, 40)]); focus(cam, 1, nf, h['body'], h['body'])

def fist_compare(nf, rfps, dur):
    """40.33-44.66: the heart and a closed fist side by side, same size; the camera pans from the fist to the heart."""
    reset(); stage(target=(0, 0, 0), key=(2.0, -6.0, 6.5), key_e=2600, fill_e=170, rim_e=480, section=1)
    h = heart(loc=(1.5, 0, 0), beat=(0.1, 0.83, 0.025), rfps=rfps, nf=nf); beat_all(h, 0.0, dur, rfps)
    fist_root = empty('FistRoot', (-1.7, 0.1, -0.2)); fist(fist_root, loc=(0, 0, 0), s=1.45, rot=(0.15, -0.3, -0.35))
    kf(fist_root, 'rotation_euler', 1, (0, 0, -0.12)); kf(fist_root, 'rotation_euler', nf, (0, 0, 0.12)); kf_ease(fist_root)
    anchor('AnFist', (-1.7, -1.3, 1.1)); anchor('AnHeart2', (1.5, -1.4, 1.2))
    motes('Motes', 140, (0, 2.5, 0), (7, 5, 4.5), color=PLASMA, r=0.018, strength=3.5, seed=3, drift=0.25, rfps=rfps, nf=nf)
    backglow((0, 0, 0), P.mix(OXY_LIT, GOLD, 0.4), r=6, strength=0.4)
    cam, tgt = cam_path([(0.0, (-2.6, -8.2, 0.6), (-1.2, 0, -0.1)), (dur, (0.8, -7.6, 0.7), (0.3, 0, -0.1))], rfps, lens=50)
    focus(cam, 1, nf, fist_root, h['body'])

def cardiac_muscle(nf, rfps, dur):
    """44.66-56.01: the heart wall up close (coronaries, fat, sheen), then the camera dives THROUGH the wall (its surface
    dissolves) into a slab of cardiac muscle fibres: striations, branching bridges, nuclei; from 50 s the fibres
    contract and relax in pulses."""
    reset(); stage(target=(0.6, -1.0, -0.6), key=(3.5, -5.0, 4.0), key_e=2200, fill_e=140, rim_e=420, spot=50, section=1)
    h = heart(beat=(0.1, 0.83, 0.02), rfps=rfps, nf=nf, coat=0.75); beat_all(h, 0.0, dur, rfps)
    _blend(h['mat']); t_cross = 3.0
    key_alpha(h['mat'], [(F(t_cross - 0.2, rfps), 1.0), (F(t_cross + 0.9, rfps), 0.0)])
    for o in list(h.get('coronaries', [])) + list(h.get('fat', [])) + list(h['vessels'].values()): hide_from(o, F(t_cross + 0.5, rfps))
    slab_root = empty('Slab', (0.6, -0.2, -0.6)); slab_root.rotation_euler = (0.25, 0.0, 0.15)
    fib = muscle_fibres(slab_root, n=15, length=7.0, spacing=0.34); hide_until(slab_root, F(t_cross - 0.6, rfps))
    for o in bpy.data.objects:
        if o.name.startswith('Fib'): hide_until(o, F(t_cross - 0.6, rfps))
    anchor('AnFibre', (0.0, -0.5, 0.9), parent_to=slab_root); anchor('AnStria', (1.4, -0.5, -0.3), parent_to=slab_root)
    # contraction pulses from 'contract and relax' (50.05 s -> shot-local 5.4 s)
    t = 5.4
    while t < dur:
        for dt, sx, sz in ((0.0, 1.0, 1.0), (0.16, 0.86, 1.08), (0.5, 1.0, 1.0)): kf(slab_root, 'scale', F(t + dt, rfps), (sx, 1.0, sz))
        t += 0.83
    kf_ease(slab_root)
    motes('Motes', 160, (0, 0, 0), (6, 4, 4), color=PLASMA, r=0.016, strength=3.5, seed=3, drift=0.2, rfps=rfps, nf=nf)
    backglow((0.6, -0.2, -0.6), P.mix(OXY_LIT, GOLD, 0.4), r=6, strength=0.4)
    cam, tgt = cam_path([(0.0, (1.6, -4.6, 0.2), (0.5, -1.0, -0.5)), (t_cross - 0.4, (0.8, -2.2, -0.35), (0.6, -0.9, -0.6)), (t_cross + 1.2, (0.7, -1.9, -0.5), (0.6, -0.2, -0.6)),
                         (dur, (-0.9, -2.4, -0.2), (0.4, -0.2, -0.7))], rfps, lens=40)
    lens_kf(cam, [(1, 50), (F(t_cross, rfps), 38), (nf, 40)]); focus(cam, 1, nf, h['body'], slab_root)

def pump_idea(nf, rfps, dur):
    """56.01-63.66: the heart as a pump: cells arrive through the venae cavae and are sent on through the aorta in pulses
    (a pressure glow runs up the aorta on every beat)."""
    h = ext_rig(nf, rfps, dur, section=1)
    pin = path_curve('PIn', [(-0.7, 0.45, 4.0), (-0.85, 0.3, 2.3), (-0.9, 0.2, 1.5), (-0.9, 0.2, 1.1)]); parent(pin, h['root'])
    pin2 = path_curve('PIn2', [(-1.1, 0.62, -3.6), (-1.1, 0.6, -1.8), (-1.1, 0.55, -0.8), (-1.05, 0.42, -0.1)]); parent(pin2, h['root'])
    pout = path_curve('POut', [(0.12, 0.3, 0.9), (0.1, 0.25, 1.35), (0.05, 0.4, 1.9), (0.2, 0.62, 2.35), (0.65, 0.95, 2.45), (1.0, 1.1, 2.1), (1.05, 1.15, 1.4), (1.0, 1.15, 0.3), (0.95, 1.1, -1.4), (0.9, 1.05, -3.2)]); parent(pout, h['root'])
    mb = mat_cell('cin', ox=0.0); mr = mat_cell('cout', ox=1.0)
    rbc_flow('In', pin, 10, rfps, nf, 0.28, R=0.085, mat=mb, seed=2, spread=0.08, u_span=1.0)
    rbc_flow('In2', pin2, 10, rfps, nf, 0.28, R=0.085, mat=mb, seed=3, spread=0.08, u_span=1.0)
    rbc_flow('Out', pout, 18, rfps, nf, 0.16, R=0.085, mat=mr, seed=4, spread=0.1, u_span=1.0)
    gl = glow_sleeve('AortaGlow', [(0.12, 0.3, 0.8), (0.1, 0.25, 1.35), (0.05, 0.4, 1.9), (0.2, 0.62, 2.35), (0.65, 0.95, 2.45), (1.0, 1.1, 2.1), (1.05, 1.15, 1.4)], 0.36, GOLD, strength=1.2, alpha=0.3); parent(gl, h['root'])
    t = 0.4; pm = gl.data.materials[0]
    while t < dur:
        key_input(pm, 'Emission Strength', [(F(t, rfps), 0.2), (F(t + 0.14, rfps), 2.4), (F(t + 0.5, rfps), 0.2)]); t += 0.83
    anchor('AnIn', (-0.85, 0.3, 2.4), parent_to=h['root']); anchor('AnOut', (0.65, 0.95, 2.6), parent_to=h['root'])
    cam, tgt = cam_orbit((0.05, 0.1, 0.2), 8.4, 0.9, -18, 20, 0.0, dur, rfps, lens=45)
    fg_cells('FG', 5, (0, -8, 0.6), (0, 0, 0), rfps, nf, seed=6, R=0.085, dist=3.6); focus(cam, 1, nf, h['body'], h['body'])

def two_pumps(nf, rfps, dur):
    """63.66-71.0: 'not one pump but two': the right half of the heart tints indigo, the left crimson, both beating."""
    h = ext_rig(nf, rfps, dur, section=1, split=True)
    set_split(h['mat'], [(F(2.6, rfps), 0.0), (F(4.0, rfps), 1.0)])
    anchor('AnRight', (-0.9, -1.2, -0.5), parent_to=h['root']); anchor('AnLeft', (0.95, -1.15, -0.7), parent_to=h['root'])
    cam, tgt = cam_orbit((0.05, 0.1, -0.1), 8.0, 0.6, 12, -14, 0.0, dur, rfps, lens=48, push=7.0)
    fg_cells('FG', 5, (0, -8, 0.6), (0, 0, 0), rfps, nf, seed=7, R=0.085, dist=3.6); focus(cam, 1, nf, h['body'], h['body'])

def dive_inside(nf, rfps, dur):
    """71.0-75.04: 'we must go inside': the camera pushes into the front wall, which dissolves, revealing the four chambers;
    ends inside-close = the first frame of section 2."""
    h = cut_rig(nf, rfps, dur, section=2, cap=True, split=True)
    set_split(h['mat'], [(1, 1.0), (F(1.6, rfps), 0.0)]); set_split(h['cap_mat'], [(1, 1.0), (F(1.6, rfps), 0.0)])
    key_alpha(h['cap_mat'], [(F(dur * 0.55, rfps), 1.0), (F(dur * 0.82, rfps), 0.0)])
    cut_streams(h, nf, rfps, dur, n=14)
    cam, tgt = cam_path([(0.0, CAM_EXT[0], CAM_EXT[1]), (dur * 0.6, (-0.6, -3.6, 0.2), (0.0, 0.1, -0.2)), (dur, CAM_CLOSE[0], CAM_CLOSE[1])], rfps, lens=48)
    lens_kf(cam, [(1, 48), (nf, 35)]); focus(cam, 1, nf, h['body'], h['body'])

# ================================================================= 2. CHAMBERS AND VALVES
def four_chambers(nf, rfps, dur):
    """77.64-90.55: from inside-close the camera settles into the hero 3/4 view of the four-chamber cutaway: atria above
    (RA, LA), ventricles below (RV, LV), cells streaming through both sides."""
    h = cut_rig(nf, rfps, dur, section=2); cut_streams(h, nf, rfps, dur)
    chamber_anchors(h['root'], 'An')
    cam, tgt = cam_path([(0.0, CAM_CLOSE[0], CAM_CLOSE[1]), (2.8, CAM_HERO[0], CAM_HERO[1]), (dur, (-1.6, -7.6, 0.5), (0.05, 0.1, -0.25))], rfps, lens=45)
    lens_kf(cam, [(1, 35), (F(2.8, rfps), 45), (nf, 47)]); focus(cam, 1, nf, h['body'], h['body'])

def receive_pump(nf, rfps, dur):
    """90.55-96.32: atria receive (camera on the upper chambers, cells pouring in) then ventricles pump out (tilt down,
    cells leaving through the artery mouths, a pressure glow at each outflow)."""
    h = cut_rig(nf, rfps, dur, section=2); pr, pl, cr, cl = cut_streams(h, nf, rfps, dur, n=20, speed=0.11)
    anchor('AnAtria', (0.0, -0.1, 1.05), parent_to=h['root']); anchor('AnVent', (0.05, -0.1, -0.95), parent_to=h['root'])
    for nm, pts in (('GlowPul', ROUTE_R[6:10]), ('GlowAor', ROUTE_L[6:10])):
        g = glow_sleeve(nm, pts, 0.22, GOLD, strength=1.4, alpha=0.18); parent(g, h['root']); hide_until(g, F(3.0, rfps))
        key_input(g.data.materials[0], 'Emission Strength', [(F(3.0, rfps), 0.3), (F(3.6, rfps), 2.2), (F(4.4, rfps), 0.6), (F(5.0, rfps), 2.2)])
    cam, tgt = cam_path([(0.0, (-2.0, -7.0, 1.4), (0.0, 0.1, 0.55)), (2.6, (-1.6, -6.2, 1.2), (0.0, 0.1, 0.5)), (dur, (-2.0, -6.6, -0.3), (0.0, 0.1, -0.6))], rfps, lens=48)
    focus(cam, 1, nf, h['body'], h['body'])

def septum(nf, rfps, dur):
    """96.32-109.07: the thick muscular septum between the two sides lights up gold; then indigo cells on the right and
    crimson cells on the left stream against it and never mix."""
    h = cut_rig(nf, rfps, dur, section=2); cut_streams(h, nf, rfps, dur, n=22, speed=0.1)
    # the septum lights up as the muscle band it is (emission mask on the cut face + linings), pulsing gently while it is named
    keys = [(1, 0.0), (F(2.0, rfps), 0.0), (F(2.8, rfps), 1.0)]; t = 2.8
    while t + 1.2 < dur: keys += [(F(t + 0.6, rfps), 0.55), (F(t + 1.2, rfps), 1.0)]; t += 1.2
    set_septum(h, keys)
    anchor('AnSeptum', (0.12, -0.15, -0.3), parent_to=h['root']); anchor('AnBlue', (-0.75, -0.1, -0.7), parent_to=h['root']); anchor('AnRed', (0.72, -0.1, -0.75), parent_to=h['root'])
    cam, tgt = cam_path([(0.0, CAM_HERO[0], CAM_HERO[1]), (5.0, (-1.2, -5.6, 0.3), (0.1, 0.1, -0.4)), (dur, (1.4, -5.8, 0.4), (0.1, 0.1, -0.45))], rfps, lens=48)
    lens_kf(cam, [(1, 45), (F(5.0, rfps), 52), (nf, 50)]); focus(cam, 1, nf, h['body'], h['body'])

def wall_thickness(nf, rfps, dur):
    """109.07-126.15: wall thickness measured on the cut lip: the thin atrial wall against the thick ventricle wall
    (right side first), then the camera pans to the left ventricle, the thickest of all."""
    h = cut_rig(nf, rfps, dur, section=2); cut_streams(h, nf, rfps, dur, n=12)
    b = h['body']
    for nm, z, x0, d in (('RA', 0.62, -3.0, 1), ('RV', -0.62, -3.0, 1), ('LA', 0.62, 3.0, -1), ('LV', -0.74, 3.0, -1)):
        o_, i_ = wall_edges(b, z, x0, d)
        if o_ is not None and i_ is not None:
            anchor(f'AnW{nm}o', tuple(o_ + Vector((0, -0.05, 0))), parent_to=h['root']); anchor(f'AnW{nm}i', tuple(i_ + Vector((0, -0.05, 0))), parent_to=h['root'])
            print('WALL', nm, round((i_ - o_).length, 3))
    for nm, pts in (('GlowLV', [(1.42, cut_y(1.42, -0.2) - 0.05, -0.2), (1.5, cut_y(1.5, -0.75) - 0.05, -0.75), (1.4, cut_y(1.4, -1.35) - 0.05, -1.35)]),):
        g = glow_sleeve(nm, pts, 0.2, GOLD, strength=1.5, alpha=0.35); parent(g, h['root']); hide_until(g, F(10.2, rfps))
    cam, tgt = cam_path([(0.0, (-3.2, -6.4, 0.6), (-0.7, 0.1, -0.05)), (4.5, (-3.0, -5.4, 0.4), (-0.75, 0.1, -0.1)), (9.5, (-2.4, -5.6, 0.3), (-0.3, 0.1, -0.15)), (12.5, (1.6, -5.4, 0.1), (0.75, 0.1, -0.5)), (dur, (2.2, -5.2, 0.0), (0.8, 0.1, -0.6))], rfps, lens=50)
    focus(cam, 1, nf, h['body'], h['body'])

def valves_exits(nf, rfps, dur):
    """126.15-133.23: a valve at every exit: four glowing rings pulse at the tricuspid, mitral, pulmonary and aortic
    positions while the valves open and shut with the beat."""
    h = cut_rig(nf, rfps, dur, section=2); cut_streams(h, nf, rfps, dur, n=14)
    for k, (c, r) in {'tri': (VALVE['tri'], 0.26), 'mit': (VALVE['mit'], 0.24), 'pul': (VALVE['pul'], 0.2), 'aor': (VALVE['aor'], 0.19)}.items():
        ring = obj_add('torus', 'Ring' + k, major_radius=r, minor_radius=0.03, major_segments=64, minor_segments=12, location=tuple(c + Vector((0, -0.05, 0))))
        if k in ('pul', 'aor'): ring.rotation_euler = (0, 0, 0)
        setmat(ring, mat_glow(GOLD, strength=2.0, name='ring' + k, alpha=0.6)); smooth(ring, auto=False); parent(ring, h['root']); hide_until(ring, F(0.8, rfps))
        anchor('AnV' + k, tuple(c + Vector((0, -0.12, 0))), parent_to=h['root'])
        pm = ring.data.materials[0]; t = 0.8
        while t < dur: key_input(pm, 'Emission Strength', [(F(t, rfps), 0.8), (F(t + 0.4, rfps), 3.0), (F(t + 0.83, rfps), 0.8)]); t += 0.83
    cam, tgt = cam_path([(0.0, CAM_HERO[0], CAM_HERO[1]), (dur, (-1.5, -6.3, 0.4), (0.0, 0.1, 0.05))], rfps, lens=48)
    lens_kf(cam, [(1, 45), (nf, 52)]); focus(cam, 1, nf, h['body'], h['body'])

# (the valve hero rigs live below, after the section-4 helpers: valve_hero_rig / av_valve_shut / semilunar_shut)

# ================================================================= 3. ONE HEARTBEAT (staged streams on the cutaway rig)
SP = 0.012            # stream spacing in path fraction (~one cell diameter)
def stage_streams(h, nf, rfps, keysR, keysL, n=18, R=0.07, prefix=''):
    pr = path_curve(prefix + 'RouteR', ROUTE_R, cyclic=True); pl = path_curve(prefix + 'RouteL', ROUTE_L, cyclic=True); parent(pr, h['root']); parent(pl, h['root'])
    cr = rbc_stream(prefix + 'SR', pr, n, rfps, keysR, SP, R=R, mat=mat_cell(prefix + 'cR', ox=0.0), seed=4, nf=nf)
    cl = rbc_stream(prefix + 'SL', pl, n, rfps, keysL, SP, R=R, mat=mat_cell(prefix + 'cL', ox=1.0), seed=5, nf=nf)
    return cr, cl

def beat_intro(nf, rfps, dur):
    """155.41-158.85: 'what happens in one heartbeat': the cutaway heart beating normally, cells in transit, slow push."""
    h = cut_rig(nf, rfps, dur, section=3, glow_col=P.mix(OXY_LIT, GOLD, 0.4)); cut_streams(h, nf, rfps, dur, n=14)
    cam, tgt = cam_path([(0.0, CAM_HERO[0], CAM_HERO[1]), (dur, (-1.9, -6.9, 0.7), (0.05, 0.1, -0.15))], rfps, lens=45)
    lens_kf(cam, [(1, 45), (nf, 48)]); focus(cam, 1, nf, h['body'], h['body'])

def atria_fill(nf, rfps, dur):
    """158.85-168.54: both atria fill (queues of cells arrive from the venae cavae and the pulmonary veins and pool in the
    atria); then the atria contract and the cells drop through the open AV valves into the ventricles."""
    vk = [(0.0, 1.0), (dur, 1.0)]                                              # AV valves stay open (filling), artery valves shut
    h = cut_rig(nf, rfps, dur, section=3, beat=False, valve_keys=vk, glow_col=P.mix(OXY_LIT, GOLD, 0.4))
    heart_pose(h, [(3.9, 0.0), (4.7, 0.85), (5.6, 0.85), (6.6, 0.0)], [(0.0, 0.0)], rfps)
    keysR = [(0.0, 0.03), (2.8, U_R['ra'] + 0.07), (4.2, U_R['ra'] + 0.07), (6.6, U_R['rv'] + 0.07), (dur, U_R['rv'] + 0.08)]
    keysL = [(0.0, 0.03), (2.8, U_L['la'] + 0.07), (4.2, U_L['la'] + 0.07), (6.6, U_L['lv'] + 0.07), (dur, U_L['lv'] + 0.08)]
    stage_streams(h, nf, rfps, keysR, keysL, n=20)
    chamber_anchors(h['root'], 'An')
    cam, tgt = cam_path([(0.0, (-1.9, -6.9, 0.7), (0.05, 0.1, -0.15)), (3.0, (-1.9, -6.4, 1.0), (0.05, 0.1, 0.3)), (7.0, (-1.7, -6.4, 0.2), (0.05, 0.1, -0.3)), (dur, (-1.6, -6.6, 0.0), (0.05, 0.1, -0.4))], rfps, lens=48)
    focus(cam, 1, nf, h['body'], h['body'])

def vent_contract(nf, rfps, dur):
    """168.54-178.0: the ventricles contract: the AV valves snap shut (gold flash on both rings) and the cells are driven
    up the outflow tracts into the pulmonary artery and the aorta (pressure glow)."""
    vk = [(0.0, 1.0), (0.7, 1.0), (1.15, 0.0), (dur, 0.0)]
    h = cut_rig(nf, rfps, dur, section=3, beat=False, valve_keys=vk, glow_col=P.mix(OXY_LIT, GOLD, 0.4))
    heart_pose(h, [(0.0, 0.0)], [(0.3, 0.0), (1.6, 1.0), (dur, 1.0)], rfps)
    keysR = [(0.0, U_R['rv'] + 0.08), (1.0, U_R['rv'] + 0.08), (5.5, U_R['trunk'] + 0.06), (dur, U_R['trunk'] + 0.12)]
    keysL = [(0.0, U_L['lv'] + 0.08), (1.0, U_L['lv'] + 0.08), (5.5, U_L['arch'] + 0.04), (dur, U_L['arch'] + 0.1)]
    stage_streams(h, nf, rfps, keysR, keysL, n=20)
    for k, (c, r) in {'tri': (VALVE['tri'], 0.26), 'mit': (VALVE['mit'], 0.24)}.items():
        ring = obj_add('torus', 'Flash' + k, major_radius=r, minor_radius=0.03, major_segments=64, minor_segments=12, location=tuple(c + Vector((0, -0.05, 0))))
        setmat(ring, mat_glow(GOLD, strength=3.0, name='flash' + k, alpha=0.7)); smooth(ring, auto=False); parent(ring, h['root']); show_between(ring, F(1.0, rfps), F(2.2, rfps))
        anchor('AnV' + k, tuple(c + Vector((0, -0.12, 0))), parent_to=h['root'])
    for nm, pts in (('GlowPul', ROUTE_R[6:11]), ('GlowAor', ROUTE_L[6:11])):
        g = glow_sleeve(nm, pts, 0.22, GOLD, strength=1.6, alpha=0.18); parent(g, h['root']); hide_until(g, F(2.4, rfps))
        key_input(g.data.materials[0], 'Emission Strength', [(F(2.4, rfps), 0.2), (F(3.2, rfps), 2.6), (F(6.0, rfps), 1.0), (F(dur, rfps), 0.3)])
    chamber_anchors(h['root'], 'An'); anchor('AnPulm', (-0.3, 0.15, 1.35), parent_to=h['root']); anchor('AnAorta', (0.12, 0.15, 1.35), parent_to=h['root'])
    cam, tgt = cam_path([(0.0, (-1.6, -6.6, 0.0), (0.05, 0.1, -0.4)), (2.6, (-1.9, -6.2, -0.1), (0.0, 0.1, -0.35)), (dur, (-1.5, -6.8, 1.0), (0.0, 0.1, 0.5))], rfps, lens=48)
    focus(cam, 1, nf, h['body'], h['body'])

def relax_refill(nf, rfps, dur):
    """178.0-183.37: the whole heart relaxes for a moment (the ventricles let go, the AV valves reopen) and fresh cells
    start filling the atria again while the last cells drift on up the arteries."""
    vk = [(0.0, 0.0), (0.9, 0.0), (1.5, 1.0), (dur, 1.0)]
    h = cut_rig(nf, rfps, dur, section=3, beat=False, valve_keys=vk, glow_col=P.mix(OXY_LIT, GOLD, 0.4))
    heart_pose(h, [(0.0, 0.0)], [(0.0, 1.0), (0.4, 1.0), (1.4, 0.0), (dur, 0.0)], rfps)
    stage_streams(h, nf, rfps, [(0.0, U_R['trunk'] + 0.12), (dur, U_R['trunk'] + 0.24)], [(0.0, U_L['arch'] + 0.1), (dur, U_L['arch'] + 0.22)], n=14, prefix='old')
    stage_streams(h, nf, rfps, [(1.3, 0.02), (dur, U_R['ra'] + 0.07)], [(1.3, 0.02), (dur, U_L['la'] + 0.07)], n=20, prefix='new')
    chamber_anchors(h['root'], 'An')
    cam, tgt = cam_path([(0.0, (-1.5, -6.8, 1.0), (0.0, 0.1, 0.5)), (dur, CAM_HERO[0], CAM_HERO[1])], rfps, lens=48)
    lens_kf(cam, [(1, 48), (nf, 45)]); focus(cam, 1, nf, h['body'], h['body'])

BEAT0_24 = 0.45        # shot-local start of the first beat cycle in the stethoscope shot (period 0.83): Lub at +0.25, Dub at +0.62
def stethoscope_chest(nf, rfps, dur):
    """183.37-198.13: a stethoscope pressed on the chest, the heart glowing and beating under the amber skin; a gold
    pulse ring spreads from the chest piece on every Lub (AV valves close) and a cyan one on every Dub (artery valves)."""
    reset(); stage(target=(0.6, -2.0, -0.5), key=(4.0, -7.5, 6.0), key_e=3000, fill_e=220, rim_e=600, spot=55, section=3)
    h = heart(rfps=rfps, nf=nf, coat=0.75); beat_all(h, BEAT0_24, dur, rfps)
    root = h['root']; h['lungs'] = lungs(root, rim=True); h['ribs'] = ribcage(root, ghost=True); h['torso'] = torso(root, a_center=0.3, a_rim=0.9, emit=1.2)
    for o in h['lungs']['lobes']: o.hide_render = True
    hm = h['mat']; p = hm.node_tree.nodes.get('Principled BSDF'); _inp(p, 'Emission Color', (*OXY_LIT, 1))
    t = BEAT0_24
    while t < dur:
        key_input(hm, 'Emission Strength', [(F(t + 0.2, rfps), 0.15), (F(t + 0.32, rfps), 1.4), (F(t + 0.75, rfps), 0.15)]); t += 0.83
    contact = (0.9, -2.12, -0.9); steth = stethoscope(root, loc=contact, s=0.55)
    anchor('AnChestPiece', (contact[0], contact[1] - 0.5, contact[2] + 0.35)); anchor('AnHeartGhost', (0.0, -1.5, 0.2), parent_to=root)
    t = BEAT0_24; k = 0
    while t + 0.62 < dur:
        for dt, col, nm in ((0.25, GOLD, 'Lub'), (0.62, CYAN, 'Dub')):
            ring = obj_add('torus', f'Pulse{nm}{k}', major_radius=0.35, minor_radius=0.03, major_segments=64, minor_segments=12, location=(contact[0], contact[1] - 0.06, contact[2]))
            ring.rotation_euler = (math.pi / 2, 0, 0); m = mat_glow(col, strength=4.0, name=f'pulse{nm}{k}', alpha=0.8); setmat(ring, m); smooth(ring, auto=False)
            f0 = F(t + dt, rfps); show_between(ring, f0, f0 + int(0.45 * rfps) + 1)
            kf(ring, 'scale', f0, (0.6, 0.6, 0.6)); kf(ring, 'scale', f0 + int(0.45 * rfps) + 1, (3.2, 3.2, 3.2)); kf_ease(ring)
            key_alpha(m, [(f0, 0.9), (f0 + int(0.45 * rfps) + 1, 0.0)])
        t += 0.83; k += 1
    motes('Motes', 120, (0, -2, 0), (8, 4, 6), color=PLASMA, r=0.02, strength=3.0, seed=3, drift=0.2, rfps=rfps, nf=nf)
    backglow((0, 0, 0), P.mix(OXY_LIT, GOLD, 0.3), r=7, strength=0.4, depth=9)
    cam, tgt = cam_orbit((0.7, -2.2, -0.5), 6.8, 0.4, -22, 16, 0.0, dur, rfps, lens=50, push=6.0)
    focus(cam, 1, nf, steth, steth)

BEAT0_25 = 0.5
def cycle_timer(nf, rfps, dur):
    """198.13-205.59: the whole cycle at true speed (under a second) and again: the cutaway heart beating with valves and
    streams, a slow orbit; the overlay's ticking timeline is locked to BEAT0_25 + k * 0.83 s."""
    h = cut_rig(nf, rfps, dur, section=3, beat=False, valve_keys=valve_schedule(BEAT0_25, dur), glow_col=P.mix(OXY_LIT, GOLD, 0.4))
    beat_all(h, BEAT0_25, dur, rfps); cut_streams(h, nf, rfps, dur, n=18, speed=0.14)
    cam, tgt = cam_orbit((0.05, 0.1, -0.2), 7.4, 0.8, -18, 10, 0.0, dur, rfps, lens=46)
    focus(cam, 1, nf, h['body'], h['body'])

# ================================================================= 4. BLOOD VESSELS
def vessel_tree(root, name, start, direction, depth, r0, mat, rnd, length=1.6, spread=0.5, tips=None, mat_tip=None):
    """Recursive bevelled-curve branching (2 children per node, tapering, slightly curved). Returns the list of tip points."""
    tips = [] if tips is None else tips; p0 = Vector(start); d = Vector(direction).normalized()
    axis = d.cross(Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))).normalized()
    side = d.cross(axis).normalized() * spread * length * rnd.uniform(0.5, 1.0)
    p1 = p0 + d * length; mid = (p0 + p1) / 2 + side * 0.4
    o = tube(f'{name}', catmull([tuple(p0), tuple(mid), tuple(p1)], 10), r0, mat, r1=r0 * 0.72, res=8, bevel_res=6); parent(o, root)
    if depth <= 1: tips.append(p1); return tips
    for k, sgn in enumerate((-1, 1)):
        nd = (d + side.normalized() * sgn * rnd.uniform(0.45, 0.9) + axis * rnd.uniform(-0.3, 0.3)).normalized()
        vessel_tree(root, f'{name}{k}', p1, nd, depth - 1, r0 * 0.68, mat, rnd, length=length * 0.78, spread=spread, tips=tips)
    return tips

def vessel_network(nf, rfps, dur):
    """208.19-220.5: the vessel network branching out of the heart: crimson arteries fan out from the aorta, indigo veins
    gather back into the venae cavae, thin gradient capillaries join the two; pull-back reveal then a slow orbit."""
    h = ext_rig(nf, rfps, dur, section=4, key=(4.0, -8.0, 8.0), key_e=4200, motes_n=220)
    rnd = random.Random(21); mA = mat_vessel(OXY, name='netA', coat=0.55, emit=0.15); mV = mat_vessel(DEOXY, name='netV', coat=0.5, emit=0.15); root = h['root']
    tipsA, tipsV = [], []
    for nm, st, d, dep in (('ArtUp', (0.4, 0.75, 3.4), (0.15, 0.05, 1), 4), ('ArtDn', (0.9, 1.05, -2.8), (0.1, 0.0, -1), 4), ('ArtL', (1.05, 0.85, 2.6), (1, 0.1, 0.35), 3), ('ArtR', (0.05, 0.72, 3.1), (-1, 0.1, 0.35), 3)):
        vessel_tree(root, nm, st, d, dep, 0.11, mA, rnd, length=2.0, tips=tipsA)
    for nm, st, d, dep in (('VeinUp', (-0.7, 0.45, 3.6), (-0.2, 0.05, 1), 4), ('VeinDn', (-1.1, 0.62, -3.1), (-0.1, 0.0, -1), 4), ('VeinL', (-0.45, 0.5, 3.2), (1, 0.15, 0.6), 3), ('VeinR', (-0.95, 0.5, 3.0), (-1, 0.1, 0.5), 3)):
        vessel_tree(root, nm, st, d, dep, 0.11, mV, rnd, length=2.0, tips=tipsV)
    mG = mat_gradient(OXY, DEOXY, axis='Z', lo=-0.5, hi=0.5, name='netCap', emit=0.6)
    used = set(); k = 0
    for ta in tipsA:
        best = min(((tv - ta).length, i) for i, tv in enumerate(tipsV) if i not in used) if len(used) < len(tipsV) else None
        if best is None or best[0] > 4.5: continue
        used.add(best[1]); tv = tipsV[best[1]]; mid = (ta + tv) / 2 + Vector((rnd.uniform(-0.4, 0.4), rnd.uniform(-0.3, 0.3), rnd.uniform(-0.4, 0.4)))
        c = tube(f'CapLink{k}', catmull([tuple(ta), tuple(mid), tuple(tv)], 12), 0.03, mG, res=8, bevel_res=5); parent(c, root); k += 1
    anchor('AnArt', tuple(tipsA[0] * 0.5 + Vector((0.4, 0.75, 3.4)) * 0.5), parent_to=root); anchor('AnVein', tuple(tipsV[0] * 0.5 + Vector((-0.7, 0.45, 3.6)) * 0.5), parent_to=root)
    anchor('AnCap', tuple((tipsA[0] + tipsV[0]) / 2), parent_to=root)
    cam, tgt = cam_path([(0.0, CAM_EXT[0], CAM_EXT[1]), (6.0, (1.5, -21.0, 0.8), (0.1, 0.4, 0.3)), (dur, (-4.5, -20.0, 1.5), (0.1, 0.4, 0.3))], rfps, lens=45)
    lens_kf(cam, [(1, 48), (F(6.0, rfps), 40), (nf, 40)]); focus(cam, 1, nf, h['body'], h['body'])

def mini_heart(loc, s, rfps, nf, dur, name='Mini'):
    h = heart(loc=loc, beat=(0.1, 0.83, 0.025), rfps=rfps, nf=nf, name=name, coronaries=False, fat=False); beat_all(h, 0.0, dur, rfps)
    h['root'].scale = (s, s, s); return h

def artery_section(nf, rfps, dur):
    """220.5-231.47: an artery cut open: cells race away from the heart (at the left) through the lumen; the three wall
    layers (endothelium, thick elastic-muscular media, outer adventitia) show on the cut rings, and the wall pulses."""
    reset(); stage(target=(0, 0, 0), key=(3.0, -6.0, 6.5), key_e=2600, fill_e=170, rim_e=520, spot=52, section=4)
    root = empty('ArtRoot', (0, 0, 0)); art = vessel_section(root, 'Art', kind='artery', loc=(0, 0, 0), length=7.0, r=0.55, cut_front=True)
    mh = mini_heart((-6.6, 0.8, -0.6), 0.55, rfps, nf, dur)
    mr = mat_cell('art_cells', ox=1.0); cells = rbc_flow('C', art['path'], 22, rfps, nf, 0.19, R=0.11, mat=mr, seed=6, spread=0.22, u_span=0.95)
    pulse_wall(art, 3.6, dur, rfps, period=0.83, amp=0.07)
    ro = art['r_out']; ti, tm, ta = art['thick']
    for nm, rr in (('AnIntima', art['r_in'] + ti * 0.5), ('AnMedia', art['r_in'] + ti + tm * 0.5), ('AnAdv', art['r_in'] + ti + tm + ta * 0.5)):
        anchor(nm, (3.49, 0.0, rr))
    anchor('AnLumen', (2.0, 0.0, 0.0))
    motes('Motes', 160, (0, 2, 0), (8, 4, 5), color=PLASMA, r=0.02, strength=3.5, seed=3, drift=0.25, rfps=rfps, nf=nf)
    backglow((0, 0, 0), P.mix(OXY_LIT, GOLD, 0.35), r=6, strength=0.4)
    cam, tgt = cam_path([(0.0, (-2.5, -8.5, 1.2), (-2.0, 0.3, -0.2)), (2.6, (2.5, -7.5, 1.6), (0.5, 0.0, 0.0)), (7.0, (5.6, -4.6, 1.8), (2.6, 0.0, 0.1)), (dur, (4.4, -5.0, 1.2), (2.0, 0.0, 0.0))], rfps, lens=45)
    focus(cam, 1, nf, mh['body'], art['layers']['media'])

def vein_section(nf, rfps, dur):
    """231.47-246.25: a vein cut open (thin wall, cells drifting back toward the heart at the right); then the camera pans
    to a vein opened along its top where pocket valves let the cells pass forward and snap shut when they try to fall back."""
    reset(); stage(target=(0, 0, 0), key=(-2.0, -6.0, 6.5), key_e=2600, fill_e=170, rim_e=520, spot=58, section=4)
    root = empty('VeinRoot', (0, 0, 0)); vs = vessel_section(root, 'Vein', kind='vein', loc=(-4.5, 0, 0), length=6.0, r=0.6, cut_front=True)
    mh = mini_heart((11.0, 0.9, -0.5), 0.55, rfps, nf, dur)
    mb = mat_cell('vein_cells', ox=0.0); rbc_flow('C', vs['path'], 18, rfps, nf, 0.09, R=0.11, mat=mb, seed=6, spread=0.25, u_span=0.95)
    vk = [(0.0, 1.0), (11.2, 1.0), (11.8, 0.0), (dur, 0.0)]
    vv = vein_valves(root, 'VV', loc=(4.0, 0, 0), length=6.0, r=0.6, n_valves=2, rfps=rfps, keys=vk)
    fwd = rbc_flow('F', vv['path'], 14, rfps, nf, 0.13, R=0.11, mat=mb, seed=7, spread=0.16, u_span=0.9)
    for o in fwd: hide_from(o, F(11.6, rfps))
    rnd = random.Random(3)
    for i in range(8):                                        # cells trying to fall back onto the shut cusps
        c = rbc(f'Back{i}', R=0.11, mat=mb); x0 = 4.0 + 1.2 + rnd.uniform(0.2, 1.4); y = rnd.uniform(-0.25, 0.25); z = -0.05 + rnd.uniform(-0.2, 0.15)
        t0 = 11.9 + rnd.uniform(0, 0.8); tm = t0 + 1.1; te = tm + 0.9
        hide_until(c, F(t0, rfps)); kf(c, 'location', F(t0, rfps), (x0, y, z)); kf(c, 'location', F(tm, rfps), (4.0 + 0.55, y * 0.6, z)); kf(c, 'location', F(te, rfps), (4.0 + 1.1, y, z + 0.1)); kf_ease(c)
    anchor('AnVWall', (-1.55, 0.0, vs['r_out'] * 0.55)); anchor('AnVLumen', (-3.0, 0.0, 0.0)); anchor('AnVValve', (4.0 + 0.6, -0.2, 0.15))
    motes('Motes', 160, (0, 2, 0), (10, 4, 5), color=PLASMA, r=0.02, strength=3.5, seed=3, drift=0.25, rfps=rfps, nf=nf)
    backglow((0, 0, 0), P.mix(DEOXY_LIT, CYAN, 0.35), r=7, strength=0.4)
    cam, tgt = cam_path([(0.0, (-7.5, -7.0, 1.8), (-4.0, 0.0, 0.0)), (4.0, (-2.8, -6.0, 1.6), (-3.2, 0.0, 0.0)), (8.6, (-1.5, -5.2, 1.4), (-2.6, 0.0, 0.0)), (10.0, (2.6, -5.0, 2.6), (4.2, 0.0, -0.2)), (dur, (4.2, -4.4, 2.4), (4.6, 0.0, -0.2))], rfps, lens=45)
    focus(cam, 1, nf, vs['layers']['media'], vv['pipe'])

def cap_scene(nf, rfps, dur, section=4, cam0=(0.7, -5.9, -0.25), tgt0=(0.0, -2.6, -0.6)):
    reset(); stage(target=(0, -1.0, -0.2), key=(3.0, -7.0, 6.0), key_e=2100, fill_e=120, rim_e=520, spot=60, section=section, env=0.06)
    light('AREA', (-2.5, -6.0, -2.5), 110, THEME[section]['fill'], 'CapFill', size=4.0, target=(0, -2.6, -0.6))
    light('AREA', (2.5, -4.5, 2.5), 140, P.mix(PLASMA, WHITE, 0.4), 'CapKey2', size=2.0, target=(0.5, -2.6, -0.6))
    root = empty('CapRoot', (0, 0, 0)); bed = capillary_bed(root, loc=(0, 0.4, 0.3), width=8.0)
    hero = endothelial_tube(root, 'Endo', loc=(0, -2.6, -0.6), length=5.2, R=0.42, rfps=rfps, nf=nf)
    OXK = [(0.0, 1.0), (0.36, 1.0), (0.42, 0.85), (0.48, 0.65), (0.54, 0.45), (0.6, 0.25), (0.66, 0.0)]            # crimson -> violet AS the oxygen leaves (a ramp, not a switch)
    for i in (1, 3, 5, 7): rbc_flow(f'Cb{i}_', bed['paths'][i], 7, rfps, nf, 0.06, R=0.05, mat=mat_cell(f'capc{i}', animated=True), seed=i, ox_keys=OXK, u_span=0.9)
    mh = mat_cell('heroc', animated=True); _inp(mh.node_tree.nodes.get('Principled BSDF'), 'Emission Strength', 0.7)
    hero_cells = rbc_flow('Hc', hero['path'], 7, rfps, nf, 0.09, R=0.21, mat=mh, seed=9, ox_keys=OXK, u_span=0.95)
    # tissue cells round the hero capillary: matte packed-cell flesh, behind / above / below the tube, never between it and the camera
    mt = mat_tissue('hero_tissue'); tissue = []; rnd = random.Random(12)
    for k in range(8):
        a = math.radians(-105 + 210 * k / 7 + rnd.uniform(-8, 8)); rad = rnd.uniform(1.15, 1.45)
        c = Vector((rnd.uniform(-2.4, 2.4), -2.6 + math.cos(a) * rad, -0.6 + math.sin(a) * rad * 1.15))
        t = meta_mesh(f'HeroT{k}', [(tuple(c), 0.5 * rnd.uniform(0.8, 1.2), (1.35, 0.85, 1.0)), (tuple(c + Vector((0.4, 0.05, 0.25))), 0.32, None)], res=0.07, mat=mt); parent(t, root); tissue.append(t)
    tissue.append(tissue_ground(root, 'HeroGround', (0, 0.2, -0.7), (4.5, 2.4), n=12, seed=33, r=(1.1, 1.7), mat=mt))
    motes('Motes', 200, (0, -1, 0), (9, 4, 5), color=PLASMA, r=0.016, strength=3.5, seed=3, drift=0.2, rfps=rfps, nf=nf)
    motes('Dust', 80, (0, -3, 0), (8, 3, 4), color=DUST, r=0.011, strength=2.2, seed=9, drift=-0.15, rfps=rfps, nf=nf)
    backglow((0, 0, 0), P.mix(OXY_LIT, DEOXY_LIT, 0.5), r=8, strength=0.3, depth=8)
    fg_cells('FG', 5, cam0, tgt0, rfps, nf, seed=7, R=0.08, dist=1.8, spread=1.5, drift=0.6)                  # bokeh foreground: soft cells crossing the frame
    return root, bed, hero, hero_cells, tissue

CAM_CAP_CLOSE = ((0.7, -5.9, -0.25), (0.0, -2.6, -0.6))
def capillary_bed_shot(nf, rfps, dur):
    """246.25-257.27: inside a tissue the arteriole fans into thin capillaries (crimson turning violet) that merge into a
    venule; then a dive to one capillary whose wall is a single layer of flat cells with plum nuclei."""
    root, bed, hero, hc, tissue = cap_scene(nf, rfps, dur, cam0=(0.9, -7.6, -0.1), tgt0=(0.0, -1.5, -0.4))
    anchor('AnArteriole', (-5.4, 0.1, 0.9)); anchor('AnCapil', (0.0, 0.0, 1.6)); anchor('AnVenule', (5.4, 0.1, 0.7)); anchor('AnCellWall', (0.3, -2.9, -0.1))
    cam, tgt = cam_path([(0.0, (0.0, -16.5, 1.2), (0.0, 0.2, 0.2)), (6.2, (0.9, -7.6, -0.1), (0.0, -1.5, -0.4)), (dur, CAM_CAP_CLOSE[0], CAM_CAP_CLOSE[1])], rfps, lens=42)
    focus(cam, 1, nf, bed['caps'][4], hero['cells'][0])

def exchange(nf, rfps, dur):
    """257.27-273.7: through the single-cell wall: oxygen (gold-white) and nutrients (green) leave the plasma for the
    tissue, carbon dioxide (violet) and waste (grey) come in; then the camera pulls back as the capillaries merge into
    the venule and the blood heads back toward the heart."""
    root, bed, hero, hc, tissue = cap_scene(nf, rfps, dur)
    rnd = random.Random(5); T = Vector((0, -2.6, -0.6)); R = 0.42
    def particle(nm, col, t0, inward, r=0.06, strength=7.0):
        a = rnd.uniform(-1.3, 1.3); x = rnd.uniform(-2.0, 2.0); dirv = Vector((0, -math.cos(a), math.sin(a)))     # radial, on the camera side of the wall (never hidden behind it)
        p_in = T + Vector((x, 0, 0)) + dirv * (R * 0.3); p_out = T + Vector((x, 0, 0)) + dirv * (R + 1.0)
        o = sphere(nm, r, tuple(p_in), seg=24, ring=12, mat=mat_glow(col, strength=strength, name=nm + '_m'))
        p0, p1 = (p_out, p_in) if inward else (p_in, p_out)
        show_between(o, F(t0, rfps), F(t0 + 2.4, rfps)); kf(o, 'location', F(t0, rfps), tuple(p0)); kf(o, 'location', F(t0 + 2.2, rfps), tuple(p1)); kf_ease(o)
        try: o.visible_shadow = False
        except Exception: pass
        return o
    for i in range(8): particle(f'O2p{i}', P.mix(O2, WHITE, 0.3), 0.6 + i * 0.55, False, strength=9.0)
    for i in range(6): particle(f'Nutp{i}', NUTRIENT, 1.4 + i * 0.7, False, r=0.05)
    for i in range(8): particle(f'CO2p{i}', CO2, 5.2 + i * 0.5, True)
    for i in range(6): particle(f'Wsp{i}', WASTE, 5.8 + i * 0.65, True, r=0.05, strength=3.0)
    anchor('AnWall1', (0.3, -2.9, -0.1)); anchor('AnTissue', (1.2, -3.4, 0.6)); anchor('AnVenule', (5.4, 0.1, 0.7))
    gl = glow_sleeve('VenGlow', [(4.0, 0.4, 0.3), (5.2, 0.5, 0.25), (6.5, 0.7, 0.1)], 0.5, DEOXY_LIT, strength=1.4, alpha=0.3); parent(gl, root); hide_until(gl, F(11.0, rfps))
    cam, tgt = cam_path([(0.0, CAM_CAP_CLOSE[0], CAM_CAP_CLOSE[1]), (5.0, (-1.3, -6.0, 0.35), (0.0, -2.6, -0.6)), (10.0, (1.2, -5.8, -1.0), (0.0, -2.6, -0.6)), (13.5, (3.0, -12.0, 0.8), (1.5, 0.0, 0.0)), (dur, (5.5, -8.5, 1.0), (5.0, 0.3, 0.2))], rfps, lens=42)
    focus(cam, 1, nf, hero['cells'][0], bed['venule'])

def rbc_hero_shot(nf, rfps, dur):
    """273.7-282.11: 0-3.4 s the biconcave red cell hero turns in the void (seen obliquely first so the deep dimple reads
    as a shaded bowl under a raking key, then facing the camera), membrane undulation, cobblestone + grain; 3.4-4.6 s the
    camera crosses the membrane through the dimple (the membrane fills the frame, a short crimson flash, its alpha keyed
    down as we pass); from 4.6 s the whole haemoglobin molecule is the hero at mid-frame: four tangled globin chains in
    two colours, four haem plates with glowing iron centres, oxygen molecules docking with a flash; out-of-focus
    haemoglobins and cells behind."""
    reset(); stage(target=(0, 0, 0), key=(3.5, -6.0, 5.0), key_e=2400, fill_e=150, rim_e=560, spot=50, section=4)
    light('AREA', (-2.0, -2.5, -1.5), 90, THEME[4]['fill'], 'HbFill', size=2.0, target=(0, 0, 0))
    light('AREA', (-3.2, -3.0, 3.4), 420, P.mix(OXY_LIT, GOLD, 0.25), 'DimpleKey', size=1.5, target=(0, 0, 0))   # a raking warm key from the upper left: the dimple shades as a bowl
    root = empty('CellRoot', (0, 0, 0)); cell = rbc_hero(root, 'Hero', R=1.7)
    # oblique at first (the dimple reads), turning to face the camera by the dive; a slow tumble all shot long
    kf(cell, 'rotation_euler', 1, (0.55, -0.6, -0.3)); kf(cell, 'rotation_euler', F(2.2, rfps), (0.95, -0.2, 0.0)); kf(cell, 'rotation_euler', F(3.4, rfps), (1.5, 0.12, 0.15)); kf(cell, 'rotation_euler', nf, (1.55, 0.35, 0.3)); kf_ease(cell)
    hb = haemoglobin(root, loc=(0, 0, 0), s=0.6, rfps=rfps, nf=nf, spin=0.05)
    for mFe in hb['fe_mats']: _inp(mFe.node_tree.nodes.get('Principled BSDF'), 'Emission Strength', 4.0)
    rnd = random.Random(4)
    for k in range(5):                                                    # out-of-focus haemoglobins behind and beside the hero (depth)
        bg = haemoglobin(root, loc=(rnd.uniform(-2.0, 2.0), rnd.uniform(2.0, 3.6), rnd.uniform(-1.2, 1.2)), s=rnd.uniform(0.32, 0.46), rfps=rfps, nf=nf, spin=rnd.uniform(-0.04, 0.04), name=f'HbBg{k}', lights=False, seed=10 + k)
        for mFe in bg['fe_mats']: _inp(mFe.node_tree.nodes.get('Principled BSDF'), 'Emission Strength', 2.5)
    mo = mat_glow(P.mix(O2, WHITE, 0.25), strength=6.0, name='o2glow')
    for k, d in enumerate(hb['dirs']):
        fe_p = d * 0.66 * 0.6; tgt_p = fe_p + d * 0.06; start = d * 1.5 + Vector((rnd.uniform(-0.25, 0.25), -0.35, rnd.uniform(-0.25, 0.25)))
        o = spheres_mesh(f'O2m{k}', [(0, 0, 0), (0.055, 0.02, 0)], 0.032, mo, subdiv=3); o.location = tuple(start); parent(o, hb['root']); t0 = 5.2 + k * 0.45
        hide_until(o, F(t0, rfps)); kf(o, 'location', F(t0, rfps), tuple(start)); kf(o, 'location', F(t0 + 1.3, rfps), tuple(tgt_p)); kf_ease(o)
        kf(o, 'rotation_euler', F(t0, rfps), (0, 0, 0)); kf(o, 'rotation_euler', F(t0 + 1.3, rfps), (1.5, 2.5, 0.8))
        key_input(hb['fe_mats'][k], 'Emission Strength', [(F(t0 + 1.1, rfps), 4.0), (F(t0 + 1.35, rfps), 11.0), (F(t0 + 2.0, rfps), 5.0)])     # the iron flashes as the O2 docks
    mc = mat_cell('bg_cells', ox=1.0)
    for i in range(6):
        c = rbc(f'Bg{i}', (rnd.uniform(-5, 5), rnd.uniform(5.0, 9.0), rnd.uniform(-3, 3)), R=0.5 * rnd.uniform(0.7, 1.3), mat=mc, rot=(rnd.uniform(0, 3), rnd.uniform(0, 3), 0))
        kf(c, 'location', 1, tuple(c.location)); kf(c, 'location', nf, (c.location.x + rnd.uniform(-1, 1), c.location.y, c.location.z + rnd.uniform(-0.6, 0.6))); kf_lin(c)
    cm = cell.data.materials[0]
    key_input(cm, 'Emission Strength', [(F(3.3, rfps), 0.12), (F(4.0, rfps), 0.8), (F(4.7, rfps), 0.25)])
    key_alpha_range(cm, [(F(3.3, rfps), (0.93, 0.99)), (F(4.0, rfps), (0.5, 0.7)), (F(4.7, rfps), (0.05, 0.14))])       # the membrane opens as we pass through it
    anchor('AnRBC', (-1.4, -0.4, 1.3)); anchor('AnHb', (0.0, -0.4, 0.72)); anchor('AnFe', tuple(hb['dirs'][0] * 0.66 * 0.6 + Vector((0, -0.05, 0))), parent_to=hb['root'])
    motes('Motes', 180, (0, 1, 0), (8, 5, 5), color=PLASMA, r=0.018, strength=3.5, seed=3, drift=0.2, rfps=rfps, nf=nf)
    backglow((0, 0, 0), P.mix(OXY_LIT, GOLD, 0.4), r=6, strength=0.45, depth=8)
    fg_cells('FG', 4, (0.9, -8.6, 1.6), (0, 0, 0), rfps, nf, seed=6, R=0.3, dist=3.0, spread=2.6)
    for o in bpy.data.objects:
        if o.name.startswith('FG'): hide_from(o, F(3.4, rfps))
    cam, tgt = cam_path([(0.0, (1.4, -8.4, 2.4), (0, 0, 0.1)), (3.4, (0.35, -3.9, 0.5), (0, 0, 0.05)), (4.6, (0.3, -1.25, 0.15), (0, 0, 0)), (6.0, (-0.8, -2.0, 0.4), (0, 0, 0)), (dur, (-1.25, -2.25, 0.55), (0, 0, 0))], rfps, lens=42)
    lens_kf(cam, [(1, 45), (F(4.6, rfps), 38), (nf, 40)]); focus(cam, 1, nf, cell, hb['irons'][0])

def mat_flesh(color, name='flesh', rough=0.62, sss=0.4, spec=0.3, ior=1.3, bump=0.25, scale=12.0):
    """Solid fleshy muscle (papillary muscles, trabeculae, organ tissue): matte-ish, soft sheen, subsurface, fibre bump."""
    m = mat_organic(color, rough=rough, sss=sss, coat=0.05, name=name, radius=(0.7, 0.16, 0.12), spec=spec, scale=0.1)
    p = m.node_tree.nodes.get('Principled BSDF'); _inp(p, 'IOR', ior); _inp(p, 'Coat Roughness', 0.4)
    _noise_bump(m, p, scale=scale, strength=bump, detail=4.0, distance=0.02)
    return m

def cavity_lights(root, name='CavL', e_v=9.0, e_a=4.5, color=None):
    """Small warm point lights INSIDE the four hollows of the cutaway heart (endoscope light): the linings, trabeculae and
    papillary muscles get real shading from within instead of one flat fill from the front."""
    col = color or P.mix(ENDO_EMIT, WHITE, 0.35); out = []
    for k, c in CH.items():
        L = light('POINT', tuple(c + Vector((0, -0.12, 0.05))), e_v if k[1] == 'V' else e_a, col, f'{name}{k}')
        try: L.data.shadow_soft_size = 0.06; L.data.use_shadow = CY          # shadowless: four extra EEVEE shadow cubemaps cost ~1.5x per frame
        except Exception: pass
        parent(L, root); out.append(L)
    return out

def strip_planar_caps(o, planes, eps=0.02):
    """A boolean DIFFERENCE leaves a closed solid: the opening it cuts is capped by a flat face ON the cut plane. For a
    thin shell that must stay OPEN (the ventricle cup, the atrium dome) delete every face whose vertices all lie on one of
    the given planes [(point_local, normal_local)]. Local (object) coordinates."""
    me = o.data; bm = bmesh.new(); bm.from_mesh(me); kill = []
    for f in bm.faces:
        for (pt, nrm) in planes:
            pt, nrm = Vector(pt), Vector(nrm).normalized()
            if all(abs((v.co - pt).dot(nrm)) < eps for v in f.verts): kill.append(f); break
    if kill: bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.to_mesh(me); bm.free(); me.update(); return len(kill)

def union_mesh(name, parts, voxel=0.05, mat=None, smooth_iter=3, sub=1, bake_=True):
    """ONE smooth organic mesh from overlapping primitive parts (a voxel remesh unions them: no CSG seams, no metaball
    bulging). parts = [('capsule', p0, p1, r0, r1) | ('sphere', c, r, (sx, sy, sz) | None) | ('box', c, (sx, sy, sz), bevel)].
    Then a Laplacian-free smooth pass and one subdivision. Returns the mesh object (unparented)."""
    bm = bmesh.new()
    for pt in parts:
        if pt[0] == 'capsule':
            p0, p1, r0, r1 = Vector(pt[1]), Vector(pt[2]), pt[3], pt[4]; d = p1 - p0; L = d.length
            M = Matrix.Translation((p0 + p1) / 2) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
            bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=r0, radius2=r1, depth=L, matrix=M)
            bmesh.ops.create_icosphere(bm, subdivisions=2, radius=r0, matrix=Matrix.Translation(p0))
            bmesh.ops.create_icosphere(bm, subdivisions=2, radius=r1, matrix=Matrix.Translation(p1))
        elif pt[0] == 'sphere':
            c, r, sc = Vector(pt[1]), pt[2], pt[3] or (1, 1, 1)
            bmesh.ops.create_icosphere(bm, subdivisions=3, radius=r, matrix=Matrix.Translation(c) @ Matrix.Diagonal((sc[0], sc[1], sc[2], 1.0)))
        elif pt[0] == 'box':
            c, sc, bev = Vector(pt[1]), pt[2], pt[3]
            ret = bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(c) @ Matrix.Diagonal((sc[0], sc[1], sc[2], 1.0)))
            if bev > 0:
                edges = list({e for v in ret['verts'] for e in v.link_edges})
                bmesh.ops.bevel(bm, geom=edges, offset=bev, segments=4, profile=0.5, affect='EDGES')
    o = mesh_obj(name, bm, mat)
    try:
        rm = o.modifiers.new('remesh', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = voxel; rm.use_smooth_shade = True
        try: rm.adaptivity = 0.0
        except Exception: pass
        sm = o.modifiers.new('smooth', 'SMOOTH'); sm.factor = 0.6; sm.iterations = smooth_iter
    except Exception as e: print('union_mesh modifiers', e)
    if bake_: bake(o)
    if sub: subsurf(o, 1, 1)
    smooth(o, auto=False); return o

def lung_veins(m, scale=5.0):
    """Surface vein lines on a lung material: a Voronoi edge network a shade darker/more violet, sunk into the surface,
    plus a fine alveolar noise bump."""
    p = m.node_tree.nodes.get('Principled BSDF'); nt = m.node_tree; n = nt.nodes
    tc = n.new('ShaderNodeTexCoord'); vor = n.new('ShaderNodeTexVoronoi'); vor.feature = 'DISTANCE_TO_EDGE'; vor.inputs['Scale'].default_value = scale
    try: vor.inputs['Randomness'].default_value = 0.85
    except Exception: pass
    ramp = n.new('ShaderNodeValToRGB'); e = ramp.color_ramp.elements; e[0].position = 0.0; e[0].color = (0.58, 0.46, 0.62, 1); e[1].position = 0.03; e[1].color = (1, 1, 1, 1)
    base_link = next((l for l in nt.links if l.to_socket == p.inputs['Base Color']), None)
    mix = n.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 0.8
    if base_link is not None: nt.links.new(base_link.from_socket, mix.inputs[6])
    else: mix.inputs[6].default_value = tuple(p.inputs['Base Color'].default_value)
    nt.links.new(tc.outputs['Object'], vor.inputs['Vector']); nt.links.new(vor.outputs['Distance'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], mix.inputs[7]); nt.links.new(mix.outputs[2], p.inputs['Base Color'])
    em_link = next((l for l in nt.links if l.to_socket == p.inputs['Emission Color']), None)
    if em_link is None:                                     # the rim glow follows the vein network too
        emx = n.new('ShaderNodeMix'); emx.data_type = 'RGBA'; emx.blend_type = 'MULTIPLY'; emx.inputs['Factor'].default_value = 0.7; emx.inputs[6].default_value = tuple(p.inputs['Emission Color'].default_value)
        nt.links.new(ramp.outputs['Color'], emx.inputs[7]); nt.links.new(emx.outputs[2], p.inputs['Emission Color'])
    b = n.new('ShaderNodeBump'); b.inputs['Strength'].default_value = 0.22; b.inputs['Distance'].default_value = 0.02; nt.links.new(ramp.outputs['Color'], b.inputs['Height'])
    _noise_bump(m, p, scale=20.0, strength=0.15, detail=5.0, distance=0.02, prev=b)
    return m

def soft_halo(name, r, color, alpha_max=0.35, emit=2.0):
    """A soft glowing halo: alpha 1 at the centre of the disc fading to 0 at the rim (Facing-driven), additive-looking."""
    m, p = _principled(name + '_m'); nt = m.node_tree; n = nt.nodes
    lw = n.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.5
    pw = n.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 2.2
    mul = n.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = alpha_max
    nt.links.new(lw.outputs['Facing'], pw.inputs[0]); nt.links.new(pw.outputs[0], mul.inputs[0]); nt.links.new(mul.outputs[0], p.inputs['Alpha'])
    _inp(p, 'Base Color', (0, 0, 0, 1)); _inp(p, 'Emission Color', (*color, 1)); _inp(p, 'Emission Strength', emit); _inp(p, 'Roughness', 1.0); _inp(p, 'Specular IOR Level', 0.0)
    _blend(m); o = sphere(name, r, mat=m)
    try: o.visible_shadow = False
    except Exception: pass
    return o, m

def see_through(m, alpha=0.5):
    """A vessel the hero drop travels INSIDE: the wall goes translucent (blended, far wall culled) so the drop reads."""
    p = m.node_tree.nodes.get('Principled BSDF'); _inp(p, 'Alpha', alpha); _blend(m)
    try: m.use_backface_culling = True
    except Exception: pass
    return m

# ================================================================= CHEST: torso, ribcage, lungs
def torso(root, a_center=0.10, a_rim=0.85, emit=2.0, name='Torso'):
    """Translucent amber torso silhouette (metaball chest, shoulders, neck, head, upper arms, abdomen) around the heart:
    fresnel rim glow, faint centre, so the ribs, lungs and heart read through it. Returns the mesh (materials[0] keyable)."""
    els = [((-0.6, 1.4, 0.7), 3.3, (1.55, 1.05, 1.25)), ((-0.6, 1.5, -3.2), 2.7, (1.35, 0.95, 1.2)),
           ((-4.9, 1.9, 3.1), 1.15, (1.2, 1.0, 0.9)), ((3.7, 1.9, 3.1), 1.15, (1.2, 1.0, 0.9)),
           ((-0.6, 2.0, 4.3), 0.95, (1.1, 1.0, 1.5)), ((-0.6, 2.0, 6.4), 1.35, (1.0, 1.1, 1.2)),
           ((-5.8, 1.9, 0.6), 0.9, (1.0, 1.0, 2.4)), ((4.6, 1.9, 0.6), 0.9, (1.0, 1.0, 2.4)),
           ((-0.6, 1.5, 2.3), 2.2, (1.7, 0.7, 0.8))]                                             # upper chest / clavicle shelf
    m = mat_rim(SKIN, SKIN_RIM, a_center=a_center, a_rim=a_rim, emit=emit, name=name + '_m', blend=0.42, rough=0.35)
    o = meta_mesh(name, els, res=0.12, mat=m); subsurf(o, 0, 1); parent(o, root)
    try: o.visible_shadow = False
    except Exception: pass
    return o

def ribcage(root, ghost=False, name='Rib', pairs=9):
    """Nine rib pairs (bevelled arcs from the spine round to the sternum, sloping down toward the front), the sternum,
    costal cartilage tint near the front, and a stack of vertebrae behind. ghost=True -> translucent rim-lit bone."""
    mB = mat_rim(BONE, (1.0, 0.95, 0.8), a_center=0.35, a_rim=0.9, emit=0.7, name=name + '_g', blend=0.5) if ghost else mat_bone(name + '_m')
    mC = mat_rim(CARTILAGE, (0.9, 1.0, 1.0), a_center=0.35, a_rim=0.9, emit=0.5, name=name + '_cg', blend=0.5) if ghost else mat_organic(CARTILAGE, rough=0.35, sss=0.35, coat=0.3, name=name + '_c')
    cx, cy = -0.6, 1.5; out = {'ribs': [], 'cart': []}
    for k in range(pairs):
        u = k / (pairs - 1); zb = 3.4 - 6.0 * u; rx = 3.4 + 1.3 * math.sin(math.pi * u) + 0.3 * u; ry = 2.75 + 0.9 * math.sin(math.pi * u)
        for sgn in (-1, 1):
            pts = []
            for j in range(7):
                th = math.pi * 0.8 * j / 6                                 # from the spine (back, +y) round the side toward the front, stopping short of the sternum
                x = cx + sgn * rx * math.sin(th); y = cy + ry * math.cos(th); z = zb - 1.1 * (j / 6) ** 1.4
                pts.append((x, y, z))
            rr = 0.085 if k < 7 else 0.07
            rib = tube(f'{name}{k}{"L" if sgn > 0 else "R"}', catmull(pts, 22), rr, mB, res=8, bevel_res=6, radii=None); parent(rib, root); out['ribs'].append(rib)
            if k < 7:                                                     # costal cartilage: the last straight stretch to the sternum
                p_end = pts[-1]; c = tube(f'{name}{k}{"L" if sgn > 0 else "R"}c', [p_end, ((p_end[0] + cx + sgn * 0.24) / 2, (p_end[1] + cy - ry) / 2 - 0.05, p_end[2] - 0.2), (cx + sgn * 0.24, cy - ry - 0.02, p_end[2] - 0.38)], rr * 0.9, mC, res=6, bevel_res=5); parent(c, root); out['cart'].append(c)
    st = tube(name + 'Sternum', [(cx, cy - 2.75, 3.0), (cx, cy - 2.95, 1.5), (cx, cy - 2.9, 0.0), (cx, cy - 2.6, -1.6)], 0.2, mB, res=8, bevel_res=6, radii=[0.24, 0.22, 0.2, 0.14]); parent(st, root); out['sternum'] = st
    for k in range(8):                                                   # vertebrae behind
        v = obj_add('cylinder', f'{name}Vert{k}', radius=0.3, depth=0.42, vertices=24, location=(cx, cy + 3.1, 3.3 - 0.8 * k)); setmat(v, mB); smooth(v)
        try: md = v.modifiers.new('bev', 'BEVEL'); md.width = 0.08; md.segments = 4
        except Exception: pass
        parent(v, root); out.setdefault('spine', []).append(v)
    return out

def lung_lobe(name, c, size, mat, seed):
    rnd = random.Random(seed); sx, sy, sz = size
    els = [(tuple(c), 0.72 * min(sx, sy, sz) * 1.15, (sx / min(size), sy / min(size), sz / min(size)))]
    for k in range(5):
        d = Vector((rnd.uniform(-0.55, 0.55) * sx, rnd.uniform(-0.45, 0.45) * sy, rnd.uniform(-0.6, 0.6) * sz))
        els.append((tuple(Vector(c) + d), 0.45 * min(size) * rnd.uniform(0.8, 1.2), (1.2, 0.9, 1.1)))
    o = meta_mesh(name, els, res=0.09, mat=mat); displace(o, scale=0.6, strength=0.06, name=name + '_d'); subsurf(o, 0, 1); return o

def lungs(root, rim=True, name='Lung', a_center=0.55):
    """The two lungs flanking the heart (right = -X, three lobes; left = +X, two lobes with the cardiac notch), the trachea
    and both bronchi. rim=True -> translucent rim-lit salmon (the heart shows through), else solid dusty tissue with pores."""
    m = mat_lung(name + '_m', rim=rim, a_center=a_center); mb = mat_organic(P.mix(CARTILAGE, LUNG, 0.4), rough=0.4, sss=0.3, coat=0.3, name=name + '_br')
    lobes = [lung_lobe(name + 'RUp', (-2.75, 1.4, 1.75), (1.55, 1.9, 1.7), m, 1), lung_lobe(name + 'RMid', (-2.95, 1.35, 0.15), (1.6, 2.0, 1.2), m, 2),
             lung_lobe(name + 'RLow', (-2.85, 1.45, -1.55), (1.7, 2.1, 1.8), m, 3),
             lung_lobe(name + 'LUp', (2.85, 1.5, 1.6), (1.45, 1.85, 1.9), m, 4), lung_lobe(name + 'LLow', (2.95, 1.55, -1.35), (1.55, 2.05, 2.0), m, 5)]
    for o in lobes:
        parent(o, root)
        try: o.visible_shadow = False
        except Exception: pass
    tr = tube(name + 'Trachea', [(-0.6, 2.3, 5.2), (-0.6, 2.3, 3.6), (-0.55, 2.25, 2.5)], 0.22, mb, res=8, bevel_res=6); parent(tr, root)
    bR = tube(name + 'BronchR', [(-0.55, 2.25, 2.5), (-1.3, 2.1, 1.9), (-2.3, 1.7, 1.3), (-2.8, 1.5, 0.6)], 0.16, mb, res=8, bevel_res=5, radii=[0.18, 0.15, 0.12, 0.09]); parent(bR, root)
    bL = tube(name + 'BronchL', [(-0.55, 2.25, 2.5), (0.4, 2.15, 2.0), (1.8, 1.8, 1.4), (2.7, 1.6, 0.6)], 0.16, mb, res=8, bevel_res=5, radii=[0.18, 0.15, 0.12, 0.09]); parent(bL, root)
    return dict(lobes=lobes, trachea=tr, bronchi=[bR, bL])

# ================================================================= FIST, MUSCLE FIBRES
def fist(root, loc=(0, 0, 0), s=1.0, rot=(0, 0, 0), name='Fist'):
    """A closed fist: palm block, four curled fingers (three phalanges each, knuckle ridges at the first and second
    joints), the thumb folded across the fingers, the wrist; unioned by a voxel remesh into ONE smooth skin, subdivided;
    skin material with subsurface and a fine pore bump. Local frame: knuckles up (+Z), fingers curl toward -Y (the
    viewer), thumb on +X."""
    P_ = [('box', (0, 0.15, 0.0), (1.55, 0.85, 1.55), 0.32), ('sphere', (0, 0.25, 0.45), 0.55, (1.35, 0.7, 0.8))]
    for i, (x, k) in enumerate(((-0.58, 0.9), (-0.19, 1.0), (0.19, 0.96), (0.58, 0.82))):
        r = 0.2 * k; mcp = (x, -0.2, 0.72 * k + 0.05); pip = (x, -0.95, 0.5 * k); dip = (x, -1.08, -0.1); tip = (x, -0.72, -0.4)
        P_ += [('capsule', mcp, pip, r * 1.05, r * 0.95), ('capsule', pip, dip, r * 0.95, r * 0.85), ('capsule', dip, tip, r * 0.85, r * 0.75),
               ('sphere', mcp, r * 1.25, (1.0, 1.0, 1.15)), ('sphere', pip, r * 1.12, None)]                       # knuckle ridges: MCP and PIP
    P_ += [('capsule', (0.9, -0.05, 0.3), (0.8, -0.85, 0.2), 0.24, 0.22), ('capsule', (0.8, -0.85, 0.2), (0.3, -1.22, 0.0), 0.22, 0.18), ('sphere', (0.8, -0.85, 0.2), 0.26, None),   # thumb across the fingers
           ('capsule', (0, 0.4, -0.7), (0, 0.6, -1.7), 0.5, 0.42)]                                                   # wrist
    o = union_mesh(name, P_, voxel=0.035, mat=mat_skin(name + '_m'), smooth_iter=4, sub=1)
    displace(o, scale=0.35, strength=0.012, name=name + '_d')
    o.location = loc; o.rotation_euler = rot; o.scale = (s, s, s); parent(o, root)
    _noise_bump(o.data.materials[0], o.data.materials[0].node_tree.nodes.get('Principled BSDF'), scale=30.0, strength=0.12, detail=5.0, distance=0.02)
    return o

def mat_fibre(name='fibre'):
    """Cardiac muscle fibre: warm red, fine striations across the fibre (bands along X), dark intercalated discs every so
    often, subsurface, a wet coat."""
    m = mat_organic(MUSCLE_LIT, rough=0.38, sss=0.4, coat=0.35, name=name, radius=(0.9, 0.25, 0.12), scale=0.1)
    p = m.node_tree.nodes.get('Principled BSDF'); nt = m.node_tree; n = nt.nodes
    tc = n.new('ShaderNodeTexCoord'); w = n.new('ShaderNodeTexWave'); w.bands_direction = 'X'; w.inputs['Scale'].default_value = 26.0; w.inputs['Distortion'].default_value = 0.8; w.inputs['Detail'].default_value = 2.0
    wr = n.new('ShaderNodeValToRGB'); e = wr.color_ramp.elements; e[0].position = 0.35; e[0].color = (0.55, 0.55, 0.55, 1); e[1].position = 0.7; e[1].color = (1, 1, 1, 1)
    disc = n.new('ShaderNodeTexWave'); disc.bands_direction = 'X'; disc.inputs['Scale'].default_value = 2.6; disc.inputs['Distortion'].default_value = 1.6; disc.inputs['Detail'].default_value = 1.0
    dr = n.new('ShaderNodeValToRGB'); de = dr.color_ramp.elements; de[0].position = 0.0; de[0].color = (0.25, 0.1, 0.1, 1); de[1].position = 0.09; de[1].color = (1, 1, 1, 1)
    mul = n.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
    col = n.new('ShaderNodeMix'); col.data_type = 'RGBA'; col.blend_type = 'MULTIPLY'; col.inputs['Factor'].default_value = 0.6; col.inputs[6].default_value = (*MUSCLE_LIT, 1)
    nt.links.new(tc.outputs['Object'], w.inputs['Vector']); nt.links.new(tc.outputs['Object'], disc.inputs['Vector'])
    nt.links.new(w.outputs['Fac'], wr.inputs['Fac']); nt.links.new(disc.outputs['Fac'], dr.inputs['Fac'])
    nt.links.new(wr.outputs['Color'], mul.inputs[6]); nt.links.new(dr.outputs['Color'], mul.inputs[7]); nt.links.new(mul.outputs[2], col.inputs[7]); nt.links.new(col.outputs[2], p.inputs['Base Color'])
    b = n.new('ShaderNodeBump'); b.inputs['Strength'].default_value = 0.3; b.inputs['Distance'].default_value = 0.02; nt.links.new(mul.outputs[2], b.inputs['Height']); nt.links.new(b.outputs['Normal'], p.inputs['Normal'])
    _inp(p, 'Coat Roughness', 0.2)
    return m

def muscle_fibres(root, n=15, length=7.0, spacing=0.34, name='Fib', seed=3):
    """A slab of branching cardiac muscle fibres (parallel along X, stacked in Z, slightly wavy), joined by Y-shaped
    bridges, with elongated plum nuclei along them. Every object is named Fib* and parented to root."""
    rnd = random.Random(seed); mf = mat_fibre(name + '_m'); fibres = []; nuclei = []; scales = []
    for k in range(n):
        z = (k - (n - 1) / 2) * spacing + rnd.uniform(-0.04, 0.04); y = rnd.uniform(-0.25, 0.25) + 0.3 * math.sin(k * 1.7)
        pts = [(-length / 2 + length * j / 8, y + 0.12 * math.sin(j * 1.3 + k), z + 0.05 * math.sin(j * 2.1 + k * 0.7)) for j in range(9)]
        r = 0.13 * rnd.uniform(0.85, 1.15)
        o = tube(f'{name}{k}', catmull(pts, 40), r, mf, res=10, bevel_res=8, radii=[r * rnd.uniform(0.85, 1.15) for _ in range(9)]); parent(o, root); fibres.append(o)
        for j in range(5):
            u = 0.1 + 0.8 * j / 4 + rnd.uniform(-0.04, 0.04); x = -length / 2 + length * u
            nuclei.append(Vector((x, y + 0.12 * math.sin(u * 8 * 1.3 + k) + rnd.uniform(-0.03, 0.03), z + 0.05 * math.sin(u * 8 * 2.1 + k * 0.7) + rnd.choice((-1, 1)) * r * 0.55))); scales.append(rnd.uniform(0.8, 1.2))
        if k > 0:                                                     # bridges to the fibre below (the branching network)
            for j in range(3):
                x0 = -length / 2 + length * ((j + rnd.uniform(0.2, 0.8)) / 3); zb = z - spacing
                p0 = (x0, y, z); p1 = (x0 + 0.35, (y + yprev) / 2, (z + zb) / 2); p2 = (x0 + 0.7, yprev, zb)
                b = tube(f'{name}{k}B{j}', catmull([p0, p1, p2], 10), r * 0.7, mf, res=8, bevel_res=6, radii=[r * 0.85, r * 0.7, r * 0.85]); parent(b, root)
        yprev = y
    nm = spheres_mesh(name + 'Nuclei', nuclei, 0.05, mat_organic(NUCLEUS, rough=0.35, sss=0.3, coat=0.4, name=name + '_nuc'), subdiv=2, rscale=scales)
    nm.scale = (2.2, 1.0, 1.0); parent(nm, root)
    return fibres

# ================================================================= GLOW SLEEVE, VESSEL SECTIONS
def glow_sleeve(name, pts, r, color, strength=1.2, alpha=0.3):
    """A soft emissive tube around a route (pressure glow along a vessel). materials[0] is a Principled with a keyable
    Emission Strength; no shadows, blended."""
    m = mat_glow(color, strength=strength, name=name + '_m', alpha=alpha)
    o = tube(name, catmull([tuple(p) for p in pts], 24), r, m, res=10, bevel_res=8)
    try: o.visible_shadow = False
    except Exception: pass
    return o

def half_pipe(name, length, r_out, r_in, mat, open_dir=(-1.0, 0.0), span=math.pi, segs=48, along=24, ripple=0.0):
    """A pipe wall segment along X (centred at the origin) whose cross-section is an arc of `span` radians on the side
    OPPOSITE open_dir (y, z), with inner and outer surfaces, two end caps (the wall cross-section) and two lip faces.
    ripple > 0 corrugates the inner surface (elastic lamellae)."""
    a0 = math.atan2(open_dir[1], open_dir[0]) + math.pi - span / 2
    bm = bmesh.new(); rings_o, rings_i = [], []
    for i in range(along + 1):
        x = -length / 2 + length * i / along; ro, ri = [], []
        for j in range(segs + 1):
            a = a0 + span * j / segs; cy, sz = math.cos(a), math.sin(a)
            rr = r_in * (1 + ripple * math.sin(a * 16) * math.sin(x * 4.0)) if ripple else r_in
            ro.append(bm.verts.new((x, r_out * cy, r_out * sz))); ri.append(bm.verts.new((x, rr * cy, rr * sz)))
        rings_o.append(ro); rings_i.append(ri)
    def quads(A, flip=False):
        for i in range(len(A) - 1):
            for j in range(len(A[i]) - 1):
                f = (A[i][j], A[i][j + 1], A[i + 1][j + 1], A[i + 1][j]) if not flip else (A[i][j], A[i + 1][j], A[i + 1][j + 1], A[i][j + 1])
                try: bm.faces.new(f)
                except Exception: pass
    quads(rings_o); quads(rings_i, flip=True)
    for idx, flip in ((0, True), (along, False)):                          # end caps
        for j in range(segs):
            f = (rings_o[idx][j], rings_o[idx][j + 1], rings_i[idx][j + 1], rings_i[idx][j])
            try: bm.faces.new(f if flip else tuple(reversed(f)))
            except Exception: pass
    for j_, flip in ((0, False), (segs, True)):                           # lips
        for i in range(along):
            f = (rings_o[i][j_], rings_i[i][j_], rings_i[i + 1][j_], rings_o[i + 1][j_])
            try: bm.faces.new(f if flip else tuple(reversed(f)))
            except Exception: pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = mesh_obj(name, bm, mat); return o

def mat_intima(name='intima'):
    m = mat_organic(INTIMA, rough=0.22, sss=0.2, coat=0.75, name=name); _noise_bump(m, m.node_tree.nodes.get('Principled BSDF'), scale=22.0, strength=0.08, detail=4.0, distance=0.02); return m
def mat_media(name='media', color=ARTERY_WALL):
    m = mat_organic(color, rough=0.45, sss=0.3, coat=0.2, name=name); p = m.node_tree.nodes.get('Principled BSDF'); nt = m.node_tree; n = nt.nodes
    tc = n.new('ShaderNodeTexCoord'); w = n.new('ShaderNodeTexWave'); w.wave_type = 'RINGS'; w.rings_direction = 'X'; w.inputs['Scale'].default_value = 9.0; w.inputs['Distortion'].default_value = 2.5; w.inputs['Detail'].default_value = 2.0
    wr = n.new('ShaderNodeValToRGB'); e = wr.color_ramp.elements; e[0].position = 0.3; e[0].color = (*P.scale(color, 0.7), 1); e[1].position = 0.8; e[1].color = (*P.scale(color, 1.15), 1)
    nt.links.new(tc.outputs['Object'], w.inputs['Vector']); nt.links.new(w.outputs['Fac'], wr.inputs['Fac']); nt.links.new(wr.outputs['Color'], p.inputs['Base Color'])
    b = n.new('ShaderNodeBump'); b.inputs['Strength'].default_value = 0.35; b.inputs['Distance'].default_value = 0.03; nt.links.new(w.outputs['Fac'], b.inputs['Height'])
    _noise_bump(m, p, scale=14.0, strength=0.1, detail=5.0, distance=0.02, prev=b); return m
def mat_adventitia(name='adv', color=ADVENTITIA):
    m = mat_organic(color, rough=0.72, sss=0.2, coat=0.05, name=name); p = m.node_tree.nodes.get('Principled BSDF'); nt = m.node_tree; n = nt.nodes
    tc = n.new('ShaderNodeTexCoord'); vor = n.new('ShaderNodeTexVoronoi'); vor.feature = 'DISTANCE_TO_EDGE'; vor.inputs['Scale'].default_value = 7.0
    ramp = n.new('ShaderNodeValToRGB'); e = ramp.color_ramp.elements; e[0].position = 0.0; e[0].color = (0.6, 0.6, 0.6, 1); e[1].position = 0.08; e[1].color = (1, 1, 1, 1)
    mix = n.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 0.7; mix.inputs[6].default_value = (*color, 1)
    nt.links.new(tc.outputs['Object'], vor.inputs['Vector']); nt.links.new(vor.outputs['Distance'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], mix.inputs[7]); nt.links.new(mix.outputs[2], p.inputs['Base Color'])
    b = n.new('ShaderNodeBump'); b.inputs['Strength'].default_value = 0.3; b.inputs['Distance'].default_value = 0.02; nt.links.new(ramp.outputs['Color'], b.inputs['Height'])
    _noise_bump(m, p, scale=30.0, strength=0.25, detail=6.0, distance=0.02, prev=b); return m

def vessel_section(root, name, kind='artery', loc=(0, 0, 0), length=7.0, r=0.55, cut_front=True, open_dir=(-1.0, 0.0), span=None):
    """A vessel cut open along its length (front half removed): three concentric wall layers built as half-pipes whose end
    caps show the cross-section. artery = thin glossy intima, THICK ringed elastic media, fibrous adventitia; vein = the
    same three layers but thin. Returns dict(layers{intima, media, adventitia}, path, r_in, r_out, thick, root)."""
    if kind == 'artery': ti, tm, ta = 0.06 * r, 0.40 * r, 0.16 * r; cm, ca = ARTERY_WALL, ADVENTITIA
    else: ti, tm, ta = 0.045 * r, 0.09 * r, 0.075 * r; cm, ca = VEIN_WALL, P.mix(ADVENTITIA, VEIN_WALL, 0.35)
    span = (span or math.pi) if cut_front else 2 * math.pi - 1e-3
    L = {}
    L['intima'] = half_pipe(name + 'Intima', length, r + ti, r, mat_intima(name + '_int'), open_dir=open_dir, span=span, ripple=0.0)
    L['media'] = half_pipe(name + 'Media', length, r + ti + tm, r + ti, mat_media(name + '_med', color=cm), open_dir=open_dir, span=span, ripple=0.0)
    L['adventitia'] = half_pipe(name + 'Adv', length, r + ti + tm + ta, r + ti + tm, mat_adventitia(name + '_adv', color=ca), open_dir=open_dir, span=span)
    for o in L.values():
        o.location = loc; parent(o, root); subsurf(o, 0, 1); smooth(o, auto=True)
    pts = [(loc[0] - length / 2 - 0.6 + (length + 1.2) * j / 6, loc[1] + 0.06 * math.sin(j * 1.9), loc[2] + 0.05 * math.cos(j * 1.3)) for j in range(7)]
    path = path_curve(name + 'Path', pts); parent(path, root)
    return dict(layers=L, path=path, r_in=r, r_out=r + ti + tm + ta, thick=(ti, tm, ta), root=root, loc=loc, length=length)

def pulse_wall(art, t0, t1, rfps, period=0.83, amp=0.07):
    """The wall of an artery section swelling with every beat (quick swell, slower recoil) from t0 to t1."""
    t = t0
    while t < t1:
        for o in art['layers'].values():
            for dt, k in ((0.0, 0.0), (0.13, 1.0), (0.5, 0.0)):
                kf(o, 'scale', F(t + dt, rfps), (1.0, 1 + amp * k, 1 + amp * k))
        t += period
    for o in art['layers'].values(): kf_ease(o)

def vein_valves(root, name, loc=(0, 0, 0), length=6.0, r=0.6, n_valves=2, rfps=12, keys=None, open_dir=(-0.55, 0.83)):
    """A vein opened along its upper front, thin wall (two layers), with n pocket valves inside: each valve = two cusps
    hinged on the wall, pointing downstream (+X), swinging inward to meet on the axis when shut (keys = [(t, open01)])."""
    L = {'intima': half_pipe(name + 'Intima', length, r * 1.045, r, mat_intima(name + '_int'), open_dir=open_dir, span=math.pi * 1.05),
         'wall': half_pipe(name + 'Wall', length, r * 1.19, r * 1.045, mat_media(name + '_w', color=VEIN_WALL), open_dir=open_dir, span=math.pi * 1.05)}
    for o in L.values(): o.location = loc; parent(o, root); subsurf(o, 0, 1); smooth(o, auto=True)
    mv = mat_valve(name + '_valve', alpha=0.92); hinges = []
    a_open = math.atan2(open_dir[1], open_dir[0]); xs = [loc[0] - length * 0.28, loc[0] + length * 0.09][:n_valves] if n_valves <= 2 else [loc[0] - length / 2 + length * (k + 0.5) / n_valves for k in range(n_valves)]
    for vi, xv in enumerate(xs):
        for k, da in enumerate((math.pi * 0.62, math.pi * 1.38)):        # two cusps on the kept wall, either side of the floor
            a = a_open + da; hp = Vector((xv, loc[1] + r * math.cos(a), loc[2] + r * math.sin(a)))
            radial = Vector((0, math.cos(a), math.sin(a))); tangent = Vector((0, -math.sin(a), math.cos(a)))
            e, o = petal(f'{name}V{vi}C{k}', tuple(hp), tuple(tangent), tuple(-radial), (1, 0, 0), r * 0.62, r * 1.0, mv, curl=0.5, segs=(12, 10), thick=0.025, taper=0.6)
            parent(e, root); hinges.append(e)
            if keys: key_swing(e, [(F(t, rfps), 6 + 70 * (1 - v)) for t, v in keys])
            else: swing_static(e, 6)
        ring = obj_add('torus', f'{name}V{vi}Ring', major_radius=r * 1.0, minor_radius=r * 0.05, major_segments=48, minor_segments=10, location=(xv, loc[1], loc[2])); ring.rotation_euler = (0, math.pi / 2, 0)
        setmat(ring, mat_organic(P.mix(P.VALVE, VEIN_WALL, 0.5), rough=0.4, sss=0.3, name=name + '_ring')); smooth(ring, auto=False); parent(ring, root)
    path = path_curve(name + 'Path', [(loc[0] - length / 2 - 0.6, loc[1], loc[2] - r * 0.15), (loc[0] - length * 0.2, loc[1] + 0.05, loc[2] - r * 0.1), (loc[0] + length * 0.2, loc[1] - 0.04, loc[2] - r * 0.12), (loc[0] + length / 2 + 0.6, loc[1], loc[2] - r * 0.1)]); parent(path, root)
    return dict(path=path, pipe=L['wall'], layers=L, valves=hinges, xs=xs)

# ================================================================= CAPILLARIES, ENDOTHELIUM
def mat_tissue(name='tissue', base=None, spot=None, alpha=1.0):
    """Body tissue around a capillary: a warm MATTE ground of packed cells (Voronoi cell borders a shade darker + a bump
    groove), soft flesh blotches, modest subsurface, no coat, IOR 1 (no Fresnel: the old translucent blobs mirrored the
    HDRI and read as pale fog), optional alpha."""
    base = base or P.mix(ORGAN, MUSCLE, 0.3); spot = spot or P.mix(ORGAN, MUSCLE_DK, 0.6)
    m, noise, ramp = mat_blotch(base, spot, scale=2.6, lo=0.38, hi=0.66, rough=0.92, sss=0.18, name=name, detail=4.0, bump=0.3, coat=0.0)
    p = m.node_tree.nodes.get('Principled BSDF'); nt = m.node_tree; n = nt.nodes
    _inp(p, 'Specular IOR Level', 0.03); _inp(p, 'IOR', 1.0); _inp(p, 'Subsurface Radius', (0.8, 0.3, 0.25)); _inp(p, 'Subsurface Scale', 0.06)
    tc = n.new('ShaderNodeTexCoord'); vor = n.new('ShaderNodeTexVoronoi'); vor.feature = 'DISTANCE_TO_EDGE'; vor.inputs['Scale'].default_value = 3.2
    try: vor.inputs['Randomness'].default_value = 0.9
    except Exception: pass
    vr = n.new('ShaderNodeValToRGB'); e = vr.color_ramp.elements; e[0].position = 0.0; e[0].color = (0.45, 0.4, 0.42, 1); e[1].position = 0.1; e[1].color = (1, 1, 1, 1)
    mul = n.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 0.85
    nt.links.new(tc.outputs['Object'], vor.inputs['Vector']); nt.links.new(vor.outputs['Distance'], vr.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], mul.inputs[6]); nt.links.new(vr.outputs['Color'], mul.inputs[7]); nt.links.new(mul.outputs[2], p.inputs['Base Color'])
    bmp = n.get(m['bump_node']) if m['bump_node'] else None
    b2 = n.new('ShaderNodeBump'); b2.inputs['Strength'].default_value = 0.4; b2.inputs['Distance'].default_value = 0.05
    nt.links.new(vr.outputs['Color'], b2.inputs['Height'])
    if bmp is not None: nt.links.new(bmp.outputs['Normal'], b2.inputs['Normal'])
    nt.links.new(b2.outputs['Normal'], p.inputs['Normal'])
    if alpha < 1.0: _inp(p, 'Alpha', alpha); _blend(m)
    return m

def tissue_ground(root, name, centre, extent, n=14, seed=21, r=(1.6, 2.6), mat=None):
    """A soft blotchy sheet of tissue cells BEHIND a scene: many big flattened metaballs in ONE mesh, so the ground is
    lumpy and continuous (never a row of separate balls) and stays one object."""
    rnd = random.Random(seed); cx, cy, cz = centre; ex, ez = extent; els = []
    for k in range(n):
        c = (cx + rnd.uniform(-ex, ex), cy + rnd.uniform(-0.4, 0.4), cz + rnd.uniform(-ez, ez))
        els.append((c, rnd.uniform(*r), (1.3, 0.55, 1.0)))
    o = meta_mesh(name, els, res=0.16, mat=mat or mat_tissue(name + '_m')); displace(o, scale=0.9, strength=0.12, name=name + '_d'); parent(o, root)
    try: o.visible_shadow = False
    except Exception: pass
    return o

def capillary_bed(root, loc=(0, 0, 0), width=8.0, n=8, seed=7, name='Cap'):
    """An arteriole (crimson, from the left) fanning through n thin capillaries (colour running crimson -> violet) that
    merge into a venule (indigo, to the right); each capillary has its own full-length guide path for cells. Tissue cells
    sit BEHIND and around the net (matte blotchy flesh), never in front of it."""
    rnd = random.Random(seed); lx, ly, lz = loc; hw = width / 2
    mA = mat_vessel(OXY, name=name + '_art', coat=0.55, emit=0.12, vein_scale=8.0); mV = mat_vessel(DEOXY, name=name + '_ven', coat=0.5, emit=0.12, vein_scale=8.0)
    mG = mat_gradient(OXY, DEOXY, axis='X', lo=-hw * 0.45, hi=hw * 0.45, name=name + '_grad', emit=0.5)
    art = tube(name + 'Arteriole', [(lx - hw - 1.6, ly, lz), (lx - hw - 0.6, ly + 0.05, lz + 0.05), (lx - hw * 0.62, ly, lz)], 0.2, mA, res=10, bevel_res=8, radii=[0.24, 0.2, 0.17]); parent(art, root)
    ven = tube(name + 'Venule', [(lx + hw * 0.62, ly, lz), (lx + hw + 0.6, ly - 0.05, lz - 0.05), (lx + hw + 1.6, ly, lz)], 0.2, mV, res=10, bevel_res=8, radii=[0.17, 0.21, 0.25]); parent(ven, root)
    caps, paths = [], []
    for i in range(n):
        a = 2 * math.pi * i / n + rnd.uniform(-0.2, 0.2); rr = rnd.uniform(1.0, 1.9); dy, dz = math.cos(a) * rr * 0.8, math.sin(a) * rr
        pts = [(lx - hw - 1.6, ly, lz), (lx - hw * 0.62, ly, lz), (lx - hw * 0.4, ly + dy * 0.45, lz + dz * 0.45), (lx - hw * 0.15, ly + dy * 0.9 + rnd.uniform(-0.2, 0.2), lz + dz * 0.9),
               (lx + hw * 0.15, ly + dy * 0.95 + rnd.uniform(-0.2, 0.2), lz + dz * 0.85 + rnd.uniform(-0.15, 0.15)), (lx + hw * 0.4, ly + dy * 0.45, lz + dz * 0.45), (lx + hw * 0.62, ly, lz), (lx + hw + 1.6, ly, lz)]
        sm = catmull(pts[1:7], 36)
        c = tube(f'{name}{i}', sm, 0.045 * rnd.uniform(0.8, 1.2), mG, res=6, bevel_res=5); parent(c, root); caps.append(c)
        if i % 2 == 0:                                            # short 2nd-order branch on every other capillary (the net look)
            q0 = Vector(sm[12]); q1 = Vector(sm[22]); side = Vector((0, rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6)))
            b = tube(f'{name}{i}b', catmull([tuple(q0), tuple((q0 + q1) / 2 + side), tuple(q1)], 12), 0.03, mG, res=6, bevel_res=4); parent(b, root); caps.append(b)
        p = path_curve(f'{name}Path{i}', pts); parent(p, root); paths.append(p)
    # tissue cells: matte blotchy flesh behind the net (y >= ly + 0.9) and a lumpy tissue sheet further back
    mt = mat_tissue(name + '_tissue'); tissue = []
    for k in range(10):
        c = Vector((lx + rnd.uniform(-hw * 0.55, hw * 0.55), ly + rnd.uniform(0.9, 2.6), lz + rnd.uniform(-2.4, 2.4)))
        t = meta_mesh(f'{name}T{k}', [(tuple(c), 0.55 * rnd.uniform(0.8, 1.3), (1.3, 0.8, 1.0)), (tuple(c + Vector((0.45, 0.1, 0.25))), 0.36, None)], res=0.08, mat=mt); parent(t, root); tissue.append(t)
        try: t.visible_shadow = False
        except Exception: pass
    tissue.append(tissue_ground(root, name + 'Ground', (lx, ly + 4.2, lz - 0.2), (hw * 0.95, 3.2), n=16, seed=seed + 5, mat=mt))
    return dict(arteriole=art, venule=ven, caps=caps, paths=paths, tissue=tissue)

def endothelial_tube(root, name, loc=(0, 0, 0), length=5.2, R=0.42, around=5, along=3, seed=4, rfps=12, nf=1):
    """A capillary whose wall is ONE layer of flat endothelial cells: staggered translucent flesh tiles wrapped on the
    cylinder (dithered transparency, no subsurface, IOR 1: a blended + subsurface tile ghosted a pale halo round every
    cell behind it), each bulging gently over a plum nucleus that shows through, separated by dark junction gaps; the
    plasma inside is a faintly lit lumen (a soft emissive inner sleeve + two dim lumen lights) so cells in it read
    crimson / violet through the wall. Returns dict(cells, nuclei, path, R, plasma)."""
    rnd = random.Random(seed); lx, ly, lz = loc
    mc, noise, ramp = mat_blotch(P.mix(CAPILLARY, OXY, 0.18), P.mix(CAPILLARY, INTIMA, 0.5), scale=6.0, lo=0.35, hi=0.7, rough=0.55, sss=0.0, name=name + '_cell', detail=3.0, bump=0.0, coat=0.0)
    pc = mc.node_tree.nodes.get('Principled BSDF'); _inp(pc, 'Specular IOR Level', 0.04); _inp(pc, 'IOR', 1.0); _inp(pc, 'Alpha', 0.58)
    _inp(pc, 'Emission Color', (*ENDO_EMIT, 1)); _inp(pc, 'Emission Strength', 0.03)
    for attr, val in (('surface_render_method', 'DITHERED'), ('blend_method', 'HASHED'), ('use_backface_culling', False)):
        try: setattr(mc, attr, val)
        except Exception: pass
    _noise_bump(mc, pc, scale=18.0, strength=0.15, detail=4.0, distance=0.02)
    mn = mat_organic(NUCLEUS, rough=0.45, sss=0.3, coat=0.2, name=name + '_nuc'); pn = mn.node_tree.nodes.get('Principled BSDF')
    _inp(pn, 'Emission Color', (*P.scale(NUCLEUS, 1.6), 1)); _inp(pn, 'Emission Strength', 0.7)
    cells, nuclei = [], []
    gap = 0.05; seg_len = length / along
    for i in range(along):
        x0 = lx - length / 2 + i * seg_len; off = (i % 2) * math.pi / around
        for j in range(around):
            a0 = off + 2 * math.pi * j / around; a1 = a0 + 2 * math.pi / around; bm = bmesh.new(); grid = []
            nu, nv = 10, 8; ac, xc = (a0 + a1) / 2, x0 + seg_len / 2
            for iv in range(nv + 1):
                x = x0 + gap + (seg_len - 2 * gap) * iv / nv; row = []
                for iu in range(nu + 1):
                    a = a0 + gap / R + (a1 - a0 - 2 * gap / R) * iu / nu
                    d2 = ((x - xc) / (seg_len * 0.3)) ** 2 + ((a - ac) * R / (R * 0.5)) ** 2
                    rr = R * (1 + 0.1 * math.exp(-d2 * 1.6))
                    row.append(bm.verts.new((x, ly + rr * math.cos(a), lz + rr * math.sin(a))))
                grid.append(row)
            for iv in range(nv):
                for iu in range(nu): bm.faces.new((grid[iv][iu], grid[iv][iu + 1], grid[iv + 1][iu + 1], grid[iv + 1][iu]))
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            o = mesh_obj(f'{name}Cell{i}{j}', bm, mc); solidify(o, 0.025); subsurf(o, 1, 2); parent(o, root); cells.append(o)
            try: o.visible_shadow = False
            except Exception: pass
            nc = Vector((xc, ly + R * 1.03 * math.cos(ac), lz + R * 1.03 * math.sin(ac)))
            nk = sphere(f'{name}Nuc{i}{j}', R * 0.16, tuple(nc), seg=24, ring=12, mat=mn, scale=(2.0, 1.0, 0.8)); nk.rotation_euler = (ac, 0, 0); parent(nk, root); nuclei.append(nk)
    # the warm plasma: a faint emissive translucent sleeve just inside the wall + two dim lumen lights
    plasma = tube(name + 'Plasma', [(lx - length / 2 - 0.3, ly, lz), (lx, ly, lz), (lx + length / 2 + 0.3, ly, lz)], R * 0.9, mat_glow(P.mix(PLASMA, OXY_LIT, 0.25), strength=0.4, name=name + '_plasma', alpha=0.1), res=4, bevel_res=8); parent(plasma, root)
    try: plasma.visible_shadow = False
    except Exception: pass
    for k, x in enumerate((lx - length * 0.28, lx + length * 0.28)):
        L = light('POINT', (x, ly, lz), 22, P.mix(PLASMA, OXY_LIT, 0.3), f'{name}LumenL{k}'); L.parent = root
        try: L.data.shadow_soft_size = 0.08
        except Exception: pass
    path = path_curve(name + 'Path', [(lx - length / 2 - 0.8, ly, lz), (lx - length * 0.2, ly + 0.03, lz - 0.02), (lx + length * 0.2, ly - 0.03, lz + 0.02), (lx + length / 2 + 0.8, ly, lz)]); parent(path, root)
    return dict(cells=cells, nuclei=nuclei, path=path, R=R, plasma=plasma)

# ================================================================= RED CELL HERO, HAEMOGLOBIN, STETHOSCOPE
def rbc_hero(root, name='Hero', R=1.7):
    """The hero red cell: deep biconcave disc with a near-opaque crimson membrane (fresnel-brightened rim, faint emission
    that the shot keys up as the camera crosses it), three scales of membrane detail (coarse undulation, a cobblestone of
    Voronoi cells, fine grain), a soft coat and a red subsurface. materials[0] is the keyable Principled; m['alpha_mr']
    names the MapRange whose To Min / To Max are the membrane's centre / rim alpha."""
    me = rbc_mesh(name + 'Mesh', R, deep=True); o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o); parent(o, root)
    m, p = _principled(name + '_m'); nt = m.node_tree; n = nt.nodes
    lw = n.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.4
    mr = n.new('ShaderNodeMapRange'); mr.name = 'AlphaRange'; mr.inputs['To Min'].default_value = 0.93; mr.inputs['To Max'].default_value = 0.99
    nt.links.new(lw.outputs['Facing'], mr.inputs['Value']); nt.links.new(mr.outputs['Result'], p.inputs['Alpha'])
    _inp(p, 'Base Color', (*OXY, 1)); _inp(p, 'Roughness', 0.5); _inp(p, 'Coat Weight', 0.15); _inp(p, 'Coat Roughness', 0.3); _inp(p, 'Specular IOR Level', 0.35)
    _inp(p, 'Subsurface Weight', 0.25); _inp(p, 'Subsurface Radius', (0.9, 0.12, 0.08)); _inp(p, 'Subsurface Scale', 0.06)   # 0.2 made EEVEE's screen-space SSS blur enormous while the membrane fills the frame (30 s/frame)
    _inp(p, 'Emission Color', (*OXY_LIT, 1)); _inp(p, 'Emission Strength', 0.12)
    b1 = _noise_bump(m, p, scale=2.4, strength=0.35, detail=3.0, distance=0.06)                    # the coarse membrane undulation
    tc = n.new('ShaderNodeTexCoord'); vor = n.new('ShaderNodeTexVoronoi'); vor.feature = 'DISTANCE_TO_EDGE'; vor.inputs['Scale'].default_value = 9.0
    try: vor.inputs['Randomness'].default_value = 0.9
    except Exception: pass
    ramp = n.new('ShaderNodeValToRGB'); e = ramp.color_ramp.elements; e[0].position = 0.0; e[0].color = (0, 0, 0, 1); e[1].position = 0.14; e[1].color = (1, 1, 1, 1)
    b2 = n.new('ShaderNodeBump'); b2.inputs['Strength'].default_value = 0.22; b2.inputs['Distance'].default_value = 0.025
    nt.links.new(tc.outputs['Object'], vor.inputs['Vector']); nt.links.new(vor.outputs['Distance'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], b2.inputs['Height']); nt.links.new(b1.outputs['Normal'], b2.inputs['Normal'])
    tint = n.new('ShaderNodeMix'); tint.data_type = 'RGBA'; tint.blend_type = 'MULTIPLY'; tint.inputs['Factor'].default_value = 0.35; tint.inputs[6].default_value = (*OXY, 1)
    nt.links.new(ramp.outputs['Color'], tint.inputs[7]); nt.links.new(tint.outputs[2], p.inputs['Base Color'])   # the cell borders a shade darker
    _noise_bump(m, p, scale=30.0, strength=0.16, detail=5.0, distance=0.012, prev=b2)               # the fine coat grain
    _blend(m); setmat(o, m); subsurf(o, 1, 2); smooth(o, auto=False); m['alpha_mr'] = 'AlphaRange'
    return o

def key_alpha_range(m, keys):
    """keys = [(frame, (centre_alpha, rim_alpha))] on a material built by rbc_hero (its fresnel alpha MapRange)."""
    mr = m.node_tree.nodes.get(m.get('alpha_mr', 'AlphaRange'))
    for f, (a0, a1) in keys:
        mr.inputs['To Min'].default_value = a0; mr.inputs['To Min'].keyframe_insert('default_value', frame=f)
        mr.inputs['To Max'].default_value = a1; mr.inputs['To Max'].keyframe_insert('default_value', frame=f)

def globin_chain(name, centre, s, mat, rnd, turns=7.0, r_spine=0.3, r_helix=0.075, r_tube=0.03):
    """One globin chain: a random-walk spine folded inside a sphere of radius r_spine*s with a helix wound round it, so
    the chain reads as a tangled coil of alpha-helix (one bevelled curve per chain)."""
    c = Vector(centre); spine = [c + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))).normalized() * r_spine * s * 0.7]
    d = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))).normalized()
    for i in range(7):
        d = (d * 0.55 + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))).normalized()
        p = spine[-1] + d * 0.3 * s
        off = p - c
        if off.length > r_spine * s: p = c + off.normalized() * r_spine * s; d = -off.normalized() * 0.5 + d * 0.5
        spine.append(p)
    sm = catmull(spine, 84); pts = []
    for i in range(len(sm)):
        a, b = sm[max(0, i - 1)], sm[min(len(sm) - 1, i + 1)]; t = (b - a).normalized() if (b - a).length > 1e-6 else Vector((0, 0, 1))
        ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0)); u = t.cross(ref).normalized(); v = t.cross(u).normalized()
        ang = 2 * math.pi * turns * i / len(sm)
        pts.append(tuple(sm[i] + (u * math.cos(ang) + v * math.sin(ang)) * r_helix * s))
    o = tube(name, pts[::2], r_tube * s, mat, res=3, bevel_res=5)
    return o

def haemoglobin(root, loc=(0, 0, 0), s=0.34, rfps=12, nf=1, spin=0.05, name='Hb', lights=True, seed=5):
    """Haemoglobin: four tangled globin chains (two alpha crimson, two beta salmon-rose) in a tetrahedral cluster, each
    carrying a flat haem plate (ring + four lobes + a disc) with a glowing iron atom at its centre facing outward (+ a
    small warm light at each iron when lights=True); the whole molecule turns slowly. Returns dict(root, chains, irons,
    haems, fe_mats)."""
    hr = empty(name + 'Root', loc); parent(hr, root)
    dirs = [Vector((1, 1, 1)).normalized(), Vector((-1, -1, 1)).normalized(), Vector((1, -1, -1)).normalized(), Vector((-1, 1, -1)).normalized()]
    mA = mat_organic(HAEMOGLOBIN, rough=0.32, sss=0.3, coat=0.5, name=name + '_a', radius=(0.9, 0.2, 0.1)); mB = mat_organic(P.mix(HAEMOGLOBIN, (0.95, 0.62, 0.48), 0.55), rough=0.36, sss=0.3, coat=0.45, name=name + '_b', radius=(0.9, 0.5, 0.35))
    for mm in (mA, mB): _noise_bump(mm, mm.node_tree.nodes.get('Principled BSDF'), scale=40.0, strength=0.18, detail=3.0, distance=0.01)
    mRing = mat_organic(P.mix(HAEM_IRON, HAEMOGLOBIN, 0.45), rough=0.3, coat=0.5, name=name + '_ring'); mPlate = mat_translucent(P.mix(HAEM_IRON, GOLD, 0.5), alpha=0.55, rough=0.3, emit=0.35, name=name + '_plate', coat=0.4)
    chains, irons, haems, fe_mats = [], [], [], []; rnd = random.Random(seed)
    for k, d in enumerate(dirs):
        c = d * 0.4 * s
        chains.append(globin_chain(f'{name}Sub{k}', tuple(c), s, mA if k < 2 else mB, rnd)); parent(chains[-1], hr)
        hc = d * 0.66 * s; q = d.to_track_quat('Z', 'Y'); rot = q.to_euler()
        ring = obj_add('torus', f'{name}Haem{k}', major_radius=0.12 * s, minor_radius=0.02 * s, major_segments=40, minor_segments=10, location=tuple(hc)); ring.rotation_euler = rot; setmat(ring, mRing); smooth(ring, auto=False); parent(ring, hr); haems.append(ring)
        plate = obj_add('cylinder', f'{name}Plate{k}', radius=0.115 * s, depth=0.012 * s, vertices=48, location=tuple(hc)); plate.rotation_euler = rot; setmat(plate, mPlate); smooth(plate, auto=False); parent(plate, hr)
        lob = []
        for j in range(4):                                                  # the four pyrrole lobes of the porphyrin
            a = math.radians(45 + 90 * j); lob.append(tuple(q @ Vector((math.cos(a) * 0.12 * s, math.sin(a) * 0.12 * s, 0)) + hc))
        lo = spheres_mesh(f'{name}Lobes{k}', lob, 0.035 * s, mRing, subdiv=2); parent(lo, hr)
        mFe = mat_glow(HAEM_IRON, strength=6.0, name=f'{name}_fe{k}'); fe_mats.append(mFe)
        fe = sphere(f'{name}Fe{k}', 0.045 * s, tuple(hc), seg=24, ring=12, mat=mFe); parent(fe, hr); irons.append(fe)
        if lights:
            L = light('POINT', tuple(hc + d * 0.03 * s), 6.0 * (s / 0.5) ** 2, HAEM_IRON, f'{name}FeL{k}'); L.parent = hr
            try: L.data.shadow_soft_size = 0.02; L.data.use_shadow = CY       # accent lights inside the frame-filling membrane: with shadows EEVEE's shadow maps cost ~25 s/frame
            except Exception: pass
    kf(hr, 'rotation_euler', 1, (0.2, 0.0, 0.0)); kf(hr, 'rotation_euler', nf, (0.2, 0.0, spin * (nf - 1) / rfps * 2 * math.pi)); kf_lin(hr)
    return dict(root=hr, chains=chains, subunits=chains, irons=irons, haems=haems, fe_mats=fe_mats, dirs=dirs)

def stethoscope(root, loc=(0, 0, 0), s=0.55, name='Steth'):
    """A stethoscope pressed on the chest: chrome chest piece (rim, diaphragm, bell, stem) lying on the skin at loc (axis
    along -Y toward the camera), black rubber tubing curving up out of frame to a chrome Y and the ear tubes."""
    mc = mat_chrome(name + '_chrome'); mr = mat_rubber(name + '_rub'); md = mat_plastic((0.82, 0.8, 0.76), rough=0.4, name=name + '_diaph', coat=0.3)
    x, y, z = loc; R = 0.95 * s
    piece = obj_add('cylinder', name + 'Piece', radius=R, depth=0.32 * s, vertices=96, location=(x, y - 0.16 * s, z)); piece.rotation_euler = (math.pi / 2, 0, 0); setmat(piece, mc); smooth(piece)
    try: md_ = piece.modifiers.new('bev', 'BEVEL'); md_.width = 0.06 * s; md_.segments = 6
    except Exception: pass
    rim = obj_add('torus', name + 'Rim', major_radius=R * 0.88, minor_radius=0.05 * s, major_segments=96, minor_segments=16, location=(x, y + 0.01 * s, z)); rim.rotation_euler = (math.pi / 2, 0, 0); setmat(rim, mc); smooth(rim, auto=False)
    dia = obj_add('cylinder', name + 'Diaphragm', radius=R * 0.84, depth=0.03 * s, vertices=96, location=(x, y + 0.005 * s, z)); dia.rotation_euler = (math.pi / 2, 0, 0); setmat(dia, md); smooth(dia)
    bell = obj_add('cone', name + 'Bell', radius1=R * 0.7, radius2=R * 0.32, depth=0.35 * s, vertices=96, location=(x, y - 0.48 * s, z)); bell.rotation_euler = (math.pi / 2, 0, 0); setmat(bell, mc); smooth(bell)
    stem = tube(name + 'Stem', [(x, y - 0.6 * s, z), (x, y - 0.75 * s, z + 0.25 * s), (x - 0.1 * s, y - 0.7 * s, z + 0.6 * s)], 0.09 * s, mc, res=8, bevel_res=6)
    tubing = tube(name + 'Tube', [(x - 0.1 * s, y - 0.7 * s, z + 0.6 * s), (x - 0.3 * s, y - 0.9 * s, z + 1.6 * s), (x - 0.9 * s, y - 1.5 * s, z + 3.2 * s), (x - 2.0 * s, y - 2.4 * s, z + 5.4 * s), (x - 3.0 * s, y - 3.4 * s, z + 8.0 * s)], 0.13 * s, mr, res=12, bevel_res=8)
    yj = sphere(name + 'Y', 0.2 * s, (x - 2.0 * s, y - 2.2 * s, z + 5.4 * s), seg=32, ring=16, mat=mc)
    ear1 = tube(name + 'Ear0', [(x - 2.0 * s, y - 2.2 * s, z + 5.4 * s), (x - 3.2 * s, y - 2.0 * s, z + 7.0 * s), (x - 4.4 * s, y - 1.8 * s, z + 9.0 * s)], 0.07 * s, mc, res=8, bevel_res=5)
    ear2 = tube(name + 'Ear1', [(x - 2.0 * s, y - 2.2 * s, z + 5.4 * s), (x - 1.2 * s, y - 2.6 * s, z + 7.2 * s), (x - 0.6 * s, y - 3.0 * s, z + 9.2 * s)], 0.07 * s, mc, res=8, bevel_res=5)
    for o in (piece, rim, dia, bell, stem, tubing, yj, ear1, ear2): parent(o, root)
    return piece

# ================================================================= HERO VALVES (s17 / s18): seen from INSIDE the ventricle / from the artery side
def chord(name, p0, target, r, mat):
    """A chorda tendinea that follows its leaflet: a cylinder from p0 stretched to `target` (STRETCH_TO), so it stays taut
    from the papillary tip to the leaflet's free edge whatever the swing."""
    o = obj_add('cylinder', name, radius=r, depth=1.0, vertices=12)
    for v in o.data.vertices: v.co = Vector((v.co.x, v.co.z + 0.5, -v.co.y))            # length along +Y, base at the origin
    setmat(o, mat); smooth(o); o.location = p0
    c = o.constraints.new('STRETCH_TO'); c.target = target; c.rest_length = 1.0; c.volume = 'NO_VOLUME'
    return o

def valve_hero_rig(kind, nf, rfps, dur, keys_open, section=2):
    """A hero AV valve (mitral 2 leaflets / tricuspid 3) seen from INSIDE the ventricle, low and to one side, looking up
    at the annulus at a 3/4 angle. The ventricle is a deep elongated cup (apex far below the camera, front cut open so
    the stage lights reach in, roof cut at the ring plane so the annulus sits IN the muscle roof and shows its cut lip).
    In the cup: the ring, two flaps hanging from its left and right sides (scalloped free edges that meet along one line
    when shut), chordae (stretch-constrained: they follow the swing) from the free edges down to two meaty papillary
    muscles rooted on the trabeculated back wall, matte fleshy endocardium darkening with depth, and a faint translucent
    atrium dome sitting on the ring (visible from below through the open valve). Returns (root, hinges, ring_c, ring_r, focus)."""
    reset(); stage(target=(0, 0.9, 0.4), key=(3.2, -3.8, 4.2), key_e=2600, fill_e=190, rim_e=520, spot=56, section=section)
    light('POINT', (0.0, 0.9, 2.5), 200, P.mix(ENDO_EMIT, GOLD, 0.35), 'AtriumLight')                       # inside the dome: back-lights the flaps' edges through the open valve
    light('AREA', (-1.4, -1.4, -2.4), 160, THEME[section]['fill'], 'FloorFill', size=2.5, target=(0.3, 1.2, -0.8))
    light('POINT', (0.9, 1.1, -1.7), 70, P.mix(ENDO_EMIT, (1, 1, 1), 0.4), 'BowlFill')
    light('POINT', (-0.6, 1.6, -3.2), 40, P.mix(ENDO_EMIT, (1, 1, 1), 0.3), 'ApexFill')
    light('SPOT', (-2.2, -0.9, 2.4), 800, P.mix(CYAN, (1, 1, 1), 0.5), 'LeafRim', spot=50, blend=0.6, target=(0.2, 0.9, 0.5))   # cool rim across the leaflet edges
    for L in bpy.data.objects:
        if L.type == 'LIGHT' and L.name in ('AtriumLight', 'BowlFill', 'ApexFill'):
            try: L.data.shadow_soft_size = 0.08
            except Exception: pass
    root = empty('ValveRoot', (0, 0, 0)); mv = mat_valve('hero_valve', alpha=0.94); mch = mat_chordae('hero_ch')
    pv = mv.node_tree.nodes.get('Principled BSDF'); ntv = mv.node_tree; nv = ntv.nodes
    _noise_bump(mv, pv, scale=14.0, strength=0.06, detail=4.0, distance=0.015)
    lw = nv.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.45                              # the thin flaps glow at their rims
    em = nv.new('ShaderNodeMath'); em.operation = 'MULTIPLY'; em.inputs[1].default_value = 0.9
    ntv.links.new(lw.outputs['Fresnel'], em.inputs[0]); ntv.links.new(em.outputs[0], pv.inputs['Emission Strength']); _inp(pv, 'Emission Color', (*P.mix(P.VALVE, ENDO_EMIT, 0.5), 1))
    _inp(pv, 'Roughness', 0.42); _inp(pv, 'Coat Weight', 0.25)
    endo = ENDO_L if kind == 'mit' else ENDO_R; flesh = P.mix(endo, MUSCLE, 0.3)
    ring_c = Vector((0, 0.9, 1.15)); ring_r = 1.25
    BC = Vector((0, 0.9, -1.95)); BR = 2.3; ZS = 1.7                  # the ventricle cup: an elongated ellipsoid, apex at z = -5.9, roof at the ring plane
    mC = mat_cut('hero_cut')
    def cutters(tag):
        f = cutter_box('VCutF' + tag, (0, BC.y - 3.0 - 0.6, BC.z), (11, 6, 13), mat=mC)                  # removes y < 0.3 (the open front)
        t = cutter_box('VCutT' + tag, (0, BC.y, ring_c.z + 0.14 + 3.0), (11, 11, 6), mat=mC)              # removes z > 1.29 (the roof above the ring)
        return f, t
    wall = sphere('VWall', BR, tuple(BC), seg=96, ring=64, mat=mat_endo(flesh, name='hero_endo', depth=(-1.4, 2.6), dark=0.32, ridges=0.7, ridge_scale=3.0, matte=True, lip=1.05, bump=0.12)); wall.scale = (1.0, 1.0, ZS)
    cf, ct = cutters('w'); boolean(wall, cf, name='cut', transfer=False); boolean(wall, ct, name='top', transfer=False); bake(wall)
    for c in (cf, ct): bpy.data.objects.remove(c)
    nk = strip_planar_caps(wall, [((0, 0.3 - BC.y, 0), (0, 1, 0)), ((0, 0, (ring_c.z + 0.14 - BC.z) / ZS), (0, 0, 1))]); print('VWall caps stripped', nk)   # the boolean capped the opening with a flat wall
    parent(wall, root)
    try: wall.data.flip_normals()
    except Exception: pass
    mus = sphere('VMuscle', BR + 0.22, tuple(BC), seg=96, ring=64, mat=mat_muscle('hero_mus')); mus.scale = (1.0, 1.0, ZS); mus.data.materials.append(mC)
    inner = sphere('VInner', BR, tuple(BC), seg=64, ring=32); inner.scale = (1.0, 1.0, ZS); inner.hide_render = True
    cf2, ct2 = cutters('m'); boolean(mus, cf2, name='cut', transfer=True); boolean(mus, ct2, name='top', transfer=True); boolean(mus, inner, name='hollow', transfer=False); bake(mus)
    for c in (cf2, ct2, inner): bpy.data.objects.remove(c)
    parent(mus, root)
    rnd = random.Random(3); mt = mat_flesh(P.mix(flesh, MUSCLE, 0.35), name='hero_trab', rough=0.7, spec=0.2, bump=0.2)
    for k in range(22):                                                # trabeculae carneae on the back wall (analytic ellipsoid positions), some forking
        a = math.radians(rnd.uniform(14, 166)); tilt = rnd.uniform(-0.25, 0.25); pts = []; ph0 = rnd.uniform(-70, -30); span = rnd.uniform(60, 95)
        for j in range(5):
            ph = math.radians(ph0 + span * j / 4 + rnd.uniform(-3, 3)); aa = a + tilt * (j / 4 - 0.5) + rnd.uniform(-0.05, 0.05)
            pts.append((BC.x + (BR - 0.07) * math.cos(ph) * math.cos(aa), BC.y + (BR - 0.07) * math.cos(ph) * math.sin(aa), BC.z + (BR - 0.07) * ZS * math.sin(ph)))
        rr = rnd.uniform(0.06, 0.1)
        t_ = tube(f'HeroTrab{k}', catmull(pts, 18), rr, mt, res=8, bevel_res=6, radii=[rr * 0.4, rr, rr * 1.1, rr * 0.9, rr * 0.4]); parent(t_, root)
        if k % 3 == 0:
            q0 = Vector(pts[2]); ab = a + rnd.choice((-1, 1)) * 0.3; pts2 = [tuple(q0)]
            for j, ph in enumerate((math.radians(ph0 + span * 0.62), math.radians(ph0 + span * 0.85))):
                pts2.append((BC.x + (BR - 0.07) * math.cos(ph) * math.cos(ab), BC.y + (BR - 0.07) * math.cos(ph) * math.sin(ab), BC.z + (BR - 0.07) * ZS * math.sin(ph)))
            f_ = tube(f'HeroTrab{k}f', catmull(pts2, 10), rr * 0.7, mt, res=6, bevel_res=5, radii=[rr * 0.8, rr * 0.6, rr * 0.3]); parent(f_, root)
    ring = obj_add('torus', 'HeroRing', major_radius=ring_r, minor_radius=0.1, major_segments=96, minor_segments=24, location=tuple(ring_c))
    setmat(ring, mat_flesh(P.mix(P.VALVE, MUSCLE, 0.4), name='hero_ringm', rough=0.5, spec=0.3, bump=0.2, scale=10.0)); smooth(ring, auto=False); parent(ring, root)
    # the atrium: a faint translucent hemisphere sitting on the ring plane; no backface culling so its ceiling shows from below
    ma = mat_rim(endo, ENDO_EMIT, a_center=0.07, a_rim=0.34, emit=0.5, name='hero_atr', blend=0.4, emit_min=0.05)
    try: ma.use_backface_culling = False
    except Exception: pass
    atr = sphere('AtriumDome', 1.55, tuple(ring_c + Vector((0, 0.05, 0.02))), seg=64, ring=32, mat=ma)
    cba = cutter_box('ACut', (0, ring_c.y, ring_c.z - 3.0 + 0.04), (8, 8, 6)); boolean(atr, cba, name='cut', transfer=False); bake(atr); bpy.data.objects.remove(cba)
    strip_planar_caps(atr, [((0, 0, 0.02), (0, 0, 1))]); parent(atr, root)
    try: atr.visible_shadow = False
    except Exception: pass
    n = 2 if kind == 'mit' else 3; hinges = []; edges = []
    angs = [math.radians(360 * k / n + (0 if n == 2 else 90)) for k in range(n)]                          # two flaps hinged LEFT and RIGHT: their free edges meet along a front-to-back line
    L = ring_r * 1.0; curl = 0.3
    for k, a in enumerate(angs):
        hp = ring_c + Vector((math.cos(a) * ring_r, math.sin(a) * ring_r, 0)); tangent = Vector((-math.sin(a), math.cos(a), 0)); inward = (ring_c - hp).normalized()
        e, o = petal(f'HeroLeaf{k}', tuple(hp), tangent, inward, (0, 0, -1), ring_r * 0.86, L, mv, curl=curl, segs=(20, 14), thick=0.05, taper=0.45, scallop=0.14, lobes=3)
        parent(e, root); hinges.append(e); key_swing(e, [(F(t, rfps), 8 + 70 * (1 - v)) for t, v in keys_open])   # 8 deg = hanging open, 78 deg = shut (tips meet at the axis)
        for m_ in range(3):                                                     # free-edge attachment points ride the hinge
            ee = empty(f'HeroEdge{k}{m_}'); ee.parent = o; ee.matrix_parent_inverse = Matrix.Identity(4)
            u = (m_ - 1) * 0.5; sc = 1.0 - 0.14 * (0.5 + 0.5 * math.cos(math.pi * 3 * u))
            ee.location = (u * ring_r * 0.86 * (1 - 0.45), curl * L * sc, -L * (1 - 0.15 * u * u) * sc); edges.append((k, ee))
    mp = mat_flesh(P.mix(MUSCLE, endo, 0.3), name='hero_pap', rough=0.6, spec=0.3, bump=0.3, scale=9.0)
    for j, sx in enumerate((-1, 1)):                                    # two papillary muscles rooted on the lower back wall, tips reaching up toward the flaps
        d = Vector((sx * 1.3, 1.0, 0)).normalized(); zb = -2.9; cr = BR * math.sqrt(max(0.05, 1 - ((zb - BC.z) / (BR * ZS)) ** 2))
        base = Vector((BC.x, BC.y, zb)) + d * (cr - 0.1); tip = Vector((sx * 0.75, 1.5, -0.7))
        pm = pap_muscle(f'HeroPap{j}', base, tip, 0.42, mp); parent(pm, root)
        for k, ee in edges:                                             # chordae from this papillary tip to BOTH flaps' free edges
            ch = chord(f'HeroCh{j}{k}{ee.name[-1]}', tuple(tip + Vector((sx * 0.06, 0, -0.06))), ee, 0.016, mch); parent(ch, root)
    foc = empty('LeafFocus', tuple(ring_c + Vector((0, 0.0, -0.5))))
    return root, hinges, ring_c, ring_r, foc

def av_valve_shut(nf, rfps, dur):
    """133.23-142.81: the mitral valve as a one-way door, seen from inside the ventricle (low 3/4 angle looking up at the
    annulus, 34-38 mm): cells drop through the two open flaps; the ventricle contracts, the flaps swing up and SLAM shut
    along one line (4.0 s, the word), and the cells that try to go back bounce off the closed valve (chordae taut,
    papillary muscles pulling); the camera cranes slowly from the left to the right of the cup all shot."""
    keys = [(0.0, 1.0), (3.6, 1.0), (4.0, 0.0), (dur, 0.0)]
    root, hinges, rc, rr, foc = valve_hero_rig('mit', nf, rfps, dur, keys)
    p_down = path_curve('PDown', [tuple(rc + Vector((0, 0.1, 2.2))), tuple(rc + Vector((0, 0.05, 1.1))), tuple(rc + Vector((0, 0, 0.0))), tuple(rc + Vector((0.1, 0.3, -1.3))), tuple(rc + Vector((0.25, 0.7, -2.6))), tuple(rc + Vector((0.3, 0.9, -3.9)))]); parent(p_down, root)
    mr = mat_cell('hero_cells', ox=1.0)
    rbc_flow('Down', p_down, 16, rfps, nf, 0.2, R=0.15, mat=mr, seed=3, spread=0.3, u_span=0.8)
    for o in bpy.data.objects:
        if o.name.startswith('Down'): hide_from(o, F(4.2, rfps))
    rnd = random.Random(8)
    for i in range(12):                                                    # back-flow attempt: rise toward the shut flaps and bounce
        c = rbc(f'Back{i}', R=0.15, mat=mr); x, y = rnd.uniform(-0.7, 0.7), rnd.uniform(0.5, 1.4); z0 = rc.z - rnd.uniform(2.4, 3.3)
        t0 = 4.3 + rnd.uniform(0, 1.4); tm = t0 + 1.2; te = tm + 1.0
        hide_until(c, F(t0, rfps)); kf(c, 'location', F(t0, rfps), (x, y, z0)); kf(c, 'location', F(tm, rfps), (x * 0.6, y, rc.z - 0.34)); kf(c, 'location', F(te, rfps), (x * 1.4, y + 0.3, rc.z - 2.1)); kf_ease(c)
        kf(c, 'rotation_euler', 1, (rnd.uniform(0, 3), 0, 0)); kf(c, 'rotation_euler', nf, (rnd.uniform(3, 6), 1.0, 0.5))
    anchor('AnValve', tuple(rc + Vector((0.1, 0.2, -0.45)))); anchor('AnAtrium', tuple(rc + Vector((0, 0.3, 1.0)))); anchor('AnVentricle', tuple(rc + Vector((0.5, 0.6, -1.9))))
    for o in (bpy.data.objects['VWall'], bpy.data.objects['VMuscle']):
        kf(o, 'scale', F(3.5, rfps), tuple(o.scale)); kf(o, 'scale', F(4.3, rfps), (o.scale[0] * 0.92, o.scale[1] * 0.92, o.scale[2] * 0.97)); kf(o, 'scale', F(7.0, rfps), (o.scale[0] * 0.92, o.scale[1] * 0.92, o.scale[2] * 0.97)); kf(o, 'scale', F(8.6, rfps), tuple(o.scale)); kf_ease(o)
    motes('Motes', 150, (0, 1.2, -1.2), (4, 3, 5), color=PLASMA, r=0.014, strength=3.5, seed=3, drift=0.2, rfps=rfps, nf=nf, subdiv=2)
    backglow((0, 0.9, 1.6), P.mix(OXY_LIT, GOLD, 0.4), r=4.5, strength=0.45, depth=6)
    fg_cells('FG', 3, (-1.9, -0.7, -3.0), (0.0, 0.9, 1.15), rfps, nf, seed=5, R=0.06, dist=1.1, spread=0.9, mat=mr)
    # low inside the cup, left of the axis, looking up at the annulus at a 3/4 angle; a slow crane from left to right as it shuts
    cam, tgt = cam_path([(0.0, (-1.9, -0.7, -3.1), (0.05, 0.95, 0.55)), (4.0, (-1.1, -0.45, -2.95), (0.0, 0.95, 0.6)), (dur, (0.95, -0.7, -3.15), (-0.05, 0.9, 0.5))], rfps, lens=33)
    lens_kf(cam, [(1, 33), (F(4.0, rfps), 36), (nf, 34)]); focus(cam, 1, nf, foc, foc)

def semilunar_shut(nf, rfps, dur):
    """142.81-152.81: the aortic valve from the ARTERY side: the camera looks down into the opened aorta at the three
    pocket cusps; while the ventricle pushes, cells stream up through the open cusps toward the camera; when it relaxes
    the pockets fill and snap shut into their three-point star, and the cells above settle on the closed pockets."""
    reset(); stage(target=(0, 0.6, 0.6), key=(3.5, -3.5, 5.5), key_e=2600, fill_e=190, rim_e=560, spot=50, section=2)
    light('POINT', (0.0, 0.6, -1.2), 220, P.mix(ENDO_EMIT, OXY_LIT, 0.4), 'VentLight')
    root = empty('SLRoot', (0, 0, 0)); mv = mat_valve('sl_valve', alpha=0.92)
    _noise_bump(mv, mv.node_tree.nodes.get('Principled BSDF'), scale=20.0, strength=0.2, detail=4.0, distance=0.02)
    art = vessel_section(root, 'Aor', kind='artery', loc=(0, 0.6, 1.6), length=6.0, r=1.0, cut_front=True, open_dir=(-1.0, 0.0), span=math.pi * 1.4)
    for o in art['layers'].values(): o.rotation_euler = (0, -math.pi / 2, 0); o.location = (0, 0.6, 1.6)
    keys = [(0.0, 1.0), (3.5, 1.0), (4.1, 0.0), (dur, 0.0)]
    hinges = semilunar_cusps(root, 'SL', (0, 0.6, 0.55), 0.95, (0, 0, 1), mv, valves_open=keys, rfps=rfps, back_only=False)
    for e in hinges:
        for ch in e.children: ch.modifiers['solid'].thickness = 0.05
    # sinuses of Valsalva: three bulges of the wall above the cusps, and the ridge ring the cusps hang from
    ring = obj_add('torus', 'SLRing', major_radius=0.98, minor_radius=0.06, major_segments=96, minor_segments=16, location=(0, 0.6, 0.55)); setmat(ring, mat_organic(P.mix(P.VALVE, ARTERY_WALL, 0.5), rough=0.4, sss=0.3, coat=0.3, name='sl_ring')); smooth(ring, auto=False); parent(ring, root)
    p_up = path_curve('PUp', [(0, 0.6, -2.4), (0, 0.6, -0.6), (0, 0.6, 0.5), (0.1, 0.7, 2.0), (0.2, 0.8, 4.2)]); parent(p_up, root)
    mr = mat_cell('sl_cells', ox=1.0); rbc_flow('Up', p_up, 16, rfps, nf, 0.24, R=0.16, mat=mr, seed=4, spread=0.4, u_span=0.85)
    for o in bpy.data.objects:
        if o.name.startswith('Up'): hide_from(o, F(4.4, rfps))
    rnd = random.Random(9)
    for i in range(10):
        c = rbc(f'Fall{i}', R=0.16, mat=mr); x, y = rnd.uniform(-0.6, 0.6), 0.6 + rnd.uniform(-0.5, 0.5); z0 = 3.2 + rnd.uniform(0, 1.2)
        t0 = 4.4 + rnd.uniform(0, 1.4); tm = t0 + 1.3; te = tm + 1.2
        hide_until(c, F(t0, rfps)); kf(c, 'location', F(t0, rfps), (x, y, z0)); kf(c, 'location', F(tm, rfps), (x * 0.7, y, 1.05)); kf(c, 'location', F(te, rfps), (x * 1.3, y, 1.6)); kf_ease(c)
    dome = sphere('VentDome', 1.9, (0, 0.6, -2.9), seg=64, ring=32, mat=mat_muscle('sl_mus')); dome.scale = (1.2, 1.0, 0.9); parent(dome, root)
    kf(dome, 'scale', 1, (1.2, 1.0, 0.9)); kf(dome, 'scale', F(3.4, rfps), (1.05, 0.88, 0.82)); kf(dome, 'scale', F(5.5, rfps), (1.2, 1.0, 0.9)); kf_ease(dome)
    anchor('AnCusps', (0, -0.3, 0.75)); anchor('AnArtery', (0.6, -0.5, 3.0)); anchor('AnVent2', (0, -0.9, -1.4))
    motes('Motes', 150, (0, 1, 0.5), (6, 4, 5), color=PLASMA, r=0.02, strength=3.5, seed=3, drift=0.2, rfps=rfps, nf=nf)
    backglow((0, 0.6, 0.6), P.mix(OXY_LIT, GOLD, 0.4), r=4.0, strength=0.4, depth=7)
    fg_cells('FG', 4, (-2.2, -3.4, 4.0), (0, 0.6, 0.6), rfps, nf, seed=6, R=0.07, dist=2.0, mat=mr)
    cam, tgt = cam_path([(0.0, (-2.4, -3.8, 3.6), (0, 0.6, 0.5)), (4.0, (-1.4, -3.2, 4.2), (0, 0.6, 0.6)), (dur, (2.0, -3.4, 4.0), (0, 0.6, 0.65))], rfps, lens=40)
    lens_kf(cam, [(1, 38), (nf, 42)]); focus(cam, 1, nf, hinges[0], hinges[0])

# ================================================================= 5. DOUBLE CIRCULATION: one shared rig, one drop, one absolute-time journey
BRAIN_C = (-0.6, 1.9, 6.3); MUSCLE_C = (4.6, 1.9, 0.9); KIDNEY_C = (1.0, 2.4, -3.4)
JOURNEY = [  # (absolute seconds, heart-local point): the drop's whole route, keyed by the narration
    (289.57, (-1.1, 0.62, -3.6)), (293.67, (-1.1, 0.62, -3.3)), (297.0, (-1.1, 0.6, -1.9)), (299.8, (-1.08, 0.5, -0.7)), (301.4, (-1.0, 0.4, -0.05)),
    (302.9, (-0.85, 0.2, 0.55)), (303.9, (-0.82, 0.16, 0.45)), (305.2, (-0.7, 0.14, -0.08)), (306.6, (-0.66, 0.12, -0.7)),
    (307.6, (-0.55, 0.11, -0.45)), (308.6, (-0.32, 0.1, 0.25)), (309.4, (-0.32, 0.1, 0.55)), (310.3, (-0.32, 0.22, 1.25)), (311.1, (-0.05, 0.62, 1.98)),
    (312.2, (-1.35, 0.85, 1.8)), (313.0, (-2.3, 0.9, 1.55)), (314.4, (-2.85, 1.15, 1.25)), (316.2, (-3.1, 1.35, 0.85)), (317.6, (-2.7, 1.1, 0.75)), (318.5, (-2.1, 1.0, 0.85)),
    (319.6, (-1.5, 0.98, 0.9)), (321.4, (-0.55, 0.78, 0.85)), (323.0, (0.45, 0.4, 0.7)), (324.0, (0.8, 0.18, 0.62)), (331.7, (0.82, 0.18, 0.6)),
    (332.6, (0.8, 0.17, 0.35)), (333.7, (0.72, 0.14, -0.08)), (335.4, (0.7, 0.1, -0.74)), (336.6, (0.5, 0.06, -0.45)), (337.6, (0.15, 0.0, 0.3)), (338.6, (0.15, 0.13, 0.56)),
    (339.9, (0.1, 0.25, 1.35)), (341.3, (0.2, 0.62, 2.35)), (342.9, (0.55, 0.9, 2.45)),
    (344.2, (0.2, 0.72, 3.4)), (345.4, (0.0, 1.1, 4.7)), (346.8, (-0.5, 1.7, 6.0)), (348.4, (-0.9, 2.1, 6.6)), (349.8, (-1.2, 1.7, 5.6)),
    (351.4, (-1.1, 1.2, 4.4)), (352.8, (-0.72, 0.5, 3.7)), (354.2, (-0.88, 0.24, 1.9)), (355.5, (-0.86, 0.18, 0.75)), (356.3, (-0.82, 0.16, 0.55)), (362.6, (-0.8, 0.16, 0.55))]
OX_KEYS = [(0.0, 0.0), (314.4, 0.0), (317.2, 1.0), (346.6, 1.0), (349.2, 0.0)]     # (absolute t, ox): indigo until the lungs, crimson until the brain

def journey_at(t):
    W = JOURNEY; P_ = [Vector(w[1]) for w in W]; T = [w[0] for w in W]; P2 = [P_[0]] + P_ + [P_[-1]]
    if t <= T[0]: return P_[0]
    if t >= T[-1]: return P_[-1]
    for i in range(len(T) - 1):
        if T[i] <= t <= T[i + 1]:
            u = (t - T[i]) / max(1e-6, T[i + 1] - T[i]); p0, p1, p2, p3 = P2[i], P2[i + 1], P2[i + 2], P2[i + 3]; u2, u3 = u * u, u * u * u
            return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u2 + (-p0 + 3 * p1 - 3 * p2 + p3) * u3)
    return P_[-1]

def ox_at_time(t):
    v = OX_KEYS[0][1]
    for (t0, v0), (t1, v1) in zip(OX_KEYS[:-1], OX_KEYS[1:]):
        if t0 <= t <= t1: return v0 + (v1 - v0) * (t - t0) / max(1e-6, t1 - t0)
        if t > t1: v = v1
    return v

def brain(root, c=BRAIN_C, name='Brain'):
    """Two hemispheres separated by a deep midline (a negative metaball slab), gyri from two scales of noise displacement
    and a sulci texture (darker grooves), cerebellum behind, brainstem."""
    m = mat_rim(BRAIN, (1.0, 0.85, 0.7), a_center=0.55, a_rim=0.95, emit=0.5, name=name + '_m', blend=0.45, rough=0.5); els = []
    p = m.node_tree.nodes.get('Principled BSDF'); nt = m.node_tree; n = nt.nodes
    tc = n.new('ShaderNodeTexCoord'); ns = n.new('ShaderNodeTexNoise'); ns.inputs['Scale'].default_value = 5.5; ns.inputs['Detail'].default_value = 4.0; ns.inputs['Roughness'].default_value = 0.6
    try: ns.inputs['Distortion'].default_value = 1.2
    except Exception: pass
    rp = n.new('ShaderNodeValToRGB'); e = rp.color_ramp.elements; e[0].position = 0.42; e[0].color = (0.45, 0.32, 0.32, 1); e[1].position = 0.55; e[1].color = (1, 1, 1, 1)
    mx = n.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 0.85; mx.inputs[6].default_value = (*BRAIN, 1)
    nt.links.new(tc.outputs['Object'], ns.inputs['Vector']); nt.links.new(ns.outputs['Fac'], rp.inputs['Fac']); nt.links.new(rp.outputs['Color'], mx.inputs[7]); nt.links.new(mx.outputs[2], p.inputs['Base Color'])
    b = n.new('ShaderNodeBump'); b.inputs['Strength'].default_value = 0.5; b.inputs['Distance'].default_value = 0.05; nt.links.new(rp.outputs['Color'], b.inputs['Height']); nt.links.new(b.outputs['Normal'], p.inputs['Normal'])
    for sgn in (-1, 1):
        cx = c[0] + sgn * 0.5
        els += [((cx, c[1], c[2]), 0.62, (1.0, 1.35, 0.95)), ((cx + sgn * 0.1, c[1] - 0.55, c[2] - 0.05), 0.45, (1.0, 1.1, 0.9)), ((cx, c[1] + 0.6, c[2] - 0.1), 0.42, None), ((cx + sgn * 0.05, c[1] + 0.1, c[2] + 0.35), 0.4, (1.0, 1.3, 0.8))]
    els += [((c[0], c[1] - 0.1, c[2] + 0.25), 0.34, (0.12, 1.9, 1.5), True),                                    # the longitudinal fissure (negative slab)
            ((c[0], c[1] + 0.55, c[2] - 0.75), 0.42, (1.5, 1.0, 0.8)), ((c[0], c[1] + 0.2, c[2] - 1.0), 0.2, (1.0, 1.0, 1.8))]
    o = meta_mesh(name, els, res=0.06, mat=m); displace(o, scale=0.24, strength=0.2, name=name + '_g', depth=2); displace(o, scale=0.09, strength=0.06, name=name + '_g2', depth=1); subsurf(o, 0, 1); parent(o, root)
    try: o.visible_shadow = False
    except Exception: pass
    return o

def muscle_bundle(root, c=MUSCLE_C, name='MuscleB'):
    """A fusiform skeletal muscle (biceps-like): bundled fascicles as parallel spindles under a rim-lit sheath, with
    striation bands across the fibres and fascicle grooves along them, tendons at both ends."""
    m = mat_rim(P.mix(ORGAN, OXY, 0.35), (1.0, 0.6, 0.45), a_center=0.55, a_rim=0.95, emit=0.5, name=name + '_m', blend=0.45, rough=0.45); els = []
    p = m.node_tree.nodes.get('Principled BSDF'); nt = m.node_tree; n = nt.nodes
    tc = n.new('ShaderNodeTexCoord'); w = n.new('ShaderNodeTexWave'); w.bands_direction = 'Z'; w.inputs['Scale'].default_value = 14.0; w.inputs['Distortion'].default_value = 0.6; w.inputs['Detail'].default_value = 2.0
    wr = n.new('ShaderNodeValToRGB'); e = wr.color_ramp.elements; e[0].position = 0.3; e[0].color = (0.55, 0.45, 0.45, 1); e[1].position = 0.7; e[1].color = (1, 1, 1, 1)
    w2 = n.new('ShaderNodeTexWave'); w2.bands_direction = 'X'; w2.inputs['Scale'].default_value = 4.0; w2.inputs['Distortion'].default_value = 1.5
    wr2 = n.new('ShaderNodeValToRGB'); e2 = wr2.color_ramp.elements; e2[0].position = 0.2; e2[0].color = (0.6, 0.5, 0.5, 1); e2[1].position = 0.5; e2[1].color = (1, 1, 1, 1)
    mul = n.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
    mx = n.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 0.8; mx.inputs[6].default_value = (*P.mix(ORGAN, OXY, 0.35), 1)
    nt.links.new(tc.outputs['Object'], w.inputs['Vector']); nt.links.new(tc.outputs['Object'], w2.inputs['Vector']); nt.links.new(w.outputs['Fac'], wr.inputs['Fac']); nt.links.new(w2.outputs['Fac'], wr2.inputs['Fac'])
    nt.links.new(wr.outputs['Color'], mul.inputs[6]); nt.links.new(wr2.outputs['Color'], mul.inputs[7]); nt.links.new(mul.outputs[2], mx.inputs[7]); nt.links.new(mx.outputs[2], p.inputs['Base Color'])
    b = n.new('ShaderNodeBump'); b.inputs['Strength'].default_value = 0.45; b.inputs['Distance'].default_value = 0.03; nt.links.new(mul.outputs[2], b.inputs['Height']); nt.links.new(b.outputs['Normal'], p.inputs['Normal'])
    for k in range(7):
        a = 2 * math.pi * k / 7; r = 0.3 if k else 0.0
        els.append(((c[0] + r * math.cos(a), c[1] + r * math.sin(a), c[2]), 0.34, (0.8, 0.8, 2.6)))
    o = meta_mesh(name, els, res=0.05, mat=m); displace(o, scale=0.5, strength=0.04, name=name + '_d'); parent(o, root)
    try: o.visible_shadow = False
    except Exception: pass
    mT = mat_organic(P.mix(CHORDAE, BONE, 0.5), rough=0.5, sss=0.3, coat=0.2, name=name + '_tendon')
    for sz in (-1, 1):                                                        # tendons
        t = tube(f'{name}Tendon{sz}', [(c[0], c[1], c[2] + sz * 0.85), (c[0] + 0.05 * sz, c[1], c[2] + sz * 1.25), (c[0] + 0.1 * sz, c[1] - 0.05, c[2] + sz * 1.6)], 0.16, mT, res=8, bevel_res=6, radii=[0.24, 0.16, 0.1]); parent(t, root)
    return o

def kidney(root, c=KIDNEY_C, name='Kidney'):
    """A bean-shaped kidney (metaballs, a negative element for the hilum), a fine granular surface, the renal artery and
    vein entering the hilum and the ureter leaving it."""
    m = mat_rim(KIDNEY, (1.0, 0.45, 0.35), a_center=0.55, a_rim=0.95, emit=0.5, name=name + '_m', blend=0.45, rough=0.45)
    _noise_bump(m, m.node_tree.nodes.get('Principled BSDF'), scale=22.0, strength=0.2, detail=5.0, distance=0.02)
    els = [((c[0], c[1], c[2] + 0.38), 0.5, (0.85, 0.65, 1.0)), ((c[0], c[1], c[2] - 0.38), 0.5, (0.85, 0.65, 1.0)), ((c[0] + 0.18, c[1], c[2]), 0.44, (0.9, 0.65, 1.25)), ((c[0] - 0.62, c[1], c[2]), 0.36, (0.8, 1.0, 1.0), True)]
    o = meta_mesh(name, els, res=0.045, mat=m); displace(o, scale=0.4, strength=0.02, name=name + '_d'); subsurf(o, 0, 1); parent(o, root)
    try: o.visible_shadow = False
    except Exception: pass
    mU = mat_organic(P.mix(BONE, ENDO, 0.4), rough=0.5, sss=0.3, coat=0.2, name=name + '_ureter')
    parent(tube(f'{name}Pelvis', [(c[0] - 0.3, c[1], c[2]), (c[0] - 0.45, c[1] + 0.05, c[2] - 0.15)], 0.09, mU, res=6, bevel_res=5, radii=[0.12, 0.07]), root)
    parent(tube(f'{name}Ureter', [(c[0] - 0.45, c[1] + 0.05, c[2] - 0.15), (c[0] - 0.4, c[1] + 0.1, c[2] - 0.8), (c[0] - 0.25, c[1] + 0.15, c[2] - 1.6), (c[0] - 0.05, c[1] + 0.2, c[2] - 2.4)], 0.035, mU, res=8, bevel_res=5), root)
    return o

def circ_rig(nf, rfps, dur, t_shot0, section=5, drop=True, torso_alpha=0.03, streams=True):
    """The section-5 rig: ghost heart (interior visible), rim-lit lungs with lobes and surface vein lines, a brain with gyri
    and a midline, a bean kidney with hilum vessels and ureter, a striated muscle with tendons, the vessels to and from
    every organ (translucent: the drop reads inside them), background cell streams on both loops, and the hero DROP
    riding JOURNEY: a small bright sphere with a soft halo and its own light. No torso: it cluttered every frame."""
    reset(); stage(target=(0, 0.6, 0.8), key=(4.0, -8.0, 8.0), key_e=3600, fill_e=220, rim_e=650, spot=62, section=section)
    h = heart(ghost=True, beat=(0.1, 0.83, 0.02), rfps=rfps, nf=nf, coronaries=False, fat=False); beat_all(h, 0.0, dur, rfps); root = h['root']
    lungs_ = lungs(root, rim=True, a_center=0.2); h['lungs'] = lungs_
    lung_veins(lungs_['lobes'][0].data.materials[0], scale=9.0)                                              # one shared lung material -> veins on every lobe
    h['brain'] = brain(root); h['muscle'] = muscle_bundle(root); h['kidney'] = kidney(root)
    mR = mat_vessel(OXY, name='circ_art', coat=0.55, emit=0.25, vein_scale=6.0); mB = mat_vessel(DEOXY, name='circ_vein', coat=0.5, emit=0.25, vein_scale=6.0)
    OV = {}
    OV['carotid'] = tube('Carotid', [(0.16, 0.7, 3.5), (0.1, 0.9, 4.4), (-0.3, 1.4, 5.4), (-0.5, 1.75, 6.0)], 0.09, mR, res=10, radii=[0.1, 0.09, 0.08, 0.06])
    OV['jugular'] = tube('Jugular', [(-1.0, 2.0, 6.2), (-1.25, 1.75, 5.4), (-1.1, 1.2, 4.4), (-0.72, 0.5, 3.75)], 0.1, mB, res=10, radii=[0.06, 0.085, 0.1, 0.12])
    OV['brachial'] = tube('Brachial', [(0.95, 0.88, 3.6), (2.2, 1.2, 3.3), (3.6, 1.6, 2.4), (4.5, 1.8, 1.7)], 0.085, mR, res=10, radii=[0.09, 0.085, 0.075, 0.06])
    OV['armvein'] = tube('ArmVein', [(4.7, 2.1, 1.6), (3.9, 1.9, 2.7), (2.4, 1.3, 3.5), (-0.6, 0.5, 3.6)], 0.09, mB, res=10, radii=[0.06, 0.08, 0.095, 0.11])
    OV['renal'] = tube('RenalA', [(0.95, 1.08, -2.4), (1.0, 1.6, -3.0), (0.75, 2.2, -3.35)], 0.07, mR, res=8, radii=[0.08, 0.07, 0.055])
    OV['renalv'] = tube('RenalV', [(0.6, 2.4, -3.55), (0.0, 1.6, -3.3), (-1.05, 0.65, -2.6)], 0.08, mB, res=8, radii=[0.055, 0.075, 0.09])
    OV['iliac'] = tube('Iliac', [(0.9, 1.05, -2.6), (1.1, 1.1, -4.2), (1.3, 1.1, -6.0)], 0.12, mR, res=8, radii=[0.15, 0.12, 0.1])
    OV['iliacv'] = tube('IliacV', [(-1.5, 0.75, -6.0), (-1.3, 0.7, -4.2), (-1.1, 0.62, -3.0)], 0.13, mB, res=8, radii=[0.1, 0.12, 0.14])
    for o in OV.values(): parent(o, root)
    h['organ_vessels'] = OV
    for m in (mR, mB) + tuple({o.data.materials[0] for o in h['vessels'].values() if o.data.materials}): see_through(m, 0.5)    # every vessel on the journey: the drop reads inside
    if streams:
        pulm = path_curve('LoopPulm', [(-0.66, 0.12, -0.6), (-0.32, 0.1, 0.5), (-0.3, 0.25, 1.3), (-0.05, 0.62, 1.98), (-1.35, 0.85, 1.8), (-2.6, 1.0, 1.3), (-3.0, 1.3, 0.7), (-2.3, 1.05, 0.7), (-1.0, 0.95, 0.85), (0.3, 0.5, 0.75), (0.8, 0.18, 0.6), (0.72, 0.14, -0.08), (0.7, 0.1, -0.74), (0.1, 0.1, -0.9)], cyclic=True); parent(pulm, root)
        sysp = path_curve('LoopSys', [(0.7, 0.1, -0.74), (0.15, 0.0, 0.3), (0.15, 0.13, 0.6), (0.1, 0.25, 1.35), (0.2, 0.62, 2.35), (0.95, 1.1, 2.3), (2.5, 1.3, 3.2), (4.0, 1.7, 2.2), (4.7, 2.0, 1.2), (3.9, 1.9, 2.7), (2.2, 1.3, 3.5), (-0.6, 0.5, 3.6), (-0.88, 0.24, 1.7), (-0.82, 0.16, 0.6), (-0.7, 0.14, -0.08), (-0.4, 0.1, -0.7)], cyclic=True); parent(sysp, root)
        rbc_flow('BgP', pulm, 12, rfps, nf, 0.05, R=0.055, mat=mat_cell('bgp_m', animated=True), seed=4, spread=0.05, ox_keys=[(0.0, 0.0), (0.45, 1.0)], u_span=0.95)
        rbc_flow('BgS', sysp, 14, rfps, nf, 0.045, R=0.055, mat=mat_cell('bgs_m', animated=True), seed=5, spread=0.05, ox_keys=[(0.0, 1.0), (0.5, 0.0)], u_span=0.95)
    motes('Motes', 200, (0, 1, 0.5), (11, 6, 8), color=PLASMA, r=0.02, strength=3.0, seed=3, drift=0.2, rfps=rfps, nf=nf)
    motes('Dust', 90, (0, -3, 0), (12, 4, 8), color=DUST, r=0.012, strength=2.2, seed=9, drift=-0.15, rfps=rfps, nf=nf)
    backglow((0, 0.6, 0.6), P.mix(OXY_LIT, DEOXY_LIT, 0.45), r=5.5, strength=0.35, depth=10)
    if drop:
        md = mat_cell('drop_m', animated=True); _inp(md.node_tree.nodes.get('Principled BSDF'), 'Emission Strength', 5.0)
        d = sphere('Drop', 0.085, mat=md); parent(d, root)                                                   # the drop: a small bright sphere ...
        halo, mh = soft_halo('DropGlow', 0.21, WHITE, alpha_max=0.4, emit=2.4); parent(halo, d)                # ... with a soft halo that reads through any vessel wall
        hp = mh.node_tree.nodes.get('Principled BSDF'); hmix = mh.node_tree.nodes.new('ShaderNodeMix'); hmix.data_type = 'RGBA'; hmix.inputs[6].default_value = (*P.mix(DEOXY_LIT, WHITE, 0.45), 1); hmix.inputs[7].default_value = (*P.mix(OXY_LIT, WHITE, 0.45), 1)
        hat = mh.node_tree.nodes.new('ShaderNodeAttribute'); hat.attribute_type = 'OBJECT'; hat.attribute_name = 'ox'; mh.node_tree.links.new(hat.outputs['Fac'], hmix.inputs['Factor']); mh.node_tree.links.new(hmix.outputs[2], hp.inputs['Emission Color'])
        L = light('POINT', (0, 0, 0), 140, P.mix(OXY_LIT, GOLD, 0.5), 'DropLight'); L.parent = d
        try: L.data.shadow_soft_size = 0.08
        except Exception: pass
        at = time_route(d, JOURNEY, rfps, t_shot0, nf)
        for f in range(1, nf + 1, 2):
            t = t_shot0 + (f - 1) / rfps; ox = ox_at_time(t)
            d['ox'] = ox; d.keyframe_insert('["ox"]', frame=f); halo['ox'] = ox; halo.keyframe_insert('["ox"]', frame=f)
            L.data.color = P.mix(DEOXY_LIT, OXY_LIT, ox); L.data.keyframe_insert('color', frame=f)
        anchor('AnDrop', (0, -0.2, 0), parent_to=d); h['drop'] = d; h['at'] = at
    return h

def cam_track(at_fn, rfps, nf, t_shot0, offset, lens=40, tgt_off=(0, 0, 0), pull=None, start=None, smooth_n=10):
    """Camera following a moving point from a world offset (smoothed), optionally blending FROM a fixed framing at the
    start (start=(t_end, cam, tgt)) and TO a fixed framing at the end (pull=(t_begin, cam, tgt))."""
    pts = [at_fn(t_shot0 + (f - 1) / rfps) for f in range(1, nf + 1)]; sm = []
    for i in range(len(pts)):
        a, b = max(0, i - smooth_n), min(len(pts), i + smooth_n + 1); sm.append(sum(pts[a:b], Vector()) / (b - a))
    cam, tgt = camera(tuple(sm[0] + Vector(offset)), tuple(sm[0] + Vector(tgt_off)), lens=lens)
    for f in range(1, nf + 1, 2):
        t = (f - 1) / rfps; c = sm[f - 1] + Vector(offset); g = sm[f - 1] + Vector(tgt_off)
        if start is not None and t < start[0]:
            u = smooth01(t / max(1e-6, start[0])); c = vlerp(start[1], c, u); g = vlerp(start[2], g, u)
        if pull is not None and t > pull[0]:
            u = smooth01((t - pull[0]) / max(1e-6, (nf - 1) / rfps - pull[0])); c = vlerp(c, pull[1], u); g = vlerp(g, pull[2], u)
        kf(cam, 'location', f, tuple(c)); kf(tgt, 'location', f, tuple(g))
    kf_lin(cam); kf_lin(tgt); return cam, tgt

def circ_intro(nf, rfps, dur):
    """284.71-293.67: 'the most important idea: double circulation' over the whole rig (heart, lungs, brain, muscle,
    kidney, the vessel loops); at 289.57 'one drop's journey': the drop lights up at the bottom of the vena cava and the
    camera racks down to it."""
    h = circ_rig(nf, rfps, dur, 284.71)
    d = h['drop']; hide_until(d, F(289.57 - 284.71 - 0.3, rfps)); L = bpy.data.objects.get('DropLight')
    if L: hide_until(L, F(289.57 - 284.71 - 0.3, rfps))
    cam, tgt = cam_path([(0.0, (2.5, -19.0, 2.5), (0.0, 0.8, 1.0)), (4.6, (0.5, -15.0, 1.6), (0.0, 0.8, 0.6)), (dur, (-0.6, -7.5, -2.2), (-1.0, 0.6, -2.8))], rfps, lens=40)
    lens_kf(cam, [(1, 38), (F(4.6, rfps), 40), (nf, 45)]); fg_cells('FG', 5, (1, -16, 1), (0, 0.8, 0.6), rfps, nf, seed=5, R=0.09, dist=5.0)
    focus(cam, 1, nf, h['body'], d)

def circ_cavae_ra_rv(nf, rfps, dur):
    """293.67-307.35: the drop rides up the inferior vena cava (the superior one joins from above) into the right atrium,
    then drops through the tricuspid valve into the right ventricle; the camera tracks it from the front-left."""
    h = circ_rig(nf, rfps, dur, 293.67)
    anchor('AnSVC', (-0.85, 0.05, 2.3), parent_to=h['root']); anchor('AnIVC', (-1.15, 0.35, -1.6), parent_to=h['root']); anchor('AnRA', (-0.82, -0.1, 0.62), parent_to=h['root']); anchor('AnRV', (-0.66, -0.1, -0.7), parent_to=h['root'])
    cam, tgt = cam_track(h['at'], rfps, nf, 293.67, (-1.3, -3.9, 0.5), lens=40, tgt_off=(0.15, 0.0, 0.1), start=(2.0, (-0.6, -7.5, -2.2), (-1.0, 0.6, -2.8)))
    lens_kf(cam, [(1, 40), (nf, 45)]); fg_cells('FG', 4, (-2, -6, 0), (-1, 0.5, 0), rfps, nf, seed=6, R=0.07, dist=2.6)
    focus(cam, 1, nf, h['drop'], h['drop'])

def circ_lungs(nf, rfps, dur):
    """307.35-318.89: the right ventricle pumps the drop up the pulmonary artery into the right lung; inside, around an
    alveolus, the drop gives up carbon dioxide (violet motes leave) and takes oxygen (gold motes dock) and turns crimson."""
    h = circ_rig(nf, rfps, dur, 307.35); root = h['root']
    anchor('AnPulmA', (-0.9, 0.5, 1.95), parent_to=root); anchor('AnLungR', (-3.0, 0.3, 1.5), parent_to=root)
    # the alveolus the drop passes: a translucent sac with a capillary wrapped round it, inside the right lung
    alv = sphere('Alveolus', 0.5, (-3.05, 1.35, 0.95), seg=48, ring=24, mat=mat_rim(LUNG, LUNG_RIM, a_center=0.2, a_rim=0.8, emit=1.2, name='alv_m', blend=0.4)); parent(alv, root)
    capm = mat_gradient(DEOXY, OXY, axis='X', lo=-3.4, hi=-2.7, name='alv_cap', emit=0.6)
    wrap = tube('AlvCap', [(-2.85 + 0.55 * math.cos(a), 1.35 + 0.55 * math.sin(a), 1.0 + 0.55 * math.sin(a * 0.5) - 0.2) for a in [i * 0.55 for i in range(12)]], 0.04, capm, res=8, bevel_res=5); parent(wrap, root)
    rnd = random.Random(6); T0 = 313.03 - 307.35
    for i in range(3):
        o = sphere(f'CO2p{i}', 0.045, (0, 0, 0), seg=20, ring=10, mat=mat_glow(CO2, strength=6.0, name=f'co2m{i}')); parent(o, root); t0 = T0 + 0.3 + i * 0.5
        p0 = Vector(journey_at(307.35 + t0)); p1 = p0 + Vector((rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.2), rnd.uniform(0.3, 0.7)))
        show_between(o, F(t0, rfps), F(t0 + 2.0, rfps)); kf(o, 'location', F(t0, rfps), tuple(p0)); kf(o, 'location', F(t0 + 1.8, rfps), tuple(p1)); kf_ease(o)
        o2 = sphere(f'O2p{i}', 0.045, (0, 0, 0), seg=20, ring=10, mat=mat_glow(O2, strength=6.0, name=f'o2m{i}')); parent(o2, root); t1 = T0 + 1.6 + i * 0.5
        q1 = Vector(journey_at(307.35 + t1 + 1.6)); q0 = q1 + Vector((rnd.uniform(-0.7, 0.7), rnd.uniform(-0.7, -0.2), rnd.uniform(0.3, 0.8)))
        show_between(o2, F(t1, rfps), F(t1 + 1.8, rfps)); kf(o2, 'location', F(t1, rfps), tuple(q0)); kf(o2, 'location', F(t1 + 1.6, rfps), tuple(q1)); kf_ease(o2)
    cam, tgt = cam_track(h['at'], rfps, nf, 307.35, (-0.8, -3.6, 0.8), lens=40, tgt_off=(0.1, 0.0, 0.05), pull=(9.5, (-3.2, -2.6, 1.5), (-3.0, 1.2, 0.95)))
    lens_kf(cam, [(1, 42), (F(6.0, rfps), 46), (nf, 48)]); fg_cells('FG', 4, (-2, -6, 1), (-2, 0.8, 1), rfps, nf, seed=7, R=0.07, dist=2.6)
    focus(cam, 1, nf, h['drop'], h['drop'])

def circ_pulm_veins(nf, rfps, dur):
    """318.89-331.73: the crimson drop returns through a pulmonary vein into the left atrium; then 'heart -> lungs -> heart':
    the pulmonary loop lights up as the camera pulls back to the heart between both lungs."""
    h = circ_rig(nf, rfps, dur, 318.89); root = h['root']
    anchor('AnPV', (-0.9, 0.7, 1.05), parent_to=root); anchor('AnLA', (0.8, -0.1, 0.62), parent_to=root); anchor('AnLungR', (-3.0, 0.3, 1.5), parent_to=root); anchor('AnLungL', (3.0, 0.3, 1.4), parent_to=root); anchor('AnHeartC', (0.05, -1.0, -0.3), parent_to=root)
    loop = glow_sleeve('LoopPulmGlow', [(-0.66, 0.12, -0.6), (-0.32, 0.1, 0.5), (-0.3, 0.25, 1.3), (-0.05, 0.62, 1.98), (-1.35, 0.85, 1.8), (-2.6, 1.0, 1.3), (-3.0, 1.3, 0.7), (-2.3, 1.05, 0.7), (-1.0, 0.95, 0.85), (0.3, 0.5, 0.75), (0.8, 0.18, 0.6)], 0.2, P.mix(DEOXY_LIT, OXY_LIT, 0.5), strength=0.0, alpha=0.4); parent(loop, root)
    key_input(loop.data.materials[0], 'Emission Strength', [(F(324.65 - 318.89, rfps), 0.0), (F(326.0 - 318.89, rfps), 2.2), (F(dur, rfps), 1.6)]); hide_until(loop, F(324.65 - 318.89, rfps))
    cam, tgt = cam_track(h['at'], rfps, nf, 318.89, (-0.4, -3.8, 0.9), lens=40, tgt_off=(0.1, 0.0, 0.0), pull=(5.4, (0.6, -12.5, 1.6), (0.0, 0.7, 0.9)))
    lens_kf(cam, [(1, 44), (F(5.4, rfps), 44), (nf, 40)]); fg_cells('FG', 4, (0, -8, 1), (0, 0.8, 0.8), rfps, nf, seed=8, R=0.08, dist=3.4)
    focus(cam, 1, nf, h['drop'], h['body'])

def circ_la_lv_aorta(nf, rfps, dur):
    """331.73-343.65: left atrium -> mitral valve -> left ventricle (the thickest wall), then the ventricle drives the drop
    up through the aortic valve and round the arch of the aorta, the body's biggest artery."""
    h = circ_rig(nf, rfps, dur, 331.73); root = h['root']
    anchor('AnLA', (0.8, -0.1, 0.62), parent_to=root); anchor('AnLV', (0.7, -0.1, -0.74), parent_to=root); anchor('AnAorta', (0.6, 0.6, 2.75), parent_to=root)
    cam, tgt = cam_track(h['at'], rfps, nf, 331.73, (1.6, -3.9, 0.4), lens=40, tgt_off=(-0.1, 0.0, 0.1), start=(1.5, (0.6, -12.5, 1.6), (0.0, 0.7, 0.9)))
    lens_kf(cam, [(1, 40), (F(4.0, rfps), 46), (nf, 44)]); fg_cells('FG', 4, (1, -6, 0), (0.5, 0.5, 0), rfps, nf, seed=9, R=0.07, dist=2.6)
    focus(cam, 1, nf, h['drop'], h['drop'])

def circ_body(nf, rfps, dur):
    """343.65-362.62: from the aorta the drop climbs the carotid to the brain, gives its oxygen (turns indigo) and comes
    back down the jugular and the superior vena cava into the right atrium, while other cells reach the muscle and the
    kidney; then 'heart -> body -> heart': the systemic loop lights up as the camera pulls back to the whole body."""
    h = circ_rig(nf, rfps, dur, 343.65); root = h['root']
    anchor('AnBrain', (-0.6, 0.4, 6.4), parent_to=root); anchor('AnMuscle', (4.6, 0.6, 1.0), parent_to=root); anchor('AnKidney', (1.0, 1.0, -3.4), parent_to=root)
    anchor('AnVC', (-0.85, -0.1, 2.5), parent_to=root); anchor('AnHeartC', (0.05, -1.0, -0.3), parent_to=root); anchor('AnBody', (2.6, -0.5, -3.2), parent_to=root)
    rnd = random.Random(4); T0 = 347.0 - 343.65
    for i in range(3):                                                   # oxygen leaving the drop for the brain tissue
        o = sphere(f'O2out{i}', 0.045, (0, 0, 0), seg=20, ring=10, mat=mat_glow(O2, strength=6.0, name=f'o2o{i}')); parent(o, root); t0 = T0 + i * 0.4
        p0 = Vector(journey_at(343.65 + t0)); p1 = p0 + Vector((rnd.uniform(-0.6, 0.6), rnd.uniform(-0.3, 0.6), rnd.uniform(0.2, 0.6)))
        show_between(o, F(t0, rfps), F(t0 + 1.8, rfps)); kf(o, 'location', F(t0, rfps), tuple(p0)); kf(o, 'location', F(t0 + 1.6, rfps), tuple(p1)); kf_ease(o)
    loop = glow_sleeve('LoopSysGlow', [(0.7, 0.1, -0.74), (0.15, 0.13, 0.6), (0.1, 0.25, 1.35), (0.2, 0.62, 2.35), (0.95, 1.1, 2.3), (2.5, 1.3, 3.2), (4.0, 1.7, 2.2), (4.7, 2.0, 1.2), (3.9, 1.9, 2.7), (2.2, 1.3, 3.5), (-0.6, 0.5, 3.6), (-0.88, 0.24, 1.7), (-0.82, 0.16, 0.6)], 0.2, P.mix(OXY_LIT, DEOXY_LIT, 0.5), strength=0.0, alpha=0.4); parent(loop, root)
    loop2 = glow_sleeve('LoopSysGlow2', [(0.2, 0.62, 2.35), (0.2, 0.72, 3.4), (0.0, 1.1, 4.7), (-0.5, 1.7, 6.0), (-0.9, 2.1, 6.6), (-1.2, 1.7, 5.6), (-1.1, 1.2, 4.4), (-0.72, 0.5, 3.7)], 0.16, P.mix(OXY_LIT, DEOXY_LIT, 0.5), strength=0.0, alpha=0.4); parent(loop2, root)
    loop3 = glow_sleeve('LoopSysGlow3', [(1.0, 1.15, 0.3), (0.95, 1.1, -1.4), (0.95, 1.08, -2.4), (1.0, 1.6, -3.0), (0.75, 2.2, -3.35), (0.0, 1.6, -3.3), (-1.05, 0.65, -2.6), (-1.1, 0.55, -0.8), (-1.0, 0.4, -0.05)], 0.16, P.mix(OXY_LIT, DEOXY_LIT, 0.5), strength=0.0, alpha=0.4); parent(loop3, root)
    for g in (loop, loop2, loop3): key_input(g.data.materials[0], 'Emission Strength', [(F(356.29 - 343.65, rfps), 0.0), (F(357.6 - 343.65, rfps), 2.2), (F(dur, rfps), 1.6)]); hide_until(g, F(356.29 - 343.65, rfps))
    cam, tgt = cam_track(h['at'], rfps, nf, 343.65, (2.0, -4.6, 0.7), lens=40, tgt_off=(-0.2, 0.0, 0.0), pull=(12.2, (1.5, -19.5, 1.4), (0.2, 0.9, 1.2)))
    lens_kf(cam, [(1, 44), (F(12.2, rfps), 44), (nf, 36)]); fg_cells('FG', 5, (1, -12, 1), (0, 0.8, 1), rfps, nf, seed=10, R=0.09, dist=4.0)
    focus(cam, 1, nf, h['drop'], h['body'])

def loop_diagram(root, nf, rfps, dur, name='Loop'):
    """The figure-8: a smaller pulmonary loop above and a larger systemic loop below crossing at a beating heart; the tube
    colour runs indigo -> crimson through the lungs and crimson -> indigo through the body; small lungs at the top, the
    organs at the bottom; cells circulate on the whole figure-8 path."""
    top_c, top_r, bot_c, bot_r = Vector((0, 0, 2.3)), 2.0, Vector((0, 0, -2.9)), 2.6
    def circ(c, r, n=32, start=-math.pi / 2, sgn=1): return [tuple(c + Vector((r * math.cos(start + sgn * 2 * math.pi * k / n), 0, r * math.sin(start + sgn * 2 * math.pi * k / n)))) for k in range(n)]
    mTop = mat_gradient(DEOXY, OXY, axis='X', lo=-0.9, hi=0.9, name=name + '_top', emit=0.9); mBot = mat_gradient(OXY, DEOXY, axis='X', lo=0.9, hi=-0.9, name=name + '_bot', emit=0.9)
    tp = tube(name + 'Top', circ(top_c, top_r), 0.16, mTop, res=6, bevel_res=8, cyclic=True); parent(tp, root)
    bt = tube(name + 'Bot', circ(bot_c, bot_r), 0.17, mBot, res=6, bevel_res=8, cyclic=True); parent(bt, root)
    h = heart(loc=(0, 0, -0.3), beat=(0.1, 0.83, 0.03), rfps=rfps, nf=nf, name=name + 'Heart', coronaries=True, fat=False, vessels=False); beat_all(h, 0.0, dur, rfps); h['root'].scale = (0.5, 0.5, 0.5)
    mL = mat_lung(name + '_lung', rim=True)
    for sgn in (-1, 1):
        lb = lung_lobe(f'{name}Lung{sgn}', (sgn * 1.05, 0.2, 4.45), (0.75, 0.9, 1.15), mL, 3 + sgn); parent(lb, root)
    sr = empty(name + 'Organs', (0, 0, -5.6)); parent(sr, root); sr.scale = (0.55, 0.55, 0.55)
    brain(sr, c=(-1.6, 0.4, 0.4)); muscle_bundle(sr, c=(0.2, 0.4, 0.0)); kidney(sr, c=(1.9, 0.5, 0.0))
    # the drop's figure-8 path: heart -> up the left of the top loop -> lungs -> down the right -> heart -> down the right of the bottom loop -> body -> up the left -> heart
    pts = [(0, 0, 0.0)] + [(-top_r * math.sin(a), 0, top_c.z - top_r * math.cos(a)) for a in [math.pi * k / 8 for k in range(1, 16)]] + [(0, 0, 0.0)] + \
          [(bot_r * math.sin(a), 0, bot_c.z + bot_r * math.cos(a)) for a in [math.pi * k / 8 for k in range(1, 16)]]
    pth = path_curve(name + 'Path', pts, cyclic=True); parent(pth, root)
    rbc_flow(name + 'Cell', pth, 26, rfps, nf, 0.06, R=0.11, mat=mat_cell(name + '_cm', animated=True), seed=6, spread=0.05, ox_keys=[(0.0, 0.0), (0.25, 1.0), (0.75, 0.0)], u_span=0.96)
    return dict(top=tp, bot=bt, heart=h, path=pth, top_c=top_c, bot_c=bot_c)

def twice_double(nf, rfps, dur):
    """362.62-371.56: the figure-8 diagram: one glowing drop runs the whole round once and passes through the heart
    TWICE (the overlay counts 1, 2 as it does): that is why it is called double circulation. Slow orbit."""
    reset(); stage(target=(0, 0, -0.4), key=(4.0, -8.0, 7.0), key_e=3200, fill_e=220, rim_e=600, spot=58, section=5)
    root = empty('LoopRoot', (0, 0, 0)); LD = loop_diagram(root, nf, rfps, dur)
    d = rbc('Drop', R=0.2, mat=mat_cell('drop_m', animated=True)); parent(d, root)
    glow = sphere('DropGlow', 0.34, mat=mat_glow(WHITE, strength=1.2, name='dropglow', alpha=0.25)); parent(glow, d)
    keys = [(1, 0.0), (nf, 1.0)]; follow(d, LD['path'], keys)
    for f in range(1, nf + 1, 2):
        u = (f - 1) / max(1, nf - 1); d['ox'] = _ox_at([(0.0, 0.0), (0.25, 1.0), (0.75, 0.0)], u); d.keyframe_insert('["ox"]', frame=f)
    anchor('AnDrop', (0, -0.3, 0), parent_to=d); anchor('AnLoopHeart', (0, -1.2, -0.1), parent_to=root); anchor('AnLoopLungs', (0, -0.6, 4.45), parent_to=root); anchor('AnLoopBody', (0, -0.6, -5.6), parent_to=root)
    motes('Motes', 200, (0, 2, 0), (9, 5, 9), color=PLASMA, r=0.02, strength=3.0, seed=3, drift=0.2, rfps=rfps, nf=nf)
    backglow((0, 0, -0.4), P.mix(OXY_LIT, DEOXY_LIT, 0.5), r=6.0, strength=0.35, depth=9)
    fg_cells('FG', 5, (0, -14, 0), (0, 0, -0.4), rfps, nf, seed=11, R=0.09, dist=4.5)
    cam, tgt = cam_orbit((0, 0, -0.6), 16.0, 0.4, -14, 14, 0.0, dur, rfps, lens=29, push=14.5)
    focus(cam, 1, nf, LD['heart']['body'], LD['heart']['body'])

def why_no_mixing(nf, rfps, dur):
    """371.56-386.65: 'why this arrangement?' on the cutaway: the septum lights gold while indigo cells on the right and
    crimson cells on the left stream past it and never mix; 'the body gets fully oxygenated blood': the aorta glows."""
    h = cut_rig(nf, rfps, dur, section=5); cut_streams(h, nf, rfps, dur, n=22, speed=0.1)
    keys = [(1, 0.0), (F(373.99 - 371.56, rfps), 0.0), (F(374.8 - 371.56, rfps), 1.0)]; t = 374.8 - 371.56
    while t + 1.2 < dur: keys += [(F(t + 0.6, rfps), 0.6), (F(t + 1.2, rfps), 1.0)]; t += 1.2
    set_septum(h, keys)
    gl = glow_sleeve('AortaGlow', [(0.12, 0.3, 0.8), (0.1, 0.25, 1.35), (0.05, 0.4, 1.9), (0.2, 0.62, 2.35), (0.65, 0.95, 2.45), (1.0, 1.1, 2.1), (1.05, 1.15, 1.4)], 0.36, OXY_LIT, strength=0.0, alpha=0.3); parent(gl, h['root'])
    key_input(gl.data.materials[0], 'Emission Strength', [(F(381.36 - 371.56, rfps), 0.0), (F(382.4 - 371.56, rfps), 2.4), (F(dur, rfps), 1.8)]); hide_until(gl, F(381.36 - 371.56, rfps))
    anchor('AnSeptum', (0.12, -0.15, -0.3), parent_to=h['root']); anchor('AnBlue', (-0.75, -0.1, -0.7), parent_to=h['root']); anchor('AnRed', (0.72, -0.1, -0.75), parent_to=h['root']); anchor('AnAorta', (0.6, 0.6, 2.6), parent_to=h['root'])
    fg_cells('FG', 4, (-2, -7, 0.5), (0, 0, -0.2), rfps, nf, seed=12, R=0.07, dist=2.8)
    cam, tgt = cam_path([(0.0, CAM_HERO[0], CAM_HERO[1]), (4.5, (-1.0, -5.4, 0.2), (0.1, 0.1, -0.4)), (9.5, (0.8, -5.6, 0.3), (0.1, 0.1, -0.35)), (dur, (0.4, -7.0, 1.4), (0.2, 0.3, 0.9))], rfps, lens=48)
    lens_kf(cam, [(1, 45), (F(4.5, rfps), 52), (F(9.5, rfps), 50), (nf, 44)]); focus(cam, 1, nf, h['body'], h['body'])

def creature_heart(root, loc, s, rfps, nf, dur, period, name):
    h = heart(loc=loc, beat=(0.1, period, 0.04), rfps=rfps, nf=nf, name=name, coronaries=False, fat=False, vessels=False); beat_all(h, 0.0, dur, rfps, period=period); h['root'].scale = (s, s, s)
    hm = h['mat']; p = hm.node_tree.nodes.get('Principled BSDF'); _inp(p, 'Emission Color', (*OXY_LIT, 1)); t = 0.1
    while t < dur: key_input(hm, 'Emission Strength', [(F(t, rfps), 0.05), (F(t + period * 0.15, rfps), 0.4), (F(t + period * 0.6, rfps), 0.05)]); t += period
    return h

def mammals_birds(nf, rfps, dur):
    """386.65-397.43: a warm-blooded mammal (a deer: body, neck, head with ears and muzzle, four legs, tail) and a bird
    (body, head, beak, tail, two flapping wings) as rim-lit silhouettes, ONE smooth skin each (voxel-unioned parts), each
    with a small fast-beating heart glowing inside and gold oxygen motes streaming in; their bodies pulse with an inner
    warmth glow."""
    reset(); stage(target=(0, 0, 0.8), key=(3.0, -8.0, 7.5), key_e=3200, fill_e=240, rim_e=600, spot=62, section=5)
    root = empty('AnimRoot', (0, 0, 0)); rnd = random.Random(3)
    mM = mat_rim(SKIN, SKIN_RIM, a_center=0.32, a_rim=0.92, emit=2.2, name='mammal_m', blend=0.4, rough=0.3, emit_min=0.35)
    mB = mat_rim(P.mix(SKIN, GOLD, 0.2), SKIN_RIM, a_center=0.32, a_rim=0.92, emit=2.2, name='bird_m', blend=0.4, rough=0.3, emit_min=0.35)
    # the deer
    dc = Vector((-4.2, 0.6, 0.2)); D = lambda x, y, z: (dc.x + x, dc.y + y, dc.z + z)
    P_ = [('capsule', D(-1.7, 0, 0.35), D(1.5, 0, 0.5), 0.78, 0.85), ('sphere', D(-0.2, 0, 0.1), 0.72, (1.7, 1.05, 0.95)), ('sphere', D(1.6, 0, 0.55), 0.8, (1.0, 0.95, 1.05)), ('sphere', D(-1.9, 0, 0.5), 0.72, (1.0, 0.95, 1.1)),
          ('capsule', D(1.9, 0, 1.0), D(2.95, 0, 2.55), 0.46, 0.34), ('sphere', D(3.15, 0, 2.85), 0.4, (1.35, 0.85, 0.85)), ('capsule', D(3.35, 0, 2.75), D(4.05, 0, 2.55), 0.27, 0.19),
          ('capsule', D(-2.0, 0, 0.55), D(-2.55, 0, 0.05), 0.11, 0.05)]
    for sy in (-1, 1):
        P_ += [('capsule', D(3.0, sy * 0.3, 3.15), D(3.05, sy * 0.55, 3.8), 0.13, 0.05),                        # ears
               ('capsule', D(1.35, sy * 0.38, -0.2), D(1.5, sy * 0.42, -1.35), 0.3, 0.2), ('capsule', D(1.5, sy * 0.42, -1.35), D(1.58, sy * 0.42, -2.5), 0.17, 0.13), ('capsule', D(1.58, sy * 0.42, -2.5), D(1.65, sy * 0.42, -3.05), 0.13, 0.13),
               ('capsule', D(-1.55, sy * 0.4, -0.2), D(-1.8, sy * 0.42, -1.3), 0.32, 0.2), ('capsule', D(-1.8, sy * 0.42, -1.3), D(-1.55, sy * 0.42, -2.4), 0.17, 0.13), ('capsule', D(-1.55, sy * 0.42, -2.4), D(-1.5, sy * 0.42, -3.05), 0.13, 0.13)]
    deer = union_mesh('Mammal', P_, voxel=0.06, mat=mM, smooth_iter=3, sub=1); parent(deer, root)
    try: deer.visible_shadow = False
    except Exception: pass
    t = 0.0                                                                   # the deer breathes
    while t < dur + 1.0:
        kf(deer, 'scale', F(t, rfps), (1, 1, 1)); kf(deer, 'scale', F(t + 1.1, rfps), (1.0, 1.03, 1.02)); t += 2.2
    kf_ease(deer)
    hd = creature_heart(root, tuple(dc + Vector((1.2, 0, 0.1))), 0.26, rfps, nf, dur, 0.5, 'DeerHeart')
    # the bird
    bc = Vector((4.3, 0.6, 2.4)); B = lambda x, y, z: (bc.x + x, bc.y + y, bc.z + z)
    Q = [('capsule', B(-0.9, 0, 0.0), B(0.95, 0, 0.3), 0.5, 0.58), ('sphere', B(0.2, 0, 0.15), 0.6, (1.2, 1.0, 1.0)), ('capsule', B(1.0, 0, 0.35), B(1.35, 0, 0.72), 0.3, 0.27), ('sphere', B(1.5, 0, 0.8), 0.36, None),
         ('capsule', B(1.75, 0, 0.76), B(2.25, 0, 0.7), 0.12, 0.02), ('sphere', B(-1.55, 0, -0.02), 0.36, (1.7, 1.2, 0.22))]
    bird = union_mesh('Bird', Q, voxel=0.04, mat=mB, smooth_iter=3, sub=1); parent(bird, root)
    try: bird.visible_shadow = False
    except Exception: pass
    wings = []
    for sgn in (-1, 1):
        wr = empty(f'Wing{sgn}', tuple(bc + Vector((0, sgn * 0.45, 0.4)))); parent(wr, root)
        Wp = [('sphere', (0, sgn * 0.9, 0), 0.62, (1.3, 1.7, 0.2)), ('sphere', (0.15, sgn * 2.0, 0.08), 0.5, (1.1, 1.7, 0.16))] + [('capsule', (-0.2 - 0.12 * k, sgn * (2.3 + 0.25 * k), 0.1), (-0.85 - 0.25 * k, sgn * (2.9 + 0.35 * k), 0.12), 0.13, 0.05) for k in range(4)]
        w = union_mesh(f'WingMesh{sgn}', Wp, voxel=0.035, mat=mB, smooth_iter=2, sub=1); w.parent = wr; w.matrix_parent_inverse = Matrix.Identity(4); wings.append(wr)
        t = 0.0
        while t < dur + 0.3:
            kf(wr, 'rotation_euler', F(t, rfps), (sgn * -0.55, 0, 0)); kf(wr, 'rotation_euler', F(t + 0.24, rfps), (sgn * 0.5, 0, 0)); t += 0.48
        kf_ease(wr)
    hb = creature_heart(root, tuple(bc + Vector((0.3, 0, 0.0))), 0.11, rfps, nf, dur, 0.22, 'BirdHeart')
    for o in (bird, hb['root']) + tuple(wings):                               # the bird bobs
        base = Vector(o.location); t = 0.0
        while t < dur + 0.5:
            kf(o, 'location', F(t, rfps), tuple(base)); kf(o, 'location', F(t + 0.24, rfps), tuple(base + Vector((0, 0, 0.18)))); t += 0.48
        kf_ease(o)
    mo = mat_glow(O2, strength=5.0, name='o2_anim')
    for i in range(16):
        tgt_c = dc + Vector((1.2, 0, 0.1)) if i % 2 == 0 else bc + Vector((0.3, 0, 0)); start = tgt_c + Vector((rnd.uniform(-3.5, 3.5), rnd.uniform(-2.5, -1.0), rnd.uniform(1.5, 4.0)))
        o = sphere(f'O2a{i}', 0.05, tuple(start), seg=16, ring=8, mat=mo); parent(o, root); t0 = rnd.uniform(0, dur - 2.5)
        show_between(o, F(t0, rfps), F(t0 + 2.4, rfps)); kf(o, 'location', F(t0, rfps), tuple(start)); kf(o, 'location', F(t0 + 2.2, rfps), tuple(tgt_c)); kf_ease(o)
    anchor('AnMammal', tuple(dc + Vector((0.4, -1.4, 2.2)))); anchor('AnBird', tuple(bc + Vector((0.0, -1.2, 1.4))))
    motes('Motes', 200, (0, 2, 1), (12, 5, 7), color=PLASMA, r=0.02, strength=3.0, seed=3, drift=0.2, rfps=rfps, nf=nf)
    backglow((0, 0.6, 0.8), P.mix(OXY_LIT, GOLD, 0.5), r=7.0, strength=0.35, depth=9)
    fg_cells('FG', 4, (0, -14, 1), (0, 0, 0.8), rfps, nf, seed=13, R=0.09, dist=4.5)
    cam, tgt = cam_path([(0.0, (-6.5, -13.5, 1.6), (-3.5, 0.5, 0.6)), (5.0, (0.0, -14.0, 2.2), (0.0, 0.5, 1.0)), (dur, (5.5, -12.0, 3.0), (3.8, 0.5, 2.2))], rfps, lens=42)
    lens_kf(cam, [(1, 42), (nf, 46)]); focus(cam, 1, nf, deer, bird)

def fish_single(nf, rfps, dur):
    """397.43-409.67: a fish (rim-lit silhouette, swaying) with its two-chamber heart behind the gills: one atrium, one
    ventricle; cells leave the heart, pass the gill arches (turn crimson), run down the body (turn indigo) and return:
    one loop, the heart passed ONCE = single circulation."""
    reset(); stage(target=(0, 0, 0), key=(3.0, -8.0, 7.0), key_e=3000, fill_e=240, rim_e=620, spot=60, section=5)
    root = empty('FishRoot', (0, 0, 0)); mF = mat_rim(P.mix(CYAN, VEIN_WALL, 0.45), P.mix(CYAN, WHITE, 0.3), a_center=0.12, a_rim=0.85, emit=1.5, name='fish_m', blend=0.45)
    els = [((0, 0, 0), 1.0, (3.2, 0.9, 1.4)), ((2.6, 0, 0.1), 0.72, (1.4, 0.8, 1.0)), ((3.6, 0, 0.05), 0.4, (1.5, 0.7, 0.7)), ((-2.9, 0, 0), 0.5, (1.4, 0.5, 0.7)), ((-4.0, 0, 0.9), 0.32, (1.4, 0.25, 1.6)), ((-4.0, 0, -0.9), 0.32, (1.4, 0.25, 1.6)),
           ((0.3, 0, 1.5), 0.42, (2.2, 0.2, 1.0)), ((1.3, 0.75, -0.7), 0.3, (1.4, 0.25, 0.9)), ((1.3, -0.75, -0.7), 0.3, (1.4, 0.25, 0.9)), ((-1.0, 0, -1.3), 0.3, (1.5, 0.2, 0.8))]
    fish = meta_mesh('Fish', els, res=0.08, mat=mF); parent(fish, root)
    try: fish.visible_shadow = False
    except Exception: pass
    # gill arches: five red arches on the head side, the site of oxygen uptake
    mG = mat_vessel(OXY, name='gill_m', coat=0.5, emit=0.9, vein_scale=12.0); gills = []
    for k in range(5):
        x = 2.05 + 0.18 * k
        g = tube(f'Gill{k}', [(x, -0.62, -0.75), (x + 0.1, -0.85, -0.2), (x + 0.12, -0.8, 0.35), (x, -0.55, 0.8)], 0.05, mG, res=8, bevel_res=5); parent(g, root); gills.append(g)
    # the two-chamber heart below/behind the gills: thin-walled atrium (indigo) feeding a muscular ventricle (wine), and the ventral aorta forward
    mAtr = mat_organic(P.mix(DEOXY, ENDO, 0.4), rough=0.4, sss=0.35, coat=0.4, name='fatr'); mVen = mat_muscle('fven', coat=0.6)
    atr = meta_mesh('FishAtrium', [((1.25, 0.05, -0.55), 0.3, (1.0, 0.9, 0.85)), ((1.05, 0.15, -0.4), 0.2, None)], res=0.03, mat=mAtr); parent(atr, root)
    ven = meta_mesh('FishVentricle', [((1.75, 0.0, -0.62), 0.36, (1.0, 0.9, 0.9)), ((1.95, 0.0, -0.45), 0.22, None)], res=0.03, mat=mVen); parent(ven, root)
    pulse_scale(atr, 0.0, dur, rfps, period=1.0, amp=0.1, phase=0.0); pulse_scale(ven, 0.0, dur, rfps, period=1.0, amp=0.12, phase=0.25)
    mR = mat_vessel(DEOXY, name='fva', coat=0.5, emit=0.3); mA = mat_vessel(OXY, name='fda', coat=0.5, emit=0.3); mV = mat_vessel(DEOXY, name='fvv', coat=0.5, emit=0.3)
    parent(tube('VentralAorta', [(1.95, 0, -0.45), (2.15, -0.3, -0.5), (2.4, -0.7, -0.4)], 0.07, mR, res=8), root)
    parent(tube('DorsalAorta', [(2.2, -0.45, 0.85), (1.2, -0.2, 0.9), (0.0, 0, 0.95), (-1.5, 0, 0.75), (-3.0, 0, 0.3)], 0.06, mA, res=10), root)
    parent(tube('BodyVein', [(-3.0, 0, -0.1), (-1.5, 0, -0.6), (0.0, 0.1, -0.85), (0.9, 0.15, -0.7), (1.2, 0.1, -0.55)], 0.06, mV, res=10), root)
    loop = path_curve('FishLoop', [(1.25, 0.05, -0.55), (1.75, 0.0, -0.62), (2.15, -0.3, -0.5), (2.45, -0.75, -0.3), (2.4, -0.7, 0.5), (2.2, -0.45, 0.85), (1.2, -0.2, 0.9), (0.0, 0, 0.95), (-1.5, 0, 0.75), (-3.0, 0, 0.3), (-3.0, 0, -0.1), (-1.5, 0, -0.6), (0.0, 0.1, -0.85), (0.9, 0.15, -0.7)], cyclic=True); parent(loop, root)
    rbc_flow('FC', loop, 22, rfps, nf, 0.07, R=0.06, mat=mat_cell('fc_m', animated=True), seed=7, spread=0.03, ox_keys=[(0.0, 0.0), (0.24, 1.0), (0.68, 0.0)], u_span=0.95)
    anchor('AnFAtrium', (1.2, -0.5, -0.95)); anchor('AnFVent', (1.9, -0.5, -1.1)); anchor('AnGills', (2.35, -1.1, 0.9)); anchor('AnFBody', (-1.5, -0.8, 1.2))
    # the fish swims in place: a gentle sway of the whole body and the tail
    t = 0.0
    while t < dur + 1:
        kf(root, 'rotation_euler', F(t, rfps), (0, 0, 0.04)); kf(root, 'rotation_euler', F(t + 0.9, rfps), (0, 0, -0.04)); t += 1.8
    kf_ease(root)
    motes('Motes', 220, (0, 2, 0), (10, 5, 6), color=DUST, r=0.02, strength=3.0, seed=3, drift=0.35, rfps=rfps, nf=nf)
    bubbles = motes('Bubbles', 60, (2, -1, 0), (5, 2, 3), color=P.mix(CYAN, WHITE, 0.5), r=0.03, strength=2.0, seed=8, drift=1.6, rfps=rfps, nf=nf)
    backglow((0, 0, 0), P.mix(CYAN, DEOXY_LIT, 0.5), r=6.0, strength=0.35, depth=8)
    fg_cells('FG', 3, (0, -10, 0), (0, 0, 0), rfps, nf, seed=14, R=0.07, dist=3.5)
    cam, tgt = cam_orbit((0.6, -0.2, 0.0), 10.5, 1.2, -22, 16, 0.0, dur, rfps, lens=42, push=8.0, tilt=0.4)
    focus(cam, 1, nf, fish, ven)

# ================================================================= 6. BLOOD PRESSURE
def pressure_arrows(root, name, n, x_span, r_in, t0, t1, rfps, period=0.83, color=GOLD, open_dir=(-1.0, 0.0)):
    """Glowing pressure arrows (cones) from the lumen toward the kept wall that flash outward on every beat."""
    m = mat_glow(color, strength=3.0, name=name + '_m', alpha=0.85); out = []; a_open = math.atan2(open_dir[1], open_dir[0]); rnd = random.Random(2)
    for i in range(n):
        x = x_span[0] + (x_span[1] - x_span[0]) * (i + 0.5) / n; a = a_open + math.pi + rnd.uniform(-1.1, 1.1)
        p0 = Vector((x, 0.35 * r_in * math.cos(a), 0.35 * r_in * math.sin(a))); p1 = Vector((x, 0.92 * r_in * math.cos(a), 0.92 * r_in * math.sin(a)))
        L_ = (p1 - p0).length; o = obj_add('cone', f'{name}{i}', radius1=0.085, radius2=0.0, depth=L_ * 0.45, vertices=24); orient(o, p0 + (p1 - p0) * 0.55, p1); setmat(o, m); smooth(o); parent(o, root)
        sh = obj_add('cylinder', f'{name}{i}s', radius=0.03, depth=L_ * 0.55, vertices=16); orient(sh, p0, p0 + (p1 - p0) * 0.55); setmat(sh, m); smooth(sh); sh.parent = o; sh.matrix_parent_inverse = o.matrix_world.inverted()
        try: o.visible_shadow = False
        except Exception: pass
        t = t0 + rnd.uniform(0, 0.15)
        while t < t1:
            for dt, s_ in ((0.0, 0.05), (0.12, 1.0), (0.5, 0.05)): kf(o, 'scale', F(t + dt, rfps), (s_, s_, s_))
            t += period
        kf_ease(o); out.append(o)
    return out

def pressure_walls(nf, rfps, dur):
    """412.27-420.3: inside an artery: cells rush along and press on the wall; with every beat the wall swells and gold
    pressure arrows flash from the blood onto the wall; 'this is blood pressure' (417.86) with the anchors on the wall."""
    reset(); stage(target=(0, 0.2, 0), key=(2.5, -6.0, 6.0), key_e=2800, fill_e=200, rim_e=560, spot=54, section=6)
    root = empty('PRoot', (0, 0, 0)); art = vessel_section(root, 'Art', kind='artery', loc=(0, 0, 0), length=8.0, r=0.75, cut_front=True)
    mr = mat_cell('p_cells', ox=1.0); rbc_flow('C', art['path'], 30, rfps, nf, 0.24, R=0.13, mat=mr, seed=6, spread=0.32, u_span=0.95)
    pulse_wall(art, 0.2, dur, rfps, period=0.83, amp=0.09); pressure_arrows(root, 'Push', 9, (-3.2, 3.2), art['r_in'], 0.2, dur, rfps)
    anchor('AnWall', (0.6, 0.35, art['r_out'] * 0.9)); anchor('AnPush', (-1.2, 0.2, art['r_in'] * 0.5))
    motes('Motes', 160, (0, 2, 0), (9, 4, 5), color=PLASMA, r=0.02, strength=3.5, seed=3, drift=0.3, rfps=rfps, nf=nf)
    backglow((0, 0, 0), P.mix(OXY_LIT, GOLD, 0.35), r=5.0, strength=0.4)
    fg_cells('FG', 5, (-2, -7, 1), (0, 0, 0), rfps, nf, seed=15, R=0.09, dist=2.8, mat=mr)
    cam, tgt = cam_path([(0.0, (-4.5, -6.0, 1.8), (-1.5, 0.2, 0.1)), (4.0, (-1.0, -4.6, 1.4), (0.2, 0.2, 0.1)), (dur, (2.2, -4.2, 1.0), (0.8, 0.3, 0.3))], rfps, lens=42)
    lens_kf(cam, [(1, 40), (nf, 46)]); focus(cam, 1, nf, art['layers']['media'], art['layers']['media'])

def gauge(root, loc=(0, 0, 0), R=1.0, name='Gauge', face_dir=-1):
    """An aneroid dial: chrome bezel ring and case, warm-white face with 0-300 mmHg ticks (every 10, long every 50), a
    red needle on a chrome hub. The face looks along -Y (at the camera). set_gauge() keys the needle."""
    mc = mat_chrome(name + '_chrome'); mf = mat_plastic(DIAL, rough=0.5, name=name + '_face', coat=0.2); mt = mat_plastic((0.12, 0.12, 0.14), rough=0.6, name=name + '_tick'); mn = mat_plastic(NEEDLE, rough=0.3, name=name + '_needle', coat=0.4)
    x, y, z = loc
    case = obj_add('cylinder', name + 'Case', radius=R, depth=0.3 * R, vertices=128, location=(x, y + 0.15 * R, z)); case.rotation_euler = (math.pi / 2, 0, 0); setmat(case, mc); smooth(case)
    try: md = case.modifiers.new('bev', 'BEVEL'); md.width = 0.05 * R; md.segments = 6
    except Exception: pass
    bez = obj_add('torus', name + 'Bezel', major_radius=R * 0.93, minor_radius=0.06 * R, major_segments=128, minor_segments=20, location=(x, y - 0.02 * R, z)); bez.rotation_euler = (math.pi / 2, 0, 0); setmat(bez, mc); smooth(bez, auto=False)
    face = obj_add('cylinder', name + 'Face', radius=R * 0.88, depth=0.02 * R, vertices=128, location=(x, y + 0.0, z)); face.rotation_euler = (math.pi / 2, 0, 0); setmat(face, mf); smooth(face)
    ticks = bmesh.new()
    for k in range(31):
        a = math.radians(-135 + 270 * k / 30); long_ = (k % 5 == 0); r0 = R * (0.72 if long_ else 0.78); r1 = R * 0.84
        bmesh.ops.create_cube(ticks, size=1.0, matrix=Matrix.Translation(Vector((x + (r0 + r1) / 2 * math.sin(a), y - 0.02 * R, z + (r0 + r1) / 2 * math.cos(a)))) @ Euler((0, -a, 0)).to_matrix().to_4x4() @ Matrix.Diagonal((0.025 * R if long_ else 0.014 * R, 0.01 * R, r1 - r0, 1.0)))
    tk = mesh_obj(name + 'Ticks', ticks, mt, smooth_=False)
    for k in range(7):                                                # numerals 0 .. 300 every 50, plus the unit
        a = math.radians(-135 + 270 * k / 6); tx = bpy.data.curves.new(f'{name}Num{k}', 'FONT'); tx.body = str(k * 50); tx.size = 0.11 * R; tx.align_x = 'CENTER'; tx.align_y = 'CENTER'
        try: tx.extrude = 0.002 * R
        except Exception: pass
        to = bpy.data.objects.new(f'{name}Num{k}', tx); bpy.context.collection.objects.link(to); to.location = (x + 0.62 * R * math.sin(a), y - 0.025 * R, z + 0.62 * R * math.cos(a)); to.rotation_euler = (math.pi / 2, 0, 0); setmat(to, mt); to.parent = root; to.matrix_parent_inverse = Matrix.Identity(4)
    tu = bpy.data.curves.new(name + 'Unit', 'FONT'); tu.body = 'mm Hg'; tu.size = 0.09 * R; tu.align_x = 'CENTER'; tu.align_y = 'CENTER'
    uo = bpy.data.objects.new(name + 'Unit', tu); bpy.context.collection.objects.link(uo); uo.location = (x, y - 0.025 * R, z - 0.38 * R); uo.rotation_euler = (math.pi / 2, 0, 0); setmat(uo, mt); uo.parent = root; uo.matrix_parent_inverse = Matrix.Identity(4)
    hub = obj_add('cylinder', name + 'Hub', radius=0.07 * R, depth=0.08 * R, vertices=32, location=(x, y - 0.05 * R, z)); hub.rotation_euler = (math.pi / 2, 0, 0); setmat(hub, mc); smooth(hub)
    piv = empty(name + 'Pivot', (x, y - 0.06 * R, z))
    nd = obj_add('cube', name + 'Needle', size=1.0); nd.scale = (0.035 * R, 0.012 * R, 0.82 * R); nd.location = (0, 0, 0.32 * R); setmat(nd, mn)
    try: md = nd.modifiers.new('bev', 'BEVEL'); md.width = 0.004 * R; md.segments = 3
    except Exception: pass
    tail = obj_add('cube', name + 'NTail', size=1.0); tail.scale = (0.06 * R, 0.012 * R, 0.14 * R); tail.location = (0, 0, -0.08 * R); setmat(tail, mn)
    for o in (nd, tail): o.parent = piv; o.matrix_parent_inverse = Matrix.Identity(4)
    tip = anchor(name + 'Tip', (0, -0.05 * R, 0.72 * R), parent_to=piv)
    for o in (case, bez, face, tk, hub, piv): parent(o, root)
    return dict(case=case, face=face, pivot=piv, needle=nd, tip=tip, loc=loc, R=R)

def gauge_angle(mmhg): return math.radians(-135 + 270 * max(0.0, min(300.0, mmhg)) / 300)
def set_gauge(g, keys, rfps):
    """keys = [(t_sec, mmHg)] -> needle rotation (about Y, clockwise from the top)."""
    for t, v in keys:
        g['pivot'].rotation_euler = (0, gauge_angle(v), 0); g['pivot'].keyframe_insert('rotation_euler', frame=F(t, rfps))
    kf_ease(g['pivot'])

def bp_keys(t0, t1, period=0.83, hi=120, lo=80):
    keys = []; t = t0
    while t < t1 + period:
        keys += [(t, lo), (t + period * 0.16, hi), (t + period * 0.36, hi - 6), (t + period * 0.9, lo)]; t += period
    return keys

def systolic_diastolic(nf, rfps, dur):
    """420.3-434.0: the cutaway heart runs ONE slow, exaggerated beat: the ventricles squeeze (cells driven out, aorta glow,
    the gauge climbs to 120 = systolic), then let go (the gauge sinks to 80 = diastolic), timed to the four sentences."""
    vk = [(0.0, 1.0), (0.5, 1.0), (1.3, 0.0), (7.2, 0.0), (8.4, 1.0), (dur, 1.0)]
    h = cut_rig(nf, rfps, dur, section=6, beat=False, valve_keys=vk, glow_col=P.mix(OXY_LIT, GOLD, 0.4))
    heart_pose(h, [(0.0, 0.0)], [(0.4, 0.0), (2.0, 1.0), (7.3, 1.0), (9.0, 0.0), (dur, 0.0)], rfps)
    keysR = [(0.0, U_R['rv'] + 0.08), (0.6, U_R['rv'] + 0.08), (4.0, U_R['trunk'] + 0.06), (dur, U_R['trunk'] + 0.1)]
    keysL = [(0.0, U_L['lv'] + 0.08), (0.6, U_L['lv'] + 0.08), (4.0, U_L['arch'] + 0.04), (dur, U_L['arch'] + 0.08)]
    stage_streams(h, nf, rfps, keysR, keysL, n=18)
    gl = glow_sleeve('AortaGlow', [(0.12, 0.3, 0.8), (0.1, 0.25, 1.35), (0.05, 0.4, 1.9), (0.2, 0.62, 2.35), (0.65, 0.95, 2.45), (1.0, 1.1, 2.1)], 0.36, GOLD, strength=0.0, alpha=0.3); parent(gl, h['root'])
    key_input(gl.data.materials[0], 'Emission Strength', [(F(0.6, rfps), 0.0), (F(2.0, rfps), 2.4), (F(7.2, rfps), 1.6), (F(9.0, rfps), 0.2)])
    g = gauge(h['root'], loc=(-3.3, 0.9, 0.3), R=0.72, name='Gauge'); set_gauge(g, [(0.0, 80), (0.6, 80), (2.0, 120), (7.2, 118), (9.0, 80), (dur, 80)], rfps)
    link = tube('GaugeLink', [(-2.6, 0.92, 0.3), (-1.9, 1.0, 0.9), (-0.9, 0.7, 1.6), (-0.3, 0.4, 1.6)], 0.05, mat_rubber('link_r'), res=8, bevel_res=5); parent(link, h['root'])
    anchor('AnGauge', (-3.3, 0.1, 1.1), parent_to=h['root']); anchor('AnHeartS', (0.05, -0.6, 1.45), parent_to=h['root']); chamber_anchors(h['root'], 'An')
    fg_cells('FG', 4, (-2, -7, 0.5), (0, 0, -0.2), rfps, nf, seed=16, R=0.07, dist=2.8)
    cam, tgt = cam_path([(0.0, (-2.4, -8.2, 0.9), (-1.0, 0.1, 0.0)), (5.0, (-2.0, -7.6, 0.6), (-1.1, 0.1, -0.1)), (dur, (-1.4, -7.8, 0.4), (-0.9, 0.1, -0.2))], rfps, lens=40)
    lens_kf(cam, [(1, 38), (nf, 42)]); focus(cam, 1, nf, h['body'], g['face'])

def gauge_120_80(nf, rfps, dur):
    """434.0-442.22: the gauge as the hero: a big aneroid dial whose needle swings between 80 and 120 with every beat of
    the small heart beside it (the heart glow and the needle rise together); slow orbit and push."""
    reset(); stage(target=(0, 0, 0.2), key=(3.0, -6.5, 6.0), key_e=2800, fill_e=220, rim_e=560, spot=54, section=6)
    root = empty('GRoot', (0, 0, 0)); g = gauge(root, loc=(0.9, 0.3, 0.3), R=1.5, name='Gauge'); set_gauge(g, bp_keys(0.2, dur), rfps)
    hm = creature_heart(root, (-2.6, 0.5, -0.3), 0.6, rfps, nf, dur, 0.83, 'MiniHeart')
    link = tube('GaugeLink', [(-1.7, 0.6, 0.4), (-1.0, 0.7, 0.9), (0.2, 0.5, 1.2), (0.9, 0.55, 0.9)], 0.06, mat_rubber('link_r'), res=8, bevel_res=5); parent(link, root)
    gl = glow_sleeve('LinkGlow', [(-1.7, 0.6, 0.4), (-1.0, 0.7, 0.9), (0.2, 0.5, 1.2), (0.9, 0.55, 0.9)], 0.11, GOLD, strength=0.0, alpha=0.4); parent(gl, root); t = 0.2
    while t < dur: key_input(gl.data.materials[0], 'Emission Strength', [(F(t, rfps), 0.1), (F(t + 0.16, rfps), 2.4), (F(t + 0.7, rfps), 0.1)]); t += 0.83
    anchor('AnNeedle', (0, -0.1, 0), parent_to=g['tip']); anchor('AnDial', (0.9, -0.5, 1.55))
    motes('Motes', 160, (0, 2, 0), (8, 4, 5), color=PLASMA, r=0.02, strength=3.5, seed=3, drift=0.25, rfps=rfps, nf=nf)
    backglow((0.2, 0.4, 0.3), P.mix(OXY_LIT, GOLD, 0.5), r=4.5, strength=0.4, depth=7)
    fg_cells('FG', 4, (0, -7, 0.5), (0, 0, 0.2), rfps, nf, seed=17, R=0.08, dist=2.8)
    cam, tgt = cam_orbit((0.0, 0.3, 0.2), 6.8, 0.9, -20, 12, 0.0, dur, rfps, lens=45, push=5.6)
    focus(cam, 1, nf, hm['body'], g['face'])

def cuff_arm(root, name='Arm'):
    """An arm (metaball upper arm, elbow, forearm, hand) with a slate-blue fabric cuff wrapped round the upper arm (a
    thick fabric shell, its edge binding, the velcro strip and a brass port), the rubber tube to a hand bulb with its
    chrome valve, and a second tube leaving toward the gauge. Returns dict(cuff, bulb, arm, port)."""
    ms = mat_skin(name + '_skin'); _noise_bump(ms, ms.node_tree.nodes.get('Principled BSDF'), scale=24.0, strength=0.1, detail=5.0, distance=0.02)
    els = [((-3.2, 0, 0.1), 0.62, (2.6, 1.0, 1.0)), ((-0.6, 0, 0), 0.6, (1.3, 1.0, 1.0)), ((1.2, 0, -0.15), 0.5, (3.0, 1.0, 0.95)), ((3.6, 0, -0.35), 0.42, (1.6, 1.0, 0.7))]
    for k in range(4): els.append(((4.4 + 0.1 * k, -0.3 + 0.2 * k, -0.45), 0.17, (2.2, 0.9, 0.9)))
    arm = meta_mesh(name, els, res=0.07, mat=ms); subsurf(arm, 0, 1); parent(arm, root)
    mfab = mat_fabric(CUFF, name + '_cuff'); cuff = obj_add('cylinder', name + 'Cuff', radius=0.9, depth=2.3, vertices=96, location=(-3.0, 0, 0.1)); cuff.rotation_euler = (0, math.pi / 2, 0); setmat(cuff, mfab); smooth(cuff)
    solidify(cuff, 0.16)
    try: md = cuff.modifiers.new('bev', 'BEVEL'); md.width = 0.05; md.segments = 4
    except Exception: pass
    parent(cuff, root)
    for sx in (-1.13, 1.13):
        edge = obj_add('torus', f'{name}Edge{sx > 0}', major_radius=0.92, minor_radius=0.05, major_segments=96, minor_segments=14, location=(-3.0 + sx, 0, 0.1)); edge.rotation_euler = (0, math.pi / 2, 0); setmat(edge, mat_fabric(P.scale(CUFF, 0.7), name + '_edge')); smooth(edge, auto=False); parent(edge, root)
    velcro = obj_add('torus', name + 'Velcro', major_radius=0.99, minor_radius=0.03, major_segments=96, minor_segments=12, location=(-3.0, 0, 0.1)); velcro.rotation_euler = (0, math.pi / 2, 0); velcro.scale = (1.0, 1.0, 1.0)
    for v in velcro.data.vertices: v.co.z *= 5.5                      # a wide strap band wrapped round the cuff
    setmat(velcro, mat_fabric((0.3, 0.32, 0.36), name + '_velcro')); smooth(velcro, auto=False); parent(velcro, root)
    mb = mat_metal((0.75, 0.6, 0.3), rough=0.35, name=name + '_brass'); port = obj_add('cylinder', name + 'Port', radius=0.09, depth=0.3, vertices=32, location=(-2.4, -0.95, -0.1)); port.rotation_euler = (math.pi / 2, 0, 0); setmat(port, mb); smooth(port); parent(port, root)
    mr = mat_rubber(name + '_rub'); t1 = tube(name + 'Tube1', [(-2.4, -1.1, -0.1), (-2.2, -1.9, -0.6), (-1.6, -2.6, -1.4), (-0.8, -2.9, -1.9)], 0.07, mr, res=10, bevel_res=6); parent(t1, root)
    bulb = meta_mesh(name + 'Bulb', [((-0.2, -3.0, -2.2), 0.42, (1.0, 1.0, 1.3)), ((-0.55, -2.95, -2.0), 0.28, None)], res=0.03, mat=mat_rubber(name + '_bulb', color=(0.06, 0.06, 0.07))); subsurf(bulb, 0, 1); parent(bulb, root)
    valve = obj_add('cylinder', name + 'Valve', radius=0.08, depth=0.35, vertices=32, location=(0.12, -3.05, -2.62)); valve.rotation_euler = (0.3, 0.9, 0); setmat(valve, mat_chrome(name + '_ch')); smooth(valve); parent(valve, root)
    knob = obj_add('cylinder', name + 'Knob', radius=0.11, depth=0.08, vertices=32, location=(0.32, -3.1, -2.75)); knob.rotation_euler = (0.3, 0.9, 0); setmat(knob, mat_chrome(name + '_ch2')); smooth(knob); parent(knob, root)
    t2 = tube(name + 'Tube2', [(-3.4, -0.95, -0.1), (-3.9, -1.8, 0.4), (-4.6, -2.2, 1.4), (-5.0, -1.9, 2.2)], 0.07, mr, res=10, bevel_res=6); parent(t2, root)
    return dict(cuff=cuff, bulb=bulb, arm=arm, port=port, tube2=t2)

def sphygmo(nf, rfps, dur):
    """442.22-447.72: the sphygmomanometer: the cuff on an arm inflates (the bulb squeezed), the dial beside it climbs;
    slow crane down and push in."""
    reset(); stage(target=(-2.5, -0.5, 0.3), key=(1.5, -6.5, 6.5), key_e=3000, fill_e=220, rim_e=560, spot=56, section=6)
    root = empty('SRoot', (0, 0, 0)); A = cuff_arm(root); g = gauge(root, loc=(-5.6, -1.4, 2.9), R=0.85, name='GaugeS')
    set_gauge(g, [(0.0, 0), (0.8, 0), (3.6, 160), (4.4, 150), (dur, 140)], rfps)
    for f_, s_ in ((F(0.8, rfps), 1.0), (F(3.6, rfps), 1.12), (F(dur, rfps), 1.12)): kf(A['cuff'], 'scale', f_, (1.0, s_, s_))
    kf_ease(A['cuff'])
    t = 0.9
    while t < 3.8:                                                        # the bulb squeezed
        kf(A['bulb'], 'scale', F(t, rfps), (1, 1, 1)); kf(A['bulb'], 'scale', F(t + 0.22, rfps), (0.82, 0.82, 0.86)); kf(A['bulb'], 'scale', F(t + 0.5, rfps), (1, 1, 1)); t += 0.6
    kf_ease(A['bulb'])
    anchor('AnCuff', (-3.0, -1.2, 1.25)); anchor('AnGaugeS', (-5.6, -2.3, 3.9)); anchor('AnBulb', (-0.2, -3.4, -1.6))
    motes('Motes', 160, (-2, 1, 0), (9, 4, 5), color=PLASMA, r=0.02, strength=3.5, seed=3, drift=0.25, rfps=rfps, nf=nf)
    backglow((-2.5, -0.5, 0.3), P.mix(OXY_LIT, GOLD, 0.5), r=5.5, strength=0.35, depth=8)
    fg_cells('FG', 3, (-2, -9, 1), (-2.5, -0.5, 0.3), rfps, nf, seed=18, R=0.08, dist=3.4)
    cam, tgt = cam_path([(0.0, (-1.2, -11.0, 3.6), (-2.8, -0.8, 0.8)), (dur, (-0.6, -9.2, 1.8), (-2.7, -1.0, 0.5))], rfps, lens=38)
    lens_kf(cam, [(1, 36), (nf, 40)]); focus(cam, 1, nf, A['cuff'], g['face'])

def hypertension(nf, rfps, dur):
    """447.72-456.66: high pressure that stays high: cells pound through the artery at speed, the wall swells hard and
    fast, a patch of the lining darkens and roughens (damage, red warning tint growing), plaque bumps rise, and the
    small heart beside it strains with a red tint; the camera pushes in on the damaged wall."""
    reset(); stage(target=(0.5, 0.2, 0), key=(2.5, -6.0, 6.0), key_e=2800, fill_e=200, rim_e=560, spot=54, section=6)
    root = empty('HRoot', (0, 0, 0)); art = vessel_section(root, 'Art', kind='artery', loc=(0, 0, 0), length=8.0, r=0.72, cut_front=True)
    mr = mat_cell('h_cells', ox=1.0); rbc_flow('C', art['path'], 34, rfps, nf, 0.34, R=0.13, mat=mr, seed=6, spread=0.3, u_span=0.95)
    pulse_wall(art, 0.2, dur, rfps, period=0.6, amp=0.13); pressure_arrows(root, 'Push', 8, (-3.0, 3.0), art['r_in'], 0.2, dur, rfps, period=0.6, color=DANGER)
    # the damage patch: a keyable 'Damage' mask on the intima (darker, rough, DANGER emission) centred at x = 1.2 on the back wall
    mi = art['layers']['intima'].data.materials[0]; p = mi.node_tree.nodes.get('Principled BSDF'); nt = mi.node_tree; n = nt.nodes
    tc = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sep.inputs['Vector'])
    dx = n.new('ShaderNodeMath'); dx.operation = 'SUBTRACT'; dx.inputs[1].default_value = 1.2; nt.links.new(sep.outputs['X'], dx.inputs[0])
    d2 = n.new('ShaderNodeMath'); d2.operation = 'MULTIPLY'; nt.links.new(dx.outputs[0], d2.inputs[0]); nt.links.new(dx.outputs[0], d2.inputs[1])
    dz = n.new('ShaderNodeMath'); dz.operation = 'SUBTRACT'; dz.inputs[1].default_value = -0.35; nt.links.new(sep.outputs['Z'], dz.inputs[0])
    z2 = n.new('ShaderNodeMath'); z2.operation = 'MULTIPLY'; nt.links.new(dz.outputs[0], z2.inputs[0]); nt.links.new(dz.outputs[0], z2.inputs[1])
    z2s = n.new('ShaderNodeMath'); z2s.operation = 'MULTIPLY'; z2s.inputs[1].default_value = 2.5; nt.links.new(z2.outputs[0], z2s.inputs[0])
    dd = n.new('ShaderNodeMath'); dd.operation = 'ADD'; nt.links.new(d2.outputs[0], dd.inputs[0]); nt.links.new(z2s.outputs[0], dd.inputs[1])
    noise = n.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 6.0; noise.inputs['Detail'].default_value = 5.0; nt.links.new(tc.outputs['Object'], noise.inputs['Vector'])
    val = n.new('ShaderNodeValue'); val.name = 'Damage'; val.outputs[0].default_value = 0.0
    rad = n.new('ShaderNodeMath'); rad.operation = 'MULTIPLY_ADD'; rad.inputs[1].default_value = 2.2; rad.inputs[2].default_value = 0.05; nt.links.new(val.outputs[0], rad.inputs[0])
    mr_ = n.new('ShaderNodeMapRange'); mr_.clamp = True; nt.links.new(dd.outputs[0], mr_.inputs['Value']); nt.links.new(rad.outputs[0], mr_.inputs['From Min']); mr_.inputs['From Max'].default_value = 0.0
    nm = n.new('ShaderNodeMath'); nm.operation = 'MULTIPLY'; nt.links.new(mr_.outputs['Result'], nm.inputs[0]); nt.links.new(noise.outputs['Fac'], nm.inputs[1])
    mk = n.new('ShaderNodeMath'); mk.operation = 'MULTIPLY_ADD'; mk.inputs[1].default_value = 1.4; nt.links.new(nm.outputs[0], mk.inputs[0]); nt.links.new(mr_.outputs['Result'], mk.inputs[2])
    mk2 = n.new('ShaderNodeMath'); mk2.operation = 'MULTIPLY'; mk2.inputs[1].default_value = 0.5; nt.links.new(mk.outputs[0], mk2.inputs[0])
    base_link = next((l for l in nt.links if l.to_socket == p.inputs['Base Color']), None); base_from = base_link.from_socket if base_link else None
    mixc = n.new('ShaderNodeMix'); mixc.data_type = 'RGBA'; mixc.inputs[6].default_value = (*INTIMA, 1); mixc.inputs[7].default_value = (0.2, 0.05, 0.04, 1)
    if base_from is not None: nt.links.new(base_from, mixc.inputs[6])
    nt.links.new(mk2.outputs[0], mixc.inputs['Factor']); nt.links.new(mixc.outputs[2], p.inputs['Base Color'])
    rough = n.new('ShaderNodeMapRange'); rough.inputs['To Min'].default_value = 0.22; rough.inputs['To Max'].default_value = 0.85; nt.links.new(mk2.outputs[0], rough.inputs['Value']); nt.links.new(rough.outputs['Result'], p.inputs['Roughness'])
    em = n.new('ShaderNodeMath'); em.operation = 'MULTIPLY'; em.inputs[1].default_value = 1.2; nt.links.new(mk2.outputs[0], em.inputs[0]); nt.links.new(em.outputs[0], p.inputs['Emission Strength']); _inp(p, 'Emission Color', (*DANGER, 1))
    for f_, v in ((F(3.2, rfps), 0.0), (F(6.2, rfps), 1.0), (F(dur, rfps), 1.0)): val.outputs[0].default_value = v; val.outputs[0].keyframe_insert('default_value', frame=f_)
    mpl = mat_organic(P.mix(FAT, DANGER, 0.3), rough=0.6, sss=0.3, coat=0.1, name='plaque'); rnd = random.Random(5)
    for k in range(7):
        a = math.pi * 0.5 + rnd.uniform(-0.5, 0.5); rr = art['r_in'] * 1.0; c = (1.2 + rnd.uniform(-0.6, 0.6), rr * math.cos(a), -0.35 * 0 + rr * math.sin(a) - 0.0)
        c = (c[0], art['r_in'] * math.cos(a) * 0.98, art['r_in'] * math.sin(a) * 0.98)
        pl = meta_mesh(f'Plaque{k}', [(c, 0.11 * rnd.uniform(0.7, 1.3), (1.5, 0.7, 1.0))], res=0.02, mat=mpl); parent(pl, root)
        kf(pl, 'scale', F(3.2 + k * 0.2, rfps), (0.01, 0.01, 0.01)); kf(pl, 'scale', F(5.8 + k * 0.2, rfps), (1, 1, 1)); kf_ease(pl)
    hm = creature_heart(root, (4.7, 1.3, 0.9), 0.42, rfps, nf, dur, 0.6, 'StrainHeart')
    p2 = hm['mat'].node_tree.nodes.get('Principled BSDF'); _inp(p2, 'Emission Color', (*DANGER, 1))
    anchor('AnDamage', (1.2, 0.3, art['r_in'] * 0.6)); anchor('AnHeartH', (4.7, 0.2, 1.9))
    motes('Motes', 160, (1, 2, 0), (9, 4, 5), color=PLASMA, r=0.02, strength=3.5, seed=3, drift=0.35, rfps=rfps, nf=nf)
    backglow((1.0, 0.2, 0), P.mix(DANGER, OXY_LIT, 0.5), r=5.0, strength=0.4)
    fg_cells('FG', 5, (0, -7, 1), (0.5, 0.2, 0), rfps, nf, seed=19, R=0.09, dist=2.8, mat=mr)
    cam, tgt = cam_path([(0.0, (-2.5, -7.4, 2.0), (1.0, 0.2, 0.0)), (5.0, (0.4, -5.6, 1.6), (1.6, 0.3, 0.3)), (dur, (1.4, -5.0, 1.4), (2.2, 0.5, 0.5))], rfps, lens=40)
    lens_kf(cam, [(1, 38), (nf, 44)]); focus(cam, 1, nf, art['layers']['media'], hm['body'])

# ================================================================= OUTRO
def recap_orbit(nf, rfps, dur):
    """456.66-472.47: the recap: the cutaway double pump beating with its valves and cell streams, then the pulmonary loop
    (to the lungs and back) and the systemic loop (to the body and back) light up outside the heart as the camera
    completes a slow orbit."""
    h = cut_rig(nf, rfps, dur, section=0); cut_streams(h, nf, rfps, dur, n=18, speed=0.1); chamber_anchors(h['root'], 'An')
    lp = glow_sleeve('RecapPulm', [(-0.05, 0.62, 1.98), (-1.35, 0.85, 1.8), (-2.6, 1.0, 1.9), (-3.3, 1.2, 1.0), (-2.6, 1.15, 0.3), (-1.4, 1.0, 0.7), (-0.5, 0.85, 0.85)], 0.14, P.mix(DEOXY_LIT, OXY_LIT, 0.5), strength=0.0, alpha=0.45); parent(lp, h['root'])
    ls = glow_sleeve('RecapSys', [(1.0, 1.1, 2.1), (2.2, 1.3, 3.1), (3.6, 1.5, 1.6), (3.8, 1.5, -1.6), (2.6, 1.4, -3.6), (0.4, 1.2, -4.0), (-1.1, 0.7, -3.0)], 0.14, P.mix(OXY_LIT, DEOXY_LIT, 0.5), strength=0.0, alpha=0.45); parent(ls, h['root'])
    for g, t0 in ((lp, 462.14 - 456.66), (ls, 465.0 - 456.66)): key_input(g.data.materials[0], 'Emission Strength', [(F(t0, rfps), 0.0), (F(t0 + 1.2, rfps), 2.2), (F(dur, rfps), 1.8)]); hide_until(g, F(t0, rfps))
    mL = mat_lung('recap_lung', rim=True)
    for sgn in (-1, 1): parent(lung_lobe(f'RecapLung{sgn}', (sgn * 3.3, 1.6, 0.6), (1.4, 1.7, 2.6), mL, 3 + sgn), h['root'])
    fg_cells('FG', 5, (0, -9, 0.5), (0, 0, -0.2), rfps, nf, seed=20, R=0.08, dist=3.4)
    cam, tgt = cam_orbit((0.05, 0.3, -0.1), 8.0, 0.8, -34, 30, 0.0, dur, rfps, lens=42, push=9.5, tilt=1.4)
    focus(cam, 1, nf, h['body'], h['body'])
