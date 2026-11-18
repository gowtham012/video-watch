// ElevenLabs: account check, voices (yours + the public library), voice picker page,
// voiceover with word timings, instrumental music, sound effects, speech-to-text.
// The key comes from Claude's extension settings (stored securely by Claude) via ELEVENLABS_API_KEY.
import { execFile } from "node:child_process";
import { createServer } from "node:http";
import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";

const API = (process.env.ELEVENLABS_BASE_URL || "https://api.elevenlabs.io").replace(/\/$/, "");
export const TTS_MODEL = "eleven_multilingual_v2";

export class UserError extends Error {}

function key() {
  const k = (process.env.ELEVENLABS_API_KEY || "").trim();
  if (!k || k.startsWith("${")) {
    throw new UserError("No ElevenLabs key yet. Open Claude → Settings → Extensions → Video Watch, paste your ElevenLabs API key " +
      "(elevenlabs.io → Developers → API Keys), then try again.");
  }
  return k;
}

const HINTS = {
  401: "The ElevenLabs key was rejected. Update it in Claude → Settings → Extensions → Video Watch.",
  402: "Your ElevenLabs plan doesn't include this, or you're out of credits.",
  403: "Your ElevenLabs plan doesn't allow this feature.",
  429: "ElevenLabs is busy (rate limit). Wait a minute and try again.",
};

export async function api(method, path, { params, body, form, raw = false, timeoutMs = 300000 } = {}) {
  const url = new URL(API + path);
  for (const [k, v] of Object.entries(params || {})) if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
  const headers = { "xi-api-key": key(), "User-Agent": "video-watch-extension" };
  let payload;
  if (form) payload = form;
  else if (body !== undefined) { headers["Content-Type"] = "application/json"; payload = JSON.stringify(body); }
  let res;
  try {
    res = await fetch(url, { method, headers, body: payload, signal: AbortSignal.timeout(timeoutMs) });
  } catch (e) {
    throw new UserError(`Couldn't reach ElevenLabs (${e.name === "TimeoutError" ? "timed out" : e.message}). Check the internet connection.`);
  }
  if (!res.ok) {
    const detail = (await res.text()).slice(0, 400);
    throw new UserError(`ElevenLabs said ${res.status}. ${HINTS[res.status] || ""} ${detail}`.trim());
  }
  return raw ? Buffer.from(await res.arrayBuffer()) : res.json();
}

// ------------------------------------------------------------- account
export async function account() {
  const s = await api("GET", "/v1/user/subscription");
  const used = s.character_count, limit = s.character_limit;
  return { plan: s.tier, characters_used: used, characters_limit: limit,
           characters_left: Number.isInteger(used) && Number.isInteger(limit) ? limit - used : null };
}

// ------------------------------------------------------------- voices
const slimMine = (v) => {
  const l = v.labels || {};
  return { voice_id: v.voice_id, name: v.name, source: "yours", gender: l.gender, age: l.age, accent: l.accent,
           use_case: l.use_case || l["use case"], descriptive: l.descriptive, language: l.language,
           description: (v.description || "").slice(0, 200), preview_url: v.preview_url, rate: 1 };
};
const slimLib = (v) => ({ voice_id: v.voice_id, name: v.name, source: "library", gender: v.gender, age: v.age,
  accent: v.accent, use_case: v.use_case, descriptive: v.descriptive, language: v.language,
  description: (v.description || "").slice(0, 200), preview_url: v.preview_url, rate: v.rate || 1 });

export async function myVoices() {
  const out = [];
  let token;
  do {
    const r = await api("GET", "/v2/voices", { params: { page_size: 100, next_page_token: token } });
    out.push(...(r.voices || []).map(slimMine));
    token = r.has_more ? r.next_page_token : null;
  } while (token);
  return out;
}

const LIB_FILTERS = ["search", "gender", "age", "accent", "use_cases", "language"];
export async function libraryPage(q = {}, page = 0, pageSize = 30) {
  const params = { page_size: pageSize, page };
  for (const k of LIB_FILTERS) if (q[k]) params[k] = q[k];
  const r = await api("GET", "/v1/shared-voices", { params });
  // voices with an extra per-use cash fee are left out
  return { voices: (r.voices || []).filter((v) => !v.fiat_rate).map(slimLib), has_more: !!r.has_more, total: r.total_count };
}

// ------------------------------------------------------------- voice picker (local page)
const picker = { server: null, url: null, seen: new Map(), chosen: null, jobDir: null };

export async function openPicker(jobDir) {
  const mine = await myVoices();
  picker.seen = new Map(mine.map((v) => [v.voice_id, v]));
  picker.chosen = null;
  picker.jobDir = jobDir;
  const html = PICKER_HTML.replace("__MINE_COUNT__", String(mine.length))
    .replace("__VOICES__", JSON.stringify(mine).replace(/<\//g, "<\\/"));
  if (picker.server) picker.server.close();
  picker.server = createServer(async (req, res) => {
    const u = new URL(req.url, "http://x");
    const send = (code, body, type = "application/json") => { res.writeHead(code, { "Content-Type": type }); res.end(body); };
    if (req.method === "GET" && u.pathname === "/api/library") {
      try {
        const q = Object.fromEntries(u.searchParams);
        const r = await libraryPage(q, Number(q.page || 0));
        r.voices.forEach((v) => picker.seen.set(v.voice_id, v));
        return send(200, JSON.stringify(r));
      } catch (e) { return send(502, JSON.stringify({ error: e.message })); }
    }
    if (req.method === "POST" && u.pathname === "/choose") {
      let raw = "";
      req.on("data", (c) => { raw += c; if (raw.length > 10000) req.destroy(); });
      req.on("end", () => {
        let id; try { id = JSON.parse(raw).voice_id; } catch { id = null; }
        const v = picker.seen.get(id);   // only a voice the page was shown can be chosen
        if (!v) return send(400, "{}");
        picker.chosen = v;
        mkdirSync(picker.jobDir, { recursive: true });
        writeFileSync(join(picker.jobDir, "voice.json"), JSON.stringify(v, null, 1));
        send(200, "{}");
      });
      return;
    }
    send(200, html, "text/html; charset=utf-8");
  });
  await new Promise((r) => picker.server.listen(0, "127.0.0.1", r));   // this Mac only
  picker.url = `http://127.0.0.1:${picker.server.address().port}/`;
  if (!process.env.VW_NO_BROWSER) execFile("open", [picker.url]);
  return { url: picker.url, your_voices: mine.length };
}

export async function waitForChoice(maxMs = 45000) {
  const end = Date.now() + maxMs;
  while (!picker.chosen && Date.now() < end) await new Promise((r) => setTimeout(r, 300));
  if (picker.chosen && picker.server) { setTimeout(() => { picker.server?.close(); picker.server = null; }, 1500); }
  return picker.chosen;
}

export function savedVoice(jobDir) {
  const p = join(jobDir, "voice.json");
  return existsSync(p) ? JSON.parse(readFileSync(p, "utf8")) : null;
}

// ------------------------------------------------------------- voiceover
function wordsFromAlignment(al = {}) {
  const words = [];
  let cur = "", s = null, e = null;
  const ch = al.characters || [], cs = al.character_start_times_seconds || [], ce = al.character_end_times_seconds || [];
  for (let i = 0; i < ch.length; i++) {
    if (/\s/.test(ch[i])) { if (cur) words.push({ word: cur, start: +s.toFixed(3), end: +e.toFixed(3) }); cur = ""; s = e = null; continue; }
    cur += ch[i]; if (s === null) s = cs[i]; e = ce[i];
  }
  if (cur) words.push({ word: cur, start: +s.toFixed(3), end: +e.toFixed(3) });
  return words;
}

export async function speak(jobDir, voiceId, lines, { speed = 1, stability = 0.5, style = 0.2 } = {}, mediaSeconds) {
  const dir = join(jobDir, "audio");
  mkdirSync(dir, { recursive: true });
  const settings = { stability, similarity_boost: 0.75, style, speed };
  const out = [];
  for (let i = 0; i < lines.length; i++) {
    const body = { text: lines[i].text, model_id: TTS_MODEL, voice_settings: settings };
    if (i > 0) body.previous_text = lines[i - 1].text;            // keeps intonation flowing across lines
    if (i + 1 < lines.length) body.next_text = lines[i + 1].text;
    const r = await api("POST", `/v1/text-to-speech/${encodeURIComponent(voiceId)}/with-timestamps`,
      { params: { output_format: "mp3_44100_128" }, body });
    const file = join(dir, `${lines[i].id}.mp3`);
    writeFileSync(file, Buffer.from(r.audio_base64, "base64"));
    const words = wordsFromAlignment(r.alignment || {});
    out.push({ id: lines[i].id, text: lines[i].text, file, seconds: (await mediaSeconds(file)) ?? words.at(-1)?.end ?? null, words });
  }
  writeFileSync(join(dir, "voiceover.json"), JSON.stringify({ voice_id: voiceId, lines: out }, null, 1));
  return out;
}

export async function music(jobDir, prompt, seconds, name = "music") {
  const dir = join(jobDir, "audio");
  mkdirSync(dir, { recursive: true });
  const ms = Math.round(Math.max(3, Math.min(600, seconds)) * 1000);
  const buf = await api("POST", "/v1/music", { params: { output_format: "mp3_44100_128" }, raw: true, timeoutMs: 600000,
    body: { prompt, music_length_ms: ms, force_instrumental: true } });
  const file = join(dir, `${name}.mp3`);
  writeFileSync(file, buf);
  return file;
}

export async function soundEffect(jobDir, text, name, seconds) {
  const dir = join(jobDir, "audio", "sfx");
  mkdirSync(dir, { recursive: true });
  const body = { text, prompt_influence: 0.5 };
  if (seconds) body.duration_seconds = Math.max(0.5, Math.min(30, seconds));
  const buf = await api("POST", "/v1/sound-generation", { params: { output_format: "mp3_44100_128" }, body, raw: true });
  const file = join(dir, `${name}.mp3`);
  writeFileSync(file, buf);
  return file;
}

export async function transcribe(audioFile) {
  const form = new FormData();
  form.set("model_id", "scribe_v1");
  form.set("file", new Blob([readFileSync(audioFile)], { type: "audio/mpeg" }), "audio.mp3");
  const r = await api("POST", "/v1/speech-to-text", { form, timeoutMs: 600000 });
  // group words into caption-sized lines (a sentence, or 12 words)
  const lines = [];
  let cur = null;
  for (const w of r.words || []) {
    if (w.type !== "word") { if (cur && w.type === "spacing") cur.text += " "; continue; }
    if (!cur) cur = { start: w.start, end: w.end, text: "" };
    cur.text += w.text; cur.end = w.end;
    if (/[.!?]$/.test(w.text) || cur.text.split(" ").length >= 12) { lines.push({ ...cur, text: cur.text.trim() }); cur = null; }
  }
  if (cur) lines.push({ ...cur, text: cur.text.trim() });
  return { language: r.language_code, lines };
}

// ------------------------------------------------------------- picker page
const PICKER_HTML = readFileSync(new URL("./picker.html", import.meta.url), "utf8");
