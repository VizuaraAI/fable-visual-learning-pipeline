# How Visual Learning makes its videos, and how this recreation matches it

I went through the channel, the website's demo lesson, and the two chapter videos you sent (Chemical Reactions and Equations, The Fundamental Unit of Life) frame by frame, one frame every three seconds, and then a few full-resolution stills for the interface details. What follows is what the videos actually do, and the choice I made for each element when rebuilding one of them. The reference for the rebuild is the 13:12 Class 10 chapter "Chemical Reactions and Equations".

## The format

Every video is 1280x720 at 24 frames per second. The narration is Hindi with the technical vocabulary in English ("कैल्शियम ऑक्साइड वाटर के साथ रिएक्ट करता है"), read by a female voice at a steady, unhurried pace. Between sentences the track drops to true digital silence; there is no music bed at all, which is a little unusual for the genre and is one of the reasons the videos feel calm. The narration and the animation are locked together: a label appears on the word that names it, an equation grows one species at a time as the sentence reaches it.

The structure of a chapter video is fixed. A cold open on a hero object with the purple title pill, a second pill reading "Complete Chapter", then a "Topic includes / Time line" table that lists the sections with their timestamps (the same timestamps go in the YouTube description). Each section starts with a blue card ("1. Chemical reaction") and ends without ceremony. The last frame is "THANKS FOR WATCHING" in a serif face on a dark blue gradient, with a LIKE button and a red subscribe button popping in a second and a half later. The narration matches it: "थैंक्स फॉर वाचिंग, इफ यू लाइक दिस वीडियो प्लीज लाइक एंड सब्सक्राइब आवर चैनल".

## The 3D stage

The scenes are rendered in a real-time engine (the reflections, the soft bloom around every emissive surface and the slightly plasticky specular highlights all point to Unity or Eevee; nothing in the frames requires a path tracer). The stage is nearly always the same: a near-black navy void, one hero prop in the middle third of the frame, one warm key light pooling on it, and a slow camera move of a few centimetres over ten or twenty seconds. When a scene needs a ground, it is a warm plank floor lit by a spotlight with a hard falloff, so the edges of the frame stay dark. Two scenes use a translucent "projector" cone of light instead of a floor (the plant, the food on the plate), and it is a plain translucent cone mesh, not a volumetric.

Materials are simple and saturated: a matte off-white candle, glass drawn as a tinted alpha surface with hot highlights rather than refraction, liquids as opaque coloured cylinders inside the glass, glowing atoms as spheres with a soft halo. Small things that need to read from a distance are exaggerated: the copper powder is a pile of orange pebbles, ferrous sulphate crystals are bright green beads, rust particles are pinkish rings that drift through the whole frame. Human figures are a translucent red mannequin on a blue slab.

## The interface layer

Everything typographic sits in a flat 2D layer on top of the render, and it is very consistent:

- A section label at the top left: a dark navy pill with a thin blue border, white bold sans text, wider than the text needs (it looks like the text is left-aligned inside a fixed-width box). It stays up for the whole section.
- The channel mark at the top right: a dark grey diamond with an orange chevron on its left edges and "VISUAL LEARNING" in a serif face with an enlarged V and L.
- Callouts: smaller versions of the same navy pill placed next to the thing they name, occasionally with a thin white arrow.
- Equations: either one wide pill holding the whole equation ("CaO + H₂O → Ca(OH)₂ + Heat"), or one pill per species with white "+" and "→" between them, a thin cyan bracket underneath the reactants, and a small white arrow pointing at the product being discussed.
- Definitions: a wide navy box with a blue border and centred bold serif text, typed out word by word with the next two words shown dim.
- Lists: pills stacked vertically, appearing one at a time on the narrator's cue.
- The "types of reactions" and molecule scenes are pure 2D: glowing circles with element symbols joined by wavy glowing bonds, on a dark slate gradient.

## What the recreation does

The rebuild is a script-driven pipeline rather than a hand-animated project, so the same recipe can produce any chapter. Blender 5.2 renders the 3D plates headlessly from a small asset library built entirely from primitives (candle, flame, dome, jar, test tube, beaker, tongs, spirit lamp, tripod and gauze, china dish, nails, rack, food dome, mannequin, plant), one script per shot with the camera moves and animation keyed to the reference timings. A second stage draws the interface layer in Python (PIL) with a timeline of 100 events read off the reference frame by frame, and streams the finished frames straight into x264. The narration is the reference's own script (taken from its captions, then cleaned of a dozen mis-transcriptions) voiced with an ElevenLabs Hindi-capable female voice and placed on the original sentence timestamps, so the voice lands on the same visuals. The gaps between sentences are left silent, like the original.

Two deliberate compromises. Most plates are rendered at 12 frames per second and upsampled to 24 with motion-compensated interpolation (the camera moves are slow enough that this is invisible; the spark and pouring shots are rendered at the full 24). And the props are simplified models, not the reference's assets: the tongs, the retort stand and the food are recognisable stand-ins, not copies.

Files: the shot list is `pipeline/shotlist.py`, the shot builders `pipeline/shots.py`, the asset kit `pipeline/kit.py`, the interface kit `pipeline/ui.py`, the event timeline `pipeline/timeline.py`, the compositor `pipeline/overlay.py`, the narration `pipeline/narration.py`, and `pipeline/assemble.py` puts it together.
