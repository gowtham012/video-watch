---
name: video
description: Claude video watch. One /video command with subcommands. "watch" (the default) watches and understands a video the way a person would — YouTube or any URL, or a local file — by skimming scene-aware keyframes, reading a timestamped transcript, noticing audio cues (music, silence, loud hits), and re-watching moments up close. "sound" finds free, openly licensed sound effects, ambience or music on Openverse for moments in a video and lines each clip up with its exact moment, with credits. Use when the user says "watch this video", "/video", "/watch", "what happens in this video", "review/critique this launch video", "summarize this talk/tutorial", "what went wrong in this screen recording", "make a video like this", "remake this for my product", "add sound effects", "find a whoosh/SFX for this cut", "sound design this video", or pastes a video link and asks anything about it.
argument-hint: "[watch|sound] <url-or-file> [question or what to do]"
---

# Claude video watch

One command, `/video`, with subcommands. Read the first word of the arguments:

| You type | Does | Instructions |
|---|---|---|
| `/video watch <url-or-file> [question]` | Watch and understand the video, then answer | This file, below |
| `/video <url-or-file> [question]` | Same as `watch` (the default) | This file, below |
| `/video sound <url-or-file-or-work-dir> [what it needs]` | Find Openverse sound effects for its moments and line them up on the timeline | Read `references/sound.md` |

When the user asks in plain words instead of a command, pick the subcommand from what they want: understanding a video is `watch`; adding or choosing sound effects, ambience or music for a video is `sound`. If a request needs both ("watch this and add sound"), run `watch` first and reuse its work dir for `sound`.

Everything is permission-based: ask before installing a tool, downloading a model, or downloading any audio file.

## watch: see a video like a person

Claude cannot take video directly. `scripts/vw.py` (in this skill's base directory) turns a video into what a person actually perceives: the *changes* on screen (not a fixed frame grid), what is said and when, and what the sound is doing. Claude then watches in passes: skim, understand, re-watch, answer.

Arguments: a URL or file path, optionally followed by a question or a time range ("from 2:10 to 3:00").

### 1. Prepare (pick the runtime)

`VW` = `python3 <this skill's base directory>/scripts/vw.py`. Pick a work dir such as `./vw-<short-slug>` in the current project, or the scratchpad.

```
VW prepare "<url-or-path>" --out <dir> [--start 2:10 --end 3:00] [--max-frames 60] [--sensitivity 2]
```

Tune it to the video:
- Screen recordings, UI demos, slides with small changes: `--sensitivity 3`.
- Fast-cut ads and launch films: `--max-frames 80`.
- Talks and podcasts over 20 minutes: `--max-frames 40`, and zoom later.
- Video longer than about 45 minutes, with a specific question: give the range with `--start`/`--end` instead of the whole video.

**Claude Code (on the user's machine):** run it directly with Bash. If `ffmpeg` or `yt-dlp` is missing, tell the user the install command (`brew install ffmpeg yt-dlp`) and ask before installing. Pillow is optional (`pip install pillow`) and adds contact sheets. If there are no captions, local Whisper is used if installed (`pip install mlx-whisper` on Apple Silicon, or `faster-whisper`).

**Cowork (cloud session):**
- **Local file on the user's computer:** stage it into the cloud workspace with `device_stage_files`, then run `VW prepare` on the staged path in cloud Bash. ffmpeg is there; `pip install pillow yt-dlp --break-system-packages` if missing.
- **URL:**
  1. Try `VW prepare` in cloud Bash first.
  2. If the host is blocked (YouTube usually is: proxy 403), download on the user's computer with `device_bash`. Use a connected folder (ask for one if there is none): `pip install -U yt-dlp` if needed, then `yt-dlp -f "b[height<=720]/bv*[height<=720]+ba" --write-auto-subs --write-subs --sub-langs "en.*,en" --sub-format vtt -o "<folder>/vw-downloads/video.%(ext)s" "<url>"`. Keep the `-o` value quoted; zsh treats `( )` as a glob.
  3. Stage the video and its `.vtt` (same base name) into the cloud, then run `VW prepare` on the staged file. The sidecar captions are picked up automatically.
  4. If both fail (the computer's sandbox follows the org's network allowlist, which often blocks YouTube too), say so plainly. Offer three ways forward:
     - The user downloads the video and drops it into a connected folder.
     - An admin allows the domain in network settings.
     - The user runs `/video watch` from Claude Code on their Mac, which has normal network access.
- Frames are read with `Read` from the cloud workspace.

YouTube "confirm you're not a bot" errors: set `VW_COOKIES_BROWSER=chrome` (or safari) and retry, or update yt-dlp.

### 2. Orient (like reading the title and the room)

Read `<dir>/manifest.md` in full before looking at any image. It has:
- Metadata, the uploader's description and chapters.
- **Visual pacing:** hard cuts, average shot length, cuts per sixth of the video.
- **Audio cues** measured from the waveform: silence, speech coverage, sound with no speech (music, SFX), loud moments.
- **Timeline:** frames, speech and audio events interleaved in time order.

Each frame has a kind:
- `start`/`cut`/`change`: a new settled visual state, captured after it settles, as a viewer would register it.
- `motion`: sampled during continuous movement.
- `coverage`: an extra look inside a long, unchanging stretch.

### 3. Skim (first watch)

View the contact sheets in order (`sheet_*.jpg`, 12 labelled frames each). This is the cheap first pass, like watching at 2× speed. On the side, write a running timeline:

`[mm:ss] what is on screen | what is said | what the sound is doing`

Pair each frame with the speech near its timestamp. Meaning comes from the combination: a slide plus the sentence said over it, a cursor plus the click sound.

Open individual `frames/*.jpg` files only where a sheet thumbnail is too small: on-screen text, code, UI labels, faces, numbers.

### 4. Re-watch what matters (second watch)

People rewind when something is fast, important or confusing. Do the same. Zoom when any of these apply:
- An answer depends on something that happens between two keyframes.
- A burst of cuts, a `loud` moment, or a `SOUND (no speech)` stretch that is clearly a beat.
- Text is unreadable, or an action or result is ambiguous (did the click work? what changed?).
- The user's question points at a moment.

```
VW zoom  --dir <dir> --start 1:32 --end 1:36 --fps 6 [--crop x,y,w,h]   # dense frames + speech in window
VW frame --dir <dir> --at 1:34.5 [--crop 0.5,0,0.5,0.5] --width 1920    # one sharp frame / lean in on a region
VW colors --dir <dir> [--at 0:03,0:12]                                  # measured palette: dominant + accent hex
```

`--crop` uses fractions of the frame: `0.5,0,0.5,0.5` is the top-right quarter. Keep zooms short, about 2–8 s, since each frame costs roughly 450–1,300 image tokens.

### 5. Understand, then answer

Build the model a person ends up with: what the video is, who it's for, the story arc and its turning points, what is shown versus claimed, and how it feels (pace, energy, music).

Then answer the user's actual question. Rules:
- **Cite timestamps** for every claim (`[01:34]`).
- **Separate the senses.** "Seen" comes from frames, "said" from the transcript, "sounds like" from audio cues. Audio cues are measurements, not hearing: music, tone of voice and sound effects are inferred from level and timing. Say so when it matters, and never claim to have heard a melody or a voice's emotion.
- **State the gaps.** With no transcript, speech is unknown, so never invent dialogue. Between frames is unseen unless zoomed.
- Prefer what is on screen over the description when they conflict, and point the conflict out.

For use-case lenses (launch/marketing critique, tutorials and talks, screen recordings and bug repros, remaking a video in the same style, general Q&A), read `references/lenses.md` and apply the matching one.

### 6. Ask what's next (when the goal wasn't stated)

If the user only pasted a link, or said just "watch this", don't guess the goal. Give the gist and the timeline, then ask once what they want to do with the video. In Claude Code use `AskUserQuestion` with these options:
- **Remake it with my content.** Same style and quality, their product or story. Uses the "Remake" lens.
- **Critique it.** Launch/marketing lens: scorecard and the top fixes.
- **Detailed summary.** Key points and takeaways.
- **Pull out text, code or steps.** Tutorial lens, verbatim.

Skip the question when the request already says what they want ("critique this", "summarize", "make one like this for X").

### Output shape (default)

1. **One-line gist:** what this video is.
2. **Timeline:** 5–15 beats, `[mm:ss] what happens`. Scale with length.
3. **The answer or analysis** the user asked for, using the lens.
4. **Confidence notes:** anything not seen, heard or verified, in one or two lines.

With the Remake lens the output is the production prompt instead (see `references/lenses.md`).

Keep the work dir. Follow-up questions should reuse it (zoom, frame) instead of re-running prepare, and so should `/video sound` if the user then wants sound effects for this video.
