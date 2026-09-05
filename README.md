# Visual Learning video pipeline

This repository is the complete pipeline behind five Visual Learning chapter videos made in September 2026: three recreations of existing chapters (Chemical Reactions and Equations, The Fundamental Unit of Life, Gravitation) and two original chapters written from a blank page (Human Heart and Circulation, DNA: From Gene to Protein). Everything a video needs is here except the finished videos themselves, which are too large for GitHub and were shared separately: the Blender asset kit, the shot builders of all five chapters, the 2D interface layer, the narration tooling, the cloud render, and the instruction files that let Claude Code do the building.

The rest of this README is a tutorial. It goes from an empty laptop to a finished chapter in the order you would actually do it, and it ends with the part that matters most in practice: what to do when a video is not good enough yet.

Contact sheets of the finished chapters are in `docs/sheets/`, so you can see what the output looks like before installing anything.

## How a video gets made here

Before the commands, the idea. The narration is the spine of every video. A chapter starts as a script (Hindi sentences with the technical terms in English, exactly how the channel narrates), the script is read by a synthetic voice one sentence at a time, and the pauses between sentences are laid out so we know, to the frame, when every word is spoken. Every visual decision hangs off that timing: shots are cut on sentence boundaries, and a label or an equation appears at the moment its word is said.

The pictures come from two layers. The 3D layer is Blender, driven entirely by Python: `pipeline/kit.py` is a kit of primitives, materials, lights and camera moves, and each chapter has a `shots.py` with one function per shot that builds the scene from that kit and keyframes it. The 2D layer is the interface the channel is known for (the navy pills with a thin blue border, the purple title, the "Topic includes / Time line" table, the diamond logo), drawn with Pillow by `pipeline/overlay.py` from a per-chapter `timeline.py`. The compositor puts the two together and the narration goes on top.

Rendering happens twice. On the laptop, every shot is rendered at one frame in EEVEE at 720p, which takes a few seconds per shot and gives you a contact sheet to review. Once the sheet passes, the whole chapter is rendered in Cycles on GPUs in Modal (1920x1080, 24 fps, depth of field, motion blur, 384 samples), composited there, and only the finished segments come back. A chapter of eight minutes is roughly 11,000 frames; on a pool of about fifty A10G GPUs the heart chapter took 84 minutes to render and five minutes to composite.

The building is done by Claude Code. Every shot builder, timeline and palette in this repository was written by Claude (the Fable 5.1 model) working from two briefs, `pipeline/AGENT_BRIEF.md` and `pipeline/ORIGINAL_BRIEF.md`, and then fixed in rounds against review notes. Your job is the director's: write the script, look at the sheets, say what is wrong, and decide when it is done. The skills in `.claude/skills/` package the building steps so you can invoke them as commands.

## Step 0: Claude Code on the Fable 5.1 model

1. Install Claude Code. Either the Claude desktop app (download from claude.ai/download and open the Code tab) or the command-line version: `npm install -g @anthropic-ai/claude-code`, then type `claude` in a terminal. Sign in with the Vizuara account.
2. Choose the model. In the desktop app the model picker is at the top of the Code tab; in the terminal type `/model`. Pick **Fable 5.1**. This matters more than it sounds: the shot-building skills were written for and tested with this model, and the briefs rely on it keeping a 250 KB shot file in view while it works. A smaller model will build something, but it will not clear the six-point bar below without many more rounds.
3. Open this repository folder as the project. Claude Code reads `CLAUDE.md` at the root on its own; that file tells it the rules of the pipeline (the Blender version, what not to edit, how to test). You don't need to paste anything.
4. Check that the skills are visible: type `/` and you should see `vl-new-chapter`, `vl-review-shots`, `vl-fix-shots`, `vl-cloud-render`, `vl-narration`, `vl-house-style` and the two asset examples, `vl-asset-organ-cutaway` and `vl-asset-blood-cells`.

## Step 1: the tools on the laptop

The pipeline was built on a MacBook Air M1 with 8 GB of RAM, so nothing here needs a workstation. (An 8 GB machine can run one Blender at a time; the skills know this and never run two.)

- **Blender 5.2** from blender.org. The scripts expect it at `/Applications/Blender.app/Contents/MacOS/Blender`; on another path, or on Linux, set `VL_BLENDER` to the executable. The kit uses the 5.2 API (slotted actions, the new compositor), so an older Blender fails on the first shot.
- **Python 3.11** and `pip install -r requirements.txt` (Pillow, numpy, modal, yt-dlp).
- **ffmpeg** (`brew install ffmpeg` on a Mac).
- **An ElevenLabs key** for the narration. Copy `.env.example` to `.env` at the root and put the key there. `.env` is ignored by git and must stay that way; a key that has been in a chat, a commit or a screenshot should be treated as burned and rotated. The voice is "Anika - Engaging Teacher" (`9FTUWXd0yHJL1ZiZ71RK`) on `eleven_multilingual_v2` at speed 1.15, which matched the channel's pace when we measured it.
- **A Modal account** for the cloud render: run `python3 -m modal setup` once; it opens a browser and stores a token. If you have more than one Modal workspace, prefix the cloud commands with `MODAL_PROFILE=<name>`, and never run the render from a shared machine where someone else might switch the active profile under you (we lost half an hour to exactly that).

Then the sanity check. This renders one EEVEE frame of the heart's four-chamber cutaway at 720p and takes about twenty seconds:

```bash
cd pipeline
VL_PROJECT=heart /Applications/Blender.app/Contents/MacOS/Blender -b --python render_shot.py -- s12 /tmp/vl_heart 78 78
```

Open `/tmp/vl_heart/s12/f_0078.png`. If you see the cutaway heart with its four chambers, the papillary muscles and the streaming cells against the navy void, the laptop side works. For the Cycles look, put `VL_ENGINE=CYCLES VL_RES=960x540 VL_SAMPLES=32 VL_DOF=1` in front of the same command; it takes a couple of minutes on the CPU.

## Step 2: read what the channel actually does

`analysis/STYLE.md` is the write-up of the house style, measured frame by frame from the channel's own videos: the format, the stage, the materials, every interface element and how it behaves. It is short. Read it once before making anything, because every choice in the kit comes from it. The `vl-house-style` skill carries the same facts for Claude.

## Step 3: a new chapter, end to end

Say the chapter is Photosynthesis and we call the project `photo`.

**3a. The script.** Make `pipeline/projects/photo/` by copying `__init__.py`, `fixes.py` and `script.py` from the heart project, then rewrite `script.py`: an `INTRO` list of sentences, `SECTIONS` (each a title and its sentences) and the `OUTRO`, in Hindi with the technical terms in English, the way the channel narrates. Keep an eye on length: at speed 1.15 the heart script came to 8:03 and the DNA script to 8:22, and we had to cut three sentences from each to get there. For a recreation of an existing chapter the reference's own Hindi captions are the script; `yt-dlp --write-auto-subs --sub-langs hi --skip-download <url>` fetches them, and `narration.py` has a `FIXES` list for the mis-transcriptions.

**3b. Narration and timing.**

```bash
cd pipeline
VL_PROJECT=photo VL_SPEED=1.15 python3 -u original.py gen      # one ElevenLabs call per sentence, cached by text
VL_PROJECT=photo python3 -u original.py layout                  # lays the sentences out, writes the timing and the mixed narration
cp ../out/photo/timing.json projects/photo/timing.json
```

`gen` is cached by sentence text, so re-running after editing a few sentences only pays for those. `layout` writes `out/photo/timing.json` (the total length, each section's card time, each sentence's start and end), `out/photo/narration.wav` and `projects/photo/transcript_hi.txt`. The copy into the project folder is not optional: the cloud only sees the `pipeline/` folder, and the overlay reads the timing from there. Or let Claude do all of this: `/vl-narration photo`.

**3c. Build the shots.** In Claude Code:

```
/vl-new-chapter photo
```

This is the long step; for the heart chapter it took a builder about two hours, in two sittings. Claude writes the storyboard and the shot list on the sentence boundaries, a palette, one builder per 3D shot, the overlay timeline and any new 2D element the chapter needs, then renders the middle frame of every shot and tiles them into `/tmp/vl_photo/smoke_sheet.png`, plus twelve composited frames in `overlay_sheet.png` and three Cycles look-checks of the hero shots. It ends with a report that scores every shot against the six points.

**3d. Review.** Open the sheets and look at every tile. The bar we hold each shot to, in the client's own words, is "very, very beautiful", and it decomposes into six things:

1. Intricate assets: three scales of detail on every hero, never a bare primitive on screen.
2. A rich environment: particles, atmosphere, an out-of-focus foreground, something behind the hero.
3. Inside-out: dives through a surface into the next space, and consecutive shots that match-cut.
4. Movement in every shot, the camera and the subject.
5. The concept explained: each sentence gets its visual proof at the moment it is spoken.
6. A designed palette and a lighting theme per section, consistent with the 2D layer.

Write the misses down as a list, one line per shot ("s17: the valve is an unreadable close-up", "s30: the tissue reads as grey glass"). `/vl-review-shots photo` does a first pass for you, but your eye is the one that counts; the person who makes the channel's videos will see things a model doesn't.

**3e. Fix.**

```
/vl-fix-shots photo  s17: camera buried in the wall, show the whole valve from inside the ventricle;  s30 s31: washed grey, tissue must be warm and matte;  s06: fist is a cluster of balls
```

The fix skill measures before it changes anything (the three hardest heart problems all turned out to be something other than the obvious fix), renders proof frames of every touched shot, then re-renders all shots to prove nothing else broke. Repeat 3d and 3e until the sheet has no misses. Two rounds were typical for us.

**3f. Render in the cloud.**

```
/vl-cloud-render photo
```

or by hand, from `pipeline/`:

```bash
VL_PROJECT=photo VL_SAMPLES=384 python3 -m modal deploy modal_render.py
python3 cloud_drive.py start photo '{"chunk":4,"only":["s12","s17"],"max_frames":4,"resume":false,"tag":"test1"}'
python3 cloud_drive.py status <call id>                      # RUNNING or DONE
python3 cloud_tools.py sample photo /tmp/photo_test1.png 2   # look at the frames before paying for the full render
python3 cloud_drive.py start photo '{"chunk":16,"resume":true,"tag":"pass1"}'
python3 cloud_tools.py frames photo                          # progress, counted from the volume
VL_PROJECT=photo python3 -m modal run modal_render.py --stage probe_cpu   # one composited frame, made inside a container
python3 cloud_drive.py start photo '{"segments":24,"tag":"comp"}' drive_composite
VL_PROJECT=photo ./finalize_orig.sh ../out/photo/work ../out/photo/narration.wav ../out/photo/photosynthesis_master_1080p.mp4
```

Deploy uploads the `pipeline/` folder, so redeploy after any code change. The test renders four frames of two hero shots; look at them, because a black frame in Cycles (usually depth of field focused on nothing) costs an hour of fifty GPUs if you only find it after the full render. The render is driven by a function that runs inside Modal, so closing the laptop does not stop it, and the driver skips chunks whose frames already exist, so a second run only fills the gaps. The finalize step probes every segment, joins them, muxes the narration and writes a 24-frame contact sheet next to the master.

**3g. Watch it.** The master is `out/photo/photosynthesis_master_1080p.mp4`. Watch the whole thing with the sound on. Anything wrong goes back to 3e, and only the shots you name get re-rendered (`"force": ["s17"]` in the pass command).

## When the video is not good: a skill for every item

Here is the part I'd read twice. The pipeline gets a chapter to "correct" on its own. Getting it to "very, very beautiful" is a matter of taste that the person who makes the channel's videos has and the model does not, and the way to transfer that taste is a skill file.

A skill is a markdown file at `.claude/skills/<name>/SKILL.md` with a short header (a name and a one-line description) followed by instructions. Claude Code lists them behind `/` and loads one when you invoke it, or when its description matches what you are doing. The workflow skills in this repository package the steps above. The skills that make the difference over time are the ones about individual items: one for how a cutaway organ must look, one for blood cells, one for how a section's lighting should feel, one for the camera moves you like, one for the narration's pacing. When a shot is not right, don't only fix it; write down what right is, as a skill, and the next chapter starts from there.

Two are included as examples, `vl-asset-organ-cutaway` and `vl-asset-blood-cells`, both written from the fixes that got the heart chapter through review. The pattern is in `docs/ITEM_SKILL_TEMPLATE.md`:

- what the item is and where it appears;
- what "good" looks like, concretely: materials, the three scales of detail, the motion, the palette entries it uses;
- the misses we have seen and what caused them (this is the valuable part: "the glass look was the Fresnel term, set IOR to 1.0" saves the next builder an hour of guessing);
- how to prove it: which frame to render, what to check in Cycles.

Then name the skill in a fix request, `/vl-fix-shots photo s12: chambers, apply vl-asset-organ-cutaway`, and Claude reads the skill before touching the shot. A chapter's worth of these and the first build of the next chapter already looks like your channel.

## What is where

```
README.md                   this tutorial
CLAUDE.md                   the rules Claude Code follows in this repo (read automatically)
analysis/STYLE.md           the measured house style
docs/LESSONS.md             every gotcha we hit, with the fix
docs/ITEM_SKILL_TEMPLATE.md the pattern for an item skill
docs/sheets/                contact sheets of the five finished chapters
.claude/skills/             the workflow skills and the two example item skills
pipeline/kit.py             the shared asset kit: primitives, materials, lights, cameras, compositor setup
pipeline/ui.py, overlay.py  the 2D interface layer and the compositor
pipeline/narration.py       ElevenLabs narration and the caption fixes; original.py lays out an original script
pipeline/render_shot.py     renders one shot (what both the laptop and the cloud call)
pipeline/modal_render.py    the Modal app: GPU render chunks, CPU composite, the server-side drivers
pipeline/cloud_drive.py     start and poll the drivers; cloud_tools.py counts frames and pulls review sheets
pipeline/finalize_orig.sh   segments -> master + contact sheet (finalize.sh does the same with a reference video)
pipeline/AGENT_BRIEF.md     the builder brief (kit contracts, testing, deliverables)
pipeline/ORIGINAL_BRIEF.md  the brief for original chapters and the six-point bar
pipeline/projects/<p>/      one folder per chapter: shotlist.py, shots.py, timeline.py, palette.py, script.py,
                            overlay_ext.py, fixes.py, timing.json, transcript_hi.txt
```

`VL_PROJECT=<p>` selects the chapter for every command; the shared modules dispatch to `projects/<p>/`.

## Numbers from the five chapters

| Chapter | Length | Frames | Cloud render |
|---|---|---|---|
| Human Heart and Circulation (original) | 8:03 | 10,964 | 709 chunks, 84 min, 0 failed |
| DNA: From Gene to Protein (original) | 8:22 | 11,401 | 684 chunks, 0 failed |
| Gravitation, Chemical Reactions v2, Fundamental Unit of Life (recreations) | 13:53, 13:12, 14:51 | 51,288 together | 2,146 chunks, 0 failed |

On an A10G at 384 samples and 1080p a frame took between 12 and 44 seconds depending on the shot; the local EEVEE smoke frames take 2 to 16 seconds each on the M1. Check the Modal dashboard for what a render costs on your plan; the figure depends on the GPU tier you are allocated.

## The gotchas, in one place

`docs/LESSONS.md` has all of them. The five that cost the most time:

1. Blender 5's GPU compositor segfaults without a display, so the cloud sets the compositor device to CPU; and OptiX denoising needs a driver file the containers don't have, so denoising is OpenImageDenoise.
2. A `modal run` app dies the moment the laptop's connection blips. Renders are driven by the `drive` function inside Modal, started with `cloud_drive.py`, and progress is read from the frames on the volume, never from the log counters (the driver restarts reset them).
3. The cloud only sees `pipeline/`. Anything a chapter reads at import time (the timing file above all) must live inside its project folder, and `probe_cpu` must pass before the 24-segment composite.
4. In Cycles, a fast, uniformly black chunk is a depth-of-field or visibility problem, not a compositor one; the usual culprit is a focus distance measured before the camera was placed.
5. Shape keys: after `shape_key_add()`, Blender's closest-point and ray-cast queries answer from the active key, not the basis. Anything draped on an animated surface must use a BVH built from the basis mesh.
