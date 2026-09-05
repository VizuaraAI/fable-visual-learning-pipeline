"""Project loader: VL_PROJECT selects projects/<name>/shots.py (builder functions)."""
import os, importlib, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
PROJECT = os.environ.get('VL_PROJECT', 'chem')
_m = importlib.import_module(f'projects.{PROJECT}.shots')
globals().update({k: v for k, v in vars(_m).items() if not k.startswith('__')})
