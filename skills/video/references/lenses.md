# Viewing lenses

Pick the lens that matches the user's goal. More than one can apply.

## Launch / marketing video critique

Watch it as the target viewer scrolling a feed, then again as a creative director.

- **Hook (0–3 s, 0–10 s):** what is the first frame and the first spoken or written line? Is there a bold claim, a tension or a question? Would a viewer stop scrolling?
- **Time to product:** the first timestamp where the real product or interface is on screen. Under 10 s is strong. Frames showing only logos or abstract motion don't count.
- **One message:** list every distinct claim with its timestamp. More than one main idea means the message is diluted.
- **Show vs tell:** the share of runtime showing real UI or real use, versus motion graphics or talking. Use frame kinds and the timeline to estimate it.
- **Pacing:** cuts per minute and where the cuts bunch up (from the manifest). Does energy rise into the reveal? Is there dead air (silence) or a beat drop (loud moment) lined up with the key visual?
- **Audio and visual sync:** do music hits (loud moments, no-speech stretches) land on cuts and reveals?
- **Legibility:** zoom on on-screen text. Could it be read at phone size in the time it's shown? Rough guide: 3+ words per second of screen time is too fast.
- **Proof and credibility:** real numbers, customers or footage, versus claims.
- **CTA:** the exact ask, when it appears, and whether there's a link or action.
- **Output:** a scorecard (hook, time to product, clarity, pacing, CTA), the three biggest fixes with timestamps, and a rewritten first 10 seconds.

## Tutorials and talks

- Extract the **structure**: chapters (from metadata, or inferred from slide changes) with timestamps.
- Capture **on-screen artifacts verbatim**: code, commands, slide bullets, diagrams. Zoom or `frame --width 1920` so text is legible, and transcribe exactly. Flag anything partially unreadable.
- Separate **what the speaker says** from **what is on the slide**. Note where they differ: the speaker adds context, or the slide is outdated.
- For how-tos: produce **numbered, reproducible steps** with the timestamp of each step, including commands, settings and values.
- For talks: the thesis, the 3–5 key arguments, the evidence for each, memorable quotes (exact, from the transcript, with timestamps) and open questions.

## Screen recordings and bug repros

- Use `--sensitivity 3` (small UI changes matter) and consider `--max-frames 80`.
- Reconstruct the **action log**: `[mm:ss] user did X → UI showed Y`. The cursor position, focused field, toasts, spinners, URL bar and console are evidence. Zoom on them.
- Find the **first divergence**: the earliest moment the UI differs from what should happen. Zoom into that window with `--fps 8–10`. Bugs live between keyframes.
- Read error messages, status codes and stack traces **verbatim** with `frame --crop`.
- Note environment clues: OS, browser, app version, viewport, logged-in user, timestamps on screen.
- **Output:** steps to reproduce, expected vs actual, the exact moment (timestamp) and the visual evidence (frame file), and likely causes ranked. Never claim a root cause that isn't visible.

## General Q&A on any video

- Answer the question first, with timestamps.
- If the question targets a moment ("what does she hold up at the end?"), zoom there before answering, even if a keyframe seems to show it.
- For "summarize": the gist line, then a 5–15 beat timeline, then key takeaways.
- For counting or tracking questions ("how many times…", "when does X first appear"), keyframes are not enough. Zoom across the relevant windows at 2–4 fps and say what sampling you used.
- For people: describe what is visible (clothing, actions, on-screen name captions). Don't identify real people from their faces. Use names only when given in captions, the title or speech.

## Remake: same style, the user's content

The goal is a production prompt that rebuilds the reference's *quality and feel* around the user's own product. Copy the style, never the content: no reference logos, footage, copy, characters or music.

**1. Get the user's content first** (one `AskUserQuestion` round, or ask in chat). Ask for:
- Product name, a one-line promise, and the 3–5 things to show.
- Real assets: screenshots, a screen recording, logo, brand colours (or "pick for me").
- Length, aspect ratio (16:9, 9:16, 1:1), platform, and the call to action.

Anything not given gets a sensible default, stated in the prompt.

**2. Pull the reference's style DNA from the evidence, not from memory.**
- **Structure:** zoom across every scene boundary (`--fps 4–8`) to get each shot's exact in/out time and what animates inside it.
- **Rhythm:** estimate the BPM from cut spacing and `loud` moments (cuts at 0.5 s multiples suggest 120 bpm). Note which beats the cuts land on.
- **Colour:** run `VW colors`. The dominant colours give the background and surfaces; the accents give the brand colours. Give each hex a *role* (background, text, primary, highlight, success).
- **Type:** weight, case, and size as a share of frame height (e.g. "headline ≈ 9% of frame height, semibold"). Note whether words animate one at a time, how far they rise, and whether they blur in.
- **Motion:** entry types (rise and fade, scale-pop, blur-in, 3D tilt, push-in), the feel of the easing (snappy ease-out vs. gentle ease-in-out), durations (e.g. 300–400 ms), stagger between items, and camera moves, motion blur and depth (shadows, glows, glass cards).
- **Story arc:** hook → problem/promise → product moment → proof → payoff → logo/CTA, each with its time range.
- **Sound:** music energy and where the hits land (from audio cues: measured, not heard).

**3. Map the user's content beat for beat** onto the same structure and timings. Keep the pacing, swap the words and screens. Where the reference has a weakness (late product, tiny CTA, no proof), fix it and say so.

**4. Output the production prompt.** Make it a single copy-paste block, written so another agent or tool can build it without seeing the reference:
- **A. Master brief:** format (resolution, fps, length), the overall look in 2–3 sentences, the palette table (hex → role), the type spec, the motion rules (easing as a cubic-bezier, standard durations, stagger), and the transition rule (e.g. hard cuts on the beat).
- **B. Shot list:** for every shot, the time range, what's on screen (exact copy, with which words get the accent colour), layout, the animation in and out, the camera, and the sound cue.
- **C. Build target.** For motion graphics with UI or text (most product ads), target code: "Build in Remotion (React) at 1920×1080, 60 fps" with components per shot, so text stays crisp and the timing is exact. Text-to-video models (Veo, Sora, Runway, Kling) garble UI text and logos, so give those per-shot prompts only for text-free footage (people, products, environments), and add "no text, no logos" to each.
- **D. Music brief:** BPM, genre and energy curve, and where the hits sit. Say it must be licensed or original.
- **E. Quality bar:** a checklist the builder must pass, such as text legible at phone size, the product visible within 3–5 s, every cut on a beat, no stretched assets, and a CTA held at least 2 s.

Offer next steps after the prompt: build it now in Claude Code (Remotion), or adjust the brief.
