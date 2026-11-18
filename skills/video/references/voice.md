# /video voice: ElevenLabs voiceover, music and sound effects

Give any video a professional voiceover in a voice the user picks, an instrumental music bed that ducks under the voice, and sound effects, all made with the user's own ElevenLabs account. The person is usually not a developer: keep every step in plain words, ask one thing at a time, and never show them a command unless they ask.

`EL` = `python3 <this skill's base directory>/scripts/eleven.py`. Work in a job folder such as `./video-<short-slug>`; everything for this video lands in it.

## Ground rules

- **The API key never goes in the chat.** If the user pastes a key into the chat anyway, don't repeat it back or use it in a command. Tell them to run setup instead (it opens a private dialog) and to regenerate the key on elevenlabs.io, since chat text is stored.
- **Spending credits needs a yes.** Voiceover, music and sound effects use the user's ElevenLabs credits. Before each generation, say what you'll make and roughly what it uses (voiceover: about 1 credit per character of script; check what's left with `EL credits`). Ask, then run.
- **Previews are free.** Listening to voices in the picker costs nothing.
- **Music may need a paid ElevenLabs plan.** If `music` fails with 402/403, offer free alternatives: no music, or `/video sound` with an Openverse track.
- **Licensing:** on ElevenLabs' free plan, audio is non-commercial and needs attribution. For company or client videos, the user needs a paid plan. Mention this once when they start.
- **Runs on the user's Mac.** The key dialog, Keychain and voice picker need the Code tab of the Claude desktop app (or Claude Code in a terminal). In a Cowork sandbox they can't reach the user's screen: say so and suggest the Code tab.

## 1. One-time setup (first use only)

Run `EL setup --check`.
- `"key": "ok"` → say which plan they're on and how many characters are left, then continue.
- `"key": "missing"` (exit 2) → explain: "I'll open a small private window. Paste your ElevenLabs API key there. Find it at elevenlabs.io → Developers → API Keys → Create key." Then run `EL setup`. It validates the key and saves it to their Mac's Keychain.
- Not on a Mac (no dialog) → they set `ELEVENLABS_API_KEY` in their environment. Guide them; don't take the key in chat.

`EL setup --forget` removes the key.

## 2. Choose a voice

Run `EL voices --dir <job> --pick`. A page opens in their browser with every voice on their account: search, filter by gender, accent and style, ▶ Listen to free previews, and a **Use this voice** button. Tell the user what to expect first ("A page will open in your browser. Listen to a few, then click Use this voice"). The command waits (up to 15 minutes) and returns the chosen voice, saved as `<job>/voice.json`. Confirm it back in words: "You picked George: male, British, warm narration."

To change the voice later, run the picker again.

## 3. Write the script with them

Ask what the video should say, or draft it from what they've told you (and from the video itself if they brought one: run `watch` first). Keep it speakable:
- Short sentences. About 2.5 words per second of video: a 30-second video holds about 75 words.
- Split it into lines, one per scene or moment. Each line becomes its own audio clip, so it can be placed exactly.
- Spell out what a voice should say: "twenty twenty-six", "A I", not symbols.

Show the script, get their OK, then write `<job>/lines.json`:

```json
[{"id": "s1", "text": "Meet the dashboard your team actually wants to open."},
 {"id": "s2", "text": "Drop in any file and it is ready in seconds."}]
```

## 4. Generate

After a yes on the credit estimate:

```
EL speak --dir <job> --script <job>/lines.json        # one mp3 per line + word timings in audio/voiceover.json
EL music --dir <job> --prompt "<style>" --seconds <video length + 2>
EL sfx   --dir <job> --text "soft whoosh" --name whoosh --seconds 1
```

- **Voice tone:** `--speed 0.9` to `1.1`; `--stability` lower (0.3) for more expressive, higher (0.7) for steadier.
- **Music prompt:** genre, mood, tempo and instruments, always instrumental. "Bright modern corporate electro-pop, 120 bpm, light synths, clean kick, uplifting." Match the video's energy; for a calm explainer, "soft ambient piano, warm pads, 90 bpm".
- **Sound effects:** a few, on the moments that carry the story (a whoosh on a big transition, a soft click on a button). Not on every cut.

Each run prints the file and its length in seconds. Line lengths decide timing.

## 5a. Their own video: mix it in

```
EL mix --dir <job> --video <their video> --out <job>/final.mp4 \
  [--voice-at s1@0.5 s2@6.0] [--sfx-at <job>/audio/sfx/whoosh.mp3@4.0] [--keep-original 0.3]
```

- Voice lines play back to back from 0.5 s unless `--voice-at` pins a line to a moment. Use `watch` (keyframes and cuts) to pick moments: a line starts just after the scene it describes appears.
- Music loops to the video's length, fades out over the last 2 s, and ducks automatically under the voice.
- `--keep-original 0.3` keeps the video's own sound quietly underneath (default: replaced).
- The original video file is never changed.

Then `watch` the result yourself (`VW prepare <job>/final.mp4 ...`) and check that each line lands on its moment before telling the user it's done. Offer adjustments in plain words: "voice a bit faster?", "music quieter?" (`--music-level`, default 0.35).

## 5b. A new video from scratch

Use the voiceover's line lengths as the scene lengths, so each scene lasts exactly as long as its line (plus about 0.4 s of air). Build the video (see the Remake lens in `references/lenses.md` for style), then mix as in 5a, or place each line at its scene's start inside the video project.
