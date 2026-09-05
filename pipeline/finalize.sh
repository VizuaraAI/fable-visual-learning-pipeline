#!/bin/zsh
# Pull composited segments from the Modal volume, concat, mux narration, write the master + comparison sheet.
# usage: finalize.sh <work_dir> <narration.wav> <reference.mp4> <out.mp4>
set -e
WORK="$1"; NARR="$2"; REF="$3"; OUT="$4"; P="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$WORK/segments"; cd "$WORK"
python3 -m modal volume get vl-plates "${VL_PROJECT:-chem}/segments" "$WORK/" --force >/dev/null
ls "$WORK/segments"/seg_*.mp4 | sort | sed "s/^/file '/;s/$/'/" > concat.txt
ffmpeg -v error -y -f concat -safe 0 -i concat.txt -c copy video_silent.mp4
ffmpeg -v error -y -i video_silent.mp4 -i "$NARR" -c:v copy -c:a aac -b:a 192k -ar 48000 -ac 2 -shortest -movflags +faststart "$OUT"
ffprobe -v error -show_entries format=duration:stream=width,height,r_frame_rate -of compact "$OUT"
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")
TS=$(python3 -c "import sys; d=float(sys.argv[1]); print(' '.join(str(round(3+(d-8)*i/21,1)) for i in range(22)))" "$DUR")
python3 "$P/compare.py" "$REF" "$OUT" "${OUT%.mp4}_comparison.png" ${=TS}
