# video-watch: will it actually work?

> **Status note (added later):** this report was written against v0.1.0. Problems 1–4 (subtitle-language aborts, no marketplace.json, small-text detection, end-of-video crash) were fixed and tested in v0.2.0. Items 5 and beyond are still open.

## 1. Verdict

**It works once a few things are fixed.** The core pipeline (keyframes, transcript, audio cues, zoom and frame) is accurate and fast on local files. But a stranger pasting a YouTube URL from a GitHub install fails twice before any of that runs. They cannot install it from GitHub at all. And on 2 of the 3 real YouTube videos tested, a subtitle 429 error aborted the download.

## 2. What was proven to work (live tests)

- **Plugin loads and triggers.** `claude plugin validate` passes, including with `--strict`. The skill appears as `video-watch:watch` in a live session. An isolated install showed "Skills (1) watch" at an always-on cost of about 128 tokens. The claude.ai upload copy syncs and matches the repo file for file.
- **Timestamps are accurate.**
  - A clock burned into the test video read 00:00:07.600 in the frame named `f005_00m07.6s.jpg`, with `--start 2`.
  - `--start`/`--end` keep absolute times throughout.
- **Cut detection is exact on high-contrast cuts:** [8.0, 16.0, 24.0], [4.0, 8.0] and [5.0] all matched the truth.
- **Audio cues are exact.** Silences at 6–9s and 20–22s, a loud burst at 26–27s, and a median level of -23 dBFS for a 0.1-amplitude sine were all reported correctly.
- **Captions work.**
  - SRT and VTT sidecars land at exact times, including a path with spaces and parentheses.
  - YouTube rolling auto-captions collapse into clean SAY lines.
  - On Fireship "Python in 100 Seconds", the full URL run took 9.5s and returned 60 frames, 17 cuts, the transcript, and the 5 chapters and metadata.
- **The Whisper fallback works.**
  - The openai-whisper CLI produced a word-perfect transcript in about 5–7.5s on short clips.
  - On a pure tone it returned an empty transcript and did not invent speech.
  - With no Whisper available, the manifest says plainly that speech is UNKNOWN.
- **Edge cases handled:** vertical video, files with no audio (Whisper is skipped cleanly), a 3s clip, and paths with spaces. Every subprocess call uses an argv list with no `shell=True`. The script compiles on Python 3.9.6 and runs on 3.15.
- **Speed and cost are good.**
  - Local `prepare` takes 0–2s on synthetic clips, about 6s on 2.4–4.8 min 720p videos, and 9.2s on a 10-min 1080p video.
  - At defaults, a 10-min video's 5 contact sheets cost about 7.2k image tokens. Opening all 60 frames instead costs about 27k. Either way this is far below Gemini's roughly 1M tokens per hour.
- **The output is good enough to understand a video.** For three real talk-style videos, the manifest plus frames was enough to say what happens in each.
- **Contact sheets work when Pillow is present** (tested in a venv). On-screen text was readable straight from the sheets.

## 3. Confirmed problems, most severe first

| # | Severity | Problem | Location | Fix |
|---|---|---|---|---|
| 1 | **Blocker** | `--sub-langs 'en.*'` also matches YouTube's auto-translated tracks (en-de, en-ar, and so on). One HTTP 429 on any of them makes yt-dlp exit non-zero, so prepare dies before the video downloads. Reproduced 3/3, and plain `en` succeeded immediately afterwards. The error then advises updating yt-dlp, but it is already current. | `vw.py:129-131`, `137-139` | Use `--sub-langs en,en-orig,en-US,en-GB,-live_chat`. Add `--ignore-errors` and treat "video file exists" as success. Show the upgrade tip only for non-subtitle errors. |
| 2 | **Major** | You cannot install it from GitHub: there is no `.claude-plugin/marketplace.json`. `marketplace add gowtham012/video-watch` fails. When the file was added to a scratch copy, the install succeeded. | `.claude-plugin/` | Add a `marketplace.json` with `"source": "./"`, a top-level `description`, and an entry name equal to `plugin.json`'s `name`. |
| 3 | **Major** | Small text or UI changes are invisible to change detection, and no `--sensitivity` value helps (2, 3, 5, 10 and 100 were all tested). Three independent tests got changed_frac 0.0 on text changes. The cause: frames are shrunk to 32x18 and the per-cell threshold is a fixed 24, while sensitivity only scales the area fraction. SKILL.md recommends `--sensitivity 3` for exactly this case. | `vw.py:27, 239, 254, 270`; `SKILL.md:21`; `lenses.md:30` | Scale `px` with sensitivity (e.g. `24/sensitivity`) and/or analyze at a larger size (96x54 to 160x90) for sensitivity of 3 or more. Re-test with the v2 screen clip. Until then, SKILL.md should say text-only changes can be missed and Claude should `zoom` across the relevant window. |
| 4 | **Major** | Asking for a frame at or past the last decoded frame kills the whole run with no manifest, because `grab()` uses `check=True`. Triggers: clips under about 0.6s, a cut in the final sample interval when the analysis fps is below 4 (videos over 30 min), and `frame`/`zoom` past the end. At default settings, short and medium videos passed. | `vw.py:101-103, 286, 298, 316, 554, 608, 625` | Have `grab` use `check=False` and return False. Clamp pick times to `duration - 1/fps - 0.05`. Clamp the `zoom` end and `frame --at` to the probed duration. |
| 5 | Minor | Re-running `prepare` into the same `--out` reuses the stale `audio16k.wav`/`.vtt`, so a new video gets the old video's transcript (reproduced). Old frames are also left behind. The docs advise a per-video dir. | `vw.py:209-216, 228-230, 521` | At the start of `prepare`, delete `audio16k.*`, `frames/` and old `video.*`. |
| 6 | Minor | Without Pillow there are no contact sheets and no warning. The host `python3` (3.15) lacks Pillow, so the "skim sheets first" step falls back to about 27k tokens of frames instead of about 7k. | `vw.py:329-333`; `SKILL.md:26, 57` | Build sheets with ffmpeg's `tile` filter, or at minimum warn on stderr, make SKILL.md:57 conditional, and offer `pip install pillow`. |
| 7 | Minor | The 60-frame cap ranks boundaries by changed area, which leaves 11–13s holes with no frame (Fireship, 58.9 to 71.8s, where on-screen code and badges appeared). The coverage budget then drops to 0. | `vw.py:288-290, 309-319` | Add a maximum-gap rule or pick within time buckets, so no stretch of 8s or more goes without a frame. |
| 8 | Minor | The README has no install section. | `README.md` | Add `/plugin marketplace add gowtham012/video-watch` and `/plugin install video-watch@video-watch`, plus `--plugin-dir` for local testing. |
| 9 | Minor | SKILL.md tells Claude to set `VW_COOKIES_BROWSER` on bot-check errors without asking the user first. SKILL.md has no rights or ToS caveat (README has one line). | `SKILL.md:29-40`; `vw.py:132-133` | Require asking the user before using browser cookies. Add the rights caveat to SKILL.md. |

## 4. Unverified or lower-confidence concerns (not checked by a second reviewer)

- **Cowork tool names.** `device_stage_files` and `device_bash` could not be found in any public doc. Check them in a real Cowork session.
- **Skill path.** SKILL.md relies on the undocumented "Base directory for this skill" header. The documented `${CLAUDE_SKILL_DIR}` is safer.
- **Metadata.** The version is out of sync: `plugin.json` says 0.1.0 while the commit says v0.2.0. There is no LICENSE file, and `license`/`repository` are missing from `plugin.json`.
- **Range options.** `--start`/`--end` do not limit the download or the Whisper run.
- **Resolution.** Downloads are capped at 720p, so `frame --width 1920` adds no detail. A full 1080p `frame` costs about 2.7k tokens on 4.7+ models, so the 450–1,300 figure in SKILL.md is out of date.
- **Keyframe selection.**
  - Coverage frames duplicate keyframes in static scenes.
  - A counter or camera shake can use up the frame budget on "motion" frames.
  - The "start" frame sits 60% into the first segment rather than at t=0.
  - A dark-to-dark cut is labelled a change rather than a cut.
- **Manifest gaps.**
  - Cut times appear only in JSON, not in `manifest.md`.
  - LOUD events are missing from the timeline.
  - With no transcript, non-speech sound spans are not reported.
  - Sound spans can run past the end of the video.
  - Captions are not labelled as auto-generated or human.
- **Input checks.**
  - An inverted or out-of-range `--start`/`--end` exits 0 with an empty manifest.
  - Bad `--crop` values give tracebacks or silent shifts.
- **Smaller bugs.**
  - Rotation metadata is ignored, so width and height are reported wrongly.
  - `ts()` can print `00:60.0`.
  - faster-whisper only catches `ImportError`.
  - The token estimate is a flat 450 per frame regardless of size.
  - Caption dedup drops real repeated lines.
  - Local sidecar matching misses names like `video.en-US.vtt`.

## 5. Recommended next steps (smallest set that makes it work for a stranger)

1. **Fix the subtitle language pattern.** Change `--sub-langs` to `en,en-orig,en-US,en-GB,-live_chat`, add `--ignore-errors`, and accept the run if the video file exists. This unblocks YouTube URLs.
2. **Add `.claude-plugin/marketplace.json`** and an Install section to the README. This unblocks installing from GitHub.
3. **Make `grab()` non-fatal and clamp times to the duration.** This stops prepare, zoom and frame from crashing near the end of a video.
4. **Fix small-text detection.** Make sensitivity lower `px` and raise the analysis size, then re-test with the synthetic screen recording. Until that lands, add the "may miss text-only changes, zoom the window" note to SKILL.md.
5. **Make Pillow's absence visible**, or use ffmpeg `tile` sheets.
6. **Clean up in `prepare`.** Wipe stale `audio16k.*`, `frames/` and `video.*` at the start.
7. **Housekeeping:** ask before using cookies, add the ToS caveat to SKILL.md, bump the version to 0.2.0, add a LICENSE, and use `${CLAUDE_SKILL_DIR}`.

Steps 1–3 are about a dozen lines and make it work for a stranger. Step 4 is what makes the screen-recording use case trustworthy.