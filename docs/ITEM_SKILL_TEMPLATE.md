# How to write a skill for one item

When a shot is not right, the fix goes into the code and the standard goes into a skill, so the next chapter starts from what you already know. One skill per item: an asset (a cutaway organ, a cell, a molecule, a vessel), a kind of shot (a dive through a membrane, a tracking shot that follows a drop), a look (a section's lighting theme, the outro), or the narration.

Create `.claude/skills/<name>/SKILL.md`. Names start with `vl-` and say what the item is: `vl-asset-leaf-cross-section`, `vl-shot-membrane-dive`, `vl-look-section-lighting`. Claude Code lists the skill behind `/` as soon as the file exists.

Copy this and fill it in. Keep it under a page; what makes a skill useful is precision, not length.

```markdown
---
name: vl-asset-<item>
description: How <the item> must look and move in Visual Learning chapters; load before building or fixing any shot that shows it.
---

# <The item>

## Where it appears
Which chapters and shots so far, and the builder functions that make it (file and function names).

## What good looks like
The three scales of detail (silhouette, secondary forms, surface micro-detail), the materials with the
settings that worked (IOR, roughness, subsurface, coat, emission), the palette entries it uses, and how it
moves. Write numbers, not adjectives: "membrane alpha 0.93 at the centre, 0.5 at the rim" beats "translucent".

## Misses we have seen, and the cause
One line each: what the reviewer saw, what the real cause was, what fixed it. This is the part that saves the
next builder the most time.

## How to prove it
Which shot and frame to render, at what settings (EEVEE 720p mid frame; Cycles 960x540, 32 samples, DOF on),
and what to check in the PNG before calling it done.
```

Then use it. In a fix request name the skill: `/vl-fix-shots photo s12: chambers, apply vl-asset-organ-cutaway`. In a build, `vl-new-chapter` reads every `vl-asset-*`, `vl-shot-*` and `vl-look-*` skill in the folder before it writes a builder, so a skill you wrote for the heart chapter shapes the first draft of the next one.

Two worked examples are in the skills folder: `vl-asset-organ-cutaway` and `vl-asset-blood-cells`.
