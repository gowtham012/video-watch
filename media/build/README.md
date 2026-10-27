# Building the videos in `media/`

Everything needed to rebuild the videos is in this repo. The launch ad (v2) lives in [`../../launch-video/`](../../launch-video/) as a Remotion project. The other two are built here with Python and ffmpeg.

| Video | Built by | Source |
|---|---|---|
| `media/launch-ad-v2.mp4` | Remotion (React) | [`launch-video/`](../../launch-video/): `cd launch-video && npm install && npm run render` (about 12 min) |
| `media/how-it-works.mp4` | Pillow slides, macOS `say` narration, ffmpeg | `make.py` + `demo/` |
| `media/launch-ad-v1.mp4` | Pillow frames piped to ffmpeg | `ad.py` + `music.py` |

**Needs:** `ffmpeg`, `pip install pillow`, macOS (for the `say` voice and the Helvetica Neue and Menlo fonts).

```bash
# how-it-works.mp4: run the plugin on the demo clip, then render slides + narration
python3 skills/video/scripts/vw.py prepare media/build/demo/demo.mp4 --out media/build/demo/out --no-whisper
python3 media/build/make.py media/build/demo media/how-it-works.mp4

# launch-ad-v1.mp4
python3 media/build/music.py /tmp/music.wav
python3 media/build/ad.py media/launch-ad-v1.mp4 /tmp/music.wav

# music for the Remotion ad (already committed as launch-video/public/music.wav)
python3 media/build/music2.py launch-video/public/music.wav
```

`demo/demo.mp4` is a synthetic 30 s test clip with 5 scenes, a silence at 9–12 s and a loud hit at 21 s, plus `demo.srt` captions. It contains no third-party footage.
