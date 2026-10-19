# video-watch

Lets Claude watch a video the way a person does. It works in Cowork and Claude Code.

[![video-watch launch ad (33 s), click to play](media/launch-ad-poster.jpg)](media/launch-ad-v2.mp4)

*33-second launch ad, built in Remotion from the plugin's own remake prompt ([source](ad/), [prompt](media/remake-prompt.md)).*

## Install

In Claude Code:

```
/plugin marketplace add gowtham012/video-watch
/plugin install video-watch@video-watch
```

To try a local checkout instead: `claude --plugin-dir /path/to/video-watch`.

Use it like this:

```
/watch https://youtube.com/watch?v=...  critique this as a launch video
/watch ~/Desktop/bug.mov  what goes wrong after login?
```

## How it "watches"

| Human does | Plugin does |
|---|---|
| Notices when the picture changes | Scans the whole video at low resolution and keeps one frame per settled visual state, plus samples during motion and in long, static stretches. Doesn't use a fixed 1-frame-per-N-seconds grid. |
| Listens to what's said | Uses captions (YouTube or sidecar `.vtt`/`.srt`). Falls back to local Whisper. Speech is placed in time next to the frames. |
| Feels the sound | Measures silence, music or sound effects without speech, and loud hits from the waveform. |
| Senses the pace | Counts hard cuts, average shot length, and where the cuts bunch up. |
| Skims, then rewinds | Labelled contact sheets for a cheap first pass, then `zoom` (dense frames for a window) and `frame --crop` (a sharp close-up). |

## Requirements

- `ffmpeg` and `ffprobe` (required). On macOS: `brew install ffmpeg`.
- `yt-dlp` for URLs: `brew install yt-dlp`.
- Optional: `pip install pillow` for contact sheets.
- Optional: `pip install mlx-whisper` (Apple Silicon) or `faster-whisper` to transcribe videos without captions. Set `VW_WHISPER_MODEL=small` for better accuracy.
- YouTube bot checks: `export VW_COOKIES_BROWSER=chrome`.

## The script directly

```
python3 skills/watch/scripts/vw.py prepare <url|file> --out ./vw-x [--start 1:00 --end 2:30] [--max-frames 60] [--sensitivity 2]
python3 skills/watch/scripts/vw.py zoom  --dir ./vw-x --start 1:10 --end 1:14 --fps 6 [--crop x,y,w,h]
python3 skills/watch/scripts/vw.py frame --dir ./vw-x --at 1:12.5 --crop 0.5,0,0.5,0.5
```

## Limits

- Audio is measured, not heard. The plugin can't tell what a melody is or how a voice sounds.
- Anything between keyframes is unseen until zoomed.
- Only process videos you have the right to download.
