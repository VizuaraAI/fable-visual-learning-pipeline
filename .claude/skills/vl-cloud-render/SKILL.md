---
name: vl-cloud-render
description: Render a reviewed chapter on Modal end to end with the checks that prevent wasted GPU hours: deploy, four-frame hero test, full pass, compositor probe, composite, finalize to a master with a contact sheet. Invoke as /vl-cloud-render <project>.
---

# Cloud render

The argument is the project `<p>`. Work from `pipeline/`. If the user has more than one Modal profile, prefix every Modal command with `MODAL_PROFILE=<workspace>`; never change the active profile.

## Before deploying

- The chapter's smoke sheet must have passed review. Do not render a chapter with known misses; a full pass is about an hour and a half of fifty GPUs.
- `projects/<p>/timing.json` must exist (the cloud only sees `pipeline/`; if the timeline reads it from `out/`, every composite segment fails).
- Remove any `shots.py.bak.*` from the project folder; the mount uploads everything under `pipeline/`.
- Check the modification time of `shots.py` and `timeline.py` against the last review; if an agent edited after the review, re-smoke first.

## The sequence

```bash
VL_PROJECT=<p> VL_SAMPLES=384 python3 -m modal deploy modal_render.py
python3 cloud_drive.py start <p> '{"chunk":4,"only":["<hero1>","<hero2>","<hero3>","<hero4>"],"max_frames":4,"resume":false,"tag":"test1"}'
```

Pick the heroes as the shots most likely to differ in Cycles: a cutaway, a close-up with depth of field, anything with glass or a volume, anything with new materials. Poll `python3 cloud_drive.py status <call id>` (RUNNING or DONE) every minute or two; the test takes five to twenty minutes depending on how many GPUs are free. Then:

```bash
python3 cloud_tools.py sample <p> /tmp/<p>_test1.png 2
```

Look at the sheet. Every tile must load and none may be black or uniformly dark; measure mean brightness with Pillow if in doubt. A fast black chunk is a depth-of-field or visibility bug; fix it locally, redeploy, and repeat the test for that shot.

```bash
python3 cloud_drive.py start <p> '{"chunk":16,"resume":true,"force":["<the test shots>"],"tag":"pass1"}'
python3 cloud_tools.py frames <p>        # per-shot counts on the volume; TOTAL and the incomplete list
python3 cloud_tools.py log <p> render_pass1.log   # only to see ok=False lines; never for progress
```

Poll every five to ten minutes. Progress comes from the frame counts on the volume, never from the log's counters. When the status returns DONE, confirm `failed: 0` in the returned dict and `frames` at 100 percent; if a chunk failed, read its log tail, fix, redeploy, and start a pass with `force` for that shot. While the render runs, pull a sample of the finished shots once (`sample <p> ... 1`) and look at it, so a systematic problem is caught early.

```bash
VL_PROJECT=<p> python3 -m modal run modal_render.py --stage probe_cpu     # one composited frame inside a container
python3 cloud_drive.py start <p> '{"segments":24,"tag":"comp"}' drive_composite
python3 cloud_tools.py log <p> composite_comp.log
VL_PROJECT=<p> ./finalize_orig.sh ../out/<p>/work ../out/<p>/narration.wav ../out/<p>/<name>_master_1080p.mp4
```

The probe must write `/tmp/probe_cpu_240.png` with the section pill and logo over a real plate; if it raises, fix the import path problem before compositing. The composite takes about five minutes. The finalize script probes every segment (all but the last must have the same frame count), concatenates, muxes the narration and writes `<master>_sheet.png`.

## Accept

- `ffprobe` the master: duration equals `timing.json`'s total, 1920x1080, 24 fps, an audio stream of the same length.
- Look at the contact sheet; every section pill, the title, the table and the outro card should be visible in it.
- Report the master path, the sheet path, the render and composite times, and the failed-chunk count. Suggest deleting the plates and segments on the volume once the user confirms the master; the volume bills storage.

## If something goes wrong

- Status returns a permission or "volume not found" error out of nowhere: the active Modal profile changed. Re-run with `MODAL_PROFILE=<workspace>`.
- The driver call disappears or restarts: the render continues server-side; re-count frames and restart the driver with `resume: true` if needed.
- A chunk brushes the one-hour timeout: lower `chunk` to 8 for that pass.
- The composite fails on fonts or imports: run the probe, read its traceback; the fix is always in `pipeline/`, then redeploy.
