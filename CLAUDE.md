# Rules for working in this repository

This is the Visual Learning video pipeline: Blender 5.2 shot builders driven by Python, a Pillow interface layer, ElevenLabs narration and a Modal cloud render. Read `README.md` for the workflow and `analysis/STYLE.md` for the house style before building anything. The builder briefs are `pipeline/AGENT_BRIEF.md` (kit contracts, testing, deliverables) and `pipeline/ORIGINAL_BRIEF.md` (original chapters and the six-point bar). The skills under `.claude/skills/` package the workflow; invoke them for chapter builds, reviews, fixes and cloud renders.

## The bar

Every 3D shot is judged on six points and sent back if it misses one: intricate assets (three scales of detail, never a bare primitive), a rich environment (never an empty void), inside-out dives with match cuts, movement of camera and subject in every shot, the concept proven at the moment its sentence is spoken, and a designed palette with a lighting theme per section. Look at every PNG you render before calling it done.

## Hard rules

- `pipeline/kit.py` is shared by every chapter. Do not edit it for one chapter's need; put project helpers in `projects/<p>/shots.py`. If kit.py must change, say so explicitly and re-smoke a shot from every existing chapter.
- Never change a chapter's `shotlist.py` cut times or an anchor object name during a fix: the overlay timeline follows them.
- One Blender process at a time on an 8 GB machine. Never run two renders in parallel locally; never post-process while a render runs.
- Blender is 5.2: no `Action.fcurves` (use `kit.kf` / `kf_ease`), the compositor tree is built by `kit.reset()` (never build your own; a half-built tree renders black), Glare and Blur options are input sockets, EEVEE transmission renders opaque (use alpha-blended Principled), and after `shape_key_add()` surface queries answer from the active key (use the BVH helpers).
- Keys: `ELEVENLABS_API_KEY` comes from the environment or a git-ignored `.env`. Never write a key into code, a commit, a log or a chat. A key that appears anywhere visible is burned; say so and ask for it to be rotated.
- Cloud: deploy after every code change (the mount is uploaded at deploy time); start renders through `cloud_drive.py` (the server-side `drive`), never through a bare `modal run`; count progress with `cloud_tools.py frames`, not the log; keep `timing.json` inside `projects/<p>/`; run `--stage probe_cpu` before `drive_composite`; prefix Modal commands with `MODAL_PROFILE=<workspace>` when more than one profile exists.
- Prove before spending: four cloud frames of two hero shots before a full pass; a local Cycles look-check (960x540, 32 samples, `VL_DOF=1`) for any material or lighting change.
- Deliverables of a build or fix go to `/tmp/vl_<p>/`: a smoke sheet of every 3D shot's middle frame, an overlay sheet of twelve composited timestamps, Cycles look-checks of the hero shots, a smoke log with one line per shot (build seconds, objects, polygons, EEVEE seconds per frame) and a report with the six-point table.

## Testing commands

```bash
cd pipeline
VL_PROJECT=<p> /Applications/Blender.app/Contents/MacOS/Blender -b --python render_shot.py -- s05 /tmp/vl_<p> 10 10   # one EEVEE 720p frame
VL_ENGINE=CYCLES VL_RES=960x540 VL_SAMPLES=32 VL_DOF=1 VL_PROJECT=<p> /Applications/Blender.app/Contents/MacOS/Blender -b --python render_shot.py -- s05 /tmp/vl_<p>/cyc 10 10
VL_PROJECT=<p> python3 -c "import overlay; overlay.PLATES='/tmp/vl_<p>'; overlay.render_frame(123.0).save('/tmp/vl_<p>/ov_123.png')"
```

Set `VL_BLENDER` if Blender is not at the default path. Keep object counts under about 250 per shot and EEVEE under 16 s per frame at 720p; the cloud times out a chunk at one hour.
