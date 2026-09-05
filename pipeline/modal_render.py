"""Cloud pipeline on Modal: (A) Cycles GPU render of frame chunks, (B) CPU compositing of timeline chunks, on one shared volume.
  modal run modal_render.py --stage test        # one tiny chunk, prints timing
  modal run modal_render.py --stage render      # all shots, all frames (24 fps, 1080p)
  modal run modal_render.py --stage composite   # UI overlay -> segments on the volume
  modal volume get vl-plates segments ./segments
"""
import modal, os, subprocess, glob, json, time

HERE = os.path.dirname(os.path.abspath(__file__))
app = modal.App(f"vl-render-{os.environ.get('VL_PROJECT', 'chem')}")
vol = modal.Volume.from_name("vl-plates", create_if_missing=True)
BLENDER_URL = "https://download.blender.org/release/Blender5.2/blender-5.2.1-linux-x64.tar.xz"
PROJECT = os.environ.get("VL_PROJECT", "chem")
IGNORE = ["**/refs/**", "**/__pycache__/**", "**/.git/**"]   # reference videos/sheets stay on the laptop
ENV = dict(VL_ENGINE="CYCLES", VL_RES="1920x1080", VL_SAMPLES=os.environ.get("VL_SAMPLES", "256"), VL_FPS_ALL="24", VL_DOF="1", VL_MBLUR="1", VL_SCALE="1.5", VL_PROJECT=PROJECT)

gpu_image = (modal.Image.debian_slim(python_version="3.11")
    .apt_install("curl", "xz-utils", "libxi6", "libxrender1", "libxkbcommon0", "libsm6", "libxext6", "libx11-6", "libgl1", "libegl1",
                 "libxfixes3", "libxxf86vm1", "libxcursor1", "libxinerama1", "libxrandr2", "libgomp1", "libglu1-mesa")
    .run_commands(f"curl -sL {BLENDER_URL} | tar -xJ -C /opt && ln -s /opt/blender-5.2.1-linux-x64/blender /usr/local/bin/blender && blender --version")
    .env(ENV)
    .add_local_dir(HERE, "/pipeline", ignore=IGNORE))   # pipeline/assets (HDRI, textures) rides along

cpu_image = (modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "fonts-liberation", "fonts-dejavu-core")
    .pip_install("pillow==11.2.1", "numpy")
    .env(ENV)
    .add_local_dir(HERE, "/pipeline", ignore=IGNORE))

GPUS = os.environ.get("VL_GPUS", "L40S,H100,A10G").split(",")   # the workspace caps ~50 A10G containers; other tiers (H100/A100) add capacity

@app.function(image=gpu_image, gpu=GPUS, volumes={"/vol": vol}, timeout=3600, max_containers=64, retries=2)
def render_chunk(job):
    sid, f0, f1 = job[:3]; overrides = job[3] if len(job) > 3 else {}; t = time.time()
    out = overrides.pop("_out", f"/vol/{PROJECT}/plates"); os.makedirs(os.path.join(out, sid), exist_ok=True)
    env = dict(os.environ, HOME="/root", **overrides)
    r = subprocess.run(["blender", "-b", "--python", "/pipeline/render_shot.py", "--", sid, out, str(f0), str(f1)], capture_output=True, text=True, env=env)
    vol.commit()
    have = len(glob.glob(os.path.join(out, sid, "f_*.png")))
    crash = open("/tmp/blender.crash.txt").read()[-1200:] if os.path.exists("/tmp/blender.crash.txt") else ""
    tail = (r.stdout[-1200:] + "\n" + r.stderr[-600:] + "\nCRASH:\n" + crash) if r.returncode != 0 else "\n".join(l for l in r.stdout.splitlines() if l.startswith("[") or "cycles devices" in l)[-600:]
    return dict(sid=sid, f0=f0, f1=f1, cfg=overrides, ok=r.returncode == 0, secs=round(time.time() - t, 1), have=have, tail=tail)


@app.function(image=gpu_image, gpu="A10G", timeout=900)
def probe():
    import shutil
    out = []
    def sh(cmd):
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True); out.append(f"$ {cmd}\n{r.stdout[-1500:]}{r.stderr[-800:]}")
    sh("nvidia-smi --query-gpu=name,driver_version --format=csv")
    sh("ls /usr/share/nvidia/ 2>&1; ls /usr/lib/x86_64-linux-gnu/ | grep -i -E 'optix|nvidia-ml|libcuda' | head")
    sh("ls /opt/blender-5.2.1-linux-x64/lib | grep -i -E 'oidn|OpenImageDenoise|tbb|optix' ")
    sh("for f in /opt/blender-5.2.1-linux-x64/lib/libOpenImageDenoise*.so*; do echo == $f; ldd $f | grep -i 'not found'; done")
    comp = ("nt=bpy.data.node_groups.new('C','CompositorNodeTree'); nt.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor'); o=nt.nodes.new('NodeGroupOutput'); rl=nt.nodes.new('CompositorNodeRLayers'); g=nt.nodes.new('CompositorNodeGlare'); g.inputs['Type'].default_value='Bloom'; nt.links.new(rl.outputs['Image'], g.inputs['Image']); nt.links.new(g.outputs['Image'], o.inputs[0]); sc.compositing_node_group=nt; sc.render.use_compositing=True")
    tests = {
      "glare_gpu_compositor": comp + "; sc.cycles.use_denoising=False",
      "glare_cpu_compositor": comp + "; sc.render.compositor_device='CPU'; sc.cycles.use_denoising=False",
      "optix_nodenoise": "sc.cycles.denoiser='OPTIX'; sc.cycles.use_denoising=False",
      "oidn_cpu": "sc.cycles.denoiser='OPENIMAGEDENOISE'; sc.cycles.use_denoising=True; sc.cycles.denoising_use_gpu=False",
      "oidn_gpu": "sc.cycles.denoiser='OPENIMAGEDENOISE'; sc.cycles.use_denoising=True; sc.cycles.denoising_use_gpu=True",
      "cpu_device_oidn": "sc.cycles.device='CPU'; sc.cycles.denoiser='OPENIMAGEDENOISE'; sc.cycles.use_denoising=True; sc.cycles.denoising_use_gpu=False",
    }
    for name, cfg in tests.items():
        expr = ("import bpy; sc=bpy.context.scene; sc.render.engine='CYCLES'; p=bpy.context.preferences.addons['cycles'].preferences; p.compute_device_type='OPTIX'; p.get_devices(); "
                "[setattr(d,'use',d.type!='CPU') for d in p.devices]; sc.cycles.device='GPU'; sc.cycles.samples=16; sc.render.resolution_x=160; sc.render.resolution_y=90; " + cfg +
                f"; sc.render.filepath='/tmp/{name}_'; bpy.ops.render.render(write_still=True); print('RENDER_OK {name}')")
        if os.path.exists('/tmp/blender.crash.txt'): os.remove('/tmp/blender.crash.txt')
        r = subprocess.run(["blender", "-b", "--python-expr", expr], capture_output=True, text=True, env=dict(os.environ, HOME="/root"))
        crash = open('/tmp/blender.crash.txt').read()[-600:] if os.path.exists('/tmp/blender.crash.txt') else ''
        out.append(f"### {name}: rc={r.returncode}\n" + "\n".join(l for l in (r.stdout + r.stderr).splitlines() if 'RENDER_OK' in l or 'rror' in l or 'denois' in l.lower())[-800:] + ("\nCRASH " + crash if crash else ""))
    return "\n\n".join(out)

@app.function(image=cpu_image, cpu=2.0, memory=4096, volumes={"/vol": vol}, timeout=3600, max_containers=32)
def composite_chunk(args):
    ci, n = args; t = time.time()
    os.makedirs(f"/vol/{PROJECT}/segments", exist_ok=True)
    r = subprocess.run(["python3", "/pipeline/overlay.py", f"/vol/{PROJECT}/plates", f"/vol/{PROJECT}/segments", str(n), str(ci)], capture_output=True, text=True)
    vol.commit()
    return dict(ci=ci, ok=r.returncode == 0, secs=round(time.time() - t, 1), tail=(r.stdout[-400:] + r.stderr[-600:]))

def _pipe():
    return HERE if os.path.exists(os.path.join(HERE, "shotlist.py")) else "/pipeline"   # inside a container the entrypoint file lives in /root

def jobs_for(chunk=48, only=None, max_frames=None):
    os.environ["VL_FPS_ALL"] = "24"
    import sys; sys.path.insert(0, _pipe())
    from shotlist import SHOTS, n_render_frames
    jobs = []
    for s in SHOTS:
        if s["mode"] != "3d" or (only and s["id"] not in only): continue
        nf = n_render_frames(s)
        if max_frames: nf = min(nf, max_frames)
        for f0 in range(1, nf + 1, chunk): jobs.append((s["id"], f0, min(nf, f0 + chunk - 1)))
    return jobs


@app.function(image=cpu_image, cpu=2.0, memory=4096, volumes={"/vol": vol}, timeout=600)
def probe_cpu(t: float = 240.0):
    import sys, io
    sys.path.insert(0, "/pipeline"); import overlay
    overlay.PLATES = f"/vol/{PROJECT}/plates"; im = overlay.render_frame(t); buf = io.BytesIO(); im.save(buf, "PNG")
    fonts = [k for k in overlay.ui.FONTS]; return dict(size=im.size, fonts=str(fonts)[:300], png=buf.getvalue())


@app.function(image=gpu_image, gpu="A10G", volumes={"/vol": vol}, timeout=1200)
def v2test():
    r = subprocess.run(["blender", "-b", "--python", "/pipeline/v2test_scene.py", "--", "/tmp/v2out"], capture_output=True, text=True, env=dict(os.environ, HOME="/root"))
    crash = open("/tmp/blender.crash.txt").read()[-800:] if os.path.exists("/tmp/blender.crash.txt") else ""
    png = open("/tmp/v2out/f_0001.png", "rb").read() if os.path.exists("/tmp/v2out/f_0001.png") else b""
    keep = "\n".join(l for l in (r.stdout + r.stderr).splitlines() if any(k in l for k in ("hdri", "bloom", "grade", "v2 test", "rror", "Traceback", "line ")))
    return dict(rc=r.returncode, log=keep[-2500:], crash=crash, png=png)

@app.function(image=cpu_image, cpu=1.0, memory=1024, timeout=300)
def probe_font():
    """Which font file each UI face resolves to in the container, and whether the special glyphs exist there."""
    import sys; sys.path.insert(0, "/pipeline"); import ui
    from PIL import Image, ImageDraw
    out = {}
    for name in ("uni", "bold", "reg", "serifb", "serif"):
        f = ui.font(name, 30)
        def bm(ch):
            im = Image.new("L", (80, 60), 0); ImageDraw.Draw(im).text((5, 5), ch, font=f, fill=255); return im.tobytes()
        missing = bm("\u2ffe")
        out[name] = dict(path=getattr(f, "path", None), **{ch: bm(ch) != missing for ch in ("\u221d", "\u2192", "\u00b2", "\u2082")})
    return out

@app.function(image=cpu_image, cpu=1.0, memory=2048, volumes={"/vol": vol}, timeout=8 * 3600)
def drive(chunk: int = 24, only: list = None, resume: bool = True, force: list = None, tag: str = "run", max_frames: int = None):
    """The render stage, run from inside Modal so it survives the laptop disconnecting (ephemeral apps die with the client).
    Skips chunks whose frames are already on the volume unless the shot is in `force`. Progress: /vol/<project>/render_<tag>.log"""
    import re
    jobs = jobs_for(chunk=chunk, only=only, max_frames=max_frames); total = len(jobs)
    if resume:
        vol.reload(); have = {}
        for d in glob.glob(f"/vol/{PROJECT}/plates/*/"):
            sid = os.path.basename(d.rstrip("/"))
            have[sid] = {int(m.group(1)) for f in os.listdir(d) for m in [re.match(r"f_(\d+)\.png$", f)] if m}
        force = set(force or [])
        jobs = [j for j in jobs if j[0] in force or not all(k in have.get(j[0], ()) for k in range(j[1], j[2] + 1))]
    logp = f"/vol/{PROJECT}/render_{tag}.log"; os.makedirs(f"/vol/{PROJECT}/plates", exist_ok=True)
    def log(line):
        with open(logp, "a") as fh: fh.write(line + "\n")
    log(f"{len(jobs)} of {total} chunks to render, {sum(j[2]-j[1]+1 for j in jobs)} frames, started {time.strftime('%Y-%m-%d %H:%M:%S')} UTC"); vol.commit()
    t = time.time(); bad = []
    for i, res in enumerate(render_chunk.map(jobs, order_outputs=False)):
        log(f"[{i+1}/{len(jobs)}] {res['sid']} {res['f0']}-{res['f1']} ok={res['ok']} {res['secs']}s have={res['have']}")
        if not res["ok"]: bad.append(res); log(res["tail"])
        if (i + 1) % 5 == 0: vol.commit()
    log(f"RENDER STAGE DONE in {time.time()-t:.0f}s, failed chunks: {len(bad)}"); vol.commit()
    return dict(jobs=len(jobs), failed=len(bad), secs=round(time.time() - t))

@app.function(image=cpu_image, cpu=1.0, memory=2048, volumes={"/vol": vol}, timeout=4 * 3600)
def drive_composite(segments: int = 24, tag: str = "comp"):
    """The composite stage run from inside Modal (survives the laptop disconnecting). Progress: /vol/<project>/composite_<tag>.log"""
    logp = f"/vol/{PROJECT}/composite_{tag}.log"; os.makedirs(f"/vol/{PROJECT}/segments", exist_ok=True)
    def log(line):
        with open(logp, "a") as fh: fh.write(line + "\n")
    t = time.time(); bad = []
    log(f"{segments} segments, started {time.strftime('%Y-%m-%d %H:%M:%S')} UTC"); vol.commit()
    for res in composite_chunk.map([(i, segments) for i in range(segments)], order_outputs=False):
        log(f"seg {res['ci']} ok={res['ok']} {res['secs']}s")
        if not res["ok"]: bad.append(res); log(res["tail"])
        vol.commit()
    log(f"COMPOSITE STAGE DONE in {time.time()-t:.0f}s, failed segments: {len(bad)}"); vol.commit()
    return dict(segments=segments, failed=len(bad), secs=round(time.time() - t))

@app.local_entrypoint()
def main(stage: str = "test", chunk: int = 48, shots: str = "", segments: int = 24):
    only = [x for x in shots.split(",") if x] or None
    if stage == "probe_font":
        print(json.dumps(probe_font.remote(), indent=1)); return
    if stage == "probe":
        print(probe.remote()); return
    if stage == "v2test":
        r = v2test.remote(); print("rc", r["rc"]); print(r["log"]); print(r["crash"])
        if r["png"]: open("/tmp/v2test_cloud.png", "wb").write(r["png"]); print("wrote /tmp/v2test_cloud.png", len(r["png"]))
        return
    if stage == "probe_cpu":
        r = probe_cpu.remote(240.0); open("/tmp/probe_cpu_240.png", "wb").write(r["png"]); print(r["size"], r["fonts"]); return
    if stage == "test":
        cfgs = [dict(), dict(VL_DENOISE_GPU="0"), dict(VL_DENOISE="0"), dict(VL_MBLUR="0"), dict(VL_DEVICE="CUDA"), dict(VL_DENOISE="0", VL_MBLUR="0", VL_DOF="0")]
        jobs = [("s42", 1, 2, dict(c, _out=f"/vol/test{i}")) for i, c in enumerate(cfgs)]
        for res in render_chunk.map(jobs): print(json.dumps(res, indent=1))
    elif stage == "test1":
        jobs = jobs_for(chunk=4, only=only or ["s42", "s17"], max_frames=4)
        for res in render_chunk.map(jobs): print(json.dumps(res, indent=1))
    elif stage == "render":
        jobs = jobs_for(chunk=chunk, only=only); print(f"{len(jobs)} chunks, {sum(j[2]-j[1]+1 for j in jobs)} frames"); t = time.time(); bad = []
        for i, res in enumerate(render_chunk.map(jobs, order_outputs=False)):
            print(f"[{i+1}/{len(jobs)}] {res['sid']} {res['f0']}-{res['f1']} ok={res['ok']} {res['secs']}s have={res['have']}", flush=True)
            if not res["ok"]: bad.append(res); print(res["tail"])
        print(f"RENDER STAGE DONE in {time.time()-t:.0f}s, failed chunks: {len(bad)}")
    elif stage == "composite":
        t = time.time()
        for res in composite_chunk.map([(i, segments) for i in range(segments)], order_outputs=False):
            print(f"seg {res['ci']} ok={res['ok']} {res['secs']}s", flush=True)
            if not res["ok"]: print(res["tail"])
        print(f"COMPOSITE STAGE DONE in {time.time()-t:.0f}s")
