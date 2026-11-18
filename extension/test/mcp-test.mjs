// End-to-end check of the extension server, acting as Claude would: node test/mcp-test.mjs <step...>
// Steps: tools, setup, brief, find, watch, zoom, youtube, picker, voice, sfx, music, mix. Key comes from the environment.
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const steps = new Set(process.argv.slice(2));
const P = process.env.TEST_PROJECT || "vw-selftest";
const client = new Client({ name: "selftest", version: "1" });
await client.connect(new StdioClientTransport({ command: "node", args: [join(root, "server", "index.js")],
  env: { ...process.env, VW_NO_BROWSER: "1" } }));

const show = (name, r) => {
  const t = r.content.filter((c) => c.type === "text").map((c) => c.text).join("\n");
  const imgs = r.content.filter((c) => c.type === "image").length;
  console.log(`\n=== ${name}${r.isError ? " (ERROR)" : ""}${imgs ? ` [+${imgs} image(s)]` : ""}\n${t.slice(0, 1400)}`);
  return r;
};
const call = async (name, args = {}) => {
  let r = await client.callTool({ name, arguments: args }, undefined, { timeout: 600000 });
  const m = r.content[0]?.text?.match(/job_id "([^"]+)"/);
  if (m) {
    console.log(`   (${name}: deferred as ${m[1]}, polling)`);
    do { r = await client.callTool({ name: "check_progress", arguments: { job_id: m[1] } }, undefined, { timeout: 600000 }); }
    while (r.content[0]?.text?.includes("Still working"));
  }
  return show(name, r);
};

if (steps.has("tools")) {
  console.log("tools:", (await client.listTools()).tools.map((x) => x.name).join(", "));
  console.log("prompts:", (await client.listPrompts()).prompts.map((x) => x.name).join(", "));
  console.log("instructions:", (client.getInstructions() || "").slice(0, 80) + "...");
}
if (steps.has("setup")) await call("video_check_setup");
if (steps.has("brief")) {
  const r = await client.callTool({ name: "video_brief_questions", arguments: {} });
  console.log("\n=== brief:", JSON.parse(r.content[0].text).map((g) => `${g.group} (${g.questions.length})`).join(" | "));
  await call("video_save_brief", { project: P, brief: { goal: "Explainer", length: "30 s" } });
}
if (steps.has("find")) await call("list_my_videos");
if (steps.has("watch")) await call("watch_video", { source: process.env.TEST_VIDEO, project: P });
if (steps.has("zoom")) await call("zoom_video", { project: P, start: "0:02", end: "0:05" });
if (steps.has("youtube")) await call("watch_video", { source: "https://www.youtube.com/watch?v=jNQXAC9IVRw", project: P + "-yt", transcribe: false });
if (steps.has("picker")) {
  const r = await call("open_voice_picker", { project: P });
  const url = r.content[0].text.match(/\((http:\/\/127\.0\.0\.1:\d+\/)\)/)[1];
  const lib = await (await fetch(url + "api/library?search=warm&language=en&gender=female&page=0")).json();
  console.log("   library search 'warm female':", lib.total, "-> picking", lib.voices[0].name);
  console.log("   bad id ->", (await fetch(url + "choose", { method: "POST", body: JSON.stringify({ voice_id: "nope" }) })).status);
  console.log("   good id ->", (await fetch(url + "choose", { method: "POST", body: JSON.stringify({ voice_id: lib.voices[0].voice_id }) })).status);
  await call("get_chosen_voice", { project: P });
}
if (steps.has("voice")) await call("make_voiceover", { project: P, lines: [{ id: "s1", text: "Meet Video Watch." }, { id: "s2", text: "Pick a voice, and your video is ready in minutes." }] });
if (steps.has("sfx")) await call("make_sound_effect", { project: P, description: "soft airy whoosh transition", name: "whoosh", seconds: 1 });
if (steps.has("music")) await call("make_music", { project: P, prompt: "bright modern corporate electro-pop, 120 bpm, light synths, uplifting", seconds: 8 });
if (steps.has("mix")) await call("mix_video", { project: P, sound_effects: [{ name: "whoosh", at: 2.5 }] });
await client.close();
