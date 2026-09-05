---
name: vl-narration
description: Turn a chapter script into the channel's narration and the timing file every shot hangs off: ElevenLabs per sentence, sentence layout with cards and gaps, timing.json copied into the project. Invoke as /vl-narration <project> once projects/<project>/script.py is written.
---

# Narration and timing

The argument is the project `<p>`. Work from `pipeline/`. The key comes from `ELEVENLABS_API_KEY` in the environment or the git-ignored `.env`; if it is missing, ask the user to set it and stop. Never print it.

## The script

`projects/<p>/script.py` has `INTRO` (a list of sentences), `SECTIONS` (a list of `(title, [sentences])`) and `OUTRO`. Read it and check it against the house facts before generating:

- Hindi sentences with the technical terms in English, the way the channel narrates ("कैल्शियम ऑक्साइड वाटर के साथ रिएक्ट करता है").
- The outro sentence is the channel's ("थैंक्स फॉर वॉचिंग, इफ यू लाइक दिस वीडियो प्लीज लाइक एंड सब्सक्राइब आवर चैनल").
- Length: at speed 1.15, about 170 sentences make an eight-minute chapter. If the user wants a target length, estimate before spending on audio and suggest cuts rather than a higher speed (1.05 ran a script to 9:24 that was meant to be eight minutes).
- Facts must match the visuals the shot list will make; if a sentence is wrong, say so before generating.

## Generate and lay out

```bash
VL_PROJECT=<p> VL_SPEED=1.15 python3 -u original.py gen
VL_PROJECT=<p> python3 -u original.py layout
cp ../out/<p>/timing.json projects/<p>/timing.json
```

`gen` calls ElevenLabs once per sentence (voice "Anika - Engaging Teacher", `9FTUWXd0yHJL1ZiZ71RK`, `eleven_multilingual_v2`, language `hi`) and caches by sentence text and speed under `out/<p>/narr/`, so edits cost only the changed sentences. `layout` places the sentences with a 0.5 s gap, a 2.6 s card before each section, a 1.2 s lead and a 6 s tail (`VL_GAP`, `VL_CARD`, `VL_LEAD`, `VL_TAIL` override them), writes `out/<p>/timing.json`, `out/<p>/narration.wav` and `projects/<p>/transcript_hi.txt`. The copy of `timing.json` into the project folder is required: the cloud mount is `pipeline/` only.

## Check

- Play or probe `out/<p>/narration.wav`; its length is `timing.json`'s `total`.
- The narration has true silence between sentences and no music; do not add a bed.
- Report the total, the number of sentences and sections, and the section timestamps in mm:ss (they go into the topic table and the YouTube description).

For a recreation of an existing chapter the script is the reference's own captions: `yt-dlp --write-auto-subs --sub-langs hi --skip-download <url>` (rate-limited; use `--sleep-subtitles`), then `narration.py gen` and `mix` with the caption timestamps, and the `FIXES` list in `narration.py` for mis-transcriptions.
