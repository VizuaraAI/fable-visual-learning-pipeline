"""Visual Learning house-style asset kit for Blender (bpy). Headless-safe.
Everything here is built from primitives so it runs on any machine with Blender >= 4.2.
Look: dark void stage, one glossy hero prop, alpha-blended 'glass', emissive flame, bloom via compositor glare.
"""
import bpy, math, random, json, os
from mathutils import Vector

FPS = 24
RES = tuple(int(v) for v in os.environ.get('VL_RES', '1280x720').split('x'))
LOGICAL = (1280, 720)          # anchors are always exported in this space; the compositor scales them

# ----------------------------------------------------------------- scene setup
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.film_transparent = False
    sc.render.filter_size = 1.5
    if os.environ.get('VL_ENGINE', 'EEVEE').upper() == 'CYCLES':
        sc.render.engine = 'CYCLES'
        cy = sc.cycles
        try:
            prefs = bpy.context.preferences.addons['cycles'].preferences
            for dev_type in ((os.environ.get('VL_DEVICE', 'OPTIX'), 'CUDA') if os.environ.get('VL_DEVICE', 'OPTIX') != 'CUDA' else ('CUDA',)):
                try:
                    prefs.compute_device_type = dev_type; prefs.get_devices()
                    if any(d.type == dev_type for d in prefs.devices): break
                except Exception: continue
            for d in prefs.devices: d.use = (d.type != 'CPU')
            print('cycles devices:', [(d.name, d.type, d.use) for d in prefs.devices])
        except Exception as e: print('cycles device setup:', e)
        cy.device = 'GPU'; cy.samples = int(os.environ.get('VL_SAMPLES', '128')); cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.015
        cy.use_denoising = os.environ.get('VL_DENOISE', '1') == '1'
        for dn in ('OPENIMAGEDENOISE', 'OPTIX'):      # OptiX denoiser needs the driver's nvoptix.bin, absent in containers
            try: cy.denoiser = dn; break
            except Exception: continue
        for attr, val in (('denoising_use_gpu', os.environ.get('VL_DENOISE_GPU', '1') == '1'), ('denoising_input_passes', 'RGB_ALBEDO_NORMAL'), ('denoising_prefilter', 'ACCURATE')):
            try: setattr(cy, attr, val)
            except Exception: pass
        cy.max_bounces = 8; cy.transparent_max_bounces = 48; cy.glossy_bounces = 4; cy.diffuse_bounces = 3; cy.transmission_bounces = 8; cy.caustics_reflective = False; cy.caustics_refractive = False
        try: cy.use_light_tree = True
        except Exception: pass
        try: sc.render.use_persistent_data = True
        except Exception: pass
        if os.environ.get('VL_MBLUR', '0') == '1':
            sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
        try: cy.volume_bounces = 2; cy.volume_max_steps = 512; cy.volume_step_rate = 0.5
        except Exception: pass
    else:
        sc.render.engine = 'BLENDER_EEVEE'
    ee = sc.eevee
    for attr, val in [('taa_render_samples', int(os.environ.get('VL_SAMPLES', '16'))), ('use_shadows', True), ('shadow_ray_count', 2),
                      ('shadow_step_count', 3), ('use_raytracing', False), ('use_volumetric_shadows', False),
                      ('use_bloom', True), ('bloom_intensity', 0.06), ('bloom_threshold', 1.2)]:
        try: setattr(ee, attr, val)
        except Exception: pass
    try: sc.view_settings.view_transform = 'Filmic'
    except Exception:
        try: sc.view_settings.view_transform = 'AgX'
        except Exception: pass
    sc.view_settings.look = 'None'
    for lk in ('AgX - Medium High Contrast', 'Medium High Contrast'):
        try: sc.view_settings.look = lk; break
        except Exception: continue
    world(0.0025, 0.004, 0.009)
    bloom()
    if os.environ.get('VL_ENGINE', 'EEVEE').upper() == 'CYCLES' and os.environ.get('VL_GRADE', '1') == '1': grade()
    return sc

def world(r, g, b, strength=1.0):
    sc = bpy.context.scene
    w = bpy.data.worlds.new('World') if sc.world is None else sc.world
    sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes.get('Background')
    bg.inputs[0].default_value = (r, g, b, 1); bg.inputs[1].default_value = strength

def bloom(threshold=1.0, strength=0.32, size=0.5):
    """Compositor glare (Bloom). Blender 5.x: node tree lives in scene.compositing_node_group, glare options are input sockets.
    Any failure -> compositor detached, so a broken tree can never black out a render."""
    sc = bpy.context.scene
    try:
        if hasattr(sc, 'compositing_node_group'):
            nt = bpy.data.node_groups.new('VLComp', 'CompositorNodeTree')
            try: nt.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
            except Exception as e: print('iface', e)
            out = nt.nodes.new('NodeGroupOutput')
        else:
            sc.use_nodes = True; nt = sc.node_tree
            for n in list(nt.nodes): nt.nodes.remove(n)
            out = nt.nodes.new('CompositorNodeComposite')
        rl = nt.nodes.new('CompositorNodeRLayers'); gl = nt.nodes.new('CompositorNodeGlare')
        ok = False
        for cand in ('Bloom', 'BLOOM', 'Fog Glow', 'FOG_GLOW'):
            try:
                if 'Type' in gl.inputs: gl.inputs['Type'].default_value = cand
                else: gl.glare_type = cand
                ok = True; break
            except Exception: continue
        if not ok: raise RuntimeError('no glare type')
        for name, val in (('Threshold', threshold), ('Strength', strength), ('Size', size), ('Quality', 'Medium')):
            try:
                if name in gl.inputs: gl.inputs[name].default_value = val
            except Exception as e: print('glare input', name, e)
        nt.links.new(rl.outputs['Image'], gl.inputs['Image']); nt.links.new(gl.outputs['Image'], out.inputs[0])
        if hasattr(sc, 'compositing_node_group'): sc.compositing_node_group = nt
        sc.render.use_compositing = True
        for attr, val in (('compositor_device', os.environ.get('VL_COMP_DEVICE', 'CPU')), ('compositor_precision', 'FULL')):
            try: setattr(sc.render, attr, val)          # GPU compositor needs a display context: headless containers segfault
            except Exception: pass
        print('bloom OK')
    except Exception as e:
        print('bloom setup skipped:', e)
        try:
            if hasattr(sc, 'compositing_node_group'): sc.compositing_node_group = None
            else: sc.use_nodes = False
        except Exception: pass

def set_range(n_frames):
    sc = bpy.context.scene; sc.frame_start = 1; sc.frame_end = max(1, n_frames)

# ----------------------------------------------------------------- materials
def _principled(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    return m, p

def _inp(p, name, val):
    if name in p.inputs:
        try: p.inputs[name].default_value = val
        except Exception: pass

def mat_plastic(color, rough=0.35, spec=0.5, name='plastic', coat=0.0, sss=0.0):
    m, p = _principled(name)
    _inp(p, 'Base Color', (*color, 1)); _inp(p, 'Roughness', rough); _inp(p, 'Coat Weight', coat)
    _inp(p, 'Subsurface Weight', sss)
    return m

def mat_metal(color=(0.75, 0.75, 0.78), rough=0.3, name='metal', metallic=1.0):
    m, p = _principled(name)
    _inp(p, 'Base Color', (*color, 1)); _inp(p, 'Roughness', rough); _inp(p, 'Metallic', metallic)
    return m

def mat_glass(tint=(0.55, 0.8, 1.0), alpha=0.16, rough=0.08, name='glass', emit=0.0):
    """Alpha-blended glass: what the reference actually looks like (transparent tint + hot highlights)."""
    m, p = _principled(name)
    _inp(p, 'Base Color', (*tint, 1)); _inp(p, 'Roughness', rough); _inp(p, 'Alpha', alpha)
    _inp(p, 'Specular IOR Level', 0.8); _inp(p, 'Coat Weight', 0.6)
    if emit: _inp(p, 'Emission Color', (*tint, 1)); _inp(p, 'Emission Strength', emit)
    for attr, val in [('surface_render_method', 'BLENDED'), ('blend_method', 'BLEND'), ('use_backface_culling', False),
                      ('show_transparent_back', True), ('use_transparency_overlap', True)]:
        try: setattr(m, attr, val)
        except Exception: pass
    try: m.shadow_method = 'NONE'
    except Exception: pass
    try: m.use_transparent_shadow = True
    except Exception: pass
    return m

def mat_liquid(color, alpha=0.75, name='liquid', emit=0.0):
    m = mat_glass(tint=color, alpha=alpha, rough=0.15, name=name, emit=emit)
    return m

def mat_emit(color, strength=8.0, name='emit', alpha=1.0):
    m, p = _principled(name)
    _inp(p, 'Base Color', (0, 0, 0, 1)); _inp(p, 'Emission Color', (*color, 1)); _inp(p, 'Emission Strength', strength)
    if alpha < 1:
        _inp(p, 'Alpha', alpha)
        for attr, val in [('surface_render_method', 'BLENDED'), ('blend_method', 'BLEND')]:
            try: setattr(m, attr, val)
            except Exception: pass
    return m

def mat_wood(name='wood'):
    """Warm plank floor: long planks along X, fine grain streaks, mild tone variation. The key spot makes the pool."""
    m, p = _principled(name); nt = m.node_tree; n = nt.nodes
    tex = n.new('ShaderNodeTexCoord')
    planks = n.new('ShaderNodeTexBrick'); planks.inputs['Scale'].default_value = 1.0
    planks.inputs['Color1'].default_value = (0.50, 0.28, 0.12, 1); planks.inputs['Color2'].default_value = (0.40, 0.22, 0.09, 1)
    planks.inputs['Mortar'].default_value = (0.12, 0.06, 0.025, 1); planks.inputs['Mortar Size'].default_value = 0.012
    try: planks.inputs['Brick Width'].default_value = 6.0; planks.inputs['Row Height'].default_value = 0.9
    except Exception: pass
    try: planks.offset = 0.5; planks.offset_frequency = 2
    except Exception: pass
    mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.25, 6.0, 1.0)
    grain = n.new('ShaderNodeTexNoise'); grain.inputs['Scale'].default_value = 4.0; grain.inputs['Detail'].default_value = 5; grain.inputs['Roughness'].default_value = 0.6
    ramp = n.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[0].color = (0.75, 0.75, 0.75, 1); ramp.color_ramp.elements[1].position = 0.65; ramp.color_ramp.elements[1].color = (1.15, 1.1, 1.05, 1)
    mix = n.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 1.0
    nt.links.new(tex.outputs['Object'], planks.inputs['Vector']); nt.links.new(tex.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], grain.inputs['Vector'])
    nt.links.new(grain.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(planks.outputs['Color'], mix.inputs[6]); nt.links.new(ramp.outputs['Color'], mix.inputs[7])
    nt.links.new(mix.outputs[2], p.inputs['Base Color'])
    _inp(p, 'Roughness', 0.38); _inp(p, 'Specular IOR Level', 0.45)
    return m

def mat_soil(name='soil'):
    m, p = _principled(name); nt = m.node_tree; n = nt.nodes
    tex = n.new('ShaderNodeTexCoord'); noise = n.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 14; noise.inputs['Detail'].default_value = 8
    vor = n.new('ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = 5.0; vor.feature = 'DISTANCE_TO_EDGE'
    ramp = n.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color = (0.30, 0.20, 0.09, 1); ramp.color_ramp.elements[1].color = (0.62, 0.45, 0.24, 1)
    mix = n.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 0.6
    cr2 = n.new('ShaderNodeValToRGB'); cr2.color_ramp.elements[0].position = 0.0; cr2.color_ramp.elements[0].color = (0.25, 0.15, 0.06, 1); cr2.color_ramp.elements[1].position = 0.08; cr2.color_ramp.elements[1].color = (1, 1, 1, 1)
    nt.links.new(tex.outputs['Object'], noise.inputs['Vector']); nt.links.new(tex.outputs['Object'], vor.inputs['Vector'])
    nt.links.new(noise.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(vor.outputs['Distance'], cr2.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], mix.inputs[6]); nt.links.new(cr2.outputs['Color'], mix.inputs[7]); nt.links.new(mix.outputs[2], p.inputs['Base Color'])
    _inp(p, 'Roughness', 0.9)
    return m

def mat_flame(name='flame'):
    """Stylised flame: emission gradient from white-yellow core to orange rim, alpha-faded edges; noise animated via driver."""
    m, p = _principled(name); nt = m.node_tree; n = nt.nodes
    tex = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ')
    grad = n.new('ShaderNodeValToRGB'); grad.color_ramp.elements[0].color = (1.0, 0.22, 0.02, 1); grad.color_ramp.elements[1].color = (1.0, 0.8, 0.35, 1)
    grad.color_ramp.elements[1].position = 0.7
    mapr = n.new('ShaderNodeMapRange'); mapr.inputs['From Min'].default_value = -1.0; mapr.inputs['From Max'].default_value = 0.6
    nt.links.new(tex.outputs['Generated'], sep.inputs['Vector'])
    # generated coords are 0..1; use z for gradient (bottom = hot yellow-white, top = orange)
    mr = n.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.0; mr.inputs['From Max'].default_value = 1.0; mr.inputs['To Min'].default_value = 1.0; mr.inputs['To Max'].default_value = 0.0
    nt.links.new(sep.outputs['Z'], mr.inputs['Value']); nt.links.new(mr.outputs['Result'], grad.inputs['Fac'])
    nt.links.new(grad.outputs['Color'], p.inputs['Emission Color'])
    _inp(p, 'Emission Strength', 3.2); _inp(p, 'Base Color', (0, 0, 0, 1))
    # fresnel-ish alpha so the silhouette is soft
    lw = n.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.35
    inv = n.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    nt.links.new(lw.outputs['Facing'], inv.inputs[1])
    pw = n.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 0.6
    nt.links.new(inv.outputs[0], pw.inputs[0]); nt.links.new(pw.outputs[0], p.inputs['Alpha'])
    for attr, val in [('surface_render_method', 'BLENDED'), ('blend_method', 'BLEND')]:
        try: setattr(m, attr, val)
        except Exception: pass
    try: m.shadow_method = 'NONE'
    except Exception: pass
    return m

# ----------------------------------------------------------------- helpers
def obj_add(kind, name, **kw):
    getattr(bpy.ops.mesh, f'primitive_{kind}_add')(**kw)
    o = bpy.context.object; o.name = name
    return o

def smooth(o, auto=True):
    try:
        bpy.context.view_layer.objects.active = o; o.select_set(True)
        bpy.ops.object.shade_smooth()
        if auto:
            try: bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
            except Exception:
                try: bpy.ops.object.shade_auto_smooth(angle=math.radians(35))
                except Exception: pass
        o.select_set(False)
    except Exception: pass

def setmat(o, m):
    o.data.materials.clear(); o.data.materials.append(m)

def kf(o, prop, frame, value):
    setattr(o, prop, value); o.keyframe_insert(data_path=prop, frame=frame)

def _fcurves(o):
    """All fcurves of an object's action, across the legacy and the slotted (Blender >= 4.4) action layouts."""
    if not (o.animation_data and o.animation_data.action): return []
    act = o.animation_data.action
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

def kf_lin(o):
    for fc in _fcurves(o):
        for k in fc.keyframe_points: k.interpolation = 'LINEAR'

def kf_ease(o, mode='EASE_IN_OUT'):
    for fc in _fcurves(o):
        for k in fc.keyframe_points: k.interpolation = 'BEZIER'; k.easing = mode

def empty(name, loc=(0, 0, 0)):
    e = bpy.data.objects.new(name, None); bpy.context.collection.objects.link(e); e.location = loc; return e

def camera(loc=(0, -9, 3), target=(0, 0, 1), lens=50):
    cam_data = bpy.data.cameras.new('Camera'); cam = bpy.data.objects.new('Camera', cam_data)
    bpy.context.collection.objects.link(cam); bpy.context.scene.camera = cam
    cam.location = loc; cam.data.lens = lens; cam.data.clip_end = 500
    tgt = empty('CamTarget', target)
    c = cam.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
    cam['target'] = tgt.name
    if os.environ.get('VL_DOF', '0') == '1':
        cam.data.dof.use_dof = True; cam.data.dof.focus_object = tgt; cam.data.dof.aperture_fstop = 5.6
    return cam, tgt

def dolly(cam, tgt, f0, f1, loc0, loc1, t0=None, t1=None, ease=True):
    kf(cam, 'location', f0, loc0); kf(cam, 'location', f1, loc1)
    if t0 is not None: kf(tgt, 'location', f0, t0); kf(tgt, 'location', f1, t1 if t1 is not None else t0)
    (kf_ease if ease else kf_lin)(cam); (kf_ease if ease else kf_lin)(tgt)

def light(kind, loc, energy, color=(1, 1, 1), name='Light', size=2.0, spot=60, blend=0.5, rot=None, target=None):
    d = bpy.data.lights.new(name, kind); d.energy = energy; d.color = color
    if kind == 'SPOT': d.spot_size = math.radians(spot); d.spot_blend = blend
    if kind == 'AREA': d.size = size
    try: d.shadow_soft_size = ((0.05 if kind == 'POINT' else 0.9) if os.environ.get('VL_ENGINE', 'EEVEE').upper() == 'CYCLES' else 0.6)   # Cycles draws a point light's radius as a visible sphere (visible_camera=False does not hide it in 5.2)
    except Exception: pass
    o = bpy.data.objects.new(name, d); bpy.context.collection.objects.link(o); o.location = loc
    try: o.visible_camera = False        # Cycles otherwise draws point lights as bright spheres of their radius
    except Exception: pass
    if target is not None:
        t = target if not isinstance(target, tuple) else empty(name + '_tgt', target)
        c = o.constraints.new('TRACK_TO'); c.target = t; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
    elif rot is not None: o.rotation_euler = rot
    return o

def studio(key=(2.5, -4.0, 7.5), key_e=2600, fill_e=60, rim_e=220, target=(0, 0, 0.8), spot=42, blend=0.85):
    """House lighting: one warm key spot pooled on the hero, a very dim cool fill, a cool rim from behind."""
    k = light('SPOT', key, key_e, (1.0, 0.95, 0.86), 'Key', spot=spot, blend=blend, target=target)
    f = light('AREA', (-6, -5, 4), fill_e, (0.7, 0.8, 1.0), 'Fill', size=6, target=target)
    r = light('AREA', (1.5, 6, 5), rim_e, (0.65, 0.8, 1.0), 'Rim', size=3, target=target)
    return k, f, r

# ----------------------------------------------------------------- props
def floor_wood(size=40):
    o = obj_add('plane', 'Floor', size=size); setmat(o, mat_wood()); return o

def light_cone(top=(0, 0, 9), base=(0, 0, 0), r_top=0.35, r_base=3.2, alpha=0.10, color=(0.75, 0.85, 1.0)):
    """The reference's visible 'projector' light cone is a translucent cone mesh, not volumetrics."""
    top, base = Vector(top), Vector(base); d = base - top; h = d.length
    o = obj_add('cone', 'LightCone', radius1=r_base, radius2=r_top, depth=h, vertices=128)
    o.location = (top + base) / 2
    # orient: cone axis z -> from base toward top; rotate so -z points to base
    o.rotation_euler = (-d).to_track_quat('Z', 'Y').to_euler()
    if os.environ.get('VL_ENGINE', 'EEVEE').upper() == 'CYCLES':
        # real god rays: a scattering volume inside the cone, lit by a spot sitting at the apex
        m = bpy.data.materials.new('cone_vol'); m.use_nodes = True; nt = m.node_tree
        for n in list(nt.nodes): nt.nodes.remove(n)
        out = nt.nodes.new('ShaderNodeOutputMaterial'); vol = nt.nodes.new('ShaderNodeVolumeScatter')
        vol.inputs['Density'].default_value = 0.045 * (alpha / 0.09); vol.inputs['Anisotropy'].default_value = 0.35; vol.inputs['Color'].default_value = (*color, 1)
        nt.links.new(vol.outputs['Volume'], out.inputs['Volume']); setmat(o, m); smooth(o)
        try: o.visible_shadow = False
        except Exception: pass
        ang = 2 * math.atan2(r_base, h)
        light('SPOT', tuple(top), 2600 * (h / 10.0) ** 2, color, 'ConeSpot', spot=math.degrees(ang) * 1.05, blend=0.4, target=tuple(base))
    else:
        m = mat_emit(color, strength=0.9, name='cone', alpha=alpha); setmat(o, m); smooth(o)
    return o

def soil_disc(r=3.0, loc=(0, 0, 0)):
    o = obj_add('cylinder', 'Soil', radius=r, depth=0.35, vertices=128, location=(loc[0], loc[1], loc[2] - 0.175))
    setmat(o, mat_soil()); return o

def plant(loc=(0, 0, 0), h=2.2, leaves=14, seed=3):
    rnd = random.Random(seed)
    stem_m = mat_plastic((0.18, 0.42, 0.10), rough=0.5, name='stem'); leaf_m = mat_plastic((0.12, 0.55, 0.12), rough=0.45, name='leaf', sss=0.2)
    parts = []
    stem = obj_add('cylinder', 'Stem', radius=0.045, depth=h, vertices=24, location=(loc[0], loc[1], loc[2] + h / 2)); setmat(stem, stem_m); parts.append(stem)
    for i in range(leaves):
        z = loc[2] + 0.35 + (h - 0.4) * (i + 0.5) / leaves; ang = i * 2.399 + rnd.random() * 0.4
        br_len = 0.55 + rnd.random() * 0.35
        br = obj_add('cylinder', f'Branch{i}', radius=0.02, depth=br_len, vertices=16)
        br.location = (loc[0] + math.cos(ang) * br_len / 2, loc[1] + math.sin(ang) * br_len / 2, z)
        br.rotation_euler = (math.radians(70), 0, ang + math.pi / 2); setmat(br, stem_m); parts.append(br)
        for j in range(3):
            lf = obj_add('uv_sphere', f'Leaf{i}_{j}', radius=0.19, segments=32, ring_count=16)
            t = 0.5 + 0.25 * j
            lf.location = (loc[0] + math.cos(ang) * br_len * t, loc[1] + math.sin(ang) * br_len * t, z + 0.2 * t + 0.04 * j)
            lf.scale = (1.0, 0.55, 0.12); lf.rotation_euler = (0.2, 0, ang + (j - 1) * 0.9); setmat(lf, leaf_m); smooth(lf); parts.append(lf)
    return parts

def mannequin(loc=(0, 0, 0), h=3.6, mat=None):
    """Red translucent human silhouette from capsules (the reference uses a translucent red body)."""
    m = mat or mat_emit((1.0, 0.10, 0.04), strength=2.2, name='body', alpha=0.30)
    u = h / 8.0; x, y, z = loc; parts = []
    def cap(name, r, length, pos, rot=(0, 0, 0)):
        o = obj_add('cylinder', name, radius=r, depth=length, vertices=48); o.location = pos; o.rotation_euler = rot
        try: mod = o.modifiers.new('bevel', 'BEVEL'); mod.width = r * 0.95; mod.segments = 12
        except Exception: pass
        setmat(o, m); smooth(o); parts.append(o); return o
    head = obj_add('uv_sphere', 'Head', radius=0.55 * u, segments=48, ring_count=24, location=(x, y, z + 7.4 * u)); setmat(head, m); smooth(head); parts.append(head)
    cap('Neck', 0.18 * u, 0.5 * u, (x, y, z + 6.75 * u))
    cap('Torso', 0.75 * u, 2.6 * u, (x, y, z + 5.3 * u)); cap('Hips', 0.7 * u, 0.9 * u, (x, y, z + 3.8 * u))
    for s in (-1, 1):
        cap(f'UpperArm{s}', 0.22 * u, 1.5 * u, (x + s * 1.05 * u, y, z + 5.6 * u), (0, math.radians(8 * s), 0))
        cap(f'LowerArm{s}', 0.19 * u, 1.5 * u, (x + s * 1.2 * u, y, z + 4.15 * u), (0, math.radians(4 * s), 0))
        cap(f'Thigh{s}', 0.32 * u, 2.0 * u, (x + s * 0.4 * u, y, z + 2.5 * u))
        cap(f'Shin{s}', 0.24 * u, 1.9 * u, (x + s * 0.42 * u, y, z + 0.9 * u))
        ft = obj_add('cube', f'Foot{s}', size=1); ft.scale = (0.28 * u, 0.5 * u, 0.12 * u); ft.location = (x + s * 0.42 * u, y - 0.15 * u, z + 0.06 * u); setmat(ft, m); parts.append(ft)
    return parts

def platform(loc=(0, 0, 0), size=6.0, color=(0.03, 0.28, 0.65)):
    o = obj_add('cube', 'Platform', size=1); o.scale = (size, size * 0.7, 0.08); o.location = (loc[0], loc[1], loc[2] - 0.04)
    setmat(o, mat_emit(color, strength=0.45, name='platform')); return o

def candle(loc=(0, 0, 0), r=0.32, h=2.6, wick=0.16):
    wax = mat_plastic((0.9, 0.89, 0.84), rough=0.3, name='wax', sss=0.6 if os.environ.get('VL_ENGINE', 'EEVEE').upper() == 'CYCLES' else 0.35)
    body = obj_add('cylinder', 'Candle', radius=r, depth=h, vertices=96, location=(loc[0], loc[1], loc[2] + h / 2)); setmat(body, wax); smooth(body)
    try: mod = body.modifiers.new('bevel', 'BEVEL'); mod.width = 0.04; mod.segments = 8
    except Exception: pass
    base = obj_add('cylinder', 'CandleBase', radius=r * 1.35, depth=0.06, vertices=96, location=(loc[0], loc[1], loc[2] + 0.03)); setmat(base, mat_metal((0.6, 0.6, 0.62), rough=0.35, name='base')); smooth(base)
    w = obj_add('cylinder', 'Wick', radius=0.018, depth=wick, vertices=16, location=(loc[0], loc[1], loc[2] + h + wick / 2 - 0.02)); setmat(w, mat_plastic((0.05, 0.04, 0.03), name='wick'))
    return body, w

def flame(loc, scale=1.0, name='Flame', strength=3.2):
    """Teardrop flame + a warm point light. Flicker is keyframed in flicker()."""
    o = obj_add('uv_sphere', name, radius=0.16 * scale, segments=48, ring_count=32, location=(loc[0], loc[1], loc[2] + 0.28 * scale))
    o.scale = (1, 1, 2.1)
    # taper the top: shrink upper vertices
    me = o.data
    for v in me.vertices:
        if v.co.z > 0: v.co.x *= (1 - 0.85 * (v.co.z / 0.16 / 1.0) ** 1.5) if v.co.z < 0.16 else 0.15; v.co.y *= (1 - 0.85 * (v.co.z / 0.16) ** 1.5) if v.co.z < 0.16 else 0.15
    m = mat_flame(name=f'{name}_mat'); setmat(o, m); smooth(o)
    core = obj_add('uv_sphere', name + 'Core', radius=0.05 * scale, segments=32, ring_count=16, location=(loc[0], loc[1], loc[2] + 0.16 * scale)); core.scale = (1, 1, 1.5)
    setmat(core, mat_emit((1.0, 0.85, 0.5), strength=strength * 1.4, name=name + '_core')); smooth(core)
    core.parent = o; core.matrix_parent_inverse = o.matrix_world.inverted()
    L = light('POINT', (loc[0], loc[1], loc[2] + 0.45 * scale), 45 * scale, (1.0, 0.62, 0.25), name + 'Light')
    L.parent = o; L.matrix_parent_inverse = o.matrix_world.inverted()
    try: L.data.shadow_soft_size = 0.25
    except Exception: pass
    return o, L

def flicker(fl, f0, f1, seed=1, amp=0.12, step=3):
    rnd = random.Random(seed); base = tuple(fl.scale)
    for f in range(f0, f1 + 1, step):
        s = 1 + rnd.uniform(-amp, amp); kf(fl, 'scale', f, (base[0] * (1 + rnd.uniform(-amp, amp) * 0.5), base[1] * (1 + rnd.uniform(-amp, amp) * 0.5), base[2] * s))
        kf(fl, 'rotation_euler', f, (rnd.uniform(-0.08, 0.08), rnd.uniform(-0.08, 0.08), 0))

def dome(r=3.2, loc=(0, 0, 0), alpha=0.18, tint=(0.35, 0.75, 1.0)):
    o = obj_add('uv_sphere', 'Dome', radius=r, segments=160, ring_count=80, location=loc)
    # cut lower half
    me = o.data
    import bmesh
    bm = bmesh.new(); bm.from_mesh(me)
    geom = [v for v in bm.verts if v.co.z < -0.01]
    bmesh.ops.delete(bm, geom=geom, context='VERTS'); bm.to_mesh(me); bm.free()
    setmat(o, mat_glass(tint, alpha=alpha, name='dome')); smooth(o)
    return o

def jar(r=1.3, h=3.6, loc=(0, 0, 0), alpha=0.22):
    o = obj_add('cylinder', 'Jar', radius=r, depth=h, vertices=128, location=(loc[0], loc[1], loc[2] + h / 2))
    setmat(o, mat_glass((0.8, 0.9, 1.0), alpha=alpha, name='jar')); smooth(o)
    try: mod = o.modifiers.new('bevel', 'BEVEL'); mod.width = 0.25; mod.segments = 16
    except Exception: pass
    return o

def _resample_profile(profile, n=48):
    """Catmull-Rom resample of a coarse (r, z) profile so lathed vessels have smooth curved silhouettes."""
    P = [profile[0]] + list(profile) + [profile[-1]]
    if len(profile) < 3: return list(profile)
    out = []
    segs = len(profile) - 1
    for i in range(segs):
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        steps = max(2, int(round(n / segs)))
        for k in range(steps):
            t = k / steps; t2, t3 = t * t, t * t * t
            r = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            z = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((max(0.0, r), z))
    out.append(profile[-1])
    return out

def glass_vessel(name, profile, loc=(0, 0, 0), verts=128, alpha=0.2, tint=(0.6, 0.85, 1.0), thickness=0.0, resample=True):
    """Lathe a vessel from (radius, z) profile pairs -> test tubes, beakers, dishes. Profiles are spline-resampled."""
    import bmesh
    if resample: profile = _resample_profile(profile)
    me = bpy.data.meshes.new(name); o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    bm = bmesh.new(); rings = []
    for (r, z) in profile:
        ring = []
        for i in range(verts):
            a = 2 * math.pi * i / verts
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        rings.append(ring)
    bm.verts.ensure_lookup_table()
    for a, b in zip(rings[:-1], rings[1:]):
        for i in range(verts):
            bm.faces.new((a[i], a[(i + 1) % verts], b[(i + 1) % verts], b[i]))
    if profile[0][0] < 1e-4: pass
    else:
        try: bm.faces.new(rings[0])
        except Exception: pass
    bm.to_mesh(me); bm.free(); o.location = loc
    setmat(o, mat_glass(tint, alpha=alpha, name=name + '_glass')); smooth(o)
    return o

def liquid_column(name, profile, loc=(0, 0, 0), color=(0.1, 0.2, 0.9), alpha=0.8, verts=128, emit=0.0):
    o = glass_vessel(name, profile, loc, verts=verts, alpha=alpha, tint=color)
    setmat(o, mat_liquid(color, alpha=alpha, name=name + '_liq', emit=emit))
    # cap the top
    import bmesh
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    top_z = max(v.co.z for v in bm.verts); top = [v for v in bm.verts if abs(v.co.z - top_z) < 1e-5]
    try: bm.faces.new(top)
    except Exception: pass
    bm.to_mesh(o.data); bm.free()
    return o

def test_tube(loc=(0, 0, 0), r=0.32, h=3.2, alpha=0.22, name='TestTube'):
    prof = [(0.0, 0.0), (0.18 * r, 0.02), (0.6 * r, 0.09), (0.9 * r, 0.22), (r, 0.42), (r, h - 0.25), (r * 1.12, h - 0.1), (r * 1.15, h)]
    return glass_vessel(name, prof, loc, alpha=alpha)

def tube_liquid(loc, r, level, color, alpha=0.85, name='TubeLiquid', emit=0.0):
    r *= 0.9
    prof = [(0.0, 0.03), (0.18 * r, 0.05), (0.6 * r, 0.12), (0.9 * r, 0.24), (r, 0.42), (r, level)]
    return liquid_column(name, prof, loc, color=color, alpha=alpha, emit=emit)

def beaker(loc=(0, 0, 0), r=1.2, h=1.7, alpha=0.2, name='Beaker'):
    prof = [(0.0, 0.0), (r * 0.98, 0.0), (r, 0.05), (r, h - 0.15), (r * 1.06, h)]
    return glass_vessel(name, prof, loc, alpha=alpha)

def beaker_liquid(loc, r, level, color, alpha=0.85, name='BeakerLiquid', emit=0.0):
    prof = [(0.0, 0.03), (r * 0.93, 0.03), (r * 0.93, level)]
    return liquid_column(name, prof, loc, color=color, alpha=alpha, emit=emit)

def watch_glass(loc=(0, 0, 0), r=1.4, name='WatchGlass'):
    prof = [(0.0, 0.0), (r * 0.5, 0.06), (r * 0.85, 0.2), (r, 0.36)]
    o = glass_vessel(name, prof, loc, alpha=0.3, tint=(0.55, 0.8, 1.0)); return o

def china_dish(loc=(0, 0, 0), r=2.2, name='ChinaDish'):
    prof = [(0.0, 0.0), (r * 0.35, 0.05), (r * 0.7, 0.45), (r * 0.92, 1.05), (r, 1.45)]
    o = glass_vessel(name, prof, loc, alpha=0.22, tint=(0.42, 0.7, 1.0)); return o

def granules(center, n, spread, r, color, seed=7, name='Gran', emit=0.0, flat=0.5):
    rnd = random.Random(seed); m = mat_plastic(color, rough=0.5, name=name + '_m'); out = []
    if emit: m = mat_emit(color, strength=emit, name=name + '_m')
    for i in range(n):
        a = rnd.random() * 2 * math.pi; d = spread * math.sqrt(rnd.random())
        o = obj_add('uv_sphere', f'{name}{i}', radius=r * rnd.uniform(0.7, 1.3), segments=24, ring_count=12)
        o.location = (center[0] + d * math.cos(a), center[1] + d * math.sin(a), center[2] + r * flat * (1 - (d / spread) ** 2) * rnd.uniform(0.3, 1.0))
        o.scale = (rnd.uniform(0.8, 1.2), rnd.uniform(0.8, 1.2), rnd.uniform(0.7, 1.0))
        o.rotation_euler = (rnd.random() * 3, rnd.random() * 3, rnd.random() * 3); setmat(o, m); smooth(o, auto=False); out.append(o)
    return out, m

def nail(loc=(0, 0, 0), L=2.4, r=0.055, mat=None, name='Nail'):
    m = mat or mat_metal((0.8, 0.8, 0.82), rough=0.35, name=name + '_m')
    shaft = obj_add('cylinder', name, radius=r, depth=L * 0.86, vertices=32, location=(loc[0], loc[1], loc[2] + L * 0.14 + L * 0.43)); setmat(shaft, m); smooth(shaft)
    tip = obj_add('cone', name + 'Tip', radius1=r, radius2=0.0, depth=L * 0.14, vertices=32, location=(loc[0], loc[1], loc[2] + L * 0.07)); tip.rotation_euler = (math.pi, 0, 0); setmat(tip, m); smooth(tip)
    head = obj_add('cylinder', name + 'Head', radius=r * 2.2, depth=0.05, vertices=48, location=(loc[0], loc[1], loc[2] + L)); setmat(head, m); smooth(head)
    for p in (tip, head): p.parent = shaft; p.matrix_parent_inverse = shaft.matrix_world.inverted()
    return shaft, m

def rod(loc, L=2.6, r=0.18, mat=None, name='Rod'):
    m = mat or mat_metal((0.8, 0.8, 0.82), rough=0.35, name=name + '_m')
    o = obj_add('cylinder', name, radius=r, depth=L, vertices=64, location=(loc[0], loc[1], loc[2] + L / 2)); setmat(o, m); smooth(o)
    try: mod = o.modifiers.new('bevel', 'BEVEL'); mod.width = 0.05; mod.segments = 8
    except Exception: pass
    return o

def ring(loc, R=0.6, r=0.12, mat=None, name='Ring'):
    m = mat or mat_metal((0.8, 0.8, 0.82), rough=0.35, name=name + '_m')
    o = obj_add('torus', name, major_radius=R, minor_radius=r, major_segments=96, minor_segments=32, location=loc); setmat(o, m); smooth(o); return o

def tongs(loc=(0, 0, 0), L=3.2, name='Tongs'):
    """Crucible tongs: two bent arms joined at a pivot, jaws at the tip. Built from cylinders."""
    m = mat_metal((0.85, 0.85, 0.87), rough=0.28, name='tongs_m'); parts = []
    root = empty(name, loc)
    def bar(n, p0, p1, r=0.045):
        p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
        o = obj_add('cylinder', n, radius=r, depth=d.length, vertices=12); o.location = (p0 + p1) / 2
        o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); setmat(o, m); smooth(o); o.parent = root; parts.append(o); return o
    for s in (-1, 1):
        bar(f'Arm{s}', (0, s * 0.02, 0), (0, s * 0.22, L * 0.55))            # handles diverge
        bar(f'Loop{s}a', (0, s * 0.22, L * 0.55), (0, s * 0.42, L * 0.75))
        bar(f'Loop{s}b', (0, s * 0.42, L * 0.75), (0, s * 0.2, L * 0.95))
        bar(f'Loop{s}c', (0, s * 0.2, L * 0.95), (0, s * 0.06, L * 0.8))
        bar(f'Jaw{s}', (0, s * 0.02, 0), (0, s * 0.05, -L * 0.28), r=0.04)
        bar(f'JawTip{s}', (0, s * 0.05, -L * 0.28), (0, s * 0.02, -L * 0.36), r=0.035)
    piv = obj_add('cylinder', 'Pivot', radius=0.08, depth=0.16, vertices=16); piv.rotation_euler = (math.pi / 2, 0, 0); setmat(piv, m); piv.parent = root; parts.append(piv)
    return root, parts

def spirit_lamp(loc=(0, 0, 0), r=0.34, h=2.6, name='Lamp'):
    """The reference burner is a yellow cylinder 'lamp' with a flame on top."""
    root = empty(name, loc)
    body = obj_add('cylinder', name + 'Body', radius=r, depth=h, vertices=64, location=(0, 0, h / 2)); setmat(body, mat_plastic((0.85, 0.72, 0.28), rough=0.35, name='lamp_m')); smooth(body)
    try: mod = body.modifiers.new('bevel', 'BEVEL'); mod.width = 0.05; mod.segments = 8
    except Exception: pass
    cap = obj_add('cylinder', name + 'Cap', radius=r * 0.55, depth=0.18, vertices=64, location=(0, 0, h + 0.09)); setmat(cap, mat_metal((0.7, 0.7, 0.72), name='lampcap')); smooth(cap)
    body.parent = root; cap.parent = root
    fl, L = flame((0, 0, h + 0.15), scale=1.15, name=name + 'Flame'); fl.parent = root
    return root, body, fl

def retort_stand(loc=(0, 0, 0), h=5.5):
    m = mat_metal((0.8, 0.8, 0.83), rough=0.3, name='stand_m'); parts = []
    base = obj_add('cube', 'StandBase', size=1); base.scale = (1.6, 1.0, 0.12); base.location = (loc[0] - 0.4, loc[1], loc[2] + 0.06); setmat(base, m); parts.append(base)
    pole = obj_add('cylinder', 'StandPole', radius=0.09, depth=h, vertices=48, location=(loc[0] - 1.1, loc[1], loc[2] + h / 2)); setmat(pole, m); smooth(pole); parts.append(pole)
    arm = obj_add('cylinder', 'StandArm', radius=0.06, depth=1.5, vertices=32, location=(loc[0] - 0.4, loc[1], loc[2] + h * 0.72)); arm.rotation_euler = (0, math.pi / 2, 0); setmat(arm, m); smooth(arm); parts.append(arm)
    clamp = obj_add('torus', 'StandClamp', major_radius=0.36, minor_radius=0.06, major_segments=64, minor_segments=20, location=(loc[0] + 0.35, loc[1], loc[2] + h * 0.72)); setmat(clamp, m); smooth(clamp); parts.append(clamp)
    return parts

def tube_rack(loc=(0, 0, 0), w=4.2, d=1.6, h=2.4):
    wood = mat_plastic((0.55, 0.32, 0.14), rough=0.55, name='rack_m'); inner = mat_plastic((0.82, 0.74, 0.5), rough=0.7, name='rack_in')
    parts = []
    back = obj_add('cube', 'RackBack', size=1); back.scale = (w, 0.12, h); back.location = (loc[0], loc[1] + d / 2, loc[2] + h / 2); setmat(back, inner); parts.append(back)
    base = obj_add('cube', 'RackBase', size=1); base.scale = (w, d, 0.15); base.location = (loc[0], loc[1], loc[2] + 0.075); setmat(base, wood); parts.append(base)
    top = obj_add('cube', 'RackTop', size=1); top.scale = (w, d, 0.15); top.location = (loc[0], loc[1], loc[2] + h - 0.075); setmat(top, wood); parts.append(top)
    for s in (-1, 1):
        side = obj_add('cube', f'RackSide{s}', size=1); side.scale = (0.15, d, h); side.location = (loc[0] + s * (w / 2 - 0.075), loc[1], loc[2] + h / 2); setmat(side, wood); parts.append(side)
    return parts

def tripod(loc=(0, 0, 0), h=3.6, r=1.5):
    m = mat_metal((0.9, 0.9, 0.92), rough=0.25, name='tripod_m'); parts = []
    ringo = obj_add('torus', 'TripodRing', major_radius=r, minor_radius=0.07, major_segments=128, minor_segments=24, location=(loc[0], loc[1], loc[2] + h)); setmat(ringo, m); smooth(ringo); parts.append(ringo)
    for i in range(3):
        a = math.radians(90 + i * 120)
        top = Vector((loc[0] + r * math.cos(a), loc[1] + r * math.sin(a), loc[2] + h)); bot = Vector((loc[0] + (r + 0.35) * math.cos(a), loc[1] + (r + 0.35) * math.sin(a), loc[2]))
        d = bot - top; leg = obj_add('cylinder', f'Leg{i}', radius=0.07, depth=d.length, vertices=32); leg.location = (top + bot) / 2; leg.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); setmat(leg, m); smooth(leg); parts.append(leg)
    return parts

def wire_gauze(loc=(0, 0, 0), size=4.0, n=9):
    m = mat_metal((0.9, 0.9, 0.9), rough=0.3, name='gauze_m'); parts = []
    for i in range(n + 1):
        t = -size / 2 + size * i / n
        a = obj_add('cylinder', f'GzX{i}', radius=0.03, depth=size, vertices=24, location=(loc[0], loc[1] + t, loc[2])); a.rotation_euler = (0, math.pi / 2, 0); setmat(a, m); parts.append(a)
        b = obj_add('cylinder', f'GzY{i}', radius=0.03, depth=size, vertices=24, location=(loc[0] + t, loc[1], loc[2])); b.rotation_euler = (math.pi / 2, 0, 0); setmat(b, m); parts.append(b)
    return parts

def plate(loc=(0, 0, 0), r=2.6):
    prof = [(0.0, 0.0), (r * 0.6, 0.02), (r * 0.85, 0.12), (r, 0.22), (r * 0.97, 0.26)]
    o = glass_vessel('Plate', prof, loc, alpha=1.0, tint=(0.7, 0.7, 0.72)); setmat(o, mat_metal((0.72, 0.72, 0.74), rough=0.3, name='plate_m', metallic=0.4)); return o

def food_dome(loc=(0, 0, 0), r=1.6, seed=5):
    """The rancidity prop: a yellow spongy half-dome with pink/orange bits (like a topped snack), later dark mould dots."""
    rnd = random.Random(seed)
    o = obj_add('uv_sphere', 'Food', radius=r, segments=96, ring_count=48, location=(loc[0], loc[1], loc[2] + 0.05)); o.scale = (1, 1, 0.75)
    import bmesh
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.02], context='VERTS')
    for v in bm.verts: v.co *= 1 + 0.05 * math.sin(v.co.x * 5) * math.cos(v.co.y * 4.2)
    bm.to_mesh(o.data); bm.free()
    setmat(o, mat_plastic((0.85, 0.72, 0.12), rough=0.55, name='food_m', sss=0.2)); smooth(o)
    try: mod = o.modifiers.new('sub', 'SUBSURF'); mod.levels = 1; mod.render_levels = 2
    except Exception: pass
    bits = []
    cols = [(0.9, 0.2, 0.55), (0.95, 0.45, 0.1), (0.85, 0.15, 0.3)]
    for i in range(16):
        th = rnd.uniform(0, 2 * math.pi); ph = rnd.uniform(0.15, 1.2)
        p = (loc[0] + r * 1.0 * math.sin(ph) * math.cos(th), loc[1] + r * 1.0 * math.sin(ph) * math.sin(th), loc[2] + 0.05 + r * 0.75 * math.cos(ph))
        b = obj_add('uv_sphere', f'Bit{i}', radius=rnd.uniform(0.12, 0.2), segments=32, ring_count=16, location=p); b.scale = (1.4, 1, 0.45)
        b.rotation_euler = (ph, 0, th); setmat(b, mat_plastic(rnd.choice(cols), rough=0.4, name=f'bit{i}')); smooth(b); bits.append(b)
    return o, bits

def mould_dots(food_loc, r, n=90, seed=11):
    rnd = random.Random(seed); m = mat_plastic((0.16, 0.06, 0.04), rough=0.6, name='mould'); dots = []
    for i in range(n):
        th = rnd.uniform(0, 2 * math.pi); ph = rnd.uniform(0.1, 1.35)
        p = (food_loc[0] + r * 1.01 * math.sin(ph) * math.cos(th), food_loc[1] + r * 1.01 * math.sin(ph) * math.sin(th), food_loc[2] + 0.05 + r * 0.76 * math.cos(ph))
        d = obj_add('uv_sphere', f'Mould{i}', radius=rnd.uniform(0.05, 0.09), segments=20, ring_count=10, location=p); d.scale = (1, 1, 0.5); d.rotation_euler = (ph, 0, th); setmat(d, m); dots.append(d)
    return dots

def floaters(n, center, spread, r=0.035, color=(0.9, 0.95, 1.0), strength=6.0, seed=2, f0=1, f1=240, drift=0.6, name='Fl', alpha=1.0):
    """Slow-drifting glowing specks (the CO2 dots inside the dome, rust particles, gas molecules)."""
    rnd = random.Random(seed); m = mat_emit(color, strength=strength, name=name + '_m', alpha=alpha); out = []
    for i in range(n):
        p = Vector((center[0] + rnd.uniform(-spread[0], spread[0]), center[1] + rnd.uniform(-spread[1], spread[1]), center[2] + rnd.uniform(-spread[2], spread[2])))
        o = obj_add('ico_sphere', f'{name}{i}', radius=r * rnd.uniform(0.6, 1.4), subdivisions=3, location=p); setmat(o, m); smooth(o, auto=False)
        f = f0
        while f <= f1:
            kf(o, 'location', f, tuple(p)); p = p + Vector((rnd.uniform(-drift, drift), rnd.uniform(-drift, drift), rnd.uniform(-drift, drift) * 0.7)); f += 36
        kf_ease(o); out.append(o)
    return out

def anchors_export(names, path, f0, f1, step=1):
    """Write per-frame 2D screen positions (px, 720p) of named objects for the overlay stage."""
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene; cam = sc.camera; res = {}
    for f in range(f0, f1 + 1, step):
        sc.frame_set(f); row = {}
        for n in names:
            o = bpy.data.objects.get(n)
            if o is None or o.hide_render: continue          # hidden (not yet spawned / already gone) -> no 2D marker either
            co = world_to_camera_view(sc, cam, o.matrix_world.translation)
            row[n] = [round(co.x * LOGICAL[0], 1), round((1 - co.y) * LOGICAL[1], 1)]
        res[f] = row
    with open(path, 'w') as fh: json.dump(res, fh)

def render(outdir, f0=None, f1=None):
    sc = bpy.context.scene; os.makedirs(outdir, exist_ok=True)
    sc.render.filepath = os.path.join(outdir, 'f_')
    if f0 is not None: sc.frame_start = f0
    if f1 is not None: sc.frame_end = f1
    bpy.ops.render.render(animation=True)

# ================================================================= cinematic v2 helpers (Cycles-first, EEVEE-safe)
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
def is_cycles(): return os.environ.get('VL_ENGINE', 'EEVEE').upper() == 'CYCLES'

def hdri(name='studio_small_09_2k.hdr', strength=0.12, rotation=0.0):
    """World environment from an HDRI (reflections in glass and metal). Keeps the dark navy look: low strength + darkening."""
    path = os.path.join(ASSETS, name)
    if not os.path.exists(path): return False
    sc = bpy.context.scene; w = sc.world; nt = w.node_tree; n = nt.nodes
    bg = n.get('Background'); env = n.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(path)
    mp = n.new('ShaderNodeMapping'); tc = n.new('ShaderNodeTexCoord'); mp.inputs['Rotation'].default_value = (0, 0, rotation)
    lp = n.new('ShaderNodeLightPath'); mix = n.new('ShaderNodeMixShader'); dark = n.new('ShaderNodeBackground')
    dark.inputs[0].default_value = tuple(bg.inputs[0].default_value); dark.inputs[1].default_value = bg.inputs[1].default_value
    bg.inputs[1].default_value = strength
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], env.inputs['Vector']); nt.links.new(env.outputs['Color'], bg.inputs['Color'])
    out = n.get('World Output')
    # camera rays see the dark void; reflections/glossy rays see the HDRI
    nt.links.new(lp.outputs['Is Camera Ray'], mix.inputs['Fac']); nt.links.new(bg.outputs['Background'], mix.inputs[1]); nt.links.new(dark.outputs['Background'], mix.inputs[2])
    nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])
    return True

def atmosphere(density=0.0015, size=60, anisotropy=0.55):
    """Thin scattering volume around the whole set so spots become soft beams (Cycles). No-op in EEVEE."""
    if not is_cycles(): return None
    o = obj_add('cube', 'Atmosphere', size=size); o.location = (0, 0, size / 2 - 2)
    m = bpy.data.materials.new('atmos'); m.use_nodes = True; nt = m.node_tree
    for nd in list(nt.nodes): nt.nodes.remove(nd)
    out = nt.nodes.new('ShaderNodeOutputMaterial'); vol = nt.nodes.new('ShaderNodeVolumeScatter')
    vol.inputs['Density'].default_value = density; vol.inputs['Anisotropy'].default_value = anisotropy
    nt.links.new(vol.outputs['Volume'], out.inputs['Volume']); setmat(o, m)
    try: o.visible_shadow = False; o.visible_camera = True
    except Exception: pass
    return o

def flame_volume(loc, scale=1.0, name='FlameVol', strength=1.0, f0=1, f1=240):
    """Volumetric candle flame: teardrop volume with noise-driven density and a blackbody-ish emission gradient, animated.
    Falls back to the mesh flame in EEVEE."""
    if not is_cycles(): return flame(loc, scale=scale, name=name)
    o = obj_add('uv_sphere', name, radius=0.17 * scale, segments=32, ring_count=24, location=(loc[0], loc[1], loc[2] + 0.36 * scale))
    r = 0.17 * scale
    for v in o.data.vertices:                      # bake the teardrop into the mesh: flicker() keys the object scale, which flattened an object-scale stretch into a ball
        z = v.co.z / r; v.co.z *= 2.5
        if z > 0: t = 1 - 0.75 * z ** 1.6; v.co.x *= t; v.co.y *= t
    m = bpy.data.materials.new(name + '_vol'); m.use_nodes = True; nt = m.node_tree; n = nt.nodes
    for nd in list(n): n.remove(nd)
    out = n.new('ShaderNodeOutputMaterial'); pv = n.new('ShaderNodeVolumePrincipled')
    tc = n.new('ShaderNodeTexCoord'); mp = n.new('ShaderNodeMapping'); noise = n.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 3.5; noise.inputs['Detail'].default_value = 4
    sep = n.new('ShaderNodeSeparateXYZ'); grad = n.new('ShaderNodeMapRange'); grad.inputs['From Min'].default_value = 0.0; grad.inputs['From Max'].default_value = 1.0; grad.inputs['To Min'].default_value = 1.0; grad.inputs['To Max'].default_value = 0.0
    sph = n.new('ShaderNodeTexGradient'); sph.gradient_type = 'SPHERICAL'
    mul = n.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul2 = n.new('ShaderNodeMath'); mul2.operation = 'MULTIPLY'; mul2.inputs[1].default_value = 24.0 * strength
    pw = n.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 1.6
    ramp = n.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color = (1.0, 0.18, 0.02, 1); ramp.color_ramp.elements[1].color = (1.0, 0.75, 0.35, 1); ramp.color_ramp.elements[0].position = 0.15
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], noise.inputs['Vector']); nt.links.new(tc.outputs['Generated'], sep.inputs['Vector']); nt.links.new(tc.outputs['Generated'], sph.inputs['Vector'])
    nt.links.new(sep.outputs['Z'], grad.inputs['Value'])                 # bottom hot (1) -> top cool (0)
    nt.links.new(sph.outputs['Fac'], pw.inputs[0]); nt.links.new(pw.outputs[0], mul.inputs[0]); nt.links.new(noise.outputs['Fac'], mul.inputs[1])
    nt.links.new(mul.outputs[0], mul2.inputs[0]); nt.links.new(mul2.outputs[0], pv.inputs['Density'])
    nt.links.new(grad.outputs['Result'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], pv.inputs['Emission Color'])
    pv.inputs['Emission Strength'].default_value = 22.0 * strength; pv.inputs['Color'].default_value = (1, 0.5, 0.2, 1); pv.inputs['Absorption Color'].default_value = (0.2, 0.05, 0.0, 1)
    nt.links.new(pv.outputs['Volume'], out.inputs['Volume']); setmat(o, m)
    # animate the noise upward so the flame licks
    mp.inputs['Location'].default_value = (0, 0, 0); mp.inputs['Location'].keyframe_insert('default_value', frame=f0)
    mp.inputs['Location'].default_value = (0, 0, -6.0 * (f1 - f0) / 24.0); mp.inputs['Location'].keyframe_insert('default_value', frame=f1)
    for fc in (m.node_tree.animation_data.action.fcurves if hasattr(m.node_tree.animation_data.action, 'fcurves') else []):
        for k in fc.keyframe_points: k.interpolation = 'LINEAR'
    core = obj_add('uv_sphere', name + 'Core', radius=0.045 * scale, segments=24, ring_count=12, location=(loc[0], loc[1], loc[2] + 0.14 * scale)); core.scale = (1, 1, 1.5)
    setmat(core, mat_emit((1.0, 0.85, 0.5), strength=5.0, name=name + '_core')); smooth(core); core.parent = o; core.matrix_parent_inverse = o.matrix_world.inverted()
    L = light('POINT', (loc[0], loc[1], loc[2] + 0.45 * scale), 45 * scale, (1.0, 0.62, 0.25), name + 'Light'); L.parent = o; L.matrix_parent_inverse = o.matrix_world.inverted()
    try: L.data.shadow_soft_size = 0.02      # 0.25 rendered as a bright ball above the flame in Cycles
    except Exception: pass
    return o, L

def smoke_wisp(loc, height=2.5, name='Smoke', density=0.06, f0=1, f1=240):
    """A faint rising smoke column above a flame (Cycles only)."""
    if not is_cycles(): return None
    o = obj_add('cylinder', name, radius=0.18, depth=height, vertices=32, location=(loc[0], loc[1], loc[2] + height / 2))
    m = bpy.data.materials.new(name + '_vol'); m.use_nodes = True; nt = m.node_tree; n = nt.nodes
    for nd in list(n): n.remove(nd)
    out = n.new('ShaderNodeOutputMaterial'); vol = n.new('ShaderNodeVolumeScatter'); tc = n.new('ShaderNodeTexCoord'); mp = n.new('ShaderNodeMapping')
    noise = n.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 2.5; noise.inputs['Detail'].default_value = 5
    sep = n.new('ShaderNodeSeparateXYZ'); fade = n.new('ShaderNodeMapRange'); fade.inputs['From Min'].default_value = 0.0; fade.inputs['From Max'].default_value = 1.0; fade.inputs['To Min'].default_value = density; fade.inputs['To Max'].default_value = 0.0
    sph = n.new('ShaderNodeTexGradient'); sph.gradient_type = 'QUADRATIC_SPHERE'
    m1 = n.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; m2 = n.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], noise.inputs['Vector']); nt.links.new(tc.outputs['Generated'], sep.inputs['Vector']); nt.links.new(tc.outputs['Generated'], sph.inputs['Vector'])
    nt.links.new(sep.outputs['Z'], fade.inputs['Value']); nt.links.new(fade.outputs['Result'], m1.inputs[0]); nt.links.new(noise.outputs['Fac'], m1.inputs[1]); nt.links.new(m1.outputs[0], m2.inputs[0]); nt.links.new(sph.outputs['Fac'], m2.inputs[1])
    nt.links.new(m2.outputs[0], vol.inputs['Density']); nt.links.new(vol.outputs['Volume'], out.inputs['Volume']); setmat(o, m)
    mp.inputs['Location'].default_value = (0, 0, 0); mp.inputs['Location'].keyframe_insert('default_value', frame=f0)
    mp.inputs['Location'].default_value = (0.3, 0, -3.0 * (f1 - f0) / 24.0); mp.inputs['Location'].keyframe_insert('default_value', frame=f1)
    try: o.visible_shadow = False
    except Exception: pass
    return o

def _lightpath_passthrough(m, p):
    """Cycles: shadow and diffuse rays see this surface as transparent, so lamps light what sits inside closed glass or
    under water (the fake-caustics trick; reset() disables caustics, which would otherwise leave interiors black)."""
    nt = m.node_tree; out = nt.nodes.get('Material Output')
    lp = nt.nodes.new('ShaderNodeLightPath'); tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mix = nt.nodes.new('ShaderNodeMixShader')
    mx = nt.nodes.new('ShaderNodeMath'); mx.operation = 'MAXIMUM'
    nt.links.new(lp.outputs['Is Shadow Ray'], mx.inputs[0]); nt.links.new(lp.outputs['Is Diffuse Ray'], mx.inputs[1])
    nt.links.new(mx.outputs[0], mix.inputs[0]); nt.links.new(p.outputs['BSDF'], mix.inputs[1]); nt.links.new(tr.outputs['BSDF'], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs['Surface'])

def mat_glass_real(tint=(0.9, 0.97, 1.0), ior=1.5, rough=0.02, name='glass_real'):
    """True refractive glass for Cycles (use with solidify() for thickness). Falls back to alpha glass in EEVEE."""
    if not is_cycles(): return mat_glass(tint, alpha=0.18, rough=rough, name=name)
    m, p = _principled(name)
    _inp(p, 'Base Color', (*tint, 1)); _inp(p, 'Roughness', rough); _inp(p, 'IOR', ior); _inp(p, 'Transmission Weight', 1.0); _inp(p, 'Coat Weight', 0.3)
    _lightpath_passthrough(m, p)
    return m

def mat_liquid_real(color=(0.1, 0.25, 0.9), ior=1.33, absorption=0.6, name='liquid_real'):
    """Tinted transmissive liquid for Cycles (volume absorption gives the colour depth)."""
    if not is_cycles(): return mat_liquid(color, alpha=0.8, name=name)
    m, p = _principled(name); nt = m.node_tree
    _inp(p, 'Base Color', (1, 1, 1, 1)); _inp(p, 'Roughness', 0.05); _inp(p, 'IOR', ior); _inp(p, 'Transmission Weight', 1.0)
    ab = nt.nodes.new('ShaderNodeVolumeAbsorption'); ab.inputs['Color'].default_value = (*color, 1); ab.inputs['Density'].default_value = absorption
    out = nt.nodes.get('Material Output'); nt.links.new(ab.outputs['Volume'], out.inputs['Volume'])
    _lightpath_passthrough(m, p)
    return m

def solidify(o, thickness=0.03):
    try: mod = o.modifiers.new('solid', 'SOLIDIFY'); mod.thickness = thickness; mod.offset = -1; mod.use_even_offset = True; return mod
    except Exception: return None

def subsurf(o, levels=1, render_levels=2):
    try: mod = o.modifiers.new('subd', 'SUBSURF'); mod.levels = levels; mod.render_levels = render_levels; return mod
    except Exception: return None

def rack_focus(cam, f0, f1, obj0, obj1):
    """Animate the focus from obj0 to obj1 between frames (DOF must be on)."""
    try:
        sc = bpy.context.scene; cam.data.dof.use_dof = True; cam.data.dof.focus_object = None
        for f, o in ((f0, obj0), (f1, obj1)):
            sc.frame_set(int(f)); bpy.context.view_layer.update()      # evaluate the dolly/constraints/parenting AT this frame (build-time matrices were identity -> focus 0 -> black frame)
            d = (Vector(o.matrix_world.translation) - Vector(cam.matrix_world.translation)).length if hasattr(o, 'matrix_world') else float(o)
            cam.data.dof.focus_distance = max(0.5, d); cam.data.dof.keyframe_insert('focus_distance', frame=f)
        sc.frame_set(1)
    except Exception as e: print('rack_focus', e)

def orbit(cam, tgt, center, radius, height, a0, a1, f0, f1, ease=True):
    """Camera arc around a centre point (angles in degrees), keeping the target fixed."""
    steps = max(2, int((f1 - f0) / 6))
    for i in range(steps + 1):
        u = i / steps; u2 = (u * u * (3 - 2 * u)) if ease else u; a = math.radians(a0 + (a1 - a0) * u2)
        kf(cam, 'location', int(f0 + (f1 - f0) * u), (center[0] + radius * math.sin(a), center[1] - radius * math.cos(a), height))
    kf_lin(cam); tgt.location = center

def grade(vignette=0.35, grain=0.0, dispersion=0.004):
    """Finishing pass after the bloom: vignette + a whisper of chromatic dispersion. Blender 5.x compositor uses the
    shader-family node types (ShaderNodeMath/Mix/MapRange) and socket inputs for options. Best effort, never fatal."""
    sc = bpy.context.scene
    try:
        nt = sc.compositing_node_group if hasattr(sc, 'compositing_node_group') else sc.node_tree
        if nt is None: return
        out = next(n for n in nt.nodes if n.bl_idname in ('NodeGroupOutput', 'CompositorNodeComposite'))
        src_link = next(l for l in nt.links if l.to_node == out); src = src_link.from_socket; nt.links.remove(src_link)
        cur = src
        if dispersion > 0:
            ld = nt.nodes.new('CompositorNodeLensdist')
            for nm, val in (('Dispersion', dispersion), ('Distortion', 0.0), ('Fit', True)):
                try:
                    if nm in ld.inputs: ld.inputs[nm].default_value = val
                except Exception: pass
            nt.links.new(cur, ld.inputs['Image']); cur = ld.outputs['Image']
        if vignette > 0:
            em = nt.nodes.new('CompositorNodeEllipseMask')
            for nm, val in (('Size', (1.35, 1.25)), ('Position', (0.5, 0.5))):
                try:
                    if nm in em.inputs: em.inputs[nm].default_value = val
                except Exception:
                    try: em.inputs[nm].default_value = val[0]
                    except Exception: pass
            for attr, val in (('width', 1.35), ('height', 1.25)):
                try: setattr(em, attr, val)
                except Exception: pass
            bl = nt.nodes.new('CompositorNodeBlur')
            for nm, val in (('Size', 320.0), ('Extend Bounds', True), ('Type', 'Gaussian')):
                try:
                    if nm in bl.inputs: bl.inputs[nm].default_value = val
                except Exception: pass
            nt.links.new(em.outputs['Mask'], bl.inputs['Image'])
            m1 = nt.nodes.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; m1.inputs[1].default_value = vignette
            m2 = nt.nodes.new('ShaderNodeMath'); m2.operation = 'ADD'; m2.inputs[1].default_value = 1 - vignette
            nt.links.new(bl.outputs['Image'], m1.inputs[0]); nt.links.new(m1.outputs[0], m2.inputs[0])
            mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1.0
            nt.links.new(cur, mx.inputs[6]); nt.links.new(m2.outputs[0], mx.inputs[7]); cur = mx.outputs[2]
        nt.links.new(cur, out.inputs[0]); print('grade OK')
    except Exception as e:
        print('grade skipped:', e)
        try:
            if not any(l.to_node == out for l in nt.links): nt.links.new(src, out.inputs[0])
        except Exception: pass

def mat_wood_pbr(name='wood_pbr', scale=0.25, tint=(0.75, 0.55, 0.38)):
    """PolyHaven CC0 wood_floor_deck (diffuse/roughness/normal). Falls back to the procedural planks if the maps are missing."""
    d = os.path.join(ASSETS, 'wood_floor_deck_diff_2k.jpg'); r = os.path.join(ASSETS, 'wood_floor_deck_rough_2k.jpg'); nm = os.path.join(ASSETS, 'wood_floor_deck_nor_gl_2k.jpg')
    if not all(os.path.exists(x) for x in (d, r, nm)): return mat_wood(name)
    m, p = _principled(name); nt = m.node_tree; n = nt.nodes
    tc = n.new('ShaderNodeTexCoord'); mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (scale, scale, scale)
    td = n.new('ShaderNodeTexImage'); td.image = bpy.data.images.load(d)
    tr = n.new('ShaderNodeTexImage'); tr.image = bpy.data.images.load(r); tr.image.colorspace_settings.name = 'Non-Color'
    tn = n.new('ShaderNodeTexImage'); tn.image = bpy.data.images.load(nm); tn.image.colorspace_settings.name = 'Non-Color'
    nmap = n.new('ShaderNodeNormalMap'); nmap.inputs['Strength'].default_value = 0.8
    mix = n.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 0.6; mix.inputs[7].default_value = (*tint, 1)
    for t in (td, tr, tn): nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], t.inputs['Vector'])
    nt.links.new(td.outputs['Color'], mix.inputs[6]); nt.links.new(mix.outputs[2], p.inputs['Base Color'])
    nt.links.new(tr.outputs['Color'], p.inputs['Roughness']); nt.links.new(tn.outputs['Color'], nmap.inputs['Color']); nt.links.new(nmap.outputs['Normal'], p.inputs['Normal'])
    _inp(p, 'Specular IOR Level', 0.45)
    return m

def floor_wood_pbr(size=40):
    o = obj_add('plane', 'Floor', size=size); setmat(o, mat_wood_pbr()); return o
