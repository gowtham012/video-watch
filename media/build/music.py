"""120 bpm synth bed for launch ad v1: python music.py <out.wav>"""
import math, random, struct, sys, wave

SR, DUR, BEAT = 44100, 33.0, 0.5
rng = random.Random(3)
# chord roots per 2 bars (4 s): A min, F, C, G  -> uplifting pop loop
CH = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (261.63, 329.63, 392.0), (196.0, 246.94, 293.66)]
out = []
for n in range(int(SR * DUR)):
    t = n / SR
    b = t % BEAT
    end = 1.0 if t < 30.5 else max(0.0, 1 - (t - 30.5) / 1.5)  # fade over the logo; silent tail
    intro = min(1.0, t / 1.5)
    s = 0.0
    if t < 30.5:
        s += 0.55 * math.sin(2 * math.pi * (45 * b + 90 * (1 - math.exp(-b * 30)) / 30)) * math.exp(-b * 9)  # kick
        hb = (t - BEAT / 2) % BEAT
        if t > 2.0:
            s += 0.06 * (rng.random() * 2 - 1) * math.exp(-hb * 70)  # offbeat hat
        if t > 4.5 and int(t / BEAT) % 4 == 1:  # clap on 2 of each bar
            s += 0.10 * (rng.random() * 2 - 1) * math.exp(-b * 25)
    chord = CH[int(t / 4) % 4]
    pad = sum(math.sin(2 * math.pi * f * t) + 0.3 * math.sin(2 * math.pi * f * 2.003 * t) for f in chord)
    s += 0.045 * pad * intro
    s += 0.12 * math.sin(2 * math.pi * chord[0] / 2 * t) * (0.6 + 0.4 * math.exp(-b * 6)) * intro  # bass pulse
    if 8.0 <= t < 9.5:  # riser into "Done"
        k = (t - 8.0) / 1.5
        s += 0.12 * k * k * (rng.random() * 2 - 1) + 0.05 * k * math.sin(2 * math.pi * (400 + 1200 * k) * t)
    if 9.5 <= t < 10.5:  # sparkle on "Done"
        u = t - 9.5
        s += 0.10 * math.exp(-u * 5) * (math.sin(2 * math.pi * 1318.5 * t) + math.sin(2 * math.pi * 1760 * t))
    out.append(max(-1.0, min(1.0, s * end * 0.9)))
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(b"".join(struct.pack("<h", int(v * 32000)) for v in out))
print(sys.argv[1])
