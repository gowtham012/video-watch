#!/usr/bin/env node
// Video Watch - Claude Desktop Extension (MCP server over stdio).
// Everything a non-developer needs to plan, voice, score and review a video, with nothing to install.
import { execFile } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import * as el from "./eleven.js";
import * as vid from "./video.js";

const VERSION = "0.6.0";
const OUTPUT = (process.env.VW_OUTPUT_DIR && !process.env.VW_OUTPUT_DIR.startsWith("${"))
  ? process.env.VW_OUTPUT_DIR : join(homedir(), "Movies", "Video Watch");

const slug = (s) => String(s || "my-video").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 48) || "my-video";
const projectDir = (p) => { const d = join(OUTPUT, slug(p)); mkdirSync(d, { recursive: true }); return d; };
const text = (t) => ({ type: "text", text: t });
const image = (file) => ({ type: "image", data: readFileSync(file).toString("base64"), mimeType: "image/jpeg" });
const ok = (...content) => ({ content });
const fail = (e) => ({ isError: true, content: [text(e instanceof el.UserError ? e.message : `Something went wrong: ${e.message}`)] });

// ---- long jobs: answer within ~45 s; if still running, hand back a job id for check_progress
const jobs = new Map();
let jobSeq = 0;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function runJob(label, fn) {
  const id = `job-${++jobSeq}`;
  const job = { label, done: null };
  job.promise = fn().then((r) => (job.done = { r }), (e) => (job.done = { e }));
  jobs.set(id, job);
  await Promise.race([job.promise, sleep(45000)]);
  return settle(id);
}
function settle(id) {
  const job = jobs.get(id);
  if (!job) return fail(new el.UserError(`No job called ${id}.`));
  if (!job.done) return ok(text(`Still working on ${job.label}. This can take a few minutes. Call check_progress with job_id "${id}" to keep waiting. Tell the user it's in progress.`));
  jobs.delete(id);
  return job.done.e ? fail(job.done.e) : job.done.r;
}

// ---- the quality brief: everything that decides how a video turns out
const BRIEF = [
  { group: "1. Purpose", questions: [
    { id: "goal", q: "What is this video for?", options: ["Product launch / ad", "Explainer or how-to", "Social media post", "Internal update", "Event or promo", "Customer story"], default: "Explainer or how-to" },
    { id: "audience", q: "Who will watch it?", options: ["Customers", "Prospects / leads", "Our team", "Investors / partners", "General social audience"], default: "Customers" },
    { id: "message", q: "In one sentence, what should viewers remember?", free_text: true },
    { id: "cta", q: "What should they do after watching? (e.g. visit a link, book a demo)", free_text: true, default: "None" } ] },
  { group: "2. Format", questions: [
    { id: "platform", q: "Where will it be posted?", options: ["YouTube / website (16:9)", "Instagram / TikTok / Shorts (9:16)", "LinkedIn (1:1 or 16:9)", "Presentation / internal (16:9)"], default: "YouTube / website (16:9)" },
    { id: "length", q: "How long?", options: ["15 s", "30 s", "60 s", "90 s", "2-3 min"], default: "30 s" },
    { id: "source", q: "What are we starting from?", options: ["My own video / screen recording", "A video I like (remake its style)", "Just screenshots, logo and text"], default: "My own video / screen recording" } ] },
  { group: "3. Feel", questions: [
    { id: "tone", q: "What tone?", options: ["Confident & premium", "Friendly & warm", "Energetic & bold", "Calm & trustworthy", "Playful"], default: "Friendly & warm" },
    { id: "voice", q: "What kind of voice?", options: ["Let me pick by listening (opens the voice picker)", "Female", "Male", "No voiceover"], default: "Let me pick by listening (opens the voice picker)" },
    { id: "language", q: "Which language and accent?", options: ["English (American)", "English (British)", "English (Indian)", "Other - I'll say"], default: "English (American)" },
    { id: "music", q: "Background music?", options: ["Upbeat modern", "Calm & ambient", "Cinematic & inspiring", "Corporate & clean", "No music"], default: "Upbeat modern" },
    { id: "sfx", q: "Sound effects?", options: ["Subtle (a few whooshes/clicks)", "None", "Punchy (on every key moment)"], default: "Subtle (a few whooshes/clicks)" } ] },
  { group: "4. Brand & details", questions: [
    { id: "brand", q: "Brand colours, logo file, or words we must say / avoid? Any names that need a specific pronunciation?", free_text: true, default: "None" } ] },
];

const INSTRUCTIONS = `Video Watch helps people who are NOT developers make, voice and review videos by chatting. Be warm, plain-spoken and brief. Never show code or file internals unless asked.

Flow for "make / improve a video":
1. Call video_brief_questions and ask the brief a group at a time (3-4 questions per message), offering the suggested option. Skip anything the user already told you. Then video_save_brief.
2. If they have a video: list_my_videos helps find it; watch_video it, look at the contact sheets, and describe it scene by scene.
3. Voice: open_voice_picker, tell them a page opened in their browser to listen and click "Use this voice", then get_chosen_voice (call again if not chosen yet).
4. Write the script with them, about 2.5 words per second of video, one line per scene. Show it and get a yes.
5. Before spending ElevenLabs credits, say what you'll make (voiceover ~1 credit per character; music; sound effects) and ask. Then make_voiceover, make_music, make_sound_effect.
6. mix_video, then watch_video the result yourself to check timing before calling it done. open_result to play it.
Rules: never ask for or repeat an API key in chat (it goes in Claude > Settings > Extensions > Video Watch). Cite timestamps. Audio cues are measured, not heard. Only process videos the user has the right to use. Free ElevenLabs plans are non-commercial with attribution.`;

const server = new McpServer({ name: "video-watch", version: VERSION }, { instructions: INSTRUCTIONS });

server.registerTool("video_check_setup", {
  title: "Check setup",
  description: "Check that the ElevenLabs key works and the video tools are ready. Shows the plan and credits left. Run this first in a new conversation.",
  inputSchema: {}, annotations: { readOnlyHint: true },
}, async () => {
  const lines = [`Video Watch ${VERSION}. Files are saved in: ${OUTPUT}`,
    `Video tools: ffmpeg ${existsSync(vid.FFMPEG) ? "ready" : "MISSING"}, downloader ${existsSync(vid.YTDLP) ? "ready" : "MISSING"}`];
  try {
    const a = await el.account();
    lines.push(`ElevenLabs: connected (plan: ${a.plan}). Characters left: ${a.characters_left?.toLocaleString() ?? "unknown"} of ${a.characters_limit?.toLocaleString() ?? "?"}.`);
  } catch (e) { lines.push(`ElevenLabs: not ready. ${e.message}`); }
  return ok(text(lines.join("\n")));
});

server.registerTool("video_brief_questions", {
  title: "Video brief questions",
  description: "The quality questions to ask before making or improving a video (purpose, audience, format, length, tone, voice, music, brand). Ask them a group at a time, offering the suggested option.",
  inputSchema: {}, annotations: { readOnlyHint: true },
}, async () => ok(text(JSON.stringify(BRIEF, null, 1))));

server.registerTool("video_save_brief", {
  title: "Save the brief",
  description: "Save the user's answers to the brief in the project folder so later steps can follow them.",
  inputSchema: { project: z.string().describe("Short project name, e.g. 'spring launch'"), brief: z.record(z.string(), z.string()).describe("Question id -> answer") },
}, async ({ project, brief }) => {
  const d = projectDir(project);
  writeFileSync(join(d, "brief.json"), JSON.stringify(brief, null, 1));
  return ok(text(`Brief saved for "${project}" (${Object.keys(brief).length} answers).`));
});

server.registerTool("list_my_videos", {
  title: "Find my videos",
  description: "List the most recent video files on this Mac (Downloads, Desktop, Movies, and the Video Watch folder), so the user can say which one.",
  inputSchema: {}, annotations: { readOnlyHint: true },
}, async () => {
  const v = vid.recentVideos(OUTPUT);
  return ok(text(v.length ? v.map((x, i) => `${i + 1}. ${x.name} (${x.mb} MB, ${x.modified})\n   ${x.path}`).join("\n")
    : "No videos found in Downloads, Desktop or Movies. Ask the user to save the video there, or give a YouTube link."));
});

server.registerTool("watch_video", {
  title: "Watch a video",
  description: "Watch a video (YouTube or any link, or a file path on this Mac) like a person: keyframes where the picture changes (as labelled contact sheets), a timestamped transcript (captions, or ElevenLabs speech-to-text which uses a few credits), cuts and silences. Use focus 'screen' for screen recordings/UI, 'ad' for fast-cut ads.",
  inputSchema: {
    source: z.string().describe("YouTube/any URL, or a file path on this Mac"),
    project: z.string().describe("Short project name; files go in its folder"),
    start: z.string().optional().describe("Optional start time, e.g. 1:30"),
    end: z.string().optional().describe("Optional end time"),
    focus: z.enum(["general", "screen", "ad", "talk"]).optional().default("general"),
    transcribe: z.boolean().optional().default(true).describe("Use ElevenLabs speech-to-text when there are no captions"),
  },
}, async ({ source, project, start, end, focus, transcribe }) => runJob(`watching ${source}`, async () => {
  const opts = { general: [48, 2], screen: [60, 3], ad: [72, 2], talk: [36, 2] }[focus];
  const m = await vid.watch(source, projectDir(project), { start, end, maxFrames: opts[0], sensitivity: opts[1], transcribe });
  const shown = m.sheets.slice(0, 5);
  return ok(text(vid.manifestText(m) + (m.sheets.length > shown.length ? `\n\n(${m.sheets.length - shown.length} more contact sheets on disk; use zoom_video for details.)` : "")),
    ...shown.map(image));
}));

server.registerTool("zoom_video", {
  title: "Re-watch a moment",
  description: "Look closely at a short moment (2-8 s) of a video already watched in this project: up to 16 dense frames as one image, plus what is said then.",
  inputSchema: { project: z.string(), start: z.string(), end: z.string(), fps: z.number().optional().default(4) },
}, async ({ project, start, end, fps }) => {
  try {
    const d = join(OUTPUT, slug(project));
    if (!existsSync(join(d, "manifest.json"))) throw new el.UserError("Watch the video first (watch_video) in this project.");
    const z0 = await vid.zoom(d, start, end, fps);
    return ok(text(`${z0.frames} frames ${start}-${end}. Said: ${z0.said.map((c) => `[${vid.ts(c.start)}] "${c.text}"`).join(" ") || "(nothing)"}`), image(z0.sheet));
  } catch (e) { return fail(e); }
});

server.registerTool("open_voice_picker", {
  title: "Open the voice picker",
  description: "Open a page in the user's browser with their ElevenLabs voices and the whole public voice library: search, filters, free previews, and a 'Use this voice' button. After opening, tell the user, then call get_chosen_voice.",
  inputSchema: { project: z.string() },
}, async ({ project }) => {
  try {
    const r = await el.openPicker(projectDir(project));
    return ok(text(`The voice picker is open in the browser (${r.url}). ${r.your_voices} of the user's own voices are shown, plus a tab to search all ElevenLabs voices. Ask them to listen and click "Use this voice", then call get_chosen_voice.`));
  } catch (e) { return fail(e); }
});

server.registerTool("get_chosen_voice", {
  title: "Get the chosen voice",
  description: "Wait (up to 45 s) for the user to click 'Use this voice' in the picker. Call again if they haven't chosen yet.",
  inputSchema: { project: z.string() },
}, async ({ project }) => {
  const v = await el.waitForChoice(45000) || el.savedVoice(join(OUTPUT, slug(project)));
  if (!v) return ok(text("No voice chosen yet. The picker is still open. Ask the user if they've found one, then call this again."));
  return ok(text(`Chosen voice: ${v.name} (${[v.gender, v.age, v.accent, v.use_case].filter(Boolean).join(", ")}). voice_id ${v.voice_id}.` +
    (Number(v.rate) > 1 ? ` Note: this voice uses ${v.rate}x credits.` : "")));
});

server.registerTool("search_voices", {
  title: "Search voices",
  description: "Search voices without the picker (the user's own voices, or the public library). Prefer open_voice_picker so the user can listen.",
  inputSchema: { query: z.string().optional(), gender: z.enum(["female", "male", "neutral"]).optional(), language: z.string().optional().default("en"),
                 library: z.boolean().optional().default(true) },
  annotations: { readOnlyHint: true },
}, async ({ query, gender, language, library }) => {
  try {
    const list = library ? (await el.libraryPage({ search: query, gender, language }, 0, 12)).voices
      : (await el.myVoices()).filter((v) => (!gender || v.gender === gender) && (!query || JSON.stringify(v).toLowerCase().includes(query.toLowerCase())));
    return ok(text(list.slice(0, 12).map((v) => `- ${v.name} [${v.voice_id}]: ${[v.gender, v.age, v.accent, v.use_case].filter(Boolean).join(", ")}. ${v.description}`).join("\n") || "No voices match."));
  } catch (e) { return fail(e); }
});

server.registerTool("make_voiceover", {
  title: "Make the voiceover",
  description: "Make the voiceover with ElevenLabs (uses about 1 credit per character; ask the user first). One audio clip per line, with exact lengths and word timings. Uses the voice chosen in the picker unless voice_id is given.",
  inputSchema: {
    project: z.string(),
    lines: z.array(z.object({ id: z.string().describe("e.g. s1, s2"), text: z.string() })).min(1),
    voice_id: z.string().optional(),
    speed: z.number().min(0.7).max(1.2).optional().default(1),
    stability: z.number().min(0).max(1).optional().default(0.5).describe("Lower = more expressive"),
  },
}, async ({ project, lines, voice_id, speed, stability }) => runJob("the voiceover", async () => {
  const d = projectDir(project);
  const voice = voice_id || el.savedVoice(d)?.voice_id;
  if (!voice) throw new el.UserError("No voice chosen yet. Open the voice picker first.");
  const out = await el.speak(d, voice, lines, { speed, stability }, vid.mediaSeconds);
  const total = out.reduce((s, l) => s + (l.seconds || 0), 0);
  return ok(text(`Voiceover made: ${out.length} lines, ${total.toFixed(1)} s in total, ${lines.reduce((s, l) => s + l.text.length, 0)} characters.\n` +
    out.map((l) => `- ${l.id}: ${l.seconds?.toFixed(1)} s  "${l.text}"`).join("\n")));
}));

server.registerTool("make_music", {
  title: "Make background music",
  description: "Make instrumental background music with ElevenLabs (uses credits; ask first; may need a paid plan). Describe genre, mood, tempo and instruments.",
  inputSchema: { project: z.string(), prompt: z.string(), seconds: z.number().min(3).max(600) },
}, async ({ project, prompt, seconds }) => runJob("the music", async () => {
  const f = await el.music(projectDir(project), prompt, seconds);
  return ok(text(`Music made: ${(await vid.mediaSeconds(f))?.toFixed(1)} s, "${prompt}".`));
}));

server.registerTool("make_sound_effect", {
  title: "Make a sound effect",
  description: "Make one sound effect with ElevenLabs (uses credits; ask first), e.g. 'soft whoosh', 'UI click', 'crowd cheer'.",
  inputSchema: { project: z.string(), description: z.string(), name: z.string().describe("short file name, e.g. whoosh1"),
                 seconds: z.number().min(0.5).max(30).optional() },
}, async ({ project, description, name, seconds }) => runJob(`the "${name}" sound`, async () => {
  const f = await el.soundEffect(projectDir(project), description, slug(name), seconds);
  return ok(text(`Sound effect "${slug(name)}" made (${(await vid.mediaSeconds(f))?.toFixed(1)} s).`));
}));

server.registerTool("mix_video", {
  title: "Put it all together",
  description: "Mix the voiceover, music (automatically quieter under the voice) and sound effects into a new copy of the video. The original is never changed. Lines play back to back from 0.5 s unless voice_at pins them to moments.",
  inputSchema: {
    project: z.string(),
    video: z.string().optional().describe("Video file path; defaults to the video watched in this project"),
    voice_at: z.record(z.string(), z.number()).optional().describe("line id -> start second, e.g. {\"s2\": 6.0}"),
    sound_effects: z.array(z.object({ name: z.string(), at: z.number() })).optional(),
    keep_original_sound: z.number().min(0).max(1).optional().default(0).describe("0 = replace, 0.3 = keep quietly"),
    music_level: z.number().min(0).max(1).optional().default(0.35),
  },
}, async ({ project, video, voice_at, sound_effects, keep_original_sound, music_level }) => runJob("the final mix", async () => {
  const d = projectDir(project);
  const src = video || (existsSync(join(d, "manifest.json")) ? JSON.parse(readFileSync(join(d, "manifest.json"), "utf8")).video : null);
  if (!src) throw new el.UserError("Which video? Give a file path, or watch_video it first.");
  const sfx = (sound_effects || []).map((x) => ({ file: join(d, "audio", "sfx", `${slug(x.name)}.mp3`), at: x.at }));
  const missing = sfx.find((x) => !existsSync(x.file));
  if (missing) throw new el.UserError(`Sound effect not made yet: ${missing.file}`);
  const r = await vid.mix(d, src, { voiceAt: voice_at || {}, sfx, keepOriginal: keep_original_sound, musicLevel: music_level });
  return ok(text(`Done: ${r.file} (${r.seconds?.toFixed(1)} s).${r.warning ? `\nNote: ${r.warning}` : ""}\nVoice lines: ${r.placed.map((p) => `${p.id} ${vid.ts(p.at)}-${vid.ts(p.until)}`).join(", ") || "none"}.\nWatch it back (watch_video) to check timing, then open_result to play it for the user.`));
}));

server.registerTool("open_result", {
  title: "Open the result",
  description: "Open the finished video (or the project folder) on the user's Mac so they can watch it.",
  inputSchema: { project: z.string(), what: z.enum(["video", "folder"]).optional().default("video") },
}, async ({ project, what }) => {
  const d = join(OUTPUT, slug(project)), f = join(d, "final.mp4");
  const target = what === "video" && existsSync(f) ? f : d;
  execFile("open", [target]);
  return ok(text(`Opened ${target}`));
});

server.registerTool("check_progress", {
  title: "Check progress",
  description: "Keep waiting for a long job (watching, voiceover, music, mixing) that said it was still working.",
  inputSchema: { job_id: z.string() },
}, async ({ job_id }) => {
  const job = jobs.get(job_id);
  if (job && !job.done) await Promise.race([job.promise, sleep(45000)]);
  return settle(job_id);
});

server.registerPrompt("make_a_video", {
  title: "Make or improve a video",
  description: "Guided: brief questions, voice picker, script, voiceover, music and the final video.",
  argsSchema: { idea: z.string().optional().describe("What the video is about, or a link/file") },
}, ({ idea }) => ({
  messages: [{ role: "user", content: { type: "text", text:
    `I want to make a great video${idea ? `: ${idea}` : ""}. Check setup first, then walk me through the brief questions a few at a time, ` +
    `help me pick a voice by listening, write the script with me, tell me the credit cost before making anything, and give me the finished video.` } }],
}));

await server.connect(new StdioServerTransport());
