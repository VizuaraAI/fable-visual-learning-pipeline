"""blender -b --python render_shot.py -- <shot_id> <out_root> [f0 f1]   renders frames f_0001.png.. for one shot."""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from shotlist import SHOTS, n_render_frames
import shots, kit

args = sys.argv[sys.argv.index('--') + 1:]
sid, out_root = args[0], args[1]
spec = next(s for s in SHOTS if s['id'] == sid)
nf = n_render_frames(spec); rfps = spec['rfps']; dur = spec['t1'] - spec['t0']
t = time.time()
getattr(shots, spec['builder'])(nf, rfps, dur)
kit.set_range(nf)
outdir = os.path.join(out_root, sid); os.makedirs(outdir, exist_ok=True)
anch = spec.get('anchors')
if anch:
    names = anch if isinstance(anch, list) else [o.name for o in bpy.data.objects if o.name[:2] in ('Hp', 'Op', 'Rp') and o.type == 'MESH']
    kit.anchors_export(names, os.path.join(outdir, 'anchors.json'), 1, nf)
f0 = int(args[2]) if len(args) > 2 else 1; f1 = int(args[3]) if len(args) > 3 else nf
print(f'[{sid}] build {time.time()-t:.1f}s; rendering {f0}..{f1} of {nf} frames @ {rfps} fps')
t = time.time(); kit.render(outdir, f0, f1)
print(f'[{sid}] rendered {f1-f0+1} frames in {time.time()-t:.1f}s ({(time.time()-t)/max(1,f1-f0+1):.2f} s/frame)')
json.dump(dict(spec, nf=nf), open(os.path.join(outdir, 'spec.json'), 'w'))
