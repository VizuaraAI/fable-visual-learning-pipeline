# Builder brief: an ORIGINAL cinematic chapter (read AGENT_BRIEF.md first, then this)

Everything in AGENT_BRIEF.md still holds (kit, shotlist/shots/timeline/overlay_ext contracts, testing, deliverables), with these differences:

## There is no reference video. The narration is the spine.
- `projects/<proj>/script.py` is the script (Hindi, English terms). `../out/<proj>/timing.json` is the measured narration layout:
  `total`, `sections` (each with `title`, `card_t0` = when its blue section card starts, `t0` = first sentence, `t1`), and `sentences`
  (each with `t0`, `t1`, `text`, `sec`). The voice is already recorded and laid out; you cannot move it. Cut shots ON sentence
  boundaries (a shot may span several sentences), and put every label / equation / callout at the moment its word is spoken.
- Intro structure (as the channel does it): cold open on the hero (0 .. first card), 'title' pill at ~1.5 s, 'Complete Chapter'
  pill at ~4.5 s, the 'Topic includes / Time line' table from ~6 s to the first card, using the section titles and mm:ss from
  timing.json. Then a 'card' 2D shot (CARD seconds, `bg` = the following 3D shot's id) at every `card_t0`. The last shot is the
  2D 'outro' (from the outro sentence 'थैंक्स फॉर वॉचिंग' to `total`).

## The bar: cinematic, "visually arresting", a deep dive
The client's words: "truly terrific and visually arresting; very high quality assets; cinematic storyline; teach in a very engaging
manner; zoom-ins, pans, rotations, deep dives". Concretely:
- The camera never sits still. Every 3D shot has a designed move: slow push-in, orbit, crane, rack focus, a dive THROUGH a wall or
  membrane into the next space, a pull-back reveal. Use kit.dolly / kit.orbit / kit.rack_focus and your own eased keyframes. Motion
  blur and DOF are on in the cloud (Cycles): give every shot a foreground/background so depth reads.
- Scale transitions are the storytelling device: body → organ → chamber → vessel → cell; cell → nucleus → chromosome → helix →
  base pair. Design consecutive shots so one ends where the next begins (match the framing across the cut).
- Assets are sculpted, not primitives: organic forms from metaballs / subdivided + displaced spheres (noise displacement, smooth
  shading, subsurface), vessels and strands as bevelled Bezier curves (smooth, tapered, with thickness), membranes with solidify
  and a coat, instanced particles (blood cells, molecules) that move with the flow. No visible facets, no hard CSG edges — bevel
  and subdivide everything the camera gets close to. Hero assets deserve 200+ lines each.
- Light like a film: kit.studio() key + rim, kit.hdri() for reflections, kit.atmosphere() for beams in open spaces, emissive accents
  (glowing bases, the oxygen glow in a red cell) with restraint. Keep the navy void: it is the house look. Colour code consistently
  (oxygenated red vs deoxygenated blue-purple; A/T/G/C each one colour, kept through the whole video).
- Every shot should look like a frame someone would screenshot. Aim for 30-45 3D shots for a 7-minute chapter.

## Anatomy / biology must be right
Match the script's facts exactly (chamber layout, valve positions, flow direction, base pairing A-T / G-C, antiparallel strands,
codon → amino acid, 5'→3' direction, ribosome subunits). If a visual would contradict the narration, change the visual.

## Deliverables (same as AGENT_BRIEF.md) plus
- A one-paragraph shot-by-shot 'storyboard' at the top of shotlist.py explaining the journey.
- Every builder tested locally at its mid frame (EEVEE 720p), all mid-frames in /tmp/vl_<proj>/smoke_sheet.png, plus a Cycles
  look-check of the three hero shots at 960x540 / 32 samples with VL_DOF=1.

## BAR RAISED (client, 5 Sep 2026): "very, very beautiful"
The client's exact definition: "Beautiful and very richly designed and intricate 3D assets, captivating storytelling, movements like
pan, zoom, go inside out, transitions, explaining the concept properly." Every 3D shot is reviewed against these six points and
sent back if it misses one:
1. INTRICATE ASSETS, three scales of detail on every hero (silhouette, secondary forms, surface micro-detail: bump, noise, veins,
   striations, pores, rings, small parts). Never a bare primitive on screen. Hero assets deserve 200+ lines each.
2. RICH ENVIRONMENT, never an empty void: floating particles/dust catching light, atmosphere beams (density <= 0.0015), out-of-focus
   foreground elements crossing the frame, a faint glow behind the hero, secondary structures in the background.
3. GO INSIDE OUT: explicit dive/transition shots where the camera passes THROUGH a surface (skin, wall, membrane, pore, lumen) and the
   interior opens up; the pass-through is visible (the surface fills the frame, alpha/emission keyed as we cross). Consecutive shots
   match cut: shot N's last frame framing = shot N+1's first frame.
4. MOVEMENT IN EVERY SHOT, camera AND subject: pan / push-in / orbit / crane / rack focus / slow lens zoom on the camera, and the
   subject itself alive (beating, flowing, turning, unzipping, growing). No plate static for more than ~3 s.
5. EXPLAIN THE CONCEPT: each script sentence gets its visual proof at the moment it is spoken (highlight + label + motion), not just a
   pretty picture.
6. BEAUTIFUL COLOUR PALETTES AND THEMES: a designed, harmonious palette per chapter in projects/<proj>/palette.py (named colours,
   linear floats for Blender + 8-bit for the overlay), used everywhere: no default saturated primaries, no random per-shot colours.
   Give each section its own lighting theme (key colour temperature, rim colour, accent) inside one coherent chapter look, keep the
   navy void as the ground, and make the semantic colours (oxygenated vs deoxygenated, A/T/G/C/U, amino acids) consistent across
   every shot AND the 2D overlay. Materials carry the palette too: coat, subsurface tint and emission accents in matching hues.
Deliverable: a self-review table in /tmp/vl_<proj>/REPORT.md (shot id -> which of the six points it demonstrates), after fixing misses.
