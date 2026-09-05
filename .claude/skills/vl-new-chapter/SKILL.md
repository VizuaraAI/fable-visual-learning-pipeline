---
name: vl-new-chapter
description: Build a complete Visual Learning chapter from its narration: storyboard, shot list on the sentence boundaries, palette, one Blender builder per 3D shot, overlay timeline, smoke sheets, Cycles look-checks and a six-point report. Invoke as /vl-new-chapter <project> once projects/<project>/timing.json exists.
---

# Build a chapter

You are the builder for one chapter of a Visual Learning video. The argument is the project name `<p>`; everything lives in `pipeline/projects/<p>/`. Work from `pipeline/` for every command.

## Read first, in this order

1. `pipeline/AGENT_BRIEF.md` (the kit contracts, shot dict fields, testing, deliverables) and `pipeline/ORIGINAL_BRIEF.md` (original chapters and the six-point bar at the end).
2. `analysis/STYLE.md` and the `vl-house-style` skill.
3. `pipeline/kit.py` in full. Do not edit it.
4. Every `vl-asset-*`, `vl-shot-*` and `vl-look-*` skill in `.claude/skills/`: they are the standards the channel's video maker has written down, and a builder that ignores them gets sent back.
5. The worked examples: `projects/heart/` (an original chapter: `STORYLINE.md`, `shotlist.py` with its storyboard, `palette.py`, `shots.py`, `timeline.py`, `overlay_ext.py`) and `projects/chem/` (a recreation).
6. The chapter's inputs: `projects/<p>/script.py` and `projects/<p>/timing.json` (from `vl-narration`), or for a recreation `projects/<p>/transcript_hi.txt` and its reference contact sheets.

## What to build

- `shotlist.py`: a one-paragraph storyboard at the top, then `SHOTS` with every cut on a sentence boundary from `timing.json`, the intro structure the channel uses (cold open, title pill at about 1.5 s, "Complete Chapter" at about 4.5 s, the topic table until the first card), a 2D `card` shot at each section's `card_t0` with `bg` set to the following 3D shot, and the 2D `outro` last. Aim for 30 to 45 3D shots for a seven-minute chapter, and `TOTAL` equal to the narration's total.
- `palette.py`: named colours (linear floats for Blender, 8-bit for the overlay), the semantic colours kept consistent across every shot and the overlay, and a lighting theme per section.
- `shots.py`: one builder `def name(nf, rfps, dur)` per 3D shot, starting with `reset()`, built from the kit, keyframed with `F(sec, rfps)`, camera from `camera()`, `dolly()` or `orbit()`. Hero assets deserve 200+ lines each. Anchors for 2D labels are objects named as the shot dict's `anchors` list.
- `timeline.py`: every label, table, callout, equation and card as `add(kind, t0, t1, ...)` events at the moment the word is spoken. New 2D kinds go in `overlay_ext.py`, never in `overlay.py`.

## How to work

- Write builders in storyline order and smoke-render each one at its middle frame as soon as it exists (EEVEE 720p, the command in `CLAUDE.md`). Look at every PNG. One Blender process at a time.
- Keep each shot under about 250 objects and 16 s per EEVEE frame at 720p.
- Match cut: a shot's last frame framing is the next shot's first.
- When a builder fails, fix it before writing the next one. Never leave a shot that renders black or empty.

## Deliverables, all under /tmp/vl_<p>/

- `smoke_sheet.png`: the middle frame of every 3D shot, tiled six per row with `<sid> <builder>` captions.
- `overlay_sheet.png`: twelve composited timestamps spread across the sections (`overlay.PLATES = '/tmp/vl_<p>'`).
- `cycles_<sid>.png` for three hero shots (960x540, 32 samples, `VL_DOF=1`).
- `smoke_log.txt`: one line per shot with build seconds, objects, polygons and EEVEE seconds per frame.
- `REPORT.md`: what was built, the design decisions, a table scoring every shot on the six points, and an honest list of what still misses.

Finish by telling the user where the sheets and the report are and which shots you would send back yourself.
