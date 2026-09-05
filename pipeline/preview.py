"""Preview clip from selected time ranges: python3 preview.py <plates> <narration.wav> <out.mp4> t0 t1 [t0 t1 ...]"""
import sys, os, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import overlay
from shotlist import FPS
from ui import W, H
plates, narr, out = sys.argv[1:4]; ts = [float(x) for x in sys.argv[4:]]
overlay.PLATES = plates; tmp = tempfile.mkdtemp(); segs = []
for i in range(0, len(ts), 2):
    t0, t1 = ts[i], ts[i + 1]; v = os.path.join(tmp, f'v{i}.mp4'); a = os.path.join(tmp, f'a{i}.wav'); m = os.path.join(tmp, f'm{i}.mp4')
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', v], stdin=subprocess.PIPE)
    for k in range(int(t0 * FPS), int(t1 * FPS)): p.stdin.write(overlay.render_frame(k / FPS).tobytes())
    p.stdin.close(); p.wait()
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t0), '-t', str(t1 - t0), '-i', narr, a], check=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', v, '-i', a, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', m], check=True); segs.append(m)
    print(f'segment {t0}-{t1} done', flush=True)
lst = os.path.join(tmp, 'list.txt'); open(lst, 'w').write(''.join(f"file '{s}'\n" for s in segs))
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', '-movflags', '+faststart', out], check=True)
print('WROTE', out)
