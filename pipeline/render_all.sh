#!/bin/zsh
# Render every 3D shot with N parallel Blender workers (default 2), statically partitioned by frame count (no flock on macOS).
# Skips shots whose frames are already complete.   usage: render_all.sh <plates_root> [workers]
ROOT="$1"; WORKERS="${2:-2}"; P="$(cd "$(dirname "$0")" && pwd)"; BLENDER="${VL_BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
cd "$P"; mkdir -p "$ROOT"
python3 - "$ROOT" "$WORKERS" <<'PY'
import sys, os, glob
from shotlist import SHOTS, n_render_frames
root, W = sys.argv[1], int(sys.argv[2])
jobs = []
for s in SHOTS:
    if s['mode'] != '3d': continue
    nf = n_render_frames(s); have = len(glob.glob(os.path.join(root, s['id'], 'f_*.png')))
    if have >= nf: continue
    jobs.append((nf, s['id']))
jobs.sort(reverse=True)
lists = [[] for _ in range(W)]; load = [0] * W
for nf, sid in jobs:
    k = load.index(min(load)); lists[k].append(sid); load[k] += nf
for k in range(W):
    open(os.path.join(root, f'worker{k+1}.txt'), 'w').write('\n'.join(lists[k]) + '\n'); print(f'worker{k+1}: {load[k]} frames', lists[k])
PY
worker() {
  local w=$1
  for sid in $(cat "$ROOT/worker$w.txt"); do
    local have nf f0
    have=$(ls "$ROOT/$sid" 2>/dev/null | grep -c "^f_"); nf=$(python3 -c "from shotlist import *; print(n_render_frames([x for x in SHOTS if x['id']=='$sid'][0]))")
    [ "$have" -ge "$nf" ] && { echo "[w$w] skip  $sid (complete)"; continue; }
    f0=$((have+1))
    echo "[w$w] start $sid $(date +%H:%M:%S) from frame $f0/$nf"
    "$BLENDER" -b --python render_shot.py -- "$sid" "$ROOT" $f0 $nf > "$ROOT/$sid.log" 2>&1
    echo "[w$w] done  $sid $(date +%H:%M:%S)  $(grep -E 'rendered' "$ROOT/$sid.log" | tail -1)"
  done
}
for w in $(seq 1 $WORKERS); do worker $w & done
wait
echo RENDER_ALL_DONE $(date +%H:%M:%S)
