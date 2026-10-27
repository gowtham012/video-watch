<div align="center">

# ▶︎ Claude Video Watch

**Claude can't take a video file directly. Now it can watch one, and score it with sound.**

Paste a YouTube link, any URL or a local file into Claude Code. Claude sees the moments the picture changes, hears what's said and when, notices what the sound is doing, and answers with a timestamp for every claim. It can also find free, openly licensed sound effects and line each one up with its exact cut.

[![version](https://img.shields.io/badge/version-0.4.0-4F46E5?style=flat-square)](.claude-plugin/plugin.json)
[![Claude Code plugin](https://img.shields.io/badge/Claude_Code-plugin-0A0A12?style=flat-square)](#install)
[![GitHub stars](https://img.shields.io/github/stars/gowtham012/video-watch?style=flat-square&color=F59E0B)](https://github.com/gowtham012/video-watch/stargazers)
[![needs ffmpeg](https://img.shields.io/badge/needs-ffmpeg_+_yt--dlp-38BDF8?style=flat-square)](#requirements)
[![python](https://img.shields.io/badge/python-3.9+-10B981?style=flat-square)](skills/video/scripts/vw.py)

<br>

[![Claude Video Watch in 30 seconds](media/demo.gif)](media/launch-ad-v2.mp4)

<sub>▲ The launch ad (click for the full version with sound). This plugin wrote the production prompt it was built from ([see how](#remake-any-video-in-your-own-style)).</sub>

<br>

**[Install](#install)** · **[What it's for](#what-its-for)** · **[How it watches](#how-it-watches)** · **[Sound effects](#add-sound-effects-on-the-beat)** · **[Numbers](#numbers)**

</div>

---

## Install

Two commands in Claude Code, plus ffmpeg:

```
/plugin marketplace add gowtham012/video-watch
/plugin install video-watch@video-watch
```

```bash
brew install ffmpeg yt-dlp      # macOS. On Linux: apt install ffmpeg && pip install yt-dlp
```

Then paste a link: `/video https://youtu.be/... what's the main argument?`

No API key and no third-party video service: the video is processed on your machine and Claude reads the result. To try a local checkout instead, start Claude Code with `claude --plugin-dir /path/to/video-watch`.

## What it's for

| You have… | Ask… |
|---|---|
| 🐛 **A bug report screen recording** | "what goes wrong after login?" and get the second it breaks, with the frame. |
| 🚀 **Your launch video, or a competitor's** | "critique this" for a hook, pacing and CTA scorecard with timestamped fixes. |
| 🎤 **A long talk or podcast** | "the 5 key arguments, with timestamps" without sitting through an hour. |
| 💻 **A coding tutorial** | "pull out the code and the steps", read verbatim from the frames. |
| 🎬 **An ad you wish you'd made** | "make one like this for my product" for a production prompt in the same style. |
| 🔊 **A silent edit** | `/video sound` for whooshes on the cuts and clicks on the taps, openly licensed and credited. |

## Why not just…

- **…give Claude a screenshot?** One frame misses everything that moves. This keeps a frame each time the picture settles, then lets Claude zoom into any second it's unsure about.
- **…use the transcript?** Half of a demo, an ad or a bug is on screen or in the sound, not in the words. Frames, speech, silences and loud hits all land on one timeline.
- **…use a model that takes video?** You'd leave Claude and your project. Here a 10-minute video costs about 7k to 27k image tokens, and the answer arrives in the session that's already working on your code.

## Use it

Everything lives under one command, `/video`, with a subcommand for each job:

| Command | What it does |
|---|---|
| `/video watch <link-or-file> [question]` | Watches the video and answers, with timestamps. `watch` is the default, so `/video <link>` works too. |
| `/video sound <link-or-file> [what it needs]` | Finds Openverse sound effects for its moments and lines them up on the timeline, with credits. |

```
/video watch https://youtube.com/watch?v=...   critique this as a launch video
/video watch ~/Desktop/bug.mov                 what goes wrong after login?
/video sound ~/Desktop/launch.mp4              whooshes on the big cuts, a click on the button press
watch this talk and give me the 5 key arguments: https://youtu.be/...
```

Plain requests work as well, which is the easiest way in the Claude desktop app and claude.ai: Claude picks the subcommand. If another plugin also has a `/video` command, use the full name `/video-watch:video`.

<details>
<summary><b>Upgrading from 0.3?</b></summary>

| Before | Now |
|---|---|
| `/video-watch:watch <link> [question]` | `/video watch <link> [question]` (or `/video-watch:video watch ...`) |
| `/watch <link>` | `/video <link>` |
| `skills/watch/scripts/vw.py` | `skills/video/scripts/vw.py` |

The install command is unchanged. Run `/plugin marketplace update video-watch` to get the new version.

</details>

If you paste a link without saying what you want, Claude gives you the gist and a timeline, then asks what to do next:

| Option | What you get |
|---|---|
| 🎬 **Remake it with my content** | Same style and quality, your product. See [below](#remake-any-video-in-your-own-style). |
| 🧐 **Critique it** | A hook, pacing and CTA scorecard, plus the top fixes, all timestamped. |
| 📝 **Detailed summary** | Key points and takeaways. |
| 💻 **Pull out text, code or steps** | Verbatim, from the frames. |

## How it watches

```mermaid
flowchart TD
    V["🎥 Video: URL or file"] --> P["prepare · yt-dlp + ffmpeg"]
    P --> K["🖼 Keyframes"]
    P --> T["💬 Transcript"]
    P --> A["🔊 Audio cues"]
    P --> C["✂️ Pacing"]
    K --> M["📄 manifest.md: one timeline"]
    T --> M
    A --> M
    C --> M
    M --> S["1 · Skim contact sheets"]
    S --> Z["2 · Zoom into key moments"]
    Z --> R["3 · Answer with timestamps"]
```

| A person… | Claude Video Watch… |
|---|---|
| **notices when the picture changes** | scans the whole video at low resolution and keeps one frame per settled visual state, not a fixed one-frame-every-N-seconds grid. |
| **listens to what's said** | uses YouTube captions or `.vtt`/`.srt` files and falls back to local Whisper. Every line keeps its timestamp. |
| **feels the sound** | measures silence, sound with no speech (music, effects) and loud hits from the waveform. |
| **senses the pace** | counts hard cuts, average shot length, and where the cuts bunch up. |
| **skims, then rewinds** | gives Claude labelled contact sheets for a cheap first pass, then `zoom` and `frame --crop` for close-ups. |

## Remake any video in your own style

Show it a video you love and say **"make one like this for my product."** The plugin pulls the video's style apart from the evidence:

- **Structure:** every shot's exact in and out time, from dense zooms across each scene boundary.
- **Rhythm:** the tempo, estimated from where cuts and loud hits land.
- **Colour:** exact hex values measured from the frames, each given a role (background, text, primary, highlight).
- **Type and motion:** weight, size, how words enter, easing, stagger, camera moves and transitions.

It then writes a **production prompt** that rebuilds that quality around your content: a master brief, a shot list with exact timings, a Remotion build plan, a music brief and a quality checklist. It copies the style only, never the original's logos, footage, copy or music.

> [`media/remake-prompt.md`](media/remake-prompt.md) is a real example: it reverse-engineers a SaaS launch ad. The video at the top of this page was built from it, and the code is in [`launch-video/`](launch-video/).

## Add sound effects, on the beat

Say **"/video sound"** (or "add sound effects to this") and Claude scores the video with free, openly licensed audio from [Openverse](https://openverse.org), about 5 million clips with no API key:

1. **Finds the moments** from what it watched: hard cuts and loud hits for whooshes and impacts, a button press for a click, quiet stretches for ambience.
2. **Searches Openverse** for each moment and shows you a shortlist with title, creator, license, length and a preview link. Only metadata is read at this point.
3. **Downloads only what you approve.** Nothing is downloaded until you say yes.
4. **Places every clip by its hit, not its first byte.** Each file's lead-in silence and peak are measured, so a whoosh peaks *on* the cut instead of drifting late, and a cue said to be "about 0:03" snaps onto the real cut.
5. **Hands over** a cue table, a `timeline.json` for your editor or Remotion, `CREDITS.md` for the video description, and, if you want, a preview render or an SFX-only stem.

The default license filter (CC0, public domain, CC BY) is safe to sync into a commercial or monetized video. No-Derivatives clips can't be synced to picture, and ShareAlike would bind the whole video, so those are left out unless you ask.

## Numbers

All of these were measured on a MacBook (Apple Silicon) while testing this release.

| Measure | Result |
|---|---|
| ⚡️ **Prepare time** | about 6 s for a 3–5 minute 720p video, about 9 s for a 10-minute 1080p video |
| 🪙 **Cost to read** | about 7k image tokens (contact sheets only) to 27k (every frame) for a 10-minute video |
| 🎯 **Timing accuracy** | cuts, silences and loud hits reported within 0.1 s on test clips |
| 🎨 **Colour accuracy** | `colors` lands within one 8-level step of the true hex |

## Commands

The skill drives all of this for you. You can also run the script directly:

```bash
VW="python3 skills/video/scripts/vw.py"

$VW prepare <url|file> --out ./vw-x [--start 1:00 --end 2:30] [--max-frames 60] [--sensitivity 2]
$VW zoom    --dir ./vw-x --start 1:10 --end 1:14 --fps 6 [--crop x,y,w,h]   # dense frames + speech in a window
$VW frame   --dir ./vw-x --at 1:12.5 [--crop 0.5,0,0.5,0.5]                 # one sharp close-up
$VW colors  --dir ./vw-x [--at 0:03,0:12]                                   # measured palette, as hex

SFX="python3 skills/video/scripts/sfx.py"

$SFX search "whoosh" --dir ./vw-x [--length shortest,short] [--license cc0,pdm,by]   # Openverse metadata only
$SFX fetch  <id> [<id> ...] --dir ./vw-x --yes                                  # download approved clips
$SFX plan   --dir ./vw-x --cues ./vw-x/sound/cues.json [--snap 0.15]            # timeline.md + CREDITS.md
$SFX mix    --dir ./vw-x --out ./vw-x/sound/preview.mp4 [--stem] [--dry-run]   # preview render or SFX stem
```

<details>
<summary><b>Tuning tips</b></summary>

- **Screen recordings and UI demos:** `--sensitivity 3` catches small changes, down to a single text label.
- **Fast-cut ads:** `--max-frames 80`.
- **Talks over 20 minutes:** `--max-frames 40`, then zoom where it matters.
- **Videos over 45 minutes with a specific question:** pass `--start`/`--end`.
- **Crop values** are fractions of the frame: `0.5,0,0.5,0.5` is the top-right quarter.

</details>

## Requirements

| Need | Install |
|---|---|
| **Required** | `ffmpeg` + `ffprobe`, and `yt-dlp` for links: `brew install ffmpeg yt-dlp` |
| Optional | `pip install pillow` for contact sheets (a cheaper first pass) |
| Optional | `pip install mlx-whisper` (Apple Silicon) or `faster-whisper`, for videos without captions. Set `VW_WHISPER_MODEL=small` for better accuracy. |
| YouTube bot checks | `export VW_COOKIES_BROWSER=chrome` (or `safari`) |
| Sound effects | Nothing extra: Openverse needs no key. Anonymous use is limited to about 20 searches a minute; set `OPENVERSE_TOKEN` for more. |

## Honest limits

- **Audio is measured, not heard.** It knows loud, silent and "music, no speech", but not what a melody is or how a voice feels. The same goes for sound effects: timing is exact, but listen to the preview to judge whether a whoosh *sounds* right.
- **Between keyframes is unseen** until Claude zooms in. Fast action, counting and sports plays need a zoom.
- **Very long videos thin out.** Ask about a time range instead.
- **Only process videos you have the right to download.**

## What's in the repo

```
.claude-plugin/        plugin + marketplace manifests
skills/video/          the /video skill: SKILL.md (watch), references/ (lenses, sound), scripts/vw.py and scripts/sfx.py
media/                 all videos (launch ad v1 + v2, how-it-works explainer), demo GIF, poster, social preview, example remake prompt
media/build/           scripts + demo clip that rebuild the videos
launch-video/          Remotion source for the launch ad v2 (not part of the plugin)
docs/                  research verdict from the multi-agent viability review
```

## Contributing

Issues and pull requests are welcome. The most useful thing you can send is a video it got wrong: the link (or a short clip), what you asked, and what it missed. [Open an issue](https://github.com/gowtham012/video-watch/issues/new).

<div align="center">
<br>

**Skim. Zoom. Answer.**

If Claude Video Watch saved you from scrubbing through a video, a ⭐ helps other people find it.

<sub>Made by Gowtham · built with Claude Code</sub>

</div>
