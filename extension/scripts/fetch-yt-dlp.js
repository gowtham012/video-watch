// Build step: download the pinned yt-dlp macOS binary into bin/ and verify its official SHA-256.
// Runs on the packer's machine only; colleagues get the binary inside the .mcpb.
import { createHash } from "node:crypto";
import { chmodSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const VERSION = "2026.10.26";
const SHA256 = "0f922c15ccc0b83eefa1c8bc9104e434318c4bf16e408e1ee93b7745a6efe0aa"; // from the release's SHA2-256SUMS
const URL = `https://github.com/yt-dlp/yt-dlp/releases/download/${VERSION}/yt-dlp_macos`;

const out = join(dirname(fileURLToPath(import.meta.url)), "..", "bin", "yt-dlp");
const sha = (buf) => createHash("sha256").update(buf).digest("hex");

if (existsSync(out) && sha(readFileSync(out)) === SHA256) {
  console.log(`yt-dlp ${VERSION} already present`);
  process.exit(0);
}
const res = await fetch(URL);
if (!res.ok) throw new Error(`download failed: ${res.status}`);
const buf = Buffer.from(await res.arrayBuffer());
if (sha(buf) !== SHA256) throw new Error("yt-dlp checksum mismatch - refusing to bundle it");
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, buf);
chmodSync(out, 0o755);
console.log(`yt-dlp ${VERSION} downloaded and verified (${buf.length} bytes)`);
