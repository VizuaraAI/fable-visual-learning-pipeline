import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, kit
from kit import *
out = sys.argv[sys.argv.index('--') + 1]
reset(); sc = bpy.context.scene; sc.render.resolution_x = 1280; sc.render.resolution_y = 720
try:
    sc.cycles.samples = 128; sc.cycles.use_denoising = True
    for d in prefs.devices: d.use = True
    sc.cycles.device = 'GPU'
except Exception as e: print('cycles prefs', e)
print('hdri', hdri()); floor_wood_pbr(); studio(key=(2.5, -4.0, 7.5), key_e=2600, target=(0, 0, 1.3))
body, w = candle((0, 0, 0)); fl, L = flame_volume((0, 0, 2.6), f0=1, f1=48); smoke_wisp((0, 0, 3.1)); atmosphere(0.004)
j = obj_add('cylinder', 'Jar', radius=1.3, depth=3.9, vertices=128, location=(2.6, 0.5, 1.95)); setmat(j, mat_glass_real()); solidify(j, 0.04); smooth(j)
cam, tgt = camera((0.6, -9.5, 2.8), (0.4, 0, 1.5), lens=50); grade()
set_range(1); t = time.time(); render(out, 1, 1); print('v2 test frame in %.1fs' % (time.time() - t))
