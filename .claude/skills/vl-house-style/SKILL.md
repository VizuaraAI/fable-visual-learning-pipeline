---
name: vl-house-style
description: The measured Visual Learning house style (format, stage, materials, every interface element, narration) as a checklist; load before designing any new shot, 2D element, palette or outro.
---

# The Visual Learning house style

Measured frame by frame from the channel's own chapter videos; `analysis/STYLE.md` is the full write-up. Everything below is a fact about what the channel does, and the kit reproduces it.

## Format

- 1280x720 at 24 fps on the channel; we render 1920x1080 at 24 fps and the overlay scales from 720p coordinates.
- Narration: a female voice, Hindi with English technical terms, unhurried; true digital silence between sentences; no music bed at all. Labels and equations appear on the word that names them.
- Structure: a cold open on the hero object with the purple title pill (about 1.5 s), a second pill "Complete Chapter" (about 4.5 s), then the "Topic includes / Time line" table until the first section card. Each section opens with a blue card ("1. Chemical reaction") and ends without ceremony. The last frame is "THANKS FOR WATCHING" in a serif face on a dark blue gradient, with a LIKE button and a red subscribe button popping in a second and a half later.

## The 3D stage

- A near-black navy void, one hero prop in the middle third of the frame, one warm key pooling on it, a slow camera move of a few centimetres over ten or twenty seconds. When a ground is needed it is a warm plank floor under a hard-falloff spotlight; frame edges stay dark.
- Materials are simple and saturated: matte off-white wax, glass as a tinted alpha surface with hot highlights, liquids as opaque coloured cylinders, glowing atoms as spheres with a soft halo. Small things are exaggerated so they read from a distance.
- The cinematic version of this (what the five chapters do) keeps the void and the pooled key and adds depth of field, motion blur, dust and atmosphere at density 0.0015 or less, an HDRI at strength 0.12 or less, and a lighting theme per section. Above those values the void turns grey.

## The interface layer (all 2D, drawn by `overlay.py`)

- Section label top left: a dark navy pill with a thin blue border, white bold sans text, wider than the text needs. It stays up for the whole section.
- Channel mark top right: a dark grey diamond with an orange chevron on its left edges and "VISUAL LEARNING" in a serif face with an enlarged V and L.
- Callouts: smaller navy pills next to the thing they name, sometimes with a thin white arrow; anchored labels follow named objects.
- Equations: one wide pill for the whole equation, or one pill per species with white "+" and "→" between them, a thin cyan bracket under the reactants and a small white arrow at the product being discussed.
- Definitions: a wide navy box with a blue border and centred bold serif text typed out word by word, the next two words shown dim.
- Lists: pills stacked vertically, appearing one at a time on the narrator's cue.
- Pure-2D scenes (types of reactions, molecules): glowing circles with element symbols joined by wavy glowing bonds on a dark slate gradient.

## Palette rules for a chapter

- A named palette in `projects/<p>/palette.py`, linear floats for Blender and 8-bit for the overlay, used everywhere; no default saturated primaries, no per-shot colours.
- Semantic colours are fixed for the whole video and shared with the 2D layer: oxygenated red against deoxygenated blue-violet; A, T, G, C each one colour; and so on.
- A lighting theme per section (key temperature, rim colour, accent) inside one coherent chapter look.

When a new element is needed, design it as the channel would: navy, thin blue border, white bold sans, on the narrator's cue.
