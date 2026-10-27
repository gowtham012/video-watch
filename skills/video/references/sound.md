# /video sound: Openverse sound effects, on the beat

Find free, openly licensed sound effects, ambience or music on [Openverse](https://openverse.org) (about 5 million audio clips, no API key) for the moments in a video that need sound, then place each clip so its hit lands exactly on its moment. The usual failure is drift: a downloaded SFX starts with a little silence, or its peak sits half a second in, so a clip dropped "at 0:03" sounds late. `scripts/sfx.py` measures every clip and places it by its hit, not by the start of the file.

`SFX` = `python3 <this skill's base directory>/scripts/sfx.py`. It reuses the `watch` work dir (`<dir>/manifest.json`) and writes into `<dir>/sound/`.

Arguments: a video (URL or file) or an existing `watch` work dir, optionally followed by what the user wants ("whooshes on every cut", "rain ambience under the intro", "a click when the button is pressed at 0:12").

## Permission rules (open source, user-first)

- **Searching** only reads metadata from Openverse. No file is downloaded. Fine to do without asking, but say you're searching Openverse.
- **Downloading audio needs a yes.** Before `fetch`, show the user exactly which clips (title, creator, license, length) and ask. `fetch` refuses to run without `--yes`; only pass it after they agree.
- **Rendering** a preview (`mix`) writes a new file and never touches the original. Offer it; don't assume it.
- Installing tools (ffmpeg) or models follows the same rule as `watch`: ask first.

## 1. Know the video

If there is no work dir yet, run `watch` first (`VW prepare ...`, then read `manifest.md`). The sound pass needs the same evidence a sound designer uses:
- **Hard cuts** and **loud moments** (from the manifest): the natural places for whooshes, hits and risers.
- **Silences** and **sound with no speech**: room for ambience or a music bed; speech stretches need quieter SFX.
- **Frames**: what is actually on screen (a door, a click, a logo reveal, a car). Zoom (`VW zoom`) where an action's exact frame matters, such as a button press or an impact.

## 2. Write a cue sheet

List the moments that need sound. One line each, with the time, what's on screen, and the sound it wants:

```
[00:03.0] cut to product reveal     -> whoosh, peak on the cut
[00:12.4] cursor clicks "Publish"   -> soft UI click, starts on the click
[00:00-00:08] calm intro, no speech -> light room tone / ambience
```

Keep it tasteful: a sound on every cut gets tiring. Prefer the cuts and loud moments that carry the story. If the user named the moments, use theirs.

## 3. Search Openverse

```
SFX search "whoosh" --dir <dir>                         # defaults: sound_effect, shortest+short, cc0/pdm/by
SFX search "rain ambience" --dir <dir> --length medium,long
SFX search "ui click" --dir <dir> --max 12 --extension wav
```

- Try 2–3 wordings per cue ("whoosh", "swoosh", "transition swish"); Openverse tags vary by source.
- `--category music` for a music bed, `sound_effect` (default) otherwise.
- **License filter.** The default `cc0,pdm,by` is safe to sync into a commercial or monetized video: syncing sound to picture is an adaptation under Creative Commons 4.0, so No-Derivatives (`nd`) clips can't be used at all, and ShareAlike (`by-sa`) would force the whole video to carry CC BY-SA. Only widen the filter (`--license cc0,pdm,by,by-sa,by-nc`) if the user asks, and say what the license obliges them to do. Results outside the safe set carry a `note`.
- Anonymous use is rate limited (about 20 requests a minute). If you hit it, wait or suggest `OPENVERSE_TOKEN`.

Pick 1–3 candidates per cue on title, tags and length (a hit should be short; ambience long enough to cover the stretch). Show the user a shortlist: cue, title, creator, license, seconds, and the `preview` link so they can listen on the source site. Then ask to download the ones you'd use.

## 4. Download (only after a yes)

```
SFX fetch <id> [<id> ...] --dir <dir> --yes
```

Each clip lands in `<dir>/sound/clips/` and is measured: `lead_in_s` (silence before the first audible sample) and `peak_s` (the attack of its loudest moment).

## 5. Place every clip on its moment

Write `<dir>/sound/cues.json`:

```json
[
  {"at": "0:03.0", "id": "<openverse id>", "anchor": "peak",  "why": "whoosh peaks on the reveal cut", "gain_db": -4},
  {"at": "0:12.4", "id": "<openverse id>", "anchor": "start", "why": "click on Publish", "max_len": 0.6},
  {"at": "0:00.0", "id": "<openverse id>", "anchor": "start", "why": "room tone under intro", "gain_db": -18, "max_len": 8, "fade_out": 1.0, "snap": false}
]
```

- `anchor: "peak"` lines up the clip's loudest moment with `at` (whooshes, risers, impacts: the swell starts before the cut). `anchor: "start"` lines up the first audible sample (clicks, footsteps, ambience).
- `gain_db` keeps SFX under speech (start around −6 to −12 dB where someone is talking, −15 to −20 dB for ambience). `max_len` and `fade_out` (seconds) shorten long clips cleanly.
- `snap` (on by default) moves a cue onto a hard cut or loud hit within 0.15 s, so "about 0:03" lands on the real cut. Turn it off for ambience and for moments that aren't cuts.

```
SFX plan --dir <dir> --cues <dir>/sound/cues.json [--snap 0.15]
```

This writes `<dir>/sound/timeline.md` (each clip, its hit time, where the file is placed, what it snapped to, gain and length), `timeline.json`, and `CREDITS.md`. Read `timeline.md` back and check each hit against the cue sheet.

## 6. Preview mix (offer it)

```
SFX mix --dir <dir> --out <dir>/sound/preview.mp4             # original video + the clips
SFX mix --dir <dir> --out <dir>/sound/sfx-stem.wav --stem     # SFX only, for an editor (Premiere, Resolve, CapCut, Remotion)
```

Options: `--bed-db -3` to lower the original audio, `--dry-run` to print the ffmpeg command instead. To check sync, run `VW prepare` on the preview and confirm the loud moments now sit on the intended cuts; this is a measurement, not listening.

## 7. Hand over

1. The cue table from `timeline.md` (time, sound, why).
2. Where the files are: clips, the preview or stem, `timeline.json` for editors and build tools (Remotion can read `place_at`, `trim_head`, `length` and `gain_db` directly).
3. **Credits.** Give `CREDITS.md` in full and tell the user to put it in the video description. CC BY clips require it; CC0 clips are credited as a courtesy. Openverse asks that apps say they're built with Openverse.
4. Anything to check: license notes from `plan`, and that sound is measured, not heard: Claude can't judge whether a whoosh *sounds* right, so ask the user to listen to the preview.

## Runtimes

- **Claude Code (user's machine):** run `SFX` directly. Needs `ffmpeg` for fetch, plan and mix.
- **Cowork (cloud):** try `SFX search` in cloud Bash first. If `api.openverse.org` or the clip's host is blocked (proxy 403), run the same commands on the user's computer with `device_bash` in a connected folder, the same way `watch` downloads videos, then stage the work dir back. If both are blocked, say so plainly and offer two ways forward: run `/video sound` from Claude Code on their Mac, which has normal network access, or browse `https://openverse.org/search/audio?q=<query>` themselves and place the clips by hand using the cue sheet.
