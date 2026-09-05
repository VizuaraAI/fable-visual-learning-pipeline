"""Final assembly: (1) upsample 12 fps plates to 24 fps with motion-compensated interpolation, (2) composite UI in parallel
chunks straight into x264 segments, (3) concat + mux the narration.   python3 assemble.py <plates_root> <work> <out.mp4> [chunks]"""
import sys, os, subprocess, glob, json
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shotlist import SHOTS, n_render_frames, FPS

def interp(root, s):
    sid = s['id']; d = os.path.join(root, sid); d24 = os.path.join(d, 'f24'); nf = n_render_frames(s)
    if s['mode'] != '3d' or s['rfps'] >= FPS or nf < 4: return sid, 'skip'
    if os.path.isdir(d24) and len(glob.glob(os.path.join(d24, '*.png'))) >= nf * 2 - 2: return sid, 'have'
    os.makedirs(d24, exist_ok=True)
    cmd = ['ffmpeg', '-v', 'error', '-y', '-framerate', str(s['rfps']), '-i', os.path.join(d, 'f_%04d.png'),
           '-vf', f"minterpolate=fps={FPS}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:search_param=24", '-start_number', '0', os.path.join(d24, '%05d.png')]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        cmd[cmd.index('-vf') + 1] = f"minterpolate=fps={FPS}:mi_mode=blend"; subprocess.run(cmd, capture_output=True, text=True)
    return sid, f'{len(glob.glob(os.path.join(d24, "*.png")))} frames'

def main():
    root, work, out = sys.argv[1], sys.argv[2], sys.argv[3]; chunks = int(sys.argv[4]) if len(sys.argv) > 4 else 6
    os.makedirs(work, exist_ok=True)
    with ThreadPoolExecutor(3) as ex:
        for sid, msg in ex.map(lambda s: interp(root, s), SHOTS): print('interp', sid, msg, flush=True)
    here = os.path.dirname(os.path.abspath(__file__))
    procs = [subprocess.Popen([sys.executable, os.path.join(here, 'overlay.py'), root, work, str(chunks), str(i)]) for i in range(chunks)]
    for p in procs: p.wait()
    with open(os.path.join(work, 'concat.txt'), 'w') as f:
        for i in range(chunks): f.write(f"file '{os.path.join(work, f'seg_{i:02d}.mp4')}'\n")
    silent = os.path.join(work, 'video_silent.mp4')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', os.path.join(work, 'concat.txt'), '-c', 'copy', silent], check=True)
    narr = sys.argv[5] if len(sys.argv) > 5 else os.path.join(os.path.dirname(work), 'narration.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', silent, '-i', narr, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-ar', '44100', '-ac', '2', '-shortest', '-movflags', '+faststart', out], check=True)
    print('WROTE', out)

if __name__ == '__main__': main()
