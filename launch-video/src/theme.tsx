import React from "react";
import { Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";

export const INTER = loadInter("normal", { weights: ["400", "500"], subsets: ["latin"] }).fontFamily;
export const MONO = loadMono("normal", { weights: ["500"], subsets: ["latin"] }).fontFamily;

// palette: one job per colour (see media/remake-prompt.md)
export const C = {
  canvas: "#F5F5FB",
  ink: "#0A0A12",
  sec: "#8A8FA3",
  pri: "#4F46E5",
  sky: "#38BDF8",
  rec: "#FF5A4E",
  ok: "#10B981",
  pink: "#F472B6",
};
export const GRAD = `linear-gradient(90deg, ${C.pri}, ${C.sky})`;
export const FPS = 60;
export const s = (t: number) => Math.round(t * FPS);
export const easeOut = Easing.bezier(0.22, 1, 0.36, 1);
export const easeCam = Easing.bezier(0.65, 0, 0.35, 1);
const CL = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** 0..1 over [from, to] seconds (shot-local), eased */
export const prog = (frame: number, from: number, to: number, ease = easeOut) =>
  interpolate(frame, [s(from), s(to)], [0, 1], { ...CL, easing: ease });

export const glass: React.CSSProperties = {
  background: "rgba(255,255,255,0.72)",
  backdropFilter: "blur(24px)",
  border: "1.5px solid rgba(79,70,229,0.18)",
  boxShadow: "0 24px 60px rgba(79,70,229,0.18)",
  borderRadius: 28,
};

export type W = { t: string; c?: string; at: number; w?: 400 | 500; mono?: boolean };

/** Kinetic word: blur-in + rise; its box grows so the phrase re-centres (reflow). */
export const Word: React.FC<W & { size: number; exitAt?: number }> = ({ t, c = C.ink, at, w = 400, mono, size, exitAt }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = prog(frame, at, at + 0.42);
  const grow = spring({ frame: frame - s(at), fps, config: { damping: 200 } });
  const e = exitAt === undefined ? 0 : prog(frame, exitAt, exitAt + 0.22, Easing.in(Easing.quad));
  const width = grow * (1 - e);
  return (
    <span
      style={{
        display: "inline-block",
        whiteSpace: "nowrap",
        maxWidth: width * t.length * size * 0.66,
        marginRight: width * size * 0.26,
        opacity: p * (1 - e),
        filter: `blur(${(1 - p) * 14 + e * 10}px)`,
        transform: `translateY(${(1 - p) * 22}px) scale(${0.96 + 0.04 * p})`,
        color: c,
        fontFamily: mono ? MONO : INTER,
        fontWeight: w,
        fontSize: size,
        letterSpacing: mono ? 0 : -size * 0.02,
      }}
    >
      {t}
    </span>
  );
};

export const Phrase: React.FC<{ words: W[]; size?: number; exitAt?: number; y?: number; children?: React.ReactNode }> = ({
  words, size = 64, exitAt, y = 0, children,
}) => (
  <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", transform: `translateY(${y}px)` }}>
    {words.map((w, i) => <Word key={i} {...w} size={size} exitAt={exitAt} />)}
    {children}
  </div>
);

/** Arrow cursor (navy, white outline) with press + ripple at `clickAt` (shot-local seconds). */
export const Cursor: React.FC<{ x: number; y: number; clickAt?: number; opacity?: number }> = ({ x, y, clickAt, opacity = 1 }) => {
  const frame = useCurrentFrame();
  const press = clickAt === undefined ? 0 : prog(frame, clickAt, clickAt + 0.06) - prog(frame, clickAt + 0.06, clickAt + 0.12);
  const rip = clickAt === undefined ? 0 : prog(frame, clickAt, clickAt + 0.45);
  return (
    <div style={{ position: "absolute", left: x, top: y, opacity, pointerEvents: "none" }}>
      {rip > 0 && rip < 1 && (
        <div style={{ position: "absolute", left: -30 * rip - 6, top: -30 * rip - 6, width: 60 * rip + 12, height: 60 * rip + 12,
          borderRadius: "50%", border: `3px solid ${C.pri}`, opacity: 1 - rip }} />
      )}
      <svg width="54" height="62" viewBox="0 0 27 31" style={{ transform: `scale(${1 - 0.1 * press})`, transformOrigin: "0 0",
        filter: "drop-shadow(0 6px 12px rgba(10,10,18,0.25))" }}>
        <path d="M2 2 L2 24 L8 18.5 L12.5 28 L16.5 26.2 L12 17 L20 17 Z" fill="#1E1B4B" stroke="#fff" strokeWidth="2" strokeLinejoin="round" />
      </svg>
    </div>
  );
};

export const Canvas: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ position: "absolute", inset: 0, background: `radial-gradient(120% 90% at 50% 40%, #FFFFFF 0%, ${C.canvas} 60%, #EEEEF8 100%)`, overflow: "hidden" }}>
    {children}
  </div>
);
