"""Project loader: VL_PROJECT selects projects/<name>/timeline.py (event list E)."""
import os, importlib, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
PROJECT = os.environ.get('VL_PROJECT', 'chem')
_m = importlib.import_module(f'projects.{PROJECT}.timeline')
E = _m.E
def events_at(t):
    return [e for e in E if e['t0'] - 0.4 <= t < e['t1'] + 0.35]
