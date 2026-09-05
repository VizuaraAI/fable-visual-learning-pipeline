# Builder brief: one Visual Learning chapter video per project

You are building the 3D shots (and the overlay timeline) for ONE chapter video in the Visual Learning house style, inside this pipeline. The bar is "cinematic": the client's words were "much more beautiful 3D objects", "depth and detail in the Blender objects", "no sharp edges, no bad-looking visuals". Every prop must be modelled with real detail (rims, thickness, bevels, subdivision, wear, small parts), never a bare primitive.

## Where things live (pipeline root = this directory)
- `kit.py` — shared asset/material/light/camera kit. READ IT FULLY. Do not edit it; put project-specific helpers in your own `projects/<proj>/shots.py`.
- `projects/<proj>/shotlist.py` — `SHOTS` list + `TOTAL` seconds. Shot dict fields: `id` ('s01'…), `t0`,`t1` absolute seconds, `mode` '3d'|'2d', `rfps` (12 or 24; the cloud forces 24), `builder` (function name in your shots.py), optional `hold` (seconds after which the plate is static), optional `anchors` (list of object names, or 'auto' = objects named Hp*/Op*/Rp* get 2D markers), for 2d shots `builder` in {'card','molecules','list','displacement_eq','outro'} plus `text`/`bg` where the compositor expects them (see projects/chem for the exact usage).
- `projects/<proj>/shots.py` — builders `def name(nf, rfps, dur)`: call `reset()` first, build the scene, keyframe with `F(sec, rfps)` for frames, create the camera with `camera()`/`dolly()`/`orbit()`. Look at projects/chem/shots.py for 36 worked examples.
- `projects/<proj>/timeline.py` — `E` list of overlay events built with `add(kind, t0, t1, **kw)`. Kinds implemented in `overlay.py`: label, title, table, card, rect, callout, pill, text_eq, list, eqpill, equation, defbox, arrow, anchor_text, anchor_particles, molecules, disp_eq, listbg, outro. All coordinates in 1280x720 space (the compositor scales). If your video needs a new 2D element, add its drawing function to your project's `overlay_ext.py` (function `draw_extra(img, e, t, spec, ui, helpers)`) — the compositor calls it for unknown kinds — instead of editing overlay.py.
- `projects/<proj>/transcript_hi.txt` — the reference's own Hindi narration with timestamps: this is the exact script AND the timing source for every visual beat.
- `projects/<proj>/refs/` — contact sheets of the reference (each tile = one frame every N seconds, 6 columns; sheet k, row r, col c → t = k*48*N + (6r+c)*N).
- `projects/<proj>/fixes.py` — `FIXES = [(wrong, right), …]` caption mis-transcriptions to correct, `SENTENCE_FIXES = {}`.

## Conventions that must hold
- Camera at -Y looking +Y, Z up. Hero at the frame's middle third. Slow eased camera moves (dolly/orbit), never static for more than ~6 s unless the reference is static.
- House lighting: `studio()` (warm pooled key, dim cool fill, cool rim), `world()` dark navy, `atmosphere()` for beams, `hdri()` for reflections. Volumetric `light_cone()` where the reference has a projector cone.
- Materials: `mat_plastic` (saturated, coat), `mat_metal`, `mat_glass_real` + `solidify()` for glassware, `mat_liquid_real`, `mat_emit` for glows, `mat_wood_pbr`/`floor_wood_pbr` for floors. Subsurface on wax/food/organic tissue. Everything smooth-shaded with enough segments (cylinders ≥ 64, spheres ≥ 48x24, lathes via `glass_vessel()` with rich profiles).
- Flames: `flame_volume()` (volumetric) — never the old mesh flame. Smoke via `smoke_wisp()`.
- Particles/markers that get 2D labels must be objects named Hp*/Op*/Rp* (or listed in `anchors`).
- Keep object counts sane (< ~600 objects per shot; use arrays/instances for repeats).

## Testing (local, cheap — do not run heavy renders on this laptop)
`cd pipeline && VL_PROJECT=<proj> /Applications/Blender.app/Contents/MacOS/Blender -b --python render_shot.py -- s05 /tmp/vl_<proj> 10 10` renders one EEVEE frame (720p) of shot s05 at frame 10 into /tmp/vl_<proj>/s05/. Look at it (Read the PNG). For a Cycles look-check use `VL_ENGINE=CYCLES VL_RES=960x540 VL_SAMPLES=32` and add `VL_DOF=1`. Test EVERY builder at least once at its mid frame, fix errors, and view a contact sheet of all mid-frames before you finish. Also dry-run the overlay: `VL_PROJECT=<proj> python3 -c "import overlay; overlay.PLATES='/tmp/vl_<proj>'; overlay.render_frame(123.0).save('/tmp/vl_<proj>/ov_123.png')"`.
- Blender here is 5.2 (slotted actions: never touch `action.fcurves`; use kit.kf/kf_ease). Compositor is set up by kit.reset(); do not build your own.

## Deliverables (report these paths and a 1-paragraph summary when done)
1. `projects/<proj>/shotlist.py`, `shots.py`, `timeline.py`, `fixes.py`
2. `/tmp/vl_<proj>/smoke_sheet.png` — mid-frame of every 3D shot, tiled, and `/tmp/vl_<proj>/overlay_sheet.png` — 12 composited timestamps.
3. A short list of anything you could not match faithfully and why.
