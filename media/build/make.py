"""Render the video-watch explainer: python make.py <explainer_dir> <out.mp4>"""
import array, json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

D, OUT = os.path.abspath(sys.argv[1]), sys.argv[2]  # absolute: ffmpeg concat lists resolve relative to the list file
W, H = 1920, 1080
BG, FG, MUTED, ACC, ACC2, WARN, CARD = (13, 17, 23), (240, 244, 248), (139, 148, 158), (88, 166, 255), (63, 185, 80), (248, 81, 73), (22, 27, 34)
HN = "/System/Library/Fonts/HelveticaNeue.ttc"
f = lambda size, bold=False: ImageFont.truetype(HN, size, index=1 if bold else 0)
mono = lambda size: ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", size)
man = json.load(open(os.path.join(D, "out", "manifest.json")))
os.makedirs(os.path.join(D, "build"), exist_ok=True)


def canvas(kicker=None, title=None):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    if kicker:
        d.text((120, 90), kicker.upper(), font=f(30, True), fill=ACC)
    if title:
        d.text((120, 135), title, font=f(68, True), fill=FG)
    d.text((W - 120, H - 70), "video-watch", font=f(26), fill=MUTED, anchor="rs")
    return im, d


def card(d, box, fill=CARD, outline=(48, 54, 61), r=22):
    d.rounded_rectangle(box, r, fill=fill, outline=outline, width=2)


def thumb(path, w):
    t = Image.open(path).convert("RGB")
    return t.resize((w, int(w * t.height / t.width)), Image.LANCZOS)


def save(im, name):
    p = os.path.join(D, "build", name + ".png")
    im.save(p)
    return p


def mmss(t):
    return f"{int(t // 60):02d}:{t % 60:04.1f}"


# ---- audio envelope of the demo clip (real data)
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(D, "demo.mp4"), "-ac", "1", "-ar", "8000",
                      "-f", "s16le", "-"], capture_output=True).stdout
smp = array.array("h", raw)
step = 8000 // 8
env = [(sum(x * x for x in smp[i:i + step]) / step) ** 0.5 for i in range(0, len(smp) - step, step)]
peak = max(env) or 1
DUR = man["range"][1]

scenes = []  # (narration, [image paths])

# 1 title
im, d = canvas()
d.text((W // 2, 420), "video-watch", font=f(140, True), fill=FG, anchor="mm")
d.text((W // 2, 540), "How Claude watches a video", font=f(56), fill=ACC, anchor="mm")
d.text((W // 2, 640), "A Claude Code plugin", font=f(34), fill=MUTED, anchor="mm")
scenes.append(("Claude can read images and text, but it can't take a video file directly. "
               "video-watch turns a video into what a person actually notices.", [save(im, "01")]))

# 2 pipeline
im, d = canvas("The pipeline", "One command: prepare")
card(d, (120, 420, 480, 640)); d.text((300, 500), "Video", font=f(48, True), fill=FG, anchor="mm")
d.text((300, 570), "YouTube URL or file", font=f(28), fill=MUTED, anchor="mm")
outs = [("Keyframes", "when the picture changes"), ("Transcript", "what is said, and when"),
        ("Audio cues", "silence, music, loud hits"), ("Pacing", "cuts per minute")]
for i, (a, b) in enumerate(outs):
    y = 300 + i * 150
    card(d, (760, y, 1180, y + 120)); d.text((790, y + 25), a, font=f(40, True), fill=FG)
    d.text((790, y + 75), b, font=f(26), fill=MUTED)
    d.line((480, 530, 760, y + 60), fill=ACC, width=4)
    d.line((1180, y + 60, 1420, 530), fill=ACC, width=4)
card(d, (1420, 420, 1800, 640), outline=ACC)
d.text((1610, 500), "manifest.md", font=mono(40), fill=ACC, anchor="mm")
d.text((1610, 570), "one timeline", font=f(28), fill=MUTED, anchor="mm")
d.text((W // 2, 960), "yt-dlp downloads  ·  ffmpeg extracts  ·  Claude reads", font=f(32), fill=MUTED, anchor="mm")
scenes.append(("One command, prepare, downloads the video with y t d l p, "
               "then uses ffmpeg to pull out four things, and writes them into one timeline.", [save(im, "02")]))

# 3 keyframes: reveal real frames one by one, with a timeline of real cuts
picks = [fr for fr in man["frames"] if fr["kind"] in ("start", "cut")]
imgs = []
for k in range(1, len(picks) + 1):
    im, d = canvas("1 · Scene-aware keyframes", "A new frame when the picture settles")
    x0, x1, ty = 160, W - 160, 720
    d.line((x0, ty, x1, ty), fill=(48, 54, 61), width=6)
    for c in man["cuts"]:
        cx = x0 + (x1 - x0) * c / DUR
        d.line((cx, ty - 22, cx, ty + 22), fill=WARN, width=5)
    d.text((x0, ty + 40), "00:00", font=mono(24), fill=MUTED)
    d.text((x1, ty + 40), mmss(DUR), font=mono(24), fill=MUTED, anchor="ra")
    d.text((x0 + 10, ty - 70), "red = hard cuts detected", font=f(26), fill=WARN)
    for i, fr in enumerate(picks[:k]):
        tw = 300
        t = thumb(os.path.join(D, "out", fr["file"]), tw)
        x, y = 160 + i * 330, 330
        im.paste(t, (x, y))
        d.rectangle((x, y, x + tw, y + t.height), outline=ACC if i == k - 1 else (48, 54, 61), width=4)
        d.text((x, y + t.height + 18), f"{mmss(fr['t'])}  {fr['kind']}", font=mono(26), fill=FG)
        cx = x0 + (x1 - x0) * fr["t"] / DUR
        d.ellipse((cx - 10, ty - 10, cx + 10, ty + 10), fill=ACC)
    imgs.append(save(im, f"03_{k}"))
scenes.append(("First, scene aware keyframes. Instead of grabbing a frame every few seconds, "
               "it scans the whole video at low resolution, and keeps one frame each time the picture "
               "settles into a new state. On this test clip, it found all four cuts.", imgs))

# 4 transcript
im, d = canvas("2 · What is said", "Captions, or local Whisper")
for i, c in enumerate(man["transcript"]):
    y = 330 + i * 130
    card(d, (160, y, 1760, y + 100))
    d.text((200, y + 50), mmss(c["start"]), font=mono(36), fill=ACC, anchor="lm")
    d.text((420, y + 50), f"“{c['text']}”", font=f(40), fill=FG, anchor="lm")
d.text((160, 900), "Every line keeps its timestamp, so speech lines up with the frames.", font=f(32), fill=MUTED)
scenes.append(("Second, what's said. It uses YouTube captions or subtitle files, "
               "and falls back to local Whisper. Every line keeps its timestamp.", [save(im, "04")]))

# 5 audio: real envelope + real detected events
im, d = canvas("3 · What the sound is doing", "Measured from the waveform")
x0, x1, base, hgt = 160, W - 160, 760, 360
au = man["audio"]
for s, e in au["silences"]:
    d.rectangle((x0 + (x1 - x0) * s / DUR, base - hgt, x0 + (x1 - x0) * e / DUR, base), outline=WARN, width=3)
for s, e in au["loud"]:
    d.rectangle((x0 + (x1 - x0) * s / DUR - 6, base - hgt, x0 + (x1 - x0) * e / DUR + 6, base), outline=(240, 180, 60), width=3)
bw = (x1 - x0) / len(env)
for i, v in enumerate(env):
    h = max(3, hgt * (v / peak))
    d.rectangle((x0 + i * bw + 1, base - h, x0 + (i + 1) * bw - 1, base), fill=ACC)
for s, e in au["silences"]:
    d.text((x0 + (x1 - x0) * (s + e) / 2 / DUR, base + 40), f"silence {mmss(s)}-{mmss(e)}", font=f(30, True), fill=WARN, anchor="ma")
for s, e in au["loud"]:
    d.text((x0 + (x1 - x0) * (s + e) / 2 / DUR, base + 40), f"loud hit {mmss(s)}", font=f(30, True), fill=(240, 180, 60), anchor="ma")
d.text((160, 930), "It measures sound. It does not hear melody or tone of voice.", font=f(32), fill=MUTED)
scenes.append(("Third, the sound. It measures silence, music without speech, and loud hits from the waveform. "
               "It measures sound. It doesn't hear it.", [save(im, "05")]))

# 6 manifest
im, d = canvas("Everything in one place", "manifest.md")
lines = [l for l in open(os.path.join(D, "out", "manifest.md")).read().splitlines() if l.startswith("[")][:13]
card(d, (120, 280, 1800, 1000))
for i, l in enumerate(lines):
    col = ACC if " SAY " in l else WARN if "SILENCE" in l else (240, 180, 60) if "SOUND" in l else FG
    d.text((160, 315 + i * 51), l[:88], font=mono(30), fill=col)
scenes.append(("Everything lands in one timeline, manifest dot M D, with frames, speech, "
               "and sound events in time order. Claude reads this first.", [save(im, "06")]))

# 7 passes: skim sheet -> zoom -> answer
steps = []
im, d = canvas("How Claude watches", "Pass 1 · Skim the contact sheets")
sh = thumb(os.path.join(D, "out", "sheet_01.jpg"), 1100)
if sh.height > 700:
    sh = sh.resize((int(sh.width * 700 / sh.height), 700))
im.paste(sh, ((W - sh.width) // 2, 290))
steps.append(save(im, "07_1"))
im, d = canvas("How Claude watches", "Pass 2 · Zoom in where it matters")
for i, fr in enumerate([x for x in man["frames"] if 6 <= x["t"] <= 12][:4]):
    t = thumb(os.path.join(D, "out", fr["file"]), 380)
    im.paste(t, (160 + i * 410, 380))
    d.text((160 + i * 410, 380 + t.height + 16), mmss(fr["t"]), font=mono(28), fill=FG)
d.text((160, 820), "vw.py zoom --start 0:06 --end 0:12 --fps 6", font=mono(34), fill=ACC)
steps.append(save(im, "07_2"))
im, d = canvas("How Claude watches", "Pass 3 · Answer with timestamps")
card(d, (160, 320, 1760, 900))
ans = ["[00:00.5]  Opens with “Welcome to the product tour.”",
       "[00:06.6]  Hard cut to the dashboard demo",
       "[00:09.0]  3 s of dead air while the demo plays",
       "[00:20.9]  Loud hit just before the final scene",
       "[00:24.5]  Call to action: “Try it today.”"]
for i, a in enumerate(ans):
    d.text((210, 370 + i * 100), a, font=f(42), fill=FG)
steps.append(save(im, "07_3"))
scenes.append(("Then Claude watches in passes. It skims the contact sheets, like watching at double speed. "
               "It zooms into the moments that matter. And it answers with a timestamp for every claim.", steps))

# 8 numbers
im, d = canvas("Cost and speed", "Cheap enough to use every day")
for i, (big, small) in enumerate([("~6 s", "to prepare a 5 minute video"),
                                  ("7k–27k", "image tokens for 10 minutes"),
                                  ("every claim", "comes with a timestamp")]):
    x = 160 + i * 560
    card(d, (x, 360, x + 500, 760))
    d.text((x + 250, 500), big, font=f(88, True), fill=ACC, anchor="mm")
    d.text((x + 250, 640), small, font=f(32), fill=MUTED, anchor="mm")
scenes.append(("A ten minute video costs about seven to twenty seven thousand image tokens, "
               "and takes seconds to prepare.", [save(im, "08")]))

# 9 install
im, d = canvas("Try it", "Install in Claude Code")
card(d, (260, 380, 1660, 640), outline=ACC)
d.text((320, 440), "/plugin marketplace add gowtham012/video-watch", font=mono(42), fill=FG)
d.text((320, 540), "/plugin install video-watch@video-watch", font=mono(42), fill=FG)
d.text((W // 2, 780), "Then:  /watch <url>  what happens in this video?", font=f(44), fill=ACC, anchor="mm")
d.text((W // 2, 870), "Needs ffmpeg and yt-dlp:  brew install ffmpeg yt-dlp", font=f(30), fill=MUTED, anchor="mm")
scenes.append(("Install it with two commands in Claude Code. Then ask slash watch, "
               "with a link, and any question about the video.", [save(im, "09")]))

# ---- narration + assembly
clips = []
for n, (text, images) in enumerate(scenes):
    aiff = os.path.join(D, "build", f"n{n:02d}.aiff")
    subprocess.run(["say", "-v", "Samantha", "-r", "175", "-o", aiff, text], check=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", aiff],
                               capture_output=True, text=True).stdout) + 0.9
    lst = os.path.join(D, "build", f"s{n:02d}.txt")
    with open(lst, "w") as fh:
        for p in images:
            fh.write(f"file '{p}'\nduration {dur / len(images):.3f}\n")
        fh.write(f"file '{images[-1]}'\n")
    clip = os.path.join(D, "build", f"c{n:02d}.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", aiff,
                    "-filter_complex", f"[0]fps=30,format=yuv420p,fade=in:0:9,fade=out:st={dur - 0.3:.2f}:d=0.3[v];"
                    f"[1]adelay=300|300,apad,atrim=0:{dur:.3f},aformat=sample_rates=44100:channel_layouts=stereo[a]",
                    "-map", "[v]", "-map", "[a]", "-t", f"{dur:.3f}", "-c:v", "libx264", "-crf", "20",
                    "-c:a", "aac", "-b:a", "160k", clip], check=True)
    clips.append(clip)
cl = os.path.join(D, "build", "all.txt")
open(cl, "w").write("".join(f"file '{c}'\n" for c in clips))
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", cl, "-c", "copy",
                "-movflags", "+faststart", OUT], check=True)
print(OUT)
