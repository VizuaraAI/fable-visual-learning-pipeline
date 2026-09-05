import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, kit; importlib.reload(kit)
import bpy
from kit import *
out = sys.argv[sys.argv.index('--') + 1]
def shot_candle():
    reset(); floor_wood(); studio(key=(2.5, -5, 7), key_e=2500, target=(0, 0, 1.2))
    body, w = candle((0, 0, 0)); fl, L = flame((0, 0, 2.6)); flicker(fl, 1, 48)
    cam, tgt = camera((0.4, -9.5, 2.6), (0, 0, 1.4), lens=55)
    set_range(2); render(os.path.join(out, 'candle'), 1, 2)
def shot_jar():
    reset(); floor_wood(); studio(key=(2.5, -5, 7), key_e=2500, target=(0, 0, 1.2))
    body, w = candle((0, 0, 0)); jar(r=1.3, h=3.8)
    cam, tgt = camera((0.4, -9.5, 2.8), (0, 0, 1.6), lens=55)
    set_range(1); render(os.path.join(out, 'jar'), 1, 1)
def shot_dome():
    reset(); floor_wood(); studio(key=(2.5, -5, 7), key_e=2500, target=(0, 0, 1.2))
    body, w = candle((0, 0, 0)); fl, L = flame((0, 0, 2.6)); dome(r=3.4)
    floaters(70, (0, 0, 1.6), (2.6, 2.6, 1.4), r=0.035, strength=5, f0=1, f1=48)
    cam, tgt = camera((0.6, -10.5, 2.4), (0, 0, 1.2), lens=50)
    set_range(1); render(os.path.join(out, 'dome'), 1, 1)
def shot_tube():
    reset(); studio(key=(2.5, -5, 7), key_e=2000, target=(0, 0, 1.6))
    t = test_tube((0, 0, 0), r=0.34, h=3.4); tube_liquid((0, 0, 0), 0.34, 1.5, (0.05, 0.15, 0.85))
    lamp, body, fl = spirit_lamp((2.5, 0, 0)); tg, parts = tongs((-2.2, 0, 2.0)); tg.rotation_euler = (0, 0.6, 0)
    gr, _ = granules((0, 0, 0.35), 40, 0.22, 0.05, (0.25, 0.85, 0.2), name='FeSO4')
    cam, tgt = camera((0.0, -9.0, 2.2), (0, 0, 1.6), lens=50)
    set_range(1); render(os.path.join(out, 'tube'), 1, 1)
t = time.time(); shot_candle(); print("candle", time.time() - t); t = time.time(); shot_dome(); print("dome", time.time() - t); t = time.time(); shot_tube(); print("tube", time.time() - t)
