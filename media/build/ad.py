"""Launch ad v1 (Pillow frames piped to ffmpeg). python ad.py <out.mp4> <music.wav>"""
import math, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1]
W, H, FPS = 1920, 1080, 30
BEAT = 0.5  # 120 bpm; scenes cut on beats
# palette: one job per colour
BG = (247, 248, 252)      # off-white canvas
INK = (15, 23, 42)        # text
IND = (79, 70, 229)       # brand / Claude
IND_L = (165, 160, 255)   # light indigo
COR = (255, 90, 78)       # cuts, playhead, attention
MNT = (16, 185, 129)      # done, audio
MUT = (100, 116, 139)     # secondary text
LINE = (226, 232, 240)    # hairlines / card borders
CARD = (255, 255, 255)

HN = "/System/Library/Fonts/HelveticaNeue.ttc"
_fc = {}
def F(size, w="r"):
    k = (size, w)
    if k not in _fc:
        _fc[k] = (ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", size) if w == "m"
                  else ImageFont.truetype(HN, size, index={"r": 0, "b": 1, "md": 10}[w]))
    return _fc[k]


def cl(x): return max(0.0, min(1.0, x))
def eo(x): x = cl(x); return 1 - (1 - x) ** 3                 # ease out
def eio(x): x = cl(x); return 3 * x * x - 2 * x * x * x         # ease in-out
def mix(c, a, bg=BG): return tuple(int(bg[i] + (c[i] - bg[i]) * a) for i in range(3))
def lerp(a, b, t): return a + (b - a) * t


# soft background: off-white with a faint indigo glow
bg = Image.new("RGB", (W, H), BG)
gd = ImageDraw.Draw(bg)
for y in range(H):  # faint top-to-bottom wash toward light indigo
    gd.line((0, y, W, y), fill=mix(IND_L, 0.06 * y / H))


def word_row(d, words, t, y, size, stagger=0.22, rise=40, dur=0.35, exit_at=None):
    """Words appear one by one, rising and fading in (LangEase kinetic type)."""
    fonts = [F(size, "b" if b else "md") for _, _, b in words]
    widths = [d.textlength(w, font=f) for (w, _, _), f in zip(words, fonts)]
    gap = size * 0.28
    x = W / 2 - (sum(widths) + gap * (len(words) - 1)) / 2
    for i, ((w, col, _), f) in enumerate(zip(words, fonts)):
        p = eo((t - i * stagger) / dur)
        a = p if exit_at is None else p * (1 - eo((t - exit_at) / 0.2))
        if a > 0.01:
            d.text((x, y + rise * (1 - p)), w, font=f, fill=mix(col, a), anchor="ls")
        x += widths[i] + gap


def card(d, box, r=28, outline=LINE, fill=CARD, width=2):
    x0, y0, x1, y1 = box
    d.rounded_rectangle((x0 + 6, y0 + 14, x1 + 6, y1 + 18), r, fill=mix((200, 205, 230), 0.5))  # soft shadow
    d.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)


# ------------------------------------------------------------- scenes (local time t)
def s_hook(im, d, t):
    phrases = [(0.0, [("Paste", IND, 1), ("a video.", INK, 0)]),
               (1.5, [("Claude", INK, 1), ("watches it", IND, 0)]),
               (3.0, [("like", INK, 0), ("you do.", COR, 1)])]
    for i, (st, words) in enumerate(phrases):
        nxt = phrases[i + 1][0] if i + 1 < len(phrases) else 99
        if st <= t < nxt:
            word_row(d, words, t - st, H / 2 + 45, 130, exit_at=(nxt - st - 0.2) if nxt < 99 else None)


def s_prompt(im, d, t):
    p = eo(t / 0.4)
    cw, ch = 1320, 200
    x0, y0 = (W - cw) / 2, H / 2 - ch / 2 + 40 * (1 - p)
    card(d, (x0, y0, x0 + cw, y0 + ch), outline=mix(IND, 0.35 * p, CARD))
    d.text((x0 + 50, y0 + 42), "Claude Code", font=F(28, "md"), fill=mix(MUT, p, CARD))
    msg = "/watch youtu.be/launch-film   what makes this ad work?"
    n = int(cl((t - 0.35) / 1.5) * len(msg))
    d.text((x0 + 50, y0 + 105), "›", font=F(48, "b"), fill=mix(IND, p, CARD))
    s = msg[:n]
    d.text((x0 + 100, y0 + 108), s, font=F(42, "m"), fill=INK)
    if int(t * 3) % 2 == 0 or n < len(msg):
        cx = x0 + 100 + d.textlength(s, font=F(42, "m")) + 4
        d.rectangle((cx, y0 + 108, cx + 4, y0 + 158), fill=IND)
    word_row(d, [("One", INK, 0), ("command.", IND, 1)], t - 0.2, 300, 64, stagger=0.15)


rng = random.Random(7)
CONF = [(rng.uniform(-1, 1), rng.uniform(-1.2, -0.2), rng.choice([IND, COR, MNT, IND_L]), rng.uniform(10, 22),
         rng.uniform(0, 6.28)) for _ in range(70)]


def s_progress(im, d, t):
    bw, bh, y = 1100, 56, H / 2 + 30
    x0 = (W - bw) / 2
    if t < 2.0:
        p = eio(t / 1.8)
        d.text((W / 2, y - 120), "Watching", font=F(54, "md"), fill=mix(INK, eo(t / 0.3)), anchor="mm")
        d.rounded_rectangle((x0, y, x0 + bw, y + bh), bh / 2, fill=LINE)
        fw = max(bh, bw * p)
        for i in range(int(fw)):  # indigo -> mint gradient fill
            c = tuple(int(lerp(IND[k], MNT[k], i / bw)) for k in range(3))
            d.line((x0 + i, y + 4, x0 + i, y + bh - 4), fill=c)
        d.rounded_rectangle((x0, y, x0 + fw, y + bh), bh / 2, outline=BG, width=4)
        n = int(p * 100)
        d.text((x0 + bw, y - 30), f"{n}", font=F(84, "b"), fill=IND, anchor="rs")
        d.text((x0 + bw + 6, y - 30), "/100", font=F(84, "r"), fill=mix(MUT, 0.5), anchor="ls")
    else:
        u = t - 2.0
        r = 80 * eo(u / 0.35)
        cx, cy = W / 2, y + 20
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=mix(MNT, 0.12), outline=MNT, width=6)
        k = eo((u - 0.2) / 0.35)  # draw the check
        pts = [(cx - 34, cy + 2), (cx - 8, cy + 28), (cx + 38, cy - 26)]
        if k > 0:
            if k < 0.4:
                e = (lerp(pts[0][0], pts[1][0], k / 0.4), lerp(pts[0][1], pts[1][1], k / 0.4))
                d.line([pts[0], e], fill=MNT, width=12, joint="curve")
            else:
                e = (lerp(pts[1][0], pts[2][0], (k - 0.4) / 0.6), lerp(pts[1][1], pts[2][1], (k - 0.4) / 0.6))
                d.line([pts[0], pts[1], e], fill=MNT, width=12, joint="curve")
        d.text((W / 2, y - 120), "Done", font=F(72, "b"), fill=mix(MNT, eo(u / 0.3)), anchor="mm")
        for vx, vy, c, s, rot in CONF:
            px = cx + vx * 900 * eo(u / 1.2)
            py = cy + (vy * 700 * eo(u / 1.0)) + 500 * u * u
            a = 1 - cl((u - 0.6) / 0.6)
            if a > 0:
                ang = rot + u * 5
                dx, dy = math.cos(ang) * s, math.sin(ang) * s / 2
                d.polygon([(px - dx, py - dy), (px + dy, py - dx), (px + dx, py + dy), (px - dy, py + dx)], fill=mix(c, a))


def make_thumb(i):
    """Abstract 'video frame' thumbnails in palette tones (no third-party footage)."""
    tw, th = 330, 186
    im = Image.new("RGB", (tw, th))
    a, b = [(IND, IND_L), (INK, IND), (COR, (255, 196, 160)), (MNT, (180, 240, 220)),
            ((30, 41, 59), (71, 85, 105)), (IND_L, CARD), (COR, IND), (MNT, IND)][i % 8]
    dd = ImageDraw.Draw(im)
    for y in range(th):
        dd.line((0, y, tw, y), fill=tuple(int(lerp(a[k], b[k], y / th)) for k in range(3)))
    if i % 3 == 0:
        dd.ellipse((tw / 2 - 40, th / 2 - 40, tw / 2 + 40, th / 2 + 40), fill=CARD)
    elif i % 3 == 1:
        for j in range(4):
            dd.rounded_rectangle((30, 40 + j * 30, 30 + 260 - j * 50, 54 + j * 30), 7, fill=CARD)
    else:
        dd.rounded_rectangle((40, 30, tw - 40, th - 30), 12, outline=CARD, width=5)
        dd.polygon([(tw / 2 - 18, th / 2 - 24), (tw / 2 - 18, th / 2 + 24), (tw / 2 + 26, th / 2)], fill=CARD)
    return im


THUMBS = [make_thumb(i) for i in range(10)]
CUTS = [0.13, 0.31, 0.47, 0.66, 0.84]


def s_frames(im, d, t):
    word_row(d, [("Sees", INK, 0), ("every", INK, 0), ("change.", COR, 1)], t, 230, 84, stagger=0.15)
    ph = eio(t / 5.2)  # playhead progress
    x0, x1, ty = 200, W - 200, 840
    d.line((x0, ty, x1, ty), fill=LINE, width=8)
    d.line((x0, ty, x0 + (x1 - x0) * ph, ty), fill=mix(IND, 0.6), width=8)
    for c in CUTS:
        if ph >= c:
            k = eo((ph - c) * 12)
            cx = x0 + (x1 - x0) * c
            d.line((cx, ty - 26 * k, cx, ty + 26 * k), fill=COR, width=6)
    hx = x0 + (x1 - x0) * ph
    d.ellipse((hx - 16, ty - 16, hx + 16, ty + 16), fill=COR)
    # filmstrip scrolls left; frames at cuts lift + get an indigo outline once the playhead passes
    off = -t * 120
    for i, th in enumerate(THUMBS):
        x = 140 + i * 370 + off
        if x < -360 or x > W:
            continue
        hit = i < len(CUTS) * 2 and i % 2 == 0 and ph >= CUTS[min(i // 2, len(CUTS) - 1)]
        lift = 30 * eo((ph - CUTS[min(i // 2, len(CUTS) - 1)]) * 10) if hit else 0
        y = 430 - lift
        im.paste(th, (int(x), int(y)))
        d.rounded_rectangle((x - 4, y - 4, x + th.width + 4, y + th.height + 4), 10,
                            outline=IND if hit else LINE, width=6 if hit else 2)
        if hit:
            d.text((x, y + th.height + 22), f"00:{6 + i * 7:02d}  cut", font=F(26, "m"), fill=INK)


def s_sound(im, d, t):
    word_row(d, [("Reads", INK, 0), ("the", INK, 0), ("sound.", MNT, 1)], t, 230, 84, stagger=0.15)
    n, x0, x1, base = 72, 200, W - 200, 720
    bw = (x1 - x0) / n
    sil, loud = (26, 36), (52, 55)
    for i in range(n):
        p = eo((t - i * 0.012) / 0.3)
        h = 40 + 90 * abs(math.sin(i * 0.7 + t * 6)) + 50 * abs(math.sin(i * 0.23 - t * 3))
        if sil[0] <= i < sil[1]:
            h = 6
        if loud[0] <= i < loud[1]:
            h = 300
        h *= p
        c = MNT if loud[0] <= i < loud[1] else mix(MNT, 0.75)
        d.rounded_rectangle((x0 + i * bw + 3, base - h, x0 + (i + 1) * bw - 3, base + h * 0.35), 6, fill=c)
    a = eo((t - 0.9) / 0.3)
    if a > 0:
        sx0, sx1 = x0 + sil[0] * bw, x0 + sil[1] * bw
        d.rounded_rectangle((sx0, base - 180, sx1, base + 70), 14, outline=mix(COR, a), width=4)
        d.text(((sx0 + sx1) / 2, base + 120), "silence  0:42", font=F(34, "b"), fill=mix(COR, a), anchor="mm")
    a = eo((t - 1.3) / 0.3)
    if a > 0:
        lx = x0 + (loud[0] + loud[1]) / 2 * bw
        d.text((lx, base + 120), "beat drop  1:07", font=F(34, "b"), fill=mix(MNT, a), anchor="mm")


def s_said(im, d, t):
    word_row(d, [("Knows", INK, 0), ("what's", INK, 0), ("said.", IND, 1)], t, 230, 84, stagger=0.15)
    lines = [("00:04", "“Meet the new dashboard.”"), ("00:11", "“Drag in any file.”"), ("00:19", "“Share it in one click.”")]
    for i, (ts, s) in enumerate(lines):
        p = eo((t - 0.35 - i * 0.3) / 0.4)
        if p <= 0:
            continue
        y = 360 + i * 150 + 40 * (1 - p)
        x = 360 - 60 * (1 - p)
        card(d, (x, y, x + 1200, y + 110), r=22)
        d.rounded_rectangle((x + 28, y + 30, x + 168, y + 80), 12, fill=mix(IND, 0.12, CARD))
        d.text((x + 98, y + 55), ts, font=F(32, "m"), fill=IND, anchor="mm")
        d.text((x + 200, y + 55), s, font=F(44, "md"), fill=INK, anchor="lm")


def s_answer(im, d, t):
    p = eo(t / 0.4)
    x0, y0 = 360, 230 + 40 * (1 - p)
    card(d, (x0, y0, x0 + 1200, y0 + 640), outline=mix(IND, 0.3 * p, CARD))
    d.ellipse((x0 + 50, y0 + 50, x0 + 86, y0 + 86), fill=IND)
    d.text((x0 + 106, y0 + 68), "Claude", font=F(38, "b"), fill=INK, anchor="lm")
    d.text((x0 + 1150, y0 + 68), "every claim, timestamped", font=F(28, "md"), fill=MUT, anchor="rm")
    items = [(MNT, "00:03", "Hook lands in 3 seconds"), (MNT, "00:11", "Product on screen early"),
             (COR, "00:24", "CTA too small to read"), (COR, "00:28", "No proof or numbers")]
    for i, (c, ts, s) in enumerate(items):
        q = eo((t - 0.4 - i * 0.35) / 0.35)
        if q <= 0:
            continue
        y = y0 + 170 + i * 110
        d.ellipse((x0 + 60, y + 12, x0 + 84, y + 36), fill=mix(c, q, CARD))
        d.text((x0 + 110, y + 24), f"[{ts}]", font=F(36, "m"), fill=mix(IND, q, CARD), anchor="lm")
        d.text((x0 + 290 + 30 * (1 - q), y + 24), s, font=F(46, "md"), fill=mix(INK, q, CARD), anchor="lm")


def s_tagline(im, d, t):
    word_row(d, [("Skim.", IND, 1), ("Zoom.", COR, 1), ("Answer.", INK, 1)], t, H / 2 + 45, 140, stagger=0.5, dur=0.4)


def s_logo(im, d, t):
    p = eo(t / 0.5)
    s = 150 * (0.85 + 0.15 * p)
    cx, cy = W / 2 - 400, H / 2 - 40
    d.rounded_rectangle((cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2), s * 0.26, fill=mix(IND, p))
    tr = s * 0.24
    d.polygon([(cx - tr * 0.7, cy - tr), (cx - tr * 0.7, cy + tr), (cx + tr, cy)], fill=mix(CARD, p, mix(IND, p)))
    d.ellipse((cx + s / 2 - 30, cy - s / 2 - 6, cx + s / 2 + 6, cy - s / 2 + 30), fill=mix(COR, p))  # rec dot
    d.text((cx + 120, cy + 4), "video-watch", font=F(130, "b"), fill=mix(INK, p), anchor="lm")
    a = eo((t - 0.6) / 0.4)
    d.text((W / 2, cy + 190), "/plugin install video-watch@video-watch", font=F(38, "m"), fill=mix(IND, a), anchor="mm")
    d.text((W / 2, cy + 260), "github.com/gowtham012/video-watch", font=F(32, "md"), fill=mix(MUT, a), anchor="mm")


SCENES = [(0.0, s_hook), (4.5, s_prompt), (7.5, s_progress), (11.0, s_frames), (16.5, s_sound),
          (19.5, s_said), (22.5, s_answer), (26.5, s_tagline), (29.0, s_logo)]
END = 33.0

# ------------------------------------------------------------- render
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", "-i", sys.argv[2], "-c:v", "libx264", "-crf", "18",
                       "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
                       "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
for fi in range(int(END * FPS)):
    T = fi / FPS
    st, fn = [s for s in SCENES if s[0] <= T][-1]
    im = bg.copy()
    d = ImageDraw.Draw(im)
    fn(im, d, T - st)
    d.text((60, 50), "video-watch", font=F(26, "md"), fill=mix(MUT, 0.35))  # faint corner mark
    ff.stdin.write(im.tobytes())
ff.stdin.close()
ff.wait()
print(OUT)
