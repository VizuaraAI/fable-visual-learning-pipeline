#!/bin/zsh
# finalize for ORIGINAL chapters (no reference.mp4): pull segments, ffprobe every one, concat, mux narration, contact sheet.
# usage: VL_PROJECT=<p> ./finalize_orig.sh <work_dir> <narration.wav> <out.mp4>
set -e
SP="$(cd "$(dirname "$0")" && pwd)"
abs() { python3 -c "import os,sys; print(os.path.abspath(sys.argv[1]))" "$1"; }
WORK="$(abs "$1")"; NARR="$(abs "$2")"; OUT="$(abs "$3")"   # resolve BEFORE the cd below (relative paths broke the dna finalize on 5 Sep)
mkdir -p "$WORK"; cd "$WORK"
python3 -m modal volume get vl-plates "${VL_PROJECT}/segments" "$WORK/" --force >/dev/null
echo "--- segment probe ---"
python3 - "$WORK/segments" <<'EOF'
import sys, os, subprocess
d = sys.argv[1]; segs = sorted(f for f in os.listdir(d) if f.endswith('.mp4')); bad = []; tot = 0.0; frames = []
for f in segs:
    p = os.path.join(d, f)
    r = subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries', 'stream=nb_read_frames,duration', '-of', 'csv=p=0', p], capture_output=True, text=True).stdout.strip()
    try:
        vals = r.split(','); nfr = int(next(v for v in vals if v.strip().isdigit())); du = float(next(v for v in vals if '.' in v))   # ffprobe prints duration,nb_read_frames in ITS order, not the -show_entries order
    except Exception: bad.append((f, r)); continue
    frames.append(nfr); tot += du; print(f'{f} frames={nfr} dur={du:.2f}')
if bad: print('BROKEN segments:', bad); sys.exit(2)
if len(set(frames[:-1])) > 1: print('WARNING: unequal segment lengths (all but the last must match):', frames); sys.exit(3)
print(f'{len(segs)} segments OK, total {tot:.2f}s, {sum(frames)} frames')
EOF
ls "$WORK/segments"/seg_*.mp4 | sort | sed "s/^/file '/;s/$/'/" > concat.txt
ffmpeg -v error -y -f concat -safe 0 -i concat.txt -c copy video_silent.mp4
ffmpeg -v error -y -i video_silent.mp4 -i "$NARR" -c:v copy -c:a aac -b:a 192k -ar 48000 -ac 2 -shortest -movflags +faststart "$OUT"
ffprobe -v error -show_entries format=duration:stream=width,height,r_frame_rate -of compact "$OUT"
python3 "$SP/master_sheet.py" "$OUT" "${OUT%.mp4}_sheet.png" 24
