---
name: vl-asset-blood-cells
description: How red blood cells must look and move in Visual Learning chapters, from a stream of instanced cells in a vessel to the hero cell the camera dives into. Load before building or fixing any shot with blood cells, capillaries or haemoglobin.
---

# Blood cells

## Where it appears

Heart chapter: every vessel and chamber shot (`rbc_flow`, `cut_streams`, `stage_streams`), the capillary shots s30 and s31 (`cap_scene`, `endothelial_tube`, `mat_tissue`), the hero cell and haemoglobin in s32 (`rbc_mesh`, `rbc_hero`, `haemoglobin`, `globin_chain`). DNA chapter: the sickle-cell shot s47. All in `projects/<p>/shots.py`.

## What good looks like

- Shape: a biconcave disc from `rbc_mesh`; for the hero, the deep profile (centre at 0.06 R, rim torus at 0.3 R) so the dimple shades as a bowl under a raking area light.
- Colour is semantic and consistent with the overlay: oxygenated crimson (`OXY`, lit `OXY_LIT`), deoxygenated blue-violet (`DEOXY`, `DEOXY_LIT`) from the palette. In a capillary the colour is a ramp along the path (`ox_keys`), crimson to violet as the oxygen leaves, never a switch.
- Membrane material: a translucent crimson with subsurface (red radius), a soft coat, faint emission the shot can key up; three scales of surface detail on the hero (coarse undulation, a Voronoi cobblestone with darker borders, fine grain); alpha near-opaque (0.93 to 0.99) except when the camera crosses it.
- Motion: cells are instanced along bevelled curve paths with `rbc_flow`; on an open path they recycle (they used to pile into a "worm ball" at the end); in a capillary they go single file and squeeze; in a chamber they stream with the beat; a valve that shuts sends a few back.
- Scale: cells are small relative to the vessel (about a fifth of the lumen in an artery section) so the vessel reads as the hero; the hero cell fills the middle third when it is the subject.
- The capillary wall is one layer of flat endothelial cells: dithered translucent tiles (alpha about 0.58, no subsurface, IOR 1), darker junction gaps, gentle bulges over plum nuclei with a little emission; the tissue around it is warm matte packed cells (Voronoi borders a shade darker, groove bump, subsurface 0.18, IOR 1, no coat, key light about 2100 W rather than 2800).
- The membrane crossing (s32, 3.4 to 4.6 s): the disc turns to face the camera, alpha keyed 0.93 to 0.5 to 0.05 with a short crimson flash, then the haemoglobin is the hero mid-frame: four globin chains in two colours, four haem plates with irons glowing brighter as oxygen docks, out-of-focus haemoglobins behind.

## Misses we have seen, and the cause

- Washed grey or white capillary tissue: a large subsurface radius plus Fresnel plus a 2800 W key; matte packed cells with IOR 1 and a dimmer key fixed it.
- Ghost spheres around cells in the capillary: EEVEE-only ghosting of alpha-blended tiles with subsurface over a bright object; clean in Cycles; dithered tiles without subsurface reduce it.
- A flat pink hero cell: no dimple, one scale of detail, membrane too transparent; the deep profile, cobblestone plus grain and near-opaque alpha fixed it.
- A "worm ball" of cells at the end of an open path: no recycling in `rbc_flow`.
- Empty lumens in the pressure shots: cells wrapped nowhere; same recycling fix.
- The hero's membrane at 30 s per EEVEE frame: subsurface scale 0.2 over a frame-filling membrane; 0.06 renders the same and seven times faster.

## How to prove it

Render s28 at frame 132, s30 at frame 66, s31 at frame 98, and s32 at frames 25, 50 and 76 (EEVEE 720p), then s31 and s32 in Cycles at 960x540, 32 samples, `VL_DOF=1`. Check: discs read as biconcave, the colour ramp is visible along the capillary, the wall is one cell thick with nuclei, the tissue is warm and matte, the hero's dimple shades as a bowl, and the haemoglobin sits whole in the middle of its frame.
