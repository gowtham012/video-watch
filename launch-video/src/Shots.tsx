import React from "react";
import { Img, interpolate, random, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { CameraMotionBlur } from "@remotion/motion-blur";
import { C, Canvas, Cursor, GRAD, INTER, MONO, Phrase, Word, easeCam, glass, prog, s } from "./theme";

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const abs: React.CSSProperties = { position: "absolute" };

/* ---------- shared bits ---------- */
const Chip: React.FC<{ at: number; size?: number }> = ({ at, size = 96 }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const k = spring({ frame: f - s(at), fps, config: { damping: 14, stiffness: 160 } });
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 18, ...glass, borderRadius: 999, padding: "14px 30px 14px 18px",
      marginRight: size * 0.26 * Math.min(k, 1), transform: `scale(${lerp(0.8, 1, k)})`, opacity: Math.min(1, k * 1.4),
      maxWidth: Math.min(k, 1) * 560, overflow: "hidden", whiteSpace: "nowrap" }}>
      <span style={{ width: 64, height: 46, borderRadius: 13, background: "#FF2D2D", display: "inline-flex", alignItems: "center", justifyContent: "center", flex: "none" }}>
        <svg width="22" height="24" viewBox="0 0 22 24"><path d="M2 2 L20 12 L2 22 Z" fill="#fff" /></svg>
      </span>
      <span style={{ fontFamily: MONO, fontSize: 36, color: C.ink }}>youtu.be/launch</span>
    </span>
  );
};

/* ---------- 1. Hook 0.0-4.4 ---------- */
export const S01: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <Canvas>
      {f < s(1.5) && <Phrase size={104} exitAt={1.3} words={[{ t: "Turn", c: C.pri, at: 0.1, w: 500 }, { t: "videos", at: 0.6 }]} />}
      {f >= s(1.5) && f < s(3.0) && <Phrase size={104} exitAt={2.8} words={[{ t: "into", at: 1.5 }, { t: "answers", c: C.pri, at: 1.9, w: 500 }]} />}
      {f >= s(3.0) && (
        <Phrase size={104} words={[{ t: "Any link", at: 3.0 }]} exitAt={4.15}>
          <Chip at={3.4} />
          <Word t="Instantly" c={C.pri} at={3.8} w={500} size={104} exitAt={4.15} />
        </Phrase>
      )}
    </Canvas>
  );
};

/* ---------- 2. Paste 4.4-6.2 (1.8 s) ---------- */
const MSG = "/watch youtu.be/launch   what makes this work?";
export const S02: React.FC = () => {
  const f = useCurrentFrame();
  const t = f / 60;
  const rise = prog(f, 0, 0.45);
  const drag = prog(f, 0.35, 0.8, easeCam);
  const drop = prog(f, 0.8, 0.95);
  const flash = prog(f, 0.8, 0.95) * (1 - prog(f, 0.95, 1.4));
  const n = Math.floor(Math.max(0, t - 0.85) * 40);
  const toChip = prog(f, 0, 0.3, easeCam);
  const cx = drag > 0 ? lerp(1000, 1010, drag) : lerp(1320, 1000, toChip);
  const cy = drag > 0 ? lerp(560, 712, drag) : lerp(860, 560, toChip);
  return (
    <Canvas>
      <div style={{ ...abs, inset: 0, transform: `scale(${1 + 0.08 * prog(f, 0, 1.8, easeCam)})` }}>
        <Phrase size={64} y={-280} words={[{ t: "Just", at: 0.05 }, { t: "paste", c: C.pri, at: 0.3, w: 500 }]} />
        <div style={{ ...abs, left: 0, right: 0, top: 0, bottom: 0, perspective: 1400 }}>
          <div style={{ ...abs, left: 310, top: 620 + 220 * (1 - rise), width: 1300, height: 190, ...glass, opacity: rise,
            transform: "rotateX(18deg)", border: `2px solid rgba(79,70,229,${0.18 + 0.7 * flash})`,
            boxShadow: `0 24px 60px rgba(79,70,229,${0.18 + 0.3 * flash})` }}>
            <div style={{ ...abs, left: 44, top: 30, fontFamily: INTER, fontWeight: 500, fontSize: 24, color: C.sec }}>Claude Code</div>
            <div style={{ ...abs, left: 44, top: 88, fontFamily: MONO, fontSize: 40, color: C.ink, whiteSpace: "nowrap" }}>
              <span style={{ color: C.pri }}>› </span>{MSG.slice(0, n)}
              <span style={{ display: "inline-block", width: 4, height: 44, marginLeft: 4, verticalAlign: "middle", background: C.pri,
                opacity: n < MSG.length || Math.floor(t * 3) % 2 === 0 ? 1 : 0 }} />
            </div>
          </div>
        </div>
        {/* chip carried by the cursor, then absorbed into the box */}
        <div style={{ ...abs, left: drag > 0 ? cx - 300 : 660, top: drag > 0 ? cy - 50 : 490, transform: `scale(${1 - 0.4 * drop})`, opacity: 1 - drop }}>
          <Chip at={-1} />
        </div>
        <Cursor x={cx} y={cy} clickAt={0.32} opacity={1 - prog(f, 1.0, 1.3)} />
      </div>
    </Canvas>
  );
};

/* ---------- 3. Fly-through 6.2-10.0 (3.8 s) ---------- */
const WavePanel: React.FC = () => (
  <svg width="1500" height="560" viewBox="0 0 1500 560" style={{ ...glass, borderRadius: 32 }}>
    {Array.from({ length: 60 }).map((_, i) => {
      const quiet = i > 22 && i < 30;
      const h = quiet ? 8 : 60 + 170 * Math.abs(Math.sin(i * 0.61)) * (i === 44 || i === 45 ? 1.9 : 1);
      return <rect key={i} x={60 + i * 23} y={280 - h / 2} width={14} height={h} rx={7} fill={i === 44 || i === 45 ? C.sky : C.pri} opacity={quiet ? 0.3 : 0.85} />;
    })}
    <text x="60" y="520" fontFamily={MONO} fontSize="30" fill={C.sec}>SILENCE 00:42-00:47   LOUD 01:07</text>
  </svg>
);
const MANI = [
  "[00:00.0] SAY \"video-watch turns a video into what...\"",
  "[00:00.6] FRAME #0 [start]  f000_00m00.6s.jpg",
  "[00:05.7] FRAME #2 [change] f002_00m05.7s.jpg",
  "[00:09.0] SAY \"One command, prepare, downloads...\"",
  "[00:15.0] FRAME #5 [change] f005_00m15.0s.jpg",
  "[00:19.0] SAY \"First, scene-aware keyframes...\"",
  "[00:20.9] FRAME #7 [change] f007_00m20.9s.jpg",
];
const ManifestPanel: React.FC = () => (
  <div style={{ width: 1500, height: 560, ...glass, borderRadius: 32, padding: "40px 54px", boxSizing: "border-box" }}>
    <div style={{ fontFamily: MONO, fontSize: 30, color: C.pri, marginBottom: 18 }}>manifest.md</div>
    {MANI.map((l, i) => (
      <div key={i} style={{ fontFamily: MONO, fontSize: 28, lineHeight: "62px", color: l.includes("SAY") ? C.pri : C.ink, whiteSpace: "nowrap" }}>{l}</div>
    ))}
  </div>
);
const SheetPanel: React.FC<{ src: string }> = ({ src }) => (
  <div style={{ width: 1500, height: 560, ...glass, borderRadius: 32, overflow: "hidden", padding: 18, boxSizing: "border-box" }}>
    <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover", borderRadius: 18 }} />
  </div>
);
const Wall: React.FC<{ a: React.ReactNode; b: React.ReactNode; style: React.CSSProperties }> = ({ a, b, style }) => (
  <div style={{ ...abs, display: "flex", gap: 80, ...style }}>{a}{b}{a}</div>
);

export const S03: React.FC = () => {
  const f = useCurrentFrame();
  const z = interpolate(f, [0, s(3.8)], [-1500, 1300], { easing: easeCam });
  const roll = interpolate(f, [0, s(3.8)], [-4, 6]);
  const whip = prog(f, 3.35, 3.8, easeCam);
  const sw = prog(f, 3.4, 3.8, easeCam);
  return (
    <Canvas>
      <CameraMotionBlur shutterAngle={180} samples={6}>
        <div style={{ ...abs, inset: 0, perspective: 900, transform: `translateX(${-1700 * whip}px)` }}>
          <div style={{ ...abs, left: 960, top: 540, transformStyle: "preserve-3d", transform: `translateZ(${z}px) rotateZ(${roll}deg)` }}>
            <Wall style={{ left: -2380, top: -280, transform: "translateX(-760px) rotateY(90deg)" }} a={<SheetPanel src="sheet.jpg" />} b={<ManifestPanel />} />
            <Wall style={{ left: -2380, top: -280, transform: "translateX(760px) rotateY(-90deg)" }} a={<WavePanel />} b={<SheetPanel src="kf3.jpg" />} />
            <Wall style={{ left: -2380, top: -280, transform: "translateY(-520px) rotateX(-90deg) rotateZ(90deg)" }} a={<ManifestPanel />} b={<SheetPanel src="kf5.jpg" />} />
            <Wall style={{ left: -2380, top: -280, transform: "translateY(520px) rotateX(90deg) rotateZ(90deg)" }} a={<SheetPanel src="kf2.jpg" />} b={<WavePanel />} />
          </div>
        </div>
      </CameraMotionBlur>
      <div style={{ ...abs, inset: 0, transform: `translateX(${-500 * whip}px)`, opacity: 1 - whip }}>
        {f < s(2.2) && (
          <Phrase size={84} exitAt={1.95} words={[{ t: "Frames.", c: C.pri, at: 0.3, w: 500 }, { t: "Speech.", c: C.pri, at: 0.8, w: 500 }, { t: "Sound.", c: C.pri, at: 1.3, w: 500 }]} />
        )}
        {f >= s(2.2) && <Phrase size={84} words={[{ t: "All in one", at: 2.2 }, { t: "timeline", c: C.pri, at: 2.55, w: 500 }]} />}
      </div>
      {/* swoosh streaks in: becomes the progress bar in shot 4 */}
      {sw > 0 && (
        <div style={{ ...abs, left: lerp(2100, 160, sw), top: 540 - 80, width: 1600, height: 160, borderRadius: 80, background: GRAD, filter: `blur(${lerp(40, 18, sw)}px)`, opacity: sw }} />
      )}
    </Canvas>
  );
};

/* ---------- 4. Watching 10.0-13.5 (3.5 s) ---------- */
export const S04: React.FC = () => {
  const f = useCurrentFrame();
  const settle = prog(f, 0, 0.5, easeCam);
  const fill = prog(f, 0.5, 2.85, easeCam);
  const col = prog(f, 2.9, 3.5, easeCam);
  const w = col > 0 ? lerp(1100, 120, col) : lerp(1600, 1100, settle);
  const h = col > 0 ? lerp(56, 120, col) : lerp(160, 56, settle);
  const ui = prog(f, 0.4, 0.7) * (1 - prog(f, 2.75, 2.95));
  const cy = 560;
  return (
    <Canvas>
      <div style={{ ...abs, left: 960 - w / 2, top: cy - h / 2, width: w, height: h, borderRadius: h / 2, overflow: "hidden",
        background: col > 0 ? `rgba(255,255,255,${0.4 + 0.5 * col})` : "#E6E7F2", filter: `blur(${18 * (1 - settle)}px)`,
        border: col > 0 ? `2px solid rgba(16,185,129,${col})` : "none", boxShadow: col > 0 ? "0 24px 60px rgba(79,70,229,0.18)" : "none" }}>
        <div style={{ height: "100%", width: col > 0 ? "100%" : `${Math.max(settle < 1 ? 100 : 5, fill * 100)}%`, background: GRAD, borderRadius: h / 2, opacity: 1 - col }} />
      </div>
      <div style={{ ...abs, left: 410, top: cy - 170, opacity: ui, fontFamily: INTER, fontSize: 56, color: C.ink }}>Watching</div>
      <div style={{ ...abs, right: 410, top: cy - 196, opacity: ui, fontFamily: INTER, fontSize: 104, letterSpacing: -2, color: C.pri, fontWeight: 500 }}>
        {Math.round(fill * 100)}<span style={{ color: C.sec, fontWeight: 400, opacity: 0.6 }}>/100</span>
      </div>
      <div style={{ ...abs, left: 0, right: 0, top: cy + 70, textAlign: "center", opacity: ui, fontFamily: MONO, fontSize: 30, color: C.sec }}>
        10-min video · 60 keyframes · 9 s
      </div>
    </Canvas>
  );
};

/* ---------- 5. Done 13.5-14.8 (1.3 s) ---------- */
export const S05: React.FC = () => {
  const f = useCurrentFrame();
  const t = f / 60;
  const draw = prog(f, 0.05, 0.4);
  const cols = [C.pri, C.sky, C.rec, C.pink];
  return (
    <Canvas>
      <Phrase size={84} y={-170} words={[{ t: "Done", c: C.pri, at: 0 }]} />
      <div style={{ ...abs, left: 900, top: 500, width: 120, height: 120, borderRadius: 60, ...glass, border: `2px solid ${C.ok}` }}>
        <svg width="120" height="120" viewBox="0 0 120 120" style={abs}>
          <path d="M36 62 L54 80 L86 44" fill="none" stroke={C.ok} strokeWidth="9" strokeLinecap="round" strokeLinejoin="round"
            strokeDasharray="80" strokeDashoffset={80 * (1 - draw)} />
        </svg>
      </div>
      {Array.from({ length: 90 }).map((_, i) => {
        const vx = (random(`x${i}`) * 2 - 1) * 1100;
        const vy = -(random(`y${i}`) * 900 + 300);
        const u = Math.max(0, t - 0.08);
        const x = 960 + vx * (1 - Math.exp(-u * 3)) / 1;
        const y = 560 + vy * (1 - Math.exp(-u * 3)) + 700 * u * u;
        const sz = 12 + random(`s${i}`) * 16;
        return (
          <div key={i} style={{ ...abs, left: x, top: y, width: sz, height: sz * 0.55, borderRadius: 3, background: cols[i % 4],
            opacity: u > 0 ? 1 - prog(f, 0.75, 1.3) : 0, transform: `rotate(${random(`r${i}`) * 360 + u * 540}deg)` }} />
        );
      })}
    </Canvas>
  );
};

/* ---------- 6. Every moment 14.8-19.0 (4.2 s) ---------- */
const KF = [["kf1.jpg", "00:15", "change"], ["kf2.jpg", "00:29", "cut"], ["kf3.jpg", "00:38", "change"], ["kf4.jpg", "00:48", "change"],
  ["kf5.jpg", "00:57", "cut"], ["kf6.jpg", "01:04", "change"]];
const FrameCard: React.FC<{ src: string; ts: string; tag: string; lift?: number }> = ({ src, ts, tag, lift = 0 }) => (
  <div style={{ width: 380, ...glass, borderRadius: 24, padding: 14, boxSizing: "border-box", transform: `translateY(${-24 * lift}px) scale(${1 + 0.08 * lift})`,
    border: `${1.5 + 1.5 * lift}px solid rgba(79,70,229,${0.18 + 0.7 * lift})`, boxShadow: `0 ${24 + 16 * lift}px ${60 + 30 * lift}px rgba(79,70,229,${0.18 + 0.22 * lift})` }}>
    <Img src={staticFile(src)} style={{ width: 352, height: 198, objectFit: "cover", borderRadius: 14, display: "block" }} />
    <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 14 }}>
      <span style={{ fontFamily: MONO, fontSize: 26, color: C.pri }}>{ts}</span>
      <span style={{ fontFamily: INTER, fontSize: 20, color: C.sec, background: "rgba(79,70,229,0.08)", borderRadius: 999, padding: "4px 12px" }}>{tag}</span>
    </div>
  </div>
);
export const S06: React.FC = () => {
  const f = useCurrentFrame();
  const glide = prog(f, 0, 3.0, easeCam);
  const rowX = lerp(1500, 350, glide);
  const rx = lerp(16, 0, glide), ry = lerp(-18, 0, glide);
  const lift = prog(f, 3.55, 3.85);
  const toCard = prog(f, 2.9, 3.45, easeCam);
  return (
    <Canvas>
      <Phrase size={64} y={-330} words={[{ t: "Every moment,", at: 0.1 }, { t: "timestamped", c: C.pri, at: 0.45, w: 500 }]} />
      <div style={{ ...abs, inset: 0, perspective: 1600 }}>
        <div style={{ ...abs, left: rowX, top: 400, display: "flex", gap: 40, transform: `rotateX(${rx}deg) rotateY(${ry}deg)`, transformOrigin: "610px 150px" }}>
          {KF.map(([src, ts, tag], i) => {
            const e = prog(f, 0.15 + 0.12 * i, 0.6 + 0.12 * i);
            return (
              <div key={i} style={{ opacity: e, transform: `translateX(${200 * (1 - e)}px)`, filter: `blur(${(1 - e) * 10}px)` }}>
                <FrameCard src={src} ts={ts} tag={tag} lift={i === 1 ? lift : 0} />
              </div>
            );
          })}
        </div>
      </div>
      <Cursor x={lerp(1350, 990, toCard)} y={lerp(900, 560, toCard)} clickAt={3.5} opacity={prog(f, 2.8, 3.0)} />
    </Canvas>
  );
};

/* ---------- 7. Re-watch 19.0-21.0 (2.0 s) ---------- */
const FAN = [[-600, -250, -14, 28], [600, -250, 12, -28], [-650, 250, 10, 22], [640, 260, -12, -22], [-260, -360, -6, 10], [270, 370, 7, -12]];
export const S07: React.FC = () => {
  const f = useCurrentFrame();
  const fan = prog(f, 0.05, 0.75, easeCam);
  const whip = prog(f, 1.55, 2.0, easeCam);
  return (
    <Canvas>
      <CameraMotionBlur shutterAngle={180} samples={6}>
        <div style={{ ...abs, inset: 0, perspective: 1600, transform: `translateX(${-1800 * whip}px)` }}>
          {FAN.map(([x, y, rz, ry], i) => (
            <div key={i} style={{ ...abs, left: 960 - 190 + x * fan, top: 560 - 150 + y * fan,
              transform: `rotateZ(${rz * fan}deg) rotateY(${ry * fan}deg) scale(${lerp(1.08, 0.82, fan)})`, opacity: i === 0 ? 1 : Math.min(1, fan * 3) }}>
              <FrameCard src={`z${i + 1}.jpg`} ts={`00:${String(19 + Math.round(i * 2.6)).padStart(2, "0")}`} tag="zoom" />
            </div>
          ))}
        </div>
      </CameraMotionBlur>
      <div style={{ ...abs, inset: 0, opacity: 1 - whip }}>
        <Phrase size={84} words={[{ t: "Re-watch", at: 0.35 }, { t: "any moment", c: C.pri, at: 0.7, w: 500 }]} />
        <div style={{ ...abs, left: 0, right: 0, top: 640, textAlign: "center", fontFamily: MONO, fontSize: 30, color: C.sec, opacity: prog(f, 0.9, 1.2) }}>
          vw.py zoom --start 0:19 --end 0:32 --fps 6
        </div>
      </div>
    </Canvas>
  );
};

/* ---------- 8. The answer 21.0-24.0 (3.0 s) ---------- */
const ANS = [["00:03", "Hook lands in 3 seconds", C.ok], ["01:34", "Checkout button never responds", C.rec], ["07:40", "CTA appears too late", C.rec]];
const CHIPS = [["Critique", 200], ["Summarize", 230], ["Remake it with my content", 420]] as const;
export const S08: React.FC = () => {
  const f = useCurrentFrame();
  const enter = prog(f, 0, 0.45);
  const flat = prog(f, 1.2, 1.8, easeCam);
  const click = prog(f, 2.4, 2.6);
  const toChip = prog(f, 1.75, 2.35, easeCam);
  return (
    <Canvas>
      <div style={{ ...abs, inset: 0, perspective: 1800 }}>
        <div style={{ ...abs, left: 360, top: 230 + 120 * (1 - enter), width: 1200, height: 620, ...glass, opacity: enter, boxSizing: "border-box", padding: "48px 60px",
          transform: `rotateY(${lerp(-12, 0, flat)}deg) rotateX(${lerp(7, 0, flat)}deg)` }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div style={{ width: 34, height: 34, borderRadius: 17, background: C.pri }} />
            <span style={{ fontFamily: INTER, fontWeight: 500, fontSize: 36, color: C.ink }}>Claude</span>
            <span style={{ marginLeft: "auto", fontFamily: INTER, fontSize: 24, color: C.sec }}>every claim, timestamped</span>
          </div>
          {ANS.map(([ts, txt, dot], i) => {
            const p = prog(f, 0.45 + 0.3 * i, 0.85 + 0.3 * i);
            return (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 24, marginTop: i ? 34 : 56, opacity: p, transform: `translateY(${20 * (1 - p)}px)`, filter: `blur(${(1 - p) * 8}px)` }}>
                <div style={{ width: 18, height: 18, borderRadius: 9, background: dot }} />
                <span style={{ fontFamily: MONO, fontSize: 34, color: C.pri }}>[{ts}]</span>
                <span style={{ fontFamily: INTER, fontSize: 44, color: C.ink }}>{txt}</span>
              </div>
            );
          })}
          <div style={{ ...abs, left: 60, top: 500, display: "flex", gap: 20, opacity: prog(f, 1.4, 1.7) }}>
            {CHIPS.map(([label, w], i) => (
              <div key={i} style={{ width: w, height: 64, borderRadius: 32, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: INTER,
                fontWeight: 500, fontSize: 26, border: "1.5px solid rgba(79,70,229,0.25)",
                background: i === 2 && click > 0 ? GRAD : "rgba(255,255,255,0.9)", color: i === 2 && click > 0 ? "#fff" : C.ink,
                boxShadow: i === 2 ? `0 12px 40px rgba(79,70,229,${0.35 * click})` : "none", transform: i === 2 ? `scale(${1 + 0.04 * click})` : undefined }}>{label}</div>
            ))}
          </div>
        </div>
      </div>
      <Cursor x={lerp(1450, 1110, toChip)} y={lerp(980, 762, toChip)} clickAt={2.4} opacity={prog(f, 1.7, 1.85)} />
    </Canvas>
  );
};

/* ---------- 9. Install 24.0-25.0 (1.0 s) ---------- */
const Button: React.FC<{ on: number; w?: number; h?: number; text?: number; bg?: string }> = ({ on, w = 560, h = 110, text = 1, bg }) => (
  <div style={{ ...abs, left: 960 - w / 2, top: 540 - h / 2, width: w, height: h, borderRadius: h / 2, overflow: "hidden",
    background: bg ?? (on > 0 ? GRAD : C.ink), boxShadow: `0 20px 60px rgba(79,70,229,${0.15 + 0.35 * on})`,
    display: "flex", alignItems: "center", justifyContent: "center" }}>
    <span style={{ fontFamily: INTER, fontWeight: 500, fontSize: 40, color: "#fff", opacity: text, whiteSpace: "nowrap" }}>Install in Claude Code</span>
  </div>
);
export const S09: React.FC = () => {
  const f = useCurrentFrame();
  const inn = prog(f, 0, 0.25);
  const to = prog(f, 0, 0.4, easeCam);
  return (
    <Canvas>
      <div style={{ ...abs, inset: 0, transform: `scale(${lerp(0.9, 1, inn) * (1 + 0.05 * prog(f, 0, 1, easeCam))})`, opacity: inn }}>
        <Button on={prog(f, 0.45, 0.6)} />
      </div>
      <Cursor x={lerp(1260, 1010, to)} y={lerp(820, 560, to)} clickAt={0.45} />
    </Canvas>
  );
};

/* ---------- 10. Rec dot -> tagline 25.0-28.5 (3.5 s) ---------- */
export const dotPath = (f: number) => {
  const c = prog(f, 0, 0.4, easeCam);
  const back = prog(f, 0.4, 0.6, easeCam);
  const go = prog(f, 0.6, 1.95, easeCam);
  const x = go > 0 ? lerp(380, 1580, go) : lerp(960, 380, back);
  return { c, x, y: 560, go };
};
export const S10: React.FC = () => {
  const f = useCurrentFrame();
  const { c, x, y, go } = dotPath(f);
  const speed = go > 0 && go < 1 ? 1 - Math.abs(go - 0.5) * 2 : 0;
  return (
    <Canvas>
      {c < 1 && <Button on={1} w={lerp(560, 36, c)} h={lerp(110, 36, c)} text={1 - c * 3} bg={c > 0.5 ? C.rec : undefined} />}
      <Phrase size={120} exitAt={3.2} words={[{ t: "Skim.", c: C.pri, at: 0.85, w: 500 }, { t: "Zoom.", c: "#8B85EF", at: 1.35, w: 500 }, { t: "Answer.", at: 1.85, w: 500 }]} />
      {c >= 1 && (
        <>
          <div style={{ ...abs, left: x - 420 * speed, top: y - 4, width: 420 * speed, height: 8, borderRadius: 4,
            background: `linear-gradient(90deg, rgba(255,90,78,0), ${C.rec})`, filter: "blur(2px)" }} />
          <div style={{ ...abs, left: x - 18, top: y - 18, width: 36, height: 36, borderRadius: 18, background: C.rec, boxShadow: `0 0 ${20 + 30 * speed}px ${C.rec}` }} />
        </>
      )}
    </Canvas>
  );
};

/* ---------- 11. Logo + CTA 28.5-33.0 (4.5 s) ---------- */
const URL = "github.com/gowtham012/video-watch";
export const S11: React.FC = () => {
  const f = useCurrentFrame();
  const t = f / 60;
  const snap = prog(f, 0, 0.4, easeCam);
  const mark = prog(f, 0.25, 0.6);
  const word = prog(f, 0.45, 0.9);
  const n = Math.floor(Math.max(0, t - 1.1) * 30);
  const pill = prog(f, 1.9, 2.3);
  const L = 548; // left edge of mark: mark 150 + gap 36 + wordmark ≈ 850 px, row centred on 960
  return (
    <Canvas>
      <div style={{ ...abs, left: L, top: 465, width: 150, height: 150, borderRadius: 40, background: C.pri, opacity: mark, transform: `scale(${lerp(0.9, 1, mark)})`,
        display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 24px 60px rgba(79,70,229,0.3)" }}>
        <svg width="56" height="64" viewBox="0 0 56 64"><path d="M6 4 Q6 0 10 2 L52 28 Q56 32 52 36 L10 62 Q6 64 6 60 Z" fill="#fff" /></svg>
      </div>
      <div style={{ ...abs, left: L + 186, top: 470, height: 140, overflow: "hidden", display: "flex", alignItems: "center" }}>
        <span style={{ fontFamily: INTER, fontWeight: 500, fontSize: 116, letterSpacing: -3, color: C.ink, opacity: word,
          transform: `translateX(${-80 * (1 - word)}px)`, display: "inline-block" }}>video-watch</span>
      </div>
      <div style={{ ...abs, left: lerp(1580, L + 150 - 22, snap) - 18 + 18, top: lerp(560, 465 - 4, snap) - 18 + 4, width: lerp(36, 32, snap), height: lerp(36, 32, snap),
        borderRadius: 18, background: C.rec, boxShadow: `0 0 0 ${6 * snap}px ${C.canvas}` }} />
      <div style={{ ...abs, left: 0, right: 0, top: 680, textAlign: "center", fontFamily: MONO, fontSize: 36, color: C.sec }}>{URL.slice(0, n)}</div>
      <div style={{ ...abs, left: 960 - 470, top: 760, width: 940, height: 84, ...glass, borderRadius: 42, opacity: pill, transform: `translateY(${16 * (1 - pill)}px)`,
        display: "flex", alignItems: "center", justifyContent: "center", fontFamily: MONO, fontSize: 34, color: C.pri }}>
        /plugin install video-watch@video-watch
      </div>
    </Canvas>
  );
};
