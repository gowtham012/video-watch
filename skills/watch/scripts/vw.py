#!/usr/bin/env python3
"""vw.py - prepare any video so an LLM can "watch" it like a person.

Subcommands
  prepare SRC --out DIR   Download/ingest, find visual changes, pick keyframes,
                          get a timestamped transcript, read audio cues, and
                          write DIR/manifest.md (+ manifest.json, frames, sheets).
  zoom    --dir DIR --start T --end T     Re-watch a window densely.
  frame   --dir DIR --at T [--crop ...]   Grab one high-res frame (lean in).

Requires: ffmpeg + ffprobe. Optional: yt-dlp (URLs), Pillow (contact sheets),
mlx_whisper / faster-whisper / openai-whisper (speech when no captions exist).
Standard library only otherwise.
"""
import argparse
import array
import glob
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys

AW, AH = 32, 18  # analysis thumbnail size (gray)
# ponytail: 9x more pixels to diff in pure Python - only paid when asked for (sensitivity >= 3)
AW_FINE, AH_FINE = 96, 54  # small UI/text changes vanish at 32x18


# ---------------------------------------------------------------- helpers
def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def run(cmd, check=True, capture=True):
    p = subprocess.run(cmd, stdout=subprocess.PIPE if capture else None,
                       stderr=subprocess.PIPE if capture else None)
    if check and p.returncode != 0:
        err = (p.stderr or b"").decode("utf-8", "replace")[-1500:]
        die(f"command failed: {' '.join(cmd[:4])} ...\n{err}")
    return p


def ts(t):
    """seconds -> M:SS.s or H:MM:SS"""
    t = max(0.0, float(t))
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    if h >= 1:
        return f"{int(h)}:{int(m):02d}:{s:04.1f}"
    return f"{int(m):02d}:{s:04.1f}"


def parse_time(v):
    if v is None:
        return None
    v = str(v).strip()
    if re.fullmatch(r"[\d.]+", v):
        return float(v)
    parts = [float(p) for p in v.split(":")]
    sec = 0.0
    for p in parts:
        sec = sec * 60 + p
    return sec


def need(tool):
    if not shutil.which(tool):
        hint = {"ffmpeg": "brew install ffmpeg", "ffprobe": "brew install ffmpeg",
                "yt-dlp": "brew install yt-dlp  (or pip install yt-dlp)"}.get(tool, "")
        die(f"'{tool}' not found. Install it: {hint}")


def probe(path):
    p = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format",
             "-show_streams", path])
    info = json.loads(p.stdout)
    v = next((s for s in info["streams"] if s.get("codec_type") == "video"), None)
    a = next((s for s in info["streams"] if s.get("codec_type") == "audio"), None)
    dur = float(info["format"].get("duration") or (v or {}).get("duration") or 0)
    fps = None
    if v and v.get("avg_frame_rate", "0/0") != "0/0":
        n, d = v["avg_frame_rate"].split("/")
        fps = round(float(n) / float(d), 2) if float(d) else None
    return {"duration": dur, "width": v and v.get("width"), "height": v and v.get("height"),
            "fps": fps, "has_audio": a is not None, "has_video": v is not None}


def scale_filter(longside):
    return (f"scale='if(gt(iw,ih),min({longside},iw),-2)':"
            f"'if(gt(iw,ih),-2,min({longside},ih))'")


def grab(video, t, out, longside=768, crop=None, dur=None):
    """One JPEG at t. Returns False (never dies) if ffmpeg can't decode a frame there."""
    if dur:
        t = max(0.0, min(t, dur - 0.25))  # seeking at/after the last frame yields nothing
    vf = []
    if crop:
        x, y, w, h = crop
        vf.append(f"crop=iw*{w}:ih*{h}:iw*{x}:ih*{y}")
    vf.append(scale_filter(longside))
    if os.path.exists(out):
        os.remove(out)
    p = run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", video,
             "-frames:v", "1", "-vf", ",".join(vf), "-q:v", "3", out], check=False)
    ok = p.returncode == 0 and os.path.exists(out)
    if not ok:
        print(f"[vw] no frame at {t:.2f}s - skipped", file=sys.stderr)
    return ok


# ---------------------------------------------------------------- ingest
def ingest(src, out, start, end):
    """Return (video_path, meta, subtitle_path_or_None)."""
    meta = {"source": src}
    if os.path.exists(src):
        video = os.path.abspath(src)
        meta["title"] = os.path.basename(src)
        base = os.path.splitext(video)[0]
        subs = next((base + e for e in (".vtt", ".srt", ".en.vtt", ".en.srt")
                     if os.path.exists(base + e)), None)
        return video, meta, subs

    if not re.match(r"https?://", src):
        die(f"not a file or URL: {src}")
    if re.search(r"\.(mp4|mov|webm|mkv|m4v)(\?|$)", src, re.I) and not shutil.which("yt-dlp"):
        video = os.path.join(out, "video" + os.path.splitext(src.split("?")[0])[1])
        run(["curl", "-L", "-sS", "-o", video, src])
        return video, meta, None

    need("yt-dlp")
    cmd = ["yt-dlp", "--no-playlist", "-f",
           "bv*[height<=720]+ba/b[height<=720]/bv*+ba/b",
           "--merge-output-format", "mp4", "-o", os.path.join(out, "video.%(ext)s"),
           "--write-info-json", "--write-subs", "--write-auto-subs",
           # ponytail: explicit list - "en.*" also matched auto-translated tracks (en-de...),
           # and one 429 on any of them aborted the whole download
           "--sub-langs", "en,en-orig,en-US,en-GB,-live_chat", "--sub-format", "vtt/srt/best",
           "--ignore-errors", "--no-progress", "--quiet", "--no-warnings"]
    if os.environ.get("VW_COOKIES_BROWSER"):  # e.g. chrome / safari, for "confirm you're not a bot"
        cmd += ["--cookies-from-browser", os.environ["VW_COOKIES_BROWSER"]]
    p = run(cmd + [src], check=False)
    vids = [f for f in glob.glob(os.path.join(out, "video.*"))
            if f.rsplit(".", 1)[-1] in ("mp4", "mkv", "webm", "mov")]
    if not vids:  # subtitle errors are non-fatal; only a missing video is
        die("yt-dlp failed: " + (p.stderr or b"").decode("utf-8", "replace")[-1200:]
            + "\nTip: update yt-dlp (brew upgrade yt-dlp) - YouTube changes often.")
    video = vids[0]
    info_p = os.path.join(out, "video.info.json")
    if os.path.exists(info_p):
        with open(info_p) as f:
            info = json.load(f)
        meta.update({k: info.get(k) for k in
                     ("title", "uploader", "upload_date", "view_count", "like_count",
                      "duration", "webpage_url")})
        meta["description"] = (info.get("description") or "")[:1500]
        meta["chapters"] = [{"start": c.get("start_time"), "title": c.get("title")}
                            for c in (info.get("chapters") or [])]
        os.remove(info_p)  # large; we keep what matters
    subs = sorted(glob.glob(os.path.join(out, "video*.vtt")) +
                  glob.glob(os.path.join(out, "video*.srt")),
                  key=lambda f: (".orig" in f, "-" in os.path.basename(f), len(f)))
    return video, meta, (subs[0] if subs else None)


# ---------------------------------------------------------------- transcript
def parse_subs(path, offset=0.0):
    txt = open(path, encoding="utf-8", errors="replace").read()
    txt = txt.replace("\r", "")
    blocks = re.split(r"\n{2,}", txt)  # YouTube cues contain " " lines; split on truly empty lines only
    cues = []
    tre = re.compile(r"(\d+:)?(\d+):(\d+)[.,](\d+)\s*-->\s*(\d+:)?(\d+):(\d+)[.,](\d+)")
    for b in blocks:
        lines = b.strip().split("\n")
        for i, line in enumerate(lines):
            m = tre.search(line)
            if not m:
                continue
            g = m.groups()
            s = int((g[0] or "0:")[:-1]) * 3600 + int(g[1]) * 60 + int(g[2]) + int(g[3]) / 10 ** len(g[3])
            e = int((g[4] or "0:")[:-1]) * 3600 + int(g[5]) * 60 + int(g[6]) + int(g[7]) / 10 ** len(g[7])
            body = [html.unescape(re.sub(r"<[^>]+>", "", l)).strip() for l in lines[i + 1:]]
            # drop caption noise: ">>" speaker marks and pure sound tags like [music]
            body = [re.sub(r"\s*(>>|\[(?:music|applause|laughter|__)\])\s*", " ", l, flags=re.I).strip() for l in body]
            body = [l for l in body if l]
            if body:
                cues.append([s - offset, e - offset, body])
            break
    # de-duplicate YouTube rolling auto-captions
    out, last = [], None
    for s, e, body in cues:
        if e - s < 0.05:
            continue
        for l in body:
            if l != last and (not out or l != out[-1][2]):
                out.append([s, e, l])
            last = l
    return merge_lines(out)


def merge_lines(cues, max_span=8.0, max_chars=160):
    merged = []
    for s, e, t in cues:
        if merged and (s - merged[-1][0] < max_span) and len(merged[-1][2]) + len(t) < max_chars \
                and not re.search(r"[.?!]$", merged[-1][2]):
            merged[-1][1] = e
            merged[-1][2] += " " + t
        else:
            merged.append([s, e, t])
    return [{"start": round(s, 2), "end": round(e, 2), "text": t} for s, e, t in merged if s >= -1]


def whisper(video, out, has_audio):
    if not has_audio:
        return None, "no audio track"
    wav = os.path.join(out, "audio16k.wav")
    if not os.path.exists(wav):
        run(["ffmpeg", "-v", "error", "-y", "-i", video, "-ac", "1", "-ar", "16000", wav])
    model = os.environ.get("VW_WHISPER_MODEL", "base")
    if shutil.which("mlx_whisper"):
        run(["mlx_whisper", wav, "--model", f"mlx-community/whisper-{model}-mlx",
             "-f", "vtt", "-o", out], check=False)
        f = os.path.join(out, "audio16k.vtt")
        if os.path.exists(f):
            return parse_subs(f), f"mlx_whisper ({model})"
    try:
        from faster_whisper import WhisperModel  # type: ignore
        segs, _ = WhisperModel(model, compute_type="int8").transcribe(wav, vad_filter=True)
        cues = [[s.start, s.end, s.text.strip()] for s in segs]
        return merge_lines(cues), f"faster-whisper ({model})"
    except ImportError:
        pass
    if shutil.which("whisper"):
        run(["whisper", wav, "--model", model, "--output_format", "vtt",
             "--output_dir", out, "--fp16", "False"], check=False)
        f = os.path.join(out, "audio16k.vtt")
        if os.path.exists(f):
            return parse_subs(f), f"openai-whisper ({model})"
    return None, ("no captions and no Whisper installed "
                  "(pip install mlx-whisper  OR  pip install faster-whisper)")


# ---------------------------------------------------------------- vision
def analyze_changes(video, start, dur, afps, size=(AW, AH)):
    """Stream tiny gray frames; return list of (t, frame_bytes)."""
    aw, ah = size
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", video,
           "-vf", f"fps={afps},scale={aw}:{ah}:flags=area,format=gray",
           "-f", "rawvideo", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    n = aw * ah
    frames, i = [], 0
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        frames.append((start + i / afps, array.array("B", buf)))
        i += 1
    p.wait()
    return frames


def diff(a, b, px=24):
    changed = 0
    tot = 0
    for x, y in zip(a, b):
        d = x - y if x > y else y - x
        tot += d
        if d > px:
            changed += 1
    n = len(a)
    return changed / n, tot / n


def pick_keyframes(frames, max_frames, sensitivity, min_gap):
    """Segment the video into visual 'states'; return keyframes + cut stats."""
    if not frames:
        return [], [], []
    fine = len(frames[0][1]) > AW * AH  # analysed at AW_FINE x AH_FINE (sensitivity >= 3)
    # fraction of area that must change. coarse: 2.0 -> 1.5%. fine: 3.0 -> 0.15% (~8 of 5184
    # cells = one short text label; a moving cursor touches ~2-4 cells, so it stays below)
    thr = (0.0045 if fine else 0.03) / sensitivity
    px = max(8, 48 / sensitivity)       # per-pixel change that counts (2.0 -> 24, 3.0 -> 16)
    bounds = [(frames[0][0], 1e9)]
    ref = frames[0][1]
    cuts = []
    prev = frames[0][1]
    for t, fr in frames[1:]:
        cf_prev, _ = diff(fr, prev)
        if cf_prev > 0.45:
            cuts.append(round(t, 2))     # hard cut between consecutive samples
        prev = fr
        cf, _ = diff(fr, ref, px)
        if cf >= thr and t - bounds[-1][0] >= min_gap:
            bounds.append((t, cf))
            ref = fr
        elif cf >= thr * 0.5:
            pass                          # drifting: keep ref (catches slow builds)
    end_t = frames[-1][0] + (frames[-1][0] - frames[-2][0] if len(frames) > 1 else 1)
    # cap number of states: keep the strongest boundaries
    if len(bounds) > max_frames:
        keep = sorted(bounds[1:], key=lambda b: -b[1])[:max_frames - 1]
        bounds = [bounds[0]] + sorted(keep)
    segs = []
    for i, (s, score) in enumerate(bounds):
        e = bounds[i + 1][0] if i + 1 < len(bounds) else end_t
        segs.append([s, e, score])
    picks = []
    for s, e, score in segs:
        # the "settled" look of a state: ~60% in, but not on the next boundary
        t = s + min((e - s) * 0.6, max(e - s - 0.25, 0))
        if score == 1e9:
            kind = "start"
        elif score >= 0.45:
            kind = "cut"
        elif e - s < min_gap * 1.6:
            kind = "motion"   # part of continuous movement, not a settled state
        else:
            kind = "change"
        picks.append({"t": round(t, 2), "kind": kind, "seg": [round(s, 2), round(e, 2)]})
    # spend leftover budget on long, unchanging stretches (talking heads, slow pans)
    budget = max_frames - len(picks)
    total = end_t - frames[0][0]
    gap = max(total / max(max_frames, 1) * 1.5, 6.0)
    extras = []
    for s, e, _ in sorted(segs, key=lambda x: -(x[1] - x[0])):
        k = int((e - s) // gap)
        for j in range(1, k + 1):
            extras.append({"t": round(s + j * (e - s) / (k + 1), 2), "kind": "coverage",
                           "seg": [round(s, 2), round(e, 2)]})
    extras.sort(key=lambda x: -(x["seg"][1] - x["seg"][0]))
    picks += extras[:max(budget, 0)]
    picks.sort(key=lambda p: p["t"])
    # de-dup near-identical times
    dedup = []
    for p in picks:
        if not dedup or p["t"] - dedup[-1]["t"] >= 0.4:
            dedup.append(p)
    return dedup, cuts, segs


def contact_sheets(frames_info, out, per_sheet=12, cols=4, thumb=384):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return []
    sheets = []
    for si in range(0, len(frames_info), per_sheet):
        group = frames_info[si:si + per_sheet]
        ims = []
        for f in group:
            im = Image.open(os.path.join(out, f["file"])).convert("RGB")
            im.thumbnail((thumb, thumb))
            ims.append((im, f))
        cw = thumb
        ch = max(im.height for im, _ in ims) + 22
        rows = math.ceil(len(ims) / cols)
        sheet = Image.new("RGB", (cols * cw, rows * ch), (20, 20, 20))
        d = ImageDraw.Draw(sheet)
        try:
            font = ImageFont.load_default(size=16)
        except TypeError:
            font = ImageFont.load_default()
        for i, (im, f) in enumerate(ims):
            x, y = (i % cols) * cw, (i // cols) * ch
            sheet.paste(im, (x + (cw - im.width) // 2, y + 22))
            d.text((x + 6, y + 3), f"#{f['idx']}  {ts(f['t'])}  {f['kind']}", fill=(255, 220, 90), font=font)
        name = f"sheet_{si // per_sheet + 1:02d}.jpg"
        sheet.save(os.path.join(out, name), quality=82)
        sheets.append({"file": name, "frames": [f["idx"] for f in group],
                       "range": [group[0]["t"], group[-1]["t"]]})
    return sheets


# ---------------------------------------------------------------- audio
def audio_cues(video, start, dur, transcript):
    res = {"rms": [], "silences": [], "non_speech_sound": [], "loud": []}
    p = run(["ffmpeg", "-v", "info", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", video,
             "-vn", "-ac", "1", "-ar", "16000", "-af",
             "silencedetect=noise=-38dB:d=0.7,asetnsamples=n=8000,astats=metadata=1:reset=1,"
             "ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-",
             "-f", "null", "-"], check=False)
    outtxt = (p.stdout or b"").decode("utf-8", "replace")
    errtxt = (p.stderr or b"").decode("utf-8", "replace")
    cur = None
    for line in outtxt.splitlines():
        m = re.search(r"pts_time:([\d.]+)", line)
        if m:
            cur = float(m.group(1))
        m = re.search(r"RMS_level=(-?[\d.]+|-inf)", line)
        if m and cur is not None:
            v = -90.0 if "inf" in m.group(1) else float(m.group(1))
            res["rms"].append((round(start + cur, 2), round(v, 1)))
    s0 = None
    for line in errtxt.splitlines():
        m = re.search(r"silence_start: (-?[\d.]+)", line)
        if m:
            s0 = float(m.group(1))
        m = re.search(r"silence_end: ([\d.]+)", line)
        if m and s0 is not None:
            res["silences"].append([round(start + max(s0, 0), 2), round(start + float(m.group(1)), 2)])
            s0 = None
    if s0 is not None:
        res["silences"].append([round(start + s0, 2), round(start + dur, 2)])
    if not res["rms"]:
        return res
    # loud moments: well above the median level
    levels = sorted(v for _, v in res["rms"] if v > -89)
    if levels:
        med = levels[len(levels) // 2]
        res["median_db"] = med
        loud, run_s = [], None
        for t, v in res["rms"]:
            if v > med + 8:
                run_s = run_s if run_s is not None else t
            elif run_s is not None:
                loud.append([run_s, t]); run_s = None
        if run_s is not None:
            loud.append([run_s, res["rms"][-1][0] + 0.5])
        res["loud"] = loud[:40]
    # sound but no speech (music, SFX, ambience) where captions are silent
    if transcript is not None:
        spoken = [(c["start"] - 0.3, c["end"] + 0.3) for c in transcript]
        def is_spoken(t):
            return any(a <= t <= b for a, b in spoken)
        def is_silent(t):
            return any(a <= t <= b for a, b in res["silences"])
        segs, run_s = [], None
        for t, v in res["rms"]:
            ok = v > -45 and not is_silent(t) and not is_spoken(t)
            if ok and run_s is None:
                run_s = t
            elif not ok and run_s is not None:
                if t - run_s >= 1.5:
                    segs.append([run_s, t])
                run_s = None
        if run_s is not None and res["rms"][-1][0] - run_s >= 1.5:
            segs.append([run_s, res["rms"][-1][0] + 0.5])
        res["non_speech_sound"] = segs[:60]
    return res


# ---------------------------------------------------------------- manifest
def write_manifest(out, meta, pinfo, frames_info, sheets, transcript, tsrc, audio, cuts, rng):
    start, end = rng
    dur = end - start
    L = []
    L.append(f"# Watching: {meta.get('title') or meta['source']}")
    L.append("")
    L.append(f"- Source: {meta.get('webpage_url') or meta['source']}")
    if meta.get("uploader"):
        L.append(f"- Channel: {meta['uploader']}  | uploaded {meta.get('upload_date')}  "
                 f"| views {meta.get('view_count')}  | likes {meta.get('like_count')}")
    L.append(f"- Analyzed range: {ts(start)} -> {ts(end)} ({dur:.1f}s)  | "
             f"{pinfo['width']}x{pinfo['height']} @ {pinfo['fps']} fps  | audio: {'yes' if pinfo['has_audio'] else 'NONE'}")
    L.append(f"- Keyframes: {len(frames_info)}  | contact sheets: {len(sheets)}  | transcript: {tsrc}")
    if meta.get("description"):
        L.append("\n## Description (uploader)\n")
        L.append(meta["description"].strip())
    if meta.get("chapters"):
        L.append("\n## Chapters\n")
        for c in meta["chapters"]:
            L.append(f"- {ts(c['start'] or 0)}  {c['title']}")

    # pacing
    L.append("\n## Visual pacing\n")
    shots = len(cuts) + 1
    L.append(f"- Hard cuts: {len(cuts)}  | avg shot length: {dur / shots:.1f}s  | "
             f"cuts/min: {len(cuts) / max(dur / 60, 1e-6):.1f}")
    if dur >= 20:
        nb = 6
        counts = [0] * nb
        for c in cuts:
            counts[min(int((c - start) / dur * nb), nb - 1)] += 1
        L.append("- Cuts per sixth of the video: " + " | ".join(
            f"{ts(start + i * dur / nb)}: {n}" for i, n in enumerate(counts)))
    states = sum(1 for f in frames_info if f["kind"] in ("change", "cut", "start"))
    L.append(f"- Distinct settled visual states: {states}. 'motion' = sampled during continuous movement; "
             f"'coverage' = extra sample inside a long unchanged stretch")

    # audio
    L.append("\n## Audio cues (measured, not heard)\n")
    if not pinfo["has_audio"]:
        L.append("- No audio track.")
    else:
        sil = sum(b - a for a, b in audio["silences"])
        L.append(f"- Silence: {sil:.1f}s ({sil / max(dur, 1e-6) * 100:.0f}%) | median level "
                 f"{audio.get('median_db', 'n/a')} dBFS")
        if transcript is not None:
            spk = sum(c["end"] - c["start"] for c in transcript)
            L.append(f"- Speech coverage (from transcript): ~{min(spk / max(dur, 1e-6), 1) * 100:.0f}%")
        if audio["non_speech_sound"]:
            L.append("- Sound with no speech (likely music / SFX / ambience): " + ", ".join(
                f"{ts(a)}-{ts(b)}" for a, b in audio["non_speech_sound"][:25]))
        if audio["loud"]:
            L.append("- Loud moments (>8 dB above median; hits, drops, applause, emphasis): " + ", ".join(
                f"{ts(a)}-{ts(b)}" for a, b in audio["loud"][:25]))
        if audio["silences"]:
            L.append("- Silences: " + ", ".join(f"{ts(a)}-{ts(b)}" for a, b in audio["silences"][:25]))

    L.append("\n## Contact sheets (skim these first)\n")
    if sheets:
        for s in sheets:
            L.append(f"- {s['file']}: frames #{s['frames'][0]}-#{s['frames'][-1]} "
                     f"({ts(s['range'][0])}-{ts(s['range'][1])})")
    else:
        L.append("- (Pillow not installed - view frames/ directly)")

    # interleaved timeline
    L.append("\n## Timeline (frames + speech + audio events, in order)\n")
    ev = []
    for f in frames_info:
        ev.append((f["t"], 0, f"FRAME #{f['idx']} [{f['kind']}] {f['file']}"))
    for c in transcript or []:
        ev.append((c["start"], 1, f'SAY ({ts(c["start"])}-{ts(c["end"])}): "{c["text"]}"'))
    for a, b in audio.get("non_speech_sound", []):
        ev.append((a, 2, f"SOUND (no speech) {ts(a)}-{ts(b)}"))
    for a, b in audio.get("silences", []):
        if b - a >= 1.5:
            ev.append((a, 2, f"SILENCE {ts(a)}-{ts(b)}"))
    for t, _, txt in sorted(ev, key=lambda x: (x[0], x[1])):
        L.append(f"[{ts(t)}] {txt}")
    if transcript is None:
        L.append("\n(No transcript - speech content is UNKNOWN. Do not guess what was said.)")

    with open(os.path.join(out, "manifest.md"), "w") as f:
        f.write("\n".join(L) + "\n")


# ---------------------------------------------------------------- commands
def cmd_prepare(a):
    need("ffmpeg"); need("ffprobe")
    out = os.path.abspath(a.out)
    os.makedirs(os.path.join(out, "frames"), exist_ok=True)
    start, end = parse_time(a.start), parse_time(a.end)
    video, meta, subs = ingest(a.src, out, start, end)
    pinfo = probe(video)
    if not pinfo["has_video"]:
        die("no video stream found")
    s = start or 0.0
    e = pinfo["duration"] if end is None else min(end, pinfo["duration"])
    dur = max(e - s, 0.1)
    print(f"[vw] {meta.get('title')}: {dur:.1f}s, {pinfo['width']}x{pinfo['height']}", file=sys.stderr)

    # transcript
    transcript, tsrc = None, "none"
    if subs:
        transcript = [c for c in parse_subs(subs) if s - 1 <= c["start"] <= e]
        tsrc = f"captions ({os.path.basename(subs)})"
    if not transcript and not a.no_whisper:
        print("[vw] no captions - trying local Whisper ...", file=sys.stderr)
        w, tsrc = whisper(video, out, pinfo["has_audio"])
        if w is not None:
            transcript = [c for c in w if s - 1 <= c["start"] <= e]
    if transcript is not None and not transcript:
        tsrc += " (empty)"

    # vision
    afps = a.analysis_fps or round(min(4.0, max(0.5, 7200 / dur)), 2)
    print(f"[vw] scanning visual changes at {afps} fps ...", file=sys.stderr)
    size = (AW_FINE, AH_FINE) if a.sensitivity >= 3 else (AW, AH)
    small = analyze_changes(video, s, dur, afps, size)
    picks, cuts, _ = pick_keyframes(small, a.max_frames, a.sensitivity, a.min_gap)
    print(f"[vw] extracting {len(picks)} keyframes ...", file=sys.stderr)
    frames_info = []
    for i, p in enumerate(picks):
        name = f"frames/f{i:03d}_{int(p['t'] // 60):02d}m{p['t'] % 60:04.1f}s.jpg"
        if grab(video, p["t"], os.path.join(out, name), a.width, dur=pinfo["duration"]):
            frames_info.append({"idx": i, "t": p["t"], "kind": p["kind"], "file": name, "seg": p["seg"]})
    sheets = [] if a.no_sheets else contact_sheets(frames_info, out)

    audio = audio_cues(video, s, dur, transcript) if pinfo["has_audio"] else \
        {"rms": [], "silences": [], "non_speech_sound": [], "loud": []}

    write_manifest(out, meta, pinfo, frames_info, sheets, transcript, tsrc, audio, cuts, (s, e))
    with open(os.path.join(out, "manifest.json"), "w") as f:
        json.dump({"video": video, "meta": meta, "probe": pinfo, "range": [s, e],
                   "frames": frames_info, "sheets": sheets, "cuts": cuts,
                   "transcript": transcript, "transcript_source": tsrc,
                   "audio": {k: v for k, v in audio.items() if k != "rms"}}, f, indent=1)
    est = len(frames_info) * 450 + len(sheets) * 1600
    print(json.dumps({"manifest": os.path.join(out, "manifest.md"), "frames": len(frames_info),
                      "sheets": len(sheets), "transcript": tsrc, "cuts": len(cuts),
                      "approx_image_tokens_all_frames": len(frames_info) * 450,
                      "approx_image_tokens_sheets_only": len(sheets) * 1600}, indent=1))


def load(dirp):
    p = os.path.join(dirp, "manifest.json")
    if not os.path.exists(p):
        die(f"{p} not found - run prepare first")
    with open(p) as f:
        return json.load(f)


def parse_crop(c):
    if not c:
        return None
    v = [float(x) for x in c.split(",")]
    if len(v) != 4 or not all(0 <= x <= 1 for x in v):
        die("--crop is x,y,w,h as fractions 0-1, e.g. 0.5,0,0.5,0.5 = top-right quarter")
    return v


def cmd_zoom(a):
    m = load(a.dir)
    s, e = parse_time(a.start), parse_time(a.end)
    if e <= s:
        die("--end must be after --start")
    n = int((e - s) * a.fps)
    if n > a.max:
        a.fps = a.max / (e - s)
        n = a.max
        print(f"[vw] capped to {n} frames ({a.fps:.2f} fps)", file=sys.stderr)
    sub = os.path.join(a.dir, f"zoom_{s:.1f}-{e:.1f}")
    os.makedirs(sub, exist_ok=True)
    crop = parse_crop(a.crop)
    files = []
    for i in range(max(n, 1)):
        t = s + (i + 0.5) / a.fps if n else s
        name = f"z{i:03d}_{int(t // 60):02d}m{t % 60:05.2f}s.jpg"
        if grab(m["video"], t, os.path.join(sub, name), a.width, crop, m["probe"]["duration"]):
            files.append({"idx": i, "t": round(t, 2), "kind": "zoom",
                          "file": os.path.relpath(os.path.join(sub, name), a.dir)})
    sheets = contact_sheets([dict(f, file=os.path.basename(f["file"])) for f in files], sub,
                            per_sheet=16, cols=4, thumb=480) if not a.no_sheets else []
    said = [c for c in (m.get("transcript") or []) if c["end"] >= s - 0.5 and c["start"] <= e + 0.5]
    print(json.dumps({"window": [ts(s), ts(e)], "fps": round(a.fps, 2), "frames": [f["file"] for f in files],
                      "sheets": [os.path.relpath(os.path.join(sub, x["file"]), a.dir) for x in sheets],
                      "speech_in_window": [f'{ts(c["start"])} "{c["text"]}"' for c in said]}, indent=1))


def cmd_frame(a):
    m = load(a.dir)
    t = parse_time(a.at)
    crop = parse_crop(a.crop)
    tag = "_crop" if crop else ""
    name = os.path.join(a.dir, f"hi_{t:.2f}s{tag}.jpg")
    if not grab(m["video"], t, name, a.width, crop, m["probe"]["duration"]):
        die(f"could not extract a frame at {ts(t)} (video is {ts(m['probe']['duration'])} long)")
    print(name)


def cmd_colors(a):
    """Measured palette: dominant colours + saturated accents, as hex with share of screen."""
    m = load(a.dir)
    dur = m["probe"]["duration"]
    times = [parse_time(x) for x in a.at.split(",")] if a.at else [f["t"] for f in m["frames"]]
    counts = {}
    for t in times:
        t = max(0.0, min(t, dur - 0.25))
        p = run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", m["video"], "-frames:v", "1",
                 # neighbor, not area: no blending, so thin text keeps its true colour
                 "-vf", "scale=320:180:flags=neighbor", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], check=False)
        px = p.stdout or b""
        for i in range(0, len(px) - 2, 3):
            k = (px[i] >> 3 << 3, px[i + 1] >> 3 << 3, px[i + 2] >> 3 << 3)  # 32 levels per channel
            counts[k] = counts.get(k, 0) + 1
    total = sum(counts.values()) or 1
    # ponytail: greedy merge of near colours (O(n*k)); fine for a few thousand buckets
    merged = []
    for c, n in sorted(counts.items(), key=lambda x: -x[1]):
        for g in merged:
            if sum((c[i] - g["c"][i]) ** 2 for i in range(3)) < 20 ** 2:
                g["n"] += n
                break
        else:
            merged.append({"c": c, "n": n})

    def sat(c):
        hi, lo = max(c), min(c)
        return 0 if hi == 0 else (hi - lo) / hi

    def fmt(g):
        return {"hex": "#%02X%02X%02X" % tuple(min(255, v + 4) for v in g["c"]),
                "share": f"{100 * g['n'] / total:.1f}%"}

    merged.sort(key=lambda g: -g["n"])
    dominant = [fmt(g) for g in merged[:a.n]]
    accents = [fmt(g) for g in merged if sat(g["c"]) > 0.45 and max(g["c"]) > 80
               and g["n"] / total > 0.0003][:a.n]  # small on screen, but they carry the brand
    print(json.dumps({"frames_sampled": len(times), "dominant": dominant, "accents": accents}, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("prepare")
    p.add_argument("src", help="YouTube/any URL, or local video path")
    p.add_argument("--out", required=True)
    p.add_argument("--start"); p.add_argument("--end")
    p.add_argument("--max-frames", type=int, default=60)
    p.add_argument("--width", type=int, default=768, help="long side of keyframes (px)")
    p.add_argument("--sensitivity", type=float, default=2.0, help=">1 catches smaller changes (screen recordings: 2-3)")
    p.add_argument("--min-gap", type=float, default=0.8, help="min seconds between visual states")
    p.add_argument("--analysis-fps", type=float)
    p.add_argument("--no-whisper", action="store_true")
    p.add_argument("--no-sheets", action="store_true")
    p.set_defaults(fn=cmd_prepare)
    z = sp.add_parser("zoom")
    z.add_argument("--dir", required=True); z.add_argument("--start", required=True)
    z.add_argument("--end", required=True); z.add_argument("--fps", type=float, default=4)
    z.add_argument("--width", type=int, default=1024); z.add_argument("--max", type=int, default=32)
    z.add_argument("--crop"); z.add_argument("--no-sheets", action="store_true")
    z.set_defaults(fn=cmd_zoom)
    f = sp.add_parser("frame")
    f.add_argument("--dir", required=True); f.add_argument("--at", required=True)
    f.add_argument("--width", type=int, default=1920); f.add_argument("--crop")
    f.set_defaults(fn=cmd_frame)
    c = sp.add_parser("colors", help="measured palette (hex) across keyframes or given times")
    c.add_argument("--dir", required=True); c.add_argument("--at", help="comma-separated times; default: all keyframes")
    c.add_argument("--n", type=int, default=8)
    c.set_defaults(fn=cmd_colors)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
