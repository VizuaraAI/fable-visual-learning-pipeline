"""Project loader: VL_PROJECT selects projects/<name>/shotlist.py (chem | cell | grav)."""
import os, importlib, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
PROJECT = os.environ.get('VL_PROJECT', 'chem')
_m = importlib.import_module(f'projects.{PROJECT}.shotlist')
SHOTS, TOTAL, FPS = _m.SHOTS, _m.TOTAL, 24
if os.environ.get('VL_FPS_ALL'):
    for _s in SHOTS:
        if _s['mode'] == '3d': _s['rfps'] = int(os.environ['VL_FPS_ALL'])
def shot_at(t):
    for s in SHOTS:
        if s['t0'] <= t < s['t1']: return s
    return SHOTS[-1]
def n_render_frames(s):
    dur = s['t1'] - s['t0']
    if s.get('hold') is not None: dur = min(dur, s['hold'])
    return max(1, int(round(dur * s['rfps'])))
