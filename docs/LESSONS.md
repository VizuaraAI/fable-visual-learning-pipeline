# Lessons from the five chapters

Everything that cost us time, with the fix that worked. Read this before your first cloud render and again when something looks wrong and you don't know why.

## Blender 5.2, headless

- The API moved. `Action.fcurves` is gone (slotted actions: layers, strips, channelbags); use `kit.kf` and `kf_ease` and never touch fcurves directly. The compositor is `scene.compositing_node_group`, a node group with a `NodeGroupOutput`; Glare, Blur, EllipseMask and Lensdist options are input sockets (`inputs['Type'].default_value = 'Bloom'`); the math, mix and map-range nodes are the shader family (`ShaderNodeMath`, `ShaderNodeMix`, `ShaderNodeMapRange`). A half-built compositor tree renders black frames: `kit.reset()` builds the one we use, and on any failure detach it.
- The GPU compositor segfaults without a display context. The cloud sets `scene.render.compositor_device = 'CPU'`.
- OptiX denoising wants the driver's `nvoptix.bin`, which the containers don't have. Denoise with OpenImageDenoise.
- EEVEE renders refractive transmission opaque when headless. Glass is an alpha-blended Principled surface, which also matches the channel's look.
- After `shape_key_add()`, `closest_point_on_mesh` and `ray_cast` on the object answer from the active shape key, not the basis. Every drape on an animated organ landed inside the wall until the surface queries went through a BVH built from the basis mesh (`bvh_of`, `nearest`, `wall_edges` in the heart's `shots.py`).
- A boolean DIFFERENCE leaves a closed solid, so a cup cut open still has a flat cap across its mouth. The heart's `strip_planar_caps()` deletes those faces after baking. This was the "camera inside a pink wall" bug.
- `delta_rotation_euler` keyed on a hinge empty rotates in the parent's space, not about the hinge's own axis. Key the child mesh's `rotation_euler` instead. Every valve leaflet in the heart chapter swung sideways until this was found.
- `flicker()` and anything that keys object scale will collapse a shape made by non-uniform object scale (the flame volume's stretch) into a ball. Bake shapes into vertices.
- Cycles draws a point light's radius as a bright sphere wherever the light is seen through glass. Give point lights a radius of about 0.05 in Cycles and never disable `visible_transmission` (that stops the light illuminating what is behind the glass).

## Materials and lighting

- "Glass bowl" hollows in a matte organ were the Principled dielectric Fresnel going to 1.0 at grazing angles. `Specular IOR Level = 0` only zeroes the head-on reflection; `IOR = 1.0` removes the rim. Pair it with a steep depth mask (lit lip, dark floor) and small warm lights inside the hollows.
- Objects inside closed refractive glass or under water render dark because caustics are off. The glass and liquid materials mix in a Transparent BSDF for shadow and diffuse rays via Light Path.
- EEVEE ghosts a translucent sphere around a bright object seen through an alpha-blended tile with subsurface. It does not exist in Cycles. Dithered tiles with no subsurface and IOR 1 reduce it; check Cycles before chasing it further.
- HDRI strength above about 0.12 or atmosphere density above 0.0015 turns the navy void grey.
- Shadowless lights are an EEVEE speed trick only. Keep `use_shadow` on in Cycles (the pipeline gates it on the engine).

## Smoothness

The first preview came back "many sharp edges, not smooth". The causes were 48-vertex lathes with 5-point profiles, icosphere subdivision-1 pebbles and 12 TAA samples. Catmull-Rom resampled profiles at 128 segments, UV spheres with smooth shading, cylinders of 32 to 128 vertices, `render.filter_size = 1.5` and 16 TAA samples fixed it; 24 samples gave nothing visible for 25 percent more time. The void makes every facet visible, so never ship a low-poly primitive.

## The laptop

- An 8 GB M1 runs one Blender at about 1.6 s per EEVEE frame; two workers run at 2.5 to 3.7 s each and any post-processing alongside makes Blender four times slower through swap. Render first, post-process after.
- macOS has no `flock` and its ffmpeg has no `drawtext`; the scripts avoid both.
- Another process on the same machine can rewrite `~/.modal.toml` and switch the active profile. Every Modal command then sees the wrong workspace ("Volume not found", empty container list, permission denied). Prefix commands with `MODAL_PROFILE=<workspace>` rather than flipping the active profile back.

## The cloud

- `modal run` apps are ephemeral and die when the client's heartbeat drops; two renders were killed at the same instant by one network blip. Deploy the app and start the server-side `drive` through `cloud_drive.py`. It skips chunks whose frames are on the volume (unless the shot is in `force`) and logs to `/vol/<p>/render_<tag>.log`.
- Never read progress from that log. The driver can be restarted by Modal inside one call and the counters start again; count frames on the volume (`cloud_tools.py frames`).
- Heavy shots run 16 to 40 s per frame at 256 samples and up to 44 s at 384. Keep chunks at 16 to 24 frames so nothing brushes the one-hour timeout.
- The workspace caps around fifty GPU containers in total, whatever the GPU type, so two chapters' renders serialise. Cancel a queued driver that has produced nothing rather than leaving it to starve.
- A redeploy does not kill a running driver; it keeps its version. The new version serves the next start.
- The cloud mount is `pipeline/` only. A chapter's `timeline.py` that reads `../out/<p>/timing.json` at import passes locally and fails every composite segment in the cloud. Keep a copy of `timing.json` in `projects/<p>/` and run `--stage probe_cpu` before `drive_composite`.
- A partial mp4 does get committed to the volume when an ephemeral composite dies mid-run, and the master comes out short. `finalize_orig.sh` probes every segment and refuses to concatenate if one is broken or if the lengths disagree.
- `ffprobe -show_entries stream=nb_read_frames,duration -of csv` prints the fields in the stream's order (duration first), not the order you asked for.

## Narration

- The reference videos' own auto-captions are the exact script, cleaned of a dozen mis-transcriptions (`FIXES` in `narration.py`); caption fetches get rate-limited, so fetch subtitles in a separate `yt-dlp` call with `--sleep-subtitles`.
- Speed 1.05 ran an eight-minute script to 9:24; 1.15 is the channel's pace. Cut sentences rather than speeding up further.
- The house narration is a female voice with English technical terms, true silence between sentences and no music bed.

## Process

- A subagent's work survives a session cut only on disk. Before relaunching one, diff its scratch files against the merged module (an `ast` compare takes a minute) instead of guessing what was lost.
- An agent can keep editing after you deploy. Check the file's modification time against the deploy time before starting a full render.
- Every review sample should come from the volume (`cloud_tools.py sample`), never from a log line that says `ok=True`; a chunk can exit cleanly and still be black.
