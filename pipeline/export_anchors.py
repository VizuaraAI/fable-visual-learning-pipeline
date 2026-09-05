"""Rebuild a shot's scene (no render) and re-export its anchors.json.  blender -b --python export_anchors.py -- <shot_id> <plates_root>"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, shots, kit
from shotlist import SHOTS, n_render_frames
sid, root = sys.argv[sys.argv.index('--') + 1:][:2]
spec = next(s for s in SHOTS if s['id'] == sid); nf = n_render_frames(spec)
getattr(shots, spec['builder'])(nf, spec['rfps'], spec['t1'] - spec['t0']); kit.set_range(nf)
anch = spec.get('anchors'); names = anch if isinstance(anch, list) else [o.name for o in bpy.data.objects if o.name[:2] in ('Hp', 'Op', 'Rp') and o.type == 'MESH']
kit.anchors_export(names, os.path.join(root, sid, 'anchors.json'), 1, nf); print('anchors re-exported', sid, len(names), 'objects')
