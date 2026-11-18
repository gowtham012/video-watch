#!/usr/bin/env python3
"""eleven.py - ElevenLabs voices, voiceover, music and sound effects for /video.

Standard library only. The API key is never printed and never passes through
the chat: `setup` asks for it in a private macOS dialog and keeps it in the
user's Keychain (or reads ELEVENLABS_API_KEY if set).

  eleven.py setup [--check | --forget]          store / check / remove the key
  eleven.py credits                              characters left on the plan
  eleven.py voices --dir D [--pick]              list voices; --pick opens a picker page
  eleven.py speak  --dir D [--voice ID] (--text T | --script lines.json)
  eleven.py music  --dir D --prompt P --seconds N
  eleven.py sfx    --dir D --text T --name N [--seconds S]
  eleven.py mix    --dir D --video V --out OUT [--voice-at id@sec ...] [--sfx-at file@sec ...]
"""
import argparse
import base64
import getpass
import json
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

API = os.environ.get("ELEVENLABS_BASE_URL", "https://api.elevenlabs.io").rstrip("/")
KEYCHAIN_SERVICE = "video-watch-elevenlabs"
TTS_MODEL = "eleven_multilingual_v2"


def die(msg, code=1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


# ---------------------------------------------------------------- key handling
def keychain_get():
    if platform.system() != "Darwin" or not shutil.which("security"):
        return None
    p = subprocess.run(["security", "find-generic-password", "-a", getpass.getuser(), "-s", KEYCHAIN_SERVICE, "-w"],
                       capture_output=True, text=True)
    return (p.stdout.strip() or None) if p.returncode == 0 else None


def api_key():
    k = os.environ.get("ELEVENLABS_API_KEY") or keychain_get()
    if not k:
        die("No ElevenLabs key yet. Run: eleven.py setup  (a private dialog asks for it; it is stored in your Keychain).", 2)
    return k


def ask_key_dialog():
    """Private macOS dialog with a hidden field. Returns the key, or None if cancelled."""
    script = ('display dialog "Paste your ElevenLabs API key.\\n\\nFind it at elevenlabs.io > Developers > API Keys. '
              'It is saved in your Mac\'s Keychain and is never shown in the chat." '
              'default answer "" with hidden answer with title "video-watch: ElevenLabs" '
              'buttons {"Cancel", "Save"} default button "Save"\n'
              'text returned of result')
    p = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 and p.stdout.strip() else None


# ---------------------------------------------------------------- http
def call(method, path, key=None, params=None, body=None, raw=False, timeout=300):
    url = API + path + ("?" + urllib.parse.urlencode(params, doseq=True) if params else "")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "xi-api-key": key or api_key(), "Content-Type": "application/json", "Accept": "*/*",
        "User-Agent": "video-watch/eleven.py"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = r.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:600]
        hint = {401: "The API key was rejected. Run: eleven.py setup",
                402: "Your ElevenLabs plan doesn't include this, or you're out of credits.",
                403: "Your ElevenLabs plan doesn't allow this feature (music needs a paid plan).",
                429: "ElevenLabs is rate limiting. Wait a minute and try again."}.get(e.code, "")
        die(f"ElevenLabs {e.code} on {path}. {hint}\n{detail}")
    except urllib.error.URLError as e:
        die(f"Could not reach ElevenLabs ({e.reason}). Check the internet connection.")
    return payload if raw else json.loads(payload or b"{}")


def ensure_dir(d):
    os.makedirs(d, exist_ok=True)
    return d


def media_seconds(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    try:
        return round(float(p.stdout.strip()), 3)
    except ValueError:
        return None


# ---------------------------------------------------------------- setup / credits
def credits_summary(sub):
    used, limit = sub.get("character_count"), sub.get("character_limit")
    return {"plan": sub.get("tier"), "characters_used": used, "characters_limit": limit,
            "characters_left": (limit - used) if isinstance(used, int) and isinstance(limit, int) else None}


def cmd_setup(a):
    if a.forget:
        subprocess.run(["security", "delete-generic-password", "-a", getpass.getuser(), "-s", KEYCHAIN_SERVICE],
                       capture_output=True)
        print("Removed the ElevenLabs key from your Keychain.")
        return
    if a.check:
        k = os.environ.get("ELEVENLABS_API_KEY") or keychain_get()
        if not k:
            print(json.dumps({"key": "missing"}))
            sys.exit(2)
        print(json.dumps({"key": "ok", **credits_summary(call("GET", "/v1/user/subscription", key=k))}, indent=1))
        return
    if platform.system() != "Darwin":
        die("The setup dialog is macOS only. Set ELEVENLABS_API_KEY in your environment instead.")
    k = ask_key_dialog()
    if not k:
        die("Setup cancelled; no key saved.", 3)
    sub = call("GET", "/v1/user/subscription", key=k)  # validate before saving
    # ponytail: key reaches `security` as an argument (briefly visible to `ps` on this Mac); fine on a personal machine
    p = subprocess.run(["security", "add-generic-password", "-a", getpass.getuser(), "-s", KEYCHAIN_SERVICE,
                        "-l", "ElevenLabs API key (video-watch)", "-w", k, "-U"], capture_output=True, text=True)
    if p.returncode != 0:
        die("Could not save to the Keychain: " + p.stderr.strip())
    print(json.dumps({"key": "saved", **credits_summary(sub)}, indent=1))


def cmd_credits(a):
    print(json.dumps(credits_summary(call("GET", "/v1/user/subscription")), indent=1))


# ---------------------------------------------------------------- voices + picker
def fetch_voices(key):
    voices, token = [], None
    while True:
        params = {"page_size": 100}
        if token:
            params["next_page_token"] = token
        r = call("GET", "/v2/voices", key=key, params=params)
        voices += r.get("voices", [])
        token = r.get("next_page_token")
        if not r.get("has_more") or not token:
            return voices


def slim_voice(v):
    lab = v.get("labels") or {}
    return {"voice_id": v.get("voice_id"), "name": v.get("name"), "category": v.get("category"),
            "gender": lab.get("gender"), "age": lab.get("age"), "accent": lab.get("accent"),
            "use_case": lab.get("use_case") or lab.get("use case"), "descriptive": lab.get("descriptive"),
            "description": (v.get("description") or "")[:200], "preview_url": v.get("preview_url")}


PICKER = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Choose a voice</title><style>
:root{--bg:#F5F5FB;--ink:#0A0A12;--sec:#5B6072;--pri:#4F46E5;--card:#fff;--line:#E4E5F0}
@media (prefers-color-scheme:dark){:root{--bg:#0E0F16;--ink:#F2F3F8;--sec:#A3A7B7;--pri:#8B85F5;--card:#181A24;--line:#2A2D3A}}
*{box-sizing:border-box}body{margin:0;font:16px/1.45 -apple-system,BlinkMacSystemFont,"Inter",sans-serif;background:var(--bg);color:var(--ink)}
header{position:sticky;top:0;background:var(--bg);padding:24px 24px 12px;border-bottom:1px solid var(--line);z-index:2}
h1{margin:0 0 4px;font-size:26px;font-weight:600}p.sub{margin:0 0 14px;color:var(--sec)}
.bar{display:flex;gap:10px;flex-wrap:wrap}input,select{font:inherit;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--ink)}
input{flex:1;min-width:220px}main{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px;padding:20px 24px 80px}
.c{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px;display:flex;flex-direction:column;gap:8px}
.c h2{margin:0;font-size:18px}.tags{display:flex;gap:6px;flex-wrap:wrap}.t{font-size:12px;padding:3px 9px;border-radius:99px;background:rgba(79,70,229,.12);color:var(--pri)}
.d{color:var(--sec);font-size:14px;flex:1}.row{display:flex;gap:8px}
button{font:inherit;font-weight:600;border:0;border-radius:10px;padding:10px 14px;cursor:pointer}
.play{background:rgba(79,70,229,.12);color:var(--pri);flex:1}.use{background:#4F46E5;color:#fff;flex:1}
button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid var(--pri);outline-offset:2px}
.done{position:fixed;inset:0;display:none;align-items:center;justify-content:center;background:var(--bg);font-size:22px;text-align:center;padding:24px}
</style></head><body>
<header><h1>Choose a voice for your video</h1><p class="sub">Press &#9654; Listen to hear each voice. Click <b>Use this voice</b> on the one you like. Claude picks it up automatically.</p>
<div class="bar"><input id="q" placeholder="Search: warm, British, narration, young..." aria-label="Search voices">
<select id="g" aria-label="Gender"><option value="">Any gender</option></select>
<select id="ac" aria-label="Accent"><option value="">Any accent</option></select>
<select id="u" aria-label="Style"><option value="">Any style</option></select></div></header>
<main id="list" aria-live="polite"></main><div class="done" id="done" role="status"></div>
<script>
const V=__VOICES__;const $=s=>document.querySelector(s);let audio=null;
function opts(sel,key){[...new Set(V.map(v=>v[key]).filter(Boolean))].sort().forEach(x=>{const o=document.createElement('option');o.value=o.textContent=x;sel.appendChild(o)})}
opts($('#g'),'gender');opts($('#ac'),'accent');opts($('#u'),'use_case');
function esc(s){return (s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function draw(){const q=$('#q').value.toLowerCase(),g=$('#g').value,a=$('#ac').value,u=$('#u').value;
$('#list').innerHTML=V.filter(v=>(!g||v.gender===g)&&(!a||v.accent===a)&&(!u||v.use_case===u)&&(!q||JSON.stringify(v).toLowerCase().includes(q)))
.map(v=>`<div class="c"><h2>${esc(v.name)}</h2><div class="tags">${[v.gender,v.age,v.accent,v.use_case,v.descriptive].filter(Boolean).map(t=>`<span class="t">${esc(t)}</span>`).join('')}</div>
<div class="d">${esc(v.description)}</div><div class="row">${v.preview_url?`<button class="play" data-p="${esc(v.preview_url)}">&#9654; Listen</button>`:''}
<button class="use" data-id="${esc(v.voice_id)}" data-n="${esc(v.name)}">Use this voice</button></div></div>`).join('')||'<p>No voices match.</p>'}
['#q','#g','#ac','#u'].forEach(s=>$(s).addEventListener('input',draw));draw();
document.addEventListener('click',async e=>{const b=e.target.closest('button');if(!b)return;
if(b.dataset.p){if(audio)audio.pause();audio=new Audio(b.dataset.p);audio.play();return}
if(b.dataset.id){if(audio)audio.pause();const r=await fetch('/choose',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({voice_id:b.dataset.id})});
$('#done').style.display='flex';$('#done').textContent=r.ok?'\\u2713 '+b.dataset.n+' selected. You can close this tab and go back to Claude.':'Something went wrong. Go back to Claude and ask it to open the picker again.'}});
</script></body></html>"""


def serve_picker(voices, out_dir, timeout_s):
    chosen = {}
    page = PICKER.replace("__VOICES__", json.dumps(voices).replace("</", "<\\/")).encode()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(page)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", "0") or 0)
            try:
                vid = json.loads(self.rfile.read(n) or b"{}").get("voice_id")
            except json.JSONDecodeError:
                vid = None
            match = next((v for v in voices if v["voice_id"] == vid), None) if self.path == "/choose" else None
            self.send_response(200 if match else 400)
            self.end_headers()
            if match:
                chosen.update(match)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)  # this Mac only, random free port
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    print(f"[eleven] voice picker open at {url} (waiting up to {timeout_s // 60} min)", file=sys.stderr, flush=True)
    if not os.environ.get("VW_NO_BROWSER"):
        webbrowser.open(url)
    end = time.time() + timeout_s
    while not chosen and time.time() < end:
        time.sleep(0.3)
    time.sleep(0.3)  # let the page receive its response
    srv.shutdown()
    if not chosen:
        die("No voice was chosen before the picker timed out. Run it again when ready.", 4)
    with open(os.path.join(out_dir, "voice.json"), "w") as f:
        json.dump(chosen, f, indent=1)
    return chosen


def cmd_voices(a):
    d = ensure_dir(a.dir)
    voices = [slim_voice(v) for v in fetch_voices(api_key())]
    with open(os.path.join(d, "voices.json"), "w") as f:
        json.dump(voices, f, indent=1)
    if a.pick:
        v = serve_picker(voices, d, a.timeout)
        print(json.dumps({"chosen": v, "saved": os.path.join(d, "voice.json")}, indent=1))
    else:
        print(json.dumps({"count": len(voices), "saved": os.path.join(d, "voices.json"),
                          "sample": [{k: v[k] for k in ("name", "gender", "accent", "use_case")} for v in voices[:12]]},
                         indent=1))


# ---------------------------------------------------------------- speak
def words_from_alignment(al):
    """Character timings -> word timings [{word, start, end}]."""
    words, cur, s, e = [], "", None, None
    for ch, cs, ce in zip(al.get("characters", []), al.get("character_start_times_seconds", []),
                          al.get("character_end_times_seconds", [])):
        if ch.isspace():
            if cur:
                words.append({"word": cur, "start": round(s, 3), "end": round(e, 3)})
            cur, s, e = "", None, None
            continue
        cur += ch
        s = cs if s is None else s
        e = ce
    if cur:
        words.append({"word": cur, "start": round(s, 3), "end": round(e, 3)})
    return words


def resolve_voice(d, voice):
    if voice:
        return voice
    p = os.path.join(d, "voice.json")
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)["voice_id"]
    die("No voice chosen. Run: eleven.py voices --dir <dir> --pick")


def cmd_speak(a):
    d = ensure_dir(os.path.join(a.dir, "audio"))
    key, voice = api_key(), resolve_voice(a.dir, a.voice)
    if a.script:
        with open(a.script) as f:
            lines = json.load(f)  # [{"id": "s1", "text": "..."}]
    else:
        lines = [{"id": "voiceover", "text": a.text}]
    chars = sum(len(l["text"]) for l in lines)
    print(f"[eleven] voicing {len(lines)} line(s), {chars} characters", file=sys.stderr)
    settings = {"stability": a.stability, "similarity_boost": 0.75, "style": a.style, "speed": a.speed}
    out = []
    for i, l in enumerate(lines):
        body = {"text": l["text"], "model_id": TTS_MODEL, "voice_settings": settings}
        # neighbouring lines keep intonation continuous across separately voiced scenes
        if i:
            body["previous_text"] = lines[i - 1]["text"]
        if i + 1 < len(lines):
            body["next_text"] = lines[i + 1]["text"]
        r = call("POST", f"/v1/text-to-speech/{voice}/with-timestamps", key=key,
                 params={"output_format": "mp3_44100_128"}, body=body)
        mp3 = os.path.join(d, f"{l['id']}.mp3")
        with open(mp3, "wb") as f:
            f.write(base64.b64decode(r["audio_base64"]))
        words = words_from_alignment(r.get("alignment") or {})
        secs = media_seconds(mp3) or (words[-1]["end"] if words else None)
        out.append({"id": l["id"], "text": l["text"], "file": mp3, "seconds": secs, "words": words})
    with open(os.path.join(d, "voiceover.json"), "w") as f:
        json.dump({"voice_id": voice, "lines": out}, f, indent=1)
    print(json.dumps({"characters": chars, "lines": [{"id": o["id"], "seconds": o["seconds"]} for o in out],
                      "saved": os.path.join(d, "voiceover.json")}, indent=1))


# ---------------------------------------------------------------- music / sfx
def cmd_music(a):
    d = ensure_dir(os.path.join(a.dir, "audio"))
    ms = int(max(3.0, min(600.0, a.seconds)) * 1000)
    data = call("POST", "/v1/music", params={"output_format": "mp3_44100_128"}, raw=True, timeout=900,
                body={"prompt": a.prompt, "music_length_ms": ms, "force_instrumental": True})
    out = os.path.join(d, a.name + ".mp3")
    with open(out, "wb") as f:
        f.write(data)
    print(json.dumps({"file": out, "seconds": media_seconds(out), "prompt": a.prompt}, indent=1))


def cmd_sfx(a):
    d = ensure_dir(os.path.join(a.dir, "audio", "sfx"))
    body = {"text": a.text, "prompt_influence": 0.5}
    if a.seconds:
        body["duration_seconds"] = max(0.5, min(30.0, a.seconds))
    data = call("POST", "/v1/sound-generation", params={"output_format": "mp3_44100_128"}, body=body, raw=True)
    out = os.path.join(d, a.name + ".mp3")
    with open(out, "wb") as f:
        f.write(data)
    print(json.dumps({"file": out, "seconds": media_seconds(out), "text": a.text}, indent=1))


# ---------------------------------------------------------------- mix onto the user's own video
def cmd_mix(a):
    """Voiceover lines at their times, music ducked under the voice, optional SFX, onto the user's video."""
    if not shutil.which("ffmpeg"):
        die("ffmpeg is missing. Install it with: brew install ffmpeg")
    vdur = media_seconds(a.video)
    if not vdur:
        die(f"Could not read the video: {a.video}")
    vo_path = os.path.join(a.dir, "audio", "voiceover.json")
    vo = json.load(open(vo_path)) if os.path.exists(vo_path) else {"lines": []}
    at = {i: float(t) for i, t in (x.rsplit("@", 1) for x in (a.voice_at or []))}
    inputs, filters, voice_labels, mix_labels = ["-i", a.video], [], [], []
    n, cursor = 1, a.voice_start
    for line in vo["lines"]:
        start = at.get(line["id"], cursor)
        cursor = start + (line["seconds"] or 0) + a.gap
        ms = int(start * 1000)
        inputs += ["-i", line["file"]]
        filters.append(f"[{n}:a]adelay={ms}|{ms},aformat=channel_layouts=stereo[v{n}]")
        voice_labels.append(f"[v{n}]")
        n += 1
    voice = bool(voice_labels)
    if voice:
        filters.append("".join(voice_labels) + f"amix=inputs={len(voice_labels)}:normalize=0,asplit=2[voice][vkey]")
        mix_labels.append("[voice]")
    music = os.path.join(a.dir, "audio", "music.mp3")
    if os.path.exists(music) and not a.no_music:
        inputs += ["-stream_loop", "-1", "-i", music]
        m = (f"[{n}:a]atrim=0:{vdur:.3f},volume={a.music_level},"
             f"afade=t=out:st={max(0.0, vdur - 2):.3f}:d=2,aformat=channel_layouts=stereo")
        if voice:  # duck the music whenever the voice speaks
            filters += [m + "[mraw]", "[mraw][vkey]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[music]"]
        else:
            filters.append(m + "[music]")
        mix_labels.append("[music]")
        n += 1
    elif voice:
        filters.append("[vkey]anullsink")
    for item in a.sfx_at or []:
        path, t = item.rsplit("@", 1)
        ms = int(float(t) * 1000)
        inputs += ["-i", path]
        filters.append(f"[{n}:a]adelay={ms}|{ms},volume={a.sfx_level},aformat=channel_layouts=stereo[s{n}]")
        mix_labels.append(f"[s{n}]")
        n += 1
    has_orig = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                               "-of", "csv=p=0", a.video], capture_output=True, text=True).stdout.strip()
    if has_orig and a.keep_original > 0:
        filters.append(f"[0:a]volume={a.keep_original},aformat=channel_layouts=stereo[orig]")
        mix_labels.append("[orig]")
    if not mix_labels:
        die("Nothing to mix: make a voiceover, music or sound effects first.")
    filters.append("".join(mix_labels) + f"amix=inputs={len(mix_labels)}:normalize=0,alimiter=limit=0.95[out]")
    cmd = ["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "0:v", "-map", "[out]",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{vdur:.3f}", a.out]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        die("ffmpeg mix failed:\n" + p.stderr[-1500:])
    print(json.dumps({"out": a.out, "seconds": media_seconds(a.out)}, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("setup", help="store the key via a private dialog")
    s.add_argument("--check", action="store_true"); s.add_argument("--forget", action="store_true")
    s.set_defaults(fn=cmd_setup)
    sp.add_parser("credits", help="characters left on the plan").set_defaults(fn=cmd_credits)
    v = sp.add_parser("voices", help="list voices; --pick opens the picker page")
    v.add_argument("--dir", required=True); v.add_argument("--pick", action="store_true")
    v.add_argument("--timeout", type=int, default=900); v.set_defaults(fn=cmd_voices)
    k = sp.add_parser("speak", help="voiceover with word timings")
    k.add_argument("--dir", required=True); k.add_argument("--voice")
    g = k.add_mutually_exclusive_group(required=True); g.add_argument("--text"); g.add_argument("--script")
    k.add_argument("--stability", type=float, default=0.5); k.add_argument("--style", type=float, default=0.2)
    k.add_argument("--speed", type=float, default=1.0); k.set_defaults(fn=cmd_speak)
    m = sp.add_parser("music", help="instrumental background music")
    m.add_argument("--dir", required=True); m.add_argument("--prompt", required=True)
    m.add_argument("--seconds", type=float, required=True); m.add_argument("--name", default="music")
    m.set_defaults(fn=cmd_music)
    f = sp.add_parser("sfx", help="one sound effect")
    f.add_argument("--dir", required=True); f.add_argument("--text", required=True)
    f.add_argument("--name", required=True); f.add_argument("--seconds", type=float); f.set_defaults(fn=cmd_sfx)
    x = sp.add_parser("mix", help="put voice, music and SFX onto an existing video")
    x.add_argument("--dir", required=True); x.add_argument("--video", required=True); x.add_argument("--out", required=True)
    x.add_argument("--voice-at", nargs="*", help='"line_id@seconds"'); x.add_argument("--voice-start", type=float, default=0.5)
    x.add_argument("--gap", type=float, default=0.4); x.add_argument("--sfx-at", nargs="*", help='"file.mp3@seconds"')
    x.add_argument("--keep-original", type=float, default=0.0); x.add_argument("--music-level", type=float, default=0.35)
    x.add_argument("--sfx-level", type=float, default=0.8); x.add_argument("--no-music", action="store_true")
    x.set_defaults(fn=cmd_mix)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
