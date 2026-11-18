// Video side: fetch (link or file), find the moments the picture changes, labelled contact sheets,
// silences, transcript (captions or ElevenLabs speech-to-text), zoom, and the final audio mix.
// Uses the ffmpeg and yt-dlp bundled inside the extension - nothing to install.
import { execFile } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync, statSync } from "node:fs";
import { homedir } from "node:os";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import ffmpegPath from "ffmpeg-static";
import { UserError } from "./eleven.js";

const HERE = dirname(fileURLToPath(import.meta.url));
export const FFMPEG = ffmpegPath;
export const YTDLP = join(HERE, "..", "bin", "yt-dlp");
const FONT = ["/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/SFNSMono.ttf"].find(existsSync);

function run(bin, args, { timeoutMs = 600000, cwd } = {}) {
  return new Promise((res) => {
    execFile(bin, args, { maxBuffer: 1 << 28, timeout: timeoutMs, cwd }, (err, stdout, stderr) =>
      res({ code: err ? (err.code ?? 1) : 0, stdout: String(stdout), stderr: String(stderr) }));
  });
}

export const ts = (t) => {
  t = Math.max(0, t);
  const h = Math.floor(t / 3600), m = Math.floor((t % 3600) / 60), s = (t % 60).toFixed(1).padStart(4, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${s}` : `${String(m).padStart(2, "0")}:${s}`;
};

export function parseTime(v) {
  if (v === undefined || v === null || v === "") return null;
  if (typeof v === "number") return v;
  return String(v).split(":").reduce((acc, p) => acc * 60 + parseFloat(p), 0);
}

export async function info(path) {
  const r = await run(FFMPEG, ["-hide_banner", "-i", path]);
  const d = r.stderr.match(/Duration: (\d+):(\d+):([\d.]+)/);
  const v = r.stderr.match(/Stream #.*Video:.*?(\d{2,5})x(\d{2,5})/);
  return { duration: d ? +d[1] * 3600 + +d[2] * 60 + +d[3] : null, width: v ? +v[1] : null, height: v ? +v[2] : null,
           hasVideo: /Stream #.*Video:/.test(r.stderr), hasAudio: /Stream #.*Audio:/.test(r.stderr) };
}
export const mediaSeconds = async (p) => (await info(p)).duration;

// ------------------------------------------------------------- find videos on this Mac
export function recentVideos(outputDir, limit = 15) {
  const roots = [join(homedir(), "Downloads"), join(homedir(), "Desktop"), join(homedir(), "Movies"), outputDir];
  const found = [];
  const walk = (dir, depth) => {
    let entries = [];
    try { entries = readdirSync(dir, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      if (e.name.startsWith(".")) continue;
      const p = join(dir, e.name);
      if (e.isDirectory() && depth > 0) walk(p, depth - 1);
      else if (/\.(mp4|mov|m4v|webm|mkv)$/i.test(e.name)) {
        try { const st = statSync(p); found.push({ path: p, name: e.name, mb: +(st.size / 1e6).toFixed(1), modified: st.mtime.toISOString().slice(0, 16).replace("T", " ") }); } catch {}
      }
    }
  };
  roots.forEach((r) => walk(r, 2));
  return found.sort((a, b) => b.modified.localeCompare(a.modified)).slice(0, limit);
}

// ------------------------------------------------------------- fetch
export async function fetchVideo(src, jobDir) {
  mkdirSync(jobDir, { recursive: true });
  if (!/^https?:\/\//i.test(src)) {
    const p = resolve(src.replace(/^~(?=$|\/)/, homedir()));
    if (!existsSync(p)) throw new UserError(`I can't find a video at ${p}. Use list_my_videos to see recent videos on this Mac.`);
    const subs = [".vtt", ".srt"].map((e) => p.replace(/\.[^.]+$/, e)).find(existsSync) || null;
    return { video: p, subs, meta: { title: basename(p), source: p } };
  }
  const out = join(jobDir, "source.%(ext)s");
  const r = await run(YTDLP, ["--no-playlist", "--ffmpeg-location", FFMPEG, "-f", "bv*[height<=720]+ba/b[height<=720]/bv*+ba/b",
    "--merge-output-format", "mp4", "-o", out, "--write-info-json", "--write-subs", "--write-auto-subs",
    "--sub-langs", "en,en-orig,en-US,en-GB,-live_chat", "--sub-format", "vtt/srt/best", "--ignore-errors",
    "--no-progress", "--quiet", "--no-warnings", src], { timeoutMs: 900000 });
  const files = readdirSync(jobDir);
  const vid = files.find((f) => /^source\.(mp4|mkv|webm|mov)$/.test(f));
  if (!vid) throw new UserError(`Couldn't download that link. ${r.stderr.slice(-500)}\nIf it's private or blocked, download it yourself and give me the file instead.`);
  const subs = files.filter((f) => /^source\..*\.(vtt|srt)$/.test(f)).sort((a, b) => (/\.en\./.test(b) ? 1 : 0) - (/\.en\./.test(a) ? 1 : 0))[0];
  let meta = { source: src };
  try {
    const j = JSON.parse(readFileSync(join(jobDir, "source.info.json"), "utf8"));
    meta = { source: src, title: j.title, channel: j.channel || j.uploader, description: (j.description || "").slice(0, 1500),
             chapters: (j.chapters || []).map((c) => ({ start: c.start_time, title: c.title })) };
  } catch {}
  return { video: join(jobDir, vid), subs: subs ? join(jobDir, subs) : null, meta };
}

// ------------------------------------------------------------- captions
export function parseSubs(path) {
  const txt = readFileSync(path, "utf8").replace(/\r/g, "");
  const cues = [];
  const re = /(\d+:)?(\d+):(\d+)[.,](\d+)\s+-->\s+(\d+:)?(\d+):(\d+)[.,](\d+)[^\n]*\n([\s\S]*?)(?=\n\n|$)/g;
  const t = (h, m, s, ms) => (h ? parseInt(h) * 3600 : 0) + +m * 60 + +s + +ms / 1000;
  let m, last = "";
  while ((m = re.exec(txt))) {
    const lines = m[9].split("\n").map((l) => l.replace(/<[^>]+>/g, "").trim()).filter(Boolean);
    const text = lines.at(-1) || "";   // YouTube rolling captions repeat the previous line first
    if (!text || text === last) continue;
    last = text;
    cues.push({ start: +t(m[1], m[2], m[3], m[4]).toFixed(2), end: +t(m[5], m[6], m[7], m[8]).toFixed(2), text });
  }
  return cues;
}

// ------------------------------------------------------------- picture changes
async function sceneScores(video, start, dur, fps, jobDir) {
  const f = join(jobDir, "scene_scores.txt");
  await run(FFMPEG, ["-v", "error", "-ss", String(start), "-t", String(dur), "-i", video, "-an", "-vf",
    // quote the path: the output folder ("Video Watch") has a space, which breaks an unquoted filter
    `fps=${fps},scale=320:-2,select='gte(scene,0)',metadata=print:key=lavfi.scene_score:file='${f.replace(/'/g, "'\\''")}'`, "-f", "null", "-"]);
  if (!existsSync(f)) return [];
  const out = [];
  let t = null;
  for (const line of readFileSync(f, "utf8").split("\n")) {
    const a = line.match(/pts_time:([\d.]+)/); if (a) t = start + +a[1];
    const b = line.match(/scene_score=([\d.]+)/); if (b && t !== null) out.push({ t, s: +b[1] });
  }
  return out;
}

function pickKeyframes(scores, start, end, maxFrames, sensitivity) {
  const thr = 0.12 / sensitivity;      // 2 -> 0.06 (default), 3 -> 0.04 catches small UI/text changes
  const cuts = scores.filter((x) => x.s >= 0.4).map((x) => +x.t.toFixed(2));
  let changes = [{ t: start, s: 1, kind: "start" }];
  for (const x of scores) if (x.s >= thr && x.t - changes.at(-1).t >= 1.0) changes.push({ t: x.t, s: x.s, kind: x.s >= 0.4 ? "cut" : "change" });
  if (changes.length > maxFrames) changes = [changes[0], ...changes.slice(1).sort((a, b) => b.s - a.s).slice(0, maxFrames - 1)].sort((a, b) => a.t - b.t);
  // a settled look: ~0.5 s after the change (or half way to the next one)
  let picks = changes.map((c, i) => {
    const next = changes[i + 1]?.t ?? end;
    return { t: Math.min(c.t + Math.min(0.5, (next - c.t) / 2), end - 0.3), kind: c.kind };
  });
  // no long blind spots: add a "coverage" frame wherever a gap is too long
  const maxGap = Math.max(6, ((end - start) / maxFrames) * 1.6);
  const filled = [];
  for (let i = 0; i < picks.length; i++) {
    filled.push(picks[i]);
    const next = picks[i + 1]?.t ?? end;
    for (let t = picks[i].t + maxGap; t < next - 1.5; t += maxGap) filled.push({ t, kind: "coverage" });
  }
  picks = filled.sort((a, b) => a.t - b.t).slice(0, Math.max(maxFrames, 8));
  return { picks: picks.map((p) => ({ ...p, t: +Math.max(0, p.t).toFixed(2) })), cuts };
}

const esc = (s) => s.replace(/\\/g, "\\\\").replace(/:/g, "\\:").replace(/'/g, "\u2019");
async function grab(video, t, full, thumb, label, width = 768) {
  const draw = FONT ? `,drawtext=fontfile='${FONT}':text='${esc(label)}':x=10:y=10:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.65:boxborderw=6` : "";
  const r = await run(FFMPEG, ["-v", "error", "-y", "-ss", t.toFixed(3), "-i", video, "-frames:v", "1", "-filter_complex",
    `[0:v]split[a][b];[a]scale='min(${width},iw)':-2[full];[b]scale=480:270:force_original_aspect_ratio=decrease,pad=480:270:(ow-iw)/2:(oh-ih)/2:color=0x111111${draw}[thumb]`,
    "-map", "[full]", "-frames:v", "1", "-q:v", "3", full, "-map", "[thumb]", "-frames:v", "1", "-q:v", "4", thumb]);
  return r.code === 0 && existsSync(full);
}

async function sheets(thumbDir, count, outDir, prefix, cols = 4, rows = 3) {
  const per = cols * rows, out = [];
  for (let i = 0; i * per < count; i++) {
    const f = join(outDir, `${prefix}_${String(i + 1).padStart(2, "0")}.jpg`);
    await run(FFMPEG, ["-v", "error", "-y", "-start_number", String(i * per), "-i", join(thumbDir, "t%03d.jpg"), "-frames:v", "1",
      "-vf", `tile=${cols}x${rows}:padding=6:margin=6:color=0x111111`, "-q:v", "4", f]);
    if (existsSync(f)) out.push(f);
  }
  return out;
}

async function silences(video, start, dur) {
  const r = await run(FFMPEG, ["-hide_banner", "-ss", String(start), "-t", String(dur), "-i", video, "-vn",
    "-af", "silencedetect=noise=-38dB:d=0.7,volumedetect", "-f", "null", "-"]);
  const out = [];
  let s = null;
  for (const line of r.stderr.split("\n")) {
    const a = line.match(/silence_start: ([\d.]+)/); if (a) s = start + +a[1];
    const b = line.match(/silence_end: ([\d.]+)/); if (b && s !== null) { out.push([+s.toFixed(1), +(start + +b[1]).toFixed(1)]); s = null; }
  }
  const mean = r.stderr.match(/mean_volume: (-?[\d.]+) dB/);
  return { silences: out, mean_db: mean ? +mean[1] : null };
}

// ------------------------------------------------------------- watch
export async function watch(src, jobDir, { start, end, maxFrames = 48, sensitivity = 2, transcribe } = {}) {
  const { video, subs, meta } = await fetchVideo(src, jobDir);
  const vi = await info(video);
  if (!vi.hasVideo || !vi.duration) throw new UserError("That file doesn't look like a playable video.");
  const s = parseTime(start) ?? 0, e = Math.min(parseTime(end) ?? vi.duration, vi.duration), dur = Math.max(e - s, 0.5);
  const fps = Math.min(4, Math.max(0.5, 7200 / dur));
  const scores = await sceneScores(video, s, dur, fps, jobDir);
  const { picks, cuts } = pickKeyframes(scores, s, e, maxFrames, sensitivity);
  const fdir = join(jobDir, "frames"), tdir = join(jobDir, "thumbs");
  mkdirSync(fdir, { recursive: true }); mkdirSync(tdir, { recursive: true });
  const frames = [];
  for (const p of picks) {
    const i = frames.length;
    const full = join(fdir, `f${String(i).padStart(3, "0")}_${ts(p.t).replace(/:/g, "m")}s.jpg`);
    if (await grab(video, p.t, full, join(tdir, `t${String(i).padStart(3, "0")}.jpg`), `#${i} ${ts(p.t)} ${p.kind}`)) frames.push({ i, t: p.t, kind: p.kind, file: full });
  }
  const sheetFiles = await sheets(tdir, frames.length, jobDir, "sheet");
  let transcript = null, transcriptSource = "none";
  if (subs) { transcript = parseSubs(subs).filter((c) => c.start >= s - 1 && c.start <= e); transcriptSource = `captions (${basename(subs)})`; }
  if ((!transcript || !transcript.length) && vi.hasAudio && transcribe !== false) {
    const a = join(jobDir, "speech.mp3");
    await run(FFMPEG, ["-v", "error", "-y", "-ss", String(s), "-t", String(dur), "-i", video, "-vn", "-ac", "1", "-ar", "16000", "-b:a", "48k", a]);
    try {
      const st = await (await import("./eleven.js")).transcribe(a);
      transcript = st.lines.map((l) => ({ ...l, start: +(l.start + s).toFixed(2), end: +(l.end + s).toFixed(2) }));
      transcriptSource = `ElevenLabs speech-to-text (${st.language || "auto"})`;
    } catch (err) { transcriptSource = `none (speech-to-text failed: ${err.message.slice(0, 120)})`; }
  }
  const audio = vi.hasAudio ? await silences(video, s, dur) : { silences: [], mean_db: null };
  const manifest = { video, meta, info: vi, range: [s, e], frames, cuts, sheets: sheetFiles, transcript, transcript_source: transcriptSource, audio };
  writeFileSync(join(jobDir, "manifest.json"), JSON.stringify(manifest, null, 1));
  return manifest;
}

export function manifestText(m) {
  const L = [];
  L.push(`# ${m.meta.title || basename(m.video)}`);
  if (m.meta.channel) L.push(`Channel: ${m.meta.channel}`);
  L.push(`Length ${ts(m.info.duration)} | ${m.info.width}x${m.info.height} | audio: ${m.info.hasAudio ? "yes" : "no"} | analysed ${ts(m.range[0])}-${ts(m.range[1])}`);
  const mins = Math.max((m.range[1] - m.range[0]) / 60, 1 / 60);
  L.push(`Pacing: ${m.cuts.length} hard cuts (${(m.cuts.length / mins).toFixed(1)}/min); ${m.frames.length} keyframes in ${m.sheets.length} contact sheet(s)`);
  L.push(`Audio (measured, not heard): mean ${m.audio.mean_db ?? "?"} dB; silences ${m.audio.silences.map(([a, b]) => `${ts(a)}-${ts(b)}`).join(", ") || "none"}`);
  L.push(`Transcript: ${m.transcript_source}`);
  if (m.meta.description) L.push(`\nDescription: ${m.meta.description.slice(0, 600)}`);
  if (m.meta.chapters?.length) L.push(`Chapters: ${m.meta.chapters.map((c) => `${ts(c.start)} ${c.title}`).join(" | ")}`);
  L.push("\n## Timeline (frames + speech)");
  const ev = [...m.frames.map((f) => ({ t: f.t, s: `FRAME #${f.i} [${f.kind}]` })),
              ...(m.transcript || []).map((c) => ({ t: c.start, s: `SAY "${c.text}"` })),
              ...m.audio.silences.map(([a, b]) => ({ t: a, s: `SILENCE until ${ts(b)}` }))].sort((a, b) => a.t - b.t);
  for (const x of ev) L.push(`[${ts(x.t)}] ${x.s}`);
  return L.join("\n");
}

export async function zoom(jobDir, start, end, fps = 4) {
  const m = JSON.parse(readFileSync(join(jobDir, "manifest.json"), "utf8"));
  const s = parseTime(start), e = Math.min(parseTime(end), m.info.duration - 0.2);
  if (!(e > s)) throw new UserError("The end time must be after the start time.");
  const n = Math.min(16, Math.max(2, Math.round((e - s) * fps)));
  const zdir = join(jobDir, `zoom_${s.toFixed(1)}-${e.toFixed(1)}`), tdir = join(zdir, "thumbs");
  mkdirSync(tdir, { recursive: true });
  let k = 0;
  for (let i = 0; i < n; i++) {
    const t = s + ((i + 0.5) * (e - s)) / n;
    if (await grab(m.video, t, join(zdir, `z${String(k).padStart(3, "0")}.jpg`), join(tdir, `t${String(k).padStart(3, "0")}.jpg`), `${ts(t)}`, 1280)) k++;
  }
  const [sheet] = await sheets(tdir, k, zdir, "zoom", 4, 4);
  const said = (m.transcript || []).filter((c) => c.end >= s - 0.5 && c.start <= e + 0.5);
  return { sheet, frames: k, said };
}

// ------------------------------------------------------------- mix voice / music / sfx onto a video
export async function mix(jobDir, videoPath, { voiceAt = {}, voiceStart = 0.5, gap = 0.4, sfx = [], keepOriginal = 0, musicLevel = 0.35, sfxLevel = 0.8, useMusic = true } = {}) {
  const vi = await info(videoPath);
  if (!vi.duration) throw new UserError(`I can't read the video at ${videoPath}.`);
  const vo = existsSync(join(jobDir, "audio", "voiceover.json")) ? JSON.parse(readFileSync(join(jobDir, "audio", "voiceover.json"), "utf8")) : { lines: [] };
  const inputs = ["-i", videoPath], f = [], voice = [], mixl = [];
  let n = 1, cursor = voiceStart;
  const placed = [];
  for (const l of vo.lines) {
    const at = voiceAt[l.id] ?? cursor;
    cursor = at + (l.seconds || 0) + gap;
    placed.push({ id: l.id, at: +at.toFixed(2), until: +(at + (l.seconds || 0)).toFixed(2) });
    inputs.push("-i", l.file);
    const ms = Math.round(at * 1000);
    f.push(`[${n}:a]adelay=${ms}|${ms},aformat=channel_layouts=stereo[v${n}]`); voice.push(`[v${n}]`); n++;
  }
  // pad the voice to the full length: the ducking filter stops when its voice input ends, which would cut the music
  if (voice.length) { f.push(`${voice.join("")}amix=inputs=${voice.length}:normalize=0,apad=whole_dur=${vi.duration.toFixed(3)},asplit=2[voice][vkey]`); mixl.push("[voice]"); }
  const musicFile = join(jobDir, "audio", "music.mp3");
  if (useMusic && existsSync(musicFile)) {
    inputs.push("-stream_loop", "-1", "-i", musicFile);
    const m = `[${n}:a]atrim=0:${vi.duration.toFixed(3)},volume=${musicLevel},afade=t=out:st=${Math.max(0, vi.duration - 2).toFixed(3)}:d=2,aformat=channel_layouts=stereo`;
    if (voice.length) f.push(`${m}[mraw]`, "[mraw][vkey]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[music]");
    else f.push(`${m}[music]`);
    mixl.push("[music]"); n++;
  } else if (voice.length) f.push("[vkey]anullsink");
  for (const x of sfx) {
    inputs.push("-i", x.file);
    const ms = Math.round(x.at * 1000);
    f.push(`[${n}:a]adelay=${ms}|${ms},volume=${sfxLevel},aformat=channel_layouts=stereo[s${n}]`); mixl.push(`[s${n}]`); n++;
  }
  if (vi.hasAudio && keepOriginal > 0) { f.push(`[0:a]volume=${keepOriginal},aformat=channel_layouts=stereo[orig]`); mixl.push("[orig]"); }
  if (!mixl.length) throw new UserError("Nothing to mix yet: make a voiceover, music or sound effects first.");
  f.push(`${mixl.join("")}amix=inputs=${mixl.length}:normalize=0,alimiter=limit=0.95[out]`);
  const out = join(jobDir, "final.mp4");
  const r = await run(FFMPEG, ["-v", "error", "-y", ...inputs, "-filter_complex", f.join(";"), "-map", "0:v", "-map", "[out]",
    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", vi.duration.toFixed(3), out]);
  if (r.code !== 0) throw new UserError("Mixing failed: " + r.stderr.slice(-600));
  const musicSecs = useMusic && existsSync(musicFile) ? (await info(musicFile)).duration : null;
  const warning = musicSecs && musicSecs < vi.duration - 1
    ? `The music (${musicSecs.toFixed(0)} s) is shorter than the video (${vi.duration.toFixed(0)} s), so it loops, and each loop fades out and restarts. For a smooth result, make the music ${Math.ceil(vi.duration + 2)} s long and mix again.`
    : null;
  return { file: out, seconds: (await info(out)).duration, placed, warning };
}
