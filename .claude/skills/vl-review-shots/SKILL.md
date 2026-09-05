---
name: vl-review-shots
description: Review a chapter's smoke sheet, overlay sheet and Cycles look-checks against the six-point bar and write the send-back list that vl-fix-shots consumes. Invoke as /vl-review-shots <project>.
---

# Review a chapter's sheets

Open every sheet under `/tmp/vl_<p>/` (`smoke_sheet.png`, `overlay_sheet.png`, `cycles_*.png`, and any `fix_review.png`) with the Read tool and look at every tile. Then read `/tmp/vl_<p>/REPORT.md` and check the builder's own six-point table against what you see; a builder marks its own work "ok" more often than a reviewer would.

## Judge each 3D shot on the six points

1. Intricate assets: silhouette, secondary forms and surface micro-detail on every hero. A bare sphere, cylinder or slab anywhere near the camera is a miss.
2. Rich environment: dust or particles catching light, atmosphere, an out-of-focus foreground, something behind the hero. An empty void is a miss.
3. Inside-out: the chapter has real dives through a surface, and consecutive shots match-cut.
4. Movement: camera and subject both move; nothing static for more than about three seconds.
5. Concept: the sentence being spoken has its visual proof on screen at that moment (the label, the highlight, the motion).
6. Palette and theme: the chapter's palette, the section's lighting theme, semantic colours consistent with the 2D layer.

## Failure patterns we have already seen

Name them when you see them; the fix skill knows their causes.

- Chambers or hollows that read as glass or plastic bowls (grazing Fresnel).
- A camera buried in a surface, a frame filled by one pink wall (a boolean cap, a focus distance of zero, a camera inside the geometry).
- Organs, hands or animals that read as clusters of balls (unfused metaballs, no skin).
- Washed grey or white translucent tissue (a big subsurface radius plus Fresnel plus too much key).
- A flat pink or flat white disc where a cell or a glowing drop should be.
- Small elements lost in a void; an empty composition at the shot's middle frame.
- Overlay text without its pill, a label overlapping another element, a label anchored to nothing.
- A rust-brown or grey frame instead of the navy void (back-glow or atmosphere too strong).
- Black or uniformly dark Cycles frames (depth of field or visibility, not the compositor).

## Output

A send-back list, one line per shot, in the form the fix skill takes:

```
s17: camera buried in the wall; show the whole valve from inside the ventricle, leaflets shut at 137.5 s
s30 s31: washed grey; warm matte tissue, single-cell capillary wall, cells crimson to violet
s06: fist is a cluster of balls; real closed fist with knuckles and a thumb across
overlay t≈88: 'Ventricles (lower two)' is bare text; make it an anchored pill
```

Mark shots that pass with a single word so the user can see the whole picture, and end with your overall call: ready for the cloud, or send back. Then offer to run `/vl-fix-shots <p>` with the list.
