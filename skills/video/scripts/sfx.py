#!/usr/bin/env python3
"""sfx.py - find openly licensed sound effects on Openverse and place them on a
video's timeline so every hit lands on its moment.

Subcommands
  search QUERY [--dir DIR]       Search Openverse audio (metadata only, nothing is
                                 downloaded). Saves candidates to DIR/sound/.
  fetch ID [ID ...] --dir DIR --yes
                                 Download chosen clips. Refuses without --yes: the
                                 user must say yes first. Measures each clip's
                                 lead-in silence and its peak.
  plan  --dir DIR --cues CUES.json [--snap 0.15]
                                 Turn a cue sheet into a sample-accurate timeline,
                                 snapping to cuts/loud hits from manifest.json, and
                                 write timeline.md + CREDITS.md.
  mix   --dir DIR --out OUT.mp4  Render a preview: the original video with the
                                 planned clips mixed in (or --stem for SFX only).

Openverse: https://api.openverse.org/v1/audio/ - no key needed. Anonymous use is
rate limited (about 20 requests/min); set OPENVERSE_TOKEN for more.
Requires: ffmpeg + ffprobe for fetch/plan/mix. Standard library only otherwise.
"""
import argparse
import array
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vw import die, need, parse_time, probe, run, ts  # noqa: E402

API = os.environ.get("VW_OPENVERSE_API", "https://api.openverse.org/v1").rstrip("/")
UA = "claude-video-watch/0.4 (+https://github.com/gowtham012/video-watch)"
# Safe for a video by default: commercial use and adaptation allowed (syncing a
# sound to picture is an adaptation under CC 4.0), no ShareAlike on the whole video.
SAFE_LICENSES = "cc0,pdm,by"
LICENSE_NOTES = {
    "by-sa": "ShareAlike: the finished video must carry CC BY-SA too",
    "by-nc": "NonCommercial: no monetized or commercial use",
    "by-nc-sa": "NonCommercial + ShareAlike",
    "by-nd": "NoDerivatives: cannot be synced into a video",
    "by-nc-nd": "NoDerivatives: cannot be synced into a video",
    "sampling+": "Sampling+: check the license terms",
    "nc-sampling+": "NonCommercial Sampling+: check the license terms",
}


# ---------------------------------------------------------------- helpers
def sound_dir(d):
    p = os.path.join(os.path.abspath(d), "sound")
    os.makedirs(p, exist_ok=True)
    return p


def read_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)


def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=1)


def api_get(path, params=None):
    url = f"{API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, "")})
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    if os.environ.get("OPENVERSE_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['OPENVERSE_TOKEN']}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            die("Openverse rate limit hit (anonymous: about 20 requests/min). Wait a minute, "
                "or set OPENVERSE_TOKEN (free: https://api.openverse.org/v1/#tag/auth).")
        if e.code == 404:
            die(f"not found on Openverse: {path}")
        die(f"Openverse returned HTTP {e.code} for {url}")
    except urllib.error.URLError as e:
        die(f"could not reach Openverse ({e.reason}). If this is a sandbox, the host may be "
            "blocked; run it where the network allows api.openverse.org.")


def slim(r):
    """keep what choosing, crediting and placing a clip needs"""
    return {
        "id": r["id"], "title": r.get("title"), "creator": r.get("creator"),
        "creator_url": r.get("creator_url"), "license": r.get("license"),
        "license_version": r.get("license_version"), "license_url": r.get("license_url"),
        "attribution": r.get("attribution"), "source": r.get("source") or r.get("provider"),
        "landing_url": r.get("foreign_landing_url"), "url": r.get("url"),
        "filetype": r.get("filetype"), "filesize": r.get("filesize"),
        "duration_s": round(r["duration"] / 1000, 2) if r.get("duration") else None,
        "category": r.get("category"), "tags": [t.get("name") for t in r.get("tags") or []][:8],
    }


def pcm(path, rate=8000):
    """decode to mono 16-bit samples for timing measurements"""
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(rate),
                        "-f", "s16le", "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        die(f"could not decode {path}: {p.stderr.decode('utf-8', 'replace')[-300:]}")
    s = array.array("h")
    s.frombytes(p.stdout[: len(p.stdout) // 2 * 2])
    if sys.byteorder == "big":
        s.byteswap()
    return s


def measure(path, rate=8000):
    """lead-in silence (first sample above -40 dBFS) and peak time, in seconds"""
    s = pcm(path, rate)
    if not s:
        return {"duration_s": 0.0, "lead_in_s": 0.0, "peak_s": 0.0}
    thr = 32768 * 10 ** (-40 / 20)
    lead = next((i for i, v in enumerate(s) if abs(v) > thr), 0)
    # the hit: first moment a short RMS window gets within 1 dB of the loudest
    # window (the attack of the main transient, not the end of a sustained plateau)
    win = max(1, rate // 50)
    sq = [v * v for v in s]
    energy, acc = [], 0
    for i, v in enumerate(sq):
        acc += v
        if i >= win:
            acc -= sq[i - win]
        energy.append(acc)
    top = max(energy) * 10 ** (-1 / 10)
    hit = next(i for i, e in enumerate(energy) if e >= top) - win // 2
    return {"duration_s": round(len(s) / rate, 3), "lead_in_s": round(lead / rate, 3),
            "peak_s": round(max(hit, 0) / rate, 3)}


def anchors(manifest):
    """moments a sound can lock onto: hard cuts and the starts of loud hits"""
    pts = [("cut", float(c)) for c in manifest.get("cuts", [])]
    pts += [("loud", float(a)) for a, _ in manifest.get("audio", {}).get("loud", [])]
    return sorted(pts, key=lambda x: x[1])


# ---------------------------------------------------------------- commands
def cmd_search(a):
    params = {"q": a.query, "category": a.category, "length": a.length,
              "license": a.license, "extension": a.extension, "source": a.source,
              "page_size": min(max(a.max, 1), 20), "page": a.page}
    data = api_get("/audio/", params)
    rows = [slim(r) for r in data.get("results", [])]
    if a.dir:
        p = os.path.join(sound_dir(a.dir), "candidates.json")
        seen = read_json(p, {})
        for r in rows:
            seen[r["id"]] = dict(r, query=a.query)
        write_json(p, seen)
    print(json.dumps({"query": a.query, "total": data.get("result_count"), "shown": len(rows),
                      "license_filter": a.license, "results": [
                          {"n": i + 1, "id": r["id"], "title": r["title"], "creator": r["creator"],
                           "license": f"{r['license']} {r['license_version'] or ''}".strip(),
                           "note": LICENSE_NOTES.get(r["license"]), "secs": r["duration_s"],
                           "type": r["filetype"], "preview": r["landing_url"]}
                          for i, r in enumerate(rows)]}, indent=1))


def cmd_fetch(a):
    if not a.yes:
        die("not downloading: ask the user first, then re-run with --yes. "
            "Tell them which clips (title, creator, license) and roughly how big.")
    need("ffmpeg")
    sd = sound_dir(a.dir)
    os.makedirs(os.path.join(sd, "clips"), exist_ok=True)
    cands = read_json(os.path.join(sd, "candidates.json"), {})
    lib_p = os.path.join(sd, "library.json")
    lib = read_json(lib_p, {})
    out = []
    for cid in a.ids:
        meta = slim(api_get(f"/audio/{urllib.parse.quote(cid)}/")) if cid not in cands else cands[cid]
        if not meta.get("url"):
            die(f"{cid}: Openverse has no file URL for this clip")
        ext = (meta.get("filetype") or os.path.splitext(urllib.parse.urlparse(meta["url"]).path)[1][1:]
               or "audio").lower()
        dest = os.path.join(sd, "clips", f"{cid}.{ext}")
        if not os.path.exists(dest):
            req = urllib.request.Request(meta["url"], headers={"User-Agent": UA})
            try:
                with urllib.request.urlopen(req, timeout=60) as r, open(dest + ".part", "wb") as f:
                    f.write(r.read())
            except (urllib.error.URLError, OSError) as e:
                die(f"{cid}: download failed from {urllib.parse.urlparse(meta['url']).netloc}: {e}")
            os.replace(dest + ".part", dest)
        meta = dict(meta, file=os.path.relpath(dest, sd), **measure(dest))
        lib[cid] = meta
        out.append({k: meta[k] for k in ("id", "title", "license", "file", "duration_s",
                                         "lead_in_s", "peak_s")})
    write_json(lib_p, lib)
    print(json.dumps({"fetched": out}, indent=1))


def cmd_plan(a):
    d = os.path.abspath(a.dir)
    sd = sound_dir(d)
    lib = read_json(os.path.join(sd, "library.json"), {})
    manifest = read_json(os.path.join(d, "manifest.json"), {})
    marks = anchors(manifest)
    vid_dur = (manifest.get("probe") or {}).get("duration")
    cues = read_json(a.cues, None)
    if not isinstance(cues, list) or not cues:
        die(f"{a.cues}: expected a JSON list of cues")
    timeline, credits, warn = [], {}, []
    for i, c in enumerate(cues, 1):
        cid = c.get("id")
        if cid not in lib:
            die(f"cue {i}: clip {cid} is not downloaded - fetch it first (with the user's yes)")
        clip = lib[cid]
        at = parse_time(c["at"])
        snapped = None
        if a.snap > 0 and c.get("snap", True) and marks:
            kind, t = min(marks, key=lambda m: abs(m[1] - at))
            if abs(t - at) <= a.snap:
                snapped, at = f"{kind} {ts(t)}", t
        anchor = c.get("anchor", "start")  # start: first audible sample; peak: loudest moment
        hit = clip["peak_s"] if anchor == "peak" else clip["lead_in_s"]
        place = at - hit                    # where the file's sample 0 goes on the video
        trim = max(0.0, -place)             # clip would start before 0:00 - cut its head
        length = clip["duration_s"] - trim
        if c.get("max_len"):
            length = min(length, float(c["max_len"]))
        if vid_dur:
            length = min(length, max(vid_dur - max(place, 0.0), 0.0))
        if length <= 0.01:
            warn.append(f"cue {i}: nothing left of {clip['title']!r} after trimming - skipped")
            continue
        lic = clip.get("license") or ""
        if lic not in SAFE_LICENSES.split(","):
            warn.append(f"cue {i}: {clip['title']!r} is {lic}: {LICENSE_NOTES.get(lic, 'check terms')}")
        timeline.append({
            "n": i, "id": cid, "title": clip["title"], "file": clip["file"],
            "hit_at": round(at, 3), "anchor": anchor, "snapped_to": snapped,
            "place_at": round(max(place, 0.0), 3), "trim_head": round(trim, 3),
            "length": round(length, 3), "gain_db": float(c.get("gain_db", 0)),
            "fade_out": float(c.get("fade_out", min(0.15, length / 3))), "why": c.get("why", ""),
        })
        credits[cid] = clip
    write_json(os.path.join(sd, "timeline.json"), {"video": manifest.get("video"), "cues": timeline})

    L = ["# Sound timeline", "",
         "Each clip is placed so its *hit* (first audible sample, or its peak for anchor=peak) "
         "lands exactly on `hit_at`, so lead-in silence in the file can't push it late.", "",
         "| # | Hit at | Clip | Placed at | Length | Gain | Snapped to | Why |",
         "|---|---|---|---|---|---|---|---|"]
    for t in timeline:
        L.append(f"| {t['n']} | {ts(t['hit_at'])} | {t['title']} ({t['anchor']}) | {ts(t['place_at'])}"
                 f"{' (head trimmed ' + str(t['trim_head']) + 's)' if t['trim_head'] else ''} | "
                 f"{t['length']:.2f}s | {t['gain_db']:+.0f} dB | {t['snapped_to'] or '-'} | {t['why']} |")
    if warn:
        L += ["", "## Check before publishing", ""] + [f"- {w}" for w in warn]
    with open(os.path.join(sd, "timeline.md"), "w") as f:
        f.write("\n".join(L) + "\n")

    C = ["# Sound credits", "",
         "Sounds from Openverse (openverse.org). Paste this into the video description.", ""]
    for clip in credits.values():
        C.append(f"- {clip.get('attribution') or (clip['title'] + ' by ' + (clip.get('creator') or 'unknown'))}"
                 + (f" Source: {clip['landing_url']}" if clip.get("landing_url") else ""))
    with open(os.path.join(sd, "CREDITS.md"), "w") as f:
        f.write("\n".join(C) + "\n")
    print(json.dumps({"timeline": os.path.join(sd, "timeline.md"),
                      "credits": os.path.join(sd, "CREDITS.md"),
                      "cues": len(timeline), "warnings": warn}, indent=1))


def cmd_mix(a):
    need("ffmpeg"); need("ffprobe")
    d = os.path.abspath(a.dir)
    sd = sound_dir(d)
    plan = read_json(os.path.join(sd, "timeline.json"), None)
    if not plan or not plan["cues"]:
        die("no timeline - run plan first")
    video = a.video or plan.get("video")
    if not video or not os.path.exists(video):
        die("video not found - pass --video")
    out = os.path.abspath(a.out)
    if os.path.abspath(video) == out:
        die("--out must be a new file; the original is never overwritten")
    info = probe(video)
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", video]
    parts, labels = [], []
    for k, t in enumerate(plan["cues"], 1):
        cmd += ["-i", os.path.join(sd, t["file"])]
        delay = int(round(t["place_at"] * 1000))
        fade_st = max(t["length"] - t["fade_out"], 0)
        parts.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,"
                     f"atrim=start={t['trim_head']:.3f}:duration={t['length']:.3f},asetpts=PTS-STARTPTS,"
                     f"afade=t=out:st={fade_st:.3f}:d={t['fade_out']:.3f},volume={t['gain_db']}dB,"
                     f"adelay={delay}|{delay}[s{k}]")
        labels.append(f"[s{k}]")
    n = len(labels)
    if a.stem or not info["has_audio"]:
        parts.append(f"{''.join(labels)}amix=inputs={n}:normalize=0:duration=longest,"
                     f"apad=whole_dur={info['duration']:.3f}[mix]")
    else:
        parts.append(f"[0:a]aresample=48000,aformat=channel_layouts=stereo,volume={a.bed_db}dB[bed]")
        parts.append(f"[bed]{''.join(labels)}amix=inputs={n + 1}:normalize=0:duration=first[mix]")
    cmd += ["-filter_complex", ";".join(parts), "-map", "[mix]"]
    if a.stem:
        cmd += ["-c:a", "pcm_s16le", out]
    else:
        cmd += ["-map", "0:v", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out]
    if a.dry_run:
        print(" ".join(f"'{c}'" if " " in c or ";" in c else c for c in cmd))
        return
    run(cmd)
    print(json.dumps({"out": out, "clips": n, "stem": bool(a.stem)}, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("search", help="search Openverse audio (metadata only)")
    s.add_argument("query")
    s.add_argument("--dir", help="video work dir; saves candidates to DIR/sound/")
    s.add_argument("--category", default="sound_effect",
                   help="sound_effect | music | podcast | audiobook | news | pronunciation (comma list)")
    s.add_argument("--length", default="shortest,short", help="shortest | short | medium | long (comma list)")
    s.add_argument("--license", default=SAFE_LICENSES,
                   help=f"comma list, default {SAFE_LICENSES} (safe to sync into a commercial video)")
    s.add_argument("--extension", help="e.g. wav,mp3")
    s.add_argument("--source", help="e.g. freesound,wikimedia_audio")
    s.add_argument("--max", type=int, default=8)
    s.add_argument("--page", type=int, default=1)
    s.set_defaults(fn=cmd_search)
    f = sp.add_parser("fetch", help="download chosen clips (needs the user's yes)")
    f.add_argument("ids", nargs="+")
    f.add_argument("--dir", required=True)
    f.add_argument("--yes", action="store_true", help="the user has approved this download")
    f.set_defaults(fn=cmd_fetch)
    p = sp.add_parser("plan", help="cue sheet -> timeline.md + CREDITS.md")
    p.add_argument("--dir", required=True)
    p.add_argument("--cues", required=True)
    p.add_argument("--snap", type=float, default=0.15, help="snap to a cut/loud hit within N seconds (0 = off)")
    p.set_defaults(fn=cmd_plan)
    m = sp.add_parser("mix", help="render a preview with the clips mixed in")
    m.add_argument("--dir", required=True)
    m.add_argument("--out", required=True)
    m.add_argument("--video", help="default: the video from manifest.json")
    m.add_argument("--bed-db", type=float, default=0.0, help="gain on the original audio")
    m.add_argument("--stem", action="store_true", help="write only the SFX track as WAV")
    m.add_argument("--dry-run", action="store_true", help="print the ffmpeg command only")
    m.set_defaults(fn=cmd_mix)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
