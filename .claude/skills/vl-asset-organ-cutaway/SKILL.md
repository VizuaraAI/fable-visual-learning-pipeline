---
name: vl-asset-organ-cutaway
description: How a cut-open organ (the four-chamber heart and any hollow organ after it) must look in Visual Learning chapters: matte fleshy cavities with real wall thickness, never glass bowls. Load before building or fixing any cutaway shot.
---

# Cutaway organ

## Where it appears

Heart chapter, every `cut_rig` shot: s10 (end), s12 to s16, s20 to s23, s25, s41, s46, s50. Built by `heart()` with its cut branch, `cut_rig`, `mat_endo`, `mat_flesh`, `cavity_lights`, `av_leaflets`, `septum_nodes` in `projects/heart/shots.py`.

## What good looks like

- The section is a coronal cut on a slightly tilted plane (0.06 rad about X, 0.08 about Z; larger angles turn the right atrium into a slit) through the whole organ, with a bevelled cut lip that shows real wall thickness: atria thin, ventricles thick, left ventricle thickest.
- Cavities are lobed hollows carved into the muscle, not spheres. Their lining is opaque and matte: Principled with IOR 1.0 (this is what kills the glass look; Specular IOR Level 0 alone does not), roughness about 0.85, no coat, subsurface 0.3 with a red radius, colour pulled about 30 percent toward the muscle (rose-violet on the right side, rose-crimson on the left), a low-frequency flesh blotch, coarse trabecular ridges (wave scale about 5.5, contrast 0.62, bump 0.6) and a steep depth mask: lit near the lip, dark within about 0.24 of the section plane toward the floor.
- Inside each hollow: trabeculae draped on the wall (some forked), papillary muscles as metaball solids in `mat_flesh` (matte, IOR 1.3, fibre bump), chordae as thin solids from the leaflets' free edges, leaflets and cusps that swing about their hinge line (key the child mesh's `rotation_euler`, never a hinge empty's delta rotation), and cells streaming through.
- Four small warm point lights inside the hollows (about 9 W in the ventricles, 4.5 W in the atria) so the lining shades from within; shadows on in Cycles.
- The septum reads as a thick muscular wall; when the narration names it, a gold emission mask on the cut face and the lining lights it up.
- Surface queries for anything draped on the animated organ go through the BVH of the basis mesh (`bvh_of`, `nearest`, `wall_edges`); the beating shape key otherwise puts every coronary and drape inside the wall.

## Misses we have seen, and the cause

- Chambers as glass or plastic bowls: Principled Fresnel going to 1.0 at the hollow's grazing rim. IOR 1.0 fixed it; the depth mask was wired right but too gentle to read.
- A flat window with bulbs and a yellow slab for the septum: the cut was a window, not a full section; rebuilt as the tilted coronal section with an emission mask instead of a slab.
- A camera inside a pink wall in the valve close-up: a boolean DIFFERENCE leaves a flat cap face across the mouth of a cut cup; `strip_planar_caps()` removes it after baking.
- Leaflets swinging sideways: delta rotation on the hinge empty rotates in parent space.
- Coronaries and fat pads buried inside the heart: surface queries answered from the contracted shape key.
- Fat pads as a row of yellow ovals ("corn kernels"): replaced by a faint translucent tint in the coronary grooves.

## How to prove it

Render s12 at frame 78 and s22 at frame 57 (EEVEE 720p), then both in Cycles at 960x540, 32 samples, `VL_DOF=1`. Check: no specular sheen or transparency on any cavity, dark floors and lit lips, papillary muscles and chordae read as solids, cells visible inside, the cut lip shows thickness, the frame edges are navy.
