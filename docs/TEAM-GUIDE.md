# video-watch: team guide

**Make, voice and review videos by chatting with Claude. No coding.**

With the video-watch plugin, Claude can:

- 🎬 **Watch any video** (a YouTube link or a file on your Mac) and summarize, critique or answer questions about it.
- 🎙 **Add a professional voiceover** to your video in a voice you pick, with background music that automatically gets quieter when the voice speaks.
- 🔊 **Add sound effects:** AI-made ones from ElevenLabs, or free ones from Openverse with credits.
- ✨ **Remake a video you like** with your own product, as a full production brief.

Setup takes about 15 minutes, once.

---

## Part 1: One-time setup

### 1. Get the Claude desktop app

Download it from **[claude.ai/download](https://claude.ai/download)**, install it and sign in with your work account.

You'll use the **Code** tab at the top of the app. It's still just a chat window, but it can work with files on your Mac, which video needs.

> **Why not Cowork or regular chat?** The voice picker and the private key window have to open on *your* screen. The Code tab runs on your Mac, so they do. Cowork runs in a sandbox and can't show them.

### 2. Make a folder for your videos

In Finder, create a folder such as **Documents → Videos**. In the Claude app, open the **Code** tab, start a new session, and choose that folder. Everything Claude makes will be saved there.

### 3. Install the plugin

Use either way; both do the same thing.

**Option A (menus):** In the Claude app, go to **Customize → Plugins → Add → Add marketplace from GitHub** and enter:

```
gowtham012/video-watch
```

Then install **video-watch** from the list. Menu labels can differ slightly between app versions.

**Option B (type it):** In a Code tab session, type these two lines one at a time:

```
/plugin marketplace add gowtham012/video-watch
```
```
/plugin install video-watch@video-watch
```

Then start a new session so the plugin loads.

### 4. Let Claude install the video tools

In the Code tab, type:

> **Check that my Mac has everything video-watch needs (ffmpeg and yt-dlp) and help me install anything missing.**

Claude checks and asks before installing anything. If your Mac doesn't have Homebrew yet, Claude shows you one command to paste into the Terminal app. It asks for your Mac password, which you type yourself.

### 5. Set up ElevenLabs (for voices and music)

1. Create an account at **[elevenlabs.io](https://elevenlabs.io)**.
2. **Pick a plan.**
   - **Free plan:** good for trying it out. Audio is for **non-commercial use only** and needs attribution. Background music may not be included.
   - **Paid plan (Starter or higher):** needed for any company, client or public video, and for music. Ask your manager which account to use.
3. **Create an API key:** in ElevenLabs, click **Developers** (bottom left), open **API Keys**, then **Create Key**.
   - Name it `video-watch`.
   - If it lets you limit access, allow only **Text to Speech**, **Voices (read)**, **Sound Effects**, **Music** and **User (read)**.
   - If it offers a **credit limit**, set one, for example a monthly cap. That keeps a mistake cheap.
   - Copy the key.
4. In the Claude Code tab, type:

   > **Set up ElevenLabs for video-watch.**

   A small private window appears. **Paste your key there**, not in the chat, and click **Save**. Claude checks the key and tells you your plan and how many credits you have left. The key is stored in your Mac's Keychain, so you only do this once.

> 🔒 **Never paste your API key into the chat.** If you do by accident, delete that key on elevenlabs.io and make a new one.

That's it. You're set up.

---

## Part 2: Using it: copy-paste prompts

Type these into a **Code tab session** in your videos folder. Replace the parts in `[brackets]`. Claude asks before it spends ElevenLabs credits or downloads anything.

### 🎙 Add a voiceover and music to your video

The most common one. Put your video file in your videos folder first.

```
/video voice

I have a video at [my-video.mp4]. Please:
1. Watch it and tell me what happens, scene by scene.
2. Open the voice picker so I can choose a voice.
3. Write a short voiceover script that matches each scene, and show it to me before making it.
4. Make the voiceover, plus [upbeat modern / calm / cinematic] instrumental background music.
5. Mix it all into a new video. Keep my original file unchanged.
Tell me how many credits each step will use before you run it.
```

What happens:
1. Claude watches your video and describes the scenes.
2. **A page opens in your browser with all the voices.** Press **▶ Listen** to hear them (free), then click **Use this voice**.
3. Claude writes the script. You approve it or ask for changes.
4. Claude makes the voice, the music and any sound effects, then gives you `final.mp4`.
5. Ask for tweaks in plain words: *"slower voice"*, *"music quieter"*, *"move the second line to the logo"*.

### 🎬 Understand or critique a video

```
/video watch [YouTube link or file] — what happens in this video?
```
```
/video watch [link] — critique this as a launch video: hook, pacing, call to action, top 3 fixes.
```
```
/video watch [link] — summarize this talk: the main points and the best quotes, with timestamps.
```

### ✨ Make a video like one you love

```
/video watch [link to a video you like]

Remake it with my content. My product is [name], it [one sentence on what it does],
and I want to show [3–5 things]. Keep the same style and quality, but use our brand
colours [hex codes, or "pick for me"]. Give me the full production brief.
```

Claude studies the video's style (shot timings, motion, fonts, exact colours) and writes a complete brief for your version. It never copies the original's logos, footage or music. Turning that brief into a finished animated video takes extra time and tools, so ask Claude: *"Can you build this video for me?"*

### 🔊 Add sound effects

AI-made, with ElevenLabs credits:

```
/video voice [my-video.mp4] — add a soft whoosh on each big transition and a click when the button is pressed.
```

Free, from Openverse (with credits for the creators):

```
/video sound [my-video.mp4] — find free sound effects for the main moments and line them up.
```

### 🗣 Just a voiceover file (no video)

```
/video voice — open the voice picker, then read this script as an MP3: "[your text]"
```

---

## Part 3: Good to know

**Costs.** ElevenLabs bills in credits. A voiceover uses about **1 credit per character** of script, so a 30-second script of about 450 characters is about 450 credits. Music and sound effects use credits too. Previewing voices in the picker is **free**. Ask Claude *"How many ElevenLabs credits do I have left?"* any time.

**Writing a good script.**
- About **75 words per 30 seconds** of video.
- Short sentences sound best.
- Write numbers the way they should be said ("twenty twenty-six", not "2026").

**Where your files go.** Everything is saved in the folder you chose, in a subfolder per video (for example `video-launch/`):
- `final.mp4`: the finished video.
- `audio/`: the voice lines, the music and the sound effects as separate MP3s.

Your original video is never changed.

**Changing your voice later.** Say *"open the voice picker again"*.

**Removing your key.** Say *"remove my ElevenLabs key from video-watch"*, or delete the key on elevenlabs.io.

**Updating the plugin.** Say *"update the video-watch plugin"*, or in Customize → Plugins, click update.

---

## Troubleshooting

| What you see | What to do |
|---|---|
| "No ElevenLabs key yet" | Say *"Set up ElevenLabs for video-watch"* and paste the key in the private window. |
| "The API key was rejected" | The key was deleted or mistyped. Make a new one on elevenlabs.io and run setup again. |
| "Your plan doesn't allow this feature" when making music | Music may need a paid ElevenLabs plan. Ask for *"no music"* or *"free music from Openverse"* instead. |
| "Out of credits" | Check your ElevenLabs usage page, or ask your manager about the plan. |
| The voice picker page didn't open | Ask Claude for the link it printed, and open it in your browser. |
| "ffmpeg is missing" | Say *"install ffmpeg for me"*. Claude asks first. |
| A YouTube video won't download | Try again, or download the video yourself and give Claude the file. |
| The picker, key window or Keychain doesn't work | Make sure you're in the **Code** tab, not Cowork or regular chat. |

**Still stuck?** Contact [your internal contact] or open an issue at [github.com/gowtham012/video-watch/issues](https://github.com/gowtham012/video-watch/issues).

---

<sub>Only process videos you have the right to use. ElevenLabs audio on the free plan is for non-commercial use with attribution. Use a paid plan for company work.</sub>
