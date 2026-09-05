---
name: vl-fix-shots
description: Fix a chapter's shots from a send-back list without breaking the rest: measure the cause first, apply any named item skill, render proof frames, re-smoke every shot, write a fix report. Invoke as /vl-fix-shots <project> <miss list>.
---

# Fix shots from a send-back list

The argument is the project `<p>` followed by the miss list (one item per shot or per overlay moment). Work from `pipeline/`. Before touching code read `CLAUDE.md`, the two briefs, `docs/LESSONS.md`, the chapter's `REPORT.md` under `/tmp/vl_<p>/`, and every item skill the list names or that covers the item (`vl-asset-*`, `vl-shot-*`, `vl-look-*` in `.claude/skills/`). If an item skill exists for the thing you are fixing, its "what good looks like" section is the specification.

## Method

1. Reproduce: render the shot's failing frame yourself (EEVEE 720p) and look at it.
2. Measure before you change. The three hardest heart problems were not what they looked like: the "glass bowls" were Fresnel at grazing angles, not the depth mask; the "pink wall" was a boolean cap face on the cut plane, found by casting the camera's centre ray; the ghost spheres around capillary cells existed only in EEVEE. Instrument a Blender run (ray casts, material swaps, one-object hides) and compare renders before rewriting a builder.
3. Change the smallest thing that fixes the cause. Do not touch `kit.py`, the shot list's cut times or any anchor name, and do not change shared assets (the exterior heart, the great vessels) unless the list says so.
4. Prove it: render the touched shots' middle frames (and the specific frames the list mentions) into `/tmp/vl_<p>/fix/<sid>/`, look at each, and for any material or lighting change also render a Cycles look-check (960x540, 32 samples, `VL_DOF=1`).
5. After the list is done, re-smoke every 3D builder at its middle frame, tiled into `/tmp/vl_<p>/fix/smoke_sheet2.png`, with a log line per shot. A fix that breaks an untouched shot is not a fix.
6. If the list names an overlay moment, dry-run the compositor at that time (`overlay.PLATES` pointing at your frames) and save the PNG.
7. Write `/tmp/vl_<p>/FIX_REPORT.md`: per item what changed (functions touched), the PNG that proves it, the root cause in one line, and anything not achieved with the reason.

## Rules of the machine

One Blender process at a time. Keep object counts under about 250 and EEVEE under 16 s per frame at 720p. Shadowless lights are an EEVEE-only speed trick; in Cycles shadows stay on. Back up `shots.py` before large edits and remove the backup before any deploy.

## When you are done

Report the proof PNGs and the report path, and say which fixes were verified in Cycles. If a fix produced a reusable standard (a material recipe, a framing rule, a root cause the next builder should know), propose an item skill for it using `docs/ITEM_SKILL_TEMPLATE.md`, or extend the one that already covers the item.
