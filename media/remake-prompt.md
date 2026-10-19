# video-watch launch ad: production prompt

The reference is the LangEase launch ad by Zelios (youtube.com/watch?v=SgmuplXU2iY, 33 s). It was analyzed with video-watch: 30 keyframes, 6 zoom windows at 4 fps, and a measured palette. This brief copies its **style and quality bar**, not its content: no LangEase or Zelios logos, footage, copy or music.

Paste everything below the line into Claude Code (or hand it to a motion designer).

---

Build a 33-second product launch ad for **video-watch**, a Claude Code plugin that lets Claude watch any video and answer questions about it with timestamps.

## A. Master brief

**Format.** 1920×1080, 60 fps, 33.0 s, H.264 MP4. Build it in **Remotion (React + TypeScript)**, one component per shot and one `<Composition>`. Every word and UI element must be real text or SVG, never a raster image of text, so it stays crisp at any size.

**Look.**
- Bright, airy, premium SaaS: a cool off-white canvas, frosted-glass UI cards with soft blue glows, and real product UI tilted in 3D.
- The camera never stops moving.
- Every scene **morphs** into the next. A shape from shot N becomes an element of shot N+1.
- Use motion blur on fast moves instead of hard cuts.
- Calm and confident, not loud.

**Palette.** One job per colour.

| Role | Hex | Use |
|---|---|---|
| Canvas | `#F5F5FB` | Background, every shot (reference measured `#F4F4FC`) |
| Ink | `#0A0A12` | Primary words and the logo wordmark |
| Secondary | `#8A8FA3` | Second-tone words ("and", "go") and small labels |
| Primary | `#4F46E5` | Accent words, the play mark, active outlines |
| Gradient | `#4F46E5 → #38BDF8` | Progress bar, the CTA button, swooshes, glows (reference: royal `#3C44F4` → sky `#74CCFC`) |
| Rec dot | `#FF5A4E` | The playhead and rec dot only. Small; it means "this moment" |
| Success | `#10B981` | The "Done" check only |
| Glass | `rgba(255,255,255,0.72)` + `backdrop-filter: blur(24px)` | Cards, with a 1.5 px border `rgba(79,70,229,0.18)` and a glow `0 24px 60px rgba(79,70,229,0.18)` |
| Confetti | primary, sky `#38BDF8`, rec dot, and pink `#F472B6` | The "Done" moment |

**Type.**
- **Inter** for words: Regular 400 for most of them, Medium 500 for the accent word. Never bold for kinetic words; the light weight is the premium feel.
- **JetBrains Mono** 500 for commands and timestamps.
- Headline words are about 6% of frame height (≈64 px) and centred. Secondary labels are about 1.6% (≈18 px).
- Two-tone phrases: the accent word goes in Primary and the rest in Ink, or in Secondary for filler words.

**Motion rules.**
- **Word entry:** opacity 0→1, blur 14 px→0, translateY 22 px→0, scale 0.96→1. 420 ms, ease `cubic-bezier(0.22, 1, 0.36, 1)`. Words in a phrase stagger by 160 ms.
- **Phrase reflow:** when a word is added, the whole phrase re-centres with a Remotion `spring({damping: 200})`. Words never pop into a fixed slot.
- **Word exit:** opacity→0 and blur→10 px, 220 ms, ease-in.
- **Camera moves:** `cubic-bezier(0.65, 0, 0.35, 1)`, using CSS `perspective: 1600px` with rotateX/rotateY/translateZ on a scene wrapper.
- **Motion blur:** wrap every fast move (whips, fly-throughs, morphs) in `@remotion/motion-blur` `<CameraMotionBlur shutterAngle={180} samples={8}>`.
- **Cursor:** a hand-pointer SVG in navy with a white outline. Clicks get a 120 ms press (scale 0.9) and a soft ring ripple.
- **Rhythm:** 120 bpm (beat = 0.5 s). Every shot change and every word lands on a beat or a half-beat.

## B. Shot list

The demo input is **your own** screen recording, a 10-minute product walkthrough. Run `vw.py prepare` on it and use the **real** outputs: `frames/*.jpg`, `sheet_*.jpg` and `manifest.md`. Don't use third-party footage.

**1. Hook (0.0–4.4 s).** Kinetic type on the canvas.
- Phrase builds word by word: **"Turn"** (Primary) **"videos"** (Ink) → swap → **"into"** (Ink) **"answers"** (Primary).
- At 3.0 s the last phrase is **"Any link"** (Ink), then a frosted-glass **link chip** (a YouTube-style red play glyph and `youtu.be/…`) pops in at scale 0.8→1 with a spring, then **"Instantly"** (Primary).
- The phrase reflows as each piece arrives.
- Sound: soft intro; the drum enters at 0.0.

**2. Paste (4.4–6.2 s).**
- A hand cursor grabs the link chip and drags it down into a tilted (rotateX 18°) frosted **Claude Code prompt box**.
- On drop, the box flashes a Primary outline and the text `/watch youtu.be/… what makes this work?` types in at 40 chars/s in mono.
- The camera pushes in 8%. Caption: **"Just"** (Ink) **"paste"** (Primary).

**3. Fly-through (6.2–10.0 s).** The signature shot, matching the reference's phone tunnel.
- Four large floating panels form a corridor (top, bottom, left and right walls, each rotated ±60°): the **real contact sheet**, the **real manifest timeline**, a **waveform** strip and a **transcript** card.
- The camera flies forward through it with motion blur.
- Centre text builds on beats: **"Frames."** → **"Frames. Speech."** → **"Frames. Speech. Sound."** in Primary, then swaps to **"All in one timeline"** (Ink, with "timeline" in Primary).
- At 9.6 s the camera whips right, and a Primary→sky **gradient swoosh** streaks across. That is the morph into shot 4.

**4. Watching (10.0–13.5 s).**
- The swoosh settles into a horizontal pill **progress bar** (gradient fill).
- A counter above the right end ticks **0 → 100** (Primary number, Secondary "/100"). Label: **"Watching"**. Small mono proof under the bar: `10-min video · 60 keyframes · 9 s`.
- At 100 the bar shrinks and rounds into a glass circle. That is the morph into shot 5.
- Sound: a riser from 12.0 s.

**5. Done (13.5–14.8 s).**
- The circle fills with a Success check that draws over 350 ms, with **"Done"** above it (Inter 400, Primary).
- Confetti bursts from the circle in the confetti palette, with gravity and spin, and fades by 14.8 s.
- Sound: a hit at 13.5 s.

**6. Every moment (14.8–19.0 s).**
- A row of glass **keyframe cards** slides in from the right with a 120 ms stagger. These are real frames, each with a mono timestamp (`00:12`, `01:34`, `03:05`, `07:40`) and a kind tag (`cut`, `change`).
- The camera tilts back to reveal the full **manifest view**: a 3D-tilted panel listing frames, `SAY` lines and `SILENCE` events.
- The hand cursor clicks the `01:34` card; it lifts with a Primary glow.

**7. Zoom in (19.0–21.0 s).**
- The clicked card **fans out into 6 copies**, rotated at different angles in 3D, like the reference's "Multiple Languages" shot. These are the dense zoom frames, `01:32 → 01:36`.
- Centre text: **"Re-watch"** (Ink) **"any moment"** (Primary).
- At 20.4 s, motion-blur whip to shot 8.

**8. The answer (21.0–24.0 s).**
- A tilted glass **Claude response panel**. Lines type in staggered by 300 ms, each with a mono Primary timestamp:
  - `[00:03]` Hook lands in 3 seconds
  - `[01:34]` Checkout button never responds
  - `[07:40]` CTA appears too late
- Below it, a row of option chips: `Critique` · `Summarize` · **`Remake it with my content`**.
- The hand cursor clicks the last chip; it turns from Ink to the gradient. This shows the new remake feature.

**9. Install button (24.0–25.0 s).**
- Camera push to a single button **"Install in Claude Code"**.
- It starts Ink with white text. The cursor clicks it and it **morphs to the gradient** with a glow, as the reference's CTA button does.

**10. Rec dot to tagline (25.0–28.5 s).**
- The button collapses into the **Rec-dot** circle with a glow. It shoots across the frame leaving a light trail, like the reference's star streak, and "writes" the tagline as it passes.
- Tagline: **"Skim."** (Primary) → **"Zoom."** (Primary 70%) → **"Answer."** (Ink), one per beat. The dot comes to rest after "Answer."

**11. Logo and CTA (28.5–33.0 s).**
- The rec dot snaps onto the corner of a Primary rounded-square **play mark**. The mark scales in 0.9→1 and **"video-watch"** (Inter 500, Ink, ≈7% of frame height) slides out from behind it.
- At 29.6 s, `github.com/gowtham012/video-watch` types in letter by letter (mono, Secondary) under the logo.
- At 30.4 s, a pill appears holding `/plugin install video-watch@video-watch` (mono, Primary).
- Hold until 33.0 s. The CTA must be readable for at least 2.5 s; this fixes the reference's tiny end URL.
- The music rings out; the last 1.0 s is quiet.

## C. Build target

- **Remotion** for all shots. Every shot here is motion graphics with real text and UI, which code renders crisply with exact timing.
- Folder layout: `src/shots/S01Hook.tsx` … `S11Logo.tsx`, `src/theme.ts` (the palette, fonts and easing above) and `src/assets/` (your real vw.py outputs and screenshots).
- Render: `npx remotion render Ad out/video-watch-launch.mp4 --codec h264 --crf 16`. Also export a 9:16 version (1080×1920): re-lay out each shot, don't just crop.
- Text-to-video models (Veo, Sora, Runway, Kling) are **not** used here, because they garble UI text and logos. If you add a lifestyle shot later (a person watching a laptop), prompt one separately and add "no text, no logos, no UI on screen".

## D. Music brief

- Upbeat, polished electro-pop at **120 bpm**, bright synths and a clean kick. Instrumental, or with a light vocal hook.
- Energy rises from the intro (0–4.4 s), builds through the fly-through, and peaks at "Done" (13.5 s). It eases slightly under the answer panel and lifts again for the tagline.
- Hits at 4.4, 10.0, 13.5, 24.0, 25.0 and 28.5 s.
- It must be **licensed** (Artlist, Epidemic, Musicbed) or original. Don't use the reference's track.

## E. Quality bar (check before export)

- [ ] Every word is legible on a phone, with nothing under 18 px at 1080p and every headline on screen for at least 1.2 s.
- [ ] The product (the prompt box) is on screen by 4.4 s, and real vw.py output by 6.2 s.
- [ ] Every shot change is a morph or a motion-blurred move. No unmotivated hard cut.
- [ ] Every cut and word entry sits on a beat (±1 frame at 60 fps).
- [ ] The palette is used by role, coral appears only as the rec dot and playhead, and there are no off-palette colours.
- [ ] One proof point is visible (`10-min video · 60 keyframes · 9 s`).
- [ ] The install CTA is held for at least 2.5 s at the end, and the URL is readable.
- [ ] No reference assets (logos, footage, copy, music) appear anywhere.
