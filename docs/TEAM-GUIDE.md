# Video Watch: team guide

**Make, voice and review videos by chatting with Claude. No coding, no Terminal.**

With the **Video Watch** extension, Claude can:

- 🎬 **Watch any video** (a YouTube link or a file on your Mac) and describe it scene by scene, critique it, or answer questions about it.
- 🎙 **Add a professional voiceover** in a voice you pick **by listening**, from your ElevenLabs voices or thousands in the public library.
- 🎵 **Add background music and sound effects** made for your video. The music automatically gets quieter whenever the voice speaks.
- ✅ **Ask the right questions first**: goal, audience, format, length, tone, voice, music and brand. Your video comes out the way you want, and no credits are wasted.

Setup takes **about 5 minutes**, once. Everything it needs is built in.

---

## Part 1: One-time setup

### 1. Get the Claude desktop app

Download it from **[claude.ai/download](https://claude.ai/download)** (Mac), install it and sign in with your work account.

### 2. Get your ElevenLabs API key

1. Create an account at **[elevenlabs.io](https://elevenlabs.io)**.
2. **Plan:** the free plan is fine for trying it out, but its audio is for **non-commercial use only** and needs attribution. Use a **paid plan** for any company, client or public video. Ask your manager which account to use.
3. In ElevenLabs, click **Developers** (bottom left), open **API Keys**, then **Create Key**.
   - Name it `video-watch`.
   - If it lets you limit access, allow only **Text to Speech**, **Speech to Text**, **Voices (read)**, **Sound Effects**, **Music** and **User (read)**.
   - If it offers a **credit limit**, set one. That keeps a mistake cheap.
   - **Copy the key.**

### 3. Install Video Watch

1. Download **[video-watch.mcpb](https://github.com/gowtham012/video-watch/releases/latest/download/video-watch.mcpb)** (about 60 MB).
2. **Double-click the file.** Claude opens and shows the **Video Watch** install window. Click **Install**.
   - If nothing happens: in Claude, open **Settings → Extensions** and drag the file onto that page.
3. In the settings form, paste your **ElevenLabs API key** (it's hidden as you type), then click **Save**.
4. Make sure the **Video Watch** switch is **on**.

> 🔒 Your key is stored securely by Claude on your Mac and is never shown in chats. **Never paste it into a chat.** If you do by accident, delete it on elevenlabs.io and make a new one.

### 4. Check it works

Start a **new chat** and type:

> **Check my Video Watch setup.**

Claude replies with your ElevenLabs plan and how many credits you have left. The first time, Claude asks permission to use Video Watch; click **Allow**. You're done.

> **"Extensions" missing in Settings, or turned off by your organization?** Your company's Claude admin controls this. Ask them to allow desktop extensions, or to approve Video Watch.

---

## Part 2: Using it

Just talk to Claude in a normal chat. The easiest start: click the **+** button in the message box, choose **Make or improve a video**, and Claude guides you through everything.

Or copy one of these, replacing the parts in `[brackets]`. Claude always tells you the credit cost and asks before it makes anything.

### 🎙 Voiceover and music for your own video

```
I have a video called [file name, or "the one I downloaded today"]. Watch it and
describe it scene by scene. Then ask me your brief questions, let me pick a voice
by listening, write a voiceover script for each scene, and make the voiceover plus
[upbeat / calm / cinematic] background music. Give me the finished video.
```

What happens:
1. Claude finds the video on your Mac and watches it.
2. **Brief:** Claude asks about the purpose, audience, length, tone, voice and music, a few questions at a time, each with a suggested answer you can just accept.
3. **A page opens in your browser with the voices.** Press **▶ Listen** (free), use the **All ElevenLabs voices** tab and filters to explore, then click **Use this voice**.
4. Claude writes the script. You approve it or ask for changes.
5. Claude makes everything and opens the finished video for you.
6. Ask for tweaks in plain words: *"slower voice"*, *"music quieter"*, *"move the second line to when the logo appears"*.

### 🎬 Understand or critique a video

```
Watch [YouTube link or file] and tell me what happens, scene by scene.
```
```
Watch [link] and critique it as a launch video: hook, pacing, call to action, and the top 3 fixes.
```
```
Watch [link] and summarize the talk: the main points and the best quotes, with timestamps.
```

### ✨ Make one like a video you love

```
Watch [link to a video you like]. I want something in the same style for [our product],
which [one sentence on what it does]. Ask me your brief questions, then give me a
script and a production brief.
```

### 🔊 Just sound effects, or just a voiceover file

```
Make a soft whoosh sound effect and a short UI click.
```
```
Let me pick a voice, then read this as an MP3: "[your text]"
```

---

## Part 3: Good to know

**Where your files go.** In **Movies → Video Watch**, one folder per project:
- `final.mp4`: the finished video.
- `audio/`: the voice lines, the music and the sound effects as separate MP3s.

Your original video is never changed. Ask *"open my project folder"* to see it.

**Costs.** ElevenLabs bills in credits:
- **Voiceover:** about **1 credit per character**, so a 30-second script is about 450 credits.
- **Music, sound effects and transcription** (for videos without captions) use credits too.
- **Listening to voices is free.**

Ask *"how many ElevenLabs credits do I have left?"* any time.

**A good script.**
- About **75 words per 30 seconds**.
- Short sentences.
- Write numbers the way they should be said ("twenty twenty-six").

**Music length.** Ask for music as long as your video. Shorter music loops, and every loop fades out and restarts.

**Changing the key.** Go to **Settings → Extensions → Video Watch → Configure**.

**Updating.** Download the newest `video-watch.mcpb` and double-click it.

---

## Troubleshooting

| What you see | What to do |
|---|---|
| "No ElevenLabs key yet" | Settings → Extensions → Video Watch → Configure. Paste the key and save. |
| "The ElevenLabs key was rejected" | Make a new key on elevenlabs.io and paste it in Configure. |
| "Your plan doesn't allow this feature" (music) | Music may need a paid plan. Ask for *"no music"* instead. |
| "Out of credits" | Check your ElevenLabs usage page, or ask your manager about the plan. |
| The voice page didn't open | Ask Claude for the picker link and open it in your browser. |
| "Couldn't download that link" | The video may be private or blocked. Download it yourself and tell Claude the file name. |
| Claude says it doesn't have Video Watch | Settings → Extensions: make sure Video Watch is **on**, then start a new chat. |
| Extensions are missing or turned off | Your org admin needs to allow desktop extensions. |

**Still stuck?** Contact [your internal contact], or open an issue at [github.com/gowtham012/video-watch/issues](https://github.com/gowtham012/video-watch/issues).

---

<sub>Mac only (Apple Silicon). Only process videos you have the right to use. ElevenLabs audio on the free plan is for non-commercial use with attribution. Use a paid plan for company work.</sub>
